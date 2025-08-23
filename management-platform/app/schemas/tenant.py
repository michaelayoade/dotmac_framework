"""
Tenant schemas for multi-tenant operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from ..models.tenant import TenantStatus, TenantTier
from ..core.sanitization import (
    validate_safe_string, validate_html_string, validate_plain_string,
    validate_email_string, validate_filename_string
)
from .common import BaseResponse


class TenantBase(BaseModel):
    """Base tenant schema."""
    name: str = Field(..., min_length=2, max_length=255, description="Tenant name")
    display_name: str = Field(..., min_length=2, max_length=255, description="Display name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    primary_contact_email: EmailStr = Field(..., description="Primary contact email")
    primary_contact_name: str = Field(..., min_length=2, max_length=255, description="Contact name")
    business_phone: Optional[str] = Field(None, max_length=20, description="Business phone")
    business_address: Optional[str] = Field(None, max_length=500, description="Business address")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    tier: TenantTier = Field(TenantTier.SMALL, description="Resource tier")
    custom_domain: Optional[str] = Field(None, max_length=255, description="Custom domain")
    max_customers: int = Field(1000, ge=1, le=1000000, description="Maximum customers")
    max_services: int = Field(10000, ge=1, le=10000000, description="Maximum services")
    max_storage_gb: int = Field(100, ge=1, le=10000, description="Maximum storage in GB")
    max_bandwidth_mbps: int = Field(1000, ge=1, le=100000, description="Maximum bandwidth")
    
    # Branding
    logo_url: Optional[str] = Field(None, max_length=500, description="Logo URL")
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Primary color")
    
    # Compliance
    gdpr_compliant: bool = Field(True, description="GDPR compliance required")
    data_region: str = Field("US", description="Data region")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tenant name with security checks."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return validate_safe_string(v, "tenant_name")
    
    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Validate display name with HTML sanitization."""
        return validate_plain_string(v)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description with HTML sanitization."""
        if v is None:
            return v
        return validate_html_string(v)
    
    @field_validator('primary_contact_email')
    @classmethod
    def validate_primary_contact_email(cls, v: str) -> str:
        """Validate primary contact email."""
        return validate_email_string(v)
    
    @field_validator('primary_contact_name')
    @classmethod
    def validate_primary_contact_name(cls, v: str) -> str:
        """Validate contact name."""
        return validate_plain_string(v)
    
    @field_validator('business_phone')
    @classmethod
    def validate_business_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate business phone."""
        if v is None:
            return v
        return validate_safe_string(v, "business_phone")
    
    @field_validator('business_address')
    @classmethod
    def validate_business_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate business address."""
        if v is None:
            return v
        return validate_plain_string(v)


class TenantUpdate(BaseModel):
    """Schema for updating tenant information."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    primary_contact_email: Optional[EmailStr] = None
    primary_contact_name: Optional[str] = Field(None, min_length=2, max_length=255)
    business_phone: Optional[str] = Field(None, max_length=20)
    business_address: Optional[str] = Field(None, max_length=500)
    custom_domain: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    max_users: Optional[int] = Field(None, gt=0, le=100000, description="Maximum users (maps to max_customers)")
    
    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate display name with HTML sanitization."""
        if v is None:
            return v
        return validate_plain_string(v)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description with HTML sanitization."""
        if v is None:
            return v
        return validate_html_string(v)
    
    @field_validator('primary_contact_email')
    @classmethod
    def validate_primary_contact_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate primary contact email."""
        if v is None:
            return v
        return validate_email_string(v)
    
    @field_validator('primary_contact_name')
    @classmethod
    def validate_primary_contact_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact name."""
        if v is None:
            return v
        return validate_plain_string(v)
    
    @field_validator('business_phone')
    @classmethod
    def validate_business_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate business phone."""
        if v is None:
            return v
        return validate_safe_string(v, "business_phone")
    
    @field_validator('business_address')
    @classmethod
    def validate_business_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate business address."""
        if v is None:
            return v
        return validate_plain_string(v)
    
    @field_validator('logo_url')
    @classmethod
    def validate_logo_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate logo URL."""
        if v is None:
            return v
        return validate_safe_string(v, "logo_url")


class TenantResponse(BaseResponse):
    """Tenant response schema."""
    name: str
    display_name: str
    description: Optional[str]
    slug: str
    primary_contact_email: EmailStr
    primary_contact_name: str
    business_phone: Optional[str]
    business_address: Optional[str]
    status: TenantStatus
    tier: TenantTier
    activated_at: Optional[datetime]
    suspended_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    max_customers: int
    max_services: int
    max_storage_gb: int
    max_bandwidth_mbps: int
    custom_domain: Optional[str]
    ssl_enabled: bool
    backup_retention_days: int
    logo_url: Optional[str]
    primary_color: Optional[str]
    billing_email: Optional[str]
    billing_cycle: str
    gdpr_compliant: bool
    data_region: str
    encryption_enabled: bool


class TenantListResponse(BaseModel):
    """Tenant list response schema."""
    tenants: List[TenantResponse]
    total: int
    page: int
    per_page: int
    pages: int


class TenantStatusUpdate(BaseModel):
    """Schema for updating tenant status."""
    status: TenantStatus = Field(..., description="New status")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")


class TenantConfigurationBase(BaseModel):
    """Base tenant configuration schema."""
    category: str = Field(..., max_length=100, description="Configuration category")
    key: str = Field(..., max_length=255, description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    is_encrypted: bool = Field(False, description="Whether value is encrypted")
    environment: str = Field("production", description="Environment")


class TenantConfigurationCreate(TenantConfigurationBase):
    """Schema for creating tenant configuration."""
    pass


class TenantConfigurationUpdate(BaseModel):
    """Schema for updating tenant configuration."""
    value: Any = Field(..., description="New configuration value")
    is_encrypted: Optional[bool] = None


class TenantConfigurationResponse(BaseResponse):
    """Tenant configuration response schema."""
    tenant_id: UUID
    category: str
    key: str
    value: Any
    is_active: bool
    is_encrypted: bool
    environment: str


class TenantOnboardingRequest(BaseModel):
    """Schema for tenant onboarding."""
    tenant_info: TenantCreate
    preferred_cloud_provider: str = Field(..., description="Cloud provider preference")
    preferred_region: str = Field(..., description="Deployment region")
    instance_size: str = Field("small", description="Instance size")
    enabled_features: List[str] = Field(default_factory=list, description="Enabled features")
    branding_config: Dict[str, Any] = Field(default_factory=dict, description="Branding configuration")
    deployment_timeline: str = Field("standard", description="Deployment priority")


class TenantOnboardingResponse(BaseModel):
    """Tenant onboarding response schema."""
    tenant: TenantResponse
    workflow_id: str
    estimated_completion_hours: int
    deployment_steps: List[Dict[str, Any]]


class TenantInvitationCreate(BaseModel):
    """Schema for tenant invitation."""
    email: EmailStr = Field(..., description="Email to invite")
    role: str = Field(..., description="Role in tenant")
    message: Optional[str] = Field(None, max_length=1000, description="Personal message")


class TenantInvitationResponse(BaseResponse):
    """Tenant invitation response schema."""
    tenant_id: UUID
    email: EmailStr
    role: str
    invitation_token: str
    expires_at: datetime
    is_accepted: bool
    invited_by: UUID
    message: Optional[str]


class TenantUsageMetricsResponse(BaseModel):
    """Tenant usage metrics response."""
    tenant_id: UUID
    metric_date: datetime
    period_type: str
    active_customers: int
    active_services: int
    storage_used_gb: int
    bandwidth_used_gb: int
    api_requests: int
    avg_response_time_ms: Optional[int]
    uptime_percentage: int
    error_rate: int
    infrastructure_cost_cents: int
    platform_cost_cents: int


class TenantHealthStatus(BaseModel):
    """Tenant health status schema."""
    tenant_id: UUID
    health_score: int = Field(..., ge=0, le=100, description="Overall health score")
    status: str
    uptime_percentage: float
    response_time_ms: int
    error_rate: float
    last_health_check: datetime
    active_alerts: int
    critical_issues: int
    warnings: int


class TenantResourceUsage(BaseModel):
    """Tenant resource usage schema."""
    tenant_id: UUID
    customers_count: int
    services_count: int
    storage_used_gb: float
    bandwidth_used_gb: float
    customers_utilization: float
    services_utilization: float
    storage_utilization: float
    bandwidth_utilization: float


class TenantBrandingUpdate(BaseModel):
    """Schema for updating tenant branding."""
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    custom_css: Optional[str] = Field(None, max_length=10000)
    
    
class TenantBillingUpdate(BaseModel):
    """Schema for updating tenant billing info."""
    billing_email: Optional[EmailStr] = None
    billing_cycle: Optional[str] = Field(None, pattern="^(monthly|annual)$")


class TenantIntegrationUpdate(BaseModel):
    """Schema for updating tenant integrations."""
    webhook_url: Optional[str] = Field(None, max_length=500)
    webhook_secret: Optional[str] = Field(None, max_length=255)


class TenantSummary(BaseModel):
    """Tenant summary for dashboard."""
    id: UUID
    name: str
    display_name: str
    status: TenantStatus
    tier: TenantTier
    created_at: datetime
    activated_at: Optional[datetime]
    users_count: int
    health_score: Optional[int]
    monthly_revenue: Optional[float]
    subscription_status: Optional[str]