"""
Shared schemas for ISP platform modules.
Common Pydantic models used across ISP services and modules.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class ServiceType(str, Enum):
    """Service type enumeration."""

    INTERNET = "internet"
    VOICE = "voice"
    TV = "tv"
    BUNDLE = "bundle"


class CustomerStatus(str, Enum):
    """Customer status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common fields."""

    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TenantAwareSchema(BaseSchema):
    """Base schema for tenant-aware entities."""

    tenant_id: Optional[str] = None


class TenantModelSchema(TenantAwareSchema):
    """Base schema for tenant model entities (alias for compatibility)."""

    pass


class AddressSchema(BaseModel):
    """Address schema for standardized address handling."""

    street_address: str = Field(..., min_length=1, max_length=200)
    street_address_2: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    state_province: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=3)  # ISO country codes
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    model_config = ConfigDict(from_attributes=True)


class ContactSchema(BaseModel):
    """Contact information schema."""

    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: Optional[str] = Field(None, max_length=20)
    alt_phone: Optional[str] = Field(None, max_length=20)
    preferred_contact_method: str = Field(default="email")  # email, phone, sms

    model_config = ConfigDict(from_attributes=True)


# Service schemas
class ServiceBase(BaseModel):
    """Base service schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    service_type: ServiceType
    status: ServiceStatus = ServiceStatus.PENDING
    monthly_cost: Optional[float] = Field(None, ge=0)
    setup_cost: Optional[float] = Field(None, ge=0)


class ServiceCreate(ServiceBase):
    """Schema for creating a service."""

    customer_id: Optional[UUID] = None


class ServiceUpdate(BaseModel):
    """Schema for updating a service."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ServiceStatus] = None
    monthly_cost: Optional[float] = Field(None, ge=0)
    setup_cost: Optional[float] = Field(None, ge=0)


class ServiceResponse(ServiceBase, TenantAwareSchema):
    """Schema for service responses."""

    customer_id: Optional[UUID] = None
    activation_date: Optional[datetime] = None
    last_billing_date: Optional[datetime] = None


# Customer schemas
class CustomerBase(BaseModel):
    """Base customer schema."""

    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    status: CustomerStatus = CustomerStatus.ACTIVE


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""

    password: Optional[str] = Field(None, min_length=8)
    address: Optional[dict[str, Any]] = None


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[CustomerStatus] = None
    address: Optional[dict[str, Any]] = None


class CustomerResponse(CustomerBase, TenantAwareSchema):
    """Schema for customer responses."""

    services: list[ServiceResponse] = []
    total_monthly_cost: Optional[float] = None


# Network schemas
class NetworkDeviceBase(BaseModel):
    """Base network device schema."""

    name: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., min_length=1, max_length=100)
    ip_address: Optional[str] = Field(None, pattern=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    mac_address: Optional[str] = Field(
        None, pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
    )
    status: str = Field(default="active")


class NetworkDeviceCreate(NetworkDeviceBase):
    """Schema for creating a network device."""

    location: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None


class NetworkDeviceResponse(NetworkDeviceBase, TenantAwareSchema):
    """Schema for network device responses."""

    location: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    last_seen: Optional[datetime] = None


# Portal schemas
class PortalUserBase(BaseModel):
    """Base portal user schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    is_active: bool = True
    portal_type: str = Field(..., min_length=1, max_length=50)


class PortalUserCreate(PortalUserBase):
    """Schema for creating a portal user."""

    password: str = Field(..., min_length=8)
    permissions: list[str] = []


class PortalUserResponse(PortalUserBase, TenantAwareSchema):
    """Schema for portal user responses."""

    permissions: list[str] = []
    last_login: Optional[datetime] = None


# Analytics schemas
class AnalyticsMetric(BaseModel):
    """Analytics metric schema."""

    name: str
    value: float
    unit: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsReport(BaseModel):
    """Analytics report schema."""

    report_type: str
    metrics: list[AnalyticsMetric] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None


# Validation schemas
class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str
    message: str
    details: Optional[dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response schema."""

    success: bool = True
    message: str
    data: Optional[dict[str, Any]] = None


# Pagination schemas
class PaginationInfo(BaseModel):
    """Pagination information schema."""

    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel):
    """Base paginated response schema."""

    pagination: PaginationInfo
    items: list[Any] = []


# Health check schemas
class HealthStatus(BaseModel):
    """Health status schema."""

    status: str = "healthy"
    checks: dict[str, str] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Export all schemas
# Additional schemas for identity module compatibility
class CustomerCreateSchema(CustomerCreate):
    """Alias for identity module compatibility."""

    pass


class UserCreateSchema(BaseModel):
    """Schema for creating users."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    portal_type: str = Field(default="admin", max_length=50)
    password_hash: str = Field(..., min_length=1)
    is_active: bool = True


__all__ = [
    # Enums
    "ServiceStatus",
    "ServiceType",
    "CustomerStatus",
    # Base schemas
    "BaseSchema",
    "TenantAwareSchema",
    "TenantModelSchema",
    "AddressSchema",
    "ContactSchema",
    # Service schemas
    "ServiceBase",
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceResponse",
    # Customer schemas
    "CustomerBase",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CustomerCreateSchema",  # Added compatibility alias
    # User schemas
    "UserCreateSchema",  # Added for identity module
    # Network schemas
    "NetworkDeviceBase",
    "NetworkDeviceCreate",
    "NetworkDeviceResponse",
    # Portal schemas
    "PortalUserBase",
    "PortalUserCreate",
    "PortalUserResponse",
    # Analytics schemas
    "AnalyticsMetric",
    "AnalyticsReport",
    # Standard responses
    "ErrorResponse",
    "SuccessResponse",
    # Pagination
    "PaginationInfo",
    "PaginatedResponse",
    # Health
    "HealthStatus",
]
