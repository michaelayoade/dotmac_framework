"""
User Management Auth Module

This module provides auth functionality for the management platform's user management system.
It acts as a bridge to the dotmac.auth package for management-specific functionality.
"""
try:
    # TODO: Fix star import - from dotmac.platform.auth import *
    from dotmac.platform.auth import (
        AuthenticationMiddleware,
        AuthError,
        EdgeJWTValidator,
        JWTService,
        get_current_user,
        require_scopes,
    )
except ImportError:
    # Provide fallback stubs if dotmac.auth not available
    class AuthError(Exception):
        pass

    class JWTService:
        def __init__(self, *args, **kwargs):
            pass

    def get_current_user(*args, **kwargs):
        raise AuthError("Auth system not available")

    def require_scopes(*scopes):
        def decorator(func):
            return func

        return decorator

    class AuthenticationMiddleware:
        def __init__(self, *args, **kwargs):
            pass

    class EdgeJWTValidator:
        def __init__(self, *args, **kwargs):
            pass


# Export commonly used auth functions for management platform
__all__ = [
    "JWTService",
    "get_current_user",
    "require_scopes",
    "AuthenticationMiddleware",
    "EdgeJWTValidator",
    "AuthError",
]
