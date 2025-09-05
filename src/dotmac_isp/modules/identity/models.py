"""
Identity management models for ISP platform.
SQLAlchemy models for users, customers, and identity-related entities.
"""

import uuid
from enum import Enum

from dotmac_isp.shared.database.base import Base, BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class AccountStatus(str, Enum):
    """Account status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class CustomerType(str, Enum):
    """Customer type enumeration."""

    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class Role(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    CUSTOMER = "customer"
    RESELLER = "reseller"
    TECHNICIAN = "technician"


class User(BaseModel):
    """User model for all platform users."""

    __tablename__ = "identity_users"

    # Basic identity fields
    username = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    email_verified = Column(Boolean, default=False)
    phone = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, default=False)

    # Authentication fields
    password_hash = Column(String(255), nullable=True)  # Nullable for SSO users
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Profile fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Authentication tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # Portal and permissions
    portal_type = Column(
        String(50), nullable=True
    )  # admin, customer, reseller, technician
    permissions = Column(JSONB, nullable=True, default=list)
    preferences = Column(JSONB, nullable=True, default=dict)

    # User metadata
    user_metadata = Column(JSONB, nullable=True, default=dict)

    # Unique constraint per tenant
    __table_args__ = ({"schema": None},)  # Will be set by tenant context


class Customer(BaseModel):
    """Customer model extending user for ISP customers."""

    __tablename__ = "customers"

    # Link to user account
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("identity_users.id"), nullable=True
    )

    # Customer-specific fields
    customer_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(20), default="active")  # active, inactive, suspended

    # Contact information
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    alt_phone = Column(String(20), nullable=True)

    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company_name = Column(String(200), nullable=True)

    # Address information
    billing_address = Column(JSONB, nullable=True)
    service_address = Column(JSONB, nullable=True)

    # Business fields
    credit_score = Column(Integer, nullable=True)
    payment_terms = Column(String(50), default="net30")  # net30, prepaid, etc.
    auto_pay_enabled = Column(Boolean, default=False)

    # Customer lifecycle
    activation_date = Column(DateTime(timezone=True), nullable=True)
    suspension_date = Column(DateTime(timezone=True), nullable=True)
    termination_date = Column(DateTime(timezone=True), nullable=True)

    # Customer service
    preferred_contact_method = Column(String(20), default="email")  # email, phone, sms
    notes = Column(Text, nullable=True)

    # Metadata and custom fields
    custom_fields = Column(JSONB, nullable=True, default=dict)
    tags = Column(JSONB, nullable=True, default=list)

    # Relationships
    user = relationship("User", backref="customer_profile")


class PortalAccess(BaseModel):
    """Portal access permissions and settings."""

    __tablename__ = "portal_access"

    # User reference
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("identity_users.id"), nullable=False
    )

    # Portal configuration
    portal_type = Column(
        String(50), nullable=False
    )  # admin, customer, reseller, technician
    access_level = Column(String(20), default="standard")  # standard, advanced, limited

    # Access control
    is_enabled = Column(Boolean, default=True)
    allowed_features = Column(JSONB, nullable=True, default=list)
    denied_features = Column(JSONB, nullable=True, default=list)

    # Session management
    max_concurrent_sessions = Column(Integer, default=3)
    session_timeout_minutes = Column(Integer, default=480)  # 8 hours

    # Security settings
    require_mfa = Column(Boolean, default=False)
    allowed_ip_ranges = Column(JSONB, nullable=True, default=list)

    # Access tracking
    last_access = Column(DateTime(timezone=True), nullable=True)
    total_logins = Column(Integer, default=0)

    # Relationships
    user = relationship("User", backref="portal_access")


class UserSession(Base):
    """User session tracking (global, not tenant-specific)."""

    __tablename__ = "user_sessions"

    id = Column(String(100), primary_key=True)  # Session ID
    user_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    # Session data
    portal_type = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)

    # Session lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)

    # Session metadata
    session_data = Column(JSONB, nullable=True, default=dict)


class AuthenticationLog(Base):
    """Authentication attempt logging (global)."""

    __tablename__ = "authentication_logs"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Authentication attempt details
    email = Column(String(255), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    tenant_id = Column(String(36), nullable=True, index=True)

    # Attempt details
    attempt_type = Column(String(20), nullable=False)  # login, logout, password_reset
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(200), nullable=True)

    # Request details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    portal_type = Column(String(50), nullable=True)

    # Timing
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Security metadata
    risk_score = Column(Integer, nullable=True)  # 0-100 risk assessment
    geo_location = Column(JSONB, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)


class PasswordResetToken(Base):
    """Password reset token management (global)."""

    __tablename__ = "password_reset_tokens"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Token details
    token = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    # Token lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Security
    ip_address = Column(String(45), nullable=True)
    email_sent_to = Column(String(255), nullable=False)


class AuthToken(Base):
    """Authentication token model (global)."""

    __tablename__ = "auth_tokens"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    token = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    # Token details
    token_type = Column(String(50), nullable=False)  # access, refresh, api_key
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Security
    scopes = Column(JSONB, nullable=True, default=list)
    ip_address = Column(String(45), nullable=True)


class LoginAttempt(Base):
    """Login attempt tracking (global)."""

    __tablename__ = "login_attempts"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Attempt details
    email = Column(String(255), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=False), nullable=True, index=True)
    tenant_id = Column(String(36), nullable=True, index=True)

    # Result
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(200), nullable=True)

    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())


class UserRole(BaseModel):
    """User role assignment (tenant-specific)."""

    __tablename__ = "user_roles"

    # References
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("identity_users.id"), nullable=False
    )
    role = Column(SQLEnum(Role), nullable=False)

    # Assignment details
    assigned_by = Column(UUID(as_uuid=False), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", backref="user_roles")


# Export all models
__all__ = [
    # Enums
    "AccountStatus",
    "CustomerType",
    "Role",
    # Models
    "User",
    "Customer",
    "PortalAccess",
    "UserSession",
    "AuthenticationLog",
    "PasswordResetToken",
    "AuthToken",
    "LoginAttempt",
    "UserRole",
]
