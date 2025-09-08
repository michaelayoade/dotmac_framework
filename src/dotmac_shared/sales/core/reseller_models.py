"""
Reseller-specific models extending the shared sales service.
Supports both ISP Framework and Management Platform reseller operations.
"""

from datetime import date
from enum import Enum
from typing import Optional

try:
    from sqlalchemy import (
        JSON,
        Boolean,
        Column,
        Date,
        DateTime,
        Float,
        ForeignKey,
        Index,
        Integer,
        Numeric,
        String,
        Text,
    )
    from sqlalchemy import Enum as SQLEnum
    from sqlalchemy.dialects.postgresql import UUID
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlalchemy.orm import relationship

    # Import base classes from sales models
    from .models import AddressMixin, AuditMixin, ContactMixin, StatusMixin, TenantModel

    SQLALCHEMY_AVAILABLE = True

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Create minimal stubs
    Column = String = Text = Boolean = DateTime = Date = None
    Integer = Float = Numeric = JSON = ForeignKey = Index = None
    UUID = relationship = hybrid_property = SQLEnum = None
    TenantModel = StatusMixin = AuditMixin = ContactMixin = AddressMixin = None


class ResellerType(str, Enum):
    """Reseller types."""

    AUTHORIZED_DEALER = "authorized_dealer"
    VALUE_ADDED_RESELLER = "value_added_reseller"
    SYSTEM_INTEGRATOR = "system_integrator"
    DISTRIBUTOR = "distributor"
    TECHNOLOGY_PARTNER = "technology_partner"
    REFERRAL_PARTNER = "referral_partner"
    WHITE_LABEL = "white_label"
    FRANCHISE = "franchise"


class ResellerStatus(str, Enum):
    """Reseller status."""

    PROSPECT = "prospect"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING_APPROVAL = "pending_approval"


class ResellerTier(str, Enum):
    """Reseller tier levels."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    PREMIER = "premier"


class CommissionStructure(str, Enum):
    """Commission structure types."""

    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    TIERED = "tiered"
    VOLUME_BASED = "volume_based"
    HYBRID = "hybrid"


class ResellerCertificationStatus(str, Enum):
    """Certification status."""

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    IN_PROGRESS = "in_progress"
    CERTIFIED = "certified"
    EXPIRED = "expired"
    REVOKED = "revoked"


# SQLAlchemy models (only available if SQLAlchemy is installed)
if SQLALCHEMY_AVAILABLE:

    class Reseller(TenantModel, StatusMixin, AuditMixin, ContactMixin, AddressMixin):
        """Reseller partner management."""

        __tablename__ = "sales_resellers"

        # Reseller identification
        reseller_id = Column(String(100), nullable=False, unique=True, index=True)
        company_name = Column(String(300), nullable=False, index=True)
        legal_name = Column(String(300), nullable=True)
        doing_business_as = Column(String(300), nullable=True)

        # Classification
        reseller_type = Column(SQLEnum(ResellerType), nullable=False, index=True)
        reseller_status = Column(
            SQLEnum(ResellerStatus),
            default=ResellerStatus.PROSPECT,
            nullable=False,
            index=True,
        )
        reseller_tier = Column(
            SQLEnum(ResellerTier),
            default=ResellerTier.BRONZE,
            nullable=False,
            index=True,
        )

        # Business information
        tax_id = Column(String(50), nullable=True)
        business_license = Column(String(100), nullable=True)
        incorporation_date = Column(Date, nullable=True)
        employee_count = Column(Integer, nullable=True)
        annual_revenue = Column(Numeric(15, 2), nullable=True)

        # Contact information
        primary_contact_name = Column(String(200), nullable=False)
        primary_contact_title = Column(String(100), nullable=True)
        primary_contact_email = Column(String(255), nullable=False)
        primary_contact_phone = Column(String(20), nullable=True)

        # Secondary contacts
        sales_contact_name = Column(String(200), nullable=True)
        sales_contact_email = Column(String(255), nullable=True)
        sales_contact_phone = Column(String(20), nullable=True)

        tech_contact_name = Column(String(200), nullable=True)
        tech_contact_email = Column(String(255), nullable=True)
        tech_contact_phone = Column(String(20), nullable=True)

        billing_contact_name = Column(String(200), nullable=True)
        billing_contact_email = Column(String(255), nullable=True)
        billing_contact_phone = Column(String(20), nullable=True)

        # Geographic coverage
        territories_covered = Column(JSON, nullable=True)
        service_areas = Column(JSON, nullable=True)
        geographic_restrictions = Column(JSON, nullable=True)

        # Capabilities and focus
        technical_capabilities = Column(JSON, nullable=True)
        target_markets = Column(JSON, nullable=True)
        specializations = Column(JSON, nullable=True)
        customer_segments = Column(JSON, nullable=True)

        # Partnership terms
        agreement_start_date = Column(Date, nullable=True)
        agreement_end_date = Column(Date, nullable=True)
        agreement_type = Column(String(50), nullable=True)
        agreement_status = Column(String(50), nullable=True)

        # Commission and incentives
        commission_structure = Column(SQLEnum(CommissionStructure), nullable=True)
        base_commission_rate = Column(Numeric(5, 2), nullable=True)
        tiered_commission_rates = Column(JSON, nullable=True)
        volume_thresholds = Column(JSON, nullable=True)
        incentive_programs = Column(JSON, nullable=True)

        # Performance metrics
        lifetime_sales = Column(Numeric(15, 2), default=0, nullable=False)
        ytd_sales = Column(Numeric(15, 2), default=0, nullable=False)
        quarterly_sales = Column(Numeric(12, 2), default=0, nullable=False)
        monthly_sales = Column(Numeric(12, 2), default=0, nullable=False)

        # Sales targets and quotas
        annual_quota = Column(Numeric(12, 2), nullable=True)
        quarterly_quota = Column(Numeric(12, 2), nullable=True)
        quota_achievement_ytd = Column(Float, nullable=True)

        # Customer and opportunity metrics
        total_customers = Column(Integer, default=0, nullable=False)
        active_opportunities = Column(Integer, default=0, nullable=False)
        conversion_rate = Column(Float, nullable=True)
        average_deal_size = Column(Numeric(10, 2), nullable=True)

        # Certification and training
        certification_status = Column(
            SQLEnum(ResellerCertificationStatus),
            default=ResellerCertificationStatus.NOT_REQUIRED,
            nullable=False,
        )
        certification_date = Column(Date, nullable=True)
        certification_expiry = Column(Date, nullable=True)
        required_certifications = Column(JSON, nullable=True)
        completed_training = Column(JSON, nullable=True)

        # Support and resources
        dedicated_support_rep = Column(String(200), nullable=True, index=True)
        support_tier = Column(String(50), nullable=True)
        marketing_resources = Column(JSON, nullable=True)
        sales_tools_access = Column(JSON, nullable=True)

        # Financial information
        credit_limit = Column(Numeric(12, 2), nullable=True)
        payment_terms = Column(String(50), nullable=True)
        billing_method = Column(String(50), nullable=True)
        tax_exempt = Column(Boolean, default=False, nullable=False)

        # Portal and system access
        portal_enabled = Column(Boolean, default=True, nullable=False)
        portal_last_login = Column(DateTime, nullable=True)
        system_integrations = Column(JSON, nullable=True)
        api_access_enabled = Column(Boolean, default=False, nullable=False)

        # Marketing and branding
        marketing_approval_required = Column(Boolean, default=True, nullable=False)
        brand_guidelines_accepted = Column(Boolean, default=False, nullable=False)
        co_marketing_approved = Column(Boolean, default=False, nullable=False)
        logo_usage_approved = Column(Boolean, default=False, nullable=False)

        # Additional information
        special_terms = Column(Text, nullable=True)
        internal_notes = Column(Text, nullable=True)
        public_notes = Column(Text, nullable=True)
        tags = Column(JSON, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        opportunities = relationship(
            "ResellerOpportunity",
            back_populates="reseller",
            cascade="all, delete-orphan",
        )
        customers = relationship("ResellerCustomer", back_populates="reseller", cascade="all, delete-orphan")
        commissions = relationship(
            "ResellerCommission",
            back_populates="reseller",
            cascade="all, delete-orphan",
        )

        __table_args__ = (
            Index("ix_resellers_tenant_id", "tenant_id", "reseller_id", unique=True),
            Index("ix_resellers_type_status", "reseller_type", "reseller_status"),
            Index("ix_resellers_tier", "reseller_tier"),
            Index("ix_resellers_support_rep", "dedicated_support_rep"),
        )

        @hybrid_property
        def quota_achievement_percentage(self) -> Optional[float]:
            """Calculate quota achievement percentage."""
            if self.annual_quota and self.annual_quota > 0:
                return round(float(self.ytd_sales) / float(self.annual_quota) * 100, 2)
            return None

        @hybrid_property
        def is_certification_expired(self) -> bool:
            """Check if certification is expired."""
            return self.certification_expiry and date.today() > self.certification_expiry

        @hybrid_property
        def days_until_agreement_expiry(self) -> Optional[int]:
            """Calculate days until agreement expires."""
            if self.agreement_end_date:
                return (self.agreement_end_date - date.today()).days
            return None

        def __repr__(self):
            return (
                f"<Reseller(id='{self.reseller_id}', company='{self.company_name}', status='{self.reseller_status}')>"
            )

    class ResellerOpportunity(TenantModel, AuditMixin):
        """Opportunities managed by resellers."""

        __tablename__ = "sales_reseller_opportunities"

        # References
        reseller_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sales_resellers.id"),
            nullable=False,
            index=True,
        )
        opportunity_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sales_opportunities.id"),
            nullable=False,
            index=True,
        )

        # Reseller-specific information
        reseller_opportunity_id = Column(String(100), nullable=True)
        reseller_contact = Column(String(200), nullable=True)
        reseller_notes = Column(Text, nullable=True)

        # Commission and splits
        commission_rate = Column(Numeric(5, 2), nullable=True)
        commission_amount = Column(Numeric(10, 2), nullable=True)
        commission_paid = Column(Boolean, default=False, nullable=False)
        commission_paid_date = Column(Date, nullable=True)

        # Registration and approval
        registration_date = Column(Date, nullable=False, default=date.today)
        approved_date = Column(Date, nullable=True)
        approved_by = Column(String(200), nullable=True)

        # Additional information
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        reseller = relationship("Reseller", back_populates="opportunities")
        opportunity = relationship("Opportunity", foreign_keys=[opportunity_id])

        __table_args__ = (
            Index("ix_reseller_opportunities_reseller", "reseller_id"),
            Index("ix_reseller_opportunities_opportunity", "opportunity_id"),
        )

        def __repr__(self):
            return f"<ResellerOpportunity(reseller_id='{self.reseller_id}', opportunity_id='{self.opportunity_id}')>"

    class ResellerCustomer(TenantModel, AuditMixin):
        """Customers managed by resellers."""

        __tablename__ = "sales_reseller_customers"

        # References
        reseller_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sales_resellers.id"),
            nullable=False,
            index=True,
        )
        customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)

        # Customer relationship
        relationship_start = Column(Date, nullable=False, default=date.today)
        relationship_status = Column(String(50), default="active", nullable=False)

        # Service information
        services_provided = Column(JSON, nullable=True)
        support_level = Column(String(50), nullable=True)

        # Revenue tracking
        lifetime_value = Column(Numeric(12, 2), default=0, nullable=False)
        monthly_recurring_revenue = Column(Numeric(10, 2), default=0, nullable=False)

        # Additional information
        notes = Column(Text, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        reseller = relationship("Reseller", back_populates="customers")

        __table_args__ = (
            Index("ix_reseller_customers_reseller", "reseller_id"),
            Index("ix_reseller_customers_customer", "customer_id"),
            Index(
                "ix_reseller_customers_relationship",
                "reseller_id",
                "customer_id",
                unique=True,
            ),
        )

        def __repr__(self):
            return f"<ResellerCustomer(reseller_id='{self.reseller_id}', customer_id='{self.customer_id}')>"

    class ResellerCommission(TenantModel, AuditMixin):
        """Commission payments to resellers."""

        __tablename__ = "sales_reseller_commissions"

        # References
        reseller_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sales_resellers.id"),
            nullable=False,
            index=True,
        )
        opportunity_id = Column(UUID(as_uuid=True), nullable=True, index=True)

        # Commission details
        commission_id = Column(String(100), nullable=False, unique=True, index=True)
        commission_type = Column(String(50), nullable=False)  # new_sale, renewal, upsell, etc.
        commission_period = Column(String(50), nullable=False)  # Q1-2024, etc.

        # Financial information
        base_amount = Column(Numeric(12, 2), nullable=False)
        commission_rate = Column(Numeric(5, 2), nullable=False)
        commission_amount = Column(Numeric(10, 2), nullable=False)

        # Payment information
        payment_status = Column(String(50), default="pending", nullable=False, index=True)
        payment_date = Column(Date, nullable=True)
        payment_method = Column(String(50), nullable=True)
        payment_reference = Column(String(200), nullable=True)

        # Period information
        earned_date = Column(Date, nullable=False)
        due_date = Column(Date, nullable=False)

        # Additional information
        description = Column(Text, nullable=True)
        notes = Column(Text, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        reseller = relationship("Reseller", back_populates="commissions")

        __table_args__ = (
            Index("ix_reseller_commissions_reseller", "reseller_id"),
            Index("ix_reseller_commissions_period", "commission_period"),
            Index("ix_reseller_commissions_status_due", "payment_status", "due_date"),
        )

        @hybrid_property
        def is_overdue(self) -> bool:
            """Check if commission payment is overdue."""
            return self.payment_status == "pending" and date.today() > self.due_date

        def __repr__(self):
            return f"<ResellerCommission(id='{self.commission_id}', reseller_id='{self.reseller_id}', amount={self.commission_amount})>"

    class ResellerTraining(TenantModel, AuditMixin):
        """Training and certification tracking for resellers."""

        __tablename__ = "sales_reseller_training"

        # References
        reseller_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sales_resellers.id"),
            nullable=False,
            index=True,
        )

        # Training details
        training_id = Column(String(100), nullable=False, index=True)
        training_name = Column(String(300), nullable=False)
        training_type = Column(String(100), nullable=False)  # certification, product, sales, technical

        # Participants
        participant_name = Column(String(200), nullable=False)
        participant_email = Column(String(255), nullable=False)
        participant_role = Column(String(100), nullable=True)

        # Training status
        enrollment_date = Column(Date, nullable=False, default=date.today)
        start_date = Column(Date, nullable=True)
        completion_date = Column(Date, nullable=True)
        status = Column(String(50), default="enrolled", nullable=False, index=True)

        # Results
        score = Column(Float, nullable=True)
        passing_score = Column(Float, nullable=True)
        passed = Column(Boolean, nullable=True)
        certificate_issued = Column(Boolean, default=False, nullable=False)
        certificate_number = Column(String(100), nullable=True)

        # Expiration and renewal
        valid_until = Column(Date, nullable=True)
        renewal_required = Column(Boolean, default=False, nullable=False)
        renewal_date = Column(Date, nullable=True)

        # Additional information
        notes = Column(Text, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        reseller = relationship("Reseller")

        __table_args__ = (
            Index("ix_reseller_training_reseller", "reseller_id"),
            Index("ix_reseller_training_status", "status"),
            Index("ix_reseller_training_expiry", "valid_until"),
        )

        @hybrid_property
        def is_expired(self) -> bool:
            """Check if training/certification is expired."""
            return self.valid_until and date.today() > self.valid_until

        def __repr__(self):
            return f"<ResellerTraining(reseller_id='{self.reseller_id}', training='{self.training_name}', status='{self.status}')>"

else:
    # Create stub classes when SQLAlchemy is not available
    class Reseller:
        """Reseller model stub."""

        pass

    class ResellerOpportunity:
        """ResellerOpportunity model stub."""

        pass

    class ResellerCustomer:
        """ResellerCustomer model stub."""

        pass

    class ResellerCommission:
        """ResellerCommission model stub."""

        pass

    class ResellerTraining:
        """ResellerTraining model stub."""

        pass
