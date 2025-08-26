"""
Additional billing repository methods that are expected by the service layer.
"""

from typing import Optional, List
from uuid import UUID
from datetime import date
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.billing import PricingPlan, Subscription, Invoice, Payment, UsageRecord
from repositories.base import BaseRepository


class BillingPlanRepository(BaseRepository[PricingPlan]):
    """Repository for billing plan operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, PricingPlan)


class PricingPlanRepository(BaseRepository[PricingPlan]):
    """Repository for pricing plan operations (alias for BillingPlanRepository)."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, PricingPlan)


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Subscription)
    
    async def get_active_subscription(self, tenant_id: UUID) -> Optional[Subscription]:
        """Get active subscription for a tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.status.in_(["active", "trial"]),
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_plan(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription with plan details."""
        # For now, just get the subscription - would implement join with plan in full implementation
        return await self.get_by_id(subscription_id)
    
    async def update_status(self, subscription_id: UUID, status: str, updated_by: str) -> Optional[Subscription]:
        """Update subscription status."""
        return await self.update(subscription_id, {"status": status}, updated_by)
    
    async def get_expiring_subscriptions(self, cutoff_date: date) -> List[Subscription]:
        """Get subscriptions expiring before cutoff date."""
        stmt = select(self.model).where(
            and_(
                self.model.end_date <= cutoff_date,
                self.model.status == "active",
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_usage_based_subscriptions(self, tenant_id: UUID = None) -> List[Subscription]:
        """Get subscriptions with usage-based billing."""
        filters = {"is_deleted": False}
        if tenant_id:
            filters["tenant_id"] = tenant_id
        return await self.list(filters=filters)
    
    async def count_active_subscriptions(self, tenant_id: UUID = None) -> int:
        """Count active subscriptions."""
        filters = {"status": "active", "is_deleted": False}
        if tenant_id:
            filters["tenant_id"] = tenant_id
        return await self.count(filters)


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for invoice operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Invoice)
    
    async def update_status(self, invoice_id: UUID, status: str, updated_by: str) -> Optional[Invoice]:
        """Update invoice status."""
        return await self.update(invoice_id, {"status": status}, updated_by)
    
    async def get_overdue_invoices(self, cutoff_date: date) -> List[Invoice]:
        """Get overdue invoices."""
        stmt = select(self.model).where(
            and_(
                self.model.due_date <= cutoff_date,
                self.model.status == "pending",
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_tenant_invoices(self, tenant_id: UUID, limit: int = 10) -> List[Invoice]:
        """Get recent invoices for a tenant."""
        return await self.list(
            filters={"tenant_id": tenant_id, "is_deleted": False},
            limit=limit,
            order_by="created_at DESC"
        )
    
    async def get_unpaid_invoices(self, tenant_id: UUID) -> List[Invoice]:
        """Get unpaid invoices for a tenant."""
        return await self.list(
            filters={"tenant_id": tenant_id, "status": "pending", "is_deleted": False}
        )
    
    async def get_tenant_invoices_for_period(self, tenant_id: UUID, start_date: date, end_date: date) -> List[Invoice]:
        """Get tenant invoices for a period."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.issue_date >= start_date,
                self.model.issue_date <= end_date,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


class PaymentRepository(BaseRepository[Payment]):
    """Repository for payment operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Payment)
    
    async def update_status(self, payment_id: UUID, status: str, updated_by: str) -> Optional[Payment]:
        """Update payment status."""
        return await self.update(payment_id, {"status": status}, updated_by)
    
    async def get_tenant_payments(self, tenant_id: UUID, limit: int = 10) -> List[Payment]:
        """Get recent payments for a tenant."""
        return await self.list(
            filters={"tenant_id": tenant_id, "is_deleted": False},
            limit=limit,
            order_by="created_at DESC"
        )
    
    async def get_pending_payments(self, provider: str = None) -> List[Payment]:
        """Get pending payments."""
        filters = {"status": "pending", "is_deleted": False}
        if provider:
            filters["payment_method"] = provider
        return await self.list(filters=filters)
    
    async def get_payments_in_period(self, start_date: date, end_date: date, tenant_id: UUID = None) -> List[Payment]:
        """Get payments in a date period."""
        stmt = select(self.model).where(
            and_(
                self.model.processed_at >= start_date,
                self.model.processed_at <= end_date,
                self.model.status == "completed",
                self.model.is_deleted == False
            )
        )
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_tenant_payments_for_period(self, tenant_id: UUID, start_date: date, end_date: date) -> List[Payment]:
        """Get tenant payments for a period."""
        return await self.get_payments_in_period(start_date, end_date, tenant_id)


class UsageRecordRepository(BaseRepository[UsageRecord]):
    """Repository for usage record operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, UsageRecord)
    
    async def get_period_usage(self, subscription_id: UUID, metric_name: str, start_date: date, end_date: date) -> Decimal:
        """Get usage for a subscription in a period."""
        stmt = select(self.model).where(
            and_(
                self.model.subscription_id == subscription_id,
                self.model.metric_name == metric_name,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        usage_records = result.scalars().all()
        return sum(record.quantity for record in usage_records)
    
    async def get_period_usage_detailed(self, subscription_id: UUID, start_date: date, end_date: date) -> List[UsageRecord]:
        """Get detailed usage records for a period."""
        stmt = select(self.model).where(
            and_(
                self.model.subscription_id == subscription_id,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_tenant_usage_for_period(self, tenant_id: UUID, start_date: date, end_date: date) -> List[UsageRecord]:
        """Get tenant usage for a period."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.timestamp >= start_date,
                self.model.timestamp <= end_date,
                self.model.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()