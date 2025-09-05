"""
JWT Module - Compatibility Module

Provides expected JWT functions for tests.
"""

from ..platform.auth.jwt_service import JWTService

_jwt_service = None


def get_jwt_service():
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JWTService()

    return _jwt_service


def create_access_token(*args, **kwargs):
    """Create access token."""
    return get_jwt_service().create_access_token(*args, **kwargs)


def verify_token(*args, **kwargs):
    """Verify token."""
    return get_jwt_service().verify_token(*args, **kwargs)


__all__ = ["create_access_token", "verify_token"]
