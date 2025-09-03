"""
Real-time Event System

Advanced event management for WebSocket connections with filtering,
transformation, persistence, and replay capabilities.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    """Event priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Common WebSocket event types."""

    # System events
    HEARTBEAT = "heartbeat"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_CLOSED = "connection_closed"

    # User events
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_STATUS_CHANGED = "user_status_changed"

    # Message events
    MESSAGE = "message"
    BROADCAST = "broadcast"
    ROOM_MESSAGE = "room_message"
    PRIVATE_MESSAGE = "private_message"

    # Business events
    NOTIFICATION = "notification"
    ALERT = "alert"
    STATUS_UPDATE = "status_update"
    DATA_CHANGED = "data_changed"

    # File events
    FILE_UPLOAD_PROGRESS = "file_upload_progress"
    FILE_GENERATION_COMPLETE = "file_generation_complete"
    FILE_READY = "file_ready"

    # Custom events
    CUSTOM = "custom"


@dataclass
class EventFilter:
    """Event filtering criteria."""

    event_types: Optional[Set[str]] = None
    tenant_ids: Optional[Set[str]] = None
    user_ids: Optional[Set[str]] = None
    rooms: Optional[Set[str]] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    priority_min: Optional[EventPriority] = None

    def matches(self, event: "WebSocketEvent") -> bool:
        """Check if event matches filter criteria."""
        if self.event_types and event.event_type not in self.event_types:
            return False

        if self.tenant_ids and event.tenant_id not in self.tenant_ids:
            return False

        if self.user_ids and event.user_id not in self.user_ids:
            return False

        if self.rooms and event.room not in self.rooms:
            return False

        if self.priority_min:
            priority_order = {
                EventPriority.LOW: 0,
                EventPriority.NORMAL: 1,
                EventPriority.HIGH: 2,
                EventPriority.CRITICAL: 3,
            }
            if priority_order.get(event.priority, 1) < priority_order.get(
                self.priority_min, 1
            ):
                return False

        if self.metadata_filters:
            for key, value in self.metadata_filters.items():
                if event.metadata.get(key) != value:
                    return False

        return True


class WebSocketEvent(BaseModel):
    """
    WebSocket event with comprehensive metadata and routing information.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = Field(..., description="Event type identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")

    # Routing information
    tenant_id: Optional[str] = Field(
        None, description="Tenant identifier for isolation"
    )
    user_id: Optional[str] = Field(None, description="User identifier")
    room: Optional[str] = Field(None, description="Room identifier")
    target_connections: Optional[List[str]] = Field(
        None, description="Specific connection targets"
    )

    # Event metadata
    priority: EventPriority = Field(EventPriority.NORMAL, description="Event priority")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event creation time"
    )
    expires_at: Optional[datetime] = Field(None, description="Event expiration time")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Delivery tracking
    delivery_attempts: int = Field(0, description="Number of delivery attempts")
    max_delivery_attempts: int = Field(3, description="Maximum delivery attempts")
    last_attempt: Optional[datetime] = Field(
        None, description="Last delivery attempt time"
    )

    # Event source
    source_service: Optional[str] = Field(None, description="Source service identifier")
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for event chains"
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("event_type must be a non-empty string")
        return v

    @field_validator("data")
    @classmethod
    def validate_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError("data must be a dictionary")
        return v

    @property
    def is_expired(self) -> bool:
        """Check if event has expired."""
        return self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at

    @property
    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return self.delivery_attempts < self.max_delivery_attempts

    def should_persist(self) -> bool:
        """Check if event should be persisted."""
        return (
            self.priority in [EventPriority.HIGH, EventPriority.CRITICAL]
            or self.expires_at is not None
        )

    def to_message(self) -> Dict[str, Any]:
        """Convert event to WebSocket message format."""
        return {
            "type": self.event_type,
            "id": self.event_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
        }


class EventSubscription(BaseModel):
    """Event subscription for connections."""

    connection_id: str
    event_filter: EventFilter
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )


class EventManager:
    """
    Enhanced event manager for WebSocket event handling with caching and replay.
    
    Provides centralized event publishing, subscription management, and event replay
    capabilities for WebSocket connections.
    """

    def __init__(self, websocket_manager, cache_service=None, config=None):
        """Initialize the event manager."""
        self.websocket_manager = websocket_manager
        self.cache_service = cache_service
        self.config = config or {}

        # Subscription management
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}

        # Event persistence (in-memory for now, can be extended to Redis/DB)
        self.event_history: Dict[str, List[WebSocketEvent]] = {}
        self.persistent_events: List[WebSocketEvent] = []

        # Performance metrics
        self.metrics = {
            "events_published": 0,
            "events_delivered": 0,
            "events_failed": 0,
            "subscriptions_active": 0,
            "replay_requests": 0,
        }

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        """Start the event manager and background tasks."""
        if self._is_running:
            return

        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_events())
        logger.info("Event manager started")

    async def stop(self):
        """Stop the event manager."""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Event manager stopped")

    async def subscribe(
        self,
        connection_id: str,
        event_types: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        rooms: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        priority_min: Optional[EventPriority] = None,
    ) -> bool:
        """
        Subscribe connection to events with filtering.

        Args:
            connection_id: WebSocket connection ID
            event_types: List of event types to subscribe to
            tenant_id: Filter by tenant ID
            user_id: Filter by user ID
            rooms: Filter by rooms
            metadata_filters: Filter by metadata
            priority_min: Minimum priority level

        Returns:
            True if subscription successful
        """
        # Verify connection exists
        if not self.websocket_manager.get_connection_info(connection_id):
            logger.warning(f"Cannot subscribe non-existent connection: {connection_id}")
            return False

        # Create event filter
        event_filter = EventFilter(
            event_types=set(event_types) if event_types else None,
            tenant_ids={tenant_id} if tenant_id else None,
            user_ids={user_id} if user_id else None,
            rooms=set(rooms) if rooms else None,
            metadata_filters=metadata_filters,
            priority_min=priority_min,
        )

        # Create subscription
        subscription = EventSubscription(
            connection_id=connection_id, event_filter=event_filter
        )

        # Add to subscriptions
        if connection_id not in self.subscriptions:
            self.subscriptions[connection_id] = []

        self.subscriptions[connection_id].append(subscription)
        self.metrics["subscriptions_active"] += 1

        logger.debug(f"Connection {connection_id} subscribed to events: {event_types}")
        return True

    async def unsubscribe(
        self, connection_id: str, event_types: Optional[List[str]] = None
    ) -> bool:
        """
        Unsubscribe connection from events.

        Args:
            connection_id: WebSocket connection ID
            event_types: Specific event types to unsubscribe from (None = all)

        Returns:
            True if unsubscription successful
        """
        if connection_id not in self.subscriptions:
            return False

        if event_types is None:
            # Unsubscribe from all events
            count = len(self.subscriptions[connection_id])
            del self.subscriptions[connection_id]
            self.metrics["subscriptions_active"] -= count
        else:
            # Unsubscribe from specific event types
            event_types_set = set(event_types)
            new_subscriptions = []
            removed_count = 0

            for subscription in self.subscriptions[connection_id]:
                if (
                    subscription.event_filter.event_types
                    and subscription.event_filter.event_types.intersection(
                        event_types_set
                    )
                ):
                    removed_count += 1
                else:
                    new_subscriptions.append(subscription)

            self.subscriptions[connection_id] = new_subscriptions
            self.metrics["subscriptions_active"] -= removed_count

            if not new_subscriptions:
                del self.subscriptions[connection_id]

        logger.debug(
            f"Connection {connection_id} unsubscribed from events: {event_types}"
        )
        return True

    async def publish_event(
        self, event: WebSocketEvent, target_connections: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish event to subscribed connections.

        Args:
            event: Event to publish
            target_connections: Specific connections to target (None = all subscribers)

        Returns:
            Dictionary with delivery results
        """
        self.metrics["events_published"] += 1

        # Persist event if needed
        if event.should_persist():
            await self._persist_event(event)

        # Find matching subscriptions
        matching_connections = await self._find_matching_connections(
            event, target_connections
        )

        if not matching_connections:
            logger.debug(f"No matching connections for event {event.event_id}")
            return {
                "event_id": event.event_id,
                "delivered": 0,
                "failed": 0,
                "connections": [],
            }

        # Deliver event to connections
        delivery_results = await self._deliver_event(event, matching_connections)

        # Update metrics
        self.metrics["events_delivered"] += delivery_results["delivered"]
        self.metrics["events_failed"] += delivery_results["failed"]

        # Call event handlers
        await self._call_event_handlers(event)

        return delivery_results

    async def replay_events(
        self,
        connection_id: str,
        since: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> int:
        """
        Replay events for reconnected client.

        Args:
            connection_id: WebSocket connection ID
            since: Replay events since this time
            event_types: Filter by event types
            limit: Maximum number of events to replay

        Returns:
            Number of events replayed
        """
        self.metrics["replay_requests"] += 1

        # Get connection info
        conn_info = self.websocket_manager.get_connection_info(connection_id)
        if not conn_info:
            return 0

        # Default since time
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=1)

        # Find events to replay
        events_to_replay = []
        for event in self.persistent_events:
            if event.timestamp < since:
                continue

            if event_types and event.event_type not in event_types:
                continue

            # Check if event matches connection's tenant/user
            if event.tenant_id and conn_info.tenant_id != event.tenant_id:
                continue

            events_to_replay.append(event)

            if len(events_to_replay) >= limit:
                break

        # Replay events
        replayed_count = 0
        for event in events_to_replay:
            success = await self.websocket_manager.send_message(
                connection_id,
                {
                    **event.to_message(),
                    "replayed": True,
                    "original_timestamp": event.timestamp.isoformat(),
                },
            )
            if success:
                replayed_count += 1

        logger.info(f"Replayed {replayed_count} events for connection {connection_id}")
        return replayed_count

    async def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler function."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)
        logger.debug(f"Added event handler for {event_type}")

    async def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove event handler function."""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                if not self.event_handlers[event_type]:
                    del self.event_handlers[event_type]
                logger.debug(f"Removed event handler for {event_type}")
            except ValueError:
                pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get event manager metrics."""
        return {
            **self.metrics,
            "persistent_events_count": len(self.persistent_events),
            "connections_with_subscriptions": len(self.subscriptions),
        }

    # Private methods
    async def _find_matching_connections(
        self, event: WebSocketEvent, target_connections: Optional[Set[str]]
    ) -> Set[str]:
        """Find connections that should receive the event."""
        matching_connections = set()

        # If specific targets provided, use those
        if target_connections:
            for connection_id in target_connections:
                if connection_id in self.subscriptions:
                    for subscription in self.subscriptions[connection_id]:
                        if subscription.event_filter.matches(event):
                            matching_connections.add(connection_id)
                            break
        else:
            # Check all subscriptions
            for connection_id, subscriptions in self.subscriptions.items():
                for subscription in subscriptions:
                    if subscription.event_filter.matches(event):
                        matching_connections.add(connection_id)
                        break

        return matching_connections

    async def _deliver_event(
        self, event: WebSocketEvent, connections: Set[str]
    ) -> Dict[str, Any]:
        """Deliver event to connections."""
        message = event.to_message()
        delivery_tasks = []

        # Create delivery tasks
        for connection_id in connections:
            task = self.websocket_manager.send_message(connection_id, message)
            delivery_tasks.append((connection_id, task))

        # Execute deliveries concurrently
        delivered = 0
        failed = 0
        connection_results = []

        if delivery_tasks:
            results = await asyncio.gather(
                *[task for _, task in delivery_tasks], return_exceptions=True
            )

            for (connection_id, _), result in zip(delivery_tasks, results):
                if result is True:
                    delivered += 1
                    connection_results.append(
                        {"connection_id": connection_id, "status": "delivered"}
                    )
                else:
                    failed += 1
                    connection_results.append(
                        {"connection_id": connection_id, "status": "failed"}
                    )

        return {
            "event_id": event.event_id,
            "delivered": delivered,
            "failed": failed,
            "connections": connection_results,
        }

    async def _persist_event(self, event: WebSocketEvent):
        """Persist event for replay."""
        self.persistent_events.append(event)

        # Limit persistent events to prevent memory bloat
        max_persistent_events = self.config.get("max_persistent_events", 10000)
        if len(self.persistent_events) > max_persistent_events:
            self.persistent_events = self.persistent_events[-max_persistent_events:]

        # Also store in cache service if available
        if self.cache_service:
            try:
                cache_key = f"websocket:event:{event.event_id}"
                await self.cache_service.set(
                    cache_key,
                    event.model_dump(),
                    ttl=3600,  # 1 hour TTL
                    tenant_id=event.tenant_id,
                )
            except Exception as e:
                logger.warning(f"Failed to cache event {event.event_id}: {e}")

    async def _call_event_handlers(self, event: WebSocketEvent):
        """Call registered event handlers."""
        handlers = self.event_handlers.get(event.event_type, [])
        if not handlers:
            return

        # Call handlers concurrently
        handler_tasks = []
        for handler in handlers:
            try:
                task = handler(event)
                if asyncio.iscoroutine(task):
                    handler_tasks.append(task)
            except Exception as e:
                logger.error(f"Error calling event handler: {e}")

        if handler_tasks:
            await asyncio.gather(*handler_tasks, return_exceptions=True)

    async def _cleanup_expired_events(self):
        """Background task to clean up expired events."""
        while self._is_running:
            try:
                now = datetime.now(timezone.utc)

                # Remove expired events
                before_count = len(self.persistent_events)
                self.persistent_events = [
                    event for event in self.persistent_events if not event.is_expired
                ]
                after_count = len(self.persistent_events)

                if before_count != after_count:
                    logger.debug(
                        f"Cleaned up {before_count - after_count} expired events"
                    )

                # Remove inactive subscriptions
                inactive_connections = []
                for connection_id in list(self.subscriptions.keys()):
                    if not self.websocket_manager.get_connection_info(connection_id):
                        inactive_connections.append(connection_id)

                for connection_id in inactive_connections:
                    await self.unsubscribe(connection_id)

                await asyncio.sleep(300)  # Clean up every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event cleanup error: {e}")
                await asyncio.sleep(60)  # Error backoff
