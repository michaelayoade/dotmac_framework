"""
Role-Based Access Control (RBAC) Engine

Production-ready RBAC implementation for DotMac platform services.
Provides comprehensive role and permission management with:
- Hierarchical role inheritance
- Dynamic permission checking
- Resource-based permissions
- Multi-tenant support
- Performance-optimized lookups
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PermissionType(str, Enum):
    """Types of permissions."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    MANAGE = "manage"


class ResourceType(str, Enum):
    """Common resource types."""

    USER = "user"
    TENANT = "tenant"
    SERVICE = "service"
    API_KEY = "api_key"
    ROLE = "role"
    PERMISSION = "permission"
    BILLING = "billing"
    ANALYTICS = "analytics"
    SYSTEM = "system"
    ALL = "*"  # Wildcard for all resources


@dataclass
class Permission:
    """Represents a single permission."""

    action: str  # e.g., "read", "write", "delete"
    resource: str  # e.g., "users", "billing", "*"
    conditions: dict[str, Any] = field(default_factory=dict)  # Optional conditions

    def __post_init__(self):
        """Validate permission format."""
        if not self.action or not self.resource:
            raise ValueError("Permission must have both action and resource")

        # Normalize to lowercase
        self.action = self.action.lower()
        self.resource = self.resource.lower()

    def matches(self, required_action: str, required_resource: str) -> bool:
        """Check if this permission matches the required permission."""
        # Exact match
        if self.action == required_action.lower() and self.resource == required_resource.lower():
            return True

        # Wildcard matches
        if self.action in ("*", "all"):
            if self.resource == required_resource.lower() or self.resource == "*":
                return True

        if self.resource in ("*", "all"):
            if self.action == required_action.lower() or self.action == "*":
                return True

        # Pattern-based matching (regex)
        if self._is_pattern(self.action) and re.match(self.action, required_action) and (
            self.resource == required_resource.lower()
            or self.resource == "*"
            or (self._is_pattern(self.resource) and re.match(self.resource, required_resource))
        ):
            return True

        if self._is_pattern(self.resource) and re.match(self.resource, required_resource):
            if (
                self.action == required_action.lower()
                or self.action == "*"
                or (self._is_pattern(self.action) and re.match(self.action, required_action))
            ):
                return True

        return False

    def _is_pattern(self, value: str) -> bool:
        """Check if value is a regex pattern."""
        return any(char in value for char in r".*+?^${}[]|()\\")

    def __str__(self) -> str:
        """String representation."""
        base = f"{self.action}:{self.resource}"
        if self.conditions:
            conditions_str = ",".join(f"{k}={v}" for k, v in self.conditions.items())
            return f"{base}[{conditions_str}]"
        return base

    def __hash__(self) -> int:
        """Make permission hashable for sets."""
        return hash((self.action, self.resource, frozenset(self.conditions.items())))

    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, Permission):
            return False
        return (
            self.action == other.action
            and self.resource == other.resource
            and self.conditions == other.conditions
        )


@dataclass
class Role:
    """Represents a role with permissions and hierarchy."""

    name: str
    permissions: set[Permission] = field(default_factory=set)
    parent_roles: set[str] = field(default_factory=set)  # Role names this role inherits from
    description: str | None = None
    is_system_role: bool = False  # System roles cannot be modified
    tenant_id: str | None = None  # For multi-tenant roles

    def __post_init__(self):
        """Validate role."""
        if not self.name:
            raise ValueError("Role name cannot be empty")

        # Normalize role name
        self.name = self.name.lower().strip()

        # Ensure permissions is a set
        if isinstance(self.permissions, list | tuple):
            self.permissions = set(self.permissions)

        # Ensure parent_roles is a set
        if isinstance(self.parent_roles, list | tuple):
            self.parent_roles = set(self.parent_roles)

    def add_permission(self, permission: Permission | str) -> None:
        """Add a permission to this role."""
        if isinstance(permission, str):
            # Parse string format like "read:users" or "write:*"
            if ":" in permission:
                action, resource = permission.split(":", 1)
                permission = Permission(action=action, resource=resource)
            else:
                raise ValueError(f"Invalid permission format: {permission}")

        if not isinstance(permission, Permission):
            raise TypeError("Permission must be Permission instance or string")

        self.permissions.add(permission)

    def remove_permission(self, permission: Permission | str) -> bool:
        """Remove a permission from this role."""
        if isinstance(permission, str):
            # Find matching permission by string representation
            for perm in self.permissions:
                if str(perm) == permission:
                    self.permissions.remove(perm)
                    return True
            return False

        if permission in self.permissions:
            self.permissions.remove(permission)
            return True
        return False

    def has_permission(self, action: str, resource: str) -> bool:
        """Check if role has specific permission (not considering inheritance)."""
        return any(permission.matches(action, resource) for permission in self.permissions)

    def add_parent_role(self, role_name: str) -> None:
        """Add a parent role for inheritance."""
        if role_name == self.name:
            raise ValueError("Role cannot inherit from itself")
        self.parent_roles.add(role_name.lower().strip())

    def remove_parent_role(self, role_name: str) -> None:
        """Remove a parent role."""
        self.parent_roles.discard(role_name.lower().strip())

    def __str__(self) -> str:
        """String representation."""
        return f"Role({self.name}, {len(self.permissions)} permissions)"

    def __hash__(self) -> int:
        """Make role hashable."""
        return hash((self.name, self.tenant_id))

    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, Role):
            return False
        return self.name == other.name and self.tenant_id == other.tenant_id


class PermissionCache:
    """Cache for permission lookups to improve performance."""

    def __init__(self, max_size: int = 1000) -> None:
        self.cache: dict[str, bool] = {}
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> bool | None:
        """Get cached result."""
        result = self.cache.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def set(self, key: str, value: bool) -> None:
        """Set cached result."""
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = value

    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
        }


class RBACEngine:
    """
    Production-ready RBAC engine with role inheritance and caching.

    Features:
    - Hierarchical role inheritance
    - Permission caching for performance
    - Multi-tenant support
    - Dynamic permission checking
    - System role protection
    """

    def __init__(self, enable_caching: bool = True, cache_size: int = 1000) -> None:
        """Initialize RBAC engine."""
        self.roles: dict[str, Role] = {}
        self.user_roles: dict[str, set[str]] = {}  # user_id -> role_names
        self.enable_caching = enable_caching
        self.cache = PermissionCache(cache_size) if enable_caching else None

        # Track inheritance graph for cycle detection
        self._inheritance_graph: dict[str, set[str]] = {}

        # Initialize with common system roles
        self._initialize_system_roles()

        logger.info(
            "RBAC engine initialized with caching %s", "enabled" if enable_caching else "disabled"
        )

    def _initialize_system_roles(self) -> None:
        """Initialize common system roles."""
        # Super admin role
        super_admin = Role(
            name="super_admin",
            description="System administrator with all permissions",
            is_system_role=True,
        )
        super_admin.add_permission(Permission("*", "*"))
        self.add_role(super_admin)

        # Admin role
        admin = Role(
            name="admin",
            description="Administrator with management permissions",
            is_system_role=True,
        )
        admin.add_permission(Permission("read", "*"))
        admin.add_permission(Permission("write", "*"))
        admin.add_permission(Permission("delete", "user"))
        admin.add_permission(Permission("manage", "role"))
        self.add_role(admin)

        # User role
        user = Role(
            name="user", description="Basic user with read permissions", is_system_role=True
        )
        user.add_permission(Permission("read", "user"))
        user.add_permission(Permission("write", "user"))
        self.add_role(user)

        # Guest role
        guest = Role(
            name="guest", description="Guest user with minimal permissions", is_system_role=True
        )
        guest.add_permission(Permission("read", "public"))
        self.add_role(guest)

    def add_role(self, role: Role) -> None:
        """Add a role to the system."""
        if not isinstance(role, Role):
            raise TypeError("Expected Role instance")

        # Check for inheritance cycles
        if role.parent_roles:
            self._check_inheritance_cycle(role.name, role.parent_roles)

        self.roles[role.name] = role
        self._update_inheritance_graph(role)

        # Clear cache when roles change
        if self.cache:
            self.cache.clear()

        logger.debug(f"Added role: {role.name}")

    def remove_role(self, role_name: str) -> bool:
        """Remove a role from the system."""
        role_name = role_name.lower().strip()

        if role_name not in self.roles:
            return False

        role = self.roles[role_name]
        if role.is_system_role:
            raise ValueError(f"Cannot remove system role: {role_name}")

        # Remove from all users
        for user_id in list(self.user_roles.keys()):
            self.remove_user_role(user_id, role_name)

        # Remove from inheritance graph
        if role_name in self._inheritance_graph:
            del self._inheritance_graph[role_name]

        # Remove as parent from other roles
        for other_role in self.roles.values():
            other_role.remove_parent_role(role_name)

        del self.roles[role_name]

        # Clear cache
        if self.cache:
            self.cache.clear()

        logger.debug(f"Removed role: {role_name}")
        return True

    def get_role(self, role_name: str) -> Role | None:
        """Get a role by name."""
        return self.roles.get(role_name.lower().strip())

    def list_roles(self, include_system: bool = True) -> list[Role]:
        """List all roles."""
        if include_system:
            return list(self.roles.values())
        return [role for role in self.roles.values() if not role.is_system_role]

    def assign_user_role(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user."""
        role_name = role_name.lower().strip()

        if role_name not in self.roles:
            raise ValueError(f"Role not found: {role_name}")

        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()

        self.user_roles[user_id].add(role_name)

        # Clear cache for this user
        if self.cache:
            # Remove all cached entries for this user
            keys_to_remove = [k for k in self.cache.cache if k.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self.cache.cache[key]

        logger.debug(f"Assigned role {role_name} to user {user_id}")
        return True

    def remove_user_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user."""
        role_name = role_name.lower().strip()

        if user_id not in self.user_roles:
            return False

        if role_name in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role_name)

            # Clean up empty user entries
            if not self.user_roles[user_id]:
                del self.user_roles[user_id]

            # Clear cache for this user
            if self.cache:
                keys_to_remove = [k for k in self.cache.cache if k.startswith(f"{user_id}:")]
                for key in keys_to_remove:
                    del self.cache.cache[key]

            logger.debug(f"Removed role {role_name} from user {user_id}")
            return True

        return False

    def get_user_roles(self, user_id: str, include_inherited: bool = True) -> set[str]:
        """Get all roles for a user."""
        direct_roles = self.user_roles.get(user_id, set())

        if not include_inherited:
            return direct_roles.copy()

        # Include inherited roles
        all_roles = set(direct_roles)
        for role_name in direct_roles:
            all_roles.update(self._get_inherited_roles(role_name))

        return all_roles

    def check_permission(
        self, user_id: str, action: str, resource: str, use_cache: bool = True
    ) -> bool:
        """Check if user has permission for action on resource."""
        # Create cache key
        cache_key = f"{user_id}:{action}:{resource}"

        # Check cache first
        if use_cache and self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Get user roles (including inherited)
        user_roles = self.get_user_roles(user_id, include_inherited=True)

        # Check permissions
        has_permission = False
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and role.has_permission(action, resource):
                has_permission = True
                break

        # Cache result
        if use_cache and self.cache:
            self.cache.set(cache_key, has_permission)

        logger.debug(
            f"Permission check: user={user_id}, action={action}, resource={resource}, result={has_permission}"
        )
        return has_permission

    def get_user_permissions(self, user_id: str) -> set[Permission]:
        """Get all permissions for a user (including inherited)."""
        user_roles = self.get_user_roles(user_id, include_inherited=True)
        permissions = set()

        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role:
                permissions.update(role.permissions)

        return permissions

    def _get_inherited_roles(self, role_name: str, visited: set[str] | None = None) -> set[str]:
        """Get all inherited roles recursively."""
        if visited is None:
            visited = set()

        if role_name in visited:
            return set()  # Cycle detection

        visited.add(role_name)
        inherited = set()

        role = self.roles.get(role_name)
        if role:
            for parent_role in role.parent_roles:
                inherited.add(parent_role)
                inherited.update(self._get_inherited_roles(parent_role, visited.copy()))

        return inherited

    def _update_inheritance_graph(self, role: Role) -> None:
        """Update inheritance graph for cycle detection."""
        self._inheritance_graph[role.name] = role.parent_roles.copy()

    def _check_inheritance_cycle(self, role_name: str, parent_roles: set[str]) -> None:
        """Check for inheritance cycles."""

        def has_cycle(current: str, target: str, visited: set[str]) -> bool:
            if current == target:
                return True
            if current in visited:
                return False

            visited.add(current)
            current_role = self.roles.get(current)
            if current_role:
                for parent in current_role.parent_roles:
                    if has_cycle(parent, target, visited.copy()):
                        return True
            return False

        for parent_role in parent_roles:
            if has_cycle(parent_role, role_name, set()):
                raise ValueError(f"Inheritance cycle detected: {role_name} -> {parent_role}")

    def get_cache_stats(self) -> dict[str, Any] | None:
        """Get cache statistics."""
        return self.cache.get_stats() if self.cache else None

    def clear_cache(self) -> None:
        """Clear permission cache."""
        if self.cache:
            self.cache.clear()

    def export_roles(self) -> dict[str, Any]:
        """Export roles configuration."""
        return {
            "roles": {
                name: {
                    "permissions": [str(p) for p in role.permissions],
                    "parent_roles": list(role.parent_roles),
                    "description": role.description,
                    "is_system_role": role.is_system_role,
                    "tenant_id": role.tenant_id,
                }
                for name, role in self.roles.items()
            },
            "user_roles": {user_id: list(roles) for user_id, roles in self.user_roles.items()},
        }

    def import_roles(self, config: dict[str, Any]) -> None:
        """Import roles configuration."""
        # Clear existing non-system roles
        for role_name in list(self.roles.keys()):
            role = self.roles[role_name]
            if not role.is_system_role:
                self.remove_role(role_name)

        # Clear user roles
        self.user_roles.clear()

        # Import roles
        for role_name, role_data in config.get("roles", {}).items():
            if role_name in self.roles and self.roles[role_name].is_system_role:
                continue  # Skip system roles

            role = Role(
                name=role_name,
                description=role_data.get("description"),
                is_system_role=role_data.get("is_system_role", False),
                tenant_id=role_data.get("tenant_id"),
            )

            # Add permissions
            for perm_str in role_data.get("permissions", []):
                role.add_permission(perm_str)

            # Add parent roles
            for parent_role in role_data.get("parent_roles", []):
                role.add_parent_role(parent_role)

            self.add_role(role)

        # Import user roles
        for user_id, role_names in config.get("user_roles", {}).items():
            for role_name in role_names:
                self.assign_user_role(user_id, role_name)


def create_rbac_engine(config: dict[str, Any] | None = None) -> RBACEngine:
    """Create RBAC engine with optional configuration."""
    config = config or {}

    enable_caching = config.get("enable_caching", True)
    cache_size = config.get("cache_size", 1000)

    engine = RBACEngine(enable_caching=enable_caching, cache_size=cache_size)

    # Import configuration if provided
    if "roles" in config or "user_roles" in config:
        engine.import_roles(config)

    return engine


# Convenience functions
def create_permission(action: str, resource: str, **conditions) -> Permission:
    """Create a permission with optional conditions."""
    return Permission(action=action, resource=resource, conditions=conditions)


def create_role(name: str, permissions: list[str], description: str | None = None) -> Role:
    """Create a role with permissions from strings."""
    role = Role(name=name, description=description)
    for perm_str in permissions:
        role.add_permission(perm_str)
    return role
