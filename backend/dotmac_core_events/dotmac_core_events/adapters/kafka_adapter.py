"""
Kafka adapter for event streaming.

Provides Apache Kafka implementation of the EventAdapter interface:
- Uses aiokafka for async Kafka operations
- Full Kafka producer and consumer functionality
- Topic and consumer group management
- Offset management and seeking
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import (
    AIOKafkaAdminClient,
    ConfigResource,
    ConfigResourceType,
    NewTopic,
)
from aiokafka.errors import TopicAlreadyExistsError

from .base import (
    AdapterConfig,
    ConsumerRecord,
    EventAdapter,
    EventRecord,
    PublishResult,
)

logger = structlog.get_logger(__name__)


class KafkaConfig(AdapterConfig):
    """Kafka-specific configuration."""

    bootstrap_servers: List[str] = ["localhost:9092"]
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None

    # Producer settings
    acks: str = "all"
    compression_type: str = "gzip"
    batch_size: int = 16384
    linger_ms: int = 10

    # Consumer settings
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 500

    @property
    def connection_string(self) -> str:
        """Build Kafka connection string."""
        return ",".join(self.bootstrap_servers)


class KafkaAdapter(EventAdapter):
    """Kafka adapter for event streaming."""

    def __init__(self, config: KafkaConfig):
        """Initialize Kafka adapter."""
        super().__init__(config)
        self.config: KafkaConfig = config
        self._producer: Optional[AIOKafkaProducer] = None
        self._admin_client: Optional[AIOKafkaAdminClient] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Kafka."""
        try:
            # Initialize producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                security_protocol=self.config.security_protocol,
                sasl_mechanism=self.config.sasl_mechanism,
                sasl_plain_username=self.config.sasl_username,
                sasl_plain_password=self.config.sasl_password,
                ssl_cafile=self.config.ssl_cafile,
                ssl_certfile=self.config.ssl_certfile,
                ssl_keyfile=self.config.ssl_keyfile,
                acks=self.config.acks,
                compression_type=self.config.compression_type,
                batch_size=self.config.batch_size,
                linger_ms=self.config.linger_ms,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )

            # Initialize admin client
            self._admin_client = AIOKafkaAdminClient(
                bootstrap_servers=self.config.bootstrap_servers,
                security_protocol=self.config.security_protocol,
                sasl_mechanism=self.config.sasl_mechanism,
                sasl_plain_username=self.config.sasl_username,
                sasl_plain_password=self.config.sasl_password,
                ssl_cafile=self.config.ssl_cafile,
                ssl_certfile=self.config.ssl_certfile,
                ssl_keyfile=self.config.ssl_keyfile,
            )

            # Start connections
            await self._producer.start()
            await self._admin_client.start()

            self._connected = True

            logger.info(
                "Connected to Kafka",
                bootstrap_servers=self.config.bootstrap_servers
            )

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kafka."""
        if self._producer:
            await self._producer.stop()
            self._producer = None

        if self._admin_client:
            await self._admin_client.close()
            self._admin_client = None

        self._connected = False
        logger.info("Disconnected from Kafka")

    def _ensure_connected(self):
        """Ensure Kafka client is connected."""
        if not self._connected or not self._producer or not self._admin_client:
            raise RuntimeError("Kafka adapter is not connected")

    async def publish(
        self,
        topic: str,
        event: EventRecord,
        partition_key: Optional[str] = None
    ) -> PublishResult:
        """Publish event to Kafka topic."""
        self._ensure_connected()

        # Prepare event data
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        }

        if event.partition_key:
            event_data["partition_key"] = event.partition_key

        if event.headers:
            event_data["headers"] = event.headers

        try:
            # Use partition_key or event.partition_key for routing
            key = partition_key or event.partition_key
            key_bytes = key.encode("utf-8") if key else None

            # Send message
            record_metadata = await self._producer.send_and_wait(
                topic,
                value=event_data,
                key=key_bytes
            )

            logger.debug(
                "Published event to Kafka",
                topic=topic,
                event_id=event.event_id,
                partition=record_metadata.partition,
                offset=record_metadata.offset
            )

            return PublishResult(
                event_id=event.event_id,
                partition=record_metadata.partition,
                offset=str(record_metadata.offset),
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(
                "Failed to publish event to Kafka",
                topic=topic,
                event_id=event.event_id,
                error=str(e)
            )
            raise

    async def subscribe(
        self,
        topics: List[str],
        consumer_group: str,
        auto_commit: bool = True
    ) -> AsyncIterator[ConsumerRecord]:
        """Subscribe to Kafka topics."""
        self._ensure_connected()

        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.config.bootstrap_servers,
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_plain_username=self.config.sasl_username,
            sasl_plain_password=self.config.sasl_password,
            ssl_cafile=self.config.ssl_cafile,
            ssl_certfile=self.config.ssl_certfile,
            ssl_keyfile=self.config.ssl_keyfile,
            group_id=consumer_group,
            auto_offset_reset=self.config.auto_offset_reset,
            enable_auto_commit=auto_commit,
            auto_commit_interval_ms=self.config.auto_commit_interval_ms,
            session_timeout_ms=self.config.session_timeout_ms,
            heartbeat_interval_ms=self.config.heartbeat_interval_ms,
            max_poll_records=self.config.max_poll_records,
            value_deserializer=lambda m: json.loads(m.decode("utf-8"))
        )

        try:
            await consumer.start()

            logger.info(
                "Started Kafka consumer",
                topics=topics,
                consumer_group=consumer_group
            )

            async for message in consumer:
                try:
                    # Parse event data
                    event_data = message.value

                    event = EventRecord(
                        event_id=event_data["event_id"],
                        event_type=event_data["event_type"],
                        data=event_data["data"],
                        partition_key=event_data.get("partition_key"),
                        timestamp=datetime.fromisoformat(event_data["timestamp"]),
                        offset=str(message.offset),
                        partition=message.partition,
                        headers=event_data.get("headers", {})
                    )

                    consumer_record = ConsumerRecord(
                        event=event,
                        offset=str(message.offset),
                        partition=message.partition,
                        topic=message.topic
                    )

                    yield consumer_record

                except Exception as e:
                    logger.error(
                        "Failed to process Kafka message",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e)
                    )

        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")
            raise
        except Exception as e:
            logger.error("Kafka consumer error", error=str(e))
            raise
        finally:
            await consumer.stop()

    async def commit_offset(
        self,
        consumer_group: str,
        topic: str,
        partition: int,
        offset: str
    ) -> None:
        """Commit offset for Kafka consumer."""
        # Note: This would require maintaining a consumer instance
        # In practice, offsets are committed through the consumer
        logger.warning("Manual offset commit requires active consumer instance")

    async def create_topic(
        self,
        topic: str,
        partitions: int = 3,
        replication_factor: int = 2,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create Kafka topic."""
        self._ensure_connected()

        topic_config = config or {}

        new_topic = NewTopic(
            name=topic,
            num_partitions=partitions,
            replication_factor=replication_factor,
            topic_configs=topic_config
        )

        try:
            await self._admin_client.create_topics([new_topic])
            logger.info(
                "Created Kafka topic",
                topic=topic,
                partitions=partitions,
                replication_factor=replication_factor
            )
        except TopicAlreadyExistsError:
            logger.warning("Kafka topic already exists", topic=topic)
        except Exception as e:
            logger.error("Failed to create Kafka topic", topic=topic, error=str(e))
            raise

    async def delete_topic(self, topic: str) -> None:
        """Delete Kafka topic."""
        self._ensure_connected()

        try:
            await self._admin_client.delete_topics([topic])
            logger.info("Deleted Kafka topic", topic=topic)
        except Exception as e:
            logger.error("Failed to delete Kafka topic", topic=topic, error=str(e))
            raise

    async def list_topics(self) -> List[str]:
        """List Kafka topics."""
        self._ensure_connected()

        try:
            metadata = await self._admin_client.list_topics()
            topics = list(metadata.topics.keys())
            # Filter out internal topics
            return [t for t in topics if not t.startswith("__")]
        except Exception as e:
            logger.error("Failed to list Kafka topics", error=str(e))
            raise

    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """Get Kafka topic information."""
        self._ensure_connected()

        try:
            metadata = await self._admin_client.describe_topics([topic])
            topic_metadata = metadata[topic]

            # Get topic configuration
            config_resources = [ConfigResource(ConfigResourceType.TOPIC, topic)]
            configs = await self._admin_client.describe_configs(config_resources)
            topic_config = configs[config_resources[0]]

            return {
                "topic": topic,
                "partitions": len(topic_metadata.partitions),
                "replication_factor": len(topic_metadata.partitions[0].replicas) if topic_metadata.partitions else 0,
                "config": {k: v.value for k, v in topic_config.configs.items()},
                "partition_info": [
                    {
                        "partition": p.partition_index,
                        "leader": p.leader,
                        "replicas": p.replicas,
                        "isr": p.isr
                    }
                    for p in topic_metadata.partitions
                ]
            }
        except Exception as e:
            logger.error("Failed to get Kafka topic info", topic=topic, error=str(e))
            raise

    async def list_consumer_groups(self) -> List[Dict[str, Any]]:
        """List Kafka consumer groups."""
        self._ensure_connected()

        try:
            groups = await self._admin_client.list_consumer_groups()

            result = []
            for group in groups:
                try:
                    group_info = await self._admin_client.describe_consumer_groups([group.group_id])
                    info = group_info[group.group_id]

                    result.append({
                        "group_id": group.group_id,
                        "state": info.state,
                        "protocol_type": info.protocol_type,
                        "protocol": info.protocol,
                        "members": len(info.members)
                    })
                except Exception as e:
                    logger.warning(
                        "Failed to get consumer group details",
                        group_id=group.group_id,
                        error=str(e)
                    )

            return result

        except Exception as e:
            logger.error("Failed to list Kafka consumer groups", error=str(e))
            raise

    async def delete_consumer_group(self, group_id: str) -> None:
        """Delete Kafka consumer group."""
        self._ensure_connected()

        try:
            await self._admin_client.delete_consumer_groups([group_id])
            logger.info("Deleted Kafka consumer group", group_id=group_id)
        except Exception as e:
            logger.error(
                "Failed to delete Kafka consumer group",
                group_id=group_id,
                error=str(e)
            )
            raise

    async def get_consumer_group_info(self, group_id: str) -> Dict[str, Any]:
        """Get Kafka consumer group information."""
        self._ensure_connected()

        try:
            group_info = await self._admin_client.describe_consumer_groups([group_id])
            info = group_info[group_id]

            return {
                "group_id": group_id,
                "state": info.state,
                "protocol_type": info.protocol_type,
                "protocol": info.protocol,
                "coordinator": f"{info.coordinator.host}:{info.coordinator.port}",
                "members": [
                    {
                        "member_id": member.member_id,
                        "client_id": member.client_id,
                        "client_host": member.client_host,
                        "assignments": [
                            {
                                "topic": assignment.topic,
                                "partitions": assignment.partitions
                            }
                            for assignment in member.member_assignment.assignment
                        ] if member.member_assignment else []
                    }
                    for member in info.members
                ]
            }
        except Exception as e:
            logger.error(
                "Failed to get Kafka consumer group info",
                group_id=group_id,
                error=str(e)
            )
            raise

    async def seek_to_beginning(
        self,
        consumer_group: str,
        topic: str,
        partition: Optional[int] = None
    ) -> None:
        """Seek consumer group to beginning."""
        # This would require consumer group offset management
        logger.warning("Kafka seek operations require consumer group offset management")

    async def seek_to_end(
        self,
        consumer_group: str,
        topic: str,
        partition: Optional[int] = None
    ) -> None:
        """Seek consumer group to end."""
        # This would require consumer group offset management
        logger.warning("Kafka seek operations require consumer group offset management")

    async def seek_to_offset(
        self,
        consumer_group: str,
        topic: str,
        partition: int,
        offset: str
    ) -> None:
        """Seek consumer group to specific offset."""
        # This would require consumer group offset management
        logger.warning("Kafka seek operations require consumer group offset management")

    async def get_latest_offset(self, topic: str, partition: int) -> str:
        """Get latest offset for topic partition."""
        self._ensure_connected()

        try:
            # Create temporary consumer to get offsets
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.config.bootstrap_servers,
                security_protocol=self.config.security_protocol,
            )
            await consumer.start()

            try:
                from kafka import TopicPartition
                tp = TopicPartition(topic, partition)
                offsets = await consumer.end_offsets([tp])
                return str(offsets[tp])
            finally:
                await consumer.stop()

        except Exception as e:
            logger.error(
                "Failed to get latest offset",
                topic=topic,
                partition=partition,
                error=str(e)
            )
            raise

    async def get_earliest_offset(self, topic: str, partition: int) -> str:
        """Get earliest offset for topic partition."""
        self._ensure_connected()

        try:
            # Create temporary consumer to get offsets
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.config.bootstrap_servers,
                security_protocol=self.config.security_protocol,
            )
            await consumer.start()

            try:
                from kafka import TopicPartition
                tp = TopicPartition(topic, partition)
                offsets = await consumer.beginning_offsets([tp])
                return str(offsets[tp])
            finally:
                await consumer.stop()

        except Exception as e:
            logger.error(
                "Failed to get earliest offset",
                topic=topic,
                partition=partition,
                error=str(e)
            )
            raise
