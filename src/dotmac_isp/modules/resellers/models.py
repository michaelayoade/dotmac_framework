"""Reseller database models for partner and channel management."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dotmac_shared.db.mixins import AuditMixin, TenantMixin
from dotmac_shared.db.models import Base


class ResellerStatus(str, Enum):
    """Reseller status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"
    TERMINATED = "terminated"


class ResellerType(str, Enum):
    """Reseller type enumeration."""
    PARTNER = "partner"
    DISTRIBUTOR = "distributor"
    AGENT = "agent"
    AFFILIATE = "affiliate"
    VAR = "var"  # Value Added Reseller
    MSP = "msp"  # Managed Service Provider


class ResellerTier(str, Enum):
    """Reseller tier enumeration for performance-based classification."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class CommissionStatus(str, Enum):
    """Commission payment status."""
    PENDING = "pending"
    CALCULATED = "calculated"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class Reseller(Base, TenantMixin, AuditMixin):
    """Model for reseller/partner management."""

    __tablename__ = "resellers"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Company Information
    company_name = Column(String(200), nullable=False)
    business_registration_number = Column(String(100))
    tax_identification_number = Column(String(100))
    website = Column(String(200))
    
    # Reseller Classification
    reseller_type = Column(Enum(ResellerType), nullable=False, default=ResellerType.PARTNER)
    reseller_tier = Column(Enum(ResellerTier), nullable=False, default=ResellerTier.BRONZE)
    status = Column(Enum(ResellerStatus), nullable=False, default=ResellerStatus.PENDING_APPROVAL)
    
    # Contact Information
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20))
    contact_person = Column(String(100))
    contact_person_title = Column(String(100))
    
    # Address Information
    billing_address = Column(Text)
    shipping_address = Column(Text)
    billing_country = Column(String(2))  # ISO country code
    billing_currency = Column(String(3))  # ISO currency code
    
    # Commission and Financial
    commission_rate = Column(Numeric(5, 4), nullable=False, default=Decimal('0.10'))  # 10%
    payment_terms_days = Column(Integer, default=30)
    minimum_payout_amount = Column(Numeric(10, 2), default=Decimal('100.00'))
    
    # Geographic Coverage
    territories = Column(JSON, default=list)  # List of territories/regions
    allowed_countries = Column(JSON, default=list)
    restricted_countries = Column(JSON, default=list)
    
    # Contract Information
    contract_start_date = Column(DateTime, nullable=False)
    contract_end_date = Column(DateTime)
    contract_number = Column(String(100))
    auto_renew = Column(Boolean, default=False)
    
    # Performance and Targets
    sales_target_annual = Column(Numeric(12, 2))
    sales_target_quarterly = Column(Numeric(12, 2))
    performance_targets = Column(JSON, default=dict)
    current_tier_requirements = Column(JSON, default=dict)
    
    # Settings and Configuration
    allow_self_provisioning = Column(Boolean, default=False)
    require_approval_for_orders = Column(Boolean, default=True)
    api_access_enabled = Column(Boolean, default=False)
    portal_access_enabled = Column(Boolean, default=True)
    
    # Marketing and Branding
    marketing_materials_approved = Column(Boolean, default=False)
    use_co_branding = Column(Boolean, default=False)
    logo_url = Column(String(500))
    brand_guidelines = Column(JSON, default=dict)
    
    # Internal Notes and Metadata
    internal_notes = Column(Text)
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    reseller_contacts = relationship("ResellerContact", back_populates="reseller", cascade="all, delete-orphan")
    reseller_opportunities = relationship("ResellerOpportunity", back_populates="reseller", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="reseller", cascade="all, delete-orphan")
    performance_records = relationship("ResellerPerformance", back_populates="reseller", cascade="all, delete-orphan")
    territory_assignments = relationship("ResellerTerritory", back_populates="reseller", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "company_name", name="uq_reseller_tenant_company"),
        UniqueConstraint("tenant_id", "contact_email", name="uq_reseller_tenant_email"),
        Index("idx_reseller_type", "reseller_type"),
        Index("idx_reseller_tier", "reseller_tier"),
        Index("idx_reseller_status", "status"),
        Index("idx_reseller_territories", "territories"),
    )

    def __repr__(self):
        return f"<Reseller(id={self.id}, company_name={self.company_name}, type={self.reseller_type})>"


class ResellerContact(Base, TenantMixin, AuditMixin):
    """Model for additional reseller contact persons."""

    __tablename__ = "reseller_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    contact_type = Column(String(50), nullable=False)  # primary, technical, billing, sales
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(100))
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    mobile = Column(String(20))
    department = Column(String(100))
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    preferred_language = Column(String(5))  # ISO language code
    
    reseller = relationship("Reseller", back_populates="reseller_contacts")

    __table_args__ = (
        Index("idx_reseller_contact_reseller", "reseller_id"),
        Index("idx_reseller_contact_type", "contact_type"),
        Index("idx_reseller_contact_primary", "is_primary"),
    )

    def __repr__(self):
        return f"<ResellerContact(id={self.id}, name={self.first_name} {self.last_name}, type={self.contact_type})>"


class ResellerOpportunity(Base, TenantMixin, AuditMixin):
    """Model for tracking opportunities assigned to resellers."""

    __tablename__ = "reseller_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    opportunity_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to CRM opportunity
    
    assigned_date = Column(DateTime, nullable=False, default=func.now())
    expected_close_date = Column(DateTime)
    actual_close_date = Column(DateTime)
    
    opportunity_value = Column(Numeric(12, 2))
    commission_override = Column(Numeric(5, 4))  # Override default commission rate
    status = Column(String(50), nullable=False, default="assigned")
    stage = Column(String(50))
    probability = Column(Integer)  # 0-100
    
    notes = Column(Text)
    internal_notes = Column(Text)
    
    reseller = relationship("Reseller", back_populates="reseller_opportunities")

    __table_args__ = (
        UniqueConstraint("reseller_id", "opportunity_id", name="uq_reseller_opportunity"),
        Index("idx_reseller_opportunity_reseller", "reseller_id"),
        Index("idx_reseller_opportunity_status", "status"),
        Index("idx_reseller_opportunity_assigned", "assigned_date"),
    )

    def __repr__(self):
        return f"<ResellerOpportunity(id={self.id}, reseller_id={self.reseller_id}, opportunity_id={self.opportunity_id})>"


class Commission(Base, TenantMixin, AuditMixin):
    """Model for tracking reseller commissions."""

    __tablename__ = "commissions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Transaction References
    opportunity_id = Column(UUID(as_uuid=True))  # Reference to opportunity
    customer_id = Column(UUID(as_uuid=True))  # Reference to customer
    order_id = Column(UUID(as_uuid=True))  # Reference to order/invoice
    
    # Commission Calculation
    sale_amount = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    commission_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    
    # Commission Details
    commission_type = Column(String(50), default="standard")  # standard, bonus, override
    commission_period = Column(String(20))  # monthly, quarterly, annual
    earned_date = Column(DateTime, nullable=False, default=func.now())
    due_date = Column(DateTime)
    
    # Payment Information
    payment_status = Column(Enum(CommissionStatus), nullable=False, default=CommissionStatus.PENDING)
    payment_date = Column(DateTime)
    payment_reference = Column(String(100))
    payment_method = Column(String(50))
    
    # Adjustments and Notes
    adjustment_amount = Column(Numeric(10, 2), default=Decimal('0.00'))
    adjustment_reason = Column(String(500))
    notes = Column(Text)
    
    reseller = relationship("Reseller", back_populates="commissions")

    __table_args__ = (
        Index("idx_commission_reseller", "reseller_id"),
        Index("idx_commission_status", "payment_status"),
        Index("idx_commission_earned", "earned_date"),
        Index("idx_commission_due", "due_date"),
        Index("idx_commission_opportunity", "opportunity_id"),
    )

    def __repr__(self):
        return f"<Commission(id={self.id}, reseller_id={self.reseller_id}, amount={self.commission_amount})>"


class ResellerPerformance(Base, TenantMixin, AuditMixin):
    """Model for tracking reseller performance metrics."""

    __tablename__ = "reseller_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Performance Period
    period_type = Column(String(20), nullable=False)  # monthly, quarterly, annual
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Sales Metrics
    total_sales = Column(Numeric(12, 2), default=Decimal('0.00'))
    total_orders = Column(Integer, default=0)
    new_customers_acquired = Column(Integer, default=0)
    customers_retained = Column(Integer, default=0)
    average_deal_size = Column(Numeric(10, 2), default=Decimal('0.00'))
    
    # Commission Metrics
    total_commissions_earned = Column(Numeric(10, 2), default=Decimal('0.00'))
    commissions_paid = Column(Numeric(10, 2), default=Decimal('0.00'))
    commissions_pending = Column(Numeric(10, 2), default=Decimal('0.00'))
    
    # Performance Indicators
    quota_achievement = Column(Numeric(5, 2))  # Percentage of quota achieved
    customer_satisfaction_score = Column(Numeric(3, 2))  # 1-5 scale
    lead_conversion_rate = Column(Numeric(5, 2))  # Percentage
    
    # Activity Metrics
    opportunities_created = Column(Integer, default=0)
    opportunities_won = Column(Integer, default=0)
    opportunities_lost = Column(Integer, default=0)
    meetings_held = Column(Integer, default=0)
    proposals_submitted = Column(Integer, default=0)
    
    # Rankings and Comparisons
    rank_in_tier = Column(Integer)
    rank_overall = Column(Integer)
    performance_score = Column(Numeric(5, 2))
    
    # Additional Metrics
    metrics = Column(JSON, default=dict)  # Flexible storage for additional KPIs
    notes = Column(Text)
    
    reseller = relationship("Reseller", back_populates="performance_records")

    __table_args__ = (
        UniqueConstraint("reseller_id", "period_type", "period_start", name="uq_reseller_performance_period"),
        Index("idx_reseller_performance_reseller", "reseller_id"),
        Index("idx_reseller_performance_period", "period_start", "period_end"),
        Index("idx_reseller_performance_type", "period_type"),
    )

    def __repr__(self):
        return f"<ResellerPerformance(id={self.id}, reseller_id={self.reseller_id}, period={self.period_type})>"


class ResellerTerritory(Base, TenantMixin, AuditMixin):
    """Model for managing reseller territory assignments."""

    __tablename__ = "reseller_territories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    territory_name = Column(String(100), nullable=False)
    territory_type = Column(String(50), nullable=False)  # country, state, region, city, postal_code
    territory_value = Column(String(100), nullable=False)  # The actual territory identifier
    
    # Territory Details
    is_exclusive = Column(Boolean, default=False)
    priority_level = Column(Integer, default=1)  # 1=highest, 5=lowest
    assigned_date = Column(DateTime, nullable=False, default=func.now())
    effective_date = Column(DateTime)
    expiry_date = Column(DateTime)
    
    # Performance in Territory
    target_revenue = Column(Numeric(12, 2))
    actual_revenue = Column(Numeric(12, 2), default=Decimal('0.00'))
    customer_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    
    reseller = relationship("Reseller", back_populates="territory_assignments")

    __table_args__ = (
        Index("idx_reseller_territory_reseller", "reseller_id"),
        Index("idx_reseller_territory_type", "territory_type"),
        Index("idx_reseller_territory_value", "territory_value"),
        Index("idx_reseller_territory_active", "is_active"),
        Index("idx_reseller_territory_exclusive", "is_exclusive"),
    )

    def __repr__(self):
        return f"<ResellerTerritory(id={self.id}, reseller_id={self.reseller_id}, territory={self.territory_name})>"


class ResellerAgreement(Base, TenantMixin, AuditMixin):
    """Model for tracking reseller agreements and contracts."""

    __tablename__ = "reseller_agreements"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("resellers.id"), nullable=False)
    
    # Agreement Details
    agreement_number = Column(String(100), nullable=False)
    agreement_type = Column(String(50), nullable=False)  # partner, distributor, msp
    agreement_title = Column(String(200))
    
    # Dates and Terms
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime)
    signature_date = Column(DateTime)
    renewal_date = Column(DateTime)
    
    # Terms and Conditions
    terms_version = Column(String(20))
    auto_renewal = Column(Boolean, default=False)
    renewal_notice_days = Column(Integer, default=90)
    termination_notice_days = Column(Integer, default=30)
    
    # Financial Terms
    minimum_commitment = Column(Numeric(12, 2))
    commitment_period_months = Column(Integer, default=12)
    volume_discounts = Column(JSON, default=dict)
    payment_terms = Column(JSON, default=dict)
    
    # Document Management
    document_url = Column(String(500))
    signed_document_url = Column(String(500))
    status = Column(String(50), nullable=False, default="draft")
    
    # Approval Workflow
    approved_by = Column(UUID(as_uuid=True))  # User ID
    approved_date = Column(DateTime)
    legal_review_completed = Column(Boolean, default=False)
    compliance_approved = Column(Boolean, default=False)
    
    notes = Column(Text)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("tenant_id", "agreement_number", name="uq_reseller_agreement_number"),
        Index("idx_reseller_agreement_reseller", "reseller_id"),
        Index("idx_reseller_agreement_status", "status"),
        Index("idx_reseller_agreement_effective", "effective_date"),
        Index("idx_reseller_agreement_expiry", "expiry_date"),
    )

    def __repr__(self):
        return f"<ResellerAgreement(id={self.id}, reseller_id={self.reseller_id}, number={self.agreement_number})>"