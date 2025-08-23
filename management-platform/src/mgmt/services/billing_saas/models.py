"""
SaaS billing database models for subscription management and revenue tracking.
"""

from datetime import datetime, date
from enum import Enum
from typing import Dict, Any, Optional, List
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    Text,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
    Numeric,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class BillingCycle(str, Enum):
    """Billing cycle enumeration."""
    
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class CommissionType(str, Enum):
    """Commission type enumeration."""
    
    INITIAL = "initial"  # First sale commission
    RECURRING = "recurring"  # Monthly recurring commission
    RENEWAL = "renewal"  # Renewal commission
    UPSELL = "upsell"  # Upsell/expansion commission
    BONUS = "bonus"  # Performance bonus
    OVERRIDE = "override"  # Manager override commission


class PricingTier(Base):
    """
    Pricing tier definitions for SaaS subscriptions.
    
    This model defines the available subscription tiers, their features,
    limits, and pricing information.
    """
    
    __tablename__ = "pricing_tiers"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Tier identification
    tier_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing information
    monthly_price = Column(Numeric(10, 2), nullable=False, default=0)
    quarterly_price = Column(Numeric(10, 2), nullable=True)
    annual_price = Column(Numeric(10, 2), nullable=True)
    
    # Resource limits
    max_customers = Column(Integer, nullable=False, default=1000)
    max_services = Column(Integer, nullable=False, default=10000)
    max_storage_gb = Column(Integer, nullable=False, default=100)
    max_bandwidth_gb = Column(Integer, nullable=False, default=1000)
    max_api_requests = Column(Integer, nullable=False, default=100000)
    max_users = Column(Integer, nullable=False, default=10)
    
    # Features
    features = Column(JSON, nullable=True, default=list)
    feature_flags = Column(JSON, nullable=True, default=dict)
    
    # Availability
    is_active = Column(Boolean, nullable=False, default=True)
    is_public = Column(Boolean, nullable=False, default=True)  # Public or private tier
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="pricing_tier")
    
    def __repr__(self) -> str:
        return f"<PricingTier(tier_id='{self.tier_id}', name='{self.name}')>"
    
    def get_price_for_cycle(self, billing_cycle: BillingCycle) -> Optional[Decimal]:
        """Get price for specific billing cycle."""
        if billing_cycle == BillingCycle.MONTHLY:
            return self.monthly_price
        elif billing_cycle == BillingCycle.QUARTERLY:
            return self.quarterly_price or (self.monthly_price * 3)
        elif billing_cycle == BillingCycle.ANNUAL:
            return self.annual_price or (self.monthly_price * 12)
        return None


class Subscription(Base):
    """
    Subscription model for tenant billing management.
    
    This model tracks the subscription lifecycle, billing cycles, and
    subscription-specific settings for each tenant.
    """
    
    __tablename__ = "subscriptions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Subscription identification
    subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)  # Links to tenant
    
    # Pricing and billing
    pricing_tier_id = Column(PGUUID(as_uuid=True), ForeignKey("pricing_tiers.id"), nullable=False)
    billing_cycle = Column(SQLEnum(BillingCycle), nullable=False, default=BillingCycle.MONTHLY)
    
    # Subscription status
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Billing periods
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    next_billing_date = Column(DateTime, nullable=False)
    
    # Trial information
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Pricing overrides
    custom_monthly_price = Column(Numeric(10, 2), nullable=True)  # Override default pricing
    discount_percentage = Column(Numeric(5, 2), nullable=True, default=0)  # Discount applied
    
    # Usage-based billing
    usage_based_billing = Column(Boolean, nullable=False, default=False)
    usage_multipliers = Column(JSON, nullable=True, default=dict)  # Custom usage rates
    
    # Payment information
    payment_method_id = Column(String(255), nullable=True)  # External payment method reference
    last_payment_date = Column(DateTime, nullable=True)
    next_payment_attempt = Column(DateTime, nullable=True)
    failed_payment_attempts = Column(Integer, nullable=False, default=0)
    
    # Subscription lifecycle
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    canceled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String(255), nullable=True)
    
    # Metadata and notes
    billing_metadata = Column(JSON, nullable=True, default=dict)
    internal_notes = Column(Text, nullable=True)
    
    # Relationships
    pricing_tier = relationship("PricingTier", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="subscription", cascade="all, delete-orphan")
    commission_records = relationship("CommissionRecord", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription(subscription_id='{self.subscription_id}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status == SubscriptionStatus.ACTIVE
    
    @property
    def is_in_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end
    
    @property
    def current_monthly_revenue(self) -> Decimal:
        """Calculate current monthly revenue for this subscription."""
        if self.custom_monthly_price:
            base_price = self.custom_monthly_price
        else:
            base_price = self.pricing_tier.monthly_price
        
        # Apply discount
        if self.discount_percentage:
            discount_multiplier = (100 - self.discount_percentage) / 100
            base_price *= discount_multiplier
        
        # Adjust for billing cycle
        if self.billing_cycle == BillingCycle.QUARTERLY:
            return base_price * 3
        elif self.billing_cycle == BillingCycle.ANNUAL:
            return base_price * 12
        
        return base_price


class UsageRecord(Base):
    """
    Usage tracking for billing and resource monitoring.
    
    This model tracks resource usage that feeds into usage-based billing
    calculations and provides data for analytics and monitoring.
    """
    
    __tablename__ = "usage_records"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Links to subscription
    subscription_id = Column(PGUUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Usage period
    usage_date = Column(Date, nullable=False, index=True)
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    
    # Usage metrics
    api_requests = Column(Integer, nullable=False, default=0)
    customers_count = Column(Integer, nullable=False, default=0)
    services_count = Column(Integer, nullable=False, default=0)
    storage_gb = Column(Numeric(10, 3), nullable=False, default=0)
    bandwidth_gb = Column(Numeric(10, 3), nullable=False, default=0)
    
    # Feature usage
    feature_usage = Column(JSON, nullable=True, default=dict)
    
    # Calculated charges
    base_charge = Column(Numeric(10, 2), nullable=False, default=0)
    usage_charges = Column(Numeric(10, 2), nullable=False, default=0)
    overage_charges = Column(Numeric(10, 2), nullable=False, default=0)
    total_charge = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Processing status
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    raw_data = Column(JSON, nullable=True)  # Raw usage data for auditing
    
    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")
    
    def __repr__(self) -> str:
        return f"<UsageRecord(tenant_id='{self.tenant_id}', date='{self.usage_date}')>"


class Invoice(Base):
    """
    Invoice model for subscription billing.
    
    This model represents invoices generated for subscriptions, including
    line items, taxes, payments, and invoice lifecycle tracking.
    """
    
    __tablename__ = "invoices"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Invoice identification
    invoice_id = Column(String(255), unique=True, nullable=False, index=True)
    invoice_number = Column(String(100), unique=True, nullable=False)
    
    # Links to subscription
    subscription_id = Column(PGUUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Invoice status and dates
    status = Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    invoice_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    
    # Financial amounts
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(5, 4), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Payment tracking
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0)
    amount_due = Column(Numeric(10, 2), nullable=False, default=0)
    payment_date = Column(DateTime, nullable=True)
    payment_method = Column(String(100), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # Line items and details
    line_items = Column(JSON, nullable=False, default=list)
    usage_details = Column(JSON, nullable=True, default=dict)
    
    # External references
    external_invoice_id = Column(String(255), nullable=True)  # Stripe, etc.
    download_url = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    
    def __repr__(self) -> str:
        return f"<Invoice(invoice_number='{self.invoice_number}', status='{self.status}')>"
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.status == InvoiceStatus.PAID and self.amount_due <= 0
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return (
            self.status == InvoiceStatus.OPEN 
            and self.due_date < datetime.utcnow()
            and self.amount_due > 0
        )


class CommissionRecord(Base):
    """
    Commission tracking for reseller partners.
    
    This model tracks commission earnings for reseller partners based on
    sales, renewals, and ongoing recurring revenue.
    """
    
    __tablename__ = "commission_records"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Commission identification
    commission_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Links to related records
    subscription_id = Column(PGUUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    reseller_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Commission details
    commission_type = Column(SQLEnum(CommissionType), nullable=False)
    commission_period = Column(String(20), nullable=False)  # monthly, quarterly, annual, one_time
    
    # Financial calculations
    base_amount = Column(Numeric(10, 2), nullable=False, default=0)  # Amount commission is calculated on
    commission_rate = Column(Numeric(5, 4), nullable=False, default=0)  # Commission rate (0.1 = 10%)
    commission_amount = Column(Numeric(10, 2), nullable=False, default=0)  # Commission earned
    
    # Bonus and overrides
    bonus_amount = Column(Numeric(10, 2), nullable=False, default=0)
    override_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_commission = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Commission period
    earned_date = Column(Date, nullable=False, index=True)
    eligible_for_payment_date = Column(Date, nullable=False)  # When commission becomes payable
    
    # Payment tracking
    payment_status = Column(String(20), nullable=False, default="pending")  # pending, approved, paid, disputed
    payment_date = Column(Date, nullable=True)
    payment_reference = Column(String(255), nullable=True)
    payment_batch_id = Column(String(255), nullable=True)
    
    # Clawback tracking
    is_clawback_eligible = Column(Boolean, nullable=False, default=True)
    clawback_period_end = Column(Date, nullable=True)
    clawback_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)
    billing_metadata = Column(JSON, nullable=True, default=dict)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="commission_records")
    
    def __repr__(self) -> str:
        return f"<CommissionRecord(commission_id='{self.commission_id}', reseller_id='{self.reseller_id}')>"
    
    @property
    def is_paid(self) -> bool:
        """Check if commission has been paid."""
        return self.payment_status == "paid" and self.payment_date is not None
    
    @property
    def is_eligible_for_payment(self) -> bool:
        """Check if commission is eligible for payment."""
        return (
            self.payment_status == "pending"
            and self.eligible_for_payment_date <= date.today()
        )


class RevenueMetrics(Base):
    """
    Aggregated revenue metrics for business intelligence.
    
    This model stores pre-calculated revenue metrics for performance
    and to support business intelligence dashboards.
    """
    
    __tablename__ = "revenue_metrics"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Time period
    metric_date = Column(Date, nullable=False, index=True)
    aggregation_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly, quarterly
    
    # Revenue metrics
    total_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    recurring_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    new_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    expansion_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    churned_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    
    # Subscription metrics
    active_subscriptions = Column(Integer, nullable=False, default=0)
    new_subscriptions = Column(Integer, nullable=False, default=0)
    canceled_subscriptions = Column(Integer, nullable=False, default=0)
    
    # Average metrics
    average_revenue_per_user = Column(Numeric(10, 2), nullable=False, default=0)
    average_contract_value = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Growth metrics
    monthly_recurring_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    annual_recurring_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    revenue_growth_rate = Column(Numeric(5, 4), nullable=True)  # Period over period growth
    
    # Commission metrics
    total_commissions_earned = Column(Numeric(10, 2), nullable=False, default=0)
    total_commissions_paid = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Segmentation
    metrics_by_tier = Column(JSON, nullable=True, default=dict)
    metrics_by_region = Column(JSON, nullable=True, default=dict)
    metrics_by_reseller = Column(JSON, nullable=True, default=dict)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<RevenueMetrics(date='{self.metric_date}', period='{self.aggregation_period}')>"