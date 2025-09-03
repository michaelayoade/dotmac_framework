"""
DotMac Events - Transport-agnostic event bus package.

This package provides a unified interface for publishing and consuming events
across different message brokers and transports.

Example usage:

    from dotmac.events import Event, create_memory_bus, ConsumerOptions, run_consumer

    # Create an event bus
    bus = create_memory_bus()

    # Publish an event
    event = Event(topic="user.created", payload={"user_id": 123, "name": "John"})
    await bus.publish(event)

    # Subscribe to events
    async def handle_user_created(event):
        print(f"User created: {event.payload}")

    options = ConsumerOptions(max_retries=3)
    await run_consumer(bus, "user.created", handle_user_created, options)

For production use with Redis or Kafka:

    from dotmac.events import create_redis_bus, create_kafka_bus, RedisConfig, KafkaConfig

    # Redis Streams
    redis_config = RedisConfig(host="localhost", port=6379)
    bus = create_redis_bus(redis_config)

    # Kafka
    kafka_config = KafkaConfig(bootstrap_servers="localhost:9092")
    bus = create_kafka_bus(kafka_config)
"""

__version__ = "1.0.0"
__package_name__ = "dotmac-events"

# Re-export public API
from .api import *

# Import api module for __all__
from . import api

# Package metadata
__all__ = [
    "__version__",
    "__package_name__",
] + api.__all__