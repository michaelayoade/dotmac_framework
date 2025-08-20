"""
SDK package for dotmac_core_events.

Provides core SDKs for:
- Event Bus operations with Redis Streams and Kafka adapters
- Schema Registry with JSON Schema validation
- Transactional Outbox pattern implementation
"""

from .event_bus import EventBusSDK, EventMetadata, PublishResult
from .outbox import OutboxEvent, OutboxEventStatus, OutboxSDK
from .schema_registry import CompatibilityLevel, RegistrationResult, SchemaRegistrySDK

__all__ = [
    # Event Bus SDK
    "EventBusSDK",
    "EventMetadata",
    "PublishResult",

    # Schema Registry SDK
    "SchemaRegistrySDK",
    "CompatibilityLevel",
    "RegistrationResult",

    # Outbox SDK
    "OutboxSDK",
    "OutboxEvent",
    "OutboxEventStatus",
]
