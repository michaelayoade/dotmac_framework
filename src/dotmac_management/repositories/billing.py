"""
Billing repository for subscription and payment operations.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.billing import (
    Commission,
    CommissionStatus,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    PricingPlan,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
)
from ..repositories.base import BaseRepository


class PricingPlanRepository(BaseRepository[PricingPlan]):
    """Repository for pricing plan operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PricingPlan)

    async def get_by_slug(self, slug: str) -> Optional[PricingPlan]:
        """Get pricing plan by slug."""
        return await self.get_by_field("slug", slug)

    async def get_active_plans(self, public_only: bool = True) -> list[PricingPlan]:
        """Get active pricing plans."""
        filters = {"is_active": True}
        if public_only:
            filters["is_public"] = True

        return await self.list(filters=filters, order_by="base_price_cents")

    async def get_by_stripe_price_id(
        self, stripe_price_id: str
    ) -> Optional[PricingPlan]:
        """Get plan by Stripe price ID."""
        return await self.get_by_field("stripe_price_id", stripe_price_id)


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Subscription)

    async def get_by_tenant(self, tenant_id: UUID) -> list[Subscription]:
        """Get subscriptions for a tenant."""
        return await self.list(
            filters={"tenant_id": tenant_id},
            order_by="-created_at",
            relationships=["pricing_plan", "tenant"],
        )

    async def get_active_subscription(self, tenant_id: UUID) -> Optional[Subscription]:
        """Get active subscription for tenant."""
        query = (
            select(Subscription)
            .where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(
                    [SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE]
                ),
                Subscription.is_deleted is False,
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_stripe_id(
        self, stripe_subscription_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe ID."""
        return await self.get_by_field("stripe_subscription_id", stripe_subscription_id)

    async def get_expiring_trials(self, days_ahead: int = 3) -> list[Subscription]:
        """Get trial subscriptions expiring soon."""
        expiry_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        query = select(Subscription).where(
            Subscription.status == SubscriptionStatus.TRIAL,
            Subscription.trial_end <= expiry_date,
            Subscription.is_deleted is False,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_subscriptions_for_renewal(self) -> list[Subscription]:
        """Get subscriptions due for renewal."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        query = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end <= tomorrow,
            Subscription.cancel_at_period_end is False,
            Subscription.is_deleted is False,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_usage(
        self, subscription_id: UUID, usage_data: dict[str, Any]
    ) -> bool:
        """Update subscription usage."""
        return (
            await self.update(subscription_id, {"current_usage": usage_data})
            is not None
        )


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for invoice operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Invoice)

    async def get_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by number."""
        return await self.get_by_field("invoice_number", invoice_number)

    async def get_by_subscription(
        self, subscription_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invoice]:
        """Get invoices for a subscription."""
        return await self.list(
            filters={"subscription_id": subscription_id},
            skip=skip,
            limit=limit,
            order_by="-invoice_date",
            relationships=["subscription", "payments"],
        )

    async def get_overdue_invoices(self) -> list[Invoice]:
        """Get overdue invoices."""
        today = datetime.now(timezone.utc)

        query = select(Invoice).where(
            Invoice.due_date < today,
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.DRAFT]),
            Invoice.is_deleted is False,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unpaid_invoices(
        self, tenant_id: Optional[UUID] = None
    ) -> list[Invoice]:
        """Get unpaid invoices."""
        query = (
            select(Invoice)
            .join(Subscription)
            .where(Invoice.status != InvoiceStatus.PAID, Invoice.is_deleted is False)
        )
        if tenant_id:
            query = query.where(Subscription.tenant_id == tenant_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        from datetime import datetime

        # Get count of invoices this month
        today = datetime.now(timezone.utc)
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        query = select(func.count(Invoice.id)).where(
            Invoice.invoice_date >= month_start
        )
        result = await self.db.execute(query)
        count = result.scalar() + 1

        return f"INV-{today.strftime('%Y%m')}-{count:04d}"

    async def mark_as_paid(
        self, invoice_id: UUID, payment_date: Optional[datetime] = None
    ) -> bool:
        """Mark invoice as paid."""
        update_data = {
            "status": InvoiceStatus.PAID,
            "paid_at": payment_date or datetime.now(timezone.utc),
            "amount_paid_cents": Invoice.total_cents,
        }

        return await self.update(invoice_id, update_data) is not None


class PaymentRepository(BaseRepository[Payment]):
    """Repository for payment operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Payment)

    async def get_by_invoice(self, invoice_id: UUID) -> list[Payment]:
        """Get payments for an invoice."""
        return await self.list(
            filters={"invoice_id": invoice_id}, order_by="-created_at"
        )

    async def get_by_stripe_payment_intent(
        self, stripe_payment_intent_id: str
    ) -> Optional[Payment]:
        """Get payment by Stripe payment intent ID."""
        return await self.get_by_field(
            "stripe_payment_intent_id", stripe_payment_intent_id
        )

    async def get_successful_payments(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """Get successful payments in date range."""

        query = select(Payment).where(Payment.status == PaymentStatus.SUCCEEDED)

        if start_date:
            query = query.where(Payment.processed_at >= start_date)
        if end_date:
            query = query.where(Payment.processed_at <= end_date)

        query = query.order_by(Payment.processed_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_failed_payments(
        self, retry_eligible: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Payment]:
        """Get failed payments, optionally only retry-eligible ones."""
        query = select(Payment).where(Payment.status == PaymentStatus.FAILED)

        if retry_eligible:
            # Only payments failed in last 3 days
            three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
            query = query.where(Payment.failed_at >= three_days_ago)

        query = query.order_by(Payment.failed_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def calculate_revenue(
        self, start_date: datetime, end_date: datetime, tenant_id: Optional[UUID] = None
    ) -> Decimal:
        """Calculate revenue for date range."""
        query = select(func.sum(Payment.amount_cents)).where(
            Payment.status == PaymentStatus.SUCCEEDED,
            Payment.processed_at >= start_date,
            Payment.processed_at <= end_date,
        )
        if tenant_id:
            query = (
                query.join(Invoice)
                .join(Subscription)
                .where(Subscription.tenant_id == tenant_id)
            )
        result = await self.db.execute(query)
        total_cents = result.scalar() or 0
        return Decimal(total_cents) / 100


class UsageRecordRepository(BaseRepository[UsageRecord]):
    """Repository for usage-based billing records."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, UsageRecord)

    async def get_unbilled_usage(
        self, subscription_id: UUID, end_date: Optional[datetime] = None
    ) -> list[UsageRecord]:
        """Get unbilled usage records for subscription."""

        query = select(UsageRecord).where(
            UsageRecord.subscription_id == subscription_id, UsageRecord.billed is False
        )
        if end_date:
            query = query.where(UsageRecord.usage_date <= end_date)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_as_billed(
        self, usage_record_ids: list[UUID], invoice_id: UUID
    ) -> int:
        """Mark usage records as billed."""
        from sqlalchemy import update

        query = (
            update(UsageRecord)
            .where(UsageRecord.id.in_(usage_record_ids))
            .values(billed=True, invoice_id=invoice_id)
        )
        result = await self.db.execute(query)
        return result.rowcount

    async def get_usage_summary(
        self, subscription_id: UUID, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Get usage summary for subscription in date range."""
        query = (
            select(
                UsageRecord.metric_name,
                func.sum(UsageRecord.quantity).label("total_quantity"),
                func.sum(UsageRecord.total_cost_cents).label("total_cost_cents"),
            )
            .where(
                UsageRecord.subscription_id == subscription_id,
                UsageRecord.usage_date >= start_date,
                UsageRecord.usage_date <= end_date,
            )
            .group_by(UsageRecord.metric_name)
        )

        result = await self.db.execute(query)

        summary = {}
        for row in result:
            summary[row.metric_name] = {
                "quantity": float(row.total_quantity),
                "cost": Decimal(row.total_cost_cents or 0) / 100,
            }

        return summary


class CommissionRepository(BaseRepository[Commission]):
    """Repository for reseller commission operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Commission)

    async def get_by_reseller(
        self,
        reseller_id: UUID,
        status: Optional[CommissionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Commission]:
        """Get commissions for a reseller."""
        filters = {"reseller_id": reseller_id}

        if status:
            filters["status"] = status

        return await self.list(
            filters=filters,
            skip=skip,
            limit=limit,
            order_by="-earned_date",
            relationships=["tenant", "subscription"],
        )

    async def get_unpaid_commissions(
        self, reseller_id: Optional[UUID] = None
    ) -> list[Commission]:
        """Get unpaid commissions."""
        filters = {"status": CommissionStatus.APPROVED}

        if reseller_id:
            filters["reseller_id"] = reseller_id

        return await self.list(filters=filters, order_by="earned_date")

    async def calculate_total_commission(
        self,
        reseller_id: UUID,
        status: Optional[CommissionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Decimal:
        """Calculate total commission amount."""
        query = select(func.sum(Commission.commission_amount_cents)).where(
            Commission.reseller_id == reseller_id
        )
        if status:
            query = query.where(Commission.status == status)
        if start_date:
            query = query.where(Commission.earned_date >= start_date)
        if end_date:
            query = query.where(Commission.earned_date <= end_date)

        result = await self.db.execute(query)
        total_cents = result.scalar() or 0
        return Decimal(total_cents) / 100

    async def approve_commissions(
        self, commission_ids: list[UUID], user_id: Optional[str] = None
    ) -> int:
        """Approve multiple commissions."""
        from sqlalchemy import update

        query = (
            update(Commission)
            .where(
                Commission.id.in_(commission_ids),
                Commission.status == CommissionStatus.PENDING,
            )
            .values(status=CommissionStatus.APPROVED)
        )
        if user_id:
            query = query.values(updated_by=user_id)

        result = await self.db.execute(query)
        return result.rowcount

    async def mark_as_paid(
        self,
        commission_ids: list[UUID],
        payment_reference: str,
        user_id: Optional[str] = None,
    ) -> int:
        """Mark commissions as paid."""
        from sqlalchemy import update

        query = (
            update(Commission)
            .where(
                Commission.id.in_(commission_ids),
                Commission.status == CommissionStatus.APPROVED,
            )
            .values(
                status=CommissionStatus.PAID,
                paid_at=func.now(),
                payment_reference=payment_reference,
            )
        )

        if user_id:
            query = query.values(updated_by=user_id)

        result = await self.db.execute(query)
        return result.rowcount
