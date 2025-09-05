"""Events handling for services SDK."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EventType(Enum):
    """Event type enumeration."""

    SERVICE_CREATED = "service_created"
    SERVICE_UPDATED = "service_updated"
    SERVICE_DELETED = "service_deleted"
    SERVICE_PROVISIONED = "service_provisioned"
    SERVICE_ACTIVATED = "service_activated"
    SERVICE_DEACTIVATED = "service_deactivated"
    BILLING_EVENT = "billing_event"
    NOTIFICATION_SENT = "notification_sent"


class Event:
    """Event data structure."""

    def __init__(
        self,
        event_type: EventType,
        tenant_id: str,
        data: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize event."""
        self.event_type = event_type
        self.tenant_id = tenant_id
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
        self.event_id = (
            f"{event_type.value}_{tenant_id}_{int(self.timestamp.timestamp())}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """Event bus for handling service events."""

    def __init__(self):
        """Init   operation."""
        self._handlers: dict[EventType, list[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        if event.event_type in self._handlers:
            handlers = self._handlers[event.event_type]
            await asyncio.gather(*[handler(event) for handler in handlers])

    async def publish_service_created(
        self, tenant_id: str, service_id: str, service_data: dict[str, Any]
    ):
        """Publish service created event."""
        event = Event(
            EventType.SERVICE_CREATED,
            tenant_id,
            {"service_id": service_id, **service_data},
        )
        await self.publish(event)

    async def publish_service_provisioned(
        self, tenant_id: str, service_id: str, provisioning_data: dict[str, Any]
    ):
        """Publish service provisioned event."""
        event = Event(
            EventType.SERVICE_PROVISIONED,
            tenant_id,
            {"service_id": service_id, **provisioning_data},
        )
        await self.publish(event)


# Global event bus instance
event_bus = EventBus()


class EventHandler:
    """Base class for event handlers."""

    def __init__(self, event_bus: EventBus = None):
        """Init   operation."""
        self.event_bus = event_bus or globals()["event_bus"]

    async def handle_event(self, event: Event):
        """Handle an event - override in subclasses."""
        pass


class ServiceEventHandler(EventHandler):
    """Handler for service-related events."""

    async def handle_service_created(self, event: Event):
        """Handle service created event."""
        # Implementation would handle service creation side effects
        pass

    async def handle_service_provisioned(self, event: Event):
        """Handle service provisioned event."""
        # Implementation would handle provisioning completion
        pass


class BillingEventHandler(EventHandler):
    """Handler for billing-related events."""

    async def handle_billing_event(self, event: Event):
        """Handle billing event."""
        # Implementation would handle billing operations
        pass


class EventService:
    """Service for managing events and event handling."""

    def __init__(self, event_bus: EventBus = None):
        """Init   operation."""
        self.event_bus = event_bus or globals()["event_bus"]
        self.handlers = []

    async def publish_event(
        self,
        event_type: EventType,
        tenant_id: str,
        data: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Publish an event through the event bus."""
        event = Event(event_type, tenant_id, data, metadata)
        await self.event_bus.publish(event)

    def register_handler(self, handler: EventHandler):
        """Register an event handler."""
        self.handlers.append(handler)

    async def process_events(self, events: list[Event]):
        """Process a batch of events."""
        for event in events:
            await self.event_bus.publish(event)
