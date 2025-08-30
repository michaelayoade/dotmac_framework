"""
Event Bus SDK - Simplified high-level API.

Provides a simplified interface for event publishing and consumption
with automatic adapter selection and sensible defaults.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

from ..adapters.kafka_adapter import KafkaConfig, KafkaEventAdapter
from ..adapters.memory_adapter import MemoryConfig, MemoryEventAdapter
from ..adapters.redis_adapter import RedisConfig, RedisEventAdapter
from ..core.event_bus import EventBus
from ..core.models import (
    ConsumerRecord,
    EventBusError,
    EventMetadata,
    EventRecord,
    PublishResult,
)

logger = structlog.get_logger(__name__)


class EventBusSDK:
    """
    High-level Event Bus SDK.

    Provides a simplified interface for event-driven applications with:
    - Automatic adapter selection based on configuration
    - Sensible defaults for common use cases
    - Simplified publishing and subscription APIs
    - Built-in error handling and retries
    """

    def __init__(
        self,
        adapter_type: str = "memory",
        connection_string: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize Event Bus SDK.

        Args:
            adapter_type: Type of adapter ('memory', 'redis', 'kafka')
            connection_string: Connection string for the adapter
            **kwargs: Additional adapter configuration
        """
        self.adapter_type = adapter_type
        self.connection_string = connection_string
        self.config = kwargs

        self._event_bus: Optional[EventBus] = None
        self._adapter = None

        logger.info("Event Bus SDK initialized", adapter_type=adapter_type)

    async def start(self) -> None:
        """Start the event bus."""
        try:
            # Create adapter based on type
            if self.adapter_type == "memory":
                config = MemoryConfig(**self.config)
                self._adapter = MemoryEventAdapter(config)

            elif self.adapter_type == "redis":
                config = RedisConfig(
                    connection_string=self.connection_string
                    or "redis://localhost:6379/0",
                    **self.config,
                )
                self._adapter = RedisEventAdapter(config)

            elif self.adapter_type == "kafka":
                config = KafkaConfig(
                    connection_string=self.connection_string or "localhost:9092",
                    bootstrap_servers=self.connection_string or "localhost:9092",
                    **self.config,
                )
                self._adapter = KafkaEventAdapter(config)

            else:
                raise EventBusError(f"Unsupported adapter type: {self.adapter_type}")

            # Create and start event bus
            self._event_bus = EventBus(self._adapter)
            await self._event_bus.start()

            logger.info("Event Bus SDK started", adapter_type=self.adapter_type)

        except Exception as e:
            logger.error("Failed to start Event Bus SDK", error=str(e))
            raise EventBusError(f"Failed to start Event Bus SDK: {e}") from e

    async def stop(self) -> None:
        """Stop the event bus."""
        try:
            if self._event_bus:
                await self._event_bus.stop()

            logger.info("Event Bus SDK stopped")

        except Exception as e:
            logger.error("Error stopping Event Bus SDK", error=str(e))

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        *,
        topic: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish an event.

        Args:
            event_type: Event type (e.g., 'user.created')
            data: Event payload
            topic: Target topic (optional)
            tenant_id: Tenant ID for multi-tenancy
            correlation_id: Correlation ID for request tracing
            user_id: User who triggered the event
            source: Source service/system

        Returns:
            PublishResult with event details
        """
        if not self._event_bus:
            raise EventBusError("Event Bus SDK not started")

        try:
            # Create metadata
            metadata = EventMetadata(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                user_id=user_id,
                source=source,
            )

            # Publish event
            result = await self._event_bus.publish(
                event_type=event_type, data=data, metadata=metadata, topic=topic
            )

            logger.debug(
                "Event published via SDK",
                event_id=result.event_id,
                event_type=event_type,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to publish event via SDK", event_type=event_type, error=str(e)
            )
            raise

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
            events: List of event dictionaries with 'event_type' and 'data'
            topic: Target topic for all events
            tenant_id: Tenant ID for all events

        Returns:
            List of PublishResult objects
        """
        if not self._event_bus:
            raise EventBusError("Event Bus SDK not started")

        try:
            results = await self._event_bus.publish_batch(
                events=events, topic=topic, tenant_id=tenant_id
            )

            logger.debug("Event batch published via SDK", batch_size=len(events))

            return results

        except Exception as e:
            logger.error(
                "Failed to publish event batch via SDK",
                batch_size=len(events),
                error=str(e),
            )
            raise

    async def subscribe(
        self,
        event_type: Union[str, List[str]],
        handler: Callable[[Dict[str, Any]], None],
        *,
        consumer_group: str = "default",
        topics: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """
        Subscribe to events with a simplified handler.

        Args:
            event_type: Event type(s) to subscribe to
            handler: Handler function that receives event data dict
            consumer_group: Consumer group name
            topics: Topics to consume from
            tenant_id: Filter by tenant ID
        """
        if not self._event_bus:
            raise EventBusError("Event Bus SDK not started")

        try:
            # Create wrapper callback that extracts event data
            async def wrapper_callback(record: ConsumerRecord):
                try:
                    # Extract simplified event data
                    event_data = {
                        "event_id": record.event.event_id,
                        "event_type": record.event.event_type,
                        "data": record.event.data,
                        "metadata": record.event.metadata.model_dump(),
                        "topic": record.topic,
                        "timestamp": record.timestamp.isoformat(),
                        "consumer_group": record.consumer_group,
                    }

                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)

                except Exception as e:
                    logger.error(
                        "Error in SDK event handler",
                        event_id=record.event.event_id,
                        error=str(e),
                    )
                    raise

            # Subscribe using event bus
            await self._event_bus.subscribe(
                event_types=event_type,
                callback=wrapper_callback,
                consumer_group=consumer_group,
                topics=topics,
                tenant_id=tenant_id,
            )

            logger.info(
                "Subscribed to events via SDK",
                event_types=event_type,
                consumer_group=consumer_group,
            )

        except Exception as e:
            logger.error(
                "Failed to subscribe via SDK", event_types=event_type, error=str(e)
            )
            raise

    async def create_topic(self, topic_name: str) -> bool:
        """Create a topic."""
        if not self._event_bus:
            raise EventBusError("Event Bus SDK not started")

        return await self._event_bus.create_topic(topic_name)

    async def health_check(self) -> Dict[str, Any]:
        """Get health status."""
        if not self._event_bus:
            return {"healthy": False, "error": "Event Bus SDK not started"}

        return await self._event_bus.health_check()

    @classmethod
    def create_memory_bus(cls, **kwargs) -> "EventBusSDK":
        """Create an in-memory event bus for testing."""
        return cls(adapter_type="memory", **kwargs)

    @classmethod
    def create_redis_bus(cls, connection_string: str, **kwargs) -> "EventBusSDK":
        """Create a Redis-backed event bus."""
        return cls(adapter_type="redis", connection_string=connection_string, **kwargs)

    @classmethod
    def create_kafka_bus(cls, bootstrap_servers: str, **kwargs) -> "EventBusSDK":
        """Create a Kafka-backed event bus."""
        return cls(adapter_type="kafka", connection_string=bootstrap_servers, **kwargs)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
