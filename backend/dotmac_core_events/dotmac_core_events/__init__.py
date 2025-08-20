"""
Dotmac Core Events - Event Streaming Platform Package

A comprehensive event streaming platform providing:
- Event Bus SDK with Redis Streams and Kafka adapters
- Schema Registry with JSON Schema validation
- Transactional Outbox pattern implementation
- REST API layer for all operations
- High-level client SDKs
- OpenAPI contracts and documentation

Example usage:
    from dotmac_core_events import EventBusSDK, SchemaRegistrySDK

    # Initialize SDKs
    event_bus = EventBusSDK(tenant_id="my-tenant")
    schema_registry = SchemaRegistrySDK(tenant_id="my-tenant")

    # Publish an event
    await event_bus.publish("user.created", {"user_id": "123", "email": "user@example.com"})
"""

from .api.admin import AdminAPI

# API classes
from .api.events import EventsAPI
from .api.health import HealthAPI
from .api.schemas import SchemasAPI

# FastAPI application factory
from .runtime.app_factory import create_app, create_development_app, create_production_app
from .client.admin_client import AdminClient

# Client SDKs
from .client.events_client import EventsClient
from .client.http_client import HTTPClient
from .client.schemas_client import SchemasClient
from .sdks.event_bus import EventBusSDK
from .sdks.outbox import OutboxSDK
from .sdks.schema_registry import SchemaRegistrySDK

__version__ = "1.0.0"

__all__ = [
    # Core SDKs
    "EventBusSDK",
    "SchemaRegistrySDK",
    "OutboxSDK",

    # API classes
    "EventsAPI",
    "SchemasAPI",
    "HealthAPI",
    "AdminAPI",

    # Client SDKs
    "EventsClient",
    "SchemasClient",
    "AdminClient",
    "HTTPClient",

    # App factory
    "create_app",
    "create_development_app",
    "create_production_app",
]
