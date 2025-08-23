"""
Billing API endpoints for subscription and payment management.
"""

from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...services.billing_service import BillingService
from ...schemas.billing import (
    BillingPlan, BillingPlanCreate, BillingPlanUpdate, BillingPlanListResponse,
    Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionListResponse,
    Invoice, InvoiceCreate, InvoiceUpdate, InvoiceListResponse,
    Payment, PaymentCreate, PaymentUpdate, PaymentListResponse,
    UsageRecord, UsageRecordCreate, UsageRecordListResponse,
    BillingAnalytics, TenantBillingOverview
)
from ...core.auth import get_current_user, require_billing_read, require_billing_write
from ...core.pagination import PaginationParams

router = APIRouter()


# Billing Plans
@router.post("/plans", response_model=BillingPlan)
async def create_billing_plan(
    plan_data: BillingPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Create a new billing plan."""
    service = BillingService(db)
    return await service.create_billing_plan(plan_data, current_user.user_id)


@router.get("/plans", response_model=BillingPlanListResponse)
async def list_billing_plans(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """List all billing plans."""
    service = BillingService(db)
    plans = await service.plan_repo.list(
        skip=pagination.skip,
        limit=pagination.limit
    )
    total = await service.plan_repo.count()
    
    return BillingPlanListResponse(
        items=plans,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/plans/{plan_id}", response_model=BillingPlan)
async def get_billing_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """Get a specific billing plan."""
    service = BillingService(db)
    plan = await service.plan_repo.get_by_id(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing plan not found"
        )
    return plan


@router.put("/plans/{plan_id}", response_model=BillingPlan)
async def update_billing_plan(
    plan_id: UUID,
    plan_update: BillingPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Update a billing plan."""
    service = BillingService(db)
    plan = await service.plan_repo.update(
        plan_id, plan_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing plan not found"
        )
    return plan


@router.delete("/plans/{plan_id}")
async def delete_billing_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Delete a billing plan."""
    service = BillingService(db)
    success = await service.plan_repo.delete(plan_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing plan not found"
        )
    return {"message": "Billing plan deleted successfully"}


# Subscriptions
@router.post("/subscriptions", response_model=Subscription)
async def create_subscription(
    tenant_id: UUID,
    plan_id: UUID,
    trial_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Create a new subscription for a tenant."""
    service = BillingService(db)
    return await service.subscribe_tenant(
        tenant_id=tenant_id,
        plan_id=plan_id,
        trial_days=trial_days,
        created_by=current_user.user_id
    )


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    tenant_id: Optional[UUID] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """List subscriptions with optional filters."""
    service = BillingService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if status:
        filters["status"] = status
    
    subscriptions = await service.subscription_repo.list(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.subscription_repo.count(filters)
    
    return SubscriptionListResponse(
        items=subscriptions,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/subscriptions/{subscription_id}", response_model=Subscription)
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """Get a specific subscription."""
    service = BillingService(db)
    subscription = await service.subscription_repo.get_with_plan(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return subscription


@router.put("/subscriptions/{subscription_id}/cancel", response_model=Subscription)
async def cancel_subscription(
    subscription_id: UUID,
    reason: Optional[str] = None,
    effective_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Cancel a subscription."""
    service = BillingService(db)
    return await service.cancel_subscription(
        subscription_id=subscription_id,
        reason=reason,
        effective_date=effective_date,
        updated_by=current_user.user_id
    )


# Invoices
@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    tenant_id: Optional[UUID] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """List invoices with optional filters."""
    service = BillingService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if status:
        filters["status"] = status
    
    invoices = await service.invoice_repo.list(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.invoice_repo.count(filters)
    
    return InvoiceListResponse(
        items=invoices,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """Get a specific invoice."""
    service = BillingService(db)
    invoice = await service.invoice_repo.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


@router.put("/invoices/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: UUID,
    invoice_update: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Update an invoice."""
    service = BillingService(db)
    invoice = await service.invoice_repo.update(
        invoice_id, invoice_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


# Payments
@router.post("/payments", response_model=Payment)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Process a payment for an invoice."""
    service = BillingService(db)
    return await service.process_payment(payment_data, current_user.user_id)


@router.get("/payments", response_model=PaymentListResponse)
async def list_payments(
    tenant_id: Optional[UUID] = None,
    invoice_id: Optional[UUID] = None,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """List payments with optional filters."""
    service = BillingService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if invoice_id:
        filters["invoice_id"] = invoice_id
    if status:
        filters["status"] = status
    
    payments = await service.payment_repo.list(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.payment_repo.count(filters)
    
    return PaymentListResponse(
        items=payments,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/payments/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """Get a specific payment."""
    service = BillingService(db)
    payment = await service.payment_repo.get_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment


# Usage Records
@router.post("/usage", response_model=dict)
async def record_usage(
    usage_data: UsageRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_write())
):
    """Record usage for a tenant's subscription."""
    service = BillingService(db)
    success = await service.record_usage(usage_data, current_user.user_id)
    
    if success:
        return {"message": "Usage recorded successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record usage"
        )


@router.get("/usage", response_model=UsageRecordListResponse)
async def list_usage_records(
    tenant_id: Optional[UUID] = None,
    subscription_id: Optional[UUID] = None,
    metric_name: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """List usage records with optional filters."""
    service = BillingService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if subscription_id:
        filters["subscription_id"] = subscription_id
    if metric_name:
        filters["metric_name"] = metric_name
    
    usage_records = await service.usage_repo.list(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.usage_repo.count(filters)
    
    return UsageRecordListResponse(
        items=usage_records,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


# Analytics and Reporting
@router.get("/analytics", response_model=BillingAnalytics)
async def get_billing_analytics(
    start_date: date = Query(..., description="Start date for analytics"),
    end_date: date = Query(..., description="End date for analytics"),
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """Get billing analytics for a period."""
    service = BillingService(db)
    return await service.generate_billing_analytics(start_date, end_date, tenant_id)


@router.get("/tenants/{tenant_id}/overview", response_model=TenantBillingOverview)
async def get_tenant_billing_overview(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_billing_read())
):
    """Get comprehensive billing overview for a tenant."""
    service = BillingService(db)
    return await service.get_tenant_billing_overview(tenant_id)