"""Portal Management Models - Portal ID system for customer authentication."""

import enum
from datetime import datetime, timedelta
from typing import Optional

from dotmac_isp.shared.database.base import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class PortalAccountStatus(enum.Enum):
    """Portal account status enumeration."""

    PENDING_ACTIVATION = ("pending_activation",)
    ACTIVE = "active"
    SUSPENDED = ("suspended",)
    LOCKED = "locked"
    EXPIRED = ("expired",)
    DISABLED = "disabled"
    DEACTIVATED = "deactivated"  # Legacy - same as disabled


class PortalAccountType(enum.Enum):
    """Portal account type enumeration."""

    CUSTOMER = ("customer",)
    TECHNICIAN = "technician"
    ADMIN = ("admin",)
    RESELLER = "reseller"


class PortalAccount(BaseModel):
    """
    Portal Account model for customer portal authentication.

    This is the PRIMARY authentication mechanism for ISP customer portals.
    Each customer gets a unique Portal ID that serves as their login credential.
    """

    __tablename__ = ("portal_accounts",)
    __table_args__ = {"extend_existing": True}

    # Portal ID - The unique identifier customers use to log in
    portal_id = Column(String(20), unique=True, nullable=False, index=True)

    # Account information
    account_type = Column(String(20), default=PortalAccountType.CUSTOMER.value, nullable=False)
    status = Column(String(20), default=PortalAccountStatus.PENDING_ACTIVATION.value, nullable=False)
    # Authentication credentials
    password_hash = (Column(String(255), nullable=False),)
    password_reset_token = (Column(String(255), nullable=True),)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Security settings
    two_factor_enabled = (Column(Boolean, default=False, nullable=False),)
    two_factor_secret = (Column(String(32), nullable=True),)
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes

    # Account lockout and security
    failed_login_attempts = (Column(Integer, default=0, nullable=False),)
    locked_until = (Column(DateTime(timezone=True), nullable=True),)
    last_successful_login = (Column(DateTime(timezone=True), nullable=True),)
    last_failed_login = Column(DateTime(timezone=True), nullable=True)

    # Password policy tracking
    password_changed_at = (Column(DateTime(timezone=True), nullable=True),)
    must_change_password = (Column(Boolean, default=True, nullable=False),)
    password_history = Column(Text, nullable=True)  # JSON array of previous password hashes

    # Account preferences
    session_timeout_minutes = (Column(Integer, default=30, nullable=False),)
    auto_logout_enabled = (Column(Boolean, default=True, nullable=False),)
    email_notifications = (Column(Boolean, default=True, nullable=False),)
    sms_notifications = Column(Boolean, default=False, nullable=False)

    # Portal customization
    theme_preference = (Column(String(20), default="light", nullable=False),)
    language_preference = (Column(String(10), default="en", nullable=False),)
    timezone_preference = Column(String(50), default="UTC", nullable=False)

    # Account linking
    customer_id = (Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True),)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Activation and verification
    activation_token = (Column(String(255), nullable=True),)
    activation_expires = (Column(DateTime(timezone=True), nullable=True),)
    email_verified = (Column(Boolean, default=False, nullable=False),)
    phone_verified = Column(Boolean, default=False, nullable=False)

    # Security audit fields
    created_by_admin_id = (Column(UUID(as_uuid=True), nullable=True),)
    last_modified_by_admin_id = (Column(UUID(as_uuid=True), nullable=True),)
    security_notes = Column(Text, nullable=True)

    # Relationships
    customer = (relationship("Customer", foreign_keys=[customer_id]),)
    user = (relationship("User", foreign_keys=[user_id]),)
    sessions = relationship("PortalSession", back_populates="portal_account", cascade="all, delete-orphan")
    login_attempts = relationship(
        "PortalLoginAttempt",
        back_populates="portal_account",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        """Initialize portal account with auto-generated portal ID if not provided."""
        if "portal_id" not in kwargs:
            kwargs["portal_id"] = self._generate_portal_id()
        super().__init__(**kwargs)

    @staticmethod
    def _generate_portal_id() -> str:
        """Generate a unique Portal ID for ISP customers."""
        import secrets
        import string

        # Generate a secure random 12-character portal ID
        chars = string.ascii_uppercase + string.digits
        # Exclude ambiguous characters
        chars = chars.replace("O", "").replace("I", "").replace("0", "").replace("1", "")

        # Generate with ISP prefix
        portal_id = "ISP" + "".join(secrets.choice(chars) for _ in range(9))
        return portal_id

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until:
            from datetime import timezone

            return datetime.now(timezone.utc) < self.locked_until
        return False

    @property
    def is_active(self) -> bool:
        """Check if account is active and can log in."""
        return self.status == PortalAccountStatus.ACTIVE.value and not self.is_locked and not self.is_deleted

    @property
    def password_expired(self) -> bool:
        """Check if password has expired (90 days default)."""
        if not self.password_changed_at:
            return True

        from datetime import timezone

        expiry_days = 90  # Could be configurable per tenant,
        expiry_date = self.password_changed_at + timedelta(days=expiry_days)
        return datetime.now(timezone.utc) > expiry_date

    def lock_account(self, duration_minutes: int = 30, reason: Optional[str] = None):
        """Lock the account for specified duration."""
        from datetime import timezone

        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self.status = PortalAccountStatus.LOCKED.value
        if reason:
            self.security_notes = (
                f"{datetime.now(timezone.utc).isoformat()}: Locked - {reason}\n{self.security_notes or ''}"
            )

    def unlock_account(self, admin_id: Optional[UUID] = None):
        """Unlock the account."""
        from datetime import timezone

        self.locked_until = None
        self.failed_login_attempts = 0
        self.status = PortalAccountStatus.ACTIVE.value
        if admin_id:
            self.last_modified_by_admin_id = admin_id
            self.security_notes = (
                f"{datetime.now(timezone.utc).isoformat()}: Unlocked by admin\n{self.security_notes or ''}"
            )

    def record_failed_login(self):
        """Record a failed login attempt."""
        from datetime import timezone

        self.failed_login_attempts += 1
        self.last_failed_login = datetime.now(timezone.utc)

        # Auto-lock after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(30, "Too many failed login attempts")

    def record_successful_login(self):
        """Record a successful login."""
        from datetime import timezone

        self.failed_login_attempts = 0
        self.last_successful_login = datetime.now(timezone.utc)
        self.locked_until = None


class PortalSession(BaseModel):
    """Portal session model for tracking active customer sessions."""

    __tablename__ = "portal_sessions"

    # Session identification
    session_token = (Column(String(255), unique=True, nullable=False, index=True),)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=False)
    # Session metadata
    ip_address = (Column(String(45), nullable=True),)
    user_agent = (Column(Text, nullable=True),)
    device_fingerprint = (Column(String(255), nullable=True),)
    location_country = (Column(String(2), nullable=True),)
    location_city = Column(String(100), nullable=True)

    # Session timing
    login_at = (Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow),)
    last_activity = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = (Column(DateTime(timezone=True), nullable=False),)
    logout_at = Column(DateTime(timezone=True), nullable=True)

    # Session state
    is_active = (Column(Boolean, default=True, nullable=False),)
    logout_reason = Column(String(50), nullable=True)  # manual, timeout, security, admin

    # Security flags
    suspicious_activity = (Column(Boolean, default=False, nullable=False),)
    security_alerts = Column(Text, nullable=True)  # JSON array of security events

    # Relationships
    portal_account = relationship("PortalAccount", back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        from datetime import timezone

        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired

    @property
    def duration_minutes(self) -> int:
        """Get session duration in minutes."""
        from datetime import timezone

        if self.logout_at:
            end_time = self.logout_at
        else:
            end_time = datetime.now(timezone.utc)

        return int((end_time - self.login_at).total_seconds() / 60)

    def extend_session(self, minutes: int = 30):
        """Extend session expiration time."""
        from datetime import timezone

        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.last_activity = datetime.now(timezone.utc)

    def terminate_session(self, reason: str = "manual"):
        """Terminate the session."""
        from datetime import timezone

        self.is_active = False
        self.logout_at = datetime.now(timezone.utc)
        self.logout_reason = reason


class PortalLoginAttempt(BaseModel):
    """Portal login attempt tracking for security monitoring."""

    __tablename__ = "portal_login_attempts"

    # Attempt identification
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id"), nullable=True)
    portal_id_attempted = Column(String(20), nullable=False, index=True)

    # Attempt details
    success = (Column(Boolean, nullable=False),)
    failure_reason = Column(String(100), nullable=True)

    # Request metadata
    ip_address = (Column(String(45), nullable=False),)
    user_agent = (Column(Text, nullable=True),)
    device_fingerprint = Column(String(255), nullable=True)

    # Geographic information
    country_code = (Column(String(2), nullable=True),)
    city = Column(String(100), nullable=True)

    # Security analysis
    risk_score = Column(Integer, default=0, nullable=False)  # 0-100,
    flagged_as_suspicious = (Column(Boolean, default=False, nullable=False),)
    security_notes = Column(Text, nullable=True)

    # Additional context
    two_factor_used = (Column(Boolean, default=False, nullable=False),)
    session_created_id = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    portal_account = relationship("PortalAccount", back_populates="login_attempts")

    @property
    def is_high_risk(self) -> bool:
        """Check if this is a high-risk login attempt."""
        return self.risk_score >= 75 or self.flagged_as_suspicious

    def calculate_risk_score(self, recent_attempts: list) -> int:
        """Calculate risk score based on various factors."""
        score = 0

        # Failed attempt adds risk
        if not self.success:
            score += 25

        # Multiple attempts from same IP in short time
        same_ip_attempts = [a for a in recent_attempts if a.ip_address == self.ip_address]
        if len(same_ip_attempts) > 3:
            score += 30

        # New geographic location
        if self.portal_account:
            previous_locations = [a.country_code for a in recent_attempts if a.success and a.country_code]
            if previous_locations and self.country_code not in previous_locations:
                score += 20

        # No 2FA when available
        if self.portal_account and self.portal_account.two_factor_enabled and not self.two_factor_used:
            score += 15

        return min(score, 100)  # Cap at 100


class SessionStatus(enum.Enum):
    """Session status enumeration."""

    ACTIVE = ("active",)
    EXPIRED = "expired"
    TERMINATED = "terminated"


class PortalPreferences(BaseModel):
    """Portal user preferences model."""

    __tablename__ = "portal_preferences"

    # Account linking
    account_id = Column(String(50), ForeignKey("portal_accounts.id"), nullable=False, unique=True)
    # Display preferences
    theme = (Column(String(20), default="light", nullable=False),)
    language = (Column(String(10), default="en", nullable=False),)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Notification preferences
    email_notifications = (Column(Boolean, default=True, nullable=False),)
    sms_notifications = (Column(Boolean, default=False, nullable=False),)
    push_notifications = (Column(Boolean, default=True, nullable=False),)
    marketing_emails = (Column(Boolean, default=False, nullable=False),)
    security_alerts = Column(Boolean, default=True, nullable=False)

    # Portal behavior preferences
    auto_refresh = (Column(Boolean, default=True, nullable=False),)
    show_tooltips = (Column(Boolean, default=True, nullable=False),)
    compact_view = (Column(Boolean, default=False, nullable=False),)
    dashboard_widgets = Column(Text, nullable=True)  # JSON config

    # Privacy preferences
    data_sharing_consent = (Column(Boolean, default=False, nullable=False),)
    analytics_tracking = Column(Boolean, default=True, nullable=False)

    # Relationships
    account = relationship("PortalAccount", foreign_keys=[account_id])
