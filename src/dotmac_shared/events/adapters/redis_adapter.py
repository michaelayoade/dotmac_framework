"""
Redis Streams Event Adapter.

Provides Redis Streams implementation of the EventAdapter interface.
Uses Redis Streams for durable, ordered event streaming with consumer groups.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..core.event_bus import EventAdapter
from ..core.models import (
    AdapterConfig,
    ConsumerConfig,
    ConsumerRecord,
    EventBusError,
    EventMetadata,
    EventRecord,
    PublishResult,
    TopicConfig,
)

logger = structlog.get_logger(__name__)


class RedisConfig(AdapterConfig):
    """Configuration for Redis event adapter."""

    # Redis connection
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

    # Streams configuration
    stream_maxlen: int = 10000  # Maximum stream length
    consumer_group_name: str = "dotmac-events"
    consumer_name: str = "dotmac-consumer"

    # Consumer settings
    claim_min_idle_ms: int = 60000  # 1 minute
    claim_count: int = 10
    block_timeout_ms: int = 5000  # 5 seconds

    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class RedisEventAdapter(EventAdapter):
    """
    Redis Streams event adapter.

    Provides durable event streaming using Redis Streams with:
    - Consumer groups for load balancing
    - Message acknowledgment
    - Dead letter handling for failed messages
    - Automatic stream trimming
    """

    def __init__(
        self,
        config: Optional[RedisConfig] = None,
        connection_string: Optional[str] = None,
    ):
        """Initialize Redis adapter."""
        if not REDIS_AVAILABLE:
            raise EventBusError(
                "Redis adapter requires 'redis' package: pip install redis"
            )

        if config is None:
            if connection_string:
                config = RedisConfig(connection_string=connection_string)
            else:
                config = RedisConfig()

        super().__init__(config)
        self.redis_config = config
        self._redis: Optional[redis.Redis] = None

        logger.info(
            "Redis event adapter initialized",
            host=config.host,
            port=config.port,
            db=config.db,
        )

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            if self.redis_config.connection_string.startswith("redis://"):
                self._redis = redis.from_url(
                    self.redis_config.connection_string,
                    decode_responses=False,  # We handle encoding ourselves
                )
            else:
                self._redis = redis.Redis(
                    host=self.redis_config.host,
                    port=self.redis_config.port,
                    db=self.redis_config.db,
                    password=self.redis_config.password,
                    decode_responses=False,
                )

            # Test connection
            await self._redis.ping()
            self._connected = True

            logger.info(
                "Connected to Redis",
                host=self.redis_config.host,
                port=self.redis_config.port,
            )

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise EventBusError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        try:
            if self._redis:
                await self._redis.close()
                self._redis = None

            self._connected = False
            logger.info("Disconnected from Redis")

        except Exception as e:
            logger.error("Error disconnecting from Redis", error=str(e))

    async def publish(
        self, event: EventRecord, topic: Optional[str] = None
    ) -> PublishResult:
        """Publish event to Redis stream."""
        if not self._connected or not self._redis:
            raise EventBusError("Redis adapter not connected")

        try:
            stream_key = self._get_stream_key(topic or event.topic or "default")

            # Serialize event data
            event_data = {
                "event_id": event.event_id.encode(),
                "event_type": event.event_type.encode(),
                "data": json.dumps(event.data, default=str).encode(),
                "metadata": json.dumps(
                    event.metadata.model_dump(), default=str
                ).encode(),
                "tenant_id": (event.tenant_id or "").encode(),
                "partition_key": (event.partition_key or "").encode(),
                "timestamp": datetime.utcnow().isoformat().encode(),
            }

            # Add to Redis stream with optional maxlen
            message_id = await self._redis.xadd(
                stream_key,
                event_data,
                maxlen=self.redis_config.stream_maxlen,
                approximate=True,
            )

            result = PublishResult(
                event_id=event.event_id,
                topic=topic or event.topic or "default",
                partition=None,  # Redis Streams don't have partitions
                offset=message_id.decode(),
                timestamp=datetime.utcnow(),
            )

            logger.debug(
                "Event published to Redis stream",
                event_id=event.event_id,
                stream=stream_key,
                message_id=message_id.decode(),
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to publish event to Redis",
                event_id=event.event_id,
                topic=topic,
                error=str(e),
            )
            raise EventBusError(f"Failed to publish event: {e}") from e

    async def publish_batch(
        self, events: List[EventRecord], topic: Optional[str] = None
    ) -> List[PublishResult]:
        """Publish multiple events using Redis pipeline."""
        if not self._connected or not self._redis:
            raise EventBusError("Redis adapter not connected")

        try:
            # Use Redis pipeline for batch operations
            pipeline = self._redis.pipeline()
            stream_key = self._get_stream_key(topic or "default")

            for event in events:
                event_data = {
                    "event_id": event.event_id.encode(),
                    "event_type": event.event_type.encode(),
                    "data": json.dumps(event.data, default=str).encode(),
                    "metadata": json.dumps(
                        event.metadata.model_dump(), default=str
                    ).encode(),
                    "tenant_id": (event.tenant_id or "").encode(),
                    "partition_key": (event.partition_key or "").encode(),
                    "timestamp": datetime.utcnow().isoformat().encode(),
                }

                pipeline.xadd(
                    stream_key,
                    event_data,
                    maxlen=self.redis_config.stream_maxlen,
                    approximate=True,
                )

            # Execute pipeline
            message_ids = await pipeline.execute()

            # Create results
            results = []
            for i, (event, message_id) in enumerate(zip(events, message_ids)):
                result = PublishResult(
                    event_id=event.event_id,
                    topic=topic or event.topic or "default",
                    partition=None,
                    offset=message_id.decode(),
                    timestamp=datetime.utcnow(),
                )
                results.append(result)

            logger.debug(
                "Event batch published to Redis",
                batch_size=len(events),
                stream=stream_key,
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to publish event batch to Redis",
                batch_size=len(events),
                error=str(e),
            )
            raise EventBusError(f"Failed to publish event batch: {e}") from e

    async def subscribe(
        self,
        topics: List[str],
        consumer_config: ConsumerConfig,
        callback: Callable[[ConsumerRecord], None],
    ) -> None:
        """Subscribe to topics using Redis consumer groups."""
        if not self._connected or not self._redis:
            raise EventBusError("Redis adapter not connected")

        try:
            # Create consumer groups for each topic
            for topic in topics:
                stream_key = self._get_stream_key(topic)
                try:
                    await self._redis.xgroup_create(
                        stream_key,
                        consumer_config.consumer_group,
                        id="0",
                        mkstream=True,
                    )
                except redis.ResponseError as e:
                    if "BUSYGROUP" not in str(e):
                        raise

            # Start consumer task
            task = asyncio.create_task(
                self._redis_consumer_loop(topics, consumer_config, callback)
            )

            logger.info(
                "Subscribed to Redis streams",
                topics=topics,
                consumer_group=consumer_config.consumer_group,
            )

        except Exception as e:
            logger.error(
                "Failed to subscribe to Redis streams", topics=topics, error=str(e)
            )
            raise EventBusError(f"Failed to subscribe: {e}") from e

    async def consume(
        self, topics: List[str], consumer_config: ConsumerConfig
    ) -> AsyncIterator[ConsumerRecord]:
        """Consume events from Redis streams."""
        if not self._connected or not self._redis:
            raise EventBusError("Redis adapter not connected")

        # Create consumer groups
        for topic in topics:
            stream_key = self._get_stream_key(topic)
            try:
                await self._redis.xgroup_create(
                    stream_key, consumer_config.consumer_group, id="0", mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

        # Build streams dict for xreadgroup
        streams = {self._get_stream_key(topic): ">" for topic in topics}

        while self._connected:
            try:
                # Read from consumer group
                messages = await self._redis.xreadgroup(
                    consumer_config.consumer_group,
                    consumer_config.consumer_id,
                    streams,
                    count=consumer_config.max_poll_records,
                    block=self.redis_config.block_timeout_ms,
                )

                if messages:
                    for stream, msgs in messages:
                        stream_name = stream.decode()
                        topic = self._get_topic_from_stream_key(stream_name)

                        for msg_id, fields in msgs:
                            try:
                                # Deserialize event
                                event = self._deserialize_redis_message(fields)

                                consumer_record = ConsumerRecord(
                                    event=event,
                                    consumer_group=consumer_config.consumer_group,
                                    consumer_id=consumer_config.consumer_id,
                                    topic=topic,
                                    partition=0,  # Redis Streams don't have partitions
                                    offset=msg_id.decode(),
                                    timestamp=datetime.utcnow(),
                                )

                                yield consumer_record

                                # Acknowledge message
                                if not consumer_config.enable_auto_commit:
                                    await self._redis.xack(
                                        stream, consumer_config.consumer_group, msg_id
                                    )

                            except Exception as e:
                                logger.error(
                                    "Error processing Redis message",
                                    message_id=msg_id.decode(),
                                    error=str(e),
                                )

            except asyncio.TimeoutError:
                continue  # Normal timeout, continue consuming
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Redis consumer", topics=topics, error=str(e))
                await asyncio.sleep(1)

    async def create_topic(self, topic_config: TopicConfig) -> bool:
        """Create Redis stream (no explicit creation needed)."""
        # Redis streams are created automatically on first write
        logger.info(
            "Redis stream will be created on first message", topic=topic_config.name
        )
        return True

    async def delete_topic(self, topic_name: str) -> bool:
        """Delete Redis stream."""
        if not self._connected or not self._redis:
            return False

        try:
            stream_key = self._get_stream_key(topic_name)
            await self._redis.delete(stream_key)

            logger.info("Redis stream deleted", topic=topic_name)
            return True

        except Exception as e:
            logger.error(
                "Failed to delete Redis stream", topic=topic_name, error=str(e)
            )
            return False

    async def list_topics(self) -> List[str]:
        """List Redis streams with the topic prefix."""
        if not self._connected or not self._redis:
            return []

        try:
            pattern = f"{self._get_stream_prefix()}*"
            stream_keys = await self._redis.keys(pattern)

            topics = []
            for key in stream_keys:
                topic = self._get_topic_from_stream_key(key.decode())
                topics.append(topic)

            return topics

        except Exception as e:
            logger.error("Failed to list Redis streams", error=str(e))
            return []

    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> bool:
        """Acknowledge message in Redis (commit offset)."""
        if not self._connected or not self._redis:
            return False

        try:
            stream_key = self._get_stream_key(topic)
            await self._redis.xack(stream_key, consumer_group, offset)
            return True

        except Exception as e:
            logger.error(
                "Failed to commit Redis offset",
                topic=topic,
                offset=offset,
                error=str(e),
            )
            return False

    def _get_stream_prefix(self) -> str:
        """Get Redis stream key prefix."""
        return "dotmac:events:stream:"

    def _get_stream_key(self, topic: str) -> str:
        """Get Redis stream key for topic."""
        return f"{self._get_stream_prefix()}{topic}"

    def _get_topic_from_stream_key(self, stream_key: str) -> str:
        """Extract topic name from Redis stream key."""
        prefix = self._get_stream_prefix()
        if stream_key.startswith(prefix):
            return stream_key[len(prefix) :]
        return stream_key

    def _deserialize_redis_message(self, fields: Dict[bytes, bytes]) -> EventRecord:
        """Deserialize Redis message fields to EventRecord."""
        try:
            # Decode fields
            event_id = fields[b"event_id"].decode()
            event_type = fields[b"event_type"].decode()
            data = json.loads(fields[b"data"].decode())
            metadata_dict = json.loads(fields[b"metadata"].decode())
            tenant_id = fields.get(b"tenant_id", b"").decode() or None
            partition_key = fields.get(b"partition_key", b"").decode() or None

            # Reconstruct metadata
            metadata = EventMetadata(
                event_id=event_id, tenant_id=tenant_id, **metadata_dict
            )

            # Create event record
            event = EventRecord(
                event_type=event_type,
                data=data,
                metadata=metadata,
                partition_key=partition_key,
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to deserialize Redis message", fields=fields, error=str(e)
            )
            raise

    async def _redis_consumer_loop(
        self,
        topics: List[str],
        consumer_config: ConsumerConfig,
        callback: Callable[[ConsumerRecord], None],
    ) -> None:
        """Background consumer loop for Redis subscriptions."""
        try:
            async for record in self.consume(topics, consumer_config):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(record)
                    else:
                        callback(record)
                except Exception as e:
                    logger.error(
                        "Error in Redis consumer callback",
                        event_id=record.event.event_id,
                        error=str(e),
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Redis consumer loop error", topics=topics, error=str(e))
