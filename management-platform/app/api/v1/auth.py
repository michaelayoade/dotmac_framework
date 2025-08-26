"""
Authentication API endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...services.auth_service import AuthService
from ...core.auth import get_current_user, get_current_active_user
from ...core.security import CurrentUser
from ...schemas.user import (
    UserLogin,
    UserLoginResponse,
    UserCreate,
    UserResponse,
    TokenRefresh,
    UserPasswordUpdate,
    UserInvitationCreate,
    UserInvitationAccept,
    UserInvitationResponse,
    UserProfileUpdate
)
from ...schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=UserLoginResponse)
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return JWT tokens."""
    auth_service = AuthService(db)
    
    # Get client IP and user agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    
    try:
        return await auth_service.login(login_data, client_ip, user_agent)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    
    try:
        return await auth_service.refresh_token(token_data.refresh_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and revoke session."""
    auth_service = AuthService(db)
    
    try:
        result = await auth_service.logout(current_user)
        return SuccessResponse(
            success=True,
            message=result["message"]
        )
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.register_user(user_data)
        
        # Convert user data to include user_id field
        user_data_dict = {
            "id": user.id,  # For BaseResponse
            "user_id": user.id,  # For the test expectation
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
            "phone": user.phone,
            "timezone": user.timezone,
            "language": user.language,
            "two_factor_enabled": user.two_factor_enabled,
            "email_notifications": user.email_notifications,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
        return UserResponse.model_validate(user_data_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile."""
    auth_service = AuthService(db)
    
    try:
        from uuid import UUID
        user = await auth_service.get_current_user_info(UUID(current_user.user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Convert user data to include user_id field
        user_data = {
            "id": user.id,  # For BaseResponse
            "user_id": user.id,  # For the test expectation
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
            "phone": user.phone,
            "timezone": user.timezone,
            "language": user.language,
            "two_factor_enabled": user.two_factor_enabled,
            "email_notifications": user.email_notifications,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
        return UserResponse.model_validate(user_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    from repositories.user import UserRepository
    from uuid import UUID
    
    user_repo = UserRepository(db)
    
    try:
        # Update user profile
        update_data = profile_data.model_dump(exclude_unset=True)
        user = await user_repo.update(UUID(current_user.user_id), update_data, current_user.user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    password_data: UserPasswordUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    auth_service = AuthService(db)
    
    try:
        from uuid import UUID
        success = await auth_service.change_password(
            UUID(current_user.user_id),
            password_data.current_password,
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change failed"
            )
        
        return SuccessResponse(
            success=True,
            message="Password changed successfully. Please login again."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/invite", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: UserInvitationCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create user invitation."""
    # Check permissions - only master admins and tenant admins can invite
    if not (current_user.is_master_admin() or current_user.is_tenant_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create invitations"
        )
    
    auth_service = AuthService(db)
    
    try:
        from uuid import UUID
        invitation_token = await auth_service.create_invitation(
            invitation_data,
            UUID(current_user.user_id)
        )
        
        return SuccessResponse(
            success=True,
            message="Invitation created successfully",
            data={"invitation_token": invitation_token}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invitation creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation creation failed"
        )


@router.post("/accept-invitation", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def accept_invitation(
    accept_data: UserInvitationAccept,
    db: AsyncSession = Depends(get_db)
):
    """Accept user invitation and create account."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.accept_invitation(accept_data)
        return UserResponse.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invitation acceptance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation acceptance failed"
        )