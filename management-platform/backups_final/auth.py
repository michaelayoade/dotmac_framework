"""
Authentication dependencies and utilities.
"""

import logging
from typing import Optional, List, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from repositories.user import UserRepository
from security import security, decode_token, CurrentUser, check_permission

logger = logging.getLogger(__name__)


async def get_current_user():
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """Get current authenticated user."""
    
    # Decode token
    token_data = decode_token(credentials.credentials)
    
    # Validate token type
    if token_data.get("type") != "access":
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID from token
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_repo = UserRepository(db)
    try:
        user = await user_repo.get_by_id(UUID(user_id))
    except ValueError:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get permissions based on role
    from security import get_role_permissions
    permissions = get_role_permissions(user.role)
    
    # Create CurrentUser object
    current_user = CurrentUser()
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        tenant_id=token_data.get("tenant_id"),
        is_active=user.is_active,
        permissions=permissions
    )
    
    return current_user


async def get_current_active_user():
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Get current active user (additional validation)."""
    if not current_user.is_active:
        raise HTTPException()
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    return current_user


def require_permissions(required_permissions: List[str]) -> Callable:
    """Dependency factory for requiring specific permissions."""
    
    def permission_checker()
        current_user: CurrentUser = Depends(get_current_active_user)
    ) -> CurrentUser:
        """Check if user has required permissions."""
        
        # Check each required permission
        for permission in required_permissions:
            if not current_user.has_permission(permission):
                raise HTTPException()
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Operation requires '{permission}' permission"
                )
        
        return current_user
    
    return permission_checker


def require_role(required_roles: List[str]) -> Callable:
    """Dependency factory for requiring specific roles."""
    
    def role_checker()
        current_user: CurrentUser = Depends(get_current_active_user)
    ) -> CurrentUser:
        """Check if user has required role."""
        
        if current_user.role not in required_roles:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of these roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_checker


def require_tenant_access(tenant_id_param: str = "tenant_id") -> Callable:
    """Dependency factory for requiring tenant access."""
    
    def tenant_access_checker()
        tenant_id: UUID,
        current_user: CurrentUser = Depends(get_current_active_user)
    ) -> CurrentUser:
        """Check if user can access the specified tenant."""
        
        if not current_user.can_access_tenant(str(tenant_id):
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        return current_user
    
    return tenant_access_checker


def require_master_admin()
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """Require master admin role."""
    if not current_user.is_master_admin():
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Master admin access required"
        )
    return current_user


def get_current_admin_user()
    current_user: CurrentUser = Depends(get_current_active_user)
) -> dict:
    """Get current user if they have admin privileges."""
    admin_roles = ["super_admin", "platform_admin", "support"]
    
    if current_user.role not in admin_roles:
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges for admin access"
        )
    
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
        "permissions": current_user.permissions
    }


def require_tenant_admin()
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """Require tenant admin role or higher."""
    if not (current_user.is_master_admin() or current_user.is_tenant_admin():
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required"
        )
    return current_user


# Common permission combinations
def require_billing_read():
    """Require billing read permission."""
    return require_permissions(["billing:read"])


def require_billing_write():
    """Require billing write permission."""
    return require_permissions(["billing:write"])


def require_deployment_read():
    """Require deployment read permission."""
    return require_permissions(["deployment:read"])


def require_deployment_write():
    """Require deployment write permission."""
    return require_permissions(["deployment:write"])


def require_plugin_read():
    """Require plugin read permission."""
    return require_permissions(["plugin:read"])


def require_plugin_write():
    """Require plugin write permission."""
    return require_permissions(["plugin:write"])


def require_plugin_install():
    """Require plugin install permission."""
    return require_permissions(["plugin:install"])


def require_plugin_review():
    """Require plugin review permission."""
    return require_permissions(["plugin:review"])


def require_monitoring_read():
    """Require monitoring read permission."""
    return require_permissions(["monitoring:read"])


def require_monitoring_write():
    """Require monitoring write permission."""
    return require_permissions(["monitoring:write"])


# Helper function to get user dict for backward compatibility
def get_current_user_dict()
    current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Get current user as dictionary (for backward compatibility)."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
        "is_active": current_user.is_active,
        "permissions": current_user.permissions
    }


def get_current_tenant_id()
    current_user: CurrentUser = Depends(get_current_user)
) -> Optional[str]:
    """Get current user's tenant ID."""
    return current_user.tenant_id


def verify_tenant_access()
    tenant_id: str,
    current_user: CurrentUser = Depends(get_current_user)
) -> bool:
    """Verify user has access to specified tenant."""
    return current_user.can_access_tenant(tenant_id)