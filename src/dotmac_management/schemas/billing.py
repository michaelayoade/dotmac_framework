"""
Billing and subscription schemas for validation and serialization.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import BaseSchema, PaginatedResponse


class StripeCustomerCreate(BaseModel):
    """Schema for creating Stripe customer."""

    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Customer name")
    metadata: Optional[dict[str, str]] = Field(None, description="Additional metadata")


class StripeSubscriptionCreate(BaseModel):
    """Schema for creating Stripe subscription."""

    customer_id: str = Field(..., description="Stripe customer ID")
    price_id: str = Field(..., description="Stripe price ID")
    trial_days: Optional[int] = Field(None, description="Trial period in days")
    metadata: Optional[dict[str, str]] = Field(None, description="Additional metadata")


class StripeWebhookEvent(BaseModel):
    """Schema for Stripe webhook events."""

    id: str = Field(..., description="Event ID")
    object: str = Field(..., description="Event object type")
    type: str = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")


class PaymentIntentCreate(BaseModel):
    """Schema for creating payment intent."""

    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    currency: str = Field(default="usd", description="Currency code")
    customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    metadata: Optional[dict[str, str]] = Field(None, description="Additional metadata")


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response."""

    payment_intent_id: str = Field(..., description="Payment intent ID")
    client_secret: str = Field(..., description="Client secret for frontend")
    status: str = Field(..., description="Payment intent status")
    amount: int = Field(..., description="Amount in cents")


class BillingPlanBase(BaseModel):
    """BillingPlanBase implementation."""

    name: str = Field(..., description="Plan name")
    description: Optional[str] = Field(None, description="Plan description")
    features: dict[str, Any] = Field(default_factory=dict, description="Plan features")
    pricing_model: str = Field(..., description="Pricing model (flat, tiered, usage)")
    base_price: Decimal = Field(..., ge=0, description="Base price")
    currency: str = Field(default="USD", description="Currency code")
    billing_cycle: str = Field(..., description="Billing cycle (monthly, yearly)")
    is_active: bool = Field(default=True, description="Whether plan is active")


class BillingPlanCreate(BillingPlanBase):
    """BillingPlanCreate implementation."""

    pass


class BillingPlanUpdate(BaseModel):
    """BillingPlanUpdate implementation."""

    name: Optional[str] = None
    description: Optional[str] = None
    features: Optional[dict[str, Any]] = None
    pricing_model: Optional[str] = None
    base_price: Optional[Decimal] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    is_active: Optional[bool] = None


class BillingPlan(BillingPlanBase, BaseSchema):
    """BillingPlan implementation."""

    pass


class PricingPlanBase(BaseModel):
    """Base schema for pricing plans."""

    name: str = Field(..., description="Pricing plan name")
    description: Optional[str] = Field(None, description="Plan description")
    base_price_cents: int = Field(..., ge=0, description="Base price in cents")
    currency: str = Field(default="USD", description="Currency code")
    billing_cycle: str = Field(..., description="Billing cycle (monthly, yearly)")
    features: Optional[dict[str, Any]] = Field(None, description="Plan features")
    is_active: bool = Field(default=True, description="Whether plan is active")


class PricingPlanCreate(PricingPlanBase):
    """Schema for creating a pricing plan."""

    pass


class PricingPlanUpdate(BaseModel):
    """Schema for updating a pricing plan."""

    name: Optional[str] = None
    description: Optional[str] = None
    base_price_cents: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    features: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class PricingPlan(PricingPlanBase, BaseSchema):
    """Schema for pricing plan response."""

    pass


class SubscriptionBase(BaseModel):
    """SubscriptionBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    plan_id: UUID = Field(..., description="Billing plan ID")
    status: str = Field(..., description="Subscription status")
    start_date: date = Field(..., description="Subscription start date")
    end_date: Optional[date] = Field(None, description="Subscription end date")
    trial_end_date: Optional[date] = Field(None, description="Trial end date")
    auto_renew: bool = Field(default=True, description="Auto-renewal setting")
    custom_pricing: Optional[dict[str, Any]] = Field(None, description="Custom pricing overrides")


class SubscriptionCreate(SubscriptionBase):
    """SubscriptionCreate implementation."""

    pass


class SubscriptionUpdate(BaseModel):
    """SubscriptionUpdate implementation."""

    plan_id: Optional[UUID] = None
    status: Optional[str] = None
    end_date: Optional[date] = None
    trial_end_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    custom_pricing: Optional[dict[str, Any]] = None


class Subscription(SubscriptionBase, BaseSchema):
    """Subscription implementation."""

    plan: Optional[BillingPlan] = None


class InvoiceBase(BaseModel):
    """InvoiceBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    subscription_id: UUID = Field(..., description="Subscription ID")
    invoice_number: str = Field(..., description="Invoice number")
    status: str = Field(..., description="Invoice status")
    issue_date: date = Field(..., description="Invoice issue date")
    due_date: date = Field(..., description="Payment due date")
    subtotal: Decimal = Field(..., ge=0, description="Subtotal amount")
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Tax amount")
    total_amount: Decimal = Field(..., ge=0, description="Total amount")
    currency: str = Field(default="USD", description="Currency code")
    billing_period_start: date = Field(..., description="Billing period start")
    billing_period_end: date = Field(..., description="Billing period end")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class InvoiceCreate(InvoiceBase):
    """InvoiceCreate implementation."""

    pass


class InvoiceUpdate(BaseModel):
    """InvoiceUpdate implementation."""

    status: Optional[str] = None
    due_date: Optional[date] = None
    metadata: Optional[dict[str, Any]] = None


class Invoice(InvoiceBase, BaseSchema):
    """Invoice implementation."""

    subscription: Optional[Subscription] = None


class InvoiceLineItemBase(BaseModel):
    """InvoiceLineItemBase implementation."""

    invoice_id: UUID = Field(..., description="Invoice ID")
    description: str = Field(..., description="Line item description")
    quantity: Decimal = Field(..., gt=0, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    total_price: Decimal = Field(..., ge=0, description="Total price")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class InvoiceLineItemCreate(InvoiceLineItemBase):
    """InvoiceLineItemCreate implementation."""

    pass


class InvoiceLineItem(InvoiceLineItemBase, BaseSchema):
    """InvoiceLineItem implementation."""

    pass


class PaymentBase(BaseModel):
    """PaymentBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    invoice_id: UUID = Field(..., description="Invoice ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD", description="Currency code")
    status: str = Field(..., description="Payment status")
    payment_method: str = Field(..., description="Payment method")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    processed_at: Optional[datetime] = Field(None, description="Payment processing timestamp")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PaymentCreate(PaymentBase):
    """PaymentCreate implementation."""

    pass


class PaymentUpdate(BaseModel):
    """PaymentUpdate implementation."""

    status: Optional[str] = None
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class Payment(PaymentBase, BaseSchema):
    """Payment implementation."""

    invoice: Optional[Invoice] = None


class UsageRecordBase(BaseModel):
    """UsageRecordBase implementation."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    subscription_id: UUID = Field(..., description="Subscription ID")
    metric_name: str = Field(..., description="Usage metric name")
    quantity: Decimal = Field(..., ge=0, description="Usage quantity")
    timestamp: datetime = Field(..., description="Usage timestamp")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class UsageRecordCreate(UsageRecordBase):
    """UsageRecordCreate implementation."""

    pass


class UsageRecord(UsageRecordBase, BaseSchema):
    """UsageRecord implementation."""

    pass


# Response schemas
class BillingPlanListResponse(PaginatedResponse):
    """BillingPlanListResponse implementation."""

    items: list[BillingPlan]


class SubscriptionListResponse(PaginatedResponse):
    """SubscriptionListResponse implementation."""

    items: list[Subscription]


class InvoiceListResponse(PaginatedResponse):
    """InvoiceListResponse implementation."""

    items: list[Invoice]


class PaymentListResponse(PaginatedResponse):
    """PaymentListResponse implementation."""

    items: list[Payment]


class UsageRecordListResponse(PaginatedResponse):
    """UsageRecordListResponse implementation."""

    items: list[UsageRecord]


# Analytics schemas
class BillingAnalytics(BaseModel):
    """BillingAnalytics implementation."""

    total_revenue: Decimal
    monthly_recurring_revenue: Decimal
    annual_recurring_revenue: Decimal
    active_subscriptions: int
    churned_subscriptions: int
    trial_conversions: int
    average_revenue_per_user: Decimal
    customer_lifetime_value: Decimal
    period_start: date
    period_end: date


class TenantBillingOverview(BaseModel):
    """TenantBillingOverview implementation."""

    tenant_id: UUID
    subscription: Optional[Subscription]
    current_period_usage: dict[str, Decimal]
    outstanding_balance: Decimal
    next_billing_date: Optional[date]
    payment_method_status: str
    recent_invoices: list[Invoice]
    recent_payments: list[Payment]
