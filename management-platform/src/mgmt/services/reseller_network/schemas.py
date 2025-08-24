"""
Pydantic schemas for reseller network services.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator

from .models import (
    ResellerStatus, ResellerTier, OpportunityStage, QuoteStatus,
    CommissionStatus, TrainingStatus
)


# Base Schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        from_attributes = True
        use_enum_values = True


# Reseller Schemas
class ResellerBase(BaseSchema):
    """Base reseller schema."""
    company_name: str = Field(..., min_length=2, max_length=255)
    contact_name: str = Field(..., min_length=2, max_length=255)
    contact_email: EmailStr
    contact_phone: str = Field(..., min_length=10, max_length=20)
    business_address: str = Field(..., min_length=10, max_length=500)
    tax_id: Optional[str] = Field(None, max_length=50)
    website_url: Optional[str] = Field(None, max_length=255)


class ResellerCreate(ResellerBase):
    """Schema for creating a new reseller."""
    tier: ResellerTier = ResellerTier.BRONZE
    base_commission_rate: Optional[Decimal] = Field(
        Decimal("0.10"), 
        ge=Decimal("0.01"), 
        le=Decimal("0.30"),
        description="Commission rate between 1% and 30%"
    )
    
    @validator('base_commission_rate')
    def validate_commission_rate(cls, v):
        if v is not None and (v < Decimal("0.01") or v > Decimal("0.30")):
            raise ValueError('Commission rate must be between 1% and 30%')
        return v


class ResellerUpdate(BaseSchema):
    """Schema for updating reseller information."""
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    business_address: Optional[str] = Field(None, min_length=10, max_length=500)
    tax_id: Optional[str] = Field(None, max_length=50)
    website_url: Optional[str] = Field(None, max_length=255)
    base_commission_rate: Optional[Decimal] = Field(
        None, 
        ge=Decimal("0.01"), 
        le=Decimal("0.30")
    )
    notes: Optional[str] = None


class ResellerResponse(ResellerBase):
    """Schema for reseller response."""
    id: UUID
    status: ResellerStatus
    tier: ResellerTier
    base_commission_rate: Decimal
    tier_upgrade_date: Optional[datetime] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class ResellerListItem(BaseSchema):
    """Compact schema for reseller listings."""
    id: UUID
    company_name: str
    contact_name: str
    contact_email: EmailStr
    status: ResellerStatus
    tier: ResellerTier
    base_commission_rate: Decimal
    created_at: datetime


# Sales Opportunity Schemas
class SalesOpportunityBase(BaseSchema):
    """Base sales opportunity schema."""
    customer_name: str = Field(..., min_length=2, max_length=255)
    customer_contact: str = Field(..., min_length=2, max_length=255)
    customer_email: EmailStr
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_location: str = Field(..., min_length=5, max_length=255)
    opportunity_name: str = Field(..., min_length=5, max_length=255)
    estimated_value: Decimal = Field(..., gt=0, description="Estimated opportunity value")
    estimated_close_date: datetime
    probability: int = Field(..., ge=0, le=100, description="Win probability percentage")
    product_interest: str = Field(..., min_length=10, max_length=500)
    notes: Optional[str] = None


class SalesOpportunityCreate(SalesOpportunityBase):
    """Schema for creating sales opportunity."""
    pass


class SalesOpportunityUpdate(BaseSchema):
    """Schema for updating sales opportunity."""
    customer_name: Optional[str] = Field(None, min_length=2, max_length=255)
    customer_contact: Optional[str] = Field(None, min_length=2, max_length=255)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_location: Optional[str] = Field(None, min_length=5, max_length=255)
    opportunity_name: Optional[str] = Field(None, min_length=5, max_length=255)
    estimated_value: Optional[Decimal] = Field(None, gt=0)
    estimated_close_date: Optional[datetime] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    product_interest: Optional[str] = Field(None, min_length=10, max_length=500)
    notes: Optional[str] = None


class SalesOpportunityResponse(SalesOpportunityBase):
    """Schema for sales opportunity response."""
    id: UUID
    reseller_id: UUID
    stage: OpportunityStage
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# Sales Quote Schemas
class SalesQuoteBase(BaseSchema):
    """Base sales quote schema."""
    quote_name: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10, max_length=1000)
    total_value: Decimal = Field(..., gt=0, description="Total quote value")
    valid_until: datetime
    terms_conditions: str = Field(..., min_length=10, max_length=2000)


class SalesQuoteCreate(SalesQuoteBase):
    """Schema for creating sales quote."""
    pass


class SalesQuoteUpdate(BaseSchema):
    """Schema for updating sales quote."""
    quote_name: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    total_value: Optional[Decimal] = Field(None, gt=0)
    valid_until: Optional[datetime] = None
    terms_conditions: Optional[str] = Field(None, min_length=10, max_length=2000)


class SalesQuoteResponse(SalesQuoteBase):
    """Schema for sales quote response."""
    id: UUID
    opportunity_id: UUID
    quote_number: str
    status: QuoteStatus
    commission_rate: Decimal
    projected_commission: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# Commission Schemas
class CommissionRecordBase(BaseSchema):
    """Base commission record schema."""
    revenue_amount: Decimal = Field(..., gt=0, description="Revenue amount for commission calculation")
    commission_rate: Decimal = Field(..., ge=0, le=1, description="Commission rate as decimal")
    commission_amount: Decimal = Field(..., ge=0, description="Calculated commission amount")
    period_start: datetime
    period_end: datetime
    contract_id: UUID


class CommissionRecordCreate(CommissionRecordBase):
    """Schema for creating commission record."""
    pass


class CommissionRecordResponse(CommissionRecordBase):
    """Schema for commission record response."""
    id: UUID
    reseller_id: UUID
    status: CommissionStatus
    calculated_at: datetime
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


# Training Schemas
class ResellerTrainingBase(BaseSchema):
    """Base reseller training schema."""
    training_program: str = Field(..., min_length=3, max_length=255)
    required: bool = False
    due_date: Optional[datetime] = None


class ResellerTrainingCreate(ResellerTrainingBase):
    """Schema for creating reseller training."""
    pass


class ResellerTrainingUpdate(BaseSchema):
    """Schema for updating reseller training."""
    due_date: Optional[datetime] = None
    completion_notes: Optional[str] = None


class ResellerTrainingResponse(ResellerTrainingBase):
    """Schema for reseller training response."""
    id: UUID
    reseller_id: UUID
    status: TrainingStatus
    assigned_at: datetime
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    assigned_by: Optional[UUID] = None


# Territory Schemas
class TerritoryAssignmentBase(BaseSchema):
    """Base territory assignment schema."""
    territory_name: str = Field(..., min_length=3, max_length=255)
    geographic_boundaries: Dict[str, Any] = Field(..., description="Geographic boundary definitions")
    market_segments: List[str] = Field(..., description="Allowed market segments")
    exclusive: bool = False


class TerritoryAssignmentCreate(TerritoryAssignmentBase):
    """Schema for creating territory assignment."""
    pass


class TerritoryAssignmentResponse(TerritoryAssignmentBase):
    """Schema for territory assignment response."""
    id: UUID
    reseller_id: UUID
    is_active: bool
    assigned_at: datetime
    expires_at: Optional[datetime] = None
    assigned_by: Optional[UUID] = None


# Performance & Analytics Schemas
class PerformanceMetrics(BaseSchema):
    """Reseller performance metrics schema."""
    opportunities: Dict[str, Any] = Field(..., description="Opportunity metrics")
    commissions: Dict[str, Any] = Field(..., description="Commission metrics")
    training: Dict[str, Any] = Field(..., description="Training completion metrics")


class ResellerDashboard(BaseSchema):
    """Comprehensive reseller dashboard data."""
    reseller_info: ResellerResponse
    performance_metrics: PerformanceMetrics
    active_opportunities: List[SalesOpportunityResponse]
    recent_quotes: List[SalesQuoteResponse]
    pending_commissions: List[CommissionRecordResponse]
    training_progress: List[ResellerTrainingResponse]


# List Response Schemas
class ResellerListResponse(BaseSchema):
    """Paginated reseller list response."""
    resellers: List[ResellerListItem]
    total: int
    page: int
    per_page: int
    pages: int


class OpportunityListResponse(BaseSchema):
    """Paginated opportunity list response."""
    opportunities: List[SalesOpportunityResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CommissionListResponse(BaseSchema):
    """Paginated commission list response."""
    commissions: List[CommissionRecordResponse]
    total: int
    page: int
    per_page: int
    pages: int


# Status Update Schemas
class ResellerStatusUpdate(BaseSchema):
    """Schema for updating reseller status."""
    status: ResellerStatus
    notes: Optional[str] = None


class OpportunityStageUpdate(BaseSchema):
    """Schema for updating opportunity stage."""
    stage: OpportunityStage
    notes: Optional[str] = None


class TierUpgradeRequest(BaseSchema):
    """Schema for tier upgrade request."""
    new_tier: ResellerTier
    justification: str = Field(..., min_length=20, max_length=1000)


# Bulk Operations Schemas
class BulkCommissionApproval(BaseSchema):
    """Schema for bulk commission approval."""
    commission_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    approval_notes: Optional[str] = None


class BulkTrainingAssignment(BaseSchema):
    """Schema for bulk training assignment."""
    reseller_ids: List[UUID] = Field(..., min_items=1, max_items=50)
    training_program: str = Field(..., min_length=3, max_length=255)
    required: bool = False
    due_date: Optional[datetime] = None