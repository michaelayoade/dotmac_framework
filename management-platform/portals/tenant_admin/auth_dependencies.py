"""
Authentication dependencies for tenant admin API endpoints.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

async def get_current_tenant_user(
    access_token: str = Cookie(None, alias="tenant_access_token"),
    csrf_token: str = Cookie(None, alias="tenant_csrf_token"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current authenticated tenant user from cookies.
    """
    if not access_token or not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Verify access token
        auth_service = AuthService(db)
        token_data = await auth_service.verify_access_token(access_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Ensure user has tenant admin role
        user_roles = token_data.get("roles", [])
        if "tenant_admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return {
            "user_id": token_data.get("user_id"),
            "tenant_id": token_data.get("tenant_id"),
            "email": token_data.get("email"),
            "roles": user_roles,
            "session_id": token_data.get("session_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

async def get_optional_tenant_user(
    access_token: str = Cookie(None, alias="tenant_access_token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Get current tenant user if authenticated, return None if not.
    """
    if not access_token:
        return None
    
    try:
        auth_service = AuthService(db)
        token_data = await auth_service.verify_access_token(access_token)
        
        if not token_data:
            return None
        
        return {
            "user_id": token_data.get("user_id"),
            "tenant_id": token_data.get("tenant_id"),
            "email": token_data.get("email"),
            "roles": token_data.get("roles", []),
            "session_id": token_data.get("session_id")
        }
        
    except Exception as e:
        logger.warning(f"Optional auth check failed: {e}")
        return None