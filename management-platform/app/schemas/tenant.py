"""
Tenant schemas aligned with database migration schema.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from ..models.tenant import TenantStatus
from ..core.sanitization import (
    validate_safe_string, validate_html_string, validate_plain_string,
    validate_email_string
)
from .common import BaseResponse


class TenantBase(BaseModel):
    """Base tenant schema matching database schema."""
    name: str = Field(..., min_length=2, max_length=255, description="Tenant name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    contact_email: EmailStr = Field(..., description="Contact email")
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact name")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    slug: str = Field(..., min_length=2, max_length=100, description="Unique slug")
    settings: Optional[Dict[str, Any]] = Field(None, description="Tenant settings")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tenant name."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return validate_safe_string(v, "tenant_name")
    
    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v: str) -> str:
        """Validate contact email."""
        return validate_email_string(v)
    
    @field_validator('contact_name')
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact name."""
        if v is None:
            return v
        return validate_plain_string(v)
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug - alphanumeric and hyphens only."""
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Slug cannot start or end with hyphen")
        return v


class TenantUpdate(BaseModel):
    """Schema for updating tenant information."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate tenant name."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return validate_safe_string(v, "tenant_name")
    
    @field_validator('contact_email')
    @classmethod
    def validate_contact_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact email."""
        if v is None:
            return v
        return validate_email_string(v)
    
    @field_validator('contact_name')
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact name."""
        if v is None:
            return v
        return validate_plain_string(v)


class TenantResponse(BaseResponse):
    """Tenant response schema."""
    name: str
    slug: str
    description: Optional[str]
    contact_email: EmailStr
    contact_name: Optional[str]
    contact_phone: Optional[str]
    status: TenantStatus
    settings: Optional[Dict[str, Any]]


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
    is_encrypted: bool


class TenantInvitationCreate(BaseModel):
    """Schema for tenant invitation."""
    email: EmailStr = Field(..., description="Email to invite")
    role: str = Field(..., description="Role in tenant")
    invited_by: Optional[str] = Field(None, description="Who sent the invitation")


class TenantInvitationResponse(BaseResponse):
    """Tenant invitation response schema."""
    tenant_id: UUID
    email: EmailStr
    role: str
    invited_by: Optional[str]
    expires_at: Optional[datetime]
    accepted_at: Optional[datetime]


class TenantOnboardingRequest(BaseModel):
    """Schema for tenant onboarding."""
    tenant_info: TenantCreate
    deployment_region: str = Field("us-east-1", description="Deployment region")
    instance_size: str = Field("small", description="Instance size")
    enabled_features: List[str] = Field(default_factory=list, description="Enabled features")


class TenantOnboardingResponse(BaseModel):
    """Tenant onboarding response schema."""
    tenant: TenantResponse
    workflow_id: str
    estimated_completion_hours: int
    deployment_steps: List[Dict[str, Any]]


class TenantSummary(BaseModel):
    """Tenant summary for dashboard."""
    id: UUID
    name: str
    slug: str
    status: TenantStatus
    created_at: datetime
    users_count: int
    health_score: Optional[int]
    monthly_revenue: Optional[float]
    subscription_status: Optional[str]