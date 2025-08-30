"""
In-Memory Event Adapter for Testing.

Provides an in-memory implementation of the EventAdapter interface.
Useful for testing and development scenarios where external dependencies
are not available or desired.
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog

from ..core.event_bus import EventAdapter
from ..core.models import (
    AdapterConfig,
    ConsumerConfig,
    ConsumerRecord,
    EventBusError,
    EventRecord,
    PublishResult,
    TopicConfig,
)

logger = structlog.get_logger(__name__)


class MemoryConfig(AdapterConfig):
    """Configuration for memory event adapter."""

    connection_string: str = "memory://"
    max_topic_size: int = 10000  # Maximum events per topic
    consumer_timeout_seconds: int = 30


class MemoryTopic:
    """In-memory topic implementation."""

    def __init__(self, name: str, max_size: int = 10000):
        self.name = name
        self.max_size = max_size
        self.events: deque = deque(maxlen=max_size)
        self.partitions: Dict[int, deque] = defaultdict(lambda: deque(maxlen=max_size))
        self.consumer_offsets: Dict[str, Dict[int, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.lock = asyncio.Lock()

    async def append(self, event: EventRecord) -> PublishResult:
        """Add event to topic."""
        async with self.lock:
            # Calculate partition (simple hash of partition key or round robin)
            if event.partition_key:
                partition = hash(event.partition_key) % 4  # 4 partitions by default
            else:
                partition = len(self.events) % 4

            # Set event metadata
            event.partition = partition
            event.offset = str(len(self.partitions[partition]))
            event.timestamp = datetime.utcnow()

            # Add to partition
            self.partitions[partition].append(event)

            # Add to main topic queue for simple consumption
            self.events.append(event)

            return PublishResult(
                event_id=event.event_id,
                topic=self.name,
                partition=partition,
                offset=event.offset,
                timestamp=event.timestamp,
            )

    async def consume(
        self, consumer_group: str, consumer_id: str, last_offset: int = 0
    ) -> List[EventRecord]:
        """Consume events from topic."""
        async with self.lock:
            # Simple consumption - return events after last offset
            current_offset = self.consumer_offsets[consumer_group].get(0, last_offset)
            available_events = list(self.events)[current_offset:]

            # Update offset
            if available_events:
                self.consumer_offsets[consumer_group][0] = current_offset + len(
                    available_events
                )

            return available_events


class MemoryEventAdapter(EventAdapter):
    """
    In-memory event adapter for testing and development.

    Provides a simple, fast event streaming implementation without
    external dependencies. Events are stored in memory and will be
    lost when the adapter is destroyed.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """Initialize memory adapter."""
        if config is None:
            config = MemoryConfig()

        super().__init__(config)

        self._topics: Dict[str, MemoryTopic] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._consumer_tasks: Dict[str, asyncio.Task] = {}

        logger.info(
            "Memory event adapter initialized", max_topic_size=config.max_topic_size
        )

    async def connect(self) -> None:
        """Connect to memory backend (no-op)."""
        self._connected = True
        logger.info("Memory event adapter connected")

    async def disconnect(self) -> None:
        """Disconnect from memory backend."""
        # Cancel consumer tasks
        for task in self._consumer_tasks.values():
            task.cancel()

        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks.values(), return_exceptions=True)

        self._consumer_tasks.clear()
        self._connected = False
        logger.info("Memory event adapter disconnected")

    async def publish(
        self, event: EventRecord, topic: Optional[str] = None
    ) -> PublishResult:
        """Publish event to a topic."""
        if not self._connected:
            raise EventBusError("Adapter not connected")

        target_topic = topic or event.topic or "default"

        # Create topic if it doesn't exist
        if target_topic not in self._topics:
            await self._create_memory_topic(target_topic)

        # Publish to topic
        topic_obj = self._topics[target_topic]
        result = await topic_obj.append(event)

        logger.debug(
            "Event published to memory topic",
            event_id=event.event_id,
            topic=target_topic,
            partition=result.partition,
            offset=result.offset,
        )

        # Notify subscribers
        await self._notify_subscribers(target_topic, event)

        return result

    async def publish_batch(
        self, events: List[EventRecord], topic: Optional[str] = None
    ) -> List[PublishResult]:
        """Publish multiple events."""
        if not self._connected:
            raise EventBusError("Adapter not connected")

        results = []
        for event in events:
            result = await self.publish(event, topic)
            results.append(result)

        logger.debug(
            "Event batch published to memory", batch_size=len(events), topic=topic
        )

        return results

    async def subscribe(
        self,
        topics: List[str],
        consumer_config: ConsumerConfig,
        callback: Callable[[ConsumerRecord], None],
    ) -> None:
        """Subscribe to topics with callback."""
        if not self._connected:
            raise EventBusError("Adapter not connected")

        # Register callback for each topic
        for topic in topics:
            self._subscribers[topic].append(callback)

        # Start consumer task
        consumer_key = f"{consumer_config.consumer_group}:{consumer_config.consumer_id}"
        if consumer_key not in self._consumer_tasks:
            task = asyncio.create_task(
                self._consumer_loop(topics, consumer_config, callback)
            )
            self._consumer_tasks[consumer_key] = task

        logger.info(
            "Subscribed to memory topics",
            topics=topics,
            consumer_group=consumer_config.consumer_group,
        )

    async def consume(
        self, topics: List[str], consumer_config: ConsumerConfig
    ) -> AsyncIterator[ConsumerRecord]:
        """Consume events as async iterator."""
        if not self._connected:
            raise EventBusError("Adapter not connected")

        consumer_offsets = defaultdict(int)

        while self._connected:
            try:
                # Check each topic for new events
                for topic in topics:
                    if topic in self._topics:
                        topic_obj = self._topics[topic]
                        events = await topic_obj.consume(
                            consumer_config.consumer_group,
                            consumer_config.consumer_id,
                            consumer_offsets[topic],
                        )

                        for event in events:
                            consumer_record = ConsumerRecord(
                                event=event,
                                consumer_group=consumer_config.consumer_group,
                                consumer_id=consumer_config.consumer_id,
                                topic=topic,
                                partition=event.partition or 0,
                                offset=event.offset or "0",
                                timestamp=datetime.utcnow(),
                            )

                            yield consumer_record
                            consumer_offsets[topic] += 1

                # Short sleep to prevent busy loop
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in memory consumer", topics=topics, error=str(e))
                await asyncio.sleep(1)

    async def create_topic(self, topic_config: TopicConfig) -> bool:
        """Create a new topic."""
        try:
            topic = MemoryTopic(
                topic_config.name,
                max_size=getattr(self.config, "max_topic_size", 10000),
            )
            self._topics[topic_config.name] = topic

            logger.info(
                "Memory topic created",
                topic=topic_config.name,
                partitions=topic_config.partitions,
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to create memory topic", topic=topic_config.name, error=str(e)
            )
            return False

    async def delete_topic(self, topic_name: str) -> bool:
        """Delete a topic."""
        try:
            if topic_name in self._topics:
                del self._topics[topic_name]

                # Remove subscribers
                if topic_name in self._subscribers:
                    del self._subscribers[topic_name]

                logger.info("Memory topic deleted", topic=topic_name)
                return True

            return False

        except Exception as e:
            logger.error(
                "Failed to delete memory topic", topic=topic_name, error=str(e)
            )
            return False

    async def list_topics(self) -> List[str]:
        """List available topics."""
        return list(self._topics.keys())

    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> bool:
        """Commit consumer offset."""
        try:
            if topic in self._topics:
                topic_obj = self._topics[topic]
                topic_obj.consumer_offsets[consumer_group][partition] = int(offset)
                return True
            return False
        except Exception as e:
            logger.error(
                "Failed to commit offset",
                topic=topic,
                consumer_group=consumer_group,
                error=str(e),
            )
            return False

    async def _create_memory_topic(self, topic_name: str) -> None:
        """Create a memory topic if it doesn't exist."""
        if topic_name not in self._topics:
            topic_config = TopicConfig(name=topic_name)
            await self.create_topic(topic_config)

    async def _notify_subscribers(self, topic: str, event: EventRecord) -> None:
        """Notify subscribers of new event."""
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    consumer_record = ConsumerRecord(
                        event=event,
                        consumer_group="default",
                        consumer_id="memory-notifier",
                        topic=topic,
                        partition=event.partition or 0,
                        offset=event.offset or "0",
                        timestamp=datetime.utcnow(),
                    )

                    if asyncio.iscoroutinefunction(callback):
                        await callback(consumer_record)
                    else:
                        callback(consumer_record)

                except Exception as e:
                    logger.error(
                        "Error in subscriber callback",
                        topic=topic,
                        event_id=event.event_id,
                        error=str(e),
                    )

    async def _consumer_loop(
        self,
        topics: List[str],
        consumer_config: ConsumerConfig,
        callback: Callable[[ConsumerRecord], None],
    ) -> None:
        """Background consumer loop for subscriptions."""
        try:
            async for record in self.consume(topics, consumer_config):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(record)
                    else:
                        callback(record)
                except Exception as e:
                    logger.error(
                        "Error in consumer callback",
                        event_id=record.event.event_id,
                        error=str(e),
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                "Consumer loop error",
                topics=topics,
                consumer_group=consumer_config.consumer_group,
                error=str(e),
            )
