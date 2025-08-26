"""Billing module schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from enum import Enum


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""

    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    CASH = "cash"
    ACH = "ach"


class TaxType(str, Enum):
    """Tax type enumeration."""

    SALES_TAX = "sales_tax"
    VAT = "vat"
    GST = "gst"
    EXCISE = "excise"


class LineItemBase(BaseModel):
    """Base line item schema."""

    description: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    discount_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)


class LineItemCreate(LineItemBase):
    """Create line item schema."""

    pass


class InvoiceLineItemCreate(LineItemBase):
    """Create invoice line item schema."""

    service_instance_id: Optional[str] = None


class LineItem(LineItemBase):
    """Line item schema."""

    id: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    """Base invoice schema."""

    customer_id: str
    invoice_number: Optional[str] = None
    issue_date: datetime
    due_date: datetime
    notes: Optional[str] = None
    terms: Optional[str] = None
    currency: str = "USD"


class InvoiceCreate(InvoiceBase):
    """Create invoice schema."""

    line_items: List[LineItemCreate] = []


class InvoiceUpdate(BaseModel):
    """Update invoice schema."""

    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class Invoice(InvoiceBase):
    """Invoice schema."""

    id: str
    status: InvoiceStatus
    line_items: List[LineItem] = []
    subtotal: Decimal
    tax_total: Decimal
    discount_total: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(Invoice):
    """Invoice response schema."""
    
    pass


class CreditNoteBase(BaseModel):
    """Base credit note schema."""

    invoice_id: str
    reason: str
    amount: Decimal = Field(gt=0)
    notes: Optional[str] = None


class CreditNoteCreate(CreditNoteBase):
    """Create credit note schema."""

    pass


class CreditNote(CreditNoteBase):
    """Credit note schema."""

    id: str
    credit_note_number: str
    status: str
    created_at: datetime
    applied_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    """Base payment schema."""

    invoice_id: str
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Create payment schema."""

    pass


class PaymentUpdate(BaseModel):
    """Update payment schema."""

    status: Optional[PaymentStatus] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class Payment(PaymentBase):
    """Payment schema."""

    id: str
    payment_date: datetime
    status: PaymentStatus
    transaction_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(Payment):
    """Payment response schema."""
    
    pass


class ReceiptBase(BaseModel):
    """Base receipt schema."""

    payment_id: str
    receipt_number: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    """Create receipt schema."""

    pass


class Receipt(ReceiptBase):
    """Receipt schema."""

    id: str
    receipt_number: str
    issued_at: datetime
    amount: Decimal
    payment_method: PaymentMethod
    customer_name: str
    invoice_number: str

    model_config = ConfigDict(from_attributes=True)


class TaxRateBase(BaseModel):
    """Base tax rate schema."""

    name: str
    rate: Decimal = Field(ge=0, le=1)
    tax_type: TaxType
    jurisdiction: str
    active: bool = True


class TaxRateCreate(TaxRateBase):
    """Create tax rate schema."""

    pass


class TaxRate(TaxRateBase):
    """Tax rate schema."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionBase(BaseModel):
    """Base subscription schema."""

    customer_id: str
    plan_id: str
    billing_cycle: str  # monthly, yearly, etc.
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    start_date: datetime
    end_date: Optional[datetime] = None


class SubscriptionCreate(SubscriptionBase):
    """Create subscription schema."""

    pass


class SubscriptionUpdate(BaseModel):
    """Update subscription schema."""
    
    plan_id: Optional[str] = None
    billing_cycle: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class Subscription(SubscriptionBase):
    """Subscription schema."""

    id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BillingReport(BaseModel):
    """Billing report schema."""

    period_start: datetime
    period_end: datetime
    total_invoiced: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    invoice_count: int
    payment_count: int
    average_payment_time: Optional[float] = None


class InvoiceCreateRequest(BaseModel):
    """Schema for creating invoice requests."""
    
    customer_id: str
    line_items: List[LineItemCreate]
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    currency: str = "USD"


class PaymentRequest(BaseModel):
    """Schema for payment requests."""
    
    invoice_id: str
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class CreditNoteRequest(BaseModel):
    """Schema for credit note requests."""
    
    customer_id: str
    amount: Decimal = Field(gt=0)
    reason: str = Field(..., max_length=500)
    invoice_id: Optional[str] = None


class BillingRuleRequest(BaseModel):
    """Schema for billing rule requests."""
    
    rule_name: str
    rule_type: str
    conditions: dict
    actions: dict
    is_active: bool = True


class InvoiceCalculationResult(BaseModel):
    """Schema for invoice calculation results."""
    
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    line_items: List[LineItem]
    
    model_config = ConfigDict(from_attributes=True)
