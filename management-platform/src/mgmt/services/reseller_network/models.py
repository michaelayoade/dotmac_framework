"""
Reseller Network Models for Partner Management and Sales Operations.

This module defines the data models for managing reseller partners, including:
- Reseller registration and profile management
- Sales pipeline and opportunity tracking
- Commission structures and payment tracking
- Territory assignments and performance metrics
- Training and certification management
- Customer relationship management
"""

import enum
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import ()
    Column, String, Text, DateTime, Boolean, Numeric, Integer,
    ForeignKey, Enum as SQLEnum, JSON, Date, Index
, timezone)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.orm import relationship, validates

from ....app.models.base import BaseModel


class ResellerStatus(str, enum.Enum):
    """Reseller account status enumeration."""
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class ResellerTier(str, enum.Enum):
    """Reseller certification tier enumeration."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class OpportunityStage(str, enum.Enum):
    """Sales opportunity stage enumeration."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class CommissionType(str, enum.Enum):
    """Commission type enumeration."""
    INITIAL = "initial"           # One-time commission on deal closure
    RECURRING = "recurring"       # Ongoing monthly/quarterly commissions
    BONUS = "bonus"              # Performance-based bonuses
    OVERRIDE = "override"        # Manager override commissions


class CommissionStatus(str, enum.Enum):
    """Commission payment status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    """Commission payment method enumeration."""
    ACH = "ach"
    WIRE = "wire"
    CHECK = "check"
    PAYPAL = "paypal"
    CRYPTO = "crypto"


class Reseller(BaseModel):
    """Reseller partner model for channel sales management."""
    
    __tablename__ = "resellers"
    
    # Company Information
    company_name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255), nullable=True)
    tax_id = Column(String(50), nullable=True)
    duns_number = Column(String(20), nullable=True)
    
    # Contact Information
    primary_contact_first_name = Column(String(100), nullable=False)
    primary_contact_last_name = Column(String(100), nullable=False)
    primary_contact_email = Column(String(255), nullable=False, index=True)
    primary_contact_phone = Column(String(20), nullable=True)
    primary_contact_title = Column(String(100), nullable=True)
    
    # Business Details
    business_type = Column(String(50), nullable=True)  # distributor, var, consultant, etc.
    industry_focus = Column(JSON, nullable=True)  # List of target industries
    target_customer_segments = Column(JSON, nullable=True)  # SMB, Enterprise, etc.
    geographical_coverage = Column(JSON, nullable=True)  # States/regions covered
    
    # Address Information
    street_address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Status and Tier
    status = Column(SQLEnum(ResellerStatus), default=ResellerStatus.PENDING_APPROVAL, nullable=False, index=True)
    tier = Column(SQLEnum(ResellerTier), default=ResellerTier.BRONZE, nullable=False, index=True)
    
    # Important Dates
    approved_date = Column(Date, nullable=True)
    tier_achieved_date = Column(Date, nullable=True)
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    
    # Performance Metrics
    total_revenue_generated = Column(Numeric(15, 2), default=0, nullable=False)
    total_commissions_earned = Column(Numeric(15, 2), default=0, nullable=False)
    active_customers = Column(Integer, default=0, nullable=False)
    customers_lifetime = Column(Integer, default=0, nullable=False)
    
    # Territory Assignment
    territory_name = Column(String(255), nullable=True, index=True)
    territory_type = Column(String(50), default="geographic", nullable=False)  # geographic, vertical, account
    exclusive_territory = Column(Boolean, default=False, nullable=False)
    
    # Commission Structure
    base_commission_rate = Column(Numeric(5, 4), default=0.10, nullable=False)  # 10%
    current_commission_rate = Column(Numeric(5, 4), default=0.10, nullable=False)
    recurring_commission_rate = Column(Numeric(5, 4), default=0.08, nullable=False)  # 8%
    
    # Business Capabilities
    technical_certifications = Column(JSON, nullable=True)
    languages_supported = Column(JSON, nullable=True)
    support_capabilities = Column(JSON, nullable=True)
    
    # Marketing and Sales Tools
    marketing_budget_annual = Column(Numeric(12, 2), nullable=True)
    sales_team_size = Column(Integer, default=1, nullable=False)
    has_dedicated_sales_rep = Column(Boolean, default=False, nullable=False)
    
    # Compliance and Legal
    background_check_completed = Column(Boolean, default=False, nullable=False)
    contracts_signed = Column(JSON, nullable=True)  # List of signed contract types
    insurance_verified = Column(Boolean, default=False, nullable=False)
    
    # Portal Access
    portal_access_enabled = Column(Boolean, default=True, nullable=False)
    last_login_date = Column(DateTime, nullable=True)
    portal_usage_metrics = Column(JSON, nullable=True)
    
    # Relationships
    opportunities = relationship("SalesOpportunity", back_populates="reseller", cascade="all, delete-orphan")
    commissions = relationship("CommissionRecord", back_populates="reseller", cascade="all, delete-orphan")
    training_progress = relationship("ResellerTraining", back_populates="reseller", cascade="all, delete-orphan")
    territory_assignments = relationship("TerritoryAssignment", back_populates="reseller", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = ()
        Index('idx_reseller_status_tier', 'status', 'tier'),
        Index('idx_reseller_territory', 'territory_name', 'territory_type'),
        Index('idx_reseller_performance', 'total_revenue_generated', 'active_customers'),
    )
    
    @validates('primary_contact_email')
    def validate_email(self, key, email):
        """Validate email format."""
        import re
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError('Invalid email format')
        return email
    
    @property
    def is_active(self) -> bool:
        """Check if reseller is currently active."""
        return self.status == ResellerStatus.ACTIVE
    
    @property
    def commission_rate_display(self) -> str:
        """Display-friendly commission rate."""
        return f"{float(self.current_commission_rate * 100):.1f}%"
    
    def update_performance_metrics(self, revenue_delta: Decimal = 0, customer_delta: int = 0):
        """Update performance metrics."""
        self.total_revenue_generated += revenue_delta
        self.active_customers += customer_delta
        if customer_delta > 0:
            self.customers_lifetime += customer_delta


class SalesOpportunity(BaseModel):
    """Sales opportunity tracking for reseller pipeline management."""
    
    __tablename__ = "sales_opportunities"
    
    # Relationship
    reseller_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    
    # Opportunity Identification
    opportunity_name = Column(String(255), nullable=False)
    prospect_company = Column(String(255), nullable=False, index=True)
    prospect_website = Column(String(500), nullable=True)
    
    # Contact Information
    primary_contact_name = Column(String(200), nullable=False)
    primary_contact_email = Column(String(255), nullable=False)
    primary_contact_phone = Column(String(20), nullable=True)
    primary_contact_title = Column(String(100), nullable=True)
    additional_contacts = Column(JSON, nullable=True)  # List of additional contacts
    
    # Opportunity Details
    description = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True, index=True)
    company_size = Column(String(50), nullable=True)  # startup, small, medium, large, enterprise
    employee_count = Column(Integer, nullable=True)
    annual_revenue = Column(Numeric(15, 2), nullable=True)
    
    # Sales Process
    stage = Column(SQLEnum(OpportunityStage), default=OpportunityStage.LEAD, nullable=False, index=True)
    probability = Column(Integer, default=20, nullable=False)  # 0-100%
    lead_source = Column(String(100), nullable=True)  # referral, marketing, cold_call, etc.
    
    # Financial Information
    estimated_value = Column(Numeric(12, 2), nullable=False)
    estimated_annual_value = Column(Numeric(12, 2), nullable=True)
    estimated_monthly_recurring = Column(Numeric(12, 2), nullable=True)
    
    # Timeline
    created_date = Column(DateTime, default=lambda: datetime.now(None), nullable=False)
    expected_close_date = Column(Date, nullable=True)
    last_activity_date = Column(DateTime, default=lambda: datetime.now(None), nullable=False)
    last_contact_date = Column(DateTime, nullable=True)
    next_follow_up_date = Column(DateTime, nullable=True)
    
    # Requirements and Technical Details
    required_features = Column(JSON, nullable=True)  # List of required features
    technical_requirements = Column(JSON, nullable=True)  # Technical specs
    compliance_requirements = Column(JSON, nullable=True)  # Regulatory requirements
    integration_requirements = Column(JSON, nullable=True)  # Systems to integrate
    
    # Competition Analysis
    competing_vendors = Column(JSON, nullable=True)  # List of competing vendors
    competitive_advantages = Column(JSON, nullable=True)  # Our advantages
    competitive_threats = Column(JSON, nullable=True)  # Threats and challenges
    
    # Internal Tracking
    assigned_to = Column(String(255), nullable=True)  # Sales rep assigned
    sales_engineer = Column(String(255), nullable=True)  # Technical support
    account_executive = Column(String(255), nullable=True)  # Senior oversight
    
    # Activity Tracking
    activities_log = Column(JSON, nullable=True)  # List of activities/interactions
    notes = Column(Text, nullable=True)
    documents = Column(JSON, nullable=True)  # Links to proposals, presentations, etc.
    
    # Tags and Classification
    tags = Column(JSON, nullable=True)  # Custom tags for filtering
    priority_level = Column(String(20), default="medium", nullable=False)  # low, medium, high
    deal_type = Column(String(50), nullable=True)  # new_business, expansion, renewal
    
    # Outcome Tracking
    close_date = Column(Date, nullable=True)
    won_reason = Column(Text, nullable=True)
    lost_reason = Column(Text, nullable=True)
    actual_value = Column(Numeric(12, 2), nullable=True)
    
    # Relationships
    reseller = relationship("Reseller", back_populates="opportunities")
    quotes = relationship("SalesQuote", back_populates="opportunity", cascade="all, delete-orphan")
    commissions = relationship("CommissionRecord", back_populates="opportunity")
    
    # Indexes
    __table_args__ = ()
        Index('idx_opportunity_stage_probability', 'stage', 'probability'),
        Index('idx_opportunity_dates', 'expected_close_date', 'last_activity_date'),
        Index('idx_opportunity_value', 'estimated_value', 'stage'),
    )
    
    @property
    def is_active(self) -> bool:
        """Check if opportunity is still active."""
        return self.stage not in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]
    
    @property
    def weighted_value(self) -> Decimal:
        """Calculate probability-weighted opportunity value."""
        return self.estimated_value * (Decimal(self.probability) / 100)
    
    def advance_stage(self, new_stage: OpportunityStage, probability: Optional[int] = None):
        """Advance opportunity to next stage."""
        self.stage = new_stage
        if probability is not None:
            self.probability = probability
        self.last_activity_date = datetime.now(None)


class SalesQuote(BaseModel):
    """Sales quotes and proposals for opportunities."""
    
    __tablename__ = "sales_quotes"
    
    # Relationships
    opportunity_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("sales_opportunities.id"), nullable=False, index=True)
    reseller_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    
    # Quote Identification
    quote_number = Column(String(50), unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    
    # Customer Information
    customer_company = Column(String(255), nullable=False)
    customer_contact_name = Column(String(200), nullable=False)
    customer_contact_email = Column(String(255), nullable=False)
    customer_address = Column(Text, nullable=True)
    
    # Quote Details
    quote_date = Column(Date, default=date.today, nullable=False)
    expiration_date = Column(Date, nullable=False)
    valid_for_days = Column(Integer, default=30, nullable=False)
    
    # Line Items
    line_items = Column(JSON, nullable=False)  # Detailed quote line items
    
    # Financial Totals
    subtotal = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0, nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0, nullable=True)
    tax_rate = Column(Numeric(5, 4), default=0, nullable=True)
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Terms and Conditions
    payment_terms = Column(String(100), default="Net 30", nullable=False)
    delivery_terms = Column(String(200), nullable=True)
    warranty_terms = Column(Text, nullable=True)
    
    # Status Tracking
    status = Column(String(50), default="draft", nullable=False)  # draft, sent, viewed, accepted, rejected, expired
    sent_date = Column(DateTime, nullable=True)
    viewed_date = Column(DateTime, nullable=True)
    accepted_date = Column(DateTime, nullable=True)
    rejected_date = Column(DateTime, nullable=True)
    
    # Commission Information
    estimated_commission = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    
    # Approval Workflow
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String(255), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Document Management
    pdf_document_url = Column(String(500), nullable=True)
    signature_document_url = Column(String(500), nullable=True)
    
    # Relationships
    opportunity = relationship("SalesOpportunity", back_populates="quotes")
    reseller = relationship("Reseller")
    
    @property
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        return date.today( > self.expiration_date)
    
    @property
)    def days_until_expiration(self) -> int:
        """Days until quote expires."""
        return (self.expiration_date - date.today(.days)
    
)    def calculate_totals(self):
        """Calculate quote totals from line items."""
        if not self.line_items:
            return None
        subtotal = sum(Decimal(str(item.get('total_amount', 0) for item in self.line_items))
        self.subtotal = subtotal
        
        if self.discount_percentage and self.discount_percentage > 0:
            self.discount_amount = subtotal * (self.discount_percentage / 100)
        
        taxable_amount = subtotal - self.discount_amount
        if self.tax_rate and self.tax_rate > 0:
            self.tax_amount = taxable_amount * self.tax_rate
        
        self.total_amount = taxable_amount + self.tax_amount


class CommissionRecord(BaseModel):
    """Commission tracking and payment records."""
    
    __tablename__ = "commission_records"
    
    # Relationships
    reseller_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    opportunity_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("sales_opportunities.id"), nullable=True, index=True)
    
    # Commission Details
    commission_type = Column(SQLEnum(CommissionType), nullable=False, index=True)
    commission_period = Column(String(50), nullable=True)  # one_time, monthly, quarterly, annual
    
    # Financial Information
    base_amount = Column(Numeric(12, 2), nullable=False)  # Amount commission is calculated from
    commission_rate = Column(Numeric(5, 4), nullable=False)  # Rate applied
    commission_amount = Column(Numeric(12, 2), nullable=False)  # Calculated commission
    
    # Dates
    earned_date = Column(Date, nullable=False, index=True)
    payment_due_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    
    # Status and Payment
    status = Column(SQLEnum(CommissionStatus), default=CommissionStatus.PENDING, nullable=False, index=True)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    payment_notes = Column(Text, nullable=True)
    
    # Customer Information (for recurring commissions)
    customer_id = Column(String(255), nullable=True, index=True)
    customer_name = Column(String(255), nullable=True)
    subscription_id = Column(String(255), nullable=True)
    
    # Additional Details
    description = Column(Text, nullable=True)
    tier_at_time_of_sale = Column(SQLEnum(ResellerTier), nullable=True)
    split_percentage = Column(Numeric(5, 2), default=100, nullable=False)  # For split commissions
    
    # Approval Workflow
    approved_by = Column(String(255), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Relationships
    reseller = relationship("Reseller", back_populates="commissions")
    opportunity = relationship("SalesOpportunity", back_populates="commissions")
    
    # Indexes
    __table_args__ = ()
        Index('idx_commission_payment', 'status', 'payment_due_date'),
        Index('idx_commission_earned', 'earned_date', 'commission_type'),
        Index('idx_commission_customer', 'customer_id', 'commission_period'),
    )
    
    @property
    def is_overdue(self) -> bool:
        """Check if commission payment is overdue."""
        return (self.payment_due_date and )
                date.today( > self.payment_due_date and )
                self.status in [CommissionStatus.PENDING, CommissionStatus.APPROVED])


class ResellerTraining(BaseModel):
    """Reseller training and certification tracking."""
    
    __tablename__ = "reseller_training"
    
    # Relationships
    reseller_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    
    # Training Module Information
    module_id = Column(String(50), nullable=False)
    module_name = Column(String(255), nullable=False)
    module_category = Column(String(100), nullable=False)  # product, sales, technical, compliance
    
    # Progress Tracking
    started_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    score = Column(Integer, nullable=True)  # 0-100
    passing_score = Column(Integer, default=80, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    
    # Certification Information
    required_for_tier = Column(SQLEnum(ResellerTier), nullable=True)
    certification_expiry_date = Column(Date, nullable=True)
    recertification_required = Column(Boolean, default=False, nullable=False)
    
    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    is_passed = Column(Boolean, default=False, nullable=False)
    
    # Additional Details
    duration_minutes = Column(Integer, nullable=True)
    instructor_name = Column(String(255), nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    # Relationships
    reseller = relationship("Reseller", back_populates="training_progress")
    
    # Indexes
    __table_args__ = ()
        Index('idx_training_module', 'reseller_id', 'module_id'),
        Index('idx_training_completion', 'is_completed', 'completed_date'),
    )
    
    @property
    def is_passed_and_current(self) -> bool:
        """Check if training is passed and still current."""
        if not self.is_passed:
            return False
        if self.certification_expiry_date and date.today( > self.certification_expiry_date:)
            return False
        return True


)class TerritoryAssignment(BaseModel):
    """Territory assignment and management for resellers."""
    
    __tablename__ = "territory_assignments"
    
    # Relationships
    reseller_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    
    # Territory Definition
    territory_name = Column(String(255), nullable=False)
    territory_type = Column(String(50), nullable=False)  # geographic, vertical, account_based
    territory_description = Column(Text, nullable=True)
    
    # Geographic Boundaries (if applicable)
    countries = Column(JSON, nullable=True)
    states_provinces = Column(JSON, nullable=True)
    cities = Column(JSON, nullable=True)
    postal_codes = Column(JSON, nullable=True)
    
    # Vertical/Industry Focus (if applicable)
    industries = Column(JSON, nullable=True)
    company_sizes = Column(JSON, nullable=True)  # startup, sme, enterprise
    
    # Account-Based Assignments
    named_accounts = Column(JSON, nullable=True)  # Specific company assignments
    
    # Assignment Details
    is_exclusive = Column(Boolean, default=False, nullable=False)
    assignment_date = Column(Date, default=date.today, nullable=False)
    effective_date = Column(Date, default=date.today, nullable=False)
    expiration_date = Column(Date, nullable=True)
    
    # Performance Expectations
    annual_quota = Column(Numeric(15, 2), nullable=True)
    quarterly_targets = Column(JSON, nullable=True)
    market_share_target = Column(Numeric(5, 2), nullable=True)  # Percentage
    
    # Territory Metrics
    total_addressable_market = Column(Integer, nullable=True)
    estimated_market_size = Column(Numeric(15, 2), nullable=True)
    current_penetration = Column(Numeric(5, 2), default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    reseller = relationship("Reseller", back_populates="territory_assignments")
    
    def check_territory_match(self, company_location: Dict[str, Any]) -> bool:
        """Check if a company location matches this territory."""
        if self.territory_type == "geographic":
            # Check geographic boundaries
            if self.countries and company_location.get('country') not in self.countries:
                return False
            if self.states_provinces and company_location.get('state') not in self.states_provinces:
                return False
            return True
        
        elif self.territory_type == "vertical":
            # Check industry match
            if self.industries and company_location.get('industry') not in self.industries:
                return False
            if self.company_sizes and company_location.get('company_size') not in self.company_sizes:
                return False
            return True
        
        elif self.territory_type == "account_based":
            # Check named accounts
            return company_location.get('company_name') in (self.named_accounts or [])
        
        return False
