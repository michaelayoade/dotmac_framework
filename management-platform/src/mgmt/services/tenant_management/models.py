"""
Tenant management database models for multi-tenant ISP customer management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    Text,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class TenantStatus(str, Enum):
    """Tenant lifecycle status enumeration."""
    
    PENDING = "pending"  # Initial registration, not yet provisioned
    PROVISIONING = "provisioning"  # Infrastructure being created
    ACTIVE = "active"  # Fully operational
    SUSPENDED = "suspended"  # Temporarily disabled
    MAINTENANCE = "maintenance"  # Under maintenance
    DEPROVISIONING = "deprovisioning"  # Being torn down
    CANCELLED = "cancelled"  # Permanently disabled
    FAILED = "failed"  # Provisioning or operation failed


class Tenant(Base):
    """
    Core tenant model representing an ISP customer with their DotMac instance.
    
    This model implements multi-tenant isolation and tracks the complete
    lifecycle of ISP customers from onboarding to cancellation.
    """
    
    __tablename__ = "tenants"
    
    # Primary identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    tenant_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Basic tenant information
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Contact and business information
    primary_contact_email = Column(String(255), nullable=False)
    primary_contact_name = Column(String(255), nullable=False)
    business_phone = Column(String(50), nullable=True)
    business_address = Column(Text, nullable=True)
    
    # Tenant status and lifecycle
    status = Column(SQLEnum(TenantStatus), nullable=False, default=TenantStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    suspended_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Resource allocation and limits
    max_customers = Column(Integer, nullable=False, default=1000)
    max_services = Column(Integer, nullable=False, default=10000)
    max_storage_gb = Column(Integer, nullable=False, default=100)
    max_bandwidth_mbps = Column(Integer, nullable=False, default=1000)
    
    # Subscription and billing
    subscription_tier = Column(String(100), nullable=False, default="standard")
    billing_email = Column(String(255), nullable=True)
    billing_cycle = Column(String(20), nullable=False, default="monthly")  # monthly, annual
    
    # Technical configuration
    custom_domain = Column(String(255), nullable=True)
    ssl_enabled = Column(Boolean, nullable=False, default=True)
    backup_retention_days = Column(Integer, nullable=False, default=30)
    
    # Multi-tenancy isolation
    isolation_level = Column(String(50), nullable=False, default="database")  # database, schema, row
    
    # Metadata and customization
    tenant_metadata = Column(JSON, nullable=True, default=dict)
    custom_settings = Column(JSON, nullable=True, default=dict)
    
    # Relationships
    configurations = relationship("TenantConfiguration", back_populates="tenant", cascade="all, delete-orphan")
    deployments = relationship("TenantDeployment", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant(tenant_id='{self.tenant_id}', name='{self.name}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is in active status."""
        return self.status == TenantStatus.ACTIVE
    
    @property
    def can_be_managed(self) -> bool:
        """Check if tenant can be managed (not cancelled or failed)."""
        return self.status not in [TenantStatus.CANCELLED, TenantStatus.FAILED]


class TenantConfiguration(Base):
    """
    Tenant-specific configuration settings and customizations.
    
    This model stores all customizable settings for each tenant's
    DotMac instance, including branding, features, and integrations.
    """
    
    __tablename__ = "tenant_configurations"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Configuration category and key-value pairs
    category = Column(String(100), nullable=False, index=True)  # branding, features, integrations, etc.
    configuration_key = Column(String(255), nullable=False)
    configuration_value = Column(JSON, nullable=True)
    
    # Configuration metadata
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)  # User ID who created the config
    
    # Relationships
    tenant = relationship("Tenant", back_populates="configurations")
    
    def __repr__(self) -> str:
        return f"<TenantConfiguration(tenant_id='{self.tenant_id}', category='{self.category}', key='{self.configuration_key}')>"


class TenantDeployment(Base):
    """
    Tenant deployment tracking and infrastructure management.
    
    This model tracks the deployment status, infrastructure details,
    and deployment history for each tenant's DotMac instance.
    """
    
    __tablename__ = "tenant_deployments"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Deployment identification
    deployment_id = Column(String(255), unique=True, nullable=False, index=True)
    deployment_name = Column(String(255), nullable=False)
    
    # Infrastructure details
    cloud_provider = Column(String(50), nullable=False)  # aws, azure, gcp, digitalocean
    region = Column(String(100), nullable=False)
    instance_type = Column(String(100), nullable=False)
    
    # Deployment status and tracking
    status = Column(String(50), nullable=False, default="pending")  # pending, deploying, active, failed, destroyed
    deployment_started_at = Column(DateTime, nullable=True)
    deployment_completed_at = Column(DateTime, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    
    # Resource tracking
    allocated_cpu = Column(Integer, nullable=True)
    allocated_memory_gb = Column(Integer, nullable=True)
    allocated_storage_gb = Column(Integer, nullable=True)
    monthly_cost_estimate = Column(Integer, nullable=True)  # Cost in cents
    
    # Deployment configuration
    infrastructure_config = Column(JSON, nullable=True)
    application_config = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="deployments")
    
    def __repr__(self) -> str:
        return f"<TenantDeployment(deployment_id='{self.deployment_id}', tenant_id='{self.tenant_id}', status='{self.status}')>"


class TenantUsageMetrics(Base):
    """
    Tenant usage metrics and billing data collection.
    
    This model tracks resource usage, billing metrics, and
    performance data for each tenant's DotMac instance.
    """
    
    __tablename__ = "tenant_usage_metrics"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Time period for metrics
    metric_date = Column(DateTime, nullable=False, index=True)
    aggregation_period = Column(String(20), nullable=False, default="daily")  # hourly, daily, monthly
    
    # Usage metrics
    active_customers = Column(Integer, nullable=False, default=0)
    active_services = Column(Integer, nullable=False, default=0)
    storage_used_gb = Column(Integer, nullable=False, default=0)
    bandwidth_used_gb = Column(Integer, nullable=False, default=0)
    api_requests = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    avg_response_time_ms = Column(Integer, nullable=True)
    uptime_percentage = Column(Integer, nullable=True)  # 0-10000 (basis points)
    error_rate_percentage = Column(Integer, nullable=True)  # 0-10000 (basis points)
    
    # Cost tracking
    infrastructure_cost_cents = Column(Integer, nullable=True)
    platform_cost_cents = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    
    def __repr__(self) -> str:
        return f"<TenantUsageMetrics(tenant_id='{self.tenant_id}', date='{self.metric_date}', period='{self.aggregation_period}')>"