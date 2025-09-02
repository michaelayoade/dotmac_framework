"""
Current user dependency injection for FastAPI applications.
Provides get_current_user and get_current_tenant functions.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .core.jwt_service import JWTService
from .core.portal_auth import PortalType
from .core.sessions import SessionManager

# Initialize security scheme
security = HTTPBearer()
jwt_service = JWTService()
# Note: SessionManager will be initialized when needed


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials

    Returns:
        Dict containing user information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Decode JWT token
        payload = jwt_service.decode_token(credentials.credentials)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # For now, return basic user info from token
        # In production, this would typically fetch from database
        current_user = {
            "id": user_id,
            "email": payload.get("email"),
            "username": payload.get("username"),
            "tenant_id": payload.get("tenant_id"),
            "portal_type": payload.get("portal_type"),
            "permissions": payload.get("permissions", []),
            "is_active": payload.get("is_active", True),
        }

        return current_user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


async def get_current_tenant(
    request: Request, current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current tenant information from authenticated user.

    Args:
        request: FastAPI request object
        current_user: Current user from get_current_user dependency

    Returns:
        Dict containing tenant information

    Raises:
        HTTPException: If tenant not found or not accessible
    """
    try:
        tenant_id = current_user.get("tenant_id")

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not associated with any tenant",
            )

        # For now, return basic tenant info
        # In production, this would fetch from database
        current_tenant = {
            "id": tenant_id,
            "name": f"Tenant-{tenant_id}",
            "domain": request.headers.get("host", "unknown.example.com"),
            "is_active": True,
            "plan": "professional",
        }

        return current_tenant

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant information: {str(e)}",
        )


# Optional helper function for tenant-aware dependencies
async def get_current_user_with_tenant(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Get both current user and tenant in a single dependency.

    Returns:
        Tuple of (user, tenant) dictionaries
    """
    user = await get_current_user(request, credentials)
    tenant = await get_current_tenant(request, user)
    return user, tenant
