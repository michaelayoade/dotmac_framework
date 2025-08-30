"""
Core event system components.

Provides the fundamental building blocks for event-driven architecture:
- Event models and metadata
- Event bus interface
- Outbox pattern implementation
- Schema registry for validation
"""

from .event_bus import EventBus
from .models import (
    AdapterConfig,
    ConsumerRecord,
    EventBusError,
    EventMetadata,
    EventRecord,
    PublishError,
    PublishResult,
    SubscriptionError,
)
from .outbox import OutboxEvent, OutboxEventStatus, OutboxManager
from .schema_registry import CompatibilityLevel, SchemaRegistry

__all__ = [
    # Models
    "EventRecord",
    "EventMetadata",
    "PublishResult",
    "ConsumerRecord",
    "AdapterConfig",
    # Core components
    "EventBus",
    "OutboxManager",
    "OutboxEvent",
    "OutboxEventStatus",
    "SchemaRegistry",
    "CompatibilityLevel",
    # Exceptions
    "EventBusError",
    "PublishError",
    "SubscriptionError",
]
