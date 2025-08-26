"""
Redis Streams adapter for event streaming.

Provides Redis Streams implementation of the EventAdapter interface:
- Uses Redis Streams for event publishing and consumption
- Consumer groups for scalable consumption
- Automatic topic creation as streams
- Offset management with Redis consumer groups
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

import redis.asyncio as redis
import structlog

from .base import (
    AdapterConfig,
    ConsumerRecord,
    EventAdapter,
    EventRecord,
    PublishResult,
)

logger = structlog.get_logger(__name__)


class RedisConfig(AdapterConfig):
    """Redis-specific configuration."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 10
    stream_maxlen: int = 10000
    consumer_timeout_ms: int = 5000

    @property
    def connection_string(self) -> str:
        """Build Redis connection string."""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class RedisAdapter(EventAdapter):
    """Redis Streams adapter for event streaming."""

    def __init__(self, config: RedisConfig):
        """Initialize Redis adapter."""
        super().__init__(config)
        self.config: RedisConfig = config
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._client = redis.from_url(
                self.config.connection_string,
                max_connections=self.config.max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )

            # Test connection
            await self._client.ping()
            self._connected = True

            logger.info(
                "Connected to Redis", host=self.config.host, port=self.config.port
            )

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("Disconnected from Redis")

    def _ensure_connected(self):
        """Ensure Redis client is connected."""
        if not self._connected or not self._client:
            raise RuntimeError("Redis adapter is not connected")

    def _topic_to_stream(self, topic: str) -> str:
        """Convert topic name to Redis stream key."""
        return f"events:{topic}"

    def _consumer_group_key(self, consumer_group: str) -> str:
        """Get consumer group key."""
        return f"cg:{consumer_group}"

    async def publish(
        self, topic: str, event: EventRecord, partition_key: Optional[str] = None
    ) -> PublishResult:
        """Publish event to Redis stream."""
        self._ensure_connected()

        stream_key = self._topic_to_stream(topic)

        # Prepare event data
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "data": json.dumps(event.data),
            "timestamp": event.timestamp.isoformat(),
        }

        if event.partition_key:
            event_data["partition_key"] = event.partition_key

        if event.headers:
            event_data["headers"] = json.dumps(event.headers)

        try:
            # Add to stream with maxlen to prevent unbounded growth
            message_id = await self._client.xadd(
                stream_key,
                event_data,
                maxlen=self.config.stream_maxlen,
                approximate=True,
            )

            logger.debug(
                "Published event to Redis stream",
                topic=topic,
                event_id=event.event_id,
                message_id=message_id,
            )

            return PublishResult(
                event_id=event.event_id, offset=message_id, timestamp=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(
                "Failed to publish event to Redis stream",
                topic=topic,
                event_id=event.event_id,
                error=str(e),
            )
            raise

    async def subscribe(  # noqa: C901
        self, topics: List[str], consumer_group: str, auto_commit: bool = True
    ) -> AsyncIterator[ConsumerRecord]:
        """Subscribe to topics using Redis consumer groups."""
        self._ensure_connected()

        stream_keys = {self._topic_to_stream(topic): ">" for topic in topics}
        consumer_name = f"consumer-{uuid.uuid4().hex[:8]}"
        group_key = self._consumer_group_key(consumer_group)

        # Create consumer groups for all streams
        for stream_key in stream_keys:
            try:
                await self._client.xgroup_create(
                    stream_key, group_key, id="0", mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(
                        "Failed to create consumer group",
                        stream=stream_key,
                        group=group_key,
                        error=str(e),
                    )
                    raise

        logger.info(
            "Started Redis consumer",
            topics=topics,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )

        try:
            while True:
                try:
                    # Read from streams
                    messages = await self._client.xreadgroup(
                        group_key,
                        consumer_name,
                        stream_keys,
                        count=1,
                        block=self.config.consumer_timeout_ms,
                    )

                    for stream_key, stream_messages in messages:
                        topic = stream_key.decode().replace("events:", "")

                        for message_id, fields in stream_messages:
                            try:
                                # Parse event data
                                event_data = {
                                    k.decode(): v.decode() for k, v in fields.items()
                                }

                                event = EventRecord(
                                    event_id=event_data["event_id"],
                                    event_type=event_data["event_type"],
                                    data=json.loads(event_data["data"]),
                                    partition_key=event_data.get("partition_key"),
                                    timestamp=datetime.fromisoformat(
                                        event_data["timestamp"]
                                    ),
                                    offset=message_id.decode(),
                                    headers=json.loads(event_data.get("headers", "{}"),
                                )

                                consumer_record = ConsumerRecord(
                                    event=event,
                                    offset=message_id.decode(),
                                    partition=0,  # Redis streams don't have partitions
                                    topic=topic,
                                )

                                yield consumer_record

                                # Auto-commit if enabled
                                if auto_commit:
                                    await self._client.xack(
                                        stream_key, group_key, message_id
                                    )

                            except Exception as e:
                                logger.error(
                                    "Failed to process message",
                                    message_id=message_id,
                                    error=str(e),
                                )
                                # Acknowledge failed message to prevent reprocessing
                                await self._client.xack(
                                    stream_key, group_key, message_id
                                )

                except redis.ResponseError as e:
                    if "NOGROUP" in str(e):
                        logger.warning("Consumer group was deleted, recreating")
                        # Recreate consumer groups
                        for stream_key in stream_keys:
                            try:
                                await self._client.xgroup_create(
                                    stream_key, group_key, id="0", mkstream=True
                                )
                            except redis.ResponseError:
                                pass
                    else:
                        logger.error("Redis consumer error", error=str(e)
                        raise

                except asyncio.TimeoutError:
                    # Normal timeout, continue polling
                    continue

        except asyncio.CancelledError:
            logger.info("Redis consumer cancelled")
            raise
        except Exception as e:
            logger.error("Redis consumer error", error=str(e)
            raise

    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> None:
        """Commit offset for Redis stream."""
        self._ensure_connected()

        stream_key = self._topic_to_stream(topic)
        group_key = self._consumer_group_key(consumer_group)

        try:
            await self._client.xack(stream_key, group_key, offset)
        except Exception as e:
            logger.error(
                "Failed to commit offset",
                topic=topic,
                consumer_group=consumer_group,
                offset=offset,
                error=str(e),
            )
            raise

    async def create_topic(
        self,
        topic: str,
        partitions: int = 3,
        replication_factor: int = 2,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create topic (Redis stream is created automatically on first write)."""
        # Redis streams are created automatically, nothing to do
        logger.info("Topic will be created automatically on first write", topic=topic)

    async def delete_topic(self, topic: str) -> None:
        """Delete Redis stream."""
        self._ensure_connected()

        stream_key = self._topic_to_stream(topic)

        try:
            await self._client.delete(stream_key)
            logger.info("Deleted Redis stream", topic=topic)
        except Exception as e:
            logger.error("Failed to delete Redis stream", topic=topic, error=str(e)
            raise

    async def list_topics(self) -> List[str]:
        """List all Redis streams (topics)."""
        self._ensure_connected()

        try:
            keys = await self._client.keys("events:*")
            topics = [key.decode().replace("events:", "") for key in keys]
            return topics
        except Exception as e:
            logger.error("Failed to list Redis streams", error=str(e)
            raise

    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """Get Redis stream information."""
        self._ensure_connected()

        stream_key = self._topic_to_stream(topic)

        try:
            info = await self._client.xinfo_stream(stream_key)

            return {
                "topic": topic,
                "length": info[b"length"],
                "first_entry": info[b"first-entry"],
                "last_entry": info[b"last-entry"],
                "groups": info[b"groups"],
            }
        except Exception as e:
            logger.error("Failed to get Redis stream info", topic=topic, error=str(e)
            raise

    async def list_consumer_groups(self) -> List[Dict[str, Any]]:
        """List consumer groups for all streams."""
        self._ensure_connected()

        topics = await self.list_topics()
        groups = []

        for topic in topics:
            stream_key = self._topic_to_stream(topic)
            try:
                group_info = await self._client.xinfo_groups(stream_key)
                for group in group_info:
                    groups.append(
                        {
                            "group_id": group[b"name"].decode(),
                            "topic": topic,
                            "consumers": group[b"consumers"],
                            "pending": group[b"pending"],
                            "last_delivered_id": group[b"last-delivered-id"].decode(),
                        }
                    )
            except redis.ResponseError:
                # No groups for this stream
                continue

        return groups

    async def delete_consumer_group(self, group_id: str) -> None:
        """Delete consumer group from all streams."""
        self._ensure_connected()

        topics = await self.list_topics()
        group_key = self._consumer_group_key(group_id)

        for topic in topics:
            stream_key = self._topic_to_stream(topic)
            try:
                await self._client.xgroup_destroy(stream_key, group_key)
            except redis.ResponseError:
                # Group doesn't exist for this stream
                continue

        logger.info("Deleted consumer group", group_id=group_id)

    async def get_consumer_group_info(self, group_id: str) -> Dict[str, Any]:
        """Get consumer group information."""
        groups = await self.list_consumer_groups()
        group_info = [g for g in groups if g["group_id"] == group_id]

        if not group_info:
            raise ValueError(f"Consumer group {group_id} not found")

        return {
            "group_id": group_id,
            "topics": [g["topic"] for g in group_info],
            "total_consumers": sum(g["consumers"] for g in group_info),
            "total_pending": sum(g["pending"] for g in group_info),
        }

    async def seek_to_beginning(
        self, consumer_group: str, topic: str, partition: Optional[int] = None
    ) -> None:
        """Seek to beginning of stream."""
        # Redis streams don't support seeking, would need to recreate consumer group
        logger.warning(
            "Redis streams don't support seeking, consider recreating consumer group"
        )

    async def seek_to_end(
        self, consumer_group: str, topic: str, partition: Optional[int] = None
    ) -> None:
        """Seek to end of stream."""
        # Redis streams don't support seeking, would need to recreate consumer group
        logger.warning(
            "Redis streams don't support seeking, consider recreating consumer group"
        )

    async def seek_to_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> None:
        """Seek to specific offset."""
        # Redis streams don't support seeking, would need to recreate consumer group
        logger.warning(
            "Redis streams don't support seeking, consider recreating consumer group"
        )

    async def get_latest_offset(self, topic: str, partition: int) -> str:
        """Get latest offset (message ID) for stream."""
        self._ensure_connected()

        stream_key = self._topic_to_stream(topic)

        try:
            info = await self.get_topic_info(topic)
            last_entry = info.get("last_entry")
            if last_entry and len(last_entry) > 0:
                return last_entry[0].decode()
            return "0-0"
        except Exception as e:
            logger.error("Failed to get latest offset", topic=topic, error=str(e)
            return "0-0"

    async def get_earliest_offset(self, topic: str, partition: int) -> str:
        """Get earliest offset (message ID) for stream."""
        self._ensure_connected()

        try:
            info = await self.get_topic_info(topic)
            first_entry = info.get("first_entry")
            if first_entry and len(first_entry) > 0:
                return first_entry[0].decode()
            return "0-0"
        except Exception as e:
            logger.error("Failed to get earliest offset", topic=topic, error=str(e)
            return "0-0"
