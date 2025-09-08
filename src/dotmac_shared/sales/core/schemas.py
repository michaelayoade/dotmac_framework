"""Sales API schemas for requests and responses."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

try:
    from pydantic import BaseModel, ConfigDict, EmailStr, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Create minimal stubs when Pydantic is not available
    class BaseModel:
        """BaseModel implementation."""

        pass

    Field = EmailStr = ConfigDict = None

# Create independent schema base class
try:
    from dotmac.core.schemas import TenantModelSchema

    SHARED_SCHEMAS_AVAILABLE = True
except ImportError:
    SHARED_SCHEMAS_AVAILABLE = False

if not SHARED_SCHEMAS_AVAILABLE:
    # Fallback when shared schemas aren't available
    if PYDANTIC_AVAILABLE:

        class TenantModelSchema(BaseModel):
            """TenantModelSchema implementation."""

            model_config = ConfigDict(from_attributes=True, extra="allow")
            id: Optional[UUID] = None
            tenant_id: str
            created_at: datetime
            updated_at: datetime

    else:
        TenantModelSchema = BaseModel

from .models import (
    ActivityStatus,
    ActivityType,
    CustomerType,
    LeadSource,
    LeadStatus,
    OpportunityStage,
    OpportunityStatus,
)

if PYDANTIC_AVAILABLE:
    # Lead Schemas
    class LeadBase(BaseModel):
        """Base lead schema."""

        first_name: str = Field(..., min_length=1, max_length=100)
        last_name: str = Field(..., min_length=1, max_length=100)
        email: Optional[EmailStr] = None
        phone: Optional[str] = Field(None, max_length=50)
        company: Optional[str] = Field(None, max_length=200)
        job_title: Optional[str] = Field(None, max_length=100)
        lead_source: LeadSource
        customer_type: Optional[CustomerType] = None
        budget: Optional[Decimal] = Field(None, ge=0)
        authority: Optional[str] = Field(None, max_length=500)
        need: Optional[str] = Field(None, max_length=500)
        timeline: Optional[str] = Field(None, max_length=200)
        street_address: Optional[str] = Field(None, max_length=255)
        city: Optional[str] = Field(None, max_length=100)
        state_province: Optional[str] = Field(None, max_length=100)
        postal_code: Optional[str] = Field(None, max_length=20)
        country_code: Optional[str] = Field(None, max_length=3)
        notes: Optional[str] = None

    class LeadCreate(LeadBase):
        """Schema for creating leads."""

        assigned_to: Optional[str] = Field(None, max_length=100)
        sales_team: Optional[str] = Field(None, max_length=100)

    class LeadUpdate(BaseModel):
        """Schema for updating leads."""

        first_name: Optional[str] = Field(None, min_length=1, max_length=100)
        last_name: Optional[str] = Field(None, min_length=1, max_length=100)
        email: Optional[EmailStr] = None
        phone: Optional[str] = Field(None, max_length=50)
        company: Optional[str] = Field(None, max_length=200)
        job_title: Optional[str] = Field(None, max_length=100)
        lead_source: Optional[LeadSource] = None
        customer_type: Optional[CustomerType] = None
        budget: Optional[Decimal] = Field(None, ge=0)
        authority: Optional[str] = Field(None, max_length=500)
        need: Optional[str] = Field(None, max_length=500)
        timeline: Optional[str] = Field(None, max_length=200)
        assigned_to: Optional[str] = Field(None, max_length=100)
        sales_team: Optional[str] = Field(None, max_length=100)
        notes: Optional[str] = None

    class LeadQualification(BaseModel):
        """Schema for lead qualification."""

        budget: Optional[Decimal] = Field(None, ge=0)
        authority: Optional[str] = Field(None, max_length=500)
        need: Optional[str] = Field(None, max_length=500)
        timeline: Optional[str] = Field(None, max_length=200)
        qualification_notes: Optional[str] = None

    class LeadResponse(TenantModelSchema, LeadBase):
        """Schema for lead responses."""

        lead_status: LeadStatus
        lead_score: int = Field(ge=0, le=100)
        first_contact_date: Optional[date] = None
        last_contact_date: Optional[date] = None
        qualification_date: Optional[date] = None
        conversion_date: Optional[date] = None
        assigned_to: Optional[str] = None
        sales_team: Optional[str] = None
        opportunity_id: Optional[UUID] = None
        qualification_notes: Optional[str] = None

    # Opportunity Schemas
    class OpportunityBase(BaseModel):
        """Base opportunity schema."""

        opportunity_name: str = Field(..., min_length=1, max_length=200)
        account_name: str = Field(..., min_length=1, max_length=200)
        contact_name: Optional[str] = Field(None, max_length=200)
        contact_email: Optional[EmailStr] = None
        contact_phone: Optional[str] = Field(None, max_length=50)
        estimated_value: Decimal = Field(..., ge=0)
        expected_close_date: date
        customer_type: Optional[CustomerType] = None
        description: Optional[str] = None
        street_address: Optional[str] = Field(None, max_length=255)
        city: Optional[str] = Field(None, max_length=100)
        state_province: Optional[str] = Field(None, max_length=100)
        postal_code: Optional[str] = Field(None, max_length=20)
        country_code: Optional[str] = Field(None, max_length=3)

    class OpportunityCreate(OpportunityBase):
        """Schema for creating opportunities."""

        lead_id: Optional[UUID] = None
        sales_owner: str = Field(..., max_length=100)
        sales_team: Optional[str] = Field(None, max_length=100)
        opportunity_stage: Optional[OpportunityStage] = OpportunityStage.PROSPECTING
        probability: Optional[int] = Field(None, ge=0, le=100)

    class OpportunityUpdate(BaseModel):
        """Schema for updating opportunities."""

        opportunity_name: Optional[str] = Field(None, min_length=1, max_length=200)
        account_name: Optional[str] = Field(None, min_length=1, max_length=200)
        contact_name: Optional[str] = Field(None, max_length=200)
        contact_email: Optional[EmailStr] = None
        contact_phone: Optional[str] = Field(None, max_length=50)
        estimated_value: Optional[Decimal] = Field(None, ge=0)
        expected_close_date: Optional[date] = None
        customer_type: Optional[CustomerType] = None
        description: Optional[str] = None
        sales_owner: Optional[str] = Field(None, max_length=100)
        sales_team: Optional[str] = Field(None, max_length=100)
        probability: Optional[int] = Field(None, ge=0, le=100)

    class OpportunityStageUpdate(BaseModel):
        """Schema for updating opportunity stage."""

        stage: OpportunityStage
        notes: Optional[str] = Field(None, max_length=1000)

    class OpportunityClose(BaseModel):
        """Schema for closing opportunities."""

        is_won: bool
        close_reason: str = Field(..., min_length=1, max_length=500)
        notes: Optional[str] = Field(None, max_length=1000)

    class OpportunityResponse(TenantModelSchema, OpportunityBase):
        """Schema for opportunity responses."""

        lead_id: Optional[UUID] = None
        opportunity_stage: OpportunityStage
        opportunity_status: OpportunityStatus
        probability: int = Field(ge=0, le=100)
        weighted_value: Optional[Decimal] = None
        sales_owner: str
        sales_team: Optional[str] = None
        close_reason: Optional[str] = None
        stage_history: Optional[list[dict[str, Any]]] = Field(default_factory=list)

    # Sales Activity Schemas
    class SalesActivityBase(BaseModel):
        """Base sales activity schema."""

        subject: str = Field(..., min_length=1, max_length=200)
        description: Optional[str] = None
        activity_type: ActivityType
        scheduled_date: datetime
        duration_minutes: Optional[int] = Field(None, ge=0)
        location: Optional[str] = Field(None, max_length=200)

    class SalesActivityCreate(SalesActivityBase):
        """Schema for creating sales activities."""

        lead_id: Optional[UUID] = None
        opportunity_id: Optional[UUID] = None
        assigned_to: str = Field(..., max_length=100)

    class SalesActivityUpdate(BaseModel):
        """Schema for updating sales activities."""

        subject: Optional[str] = Field(None, min_length=1, max_length=200)
        description: Optional[str] = None
        activity_type: Optional[ActivityType] = None
        scheduled_date: Optional[datetime] = None
        duration_minutes: Optional[int] = Field(None, ge=0)
        location: Optional[str] = Field(None, max_length=200)
        assigned_to: Optional[str] = Field(None, max_length=100)

    class SalesActivityComplete(BaseModel):
        """Schema for completing activities."""

        outcome: str = Field(..., min_length=1, max_length=200)
        outcome_description: Optional[str] = Field(None, max_length=1000)

    class SalesActivityResponse(TenantModelSchema, SalesActivityBase):
        """Schema for sales activity responses."""

        lead_id: Optional[UUID] = None
        opportunity_id: Optional[UUID] = None
        activity_status: ActivityStatus
        assigned_to: str
        completed_date: Optional[datetime] = None
        outcome: Optional[str] = None
        outcome_description: Optional[str] = None

    # Analytics and Reporting Schemas
    class SalesDashboard(BaseModel):
        """Sales dashboard data."""

        current_month: dict[str, Any] = Field(default_factory=dict)
        current_quarter: dict[str, Any] = Field(default_factory=dict)
        current_year: dict[str, Any] = Field(default_factory=dict)
        pipeline: dict[str, Any] = Field(default_factory=dict)
        activities: dict[str, Any] = Field(default_factory=dict)
        leads: dict[str, Any] = Field(default_factory=dict)
        last_updated: str

    class SalesMetrics(BaseModel):
        """Sales performance metrics."""

        revenue: Decimal = Field(default=Decimal("0.00"))
        deals_closed: int = 0
        deals_won: int = 0
        deals_lost: int = 0
        win_rate: float = 0.0
        average_deal_size: Decimal = Field(default=Decimal("0.00"))
        sales_cycle_length: float = 0.0
        conversion_rate: float = 0.0

    class LeadConversionFunnel(BaseModel):
        """Lead conversion funnel analysis."""

        total_leads: int
        status_breakdown: dict[str, int] = Field(default_factory=dict)
        conversion_rates: dict[str, float] = Field(default_factory=dict)

    class PipelineSummary(BaseModel):
        """Sales pipeline summary."""

        total_opportunities: int = 0
        total_value: Decimal = Field(default=Decimal("0.00"))
        weighted_value: Decimal = Field(default=Decimal("0.00"))
        by_stage: dict[str, dict[str, Any]] = Field(default_factory=dict)
        by_owner: dict[str, dict[str, Any]] = Field(default_factory=dict)
        closing_this_month: dict[str, Any] = Field(default_factory=dict)
        closing_this_quarter: dict[str, Any] = Field(default_factory=dict)

    class SalesForecast(BaseModel):
        """Sales forecast data."""

        quarter: str
        pipeline: dict[str, Any] = Field(default_factory=dict)
        best_case: dict[str, Any] = Field(default_factory=dict)
        commit: dict[str, Any] = Field(default_factory=dict)

    # List Response Schemas
    class LeadListResponse(BaseModel):
        """Lead list response."""

        leads: list[LeadResponse]
        total_count: int
        new_leads: int
        qualified_leads: int
        converted_leads: int

    class OpportunityListResponse(BaseModel):
        """Opportunity list response."""

        opportunities: list[OpportunityResponse]
        total_count: int
        active_opportunities: int
        won_opportunities: int
        lost_opportunities: int
        total_pipeline_value: Decimal = Field(default=Decimal("0.00"))

    class SalesActivityListResponse(BaseModel):
        """Sales activity list response."""

        activities: list[SalesActivityResponse]
        total_count: int
        completed_activities: int
        overdue_activities: int
        upcoming_activities: int

    # Filter Schemas
    class LeadFilters(BaseModel):
        """Lead filtering options."""

        lead_source: Optional[LeadSource] = None
        lead_status: Optional[LeadStatus] = None
        customer_type: Optional[CustomerType] = None
        assigned_to: Optional[str] = None
        sales_team: Optional[str] = None
        created_from: Optional[date] = None
        created_to: Optional[date] = None
        follow_up_overdue: Optional[bool] = None

    class OpportunityFilters(BaseModel):
        """Opportunity filtering options."""

        opportunity_stage: Optional[OpportunityStage] = None
        opportunity_status: Optional[OpportunityStatus] = None
        sales_owner: Optional[str] = None
        sales_team: Optional[str] = None
        customer_type: Optional[CustomerType] = None
        close_date_from: Optional[date] = None
        close_date_to: Optional[date] = None
        min_value: Optional[Decimal] = None
        max_value: Optional[Decimal] = None
        overdue_only: bool = False

    class ActivityFilters(BaseModel):
        """Activity filtering options."""

        lead_id: Optional[UUID] = None
        opportunity_id: Optional[UUID] = None
        activity_type: Optional[ActivityType] = None
        activity_status: Optional[ActivityStatus] = None
        assigned_to: Optional[str] = None
        date_from: Optional[datetime] = None
        date_to: Optional[datetime] = None
        overdue_only: bool = False

else:
    # Create stub classes when Pydantic is not available
    LeadBase = LeadCreate = LeadUpdate = LeadResponse = None
    OpportunityBase = OpportunityCreate = OpportunityUpdate = OpportunityResponse = None
    SalesActivityBase = SalesActivityCreate = SalesActivityUpdate = SalesActivityResponse = None
    SalesDashboard = SalesMetrics = PipelineSummary = None
    LeadListResponse = OpportunityListResponse = SalesActivityListResponse = None
    LeadFilters = OpportunityFilters = ActivityFilters = None
