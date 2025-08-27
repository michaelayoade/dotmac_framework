"""
Tenant Admin Billing API endpoints.
Provides billing and subscription information for tenant portal.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.billing_service import BillingService
from app.services.tenant_service import TenantService
from .auth_dependencies import get_current_tenant_user

logger = logging.getLogger(__name__)

# Response Models
class PaymentMethod(BaseModel):
    payment_method_id: str
    type: str
    card_brand: Optional[str] = None
    card_last_four: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    is_default: bool
    created_at: datetime

class InvoiceLineItem(BaseModel):
    description: str
    amount: float
    quantity: int = 1

class Invoice(BaseModel):
    invoice_id: str
    invoice_date: datetime
    due_date: datetime
    period_start: datetime
    period_end: datetime
    subtotal: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    amount_due: float
    status: str
    payment_date: Optional[datetime] = None
    line_items: List[InvoiceLineItem]
    payment_method: Optional[str] = None
    download_url: Optional[str] = None

class BillingInfo(BaseModel):
    subscription_id: str
    subscription_tier: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: datetime
    current_amount: float
    next_amount: float
    usage_charges: Dict[str, float]
    overage_charges: Dict[str, float]
    payment_methods: List[PaymentMethod]
    default_payment_method: Optional[str] = None
    recent_invoices: List[Invoice]
    account_status: str
    days_overdue: int = 0
    usage_alerts: List[str] = []
    payment_alerts: List[str] = []

class UsageBreakdown(BaseModel):
    period_start: datetime
    period_end: datetime
    base_subscription: float
    usage_charges: Dict[str, float]
    overage_charges: Dict[str, float]
    discounts: Dict[str, float]
    tax_amount: float
    total_amount: float
    estimated_next_bill: float

# Create router
tenant_billing_router = APIRouter()

@tenant_billing_router.get("/", response_model=BillingInfo)
async def get_billing_info(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get comprehensive billing information for the tenant.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        # Get services
        billing_service = BillingService(db)
        tenant_service = TenantService(db)
        
        # Get tenant and subscription info
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get billing details
        subscription = await billing_service.get_tenant_subscription(tenant_id)
        payment_methods = await billing_service.get_payment_methods(tenant_id)
        recent_invoices = await billing_service.get_recent_invoices(tenant_id, limit=5)
        current_usage = await billing_service.get_current_usage(tenant_id)
        
        # Calculate periods
        now = datetime.utcnow()
        if subscription and subscription.get("billing_cycle") == "yearly":
            period_start = now.replace(month=1, day=1)
            period_end = now.replace(year=now.year + 1, month=1, day=1)
            next_billing = period_end
        else:
            # Monthly billing
            period_start = now.replace(day=1)
            next_month = now.month % 12 + 1
            next_year = now.year + (1 if now.month == 12 else 0)
            period_end = now.replace(year=next_year, month=next_month, day=1)
            next_billing = period_end
        
        # Build payment methods
        payment_method_list = []
        default_payment_method = None
        
        for pm in payment_methods:
            payment_method = PaymentMethod(
                payment_method_id=pm.get("id", "pm_default"),
                type=pm.get("type", "card"),
                card_brand=pm.get("card", {}).get("brand"),
                card_last_four=pm.get("card", {}).get("last4"),
                card_exp_month=pm.get("card", {}).get("exp_month"),
                card_exp_year=pm.get("card", {}).get("exp_year"),
                is_default=pm.get("is_default", False),
                created_at=datetime.fromtimestamp(pm.get("created", now.timestamp()))
            )
            payment_method_list.append(payment_method)
            
            if pm.get("is_default"):
                default_payment_method = pm.get("id")
        
        # Build recent invoices
        invoice_list = []
        for inv in recent_invoices:
            line_items = []
            for line in inv.get("lines", {}).get("data", []):
                line_items.append(InvoiceLineItem(
                    description=line.get("description", "Service charge"),
                    amount=line.get("amount", 0) / 100,  # Convert from cents
                    quantity=line.get("quantity", 1)
                ))
            
            invoice = Invoice(
                invoice_id=inv.get("id", "inv_unknown"),
                invoice_date=datetime.fromtimestamp(inv.get("created", now.timestamp())),
                due_date=datetime.fromtimestamp(inv.get("due_date", now.timestamp())),
                period_start=datetime.fromtimestamp(inv.get("period_start", now.timestamp())),
                period_end=datetime.fromtimestamp(inv.get("period_end", now.timestamp())),
                subtotal=inv.get("subtotal", 0) / 100,
                tax_amount=inv.get("tax", 0) / 100,
                total_amount=inv.get("total", 0) / 100,
                amount_paid=inv.get("amount_paid", 0) / 100,
                amount_due=inv.get("amount_due", 0) / 100,
                status=inv.get("status", "draft"),
                payment_date=datetime.fromtimestamp(inv.get("status_transitions", {}).get("paid_at", 0)) if inv.get("status_transitions", {}).get("paid_at") else None,
                line_items=line_items,
                payment_method=f"{inv.get('payment_intent', {}).get('charges', {}).get('data', [{}])[0].get('payment_method_details', {}).get('card', {}).get('brand', 'Unknown')} ending in {inv.get('payment_intent', {}).get('charges', {}).get('data', [{}])[0].get('payment_method_details', {}).get('card', {}).get('last4', '****')}",
                download_url=inv.get("invoice_pdf")
            )
            invoice_list.append(invoice)
        
        # Calculate usage and overage charges
        usage_charges = {}
        overage_charges = {}
        
        if current_usage:
            # API requests
            api_requests = current_usage.get("api_requests", 0)
            included_requests = subscription.get("included_api_requests", 100000)
            if api_requests > included_requests:
                overage_requests = api_requests - included_requests
                usage_charges["api_requests"] = overage_requests * 0.01  # $0.01 per extra request
            
            # Storage
            storage_gb = current_usage.get("storage_gb", 0)
            included_storage = subscription.get("included_storage_gb", 100)
            if storage_gb > included_storage:
                overage_storage = storage_gb - included_storage
                overage_charges["storage"] = overage_storage * 0.50  # $0.50 per GB
            
            # Bandwidth
            bandwidth_gb = current_usage.get("bandwidth_gb", 0)
            included_bandwidth = subscription.get("included_bandwidth_gb", 1000)
            if bandwidth_gb > included_bandwidth:
                overage_bandwidth = bandwidth_gb - included_bandwidth
                overage_charges["bandwidth"] = overage_bandwidth * 0.10  # $0.10 per GB
        
        # Build subscription info
        subscription_tier = subscription.get("tier", tenant.subscription_tier) or "standard"
        billing_cycle = subscription.get("billing_cycle", tenant.billing_cycle) or "monthly"
        current_amount = subscription.get("amount", 2500.0)
        
        # Calculate next amount including usage
        next_amount = current_amount + sum(usage_charges.values()) + sum(overage_charges.values())
        
        # Check account status
        account_status = "active"
        days_overdue = 0
        
        if recent_invoices:
            latest_invoice = recent_invoices[0]
            if latest_invoice.get("status") == "past_due":
                account_status = "past_due"
                due_date = datetime.fromtimestamp(latest_invoice.get("due_date", now.timestamp()))
                days_overdue = max(0, (now - due_date).days)
        
        return BillingInfo(
            subscription_id=subscription.get("id", f"sub_{tenant_id}"),
            subscription_tier=subscription_tier,
            billing_cycle=billing_cycle,
            current_period_start=period_start,
            current_period_end=period_end,
            next_billing_date=next_billing,
            current_amount=current_amount,
            next_amount=next_amount,
            usage_charges=usage_charges,
            overage_charges=overage_charges,
            payment_methods=payment_method_list,
            default_payment_method=default_payment_method,
            recent_invoices=invoice_list,
            account_status=account_status,
            days_overdue=days_overdue,
            usage_alerts=[],
            payment_alerts=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get billing info for {current_user.get('tenant_id')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing information"
        )


@tenant_billing_router.get("/usage", response_model=UsageBreakdown)
async def get_usage_breakdown(
    period: str = Query("current", regex="^(current|previous)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get detailed usage breakdown for billing period.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        billing_service = BillingService(db)
        
        # Calculate period dates
        now = datetime.utcnow()
        if period == "current":
            period_start = now.replace(day=1)
            next_month = now.month % 12 + 1
            next_year = now.year + (1 if now.month == 12 else 0)
            period_end = now.replace(year=next_year, month=next_month, day=1)
        else:  # previous
            period_end = now.replace(day=1)
            prev_month = now.month - 1 if now.month > 1 else 12
            prev_year = now.year - (1 if now.month == 1 else 0)
            period_start = now.replace(year=prev_year, month=prev_month, day=1)
        
        # Get usage data for the period
        usage_data = await billing_service.get_usage_for_period(
            tenant_id, 
            period_start, 
            period_end
        )
        
        # Get subscription info
        subscription = await billing_service.get_tenant_subscription(tenant_id)
        base_amount = subscription.get("amount", 2500.0)
        
        # Calculate charges
        usage_charges = {}
        overage_charges = {}
        
        # API requests overage
        api_requests = usage_data.get("api_requests", 0)
        included_api = subscription.get("included_api_requests", 100000)
        if api_requests > included_api:
            overage_charges["api_requests"] = (api_requests - included_api) * 0.01
        
        # Storage overage
        storage_gb = usage_data.get("max_storage_gb", 0)
        included_storage = subscription.get("included_storage_gb", 100)
        if storage_gb > included_storage:
            overage_charges["storage"] = (storage_gb - included_storage) * 0.50
        
        # Bandwidth overage
        bandwidth_gb = usage_data.get("bandwidth_gb", 0)
        included_bandwidth = subscription.get("included_bandwidth_gb", 1000)
        if bandwidth_gb > included_bandwidth:
            overage_charges["bandwidth"] = (bandwidth_gb - included_bandwidth) * 0.10
        
        # Calculate totals
        subtotal = base_amount + sum(usage_charges.values()) + sum(overage_charges.values())
        discounts = {}  # Apply any discounts
        discount_total = sum(discounts.values())
        tax_rate = 0.09  # 9% tax rate
        tax_amount = (subtotal - discount_total) * tax_rate
        total_amount = subtotal - discount_total + tax_amount
        
        # Estimate next bill (current usage projected)
        if period == "current":
            days_in_period = (period_end - period_start).days
            days_elapsed = (now - period_start).days
            if days_elapsed > 0:
                projection_factor = days_in_period / days_elapsed
                estimated_next_bill = total_amount * projection_factor
            else:
                estimated_next_bill = total_amount
        else:
            estimated_next_bill = total_amount
        
        return UsageBreakdown(
            period_start=period_start,
            period_end=period_end,
            base_subscription=base_amount,
            usage_charges=usage_charges,
            overage_charges=overage_charges,
            discounts=discounts,
            tax_amount=tax_amount,
            total_amount=total_amount,
            estimated_next_bill=estimated_next_bill
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage breakdown for {current_user.get('tenant_id')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage breakdown"
        )


@tenant_billing_router.get("/invoices/{invoice_id}")
async def get_invoice_details(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get detailed information about a specific invoice.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        billing_service = BillingService(db)
        
        # Get invoice details
        invoice = await billing_service.get_invoice(tenant_id, invoice_id)
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        # Return detailed invoice information
        return {
            "invoice_id": invoice.get("id"),
            "number": invoice.get("number"),
            "status": invoice.get("status"),
            "amount_due": invoice.get("amount_due", 0) / 100,
            "amount_paid": invoice.get("amount_paid", 0) / 100,
            "total": invoice.get("total", 0) / 100,
            "subtotal": invoice.get("subtotal", 0) / 100,
            "tax": invoice.get("tax", 0) / 100,
            "created": datetime.fromtimestamp(invoice.get("created")),
            "due_date": datetime.fromtimestamp(invoice.get("due_date")),
            "period_start": datetime.fromtimestamp(invoice.get("period_start")),
            "period_end": datetime.fromtimestamp(invoice.get("period_end")),
            "pdf_url": invoice.get("invoice_pdf"),
            "hosted_url": invoice.get("hosted_invoice_url"),
            "line_items": [
                {
                    "description": line.get("description"),
                    "amount": line.get("amount", 0) / 100,
                    "quantity": line.get("quantity", 1),
                    "unit_amount": line.get("price", {}).get("unit_amount", 0) / 100
                }
                for line in invoice.get("lines", {}).get("data", [])
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get invoice {invoice_id} for {current_user.get('tenant_id')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invoice details"
        )