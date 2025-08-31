"""Portal Management Schemas - Pydantic models for Portal ID system."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import PortalAccountStatus, PortalAccountType


class PortalAccountBase(BaseModel):
    """Base Portal Account schema."""

    account_type: PortalAccountType = PortalAccountType.CUSTOMER
    email_notifications: bool = True
    sms_notifications: bool = False
    theme_preference: str = Field(default="light", pattern="^(light|dark|auto)$")
    language_preference: str = Field(default="en", max_length=10)
    timezone_preference: str = Field(default="UTC", max_length=50)
    session_timeout_minutes: int = Field(
        default=30, ge=5, le=480
    )  # 5 minutes to 8 hours


class PortalAccountCreate(PortalAccountBase):
    """Schema for creating a new Portal Account."""

    password: str = Field(..., min_length=8, max_length=128)
    customer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    portal_id: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return v


class PortalAccountUpdate(BaseModel):
    """Schema for updating Portal Account."""

    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    theme_preference: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    language_preference: Optional[str] = Field(None, max_length=10)
    timezone_preference: Optional[str] = Field(None, max_length=50)
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=480)


class PortalAccountResponse(PortalAccountBase):
    """Schema for Portal Account response."""

    id: UUID
    portal_id: str
    status: PortalAccountStatus
    tenant_id: UUID
    two_factor_enabled: bool
    email_verified: bool
    phone_verified: bool
    must_change_password: bool
    last_successful_login: Optional[datetime]
    password_changed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortalLoginRequest(BaseModel):
    """Schema for portal login request."""

    portal_id: str = Field(..., max_length=20)
    password: str = Field(..., max_length=128)
    two_factor_code: Optional[str] = Field(None, max_length=10)
    remember_me: bool = False
    device_fingerprint: Optional[str] = Field(None, max_length=255)


class PortalLoginResponse(BaseModel):
    """Schema for portal login response."""

    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None  # seconds
    token_type: str = "bearer"
    portal_account: Optional[PortalAccountResponse] = None
    require_password_change: bool = False
    require_two_factor: bool = False
    two_factor_methods: List[str] = []
    message: Optional[str] = None


class PortalPasswordChangeRequest(BaseModel):
    """Schema for portal password change."""

    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return v


class PortalPasswordResetRequest(BaseModel):
    """Schema for portal password reset request."""

    portal_id: str = Field(..., max_length=20)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)


class PortalPasswordResetConfirm(BaseModel):
    """Schema for portal password reset confirmation."""

    reset_token: str = Field(..., max_length=255)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return v


class Portal2FASetupRequest(BaseModel):
    """Schema for 2FA setup request."""

    method: str = Field(..., pattern="^(totp|sms|email)$")
    phone_number: Optional[str] = Field(None, max_length=20)


class Portal2FASetupResponse(BaseModel):
    """Schema for 2FA setup response."""

    secret: Optional[str] = None  # TOTP secret
    qr_code_url: Optional[str] = None  # QR code for TOTP apps
    backup_codes: List[str] = []
    setup_complete: bool = False


class Portal2FAVerifyRequest(BaseModel):
    """Schema for 2FA verification."""

    code: str = Field(..., max_length=10)
    backup_code: Optional[str] = Field(None, max_length=20)


class PortalSessionResponse(BaseModel):
    """Schema for portal session information."""

    id: UUID
    session_token: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    location_country: Optional[str]
    location_city: Optional[str]
    login_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool
    duration_minutes: int

    model_config = ConfigDict(from_attributes=True)


class PortalSecurityEventResponse(BaseModel):
    """Schema for portal security events."""

    id: UUID
    event_type: str
    portal_id: str
    ip_address: str
    user_agent: Optional[str]
    success: bool
    failure_reason: Optional[str]
    risk_score: int
    flagged_as_suspicious: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortalAccountAdminCreate(PortalAccountCreate):
    """Schema for admin creation of Portal Account."""

    status: PortalAccountStatus = PortalAccountStatus.ACTIVE
    must_change_password: bool = True
    email_verified: bool = False
    phone_verified: bool = False


class PortalAccountAdminUpdate(PortalAccountUpdate):
    """Schema for admin updates to Portal Account."""

    status: Optional[PortalAccountStatus] = None
    must_change_password: Optional[bool] = None
    email_verified: Optional[bool] = None
    phone_verified: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None
    failed_login_attempts: Optional[int] = None
    security_notes: Optional[str] = None


class PortalBulkOperationRequest(BaseModel):
    """Schema for bulk operations on Portal Accounts."""

    portal_account_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    operation: str = Field(..., pattern="^(activate|suspend|lock|unlock|reset_2fa)$")
    reason: Optional[str] = Field(None, max_length=255)


class PortalBulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""

    total_requested: int
    successful: int
    failed: int
    errors: List[str] = []
    processed_ids: List[UUID] = []


class PortalAnalyticsResponse(BaseModel):
    """Schema for portal analytics data."""

    total_accounts: int
    active_accounts: int
    suspended_accounts: int
    locked_accounts: int
    pending_accounts: int

    total_sessions_today: int
    active_sessions: int
    failed_logins_today: int

    two_factor_enabled_count: int
    password_expires_soon_count: int  # Within 30 days

    top_locations: List[dict] = []  # Country/city usage stats
    security_alerts_count: int

    model_config = ConfigDict(from_attributes=True)


class PortalPreferencesBase(BaseModel):
    """Base portal preferences schema."""

    theme: str = Field(default="light", pattern="^(light|dark|auto)$")
    language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    marketing_emails: bool = False
    security_alerts: bool = True
    auto_refresh: bool = True
    show_tooltips: bool = True
    compact_view: bool = False
    data_sharing_consent: bool = False
    analytics_tracking: bool = True


class PortalPreferencesCreate(PortalPreferencesBase):
    """Schema for creating portal preferences."""

    account_id: str


class PortalPreferencesUpdate(BaseModel):
    """Schema for updating portal preferences."""

    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    security_alerts: Optional[bool] = None
    auto_refresh: Optional[bool] = None
    show_tooltips: Optional[bool] = None
    compact_view: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None
    analytics_tracking: Optional[bool] = None


class PortalPreferences(PortalPreferencesBase):
    """Portal preferences response schema."""

    id: str
    account_id: str
    tenant_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PortalSession(BaseModel):
    """Portal session response schema."""

    id: str
    account_id: str
    session_token: str
    tenant_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    session_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PortalAccount(PortalAccountBase):
    """Portal account response schema."""

    id: str
    tenant_id: str
    portal_id: str
    account_status: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
