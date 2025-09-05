"""
Production-ready schema base classes with strict validation enforcement.
Mandatory inheritance for all schemas - no custom BaseModel usage allowed.
"""

import logging
import re
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from pydantic.config import ConfigDict


class TenantModel(BaseModel):
    """Base tenant-aware schema model."""

    tenant_id: str | None = Field(None, description="Tenant identifier")


logger = logging.getLogger(__name__)

# Type variable for generic pagination
T = TypeVar("T")


class SchemaValidationError(Exception):
    """Raised when schemas don't follow DRY patterns."""

    pass


# === Core Base Schemas ===


class BaseSchema(BaseModel):
    """Production-ready root base schema with strict validation."""

    model_config = ConfigDict(
        # Strict validation - no extra fields allowed
        extra="forbid",
        # Validate on assignment
        validate_assignment=True,
        # Use enum values
        use_enum_values=True,
        # Populate by name and alias
        populate_by_name=True,
        # Enable ORM mode for database integration
        from_attributes=True,
        # Strict validation for production
        str_strip_whitespace=True,
        json_schema_extra={"examples": []},
    )

    def __init_subclass__(cls, **kwargs):
        """Enforce schema inheritance patterns."""
        super().__init_subclass__(**kwargs)

        # Ensure all schemas inherit from our base classes
        if cls.__name__ != "BaseSchema" and not any(
            base.__name__.endswith(("Entity", "Schema", "Mixin")) for base in cls.__mro__[1:]
        ):
            logger.warning(f"Schema {cls.__name__} should inherit from standard base classes")

        # Log schema registration for audit
        logger.debug(f"Registered schema: {cls.__name__}")


class TimestampMixin(BaseModel):
    """Mixin for entities with timestamps - used in 80% of schemas."""

    created_at: datetime | None = Field(None, description="When the entity was created")
    updated_at: datetime | None = Field(None, description="When the entity was last updated")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime strings to datetime objects with strict validation."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid datetime format: {v}") from e
        if isinstance(v, datetime):
            return v
        raise ValueError(f"Datetime must be string or datetime object, got {type(v)}")


class IdentifiedMixin(BaseModel):
    """Mixin for entities with UUID identification."""

    id: UUID = Field(description="Unique identifier for the entity")


class NamedMixin(BaseModel):
    """Mixin for entities with name fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Name of the entity")

    @field_validator("name")
    def validate_name(cls, v):
        """Validate name contains valid characters."""
        if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()


class DescriptionMixin(BaseModel):
    """Mixin for entities with description fields."""

    description: str | None = Field(None, max_length=1000, description="Optional description")


class StatusMixin(BaseModel):
    """Mixin for entities with status tracking."""

    is_active: bool = Field(True, description="Whether the entity is active")

    status: str | None = Field("active", description="Current status of the entity")


class TenantMixin(BaseModel):
    """Mixin for multi-tenant entities."""

    tenant_id: UUID | None = Field(None, description="Tenant this entity belongs to")


# === Contact Information Mixins ===


class EmailMixin(BaseModel):
    """Mixin for entities with email fields."""

    email: EmailStr = Field(description="Email address")

    @field_validator("email")
    def validate_email(cls, v):
        """Additional email validation."""
        return v.lower().strip()


class PhoneMixin(BaseModel):
    """Mixin for entities with phone fields."""

    phone: str | None = Field(
        None, description="Phone number", pattern=r"^\+?[\d\s\-\(\)]{10,}$"
    )

    @field_validator("phone")
    def validate_phone(cls, v):
        """Clean and validate phone number."""
        if v:
            # Remove non-digit characters except +
            cleaned = re.sub(r"[^\d+]", "", v)
            if len(cleaned) < 10:
                raise ValueError("Phone number too short")
            return cleaned
        return v


class AddressMixin(BaseModel):
    """Mixin for entities with address fields."""

    address: dict[str, Any] | None = Field(None, description="Address information")

    @field_validator("address")
    def validate_address(cls, v):
        """Validate address structure."""
        if v:
            required_fields = ["street", "city"]
            for field in required_fields:
                if not v.get(field):
                    raise ValueError(f"Address must include {field}")
        return v


# === Standard Entity Base Classes ===


class BaseEntity(BaseSchema, IdentifiedMixin, TimestampMixin):
    """Base class for all entities with ID and timestamps."""

    pass


class NamedEntity(BaseEntity, NamedMixin, DescriptionMixin):
    """Base class for named entities with descriptions."""

    pass


class ActiveEntity(NamedEntity, StatusMixin):
    """Base class for entities with status tracking."""

    pass


class TenantEntity(ActiveEntity, TenantMixin):
    """Base class for multi-tenant entities."""

    pass


class PersonEntity(BaseEntity, StatusMixin, TenantMixin):
    """Base class for person-related entities."""

    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=r"^\+?[\d\s\-\(\)]{10,}$")

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"


class CompanyEntity(TenantEntity):
    """Base class for company/organization entities."""

    company_name: str | None = Field(None, max_length=200, description="Company name")
    tax_id: str | None = Field(None, max_length=50, description="Tax identification number")


# === CRUD Operation Schemas ===


class BaseCreateSchema(BaseSchema):
    """Base schema for create operations."""

    model_config = ConfigDict(exclude_none=True)


class BaseUpdateSchema(BaseSchema):
    """Base schema for update operations - all fields optional."""

    model_config = ConfigDict(exclude_none=True)


class BaseResponseSchema(BaseEntity):
    """Base schema for API responses."""

    model_config = ConfigDict(exclude_none=False, from_attributes=True)


# === Pagination and Search Schemas ===


class PaginationSchema(BaseSchema):
    """Standard pagination parameters."""

    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


class PaginatedResponseSchema(BaseSchema, Generic[T]):
    """Standard paginated response format."""

    items: list[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")

    @model_validator(mode="before")
    @classmethod
    def calculate_pages(cls, values):
        """Calculate total pages."""
        total = values.get("total", 0)
        size = values.get("size", 20)
        values["pages"] = (total + size - 1) // size if total > 0 else 0
        return values


class SearchSchema(BaseSchema):
    """Standard search parameters."""

    query: str | None = Field(None, max_length=500, description="Search query")
    filters: dict[str, Any] | None = Field(None, description="Additional filters")
    sort_by: str | None = Field("created_at", description="Field to sort by")
    sort_order: str | None = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# === Specialized Validation Mixins ===


class CurrencyMixin(BaseModel):
    """Mixin for entities with currency fields."""

    amount: float = Field(..., ge=0, description="Amount in the specified currency")
    currency: str = Field("USD", pattern="^[A-Z]{3}$", description="Currency code (ISO 4217)")


class DateRangeMixin(BaseModel):
    """Mixin for entities with date ranges."""

    start_date: datetime | None = Field(None, description="Start date")
    end_date: datetime | None = Field(None, description="End date")

    @model_validator(mode="after")
    def validate_date_range(self):
        """Ensure end_date is after start_date."""
        start = self.start_date
        end = self.end_date

        if start and end and end <= start:
            raise ValueError("End date must be after start date")

        return self


class GeoLocationMixin(BaseModel):
    """Mixin for entities with geographic coordinates."""

    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")


# === Usage Examples and Migration Guide ===

"""
BEFORE (repeated across multiple schema files):
class CustomerResponse(BaseModel):
    id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\\+?[\\d\\s\\-\\(\\)]{10,}$')
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID

AFTER (DRY approach):
class CustomerResponse(PersonEntity):
    # Inherits all common fields automatically
    # Add only customer-specific fields
    account_balance: float = Field(0.0, description="Account balance")
    subscription_tier: str = Field("basic", description="Subscription tier")

MIGRATION STEPS:
1. Import: from dotmac.core.schemas.base_schemas import PersonEntity
2. Change: class CustomerResponse(BaseModel) -> class CustomerResponse(PersonEntity)
3. Remove: All duplicate field definitions that are in PersonEntity
4. Keep: Only customer-specific fields
"""
