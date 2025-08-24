"""Resellers models for partner management, channel sales, and commission tracking."""

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


class PartnerType(str, Enum):
    """Partner types."""

    RESELLER = "reseller"
    DISTRIBUTOR = "distributor"
    AGENT = "agent"
    REFERRAL = "referral"
    VAR = "var"  # Value Added Reseller
    MSP = "msp"  # Managed Service Provider
    CHANNEL = "channel"
    AFFILIATE = "affiliate"


class PartnerStatus(str, Enum):
    """Partner status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    UNDER_REVIEW = "under_review"


class PartnerTier(str, Enum):
    """Partner tier levels."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    ELITE = "elite"


class CommissionStatus(str, Enum):
    """Commission status."""

    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class CommissionType(str, Enum):
    """Commission types."""

    FLAT_FEE = "flat_fee"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    BONUS = "bonus"
    OVERRIDE = "override"
    RESIDUAL = "residual"


class DealStatus(str, Enum):
    """Deal registration status."""

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WON = "won"
    LOST = "lost"


class CertificationStatus(str, Enum):
    """Certification status."""

    VALID = "valid"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class Partner(TenantModel, StatusMixin, AuditMixin, ContactMixin, AddressMixin):
    """Partners and reseller organizations."""

    __tablename__ = "reseller_partners"

    # Partner identification
    partner_code = Column(String(100), nullable=False, index=True)
    legal_name = Column(String(300), nullable=False)
    trade_name = Column(String(300), nullable=True)

    # Classification
    partner_type = Column(SQLEnum(PartnerType), nullable=False, index=True)
    partner_status = Column(
        SQLEnum(PartnerStatus),
        default=PartnerStatus.PENDING,
        nullable=False,
        index=True,
    )
    partner_tier = Column(
        SQLEnum(PartnerTier), default=PartnerTier.BRONZE, nullable=False, index=True
    )

    # Business information
    business_registration_number = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)
    duns_number = Column(String(20), nullable=True)

    # Contract details
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    contract_number = Column(String(100), nullable=True)
    auto_renewal = Column(Boolean, default=False, nullable=False)

    # Geographic and market coverage
    territories = Column(JSON, nullable=True)  # Geographic territories
    market_segments = Column(JSON, nullable=True)  # Target market segments
    verticals = Column(JSON, nullable=True)  # Industry verticals

    # Business metrics
    annual_revenue = Column(Numeric(15, 2), nullable=True)
    employee_count = Column(Integer, nullable=True)
    years_in_business = Column(Integer, nullable=True)

    # Partner capabilities
    technical_expertise = Column(JSON, nullable=True)
    service_offerings = Column(JSON, nullable=True)
    support_capabilities = Column(JSON, nullable=True)

    # Performance metrics
    sales_target = Column(Numeric(12, 2), nullable=True)
    ytd_sales = Column(Numeric(12, 2), default=0, nullable=False)
    customer_satisfaction = Column(Float, nullable=True)  # 1-5 rating

    # Commission and pricing
    default_commission_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    discount_level = Column(Numeric(5, 2), nullable=True)  # Percentage
    payment_terms = Column(String(100), nullable=True)

    # Banking information
    bank_name = Column(String(200), nullable=True)
    bank_account_number = Column(String(100), nullable=True)
    bank_routing_number = Column(String(50), nullable=True)
    payment_method = Column(String(50), default="bank_transfer", nullable=False)

    # Marketing support
    marketing_allowance = Column(Numeric(10, 2), nullable=True)
    co_op_funds_available = Column(Numeric(10, 2), default=0, nullable=False)
    co_op_funds_used = Column(Numeric(10, 2), default=0, nullable=False)

    # Online presence
    website_url = Column(String(500), nullable=True)
    social_media_links = Column(JSON, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    contacts = relationship(
        "PartnerContact", back_populates="partner", cascade="all, delete-orphan"
    )
    certifications = relationship(
        "PartnerCertification", back_populates="partner", cascade="all, delete-orphan"
    )
    deals = relationship("DealRegistration", back_populates="partner")
    commissions = relationship("Commission", back_populates="partner")

    __table_args__ = (
        Index("ix_partners_tenant_code", "tenant_id", "partner_code", unique=True),
        Index("ix_partners_type_status", "partner_type", "partner_status"),
        Index("ix_partners_tier", "partner_tier"),
    )

    @hybrid_property
    def contract_is_expiring(self) -> bool:
        """Check if contract is expiring within 90 days."""
        if not self.contract_end_date:
            return False
        days_to_expiry = (self.contract_end_date - date.today()).days
        return 0 <= days_to_expiry <= 90

    @hybrid_property
    def sales_target_achievement(self) -> Optional[float]:
        """Calculate sales target achievement percentage."""
        if self.sales_target and self.sales_target > 0:
            return round((float(self.ytd_sales) / float(self.sales_target)) * 100, 2)
        return None

    @hybrid_property
    def co_op_utilization(self) -> float:
        """Calculate co-op fund utilization percentage."""
        if self.co_op_funds_available and self.co_op_funds_available > 0:
            return round(
                (float(self.co_op_funds_used) / float(self.co_op_funds_available))
                * 100,
                2,
            )
        return 0.0

    def __repr__(self):
        """  Repr   operation."""
        return f"<Partner(code='{self.partner_code}', name='{self.legal_name}', type='{self.partner_type}')>"


class PartnerContact(TenantModel, AuditMixin, ContactMixin):
    """Partner contact persons."""

    __tablename__ = "reseller_partner_contacts"

    # Partner reference
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_partners.id"),
        nullable=False,
        index=True,
    )

    # Contact details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    job_title = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)

    # Contact classification
    contact_type = Column(
        String(50), nullable=False, index=True
    )  # primary, sales, technical, billing, etc.
    is_primary = Column(Boolean, default=False, nullable=False)

    # Availability
    business_hours = Column(JSON, nullable=True)
    time_zone = Column(String(50), nullable=True)
    preferred_contact_method = Column(String(50), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    partner = relationship("Partner", back_populates="contacts")

    __table_args__ = (
        Index("ix_partner_contacts_partner_type", "partner_id", "contact_type"),
        Index("ix_partner_contacts_primary", "partner_id", "is_primary"),
    )

    @hybrid_property
    def full_name(self) -> str:
        """Get contact's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        """  Repr   operation."""
        return f"<PartnerContact(partner_id='{self.partner_id}', name='{self.full_name}', type='{self.contact_type}')>"


class PartnerCertification(TenantModel, AuditMixin):
    """Partner certifications and qualifications."""

    __tablename__ = "reseller_partner_certifications"

    # Partner reference
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_partners.id"),
        nullable=False,
        index=True,
    )

    # Certification details
    certification_name = Column(String(300), nullable=False)
    certification_code = Column(String(100), nullable=True)
    issuing_organization = Column(String(200), nullable=False)

    # Certification status
    certification_status = Column(
        SQLEnum(CertificationStatus),
        default=CertificationStatus.VALID,
        nullable=False,
        index=True,
    )

    # Dates
    issued_date = Column(Date, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=True)

    # Requirements and maintenance
    requirements_met = Column(JSON, nullable=True)
    maintenance_required = Column(Boolean, default=False, nullable=False)
    renewal_required = Column(Boolean, default=True, nullable=False)

    # Certificate details
    certificate_number = Column(String(200), nullable=True)
    certificate_url = Column(String(500), nullable=True)
    verification_url = Column(String(500), nullable=True)

    # Benefits and privileges
    tier_benefits = Column(JSON, nullable=True)
    discount_eligibility = Column(JSON, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    partner = relationship("Partner", back_populates="certifications")

    __table_args__ = (
        Index("ix_certifications_partner_status", "partner_id", "certification_status"),
        Index("ix_certifications_expiry", "valid_until"),
    )

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if certification is expired."""
        return self.valid_until and date.today() > self.valid_until

    @hybrid_property
    def days_to_expiry(self) -> Optional[int]:
        """Calculate days until certification expires."""
        if self.valid_until:
            return (self.valid_until - date.today()).days
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<PartnerCertification(partner_id='{self.partner_id}', name='{self.certification_name}')>"


class DealRegistration(TenantModel, AuditMixin):
    """Deal registrations for partner opportunities."""

    __tablename__ = "reseller_deal_registrations"

    # Deal identification
    deal_number = Column(String(100), nullable=False, unique=True, index=True)
    deal_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Partner reference
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_partners.id"),
        nullable=False,
        index=True,
    )

    # Customer information
    customer_name = Column(String(300), nullable=False)
    customer_contact = Column(String(200), nullable=True)
    customer_email = Column(String(255), nullable=True)
    end_customer_name = Column(String(300), nullable=True)  # For distributor deals

    # Deal details
    deal_value = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    products = Column(JSON, nullable=False)  # List of products/services

    # Timeline
    registration_date = Column(Date, nullable=False, default=date.today)
    expected_close_date = Column(Date, nullable=False)
    protection_period_end = Column(Date, nullable=True)

    # Status and approval
    deal_status = Column(
        SQLEnum(DealStatus), default=DealStatus.SUBMITTED, nullable=False, index=True
    )
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Competition and positioning
    competitors = Column(JSON, nullable=True)
    competitive_situation = Column(Text, nullable=True)
    partner_advantages = Column(Text, nullable=True)

    # Commission and pricing
    commission_rate = Column(Numeric(5, 2), nullable=True)
    special_pricing = Column(Boolean, default=False, nullable=False)
    pricing_notes = Column(Text, nullable=True)

    # Support requirements
    technical_support_needed = Column(Boolean, default=False, nullable=False)
    presales_support_needed = Column(Boolean, default=False, nullable=False)
    support_requirements = Column(Text, nullable=True)

    # Outcome tracking
    actual_close_date = Column(Date, nullable=True)
    actual_deal_value = Column(Numeric(12, 2), nullable=True)
    win_loss_reason = Column(Text, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    partner = relationship("Partner", back_populates="deals")

    __table_args__ = (
        Index("ix_deals_partner_status", "partner_id", "deal_status"),
        Index("ix_deals_close_date", "expected_close_date"),
        Index("ix_deals_value", "deal_value"),
    )

    @hybrid_property
    def is_protected(self) -> bool:
        """Check if deal is still in protection period."""
        return self.protection_period_end and date.today() <= self.protection_period_end

    @hybrid_property
    def days_to_close(self) -> int:
        """Calculate days until expected close."""
        return (self.expected_close_date - date.today()).days

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if deal is overdue."""
        return (
            self.deal_status not in [DealStatus.WON, DealStatus.LOST]
            and date.today() > self.expected_close_date
        )

    def __repr__(self):
        """  Repr   operation."""
        return f"<DealRegistration(number='{self.deal_number}', partner_id='{self.partner_id}', value={self.deal_value})>"


class Commission(TenantModel, AuditMixin):
    """Commission calculations and payments."""

    __tablename__ = "reseller_commissions"

    # Commission identification
    commission_id = Column(String(100), nullable=False, unique=True, index=True)

    # References
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_partners.id"),
        nullable=False,
        index=True,
    )
    deal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_deal_registrations.id"),
        nullable=True,
        index=True,
    )
    sale_id = Column(String(100), nullable=True, index=True)  # External sale reference

    # Commission details
    commission_type = Column(SQLEnum(CommissionType), nullable=False, index=True)
    commission_period = Column(String(50), nullable=False)  # Q1-2024, Jan-2024, etc.

    # Financial details
    base_amount = Column(
        Numeric(12, 2), nullable=False
    )  # Amount commission is calculated on
    commission_rate = Column(Numeric(5, 2), nullable=False)  # Percentage or flat amount
    commission_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    # Tax handling
    tax_withholding = Column(Numeric(10, 2), default=0, nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False)

    # Status and processing
    commission_status = Column(
        SQLEnum(CommissionStatus),
        default=CommissionStatus.PENDING,
        nullable=False,
        index=True,
    )
    calculation_date = Column(Date, nullable=False, default=date.today)
    approval_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)

    # Payment details
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(200), nullable=True)
    payment_batch = Column(String(100), nullable=True)

    # Product/service details
    product_category = Column(String(100), nullable=True)
    products = Column(JSON, nullable=True)

    # Approval workflow
    approved_by = Column(String(200), nullable=True)
    approval_notes = Column(Text, nullable=True)

    # Dispute handling
    disputed_amount = Column(Numeric(10, 2), nullable=True)
    dispute_reason = Column(Text, nullable=True)
    dispute_resolution = Column(Text, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    partner = relationship("Partner", back_populates="commissions")
    deal = relationship("DealRegistration")

    __table_args__ = (
        Index("ix_commissions_partner_period", "partner_id", "commission_period"),
        Index("ix_commissions_status_date", "commission_status", "calculation_date"),
        Index("ix_commissions_payment_date", "payment_date"),
    )

    @hybrid_property
    def effective_rate(self) -> float:
        """Calculate effective commission rate."""
        if self.base_amount and self.base_amount > 0:
            return round(
                (float(self.commission_amount) / float(self.base_amount)) * 100, 2
            )
        return 0.0

    @hybrid_property
    def days_since_calculation(self) -> int:
        """Calculate days since commission was calculated."""
        return (date.today() - self.calculation_date).days

    def __repr__(self):
        """  Repr   operation."""
        return f"<Commission(id='{self.commission_id}', partner_id='{self.partner_id}', amount={self.commission_amount})>"


class PartnerProgram(TenantModel, StatusMixin, AuditMixin):
    """Partner programs and initiatives."""

    __tablename__ = "reseller_partner_programs"

    # Program identification
    program_code = Column(String(100), nullable=False, index=True)
    program_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Program details
    program_type = Column(
        String(100), nullable=False
    )  # certification, incentive, training, etc.
    eligibility_criteria = Column(JSON, nullable=True)

    # Timeline
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    registration_deadline = Column(Date, nullable=True)

    # Benefits and rewards
    benefits = Column(JSON, nullable=False)
    rewards = Column(JSON, nullable=True)
    incentive_structure = Column(JSON, nullable=True)

    # Requirements
    participation_requirements = Column(JSON, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    reporting_requirements = Column(JSON, nullable=True)

    # Enrollment and participation
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0, nullable=False)
    auto_enrollment = Column(Boolean, default=False, nullable=False)

    # Program management
    program_manager = Column(String(200), nullable=True)
    budget_allocated = Column(Numeric(12, 2), nullable=True)
    budget_used = Column(Numeric(12, 2), default=0, nullable=False)

    # Communication
    communication_plan = Column(JSON, nullable=True)
    marketing_materials = Column(JSON, nullable=True)

    # Additional information
    terms_and_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    enrollments = relationship(
        "ProgramEnrollment", back_populates="program", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_programs_tenant_code", "tenant_id", "program_code", unique=True),
        Index("ix_programs_dates", "start_date", "end_date"),
        Index("ix_programs_type", "program_type"),
    )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if program is currently active."""
        today = date.today()
        return self.start_date <= today and (
            not self.end_date or today <= self.end_date
        )

    @hybrid_property
    def enrollment_capacity(self) -> Optional[float]:
        """Calculate enrollment capacity percentage."""
        if self.max_participants:
            return round((self.current_participants / self.max_participants) * 100, 2)
        return None

    def __repr__(self):
        """  Repr   operation."""
        return (
            f"<PartnerProgram(code='{self.program_code}', name='{self.program_name}')>"
        )


class ProgramEnrollment(TenantModel, AuditMixin):
    """Partner enrollments in programs."""

    __tablename__ = "reseller_program_enrollments"

    # References
    program_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_partner_programs.id"),
        nullable=False,
        index=True,
    )
    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reseller_partners.id"),
        nullable=False,
        index=True,
    )

    # Enrollment details
    enrollment_date = Column(Date, nullable=False, default=date.today)
    enrollment_status = Column(String(50), default="active", nullable=False, index=True)
    completion_date = Column(Date, nullable=True)

    # Progress tracking
    progress_percentage = Column(Integer, default=0, nullable=False)
    milestones_completed = Column(JSON, nullable=True)
    requirements_met = Column(JSON, nullable=True)

    # Performance
    performance_score = Column(Float, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    achievements = Column(JSON, nullable=True)

    # Benefits received
    benefits_claimed = Column(JSON, nullable=True)
    rewards_earned = Column(JSON, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    program = relationship("PartnerProgram", back_populates="enrollments")
    partner = relationship("Partner")

    __table_args__ = (
        Index(
            "ix_enrollments_program_partner", "program_id", "partner_id", unique=True
        ),
        Index("ix_enrollments_status", "enrollment_status"),
    )

    @hybrid_property
    def is_completed(self) -> bool:
        """Check if enrollment is completed."""
        return self.enrollment_status == "completed" or self.completion_date is not None

    def __repr__(self):
        """  Repr   operation."""
        return f"<ProgramEnrollment(program_id='{self.program_id}', partner_id='{self.partner_id}')>"
