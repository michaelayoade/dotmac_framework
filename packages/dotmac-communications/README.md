# DotMac Communications

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/dotmac-framework/dotmac-framework)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)

Comprehensive communication system integrating notifications, websockets, and events into a unified, production-ready package.

## 🚀 Features

### 📧 Notifications
- **Multi-channel delivery**: Email, SMS, push notifications, webhooks, Slack
- **Template engine**: Jinja2 templates with conditional logic
- **Delivery tracking**: Real-time status updates and delivery confirmation
- **Provider integration**: SMTP, Twilio, FCM, OneSignal, Slack, Discord
- **Retry mechanisms**: Configurable exponential backoff and circuit breakers
- **Bulk operations**: Efficient batch sending with rate limiting

### 🔄 WebSockets  
- **Real-time communication**: Bidirectional WebSocket support
- **Channel management**: Topic-based messaging and broadcasting
- **Horizontal scaling**: Redis-backed connection sharing across instances
- **Authentication**: JWT, session-based auth with middleware support
- **Connection pooling**: Efficient resource management
- **Health monitoring**: Connection health checks and auto-reconnection

### ⚡ Events
- **Event-driven architecture**: Publish/subscribe pattern with multiple backends
- **Message brokers**: Memory, Redis Streams with extensible adapter pattern
- **Dead letter queues**: Failed message handling and retry logic
- **Event sourcing**: Complete audit trail with event replay capabilities
- **Schema validation**: Automatic event validation and versioning
- **Observability**: Comprehensive metrics and distributed tracing

## 📦 Installation

### Basic Installation

```bash
poetry add dotmac-communications
```

### With Optional Features

```bash
# SMS support via Twilio
poetry add dotmac-communications[sms]

# Push notifications
poetry add dotmac-communications[push]

# Background task processing
poetry add dotmac-communications[celery]

# All features
poetry add dotmac-communications[all]
```

## 🚀 Quick Start

### Unified Service

```python
from dotmac.communications import create_communications_service

# Create unified service
comm = create_communications_service()

# Send notification
await comm.notifications.send_email(
    to="user@example.com",
    subject="Welcome {{name}}!",
    template="welcome_email",
    context={"name": "John", "company": "Acme Inc"}
)

# Real-time WebSocket messaging
async def handle_websocket(websocket, tenant_id):
    manager = comm.websockets
    await manager.connect(websocket, tenant_id)
    
    await manager.broadcast(
        channel="notifications",
        message={"type": "welcome", "user": "John"}
    )

# Event-driven processing
@comm.events.subscribe("user.registered")
async def on_user_registered(event):
    user_data = event.payload
    
    # Send welcome notification
    await comm.notifications.send_template(
        "welcome_series", 
        user_data["email"],
        user_data
    )
    
    # Notify admins via WebSocket
    await comm.websockets.send_to_channel(
        "admin_alerts",
        {"type": "new_user", "user": user_data}
    )
```

### Standalone Services

```python
# Individual service creation
from dotmac.communications import (
    create_notification_service,
    create_websocket_manager,
    create_event_bus
)

# Notifications only
notifications = create_notification_service({
    "retry_attempts": 5,
    "providers": {
        "email": {"smtp_host": "smtp.example.com"},
        "sms": {"twilio_sid": "your_sid"}
    }
})

# WebSockets only  
websockets = create_websocket_manager({
    "max_connections": 10000,
    "redis_url": "redis://localhost:6379"
})

# Events only
events = create_event_bus({
    "backend": "redis",
    "redis_url": "redis://localhost:6379"
})
```

## 🔧 Configuration

### Complete Configuration Example

```python
config = {
    "notifications": {
        "default_template_engine": "jinja2",
        "retry_attempts": 3,
        "retry_delay": 60,
        "delivery_timeout": 300,
        "track_delivery": True,
        "providers": {
            "email": {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "your_email@gmail.com",
                "password": "your_app_password",
                "use_tls": True
            },
            "sms": {
                "provider": "twilio",
                "account_sid": "your_twilio_sid",
                "auth_token": "your_twilio_token"
            },
            "push": {
                "provider": "fcm", 
                "server_key": "your_fcm_server_key"
            }
        }
    },
    "websockets": {
        "connection_timeout": 60,
        "heartbeat_interval": 30,
        "max_connections_per_tenant": 1000,
        "message_size_limit": 1048576,
        "enable_compression": True,
        "redis_url": "redis://localhost:6379/0"
    },
    "events": {
        "default_adapter": "redis",
        "retry_policy": "exponential_backoff",
        "max_retries": 5,
        "dead_letter_enabled": True,
        "event_ttl": 3600,
        "redis_url": "redis://localhost:6379/1"
    }
}

# Use configuration
comm = create_communications_service(config)
```

### Environment Variables

```bash
# Notifications
DOTMAC_SMTP_HOST=smtp.gmail.com
DOTMAC_SMTP_PORT=587
DOTMAC_SMTP_USERNAME=your_email@gmail.com
DOTMAC_SMTP_PASSWORD=your_password

# Twilio SMS
DOTMAC_TWILIO_SID=your_twilio_sid
DOTMAC_TWILIO_TOKEN=your_twilio_token

# WebSockets & Events Redis
DOTMAC_REDIS_URL=redis://localhost:6379

# Push notifications  
DOTMAC_FCM_SERVER_KEY=your_fcm_key
```

## 📚 Advanced Usage

### Custom Notification Templates

```python
# Define templates
templates = {
    "welcome_email": {
        "subject": "Welcome to {{company_name}}, {{user_name}}!",
        "html": """
        <h1>Welcome {{user_name}}!</h1>
        <p>Thanks for joining {{company_name}}.</p>
        <p>Your account: {{user_email}}</p>
        """,
        "text": "Welcome {{user_name}}! Thanks for joining {{company_name}}."
    },
    "password_reset": {
        "subject": "Reset your password",
        "html": "<p>Click <a href='{{reset_link}}'>here</a> to reset.</p>"
    }
}

# Send with template
await comm.notifications.send_template(
    template_name="welcome_email",
    recipient="user@example.com", 
    context={
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "company_name": "Acme Corp"
    }
)
```

### WebSocket Channel Management

```python
# Create channels and broadcast
websocket_manager = comm.websockets

# Connect user to specific channels
await websocket_manager.join_channel("user123", "general")
await websocket_manager.join_channel("user123", "notifications")

# Broadcast to all users in channel
await websocket_manager.broadcast_to_channel(
    "general",
    {"type": "announcement", "message": "System maintenance in 1 hour"}
)

# Send to specific user
await websocket_manager.send_to_user(
    "user123", 
    {"type": "personal", "message": "Your order is ready!"}
)

# Room-based messaging
await websocket_manager.create_room("project_alpha", ["user123", "user456"])
await websocket_manager.broadcast_to_room(
    "project_alpha",
    {"type": "project_update", "status": "Phase 1 complete"}
)
```

### Event Sourcing & Processing

```python
# Define event handlers
@comm.events.subscribe("order.created")
async def handle_order_created(event):
    order = event.payload
    
    # Send confirmation email
    await comm.notifications.send_template(
        "order_confirmation",
        order["customer_email"], 
        order
    )
    
    # Notify fulfillment team
    await comm.events.publish(Event(
        topic="fulfillment.order_received",
        payload={"order_id": order["id"], "priority": order["priority"]}
    ))

@comm.events.subscribe("payment.failed")  
async def handle_payment_failed(event):
    # Send payment retry notification
    await comm.notifications.send_urgent(
        recipient=event.payload["customer_email"],
        message="Payment failed. Please update your payment method."
    )
    
    # Schedule retry after delay
    await comm.events.publish_delayed(
        Event(topic="payment.retry", payload=event.payload),
        delay_seconds=3600  # Retry in 1 hour
    )

# Publish events
await comm.events.publish(Event(
    topic="user.registered",
    payload={
        "user_id": "user123",
        "email": "new_user@example.com",
        "registration_ip": "192.168.1.100"
    }
))
```

## 🏗️ Architecture

### Component Overview

```
dotmac-communications/
├── notifications/          # Multi-channel messaging
│   ├── providers/         # Email, SMS, Push, Webhook providers
│   ├── templates/         # Template engine and management
│   └── tracking/          # Delivery tracking and analytics
├── websockets/           # Real-time communication
│   ├── gateway/          # WebSocket gateway and routing
│   ├── channels/         # Channel and room management  
│   ├── auth/             # Authentication middleware
│   └── scaling/          # Redis-backed horizontal scaling
├── events/               # Event-driven messaging
│   ├── bus/              # Abstract bus interface
│   ├── adapters/         # Memory, Redis adapters
│   ├── consumer/         # Event consumption and processing
│   └── dlq/              # Dead letter queue handling
└── core/                 # Shared utilities and config
```

### Integration Patterns

```python
# Pattern 1: Microservice Communication
class OrderService:
    def __init__(self, comm):
        self.comm = comm
        
    async def create_order(self, order_data):
        # Create order in database
        order = await self.save_order(order_data)
        
        # Publish event for other services
        await self.comm.events.publish(Event(
            topic="order.created", 
            payload=order
        ))
        
        return order

# Pattern 2: Real-time Dashboard Updates  
class DashboardManager:
    def __init__(self, comm):
        self.comm = comm
        
    async def setup_listeners(self):
        @self.comm.events.subscribe("metrics.updated")
        async def on_metrics_update(event):
            # Push to dashboard via WebSocket
            await self.comm.websockets.broadcast_to_channel(
                "dashboard",
                {"type": "metrics", "data": event.payload}
            )

# Pattern 3: Multi-tenant Notifications
class TenantNotificationManager:
    def __init__(self, comm):
        self.comm = comm
        
    async def send_tenant_broadcast(self, tenant_id, message):
        # Send via multiple channels
        tasks = [
            self.comm.notifications.send_email_blast(tenant_id, message),
            self.comm.websockets.broadcast_to_tenant(tenant_id, message),
            self.comm.events.publish(Event(
                topic=f"tenant.{tenant_id}.broadcast",
                payload=message
            ))
        ]
        await asyncio.gather(*tasks)
```

## 🧪 Testing

### Run Tests

```bash
# Install development dependencies
poetry install --with dev

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=dotmac.communications --cov-report=html

# Run specific component tests
poetry run pytest tests/test_notifications.py
poetry run pytest tests/test_websockets.py  
poetry run pytest tests/test_events.py

# Run integration tests only
poetry run pytest -m integration

# Run async tests
poetry run pytest -m async
```

### Example Tests

```python
import pytest
from dotmac.communications import create_communications_service

@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete communication workflow."""
    comm = create_communications_service()
    
    # Simulate user registration event
    await comm.events.publish(Event(
        topic="user.registered",
        payload={"email": "test@example.com", "name": "Test User"}
    ))
    
    # Verify notification was sent (mock or integration test)
    # Verify WebSocket message was broadcast
    # Verify event was processed
```

## 🚀 Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --only=main

COPY . .
EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: communications-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: communications-service
  template:
    spec:
      containers:
      - name: communications
        image: your-registry/communications-service:latest
        env:
        - name: DOTMAC_REDIS_URL
          value: "redis://redis-service:6379"
        - name: DOTMAC_SMTP_HOST
          valueFrom:
            secretKeyRef:
              name: communications-secrets
              key: smtp-host
```

### Performance Tuning

```python
# High-performance configuration
config = {
    "notifications": {
        "batch_size": 1000,           # Batch notifications
        "worker_concurrency": 50,     # Parallel workers
        "rate_limit_per_minute": 5000 # Rate limiting
    },
    "websockets": {
        "max_connections": 50000,     # Connection limit
        "message_buffer_size": 10000, # Message buffering
        "compression_threshold": 1024 # Compress large messages
    },
    "events": {
        "batch_publish_size": 100,    # Batch event publishing
        "consumer_concurrency": 20,   # Parallel consumers
        "prefetch_count": 50          # Message prefetching
    }
}
```

## 📖 Documentation

- **[API Reference](docs/api.md)**: Complete API documentation
- **[Configuration Guide](docs/configuration.md)**: Detailed configuration options
- **[Migration Guide](MIGRATION_GUIDE.md)**: Migrate from separate packages
- **[Examples](examples/)**: Usage examples and patterns
- **[Contributing](CONTRIBUTING.md)**: Development and contribution guidelines

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/dotmac-framework/dotmac-framework
cd dotmac-framework/packages/dotmac-communications

# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Run linting
poetry run black .
poetry run isort .
poetry run ruff check .
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/dotmac-framework/dotmac-framework/issues)
- **Documentation**: [docs.dotmac-framework.dev](https://docs.dotmac-framework.dev)
- **Community**: [Discord](https://discord.gg/dotmac-framework)

---

Made with ❤️ by the DotMac Framework team