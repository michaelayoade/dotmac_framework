"""
Refactored Kafka components with single responsibilities.
Extracted from monolithic KafkaAdapter class.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
from kafka import TopicPartition

from .base import ConsumerRecord, EventRecord, PublishResult

logger = structlog.get_logger(__name__)


class KafkaConnectionManager:
    """Manages Kafka connections and client lifecycle."""

    def __init__(self, config):
        """  Init   operation."""
        self.config = config
        self._producer: Optional[AIOKafkaProducer] = None
        self._admin_client: Optional[AIOKafkaAdminClient] = None
        self._connected = False

    async def connect(self) -> None:
        """Establish Kafka connections."""
        if self._connected:
            return

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
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
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

            # Start clients
            await self._producer.start()

            self._connected = True
            logger.info(
                "Kafka connection established", servers=self.config.bootstrap_servers
            )

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e))
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Close all Kafka connections."""
        try:
            if self._producer:
                await self._producer.stop()
                self._producer = None

            if self._admin_client:
                await self._admin_client.close()
                self._admin_client = None

            self._connected = False
            logger.info("Kafka connections closed")

        except Exception as e:
            logger.warning("Error during Kafka disconnect", error=str(e))

    @property
    def is_connected(self) -> bool:
        """Check if connected to Kafka."""
        return self._connected

    @property
    def producer(self) -> AIOKafkaProducer:
        """Get producer instance."""
        if not self._connected or not self._producer:
            raise RuntimeError("Kafka not connected")
        return self._producer

    @property
    def admin_client(self) -> AIOKafkaAdminClient:
        """Get admin client instance."""
        if not self._admin_client:
            raise RuntimeError("Kafka admin client not available")
        return self._admin_client


class KafkaProducerService:
    """Handles Kafka message production."""

    def __init__(self, connection_manager: KafkaConnectionManager):
        """  Init   operation."""
        self.connection_manager = connection_manager

    async def publish_event(self, event: EventRecord) -> PublishResult:
        """Publish event to Kafka topic."""
        try:
            producer = self.connection_manager.producer

            # Prepare message data
            message_data = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "data": event.data,
                "partition_key": event.partition_key,
                "timestamp": event.timestamp.isoformat(),
                "headers": event.headers or {},
            }

            # Send message
            result = await producer.send_and_wait(
                topic=event.event_type,
                value=message_data,
                key=(
                    event.partition_key.encode("utf-8") if event.partition_key else None
                ),
            )

            logger.debug(
                "Event published to Kafka",
                event_id=event.event_id,
                topic=event.event_type,
                partition=result.partition,
                offset=result.offset,
            )

            return PublishResult(
                success=True,
                message_id=f"{result.partition}:{result.offset}",
                offset=str(result.offset),
                partition=result.partition,
            )

        except Exception as e:
            logger.error(
                "Failed to publish event to Kafka",
                event_id=event.event_id,
                event_type=event.event_type,
                error=str(e),
            )

            return PublishResult(success=False, error=str(e))


class KafkaConsumerService:
    """Handles Kafka message consumption."""

    def __init__(self, connection_manager: KafkaConnectionManager):
        """  Init   operation."""
        self.connection_manager = connection_manager

    async def consume_events(
        self, topics: List[str], consumer_group: str, auto_commit: bool = True
    ) -> AsyncIterator[ConsumerRecord]:
        """Consume events from Kafka topics."""
        consumer = self._create_consumer(topics, consumer_group, auto_commit)

        try:
            await consumer.start()

            logger.info(
                "Started Kafka consumer", topics=topics, consumer_group=consumer_group
            )

            async for message in consumer:
                try:
                    consumer_record = self._parse_message(message)
                    yield consumer_record

                except Exception as e:
                    logger.error(
                        "Failed to process Kafka message",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                    )

        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")
            raise
        except Exception as e:
            logger.error("Kafka consumer error", error=str(e))
            raise
        finally:
            await consumer.stop()

    def _create_consumer(
        self, topics: List[str], consumer_group: str, auto_commit: bool
    ) -> AIOKafkaConsumer:
        """Create Kafka consumer with proper configuration."""
        return AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.connection_manager.config.bootstrap_servers,
            security_protocol=self.connection_manager.config.security_protocol,
            sasl_mechanism=self.connection_manager.config.sasl_mechanism,
            sasl_plain_username=self.connection_manager.config.sasl_username,
            sasl_plain_password=self.connection_manager.config.sasl_password,
            ssl_cafile=self.connection_manager.config.ssl_cafile,
            ssl_certfile=self.connection_manager.config.ssl_certfile,
            ssl_keyfile=self.connection_manager.config.ssl_keyfile,
            group_id=consumer_group,
            auto_offset_reset=self.connection_manager.config.auto_offset_reset,
            enable_auto_commit=auto_commit,
            auto_commit_interval_ms=self.connection_manager.config.auto_commit_interval_ms,
            session_timeout_ms=self.connection_manager.config.session_timeout_ms,
            heartbeat_interval_ms=self.connection_manager.config.heartbeat_interval_ms,
            max_poll_records=self.connection_manager.config.max_poll_records,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

    def _parse_message(self, message) -> ConsumerRecord:
        """Parse Kafka message into ConsumerRecord."""
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
            headers=event_data.get("headers", {}),
        )

        return ConsumerRecord(
            event=event,
            offset=str(message.offset),
            partition=message.partition,
            topic=message.topic,
        )


class KafkaTopicManager:
    """Handles Kafka topic management operations."""

    def __init__(self, connection_manager: KafkaConnectionManager):
        """  Init   operation."""
        self.connection_manager = connection_manager

    async def create_topic(
        self,
        topic: str,
        partitions: int = 3,
        replication_factor: int = 2,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create Kafka topic."""
        try:
            admin_client = self.connection_manager.admin_client
            topic_config = config or {}

            new_topic = NewTopic(
                name=topic,
                num_partitions=partitions,
                replication_factor=replication_factor,
                topic_configs=topic_config,
            )

            await admin_client.create_topics([new_topic], validate_only=False)

            logger.info(
                "Kafka topic created",
                topic=topic,
                partitions=partitions,
                replication_factor=replication_factor,
            )

        except TopicAlreadyExistsError:
            logger.warning("Kafka topic already exists", topic=topic)
        except Exception as e:
            logger.error("Failed to create Kafka topic", topic=topic, error=str(e))
            raise

    async def delete_topic(self, topic: str) -> None:
        """Delete Kafka topic."""
        try:
            admin_client = self.connection_manager.admin_client
            await admin_client.delete_topics([topic])

            logger.info("Kafka topic deleted", topic=topic)

        except Exception as e:
            logger.error("Failed to delete Kafka topic", topic=topic, error=str(e))
            raise

    async def list_topics(self) -> Dict[str, Any]:
        """List Kafka topics."""
        try:
            admin_client = self.connection_manager.admin_client
            metadata = await admin_client.list_topics()

            return {
                "topics": list(metadata.topics.keys()),
                "brokers": [
                    {"id": broker.nodeId, "host": broker.host, "port": broker.port}
                    for broker in metadata.brokers
                ],
            }

        except Exception as e:
            logger.error("Failed to list Kafka topics", error=str(e))
            raise


class KafkaOffsetManager:
    """Handles Kafka offset management operations."""

    def __init__(self, connection_manager: KafkaConnectionManager):
        """  Init   operation."""
        self.connection_manager = connection_manager

    async def get_latest_offset(self, topic: str, partition: int) -> str:
        """Get latest offset for topic partition."""
        try:
            # Create temporary consumer to get offsets
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.connection_manager.config.bootstrap_servers,
                security_protocol=self.connection_manager.config.security_protocol,
            )
            await consumer.start()

            try:
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
                error=str(e),
            )
            raise

    async def get_earliest_offset(self, topic: str, partition: int) -> str:
        """Get earliest offset for topic partition."""
        try:
            # Create temporary consumer to get offsets
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.connection_manager.config.bootstrap_servers,
                security_protocol=self.connection_manager.config.security_protocol,
            )
            await consumer.start()

            try:
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
                error=str(e),
            )
            raise

    async def commit_offset(
        self, consumer_group: str, topic: str, partition: int, offset: str
    ) -> None:
        """Commit offset for Kafka consumer."""
        # Note: This would require maintaining a consumer instance
        # In practice, offsets are committed through the consumer
        logger.warning("Manual offset commit requires active consumer instance")


class KafkaMonitoringService:
    """Handles Kafka monitoring and health checks."""

    def __init__(self, connection_manager: KafkaConnectionManager):
        """  Init   operation."""
        self.connection_manager = connection_manager

    async def get_consumer_group_info(self, group_id: str) -> Dict[str, Any]:
        """Get Kafka consumer group information."""
        try:
            admin_client = self.connection_manager.admin_client

            # Get consumer group description
            descriptions = await admin_client.describe_consumer_groups([group_id])
            info = descriptions[group_id]

            return {
                "group_id": group_id,
                "state": info.state,
                "protocol_type": info.protocol_type,
                "protocol": info.protocol,
                "members": [
                    {
                        "member_id": member.member_id,
                        "client_id": member.client_id,
                        "client_host": member.client_host,
                        "assignment": (
                            [
                                f"{tp.topic}:{tp.partition}"
                                for tp in member.member_assignment.assignment()
                            ]
                            if member.member_assignment
                            else []
                        ),
                    }
                    for member in info.members
                ],
            }
        except Exception as e:
            logger.error(
                "Failed to get Kafka consumer group info",
                group_id=group_id,
                error=str(e),
            )
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform Kafka health check."""
        try:
            if not self.connection_manager.is_connected:
                return {"healthy": False, "error": "Not connected to Kafka"}

            # Try to list topics as a health check
            topics_info = await self.connection_manager.admin_client.list_topics()

            return {
                "healthy": True,
                "brokers_count": len(topics_info.brokers),
                "topics_count": len(topics_info.topics),
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}
