"""
Tenant Admin Authentication API endpoints.
Handles authentication for the tenant portal application.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.services.tenant_service import TenantService
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    csrf_token: str
    session_id: str

class LoginResponse(BaseModel):
    success: bool
    user: Dict[str, Any]
    tenant: Dict[str, Any]
    tokens: Dict[str, str]
    requires_mfa: bool = False

class RefreshRequest(BaseModel):
    refresh_token: str

class AuthResponse(BaseModel):
    success: bool
    user: Optional[Dict[str, Any]] = None
    tenant: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Create router
tenant_auth_router = APIRouter()

@tenant_auth_router.post("/login", response_model=LoginResponse)
async def tenant_admin_login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate tenant admin user and establish secure session.
    """
    try:
        # Basic rate limiting check (IP-based)
        client_ip = request.client.host
        
        # Get user by email
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_email(login_data.email)
        
        if not user:
            # Prevent user enumeration - same error for invalid user/password
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            # Log failed attempt
            logger.warning(f"Failed login attempt for {login_data.email} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Get user's tenant
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_id(user.tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant not found"
            )
        
        # Check tenant status
        if tenant.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant account is not active"
            )
        
        # Check if user has tenant admin role
        if "tenant_admin" not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "user_id": str(user.id),
                "tenant_id": str(tenant.id),
                "email": user.email,
                "roles": user.roles,
                "session_id": login_data.session_id
            }
        )
        
        refresh_token = create_refresh_token(
            data={
                "sub": str(user.id),
                "user_id": str(user.id),
                "tenant_id": str(tenant.id),
                "session_id": login_data.session_id
            }
        )
        
        # Set secure HTTP-only cookies
        max_age = 86400 if login_data.remember_me else 3600  # 24h or 1h
        
        response.set_cookie(
            key="tenant_access_token",
            value=access_token,
            max_age=900,  # 15 minutes
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        response.set_cookie(
            key="tenant_refresh_token", 
            value=refresh_token,
            max_age=max_age,
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        response.set_cookie(
            key="tenant_csrf_token",
            value=login_data.csrf_token,
            max_age=max_age,
            httponly=False,  # Accessible to client for CSRF headers
            secure=True,
            samesite="strict"
        )
        
        response.set_cookie(
            key="tenant_session_id",
            value=login_data.session_id,
            max_age=max_age,
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        # Update last login
        await auth_service.update_last_login(user.id)
        
        # Log successful login
        logger.info(f"Successful login for tenant admin {user.email} from {client_ip}")
        
        return LoginResponse(
            success=True,
            user={
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name or "Tenant Admin",
                "role": "tenant_admin",
                "tenant_id": str(tenant.id),
                "permissions": user.roles,
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                "mfa_enabled": getattr(user, 'mfa_enabled', False)
            },
            tenant={
                "id": str(tenant.id),
                "name": tenant.name,
                "display_name": tenant.display_name,
                "slug": tenant.slug,
                "status": tenant.status,
                "tier": tenant.subscription_tier or "standard",
                "custom_domain": tenant.custom_domain,
                "primary_color": tenant.primary_color,
                "logo_url": tenant.logo_url,
                "features": tenant.enabled_features or []
            },
            tokens={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 900  # 15 minutes
            },
            requires_mfa=getattr(user, 'mfa_enabled', False) and not getattr(user, 'mfa_verified', False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {login_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@tenant_auth_router.post("/logout")
async def tenant_admin_logout(
    response: Response,
    csrf_token: str = Cookie(None, alias="tenant_csrf_token")
):
    """
    Logout tenant admin user and clear session.
    """
    try:
        # Clear all authentication cookies
        cookie_names = [
            "tenant_access_token",
            "tenant_refresh_token", 
            "tenant_csrf_token",
            "tenant_session_id"
        ]
        
        for cookie_name in cookie_names:
            response.set_cookie(
                key=cookie_name,
                value="",
                max_age=0,
                expires=datetime.utcnow() - timedelta(days=1),
                httponly=True,
                secure=True,
                samesite="strict"
            )
        
        logger.info("Tenant admin logout successful")
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"success": True, "message": "Logged out successfully"}  # Always succeed for security


@tenant_auth_router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(None, alias="tenant_refresh_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required"
            )
        
        # Verify refresh token and get user data
        auth_service = AuthService(db)
        token_data = await auth_service.verify_refresh_token(refresh_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user and tenant
        user = await auth_service.get_user_by_id(token_data.get("user_id"))
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_id(token_data.get("tenant_id"))
        
        if not user or not tenant or not user.is_active or tenant.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Generate new access token
        new_access_token = create_access_token(
            data={
                "sub": str(user.id),
                "user_id": str(user.id),
                "tenant_id": str(tenant.id),
                "email": user.email,
                "roles": user.roles,
                "session_id": token_data.get("session_id")
            }
        )
        
        # Set new access token cookie
        response.set_cookie(
            key="tenant_access_token",
            value=new_access_token,
            max_age=900,  # 15 minutes
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        return AuthResponse(
            success=True,
            user={
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name or "Tenant Admin",
                "role": "tenant_admin",
                "tenant_id": str(tenant.id),
                "permissions": user.roles,
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None
            },
            tenant={
                "id": str(tenant.id),
                "name": tenant.name,
                "display_name": tenant.display_name,
                "slug": tenant.slug,
                "status": tenant.status,
                "tier": tenant.subscription_tier or "standard"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@tenant_auth_router.get("/validate")
async def validate_session(
    csrf_token: str = Cookie(None, alias="tenant_csrf_token"),
    access_token: str = Cookie(None, alias="tenant_access_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate current session and return user info.
    """
    try:
        if not access_token or not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Verify access token
        auth_service = AuthService(db)
        token_data = await auth_service.verify_access_token(access_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {"valid": True, "user_id": token_data.get("user_id")}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session validation failed"
        )


@tenant_auth_router.get("/me", response_model=AuthResponse)
async def get_current_user(
    access_token: str = Cookie(None, alias="tenant_access_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user and tenant information.
    """
    try:
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Verify token and get user data
        auth_service = AuthService(db)
        token_data = await auth_service.verify_access_token(access_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user and tenant
        user = await auth_service.get_user_by_id(token_data.get("user_id"))
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_id(token_data.get("tenant_id"))
        
        if not user or not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User or tenant not found"
            )
        
        return AuthResponse(
            success=True,
            user={
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name or "Tenant Admin",
                "role": "tenant_admin",
                "tenant_id": str(tenant.id),
                "permissions": user.roles,
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None
            },
            tenant={
                "id": str(tenant.id),
                "name": tenant.name,
                "display_name": tenant.display_name,
                "slug": tenant.slug,
                "status": tenant.status,
                "tier": tenant.subscription_tier or "standard",
                "custom_domain": tenant.custom_domain,
                "primary_color": tenant.primary_color,
                "logo_url": tenant.logo_url,
                "features": tenant.enabled_features or []
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )