"""
User lifecycle schemas for registration, activation, and deactivation workflows.

Provides consistent data models for user lifecycle events across platforms.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

from .user_schemas import UserStatus, UserType


class RegistrationSource(str, Enum):
    """Sources of user registration."""

    WEB_PORTAL = "web_portal"
    MOBILE_APP = "mobile_app"
    API = "api"
    ADMIN_PORTAL = "admin_portal"
    INVITATION = "invitation"
    BULK_IMPORT = "bulk_import"
    ISP_CUSTOMER_PORTAL = "isp_customer_portal"
    MANAGEMENT_PLATFORM = "management_platform"


class VerificationType(str, Enum):
    """Types of user verification."""

    EMAIL = "email"
    PHONE = "phone"
    DOCUMENT = "document"
    MANUAL = "manual"
    AUTO = "auto"


class DeactivationReason(str, Enum):
    """Reasons for user deactivation."""

    USER_REQUEST = "user_request"
    ADMIN_ACTION = "admin_action"
    INACTIVITY = "inactivity"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_BREACH = "security_breach"
    BILLING_ISSUE = "billing_issue"
    SERVICE_TERMINATION = "service_termination"
    ACCOUNT_CLOSURE = "account_closure"


class UserRegistration(BaseModel):
    """Schema for user registration requests."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    user_type: UserType

    # Optional registration fields
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en-US"

    # Platform association
    tenant_id: Optional[UUID] = None

    # Registration metadata
    registration_source: RegistrationSource = RegistrationSource.WEB_PORTAL
    referral_code: Optional[str] = None
    terms_accepted: bool = True
    privacy_policy_accepted: bool = True
    marketing_consent: bool = False

    # Approval workflow
    requires_approval: bool = False
    approval_level: Optional[str] = None  # basic, admin, super_admin

    # Platform-specific registration data
    platform_specific: Dict[str, Any] = Field(default_factory=dict)

    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, hyphens, underscores, and periods"
            )
        return v.lower()

    @validator("password")
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


class UserActivation(BaseModel):
    """Schema for user activation requests."""

    user_id: UUID
    activation_type: str = "email_verification"  # email, phone, manual, auto
    verification_code: Optional[str] = None
    verification_token: Optional[str] = None

    # Activation context
    platform_context: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    activated_by: Optional[UUID] = None  # For manual activation

    # Service activation (for ISP customers)
    activate_services: bool = False
    service_activation_data: Dict[str, Any] = Field(default_factory=dict)


class UserDeactivation(BaseModel):
    """Schema for user deactivation requests."""

    user_id: UUID
    reason: DeactivationReason
    deactivated_by: UUID

    # Deactivation details
    reason_details: Optional[str] = None
    effective_date: Optional[datetime] = None
    reactivation_allowed: bool = True
    data_retention_days: Optional[int] = None

    # Notification settings
    notify_user: bool = True
    notification_message: Optional[str] = None

    # Platform-specific deactivation data
    platform_context: Dict[str, Any] = Field(default_factory=dict)


class UserDeletion(BaseModel):
    """Schema for user deletion requests."""

    user_id: UUID
    deleted_by: UUID
    deletion_type: str = "soft"  # soft, hard, anonymized

    # Deletion justification
    reason: str
    reason_details: Optional[str] = None

    # Data handling
    anonymize_data: bool = True
    preserve_audit_trail: bool = True
    data_export_requested: bool = False

    # Compliance
    gdpr_request: bool = False
    legal_hold: bool = False

    # Platform-specific deletion data
    platform_context: Dict[str, Any] = Field(default_factory=dict)


class UserLifecycleEvent(BaseModel):
    """Schema for user lifecycle event tracking."""

    event_id: UUID
    user_id: UUID
    event_type: str  # registration, activation, deactivation, deletion, update
    event_data: Dict[str, Any]

    # Event metadata
    timestamp: datetime
    source_platform: str
    triggered_by: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Event outcome
    success: bool = True
    error_message: Optional[str] = None

    # Related events
    parent_event_id: Optional[UUID] = None
    correlation_id: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        orm_mode = True


class UserVerificationRequest(BaseModel):
    """Schema for user verification requests."""

    user_id: UUID
    verification_type: VerificationType
    verification_value: str  # email, phone, document ID, etc.

    # Request context
    requested_by: Optional[UUID] = None
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None

    # Platform-specific verification data
    verification_data: Dict[str, Any] = Field(default_factory=dict)


class UserApprovalRequest(BaseModel):
    """Schema for user approval workflow."""

    user_id: UUID
    approval_type: str = "registration"  # registration, role_change, permission_change
    approval_level: str  # basic, admin, super_admin

    # Approval details
    requested_by: UUID
    reason: str
    approval_data: Dict[str, Any] = Field(default_factory=dict)

    # Workflow
    priority: str = "normal"  # low, normal, high, urgent
    due_date: Optional[datetime] = None
    auto_approve_after: Optional[datetime] = None


class UserApprovalResponse(BaseModel):
    """Schema for user approval responses."""

    approval_request_id: UUID
    approved: bool
    approved_by: UUID
    approval_timestamp: datetime

    # Response details
    comments: Optional[str] = None
    conditions: Optional[List[str]] = None

    # Follow-up actions
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None


class BulkUserOperation(BaseModel):
    """Schema for bulk user operations."""

    operation_type: str  # register, activate, deactivate, update, delete
    user_data: List[Dict[str, Any]]

    # Operation context
    initiated_by: UUID
    batch_id: Optional[str] = None

    # Processing options
    stop_on_error: bool = False
    validate_only: bool = False
    send_notifications: bool = True

    # Platform-specific bulk data
    platform_context: Dict[str, Any] = Field(default_factory=dict)


class BulkUserOperationResult(BaseModel):
    """Schema for bulk user operation results."""

    operation_id: UUID
    batch_id: Optional[str] = None
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int

    # Results breakdown
    success_details: List[Dict[str, Any]] = Field(default_factory=list)
    error_details: List[Dict[str, Any]] = Field(default_factory=list)

    # Operation metadata
    started_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    # Status tracking
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    progress_percentage: float = 0.0
