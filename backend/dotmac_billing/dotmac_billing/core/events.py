"""
Event system for platform integration and webhook support.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Billing event types."""

    # Account events
    ACCOUNT_CREATED = "billing.account.created"
    ACCOUNT_UPDATED = "billing.account.updated"
    ACCOUNT_SUSPENDED = "billing.account.suspended"
    ACCOUNT_REACTIVATED = "billing.account.reactivated"

    # Invoice events
    INVOICE_CREATED = "billing.invoice.created"
    INVOICE_FINALIZED = "billing.invoice.finalized"
    INVOICE_SENT = "billing.invoice.sent"
    INVOICE_PAID = "billing.invoice.paid"
    INVOICE_OVERDUE = "billing.invoice.overdue"
    INVOICE_CANCELED = "billing.invoice.canceled"

    # Payment events
    PAYMENT_PROCESSING = "billing.payment.processing"
    PAYMENT_SUCCEEDED = "billing.payment.succeeded"
    PAYMENT_FAILED = "billing.payment.failed"
    PAYMENT_REFUNDED = "billing.payment.refunded"

    # Dunning events
    DUNNING_STARTED = "billing.dunning.started"
    DUNNING_ESCALATED = "billing.dunning.escalated"
    DUNNING_RESOLVED = "billing.dunning.resolved"

    # Cycle events
    CYCLE_STARTED = "billing.cycle.started"
    CYCLE_COMPLETED = "billing.cycle.completed"


@dataclass
class BillingEvent:
    """Billing event data structure."""

    event_type: EventType
    tenant_id: str
    timestamp: datetime
    data: Dict[str, Any]
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "idempotency_key": self.idempotency_key
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BillingEvent":
        """Create event from dictionary."""
        return cls(
            event_id=data.get("event_id"),
            event_type=EventType(data["event_type"]),
            tenant_id=data["tenant_id"],
            user_id=data.get("user_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data["data"],
            idempotency_key=data.get("idempotency_key")
        )


class EventPublisher(ABC):
    """Abstract base class for event publishers."""

    @abstractmethod
    async def publish(self, event: BillingEvent) -> bool:
        """Publish an event."""
        pass

    @abstractmethod
    async def publish_batch(self, events: List[BillingEvent]) -> bool:
        """Publish multiple events."""
        pass


class WebhookPublisher(EventPublisher):
    """Webhook-based event publisher for platform integration."""

    def __init__(self, webhook_url: str, secret_key: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret_key = secret_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def publish(self, event: BillingEvent) -> bool:
        """Publish event via webhook."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Event-Type": event.event_type.value,
                "X-Tenant-ID": event.tenant_id
            }

            if self.secret_key:
                import hashlib
                import hmac

                payload = json.dumps(event.to_dict())
                signature = hmac.new(
                    self.secret_key.encode(),
                    payload.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Signature"] = f"sha256={signature}"

            response = await self.client.post(
                self.webhook_url,
                json=event.to_dict(),
                headers=headers
            )

            response.raise_for_status()
            logger.info(f"Event published successfully: {event.event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type.value}: {e}")
            return False

    async def publish_batch(self, events: List[BillingEvent]) -> bool:
        """Publish multiple events in batch."""
        try:
            payload = {
                "events": [event.to_dict() for event in events],
                "batch_size": len(events)
            }

            headers = {
                "Content-Type": "application/json",
                "X-Event-Type": "billing.batch",
                "X-Batch-Size": str(len(events))
            }

            response = await self.client.post(
                f"{self.webhook_url}/batch",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            logger.info(f"Batch of {len(events)} events published successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event batch: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class InMemoryPublisher(EventPublisher):
    """In-memory event publisher for testing and development."""

    def __init__(self):
        self.events: List[BillingEvent] = []
        self.handlers: Dict[EventType, List[Callable]] = {}

    async def publish(self, event: BillingEvent) -> bool:
        """Publish event to memory store."""
        self.events.append(event)

        # Call registered handlers
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")

        return True

    async def publish_batch(self, events: List[BillingEvent]) -> bool:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)
        return True

    def register_handler(self, event_type: EventType, handler: Callable):
        """Register event handler."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def get_events(self, event_type: Optional[EventType] = None, tenant_id: Optional[str] = None) -> List[BillingEvent]:
        """Get events from memory store."""
        events = self.events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        return events

    def clear(self):
        """Clear all events."""
        self.events.clear()


class EventManager:
    """Central event management for the billing system."""

    def __init__(self, publisher: Optional[EventPublisher] = None):
        self.publisher = publisher or InMemoryPublisher()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False

    async def emit(self, event_type: EventType, tenant_id: str, data: Dict[str, Any],
                   user_id: Optional[str] = None, idempotency_key: Optional[str] = None) -> BillingEvent:
        """Emit a billing event."""
        event = BillingEvent(
            event_type=event_type,
            tenant_id=tenant_id,
            timestamp=datetime.now(timezone.utc),
            data=data,
            user_id=user_id,
            idempotency_key=idempotency_key,
            event_id=f"{event_type.value}_{tenant_id}_{datetime.now(timezone.utc).timestamp()}"
        )

        await self._event_queue.put(event)

        if not self._processing:
            asyncio.create_task(self._process_events())

        return event

    async def _process_events(self):
        """Process events from the queue."""
        self._processing = True

        try:
            while True:
                try:
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self.publisher.publish(event)
                    self._event_queue.task_done()
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
        finally:
            self._processing = False

    async def emit_account_created(self, tenant_id: str, account_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit account created event."""
        return await self.emit(EventType.ACCOUNT_CREATED, tenant_id, account_data, user_id)

    async def emit_invoice_created(self, tenant_id: str, invoice_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit invoice created event."""
        return await self.emit(EventType.INVOICE_CREATED, tenant_id, invoice_data, user_id)

    async def emit_payment_succeeded(self, tenant_id: str, payment_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit payment succeeded event."""
        return await self.emit(EventType.PAYMENT_SUCCEEDED, tenant_id, payment_data, user_id)

    async def emit_payment_failed(self, tenant_id: str, payment_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit payment failed event."""
        return await self.emit(EventType.PAYMENT_FAILED, tenant_id, payment_data, user_id)

    async def emit_dunning_escalated(self, tenant_id: str, dunning_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit dunning escalated event."""
        return await self.emit(EventType.DUNNING_ESCALATED, tenant_id, dunning_data, user_id)

    async def close(self):
        """Close event manager and publisher."""
        await self._event_queue.join()
        if hasattr(self.publisher, 'close'):
            await self.publisher.close()


# Global event manager instance
_event_manager: Optional[EventManager] = None


def get_event_manager() -> EventManager:
    """Get global event manager instance."""
    global _event_manager
    if _event_manager is None:
        from .config import get_config
        config = get_config()

        # Initialize publisher based on configuration
        if hasattr(config, 'platform_webhook_url') and config.platform_webhook_url:
            publisher = WebhookPublisher(
                webhook_url=config.platform_webhook_url,
                secret_key=getattr(config, 'platform_webhook_secret', None)
            )
        else:
            publisher = InMemoryPublisher()

        _event_manager = EventManager(publisher)

    return _event_manager


def set_event_manager(manager: EventManager):
    """Set global event manager instance."""
    global _event_manager
    _event_manager = manager
