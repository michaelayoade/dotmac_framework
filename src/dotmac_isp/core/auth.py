"""
Centralized authentication utilities for API endpoints.
"""

from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dotmac_isp.core.database import get_async_db

try:
    from dotmac.platform.auth.jwt_service import JWTService
except ImportError:
    # Fallback stub if platform services not available
    class JWTService:
        def __init__(self, *args, **kwargs):
            pass


# Security scheme
security = HTTPBearer()


class CurrentUser:
    """Current authenticated user information."""

    def __init__(
        self,
        id: UUID,
        email: str,
        tenant_id: UUID,
        roles: list[str],
        permissions: list[str],
    ):
        self.id = id
        self.email = email
        self.tenant_id = tenant_id
        self.roles = roles
        self.permissions = permissions


async def authenticate_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_async_db),
) -> CurrentUser:
    """
    Authenticate user from JWT token and return user information.
    This is a dependency that can be used in all protected endpoints.
    """
    try:
        # In a real implementation, this would:
        # 1. Decode and validate JWT token
        # 2. Query user from database
        # 3. Check if user is active
        # 4. Return user information

        # Placeholder implementation
        token = credentials.credentials  # noqa: S105 - variable name only, not a hardcoded secret
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Simulate token validation (replace with actual JWT validation)
        if token == "invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Return mock user (replace with actual user lookup)
        return CurrentUser(
            id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            email="admin@example.com",
            tenant_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
            roles=["admin"],
            permissions=["read", "write", "admin"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}",
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_async_db),
) -> CurrentUser:
    """Alias for authenticate_user for backward compatibility."""
    return await authenticate_user(credentials, db)


def require_permissions(*required_permissions: str):
    """
    Decorator to require specific permissions for an endpoint.
    Usage: @require_permissions("admin", "billing:write")
    """

    def dependency(current_user: CurrentUser = Depends(authenticate_user)):
        for permission in required_permissions:
            if permission not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}",
                )
        return current_user

    return dependency


def require_roles(*required_roles: str):
    """
    Decorator to require specific roles for an endpoint.
    Usage: @require_roles("admin", "manager")
    """

    def dependency(current_user: CurrentUser = Depends(authenticate_user)):
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: one of {required_roles}",
            )
        return current_user

    return dependency


async def get_tenant_context(
    current_user: CurrentUser = Depends(authenticate_user),
) -> dict[str, Any]:
    """Get tenant context for multi-tenant operations."""
    return {
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "permissions": current_user.permissions,
    }
