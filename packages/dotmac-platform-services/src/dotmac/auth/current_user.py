"""
Current User - Compatibility Module

Re-exports platform.auth.current_user for backward compatibility.
"""

from ..platform.auth.current_user import (
    ServiceClaims,
    UserClaims,
    get_current_service,
    get_current_tenant,
    get_current_user,
    get_optional_user,
    require_admin,
    require_roles,
    require_scopes,
    require_tenant_access,
)

__all__ = [
    "ServiceClaims",
    "UserClaims",
    "get_current_service",
    "get_current_tenant",
    "get_current_user",
    "get_optional_user",
    "require_admin",
    "require_roles",
    "require_scopes",
    "require_tenant_access"
]
