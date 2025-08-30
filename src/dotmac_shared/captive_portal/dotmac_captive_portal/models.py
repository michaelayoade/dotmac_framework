"""
Database models for captive portal functionality.

Provides SQLAlchemy models for all captive portal entities including
portals, users, sessions, vouchers, billing plans, and analytics.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

import structlog
from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

logger = structlog.get_logger(__name__)

Base = declarative_base()


class AuthMethodType(Enum):
    """Authentication method types."""

    EMAIL = "email"
    SMS = "sms"
    SOCIAL = "social"
    VOUCHER = "voucher"
    RADIUS = "radius"
    FREE = "free"
    PAYMENT = "payment"


class SessionStatus(Enum):
    """User session status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"


class PortalStatus(Enum):
    """Portal status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"


class BillingStatus(Enum):
    """Billing status."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Portal(Base):
    """Captive portal configuration model."""

    __tablename__ = "captive_portals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic configuration
    name = Column(String(255), nullable=False)
    ssid = Column(String(100), nullable=False)
    location = Column(String(500))
    description = Column(Text)

    # Network settings
    network_range = Column(String(50))  # e.g., "192.168.1.0/24"
    gateway_ip = Column(String(45))
    dns_servers = Column(JSON)  # List of DNS server IPs

    # Portal URLs and endpoints
    portal_url = Column(String(500))
    redirect_url = Column(String(500))
    success_url = Column(String(500))
    terms_url = Column(String(500))

    # Authentication settings
    auth_methods = Column(JSON)  # List of enabled auth methods
    require_terms = Column(Boolean, default=True)
    require_email_verification = Column(Boolean, default=True)

    # Session limits
    session_timeout = Column(Integer, default=3600)  # seconds
    idle_timeout = Column(Integer, default=1800)  # seconds
    max_concurrent_sessions = Column(Integer, default=100)
    data_limit_mb = Column(Integer, default=0)  # 0 = unlimited

    # Bandwidth limits (in kbps)
    bandwidth_limit_down = Column(Integer, default=0)  # 0 = unlimited
    bandwidth_limit_up = Column(Integer, default=0)

    # Billing integration
    billing_enabled = Column(Boolean, default=False)
    default_billing_plan_id = Column(UUID(as_uuid=True), ForeignKey("billing_plans.id"))

    # Customization
    theme_config = Column(JSON)  # Theme and branding configuration
    custom_css = Column(Text)
    custom_html = Column(Text)
    logo_url = Column(String(500))

    # Status and timestamps
    status = Column(SQLEnum(PortalStatus), default=PortalStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sessions = relationship(
        "Session", back_populates="portal", cascade="all, delete-orphan"
    )
    vouchers = relationship(
        "Voucher", back_populates="portal", cascade="all, delete-orphan"
    )
    guest_users = relationship(
        "GuestUser", back_populates="portal", cascade="all, delete-orphan"
    )
    default_billing_plan = relationship("BillingPlan")

    def __repr__(self) -> str:
        return f"<Portal(id={self.id}, name='{self.name}', ssid='{self.ssid}')>"


class GuestUser(Base):
    """Guest user model for captive portal access."""

    __tablename__ = "captive_portal_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portals.id"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # User identification
    email = Column(String(255), index=True)
    phone_number = Column(String(20), index=True)
    username = Column(String(100), index=True)

    # Personal information
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))

    # Authentication
    auth_method = Column(SQLEnum(AuthMethodType), nullable=False)
    password_hash = Column(String(255))  # For username/password auth
    social_provider = Column(String(50))  # google, facebook, etc.
    social_id = Column(String(255))

    # Verification status
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(10))
    verification_expires = Column(DateTime(timezone=True))

    # Account limits and billing
    data_limit_mb = Column(Integer, default=0)  # 0 = inherit from portal
    time_limit_minutes = Column(Integer, default=0)  # 0 = inherit from portal
    billing_plan_id = Column(UUID(as_uuid=True), ForeignKey("billing_plans.id"))

    # Account status
    is_active = Column(Boolean, default=True)
    valid_until = Column(DateTime(timezone=True))
    last_login = Column(DateTime(timezone=True))
    login_count = Column(Integer, default=0)

    # Usage tracking
    total_data_mb = Column(Float, default=0.0)
    total_time_minutes = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portal = relationship("Portal", back_populates="guest_users")
    sessions = relationship(
        "Session", back_populates="guest_user", cascade="all, delete-orphan"
    )
    billing_plan = relationship("BillingPlan")

    def __repr__(self) -> str:
        identifier = self.email or self.phone_number or self.username
        return f"<GuestUser(id={self.id}, identifier='{identifier}')>"


class Session(Base):
    """User session model for tracking captive portal access."""

    __tablename__ = "captive_portal_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portals.id"), nullable=False
    )
    guest_user_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portal_users.id"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Session identification
    session_token = Column(String(255), unique=True, nullable=False)
    client_mac = Column(String(17))  # MAC address format: XX:XX:XX:XX:XX:XX
    client_ip = Column(String(45))  # IPv4 or IPv6
    client_hostname = Column(String(255))

    # Device information
    user_agent = Column(Text)
    device_type = Column(String(50))  # mobile, desktop, tablet
    browser = Column(String(100))
    os = Column(String(100))

    # Session timing
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Usage tracking
    bytes_downloaded = Column(Integer, default=0)
    bytes_uploaded = Column(Integer, default=0)
    packets_received = Column(Integer, default=0)
    packets_sent = Column(Integer, default=0)

    # Location and access point
    access_point_mac = Column(String(17))
    access_point_name = Column(String(255))
    location_coordinates = Column(String(50))  # lat,lng format

    # Session status and termination
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE)
    termination_reason = Column(String(255))

    # Billing tracking
    billing_session_id = Column(String(255))  # External billing system reference
    chargeable_bytes = Column(Integer, default=0)
    charge_amount = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portal = relationship("Portal", back_populates="sessions")
    guest_user = relationship("GuestUser", back_populates="sessions")

    @property
    def duration_minutes(self) -> int | None:
        """Calculate session duration in minutes."""
        end = datetime.now(UTC) if not self.end_time else self.end_time

        if self.start_time:
            delta = end - self.start_time
            return int(delta.total_seconds() / 60)
        return None

    @property
    def total_bytes(self) -> int:
        """Calculate total bytes transferred."""
        return self.bytes_downloaded + self.bytes_uploaded

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, client_ip='{self.client_ip}', status='{self.status.value}')>"


class Voucher(Base):
    """Access voucher model for pre-paid captive portal access."""

    __tablename__ = "captive_portal_vouchers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portals.id"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Voucher identification
    code = Column(String(50), unique=True, nullable=False, index=True)
    batch_id = Column(String(100))  # For bulk voucher generation

    # Access limits
    duration_minutes = Column(Integer, nullable=False)
    data_limit_mb = Column(Integer, default=0)  # 0 = unlimited
    bandwidth_limit_down = Column(Integer, default=0)  # kbps
    bandwidth_limit_up = Column(Integer, default=0)  # kbps

    # Usage restrictions
    max_devices = Column(Integer, default=1)
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True))

    # Redemption tracking
    is_redeemed = Column(Boolean, default=False)
    redeemed_at = Column(DateTime(timezone=True))
    redeemed_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portal_users.id")
    )
    redemption_count = Column(Integer, default=0)

    # Billing information
    price = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    payment_reference = Column(String(255))

    # Generation metadata
    generated_by = Column(String(255))  # admin user or system
    generation_notes = Column(Text)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portal = relationship("Portal", back_populates="vouchers")
    redeemed_by = relationship("GuestUser", foreign_keys=[redeemed_by_user_id])

    @property
    def is_expired(self) -> bool:
        """Check if voucher has expired."""
        if self.valid_until:
            return datetime.now(UTC) > self.valid_until
        return False

    @property
    def is_valid(self) -> bool:
        """Check if voucher is valid for redemption."""
        now = datetime.now(UTC)
        return (
            self.is_active
            and not self.is_expired
            and (not self.valid_from or now >= self.valid_from)
            and (not self.max_devices or self.redemption_count < self.max_devices)
        )

    def __repr__(self) -> str:
        return (
            f"<Voucher(id={self.id}, code='{self.code}', redeemed={self.is_redeemed})>"
        )


class BillingPlan(Base):
    """Billing plan model for captive portal access pricing."""

    __tablename__ = "billing_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Plan identification
    name = Column(String(255), nullable=False)
    description = Column(Text)
    plan_code = Column(String(100), unique=True, nullable=False)

    # Pricing structure
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    billing_type = Column(String(50))  # one_time, recurring, usage_based
    billing_cycle = Column(String(50))  # daily, weekly, monthly

    # Access limits
    duration_minutes = Column(Integer)  # Session duration
    data_limit_mb = Column(Integer, default=0)  # Data allowance
    bandwidth_limit_down = Column(Integer, default=0)  # Download speed limit
    bandwidth_limit_up = Column(Integer, default=0)  # Upload speed limit

    # Validity period
    validity_days = Column(Integer)  # How long the plan remains valid

    # Features
    features = Column(JSON)  # Additional features and restrictions

    # Plan status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<BillingPlan(id={self.id}, name='{self.name}', price={self.price})>"


class AuthMethod(Base):
    """Authentication method configuration model."""

    __tablename__ = "captive_portal_auth_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portals.id"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Method identification
    method_type = Column(SQLEnum(AuthMethodType), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Configuration
    config = Column(JSON)  # Method-specific configuration
    is_enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Ordering and display
    display_order = Column(Integer, default=0)
    display_name = Column(String(255))
    icon_url = Column(String(500))

    # Limitations
    daily_limit = Column(Integer, default=0)  # Max authentications per day
    rate_limit = Column(Integer, default=0)  # Max authentications per hour

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portal = relationship("Portal")

    def __repr__(self) -> str:
        return f"<AuthMethod(id={self.id}, type='{self.method_type.value}', name='{self.name}')>"


class UsageLog(Base):
    """Usage tracking and analytics model."""

    __tablename__ = "captive_portal_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("captive_portal_sessions.id"))
    portal_id = Column(
        UUID(as_uuid=True), ForeignKey("captive_portals.id"), nullable=False
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Usage metrics
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    bytes_downloaded = Column(Integer, default=0)
    bytes_uploaded = Column(Integer, default=0)
    packets_received = Column(Integer, default=0)
    packets_sent = Column(Integer, default=0)

    # Network quality metrics
    signal_strength = Column(Integer)  # dBm
    connection_speed = Column(Float)  # Mbps
    latency_ms = Column(Integer)

    # Location tracking
    access_point_mac = Column(String(17))
    location_coordinates = Column(String(50))

    # Event tracking
    event_type = Column(String(100))  # connect, disconnect, data_limit, time_limit
    event_data = Column(JSON)  # Additional event information

    # Relationships
    session = relationship("Session")
    portal = relationship("Portal")

    def __repr__(self) -> str:
        return f"<UsageLog(id={self.id}, timestamp={self.timestamp}, event='{self.event_type}')>"
