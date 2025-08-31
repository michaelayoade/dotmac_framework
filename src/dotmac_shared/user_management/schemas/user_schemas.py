"""
Unified user schemas for cross-platform user management.

These schemas provide consistent data models across ISP Framework and
Management Platform while allowing for platform-specific extensions.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserType(str, Enum):
    """Universal user types across all platforms."""

    # ISP Framework user types
    CUSTOMER = "customer"
    TECHNICIAN = "technician"
    ISP_ADMIN = "isp_admin"
    ISP_SUPPORT = "isp_support"

    # Management Platform user types
    SUPER_ADMIN = "super_admin"
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    PLATFORM_SUPPORT = "platform_support"

    # Common user types
    API_USER = "api_user"
    READONLY = "readonly"


class UserStatus(str, Enum):
    """User account status."""

    PENDING = "pending"  # Registered but not verified
    ACTIVE = "active"  # Active and verified
    INACTIVE = "inactive"  # Temporarily disabled
    SUSPENDED = "suspended"  # Administratively suspended
    DELETED = "deleted"  # Marked for deletion
    ARCHIVED = "archived"  # Historical record


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    email: bool = True
    sms: bool = False
    push: bool = True
    in_app: bool = True

    # Notification types
    security_alerts: bool = True
    account_updates: bool = True
    system_maintenance: bool = False
    marketing: bool = False

    # Platform-specific notifications
    platform_specific: Dict[str, Any] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    """User preferences and settings."""

    language: str = "en-US"
    timezone: str = "UTC"
    theme: str = "light"  # light, dark, auto
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"  # 12h, 24h

    # Notification preferences
    notifications: NotificationPreferences = Field(
        default_factory=NotificationPreferences
    )

    # Platform-specific preferences
    platform_specific: Dict[str, Any] = Field(default_factory=dict)


class ContactInformation(BaseModel):
    """User contact information."""

    phone: Optional[str] = None
    mobile: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class UserProfile(BaseModel):
    """Extended user profile information."""

    # Personal information
    title: Optional[str] = None  # Mr., Ms., Dr., etc.
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

    # Contact information
    contact: ContactInformation = Field(default_factory=ContactInformation)

    # Professional information
    job_title: Optional[str] = None
    department: Optional[str] = None
    company: Optional[str] = None

    # Profile metadata
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None

    # Preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences)

    # Platform-specific profile data
    platform_specific: Dict[str, Any] = Field(default_factory=dict)


class UserBase(BaseModel):
    """Base user model with common fields."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    user_type: UserType
    is_active: bool = True
    is_verified: bool = False

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens, underscores, and periods"
            )
        return v.lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        """Validate name fields."""
        if not v.replace(" ", "").replace("-", "").replace("'", "").isalpha():
            raise ValueError(
                "Names can only contain letters, spaces, hyphens, and apostrophes"
            )
        return v.strip().title()


class UserCreate(UserBase):
    """Schema for creating new users."""

    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: Optional[str] = None

    # Optional profile information at registration
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en-US"

    # Platform-specific creation data
    tenant_id: Optional[UUID] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    platform_specific: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not (has_upper and has_lower and has_digit and has_symbol):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one symbol"
            )

        return v

    @field_validator("password_confirm")
    @classmethod
    def validate_password_confirm(cls, v, values):
        """Validate password confirmation matches."""
        if v and "password" in values and v != values["password"]:
            raise ValueError("Password confirmation does not match")
        return v


class UserUpdate(BaseModel):
    """Schema for updating existing users."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    # Status updates
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    status: Optional[UserStatus] = None

    # Profile updates
    profile: Optional[UserProfile] = None

    # Platform-specific updates
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    platform_specific: Optional[Dict[str, Any]] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        """Validate name fields."""
        if v and not v.replace(" ", "").replace("-", "").replace("'", "").isalpha():
            raise ValueError(
                "Names can only contain letters, spaces, hyphens, and apostrophes"
            )
        return v.strip().title() if v else v


class UserResponse(UserBase):
    """Schema for user response data."""

    id: UUID
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    # Extended profile
    profile: Optional[UserProfile] = None

    # Security information
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None
    mfa_enabled: bool = False

    # Platform association
    tenant_id: Optional[UUID] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)

    # Platform-specific response data
    platform_specific: Dict[str, Any] = Field(default_factory=dict)

    # Activity information
    login_count: int = 0
    failed_login_count: int = 0
    last_failed_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

    last_login: Optional[datetime] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Get user's display name (full name or username)."""
        return self.full_name if self.first_name and self.last_name else self.username


class UserSearchQuery(BaseModel):
    """Schema for user search queries."""

    query: Optional[str] = None  # Search in username, name, email
    user_type: Optional[UserType] = None
    status: Optional[UserStatus] = None
    tenant_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_login_after: Optional[datetime] = None
    last_login_before: Optional[datetime] = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    # Sorting
    sort_by: str = "created_at"  # username, email, created_at, last_login
    sort_order: str = Field("desc", regex="^(asc|desc)$")


class UserSearchResult(BaseModel):
    """Schema for user search results."""

    users: List[UserSummary]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_next_page(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.total_pages

    @property
    def has_previous_page(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1
