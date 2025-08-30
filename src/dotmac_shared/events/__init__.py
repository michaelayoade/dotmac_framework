"""
DotMac Events - Event-Driven Architecture Toolkit

This package provides comprehensive event streaming and processing capabilities:
- Event Bus with Redis and Kafka adapters
- Transactional Outbox pattern implementation
- Schema Registry for event validation
- Consumer groups and partition management
- Dead letter queue support
- Multi-tenant event isolation
"""

# Core imports with error handling
try:
    from .core.event_bus import EventBus
    from .core.models import (
        ConsumerRecord,
        EventBusError,
        EventMetadata,
        EventRecord,
        PublishError,
        PublishResult,
        SubscriptionError,
    )
    from .core.outbox import OutboxEvent, OutboxEventStatus, OutboxManager
    from .core.schema_registry import CompatibilityLevel, SchemaRegistry
except ImportError as e:
    import warnings

    warnings.warn(f"Events core components not available: {e}")
    # Set to None so code can check availability
    EventRecord = EventMetadata = PublishResult = None
    EventBus = OutboxManager = SchemaRegistry = None

# Adapter imports with graceful handling
try:
    from .adapters.kafka_adapter import KafkaEventAdapter
    from .adapters.memory_adapter import MemoryEventAdapter
    from .adapters.redis_adapter import RedisEventAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"Event adapters not fully available: {e}")
    RedisEventAdapter = KafkaEventAdapter = MemoryEventAdapter = None

# SDK convenience exports
try:
    from .sdk.event_bus_sdk import EventBusSDK
    from .sdk.outbox_sdk import OutboxSDK
    from .sdk.schema_registry_sdk import SchemaRegistrySDK
except ImportError as e:
    import warnings

    warnings.warn(f"Event SDKs not available: {e}")
    EventBusSDK = OutboxSDK = SchemaRegistrySDK = None

# Version and metadata
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core models
    "EventRecord",
    "EventMetadata",
    "PublishResult",
    "ConsumerRecord",
    # Core components
    "EventBus",
    "OutboxManager",
    "OutboxEvent",
    "OutboxEventStatus",
    "SchemaRegistry",
    "CompatibilityLevel",
    # Adapters
    "RedisEventAdapter",
    "KafkaEventAdapter",
    "MemoryEventAdapter",
    "EventBusSDK",
    "OutboxSDK",
    "SchemaRegistrySDK",
    # Exceptions
    "EventBusError",
    "PublishError",
    "SubscriptionError",
    # Version
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "event_bus": {
        "default_adapter": "memory",
        "batch_size": 100,
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_backoff_seconds": 1.0,
    },
    "redis": {
        "stream_maxlen": 10000,
        "consumer_group_name": "dotmac-events",
        "consumer_name": "dotmac-consumer",
        "claim_min_idle_ms": 60000,
        "claim_count": 10,
    },
    "kafka": {
        "bootstrap_servers": "localhost:9092",
        "consumer_group_id": "dotmac-events",
        "auto_offset_reset": "latest",
        "enable_auto_commit": False,
        "session_timeout_ms": 30000,
    },
    "outbox": {
        "dispatch_interval_seconds": 5,
        "batch_size": 50,
        "max_retries": 5,
        "dead_letter_threshold": 10,
        "cleanup_interval_hours": 24,
    },
    "schema_registry": {
        "cache_ttl_seconds": 3600,
        "compatibility_level": "BACKWARD",
        "subject_name_strategy": "TopicNameStrategy",
    },
}


def get_version():
    """Get package version."""
    return __version__


def get_default_config():
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()


# Quick setup functions for common use cases
def create_memory_event_bus() -> "EventBus":
    """Create an in-memory event bus for testing/development."""
    if not EventBus or not MemoryEventAdapter:
        raise ImportError("Event components not available")

    from .adapters.memory_adapter import MemoryEventAdapter

    adapter = MemoryEventAdapter()
    return EventBus(adapter=adapter)


def create_redis_event_bus(connection_string: str) -> "EventBus":
    """Create a Redis-backed event bus."""
    if not EventBus or not RedisEventAdapter:
        raise ImportError("Redis event components not available")

    from .adapters.redis_adapter import RedisEventAdapter

    adapter = RedisEventAdapter(connection_string=connection_string)
    return EventBus(adapter=adapter)


def create_kafka_event_bus(bootstrap_servers: str) -> "EventBus":
    """Create a Kafka-backed event bus."""
    if not EventBus or not KafkaEventAdapter:
        raise ImportError("Kafka event components not available")

    from .adapters.kafka_adapter import KafkaEventAdapter

    adapter = KafkaEventAdapter(bootstrap_servers=bootstrap_servers)
    return EventBus(adapter=adapter)
