"""
In-memory adapter for testing and development.

Provides in-memory implementation of the EventAdapter interface:
- Uses Python data structures for event storage
- Simulates partitions and consumer groups
- Useful for testing and development
- No persistence - data is lost on restart
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Set

import structlog

from .base import (
    AdapterConfig,
    ConsumerRecord,
    EventAdapter,
    EventRecord,
    PublishResult,
)

logger = structlog.get_logger(__name__)


class MemoryConfig(AdapterConfig):
    """In-memory adapter configuration."""

    max_messages_per_topic: int = 10000
    max_consumer_lag: int = 1000

    @property
    def connection_string(self) -> str:
        """Memory adapter doesn't need connection string."""
        return "memory://localhost"


class MemoryAdapter(EventAdapter):
    """In-memory adapter for testing and development."""

    def __init__(self, config: MemoryConfig):
        """Initialize memory adapter."""
        super().__init__(config)
        self.config: MemoryConfig = config

        # Storage
        self._topics: Dict[str, Dict[int, deque]] = defaultdict(lambda: defaultdict(deque))
        self._topic_configs: Dict[str, Dict[str, Any]] = {}
        self._consumer_groups: Dict[str, Dict[str, Any]] = {}
        self._consumer_offsets: Dict[str, Dict[str, Dict[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

        # State
        self._connected = False
        self._message_counter = 0

    async def connect(self) -> None:
        """Connect to memory adapter."""
        self._connected = True
        logger.info("Connected to memory adapter")

    async def disconnect(self) -> None:
        """Disconnect from memory adapter."""
        self._connected = False

        # Clear all subscribers
        for queues in self._subscribers.values():
            for queue in queues:
                try:
                    queue.put_nowait(None)  # Signal end
                except asyncio.QueueFull:
                    pass

        self._subscribers.clear()
        logger.info("Disconnected from memory adapter")

    def _ensure_connected(self):
        """Ensure adapter is connected."""
        if not self._connected:
            raise RuntimeError("Memory adapter is not connected")

    def _get_next_message_id(self) -> str:
        """Get next message ID."""
        self._message_counter += 1
        return str(self._message_counter)

    def _get_partition(self, topic: str, partition_key: Optional[str]) -> int:
        """Get partition for message."""
        if topic not in self._topic_configs:
            return 0

        partitions = self._topic_configs[topic].get("partitions", 1)

        if partition_key:
            return hash(partition_key) % partitions
        return 0

    async def publish(
        self,
        topic: str,
        event: EventRecord,
        partition_key: Optional[str] = None
    ) -> PublishResult:
        """Publish event to memory topic."""
        self._ensure_connected()

        # Auto-create topic if it doesn't exist
        if topic not in self._topic_configs:
            await self.create_topic(topic)

        partition = self._get_partition(topic, partition_key or event.partition_key)
        message_id = self._get_next_message_id()

        # Create message with offset
        message = {
            "message_id": message_id,
            "event": event,
            "timestamp": datetime.now(),
            "partition": partition
        }

        # Add to topic partition
        topic_partitions = self._topics[topic]
        partition_queue = topic_partitions[partition]

        # Enforce max messages limit
        if len(partition_queue) >= self.config.max_messages_per_topic:
            partition_queue.popleft()  # Remove oldest message

        partition_queue.append(message)

        # Notify subscribers
        if topic in self._subscribers:
            consumer_record = ConsumerRecord(
                event=event,
                offset=message_id,
                partition=partition,
                topic=topic
            )

            for queue in self._subscribers[topic]:
                try:
                    queue.put_nowait(consumer_record)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, dropping message")

        logger.debug(
            "Published event to memory topic",
            topic=topic,
            event_id=event.event_id,
            partition=partition,
            message_id=message_id
        )

        return PublishResult(
            event_id=event.event_id,
            partition=partition,
            offset=message_id,
            timestamp=datetime.now()
        )

    async def subscribe(  # noqa: C901
        self,
        topics: List[str],
        consumer_group: str,
        auto_commit: bool = True
    ) -> AsyncIterator[ConsumerRecord]:
        """Subscribe to topics."""
        self._ensure_connected()

        # Register consumer group
        if consumer_group not in self._consumer_groups:
            self._consumer_groups[consumer_group] = {
                "topics": set(topics),
                "members": 1,
                "created_at": datetime.now()
            }
        else:
            self._consumer_groups[consumer_group]["topics"].update(topics)
            self._consumer_groups[consumer_group]["members"] += 1

        # Create subscriber queue
        subscriber_queue = asyncio.Queue(maxsize=1000)

        # Register for all topics
        for topic in topics:
            self._subscribers[topic].add(subscriber_queue)

        # Send historical messages based on consumer group offset
        for topic in topics:
            if topic in self._topics:
                for partition, messages in self._topics[topic].items():
                    offset = self._consumer_offsets[consumer_group][topic][partition]

                    # Find messages after offset
                    for i, message in enumerate(messages):
                        if int(message["message_id"]) > offset:
                            consumer_record = ConsumerRecord(
                                event=message["event"],
                                offset=message["message_id"],
                                partition=partition,
                                topic=topic
                            )
                            try:
                                subscriber_queue.put_nowait(consumer_record)
                            except asyncio.QueueFull:
                                logger.warning("Subscriber queue full during historical replay")
                                break

        logger.info(
            "Started memory consumer",
            topics=topics,
            consumer_group=consumer_group
        )

        try:
            while True:
                try:
                    # Wait for messages
                    record = await asyncio.wait_for(subscriber_queue.get(), timeout=1.0)

                    if record is None:  # End signal
                        break

                    yield record

                    # Auto-commit offset
                    if auto_commit:
                        await self.commit_offset(
                            consumer_group,
                            record.topic,
                            record.partition,
                            record.offset
                        )

                except asyncio.TimeoutError:
                    # Normal timeout, continue polling
                    continue

        except asyncio.CancelledError:
            logger.info("Memory consumer cancelled")
            raise
        except Exception as e:
            logger.error("Memory consumer error", error=str(e))
            raise
        finally:
            # Cleanup
            for topic in topics:
                if topic in self._subscribers:
                    self._subscribers[topic].discard(subscriber_queue)

            # Update consumer group
            if consumer_group in self._consumer_groups:
                self._consumer_groups[consumer_group]["members"] -= 1
                if self._consumer_groups[consumer_group]["members"] <= 0:
                    del self._consumer_groups[consumer_group]

    async def commit_offset(
        self,
        consumer_group: str,
        topic: str,
        partition: int,
        offset: str
    ) -> None:
        """Commit offset for consumer group."""
        self._ensure_connected()

        self._consumer_offsets[consumer_group][topic][partition] = int(offset)

        logger.debug(
            "Committed offset",
            consumer_group=consumer_group,
            topic=topic,
            partition=partition,
            offset=offset
        )

    async def create_topic(
        self,
        topic: str,
        partitions: int = 3,
        replication_factor: int = 2,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create memory topic."""
        self._ensure_connected()

        if topic in self._topic_configs:
            logger.warning("Topic already exists", topic=topic)
            return

        self._topic_configs[topic] = {
            "partitions": partitions,
            "replication_factor": replication_factor,
            "config": config or {},
            "created_at": datetime.now()
        }

        # Initialize partitions
        for i in range(partitions):
            self._topics[topic][i] = deque(maxlen=self.config.max_messages_per_topic)

        logger.info(
            "Created memory topic",
            topic=topic,
            partitions=partitions,
            replication_factor=replication_factor
        )

    async def delete_topic(self, topic: str) -> None:
        """Delete memory topic."""
        self._ensure_connected()

        if topic in self._topic_configs:
            del self._topic_configs[topic]

        if topic in self._topics:
            del self._topics[topic]

        # Clear subscribers
        if topic in self._subscribers:
            for queue in self._subscribers[topic]:
                try:
                    queue.put_nowait(None)  # Signal end
                except asyncio.QueueFull:
                    pass
            del self._subscribers[topic]

        logger.info("Deleted memory topic", topic=topic)

    async def list_topics(self) -> List[str]:
        """List all memory topics."""
        self._ensure_connected()
        return list(self._topic_configs.keys())

    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """Get memory topic information."""
        self._ensure_connected()

        if topic not in self._topic_configs:
            raise ValueError(f"Topic {topic} not found")

        config = self._topic_configs[topic]

        # Calculate message count
        message_count = 0
        if topic in self._topics:
            message_count = sum(len(partition) for partition in self._topics[topic].values())

        return {
            "topic": topic,
            "partitions": config["partitions"],
            "replication_factor": config["replication_factor"],
            "message_count": message_count,
            "created_at": config["created_at"].isoformat(),
            "config": config["config"]
        }

    async def list_consumer_groups(self) -> List[Dict[str, Any]]:
        """List all consumer groups."""
        self._ensure_connected()

        groups = []
        for group_id, info in self._consumer_groups.items():
            groups.append({
                "group_id": group_id,
                "topics": list(info["topics"]),
                "members": info["members"],
                "created_at": info["created_at"].isoformat()
            })

        return groups

    async def delete_consumer_group(self, group_id: str) -> None:
        """Delete consumer group."""
        self._ensure_connected()

        if group_id in self._consumer_groups:
            del self._consumer_groups[group_id]

        if group_id in self._consumer_offsets:
            del self._consumer_offsets[group_id]

        logger.info("Deleted consumer group", group_id=group_id)

    async def get_consumer_group_info(self, group_id: str) -> Dict[str, Any]:
        """Get consumer group information."""
        self._ensure_connected()

        if group_id not in self._consumer_groups:
            raise ValueError(f"Consumer group {group_id} not found")

        info = self._consumer_groups[group_id]
        offsets = self._consumer_offsets.get(group_id, {})

        return {
            "group_id": group_id,
            "topics": list(info["topics"]),
            "members": info["members"],
            "created_at": info["created_at"].isoformat(),
            "offsets": {
                topic: dict(partitions) for topic, partitions in offsets.items()
            }
        }

    async def seek_to_beginning(
        self,
        consumer_group: str,
        topic: str,
        partition: Optional[int] = None
    ) -> None:
        """Seek to beginning of topic."""
        self._ensure_connected()

        if partition is not None:
            self._consumer_offsets[consumer_group][topic][partition] = 0
        # Reset all partitions
        elif topic in self._topic_configs:
            partitions = self._topic_configs[topic]["partitions"]
            for p in range(partitions):
                self._consumer_offsets[consumer_group][topic][p] = 0

        logger.info(
            "Seeked to beginning",
            consumer_group=consumer_group,
            topic=topic,
            partition=partition
        )

    async def seek_to_end(
        self,
        consumer_group: str,
        topic: str,
        partition: Optional[int] = None
    ) -> None:
        """Seek to end of topic."""
        self._ensure_connected()

        if partition is not None:
            latest_offset = await self.get_latest_offset(topic, partition)
            self._consumer_offsets[consumer_group][topic][partition] = int(latest_offset)
        # Seek all partitions
        elif topic in self._topic_configs:
            partitions = self._topic_configs[topic]["partitions"]
            for p in range(partitions):
                latest_offset = await self.get_latest_offset(topic, p)
                self._consumer_offsets[consumer_group][topic][p] = int(latest_offset)

        logger.info(
            "Seeked to end",
            consumer_group=consumer_group,
            topic=topic,
            partition=partition
        )

    async def seek_to_offset(
        self,
        consumer_group: str,
        topic: str,
        partition: int,
        offset: str
    ) -> None:
        """Seek to specific offset."""
        self._ensure_connected()

        self._consumer_offsets[consumer_group][topic][partition] = int(offset)

        logger.info(
            "Seeked to offset",
            consumer_group=consumer_group,
            topic=topic,
            partition=partition,
            offset=offset
        )

    async def get_latest_offset(self, topic: str, partition: int) -> str:
        """Get latest offset for topic partition."""
        self._ensure_connected()

        if topic not in self._topics or partition not in self._topics[topic]:
            return "0"

        partition_queue = self._topics[topic][partition]
        if not partition_queue:
            return "0"

        return partition_queue[-1]["message_id"]

    async def get_earliest_offset(self, topic: str, partition: int) -> str:
        """Get earliest offset for topic partition."""
        self._ensure_connected()

        if topic not in self._topics or partition not in self._topics[topic]:
            return "0"

        partition_queue = self._topics[topic][partition]
        if not partition_queue:
            return "0"

        return partition_queue[0]["message_id"]
