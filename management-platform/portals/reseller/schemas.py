"""
Pydantic schemas for Reseller Portal API requests and responses.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
from uuid import UUID
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class OpportunityStage(str, Enum):
    """Sales opportunity stages."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class CustomerHealthStatus(str, Enum):
    """Customer health status levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class CommissionStatus(str, Enum):
    """Commission payment status."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class SalesMetrics(BaseModel):
    """Sales performance metrics for reseller dashboard."""
    
    # Current period metrics
    monthly_sales: int = Field(..., ge=0, description="Sales closed this month")
    quarterly_sales: int = Field(..., ge=0, description="Sales closed this quarter")
    yearly_sales: int = Field(..., ge=0, description="Sales closed this year")
    
    # Revenue metrics
    monthly_revenue: Decimal = Field(..., ge=0, description="Revenue generated this month")
    quarterly_revenue: Decimal = Field(..., ge=0, description="Revenue generated this quarter")
    yearly_revenue: Decimal = Field(..., ge=0, description="Revenue generated this year")
    
    # Pipeline metrics
    pipeline_value: Decimal = Field(..., ge=0, description="Total pipeline value")
    weighted_pipeline: Decimal = Field(..., ge=0, description="Weighted pipeline value")
    
    # Performance indicators
    conversion_rate: float = Field(..., ge=0, le=1, description="Lead to customer conversion rate")
    avg_deal_size: Decimal = Field(..., ge=0, description="Average deal size")
    sales_cycle_days: int = Field(..., ge=0, description="Average sales cycle in days")
    
    # Targets
    monthly_target: Decimal = Field(..., ge=0, description="Monthly sales target")
    quarterly_target: Decimal = Field(..., ge=0, description="Quarterly sales target")
    yearly_target: Decimal = Field(..., ge=0, description="Yearly sales target")
    
    # Achievement rates
    monthly_achievement: float = Field(..., ge=0, description="Monthly target achievement rate")
    quarterly_achievement: float = Field(..., ge=0, description="Quarterly target achievement rate")
    yearly_achievement: float = Field(..., ge=0, description="Yearly target achievement rate")


class CommissionMetrics(BaseModel):
    """Commission earnings and tracking metrics."""
    
    # Current earnings
    total_earned: Decimal = Field(..., ge=0, description="Total commissions earned")
    monthly_earned: Decimal = Field(..., ge=0, description="Commissions earned this month")
    quarterly_earned: Decimal = Field(..., ge=0, description="Commissions earned this quarter")
    yearly_earned: Decimal = Field(..., ge=0, description="Commissions earned this year")
    
    # Pending commissions
    pending_amount: Decimal = Field(..., ge=0, description="Pending commission amount")
    next_payout_date: date = Field(..., description="Next commission payout date")
    
    # Commission rates
    base_commission_rate: float = Field(..., ge=0, le=1, description="Base commission rate")
    current_tier_rate: float = Field(..., ge=0, le=1, description="Current tier commission rate")
    
    # Recurring revenue tracking
    monthly_recurring_commission: Decimal = Field(..., ge=0, description="Monthly recurring commission")
    recurring_revenue_base: Decimal = Field(..., ge=0, description="Total recurring revenue base")
    
    # Performance bonuses
    bonus_earned: Decimal = Field(..., ge=0, description="Performance bonuses earned")
    bonus_eligible: bool = Field(..., description="Whether eligible for bonuses")


class TerritoryMetrics(BaseModel):
    """Territory performance metrics."""
    
    territory_name: str
    territory_type: str = Field(..., regex="^(geographic|industry|account_size)$")
    
    # Market size
    total_addressable_market: int = Field(..., ge=0, description="Total prospects in territory")
    market_penetration: float = Field(..., ge=0, le=1, description="Market penetration rate")
    
    # Customer metrics
    active_customers: int = Field(..., ge=0, description="Active customers in territory")
    churned_customers: int = Field(..., ge=0, description="Churned customers this period")
    
    # Competitive landscape
    market_share: float = Field(..., ge=0, le=1, description="Estimated market share")
    key_competitors: List[str] = Field(default_factory=list, description="Key competitors")
    competitive_threats: int = Field(..., ge=0, description="Active competitive threats")


class ResellerDashboardOverview(BaseModel):
    """Complete reseller dashboard overview."""
    
    # Reseller identification
    reseller_id: str
    reseller_name: str
    territory: str
    
    # Performance metrics
    sales_metrics: SalesMetrics
    commission_metrics: CommissionMetrics
    territory_metrics: TerritoryMetrics
    
    # Recent activity
    recent_opportunities: int = Field(..., ge=0, description="New opportunities this week")
    recent_customers: int = Field(..., ge=0, description="New customers this week")
    recent_quotes: int = Field(..., ge=0, description="Quotes generated this week")
    
    # Alerts and notifications
    quota_achievement: float = Field(..., ge=0, description="Quota achievement percentage")
    at_risk_customers: int = Field(..., ge=0, description="Number of at-risk customers")
    expiring_quotes: int = Field(..., ge=0, description="Number of expiring quotes")
    
    # Training and certification
    certification_level: str = Field(..., regex="^(bronze|silver|gold|platinum)$")
    training_completion: float = Field(..., ge=0, le=1, description="Training completion percentage")
    
    generated_at: datetime


class ProspectContact(BaseModel):
    """Prospect contact information."""
    
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=100)
    linkedin_url: Optional[str] = None
    
    # Relationship
    is_primary: bool = Field(True, description="Primary contact for this prospect")
    is_decision_maker: bool = Field(False, description="Has decision-making authority")
    influence_level: str = Field("medium", regex="^(low|medium|high)$")


class SalesOpportunity(BaseModel):
    """Sales opportunity tracking."""
    
    # Opportunity identification
    opportunity_id: str
    prospect_company: str
    prospect_website: Optional[str] = None
    
    # Contact information
    contacts: List[ProspectContact] = Field(min_items=1, description="Prospect contacts")
    
    # Opportunity details
    opportunity_name: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    industry: str
    company_size: str = Field(..., regex="^(startup|small|medium|enterprise)$")
    
    # Sales process
    stage: OpportunityStage
    probability: int = Field(..., ge=0, le=100, description="Close probability percentage")
    
    # Financial details
    estimated_value: Decimal = Field(..., ge=0, description="Estimated deal value")
    monthly_recurring_revenue: Decimal = Field(..., ge=0, description="Estimated MRR")
    
    # Timeline
    created_date: datetime
    last_activity_date: datetime
    expected_close_date: date
    
    # Requirements
    required_features: List[str] = Field(default_factory=list)
    technical_requirements: Dict[str, Any] = Field(default_factory=dict)
    compliance_requirements: List[str] = Field(default_factory=list)
    
    # Competitive information
    competing_vendors: List[str] = Field(default_factory=list)
    competitive_advantages: List[str] = Field(default_factory=list)
    
    # Internal tracking
    assigned_to: str = Field(..., description="Assigned sales rep")
    lead_source: str
    tags: List[str] = Field(default_factory=list)
    
    # Activity tracking
    last_contact_date: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    notes: Optional[str] = None


class SalesOpportunityCreate(BaseModel):
    """Create new sales opportunity."""
    
    prospect_company: str = Field(..., min_length=1, max_length=200)
    prospect_website: Optional[str] = None
    
    # Primary contact (additional contacts can be added later)
    contact_first_name: str = Field(..., min_length=1, max_length=50)
    contact_last_name: str = Field(..., min_length=1, max_length=50)
    contact_email: EmailStr
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_title: Optional[str] = Field(None, max_length=100)
    
    # Opportunity details
    opportunity_name: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    industry: str
    company_size: str = Field(..., regex="^(startup|small|medium|enterprise)$")
    
    # Initial estimates
    estimated_value: Decimal = Field(..., ge=0)
    expected_close_date: date
    
    # Additional information
    lead_source: str
    initial_requirements: Optional[str] = None
    competing_vendors: List[str] = Field(default_factory=list)


class SalesOpportunityUpdate(BaseModel):
    """Update sales opportunity."""
    
    stage: Optional[OpportunityStage] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    estimated_value: Optional[Decimal] = Field(None, ge=0)
    expected_close_date: Optional[date] = None
    
    # Activity updates
    last_activity_note: Optional[str] = None
    next_follow_up: Optional[datetime] = None
    
    # Requirements updates
    required_features: Optional[List[str]] = None
    technical_requirements: Optional[Dict[str, Any]] = None
    
    # Competitive updates
    competing_vendors: Optional[List[str]] = None
    competitive_advantages: Optional[List[str]] = None


class SalesQuoteLineItem(BaseModel):
    """Sales quote line item."""
    
    product_name: str
    description: str
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_percentage: float = Field(0, ge=0, le=100)
    total_amount: Decimal = Field(..., ge=0)
    
    # Subscription details
    billing_frequency: str = Field("monthly", regex="^(monthly|quarterly|annual)$")
    subscription_term_months: int = Field(12, ge=1, le=60)


class SalesQuote(BaseModel):
    """Sales quote generation."""
    
    quote_id: str
    opportunity_id: str
    quote_number: str
    
    # Customer information
    customer_company: str
    customer_contact: ProspectContact
    
    # Quote details
    quote_date: date
    expiration_date: date
    
    # Line items
    line_items: List[SalesQuoteLineItem] = Field(min_items=1)
    
    # Pricing
    subtotal: Decimal = Field(..., ge=0)
    discount_amount: Decimal = Field(0, ge=0)
    tax_rate: float = Field(0, ge=0, le=1)
    tax_amount: Decimal = Field(0, ge=0)
    total_amount: Decimal = Field(..., ge=0)
    
    # Terms
    payment_terms: str = Field("Net 30", description="Payment terms")
    delivery_terms: str = Field("Standard deployment", description="Delivery terms")
    
    # Additional information
    notes: Optional[str] = None
    terms_and_conditions: str
    
    # Status tracking
    status: str = Field("draft", regex="^(draft|sent|viewed|accepted|rejected|expired)$")
    sent_date: Optional[datetime] = None
    viewed_date: Optional[datetime] = None
    
    # Commission information
    estimated_commission: Decimal = Field(..., ge=0)
    commission_rate: float = Field(..., ge=0, le=1)


class CommissionRecord(BaseModel):
    """Commission record for tracking earnings."""
    
    commission_id: str
    opportunity_id: str
    customer_id: str
    
    # Commission details
    commission_type: str = Field(..., regex="^(initial|recurring|bonus|override)$")
    commission_period: str = Field(..., regex="^(monthly|quarterly|annual|one_time)$")
    
    # Financial details
    base_amount: Decimal = Field(..., ge=0, description="Base amount for commission calculation")
    commission_rate: float = Field(..., ge=0, le=1, description="Commission rate applied")
    commission_amount: Decimal = Field(..., ge=0, description="Commission amount earned")
    
    # Dates
    earned_date: date = Field(..., description="Date commission was earned")
    payment_date: Optional[date] = None
    
    # Status
    status: CommissionStatus
    payment_reference: Optional[str] = None
    
    # Metadata
    notes: Optional[str] = None


class CommissionSummary(BaseModel):
    """Commission summary and earnings report."""
    
    # Summary period
    period_start: date
    period_end: date
    
    # Commission totals
    total_commissions: List[CommissionRecord]
    
    # Summary amounts
    total_earned: Decimal = Field(..., ge=0)
    total_paid: Decimal = Field(..., ge=0)
    total_pending: Decimal = Field(..., ge=0)
    
    # Breakdown by type
    initial_commissions: Decimal = Field(..., ge=0)
    recurring_commissions: Decimal = Field(..., ge=0)
    bonus_commissions: Decimal = Field(..., ge=0)
    
    # Payment schedule
    next_payout_date: date
    next_payout_amount: Decimal = Field(..., ge=0)
    
    # Performance metrics
    commission_growth_rate: float = Field(..., description="Commission growth rate vs previous period")
    recurring_percentage: float = Field(..., ge=0, le=1, description="Percentage of recurring commissions")


class CustomerHealthScore(BaseModel):
    """Customer health scoring for expansion opportunities."""
    
    customer_id: str
    customer_name: str
    
    # Health metrics
    health_status: CustomerHealthStatus
    health_score: int = Field(..., ge=0, le=100, description="Overall health score")
    
    # Usage indicators
    usage_trend: str = Field(..., regex="^(increasing|stable|decreasing)$")
    feature_adoption_rate: float = Field(..., ge=0, le=1, description="Feature adoption rate")
    support_ticket_frequency: int = Field(..., ge=0, description="Support tickets per month")
    
    # Financial indicators  
    payment_history: str = Field(..., regex="^(excellent|good|concerning|poor)$")
    contract_value: Decimal = Field(..., ge=0, description="Current contract value")
    
    # Relationship indicators
    engagement_level: str = Field(..., regex="^(high|medium|low)$")
    stakeholder_satisfaction: int = Field(..., ge=1, le=5, description="Stakeholder satisfaction rating")
    
    # Expansion opportunities
    upsell_potential: str = Field(..., regex="^(high|medium|low|none)$")
    recommended_products: List[str] = Field(default_factory=list)
    estimated_expansion_value: Decimal = Field(..., ge=0)
    
    # Risk factors
    churn_risk: str = Field(..., regex="^(low|medium|high|critical)$")
    risk_factors: List[str] = Field(default_factory=list)
    risk_mitigation_actions: List[str] = Field(default_factory=list)
    
    # Timeline
    last_updated: datetime
    next_review_date: date


class TerritoryPerformance(BaseModel):
    """Territory performance analysis."""
    
    territory_id: str
    territory_name: str
    territory_type: str
    
    # Geographic boundaries (if applicable)
    geographic_boundaries: Optional[Dict[str, Any]] = None
    
    # Market analysis
    total_addressable_market: int = Field(..., ge=0)
    serviceable_addressable_market: int = Field(..., ge=0)
    market_penetration: float = Field(..., ge=0, le=1)
    
    # Performance metrics
    active_customers: int = Field(..., ge=0)
    pipeline_opportunities: int = Field(..., ge=0)
    closed_deals_ytd: int = Field(..., ge=0)
    revenue_ytd: Decimal = Field(..., ge=0)
    
    # Competitive analysis
    market_share: float = Field(..., ge=0, le=1)
    primary_competitors: List[str] = Field(default_factory=list)
    competitive_win_rate: float = Field(..., ge=0, le=1)
    
    # Trends
    growth_rate: float = Field(..., description="Year-over-year growth rate")
    seasonality_factors: Dict[str, float] = Field(default_factory=dict)
    
    # Opportunities
    expansion_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    market_gaps: List[str] = Field(default_factory=list)


class TrainingModule(BaseModel):
    """Training module for reseller certification."""
    
    module_id: str
    module_name: str
    description: str
    category: str
    
    # Content details
    duration_minutes: int = Field(..., ge=1)
    difficulty_level: str = Field(..., regex="^(beginner|intermediate|advanced)$")
    prerequisites: List[str] = Field(default_factory=list)
    
    # Completion tracking
    is_completed: bool = False
    completion_date: Optional[datetime] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    
    # Content access
    content_url: str
    materials: List[Dict[str, str]] = Field(default_factory=list)
    
    # Certification requirements
    required_for_certification: bool = False
    certification_level: Optional[str] = Field(None, regex="^(bronze|silver|gold|platinum)$")


class CertificationProgress(BaseModel):
    """Reseller certification progress tracking."""
    
    reseller_id: str
    current_level: str = Field(..., regex="^(none|bronze|silver|gold|platinum)$")
    
    # Progress tracking
    total_modules: int = Field(..., ge=0)
    completed_modules: int = Field(..., ge=0)
    completion_percentage: float = Field(..., ge=0, le=1)
    
    # Level requirements
    next_level: Optional[str] = Field(None, regex="^(bronze|silver|gold|platinum)$")
    next_level_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    # Module progress
    modules: List[TrainingModule]
    
    # Certification dates
    last_certification_date: Optional[datetime] = None
    certification_expiry_date: Optional[datetime] = None
    
    # Benefits
    current_benefits: List[str] = Field(default_factory=list)
    next_level_benefits: List[str] = Field(default_factory=list)