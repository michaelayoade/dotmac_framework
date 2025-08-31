"""
Pydantic schemas for the DotMac Billing Package.

These schemas define the request/response models for API endpoints
and provide validation for billing operations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..core.models import (
    BillingCycle,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    PricingModel,
    SubscriptionStatus,
    TaxType,
)


# Base configuration for all schemas
class BillingBaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


# Customer Schemas
class CustomerBase(BillingBaseSchema):
    """Base customer schema with common fields."""

    customer_code: str = Field(
        ..., min_length=1, max_length=50, description="Unique customer code"
    )
    email: str = Field(..., description="Customer email address")
    name: str = Field(
        ..., min_length=1, max_length=255, description="Customer full name"
    )
    company_name: Optional[str] = Field(
        None, max_length=255, description="Company name"
    )
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")

    # Address fields
    address_line1: Optional[str] = Field(
        None, max_length=255, description="Address line 1"
    )
    address_line2: Optional[str] = Field(
        None, max_length=255, description="Address line 2"
    )
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    postal_code: Optional[str] = Field(
        None, max_length=20, description="Postal/ZIP code"
    )
    country: Optional[str] = Field(
        None, min_length=2, max_length=2, description="ISO country code"
    )

    # Billing preferences
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Currency code"
    )
    payment_terms: str = Field(default="NET_30", description="Payment terms")
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID number")

    # Settings
    auto_charge: bool = Field(default=False, description="Enable automatic charging")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email address")
        return v.lower()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Currency validation."""
        return v.upper()


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""

    tenant_id: Optional[UUID] = Field(
        None, description="Tenant ID for multi-tenant support"
    )
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom metadata"
    )


class CustomerUpdate(BillingBaseSchema):
    """Schema for updating customer information."""

    email: Optional[str] = Field(None, description="Customer email address")
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Customer full name"
    )
    company_name: Optional[str] = Field(
        None, max_length=255, description="Company name"
    )
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")

    # Address fields
    address_line1: Optional[str] = Field(
        None, max_length=255, description="Address line 1"
    )
    address_line2: Optional[str] = Field(
        None, max_length=255, description="Address line 2"
    )
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    postal_code: Optional[str] = Field(
        None, max_length=20, description="Postal/ZIP code"
    )
    country: Optional[str] = Field(
        None, min_length=2, max_length=2, description="ISO country code"
    )

    # Billing preferences
    currency: Optional[str] = Field(
        None, min_length=3, max_length=3, description="Currency code"
    )
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID number")

    # Settings
    is_active: Optional[bool] = Field(None, description="Customer active status")
    auto_charge: Optional[bool] = Field(None, description="Enable automatic charging")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Custom metadata"
    )


class CustomerResponse(CustomerBase):
    """Schema for customer API responses."""

    id: UUID = Field(..., description="Customer unique identifier")
    is_active: bool = Field(..., description="Customer active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata"
    )


class CustomerListResponse(BillingBaseSchema):
    """Schema for paginated customer list responses."""

    customers: List[CustomerResponse] = Field(
        default_factory=list, description="List of customers"
    )
    total_count: int = Field(..., description="Total number of customers")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Billing Plan Schemas
class BillingPlanBase(BillingBaseSchema):
    """Base billing plan schema."""

    plan_code: str = Field(
        ..., min_length=1, max_length=50, description="Unique plan code"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Plan name")
    description: Optional[str] = Field(None, description="Plan description")

    # Pricing configuration
    pricing_model: PricingModel = Field(..., description="Pricing model")
    base_price: Decimal = Field(..., ge=0, description="Base price")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Currency code"
    )
    billing_cycle: BillingCycle = Field(..., description="Billing cycle")

    # Usage and limits
    usage_unit: Optional[str] = Field(
        None, max_length=50, description="Usage unit (GB, hours, etc.)"
    )
    included_usage: Optional[Decimal] = Field(
        None, ge=0, description="Included usage quantity"
    )
    overage_price: Optional[Decimal] = Field(
        None, ge=0, description="Price per overage unit"
    )

    setup_fee: Decimal = Field(default=0, ge=0, description="One-time setup fee")
    cancellation_fee: Decimal = Field(default=0, ge=0, description="Cancellation fee")
    trial_days: int = Field(default=0, ge=0, description="Trial period in days")

    # Visibility
    is_public: bool = Field(default=False, description="Plan is publicly available")


class BillingPlanCreate(BillingPlanBase):
    """Schema for creating a billing plan."""

    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom metadata"
    )


class BillingPlanUpdate(BillingBaseSchema):
    """Schema for updating a billing plan."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Plan name"
    )
    description: Optional[str] = Field(None, description="Plan description")
    base_price: Optional[Decimal] = Field(None, ge=0, description="Base price")

    # Usage and limits
    included_usage: Optional[Decimal] = Field(
        None, ge=0, description="Included usage quantity"
    )
    overage_price: Optional[Decimal] = Field(
        None, ge=0, description="Price per overage unit"
    )

    setup_fee: Optional[Decimal] = Field(None, ge=0, description="One-time setup fee")
    cancellation_fee: Optional[Decimal] = Field(
        None, ge=0, description="Cancellation fee"
    )
    trial_days: Optional[int] = Field(None, ge=0, description="Trial period in days")

    # Status
    is_active: Optional[bool] = Field(None, description="Plan active status")
    is_public: Optional[bool] = Field(None, description="Plan is publicly available")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Custom metadata"
    )


class BillingPlanResponse(BillingPlanBase):
    """Schema for billing plan API responses."""

    id: UUID = Field(..., description="Plan unique identifier")
    is_active: bool = Field(..., description="Plan active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata"
    )


class BillingPlanListResponse(BillingBaseSchema):
    """Schema for paginated billing plan list responses."""

    plans: List[BillingPlanResponse] = Field(
        default_factory=list, description="List of billing plans"
    )
    total_count: int = Field(..., description="Total number of plans")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Subscription Schemas
class SubscriptionBase(BillingBaseSchema):
    """Base subscription schema."""

    customer_id: UUID = Field(..., description="Customer ID")
    billing_plan_id: UUID = Field(..., description="Billing plan ID")

    # Subscription configuration
    quantity: Decimal = Field(default=1, gt=0, description="Subscription quantity")
    custom_price: Optional[Decimal] = Field(
        None, ge=0, description="Custom price override"
    )

    # Dates
    start_date: date = Field(..., description="Subscription start date")
    end_date: Optional[date] = Field(None, description="Subscription end date")
    trial_end_date: Optional[date] = Field(None, description="Trial period end date")


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription."""

    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom metadata"
    )


class SubscriptionUpdate(BillingBaseSchema):
    """Schema for updating a subscription."""

    quantity: Optional[Decimal] = Field(None, gt=0, description="Subscription quantity")
    custom_price: Optional[Decimal] = Field(
        None, ge=0, description="Custom price override"
    )
    end_date: Optional[date] = Field(None, description="Subscription end date")
    status: Optional[SubscriptionStatus] = Field(
        None, description="Subscription status"
    )
    custom_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Custom metadata"
    )


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription API responses."""

    id: UUID = Field(..., description="Subscription unique identifier")
    subscription_number: str = Field(..., description="Subscription number")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    next_billing_date: date = Field(..., description="Next billing date")
    current_usage: Decimal = Field(..., description="Current usage amount")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata"
    )


class SubscriptionListResponse(BillingBaseSchema):
    """Schema for paginated subscription list responses."""

    subscriptions: List[SubscriptionResponse] = Field(
        default_factory=list, description="List of subscriptions"
    )
    total_count: int = Field(..., description="Total number of subscriptions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Invoice Schemas
class InvoiceLineItemBase(BillingBaseSchema):
    """Base invoice line item schema."""

    description: str = Field(
        ..., min_length=1, max_length=500, description="Item description"
    )
    quantity: Decimal = Field(..., gt=0, description="Item quantity")
    unit_price: Decimal = Field(..., description="Price per unit")
    taxable: bool = Field(default=True, description="Item is taxable")
    product_code: Optional[str] = Field(
        None, max_length=50, description="Product/service code"
    )
    service_period_start: Optional[date] = Field(
        None, description="Service period start"
    )
    service_period_end: Optional[date] = Field(None, description="Service period end")


class InvoiceLineItemResponse(InvoiceLineItemBase):
    """Schema for invoice line item responses."""

    id: UUID = Field(..., description="Line item unique identifier")
    line_total: Decimal = Field(..., description="Line total amount")
    tax_amount: Decimal = Field(..., description="Tax amount for line item")


class InvoiceBase(BillingBaseSchema):
    """Base invoice schema."""

    customer_id: UUID = Field(..., description="Customer ID")
    subscription_id: Optional[UUID] = Field(None, description="Subscription ID")

    # Invoice dates
    invoice_date: date = Field(..., description="Invoice date")
    due_date: date = Field(..., description="Payment due date")
    service_period_start: Optional[date] = Field(
        None, description="Service period start"
    )
    service_period_end: Optional[date] = Field(None, description="Service period end")

    # Financial information
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Currency code"
    )
    tax_type: TaxType = Field(default=TaxType.NONE, description="Tax type")
    tax_rate: Decimal = Field(default=0, ge=0, le=1, description="Tax rate as decimal")

    # Additional information
    notes: Optional[str] = Field(None, description="Invoice notes")
    terms: Optional[str] = Field(None, description="Payment terms")
    po_number: Optional[str] = Field(
        None, max_length=100, description="Purchase order number"
    )


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice."""

    line_items: List[InvoiceLineItemBase] = Field(
        ..., min_length=1, description="Invoice line items"
    )
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom metadata"
    )


class InvoiceUpdate(BillingBaseSchema):
    """Schema for updating an invoice."""

    due_date: Optional[date] = Field(None, description="Payment due date")
    notes: Optional[str] = Field(None, description="Invoice notes")
    terms: Optional[str] = Field(None, description="Payment terms")
    po_number: Optional[str] = Field(
        None, max_length=100, description="Purchase order number"
    )
    status: Optional[InvoiceStatus] = Field(None, description="Invoice status")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Custom metadata"
    )


class InvoiceResponse(InvoiceBase):
    """Schema for invoice API responses."""

    id: UUID = Field(..., description="Invoice unique identifier")
    invoice_number: str = Field(..., description="Invoice number")
    status: InvoiceStatus = Field(..., description="Invoice status")

    # Financial totals
    subtotal: Decimal = Field(..., description="Subtotal amount")
    tax_amount: Decimal = Field(..., description="Tax amount")
    discount_amount: Decimal = Field(..., description="Discount amount")
    total_amount: Decimal = Field(..., description="Total amount")
    amount_paid: Decimal = Field(..., description="Amount paid")
    amount_due: Decimal = Field(..., description="Amount due")

    # Additional fields
    pdf_url: Optional[str] = Field(None, description="PDF download URL")
    sent_at: Optional[datetime] = Field(None, description="Email sent timestamp")
    line_items: List[InvoiceLineItemResponse] = Field(
        default_factory=list, description="Line items"
    )

    # Metadata
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata"
    )

    # Computed properties
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.amount_due <= 0

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        from datetime import date

        return (
            self.status in [InvoiceStatus.SENT, InvoiceStatus.PENDING]
            and self.due_date < date.today()
            and self.amount_due > 0
        )


class InvoiceListResponse(BillingBaseSchema):
    """Schema for paginated invoice list responses."""

    invoices: List[InvoiceResponse] = Field(
        default_factory=list, description="List of invoices"
    )
    total_count: int = Field(..., description="Total number of invoices")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Payment Schemas
class PaymentBase(BillingBaseSchema):
    """Base payment schema."""

    customer_id: UUID = Field(..., description="Customer ID")
    invoice_id: Optional[UUID] = Field(None, description="Invoice ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Currency code"
    )
    payment_method: PaymentMethod = Field(..., description="Payment method")
    notes: Optional[str] = Field(None, description="Payment notes")


class PaymentCreate(PaymentBase):
    """Schema for creating a payment."""

    payment_method_id: Optional[str] = Field(
        None, description="Payment method identifier"
    )
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom metadata"
    )


class PaymentResponse(PaymentBase):
    """Schema for payment API responses."""

    id: UUID = Field(..., description="Payment unique identifier")
    payment_number: str = Field(..., description="Payment number")
    status: PaymentStatus = Field(..., description="Payment status")
    payment_date: datetime = Field(..., description="Payment date")
    processed_date: Optional[datetime] = Field(None, description="Processing date")

    # Gateway information
    gateway_transaction_id: Optional[str] = Field(
        None, description="Gateway transaction ID"
    )
    authorization_code: Optional[str] = Field(None, description="Authorization code")
    failure_reason: Optional[str] = Field(None, description="Failure reason")

    # Metadata
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata"
    )


class PaymentListResponse(BillingBaseSchema):
    """Schema for paginated payment list responses."""

    payments: List[PaymentResponse] = Field(
        default_factory=list, description="List of payments"
    )
    total_count: int = Field(..., description="Total number of payments")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Usage Record Schemas
class UsageRecordBase(BillingBaseSchema):
    """Base usage record schema."""

    subscription_id: UUID = Field(..., description="Subscription ID")
    usage_date: date = Field(..., description="Usage date")
    quantity: Decimal = Field(..., gt=0, description="Usage quantity")
    unit_type: str = Field(
        ..., min_length=1, max_length=50, description="Usage unit type"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Usage description"
    )
    source_system: Optional[str] = Field(
        None, max_length=100, description="Source system"
    )


class UsageRecordCreate(UsageRecordBase):
    """Schema for creating a usage record."""

    rate: Optional[Decimal] = Field(None, ge=0, description="Rate per unit")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom metadata"
    )


class UsageRecordResponse(UsageRecordBase):
    """Schema for usage record API responses."""

    id: UUID = Field(..., description="Usage record unique identifier")
    rate: Optional[Decimal] = Field(None, description="Rate per unit")
    amount: Optional[Decimal] = Field(None, description="Calculated amount")
    processed: bool = Field(..., description="Processing status")
    processed_date: Optional[datetime] = Field(None, description="Processing date")

    # Metadata
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata"
    )


class UsageRecordListResponse(BillingBaseSchema):
    """Schema for paginated usage record list responses."""

    usage_records: List[UsageRecordResponse] = Field(
        default_factory=list, description="List of usage records"
    )
    total_count: int = Field(..., description="Total number of usage records")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Analytics Schemas
class RevenueMetricsResponse(BillingBaseSchema):
    """Schema for revenue analytics."""

    total_revenue: Decimal = Field(..., description="Total revenue")
    monthly_recurring_revenue: Decimal = Field(
        ..., description="Monthly recurring revenue"
    )
    annual_recurring_revenue: Decimal = Field(
        ..., description="Annual recurring revenue"
    )
    average_revenue_per_user: Decimal = Field(
        ..., description="Average revenue per user"
    )
    revenue_growth_rate: Decimal = Field(..., description="Revenue growth rate")
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")


class CustomerMetricsResponse(BillingBaseSchema):
    """Schema for customer analytics."""

    total_customers: int = Field(..., description="Total number of customers")
    active_customers: int = Field(..., description="Active customers")
    new_customers: int = Field(..., description="New customers in period")
    churned_customers: int = Field(..., description="Churned customers in period")
    customer_acquisition_cost: Decimal = Field(
        ..., description="Customer acquisition cost"
    )
    customer_lifetime_value: Decimal = Field(..., description="Customer lifetime value")
    churn_rate: Decimal = Field(..., description="Customer churn rate")


class SubscriptionMetricsResponse(BillingBaseSchema):
    """Schema for subscription analytics."""

    total_subscriptions: int = Field(..., description="Total subscriptions")
    active_subscriptions: int = Field(..., description="Active subscriptions")
    new_subscriptions: int = Field(..., description="New subscriptions in period")
    cancelled_subscriptions: int = Field(
        ..., description="Cancelled subscriptions in period"
    )
    subscription_churn_rate: Decimal = Field(..., description="Subscription churn rate")
    average_subscription_value: Decimal = Field(
        ..., description="Average subscription value"
    )


class BillingAnalyticsResponse(BillingBaseSchema):
    """Schema for comprehensive billing analytics."""

    revenue_metrics: RevenueMetricsResponse = Field(
        ..., description="Revenue analytics"
    )
    customer_metrics: CustomerMetricsResponse = Field(
        ..., description="Customer analytics"
    )
    subscription_metrics: SubscriptionMetricsResponse = Field(
        ..., description="Subscription analytics"
    )
    period_start: date = Field(..., description="Analysis period start")
    period_end: date = Field(..., description="Analysis period end")
    generated_at: datetime = Field(..., description="Report generation timestamp")
