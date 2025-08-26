"""Shared Pydantic schemas and base classes."""

from datetime import datetime, timezone
from typing import Optional, List, Any, Generic, TypeVar
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from fastapi import Query


class BaseSchema(BaseModel):
    """Base Pydantic schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime


class SoftDeleteSchema(BaseSchema):
    """Schema mixin for soft delete fields."""

    deleted_at: Optional[datetime] = None
    is_deleted: bool = False


class TenantSchema(BaseSchema):
    """Schema mixin for tenant fields."""

    tenant_id: UUID


class BaseModelSchema(BaseSchema):
    """Base schema for database models."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False


class TenantModelSchema(BaseModelSchema):
    """Base schema for tenant-specific models."""

    tenant_id: UUID


class AddressSchema(BaseSchema):
    """Schema for address information."""

    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: str = Field(default="US", max_length=2)


class ContactSchema(BaseSchema):
    """Schema for contact information."""

    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    email_primary: Optional[str] = None
    email_secondary: Optional[str] = None
    website: Optional[str] = None


class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


# Type variable for generic pagination
T = TypeVar("T")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Schema for paginated responses."""

    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, size: int):
        """Create paginated response."""
        pages = (total + size - 1) // size  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )


class ErrorResponse(BaseSchema):
    """Schema for error responses."""

    error: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SuccessResponse(BaseSchema):
    """Schema for success responses."""

    success: bool = True
    message: str
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkOperationResponse(BaseSchema):
    """Schema for bulk operation responses."""

    total_processed: int
    successful: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
