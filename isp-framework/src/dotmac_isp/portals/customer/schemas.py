"""Customer portal API schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from decimal import Decimal

from dotmac_isp.modules.identity.schemas import CustomerResponseAPI
from dotmac_isp.modules.billing.schemas import InvoiceResponse, PaymentResponse
from dotmac_isp.modules.support.schemas import TicketResponse, TicketCommentCreate
from dotmac_isp.modules.services.schemas import ServiceInstanceResponse


class CustomerDashboard(BaseModel):
    """Customer dashboard data."""

    account_status: str
    current_balance: Decimal
    next_bill_date: Optional[datetime] = None
    services: List[ServiceInstanceResponse] = Field(default_factory=list)
    recent_usage: Dict[str, Any] = Field(default_factory=dict)
    open_tickets: int = 0
    recent_payments: List[PaymentResponse] = Field(default_factory=list)
    account_summary: Dict[str, Any] = Field(default_factory=dict)


class CustomerProfileUpdate(BaseModel):
    """Customer profile update schema."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    street_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)


class ServiceUsageResponse(BaseModel):
    """Service usage response."""

    service_id: UUID
    service_name: str
    current_month: Dict[str, Any]
    usage_history: List[Dict[str, Any]] = Field(default_factory=list)
    billing_cycle: str
    data_allowance: Optional[str] = None
    usage_percentage: Optional[float] = None


class PaymentMethodBase(BaseModel):
    """Base payment method schema."""

    method_type: str  # card, bank_account, etc.
    nickname: Optional[str] = None
    is_default: bool = False


class PaymentMethodCreate(PaymentMethodBase):
    """Create payment method schema."""

    card_number: Optional[str] = Field(None, min_length=13, max_length=19)
    expiry_month: Optional[int] = Field(None, ge=1, le=12)
    expiry_year: Optional[int] = Field(None, ge=2024)
    cvv: Optional[str] = Field(None, min_length=3, max_length=4)
    cardholder_name: Optional[str] = Field(None, max_length=100)
    # Bank account fields
    account_number: Optional[str] = None
    routing_number: Optional[str] = None
    account_holder_name: Optional[str] = None


class PaymentMethodResponse(PaymentMethodBase):
    """Payment method response schema."""

    id: UUID
    masked_number: str  # Last 4 digits or masked account
    created_at: datetime
    updated_at: datetime


class PaymentRequest(BaseModel):
    """Payment request schema."""

    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)
    payment_method_id: UUID
    notes: Optional[str] = Field(None, max_length=500)


class TicketCreateRequest(BaseModel):
    """Ticket creation request."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    category: str
    priority: str = "medium"


class TicketCommentRequest(BaseModel):
    """Ticket comment request."""

    content: str = Field(..., min_length=1, max_length=2000)
    is_internal: bool = False


class CustomerServicesList(BaseModel):
    """Customer services list response."""

    services: List[ServiceInstanceResponse]
    total_count: int
    active_services: int
    suspended_services: int


class CustomerInvoicesList(BaseModel):
    """Customer invoices list response."""

    invoices: List[InvoiceResponse]
    total_count: int
    outstanding_balance: Decimal
    overdue_count: int


class CustomerTicketsList(BaseModel):
    """Customer tickets list response."""

    tickets: List[TicketResponse]
    total_count: int
    open_tickets: int
    resolved_tickets: int
