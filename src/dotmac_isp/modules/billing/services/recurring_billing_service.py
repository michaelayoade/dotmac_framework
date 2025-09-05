"""Recurring billing service for automated billing cycles."""

from datetime import date, datetime
from typing import Optional

from dotmac_isp.modules.billing.models import BillingCycle, Invoice, Subscription
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .billing_service import BillingService


class RecurringBillingService:
    """Service for managing recurring billing operations."""

    def __init__(self, db_session: AsyncSession):
        """Init   operation."""
        self.db_session = db_session
        self.billing_service = BillingService(db_session)

    async def process_recurring_billing(self, tenant_id: str) -> list[Invoice]:
        """Process all due recurring billing for a tenant."""
        # Get all due subscriptions
        query = select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active is True,
            Subscription.next_billing_date <= date.today(),
        )
        result = await self.db_session.execute(query)
        due_subscriptions = result.scalars().all()

        invoices = []
        for subscription in due_subscriptions:
            invoice = await self._create_invoice_from_subscription(subscription)
            if invoice:
                invoices.append(invoice)
                await self._update_next_billing_date(subscription)

        return invoices

    async def _create_invoice_from_subscription(
        self, subscription: Subscription
    ) -> Optional[Invoice]:
        """Create an invoice from a subscription."""
        line_items = [
            {
                "description": f"Subscription for Service {subscription.service_instance_id}",
                "quantity": 1,
                "unit_price": subscription.amount,
            }
        ]

        invoice = await self.billing_service.create_invoice(
            customer_id=subscription.customer_id,
            tenant_id=subscription.tenant_id,
            line_items=line_items,
            due_date=date.today() + datetime.timedelta(days=30),
        )
        return invoice

    async def _update_next_billing_date(self, subscription: Subscription) -> None:
        """Update the next billing date for a subscription."""
        if subscription.billing_cycle == BillingCycle.MONTHLY:
            from dateutil.relativedelta import relativedelta

            subscription.next_billing_date = (
                subscription.next_billing_date + relativedelta(months=1)
            )
        elif subscription.billing_cycle == BillingCycle.QUARTERLY:
            from dateutil.relativedelta import relativedelta

            subscription.next_billing_date = (
                subscription.next_billing_date + relativedelta(months=3)
            )
        elif subscription.billing_cycle == BillingCycle.ANNUALLY:
            from dateutil.relativedelta import relativedelta

            subscription.next_billing_date = (
                subscription.next_billing_date + relativedelta(years=1)
            )

        await self.db_session.commit()

    async def create_recurring_invoice(
        self, subscription_id: str, billing_date: Optional[date] = None
    ) -> Optional[Invoice]:
        """Create a recurring invoice for a specific subscription."""
        subscription = await self.db_session.get(Subscription, subscription_id)
        if not subscription or not subscription.is_active:
            return None

        return await self._create_invoice_from_subscription(subscription)
