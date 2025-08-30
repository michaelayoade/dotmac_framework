"""
Concrete repository implementations for billing entities.

These repositories implement the protocol interfaces and provide
specialized query methods for each billing entity type.
"""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from ..core.models import (
    BillingPlan,
    Customer,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
)
from ..schemas.billing_schemas import (
    BillingPlanCreate,
    BillingPlanUpdate,
    CustomerCreate,
    CustomerUpdate,
    InvoiceCreate,
    PaymentCreate,
    SubscriptionCreate,
    SubscriptionUpdate,
    UsageRecordCreate,
)
from ..services.protocols import (
    BillingPlanRepositoryProtocol,
    CustomerRepositoryProtocol,
    DatabaseSessionProtocol,
    InvoiceRepositoryProtocol,
    PaymentRepositoryProtocol,
    SubscriptionRepositoryProtocol,
    UsageRepositoryProtocol,
)
from .base_repository import BaseBillingRepository


class CustomerRepository(
    BaseBillingRepository[Customer, CustomerCreate, CustomerUpdate]
):
    """Repository for customer operations."""

    def __init__(self, db: DatabaseSessionProtocol):
        super().__init__(Customer, db)

    async def get_by_email(
        self, email: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Customer]:
        """Get customer by email address."""
        query = select(self.model).where(self.model.email == email.lower())

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_customer_code(
        self, customer_code: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Customer]:
        """Get customer by customer code."""
        query = select(self.model).where(self.model.customer_code == customer_code)

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_customers(
        self, tenant_id: Optional[UUID] = None
    ) -> List[Customer]:
        """Get all active customers."""
        filters = {"is_active": True}
        return await self.get_multi(tenant_id=tenant_id, filters=filters)

    async def search_customers(
        self,
        search_term: str,
        tenant_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Customer]:
        """Search customers by name, email, or company name."""
        search_pattern = f"%{search_term.lower()}%"

        query = select(self.model).where(
            (func.lower(self.model.name).contains(search_pattern))
            | (func.lower(self.model.email).contains(search_pattern))
            | (func.lower(self.model.company_name).contains(search_pattern))
        )

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        query = query.offset(skip).limit(limit).order_by(self.model.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()


class BillingPlanRepository(
    BaseBillingRepository[BillingPlan, BillingPlanCreate, BillingPlanUpdate]
):
    """Repository for billing plan operations."""

    def __init__(self, db: DatabaseSessionProtocol):
        super().__init__(BillingPlan, db)

    async def get_by_plan_code(
        self, plan_code: str, tenant_id: Optional[UUID] = None
    ) -> Optional[BillingPlan]:
        """Get billing plan by plan code."""
        query = select(self.model).where(self.model.plan_code == plan_code)

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        # Load pricing tiers
        query = query.options(selectinload(self.model.pricing_tiers))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_plans(
        self, tenant_id: Optional[UUID] = None
    ) -> List[BillingPlan]:
        """Get all active billing plans."""
        filters = {"is_active": True}
        return await self.get_multi(
            tenant_id=tenant_id, filters=filters, load_relationships=["pricing_tiers"]
        )

    async def get_public_plans(
        self, tenant_id: Optional[UUID] = None
    ) -> List[BillingPlan]:
        """Get all public billing plans."""
        filters = {"is_active": True, "is_public": True}
        return await self.get_multi(
            tenant_id=tenant_id, filters=filters, load_relationships=["pricing_tiers"]
        )


class SubscriptionRepository(
    BaseBillingRepository[Subscription, SubscriptionCreate, SubscriptionUpdate]
):
    """Repository for subscription operations."""

    def __init__(self, db: DatabaseSessionProtocol):
        super().__init__(Subscription, db)

    async def get_by_customer(self, customer_id: UUID) -> List[Subscription]:
        """Get all subscriptions for a customer."""
        filters = {"customer_id": customer_id}
        return await self.get_multi(
            filters=filters, load_relationships=["customer", "billing_plan"]
        )

    async def get_active_subscriptions(
        self, tenant_id: Optional[UUID] = None
    ) -> List[Subscription]:
        """Get all active subscriptions."""
        filters = {"status": SubscriptionStatus.ACTIVE}
        return await self.get_multi(
            tenant_id=tenant_id,
            filters=filters,
            load_relationships=["customer", "billing_plan"],
        )

    async def get_due_for_billing(
        self, billing_date: date = None
    ) -> List[Subscription]:
        """Get subscriptions due for billing on a specific date."""
        if billing_date is None:
            billing_date = date.today()

        query = (
            select(self.model)
            .where(
                and_(
                    self.model.status == SubscriptionStatus.ACTIVE,
                    self.model.next_billing_date <= billing_date,
                )
            )
            .options(
                selectinload(self.model.customer), selectinload(self.model.billing_plan)
            )
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_subscription_number(
        self, subscription_number: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Subscription]:
        """Get subscription by subscription number."""
        query = select(self.model).where(
            self.model.subscription_number == subscription_number
        )

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        query = query.options(
            selectinload(self.model.customer), selectinload(self.model.billing_plan)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_expiring_subscriptions(
        self, days_ahead: int = 30, tenant_id: Optional[UUID] = None
    ) -> List[Subscription]:
        """Get subscriptions expiring within specified days."""
        expiry_date = date.today() + datetime.timedelta(days=days_ahead)

        query = select(self.model).where(
            and_(
                self.model.status == SubscriptionStatus.ACTIVE,
                self.model.end_date.isnot(None),
                self.model.end_date <= expiry_date,
            )
        )

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        query = query.options(
            selectinload(self.model.customer), selectinload(self.model.billing_plan)
        )

        result = await self.db.execute(query)
        return result.scalars().all()


class InvoiceRepository(BaseBillingRepository[Invoice, InvoiceCreate, None]):
    """Repository for invoice operations."""

    def __init__(self, db: DatabaseSessionProtocol):
        super().__init__(Invoice, db)

    async def get_by_customer(self, customer_id: UUID) -> List[Invoice]:
        """Get all invoices for a customer."""
        filters = {"customer_id": customer_id}
        return await self.get_multi(
            filters=filters, load_relationships=["customer", "line_items", "payments"]
        )

    async def get_by_subscription(self, subscription_id: UUID) -> List[Invoice]:
        """Get all invoices for a subscription."""
        filters = {"subscription_id": subscription_id}
        return await self.get_multi(
            filters=filters,
            load_relationships=["customer", "subscription", "line_items"],
        )

    async def get_by_status(
        self, status: InvoiceStatus, tenant_id: Optional[UUID] = None
    ) -> List[Invoice]:
        """Get invoices by status."""
        filters = {"status": status}
        return await self.get_multi(
            tenant_id=tenant_id,
            filters=filters,
            load_relationships=["customer", "line_items"],
        )

    async def get_overdue_invoices(
        self, tenant_id: Optional[UUID] = None
    ) -> List[Invoice]:
        """Get all overdue invoices."""
        today = date.today()

        query = select(self.model).where(
            and_(
                self.model.status.in_([InvoiceStatus.SENT, InvoiceStatus.PENDING]),
                self.model.due_date < today,
                self.model.amount_due > 0,
            )
        )

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        query = query.options(
            selectinload(self.model.customer), selectinload(self.model.line_items)
        ).order_by(self.model.due_date.asc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_invoice_number(
        self, invoice_number: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        query = select(self.model).where(self.model.invoice_number == invoice_number)

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        query = query.options(
            selectinload(self.model.customer),
            selectinload(self.model.line_items),
            selectinload(self.model.payments),
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_revenue_by_period(
        self, start_date: date, end_date: date, tenant_id: Optional[UUID] = None
    ) -> List[dict]:
        """Get revenue summary by period."""
        query = (
            select(
                func.date_trunc("month", self.model.invoice_date).label("period"),
                func.sum(self.model.total_amount).label("total_revenue"),
                func.count(self.model.id).label("invoice_count"),
            )
            .where(
                and_(
                    self.model.invoice_date >= start_date,
                    self.model.invoice_date <= end_date,
                    self.model.status.in_([InvoiceStatus.PAID, InvoiceStatus.SENT]),
                )
            )
            .group_by("period")
            .order_by("period")
        )

        if tenant_id is not None:
            query = query.where(self.model.tenant_id == tenant_id)

        result = await self.db.execute(query)
        return [
            {
                "period": row.period,
                "total_revenue": row.total_revenue,
                "invoice_count": row.invoice_count,
            }
            for row in result
        ]


class PaymentRepository(BaseBillingRepository[Payment, PaymentCreate, None]):
    """Repository for payment operations."""

    def __init__(self, db: DatabaseSessionProtocol):
        super().__init__(Payment, db)

    async def get_by_customer(self, customer_id: UUID) -> List[Payment]:
        """Get all payments for a customer."""
        filters = {"customer_id": customer_id}
        return await self.get_multi(
            filters=filters, load_relationships=["customer", "invoice"]
        )

    async def get_by_invoice(self, invoice_id: UUID) -> List[Payment]:
        """Get all payments for an invoice."""
        filters = {"invoice_id": invoice_id}
        return await self.get_multi(filters=filters, load_relationships=["customer"])

    async def get_by_status(
        self, status: PaymentStatus, tenant_id: Optional[UUID] = None
    ) -> List[Payment]:
        """Get payments by status."""
        filters = {"status": status}
        return await self.get_multi(
            tenant_id=tenant_id,
            filters=filters,
            load_relationships=["customer", "invoice"],
        )

    async def get_failed_payments(
        self, tenant_id: Optional[UUID] = None
    ) -> List[Payment]:
        """Get failed payments that need attention."""
        filters = {"status": PaymentStatus.FAILED}
        return await self.get_multi(
            tenant_id=tenant_id,
            filters=filters,
            load_relationships=["customer", "invoice"],
        )

    async def get_payments_by_date_range(
        self, start_date: date, end_date: date, tenant_id: Optional[UUID] = None
    ) -> List[Payment]:
        """Get payments within a date range."""
        filters = {"payment_date": {"gte": start_date, "lte": end_date}}
        return await self.get_multi(
            tenant_id=tenant_id,
            filters=filters,
            load_relationships=["customer", "invoice"],
        )


class UsageRepository(BaseBillingRepository[UsageRecord, UsageRecordCreate, None]):
    """Repository for usage record operations."""

    def __init__(self, db: DatabaseSessionProtocol):
        super().__init__(UsageRecord, db)

    async def get_by_subscription(
        self,
        subscription_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[UsageRecord]:
        """Get usage records for a subscription within date range."""
        filters = {"subscription_id": subscription_id}

        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["gte"] = start_date
            if end_date:
                date_filter["lte"] = end_date
            filters["usage_date"] = date_filter

        return await self.get_multi(
            filters=filters, load_relationships=["subscription"]
        )

    async def get_unprocessed_usage(
        self, tenant_id: Optional[UUID] = None
    ) -> List[UsageRecord]:
        """Get unprocessed usage records."""
        filters = {"processed": False}
        return await self.get_multi(
            tenant_id=tenant_id, filters=filters, load_relationships=["subscription"]
        )

    async def get_usage_summary_by_subscription(
        self, subscription_id: UUID, start_date: date, end_date: date
    ) -> dict:
        """Get usage summary for a subscription in a period."""
        query = select(
            func.sum(self.model.quantity).label("total_usage"),
            func.count(self.model.id).label("usage_count"),
            func.sum(self.model.amount).label("total_amount"),
        ).where(
            and_(
                self.model.subscription_id == subscription_id,
                self.model.usage_date >= start_date,
                self.model.usage_date <= end_date,
            )
        )

        result = await self.db.execute(query)
        row = result.first()

        return {
            "total_usage": row.total_usage or 0,
            "usage_count": row.usage_count or 0,
            "total_amount": row.total_amount or 0,
        }

    async def bulk_mark_processed(self, usage_ids: List[UUID]) -> int:
        """Mark multiple usage records as processed."""
        if not usage_ids:
            return 0

        query = select(self.model).where(self.model.id.in_(usage_ids))
        result = await self.db.execute(query)
        usage_records = result.scalars().all()

        count = 0
        for usage_record in usage_records:
            usage_record.processed = True
            usage_record.processed_date = datetime.utcnow()
            count += 1

        await self.db.commit()
        return count
