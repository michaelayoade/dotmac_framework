# Dotmac Core Events

A production-ready event streaming platform with multi-tenant safety, observability, and extensible adapters for Redis Streams, Apache Kafka, and in-memory backends.

## Features

- **Multi-Tenant Safe**: Complete tenant isolation at all levels
- **Multiple Adapters**: Redis Streams, Apache Kafka, and in-memory backends
- **Schema Registry**: JSON Schema validation with versioning and compatibility checking
- **Transactional Outbox**: Reliable event publishing with database integration
- **REST API**: Complete HTTP API for event operations
- **Client SDKs**: High-level async Python clients
- **Observability**: Built-in metrics, logging, and health checks
- **Production Ready**: Comprehensive error handling, retries, and monitoring

## Quick Start

### Installation

```bash
# Basic installation
pip install dotmac-core-events

# With Redis support
pip install dotmac-core-events[redis]

# With Kafka support  
pip install dotmac-core-events[kafka]

# With all adapters
pip install dotmac-core-events[all]
```

### Basic Usage

#### Using the SDK

```python
import asyncio
from dotmac_core_events import EventBusSDK
from dotmac_core_events.adapters import MemoryAdapter, MemoryConfig

async def main():
    # Initialize adapter
    config = MemoryConfig()
    adapter = MemoryAdapter(config)
    await adapter.connect()
    
    # Initialize SDK
    event_bus = EventBusSDK(adapter=adapter)
    
    # Publish an event
    result = await event_bus.publish(
        event_type="user.created",
        data={"user_id": "123", "email": "user@example.com"},
        tenant_id="tenant-1"
    )
    print(f"Published event: {result.event_id}")
    
    # Subscribe to events
    async for event in event_bus.subscribe(
        event_types=["user.created"],
        consumer_group="user-service",
        tenant_id="tenant-1"
    ):
        print(f"Received event: {event.event_type}")
        break
    
    await adapter.disconnect()

asyncio.run(main())
```

#### Using the REST API

```python
import asyncio
from dotmac_core_events.client import EventsClient

async def main():
    async with EventsClient(
        base_url="http://localhost:8000",
        tenant_id="tenant-1"
    ) as client:
        # Publish an event
        result = await client.publish_event(
            event_type="user.created",
            data={"user_id": "123", "email": "user@example.com"}
        )
        print(f"Published: {result}")
        
        # Get event history
        history = await client.get_event_history(
            event_type="user.created",
            limit=10
        )
        print(f"Found {len(history['events'])} events")

asyncio.run(main())
```

#### Running the Server

```python
from dotmac_core_events.runtime import create_app
import uvicorn

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Configuration

### Environment Variables

```bash
# Adapter configuration
ADAPTER_TYPE=redis  # memory, redis, kafka
REDIS_HOST=localhost
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Database (for outbox pattern)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Security
JWT_SECRET_KEY=<REPLACE_WITH_STRONG_RANDOM_SECRET>
CORS_ORIGINS=https://yourdomain.com

# Observability
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Configuration File

```yaml
# config.yaml
app_name: "my-events-service"
adapter_type: "redis"
adapter_config:
  host: "redis.example.com"
  port: 6379
  password: "<REPLACE_WITH_REDIS_PASSWORD>"

database:
  url: "postgresql+asyncpg://user:pass@db.example.com/events"
  pool_size: 20

security:
  jwt_secret_key: "<REPLACE_WITH_STRONG_RANDOM_SECRET>"
  cors_origins: ["https://yourdomain.com"]

observability:
  log_level: "INFO"
  enable_metrics: true
```

## Architecture

### Core Components

- **EventBusSDK**: Main SDK for event publishing and consumption
- **SchemaRegistrySDK**: Schema validation and management
- **OutboxSDK**: Transactional outbox pattern implementation
- **Adapters**: Pluggable backends (Redis, Kafka, Memory)
- **REST API**: HTTP endpoints for all operations
- **Client SDKs**: High-level HTTP clients

### Multi-Tenancy

All operations are tenant-scoped:

```python
# SDK usage
await event_bus.publish(
    event_type="order.created",
    data={"order_id": "123"},
    tenant_id="tenant-1"  # Required
)

# HTTP headers
headers = {
    "X-Tenant-ID": "tenant-1",
    "Authorization": "Bearer <token>"
}
```

### Schema Management

```python
from dotmac_core_events import SchemaRegistrySDK

schema_registry = SchemaRegistrySDK()

# Register schema
await schema_registry.register_schema(
    event_type="user.created",
    version="1.0",
    schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["user_id", "email"]
    },
    tenant_id="tenant-1"
)

# Validate data
result = await schema_registry.validate_event(
    event_type="user.created",
    data={"user_id": "123", "email": "user@example.com"},
    tenant_id="tenant-1"
)
```

### Transactional Outbox

```python
from dotmac_core_events import OutboxSDK
from sqlalchemy.ext.asyncio import AsyncSession

outbox = OutboxSDK(database_url="postgresql+asyncpg://...")

async def create_user_with_event(session: AsyncSession, user_data):
    # Create user in database
    user = User(**user_data)
    session.add(user)
    
    # Store event in outbox (same transaction)
    await outbox.store_event(
        session=session,
        event_type="user.created",
        data={"user_id": user.id, "email": user.email},
        tenant_id="tenant-1"
    )
    
    await session.commit()
    # Event will be dispatched by background task
```

## API Reference

### REST Endpoints

#### Events API

- `POST /api/v1/events/publish` - Publish an event
- `POST /api/v1/events/subscribe` - Subscribe to events
- `GET /api/v1/events/history` - Get event history
- `POST /api/v1/events/replay` - Replay historical events

#### Schema Registry API

- `POST /api/v1/schemas/{event_type}` - Register schema
- `GET /api/v1/schemas/{event_type}` - Get schema
- `POST /api/v1/schemas/{event_type}/validate` - Validate data
- `DELETE /api/v1/schemas/{event_type}` - Delete schema

#### Admin API

- `POST /api/v1/admin/topics` - Create topic
- `GET /api/v1/admin/topics` - List topics
- `DELETE /api/v1/admin/topics/{topic}` - Delete topic
- `GET /api/v1/admin/consumer-groups` - List consumer groups

#### Health API

- `GET /api/v1/health` - Health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

## Adapters

### Redis Streams

```python
from dotmac_core_events.adapters import RedisAdapter, RedisConfig

config = RedisConfig(
    host="localhost",
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True
)
adapter = RedisAdapter(config)
```

### Apache Kafka

```python
from dotmac_core_events.adapters import KafkaAdapter, KafkaConfig

config = KafkaConfig(
    bootstrap_servers=["localhost:9092"],
    security_protocol="SASL_SSL",
    sasl_mechanism="PLAIN",
    sasl_username=os.getenv("KAFKA_SASL_USERNAME"),
    sasl_password=os.getenv("KAFKA_SASL_PASSWORD")
)
adapter = KafkaAdapter(config)
```

### In-Memory (Testing)

```python
from dotmac_core_events.adapters import MemoryAdapter, MemoryConfig

config = MemoryConfig(
    max_messages_per_topic=10000
)
adapter = MemoryAdapter(config)
```

## Development

### Setup

```bash
git clone https://github.com/dotmac/dotmac-core-events.git
cd dotmac-core-events
pip install -e ".[dev]"
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires Redis/Kafka)
pytest tests/integration/

# All tests
pytest
```

### Code Quality

```bash
# Format code
black dotmac_core_events/
isort dotmac_core_events/

# Lint
flake8 dotmac_core_events/
mypy dotmac_core_events/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e ".[redis,kafka]"

EXPOSE 8000
CMD ["uvicorn", "dotmac_core_events.runtime:create_production_app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-events
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dotmac-events
  template:
    metadata:
      labels:
        app: dotmac-events
    spec:
      containers:
      - name: events
        image: dotmac/core-events:latest
        ports:
        - containerPort: 8000
        env:
        - name: ADAPTER_TYPE
          value: "kafka"
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: jwt-secret
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- Documentation: https://dotmac-core-events.readthedocs.io/
- Issues: https://github.com/dotmac/dotmac-core-events/issues
- Discussions: https://github.com/dotmac/dotmac-core-events/discussions
