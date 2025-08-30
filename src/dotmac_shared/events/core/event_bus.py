"""
Core Event Bus implementation.

Provides the main event bus interface with pluggable adapters for different backends.
Supports async/await patterns, error handling, and multi-tenant event routing.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

import structlog

from .models import (
    AdapterConfig,
    ConsumerConfig,
    ConsumerRecord,
    EventBusError,
    EventMetadata,
    EventRecord,
    PublishError,
    PublishResult,
    SubscriptionError,
    TopicConfig,
)

logger = structlog.get_logger(__name__)


class EventAdapter(ABC):
    """
    Abstract base class for event streaming adapters.

    All event adapters (Redis, Kafka, etc.) must implement this interface.
    """

    def __init__(self, config: AdapterConfig):
        """Initialize adapter with configuration."""
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the event streaming backend."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the event streaming backend."""
        pass

    @abstractmethod
    async def publish(
        self, event: EventRecord, topic: Optional[str] = None
    ) -> PublishResult:
        """Publish an event to a topic/stream."""
        pass

    @abstractmethod
    async def publish_batch(
        self, events: List[EventRecord], topic: Optional[str] = None
    ) -> List[PublishResult]:
        """Publish multiple events in a batch."""
        pass

    @abstractmethod
    async def subscribe(
        self,
        topics: List[str],
        consumer_config: ConsumerConfig,
        callback: Callable[[ConsumerRecord], None],
    ) -> None:
        """Subscribe to topics and process events with callback."""
        pass

    @abstractmethod
    async def consume(
        self, topics: List[str], consumer_config: ConsumerConfig
    ) -> AsyncIterator[ConsumerRecord]:
        """Consume events from topics as an async iterator."""
        pass

    @abstractmethod
    async def create_topic(self, topic_config: TopicConfig) -> bool:
        """Create a new topic/stream."""
        pass

    @abstractmethod
    async def delete_topic(self, topic_name: str) -> bool:
        """Delete a topic/stream."""
        pass

    @abstractmethod
    async def list_topics(self) -> List[str]:
        """List available topics/streams."""
        pass

    @abstractmethod
    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> bool:
        """Manually commit consumer offset."""
        pass

    @property
    def connected(self) -> bool:
        """Check if adapter is connected."""
        return self._connected

    @property
    def adapter_type(self) -> str:
        """Get adapter type name."""
        return self.__class__.__name__.replace("Adapter", "").lower()


class EventBus:
    """
    Main Event Bus implementation.

    Provides high-level event publishing and consumption with support for:
    - Multiple backend adapters (Redis, Kafka, Memory)
    - Async/await event processing
    - Error handling and retries
    - Multi-tenant event isolation
    - Dead letter queues
    - Event filtering and transformation
    """

    def __init__(
        self,
        adapter: EventAdapter,
        default_topic: str = "events",
        enable_dead_letter: bool = True,
        dead_letter_topic: str = "events-dlq",
    ):
        """
        Initialize event bus.

        Args:
            adapter: Event adapter implementation
            default_topic: Default topic for events
            enable_dead_letter: Enable dead letter queue
            dead_letter_topic: Topic for failed events
        """
        self.adapter = adapter
        self.default_topic = default_topic
        self.enable_dead_letter = enable_dead_letter
        self.dead_letter_topic = dead_letter_topic

        # State tracking
        self._subscribers: Dict[str, List[Callable]] = {}
        self._consumer_tasks: Set[asyncio.Task] = set()
        self._running = False

        logger.info(
            "Event bus initialized",
            adapter=adapter.adapter_type,
            default_topic=default_topic,
        )

    async def start(self) -> None:
        """Start the event bus and connect adapter."""
        try:
            if not self.adapter.connected:
                await self.adapter.connect()

            self._running = True
            logger.info("Event bus started successfully")

        except Exception as e:
            logger.error("Failed to start event bus", error=str(e))
            raise EventBusError(f"Failed to start event bus: {e}") from e

    async def stop(self) -> None:
        """Stop the event bus and disconnect adapter."""
        try:
            self._running = False

            # Cancel consumer tasks
            for task in self._consumer_tasks:
                task.cancel()

            if self._consumer_tasks:
                await asyncio.gather(*self._consumer_tasks, return_exceptions=True)

            self._consumer_tasks.clear()

            # Disconnect adapter
            if self.adapter.connected:
                await self.adapter.disconnect()

            logger.info("Event bus stopped successfully")

        except Exception as e:
            logger.error("Error stopping event bus", error=str(e))
            raise EventBusError(f"Failed to stop event bus: {e}") from e

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        *,
        metadata: Optional[EventMetadata] = None,
        topic: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish a single event.

        Args:
            event_type: Type of event (e.g., 'user.created', 'order.confirmed')
            data: Event payload data
            metadata: Optional event metadata (auto-generated if not provided)
            topic: Target topic (uses default if not provided)
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            PublishResult with event ID and broker details

        Raises:
            PublishError: If publishing fails
        """
        try:
            if not self._running:
                raise PublishError("Event bus is not running")

            # Create metadata if not provided
            if metadata is None:
                metadata = EventMetadata(tenant_id=tenant_id)
            elif tenant_id and not metadata.tenant_id:
                metadata.tenant_id = tenant_id

            # Create event record
            event = EventRecord(
                event_type=event_type,
                data=data,
                metadata=metadata,
                topic=topic or self.default_topic,
            )

            logger.debug(
                "Publishing event",
                event_id=event.event_id,
                event_type=event_type,
                topic=event.topic,
                tenant_id=tenant_id,
            )

            # Publish through adapter
            result = await self.adapter.publish(event, topic or self.default_topic)

            logger.info(
                "Event published successfully",
                event_id=event.event_id,
                event_type=event_type,
                topic=result.topic,
                partition=result.partition,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event_type,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise PublishError(f"Failed to publish event '{event_type}': {e}") from e

    async def publish_batch(
        self,
        events: List[Dict[str, Any]],
        *,
        topic: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[PublishResult]:
        """
        Publish multiple events in a batch.

        Args:
            events: List of event dictionaries with 'event_type' and 'data' keys
            topic: Target topic for all events
            tenant_id: Tenant ID for all events

        Returns:
            List of PublishResult objects

        Raises:
            PublishError: If batch publishing fails
        """
        try:
            if not self._running:
                raise PublishError("Event bus is not running")

            if not events:
                return []

            # Convert to EventRecord objects
            event_records = []
            for event_dict in events:
                metadata = EventMetadata(tenant_id=tenant_id)

                event_record = EventRecord(
                    event_type=event_dict["event_type"],
                    data=event_dict["data"],
                    metadata=metadata,
                    topic=topic or self.default_topic,
                )
                event_records.append(event_record)

            logger.debug(
                "Publishing event batch",
                batch_size=len(event_records),
                topic=topic or self.default_topic,
                tenant_id=tenant_id,
            )

            # Publish through adapter
            results = await self.adapter.publish_batch(
                event_records, topic or self.default_topic
            )

            logger.info(
                "Event batch published successfully",
                batch_size=len(results),
                topic=topic or self.default_topic,
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to publish event batch",
                batch_size=len(events) if events else 0,
                error=str(e),
            )
            raise PublishError(f"Failed to publish event batch: {e}") from e

    async def subscribe(
        self,
        event_types: Union[str, List[str]],
        callback: Callable[[ConsumerRecord], None],
        *,
        consumer_group: str = "default",
        topics: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        filter_func: Optional[Callable[[EventRecord], bool]] = None,
    ) -> None:
        """
        Subscribe to events with a callback function.

        Args:
            event_types: Event type(s) to subscribe to
            callback: Function to call for each event
            consumer_group: Consumer group name
            topics: Topics to consume from (uses default if not provided)
            tenant_id: Filter events by tenant ID
            filter_func: Additional filter function for events

        Raises:
            SubscriptionError: If subscription fails
        """
        try:
            if not self._running:
                raise SubscriptionError("Event bus is not running")

            # Normalize event types
            if isinstance(event_types, str):
                event_types = [event_types]

            # Setup consumer config
            consumer_config = ConsumerConfig(
                consumer_group=consumer_group, topics=topics or [self.default_topic]
            )

            # Create filtered callback
            async def filtered_callback(record: ConsumerRecord):
                try:
                    event = record.event

                    # Filter by event type
                    if event.event_type not in event_types:
                        return

                    # Filter by tenant
                    if tenant_id and event.tenant_id != tenant_id:
                        return

                    # Apply custom filter
                    if filter_func and not filter_func(event):
                        return

                    # Call user callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(record)
                    else:
                        callback(record)

                except Exception as e:
                    logger.error(
                        "Error in event callback",
                        event_type=record.event.event_type,
                        event_id=record.event.event_id,
                        error=str(e),
                    )

                    if self.enable_dead_letter:
                        await self._send_to_dead_letter(record.event, str(e))

            # Start subscription
            await self.adapter.subscribe(
                consumer_config.topics, consumer_config, filtered_callback
            )

            logger.info(
                "Subscription started",
                event_types=event_types,
                consumer_group=consumer_group,
                topics=consumer_config.topics,
            )

        except Exception as e:
            logger.error(
                "Failed to subscribe to events",
                event_types=event_types,
                consumer_group=consumer_group,
                error=str(e),
            )
            raise SubscriptionError(f"Failed to subscribe: {e}") from e

    async def consume(
        self,
        topics: Optional[List[str]] = None,
        *,
        consumer_group: str = "default",
        event_types: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> AsyncIterator[ConsumerRecord]:
        """
        Consume events as an async iterator.

        Args:
            topics: Topics to consume from
            consumer_group: Consumer group name
            event_types: Filter by event types
            tenant_id: Filter by tenant ID

        Yields:
            ConsumerRecord objects for matching events

        Raises:
            SubscriptionError: If consumption fails
        """
        try:
            if not self._running:
                raise SubscriptionError("Event bus is not running")

            consumer_config = ConsumerConfig(
                consumer_group=consumer_group, topics=topics or [self.default_topic]
            )

            async for record in self.adapter.consume(
                consumer_config.topics, consumer_config
            ):
                event = record.event

                # Apply filters
                if event_types and event.event_type not in event_types:
                    continue

                if tenant_id and event.tenant_id != tenant_id:
                    continue

                yield record

        except Exception as e:
            logger.error(
                "Error consuming events",
                topics=topics,
                consumer_group=consumer_group,
                error=str(e),
            )
            raise SubscriptionError(f"Error consuming events: {e}") from e

    async def create_topic(
        self, topic_name: str, *, partitions: int = 1, replication_factor: int = 1
    ) -> bool:
        """
        Create a new topic.

        Args:
            topic_name: Name of topic to create
            partitions: Number of partitions
            replication_factor: Replication factor

        Returns:
            True if created successfully
        """
        try:
            topic_config = TopicConfig(
                name=topic_name,
                partitions=partitions,
                replication_factor=replication_factor,
            )

            result = await self.adapter.create_topic(topic_config)

            if result:
                logger.info("Topic created successfully", topic=topic_name)

            return result

        except Exception as e:
            logger.error("Failed to create topic", topic=topic_name, error=str(e))
            return False

    async def _send_to_dead_letter(self, event: EventRecord, error: str) -> None:
        """Send failed event to dead letter queue."""
        try:
            if not self.enable_dead_letter:
                return

            # Add error info to metadata
            dlq_metadata = event.metadata.model_copy()
            dlq_metadata.headers["error"] = error
            dlq_metadata.headers["original_topic"] = event.topic or self.default_topic
            dlq_metadata.headers["failed_at"] = datetime.utcnow().isoformat()

            dlq_event = EventRecord(
                event_type=f"dlq.{event.event_type}",
                data=event.data,
                metadata=dlq_metadata,
                topic=self.dead_letter_topic,
            )

            await self.adapter.publish(dlq_event, self.dead_letter_topic)

            logger.warning(
                "Event sent to dead letter queue", event_id=event.event_id, error=error
            )

        except Exception as e:
            logger.error(
                "Failed to send event to dead letter queue",
                event_id=event.event_id,
                error=str(e),
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check event bus health status."""
        try:
            health = {
                "running": self._running,
                "adapter_connected": self.adapter.connected,
                "adapter_type": self.adapter.adapter_type,
                "active_subscriptions": len(self._consumer_tasks),
                "default_topic": self.default_topic,
                "dead_letter_enabled": self.enable_dead_letter,
            }

            # Try to list topics as connectivity check
            if self.adapter.connected:
                topics = await self.adapter.list_topics()
                health["available_topics"] = len(topics)
                health["healthy"] = True
            else:
                health["healthy"] = False

            return health

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"healthy": False, "error": str(e), "running": self._running}
