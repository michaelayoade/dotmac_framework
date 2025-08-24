"""Sales models for pipeline management, lead tracking, and sales performance."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Integer,
    Float,
    Numeric,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin
from dotmac_isp.shared.models import ContactMixin, AddressMixin


class LeadSource(str, Enum):
    """Lead source types."""

    WEBSITE = "website"
    REFERRAL = "referral"
    COLD_CALL = "cold_call"
    EMAIL_CAMPAIGN = "email_campaign"
    SOCIAL_MEDIA = "social_media"
    EVENT = "event"
    TRADE_SHOW = "trade_show"
    ADVERTISEMENT = "advertisement"
    PARTNER = "partner"
    EXISTING_CUSTOMER = "existing_customer"
    OTHER = "other"


class LeadStatus(str, Enum):
    """Lead status."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"
    LOST = "lost"
    DUPLICATE = "duplicate"


class OpportunityStage(str, Enum):
    """Opportunity sales stages."""

    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OpportunityStatus(str, Enum):
    """Opportunity status."""

    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class ActivityType(str, Enum):
    """Sales activity types."""

    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    DEMO = "demo"
    PRESENTATION = "presentation"
    PROPOSAL = "proposal"
    FOLLOW_UP = "follow_up"
    SITE_VISIT = "site_visit"
    CONTRACT_REVIEW = "contract_review"
    OTHER = "other"


class ActivityStatus(str, Enum):
    """Activity status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class QuoteStatus(str, Enum):
    """Quote status."""

    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVISED = "revised"


class CustomerType(str, Enum):
    """Customer types."""

    RESIDENTIAL = "residential"
    SMALL_BUSINESS = "small_business"
    MEDIUM_BUSINESS = "medium_business"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    NON_PROFIT = "non_profit"


class Lead(TenantModel, StatusMixin, AuditMixin, ContactMixin, AddressMixin):
    """Sales leads and prospects."""

    __tablename__ = "sales_leads"

    # Lead identification
    lead_id = Column(String(100), nullable=False, unique=True, index=True)

    # Personal/company information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(300), nullable=True)
    job_title = Column(String(200), nullable=True)

    # Lead classification
    lead_source = Column(SQLEnum(LeadSource), nullable=False, index=True)
    lead_status = Column(
        SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True
    )
    customer_type = Column(SQLEnum(CustomerType), nullable=True, index=True)

    # Qualification
    budget = Column(Numeric(12, 2), nullable=True)
    authority = Column(String(200), nullable=True)  # Decision maker info
    need = Column(Text, nullable=True)
    timeline = Column(String(100), nullable=True)

    # Interest and requirements
    products_interested = Column(JSON, nullable=True)
    service_requirements = Column(Text, nullable=True)
    pain_points = Column(Text, nullable=True)

    # Source details
    source_campaign = Column(String(200), nullable=True)
    source_medium = Column(String(100), nullable=True)
    source_details = Column(JSON, nullable=True)
    referral_source = Column(String(200), nullable=True)

    # Assignment and ownership
    assigned_to = Column(String(200), nullable=True, index=True)
    sales_team = Column(String(100), nullable=True)

    # Engagement tracking
    first_contact_date = Column(Date, nullable=True)
    last_contact_date = Column(Date, nullable=True)
    next_follow_up_date = Column(Date, nullable=True)
    contact_attempts = Column(Integer, default=0, nullable=False)

    # Scoring and qualification
    lead_score = Column(Integer, default=0, nullable=False)
    qualification_notes = Column(Text, nullable=True)

    # Conversion tracking
    converted_date = Column(Date, nullable=True)
    opportunity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Additional information
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    activities = relationship(
        "SalesActivity", foreign_keys="[SalesActivity.lead_id]", back_populates="lead"
    )

    __table_args__ = (
        Index("ix_leads_source_status", "lead_source", "lead_status"),
        Index("ix_leads_assigned_to", "assigned_to"),
        Index("ix_leads_next_follow_up", "next_follow_up_date"),
    )

    @hybrid_property
    def full_name(self) -> str:
        """Get lead's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or "Unknown"

    @hybrid_property
    def days_since_creation(self) -> int:
        """Calculate days since lead was created."""
        return (date.today() - self.created_at.date()).days

    @hybrid_property
    def is_overdue_follow_up(self) -> bool:
        """Check if lead is overdue for follow-up."""
        return self.next_follow_up_date and date.today() > self.next_follow_up_date

    def __repr__(self):
        """  Repr   operation."""
        return f"<Lead(id='{self.lead_id}', name='{self.full_name}', status='{self.lead_status}')>"


class Opportunity(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Sales opportunities and deals."""

    __tablename__ = "sales_opportunities"

    # Opportunity identification
    opportunity_id = Column(String(100), nullable=False, unique=True, index=True)
    opportunity_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Customer information
    lead_id = Column(
        UUID(as_uuid=True), ForeignKey("sales_leads.id"), nullable=True, index=True
    )
    customer_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # If existing customer
    account_name = Column(String(300), nullable=False)
    contact_name = Column(String(200), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)

    # Opportunity details
    customer_type = Column(SQLEnum(CustomerType), nullable=False, index=True)
    opportunity_stage = Column(
        SQLEnum(OpportunityStage),
        default=OpportunityStage.PROSPECTING,
        nullable=False,
        index=True,
    )
    opportunity_status = Column(
        SQLEnum(OpportunityStatus),
        default=OpportunityStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Financial details
    estimated_value = Column(Numeric(12, 2), nullable=False)
    weighted_value = Column(Numeric(12, 2), nullable=True)
    probability = Column(Integer, default=10, nullable=False)  # 0-100 percentage
    currency = Column(String(3), default="USD", nullable=False)

    # Products and services
    products = Column(JSON, nullable=True)
    services = Column(JSON, nullable=True)
    solution_summary = Column(Text, nullable=True)

    # Timeline
    created_date = Column(Date, nullable=False, default=date.today)
    expected_close_date = Column(Date, nullable=False, index=True)
    actual_close_date = Column(Date, nullable=True)
    sales_cycle_days = Column(Integer, nullable=True)

    # Assignment
    sales_owner = Column(String(200), nullable=False, index=True)
    sales_team = Column(String(100), nullable=True)
    sales_engineer = Column(String(200), nullable=True)

    # Competition and positioning
    competitors = Column(JSON, nullable=True)
    competitive_threats = Column(Text, nullable=True)
    our_advantages = Column(Text, nullable=True)

    # Qualification (BANT)
    budget_confirmed = Column(Boolean, default=False, nullable=False)
    authority_identified = Column(Boolean, default=False, nullable=False)
    need_established = Column(Boolean, default=False, nullable=False)
    timeline_established = Column(Boolean, default=False, nullable=False)

    # Decision process
    decision_makers = Column(JSON, nullable=True)
    decision_criteria = Column(JSON, nullable=True)
    decision_process = Column(Text, nullable=True)

    # Forecasting
    forecast_category = Column(
        String(50), nullable=True
    )  # pipeline, best_case, commit, closed
    forecast_quarter = Column(String(20), nullable=True)
    next_steps = Column(Text, nullable=True)

    # Win/Loss tracking
    close_reason = Column(String(200), nullable=True)
    won_reasons = Column(JSON, nullable=True)
    lost_reasons = Column(JSON, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    # Additional information
    special_terms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    lead = relationship("Lead")
    activities = relationship(
        "SalesActivity",
        foreign_keys="[SalesActivity.opportunity_id]",
        back_populates="opportunity",
    )
    quotes = relationship(
        "Quote", back_populates="opportunity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_opportunities_stage_status", "opportunity_stage", "opportunity_status"
        ),
        Index(
            "ix_opportunities_owner_close_date", "sales_owner", "expected_close_date"
        ),
        Index("ix_opportunities_value", "estimated_value"),
    )

    @hybrid_property
    def is_won(self) -> bool:
        """Check if opportunity is won."""
        return self.opportunity_status == OpportunityStatus.WON

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if opportunity is overdue."""
        return (
            self.opportunity_status == OpportunityStatus.ACTIVE
            and date.today() > self.expected_close_date
        )

    @hybrid_property
    def age_days(self) -> int:
        """Calculate opportunity age in days."""
        return (date.today() - self.created_date).days

    def __repr__(self):
        """  Repr   operation."""
        return f"<Opportunity(id='{self.opportunity_id}', name='{self.opportunity_name}', stage='{self.opportunity_stage}')>"


class SalesActivity(TenantModel, AuditMixin):
    """Sales activities and interactions."""

    __tablename__ = "sales_activities"

    # Activity identification
    activity_id = Column(String(100), nullable=False, unique=True, index=True)
    subject = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # References
    lead_id = Column(
        UUID(as_uuid=True), ForeignKey("sales_leads.id"), nullable=True, index=True
    )
    opportunity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sales_opportunities.id"),
        nullable=True,
        index=True,
    )
    contact_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Activity details
    activity_type = Column(SQLEnum(ActivityType), nullable=False, index=True)
    activity_status = Column(
        SQLEnum(ActivityStatus),
        default=ActivityStatus.PLANNED,
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=True)
    location = Column(String(500), nullable=True)

    # Completion
    completed_date = Column(DateTime, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Participants
    assigned_to = Column(String(200), nullable=False, index=True)
    attendees = Column(JSON, nullable=True)
    customer_contacts = Column(JSON, nullable=True)

    # Results and outcomes
    outcome = Column(String(100), nullable=True)
    outcome_description = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(Date, nullable=True)

    # Content and materials
    presentation_used = Column(String(500), nullable=True)
    documents_shared = Column(JSON, nullable=True)
    materials_requested = Column(JSON, nullable=True)

    # Scoring and qualification
    engagement_score = Column(Integer, nullable=True)  # 1-5 rating
    buying_interest = Column(Integer, nullable=True)  # 1-5 rating
    decision_timeline = Column(String(100), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    lead = relationship("Lead", foreign_keys=[lead_id], back_populates="activities")
    opportunity = relationship(
        "Opportunity", foreign_keys=[opportunity_id], back_populates="activities"
    )

    __table_args__ = (
        Index("ix_activities_type_date", "activity_type", "scheduled_date"),
        Index("ix_activities_assigned_to", "assigned_to"),
        Index("ix_activities_follow_up", "follow_up_date"),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if activity is overdue."""
        return (
            self.activity_status == ActivityStatus.PLANNED
            and datetime.now() > self.scheduled_date
        )

    @hybrid_property
    def days_until_scheduled(self) -> int:
        """Calculate days until scheduled date."""
        return (self.scheduled_date.date() - date.today()).days

    def __repr__(self):
        """  Repr   operation."""
        return f"<SalesActivity(id='{self.activity_id}', type='{self.activity_type}', status='{self.activity_status}')>"


class Quote(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Sales quotes and proposals."""

    __tablename__ = "sales_quotes"

    # Quote identification
    quote_number = Column(String(100), nullable=False, unique=True, index=True)
    quote_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # References
    opportunity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sales_opportunities.id"),
        nullable=False,
        index=True,
    )
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Customer information
    customer_name = Column(String(300), nullable=False)
    customer_contact = Column(String(200), nullable=True)
    customer_email = Column(String(255), nullable=True)

    # Quote details
    quote_status = Column(
        SQLEnum(QuoteStatus), default=QuoteStatus.DRAFT, nullable=False, index=True
    )
    quote_date = Column(Date, nullable=False, default=date.today)
    valid_until = Column(Date, nullable=False)

    # Financial totals
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), default=0, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    # Terms and conditions
    payment_terms = Column(String(200), nullable=True)
    delivery_terms = Column(String(200), nullable=True)
    warranty_terms = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)

    # Sales information
    sales_owner = Column(String(200), nullable=False, index=True)
    prepared_by = Column(String(200), nullable=False)
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)

    # Customer interaction
    sent_date = Column(Date, nullable=True)
    viewed_date = Column(Date, nullable=True)
    response_date = Column(Date, nullable=True)
    accepted_date = Column(Date, nullable=True)

    # Revision tracking
    revision_number = Column(Integer, default=1, nullable=False)
    parent_quote_id = Column(
        UUID(as_uuid=True), ForeignKey("sales_quotes.id"), nullable=True
    )

    # Documents and presentation
    quote_document_url = Column(String(500), nullable=True)
    presentation_url = Column(String(500), nullable=True)
    supporting_documents = Column(JSON, nullable=True)

    # Additional information
    special_instructions = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="quotes")
    line_items = relationship(
        "QuoteLineItem", back_populates="quote", cascade="all, delete-orphan"
    )
    parent_quote = relationship("Quote", remote_side="Quote.id")

    __table_args__ = (
        Index("ix_quotes_opportunity_status", "opportunity_id", "quote_status"),
        Index("ix_quotes_owner_date", "sales_owner", "quote_date"),
        Index("ix_quotes_valid_until", "valid_until"),
    )

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if quote is expired."""
        return date.today() > self.valid_until

    @hybrid_property
    def days_to_expiry(self) -> int:
        """Calculate days until quote expires."""
        return (self.valid_until - date.today()).days

    @hybrid_property
    def response_time_days(self) -> Optional[int]:
        """Calculate response time in days."""
        if self.sent_date and self.response_date:
            return (self.response_date - self.sent_date).days
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<Quote(number='{self.quote_number}', opportunity_id='{self.opportunity_id}', total={self.total_amount})>"


class QuoteLineItem(TenantModel, AuditMixin):
    """Individual line items in quotes."""

    __tablename__ = "sales_quote_line_items"

    # References
    quote_id = Column(
        UUID(as_uuid=True), ForeignKey("sales_quotes.id"), nullable=False, index=True
    )

    # Line item details
    line_number = Column(Integer, nullable=False)
    product_code = Column(String(100), nullable=True)
    product_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Quantities and pricing
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    list_price = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Numeric(5, 2), default=0, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0, nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)

    # Product classification
    product_category = Column(String(100), nullable=True)
    revenue_type = Column(String(50), nullable=True)  # one_time, recurring, usage
    billing_frequency = Column(String(50), nullable=True)  # monthly, annually, etc.

    # Delivery and fulfillment
    delivery_date = Column(Date, nullable=True)
    lead_time_days = Column(Integer, nullable=True)

    # Cost information (for margin analysis)
    unit_cost = Column(Numeric(10, 2), nullable=True)
    margin_percent = Column(Numeric(5, 2), nullable=True)
    margin_amount = Column(Numeric(10, 2), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    quote = relationship("Quote", back_populates="line_items")

    __table_args__ = (
        Index("ix_quote_lines_quote_line", "quote_id", "line_number", unique=True),
        Index("ix_quote_lines_product", "product_code"),
    )

    @hybrid_property
    def effective_unit_price(self) -> Decimal:
        """Calculate effective unit price after discount."""
        return self.unit_price - self.discount_amount

    @hybrid_property
    def margin_percentage(self) -> Optional[float]:
        """Calculate margin percentage."""
        if self.unit_cost and self.unit_price > 0:
            margin = (self.unit_price - self.unit_cost) / self.unit_price
            return round(margin * 100, 2)
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<QuoteLineItem(quote_id='{self.quote_id}', line={self.line_number}, product='{self.product_name}')>"


class SalesForecast(TenantModel, AuditMixin):
    """Sales forecasting and pipeline analysis."""

    __tablename__ = "sales_forecasts"

    # Forecast identification
    forecast_id = Column(String(100), nullable=False, unique=True, index=True)
    forecast_name = Column(String(200), nullable=False)

    # Forecast period
    forecast_period = Column(
        String(50), nullable=False, index=True
    )  # Q1-2024, Jan-2024, etc.
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Forecast scope
    sales_team = Column(String(100), nullable=True, index=True)
    territory = Column(String(100), nullable=True)
    product_line = Column(String(100), nullable=True)

    # Forecast amounts
    pipeline_total = Column(Numeric(15, 2), nullable=False, default=0)
    best_case = Column(Numeric(15, 2), nullable=False, default=0)
    commit = Column(Numeric(15, 2), nullable=False, default=0)
    closed_won = Column(Numeric(15, 2), nullable=False, default=0)

    # Targets and quotas
    quota_target = Column(Numeric(12, 2), nullable=True)
    stretch_target = Column(Numeric(12, 2), nullable=True)

    # Accuracy tracking
    accuracy_percent = Column(Float, nullable=True)
    variance_amount = Column(Numeric(12, 2), nullable=True)

    # Forecast submission
    submitted_by = Column(String(200), nullable=False)
    submitted_date = Column(Date, nullable=False, default=date.today)
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)

    # Analysis
    top_opportunities = Column(JSON, nullable=True)
    risk_factors = Column(JSON, nullable=True)
    upside_potential = Column(JSON, nullable=True)

    # Additional information
    commentary = Column(Text, nullable=True)
    assumptions = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_forecasts_period_team", "forecast_period", "sales_team"),
        Index("ix_forecasts_submitted", "submitted_date"),
    )

    @hybrid_property
    def quota_achievement(self) -> Optional[float]:
        """Calculate quota achievement percentage."""
        if self.quota_target and self.quota_target > 0:
            return round((float(self.closed_won) / float(self.quota_target)) * 100, 2)
        return None

    @hybrid_property
    def pipeline_coverage(self) -> Optional[float]:
        """Calculate pipeline coverage ratio."""
        if self.quota_target and self.quota_target > 0:
            return round(float(self.pipeline_total) / float(self.quota_target), 2)
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<SalesForecast(id='{self.forecast_id}', period='{self.forecast_period}', commit={self.commit})>"


class Territory(TenantModel, StatusMixin, AuditMixin):
    """Sales territories and coverage areas."""

    __tablename__ = "sales_territories"

    # Territory identification
    territory_code = Column(String(100), nullable=False, index=True)
    territory_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Geographic definition
    geographic_areas = Column(JSON, nullable=False)  # States, regions, ZIP codes
    exclusions = Column(JSON, nullable=True)

    # Assignment
    territory_manager = Column(String(200), nullable=True, index=True)
    sales_team = Column(String(100), nullable=True)
    coverage_model = Column(String(50), nullable=True)  # direct, partner, hybrid

    # Market characteristics
    market_size = Column(Numeric(15, 2), nullable=True)
    customer_count = Column(Integer, nullable=True)
    potential_customers = Column(Integer, nullable=True)
    market_penetration = Column(Float, nullable=True)

    # Performance targets
    annual_quota = Column(Numeric(12, 2), nullable=True)
    quarterly_targets = Column(JSON, nullable=True)

    # Territory rules
    assignment_rules = Column(JSON, nullable=True)
    overlap_handling = Column(Text, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_territories_tenant_code", "tenant_id", "territory_code", unique=True),
        Index("ix_territories_manager", "territory_manager"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return (
            f"<Territory(code='{self.territory_code}', name='{self.territory_name}')>"
        )
