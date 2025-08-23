"""Billing models - Invoices, payments, subscriptions, and billing cycles."""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    Date,
    DateTime,
    Numeric,
    Boolean,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from dotmac_isp.shared.database.base import TenantModel


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
    BANK_TRANSFER = "bank_transfer"
    ACH = "ach"
    PAYPAL = "paypal"
    CHECK = "check"
    CASH = "cash"
    WIRE = "wire"


class BillingCycle(enum.Enum):
    """Billing cycle enumeration."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ONE_TIME = "one_time"


class TaxType(enum.Enum):
    """Tax type enumeration."""

    SALES_TAX = "sales_tax"
    VAT = "vat"
    GST = "gst"
    NONE = "none"


class Invoice(TenantModel):
    """Invoice model for billing customers."""

    __tablename__ = "invoices"

    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # Invoice dates
    invoice_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date, nullable=False)

    # Financial information
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)

    # Status and metadata
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    notes = Column(Text, nullable=True)

    # Payment tracking
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)
    paid_date = Column(Date, nullable=True)

    # External references
    external_invoice_id = Column(
        String(255), nullable=True
    )  # For payment processor integration

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    line_items = relationship(
        "InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="invoice")

    @property
    def balance_due(self) -> Decimal:
        """Calculate remaining balance due."""
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return self.due_date < date.today() and self.status not in [
            InvoiceStatus.PAID,
            InvoiceStatus.CANCELLED,
        ]


class InvoiceLineItem(TenantModel):
    """Line items for invoices."""

    __tablename__ = "invoice_line_items"

    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)

    # Item details
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    # Tax information
    tax_rate = Column(
        Numeric(5, 4), nullable=False, default=0
    )  # e.g., 0.0825 for 8.25%
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)

    # Service reference
    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=True
    )

    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")
    service_instance = relationship("ServiceInstance")


class Payment(TenantModel):
    """Payment model for invoice payments."""

    __tablename__ = "payments"

    # Payment identification
    payment_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Payment processing
    transaction_id = Column(String(255), nullable=True)  # External transaction ID
    reference_number = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # Failure information
    failure_reason = Column(String(500), nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    receipts = relationship("Receipt", back_populates="payment", cascade="all, delete-orphan")


class Subscription(TenantModel):
    """Subscription model for recurring billing."""

    __tablename__ = "subscriptions"

    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    service_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("service_instances.id"), nullable=False
    )

    # Subscription details
    billing_cycle = Column(Enum(BillingCycle), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # NULL for ongoing subscriptions
    next_billing_date = Column(Date, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    auto_renew = Column(Boolean, default=True, nullable=False)

    # Relationships
    customer = relationship("Customer")
    service_instance = relationship("ServiceInstance")


class BillingAccount(TenantModel):
    """Billing account for customer payment information."""

    __tablename__ = "billing_accounts"

    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # Account details
    account_name = Column(String(255), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    # Payment method details (stored securely)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    card_last_four = Column(String(4), nullable=True)  # For credit cards
    card_expiry = Column(String(7), nullable=True)  # MM/YYYY format
    bank_name = Column(String(255), nullable=True)  # For bank transfers
    account_number_masked = Column(String(50), nullable=True)  # Masked account number

    # External payment processor references
    stripe_payment_method_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)

    # Status
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    customer = relationship("Customer")


class TaxRate(TenantModel):
    """Tax rate configuration."""

    __tablename__ = "tax_rates"

    name = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 4), nullable=False)  # e.g., 0.0825 for 8.25%
    tax_type = Column(Enum(TaxType), nullable=False)

    # Geographic applicability
    country_code = Column(String(2), nullable=True)
    state_province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Effective dates
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)


class CreditNote(TenantModel):
    """Credit note model for refunds and adjustments."""

    __tablename__ = "credit_notes"

    # Credit note identification
    credit_note_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)

    # Credit note details
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(500), nullable=False)
    credit_date = Column(Date, nullable=False, default=date.today)

    # Status
    is_applied = Column(Boolean, default=False, nullable=False)
    applied_date = Column(Date, nullable=True)

    # Relationships
    customer = relationship("Customer")
    invoice = relationship("Invoice")


class Receipt(TenantModel):
    """Receipt model for payment confirmations."""

    __tablename__ = "receipts"

    # Receipt identification
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)

    # Receipt details
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    
    # Customer and invoice information (denormalized for receipt purposes)
    customer_name = Column(String(255), nullable=False)
    invoice_number = Column(String(50), nullable=False)

    # Relationships
    payment = relationship("Payment", back_populates="receipts")


class LateFee(TenantModel):
    """Late fee model for overdue invoice charges."""

    __tablename__ = "late_fees"

    # Late fee identification
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # Fee details
    fee_amount = Column(Numeric(10, 2), nullable=False)
    fee_date = Column(Date, nullable=False, default=date.today)
    days_overdue = Column(String(50), nullable=False)

    # Status
    is_waived = Column(Boolean, default=False, nullable=False)
    waived_date = Column(Date, nullable=True)
    waived_reason = Column(String(500), nullable=True)

    # Relationships
    invoice = relationship("Invoice")
    customer = relationship("Customer")
