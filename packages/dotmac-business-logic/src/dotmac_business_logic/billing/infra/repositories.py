"""
SQLAlchemy implementations of billing repositories.

This module implements the repository interfaces defined in the core
domain using SQLAlchemy for data persistence.
"""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.interfaces import BillingRepository
from ..core.models import InvoiceStatus, PaymentStatus


class SQLAlchemyBillingRepository(BillingRepository):
    """SQLAlchemy implementation of billing repository."""

    def __init__(
        self,
        session: AsyncSession,
        customer_model: type,
        subscription_model: type,
        invoice_model: type,
        payment_model: type,
        usage_record_model: type,
        tenant_id: Optional[UUID] = None,
    ):
        """
        Initialize repository with SQLAlchemy session and model classes.

        Args:
            session: Async SQLAlchemy session
            customer_model: Customer ORM model class
            subscription_model: Subscription ORM model class
            invoice_model: Invoice ORM model class
            payment_model: Payment ORM model class
            usage_record_model: UsageRecord ORM model class
            tenant_id: Tenant ID for multi-tenant filtering
        """
        self.session = session
        self.customer_model = customer_model
        self.subscription_model = subscription_model
        self.invoice_model = invoice_model
        self.payment_model = payment_model
        self.usage_record_model = usage_record_model
        self.tenant_id = tenant_id

    def _add_tenant_filter(self, query, model_class):
        """Add tenant filtering to query if tenant_id is set."""
        if self.tenant_id and hasattr(model_class, 'tenant_id'):
            return query.where(model_class.tenant_id == self.tenant_id)
        return query

    # Customer operations
    async def get_customer(self, customer_id: UUID) -> Any:
        """Get customer by ID."""
        query = select(self.customer_model).where(self.customer_model.id == customer_id)
        query = self._add_tenant_filter(query, self.customer_model)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_customer(self, customer_data: dict[str, Any]) -> Any:
        """Create new customer."""
        if self.tenant_id:
            customer_data['tenant_id'] = self.tenant_id

        customer = self.customer_model(**customer_data)
        self.session.add(customer)
        await self.session.flush()
        return customer

    # Subscription operations
    async def get_subscription(self, subscription_id: UUID) -> Any:
        """Get subscription by ID with related data."""
        query = (
            select(self.subscription_model)
            .options(
                selectinload(self.subscription_model.customer),
                selectinload(self.subscription_model.billing_plan),
            )
            .where(self.subscription_model.id == subscription_id)
        )
        query = self._add_tenant_filter(query, self.subscription_model)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_customer_subscriptions(self, customer_id: UUID) -> list[Any]:
        """Get all subscriptions for a customer."""
        query = (
            select(self.subscription_model)
            .options(selectinload(self.subscription_model.billing_plan))
            .where(self.subscription_model.customer_id == customer_id)
        )
        query = self._add_tenant_filter(query, self.subscription_model)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_subscription(self, subscription_data: dict[str, Any]) -> Any:
        """Create new subscription."""
        if self.tenant_id:
            subscription_data['tenant_id'] = self.tenant_id

        subscription = self.subscription_model(**subscription_data)
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def update_subscription(self, subscription_id: UUID, data: dict[str, Any]) -> Any:
        """Update subscription."""
        query = (
            update(self.subscription_model)
            .where(self.subscription_model.id == subscription_id)
            .values(**data)
            .returning(self.subscription_model)
        )

        if self.tenant_id and hasattr(self.subscription_model, 'tenant_id'):
            query = query.where(self.subscription_model.tenant_id == self.tenant_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_due_subscriptions(self, as_of_date: date) -> list[Any]:
        """Get subscriptions due for billing."""
        query = (
            select(self.subscription_model)
            .options(
                selectinload(self.subscription_model.billing_plan),
                selectinload(self.subscription_model.customer),
            )
            .where(
                and_(
                    self.subscription_model.next_billing_date <= as_of_date,
                    self.subscription_model.status.in_(['active', 'trial']),
                )
            )
        )
        query = self._add_tenant_filter(query, self.subscription_model)
        result = await self.session.execute(query)
        return result.scalars().all()

    # Invoice operations
    async def get_invoice(self, invoice_id: UUID) -> Any:
        """Get invoice by ID with line items."""
        query = (
            select(self.invoice_model)
            .options(
                selectinload(self.invoice_model.line_items),
                selectinload(self.invoice_model.customer),
            )
            .where(self.invoice_model.id == invoice_id)
        )
        query = self._add_tenant_filter(query, self.invoice_model)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_invoice(self, invoice_data: dict[str, Any]) -> Any:
        """Create new invoice."""
        if self.tenant_id:
            invoice_data['tenant_id'] = self.tenant_id

        invoice = self.invoice_model(**invoice_data)
        self.session.add(invoice)
        await self.session.flush()
        return invoice

    async def update_invoice_status(self, invoice_id: UUID, status: InvoiceStatus) -> Any:
        """Update invoice status."""
        query = (
            update(self.invoice_model)
            .where(self.invoice_model.id == invoice_id)
            .values(status=status)
            .returning(self.invoice_model)
        )

        if self.tenant_id and hasattr(self.invoice_model, 'tenant_id'):
            query = query.where(self.invoice_model.tenant_id == self.tenant_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # Payment operations
    async def create_payment(self, payment_data: dict[str, Any]) -> Any:
        """Create new payment record."""
        if self.tenant_id:
            payment_data['tenant_id'] = self.tenant_id

        payment = self.payment_model(**payment_data)
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_payment_by_idempotency_key(self, key: str) -> Optional[Any]:
        """Find payment by idempotency key."""
        query = select(self.payment_model).where(
            self.payment_model.idempotency_key == key
        )
        query = self._add_tenant_filter(query, self.payment_model)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_payment_status(self, payment_id: UUID, status: PaymentStatus) -> Any:
        """Update payment status."""
        query = (
            update(self.payment_model)
            .where(self.payment_model.id == payment_id)
            .values(status=status)
            .returning(self.payment_model)
        )

        if self.tenant_id and hasattr(self.payment_model, 'tenant_id'):
            query = query.where(self.payment_model.tenant_id == self.tenant_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # Usage operations
    async def get_usage_records(
        self,
        subscription_id: UUID,
        start_date: date,
        end_date: date
    ) -> list[Any]:
        """Get usage records for billing period."""
        query = (
            select(self.usage_record_model)
            .where(
                and_(
                    self.usage_record_model.subscription_id == subscription_id,
                    self.usage_record_model.recorded_at >= start_date,
                    self.usage_record_model.recorded_at <= end_date,
                )
            )
            .order_by(self.usage_record_model.recorded_at)
        )
        query = self._add_tenant_filter(query, self.usage_record_model)
        result = await self.session.execute(query)
        return result.scalars().all()

    # Transaction support
    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

    async def flush(self) -> None:
        """Flush pending changes without committing."""
        await self.session.flush()


class UnitOfWork:
    """
    Unit of Work pattern implementation for managing transactions.

    Ensures that all repository operations within a business transaction
    are committed or rolled back together.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repositories = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    def get_billing_repository(
        self,
        customer_model: type,
        subscription_model: type,
        invoice_model: type,
        payment_model: type,
        usage_record_model: type,
        tenant_id: Optional[UUID] = None,
    ) -> SQLAlchemyBillingRepository:
        """Get or create billing repository instance."""
        key = 'billing_repository'
        if key not in self._repositories:
            self._repositories[key] = SQLAlchemyBillingRepository(
                session=self.session,
                customer_model=customer_model,
                subscription_model=subscription_model,
                invoice_model=invoice_model,
                payment_model=payment_model,
                usage_record_model=usage_record_model,
                tenant_id=tenant_id,
            )
        return self._repositories[key]

    async def commit(self) -> None:
        """Commit all changes in this unit of work."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback all changes in this unit of work."""
        await self.session.rollback()

    async def flush(self) -> None:
        """Flush changes without committing."""
        await self.session.flush()


# Repository factory for dependency injection
class RepositoryFactory:
    """Factory for creating repository instances with proper configuration."""

    def __init__(
        self,
        session_factory: callable,
        customer_model: type,
        subscription_model: type,
        invoice_model: type,
        payment_model: type,
        usage_record_model: type,
    ):
        self.session_factory = session_factory
        self.customer_model = customer_model
        self.subscription_model = subscription_model
        self.invoice_model = invoice_model
        self.payment_model = payment_model
        self.usage_record_model = usage_record_model

    async def create_billing_repository(
        self,
        tenant_id: Optional[UUID] = None
    ) -> SQLAlchemyBillingRepository:
        """Create a new billing repository instance."""
        session = await self.session_factory()

        return SQLAlchemyBillingRepository(
            session=session,
            customer_model=self.customer_model,
            subscription_model=self.subscription_model,
            invoice_model=self.invoice_model,
            payment_model=self.payment_model,
            usage_record_model=self.usage_record_model,
            tenant_id=tenant_id,
        )

    async def create_unit_of_work(self) -> UnitOfWork:
        """Create a new unit of work instance."""
        session = await self.session_factory()
        return UnitOfWork(session)
