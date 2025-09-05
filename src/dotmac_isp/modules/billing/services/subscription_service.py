"""Subscription service for managing subscriptions."""

from datetime import date
from decimal import Decimal
from typing import Optional

from dotmac_isp.modules.billing.models import Subscription
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SubscriptionService:
    """Service for subscription operations."""

    def __init__(self, db_session: AsyncSession):
        """Init   operation."""
        self.db_session = db_session

    async def get_subscription_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return await self.db_session.get(Subscription, subscription_id)

    async def get_subscriptions_by_customer(
        self, customer_id: str, tenant_id: str, active_only: bool = True
    ) -> list[Subscription]:
        """Get all subscriptions for a customer."""
        query = select(Subscription).where(Subscription.customer_id == customer_id, Subscription.tenant_id == tenant_id)
        if active_only:
            query = query.where(Subscription.is_active is True)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def cancel_subscription(self, subscription_id: str, end_date: Optional[date] = None) -> bool:
        """Cancel a subscription."""
        subscription = await self.db_session.get(Subscription, subscription_id)
        if subscription:
            subscription.is_active = False
            subscription.end_date = end_date or date.today()
            await self.db_session.commit()
            return True
        return False

    async def update_subscription_amount(self, subscription_id: str, new_amount: Decimal) -> bool:
        """Update subscription amount."""
        subscription = await self.db_session.get(Subscription, subscription_id)
        if subscription:
            subscription.amount = new_amount
            await self.db_session.commit()
            return True
        return False

    async def get_due_subscriptions(self, tenant_id: str) -> list[Subscription]:
        """Get subscriptions that are due for billing."""
        query = select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active is True,
            Subscription.next_billing_date <= date.today(),
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
