"""
User schemas for authentication and user management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .common import BaseResponse


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    username: Optional[str] = Field(None, min_length=3, max_length=100, description="Username")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: str = Field("UTC", max_length=50, description="User timezone")
    language: str = Field("en", max_length=10, description="Preferred language")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=255, description="Password")
    role: str = Field(..., description="User role")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID for tenant users")


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    email_notifications: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    """Schema for password update."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=255, description="New password")


class UserResponse(BaseResponse):
    """User response schema."""

    user_id: UUID
    email: EmailStr
    full_name: str
    username: Optional[str]
    role: str
    tenant_id: Optional[UUID]
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    phone: Optional[str]
    timezone: str
    language: str
    two_factor_enabled: bool
    email_notifications: bool


class UserLogin(BaseModel):
    """User login schema."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Remember login session")


class UserLoginResponse(BaseModel):
    """Login response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserResponse


class TokenRefresh(BaseModel):
    """Token refresh schema."""

    refresh_token: str = Field(..., description="Refresh token")


class UserInvitationCreate(BaseModel):
    """Schema for creating user invitation."""

    email: EmailStr = Field(..., description="Email to invite")
    role: str = Field(..., description="Role to assign")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID for tenant users")
    message: Optional[str] = Field(None, max_length=1000, description="Personal message")


class UserInvitationResponse(BaseResponse):
    """User invitation response schema."""

    email: EmailStr
    role: str
    tenant_id: Optional[UUID]
    invitation_token: str
    expires_at: datetime
    is_accepted: bool
    invited_by: UUID
    message: Optional[str]


class UserInvitationAccept(BaseModel):
    """Schema for accepting user invitation."""

    invitation_token: str = Field(..., description="Invitation token")
    password: str = Field(..., min_length=8, description="Password for new account")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")


class UserProfileUpdate(BaseModel):
    """Schema for user profile updates."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)


class TwoFactorSetup(BaseModel):
    """Schema for two-factor authentication setup."""

    enabled: bool = Field(..., description="Enable or disable 2FA")
    totp_code: Optional[str] = Field(None, description="TOTP code for verification")


class UserSessionResponse(BaseResponse):
    """User session response schema."""

    user_id: UUID
    ip_address: Optional[str]
    user_agent: Optional[str]
    expires_at: datetime
    last_activity: datetime
    is_active: bool


class UserListResponse(BaseModel):
    """User list response schema."""

    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ForgotPassword(BaseModel):
    """Forgot password schema."""

    email: EmailStr = Field(..., description="Email address")


class ResetPassword(BaseModel):
    """Reset password schema."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangeEmail(BaseModel):
    """Change email schema."""

    new_email: EmailStr = Field(..., description="New email address")
    password: str = Field(..., description="Current password for verification")


class UserPermissions(BaseModel):
    """User permissions schema."""

    permissions: list[str] = Field(..., description="List of user permissions")
    role: str = Field(..., description="User role")


class UserActivity(BaseModel):
    """User activity log schema."""

    timestamp: datetime
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    ip_address: Optional[str]
    details: dict = Field(default_factory=dict)
