"""
Pydantic schemas for ISP reseller operations.
These schemas interface with the shared reseller models.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from dotmac_shared.api.exception_handlers import standard_exception_handler


# Enums (matching shared reseller models)
class ResellerTypeEnum(str, Enum):
    """ResellerTypeEnum implementation."""

    PARTNER = "PARTNER"
    DISTRIBUTOR = "DISTRIBUTOR"
    AGENT = "AGENT"
    AFFILIATE = "AFFILIATE"


class ResellerTierEnum(str, Enum):
    """ResellerTierEnum implementation."""

    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class CommissionStatusEnum(str, Enum):
    """CommissionStatusEnum implementation."""

    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class ResellerStatusEnum(str, Enum):
    """ResellerStatusEnum implementation."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


# Request schemas
class ResellerCreate(BaseModel):
    """Schema for creating new resellers."""

    company_name: str = Field(..., min_length=1, max_length=200)
    reseller_type: ResellerTypeEnum
    reseller_tier: ResellerTierEnum = ResellerTierEnum.BRONZE
    commission_rate: Decimal = Field(..., ge=0, le=1)

    # Contact information
    contact_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_person: str = Field(..., min_length=1, max_length=100)

    # Address information
    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)

    # Contract information
    contract_start_date: str = Field(..., description="ISO format datetime")
    contract_end_date: Optional[str] = Field(None, description="ISO format datetime")

    # Business information
    territories: List[str] = Field(default_factory=list)

    # Performance and targets
    performance_targets: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("contract_start_date")
    @classmethod
    def validate_start_date(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("contract_start_date must be valid ISO format datetime")

    @field_validator("contract_end_date")
    @classmethod
    def validate_end_date(cls, v):
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("contract_end_date must be valid ISO format datetime")

    model_config = ConfigDict(json_encoders={Decimal: str})


class ResellerUpdate(BaseModel):
    """Schema for updating reseller information."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    reseller_type: Optional[ResellerTypeEnum] = None
    reseller_tier: Optional[ResellerTierEnum] = None
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)

    contact_email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_person: Optional[str] = Field(None, max_length=100)

    billing_address: Optional[str] = Field(None, max_length=500)
    shipping_address: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)

    territories: Optional[List[str]] = None
    performance_targets: Optional[Dict[str, Any]] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(json_encoders={Decimal: str})


class ResellerOpportunityCreate(BaseModel):
    """Schema for assigning an opportunity to a reseller."""

    opportunity_id: str = Field(..., min_length=1)
    commission_override: Optional[Decimal] = Field(None, ge=0, le=1)
    notes: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(json_encoders={Decimal: str})


class CommissionCalculation(BaseModel):
    """Schema for commission calculation requests."""

    reseller_id: str = Field(..., min_length=1)
    sale_amount: Decimal = Field(..., gt=0)
    commission_override: Optional[Decimal] = Field(None, ge=0, le=1)

    model_config = ConfigDict(json_encoders={Decimal: str})


class CommissionRecord(BaseModel):
    """Schema for recording commissions."""

    reseller_id: str = Field(..., min_length=1)
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    sale_amount: Decimal = Field(..., gt=0)
    commission_rate: Decimal = Field(..., ge=0, le=1)
    commission_amount: Decimal = Field(..., ge=0)

    model_config = ConfigDict(json_encoders={Decimal: str})


# Response schemas
class ResellerResponse(BaseModel):
    """Schema for reseller response."""

    reseller_id: str
    tenant_id: str
    company_name: str
    reseller_type: str
    reseller_tier: str
    commission_rate: float
    
    contact_email: str
    contact_phone: Optional[str]
    contact_person: str
    
    billing_address: Optional[str]
    shipping_address: Optional[str]
    website: Optional[str]

    territories: List[str]
    status: str

    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ResellerOpportunityResponse(BaseModel):
    """Schema for reseller opportunity response."""

    reseller_opportunity_id: str
    tenant_id: str
    reseller_id: str
    opportunity_id: str
    assigned_date: str
    commission_override: Optional[float]
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class CommissionResponse(BaseModel):
    """Schema for commission response."""

    commission_id: str
    tenant_id: str
    reseller_id: str
    sale_amount: float
    commission_amount: float
    payment_status: str
    calculated_date: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class CommissionCalculationResponse(BaseModel):
    """Schema for commission calculation response."""

    reseller_id: str
    sale_amount: float
    commission_rate: float
    commission_amount: float
    calculated_at: str

    model_config = ConfigDict(from_attributes=True)


class ResellerPerformanceResponse(BaseModel):
    """Schema for reseller performance metrics."""

    reseller_id: str
    tenant_id: str
    period_start: Optional[str]
    period_end: Optional[str]
    metrics: Dict[str, Any]
    calculated_at: str

    model_config = ConfigDict(from_attributes=True)


class ResellerListResponse(BaseModel):
    """Schema for paginated reseller list."""

    resellers: List[ResellerResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)


# Health check schema
class ResellerHealthResponse(BaseModel):
    """Schema for reseller service health check."""

    reseller_service: str
    tenant_id: str
    user_service: Optional[str]
    cache_service: Optional[Dict[str, Any]]
    event_bus: str
    timestamp: str

    model_config = ConfigDict(from_attributes=True)