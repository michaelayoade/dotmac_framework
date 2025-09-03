"""Kafka event bus adapter."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

from ..bus import ConsumeError, EventHandler, NotSupportedError, PublishError
from ..codecs.json_codec import JsonCodec
from ..message import Event, MessageCodec
from .base import AdapterConfig, AdapterMetadata, BaseAdapter

__all__ = [
    "KafkaEventBus",
    "KafkaConfig", 
    "create_kafka_bus",
]

logger = logging.getLogger(__name__)

# Optional Kafka import
try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = None  # type: ignore
    AIOKafkaConsumer = None  # type: ignore


class KafkaConfig(AdapterConfig):
    """Configuration for Kafka event bus."""
    
    def __init__(
        self,
        *,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "dotmac-events",
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: Optional[str] = None,
        sasl_username: Optional[str] = None,
        sasl_password: Optional[str] = None,
        ssl_context: Optional[Any] = None,
        api_version: str = "auto",
        auto_offset_reset: str = "latest",
        enable_auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        compression_type: str = "none",
        batch_size: int = 16384,
        linger_ms: int = 0,
        acks: str = "1",
        retries: int = 2147483647,
        codec: Optional[MessageCodec] = None,
        **kwargs: Any,
    ):
        """
        Initialize Kafka configuration.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            client_id: Client identifier
            security_protocol: Security protocol (PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL)
            sasl_mechanism: SASL mechanism (PLAIN, SCRAM-SHA-256, SCRAM-SHA-512)
            sasl_username: SASL username
            sasl_password: SASL password
            ssl_context: SSL context
            api_version: Kafka API version
            auto_offset_reset: Auto offset reset policy
            enable_auto_commit: Enable auto commit
            auto_commit_interval_ms: Auto commit interval
            compression_type: Producer compression (none, gzip, snappy, lz4, zstd)
            batch_size: Producer batch size
            linger_ms: Producer linger time
            acks: Producer acknowledgment level
            retries: Producer retry count
            codec: Message codec for serialization
            **kwargs: Base adapter config options
        """
        super().__init__(**kwargs)
        
        # Connection settings
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.security_protocol = security_protocol
        self.sasl_mechanism = sasl_mechanism
        self.sasl_username = sasl_username
        self.sasl_password = sasl_password
        self.ssl_context = ssl_context
        self.api_version = api_version
        
        # Consumer settings
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.auto_commit_interval_ms = auto_commit_interval_ms
        
        # Producer settings
        self.compression_type = compression_type
        self.batch_size = batch_size
        self.linger_ms = linger_ms
        self.acks = acks
        self.retries = retries
        
        # Codec
        self.codec = codec or JsonCodec.compact()
    
    def get_common_config(self) -> Dict[str, Any]:
        """Get common Kafka configuration."""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "security_protocol": self.security_protocol,
            "api_version": self.api_version,
        }
        
        if self.sasl_mechanism:
            config["sasl_mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl_plain_username"] = self.sasl_username
        if self.sasl_password:
            config["sasl_plain_password"] = self.sasl_password
        if self.ssl_context:
            config["ssl_context"] = self.ssl_context
        
        return config
    
    def get_producer_config(self) -> Dict[str, Any]:
        """Get Kafka producer configuration."""
        config = self.get_common_config()
        config.update({
            "compression_type": self.compression_type,
            "batch_size": self.batch_size,
            "linger_ms": self.linger_ms,
            "acks": self.acks,
            "retries": self.retries,
        })
        return config
    
    def get_consumer_config(self, group_id: str) -> Dict[str, Any]:
        """Get Kafka consumer configuration."""
        config = self.get_common_config()
        config.update({
            "group_id": group_id,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
            "auto_commit_interval_ms": self.auto_commit_interval_ms,
        })
        return config


class ConsumerInfo:
    """Information about a Kafka consumer."""
    
    def __init__(
        self,
        topic: str,
        group: str,
        handler: EventHandler,
        consumer: AIOKafkaConsumer,
        task: asyncio.Task[None],
    ):
        self.topic = topic
        self.group = group
        self.handler = handler
        self.consumer = consumer
        self.task = task
    
    async def stop(self) -> None:
        """Stop the consumer."""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.consumer:
            await self.consumer.stop()


class KafkaEventBus(BaseAdapter):
    """
    Kafka event bus implementation.
    
    Uses Apache Kafka for scalable message streaming with topics and
    consumer groups. Supports partitioning and at-least-once delivery.
    """
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize Kafka event bus.
        
        Args:
            config: Kafka-specific configuration
        """
        if not KAFKA_AVAILABLE:
            raise ImportError(
                "Kafka support not available. Install with: pip install 'dotmac-events[kafka]'"
            )
        
        super().__init__(config)
        self.config: KafkaConfig = config
        
        # Kafka producer
        self._producer: Optional[AIOKafkaProducer] = None
        
        # Active consumers
        self._consumers: List[ConsumerInfo] = []
        
        # Producer lock
        self._producer_lock = asyncio.Lock()
    
    @property
    def metadata(self) -> AdapterMetadata:
        """Get adapter metadata."""
        return AdapterMetadata(
            name="kafka",
            version="1.0.0", 
            description="Apache Kafka event bus with topics and consumer groups",
            supported_features={
                "publish",
                "subscribe",
                "consumer_groups",
                "partitioning",
                "at_least_once_delivery",
                "persistence",
                "scalability",
            },
        )
    
    async def _get_producer(self) -> AIOKafkaProducer:
        """Get or create Kafka producer."""
        if self._producer is None:
            async with self._producer_lock:
                if self._producer is None:
                    self._producer = AIOKafkaProducer(**self.config.get_producer_config())
                    await self._producer.start()
                    self._logger.info(f"Started Kafka producer for {self.config.bootstrap_servers}")
        
        return self._producer
    
    async def publish(
        self,
        event: Event,
        *,
        partition_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Publish an event to a Kafka topic.
        
        Args:
            event: Event to publish
            partition_key: Key for partitioning (uses event.key if not provided)
            headers: Additional headers to add to event
        """
        self._ensure_not_closed()
        
        try:
            # Add headers if provided
            if headers:
                event = event.with_headers(**headers)
            
            # Serialize event
            event_data = self.config.codec.encode(event)
            
            # Determine partition key
            key = partition_key or event.key
            key_bytes = key.encode("utf-8") if key else None
            
            # Build Kafka headers
            kafka_headers = []
            if event.metadata:
                for header_key, header_value in event.metadata.to_headers().items():
                    kafka_headers.append((header_key, header_value.encode("utf-8")))
            
            if event.headers:
                for header_key, header_value in event.headers.items():
                    kafka_headers.append((header_key, header_value.encode("utf-8")))
            
            # Add content type
            kafka_headers.append(("content_type", self.config.codec.content_type.encode("utf-8")))
            
            # Get producer and send
            producer = await self._get_producer()
            
            await producer.send(
                event.topic,
                value=event_data,
                key=key_bytes,
                headers=kafka_headers,
            )
            
            self._logger.debug(f"Published event to Kafka topic '{event.topic}': {event.id}")
            
        except Exception as e:
            if isinstance(e, PublishError):
                raise
            raise PublishError(f"Failed to publish event to Kafka: {e}", event=event, cause=e)
    
    async def subscribe(
        self,
        topic: str,
        handler: EventHandler,
        *,
        group: str = "default",
        concurrency: int = 1,
        auto_offset_reset: str = "latest",
        **kwargs: Any,
    ) -> None:
        """
        Subscribe to events on a Kafka topic.
        
        Args:
            topic: Topic to subscribe to
            handler: Event handler function
            group: Consumer group name
            concurrency: Number of concurrent consumers (ignored, handled by Kafka)
            auto_offset_reset: Where to start consuming ("earliest" or "latest")
            **kwargs: Additional Kafka consumer options
        """
        self._ensure_not_closed()
        
        try:
            # Create consumer configuration
            consumer_config = self.config.get_consumer_config(group)
            consumer_config["auto_offset_reset"] = auto_offset_reset
            consumer_config.update(kwargs)
            
            # Create consumer
            consumer = AIOKafkaConsumer(
                topic,
                **consumer_config,
            )
            
            # Start consumer
            await consumer.start()
            
            # Start consumer task
            task = asyncio.create_task(
                self._consume_loop(topic, group, handler, consumer)
            )
            
            # Track consumer
            consumer_info = ConsumerInfo(topic, group, handler, consumer, task)
            self._consumers.append(consumer_info)
            
            self._logger.info(f"Subscribed to Kafka topic '{topic}' with group '{group}'")
            
        except Exception as e:
            if isinstance(e, ConsumeError):
                raise
            raise ConsumeError(f"Failed to subscribe to Kafka topic '{topic}': {e}", topic=topic, cause=e)
    
    async def request(
        self,
        subject: str,
        payload: Dict[str, Any], 
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Kafka doesn't naturally support request-reply."""
        raise NotSupportedError("Request-reply pattern not supported by Kafka adapter")
    
    async def _consume_loop(
        self,
        topic: str,
        group: str,
        handler: EventHandler,
        consumer: AIOKafkaConsumer,
    ) -> None:
        """Main consumer loop for Kafka."""
        self._logger.info(f"Started Kafka consumer for topic '{topic}', group '{group}'")
        
        try:
            async for message in consumer:
                try:
                    # Decode Kafka message to Event
                    event = self._decode_kafka_message(message)
                    
                    # Handle event
                    await handler(event)
                    
                    self._logger.debug(
                        f"Processed Kafka message from topic '{topic}', "
                        f"partition {message.partition}, offset {message.offset}"
                    )
                    
                except Exception as e:
                    self._logger.error(
                        f"Error processing Kafka message from topic '{topic}': {e}",
                        exc_info=True,
                    )
                    # In a real implementation, this would go to retry/DLQ logic
        
        except asyncio.CancelledError:
            self._logger.info(f"Kafka consumer for topic '{topic}' cancelled")
        except Exception as e:
            self._logger.error(f"Kafka consumer for topic '{topic}' failed: {e}")
        
        self._logger.info(f"Kafka consumer for topic '{topic}' stopped")
    
    def _decode_kafka_message(self, message: Any) -> Event:
        """Decode a Kafka message to an Event."""
        # Decode event data
        event = self.config.codec.decode(message.value)
        
        # Extract headers from Kafka message
        headers = {}
        if message.headers:
            for header_key, header_value in message.headers:
                # Skip content_type header as it's handled by codec
                if header_key != "content_type":
                    headers[header_key] = header_value.decode("utf-8")
        
        # Add Kafka-specific metadata
        headers.update({
            "kafka_topic": message.topic,
            "kafka_partition": str(message.partition),
            "kafka_offset": str(message.offset),
        })
        
        if message.timestamp:
            headers["kafka_timestamp"] = str(message.timestamp)
        
        # Add headers to event
        if headers:
            event = event.with_headers(**headers)
        
        return event
    
    async def _close_impl(self) -> None:
        """Close Kafka event bus."""
        # Stop all consumers
        for consumer_info in self._consumers:
            await consumer_info.stop()
        
        self._consumers.clear()
        
        # Stop producer
        if self._producer:
            await self._producer.stop()
            self._producer = None


def create_kafka_bus(config: Optional[KafkaConfig] = None) -> KafkaEventBus:
    """
    Factory function to create a Kafka event bus.
    
    Args:
        config: Kafka configuration (uses defaults if None)
        
    Returns:
        Configured Kafka event bus
        
    Raises:
        ImportError: If Kafka support is not available
    """
    if not KAFKA_AVAILABLE:
        raise ImportError(
            "Kafka support not available. Install with: pip install 'dotmac-events[kafka]'"
        )
    
    return KafkaEventBus(config or KafkaConfig())