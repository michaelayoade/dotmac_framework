"""RBAC (Role-Based Access Control) contract definitions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class PermissionType(str, Enum):
    """Permission type enumeration."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(str, Enum):
    """Resource type enumeration."""

    USER = "user"
    CUSTOMER = "customer"
    SERVICE = "service"
    BILLING = "billing"
    NETWORK = "network"
    ANALYTICS = "analytics"
    SYSTEM = "system"


class UserRole(str, Enum):
    """User role enumeration."""

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    TECHNICIAN = "technician"
    SUPPORT = "support"
    SALES = "sales"
    CUSTOMER = "customer"


class PermissionScope(str, Enum):
    """Permission scope enumeration."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class Permission:
    """Permission definition."""

    id: str
    name: str
    resource_type: ResourceType
    permission_type: PermissionType
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class Role:
    """Role definition."""

    id: str
    name: str
    description: Optional[str] = None
    permissions: List[Permission] = None
    is_system_role: bool = False
    tenant_id: Optional[str] = None


@dataclass
class RoleAssignment:
    """Role assignment definition."""

    id: str
    user_id: str
    role_id: str
    tenant_id: str
    granted_by: Optional[str] = None
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class AccessRequest:
    """Access request for permission checking."""

    user_id: str
    resource_type: ResourceType
    permission_type: PermissionType
    resource_id: Optional[str] = None
    tenant_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class RoleAssignmentRequest:
    """Role assignment request."""

    user_id: str
    role_id: str
    tenant_id: str
    granted_by: Optional[str] = None
    expires_at: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class RoleAssignmentResponse:
    """Role assignment response."""

    assignment_id: str
    user_id: str
    role_id: str
    tenant_id: str
    granted_by: Optional[str] = None
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    status: str = "active"


@dataclass
class RoleHierarchyResponse:
    """Role hierarchy response."""

    role_id: str
    role_name: str
    parent_roles: List[str] = None
    child_roles: List[str] = None
    level: int = 0


@dataclass
class AccessResponse:
    """Access response for permission checking."""

    granted: bool
    reason: Optional[str] = None


# Alias for compatibility
PermissionCheckRequest = AccessRequest
PermissionCheckResponse = AccessResponse


@dataclass
class BulkPermissionCheckRequest:
    """Bulk permission check request."""

    requests: List[AccessRequest]
    user_id: str
    tenant_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class BulkPermissionCheckResponse:
    """Bulk permission check response."""

    results: List[AccessResponse]
    user_id: str
    tenant_id: Optional[str] = None


@dataclass
class UserRolesResponse:
    """User roles response."""

    user_id: str
    roles: List[str]
    effective_permissions: List[str]
    is_admin: bool = False


__all__ = [
    # Enums
    "PermissionType",
    "ResourceType",
    "UserRole",
    "PermissionScope",
    # Core classes
    "Permission",
    "Role",
    "RoleAssignment",
    "AccessRequest",
    "AccessResponse",
    # Request/Response classes
    "RoleAssignmentRequest",
    "RoleAssignmentResponse",
    "RoleHierarchyResponse",
    "BulkPermissionCheckRequest",
    "BulkPermissionCheckResponse",
    "UserRolesResponse",
    # Aliases
    "PermissionCheckRequest",
    "PermissionCheckResponse",
]
