"""Sales API schemas for requests and responses."""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from dotmac_isp.shared.schemas import TenantModelSchema
from .models import (
    LeadSource,
    LeadStatus,
    OpportunityStage,
    OpportunityStatus,
    ActivityType,
    ActivityStatus,
    QuoteStatus,
    CustomerType,
)


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
    stage_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


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


# Campaign Schemas (for future implementation)
class CampaignBase(BaseModel):
    """Base campaign schema."""

    campaign_name: str = Field(..., min_length=1, max_length=200)
    campaign_type: str = Field(..., max_length=50)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    target_audience: Optional[str] = Field(None, max_length=500)


class CampaignCreate(CampaignBase):
    """Schema for creating campaigns."""

    owner: str = Field(..., max_length=100)


class CampaignUpdate(BaseModel):
    """Schema for updating campaigns."""

    campaign_name: Optional[str] = Field(None, min_length=1, max_length=200)
    campaign_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    target_audience: Optional[str] = Field(None, max_length=500)
    owner: Optional[str] = Field(None, max_length=100)


class CampaignResponse(TenantModelSchema, CampaignBase):
    """Schema for campaign responses."""

    campaign_status: str
    owner: str
    total_leads: int = 0
    qualified_leads: int = 0
    converted_leads: int = 0
    total_cost: Optional[Decimal] = None
    cost_per_lead: Optional[Decimal] = None
    roi: Optional[float] = None


# Analytics and Reporting Schemas
class SalesDashboard(BaseModel):
    """Sales dashboard data."""

    current_month: Dict[str, Any] = Field(default_factory=dict)
    current_quarter: Dict[str, Any] = Field(default_factory=dict)
    current_year: Dict[str, Any] = Field(default_factory=dict)
    pipeline: Dict[str, Any] = Field(default_factory=dict)
    activities: Dict[str, Any] = Field(default_factory=dict)
    leads: Dict[str, Any] = Field(default_factory=dict)
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
    status_breakdown: Dict[str, int] = Field(default_factory=dict)
    conversion_rates: Dict[str, float] = Field(default_factory=dict)


class PipelineSummary(BaseModel):
    """Sales pipeline summary."""

    total_opportunities: int = 0
    total_value: Decimal = Field(default=Decimal("0.00"))
    weighted_value: Decimal = Field(default=Decimal("0.00"))
    by_stage: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_owner: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    closing_this_month: Dict[str, Any] = Field(default_factory=dict)
    closing_this_quarter: Dict[str, Any] = Field(default_factory=dict)


class SalesForecast(BaseModel):
    """Sales forecast data."""

    quarter: str
    pipeline: Dict[str, Any] = Field(default_factory=dict)
    best_case: Dict[str, Any] = Field(default_factory=dict)
    commit: Dict[str, Any] = Field(default_factory=dict)


# List Response Schemas
class LeadListResponse(BaseModel):
    """Lead list response."""

    leads: List[LeadResponse]
    total_count: int
    new_leads: int
    qualified_leads: int
    converted_leads: int


class OpportunityListResponse(BaseModel):
    """Opportunity list response."""

    opportunities: List[OpportunityResponse]
    total_count: int
    active_opportunities: int
    won_opportunities: int
    lost_opportunities: int
    total_pipeline_value: Decimal = Field(default=Decimal("0.00"))


class SalesActivityListResponse(BaseModel):
    """Sales activity list response."""

    activities: List[SalesActivityResponse]
    total_count: int
    completed_activities: int
    overdue_activities: int
    upcoming_activities: int


class CampaignListResponse(BaseModel):
    """Campaign list response."""

    campaigns: List[CampaignResponse]
    total_count: int
    active_campaigns: int
    completed_campaigns: int


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
