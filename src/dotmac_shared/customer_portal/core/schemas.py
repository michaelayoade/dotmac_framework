"""
Shared customer portal schemas.

Unified data models for customer portal functionality across platforms.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class PortalType(str, Enum):
    """Portal deployment types."""

    ISP_CUSTOMER = "isp_customer"
    MANAGEMENT_CUSTOMER = "management_customer"
    RESELLER_CUSTOMER = "reseller_customer"


class CustomerStatus(str, Enum):
    """Customer account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"
    DELINQUENT = "delinquent"


class ServiceStatus(str, Enum):
    """Service instance status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PROVISIONING = "provisioning"
    ERROR = "error"


class CustomerDashboardData(BaseModel):
    """Unified customer dashboard data structure."""

    # Account information
    customer_id: UUID
    account_number: str
    account_status: CustomerStatus
    portal_type: PortalType

    # Financial summary
    current_balance: Decimal = Field(default=Decimal("0.00"))
    next_bill_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[Decimal] = None

    # Services summary
    active_services: int = 0
    total_services: int = 0
    services: List["ServiceSummary"] = Field(default_factory=list)

    # Support summary
    open_tickets: int = 0
    recent_tickets: List["TicketSummary"] = Field(default_factory=list)

    # Usage summary (for ISP customers)
    usage_summary: Optional["UsageSummary"] = None

    # Platform-specific data
    platform_data: Dict[str, Any] = Field(default_factory=dict)


class ServiceSummary(BaseModel):
    """Service summary for dashboard."""

    service_id: UUID
    service_name: str
    service_type: str
    status: ServiceStatus
    monthly_cost: Decimal
    installation_date: Optional[datetime] = None
    next_renewal: Optional[datetime] = None
    usage_allowance: Optional[str] = None
    current_usage: Optional[str] = None


class TicketSummary(BaseModel):
    """Support ticket summary."""

    ticket_id: UUID
    title: str
    status: str
    priority: str
    created_at: datetime
    last_update: datetime
    assigned_to: Optional[str] = None


class UsageSummary(BaseModel):
    """Usage summary for ISP services."""

    billing_cycle_start: datetime
    billing_cycle_end: datetime
    data_usage_gb: Optional[Decimal] = None
    data_allowance_gb: Optional[Decimal] = None
    voice_minutes: Optional[int] = None
    voice_allowance: Optional[int] = None
    additional_charges: List["UsageCharge"] = Field(default_factory=list)


class UsageCharge(BaseModel):
    """Additional usage charges."""

    charge_type: str
    description: str
    quantity: Decimal
    rate: Decimal
    amount: Decimal


class CustomerPortalConfig(BaseModel):
    """Portal configuration per platform."""

    portal_type: PortalType
    tenant_id: UUID
    platform_id: str  # 'isp' or 'management'

    # Feature flags
    billing_enabled: bool = True
    ticketing_enabled: bool = True
    usage_tracking_enabled: bool = False
    service_management_enabled: bool = True
    payment_management_enabled: bool = True

    # UI customization
    branding: Dict[str, Any] = Field(default_factory=dict)
    custom_fields: List[Dict[str, Any]] = Field(default_factory=list)

    # Business rules
    auto_suspend_days: int = 30
    payment_grace_period_days: int = 5
    service_change_restrictions: List[str] = Field(default_factory=list)


class PortalSessionData(BaseModel):
    """Portal session information."""

    session_id: UUID
    customer_id: UUID
    portal_type: PortalType
    tenant_id: UUID
    created_at: datetime
    expires_at: datetime

    # Session state
    permissions: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class CustomerProfileUpdate(BaseModel):
    """Customer profile update request."""

    # Personal information
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)

    # Address information
    street_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    # Communication preferences
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    marketing_communications: Optional[bool] = None

    # Platform-specific fields
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class ServiceUsageData(BaseModel):
    """Service usage data."""

    service_id: UUID
    service_name: str
    billing_period_start: datetime
    billing_period_end: datetime

    # Usage metrics
    usage_data: Dict[str, Decimal] = Field(default_factory=dict)
    allowances: Dict[str, Decimal] = Field(default_factory=dict)
    overage_charges: List[UsageCharge] = Field(default_factory=list)

    # Historical data
    usage_history: List[Dict[str, Any]] = Field(default_factory=list)


class BillingSummary(BaseModel):
    """Billing summary information."""

    customer_id: UUID
    current_balance: Decimal

    # Next bill
    next_bill_date: Optional[datetime] = None
    estimated_amount: Optional[Decimal] = None

    # Recent activity
    recent_invoices: List["InvoiceSummary"] = Field(default_factory=list)
    recent_payments: List["PaymentSummary"] = Field(default_factory=list)

    # Payment methods
    payment_methods: List["PaymentMethodSummary"] = Field(default_factory=list)
    default_payment_method: Optional[UUID] = None


class InvoiceSummary(BaseModel):
    """Invoice summary."""

    invoice_id: UUID
    invoice_number: str
    amount: Decimal
    due_date: datetime
    status: str
    created_at: datetime


class PaymentSummary(BaseModel):
    """Payment summary."""

    payment_id: UUID
    amount: Decimal
    payment_date: datetime
    payment_method: str
    status: str
    reference_number: Optional[str] = None


class PaymentMethodSummary(BaseModel):
    """Payment method summary."""

    payment_method_id: UUID
    method_type: str  # 'card', 'bank', 'check', etc.
    display_name: str
    masked_details: str
    is_default: bool
    expires_at: Optional[datetime] = None
    status: str


# Update forward references
CustomerDashboardData.model_rebuild()
