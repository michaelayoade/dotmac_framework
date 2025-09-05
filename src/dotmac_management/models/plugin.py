"""
Plugin licensing and management models.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class PluginStatus(str, Enum):
    """Plugin status enumeration."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISCONTINUED = "discontinued"


class LicenseTier(str, Enum):
    """Plugin license tiers."""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, Enum):
    """Plugin license status."""

    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PluginCategory(BaseModel):
    """Plugin category management."""

    __tablename__ = "plugin_categories"

    # Category details
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Category metadata
    icon = Column(String(255), nullable=True)  # Icon URL or class
    color = Column(String(7), nullable=True)  # Hex color
    sort_order = Column(Integer, default=0, nullable=False)

    # Category status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    plugins = relationship("Plugin", back_populates="category")

    def __repr__(self) -> str:
        return f"<PluginCategory(name='{self.name}')>"


class Plugin(BaseModel):
    """Plugin catalog and management."""

    __tablename__ = "plugins"

    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plugin_categories.id"),
        nullable=False,
        index=True,
    )

    # Plugin identification
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(50), nullable=False)

    # Plugin details
    short_description = Column(String(500), nullable=False)
    full_description = Column(Text, nullable=True)
    features = Column(JSON, default=list, nullable=False)  # List of features

    # Plugin metadata
    author = Column(String(255), nullable=False)
    website_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    support_url = Column(String(500), nullable=True)

    # Technical details
    min_dotmac_version = Column(String(50), nullable=False)
    max_dotmac_version = Column(String(50), nullable=True)
    dependencies = Column(JSON, default=list, nullable=False)  # Required plugins

    # Plugin assets
    icon_url = Column(String(500), nullable=True)
    screenshot_urls = Column(JSON, default=list, nullable=False)
    download_url = Column(String(500), nullable=True)

    # Plugin status
    status = Column(
        SQLEnum(PluginStatus), default=PluginStatus.ACTIVE, nullable=False, index=True
    )
    is_featured = Column(Boolean, default=False, nullable=False, index=True)

    # Plugin metrics
    download_count = Column(Integer, default=0, nullable=False)
    active_installations = Column(Integer, default=0, nullable=False)
    rating_average = Column(Numeric(3, 2), nullable=True)  # 0.00 to 5.00
    rating_count = Column(Integer, default=0, nullable=False)

    # Pricing configuration
    free_tier_available = Column(Boolean, default=True, nullable=False)
    basic_price_cents = Column(Integer, default=0, nullable=False)  # Monthly price
    premium_price_cents = Column(Integer, default=0, nullable=False)
    enterprise_price_cents = Column(Integer, default=0, nullable=False)

    # Usage-based pricing
    usage_based_pricing = Column(Boolean, default=False, nullable=False)
    usage_price_per_unit_cents = Column(Integer, default=0, nullable=False)
    usage_unit = Column(String(50), nullable=True)  # api_calls, users, etc.

    # Trial configuration
    trial_days = Column(Integer, default=14, nullable=False)

    # Plugin configuration
    default_configuration = Column(JSON, default=dict, nullable=False)
    configuration_schema = Column(JSON, default=dict, nullable=False)

    # Relationships
    category = relationship("PluginCategory", back_populates="plugins")
    licenses = relationship("PluginLicense", back_populates="plugin")
    usage_records = relationship("PluginUsage", back_populates="plugin")

    def __repr__(self) -> str:
        return f"<Plugin(name='{self.name}', version='{self.version}')>"

    @property
    def basic_monthly_price(self) -> Decimal:
        """Get basic monthly price in dollars."""
        return Decimal(self.basic_price_cents) / 100

    @property
    def premium_monthly_price(self) -> Decimal:
        """Get premium monthly price in dollars."""
        return Decimal(self.premium_price_cents) / 100

    @property
    def enterprise_monthly_price(self) -> Decimal:
        """Get enterprise monthly price in dollars."""
        return Decimal(self.enterprise_price_cents) / 100

    def get_price_for_tier(self, tier: LicenseTier) -> Decimal:
        """Get price for specific tier."""
        price_mapping = {
            LicenseTier.FREE: Decimal(0),
            LicenseTier.BASIC: self.basic_monthly_price,
            LicenseTier.PREMIUM: self.premium_monthly_price,
            LicenseTier.ENTERPRISE: self.enterprise_monthly_price,
        }
        return price_mapping.get(tier, Decimal(0))


class PluginLicense(BaseModel):
    """Plugin license management for tenants."""

    __tablename__ = "plugin_licenses"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_tenants.id"),
        nullable=False,
        index=True,
    )
    plugin_id = Column(
        UUID(as_uuid=True), ForeignKey("plugins.id"), nullable=False, index=True
    )

    # License details
    license_tier = Column(SQLEnum(LicenseTier), nullable=False, index=True)
    status = Column(
        SQLEnum(LicenseStatus), default=LicenseStatus.TRIAL, nullable=False, index=True
    )

    # License period
    activated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at = Column(DateTime, nullable=True, index=True)
    trial_ends_at = Column(DateTime, nullable=True)

    # Usage limits
    usage_limit = Column(Integer, nullable=True)  # Monthly usage limit
    current_usage = Column(Integer, default=0, nullable=False)

    # License configuration
    configuration = Column(JSON, default=dict, nullable=False)
    feature_flags = Column(JSON, default=dict, nullable=False)

    # Billing integration
    subscription_id = Column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
    )
    last_billing_date = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)

    # License metadata
    license_key = Column(String(255), nullable=True, index=True)
    installation_count = Column(Integer, default=1, nullable=False)
    max_installations = Column(Integer, default=1, nullable=False)

    # Auto-renewal
    auto_renew = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="plugin_licenses")
    plugin = relationship("Plugin", back_populates="licenses")
    usage_records = relationship("PluginUsage", back_populates="license")
    subscription = relationship("Subscription")

    def __repr__(self) -> str:
        return f"<PluginLicense(tenant_id='{self.tenant_id}', plugin_id='{self.plugin_id}', tier='{self.license_tier}')>"

    @property
    def is_active(self) -> bool:
        """Check if license is active."""
        return self.status in [LicenseStatus.TRIAL, LicenseStatus.ACTIVE]

    @property
    def is_trial(self) -> bool:
        """Check if license is in trial."""
        return self.status == LicenseStatus.TRIAL

    @property
    def is_expired(self) -> bool:
        """Check if license is expired."""
        if self.expires_at:
            return datetime.now(timezone.utc) > self.expires_at
        return False

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until expiry."""
        if not self.expires_at:
            return -1
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage."""
        if not self.usage_limit:
            return 0.0
        return min(100.0, (self.current_usage / self.usage_limit) * 100)

    def activate(self, license_key: Optional[str] = None) -> None:
        """Activate license."""
        self.status = LicenseStatus.ACTIVE
        self.activated_at = datetime.now(timezone.utc)
        if license_key:
            self.license_key = license_key

    def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend license."""
        self.status = LicenseStatus.SUSPENDED

    def expire(self) -> None:
        """Mark license as expired."""
        self.status = LicenseStatus.EXPIRED

    def renew(self, expires_at: datetime) -> None:
        """Renew license."""
        self.status = LicenseStatus.ACTIVE
        self.expires_at = expires_at
        self.current_usage = 0  # Reset usage for new period

    def record_usage(self, amount: int = 1) -> bool:
        """Record usage and check limits."""
        self.current_usage += amount

        # Check if usage limit exceeded
        if self.usage_limit and self.current_usage > self.usage_limit:
            return False  # Usage limit exceeded

        return True


class PluginUsage(BaseModel):
    """Plugin usage tracking for billing and analytics."""

    __tablename__ = "plugin_usage"

    license_id = Column(
        UUID(as_uuid=True), ForeignKey("plugin_licenses.id"), nullable=False, index=True
    )
    plugin_id = Column(
        UUID(as_uuid=True), ForeignKey("plugins.id"), nullable=False, index=True
    )

    # Usage details
    usage_date = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    usage_type = Column(
        String(100), nullable=False, index=True
    )  # api_call, feature_use, etc.
    quantity = Column(Integer, default=1, nullable=False)

    # Usage metadata
    feature_name = Column(String(255), nullable=True)
    endpoint = Column(String(255), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Usage context
    request_id = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(String(500), nullable=True)

    # Billing integration
    billable = Column(Boolean, default=True, nullable=False)
    unit_cost_cents = Column(Integer, default=0, nullable=False)
    total_cost_cents = Column(Integer, default=0, nullable=False)
    billed = Column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    license = relationship("PluginLicense", back_populates="usage_records")
    plugin = relationship("Plugin", back_populates="usage_records")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<PluginUsage(plugin_id='{self.plugin_id}', type='{self.usage_type}', quantity={self.quantity})>"

    @property
    def total_cost(self) -> Decimal:
        """Get total cost in dollars."""
        return Decimal(self.total_cost_cents) / 100
