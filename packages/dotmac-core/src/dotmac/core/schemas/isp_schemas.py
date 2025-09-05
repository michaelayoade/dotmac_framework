"""ISP-specific schema patterns for DRY implementation."""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from .base_schemas import TenantModel


class ISPBaseSchema(TenantModel):
    """Base schema for all ISP module operations."""

    pass


class ISPCreateSchema(ISPBaseSchema):
    """Base schema for ISP resource creation."""

    tenant_id: str = Field(..., description="Tenant identifier")


class ISPUpdateSchema(TenantModel):
    """Base schema for ISP resource updates."""

    # Most update schemas have optional fields
    pass


class ISPResponseSchema(ISPBaseSchema):
    """Base schema for ISP API responses."""

    id: UUID = Field(..., description="Unique resource identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class ISPListResponseSchema(TenantModel):
    """Base schema for ISP list responses."""

    items: list = Field(..., description="List of items")
    total: int = Field(..., description="Total item count")
    page: int = Field(1, description="Current page")
    per_page: int = Field(50, description="Items per page")

    model_config = ConfigDict(from_attributes=True)
