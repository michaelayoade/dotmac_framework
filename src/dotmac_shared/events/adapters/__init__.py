"""
Event streaming adapters for different backends.

Provides concrete implementations of the EventAdapter interface:
- MemoryEventAdapter: In-memory adapter for testing
- RedisEventAdapter: Redis Streams adapter for production
- KafkaEventAdapter: Apache Kafka adapter for high-throughput scenarios
"""

# Memory adapter (always available)
from .memory_adapter import MemoryConfig, MemoryEventAdapter

# Redis adapter with error handling
try:
    from .redis_adapter import RedisConfig, RedisEventAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"Redis event adapter not available: {e}")
    RedisEventAdapter = RedisConfig = None

# Kafka adapter with error handling
try:
    from .kafka_adapter import KafkaConfig, KafkaEventAdapter
except ImportError as e:
    import warnings

    warnings.warn(f"Kafka event adapter not available: {e}")
    KafkaEventAdapter = KafkaConfig = None

__all__ = [
    # Memory (always available)
    "MemoryEventAdapter",
    "MemoryConfig",
    # Redis (optional)
    "RedisEventAdapter",
    "RedisConfig",
    # Kafka (optional)
    "KafkaEventAdapter",
    "KafkaConfig",
]
