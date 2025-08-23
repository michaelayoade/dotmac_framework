"""
Adapters package for dotmac_core_events.

Provides adapter implementations for different event streaming backends:
- Redis Streams adapter
- Kafka adapter
- In-memory adapter (for testing)
- Database adapter (for outbox pattern)
"""

from .base import AdapterConfig, EventAdapter
from .kafka_adapter import KafkaAdapter, KafkaConfig
from .memory_adapter import MemoryAdapter, MemoryConfig
from .redis_adapter import RedisAdapter, RedisConfig

__all__ = [
    "EventAdapter",
    "AdapterConfig",
    "RedisAdapter",
    "RedisConfig",
    "KafkaAdapter",
    "KafkaConfig",
    "MemoryAdapter",
    "MemoryConfig",
]
