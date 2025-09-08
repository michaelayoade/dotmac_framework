"""
Core billing domain models and value objects.

This module contains pure domain objects with no framework dependencies.
These are the fundamental building blocks of the billing domain.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class BillingCycle(str, Enum):
    """Billing cycle enumeration."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"
    ONE_TIME = "one_time"


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CASH = "cash"
    CHECK = "check"
    WIRE = "wire"
    ACH = "ach"
    OTHER = "other"


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class TaxType(str, Enum):
    """Tax type enumeration."""
    NONE = "none"
    SALES_TAX = "sales_tax"
    VAT = "vat"
    GST = "gst"
    HST = "hst"
    CUSTOM = "custom"


class PricingModel(str, Enum):
    """Pricing model enumeration."""
    FLAT_RATE = "flat_rate"
    TIERED = "tiered"
    USAGE_BASED = "usage_based"
    HYBRID = "hybrid"


class PricingTier(str, Enum):
    """Pricing tier enumeration."""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingPeriod(str, Enum):
    """Billing period enumeration."""
    CURRENT = "current"
    PREVIOUS = "previous"
    NEXT = "next"


@dataclass(frozen=True)
class Money:
    """Value object representing a monetary amount."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        # Ensure amount is properly quantized for currency precision
        if self.currency in ["USD", "EUR", "GBP", "CAD"]:
            # Most currencies use 2 decimal places
            quantized = self.amount.quantize(Decimal('0.01'))
            object.__setattr__(self, 'amount', quantized)

    def add(self, other: 'Money') -> 'Money':
        """Add two money amounts (must be same currency)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: 'Money') -> 'Money':
        """Subtract two money amounts (must be same currency)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: Decimal) -> 'Money':
        """Multiply money by a factor."""
        return Money(self.amount * factor, self.currency)

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == Decimal('0')

    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > Decimal('0')

    def is_negative(self) -> bool:
        """Check if amount is negative."""
        return self.amount < Decimal('0')


@dataclass(frozen=True)
class BillingPeriodValue:
    """Value object representing a billing period."""

    start_date: date
    end_date: date
    cycle: BillingCycle

    def __post_init__(self):
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")

    def days_in_period(self) -> int:
        """Get number of days in the billing period."""
        return (self.end_date - self.start_date).days

    def contains_date(self, check_date: date) -> bool:
        """Check if a date falls within this billing period."""
        return self.start_date <= check_date <= self.end_date

    def get_proration_factor(self, partial_start: date, partial_end: Optional[date] = None) -> Decimal:
        """Calculate proration factor for partial period."""
        actual_start = max(self.start_date, partial_start)
        actual_end = min(self.end_date, partial_end) if partial_end else self.end_date

        if actual_start >= actual_end:
            return Decimal('0')

        actual_days = (actual_end - actual_start).days
        total_days = self.days_in_period()

        return Decimal(actual_days) / Decimal(total_days)


@dataclass(frozen=True)
class UsageMetric:
    """Value object representing a usage metric."""

    name: str
    quantity: Decimal
    unit: str
    period: BillingPeriodValue

    def __post_init__(self):
        if self.quantity < Decimal('0'):
            raise ValueError("Usage quantity cannot be negative")

    def is_zero(self) -> bool:
        """Check if usage is zero."""
        return self.quantity == Decimal('0')


@dataclass(frozen=True)
class TaxCalculation:
    """Value object representing a tax calculation."""

    base_amount: Money
    tax_rate: Decimal
    tax_amount: Money
    tax_type: TaxType
    jurisdiction: Optional[str] = None

    def __post_init__(self):
        if self.base_amount.currency != self.tax_amount.currency:
            raise ValueError("Base amount and tax amount must have same currency")

        # Verify tax calculation is correct
        expected_tax = self.base_amount.multiply(self.tax_rate)
        if abs(expected_tax.amount - self.tax_amount.amount) > Decimal('0.01'):
            raise ValueError("Tax amount doesn't match calculated tax")

    def total_amount(self) -> Money:
        """Get total amount including tax."""
        return self.base_amount.add(self.tax_amount)


@dataclass(frozen=True)
class LineItem:
    """Value object representing an invoice line item."""

    description: str
    quantity: Decimal
    unit_price: Money
    subtotal: Money
    tax_calculation: Optional[TaxCalculation] = None
    taxable: bool = True

    def __post_init__(self):
        # Verify subtotal calculation
        expected_subtotal = self.unit_price.multiply(self.quantity)
        if abs(expected_subtotal.amount - self.subtotal.amount) > Decimal('0.01'):
            raise ValueError("Subtotal doesn't match quantity * unit price")

    def total_amount(self) -> Money:
        """Get total amount including tax."""
        if self.tax_calculation and self.taxable:
            return self.tax_calculation.total_amount()
        return self.subtotal
