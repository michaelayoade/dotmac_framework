# DotMac Events

A transport-agnostic event bus package for the DotMac Framework, providing unified interfaces for publishing and consuming events across different message brokers.

[![PyPI version](https://badge.fury.io/py/dotmac-events.svg)](https://badge.fury.io/py/dotmac-events)
[![Python Support](https://img.shields.io/pypi/pyversions/dotmac-events.svg)](https://pypi.org/project/dotmac-events/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🚌 **Unified EventBus Interface**: Consistent API across different message brokers
- 🔌 **Pluggable Adapters**: Support for Redis Streams, Kafka, and in-memory transports
- 📝 **Typed Event Schemas**: Structured event definitions with JSON codec
- ♻️ **Retry & DLQ**: Automatic retry with exponential backoff and Dead Letter Queues
- 👥 **Consumer Groups**: At-least-once delivery with consumer group semantics
- 📊 **Observability**: Built-in metrics and tracing integration
- 🔒 **Production Ready**: Robust error handling and graceful degradation

## Quick Start

### Installation

```bash
# Base installation (memory adapter only)
pip install dotmac-events

# With Redis Streams support
pip install "dotmac-events[redis]"

# With Kafka support
pip install "dotmac-events[kafka]"

# With all adapters and features
pip install "dotmac-events[all]"
```

### Basic Usage

```python
import asyncio
from dotmac.events import Event, create_memory_bus, ConsumerOptions, run_consumer

async def main():
    # Create event bus
    bus = create_memory_bus()
    
    # Define event handler
    async def handle_user_created(event):
        print(f"User created: {event.payload}")
    
    # Subscribe to events
    options = ConsumerOptions(max_retries=3)
    await run_consumer(bus, "user.created", handle_user_created, options)
    
    # Publish an event
    event = Event(
        topic="user.created",
        payload={"user_id": 123, "name": "John Doe", "email": "john@example.com"},
        key="user-123",
        tenant_id="acme-corp"
    )
    await bus.publish(event)
    
    # Keep running
    await asyncio.sleep(1)
    await bus.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Adapters

### Memory Adapter (Development/Testing)

```python
from dotmac.events import create_memory_bus, MemoryConfig

# Basic memory bus
bus = create_memory_bus()

# With configuration
config = MemoryConfig(max_queue_size=1000, enable_persistence=True)
bus = create_memory_bus(config)
```

### Redis Streams Adapter

```python
from dotmac.events import create_redis_bus, RedisConfig

# Basic Redis configuration
config = RedisConfig(host="localhost", port=6379, db=0)
bus = create_redis_bus(config)

# Advanced configuration
config = RedisConfig(
    url="redis://localhost:6379/0",
    max_stream_length=10000,
    consumer_timeout=5.0,
    prefetch_count=10,
)
bus = create_redis_bus(config)
```

### Kafka Adapter

```python
from dotmac.events import create_kafka_bus, KafkaConfig

# Basic Kafka configuration
config = KafkaConfig(bootstrap_servers="localhost:9092")
bus = create_kafka_bus(config)

# Production configuration
config = KafkaConfig(
    bootstrap_servers="kafka1:9092,kafka2:9092,kafka3:9092",
    security_protocol="SASL_SSL",
    sasl_mechanism="SCRAM-SHA-256",
    sasl_username="your-username",
    sasl_password="your-password",
    acks="all",
    compression_type="snappy",
)
bus = create_kafka_bus(config)
```

## Event Structure

```python
from dotmac.events import Event, EventMetadata

# Basic event
event = Event(
    topic="order.created",
    payload={"order_id": "12345", "amount": 99.99},
)

# Full event with metadata
event = Event(
    topic="user.updated",
    payload={"user_id": 123, "changes": {"email": "new@example.com"}},
    key="user-123",                    # For partitioning
    headers={"source": "user-service"},  # Custom headers
    tenant_id="acme-corp",             # Multi-tenant support
)

# Access event properties
print(f"Event ID: {event.id}")
print(f"Timestamp: {event.timestamp}")
print(f"Topic: {event.topic}")
```

## Consumer Groups and Retry Logic

```python
from dotmac.events import ConsumerOptions, create_exponential_retry_options

# Basic consumer options
options = ConsumerOptions(
    max_retries=5,
    backoff_base_ms=1000,
    dlq_topic="failed.events",
)

# Exponential backoff
options = create_exponential_retry_options(
    max_retries=3,
    base_delay_ms=100,
    max_delay_ms=30000,
)

# Subscribe with options
await run_consumer(
    bus, 
    "order.events", 
    handle_order, 
    options,
    group="order-processor",
    concurrency=5
)
```

## Dead Letter Queue (DLQ)

```python
from dotmac.events import SimpleDLQ, create_dlq_consumer, log_dlq_entry

# Basic DLQ handling
async def process_failed_event(dlq_entry):
    print(f"Failed event: {dlq_entry.original_topic}")
    print(f"Error: {dlq_entry.error}")
    print(f"Retry count: {dlq_entry.retry_count}")

# Start DLQ consumer
dlq_consumer = await create_dlq_consumer(
    bus=bus,
    dlq_topic="orders.DLQ",
    handler=process_failed_event,
    group="dlq-processor"
)
```

## Observability Integration

### Basic Metrics

```python
from dotmac.events import create_default_hooks

# Enable basic metrics and logging
hooks = create_default_hooks()
```

### DotMac Observability Integration

```python
from dotmac.events import create_dotmac_observability_hooks
from dotmac.observability import initialize_metrics_registry, initialize_tenant_metrics

# Set up observability
metrics_registry = initialize_metrics_registry("event-service")
tenant_metrics = initialize_tenant_metrics("event-service", metrics_registry)

# Create hooks
hooks = create_dotmac_observability_hooks(
    metrics_registry=metrics_registry,
    tenant_metrics=tenant_metrics,
)

# Metrics will be automatically recorded for:
# - events_published_total
# - events_consumed_total  
# - event_publish_duration_seconds
# - event_consume_duration_seconds
# - events_retried_total
# - events_dlq_total
```

## Advanced Usage

### Custom Codecs

```python
from dotmac.events import JsonCodec

# Custom JSON codec with schema validation
def validate_schema(topic: str, payload: dict) -> None:
    if topic == "user.created" and "user_id" not in payload:
        raise ValueError("user_id is required")

codec = JsonCodec.with_schema_validation(validate_schema)
```

### Request-Reply Pattern (Memory Adapter)

```python
# Set up reply handler
async def handle_request(event):
    if event.topic == "calculate.sum":
        result = sum(event.payload["numbers"])
        
        # Reply automatically handled by memory adapter
        return {"result": result}

await bus.subscribe("calculate.sum", handle_request)

# Send request
response = await bus.request(
    "calculate.sum",
    {"numbers": [1, 2, 3, 4, 5]},
    timeout=5.0
)
print(f"Sum: {response['result']}")  # Sum: 15
```

### Batch Processing

```python
async def batch_handler(events):
    """Process events in batches for efficiency."""
    print(f"Processing batch of {len(events)} events")
    
    for event in events:
        # Process each event
        await process_event(event)

# Note: Batch processing depends on adapter implementation
# Memory and Redis adapters support individual event processing
# Kafka adapter naturally supports batch consumption
```

## Configuration Examples

### Development Environment

```python
from dotmac.events import create_memory_bus, MemoryConfig

# Memory bus with persistence for debugging
config = MemoryConfig(
    max_queue_size=1000,
    enable_persistence=True,  # Keep event history
)
bus = create_memory_bus(config)
```

### Production Environment with Redis

```python
from dotmac.events import create_redis_bus, RedisConfig, ConsumerOptions

# Production Redis configuration
config = RedisConfig(
    url="redis://redis-cluster.internal:6379/0",
    max_stream_length=100000,
    consumer_timeout=30.0,
    prefetch_count=50,
    connection_timeout=10.0,
    max_connections=20,
)

bus = create_redis_bus(config)

# Production consumer options
options = ConsumerOptions(
    max_retries=5,
    backoff_base_ms=1000,
    backoff_multiplier=2.0,
    backoff_max_delay_ms=60000,  # 1 minute max delay
    dlq_topic="production.dlq",
)
```

### Production Environment with Kafka

```python
from dotmac.events import create_kafka_bus, KafkaConfig

# Production Kafka configuration
config = KafkaConfig(
    bootstrap_servers="kafka1:9092,kafka2:9092,kafka3:9092",
    security_protocol="SASL_SSL",
    sasl_mechanism="SCRAM-SHA-256",
    sasl_username="event-service",
    sasl_password="secure-password",
    acks="all",                    # Wait for all replicas
    retries=2147483647,           # Infinite retries
    compression_type="snappy",     # Compression
    batch_size=32768,             # 32KB batches
    linger_ms=10,                 # Batch delay
)

bus = create_kafka_bus(config)
```

## Error Handling

### Graceful Degradation

```python
async def resilient_handler(event):
    try:
        # Primary processing
        await primary_processor(event)
    except CriticalError:
        # Re-raise critical errors for retry/DLQ
        raise
    except NonCriticalError as e:
        # Log and continue for non-critical errors
        logger.warning(f"Non-critical error: {e}")
        await fallback_processor(event)

# Configure retry only for specific exceptions
from dotmac.events.consumer import RetryPolicy

policy = RetryPolicy(
    max_retries=3,
    retry_on_exceptions=(CriticalError, TimeoutError),
)
```

### Monitoring Failed Events

```python
from dotmac.events import create_dlq_consumer, alert_on_dlq_entry

# Alert on DLQ events
await create_dlq_consumer(
    bus=bus,
    dlq_topic="critical.events.DLQ",
    handler=alert_on_dlq_entry,  # Built-in alerting
    group="alert-processor"
)

# Custom DLQ monitoring
async def monitor_failures(dlq_entry):
    # Send to monitoring system
    await monitoring.record_failure(
        topic=dlq_entry.original_topic,
        error=dlq_entry.error,
        tenant_id=dlq_entry.original_event.tenant_id,
    )
    
    # Auto-reprocess after delay
    if dlq_entry.retry_count < 10:
        await schedule_reprocess(dlq_entry, delay_minutes=30)
```

## Testing

### Unit Testing with Memory Adapter

```python
import pytest
from dotmac.events import create_memory_bus, Event

@pytest.mark.asyncio
async def test_event_processing():
    bus = create_memory_bus()
    processed_events = []
    
    async def handler(event):
        processed_events.append(event)
    
    await bus.subscribe("test.topic", handler)
    
    # Publish test event
    event = Event(topic="test.topic", payload={"test": "data"})
    await bus.publish(event)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    assert len(processed_events) == 1
    assert processed_events[0].payload["test"] == "data"
    
    await bus.close()
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_integration():
    config = RedisConfig(host="localhost", port=6379)
    bus = create_redis_bus(config)
    
    # Test full publish-consume cycle
    received = []
    
    async def handler(event):
        received.append(event)
    
    await bus.subscribe("integration.test", handler, group="test-group")
    
    event = Event(topic="integration.test", payload={"integration": True})
    await bus.publish(event)
    
    # Wait for Redis processing
    await asyncio.sleep(1.0)
    
    assert len(received) == 1
    assert received[0].payload["integration"] is True
    
    await bus.close()
```

## Migration from Legacy Systems

If you're migrating from `dotmac_shared.events`:

### Before
```python
from dotmac_shared.events import EventBus, Event

bus = EventBus("redis://localhost:6379")
await bus.publish("topic", {"data": "value"})
```

### After
```python
from dotmac.events import create_redis_bus, RedisConfig, Event

config = RedisConfig(host="localhost", port=6379)
bus = create_redis_bus(config)

event = Event(topic="topic", payload={"data": "value"})
await bus.publish(event)
```

## Performance Considerations

### Throughput Optimization

- **Kafka**: Use batch processing and tune `batch_size`, `linger_ms`
- **Redis**: Configure `prefetch_count` and `max_stream_length`
- **Memory**: Set appropriate `max_queue_size` and concurrency levels

### Memory Usage

- Enable stream length limits in Redis (`max_stream_length`)
- Use compression in Kafka (`compression_type`)
- Disable persistence in memory adapter for production

### Latency Optimization

- Reduce `linger_ms` in Kafka for lower latency
- Increase `prefetch_count` in Redis for better throughput
- Use appropriate `concurrency` levels for consumers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/dotmac-framework/dotmac-events
cd dotmac-events
pip install -e ".[dev,all]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📖 Documentation: [https://docs.dotmac.com/events](https://docs.dotmac.com/events)
- 🐛 Issues: [GitHub Issues](https://github.com/dotmac-framework/dotmac-events/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/dotmac-framework/dotmac-events/discussions)