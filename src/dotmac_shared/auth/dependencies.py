"""
Authentication dependencies for FastAPI applications.
Provides commonly needed dependency functions for authentication and authorization.
"""

from typing import Any, Dict, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .current_user import get_current_user, get_current_tenant, get_current_user_with_tenant
from .core.jwt_service import JWTService
from .core.portal_auth import PortalType
from .core.sessions import SessionManager
from .core.permissions import PermissionManager

# Initialize commonly used services
security = HTTPBearer()
jwt_service = JWTService()
permission_manager = PermissionManager()


async def get_auth_service():
    """Get authentication service instance."""
    return jwt_service


async def get_permission_manager():
    """Get permission manager service instance."""
    return permission_manager


async def get_session_manager():
    """Get session manager instance."""
    return SessionManager()


def require_permission(permission: str):
    """Decorator factory to require specific permission."""
    async def _permission_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_permissions = current_user.get("permissions", [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return _permission_dependency


def require_portal_type(portal_type: PortalType):
    """Decorator factory to require specific portal type."""
    async def _portal_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_portal_type = current_user.get("portal_type")
        if user_portal_type != portal_type.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portal type '{portal_type.value}' required"
            )
        return current_user
    return _portal_dependency


async def require_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Require user to be active."""
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


async def require_tenant_access(
    current_tenant: Dict[str, Any] = Depends(get_current_tenant)
):
    """Require valid tenant access."""
    if not current_tenant.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access is inactive"
        )
    return current_tenant


# Common dependency combinations
async def get_authenticated_user(
    current_user: Dict[str, Any] = Depends(require_active_user)
):
    """Get authenticated and active user."""
    return current_user


async def get_authenticated_user_and_tenant(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    tenant: Dict[str, Any] = Depends(require_tenant_access)
):
    """Get authenticated user with active tenant."""
    return user, tenant


def require_permissions(permissions):
    """
    FastAPI dependency for requiring multiple permissions.
    
    Args:
        permissions: List of required permissions
        
    Returns:
        Dependency function that validates permissions
    """
    def _check_permissions(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        """Validate user has required permissions."""
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
            
        user_permissions = current_user.get("permissions", [])
        
        # Check if user has all required permissions
        for permission in permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission required: {permission}"
                )
        
        return None  # Return None to indicate success
    
    return _check_permissions

# Export all commonly used dependencies
__all__ = [
    'get_current_user',
    'get_current_tenant', 
    'get_current_user_with_tenant',
    'get_auth_service',
    'get_permission_manager',
    'get_session_manager',
    'require_permission',
    'require_permissions',  # Added multi-permission check
    'require_portal_type',
    'require_active_user',
    'require_tenant_access',
    'get_authenticated_user',
    'get_authenticated_user_and_tenant',
    'security',
    'jwt_service',
    'permission_manager'
]