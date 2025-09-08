"""
Billing domain events.

Domain events represent important business occurrences that other parts
of the system may need to react to. Events flow outward from the domain core.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: UUID
    occurred_at: datetime
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class InvoiceGenerated:
    """Raised when a new invoice is generated."""

    event_id: UUID
    occurred_at: datetime
    invoice_id: UUID
    customer_id: UUID
    amount: Decimal
    currency: str
    due_date: datetime
    invoice_number: str
    subscription_id: UUID | None = None
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class PaymentProcessed:
    """Raised when a payment is successfully processed."""

    event_id: UUID
    occurred_at: datetime
    payment_id: UUID
    invoice_id: UUID
    customer_id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    transaction_id: str | None = None
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class PaymentFailed:
    """Raised when a payment fails to process."""

    event_id: UUID
    occurred_at: datetime
    payment_id: UUID
    invoice_id: UUID
    customer_id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    error_message: str
    error_code: str | None = None
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class SubscriptionCreated:
    """Raised when a new subscription is created."""

    event_id: UUID
    occurred_at: datetime
    subscription_id: UUID
    customer_id: UUID
    plan_id: UUID
    start_date: datetime
    billing_cycle: str
    trial_end_date: datetime | None = None
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class SubscriptionCancelled:
    """Raised when a subscription is cancelled."""

    event_id: UUID
    occurred_at: datetime
    subscription_id: UUID
    customer_id: UUID
    cancelled_at: datetime
    effective_date: datetime
    reason: str | None = None
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class SubscriptionRenewed:
    """Raised when a subscription is renewed."""

    event_id: UUID
    occurred_at: datetime
    subscription_id: UUID
    customer_id: UUID
    previous_period_end: datetime
    new_period_end: datetime
    amount: Decimal
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class UsageMeterUpdated:
    """Raised when usage meters are updated."""

    event_id: UUID
    occurred_at: datetime
    subscription_id: UUID
    customer_id: UUID
    meter_name: str
    usage_quantity: Decimal
    period_start: datetime
    period_end: datetime
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class CreditApplied:
    """Raised when a credit is applied to a customer account."""

    event_id: UUID
    occurred_at: datetime
    credit_id: UUID
    customer_id: UUID
    amount: Decimal
    reason: str
    applied_at: datetime
    invoice_id: UUID | None = None
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class RefundProcessed:
    """Raised when a refund is processed."""

    event_id: UUID
    occurred_at: datetime
    refund_id: UUID
    original_payment_id: UUID
    customer_id: UUID
    amount: Decimal
    currency: str
    processed_at: datetime
    reason: str | None = None
    tenant_id: UUID | None = None


class EventBus:
    """Simple event bus for domain events."""

    def __init__(self):
        self._handlers: dict[type, list[callable]] = {}

    def subscribe(self, event_type: type, handler: callable) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        """Publish an event to all registered handlers."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        for handler in handlers:
            try:
                if callable(handler):
                    if hasattr(handler, '__await__'):
                        await handler(event)
                    else:
                        handler(event)
            except Exception:
                # Log error but don't fail the original operation
                # In production, you'd want proper error handling/logging here
                pass


# Global event bus instance
event_bus = EventBus()


async def publish_event(event: DomainEvent) -> None:
    """Convenience function to publish an event."""
    await event_bus.publish(event)
