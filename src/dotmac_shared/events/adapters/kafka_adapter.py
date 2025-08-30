"""
Apache Kafka Event Adapter.

Provides Kafka implementation of the EventAdapter interface.
Uses aiokafka for high-throughput, distributed event streaming.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.errors import KafkaError

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = AIOKafkaConsumer = KafkaError = None

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


class KafkaConfig(AdapterConfig):
    """Configuration for Kafka event adapter."""

    # Kafka connection
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None

    # Producer settings
    acks: str = "all"  # Wait for all replicas
    retries: int = 3
    max_in_flight_requests_per_connection: int = 5
    enable_idempotence: bool = True
    compression_type: str = "gzip"

    # Consumer settings
    consumer_group_id: str = "dotmac-events"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = False
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 500

    @property
    def producer_config(self) -> Dict[str, Any]:
        """Get producer configuration."""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "security_protocol": self.security_protocol,
            "acks": self.acks,
            "retries": self.retries,
            "max_in_flight_requests_per_connection": self.max_in_flight_requests_per_connection,
            "enable_idempotence": self.enable_idempotence,
            "compression_type": self.compression_type,
        }

        if self.sasl_mechanism:
            config.update(
                {
                    "sasl_mechanism": self.sasl_mechanism,
                    "sasl_plain_username": self.sasl_plain_username,
                    "sasl_plain_password": self.sasl_plain_password,
                }
            )

        return config

    @property
    def consumer_config(self) -> Dict[str, Any]:
        """Get consumer configuration."""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "security_protocol": self.security_protocol,
            "group_id": self.consumer_group_id,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
            "session_timeout_ms": self.session_timeout_ms,
            "heartbeat_interval_ms": self.heartbeat_interval_ms,
            "max_poll_records": self.max_poll_records,
        }

        if self.sasl_mechanism:
            config.update(
                {
                    "sasl_mechanism": self.sasl_mechanism,
                    "sasl_plain_username": self.sasl_plain_username,
                    "sasl_plain_password": self.sasl_plain_password,
                }
            )

        return config


class KafkaEventAdapter(EventAdapter):
    """
    Apache Kafka event adapter.

    Provides high-throughput, distributed event streaming using Kafka with:
    - Partitioned topics for scalability
    - Consumer groups for load balancing
    - Configurable acknowledgment levels
    - Exactly-once semantics (when configured)
    """

    def __init__(
        self,
        config: Optional[KafkaConfig] = None,
        bootstrap_servers: Optional[str] = None,
    ):
        """Initialize Kafka adapter."""
        if not KAFKA_AVAILABLE:
            raise EventBusError(
                "Kafka adapter requires 'aiokafka' package: pip install aiokafka"
            )

        if config is None:
            if bootstrap_servers:
                config = KafkaConfig(
                    connection_string=bootstrap_servers,
                    bootstrap_servers=bootstrap_servers,
                )
            else:
                config = KafkaConfig()

        super().__init__(config)
        self.kafka_config = config

        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._admin_client = None

        logger.info(
            "Kafka event adapter initialized",
            bootstrap_servers=config.bootstrap_servers,
        )

    async def connect(self) -> None:
        """Connect to Kafka cluster."""
        try:
            # Create and start producer
            self._producer = AIOKafkaProducer(**self.kafka_config.producer_config)
            await self._producer.start()

            self._connected = True

            logger.info(
                "Connected to Kafka",
                bootstrap_servers=self.kafka_config.bootstrap_servers,
            )

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e))
            raise EventBusError(f"Failed to connect to Kafka: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Kafka."""
        try:
            # Stop all consumers
            for consumer in self._consumers.values():
                await consumer.stop()
            self._consumers.clear()

            # Stop producer
            if self._producer:
                await self._producer.stop()
                self._producer = None

            self._connected = False
            logger.info("Disconnected from Kafka")

        except Exception as e:
            logger.error("Error disconnecting from Kafka", error=str(e))

    async def publish(
        self, event: EventRecord, topic: Optional[str] = None
    ) -> PublishResult:
        """Publish event to Kafka topic."""
        if not self._connected or not self._producer:
            raise EventBusError("Kafka adapter not connected")

        try:
            target_topic = topic or event.topic or "default"

            # Create message
            message_key = None
            if event.partition_key:
                message_key = event.partition_key.encode()

            # Serialize event
            message_value = self._serialize_event(event)

            # Create headers
            headers = [
                ("event_id", event.event_id.encode()),
                ("event_type", event.event_type.encode()),
                ("tenant_id", (event.tenant_id or "").encode()),
                ("timestamp", datetime.utcnow().isoformat().encode()),
            ]

            # Send to Kafka
            record_metadata = await self._producer.send_and_wait(
                target_topic, value=message_value, key=message_key, headers=headers
            )

            result = PublishResult(
                event_id=event.event_id,
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=str(record_metadata.offset),
                timestamp=datetime.utcfromtimestamp(record_metadata.timestamp / 1000),
            )

            logger.debug(
                "Event published to Kafka",
                event_id=event.event_id,
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to publish event to Kafka",
                event_id=event.event_id,
                topic=topic,
                error=str(e),
            )
            raise EventBusError(f"Failed to publish event: {e}") from e

    async def publish_batch(
        self, events: List[EventRecord], topic: Optional[str] = None
    ) -> List[PublishResult]:
        """Publish multiple events to Kafka."""
        if not self._connected or not self._producer:
            raise EventBusError("Kafka adapter not connected")

        try:
            # Send all events
            futures = []
            for event in events:
                target_topic = topic or event.topic or "default"

                message_key = None
                if event.partition_key:
                    message_key = event.partition_key.encode()

                message_value = self._serialize_event(event)

                headers = [
                    ("event_id", event.event_id.encode()),
                    ("event_type", event.event_type.encode()),
                    ("tenant_id", (event.tenant_id or "").encode()),
                    ("timestamp", datetime.utcnow().isoformat().encode()),
                ]

                future = self._producer.send(
                    target_topic, value=message_value, key=message_key, headers=headers
                )
                futures.append((event, future))

            # Wait for all sends to complete
            results = []
            for event, future in futures:
                try:
                    record_metadata = await future
                    result = PublishResult(
                        event_id=event.event_id,
                        topic=record_metadata.topic,
                        partition=record_metadata.partition,
                        offset=str(record_metadata.offset),
                        timestamp=datetime.utcfromtimestamp(
                            record_metadata.timestamp / 1000
                        ),
                    )
                    results.append(result)
                except Exception as e:
                    # Individual event failed
                    result = PublishResult(
                        event_id=event.event_id,
                        topic=topic or "default",
                        success=False,
                        error=str(e),
                    )
                    results.append(result)

            logger.debug(
                "Event batch published to Kafka",
                batch_size=len(events),
                successful=len([r for r in results if r.success]),
            )

            return results

        except Exception as e:
            logger.error(
                "Failed to publish event batch to Kafka",
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
        """Subscribe to topics using Kafka consumer."""
        if not self._connected:
            raise EventBusError("Kafka adapter not connected")

        try:
            consumer_key = (
                f"{consumer_config.consumer_group}:{consumer_config.consumer_id}"
            )

            if consumer_key not in self._consumers:
                # Create consumer
                kafka_consumer_config = self.kafka_config.consumer_config.copy()
                kafka_consumer_config["group_id"] = consumer_config.consumer_group

                consumer = AIOKafkaConsumer(*topics, **kafka_consumer_config)

                await consumer.start()
                self._consumers[consumer_key] = consumer

                # Start background consumer task
                asyncio.create_task(
                    self._kafka_consumer_loop(consumer, consumer_config, callback)
                )

            logger.info(
                "Subscribed to Kafka topics",
                topics=topics,
                consumer_group=consumer_config.consumer_group,
            )

        except Exception as e:
            logger.error(
                "Failed to subscribe to Kafka topics", topics=topics, error=str(e)
            )
            raise EventBusError(f"Failed to subscribe: {e}") from e

    async def consume(
        self, topics: List[str], consumer_config: ConsumerConfig
    ) -> AsyncIterator[ConsumerRecord]:
        """Consume events from Kafka topics."""
        if not self._connected:
            raise EventBusError("Kafka adapter not connected")

        # Create consumer
        kafka_consumer_config = self.kafka_config.consumer_config.copy()
        kafka_consumer_config["group_id"] = consumer_config.consumer_group

        consumer = AIOKafkaConsumer(*topics, **kafka_consumer_config)

        try:
            await consumer.start()

            async for message in consumer:
                try:
                    # Deserialize event
                    event = self._deserialize_kafka_message(message)

                    consumer_record = ConsumerRecord(
                        event=event,
                        consumer_group=consumer_config.consumer_group,
                        consumer_id=consumer_config.consumer_id,
                        topic=message.topic,
                        partition=message.partition,
                        offset=str(message.offset),
                        timestamp=datetime.utcfromtimestamp(message.timestamp / 1000),
                        lag=None,  # Kafka lag calculation would require additional calls
                    )

                    yield consumer_record

                    # Manual commit if auto-commit is disabled
                    if not consumer_config.enable_auto_commit:
                        await consumer.commit()

                except Exception as e:
                    logger.error(
                        "Error processing Kafka message",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in Kafka consumer", topics=topics, error=str(e))
        finally:
            await consumer.stop()

    async def create_topic(self, topic_config: TopicConfig) -> bool:
        """Create Kafka topic (requires kafka-admin)."""
        try:
            # For now, assume topics are created externally or auto-created
            # Full implementation would use kafka-admin package
            logger.info(
                "Kafka topic creation not implemented - ensure topic exists",
                topic=topic_config.name,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to create Kafka topic", topic=topic_config.name, error=str(e)
            )
            return False

    async def delete_topic(self, topic_name: str) -> bool:
        """Delete Kafka topic (requires admin privileges)."""
        try:
            # Full implementation would use kafka-admin package
            logger.info("Kafka topic deletion not implemented", topic=topic_name)
            return False

        except Exception as e:
            logger.error("Failed to delete Kafka topic", topic=topic_name, error=str(e))
            return False

    async def list_topics(self) -> List[str]:
        """List Kafka topics."""
        if not self._connected or not self._producer:
            return []

        try:
            # Get cluster metadata
            cluster = self._producer.client.cluster
            await cluster.request_update()

            # Extract topic names
            topics = list(cluster.topics())
            return topics

        except Exception as e:
            logger.error("Failed to list Kafka topics", error=str(e))
            return []

    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> bool:
        """Commit offset for Kafka consumer."""
        try:
            # Find consumer for this group
            for consumer_key, consumer in self._consumers.items():
                if consumer_group in consumer_key:
                    from aiokafka.structs import TopicPartition

                    tp = TopicPartition(topic, partition)
                    await consumer.commit(
                        {tp: int(offset) + 1}
                    )  # Kafka expects next offset
                    return True

            return False

        except Exception as e:
            logger.error(
                "Failed to commit Kafka offset",
                consumer_group=consumer_group,
                topic=topic,
                partition=partition,
                error=str(e),
            )
            return False

    def _serialize_event(self, event: EventRecord) -> bytes:
        """Serialize EventRecord to bytes for Kafka."""
        try:
            event_dict = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "data": event.data,
                "metadata": event.metadata.model_dump(),
                "partition_key": event.partition_key,
                "tenant_id": event.tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return json.dumps(event_dict, default=str).encode()

        except Exception as e:
            logger.error(
                "Failed to serialize event", event_id=event.event_id, error=str(e)
            )
            raise

    def _deserialize_kafka_message(self, message) -> EventRecord:
        """Deserialize Kafka message to EventRecord."""
        try:
            # Parse JSON message
            event_dict = json.loads(message.value.decode())

            # Extract metadata
            metadata_dict = event_dict.get("metadata", {})
            metadata = EventMetadata(
                event_id=event_dict["event_id"],
                tenant_id=event_dict.get("tenant_id"),
                **metadata_dict,
            )

            # Create event record
            event = EventRecord(
                event_type=event_dict["event_type"],
                data=event_dict["data"],
                metadata=metadata,
                partition_key=event_dict.get("partition_key"),
                partition=message.partition,
                offset=str(message.offset),
                timestamp=datetime.utcfromtimestamp(message.timestamp / 1000),
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to deserialize Kafka message",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                error=str(e),
            )
            raise

    async def _kafka_consumer_loop(
        self,
        consumer: AIOKafkaConsumer,
        consumer_config: ConsumerConfig,
        callback: Callable[[ConsumerRecord], None],
    ) -> None:
        """Background consumer loop for Kafka subscriptions."""
        try:
            async for message in consumer:
                try:
                    event = self._deserialize_kafka_message(message)

                    consumer_record = ConsumerRecord(
                        event=event,
                        consumer_group=consumer_config.consumer_group,
                        consumer_id=consumer_config.consumer_id,
                        topic=message.topic,
                        partition=message.partition,
                        offset=str(message.offset),
                        timestamp=datetime.utcfromtimestamp(message.timestamp / 1000),
                    )

                    if asyncio.iscoroutinefunction(callback):
                        await callback(consumer_record)
                    else:
                        callback(consumer_record)

                    # Manual commit if needed
                    if not consumer_config.enable_auto_commit:
                        await consumer.commit()

                except Exception as e:
                    logger.error(
                        "Error in Kafka consumer callback",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Kafka consumer loop error", error=str(e))
