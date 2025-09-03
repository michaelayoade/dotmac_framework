# Changelog

All notable changes to the dotmac-events package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-03

### Added

#### Core Features
- **Unified EventBus Interface**: Abstract event bus with consistent API across adapters
- **Event Message Structure**: Structured Event class with payload, headers, metadata, and tenant support
- **JSON Codec**: Stable JSON serialization with schema validation hooks
- **Transport Adapters**: Pluggable adapter system for different message brokers

#### Adapters
- **Memory Adapter**: In-memory event bus for development and testing
  - Consumer groups simulation
  - Request-reply pattern support
  - Event persistence option for debugging
  - Configurable queue sizes and concurrency
- **Redis Streams Adapter**: Production-ready Redis Streams integration
  - Consumer groups with at-least-once delivery
  - Automatic acknowledgments
  - Stream length management
  - Connection pooling and error handling
- **Kafka Adapter**: Apache Kafka integration for scalable messaging
  - Partition-aware publishing with custom keys
  - Consumer group management
  - Configurable serialization and compression
  - SASL/SSL security support

#### Reliability Features
- **Retry Logic**: Configurable retry with exponential backoff
- **Dead Letter Queue (DLQ)**: Automatic DLQ handling for failed events
- **Error Recovery**: Graceful error handling with categorized exceptions
- **Consumer Groups**: At-least-once delivery semantics

#### Observability
- **Metrics Integration**: Built-in metrics collection for events
- **Observability Hooks**: Pluggable hooks for metrics and tracing
- **DotMac Observability**: Native integration with dotmac-observability package
- **Performance Monitoring**: Duration tracking and error rate monitoring

#### Developer Experience
- **Type Hints**: Full type annotation support
- **Async/Await**: Native async support throughout
- **Context Managers**: Automatic resource cleanup
- **Comprehensive Testing**: Unit and integration tests

### Package Structure
```
dotmac-events/
├── src/dotmac/events/
│   ├── __init__.py              # Public API
│   ├── api.py                   # Internal API re-exports
│   ├── bus.py                   # EventBus interface and exceptions
│   ├── message.py               # Event and metadata structures
│   ├── consumer.py              # Consumer runner with retry logic
│   ├── dlq.py                   # Dead Letter Queue abstractions
│   ├── observability.py         # Observability hooks and integration
│   ├── codecs/
│   │   ├── __init__.py
│   │   └── json_codec.py        # JSON serialization codec
│   └── adapters/
│       ├── __init__.py
│       ├── base.py              # Adapter base classes
│       ├── memory.py            # In-memory adapter
│       ├── redis_streams.py     # Redis Streams adapter
│       └── kafka.py             # Kafka adapter
├── tests/                       # Comprehensive test suite
├── .github/workflows/ci.yml     # CI/CD pipeline
├── pyproject.toml              # Package configuration
├── README.md                   # Documentation
└── CHANGELOG.md                # This file
```

### Optional Dependencies
- `redis`: Redis Streams support (`redis[hiredis]>=5.0.0`)
- `kafka`: Apache Kafka support (`aiokafka>=0.10.0`)
- `avro`: Apache Avro codec support (`fastavro>=1.9.4`)
- `otel`: OpenTelemetry integration (`opentelemetry-api>=1.25.0`)
- `all`: All optional dependencies
- `dev`: Development and testing dependencies

### Default Event Structure
```python
Event(
    topic: str,                    # Required: event topic/subject
    payload: Dict[str, Any],       # Required: event data
    key: Optional[str] = None,     # Optional: partition/routing key
    headers: Optional[Dict[str, str]] = None,  # Optional: custom headers
    tenant_id: Optional[str] = None,           # Optional: multi-tenant ID
    metadata: Optional[EventMetadata] = None,  # Optional: event metadata
)
```

### Supported Event Patterns
- **Publish-Subscribe**: One-to-many event distribution
- **Consumer Groups**: Load balancing across multiple consumers  
- **Request-Reply**: Synchronous request-response (memory adapter)
- **Dead Letter Queue**: Failed event handling and reprocessing

### Adapters Comparison

| Feature | Memory | Redis Streams | Kafka |
|---------|--------|---------------|-------|
| **Persistence** | Optional | Yes | Yes |
| **Consumer Groups** | Simulated | Native | Native |
| **Partitioning** | No | No | Yes |
| **Scalability** | Single Process | Multi Process | Distributed |
| **Ordering** | FIFO | FIFO | Per Partition |
| **Request-Reply** | Yes | No | No |
| **Production Ready** | No | Yes | Yes |

### Configuration Examples

#### Memory Adapter
```python
from dotmac.events import create_memory_bus, MemoryConfig

config = MemoryConfig(
    max_queue_size=1000,
    enable_persistence=True,
)
bus = create_memory_bus(config)
```

#### Redis Streams Adapter
```python
from dotmac.events import create_redis_bus, RedisConfig

config = RedisConfig(
    host="localhost",
    port=6379,
    max_stream_length=10000,
    prefetch_count=10,
)
bus = create_redis_bus(config)
```

#### Kafka Adapter
```python
from dotmac.events import create_kafka_bus, KafkaConfig

config = KafkaConfig(
    bootstrap_servers="localhost:9092",
    acks="all",
    compression_type="snappy",
)
bus = create_kafka_bus(config)
```

### Retry and DLQ Configuration
```python
from dotmac.events import ConsumerOptions, create_exponential_retry_options

# Simple retry
options = ConsumerOptions(
    max_retries=3,
    backoff_base_ms=1000,
    dlq_topic="failed.events",
)

# Exponential backoff
options = create_exponential_retry_options(
    max_retries=5,
    base_delay_ms=100,
    max_delay_ms=30000,
)
```

### Observability Integration
```python
from dotmac.events import create_dotmac_observability_hooks

# Automatic metrics collection
hooks = create_dotmac_observability_hooks(
    metrics_registry=metrics_registry,
    tenant_metrics=tenant_metrics,
)

# Metrics collected:
# - events_published_total
# - events_consumed_total  
# - event_publish_duration_seconds
# - event_consume_duration_seconds
# - events_retried_total
# - events_dlq_total
```

### Testing Support
- **Memory Adapter**: Perfect for unit testing
- **Test Utilities**: Helpers for async testing
- **Integration Tests**: Redis and Kafka integration tests
- **CI/CD Pipeline**: Multi-Python version testing with service dependencies

### Migration Support
- **Backward Compatibility**: Migration shims for dotmac_shared.events
- **Deprecation Warnings**: Clear migration guidance
- **API Compatibility**: Smooth transition path

### Performance Optimizations
- **Connection Pooling**: Efficient resource management
- **Batch Processing**: Configurable batch sizes where supported
- **Compression**: Optional compression for Kafka
- **Prefetching**: Configurable message prefetching

### Security Features
- **SASL/SSL Support**: Kafka security protocols
- **Connection Security**: Redis AUTH and SSL support
- **Header Validation**: Safe header handling
- **Input Sanitization**: Payload validation hooks

### Documentation
- **Comprehensive README**: Usage examples and configuration guides
- **API Documentation**: Type hints and docstrings
- **Integration Examples**: Real-world usage patterns
- **Performance Tuning**: Optimization guidance

### CI/CD Features
- **Multi-Python Support**: Python 3.10, 3.11, 3.12
- **Service Testing**: Redis and Kafka service integration
- **Security Scanning**: Bandit and safety checks
- **Coverage Reporting**: Codecov integration
- **Build Artifacts**: Automated package building

### Initial Release Notes
This is the initial release of the dotmac-events package, extracted and enhanced from the DotMac Framework's event handling components. The package provides a production-ready, transport-agnostic event bus system with enterprise features including:

- Multi-adapter support (Memory, Redis Streams, Kafka)
- Automatic retry logic with exponential backoff
- Dead Letter Queue handling for failed events
- Built-in observability and metrics collection
- Consumer group support for scalable processing
- Type-safe event structures with metadata support

The package is designed for easy adoption in both development and production environments, with adapters ranging from simple in-memory queues for testing to distributed systems like Apache Kafka for high-scale production deployments.

### Breaking Changes
- New package name: `dotmac-events` (extracted from `dotmac-shared`)
- Updated import paths: `from dotmac.events import ...`
- New Event structure with typed fields and metadata
- Adapter-based architecture replacing direct broker clients

### Deprecations
- `dotmac_shared.events` module is deprecated and will be removed in next minor release
- Legacy event publishing patterns are deprecated in favor of structured Events
- Direct Redis/Kafka client usage is deprecated in favor of adapter pattern

### Security
- Safe serialization with input validation
- Secure connection handling for Redis and Kafka
- Header sanitization to prevent injection attacks
- Credential management best practices