"""
Role-Based Access Control (RBAC) System

Implements comprehensive RBAC with:
- Hierarchical permission system
- Tenant-scoped permissions
- Dynamic permission checking
- Role inheritance
- Resource-based access control
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions following resource:action pattern."""

    # System-level permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_READ = "system:read"
    SYSTEM_MONITOR = "system:monitor"

    # Tenant management
    TENANT_ADMIN = "tenant:admin"
    TENANT_CREATE = "tenant:create"
    TENANT_DELETE = "tenant:delete"
    TENANT_UPDATE = "tenant:update"
    TENANT_READ = "tenant:read"

    # User management
    USER_ADMIN = "user:admin"
    USER_CREATE = "user:create"
    USER_DELETE = "user:delete"
    USER_UPDATE = "user:update"
    USER_READ = "user:read"
    USER_IMPERSONATE = "user:impersonate"

    # Customer management
    CUSTOMER_ADMIN = "customer:admin"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_DELETE = "customer:delete"
    CUSTOMER_UPDATE = "customer:update"
    CUSTOMER_READ = "customer:read"
    CUSTOMER_BILLING = "customer:billing"

    # Billing permissions
    BILLING_ADMIN = "billing:admin"
    BILLING_CREATE = "billing:create"
    BILLING_UPDATE = "billing:update"
    BILLING_DELETE = "billing:delete"
    BILLING_READ = "billing:read"
    BILLING_INVOICE = "billing:invoice"
    BILLING_PAYMENT = "billing:payment"
    BILLING_REFUND = "billing:refund"

    # Network management
    NETWORK_ADMIN = "network:admin"
    NETWORK_CONFIG = "network:config"
    NETWORK_MONITOR = "network:monitor"
    NETWORK_PROVISION = "network:provision"
    NETWORK_READ = "network:read"

    # Service management
    SERVICE_ADMIN = "service:admin"
    SERVICE_CREATE = "service:create"
    SERVICE_UPDATE = "service:update"
    SERVICE_DELETE = "service:delete"
    SERVICE_READ = "service:read"
    SERVICE_PROVISION = "service:provision"

    # Analytics and reporting
    ANALYTICS_ADMIN = "analytics:admin"
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_CREATE = "analytics:create"

    # Support and ticketing
    SUPPORT_ADMIN = "support:admin"
    SUPPORT_CREATE = "support:create"
    SUPPORT_UPDATE = "support:update"
    SUPPORT_DELETE = "support:delete"
    SUPPORT_READ = "support:read"
    SUPPORT_ASSIGN = "support:assign"

    # Field operations
    FIELD_ADMIN = "field:admin"
    FIELD_ASSIGN = "field:assign"
    FIELD_SCHEDULE = "field:schedule"
    FIELD_READ = "field:read"

    # Inventory management
    INVENTORY_ADMIN = "inventory:admin"
    INVENTORY_CREATE = "inventory:create"
    INVENTORY_UPDATE = "inventory:update"
    INVENTORY_DELETE = "inventory:delete"
    INVENTORY_READ = "inventory:read"

    # Plugin management
    PLUGIN_ADMIN = "plugin:admin"
    PLUGIN_INSTALL = "plugin:install"
    PLUGIN_UNINSTALL = "plugin:uninstall"
    PLUGIN_CONFIG = "plugin:config"
    PLUGIN_READ = "plugin:read"

    # Portal access
    PORTAL_ADMIN = "portal:admin"
    PORTAL_CUSTOMER = "portal:customer"
    PORTAL_RESELLER = "portal:reseller"
    PORTAL_TECHNICIAN = "portal:technician"

    # API access
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"

    # Field operations (additional permissions)
    FIELD_OPS_READ = "field_ops:read"
    FIELD_OPS_UPDATE = "field_ops:update"

    # Network technician permissions
    NETWORK_TECHNICIAN = "network:technician"
    SUPPORT_TECHNICIAN = "support:technician"

    # Reseller permissions
    RESELLER_READ = "reseller:read"
    RESELLER_UPDATE = "reseller:update"

    @classmethod
    def from_resource_action(cls, resource: str, action: str) -> Optional["Permission"]:
        """Create Permission from resource and action.

        Args:
            resource: Resource name (e.g., 'billing', 'customer')
            action: Action name (e.g., 'read', 'write', 'admin')

        Returns:
            Permission if found, None otherwise
        """
        permission_value = f"{resource}:{action}"

        # Try to find exact match
        for permission in cls:
            if permission.value == permission_value:
                return permission

        # Try common variations
        variations = [
            f"{resource}:{action}",
            f"{resource.lower()}:{action.lower()}",
            f"{resource.upper()}:{action.upper()}",
        ]

        for variation in variations:
            for permission in cls:
                if permission.value == variation:
                    return permission

        return None


class Role(Enum):
    """System roles with hierarchical structure."""

    # Super admin - platform-wide access
    SUPER_ADMIN = "super_admin"

    # Platform administrators
    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_SUPPORT = "platform_support"

    # Tenant-level roles
    TENANT_ADMIN = "tenant_admin"
    TENANT_MANAGER = "tenant_manager"

    # Operational roles
    BILLING_MANAGER = "billing_manager"
    NETWORK_ADMIN = "network_admin"
    CUSTOMER_SERVICE = "customer_service"
    FIELD_TECHNICIAN = "field_technician"
    SUPPORT_AGENT = "support_agent"

    # Customer-facing roles
    RESELLER_ADMIN = "reseller_admin"
    RESELLER_AGENT = "reseller_agent"
    CUSTOMER_ADMIN = "customer_admin"
    CUSTOMER_USER = "customer_user"

    # Technical roles
    NETWORK_TECHNICIAN = "network_technician"
    SUPPORT_TECHNICIAN = "support_technician"

    # Read-only roles
    ANALYST = "analyst"
    AUDITOR = "auditor"
    READ_ONLY = "read_only"


@dataclass
class PermissionScope:
    """Defines the scope of a permission."""

    tenant_id: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPermissions:
    """User permission container."""

    user_id: str
    tenant_id: str
    roles: List[Role]
    explicit_permissions: Set[Permission]
    denied_permissions: Set[Permission] = field(default_factory=set)
    scoped_permissions: Dict[str, PermissionScope] = field(default_factory=dict)

    def has_role(self, role: Role) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def has_any_role(self, roles: List[Role]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def is_super_admin(self) -> bool:
        """Check if user is super admin."""
        return Role.SUPER_ADMIN in self.roles

    def is_tenant_admin(self) -> bool:
        """Check if user is tenant admin."""
        return Role.TENANT_ADMIN in self.roles or self.is_super_admin()


class PermissionProvider(ABC):
    """Abstract base class for permission providers."""

    @abstractmethod
    async def get_user_permissions(
        self, user_id: str, tenant_id: str
    ) -> UserPermissions:
        """Get user permissions from data source."""
        pass

    @abstractmethod
    async def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions for a role."""
        pass

    @abstractmethod
    async def check_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        tenant_id: str,
    ) -> bool:
        """Check if user can access specific resource."""
        pass


class PermissionManager:
    """
    Core permission management system.

    Handles role-based access control with:
    - Hierarchical roles and permissions
    - Tenant isolation
    - Resource-based access control
    - Permission inheritance
    - Dynamic permission evaluation
    """

    def __init__(self, permission_provider: Optional[PermissionProvider] = None):
        """
        Initialize permission manager.

        Args:
            permission_provider: Provider for fetching permissions from database
        """
        self.permission_provider = permission_provider
        self._role_permissions_cache: Dict[Role, Set[Permission]] = {}
        self._user_permissions_cache: Dict[str, UserPermissions] = {}

        # Initialize default role permissions
        self._initialize_role_permissions()

        logger.info("Permission Manager initialized")

    def _initialize_role_permissions(self):
        """Initialize default role-to-permission mappings."""
        self._role_permissions_cache = {
            # Super admin has all permissions
            Role.SUPER_ADMIN: set(Permission),
            # Platform administrators
            Role.PLATFORM_ADMIN: {
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_READ,
                Permission.SYSTEM_MONITOR,
                Permission.TENANT_ADMIN,
                Permission.TENANT_CREATE,
                Permission.TENANT_DELETE,
                Permission.TENANT_UPDATE,
                Permission.TENANT_READ,
                Permission.USER_ADMIN,
                Permission.USER_CREATE,
                Permission.USER_DELETE,
                Permission.USER_UPDATE,
                Permission.USER_READ,
                Permission.PLUGIN_ADMIN,
                Permission.PLUGIN_INSTALL,
                Permission.PLUGIN_UNINSTALL,
                Permission.API_ADMIN,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            Role.PLATFORM_SUPPORT: {
                Permission.SYSTEM_READ,
                Permission.SYSTEM_MONITOR,
                Permission.TENANT_READ,
                Permission.USER_READ,
                Permission.SUPPORT_ADMIN,
                Permission.SUPPORT_CREATE,
                Permission.SUPPORT_UPDATE,
                Permission.SUPPORT_READ,
                Permission.SUPPORT_ASSIGN,
                Permission.API_READ,
            },
            # Tenant-level roles
            Role.TENANT_ADMIN: {
                Permission.TENANT_UPDATE,
                Permission.TENANT_READ,
                Permission.USER_ADMIN,
                Permission.USER_CREATE,
                Permission.USER_DELETE,
                Permission.USER_UPDATE,
                Permission.USER_READ,
                Permission.CUSTOMER_ADMIN,
                Permission.CUSTOMER_CREATE,
                Permission.CUSTOMER_DELETE,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_BILLING,
                Permission.BILLING_ADMIN,
                Permission.BILLING_CREATE,
                Permission.BILLING_UPDATE,
                Permission.BILLING_DELETE,
                Permission.BILLING_READ,
                Permission.BILLING_INVOICE,
                Permission.BILLING_PAYMENT,
                Permission.BILLING_REFUND,
                Permission.NETWORK_ADMIN,
                Permission.NETWORK_CONFIG,
                Permission.NETWORK_MONITOR,
                Permission.NETWORK_PROVISION,
                Permission.NETWORK_READ,
                Permission.SERVICE_ADMIN,
                Permission.SERVICE_CREATE,
                Permission.SERVICE_UPDATE,
                Permission.SERVICE_DELETE,
                Permission.SERVICE_READ,
                Permission.SERVICE_PROVISION,
                Permission.ANALYTICS_ADMIN,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.PORTAL_ADMIN,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            Role.TENANT_MANAGER: {
                Permission.TENANT_READ,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_BILLING,
                Permission.BILLING_READ,
                Permission.BILLING_UPDATE,
                Permission.BILLING_INVOICE,
                Permission.SERVICE_READ,
                Permission.SERVICE_UPDATE,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.API_READ,
            },
            # Operational roles
            Role.BILLING_MANAGER: {
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_BILLING,
                Permission.BILLING_ADMIN,
                Permission.BILLING_CREATE,
                Permission.BILLING_UPDATE,
                Permission.BILLING_DELETE,
                Permission.BILLING_READ,
                Permission.BILLING_INVOICE,
                Permission.BILLING_PAYMENT,
                Permission.BILLING_REFUND,
                Permission.SERVICE_READ,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.API_READ,
            },
            Role.NETWORK_ADMIN: {
                Permission.NETWORK_ADMIN,
                Permission.NETWORK_CONFIG,
                Permission.NETWORK_MONITOR,
                Permission.NETWORK_PROVISION,
                Permission.NETWORK_READ,
                Permission.SERVICE_READ,
                Permission.SERVICE_UPDATE,
                Permission.SERVICE_PROVISION,
                Permission.INVENTORY_ADMIN,
                Permission.INVENTORY_CREATE,
                Permission.INVENTORY_UPDATE,
                Permission.INVENTORY_READ,
                Permission.FIELD_READ,
                Permission.FIELD_ASSIGN,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            Role.CUSTOMER_SERVICE: {
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.BILLING_READ,
                Permission.BILLING_UPDATE,
                Permission.SERVICE_READ,
                Permission.SERVICE_UPDATE,
                Permission.SUPPORT_CREATE,
                Permission.SUPPORT_UPDATE,
                Permission.SUPPORT_READ,
                Permission.SUPPORT_ASSIGN,
                Permission.PORTAL_CUSTOMER,
                Permission.API_READ,
            },
            Role.FIELD_TECHNICIAN: {
                Permission.FIELD_READ,
                Permission.FIELD_SCHEDULE,
                Permission.SERVICE_READ,
                Permission.SERVICE_UPDATE,
                Permission.NETWORK_READ,
                Permission.NETWORK_MONITOR,
                Permission.INVENTORY_READ,
                Permission.INVENTORY_UPDATE,
                Permission.CUSTOMER_READ,
                Permission.PORTAL_TECHNICIAN,
                Permission.API_READ,
            },
            Role.SUPPORT_AGENT: {
                Permission.CUSTOMER_READ,
                Permission.SUPPORT_CREATE,
                Permission.SUPPORT_UPDATE,
                Permission.SUPPORT_READ,
                Permission.SERVICE_READ,
                Permission.API_READ,
            },
            # Customer-facing roles
            Role.RESELLER_ADMIN: {
                Permission.CUSTOMER_CREATE,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_READ,
                Permission.BILLING_READ,
                Permission.BILLING_INVOICE,
                Permission.SERVICE_CREATE,
                Permission.SERVICE_READ,
                Permission.SERVICE_UPDATE,
                Permission.ANALYTICS_READ,
                Permission.PORTAL_RESELLER,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            Role.RESELLER_AGENT: {
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.SERVICE_READ,
                Permission.PORTAL_RESELLER,
                Permission.API_READ,
            },
            Role.CUSTOMER_ADMIN: {
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.BILLING_READ,
                Permission.SERVICE_READ,
                Permission.SUPPORT_CREATE,
                Permission.SUPPORT_READ,
                Permission.PORTAL_CUSTOMER,
                Permission.API_READ,
            },
            Role.CUSTOMER_USER: {
                Permission.CUSTOMER_READ,
                Permission.BILLING_READ,
                Permission.SERVICE_READ,
                Permission.SUPPORT_CREATE,
                Permission.SUPPORT_READ,
                Permission.PORTAL_CUSTOMER,
                Permission.API_READ,
            },
            # Read-only roles
            Role.ANALYST: {
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.CUSTOMER_READ,
                Permission.BILLING_READ,
                Permission.SERVICE_READ,
                Permission.NETWORK_READ,
                Permission.API_READ,
            },
            Role.AUDITOR: {
                Permission.SYSTEM_READ,
                Permission.TENANT_READ,
                Permission.USER_READ,
                Permission.CUSTOMER_READ,
                Permission.BILLING_READ,
                Permission.SERVICE_READ,
                Permission.NETWORK_READ,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
                Permission.API_READ,
            },
            Role.READ_ONLY: {
                Permission.API_READ,
            },
        }

    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """
        Get all permissions for a role.

        Args:
            role: Role to get permissions for

        Returns:
            Set of permissions for the role
        """
        return self._role_permissions_cache.get(role, set())

    def get_user_effective_permissions(
        self, user_permissions: UserPermissions
    ) -> Set[Permission]:
        """
        Get user's effective permissions (from roles + explicit permissions).

        Args:
            user_permissions: User permission container

        Returns:
            Set of effective permissions
        """
        effective_permissions = set(user_permissions.explicit_permissions)

        # Add permissions from roles
        for role in user_permissions.roles:
            role_perms = self.get_role_permissions(role)
            effective_permissions.update(role_perms)

        # Remove explicitly denied permissions
        effective_permissions -= user_permissions.denied_permissions

        return effective_permissions

    def check_permission(
        self,
        user_permissions: UserPermissions,
        required_permission: Permission,
        scope: Optional[PermissionScope] = None,
    ) -> bool:
        """
        Check if user has required permission.

        Args:
            user_permissions: User permissions
            required_permission: Permission to check
            scope: Permission scope (tenant, resource, etc.)

        Returns:
            True if user has permission
        """
        # Super admin has all permissions
        if user_permissions.is_super_admin():
            return True

        # Check if permission is explicitly denied
        if required_permission in user_permissions.denied_permissions:
            return False

        # Check effective permissions
        effective_permissions = self.get_user_effective_permissions(user_permissions)

        # Check for exact permission match
        if required_permission in effective_permissions:
            # Additional scope validation if provided
            if scope and scope.tenant_id:
                # Ensure tenant access
                if scope.tenant_id != user_permissions.tenant_id:
                    # Check if user has cross-tenant permissions (platform admin)
                    if not user_permissions.has_any_role(
                        [Role.SUPER_ADMIN, Role.PLATFORM_ADMIN]
                    ):
                        return False

            return True

        # Check for hierarchical permissions (admin implies all sub-permissions)
        return self._check_hierarchical_permission(
            effective_permissions, required_permission
        )

    def _check_hierarchical_permission(
        self, user_permissions: Set[Permission], required_permission: Permission
    ) -> bool:
        """Check if user has hierarchical permission (admin implies sub-permissions)."""
        permission_str = required_permission.value
        resource, action = permission_str.split(":", 1)

        # Check if user has admin permission for the resource
        admin_permission_str = f"{resource}:admin"
        try:
            admin_permission = Permission(admin_permission_str)
            if admin_permission in user_permissions:
                return True
        except ValueError:
            pass

        # Check for system admin (implies all system permissions)
        if (
            permission_str.startswith("system:")
            and Permission.SYSTEM_ADMIN in user_permissions
        ):
            return True

        return False

    def check_multiple_permissions(
        self,
        user_permissions: UserPermissions,
        required_permissions: List[Permission],
        require_all: bool = True,
        scope: Optional[PermissionScope] = None,
    ) -> bool:
        """
        Check multiple permissions.

        Args:
            user_permissions: User permissions
            required_permissions: List of permissions to check
            require_all: If True, user must have ALL permissions. If False, ANY permission.
            scope: Permission scope

        Returns:
            True if permission check passes
        """
        if require_all:
            return all(
                self.check_permission(user_permissions, perm, scope)
                for perm in required_permissions
            )
        else:
            return any(
                self.check_permission(user_permissions, perm, scope)
                for perm in required_permissions
            )

    def can_access_tenant(
        self, user_permissions: UserPermissions, tenant_id: str
    ) -> bool:
        """
        Check if user can access specific tenant.

        Args:
            user_permissions: User permissions
            tenant_id: Tenant ID to check

        Returns:
            True if user can access tenant
        """
        # Super admin and platform admin can access all tenants
        if user_permissions.has_any_role([Role.SUPER_ADMIN, Role.PLATFORM_ADMIN]):
            return True

        # Users can access their own tenant
        if user_permissions.tenant_id == tenant_id:
            return True

        # Check for explicit cross-tenant permissions (future feature)
        # This could be implemented for reseller hierarchies, etc.

        return False

    def get_accessible_tenants(self, user_permissions: UserPermissions) -> List[str]:
        """
        Get list of tenant IDs user can access.

        Args:
            user_permissions: User permissions

        Returns:
            List of accessible tenant IDs
        """
        # Super admin and platform admin can access all tenants
        if user_permissions.has_any_role([Role.SUPER_ADMIN, Role.PLATFORM_ADMIN]):
            return ["*"]  # Wildcard indicating all tenants

        # Regular users can only access their own tenant
        accessible_tenants = [user_permissions.tenant_id]

        # Future: Add logic for hierarchical tenant access (resellers, etc.)

        return accessible_tenants

    def validate_role_assignment(
        self,
        assigner_permissions: UserPermissions,
        target_role: Role,
        target_tenant_id: str,
    ) -> bool:
        """
        Validate if user can assign a role to another user.

        Args:
            assigner_permissions: Permissions of user doing the assignment
            target_role: Role being assigned
            target_tenant_id: Tenant where role is being assigned

        Returns:
            True if role assignment is allowed
        """
        # Super admin can assign any role
        if assigner_permissions.is_super_admin():
            return True

        # Platform admin can assign most roles except super admin
        if assigner_permissions.has_role(Role.PLATFORM_ADMIN):
            if target_role == Role.SUPER_ADMIN:
                return False
            return True

        # Tenant admin can assign tenant-level roles within their tenant
        if assigner_permissions.is_tenant_admin():
            if target_tenant_id != assigner_permissions.tenant_id:
                return False

            # Cannot assign platform or super admin roles
            platform_roles = {
                Role.SUPER_ADMIN,
                Role.PLATFORM_ADMIN,
                Role.PLATFORM_SUPPORT,
            }
            if target_role in platform_roles:
                return False

            return True

        # Regular users cannot assign roles
        return False

    async def get_user_permissions(
        self, user_id: str, tenant_id: str
    ) -> Optional[UserPermissions]:
        """
        Get user permissions from provider with caching.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            UserPermissions object or None if not found
        """
        cache_key = f"{user_id}:{tenant_id}"

        # Check cache first
        if cache_key in self._user_permissions_cache:
            return self._user_permissions_cache[cache_key]

        # Fetch from provider
        if self.permission_provider:
            try:
                permissions = await self.permission_provider.get_user_permissions(
                    user_id, tenant_id
                )
                self._user_permissions_cache[cache_key] = permissions
                return permissions
            except Exception as e:
                logger.error(f"Failed to fetch user permissions: {e}")

        return None

    def clear_user_cache(self, user_id: Optional[str] = None):
        """
        Clear user permissions cache.

        Args:
            user_id: Specific user to clear, or None to clear all
        """
        if user_id:
            # Clear specific user from cache
            keys_to_remove = [
                key
                for key in self._user_permissions_cache.keys()
                if key.startswith(f"{user_id}:")
            ]
            for key in keys_to_remove:
                del self._user_permissions_cache[key]
        else:
            # Clear entire cache
            self._user_permissions_cache.clear()

        logger.info(f"Cleared permission cache for user: {user_id or 'all users'}")

    def get_permission_summary(
        self, user_permissions: UserPermissions
    ) -> Dict[str, Any]:
        """
        Get human-readable permission summary.

        Args:
            user_permissions: User permissions

        Returns:
            Permission summary dictionary
        """
        effective_permissions = self.get_user_effective_permissions(user_permissions)

        # Group permissions by resource
        resources: Dict[str, List[str]] = {}
        for perm in effective_permissions:
            resource, action = perm.value.split(":", 1)
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(action)

        return {
            "user_id": user_permissions.user_id,
            "tenant_id": user_permissions.tenant_id,
            "roles": [role.value for role in user_permissions.roles],
            "is_super_admin": user_permissions.is_super_admin(),
            "is_tenant_admin": user_permissions.is_tenant_admin(),
            "total_permissions": len(effective_permissions),
            "permissions_by_resource": resources,
            "explicit_permissions": len(user_permissions.explicit_permissions),
            "denied_permissions": len(user_permissions.denied_permissions),
        }
