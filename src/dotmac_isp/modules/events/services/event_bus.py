"""
Event Bus Service - DRY Migration
Provides centralized event publishing, subscription management, and event routing.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotmac.application import standard_exception_handler
from dotmac_shared.services.base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EventSubscription:
    """Represents an event subscription."""

    def __init__(self, event_type: str, handler: Callable, subscriber_id: str):
        self.event_type = event_type
        self.handler = handler
        self.subscriber_id = subscriber_id
        self.created_at = datetime.now(timezone.utc)
        self.active = True


class EventMessage:
    """Represents an event message."""

    def __init__(
        self,
        event_type: str,
        data: dict[str, Any],
        source: str,
        tenant_id: str,
        correlation_id: str | None = None,
    ):
        self.id = str(uuid4())
        self.event_type = event_type
        self.data = data
        self.source = source
        self.tenant_id = tenant_id
        self.correlation_id = correlation_id or str(uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.processed = False


class EventBusService(BaseService):
    """Centralized event bus for reactive network operations."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        super().__init__(
            db=db,
            tenant_id=tenant_id,
            create_schema=dict,
            update_schema=dict,
            response_schema=dict,
        )

        # Event handlers registry
        self._event_handlers: dict[str, list[EventSubscription]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_active = False
        self._processing_task: asyncio.Task | None = None

    @standard_exception_handler
    async def publish_event(
        self,
        event_type: str,
        data: dict[str, Any],
        source: str = "system",
        correlation_id: str | None = None,
    ) -> str:
        """Publish an event to the event bus."""
        event = EventMessage(
            event_type=event_type,
            data=data,
            source=source,
            tenant_id=self.tenant_id,
            correlation_id=correlation_id,
        )

        logger.info(
            f"Publishing event {event.id}: {event_type} from {source}",
            extra={"tenant_id": self.tenant_id, "correlation_id": correlation_id},
        )

        # Add to processing queue
        await self._event_queue.put(event)

        # Start processing if not active
        if not self._processing_active:
            await self._start_processing()

        return event.id

    @standard_exception_handler
    async def subscribe(
        self,
        event_type: str,
        handler: Callable[[EventMessage], Any],
        subscriber_id: str,
    ) -> str:
        """Subscribe to events of a specific type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        subscription = EventSubscription(event_type, handler, subscriber_id)
        self._event_handlers[event_type].append(subscription)

        logger.info(
            f"Registered handler for event type '{event_type}' from subscriber '{subscriber_id}'",
            extra={"tenant_id": self.tenant_id},
        )

        return subscription.subscriber_id

    @standard_exception_handler
    async def unsubscribe(self, event_type: str, subscriber_id: str) -> bool:
        """Unsubscribe from events."""
        if event_type not in self._event_handlers:
            return False

        initial_count = len(self._event_handlers[event_type])
        self._event_handlers[event_type] = [
            sub for sub in self._event_handlers[event_type] if sub.subscriber_id != subscriber_id
        ]

        removed = initial_count > len(self._event_handlers[event_type])

        if removed:
            logger.info(
                f"Unsubscribed '{subscriber_id}' from event type '{event_type}'",
                extra={"tenant_id": self.tenant_id},
            )

        return removed

    @standard_exception_handler
    async def get_event_types(self) -> list[str]:
        """Get all registered event types."""
        return list(self._event_handlers.keys())

    @standard_exception_handler
    async def get_subscribers(self, event_type: str) -> list[dict[str, Any]]:
        """Get all subscribers for a specific event type."""
        if event_type not in self._event_handlers:
            return []

        return [
            {
                "subscriber_id": sub.subscriber_id,
                "event_type": sub.event_type,
                "created_at": sub.created_at.isoformat(),
                "active": sub.active,
            }
            for sub in self._event_handlers[event_type]
        ]

    async def _start_processing(self) -> None:
        """Start event processing task."""
        if self._processing_active:
            return

        self._processing_active = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Event processing started", extra={"tenant_id": self.tenant_id})

    async def _stop_processing(self) -> None:
        """Stop event processing task."""
        self._processing_active = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Event processing stopped", extra={"tenant_id": self.tenant_id})

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._processing_active:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                self._event_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(
                    f"Error processing event: {e}",
                    extra={"tenant_id": self.tenant_id},
                    exc_info=True,
                )

    async def _handle_event(self, event: EventMessage) -> None:
        """Handle a specific event by calling all registered handlers."""
        handlers = self._event_handlers.get(event.event_type, [])

        if not handlers:
            logger.debug(
                f"No handlers for event type '{event.event_type}'",
                extra={"tenant_id": self.tenant_id, "event_id": event.id},
            )
            return

        logger.debug(
            f"Processing event {event.id} with {len(handlers)} handlers",
            extra={"tenant_id": self.tenant_id, "event_type": event.event_type},
        )

        # Execute all handlers
        tasks = []
        for subscription in handlers:
            if subscription.active:
                tasks.append(self._execute_handler(subscription, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        event.processed = True

    async def _execute_handler(
        self,
        subscription: EventSubscription,
        event: EventMessage,
    ) -> None:
        """Execute a single event handler."""
        try:
            if asyncio.iscoroutinefunction(subscription.handler):
                await subscription.handler(event)
            else:
                subscription.handler(event)

        except Exception as e:
            logger.error(
                f"Handler '{subscription.subscriber_id}' failed for event '{event.id}': {e}",
                extra={
                    "tenant_id": self.tenant_id,
                    "event_type": event.event_type,
                    "subscriber_id": subscription.subscriber_id,
                },
                exc_info=True,
            )

    @standard_exception_handler
    async def get_queue_size(self) -> int:
        """Get current event queue size."""
        return self._event_queue.qsize()

    @standard_exception_handler
    async def flush_queue(self) -> int:
        """Flush all pending events and return count."""
        count = 0
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
                self._event_queue.task_done()
                count += 1
            except asyncio.QueueEmpty:
                break

        logger.info(f"Flushed {count} events from queue", extra={"tenant_id": self.tenant_id})
        return count

    @standard_exception_handler
    async def health_check(self) -> dict[str, Any]:
        """Check event bus health status."""
        return {
            "status": "healthy" if self._processing_active else "stopped",
            "queue_size": await self.get_queue_size(),
            "registered_event_types": len(self._event_handlers),
            "total_subscribers": sum(len(subs) for subs in self._event_handlers.values()),
            "processing_active": self._processing_active,
        }

    async def cleanup(self) -> None:
        """Cleanup event bus resources."""
        await self._stop_processing()
        await self.flush_queue()
        self._event_handlers.clear()
        logger.info("Event bus cleanup completed", extra={"tenant_id": self.tenant_id})


__all__ = ["EventBusService", "EventMessage", "EventSubscription"]
