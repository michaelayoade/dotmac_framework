"""
Pydantic schemas for tenant management API requests and responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from .models import TenantStatus


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Internal tenant name")
    display_name: str = Field(..., min_length=1, max_length=255, description="Display name for the ISP")
    description: Optional[str] = Field(None, description="Tenant description")
    
    primary_contact_email: EmailStr = Field(..., description="Primary contact email address")
    primary_contact_name: str = Field(..., min_length=1, max_length=255, description="Primary contact name")
    business_phone: Optional[str] = Field(None, max_length=50, description="Business phone number")
    business_address: Optional[str] = Field(None, description="Business address")
    
    subscription_tier: str = Field("standard", description="Subscription tier")
    billing_email: Optional[EmailStr] = Field(None, description="Billing contact email")
    billing_cycle: str = Field("monthly", pattern="^(monthly|annual)$", description="Billing cycle")
    
    custom_domain: Optional[str] = Field(None, max_length=255, description="Custom domain for the tenant")
    ssl_enabled: bool = Field(True, description="SSL enabled for custom domain")
    backup_retention_days: int = Field(30, ge=1, le=365, description="Backup retention in days")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    
    # Resource limits
    max_customers: int = Field(1000, ge=1, le=100000, description="Maximum number of customers")
    max_services: int = Field(10000, ge=1, le=1000000, description="Maximum number of services")
    max_storage_gb: int = Field(100, ge=1, le=10000, description="Maximum storage in GB")
    max_bandwidth_mbps: int = Field(1000, ge=1, le=100000, description="Maximum bandwidth in Mbps")
    
    # Multi-tenancy configuration
    isolation_level: str = Field("database", pattern="^(database|schema|row)$", description="Data isolation level")
    
    # Custom settings
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="Custom tenant settings")


class TenantUpdate(BaseModel):
    """Schema for updating tenant information."""
    
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    
    primary_contact_email: Optional[EmailStr] = None
    primary_contact_name: Optional[str] = Field(None, min_length=1, max_length=255)
    business_phone: Optional[str] = Field(None, max_length=50)
    business_address: Optional[str] = None
    
    subscription_tier: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    billing_cycle: Optional[str] = Field(None, pattern="^(monthly|annual)$")
    
    custom_domain: Optional[str] = Field(None, max_length=255)
    ssl_enabled: Optional[bool] = None
    backup_retention_days: Optional[int] = Field(None, ge=1, le=365)
    
    # Resource limits
    max_customers: Optional[int] = Field(None, ge=1, le=100000)
    max_services: Optional[int] = Field(None, ge=1, le=1000000)
    max_storage_gb: Optional[int] = Field(None, ge=1, le=10000)
    max_bandwidth_mbps: Optional[int] = Field(None, ge=1, le=100000)
    
    # Custom settings
    metadata: Optional[Dict[str, Any]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class TenantStatusUpdate(BaseModel):
    """Schema for updating tenant status."""
    
    status: TenantStatus = Field(..., description="New tenant status")
    reason: Optional[str] = Field(None, description="Reason for status change")


class TenantResponse(TenantBase):
    """Schema for tenant API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: str
    status: TenantStatus
    
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Resource limits
    max_customers: int
    max_services: int
    max_storage_gb: int
    max_bandwidth_mbps: int
    
    # Multi-tenancy configuration
    isolation_level: str
    
    # Custom settings
    metadata: Optional[Dict[str, Any]] = None
    custom_settings: Optional[Dict[str, Any]] = None
    
    # Derived properties
    is_active: bool = Field(..., description="Whether tenant is active")
    can_be_managed: bool = Field(..., description="Whether tenant can be managed")


class TenantOnboardingRequest(BaseModel):
    """Comprehensive tenant onboarding request schema."""
    
    # Basic tenant information
    tenant_info: TenantCreate
    
    # Deployment preferences
    preferred_cloud_provider: str = Field(..., pattern="^(aws|azure|gcp|digitalocean)$")
    preferred_region: str = Field(..., description="Preferred deployment region")
    instance_size: str = Field("medium", pattern="^(small|medium|large|xlarge)$")
    
    # Feature configuration
    enabled_features: List[str] = Field(default_factory=list, description="Features to enable")
    integration_requirements: Optional[Dict[str, Any]] = Field(None, description="Required integrations")
    
    # Branding and customization
    branding_config: Optional[Dict[str, Any]] = Field(None, description="Branding configuration")
    
    # Additional requirements
    special_requirements: Optional[str] = Field(None, description="Special requirements or notes")


class TenantConfigurationBase(BaseModel):
    """Base tenant configuration schema."""
    
    category: str = Field(..., min_length=1, max_length=100, description="Configuration category")
    configuration_key: str = Field(..., min_length=1, max_length=255, description="Configuration key")
    configuration_value: Optional[Dict[str, Any]] = Field(None, description="Configuration value")


class TenantConfigurationCreate(TenantConfigurationBase):
    """Schema for creating tenant configurations."""
    
    is_active: bool = Field(True, description="Whether configuration is active")


class TenantConfigurationUpdate(BaseModel):
    """Schema for updating tenant configurations."""
    
    configuration_value: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TenantConfigurationResponse(TenantConfigurationBase):
    """Schema for tenant configuration API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None


class TenantListResponse(BaseModel):
    """Schema for tenant list API responses."""
    
    tenants: List[TenantResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class TenantUsageMetricsResponse(BaseModel):
    """Schema for tenant usage metrics responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    tenant_id: UUID
    metric_date: datetime
    aggregation_period: str
    
    # Usage metrics
    active_customers: int
    active_services: int
    storage_used_gb: int
    bandwidth_used_gb: int
    api_requests: int
    
    # Performance metrics
    avg_response_time_ms: Optional[int] = None
    uptime_percentage: Optional[int] = None
    error_rate_percentage: Optional[int] = None
    
    # Cost tracking
    infrastructure_cost_cents: Optional[int] = None
    platform_cost_cents: Optional[int] = None


class TenantHealthStatus(BaseModel):
    """Schema for tenant health status."""
    
    tenant_id: str
    status: TenantStatus
    last_health_check: Optional[datetime] = None
    health_score: int = Field(..., ge=0, le=100, description="Health score (0-100)")
    
    # Health indicators
    uptime_percentage: Optional[float] = None
    response_time_ms: Optional[int] = None
    error_rate: Optional[float] = None
    resource_utilization: Optional[Dict[str, float]] = None
    
    # Issues and alerts
    active_alerts: int = Field(0, ge=0, description="Number of active alerts")
    critical_issues: int = Field(0, ge=0, description="Number of critical issues")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Health recommendations")