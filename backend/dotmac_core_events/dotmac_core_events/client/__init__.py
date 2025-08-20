"""
Client SDK package for dotmac_core_events.

Provides high-level async clients for:
- Event operations (publish, subscribe, history, replay)
- Schema registry operations (register, validate, compatibility)
- Administrative operations (topics, consumer groups, maintenance)
- HTTP communication with retry and error handling
"""

# Convenience imports
from .admin_client import AdminClient, create_topic, list_topics, run_cleanup
from .events_client import (
    EventsClient,
    get_event_history,
    publish_event,
    subscribe_to_events,
)
from .http_client import HTTPClient
from .schemas_client import SchemasClient, get_schema, register_schema, validate_data

__all__ = [
    # Main client classes
    "AdminClient",
    "EventsClient",
    "HTTPClient",
    "SchemasClient",

    # Convenience functions
    "create_topic",
    "list_topics",
    "run_cleanup",
    "publish_event",
    "subscribe_to_events",
    "get_event_history",
    "register_schema",
    "validate_data",
    "get_schema",
]
