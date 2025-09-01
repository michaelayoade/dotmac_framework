"""
Reseller models for ISP Framework

Leverages shared reseller enums while maintaining separate table structures.
Follows DRY principles through shared enums and patterns.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from dotmac_isp.shared.database.base import BaseModel

# Import shared enums - reuse completely for DRY compliance
from dotmac_shared.sales.core.reseller_models import (
    ResellerType,
    ResellerStatus, 
    ResellerTier,
    CommissionStructure,
    ResellerCertificationStatus
)


class ISPReseller(BaseModel):
    """
    ISP reseller model with comprehensive partner management.
    Uses shared enums but independent table structure for tenant isolation.
    """
    
    __tablename__ = "isp_resellers"
    
    # Basic reseller information
    reseller_id = Column(String(100), nullable=False, unique=True, index=True)
    company_name = Column(String(300), nullable=False, index=True)
    legal_name = Column(String(300), nullable=True)
    doing_business_as = Column(String(300), nullable=True)
    
    # Classification using shared enums
    reseller_type = Column(SQLEnum(ResellerType), nullable=False, index=True)
    reseller_status = Column(
        SQLEnum(ResellerStatus), 
        default=ResellerStatus.PROSPECT, 
        nullable=False, 
        index=True
    )
    reseller_tier = Column(
        SQLEnum(ResellerTier), 
        default=ResellerTier.BRONZE, 
        nullable=False, 
        index=True
    )
    
    # Contact information
    primary_contact_name = Column(String(200), nullable=False)
    primary_contact_email = Column(String(255), nullable=False, index=True)
    primary_contact_phone = Column(String(20), nullable=True)
    
    # Business details
    tax_id = Column(String(50), nullable=True)
    business_license = Column(String(100), nullable=True)
    website_url = Column(String(500), nullable=True)
    business_address = Column(JSONB, nullable=True)
    
    # Service territories and capabilities
    service_territories = Column(JSONB, nullable=True)
    service_types_offered = Column(JSONB, nullable=True)  # internet, phone, tv, bundle
    installation_capabilities = Column(JSONB, nullable=True)  # fiber, wireless, etc
    
    # Partnership agreement
    agreement_start_date = Column(Date, nullable=True)
    agreement_end_date = Column(Date, nullable=True)
    agreement_type = Column(String(50), nullable=True)
    
    # Commission structure using shared enum
    commission_structure = Column(SQLEnum(CommissionStructure), nullable=True)
    base_commission_rate = Column(Numeric(5, 2), nullable=True)
    
    # Performance metrics
    total_customers = Column(Integer, default=0, nullable=False)
    active_customers = Column(Integer, default=0, nullable=False)
    lifetime_sales = Column(Numeric(15, 2), default=0, nullable=False)
    ytd_sales = Column(Numeric(15, 2), default=0, nullable=False)
    monthly_sales = Column(Numeric(12, 2), default=0, nullable=False)
    annual_quota = Column(Numeric(12, 2), nullable=True)
    
    # ISP-specific performance metrics
    customer_churn_rate = Column(Numeric(5, 2), nullable=True)
    average_install_time_days = Column(Integer, nullable=True)
    customer_satisfaction_score = Column(Numeric(3, 2), nullable=True)
    
    # Portal access
    portal_enabled = Column(Boolean, default=True, nullable=False)
    portal_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    portal_last_login = Column(DateTime, nullable=True)
    
    # Support and certification
    assigned_support_rep = Column(String(200), nullable=True)
    certification_status = Column(
        SQLEnum(ResellerCertificationStatus),
        default=ResellerCertificationStatus.NOT_REQUIRED,
        nullable=False
    )
    certification_date = Column(Date, nullable=True)
    
    # Custom fields
    custom_fields = Column(JSONB, default=dict, nullable=False)
    internal_notes = Column(Text, nullable=True)
    tags = Column(JSONB, default=list, nullable=False)
    
    # Relationships
    customers = relationship("ResellerCustomer", back_populates="reseller", cascade="all, delete-orphan")
    commissions = relationship("ResellerCommission", back_populates="reseller", cascade="all, delete-orphan")
    opportunities = relationship("ResellerOpportunity", back_populates="reseller", cascade="all, delete-orphan")
    applications = relationship("ResellerApplication", back_populates="approved_reseller")
    
    @property
    def is_active(self) -> bool:
        """Check if reseller is active and can operate."""
        return self.reseller_status == ResellerStatus.ACTIVE
    
    @property
    def commission_rate_display(self) -> str:
        """Get formatted commission rate for display."""
        if self.base_commission_rate:
            return f"{self.base_commission_rate}%"
        return "Not Set"
    
    def __repr__(self):
        return f"<ISPReseller(id='{self.reseller_id}', company='{self.company_name}', status='{self.reseller_status}')>"


class ResellerCustomer(BaseModel):
    """
    ISP customer-reseller relationship model.
    Tracks customers assigned to resellers for management.
    """
    
    __tablename__ = "isp_reseller_customers"
    
    # References
    reseller_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("isp_resellers.id"), 
        nullable=False, 
        index=True
    )
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Relationship details
    relationship_start_date = Column(Date, nullable=False, default=date.today)
    relationship_status = Column(String(50), default="active", nullable=False, index=True)
    assignment_type = Column(String(50), nullable=True)  # direct, referral, inherited
    
    # ISP-specific service tracking
    primary_service_type = Column(String(50), nullable=True)  # internet, phone, tv
    connection_type = Column(String(50), nullable=True)  # fiber, cable, dsl, wireless
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
    
    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSONB, default=dict, nullable=False)
    
    # Relationship
    reseller = relationship("ISPReseller", back_populates="customers")
    
    def __repr__(self):
        return f"<ResellerCustomer(reseller_id='{self.reseller_id}', customer_id='{self.customer_id}')>"


class ResellerOpportunity(BaseModel):
    """
    ISP sales opportunity managed by resellers.
    Tracks potential customers through the sales pipeline.
    """
    
    __tablename__ = "isp_reseller_opportunities"
    
    # References
    reseller_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("isp_resellers.id"), 
        nullable=False, 
        index=True
    )
    
    # Opportunity identification
    opportunity_id = Column(String(100), nullable=False, unique=True, index=True)
    opportunity_name = Column(String(300), nullable=False)
    
    # Prospect information
    prospect_name = Column(String(200), nullable=False)
    prospect_email = Column(String(255), nullable=True)
    prospect_phone = Column(String(20), nullable=True)
    prospect_address = Column(JSONB, nullable=True)
    
    # Opportunity details
    opportunity_type = Column(String(50), nullable=False)  # new_customer, upsell, renewal
    estimated_value = Column(Numeric(10, 2), nullable=True)
    probability = Column(Integer, default=50, nullable=False)
    
    # ISP-specific opportunity details
    desired_service_type = Column(String(50), nullable=True)
    desired_speed_mbps = Column(Integer, nullable=True)
    installation_address = Column(JSONB, nullable=True)
    service_availability_confirmed = Column(Boolean, default=False, nullable=False)
    technical_survey_completed = Column(Boolean, default=False, nullable=False)
    
    # Sales pipeline
    stage = Column(String(50), nullable=False, default="prospect", index=True)
    expected_close_date = Column(Date, nullable=True)
    actual_close_date = Column(Date, nullable=True)
    
    # Source and tracking
    lead_source = Column(String(100), nullable=True)
    first_contact_date = Column(Date, nullable=True)
    last_contact_date = Column(Date, nullable=True)
    
    # Commission planning
    estimated_commission = Column(Numeric(8, 2), nullable=True)
    
    # Additional information
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    next_action = Column(String(500), nullable=True)
    custom_fields = Column(JSONB, default=dict, nullable=False)
    
    # Relationship
    reseller = relationship("ISPReseller", back_populates="opportunities")
    
    @property
    def is_active(self) -> bool:
        """Check if opportunity is still active (not closed)."""
        return self.stage not in ["closed_won", "closed_lost"]
    
    @property
    def is_overdue(self) -> bool:
        """Check if opportunity is past expected close date."""
        return (
            self.expected_close_date 
            and date.today() > self.expected_close_date 
            and self.is_active
        )
    
    def __repr__(self):
        return f"<ResellerOpportunity(id='{self.opportunity_id}', name='{self.opportunity_name}', stage='{self.stage}')>"


class ResellerCommission(BaseModel):
    """
    ISP commission tracking for reseller payments.
    Tracks all commission calculations and payment status.
    """
    
    __tablename__ = "isp_reseller_commissions"
    
    # References
    reseller_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("isp_resellers.id"), 
        nullable=False, 
        index=True
    )
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    service_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Commission identification
    commission_id = Column(String(100), nullable=False, unique=True, index=True)
    commission_type = Column(String(50), nullable=False, index=True)
    
    # Financial details
    base_amount = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(10, 2), nullable=False)
    
    # ISP-specific commission details
    service_type = Column(String(50), nullable=True)  # internet, phone, tv
    service_tier = Column(String(50), nullable=True)  # basic, premium, enterprise
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
    custom_fields = Column(JSONB, default=dict, nullable=False)
    
    # Relationship
    reseller = relationship("ISPReseller", back_populates="commissions")
    
    @property
    def is_overdue(self) -> bool:
        """Check if commission payment is overdue."""
        return (
            self.payment_status == "pending" 
            and self.payment_due_date 
            and date.today() > self.payment_due_date
        )
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Calculate days until payment is due."""
        if self.payment_due_date and self.payment_status == "pending":
            return (self.payment_due_date - date.today()).days
        return None
    
    def __repr__(self):
        return f"<ResellerCommission(id='{self.commission_id}', amount={self.commission_amount}, status='{self.payment_status}')>"


class ResellerApplication(BaseModel):
    """
    Reseller application model for website signup flow.
    Manages the application and approval process for new resellers.
    """
    
    __tablename__ = "isp_reseller_applications"
    
    # Application identification
    application_id = Column(String(100), nullable=False, unique=True, index=True)
    application_status = Column(
        String(50), 
        default="submitted", 
        nullable=False, 
        index=True
    )  # submitted, under_review, approved, rejected, withdrawn
    
    # Company information (required for application)
    company_name = Column(String(300), nullable=False)
    legal_company_name = Column(String(300), nullable=True)
    website_url = Column(String(500), nullable=True)
    business_type = Column(String(100), nullable=True)
    years_in_business = Column(Integer, nullable=True)
    
    # Primary contact
    contact_name = Column(String(200), nullable=False)
    contact_title = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=False, index=True)
    contact_phone = Column(String(20), nullable=True)
    
    # Business details
    employee_count = Column(Integer, nullable=True)
    annual_revenue_range = Column(String(50), nullable=True)
    telecom_experience_years = Column(Integer, nullable=True)
    business_description = Column(Text, nullable=True)
    
    # Desired partnership details
    desired_territories = Column(JSONB, nullable=True)
    target_customer_segments = Column(JSONB, nullable=True)  # residential, business
    estimated_monthly_customers = Column(Integer, nullable=True)
    preferred_commission_structure = Column(String(50), nullable=True)
    
    # Application processing
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_by = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Approval/rejection details
    decision_date = Column(Date, nullable=True)
    decision_reason = Column(Text, nullable=True)
    approved_reseller_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("isp_resellers.id"), 
        nullable=True, 
        index=True
    )
    
    # Documents and attachments
    uploaded_documents = Column(JSONB, nullable=True)
    
    # Follow-up tracking
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_notes = Column(Text, nullable=True)
    next_contact_date = Column(Date, nullable=True)
    
    # Relationships
    approved_reseller = relationship("ISPReseller", back_populates="applications")
    
    def __repr__(self):
        return f"<ResellerApplication(id='{self.application_id}', company='{self.company_name}', status='{self.application_status}')>"
    
    @property
    def can_be_approved(self) -> bool:
        """Check if application can be approved."""
        return self.application_status in ["submitted", "under_review"]
    
    @property
    def is_pending_review(self) -> bool:
        """Check if application is awaiting review."""
        return self.application_status == "submitted"
    
    @property
    def days_since_submission(self) -> int:
        """Calculate days since application was submitted."""
        return (datetime.utcnow() - self.submitted_at).days


# Export models for easy importing
__all__ = [
    # ISP-specific models
    "ISPReseller",
    "ResellerCustomer", 
    "ResellerOpportunity",
    "ResellerCommission",
    "ResellerApplication",
    # Re-export shared enums for convenience
    "ResellerType",
    "ResellerStatus", 
    "ResellerTier",
    "CommissionStructure",
    "ResellerCertificationStatus"
]