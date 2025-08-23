"""
Billing and subscription models.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSON
from .base import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from .base import BaseModel


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"
    PAUSED = "paused"


class PricingPlanType(str, Enum):
    """Pricing plan type."""
    FIXED = "fixed"         # Fixed monthly/annual price
    USAGE_BASED = "usage_based"  # Pay per usage
    TIERED = "tiered"       # Usage tiers
    HYBRID = "hybrid"       # Fixed base + usage


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CommissionStatus(str, Enum):
    """Commission status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class PricingPlan(BaseModel):
    """Pricing plans for tenant subscriptions."""
    
    __tablename__ = "pricing_plans"
    
    # Basic plan information
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Plan type and pricing
    plan_type = Column(SQLEnum(PricingPlanType), nullable=False, index=True)
    base_price_cents = Column(Integer, default=0, nullable=False)  # Base price in cents
    setup_fee_cents = Column(Integer, default=0, nullable=False)
    
    # Billing configuration
    billing_interval = Column(String(20), default="monthly", nullable=False)  # monthly, annual
    billing_interval_count = Column(Integer, default=1, nullable=False)
    trial_days = Column(Integer, default=14, nullable=False)
    
    # Resource limits
    max_tenants = Column(Integer, default=1, nullable=False)
    max_users = Column(Integer, default=10, nullable=False)
    max_storage_gb = Column(Integer, default=100, nullable=False)
    max_bandwidth_gb = Column(Integer, default=1000, nullable=False)
    max_api_calls = Column(Integer, default=100000, nullable=False)
    
    # Plan status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_public = Column(Boolean, default=True, nullable=False)  # Publicly available
    
    # Plan metadata
    features = Column(JSON, default=list, nullable=False)  # List of included features
    usage_limits = Column(JSON, default=dict, nullable=False)  # Usage-based limits
    pricing_tiers = Column(JSON, default=list, nullable=False)  # Tiered pricing
    
    # Stripe integration
    stripe_price_id = Column(String(255), nullable=True, index=True)
    stripe_product_id = Column(String(255), nullable=True)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="pricing_plan")
    
    def __repr__(self) -> str:
        return f"<PricingPlan(name='{self.name}', type='{self.plan_type}')>"
    
    @property
    def monthly_price(self) -> Decimal:
        """Get monthly price in dollars."""
        if self.billing_interval == "annual":
            return Decimal(self.base_price_cents) / 100 / 12
        return Decimal(self.base_price_cents) / 100
    
    @property
    def annual_price(self) -> Decimal:
        """Get annual price in dollars."""
        if self.billing_interval == "monthly":
            return Decimal(self.base_price_cents) / 100 * 12
        return Decimal(self.base_price_cents) / 100


class Subscription(BaseModel):
    """Tenant subscription management."""
    
    __tablename__ = "subscriptions"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    pricing_plan_id = Column(UUID(as_uuid=True), ForeignKey("pricing_plans.id"), nullable=False)
    
    # Subscription details
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False, index=True)
    
    # Subscription period
    current_period_start = Column(DateTime, nullable=False, index=True)
    current_period_end = Column(DateTime, nullable=False, index=True)
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Billing configuration
    billing_cycle_day = Column(Integer, default=1, nullable=False)  # Day of month for billing
    
    # Subscription metadata
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(500), nullable=True)
    
    # Usage tracking
    current_usage = Column(JSON, default=dict, nullable=False)
    
    # Payment information
    default_payment_method_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Stripe integration
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="subscriptions")
    pricing_plan = relationship("PricingPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
    usage_records = relationship("UsageRecord", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<Subscription(tenant_id='{self.tenant_id}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE]
    
    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial."""
        return self.status == SubscriptionStatus.TRIAL
    
    @property
    def days_until_renewal(self) -> int:
        """Calculate days until next renewal."""
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)
    
    def cancel(self, reason: str = None, at_period_end: bool = True) -> None:
        """Cancel subscription."""
        if at_period_end:
            self.cancel_at_period_end = True
        else:
            self.status = SubscriptionStatus.CANCELLED
            self.cancelled_at = datetime.utcnow()
        self.cancel_reason = reason
    
    def reactivate(self) -> None:
        """Reactivate cancelled subscription."""
        self.status = SubscriptionStatus.ACTIVE
        self.cancel_at_period_end = False
        self.cancelled_at = None
        self.cancel_reason = None


class Invoice(BaseModel):
    """Invoice management."""
    
    __tablename__ = "invoices"
    
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    
    # Invoice details
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    
    # Invoice period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Amount details
    subtotal_cents = Column(Integer, nullable=False)
    tax_cents = Column(Integer, default=0, nullable=False)
    total_cents = Column(Integer, nullable=False)
    amount_paid_cents = Column(Integer, default=0, nullable=False)
    amount_due_cents = Column(Integer, nullable=False)
    
    # Invoice dates
    invoice_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    
    # Invoice metadata
    currency = Column(String(3), default="USD", nullable=False)
    description = Column(Text, nullable=True)
    line_items = Column(JSON, default=list, nullable=False)
    
    # Payment tracking
    payment_attempted = Column(Boolean, default=False, nullable=False)
    payment_attempts = Column(Integer, default=0, nullable=False)
    next_payment_attempt = Column(DateTime, nullable=True)
    
    # Stripe integration
    stripe_invoice_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")
    
    def __repr__(self) -> str:
        return f"<Invoice(number='{self.invoice_number}', status='{self.status}')>"
    
    @property
    def total_amount(self) -> Decimal:
        """Get total amount in dollars."""
        return Decimal(self.total_cents) / 100
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return self.due_date < datetime.utcnow() and self.status not in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.status == InvoiceStatus.PAID
    
    def mark_paid(self, payment_date: datetime = None) -> None:
        """Mark invoice as paid."""
        self.status = InvoiceStatus.PAID
        self.paid_at = payment_date or datetime.utcnow()
        self.amount_paid_cents = self.total_cents


class Payment(BaseModel):
    """Payment tracking."""
    
    __tablename__ = "payments"
    
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True)
    
    # Payment details
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Payment method
    payment_method_type = Column(String(50), nullable=False)  # card, bank_transfer, etc.
    payment_method_details = Column(JSON, default=dict, nullable=False)
    
    # Payment processing
    processed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    
    # External payment processor
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    stripe_charge_id = Column(String(255), nullable=True)
    processor_fee_cents = Column(Integer, default=0, nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    
    def __repr__(self) -> str:
        return f"<Payment(amount_cents={self.amount_cents}, status='{self.status}')>"
    
    @property
    def amount(self) -> Decimal:
        """Get payment amount in dollars."""
        return Decimal(self.amount_cents) / 100
    
    def mark_succeeded(self, processed_at: datetime = None) -> None:
        """Mark payment as succeeded."""
        self.status = PaymentStatus.SUCCEEDED
        self.processed_at = processed_at or datetime.utcnow()
    
    def mark_failed(self, reason: str, failed_at: datetime = None) -> None:
        """Mark payment as failed."""
        self.status = PaymentStatus.FAILED
        self.failed_at = failed_at or datetime.utcnow()
        self.failure_reason = reason


class UsageRecord(BaseModel):
    """Usage-based billing records."""
    
    __tablename__ = "usage_records"
    
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)
    
    # Usage details
    metric_name = Column(String(100), nullable=False, index=True)  # api_calls, storage_gb, etc.
    quantity = Column(Numeric(15, 6), nullable=False)
    unit_price_cents = Column(Integer, nullable=False)
    total_cost_cents = Column(Integer, nullable=False)
    
    # Usage period
    usage_date = Column(DateTime, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Usage metadata
    description = Column(String(500), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    
    # Billing status
    billed = Column(Boolean, default=False, nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")
    invoice = relationship("Invoice")
    
    def __repr__(self) -> str:
        return f"<UsageRecord(metric='{self.metric_name}', quantity={self.quantity})>"
    
    @property
    def total_cost(self) -> Decimal:
        """Get total cost in dollars."""
        return Decimal(self.total_cost_cents) / 100


class Commission(BaseModel):
    """Reseller commission tracking."""
    
    __tablename__ = "commissions"
    
    # Commission details
    reseller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    
    # Commission calculation
    base_amount_cents = Column(Integer, nullable=False)  # Amount commission is based on
    commission_rate = Column(Numeric(5, 4), nullable=False)  # Commission rate (0.1000 = 10%)
    commission_amount_cents = Column(Integer, nullable=False)
    
    # Commission status
    status = Column(SQLEnum(CommissionStatus), default=CommissionStatus.PENDING, nullable=False, index=True)
    
    # Commission period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    earned_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Payment details
    paid_at = Column(DateTime, nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # Relationships
    reseller = relationship("User")
    tenant = relationship("Tenant")
    subscription = relationship("Subscription")
    invoice = relationship("Invoice")
    
    def __repr__(self) -> str:
        return f"<Commission(reseller_id='{self.reseller_id}', amount_cents={self.commission_amount_cents})>"
    
    @property
    def commission_amount(self) -> Decimal:
        """Get commission amount in dollars."""
        return Decimal(self.commission_amount_cents) / 100
    
    @property
    def base_amount(self) -> Decimal:
        """Get base amount in dollars."""
        return Decimal(self.base_amount_cents) / 100
    
    def mark_paid(self, payment_reference: str = None, paid_at: datetime = None) -> None:
        """Mark commission as paid."""
        self.status = CommissionStatus.PAID
        self.paid_at = paid_at or datetime.utcnow()
        self.payment_reference = payment_reference