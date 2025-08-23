"""
Event Bus SDK for dotmac_core_events.

Provides high-level event streaming operations with:
- Multi-tenant event publishing and subscription
- Idempotency support
- Consumer groups and partition management
- Dead letter queue integration
- Adapter interface for Redis Streams and Kafka
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Set

import structlog

logger = structlog.get_logger(__name__)


class EventBusError(Exception):
    """Base exception for Event Bus operations."""

    pass


class PublishError(EventBusError):
    """Exception raised when event publishing fails."""

    pass


class SubscriptionError(EventBusError):
    """Exception raised when subscription operations fail."""

    pass


@dataclass
class EventMetadata:
    """Event metadata for tracing and correlation."""

    source: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            k: v
            for k, v in {
                "source": self.source,
                "correlation_id": self.correlation_id,
                "causation_id": self.causation_id,
                "user_id": self.user_id,
                "trace_id": self.trace_id,
                "span_id": self.span_id,
            }.items()
            if v is not None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventMetadata":
        """Create from dictionary."""
        return cls(
            source=data.get("source"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            user_id=data.get("user_id"),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
        )


@dataclass
class PublishResult:
    """Result of event publishing operation."""

    event_id: str
    partition: int
    offset: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "partition": self.partition,
            "offset": self.offset,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Event:
    """Event data structure."""

    event_id: str
    event_type: str
    data: Dict[str, Any]
    event_metadata: EventMetadata
    timestamp: datetime
    partition: int
    offset: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "metadata": self.event_metadata.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "partition": self.partition,
            "offset": self.offset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            data=data["data"],
            metadata=EventMetadata.from_dict(data.get("metadata", {})),
            timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
            partition=data["partition"],
            offset=data["offset"],
        )


class EventBusAdapter(ABC):
    """Abstract adapter interface for event bus implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the adapter."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the adapter and cleanup resources."""
        pass

    @abstractmethod
    async def publish(
        self,
        topic: str,
        event_id: str,
        event_type: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,
        event_metadata: Optional[EventMetadata] = None,
    ) -> PublishResult:
        """Publish an event to the specified topic."""
        pass

    @abstractmethod
    async def subscribe(
        self,
        topics: List[str],
        consumer_group: str,
        auto_commit: bool = True,
        max_poll_records: int = 100,
    ) -> AsyncIterator[Event]:
        """Subscribe to events from specified topics."""
        pass

    @abstractmethod
    async def unsubscribe(self, consumer_group: str) -> None:
        """Unsubscribe from all topics for the consumer group."""
        pass

    @abstractmethod
    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """Get information about a topic."""
        pass

    @abstractmethod
    async def list_topics(self) -> List[str]:
        """List all available topics."""
        pass

    @abstractmethod
    async def create_topic(
        self, topic: str, partitions: int = 3, replication_factor: int = 2, **kwargs
    ) -> None:
        """Create a new topic."""
        pass

    @abstractmethod
    async def delete_topic(self, topic: str) -> None:
        """Delete a topic."""
        pass


class EventBusSDK:
    """
    High-level Event Bus SDK with tenant isolation and multi-adapter support.

    Provides:
    - Multi-tenant event publishing and subscription
    - Idempotency support with configurable keys
    - Consumer groups and partition management
    - Dead letter queue integration
    - Metrics and observability
    """

    def __init__(
        self,
        tenant_id: str,
        adapter: EventBusAdapter,
        topic_prefix: Optional[str] = None,
        enable_dlq: bool = True,
        dlq_handler: Optional[Any] = None,
    ):
        """
        Initialize the Event Bus SDK.

        Args:
            tenant_id: Tenant identifier for isolation
            adapter: Event bus adapter implementation
            topic_prefix: Optional prefix for all topics
            enable_dlq: Whether to enable dead letter queue
            dlq_handler: Optional DLQ handler instance
        """
        self.tenant_id = tenant_id
        self.adapter = adapter
        self.topic_prefix = topic_prefix or f"tenant-{tenant_id}"
        self.enable_dlq = enable_dlq
        self.dlq_handler = dlq_handler

        # Internal state
        self._initialized = False
        self._subscriptions: Set[str] = set()
        self._idempotency_cache: Dict[str, PublishResult] = {}

        # Metrics
        self._publish_count = 0
        self._consume_count = 0
        self._error_count = 0

    async def initialize(self) -> None:
        """Initialize the SDK and adapter."""
        if self._initialized:
            return

        await self.adapter.initialize()
        self._initialized = True

        logger.info(
            "EventBusSDK initialized",
            tenant_id=self.tenant_id,
            topic_prefix=self.topic_prefix,
        )

    async def close(self) -> None:
        """Close the SDK and cleanup resources."""
        if not self._initialized:
            return

        # Unsubscribe from all active subscriptions
        for subscription in list(self._subscriptions):
            try:
                await self.adapter.unsubscribe(subscription)
            except Exception as e:
                logger.warning(
                    "Failed to unsubscribe",
                    subscription=subscription,
                    error=str(e),
                )

        await self.adapter.close()
        self._initialized = False

        logger.info("EventBusSDK closed", tenant_id=self.tenant_id)

    def _event_type_to_topic(self, event_type: str) -> str:
        """Convert event type to topic name with tenant prefix."""
        return f"{self.topic_prefix}.{event_type}"

    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return str(uuid.uuid4())

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,
        event_metadata: Optional[EventMetadata] = None,
        idempotency_key: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish an event to the event stream.

        Args:
            event_type: Type of event to publish
            data: Event payload data
            partition_key: Optional key for partition routing
            event_metadata: Optional event metadata
            idempotency_key: Optional key for idempotency

        Returns:
            PublishResult with event details

        Raises:
            PublishError: If publishing fails
        """
        if not self._initialized:
            await self.initialize()

        # Check idempotency
        if idempotency_key and idempotency_key in self._idempotency_cache:
            logger.info(
                "Event already published (idempotent)",
                event_type=event_type,
                idempotency_key=idempotency_key,
            )
            return self._idempotency_cache[idempotency_key]

        try:
            # Generate event ID and prepare metadata
            event_id = self._generate_event_id()
            if event_metadata is None:
                event_metadata = EventMetadata()

            # Add tenant context to metadata
            if not event_metadata.source:
                event_metadata.source = f"tenant-{self.tenant_id}"

            # Publish to adapter
            topic = self._event_type_to_topic(event_type)
            result = await self.adapter.publish(
                topic=topic,
                event_id=event_id,
                event_type=event_type,
                data=data,
                partition_key=partition_key,
                metadata=event_metadata,
            )

            # Cache for idempotency
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result

            # Update metrics
            self._publish_count += 1

            logger.info(
                "Event published",
                event_id=event_id,
                event_type=event_type,
                topic=topic,
                partition=result.partition,
                offset=result.offset,
            )

            return result

        except Exception as e:
            self._error_count += 1
            logger.error(
                "Failed to publish event",
                event_type=event_type,
                error=str(e),
                tenant_id=self.tenant_id,
            )
            raise PublishError(f"Failed to publish event: {e}") from e

    async def subscribe(
        self,
        event_types: List[str],
        consumer_group: str,
        auto_commit: bool = True,
        max_poll_records: int = 100,
    ) -> AsyncIterator[Event]:
        """
        Subscribe to events of specified types.

        Args:
            event_types: List of event types to subscribe to
            consumer_group: Consumer group identifier
            auto_commit: Whether to auto-commit message offsets
            max_poll_records: Maximum records to poll at once

        Yields:
            Event objects as they arrive

        Raises:
            SubscriptionError: If subscription fails
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Convert event types to topics
            topics = [self._event_type_to_topic(et) for et in event_types]

            # Add to active subscriptions
            subscription_key = f"{consumer_group}:{':'.join(topics)}"
            self._subscriptions.add(subscription_key)

            logger.info(
                "Starting subscription",
                event_types=event_types,
                consumer_group=consumer_group,
                topics=topics,
            )

            # Subscribe via adapter
            async for event in self.adapter.subscribe(
                topics=topics,
                consumer_group=consumer_group,
                auto_commit=auto_commit,
                max_poll_records=max_poll_records,
            ):
                self._consume_count += 1

                logger.debug(
                    "Event received",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    consumer_group=consumer_group,
                )

                yield event

        except Exception as e:
            self._error_count += 1
            logger.error(
                "Subscription failed",
                event_types=event_types,
                consumer_group=consumer_group,
                error=str(e),
            )
            raise SubscriptionError(f"Subscription failed: {e}") from e
        finally:
            # Remove from active subscriptions
            if "subscription_key" in locals():
                self._subscriptions.discard(subscription_key)

    async def unsubscribe(self, consumer_group: str) -> None:
        """
        Unsubscribe from all topics for a consumer group.

        Args:
            consumer_group: Consumer group to unsubscribe
        """
        if not self._initialized:
            return

        try:
            await self.adapter.unsubscribe(consumer_group)

            # Remove from active subscriptions
            to_remove = [
                s for s in self._subscriptions if s.startswith(f"{consumer_group}:")
            ]
            for subscription in to_remove:
                self._subscriptions.discard(subscription)

            logger.info("Unsubscribed", consumer_group=consumer_group)

        except Exception as e:
            logger.error(
                "Failed to unsubscribe",
                consumer_group=consumer_group,
                error=str(e),
            )
            raise SubscriptionError(f"Failed to unsubscribe: {e}") from e

    async def get_topic_info(self, event_type: str) -> Dict[str, Any]:
        """
        Get information about a topic.

        Args:
            event_type: Event type to get info for

        Returns:
            Topic information dictionary
        """
        if not self._initialized:
            await self.initialize()

        topic = self._event_type_to_topic(event_type)
        return await self.adapter.get_topic_info(topic)

    async def list_topics(self) -> List[str]:
        """
        List all topics for this tenant.

        Returns:
            List of topic names
        """
        if not self._initialized:
            await self.initialize()

        all_topics = await self.adapter.list_topics()
        # Filter by tenant prefix
        tenant_topics = [
            topic for topic in all_topics if topic.startswith(f"{self.topic_prefix}.")
        ]
        return tenant_topics

    async def create_topic(
        self,
        event_type: str,
        partitions: int = 3,
        replication_factor: int = 2,
        retention_hours: int = 168,
        cleanup_policy: str = "delete",
    ) -> None:
        """
        Create a new topic for an event type.

        Args:
            event_type: Event type for the topic
            partitions: Number of partitions
            replication_factor: Replication factor
            retention_hours: Message retention in hours
            cleanup_policy: Cleanup policy
        """
        if not self._initialized:
            await self.initialize()

        topic = self._event_type_to_topic(event_type)

        await self.adapter.create_topic(
            topic=topic,
            partitions=partitions,
            replication_factor=replication_factor,
            retention_hours=retention_hours,
            cleanup_policy=cleanup_policy,
        )

        logger.info(
            "Topic created",
            event_type=event_type,
            topic=topic,
            partitions=partitions,
        )

    async def delete_topic(self, event_type: str) -> None:
        """
        Delete a topic for an event type.

        Args:
            event_type: Event type to delete topic for
        """
        if not self._initialized:
            await self.initialize()

        topic = self._event_type_to_topic(event_type)
        await self.adapter.delete_topic(topic)

        logger.info("Topic deleted", event_type=event_type, topic=topic)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get SDK metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "tenant_id": self.tenant_id,
            "publish_count": self._publish_count,
            "consume_count": self._consume_count,
            "error_count": self._error_count,
            "active_subscriptions": len(self._subscriptions),
            "idempotency_cache_size": len(self._idempotency_cache),
        }
