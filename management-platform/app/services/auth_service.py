"""
Authentication service for user management and JWT operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import (
    CurrentUser,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from ..models.user import User
from ..repositories.user import (
    UserInvitationRepository,
    UserRepository,
    UserSessionRepository,
)
from ..schemas.user import (
    UserCreate,
    UserInvitationAccept,
    UserInvitationCreate,
    UserLogin,
    UserLoginResponse,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)
        self.invitation_repo = UserInvitationRepository(db)
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.user_repo.get_by_email(email)
        
        if not user:
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="User account is locked due to too many failed attempts"
            )
        
        if not verify_password(password, user.password_hash):
            # Increment failed login attempts
            await self.user_repo.increment_failed_login(user.id)
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 4:
                await self.user_repo.lock_user(user.id, duration_minutes=30)
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account locked due to too many failed attempts"
                )
            
            return None
        
        # Update login timestamp
        await self.user_repo.update_last_login(user.id)
        return user
    
    async def login(
        self, 
        login_data: UserLogin, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserLoginResponse:
        """Login user and create session."""
        user = await self.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create JWT tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        # Create session record
        expires_at = datetime.utcnow() + timedelta(
            days=30 if login_data.remember_me else 7
        )
        
        await self.session_repo.create({
            "user_id": user.id,
            "session_token": access_token[:50],  # Store partial token
            "refresh_token": refresh_token[:50],
            "ip_address": ip_address,
            "user_agent": user_agent,
            "expires_at": expires_at
        })
        
        # Create response
        from ..schemas.user import UserResponse
        
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
        
        user_response = UserResponse.model_validate(user_data)
        
        return UserLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=user_response
        )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh access token using refresh token."""
        try:
            payload = decode_token(refresh_token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            user = await self.user_repo.get_by_id(UUID(user_id))
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Create new access token
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None
            }
            
            new_access_token = create_access_token(token_data)
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def logout(self, current_user: CurrentUser) -> Dict[str, str]:
        """Logout user and revoke session."""
        # Revoke all user sessions
        revoked_count = await self.session_repo.revoke_all_sessions(UUID(current_user.user_id))
        
        logger.info(f"User {current_user.user_id} logged out, {revoked_count} sessions revoked")
        
        return {"message": "Successfully logged out"}
    
    async def register_user(self, user_data: UserCreate) -> User:
        """Register new user."""
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        if user_data.username:
            existing_username = await self.user_repo.get_by_username(user_data.username)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken"
                )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hashed_password
        
        user = await self.user_repo.create(user_dict)
        
        logger.info(f"New user registered: {user.email}")
        return user
    
    async def create_invitation(
        self, 
        invitation_data: UserInvitationCreate,
        invited_by_id: UUID
    ) -> str:
        """Create user invitation."""
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(invitation_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Generate invitation token
        invitation_token = str(uuid4())
        
        # Create invitation
        await self.invitation_repo.create({
            "email": invitation_data.email,
            "role": invitation_data.role,
            "tenant_id": invitation_data.tenant_id,
            "invitation_token": invitation_token,
            "invited_by": invited_by_id,
            "expires_at": datetime.utcnow() + timedelta(days=7),
            "message": invitation_data.message
        })
        
        logger.info(f"User invitation created for {invitation_data.email}")
        return invitation_token
    
    async def accept_invitation(self, accept_data: UserInvitationAccept) -> User:
        """Accept user invitation and create account."""
        # Get invitation
        invitation = await self.invitation_repo.get_by_token(accept_data.invitation_token)
        
        if not invitation or not invitation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )
        
        # Create user
        user_data = UserCreate(
            email=invitation.email,
            full_name=accept_data.full_name,
            password=accept_data.password,
            role=invitation.role,
            tenant_id=invitation.tenant_id,
            is_verified=True
        )
        
        user = await self.register_user(user_data)
        
        # Mark invitation as accepted
        await self.invitation_repo.accept_invitation(invitation.id, user.id)
        
        logger.info(f"User invitation accepted: {user.email}")
        return user
    
    async def change_password(
        self, 
        user_id: UUID, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        hashed_password = get_password_hash(new_password)
        updated = await self.user_repo.update(
            user_id,
            {
                "password_hash": hashed_password,
                "password_changed_at": datetime.utcnow()
            }
        )
        
        if updated:
            # Revoke all existing sessions to force re-login
            await self.session_repo.revoke_all_sessions(user_id)
            logger.info(f"Password changed for user {user.email}")
        
        return updated is not None
    
    async def get_current_user_info(self, user_id: UUID) -> Optional[User]:
        """Get current user information."""
        return await self.user_repo.get_by_id(user_id)
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self.session_repo.cleanup_expired_sessions()
    
    async def cleanup_expired_invitations(self) -> int:
        """Clean up expired invitations."""
        return await self.invitation_repo.cleanup_expired_invitations()