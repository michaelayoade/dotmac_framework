"""
Dependency injection for FastAPI endpoints.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.user import UserRepository
from .security import security, decode_token, CurrentUser

logger = logging.getLogger(__name__)


async def get_current_user(credentials): HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if user is None:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    return CurrentUser(user_id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
    )


async def get_current_active_user(current_user): CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
    return current_user


def require_permission(permission: str):
    """Dependency to require specific permission."""
    def _require_permission()
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission)' required",
            )
        return current_user
    
    return _require_permission


def require_master_admin()
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    """Dependency to require master admin role."""
    if not current_user.is_master_admin():
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Master admin access required",
        )
    return current_user


def require_tenant_admin()
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    """Dependency to require tenant admin role."""
    if not (current_user.is_tenant_admin() or current_user.is_master_admin():
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required",
        )
    return current_user


def require_reseller()
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    """Dependency to require reseller role."""
    if not (current_user.is_reseller() or current_user.is_master_admin():
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reseller access required",
        )
    return current_user


def require_tenant_access(tenant_id: str):
    """Dependency to require access to specific tenant."""
    def _require_tenant_access()
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not current_user.can_access_tenant(tenant_id):
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to tenant '{tenant_id}' denied",
            )
        return current_user
    
    return _require_tenant_access


class CommonQueryParams:
    """Common query parameters for list endpoints."""
    
    def __init__()
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ):
        self.skip = skip
        self.limit = min(limit, 100)  # Maximum 100 items per page
        self.search = search


def common_parameters()
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
) -> CommonQueryParams:
    """Common query parameters dependency."""
    return CommonQueryParams(skip=skip, limit=limit, search=search)