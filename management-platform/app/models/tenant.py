"""
Tenant management models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from .base import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class TenantStatus(str, Enum):
    """Tenant status enumeration."""
    PENDING = "pending"          # Initial registration
    PROVISIONING = "provisioning"  # Infrastructure being created
    ACTIVE = "active"           # Fully operational
    SUSPENDED = "suspended"     # Temporarily disabled
    MAINTENANCE = "maintenance" # Under maintenance
    CANCELLED = "cancelled"     # Permanently disabled
    FAILED = "failed"          # Provisioning failed


class TenantTier(str, Enum):
    """Tenant resource tier."""
    MICRO = "micro"      # Minimal resources
    SMALL = "small"      # Small business
    MEDIUM = "medium"    # Growing business
    LARGE = "large"      # Enterprise
    XLARGE = "xlarge"    # Large enterprise


class Tenant(BaseModel):
    """Core tenant model for ISP customers."""
    
    __tablename__ = "tenants"
    
    # Basic tenant information
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Contact information
    primary_contact_email = Column(String(255), nullable=False, index=True)
    primary_contact_name = Column(String(255), nullable=False)
    business_phone = Column(String(20), nullable=True)
    business_address = Column(Text, nullable=True)
    
    # Tenant status and lifecycle
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.PENDING, nullable=False, index=True)
    tier = Column(SQLEnum(TenantTier), default=TenantTier.SMALL, nullable=False, index=True)
    
    # Important dates
    activated_at = Column(DateTime, nullable=True)
    suspended_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Resource limits based on subscription
    max_customers = Column(Integer, default=1000, nullable=False)
    max_services = Column(Integer, default=10000, nullable=False)
    max_storage_gb = Column(Integer, default=100, nullable=False)
    max_bandwidth_mbps = Column(Integer, default=1000, nullable=False)
    
    # Technical configuration
    custom_domain = Column(String(255), nullable=True, index=True)
    ssl_enabled = Column(Boolean, default=True, nullable=False)
    backup_retention_days = Column(Integer, default=30, nullable=False)
    
    # Branding and customization
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    custom_css = Column(Text, nullable=True)
    
    # Billing information
    billing_email = Column(String(255), nullable=True)
    billing_cycle = Column(String(20), default="monthly", nullable=False)  # monthly, annual
    
    # Integration settings
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    api_key = Column(String(255), nullable=True, index=True)
    
    # Compliance and security
    gdpr_compliant = Column(Boolean, default=True, nullable=False)
    data_region = Column(String(50), default="US", nullable=False)
    encryption_enabled = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    configurations = relationship("TenantConfiguration", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant")
    deployments = relationship("Deployment", back_populates="tenant")
    plugin_licenses = relationship("PluginLicense", back_populates="tenant")
    health_checks = relationship("HealthCheck", back_populates="tenant")
    
    def __repr__(self) -> str:
        return f"<Tenant(name='{self.name}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE
    
    @property
    def can_deploy(self) -> bool:
        """Check if tenant can deploy new instances."""
        return self.status in [TenantStatus.ACTIVE, TenantStatus.MAINTENANCE]
    
    @property
    def subscription_active(self) -> bool:
        """Check if tenant has active subscription."""
        return any(sub.is_active for sub in self.subscriptions)
    
    def activate(self, user_id: str = None) -> None:
        """Activate tenant."""
        self.status = TenantStatus.ACTIVE
        self.activated_at = datetime.utcnow()
        self.suspended_at = None
        if user_id:
            self.updated_by = user_id
    
    def suspend(self, user_id: str = None) -> None:
        """Suspend tenant."""
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = datetime.utcnow()
        if user_id:
            self.updated_by = user_id
    
    def cancel(self, user_id: str = None) -> None:
        """Cancel tenant."""
        self.status = TenantStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        if user_id:
            self.updated_by = user_id
    
    def get_resource_limits(self) -> Dict[str, Any]:
        """Get resource limits for this tenant."""
        return {
            "max_customers": self.max_customers,
            "max_services": self.max_services,
            "max_storage_gb": self.max_storage_gb,
            "max_bandwidth_mbps": self.max_bandwidth_mbps,
        }


class TenantConfiguration(BaseModel):
    """Tenant-specific configuration settings."""
    
    __tablename__ = "tenant_configurations"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Configuration details
    category = Column(String(100), nullable=False, index=True)  # branding, features, integrations
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=True)
    
    # Configuration metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    environment = Column(String(20), default="production", nullable=False)  # production, staging
    
    # Relationships
    tenant = relationship("Tenant", back_populates="configurations")
    
    def __repr__(self) -> str:
        return f"<TenantConfiguration(tenant_id='{self.tenant_id}', key='{self.key}')>"


class TenantInvitation(BaseModel):
    """Tenant user invitation management."""
    
    __tablename__ = "tenant_invitations"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # tenant_admin, tenant_user
    invitation_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Invitation metadata
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    message = Column(Text, nullable=True)
    
    # Status tracking
    is_accepted = Column(Boolean, default=False, nullable=False, index=True)
    accepted_at = Column(DateTime, nullable=True)
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    invited_by_user = relationship("User", foreign_keys=[invited_by])
    accepted_by_user = relationship("User", foreign_keys=[accepted_by])
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if invitation is valid."""
        return not self.is_accepted and not self.is_expired and self.is_active
    
    def accept(self, user_id: str) -> None:
        """Mark invitation as accepted."""
        self.is_accepted = True
        self.accepted_at = datetime.utcnow()
        self.accepted_by = user_id


class TenantUsageMetrics(BaseModel):
    """Tenant usage metrics for billing and analytics."""
    
    __tablename__ = "tenant_usage_metrics"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Time period
    metric_date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), default="daily", nullable=False)  # hourly, daily, monthly
    
    # Usage metrics
    active_customers = Column(Integer, default=0, nullable=False)
    active_services = Column(Integer, default=0, nullable=False)
    storage_used_gb = Column(Integer, default=0, nullable=False)
    bandwidth_used_gb = Column(Integer, default=0, nullable=False)
    api_requests = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    avg_response_time_ms = Column(Integer, nullable=True)
    uptime_percentage = Column(Integer, default=10000, nullable=False)  # Basis points (100.00%)
    error_rate = Column(Integer, default=0, nullable=False)  # Basis points
    
    # Cost tracking
    infrastructure_cost_cents = Column(Integer, default=0, nullable=False)
    platform_cost_cents = Column(Integer, default=0, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    
    def __repr__(self) -> str:
        return f"<TenantUsageMetrics(tenant_id='{self.tenant_id}', date='{self.metric_date}')>"