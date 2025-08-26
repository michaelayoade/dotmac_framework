"""
RBAC SDK for Platform using contract-first design with Pydantic v2.

Provides Role-Based Access Control functionality with comprehensive permission
checking, role management, and hierarchical role support.
"""

import logging
from datetime import datetime
from typing import Any, Optional, List

from dotmac_isp.sdks.contracts.rbac import (
    BulkPermissionCheckRequest,
    BulkPermissionCheckResponse,
    Permission,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionScope,
    ResourceType,
    Role,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    RoleHierarchyResponse,
    UserRole,
    UserRolesResponse,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class RBACError(Exception):
    """Base RBAC error."""

    pass


class PermissionDeniedError(RBACError):
    """Permission denied error."""

    pass


class RoleNotFoundError(RBACError):
    """Role not found error."""

    pass


class UserNotFoundError(RBACError):
    """User not found error."""

    pass


class CircularRoleError(RBACError):
    """Circular role dependency error."""

    pass


class RBACSDKConfig:
    """RBAC SDK configuration."""

    def __init__(
        self,
        cache_ttl: int = 300,
        max_role_depth: int = 5,
        enable_caching: bool = True,
        enable_audit_logging: bool = True,
        default_permissions: Optional[List[str]] = None,
        system_roles: Optional[List[str]] = None,
    ):
        """Initialize RBAC SDK."""
        self.cache_ttl = cache_ttl
        self.max_role_depth = max_role_depth
        self.enable_caching = enable_caching
        self.enable_audit_logging = enable_audit_logging
        self.default_permissions = default_permissions or []
        self.system_roles = system_roles or ["super_admin", "admin", "user"]


class RBACSDK:
    """
    Contract-first RBAC SDK with comprehensive permission checking and role management.

    Features:
    - Hierarchical role support with inheritance
    - Permission caching for performance
    - Bulk permission checking
    - Audit logging for security compliance
    - Tenant isolation support
    - Circular dependency detection
    - Wildcard permission matching
    """

    def __init__(
        self,
        config: RBACSDKConfig | None = None,
        cache_sdk: Any | None = None,
        database_sdk: Any | None = None,
    ):
        """Initialize RBAC SDK."""
        self.config = config or RBACSDKConfig()
        self.cache_sdk = cache_sdk
        self.database_sdk = database_sdk

        # In-memory stores for testing/fallback
        self._roles: dict[str, Role] = {}
        self._permissions: dict[str, Permission] = {}
        self._user_roles: dict[str, list[UserRole]] = {}
        self._role_hierarchy: dict[str, set[str]] = {}  # role -> parent roles

        # Performance tracking
        self._stats = {
            "permission_checks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "role_assignments": 0,
            "permission_denials": 0,
        }

        # Initialize default roles and permissions
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default roles and permissions."""
        # Default permissions
        default_perms = [
            Permission(
                name="profile.read",
                description="Read own profile",
                resource_type=ResourceType.USER,
                scope=PermissionScope.READ,
            ),
            Permission(
                name="profile.write",
                description="Update own profile",
                resource_type=ResourceType.USER,
                scope=PermissionScope.WRITE,
            ),
            Permission(
                name="users.read",
                description="Read user information",
                resource_type=ResourceType.USER,
                scope=PermissionScope.READ,
            ),
            Permission(
                name="users.write",
                description="Create and update users",
                resource_type=ResourceType.USER,
                scope=PermissionScope.WRITE,
            ),
            Permission(
                name="users.delete",
                description="Delete users",
                resource_type=ResourceType.USER,
                scope=PermissionScope.DELETE,
            ),
            Permission(
                name="roles.admin",
                description="Manage roles and permissions",
                resource_type=ResourceType.ROLE,
                scope=PermissionScope.ADMIN,
            ),
            Permission(
                name="system.admin",
                description="System administration",
                resource_type=ResourceType.SYSTEM,
                scope=PermissionScope.ADMIN,
                is_system=True,
            ),
        ]

        for perm in default_perms:
            self._permissions[perm.name] = perm

        # Default roles
        default_roles = [
            Role(
                name="user",
                display_name="User",
                description="Standard user with basic permissions",
                permissions=["profile.read", "profile.write"],
                is_default=True,
            ),
            Role(
                name="developer",
                display_name="Developer",
                description="Developer with read/write permissions for development tasks",
                permissions=["users.read", "profile.read", "profile.write"],
                parent_roles=["user"],
            ),
            Role(
                name="manager",
                display_name="Manager",
                description="Manager with user management permissions",
                permissions=["users.read", "users.write"],
                parent_roles=["user"],
            ),
            Role(
                name="admin",
                display_name="Administrator",
                description="Administrator with full user and role management",
                permissions=[
                    "users.read",
                    "users.write",
                    "users.delete",
                    "roles.admin",
                    "system.admin",
                ],
                parent_roles=["manager"],
            ),
            Role(
                name="super_admin",
                display_name="Super Administrator",
                description="Super administrator with system access",
                permissions=["system.admin"],
                parent_roles=["admin"],
                is_system=True,
            ),
        ]

        for role in default_roles:
            self._roles[role.name] = role
            self._role_hierarchy[role.name] = set(role.parent_roles)

    async def _get_cache_key(
        self, key_type: str, identifier: str, tenant_id: str | None = None
    ) -> str:
        """Generate cache key with tenant isolation."""
        tenant_prefix = f"tenant:{tenant_id}:" if tenant_id else "global:"
        return f"rbac:{tenant_prefix}{key_type}:{identifier}"

    async def _cache_get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return None

        try:
            result = await self.cache_sdk.get(key)
            if result is not None:
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1
            return result
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            self._stats["cache_misses"] += 1
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.set(key, value, ttl or self.config.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")

    async def _cache_delete(self, key: str) -> None:
        """Delete value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")

    def _match_permission(self, required: str, granted: str) -> bool:
        """Check if granted permission matches required permission."""
        # Exact match
        if required == granted:
            return True

        # Wildcard match
        if granted.endswith(".*"):
            prefix = granted[:-2]
            return required.startswith(prefix + ".")

        return granted == "*"

    def _get_effective_permissions(
        self, roles: list[str], tenant_id: str | None = None
    ) -> set[str]:
        """Get all effective permissions for a list of roles."""
        effective_perms = set()

        # Add default permissions
        effective_perms.update(self.config.default_permissions)

        # Process each role and its hierarchy
        processed_roles = set()

        def process_role(role_name: str, depth: int = 0) -> None:
            """Process Role operation."""
            if depth > self.config.max_role_depth:
                logger.warning(f"Max role depth exceeded for role {role_name}")
                return

            if role_name in processed_roles:
                return

            processed_roles.add(role_name)

            # Get role
            role = self._roles.get(role_name)
            if not role:
                logger.warning(f"Role not found: {role_name}")
                return

            # Add role permissions
            effective_perms.update(role.permissions)

            # Process parent roles
            for parent_role in role.parent_roles:
                process_role(parent_role, depth + 1)

        # Process all roles
        for role_name in roles:
            process_role(role_name)

        return effective_perms

    async def check_permission(
        self,
        request: PermissionCheckRequest,
        context: RequestContext | None = None,
    ) -> PermissionCheckResponse:
        """Check if user has specific permission."""
        start_time = datetime.now(UTC)
        self._stats["permission_checks"] += 1

        try:
            tenant_id = (
                context.headers.x_tenant_id
                if context
                else request.context.get("tenant_id")
            )

            # Get user roles from cache first
            cache_key = await self._get_cache_key(
                "user_roles", request.user_id, tenant_id
            )
            cached_roles = await self._cache_get(cache_key)

            if cached_roles is None:
                # Get from database or fallback to in-memory
                user_roles = self._user_roles.get(request.user_id, [])
                # Filter active roles
                active_roles = [
                    ur
                    for ur in user_roles
                    if not ur.is_expired
                    and (
                        not tenant_id
                        or not ur.conditions.get("tenant_id")
                        or ur.conditions.get("tenant_id") == tenant_id
                    )
                ]
                role_names = [ur.role_name for ur in active_roles]

                # Cache the result
                await self._cache_set(cache_key, role_names)
            else:
                role_names = cached_roles

            # Get effective permissions
            effective_permissions = self._get_effective_permissions(
                role_names, tenant_id
            )

            # Check permission
            allowed = False
            matched_roles = []
            matched_permissions = []

            for perm in effective_permissions:
                if self._match_permission(request.permission, perm):
                    allowed = True
                    matched_permissions.append(perm)

                    # Find which roles granted this permission
                    for role_name in role_names:
                        role = self._roles.get(role_name)
                        if role and perm in self._get_effective_permissions(
                            [role_name], tenant_id
                        ):
                            if role_name not in matched_roles:
                                matched_roles.append(role_name)
                    break

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Permission check: user={request.user_id}, permission={request.permission}, "
                    f"allowed={allowed}, roles={matched_roles}, tenant={tenant_id}"
                )

            if not allowed:
                self._stats["permission_denials"] += 1

            end_time = datetime.now(UTC)
            evaluation_time = (end_time - start_time).total_seconds() * 1000

            return PermissionCheckResponse(
                allowed=allowed,
                user_id=request.user_id,
                permission=request.permission,
                matched_roles=matched_roles,
                matched_permissions=matched_permissions,
                denial_reason="Insufficient permissions" if not allowed else None,
                evaluation_time_ms=evaluation_time,
            )

        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            end_time = datetime.now(UTC)
            evaluation_time = (end_time - start_time).total_seconds() * 1000

            return PermissionCheckResponse(
                allowed=False,
                user_id=request.user_id,
                permission=request.permission,
                matched_roles=[],
                matched_permissions=[],
                denial_reason=f"Permission check error: {str(e)}",
                evaluation_time_ms=evaluation_time,
            )

    async def check_permissions_bulk(
        self,
        request: BulkPermissionCheckRequest,
        context: RequestContext | None = None,
    ) -> BulkPermissionCheckResponse:
        """Check multiple permissions for a user."""
        start_time = datetime.now(UTC)

        # Check each permission
        results = {}
        allowed_count = 0

        for permission in request.permissions:
            perm_request = PermissionCheckRequest(
                user_id=request.user_id,
                permission=permission,
                context=request.context,
            )

            perm_response = await self.check_permission(perm_request, context)
            results[permission] = perm_response.allowed

            if perm_response.allowed:
                allowed_count += 1

        end_time = datetime.now(UTC)
        evaluation_time = (end_time - start_time).total_seconds() * 1000

        return BulkPermissionCheckResponse(
            user_id=request.user_id,
            results=results,
            allowed_count=allowed_count,
            total_count=len(request.permissions),
            evaluation_time_ms=evaluation_time,
        )

    async def assign_role(
        self,
        request: RoleAssignmentRequest,
        context: RequestContext | None = None,
    ) -> RoleAssignmentResponse:
        """Assign role to user."""
        try:
            # Validate role exists
            if request.role_name not in self._roles:
                return RoleAssignmentResponse(
                    success=False,
                    user_id=request.user_id,
                    role_name=request.role_name,
                    error="Role does not exist",
                )

            # Create user role assignment with tenant context
            conditions = request.conditions.model_copy() if request.conditions else {}
            if context and context.headers and context.headers.x_tenant_id:
                conditions["tenant_id"] = context.headers.x_tenant_id

            user_role = UserRole(
                user_id=request.user_id,
                role_name=request.role_name,
                granted_by=(
                    context.headers.x_user_id if context and context.headers else None
                ),
                expires_at=request.expires_at,
                conditions=conditions,
            )

            # Add to user roles
            if request.user_id not in self._user_roles:
                self._user_roles[request.user_id] = []

            # Check if role already assigned
            existing_roles = self._user_roles[request.user_id]
            for existing_role in existing_roles:
                if existing_role.role_name == request.role_name:
                    return RoleAssignmentResponse(
                        success=False,
                        user_id=request.user_id,
                        role_name=request.role_name,
                        error="Role already assigned to user",
                    )

            self._user_roles[request.user_id].append(user_role)
            self._stats["role_assignments"] += 1

            # Clear cache
            tenant_id = (
                context.headers.x_tenant_id
                if context and context.headers
                else request.conditions.get("tenant_id")
            )
            cache_key = await self._get_cache_key(
                "user_roles", request.user_id, tenant_id
            )
            await self._cache_delete(cache_key)

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Role assigned: user={request.user_id}, role={request.role_name}, "
                    f"granted_by={context.headers.x_user_id if context and context.headers else 'system'}, tenant={tenant_id}"
                )

            return RoleAssignmentResponse(
                success=True,
                user_id=request.user_id,
                role_name=request.role_name,
                assignment_id=f"assignment-{request.user_id}-{request.role_name}",
            )

        except Exception as e:
            logger.error(f"Role assignment failed: {e}")
            return RoleAssignmentResponse(
                success=False,
                user_id=request.user_id,
                role_name=request.role_name,
                error=f"Assignment failed: {str(e)}",
            )

    async def revoke_role(
        self,
        user_id: str,
        role_name: str,
        context: RequestContext | None = None,
    ) -> RoleAssignmentResponse:
        """Revoke role from user."""
        try:
            if user_id not in self._user_roles:
                return RoleAssignmentResponse(
                    success=False,
                    user_id=user_id,
                    role_name=role_name,
                    error="User has no role assignments",
                )

            # Find and remove role
            user_roles = self._user_roles[user_id]
            for i, user_role in enumerate(user_roles):
                if user_role.role_name == role_name:
                    del user_roles[i]

                    # Clear cache
                    tenant_id = context.tenant_id if context else None
                    cache_key = await self._get_cache_key(
                        "user_roles", user_id, tenant_id
                    )
                    await self._cache_delete(cache_key)

                    # Audit logging
                    if self.config.enable_audit_logging:
                        logger.info(
                            f"Role revoked: user={user_id}, role={role_name}, "
                            f"revoked_by={context.headers.x_user_id if context and context.headers else 'system'}"
                        )

                    return RoleAssignmentResponse(
                        success=True,
                        user_id=user_id,
                        role_name=role_name,
                    )

            return RoleAssignmentResponse(
                success=False,
                user_id=user_id,
                role_name=role_name,
                error="Role not assigned to user",
            )

        except Exception as e:
            logger.error(f"Role revocation failed: {e}")
            return RoleAssignmentResponse(
                success=False,
                user_id=user_id,
                role_name=role_name,
                error=f"Revocation failed: {str(e)}",
            )

    async def get_user_roles(
        self,
        user_id: str,
        context: RequestContext | None = None,
    ) -> UserRolesResponse:
        """Get all roles assigned to a user."""
        tenant_id = context.tenant_id if context else None

        # Get user roles
        user_roles = self._user_roles.get(user_id, [])

        # Filter by tenant and active roles
        active_roles = [
            ur
            for ur in user_roles
            if not ur.is_expired
            and (not tenant_id or ur.conditions.get("tenant_id") == tenant_id)
        ]

        # Get effective permissions
        role_names = [ur.role_name for ur in active_roles]
        effective_permissions = list(
            self._get_effective_permissions(role_names, tenant_id)
        )

        # Check if user is admin
        is_admin = any(
            self._match_permission("system.admin", perm)
            or self._match_permission("roles.admin", perm)
            for perm in effective_permissions
        )

        return UserRolesResponse(
            user_id=user_id,
            roles=active_roles,
            effective_permissions=effective_permissions,
            is_admin=is_admin,
        )

    async def get_role_hierarchy(self) -> RoleHierarchyResponse:
        """Get complete role hierarchy and permissions."""
        hierarchy = {}
        permissions_map = {}

        for role_name, role in self._roles.items():
            # Build hierarchy (role -> child roles)
            children = []
            for other_role_name, other_role in self._roles.items():
                if role_name in other_role.parent_roles:
                    children.append(other_role_name)
            hierarchy[role_name] = children

            # Build permissions map
            effective_perms = self._get_effective_permissions([role_name])
            permissions_map[role_name] = list(effective_perms)

        return RoleHierarchyResponse(
            roles=list(self._roles.values()),
            hierarchy=hierarchy,
            permissions_map=permissions_map,
        )

    async def create_role(
        self,
        role: Role,
        context: RequestContext | None = None,
    ) -> bool:
        """Create a new role."""
        try:
            # Validate role doesn't exist
            if role.name in self._roles:
                raise ValueError(f"Role {role.name} already exists")

            # Validate parent roles exist
            for parent_role in role.parent_roles:
                if parent_role not in self._roles:
                    raise ValueError(f"Parent role {parent_role} does not exist")

            # Check for circular dependencies
            if self._would_create_cycle(role.name, role.parent_roles):
                raise CircularRoleError(
                    f"Role {role.name} would create circular dependency"
                )

            # Add role
            self._roles[role.name] = role
            self._role_hierarchy[role.name] = set(role.parent_roles)

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Role created: name={role.name}, permissions={role.permissions}, "
                    f"parents={role.parent_roles}, created_by={context.headers.x_user_id if context and context.headers else 'system'}"
                )

            return True

        except Exception as e:
            logger.error(f"Role creation failed: {e}")
            raise

    def _would_create_cycle(self, role_name: str, parent_roles: list[str]) -> bool:
        """Check if adding parent roles would create a circular dependency."""

        def has_path(start: str, end: str, visited: set[str]) -> bool:
            """Has Path operation."""
            if start == end:
                return True
            if start in visited:
                return False

            visited.add(start)
            for parent in self._role_hierarchy.get(start, set()):
                if has_path(parent, end, visited):
                    return True
            return False

        # Check if any parent role has a path back to this role
        for parent_role in parent_roles:
            if has_path(parent_role, role_name, set()):
                return True

        return False

    async def get_stats(self) -> dict[str, Any]:
        """Get RBAC performance statistics."""
        return {
            **self._stats,
            "total_roles": len(self._roles),
            "total_permissions": len(self._permissions),
            "total_user_assignments": sum(
                len(roles) for roles in self._user_roles.values()
            ),
            "cache_hit_rate": (
                self._stats["cache_hits"]
                / (self._stats["cache_hits"] + self._stats["cache_misses"])
                if (self._stats["cache_hits"] + self._stats["cache_misses"]) > 0
                else 0.0
            ),
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        try:
            # Test basic functionality
            test_request = PermissionCheckRequest(
                user_id="health_check_user",
                permission="test.permission",
            )

            start_time = datetime.now(UTC)
            await self.check_permission(test_request)
            end_time = datetime.now(UTC)

            response_time = (end_time - start_time).total_seconds() * 1000

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "roles_count": len(self._roles),
                "permissions_count": len(self._permissions),
                "cache_enabled": self.config.enable_caching,
                "audit_enabled": self.config.enable_audit_logging,
            }

        except Exception as e:
            logger.error(f"RBAC health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "roles_count": len(self._roles),
                "permissions_count": len(self._permissions),
            }


__all__ = [
    "RBACSDKConfig",
    "RBACDK",
    "RBACError",
    "PermissionDeniedError",
    "RoleNotFoundError",
    "UserNotFoundError",
    "CircularRoleError",
]
