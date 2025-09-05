"""
DotMac Auth - Convenience Import Aliases

This module provides backward-compatible imports for tests and existing code
that expects dotmac.auth instead of dotmac.platform.auth.
"""

from ..platform.auth.current_user import (
    get_current_service,
    get_current_tenant,
    get_current_user,
    get_optional_user,
    require_admin,
    require_roles,
    require_scopes,
    require_tenant_access,
)
from ..platform.auth.exceptions import (
    AuthError,
    InvalidToken,
    TokenError,
    TokenExpired,
    TokenNotFound,
)
from ..platform.auth.jwt_service import JWTService, create_jwt_service_from_config


# Add convenience functions that tests might expect
def create_access_token(*args, **kwargs):
    """Create access token - convenience function for tests."""
    jwt_service = JWTService()
    return jwt_service.create_access_token(*args, **kwargs)


def verify_token(*args, **kwargs):
    """Verify token - convenience function for tests."""
    jwt_service = JWTService()
    return jwt_service.verify_token(*args, **kwargs)


# Re-export everything for compatibility
__all__ = [
    "get_current_user",
    "get_current_tenant",
    "get_current_service",
    "get_optional_user",
    "require_scopes",
    "require_roles",
    "require_admin",
    "require_tenant_access",
    "JWTService",
    "create_jwt_service_from_config",
    "create_access_token",
    "verify_token",
    "AuthError",
    "TokenError",
    "TokenExpired",
    "TokenNotFound",
    "InvalidToken",
]
