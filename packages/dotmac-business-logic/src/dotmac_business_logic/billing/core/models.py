"""
Core billing models for the DotMac Billing Package.

These models provide the foundation for billing functionality across
ISP and service provider applications with multi-tenant support.
"""

import enum
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship

# Base for models - can be overridden by implementing platforms
Base = declarative_base()


class InvoiceStatus(enum.Enum):
    """Invoice status enumeration."""

    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(enum.Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(enum.Enum):
    """Payment method enumeration."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    ACH = "ach"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CHECK = "check"
    CASH = "cash"
    WIRE = "wire"
    CRYPTOCURRENCY = "cryptocurrency"


class BillingCycle(enum.Enum):
    """Billing cycle enumeration."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"
    ONE_TIME = "one_time"


class SubscriptionStatus(enum.Enum):
    """Subscription status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    PENDING = "pending"


class TaxType(enum.Enum):
    """Tax type enumeration."""

    SALES_TAX = "sales_tax"
    VAT = "vat"
    GST = "gst"
    EXCISE_TAX = "excise_tax"
    NONE = "none"


class PricingModel(enum.Enum):
    """Pricing model enumeration."""

    FLAT_RATE = "flat_rate"
    USAGE_BASED = "usage_based"
    TIERED = "tiered"
    VOLUME_BASED = "volume_based"
    HYBRID = "hybrid"


class BillingModelMixin:
    """Base mixin for billing models with common fields."""

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    tenant_id = Column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )  # Multi-tenant support
    custom_metadata = Column(
        JSON, default=dict, nullable=False
    )  # Flexible metadata storage


class Customer(BillingModelMixin, Base):
    """Customer model for billing management."""

    __tablename__ = "billing_customers"

    # Customer identification
    customer_code = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)

    # Contact information
    phone = Column(String(50), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(2), nullable=True)  # ISO country code

    # Billing preferences
    currency = Column(String(3), default="USD", nullable=False)
    payment_terms = Column(String(50), default="NET_30", nullable=False)
    tax_id = Column(String(50), nullable=True)

    # Status and flags
    is_active = Column(Boolean, default=True, nullable=False)
    auto_charge = Column(Boolean, default=False, nullable=False)

    # Relationships
    subscriptions = relationship(
        "Subscription", back_populates="customer", cascade="all, delete-orphan"
    )
    invoices = relationship(
        "Invoice", back_populates="customer", cascade="all, delete-orphan"
    )
    payments = relationship(
        "Payment", back_populates="customer", cascade="all, delete-orphan"
    )


class BillingPlan(BillingModelMixin, Base):
    """Billing plan template for services and products."""

    __tablename__ = "billing_plans"

    # Plan identification
    plan_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing configuration
    pricing_model = Column(
        Enum(PricingModel), default=PricingModel.FLAT_RATE, nullable=False
    )
    base_price = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), default="USD", nullable=False)
    billing_cycle = Column(
        Enum(BillingCycle), default=BillingCycle.MONTHLY, nullable=False
    )

    # Usage and limits
    usage_unit = Column(String(50), nullable=True)  # GB, hours, requests, etc.
    included_usage = Column(Numeric(12, 4), nullable=True, default=0)
    overage_price = Column(Numeric(10, 4), nullable=True, default=0)

    # Plan configuration
    setup_fee = Column(Numeric(10, 2), nullable=False, default=0)
    cancellation_fee = Column(Numeric(10, 2), nullable=False, default=0)
    trial_days = Column(String(10), nullable=True, default=0)

    # Status and lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="billing_plan")
    pricing_tiers = relationship(
        "PricingTier", back_populates="billing_plan", cascade="all, delete-orphan"
    )


class PricingTier(BillingModelMixin, Base):
    """Pricing tiers for tiered billing models."""

    __tablename__ = "billing_pricing_tiers"

    billing_plan_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=False
    )

    # Tier configuration
    tier_name = Column(String(100), nullable=False)
    min_quantity = Column(Numeric(12, 4), nullable=False, default=0)
    max_quantity = Column(Numeric(12, 4), nullable=True)  # NULL for unlimited
    price_per_unit = Column(Numeric(10, 4), nullable=False)
    flat_fee = Column(Numeric(10, 2), nullable=False, default=0)

    # Relationships
    billing_plan = relationship("BillingPlan", back_populates="pricing_tiers")


class Subscription(BillingModelMixin, Base):
    """Customer subscription to billing plans."""

    __tablename__ = "billing_subscriptions"

    # Subscription identification
    subscription_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False
    )
    billing_plan_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=False
    )

    # Subscription lifecycle
    start_date = Column(Date, nullable=False, default=date.today)
    end_date = Column(Date, nullable=True)  # NULL for ongoing subscriptions
    trial_end_date = Column(Date, nullable=True)
    next_billing_date = Column(Date, nullable=False)

    # Subscription configuration
    status = Column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False
    )
    quantity = Column(Numeric(12, 4), nullable=False, default=1)
    custom_price = Column(Numeric(10, 2), nullable=True)  # Override plan price

    # Usage tracking
    current_usage = Column(Numeric(12, 4), nullable=False, default=0)
    usage_reset_date = Column(Date, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="subscriptions")
    billing_plan = relationship("BillingPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
    usage_records = relationship(
        "UsageRecord", back_populates="subscription", cascade="all, delete-orphan"
    )


class Invoice(BillingModelMixin, Base):
    """Invoice for billing customers."""

    __tablename__ = "billing_invoices"

    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False
    )
    subscription_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_subscriptions.id"), nullable=True
    )

    # Invoice dates
    invoice_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date, nullable=False)
    service_period_start = Column(Date, nullable=True)
    service_period_end = Column(Date, nullable=True)

    # Financial information
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0)
    amount_due = Column(Numeric(10, 2), nullable=False, default=0)

    # Status and configuration
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    tax_type = Column(Enum(TaxType), default=TaxType.NONE, nullable=False)
    tax_rate = Column(Numeric(5, 4), nullable=False, default=0)

    # Additional information
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    po_number = Column(String(100), nullable=True)

    # PDF and delivery
    pdf_url = Column(String(500), nullable=True)
    sent_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    line_items = relationship(
        "InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="invoice")

    @hybrid_property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.amount_due <= 0

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return (
            self.status in [InvoiceStatus.SENT, InvoiceStatus.PENDING]
            and self.due_date < date.today()
            and self.amount_due > 0
        )


class InvoiceLineItem(BillingModelMixin, Base):
    """Line items for invoices."""

    __tablename__ = "billing_invoice_line_items"

    invoice_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=False
    )

    # Line item details
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(12, 4), nullable=False, default=1)
    unit_price = Column(Numeric(10, 4), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    # Tax information
    taxable = Column(Boolean, default=True, nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)

    # Product/service reference
    product_code = Column(String(50), nullable=True)
    service_period_start = Column(Date, nullable=True)
    service_period_end = Column(Date, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")


class Payment(BillingModelMixin, Base):
    """Payment records for invoices."""

    __tablename__ = "billing_payments"

    # Payment identification
    payment_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False
    )
    invoice_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True
    )

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Payment dates
    payment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_date = Column(DateTime, nullable=True)

    # External references
    gateway_transaction_id = Column(String(255), nullable=True)
    gateway_reference = Column(String(255), nullable=True)
    authorization_code = Column(String(100), nullable=True)

    # Payment details
    notes = Column(Text, nullable=True)
    failure_reason = Column(String(500), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")


class UsageRecord(BillingModelMixin, Base):
    """Usage tracking for usage-based billing."""

    __tablename__ = "billing_usage_records"

    subscription_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_subscriptions.id"), nullable=False
    )

    # Usage details
    usage_date = Column(Date, nullable=False, default=date.today)
    quantity = Column(Numeric(12, 4), nullable=False)
    unit_type = Column(String(50), nullable=False)  # GB, hours, API calls, etc.

    # Pricing information
    rate = Column(Numeric(10, 4), nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)

    # Metadata
    description = Column(String(500), nullable=True)
    source_system = Column(String(100), nullable=True)

    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processed_date = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")


class BillingPeriod(BillingModelMixin, Base):
    """Billing periods for subscription lifecycle management."""

    __tablename__ = "billing_periods"

    subscription_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_subscriptions.id"), nullable=False
    )

    # Period dates
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Financial summary
    base_amount = Column(Numeric(10, 2), nullable=False, default=0)
    usage_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)

    # Status
    invoiced = Column(Boolean, default=False, nullable=False)
    invoice_id = Column(
        PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True
    )

    # Usage summary
    total_usage = Column(Numeric(12, 4), nullable=False, default=0)
    included_usage = Column(Numeric(12, 4), nullable=False, default=0)
    overage_usage = Column(Numeric(12, 4), nullable=False, default=0)

    # Relationships
    subscription = relationship("Subscription")
    invoice = relationship("Invoice")
