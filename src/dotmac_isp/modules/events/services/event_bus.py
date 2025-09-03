"""
Event Bus Service.

Provides centralized event publishing, subscription management,
and event routing for reactive network operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from sqlalchemy.orm import Session

from dotmac_isp.shared.base_service import BaseTenantService
from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = logging.getLogger(__name__)


class EventBusService(BaseTenantService):
    """Centralized event bus for reactive network operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=None,
            create_schema=None,
            update_schema=None,
            response_schema=None,
            tenant_id=tenant_id
        )
        
        # In-memory event handlers registry
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._async_handlers: Dict[str, List[Callable]] = {}
        self._event_subscriptions: Dict[str, Set[str]] = {}
        
        # Event processing queue
        self._event_queue = asyncio.Queue()
        self._processing_active = False

    @standard_exception_handler
    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: int = 5  # 1 = highest, 10 = lowest
    ) -> str:
        """Publish event to the event bus."""
        event_id = str(uuid4())
        
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "tenant_id": self.tenant_id,
            "data": data,
            "source": source or "unknown",
            "correlation_id": correlation_id,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "published_at": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Publishing event {event_type} with ID {event_id}")

        # Add to processing queue
        await self._event_queue.put(event)
        
        # Start event processing if not already running
        if not self._processing_active:
            asyncio.create_task(self._process_event_queue())

        return event_id

    @standard_exception_handler
    async def subscribe(
        self,
        event_type: str,
        handler: Callable,
        handler_id: Optional[str] = None,
        is_async: bool = True
    ) -> str:
        """Subscribe handler to event type."""
        subscription_id = handler_id or str(uuid4())
        
        if is_async:
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)
        else:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(handler)
        
        # Track subscription
        if event_type not in self._event_subscriptions:
            self._event_subscriptions[event_type] = set()
        self._event_subscriptions[event_type].add(subscription_id)

        logger.info(f"Subscribed handler {subscription_id} to event type {event_type}")
        
        return subscription_id

    @standard_exception_handler
    async def unsubscribe(self, event_type: str, subscription_id: str) -> bool:
        """Unsubscribe handler from event type."""
        if event_type in self._event_subscriptions:
            self._event_subscriptions[event_type].discard(subscription_id)
            logger.info(f"Unsubscribed handler {subscription_id} from event type {event_type}")
            return True
        return False

    @standard_exception_handler
    async def publish_device_health_event(
        self,
        device_id: str,
        health_status: str,
        health_score: float,
        metrics: Dict[str, Any]
    ) -> str:
        """Publish device health change event."""
        return await self.publish_event(
            event_type="device.health.changed",
            data={
                "device_id": device_id,
                "health_status": health_status,
                "health_score": health_score,
                "metrics": metrics,
                "previous_status": metrics.get("previous_health_status")
            },
            source="monitoring_service"
        )

    @standard_exception_handler
    async def publish_alarm_event(
        self,
        alarm_id: str,
        alarm_type: str,
        action: str,  # created, acknowledged, cleared, escalated
        alarm_data: Dict[str, Any]
    ) -> str:
        """Publish alarm management event."""
        return await self.publish_event(
            event_type=f"alarm.{action}",
            data={
                "alarm_id": alarm_id,
                "alarm_type": alarm_type,
                "action": action,
                "alarm_data": alarm_data
            },
            source="alarm_service",
            priority=2 if alarm_data.get("severity") == "critical" else 5
        )

    @standard_exception_handler
    async def publish_service_event(
        self,
        service_id: str,
        customer_id: str,
        event_type: str,  # provisioned, activated, modified, suspended, cancelled
        service_data: Dict[str, Any]
    ) -> str:
        """Publish service lifecycle event."""
        return await self.publish_event(
            event_type=f"service.{event_type}",
            data={
                "service_id": service_id,
                "customer_id": customer_id,
                "service_data": service_data
            },
            source="services_service"
        )

    @standard_exception_handler
    async def publish_workflow_event(
        self,
        workflow_id: str,
        workflow_type: str,
        status: str,  # started, step_completed, step_failed, completed, failed
        workflow_data: Dict[str, Any]
    ) -> str:
        """Publish workflow execution event."""
        return await self.publish_event(
            event_type=f"workflow.{status}",
            data={
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "status": status,
                "workflow_data": workflow_data
            },
            source="orchestration_service"
        )

    @standard_exception_handler
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        stats = {
            "registered_event_types": list(self._event_subscriptions.keys()),
            "total_subscriptions": sum(len(subs) for subs in self._event_subscriptions.values()),
            "async_handlers_count": sum(len(handlers) for handlers in self._async_handlers.values()),
            "sync_handlers_count": sum(len(handlers) for handlers in self._event_handlers.values()),
            "queue_size": self._event_queue.qsize(),
            "processing_active": self._processing_active,
            "subscription_details": {
                event_type: len(subs) 
                for event_type, subs in self._event_subscriptions.items()
            }
        }
        return stats

    # Private methods for event processing

    async def _process_event_queue(self) -> None:
        """Process events from the queue."""
        self._processing_active = True
        logger.info("Started event queue processing")
        
        try:
            while True:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self._dispatch_event(event)
                    self._event_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Check if queue is empty and stop processing
                    if self._event_queue.empty():
                        break
                    continue
                    
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")
                    continue
                    
        finally:
            self._processing_active = False
            logger.info("Stopped event queue processing")

    async def _dispatch_event(self, event: Dict[str, Any]) -> None:
        """Dispatch event to registered handlers."""
        event_type = event["event_type"]
        
        logger.debug(f"Dispatching event {event_type} (ID: {event['event_id']})")
        
        # Collect all handlers for this event type
        handlers_to_call = []
        
        # Add direct event type handlers
        if event_type in self._async_handlers:
            handlers_to_call.extend(self._async_handlers[event_type])
            
        if event_type in self._event_handlers:
            handlers_to_call.extend(self._event_handlers[event_type])
        
        # Add wildcard handlers (e.g., handlers subscribed to "device.*")
        for registered_type, handlers in self._async_handlers.items():
            if self._matches_pattern(event_type, registered_type):
                handlers_to_call.extend(handlers)
        
        for registered_type, handlers in self._event_handlers.items():
            if self._matches_pattern(event_type, registered_type):
                handlers_to_call.extend(handlers)

        if not handlers_to_call:
            logger.debug(f"No handlers registered for event type {event_type}")
            return

        # Execute handlers
        handler_tasks = []
        for handler in handlers_to_call:
            try:
                if asyncio.iscoroutinefunction(handler):
                    task = asyncio.create_task(handler(event))
                    handler_tasks.append(task)
                else:
                    # Execute sync handler in thread pool
                    handler(event)
            except Exception as e:
                logger.error(f"Error executing event handler: {str(e)}")

        # Wait for async handlers to complete
        if handler_tasks:
            try:
                await asyncio.gather(*handler_tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error in async handler execution: {str(e)}")

        logger.debug(f"Dispatched event {event_type} to {len(handlers_to_call)} handlers")

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches subscription pattern."""
        if pattern == "*":
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return event_type.startswith(prefix)
            
        return event_type == pattern


# Global event bus instance (singleton pattern)
_event_bus_instance = None

def get_event_bus(db: Session, tenant_id: str) -> EventBusService:
    """Get global event bus instance."""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBusService(db, tenant_id)
    return _event_bus_instance