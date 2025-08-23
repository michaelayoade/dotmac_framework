"""Database models for plugin licensing integration."""

import enum
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, Enum, JSON, ForeignKey, UniqueConstraint, Index, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal
from sqlalchemy import Numeric

from mgmt.shared.database.base import TenantModel, TimestampMixin


class PluginTier(enum.Enum):
    """Plugin pricing tier."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class LicenseStatus(enum.Enum):
    """License status for plugin subscriptions."""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"


class UsageMetricType(enum.Enum):
    """Type of usage metrics for plugin billing."""
    MONTHLY_ACTIVE_USERS = "monthly_active_users"
    API_CALLS = "api_calls"
    STORAGE_GB = "storage_gb"
    TRANSACTIONS = "transactions"
    REPORTS_GENERATED = "reports_generated"
    INTEGRATIONS_ACTIVE = "integrations_active"
    CUSTOM_METRIC = "custom_metric"


class PluginCatalog(TenantModel):
    """Catalog of available plugins for licensing."""
    
    __tablename__ = "plugin_catalog"
    __table_args__ = (
        UniqueConstraint('plugin_id', name='uq_plugin_catalog_id'),
        Index('idx_plugin_catalog_category', 'category'),
        Index('idx_plugin_catalog_tier', 'tier'),
    )
    
    # Plugin identification
    plugin_id = Column(String(255), nullable=False, unique=True, index=True)
    plugin_name = Column(String(255), nullable=False)
    plugin_version = Column(String(50), nullable=False)
    plugin_description = Column(Text, nullable=True)
    plugin_author = Column(String(255), nullable=True)
    
    # Plugin categorization
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    tags = Column(JSONB, nullable=True)  # List of tags for search
    
    # Pricing and tiers
    tier = Column(Enum(PluginTier), nullable=False, default=PluginTier.FREE, index=True)
    is_free = Column(Boolean, default=True, nullable=False)
    
    # Pricing information
    monthly_price = Column(Numeric(10, 2), nullable=True)
    annual_price = Column(Numeric(10, 2), nullable=True)
    setup_fee = Column(Numeric(10, 2), nullable=True)
    
    # Usage-based pricing
    has_usage_billing = Column(Boolean, default=False, nullable=False)
    usage_metrics = Column(JSONB, nullable=True)  # List of billable metrics
    usage_rates = Column(JSONB, nullable=True)    # Pricing per metric
    
    # Feature and limits
    features = Column(JSONB, nullable=True)       # List of features
    usage_limits = Column(JSONB, nullable=True)   # Usage limits per tier
    
    # Availability and compatibility
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    min_framework_version = Column(String(50), nullable=True)
    max_framework_version = Column(String(50), nullable=True)
    
    # Dependencies
    dependencies = Column(JSONB, nullable=True)   # Required plugins
    conflicts = Column(JSONB, nullable=True)      # Conflicting plugins
    
    # Marketing information
    display_name = Column(String(255), nullable=True)
    short_description = Column(String(500), nullable=True)
    long_description = Column(Text, nullable=True)
    screenshots = Column(JSONB, nullable=True)    # URLs to screenshots
    documentation_url = Column(String(500), nullable=True)
    support_url = Column(String(500), nullable=True)
    
    # Publisher information
    publisher_name = Column(String(255), nullable=True)
    publisher_url = Column(String(500), nullable=True)
    publisher_contact = Column(String(255), nullable=True)
    
    # Trial settings
    trial_days = Column(Integer, nullable=True)
    trial_limitations = Column(JSONB, nullable=True)
    
    # Integration settings
    webhook_endpoints = Column(JSONB, nullable=True)
    api_endpoints = Column(JSONB, nullable=True)
    configuration_schema = Column(JSONB, nullable=True)


class PluginSubscription(TenantModel):
    """Plugin subscription model linking tenants to licensed plugins."""
    
    __tablename__ = "plugin_subscriptions"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'plugin_id', name='uq_tenant_plugin_subscription'),
        Index('idx_plugin_subscription_status', 'status'),
        Index('idx_plugin_subscription_expires', 'expires_at'),
    )
    
    # Plugin and tenant reference
    plugin_id = Column(String(255), ForeignKey('plugin_catalog.plugin_id'), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.id'), nullable=True)  # Link to main subscription
    
    # Subscription details
    subscription_name = Column(String(255), nullable=True)
    status = Column(Enum(LicenseStatus), nullable=False, default=LicenseStatus.ACTIVE, index=True)
    tier = Column(Enum(PluginTier), nullable=False, index=True)
    
    # License period
    starts_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    auto_renewal = Column(Boolean, default=True, nullable=False)
    
    # Trial information
    is_trial = Column(Boolean, default=False, nullable=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    trial_converted = Column(Boolean, default=False, nullable=False)
    
    # Pricing and billing
    monthly_price = Column(Numeric(10, 2), nullable=True)
    annual_price = Column(Numeric(10, 2), nullable=True)
    custom_pricing = Column(Boolean, default=False, nullable=False)
    billing_cycle = Column(String(20), default="monthly", nullable=False)
    
    # Usage limits and entitlements
    usage_limits = Column(JSONB, nullable=True)   # Current usage limits
    feature_entitlements = Column(JSONB, nullable=True)  # Enabled features
    
    # Configuration
    plugin_config = Column(JSONB, nullable=True)  # Plugin-specific configuration
    environment_vars = Column(JSONB, nullable=True)  # Environment variables
    
    # Usage tracking
    current_usage = Column(JSONB, nullable=True)  # Current usage stats
    last_usage_update = Column(DateTime(timezone=True), nullable=True)
    usage_reset_date = Column(Date, nullable=True)  # When usage counters reset
    
    # License management
    license_key = Column(String(500), nullable=True)  # Encrypted license key
    activation_count = Column(Integer, default=0, nullable=False)
    max_activations = Column(Integer, default=1, nullable=False)
    
    # Metadata
    activated_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    suspension_reason = Column(Text, nullable=True)
    
    # References
    purchased_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    plugin = relationship("PluginCatalog")
    # subscription would be relationship to main billing subscription if linked
    entitlements = relationship("LicenseEntitlement", back_populates="plugin_subscription", cascade="all, delete-orphan")
    usage_records = relationship("PluginUsageRecord", back_populates="plugin_subscription", cascade="all, delete-orphan")
    
    @property
    def is_active(self) -> bool:
        """Check if plugin subscription is active."""
        if self.status != LicenseStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
            
        return True
    
    @property
    def is_trial_active(self) -> bool:
        """Check if trial is still active."""
        if not self.is_trial:
            return False
            
        if self.trial_ends_at and datetime.utcnow() > self.trial_ends_at:
            return False
            
        return True
    
    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until subscription expires."""
        if not self.expires_at:
            return None
            
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def check_usage_limit(self, metric: str, requested_usage: int = 1) -> bool:
        """Check if usage is within limits."""
        if not self.usage_limits or metric not in self.usage_limits:
            return True  # No limit set
            
        current = self.current_usage.get(metric, 0) if self.current_usage else 0
        limit = self.usage_limits[metric]
        
        if limit == -1:  # Unlimited
            return True
            
        return (current + requested_usage) <= limit
    
    def increment_usage(self, metric: str, amount: int = 1):
        """Increment usage counter for metric."""
        if not self.current_usage:
            self.current_usage = {}
            
        self.current_usage[metric] = self.current_usage.get(metric, 0) + amount
        self.last_usage_update = datetime.utcnow()


class LicenseEntitlement(TenantModel):
    """Individual feature entitlements within a plugin subscription."""
    
    __tablename__ = "license_entitlements"
    __table_args__ = (
        UniqueConstraint('plugin_subscription_id', 'feature_name', name='uq_entitlement_feature'),
        Index('idx_entitlement_feature', 'feature_name'),
        Index('idx_entitlement_active', 'is_enabled'),
    )
    
    # Reference to plugin subscription
    plugin_subscription_id = Column(UUID(as_uuid=True), ForeignKey('plugin_subscriptions.id'), nullable=False, index=True)
    
    # Feature details
    feature_name = Column(String(255), nullable=False, index=True)
    feature_description = Column(Text, nullable=True)
    feature_category = Column(String(100), nullable=True)
    
    # Entitlement status
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)
    is_trial_feature = Column(Boolean, default=False, nullable=False)
    
    # Usage limits for this feature
    usage_limit = Column(Integer, nullable=True)  # -1 for unlimited
    usage_period = Column(String(20), default="monthly", nullable=False)  # monthly, daily, weekly
    current_usage = Column(Integer, default=0, nullable=False)
    
    # Feature-specific configuration
    feature_config = Column(JSONB, nullable=True)
    feature_metadata = Column(JSONB, nullable=True)
    
    # Validity period
    valid_from = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_reset_date = Column(Date, nullable=True)
    
    # Relationships
    plugin_subscription = relationship("PluginSubscription", back_populates="entitlements")
    
    @property
    def is_valid(self) -> bool:
        """Check if entitlement is currently valid."""
        if not self.is_enabled:
            return False
            
        now = datetime.utcnow()
        
        if now < self.valid_from:
            return False
            
        if self.valid_until and now > self.valid_until:
            return False
            
        return True
    
    @property
    def has_usage_remaining(self) -> bool:
        """Check if there's usage remaining for this feature."""
        if self.usage_limit is None or self.usage_limit == -1:
            return True  # Unlimited
            
        return self.current_usage < self.usage_limit
    
    def can_use_feature(self, requested_usage: int = 1) -> bool:
        """Check if feature can be used with requested usage amount."""
        if not self.is_valid:
            return False
            
        if self.usage_limit is None or self.usage_limit == -1:
            return True
            
        return (self.current_usage + requested_usage) <= self.usage_limit


class PluginUsageRecord(TenantModel):
    """Usage tracking records for plugin billing and analytics."""
    
    __tablename__ = "plugin_usage_records"
    __table_args__ = (
        Index('idx_plugin_usage_date', 'usage_date'),
        Index('idx_plugin_usage_metric', 'metric_name'),
        Index('idx_plugin_usage_subscription', 'plugin_subscription_id'),
    )
    
    # Reference to plugin subscription
    plugin_subscription_id = Column(UUID(as_uuid=True), ForeignKey('plugin_subscriptions.id'), nullable=False, index=True)
    plugin_id = Column(String(255), nullable=False, index=True)
    
    # Usage period
    usage_date = Column(Date, nullable=False, index=True)
    usage_hour = Column(Integer, nullable=True)  # Hour of day for hourly tracking
    
    # Metric information
    metric_name = Column(String(255), nullable=False, index=True)
    metric_type = Column(Enum(UsageMetricType), nullable=False)
    
    # Usage data
    usage_count = Column(Integer, default=0, nullable=False)
    usage_value = Column(Numeric(15, 6), nullable=True)  # For non-count metrics
    
    # Billing information
    is_billable = Column(Boolean, default=True, nullable=False)
    unit_price = Column(Numeric(10, 6), nullable=True)
    total_charge = Column(Numeric(10, 2), nullable=True)
    
    # Context and metadata
    usage_context = Column(JSONB, nullable=True)  # Additional context about usage
    raw_data = Column(JSONB, nullable=True)       # Raw usage data for auditing
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    billing_period = Column(String(20), nullable=True)  # Which billing period this applies to
    
    # Relationships
    plugin_subscription = relationship("PluginSubscription", back_populates="usage_records")
    
    def __repr__(self) -> str:
        return f"<PluginUsageRecord(plugin={self.plugin_id}, metric={self.metric_name}, date={self.usage_date})>"


class PluginLicenseHistory(TenantModel):
    """Historical record of plugin license changes."""
    
    __tablename__ = "plugin_license_history"
    __table_args__ = (
        Index('idx_license_history_plugin', 'plugin_subscription_id'),
        Index('idx_license_history_date', 'changed_at'),
        Index('idx_license_history_action', 'action_type'),
    )
    
    # Reference to plugin subscription
    plugin_subscription_id = Column(UUID(as_uuid=True), ForeignKey('plugin_subscriptions.id'), nullable=False, index=True)
    
    # Change details
    action_type = Column(String(50), nullable=False, index=True)  # activated, suspended, renewed, upgraded, etc.
    previous_status = Column(Enum(LicenseStatus), nullable=True)
    new_status = Column(Enum(LicenseStatus), nullable=False)
    
    # Change context
    reason = Column(Text, nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Previous and new values
    previous_config = Column(JSONB, nullable=True)
    new_config = Column(JSONB, nullable=True)
    
    # Impact tracking
    downtime_minutes = Column(Integer, nullable=True)
    users_affected = Column(Integer, nullable=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)
    correlation_id = Column(String(255), nullable=True)  # For tracking related changes
    
    # Relationships
    plugin_subscription = relationship("PluginSubscription")
    
    def __repr__(self) -> str:
        return f"<PluginLicenseHistory(action={self.action_type}, changed_at={self.changed_at})>"