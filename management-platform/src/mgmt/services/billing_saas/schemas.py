"""
Pydantic schemas for SaaS Billing Service.

These schemas define the data transfer objects for API requests and responses
for subscription management, billing, and commission tracking.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from .models import SubscriptionStatus


class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    pricing_tier: str = Field(..., description="Pricing tier for the subscription")
    billing_cycle: str = Field(..., description="Billing cycle (monthly, yearly)")
    custom_pricing: Optional[Dict[str, Any]] = Field(None, description="Custom pricing configuration")


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription."""
    tenant_id: UUID = Field(..., description="Tenant ID for the subscription")
    start_date: Optional[datetime] = Field(None, description="Subscription start date")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    pricing_tier: Optional[str] = Field(None, description="Updated pricing tier")
    billing_cycle: Optional[str] = Field(None, description="Updated billing cycle")
    status: Optional[SubscriptionStatus] = Field(None, description="Updated subscription status")
    custom_pricing: Optional[Dict[str, Any]] = Field(None, description="Updated custom pricing")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response."""
    id: UUID = Field(..., description="Subscription ID")
    tenant_id: UUID = Field(..., description="Associated tenant ID")
    status: SubscriptionStatus = Field(..., description="Current subscription status")
    start_date: datetime = Field(..., description="Subscription start date")
    end_date: Optional[datetime] = Field(None, description="Subscription end date")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="User who created the subscription")
    updated_by: str = Field(..., description="User who last updated the subscription")
    
    model_config = ConfigDict(from_attributes=True)


class UsageRecordCreate(BaseModel):
    """Schema for creating a usage record."""
    tenant_id: UUID = Field(..., description="Tenant ID")
    subscription_id: UUID = Field(..., description="Associated subscription ID")
    metric_name: str = Field(..., description="Usage metric name")
    quantity: Decimal = Field(..., description="Usage quantity")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional usage metadata")
    timestamp: Optional[datetime] = Field(None, description="Usage timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class UsageRecordResponse(BaseModel):
    """Schema for usage record response."""
    id: UUID = Field(..., description="Usage record ID")
    tenant_id: UUID = Field(..., description="Associated tenant ID")
    subscription_id: UUID = Field(..., description="Associated subscription ID")
    metric_name: str = Field(..., description="Usage metric name")
    quantity: Decimal = Field(..., description="Usage quantity")
    timestamp: datetime = Field(..., description="Usage timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional usage metadata")
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    """Base invoice schema."""
    total_amount: Decimal = Field(..., description="Total invoice amount")
    due_date: datetime = Field(..., description="Invoice due date")
    description: Optional[str] = Field(None, description="Invoice description")


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice."""
    tenant_id: UUID = Field(..., description="Associated tenant ID")
    subscription_id: UUID = Field(..., description="Associated subscription ID")
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response."""
    id: UUID = Field(..., description="Invoice ID")
    tenant_id: UUID = Field(..., description="Associated tenant ID")
    subscription_id: UUID = Field(..., description="Associated subscription ID")
    invoice_number: str = Field(..., description="Invoice number")
    status: str = Field(..., description="Invoice status")
    issued_date: datetime = Field(..., description="Invoice issue date")
    paid_date: Optional[datetime] = Field(None, description="Payment date")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class CommissionCalculation(BaseModel):
    """Schema for commission calculation."""
    reseller_id: UUID = Field(..., description="Reseller ID")
    period_start: datetime = Field(..., description="Commission period start")
    period_end: datetime = Field(..., description="Commission period end")
    total_revenue: Decimal = Field(..., description="Total revenue for the period")
    commission_rate: Decimal = Field(..., description="Commission rate applied")
    commission_amount: Decimal = Field(..., description="Calculated commission amount")
    
    model_config = ConfigDict(from_attributes=True)


class CommissionRecordResponse(BaseModel):
    """Schema for commission record response."""
    id: UUID = Field(..., description="Commission record ID")
    reseller_id: UUID = Field(..., description="Associated reseller ID")
    tenant_id: UUID = Field(..., description="Associated tenant ID")
    commission_amount: Decimal = Field(..., description="Commission amount")
    commission_rate: Decimal = Field(..., description="Commission rate")
    calculation_period_start: datetime = Field(..., description="Calculation period start")
    calculation_period_end: datetime = Field(..., description="Calculation period end")
    status: str = Field(..., description="Commission record status")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionMetrics(BaseModel):
    """Schema for subscription metrics."""
    total_subscriptions: int = Field(..., description="Total number of subscriptions")
    active_subscriptions: int = Field(..., description="Number of active subscriptions")
    cancelled_subscriptions: int = Field(..., description="Number of cancelled subscriptions")
    trial_subscriptions: int = Field(0, description="Number of trial subscriptions")
    monthly_recurring_revenue: Optional[Decimal] = Field(None, description="Monthly recurring revenue")
    annual_recurring_revenue: Optional[Decimal] = Field(None, description="Annual recurring revenue")
    
    model_config = ConfigDict(from_attributes=True)


class BillingDashboard(BaseModel):
    """Schema for billing dashboard data."""
    metrics: SubscriptionMetrics = Field(..., description="Subscription metrics")
    recent_invoices: List[InvoiceResponse] = Field(..., description="Recent invoices")
    revenue_trend: List[Dict[str, Any]] = Field(..., description="Revenue trend data")
    top_customers: List[Dict[str, Any]] = Field(..., description="Top customers by revenue")
    
    model_config = ConfigDict(from_attributes=True)