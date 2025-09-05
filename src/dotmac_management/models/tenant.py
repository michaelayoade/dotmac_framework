"""
Tenant management models for the Management platform
"""

from enum import Enum

from dotmac.database.base import BaseModel
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text


class TenantStatus(str, Enum):
    """Tenant provisioning and operational status"""

    REQUESTED = "requested"  # Initial signup submitted
    VALIDATING = "validating"  # Validating signup details
    QUEUED = "queued"  # Queued for provisioning
    PROVISIONING = "provisioning"  # Infrastructure being created
    MIGRATING = "migrating"  # Database migrations running
    SEEDING = "seeding"  # Initial data being seeded
    TESTING = "testing"  # Running health checks
    READY = "ready"  # Fully operational
    ACTIVE = "active"  # Active and serving traffic
    SUSPENDED = "suspended"  # Temporarily disabled
    FAILED = "failed"  # Provisioning failed
    DEPROVISIONING = "deprovisioning"  # Being torn down
    ARCHIVED = "archived"  # Permanently disabled


class TenantPlan(str, Enum):
    """Tenant subscription plans"""

    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class DeploymentType(str, Enum):
    """How the tenant infrastructure is deployed"""

    MANAGED = "managed"  # We provision and manage infrastructure
    CUSTOMER_VPS = "customer_vps"  # Customer provides VPS, we manage software


class CustomerTenant(BaseModel):
    """Customer tenant - represents a provisioned ISP customer environment"""

    __tablename__ = "customer_tenants"

    # Identity
    tenant_id = Column(String(100), unique=True, nullable=False, index=True)
    subdomain = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=False)
    description = Column(Text)

    # Status and lifecycle
    status = Column(String(50), default=TenantStatus.REQUESTED, nullable=False, index=True)
    plan = Column(String(50), default=TenantPlan.STARTER, nullable=False)
    deployment_type = Column(String(50), default=DeploymentType.MANAGED, nullable=False, index=True)
    region = Column(String(50), nullable=False)

    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_email = Column(String(255), nullable=False)
    admin_name = Column(String(200), nullable=False)

    # Infrastructure
    domain = Column(String(255))  # Full domain: subdomain.example.com
    container_id = Column(String(100))  # Coolify container/service ID
    database_url = Column(String(500))  # Encrypted tenant database URL
    redis_url = Column(String(500))  # Encrypted tenant Redis URL

    # Configuration
    settings = Column(JSON, default=dict)
    environment_vars = Column(JSON, default=dict)  # Encrypted tenant-specific env vars

    # Provisioning metadata
    provisioning_logs = Column(JSON, default=list)
    provisioning_started_at = Column(DateTime)
    provisioning_completed_at = Column(DateTime)
    last_health_check = Column(DateTime)
    health_status = Column(String(50), default="unknown")

    # Billing
    billing_email = Column(String(255))
    payment_method_id = Column(String(100))  # Stripe/payment provider ID
    subscription_id = Column(String(100))
    next_billing_date = Column(DateTime)

    # Features
    enabled_features = Column(JSON, default=list)
    feature_limits = Column(JSON, default=dict)

    # VPS-specific fields (only used when deployment_type = CUSTOMER_VPS)
    vps_ip = Column(String(45))  # IPv4 or IPv6
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100))
    ssh_key = Column(Text)  # SSH public key
    ssh_password_hash = Column(String(255))  # Encrypted password (alternative)
    custom_domain = Column(String(255))  # Customer's custom domain
    expected_customers = Column(Integer, default=100)
    estimated_traffic = Column(String(20), default="low")  # low, medium, high
    timezone = Column(String(50), default="UTC")
    preferred_backup_time = Column(String(10), default="02:00")
    support_tier = Column(String(50), default="basic")  # basic, premium, enterprise
