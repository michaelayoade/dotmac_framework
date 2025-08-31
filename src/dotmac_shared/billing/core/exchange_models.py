"""
Simple manual exchange rate system for multi-currency payments.

Allows customers to have a base currency and manually set exchange rates
for payments in other currencies.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .models import BillingModelMixin, Base


class ExchangeRateStatus(enum.Enum):
    """Exchange rate entry status."""
    
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class CustomerCurrency(BillingModelMixin, Base):
    """Customer's supported currencies with base currency designation."""
    
    __tablename__ = "customer_currencies"
    
    # Customer reference
    customer_id = Column(
        PGUUID(as_uuid=True), 
        ForeignKey("billing_customers.id"), 
        nullable=False
    )
    
    # Currency details
    currency_code = Column(String(3), nullable=False)
    is_base_currency = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Display settings
    display_name = Column(String(100), nullable=True)  # e.g., "Nigerian Naira"
    notes = Column(Text, nullable=True)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', 'currency_code', name='unique_customer_currency'),
    )
    
    # Relationships
    customer = relationship("Customer")
    exchange_rates = relationship(
        "ManualExchangeRate", 
        back_populates="customer_currency",
        cascade="all, delete-orphan"
    )


class ManualExchangeRate(BillingModelMixin, Base):
    """Manual exchange rates set by customers for specific transactions."""
    
    __tablename__ = "manual_exchange_rates"
    
    # Currency pair reference
    customer_currency_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("customer_currencies.id"),
        nullable=False
    )
    
    # Exchange rate details
    from_currency = Column(String(3), nullable=False)  # Payment currency
    to_currency = Column(String(3), nullable=False)    # Base currency
    exchange_rate = Column(Numeric(15, 6), nullable=False)  # 6 decimal precision
    
    # Rate metadata
    rate_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until = Column(DateTime, nullable=True)  # Optional expiry
    status = Column(
        String(20), 
        default=ExchangeRateStatus.ACTIVE.value, 
        nullable=False
    )
    
    # Transaction context
    reference_invoice_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_invoices.id"),
        nullable=True
    )
    reference_payment_id = Column(
        PGUUID(as_uuid=True), 
        ForeignKey("billing_payments.id"),
        nullable=True
    )
    
    # Additional info
    source = Column(String(100), nullable=True)  # e.g., "Manual Entry", "Bank Rate"
    notes = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)  # User who set the rate
    
    # Relationships
    customer_currency = relationship("CustomerCurrency", back_populates="exchange_rates")
    invoice = relationship("Invoice")
    payment = relationship("Payment")


class MultiCurrencyPayment(BillingModelMixin, Base):
    """Extended payment record with multi-currency support."""
    
    __tablename__ = "multi_currency_payments"
    
    # Original payment reference
    payment_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_payments.id"),
        nullable=False
    )
    
    # Exchange rate used
    exchange_rate_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("manual_exchange_rates.id"),
        nullable=False
    )
    
    # Payment amounts
    original_amount = Column(Numeric(12, 2), nullable=False)      # Amount paid
    original_currency = Column(String(3), nullable=False)        # Currency paid in
    converted_amount = Column(Numeric(12, 2), nullable=False)    # Amount in base currency
    converted_currency = Column(String(3), nullable=False)       # Base currency
    
    # Conversion details
    conversion_rate = Column(Numeric(15, 6), nullable=False)     # Rate used
    conversion_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Reconciliation
    is_reconciled = Column(Boolean, default=False, nullable=False)
    reconciled_date = Column(DateTime, nullable=True)
    reconciled_by = Column(String(255), nullable=True)
    
    # Variance tracking
    expected_amount = Column(Numeric(12, 2), nullable=True)      # Expected in base currency
    variance_amount = Column(Numeric(12, 2), default=0, nullable=False)
    variance_notes = Column(Text, nullable=True)
    
    # Relationships
    payment = relationship("Payment")
    exchange_rate = relationship("ManualExchangeRate")


class ExchangeRateHistory(BillingModelMixin, Base):
    """History of exchange rate changes for audit purposes."""
    
    __tablename__ = "exchange_rate_history"
    
    # Rate reference
    exchange_rate_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("manual_exchange_rates.id"),
        nullable=False
    )
    
    # Historical data
    old_rate = Column(Numeric(15, 6), nullable=True)
    new_rate = Column(Numeric(15, 6), nullable=False)
    change_reason = Column(String(500), nullable=True)
    changed_by = Column(String(255), nullable=False)
    change_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    exchange_rate = relationship("ManualExchangeRate")


# Helper functions for currency operations
def calculate_converted_amount(
    amount: Decimal, 
    exchange_rate: Decimal, 
    from_currency: str,
    to_currency: str
) -> Decimal:
    """
    Calculate converted amount using exchange rate.
    
    Args:
        amount: Amount to convert
        exchange_rate: Exchange rate (from_currency to to_currency)
        from_currency: Source currency
        to_currency: Target currency
        
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return amount
    
    # Apply exchange rate
    converted = amount * exchange_rate
    
    # Round to 2 decimal places for currency
    return Decimal(str(round(converted, 2)))


def calculate_variance(
    expected_amount: Decimal,
    actual_amount: Decimal
) -> tuple[Decimal, str]:
    """
    Calculate variance between expected and actual amounts.
    
    Returns:
        Tuple of (variance_amount, variance_percentage)
    """
    variance = actual_amount - expected_amount
    
    if expected_amount > 0:
        percentage = (variance / expected_amount) * 100
        return variance, f"{percentage:.2f}%"
    
    return variance, "N/A"