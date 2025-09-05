"""
Complete database models for reseller management
Designed to work independently without problematic dependencies
"""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# Enums
class ResellerType(str, Enum):
    AUTHORIZED_DEALER = "authorized_dealer"
    VALUE_ADDED_RESELLER = "value_added_reseller"
    SYSTEM_INTEGRATOR = "system_integrator"
    DISTRIBUTOR = "distributor"
    TECHNOLOGY_PARTNER = "technology_partner"
    REFERRAL_PARTNER = "referral_partner"


class ResellerStatus(str, Enum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class ApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CommissionStructure(str, Enum):
    PERCENTAGE = "percentage"
    FLAT_FEE = "flat_fee"
    TIERED = "tiered"


class ResellerApplication(Base):
    """Reseller application model with complete data structure"""

    __tablename__ = "reseller_applications"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Application tracking
    application_id = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, nullable=False, index=True)

    # Company information
    company_name = Column(String(300), nullable=False, index=True)
    legal_company_name = Column(String(300), nullable=True)
    website_url = Column(String(500), nullable=True)
    business_type = Column(String(100), nullable=True)
    years_in_business = Column(Integer, nullable=True)
    employee_count = Column(Integer, nullable=True)
    annual_revenue_range = Column(String(50), nullable=True)

    # Primary contact
    contact_name = Column(String(200), nullable=False)
    contact_title = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=False, index=True)
    contact_phone = Column(String(20), nullable=True)

    # Business details
    business_description = Column(Text, nullable=True)
    telecom_experience_years = Column(Integer, nullable=True)
    target_customer_segments = Column(JSON, nullable=True)
    desired_territories = Column(JSON, nullable=True)
    estimated_monthly_customers = Column(Integer, nullable=True)
    preferred_commission_structure = Column(String(50), nullable=True)

    # Technical capabilities
    technical_capabilities = Column(JSON, nullable=True)
    installation_experience = Column(Boolean, default=False)
    support_capabilities = Column(JSON, nullable=True)

    # Financial information
    business_license_number = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)
    insurance_coverage = Column(Boolean, default=False)
    credit_references = Column(JSON, nullable=True)

    # Application processing
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_by = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision_date = Column(Date, nullable=True)
    decision_reason = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Follow-up and communication
    follow_up_required = Column(Boolean, default=False)
    follow_up_notes = Column(Text, nullable=True)
    next_contact_date = Column(Date, nullable=True)
    communication_log = Column(JSON, default=list, nullable=False)

    # Documents and attachments
    uploaded_documents = Column(JSON, nullable=True)
    required_documents = Column(JSON, nullable=True)

    # Tenant isolation
    tenant_id = Column(String(100), nullable=True, index=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to approved reseller
    approved_reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=True)
    approved_reseller = relationship("Reseller", back_populates="applications")

    # Indexes for performance
    __table_args__ = (
        Index("idx_application_tenant_status", "tenant_id", "status"),
        Index("idx_application_email", "contact_email"),
        Index("idx_application_company", "company_name"),
    )

    def __repr__(self):
        return (
            f"<ResellerApplication(id='{self.application_id}', company='{self.company_name}', status='{self.status}')>"
        )


class Reseller(Base):
    """Complete reseller model for approved partners"""

    __tablename__ = "resellers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reseller identification
    reseller_id = Column(String(100), nullable=False, unique=True, index=True)
    company_name = Column(String(300), nullable=False, index=True)
    legal_name = Column(String(300), nullable=True)
    doing_business_as = Column(String(300), nullable=True)

    # Classification
    reseller_type = Column(SQLEnum(ResellerType), nullable=False, index=True)
    status = Column(SQLEnum(ResellerStatus), default=ResellerStatus.ACTIVE, nullable=False, index=True)

    # Contact information
    primary_contact_name = Column(String(200), nullable=False)
    primary_contact_email = Column(String(255), nullable=False, index=True)
    primary_contact_phone = Column(String(20), nullable=True)
    secondary_contact_name = Column(String(200), nullable=True)
    secondary_contact_email = Column(String(255), nullable=True)
    secondary_contact_phone = Column(String(20), nullable=True)

    # Business details
    tax_id = Column(String(50), nullable=True)
    business_license = Column(String(100), nullable=True)
    website_url = Column(String(500), nullable=True)
    business_address = Column(JSON, nullable=True)
    billing_address = Column(JSON, nullable=True)

    # Service capabilities
    service_territories = Column(JSON, nullable=True)
    service_types_offered = Column(JSON, nullable=True)
    installation_capabilities = Column(JSON, nullable=True)
    support_capabilities = Column(JSON, nullable=True)

    # Partnership agreement
    agreement_start_date = Column(Date, nullable=True)
    agreement_end_date = Column(Date, nullable=True)
    agreement_type = Column(String(50), nullable=True)
    contract_terms = Column(JSON, nullable=True)

    # Commission and financial
    commission_structure = Column(SQLEnum(CommissionStructure), nullable=True)
    base_commission_rate = Column(Numeric(5, 2), nullable=True)
    tier_rates = Column(JSON, nullable=True)  # For tiered commission structures
    payment_terms = Column(String(100), nullable=True)
    payment_method = Column(String(50), nullable=True)

    # Performance metrics
    total_customers = Column(Integer, default=0, nullable=False)
    active_customers = Column(Integer, default=0, nullable=False)
    lifetime_sales = Column(Numeric(15, 2), default=0, nullable=False)
    ytd_sales = Column(Numeric(15, 2), default=0, nullable=False)
    monthly_sales = Column(Numeric(12, 2), default=0, nullable=False)
    annual_quota = Column(Numeric(12, 2), nullable=True)

    # Performance quality metrics
    customer_churn_rate = Column(Numeric(5, 2), nullable=True)
    average_install_time_days = Column(Integer, nullable=True)
    customer_satisfaction_score = Column(Numeric(3, 2), nullable=True)
    support_ticket_resolution_rate = Column(Numeric(5, 2), nullable=True)

    # Portal access
    portal_enabled = Column(Boolean, default=True, nullable=False)
    portal_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    portal_last_login = Column(DateTime, nullable=True)
    portal_permissions = Column(JSON, nullable=True)

    # Support and training
    assigned_account_manager = Column(String(200), nullable=True)
    assigned_technical_contact = Column(String(200), nullable=True)
    certification_level = Column(String(50), nullable=True)
    certification_date = Column(Date, nullable=True)
    training_completed = Column(JSON, nullable=True)

    # Custom fields and notes
    custom_fields = Column(JSON, default=dict, nullable=False)
    internal_notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)

    # Tenant isolation
    tenant_id = Column(String(100), nullable=True, index=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(200), nullable=True)

    # Relationships
    applications = relationship("ResellerApplication", back_populates="approved_reseller")
    customers = relationship("ResellerCustomer", back_populates="reseller", cascade="all, delete-orphan")
    commissions = relationship("ResellerCommission", back_populates="reseller", cascade="all, delete-orphan")
    opportunities = relationship("ResellerOpportunity", back_populates="reseller", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("idx_reseller_tenant_status", "tenant_id", "status"),
        Index("idx_reseller_type", "reseller_type"),
        Index("idx_reseller_contact_email", "primary_contact_email"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == ResellerStatus.ACTIVE

    @property
    def commission_rate_display(self) -> str:
        if self.base_commission_rate:
            return f"{self.base_commission_rate}%"
        return "Not Set"

    def __repr__(self):
        return f"<Reseller(id='{self.reseller_id}', company='{self.company_name}', status='{self.status}')>"


class ResellerCustomer(Base):
    """Customer-reseller relationship model"""

    __tablename__ = "reseller_customers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Relationship details
    relationship_start_date = Column(Date, nullable=False, default=date.today)
    relationship_status = Column(String(50), default="active", nullable=False, index=True)
    assignment_type = Column(String(50), nullable=True)  # direct, referral, inherited

    # Service details
    primary_service_type = Column(String(50), nullable=True)
    connection_type = Column(String(50), nullable=True)
    service_speed_mbps = Column(Integer, nullable=True)
    installation_date = Column(Date, nullable=True)
    last_service_call = Column(Date, nullable=True)

    # Financial tracking
    monthly_recurring_revenue = Column(Numeric(10, 2), default=0, nullable=False)
    lifetime_value = Column(Numeric(12, 2), default=0, nullable=False)
    total_commission_paid = Column(Numeric(10, 2), default=0, nullable=False)

    # Customer acquisition
    acquisition_date = Column(Date, nullable=True)
    acquisition_channel = Column(String(100), nullable=True)
    acquisition_cost = Column(Numeric(8, 2), nullable=True)

    # Performance metrics
    support_tickets_count = Column(Integer, default=0)
    satisfaction_score = Column(Numeric(3, 2), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, default=dict, nullable=False)

    # Tenant isolation
    tenant_id = Column(String(100), nullable=True, index=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reseller = relationship("Reseller", back_populates="customers")

    # Indexes for performance
    __table_args__ = (
        Index("idx_reseller_customer_tenant", "tenant_id", "reseller_id"),
        Index("idx_customer_reseller", "customer_id", "reseller_id"),
    )

    def __repr__(self):
        return f"<ResellerCustomer(reseller_id='{self.reseller_id}', customer_id='{self.customer_id}')>"


class ResellerOpportunity(Base):
    """Sales opportunity managed by resellers"""

    __tablename__ = "reseller_opportunities"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)

    # Opportunity identification
    opportunity_id = Column(String(100), nullable=False, unique=True, index=True)
    opportunity_name = Column(String(300), nullable=False)

    # Prospect information
    prospect_name = Column(String(200), nullable=False)
    prospect_email = Column(String(255), nullable=True)
    prospect_phone = Column(String(20), nullable=True)
    prospect_address = Column(JSON, nullable=True)
    prospect_company = Column(String(200), nullable=True)

    # Opportunity details
    opportunity_type = Column(String(50), nullable=False)  # new_customer, upsell, renewal
    estimated_value = Column(Numeric(10, 2), nullable=True)
    probability = Column(Integer, default=50, nullable=False)

    # Service requirements
    desired_service_type = Column(String(50), nullable=True)
    desired_speed_mbps = Column(Integer, nullable=True)
    installation_address = Column(JSON, nullable=True)
    service_availability_confirmed = Column(Boolean, default=False, nullable=False)
    technical_survey_completed = Column(Boolean, default=False, nullable=False)

    # Sales pipeline
    stage = Column(String(50), nullable=False, default="prospect", index=True)
    expected_close_date = Column(Date, nullable=True)
    actual_close_date = Column(Date, nullable=True)
    close_reason = Column(String(200), nullable=True)

    # Source and tracking
    lead_source = Column(String(100), nullable=True)
    first_contact_date = Column(Date, nullable=True)
    last_contact_date = Column(Date, nullable=True)
    next_follow_up_date = Column(Date, nullable=True)

    # Commission planning
    estimated_commission = Column(Numeric(8, 2), nullable=True)

    # Additional information
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    next_action = Column(String(500), nullable=True)
    custom_fields = Column(JSON, default=dict, nullable=False)

    # Communication log
    communication_log = Column(JSON, default=list, nullable=False)

    # Tenant isolation
    tenant_id = Column(String(100), nullable=True, index=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reseller = relationship("Reseller", back_populates="opportunities")

    # Indexes for performance
    __table_args__ = (
        Index("idx_opportunity_tenant_stage", "tenant_id", "stage"),
        Index("idx_opportunity_reseller_stage", "reseller_id", "stage"),
        Index("idx_opportunity_close_date", "expected_close_date"),
    )

    @property
    def is_active(self) -> bool:
        return self.stage not in ["closed_won", "closed_lost"]

    @property
    def is_overdue(self) -> bool:
        return self.expected_close_date and date.today() > self.expected_close_date and self.is_active

    def __repr__(self):
        return (
            f"<ResellerOpportunity(id='{self.opportunity_id}', name='{self.opportunity_name}', stage='{self.stage}')>"
        )


class ResellerCommission(Base):
    """Commission tracking for reseller payments"""

    __tablename__ = "reseller_commissions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    service_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Commission identification
    commission_id = Column(String(100), nullable=False, unique=True, index=True)
    commission_type = Column(String(50), nullable=False, index=True)

    # Financial details
    base_amount = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(10, 2), nullable=False)

    # Service-specific details
    service_type = Column(String(50), nullable=True)
    service_tier = Column(String(50), nullable=True)
    installation_commission = Column(Numeric(8, 2), default=0, nullable=False)
    monthly_recurring_commission = Column(Numeric(8, 2), default=0, nullable=False)

    # Period information
    commission_period = Column(String(50), nullable=False, index=True)
    service_period_start = Column(Date, nullable=True)
    service_period_end = Column(Date, nullable=True)
    earned_date = Column(Date, nullable=False, index=True)

    # Payment tracking
    payment_status = Column(String(50), default="pending", nullable=False, index=True)
    payment_due_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(200), nullable=True)

    # Additional details
    description = Column(String(500), nullable=True)
    calculation_notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, default=dict, nullable=False)

    # Tenant isolation
    tenant_id = Column(String(100), nullable=True, index=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reseller = relationship("Reseller", back_populates="commissions")

    # Indexes for performance
    __table_args__ = (
        Index("idx_commission_tenant_status", "tenant_id", "payment_status"),
        Index("idx_commission_reseller_period", "reseller_id", "commission_period"),
        Index("idx_commission_due_date", "payment_due_date"),
    )

    @property
    def is_overdue(self) -> bool:
        return self.payment_status == "pending" and self.payment_due_date and date.today() > self.payment_due_date

    @property
    def days_until_due(self) -> Optional[int]:
        if self.payment_due_date and self.payment_status == "pending":
            return (self.payment_due_date - date.today()).days
        return None

    def __repr__(self):
        return f"<ResellerCommission(id='{self.commission_id}', amount={self.commission_amount}, status='{self.payment_status}')>"


# Export all models
__all__ = [
    "Base",
    "ResellerApplication",
    "Reseller",
    "ResellerCustomer",
    "ResellerOpportunity",
    "ResellerCommission",
    "ResellerType",
    "ResellerStatus",
    "ApplicationStatus",
    "CommissionStructure",
]
