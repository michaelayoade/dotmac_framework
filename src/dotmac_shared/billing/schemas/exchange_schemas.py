"""
Pydantic schemas for manual exchange rate system.

Provides validation and API models for multi-currency operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .billing_schemas import BillingBaseSchema
from ...formatting import validate_currency_code, get_supported_currencies


# Customer Currency Schemas
class CustomerCurrencyBase(BillingBaseSchema):
    """Base schema for customer currency configuration."""
    
    currency_code: str = Field(
        ..., 
        min_length=3, 
        max_length=3, 
        description="ISO 4217 currency code"
    )
    is_base_currency: bool = Field(
        default=False, 
        description="Whether this is the customer's base currency"
    )
    is_active: bool = Field(default=True, description="Currency is active for use")
    display_name: Optional[str] = Field(
        None, 
        max_length=100, 
        description="Display name for currency"
    )
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator("currency_code")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Validate currency code is supported."""
        v = v.upper()
        if not validate_currency_code(v):
            supported = ", ".join(get_supported_currencies())
            raise ValueError(f"Unsupported currency: {v}. Supported: {supported}")
        return v


class CustomerCurrencyCreate(CustomerCurrencyBase):
    """Schema for creating customer currency."""
    
    customer_id: UUID = Field(..., description="Customer ID")


class CustomerCurrencyUpdate(BillingBaseSchema):
    """Schema for updating customer currency."""
    
    is_base_currency: Optional[bool] = Field(None, description="Base currency flag")
    is_active: Optional[bool] = Field(None, description="Active status")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    notes: Optional[str] = Field(None, description="Notes")


class CustomerCurrencyResponse(CustomerCurrencyBase):
    """Schema for customer currency API responses."""
    
    id: UUID = Field(..., description="Currency configuration ID")
    customer_id: UUID = Field(..., description="Customer ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Exchange Rate Schemas
class ManualExchangeRateBase(BillingBaseSchema):
    """Base schema for manual exchange rates."""
    
    from_currency: str = Field(
        ..., 
        min_length=3, 
        max_length=3,
        description="Currency being converted from"
    )
    to_currency: str = Field(
        ..., 
        min_length=3, 
        max_length=3,
        description="Currency being converted to"
    )
    exchange_rate: Decimal = Field(
        ..., 
        gt=0, 
        decimal_places=6,
        description="Exchange rate (from_currency to to_currency)"
    )
    rate_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date when rate was set"
    )
    valid_until: Optional[datetime] = Field(
        None, 
        description="Optional expiry date for rate"
    )
    source: Optional[str] = Field(
        None, 
        max_length=100,
        description="Source of exchange rate"
    )
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currencies(cls, v: str) -> str:
        """Validate currency codes."""
        v = v.upper()
        if not validate_currency_code(v):
            supported = ", ".join(get_supported_currencies())
            raise ValueError(f"Unsupported currency: {v}. Supported: {supported}")
        return v
    
    @field_validator("exchange_rate")
    @classmethod
    def validate_exchange_rate(cls, v: Decimal) -> Decimal:
        """Validate exchange rate is reasonable."""
        if v <= 0:
            raise ValueError("Exchange rate must be positive")
        if v > Decimal("1000000"):  # Sanity check
            raise ValueError("Exchange rate seems unreasonably high")
        return v


class ManualExchangeRateCreate(ManualExchangeRateBase):
    """Schema for creating manual exchange rate."""
    
    customer_currency_id: UUID = Field(..., description="Customer currency configuration ID")
    reference_invoice_id: Optional[UUID] = Field(None, description="Related invoice ID")
    reference_payment_id: Optional[UUID] = Field(None, description="Related payment ID")
    created_by: Optional[str] = Field(None, description="User who created the rate")


class ManualExchangeRateUpdate(BillingBaseSchema):
    """Schema for updating exchange rate."""
    
    exchange_rate: Optional[Decimal] = Field(
        None, 
        gt=0, 
        decimal_places=6,
        description="New exchange rate"
    )
    valid_until: Optional[datetime] = Field(None, description="Expiry date")
    status: Optional[str] = Field(None, description="Rate status")
    source: Optional[str] = Field(None, max_length=100, description="Rate source")
    notes: Optional[str] = Field(None, description="Notes")


class ManualExchangeRateResponse(ManualExchangeRateBase):
    """Schema for exchange rate API responses."""
    
    id: UUID = Field(..., description="Exchange rate ID")
    customer_currency_id: UUID = Field(..., description="Customer currency ID")
    status: str = Field(..., description="Rate status")
    reference_invoice_id: Optional[UUID] = Field(None, description="Related invoice")
    reference_payment_id: Optional[UUID] = Field(None, description="Related payment")
    created_by: Optional[str] = Field(None, description="Creator")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Multi-Currency Payment Schemas
class MultiCurrencyPaymentBase(BillingBaseSchema):
    """Base schema for multi-currency payments."""
    
    original_amount: Decimal = Field(..., gt=0, description="Amount paid in original currency")
    original_currency: str = Field(..., min_length=3, max_length=3, description="Payment currency")
    converted_amount: Decimal = Field(..., gt=0, description="Amount in base currency")
    converted_currency: str = Field(..., min_length=3, max_length=3, description="Base currency")
    conversion_rate: Decimal = Field(..., gt=0, description="Rate used for conversion")
    expected_amount: Optional[Decimal] = Field(None, description="Expected amount in base currency")
    variance_notes: Optional[str] = Field(None, description="Variance explanation")


class MultiCurrencyPaymentCreate(MultiCurrencyPaymentBase):
    """Schema for creating multi-currency payment record."""
    
    payment_id: UUID = Field(..., description="Original payment ID")
    exchange_rate_id: UUID = Field(..., description="Exchange rate used")


class MultiCurrencyPaymentResponse(MultiCurrencyPaymentBase):
    """Schema for multi-currency payment responses."""
    
    id: UUID = Field(..., description="Multi-currency payment ID")
    payment_id: UUID = Field(..., description="Original payment ID")
    exchange_rate_id: UUID = Field(..., description="Exchange rate used")
    conversion_date: datetime = Field(..., description="Conversion timestamp")
    is_reconciled: bool = Field(..., description="Reconciliation status")
    reconciled_date: Optional[datetime] = Field(None, description="Reconciliation date")
    reconciled_by: Optional[str] = Field(None, description="Who reconciled")
    variance_amount: Decimal = Field(..., description="Variance from expected")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Payment with Exchange Rate Schema
class PaymentWithExchangeRateCreate(BillingBaseSchema):
    """Schema for creating payment with manual exchange rate."""
    
    # Payment details
    customer_id: UUID = Field(..., description="Customer ID")
    invoice_id: Optional[UUID] = Field(None, description="Invoice ID")
    payment_amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_currency: str = Field(
        ..., 
        min_length=3, 
        max_length=3,
        description="Currency of payment"
    )
    payment_method: str = Field(..., description="Payment method")
    payment_notes: Optional[str] = Field(None, description="Payment notes")
    
    # Exchange rate details
    base_currency: str = Field(
        ..., 
        min_length=3, 
        max_length=3,
        description="Customer's base currency"
    )
    exchange_rate: Decimal = Field(
        ..., 
        gt=0, 
        decimal_places=6,
        description="Manual exchange rate"
    )
    rate_source: Optional[str] = Field(None, description="Source of exchange rate")
    rate_notes: Optional[str] = Field(None, description="Exchange rate notes")
    
    @field_validator("payment_currency", "base_currency")
    @classmethod
    def validate_currencies(cls, v: str) -> str:
        """Validate currency codes."""
        v = v.upper()
        if not validate_currency_code(v):
            supported = ", ".join(get_supported_currencies())
            raise ValueError(f"Unsupported currency: {v}. Supported: {supported}")
        return v


# Currency Conversion Utility Schema
class CurrencyConversionRequest(BillingBaseSchema):
    """Schema for currency conversion requests."""
    
    amount: Decimal = Field(..., gt=0, description="Amount to convert")
    from_currency: str = Field(..., min_length=3, max_length=3, description="Source currency")
    to_currency: str = Field(..., min_length=3, max_length=3, description="Target currency")
    exchange_rate: Decimal = Field(..., gt=0, description="Exchange rate to use")


class CurrencyConversionResponse(BillingBaseSchema):
    """Schema for currency conversion responses."""
    
    original_amount: Decimal = Field(..., description="Original amount")
    original_currency: str = Field(..., description="Original currency")
    converted_amount: Decimal = Field(..., description="Converted amount")
    converted_currency: str = Field(..., description="Target currency")
    exchange_rate: Decimal = Field(..., description="Rate used")
    conversion_date: datetime = Field(..., description="Conversion timestamp")


# List Response Schemas
class CustomerCurrencyListResponse(BillingBaseSchema):
    """Schema for customer currency list responses."""
    
    currencies: List[CustomerCurrencyResponse] = Field(
        default_factory=list, 
        description="List of customer currencies"
    )
    total_count: int = Field(..., description="Total number of currencies")


class ExchangeRateListResponse(BillingBaseSchema):
    """Schema for exchange rate list responses."""
    
    exchange_rates: List[ManualExchangeRateResponse] = Field(
        default_factory=list,
        description="List of exchange rates"
    )
    total_count: int = Field(..., description="Total number of rates")


class MultiCurrencyPaymentListResponse(BillingBaseSchema):
    """Schema for multi-currency payment list responses."""
    
    payments: List[MultiCurrencyPaymentResponse] = Field(
        default_factory=list,
        description="List of multi-currency payments"
    )
    total_count: int = Field(..., description="Total number of payments")