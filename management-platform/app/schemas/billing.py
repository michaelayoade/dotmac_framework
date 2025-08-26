"""
Billing and subscription schemas for validation and serialization.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from schemas.common import BaseSchema, PaginatedResponse


# Stripe Integration Schemas

class StripeCustomerCreate(BaseModel):
    """Schema for creating Stripe customer."""
    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Customer name")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")


class StripeSubscriptionCreate(BaseModel):
    """Schema for creating Stripe subscription."""
    customer_id: str = Field(..., description="Stripe customer ID")
    price_id: str = Field(..., description="Stripe price ID")
    trial_days: Optional[int] = Field(None, description="Trial period in days")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")


class StripeWebhookEvent(BaseModel):
    """Schema for Stripe webhook events."""
    id: str = Field(..., description="Event ID")
    object: str = Field(..., description="Event object type")
    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")


class PaymentIntentCreate(BaseModel):
    """Schema for creating payment intent."""
    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    currency: str = Field(default="usd", description="Currency code")
    customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response."""
    payment_intent_id: str = Field(..., description="Payment intent ID")
    client_secret: str = Field(..., description="Client secret for frontend")
    status: str = Field(..., description="Payment intent status")
    amount: int = Field(..., description="Amount in cents")


class BillingPlanBase(BaseModel):
    name: str = Field(..., description="Plan name")
    description: Optional[str] = Field(None, description="Plan description")
    features: Dict[str, Any] = Field(default_factory=dict, description="Plan features")
    pricing_model: str = Field(..., description="Pricing model (flat, tiered, usage)")
    base_price: Decimal = Field(..., ge=0, description="Base price")
    currency: str = Field(default="USD", description="Currency code")
    billing_cycle: str = Field(..., description="Billing cycle (monthly, yearly)")
    is_active: bool = Field(default=True, description="Whether plan is active")


class BillingPlanCreate(BillingPlanBase):
    pass


class BillingPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    pricing_model: Optional[str] = None
    base_price: Optional[Decimal] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    is_active: Optional[bool] = None


class BillingPlan(BillingPlanBase, BaseSchema):
    pass


class PricingPlanBase(BaseModel):
    """Base schema for pricing plans."""
    name: str = Field(..., description="Pricing plan name")
    description: Optional[str] = Field(None, description="Plan description")
    base_price_cents: int = Field(..., ge=0, description="Base price in cents")
    currency: str = Field(default="USD", description="Currency code")
    billing_cycle: str = Field(..., description="Billing cycle (monthly, yearly)")
    features: Optional[Dict[str, Any]] = Field(None, description="Plan features")
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
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PricingPlan(PricingPlanBase, BaseSchema):
    """Schema for pricing plan response."""
    pass


class SubscriptionBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    plan_id: UUID = Field(..., description="Billing plan ID")
    status: str = Field(..., description="Subscription status")
    start_date: date = Field(..., description="Subscription start date")
    end_date: Optional[date] = Field(None, description="Subscription end date")
    trial_end_date: Optional[date] = Field(None, description="Trial end date")
    auto_renew: bool = Field(default=True, description="Auto-renewal setting")
    custom_pricing: Optional[Dict[str, Any]] = Field(None, description="Custom pricing overrides")


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    plan_id: Optional[UUID] = None
    status: Optional[str] = None
    end_date: Optional[date] = None
    trial_end_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    custom_pricing: Optional[Dict[str, Any]] = None


class Subscription(SubscriptionBase, BaseSchema):
    plan: Optional[BillingPlan] = None


class InvoiceBase(BaseModel):
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
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    due_date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None


class Invoice(InvoiceBase, BaseSchema):
    subscription: Optional[Subscription] = None


class InvoiceLineItemBase(BaseModel):
    invoice_id: UUID = Field(..., description="Invoice ID")
    description: str = Field(..., description="Line item description")
    quantity: Decimal = Field(..., gt=0, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    total_price: Decimal = Field(..., ge=0, description="Total price")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass


class InvoiceLineItem(InvoiceLineItemBase, BaseSchema):
    pass


class PaymentBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    invoice_id: UUID = Field(..., description="Invoice ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD", description="Currency code")
    status: str = Field(..., description="Payment status")
    payment_method: str = Field(..., description="Payment method")
    transaction_id: Optional[str] = Field(None, description="External transaction ID")
    processed_at: Optional[datetime] = Field(None, description="Payment processing timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class Payment(PaymentBase, BaseSchema):
    invoice: Optional[Invoice] = None


class UsageRecordBase(BaseModel):
    tenant_id: UUID = Field(..., description="Tenant ID")
    subscription_id: UUID = Field(..., description="Subscription ID")
    metric_name: str = Field(..., description="Usage metric name")
    quantity: Decimal = Field(..., ge=0, description="Usage quantity")
    timestamp: datetime = Field(..., description="Usage timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class UsageRecordCreate(UsageRecordBase):
    pass


class UsageRecord(UsageRecordBase, BaseSchema):
    pass


# Response schemas
class BillingPlanListResponse(PaginatedResponse):
    items: List[BillingPlan]


class SubscriptionListResponse(PaginatedResponse):
    items: List[Subscription]


class InvoiceListResponse(PaginatedResponse):
    items: List[Invoice]


class PaymentListResponse(PaginatedResponse):
    items: List[Payment]


class UsageRecordListResponse(PaginatedResponse):
    items: List[UsageRecord]


# Analytics schemas
class BillingAnalytics(BaseModel):
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
    tenant_id: UUID
    subscription: Optional[Subscription]
    current_period_usage: Dict[str, Decimal]
    outstanding_balance: Decimal
    next_billing_date: Optional[date]
    payment_method_status: str
    recent_invoices: List[Invoice]
    recent_payments: List[Payment]