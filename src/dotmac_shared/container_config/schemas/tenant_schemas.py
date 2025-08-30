"""Tenant-specific schemas and data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SubscriptionPlan(str, Enum):
    """Available subscription plans."""

    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class EnvironmentType(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class TenantStatus(str, Enum):
    """Tenant status options."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    MIGRATING = "migrating"


class TenantLimits(BaseModel):
    """Resource limits for a tenant."""

    # User limits
    max_users: int = Field(default=10, ge=1, description="Maximum number of users")
    max_admins: int = Field(
        default=5, ge=1, description="Maximum number of admin users"
    )

    # Data limits
    max_storage_gb: int = Field(default=10, ge=1, description="Maximum storage in GB")
    max_bandwidth_gb: int = Field(
        default=100, ge=1, description="Maximum bandwidth in GB/month"
    )

    # API limits
    api_rate_limit: int = Field(default=1000, ge=1, description="API requests per hour")
    max_api_keys: int = Field(default=5, ge=1, description="Maximum API keys")

    # Service limits
    max_services: int = Field(
        default=10, ge=1, description="Maximum number of services"
    )
    max_integrations: int = Field(default=5, ge=0, description="Maximum integrations")

    # Database limits
    max_database_connections: int = Field(
        default=20, ge=1, description="Max DB connections"
    )
    max_database_size_gb: int = Field(
        default=5, ge=1, description="Max database size in GB"
    )

    # Compute limits
    max_cpu_cores: float = Field(default=2.0, ge=0.1, description="Maximum CPU cores")
    max_memory_gb: float = Field(
        default=4.0, ge=0.5, description="Maximum memory in GB"
    )

    # Network limits
    max_concurrent_connections: int = Field(
        default=100, ge=1, description="Max concurrent connections"
    )

    @field_validator("max_cpu_cores", "max_memory_gb")
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class TenantMetadata(BaseModel):
    """Additional metadata for a tenant."""

    # Business information
    company_name: Optional[str] = Field(None, description="Company name")
    industry: Optional[str] = Field(None, description="Industry sector")
    region: Optional[str] = Field(None, description="Geographic region")
    timezone: str = Field(default="UTC", description="Tenant timezone")

    # Technical metadata
    deployment_region: Optional[str] = Field(None, description="Deployment region")
    data_center: Optional[str] = Field(None, description="Data center location")
    kubernetes_namespace: Optional[str] = Field(None, description="K8s namespace")

    # Billing metadata
    billing_contact: Optional[str] = Field(None, description="Billing contact email")
    payment_method: Optional[str] = Field(None, description="Payment method")

    # Support metadata
    support_tier: str = Field(default="standard", description="Support tier level")
    support_contact: Optional[str] = Field(None, description="Support contact")

    # Custom fields
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )


class TenantSettings(BaseModel):
    """Tenant-specific settings and preferences."""

    # Feature toggles
    features_enabled: List[str] = Field(
        default_factory=list, description="Enabled features"
    )
    features_disabled: List[str] = Field(
        default_factory=list, description="Disabled features"
    )

    # UI/UX settings
    theme: str = Field(default="default", description="UI theme")
    language: str = Field(default="en", description="Default language")
    date_format: str = Field(default="YYYY-MM-DD", description="Date format preference")
    time_format: str = Field(default="24h", description="Time format (12h/24h)")

    # Notification preferences
    email_notifications: bool = Field(
        default=True, description="Enable email notifications"
    )
    sms_notifications: bool = Field(
        default=False, description="Enable SMS notifications"
    )
    webhook_notifications: bool = Field(
        default=False, description="Enable webhook notifications"
    )

    # Security settings
    password_policy: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_symbols": False,
            "expiry_days": 90,
        },
        description="Password policy configuration",
    )

    mfa_required: bool = Field(
        default=False, description="Require multi-factor authentication"
    )
    session_timeout: int = Field(
        default=3600, ge=300, description="Session timeout in seconds"
    )

    # Data retention
    log_retention_days: int = Field(
        default=30, ge=1, description="Log retention in days"
    )
    backup_retention_days: int = Field(
        default=90, ge=1, description="Backup retention in days"
    )

    # Integration settings
    webhooks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Webhook configurations"
    )
    external_apis: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="External API configs"
    )

    # Custom settings
    custom_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Custom tenant settings"
    )

    @field_validator("session_timeout")
    @classmethod
    def validate_session_timeout(cls, v: int) -> int:
        if v < 300:  # Minimum 5 minutes
            raise ValueError("Session timeout must be at least 300 seconds")
        if v > 86400:  # Maximum 24 hours
            raise ValueError("Session timeout cannot exceed 86400 seconds")
        return v


class TenantInfo(BaseModel):
    """Complete tenant information model."""

    # Core identification
    tenant_id: UUID = Field(..., description="Unique tenant identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    slug: str = Field(
        ..., min_length=1, max_length=100, description="URL-safe tenant slug"
    )

    # Status and lifecycle
    status: TenantStatus = Field(
        default=TenantStatus.ACTIVE, description="Tenant status"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )

    # Subscription information
    subscription_plan: SubscriptionPlan = Field(
        ..., description="Current subscription plan"
    )
    subscription_start_date: datetime = Field(
        default_factory=datetime.now, description="Subscription start date"
    )
    subscription_end_date: Optional[datetime] = Field(
        None, description="Subscription end date"
    )
    billing_cycle: str = Field(default="monthly", description="Billing cycle")

    # Configuration
    limits: TenantLimits = Field(
        default_factory=TenantLimits, description="Resource limits"
    )
    settings: TenantSettings = Field(
        default_factory=TenantSettings, description="Tenant settings"
    )
    metadata: TenantMetadata = Field(
        default_factory=TenantMetadata, description="Additional metadata"
    )

    # Domain and networking
    primary_domain: Optional[str] = Field(None, description="Primary domain")
    custom_domains: List[str] = Field(
        default_factory=list, description="Custom domains"
    )

    # Contact information
    admin_email: str = Field(..., description="Primary admin email")
    technical_contact: Optional[str] = Field(
        None, description="Technical contact email"
    )

    # Deployment information
    environment: EnvironmentType = Field(
        default=EnvironmentType.PRODUCTION, description="Environment type"
    )
    deployment_config: Dict[str, Any] = Field(
        default_factory=dict, description="Deployment configuration"
    )

    # Parent/child relationships (for reseller scenarios)
    parent_tenant_id: Optional[UUID] = Field(None, description="Parent tenant ID")
    child_tenant_ids: List[UUID] = Field(
        default_factory=list, description="Child tenant IDs"
    )

    # Audit fields
    created_by: Optional[str] = Field(None, description="Creator user ID")
    updated_by: Optional[str] = Field(None, description="Last updater user ID")
    version: int = Field(default=1, description="Configuration version")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Slug must contain only lowercase letters, numbers, and hyphens"
            )
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with a hyphen")
        return v

    @field_validator("admin_email", "technical_contact")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("custom_domains")
    @classmethod
    def validate_domains(cls, v: List[str]) -> List[str]:
        import re

        domain_pattern = r"^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.([a-zA-Z]{2,}|[a-zA-Z]{2,}\.[a-zA-Z]{2,})$"
        for domain in v:
            if not re.match(domain_pattern, domain):
                raise ValueError(f"Invalid domain format: {domain}")
        return v

    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE

    def is_subscription_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.subscription_end_date is None:
            return True
        return datetime.now() < self.subscription_end_date

    def get_plan_features(self) -> List[str]:
        """Get features available for current subscription plan."""
        plan_features = {
            SubscriptionPlan.BASIC: [
                "basic_analytics",
                "email_support",
                "standard_integration",
            ],
            SubscriptionPlan.PREMIUM: [
                "basic_analytics",
                "advanced_analytics",
                "email_support",
                "phone_support",
                "standard_integration",
                "premium_integration",
                "custom_branding",
            ],
            SubscriptionPlan.ENTERPRISE: [
                "basic_analytics",
                "advanced_analytics",
                "email_support",
                "phone_support",
                "priority_support",
                "standard_integration",
                "premium_integration",
                "enterprise_integration",
                "custom_branding",
                "white_label",
                "sso",
                "advanced_security",
            ],
            SubscriptionPlan.CUSTOM: [],  # Defined per tenant
        }
        return plan_features.get(self.subscription_plan, [])

    def can_access_feature(self, feature_name: str) -> bool:
        """Check if tenant can access a specific feature."""
        # Check explicit settings first
        if feature_name in self.settings.features_disabled:
            return False
        if feature_name in self.settings.features_enabled:
            return True

        # Check plan features
        return feature_name in self.get_plan_features()

    def get_resource_usage_percentage(
        self, resource: str, current_usage: float
    ) -> float:
        """Calculate resource usage percentage."""
        limits_map = {
            "storage": self.limits.max_storage_gb,
            "bandwidth": self.limits.max_bandwidth_gb,
            "users": self.limits.max_users,
            "cpu": self.limits.max_cpu_cores,
            "memory": self.limits.max_memory_gb,
        }

        if resource not in limits_map:
            return 0.0

        limit = limits_map[resource]
        return min((current_usage / limit) * 100, 100.0) if limit > 0 else 0.0

    def to_config_context(self) -> Dict[str, Any]:
        """Convert tenant info to template context."""
        return {
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "slug": self.slug,
            "plan": self.subscription_plan,
            "environment": self.environment,
            "limits": self.limits.model_dump(),
            "settings": self.settings.model_dump(),
            "metadata": self.metadata.model_dump(),
            "domains": {"primary": self.primary_domain, "custom": self.custom_domains},
            "features": self.get_plan_features(),
            "contacts": {
                "admin": self.admin_email,
                "technical": self.technical_contact,
            },
        }
