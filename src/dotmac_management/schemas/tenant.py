"""
Tenant schemas aligned with database migration schema.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from dotmac_shared.validation.common_validators import CommonValidators, ValidationPatterns
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)

from ..core.sanitization import (
    validate_email_string,
    validate_plain_string,
    validate_safe_string,
)
from ..models.tenant import TenantStatus
from .common import BaseResponse


class TenantBase(BaseModel):
    """Base tenant schema matching database schema."""

    name: str = Field(..., min_length=2, max_length=255, description="Tenant name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    contact_email: EmailStr = Field(..., description="Contact email")
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact name")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Enhanced tenant name validation"""
        return CommonValidators.validate_required_string(v, "Tenant name", 2, 255)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced description validation"""
        return CommonValidators.validate_description(v, 1000)

    @field_validator("contact_name")
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced contact name validation"""
        if v is None:
            return None
        return CommonValidators.validate_user_name(v)

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced phone validation"""
        return CommonValidators.validate_phone(v)


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""

    slug: str = Field(..., min_length=2, max_length=100, description="Unique slug")
    settings: Optional[dict[str, Any]] = Field(None, description="Tenant settings")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tenant name."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return validate_safe_string(v, "tenant_name")

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str) -> str:
        """Validate contact email."""
        return validate_email_string(v)

    @field_validator("contact_name")
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact name."""
        if v is None:
            return v
        return validate_plain_string(v)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Enhanced slug validation using common validators"""
        # Use the common slug validator
        return CommonValidators.validate_slug(v, "Tenant slug")


class TenantUpdate(BaseModel):
    """Schema for updating tenant information."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    settings: Optional[dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate tenant name."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return validate_safe_string(v, "tenant_name")

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact email."""
        if v is None:
            return v
        return validate_email_string(v)

    @field_validator("contact_name")
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
    settings: Optional[dict[str, Any]]


class TenantListResponse(BaseModel):
    """Tenant list response schema."""

    tenants: list[TenantResponse]
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

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate configuration category"""
        clean_category = CommonValidators.validate_required_string(v, "Configuration category", 2, 100)

        # Allow only alphanumeric and underscore for config categories
        if not ValidationPatterns.SLUG.match(clean_category.replace("_", "-")):
            raise ValueError("Configuration category can only contain lowercase letters, numbers, and underscores")

        return clean_category

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate configuration key"""
        clean_key = CommonValidators.validate_required_string(v, "Configuration key", 1, 255)

        # Allow alphanumeric, underscore, dot, and hyphen for config keys
        import re

        if not re.match(r"^[a-zA-Z0-9._-]+$", clean_key):
            raise ValueError("Configuration key can only contain letters, numbers, dots, underscores, and hyphens")

        return clean_key

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        """Validate configuration value with security checks"""
        if isinstance(v, str):
            # String length limit
            if len(v) > 10000:  # 10KB limit for string values
                raise ValueError("Configuration value must be less than 10KB")

            # Basic security check - prevent script injection
            if "<script" in v.lower() or "javascript:" in v.lower():
                raise ValueError("Configuration value contains potentially dangerous content")

        elif isinstance(v, dict):
            # JSON object size limit
            import json

            json_str = json.dumps(v)
            if len(json_str) > 50000:  # 50KB limit for JSON values
                raise ValueError("Configuration value JSON must be less than 50KB")

        return v


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
    enabled_features: list[str] = Field(default_factory=list, description="Enabled features")

    @field_validator("deployment_region")
    @classmethod
    def validate_deployment_region(cls, v: str) -> str:
        """Validate deployment region"""
        return CommonValidators.validate_region(v)

    @field_validator("instance_size")
    @classmethod
    def validate_instance_size(cls, v: str) -> str:
        """Validate instance size"""
        clean_size = v.strip().lower()
        allowed_sizes = ["small", "medium", "large", "xlarge", "xxlarge"]

        if clean_size not in allowed_sizes:
            raise ValueError(f"Instance size must be one of: {allowed_sizes}")

        return clean_size

    @field_validator("enabled_features")
    @classmethod
    def validate_enabled_features(cls, v: list[str]) -> list[str]:
        """Validate enabled features list"""
        if not isinstance(v, list):
            raise ValueError("Enabled features must be a list")

        # Limit number of features
        if len(v) > 50:
            raise ValueError("Cannot enable more than 50 features")

        # Validate each feature name
        clean_features = []
        for feature in v:
            if not isinstance(feature, str):
                raise ValueError("Feature names must be strings")

            clean_feature = feature.strip().lower()

            # Feature name format validation
            if not ValidationPatterns.SLUG.match(clean_feature):
                raise ValueError(f'Feature name "{feature}" contains invalid characters')

            if len(clean_feature) < 2 or len(clean_feature) > 50:
                raise ValueError(f'Feature name "{feature}" must be between 2 and 50 characters')

            clean_features.append(clean_feature)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(clean_features))


class TenantOnboardingResponse(BaseModel):
    """Tenant onboarding response schema."""

    tenant: TenantResponse
    workflow_id: str
    estimated_completion_hours: int
    deployment_steps: list[dict[str, Any]]


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
