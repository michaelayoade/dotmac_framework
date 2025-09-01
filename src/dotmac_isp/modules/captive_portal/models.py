"""Captive Portal models integrated with DotMac ISP Framework."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dotmac_isp.shared.database.base import BaseModel


class SessionStatus(Enum):
    """Captive portal session status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"


class AuthMethodType(Enum):
    """Supported authentication methods."""

    EMAIL = "email"
    SMS = "sms"
    SOCIAL = "social"
    VOUCHER = "voucher"
    RADIUS = "radius"
    FREE = "free"
    PAYMENT = "payment"


class PortalStatus(Enum):
    """Portal configuration status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"


class VoucherStatus(Enum):
    """Voucher status."""

    ACTIVE = "active"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CaptivePortalConfig(BaseModel):
    """Captive portal configuration linked to customers/locations."""

    __tablename__ = "captive_portal_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ssid", name="uq_portal_tenant_ssid"),
        Index("ix_portal_tenant_id", "tenant_id"),
        Index("ix_portal_customer_id", "customer_id"),
        {"extend_existing": True},
    )
    # Basic configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ssid: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Link to existing customer system
    customer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Network settings
    network_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gateway_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    dns_servers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Portal URLs
    portal_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    redirect_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    success_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    terms_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Authentication settings
    auth_methods: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    require_terms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_email_verification: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Session limits
    session_timeout: Mapped[int] = mapped_column(
        Integer, default=3600, nullable=False
    )  # seconds
    idle_timeout: Mapped[int] = mapped_column(
        Integer, default=1800, nullable=False
    )  # seconds
    max_concurrent_sessions: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False
    )
    data_limit_mb: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = unlimited

    # Bandwidth limits (in kbps)
    bandwidth_limit_down: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    bandwidth_limit_up: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Billing integration - use existing billing system
    billing_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    default_billing_plan_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("billing_plans.id"), nullable=True
    )
    # Customization
    theme_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    custom_css: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Portal status
    portal_status: Mapped[str] = mapped_column(
        SQLEnum(PortalStatus), default=PortalStatus.ACTIVE, nullable=False
    )
    # Relationships - leverage existing models
    customer = relationship("Customer", back_populates="captive_portals")
    sessions = relationship(
        "CaptivePortalSession", back_populates="portal", cascade="all, delete-orphan"
    )
    auth_methods_config = relationship(
        "AuthMethod", back_populates="portal", cascade="all, delete-orphan"
    )
    vouchers = relationship(
        "Voucher", back_populates="portal", cascade="all, delete-orphan"
    )
    customization = relationship(
        "PortalCustomization",
        back_populates="portal",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CaptivePortalSession(BaseModel):
    """User session for captive portal access - integrates with existing User model."""

    __tablename__ = "captive_portal_sessions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "session_token", name="uq_session_tenant_token"),
        Index("ix_session_tenant_id", "tenant_id"),
        Index("ix_session_portal_id", "portal_id"),
        Index("ix_session_user_id", "user_id"),
        Index("ix_session_customer_id", "customer_id"),
        Index("ix_session_token", "session_token"),
        {"extend_existing": True},
    )
    # Session identification
    session_token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    portal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("captive_portal_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Link to existing user/customer system
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Client information
    client_mac: Mapped[Optional[str]] = mapped_column(String(17), nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    client_hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Device information
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Session timing
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Usage tracking - integrates with analytics module
    bytes_downloaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    packets_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    packets_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Location and access point
    access_point_mac: Mapped[Optional[str]] = mapped_column(String(17), nullable=True)
    access_point_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_coordinates: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )

    # Session status and termination
    session_status: Mapped[str] = mapped_column(
        SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False
    )
    termination_reason: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Authentication method used
    auth_method_used: Mapped[str] = mapped_column(
        SQLEnum(AuthMethodType), nullable=False
    )
    auth_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Billing integration - use existing billing system
    billing_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    chargeable_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    charge_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    portal = relationship("CaptivePortalConfig", back_populates="sessions")
    user = relationship("User")  # Link to existing User model
    customer = relationship("Customer")  # Link to existing Customer model

    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate session duration in minutes."""
        end = self.end_time or datetime.now(timezone.utc)
        if self.start_time:
            delta = end - self.start_time
            return int(delta.total_seconds() / 60)
        return None

    @property
    def total_bytes(self) -> int:
        """Calculate total bytes transferred."""
        return self.bytes_downloaded + self.bytes_uploaded

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return (
            self.session_status == SessionStatus.ACTIVE
            and datetime.now(timezone.utc) < self.expires_at
        )


class AuthMethod(BaseModel):
    """Authentication method configuration for captive portals."""

    __tablename__ = "captive_portal_auth_methods"
    __table_args__ = (
        Index("ix_auth_method_tenant_id", "tenant_id"),
        Index("ix_auth_method_portal_id", "portal_id"),
        {"extend_existing": True},
    )
    portal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("captive_portal_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Method identification
    method_type: Mapped[str] = mapped_column(SQLEnum(AuthMethodType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Ordering and display
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Limitations
    daily_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    portal = relationship("CaptivePortalConfig", back_populates="auth_methods_config")


class Voucher(BaseModel):
    """Access vouchers for pre-paid captive portal access."""

    __tablename__ = "captive_portal_vouchers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_voucher_tenant_code"),
        Index("ix_voucher_tenant_id", "tenant_id"),
        Index("ix_voucher_portal_id", "portal_id"),
        Index("ix_voucher_code", "code"),
        Index("ix_voucher_batch_id", "batch_id"),
        {"extend_existing": True},
    )
    portal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("captive_portal_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Voucher identification
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    batch_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("captive_portal_voucher_batches.id"),
        nullable=True,
    )
    # Access limits
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    data_limit_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bandwidth_limit_down: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    bandwidth_limit_up: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Usage restrictions
    max_devices: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Redemption tracking
    redemption_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_redeemed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_redeemed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    redeemed_by_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    # Billing information - integrate with existing billing
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    billing_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Generation metadata
    generated_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    generation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Voucher status
    voucher_status: Mapped[str] = mapped_column(
        SQLEnum(VoucherStatus), default=VoucherStatus.ACTIVE, nullable=False
    )
    # Relationships
    portal = relationship("CaptivePortalConfig", back_populates="vouchers")
    batch = relationship("VoucherBatch", back_populates="vouchers")
    redeemed_by = relationship("User", foreign_keys=[redeemed_by_user_id])
    generated_by_user = relationship("User", foreign_keys=[generated_by])

    @property
    def is_expired(self) -> bool:
        """Check if voucher has expired."""
        if self.valid_until:
            return datetime.now(timezone.utc) > self.valid_until
        return False

    @property
    def is_valid_for_redemption(self) -> bool:
        """Check if voucher is valid for redemption."""
        now = datetime.now(timezone.utc)
        return (
            self.voucher_status == VoucherStatus.ACTIVE
            and not self.is_expired
            and now >= self.valid_from
            and (not self.max_devices or self.redemption_count < self.max_devices)
        )


class VoucherBatch(BaseModel):
    """Batch management for bulk voucher generation."""

    __tablename__ = "captive_portal_voucher_batches"
    __table_args__ = (
        Index("ix_voucher_batch_tenant_id", "tenant_id"),
        {"extend_existing": True},
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Batch configuration
    voucher_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Template settings for vouchers in this batch
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    data_limit_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Generation metadata
    generated_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    # Relationships
    vouchers = relationship("Voucher", back_populates="batch")
    generated_by_user = relationship("User")

    @property
    def is_complete(self) -> bool:
        """Check if all vouchers in batch have been generated."""
        return self.generated_count >= self.voucher_count


class PortalCustomization(BaseModel):
    """Portal customization and branding settings."""

    __tablename__ = "captive_portal_customizations"
    __table_args__ = (
        Index("ix_customization_tenant_id", "tenant_id"),
        Index("ix_customization_portal_id", "portal_id"),
        {"extend_existing": True},
    )
    portal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("captive_portal_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Branding
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    background_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Theme configuration
    primary_color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True
    )  # hex color
    secondary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    text_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    background_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    # Custom content
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    footer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_css: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Language and localization
    default_language: Mapped[str] = mapped_column(
        String(5), default="en", nullable=False
    )
    supported_languages: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Contact information
    support_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    support_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Legal
    terms_of_service_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    privacy_policy_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Relationships
    portal = relationship("CaptivePortalConfig", back_populates="customization")


class PortalUsageStats(BaseModel):
    """Usage statistics and analytics for captive portals."""

    __tablename__ = "captive_portal_usage_stats"
    __table_args__ = (
        Index("ix_usage_stats_tenant_id", "tenant_id"),
        Index("ix_usage_stats_portal_id", "portal_id"),
        Index("ix_usage_stats_date", "stats_date"),
        {"extend_existing": True},
    )
    portal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("captive_portal_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Time period
    stats_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # hour, day, week, month

    # Session statistics
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_session_duration: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )

    # Data usage
    total_bytes_downloaded: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_bytes_uploaded: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Authentication method breakdown
    auth_method_stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Device type breakdown
    device_type_stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Revenue (if billing enabled)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    portal = relationship("CaptivePortalConfig")
