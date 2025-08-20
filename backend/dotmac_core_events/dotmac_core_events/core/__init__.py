"""
Core utilities and shared components for dotmac_core_events.

Provides:
- Base classes and interfaces
- Dependency injection
- Configuration management
- Common utilities
"""

from .dependencies import (
    get_event_bus,
    get_outbox,
    get_schema_registry,
    get_tenant_id,
    get_user_id,
    set_event_bus_instance,
    set_outbox_instance,
    set_schema_registry_instance,
)

__all__ = [
    "get_event_bus",
    "get_schema_registry",
    "get_outbox",
    "get_tenant_id",
    "get_user_id",
    "set_event_bus_instance",
    "set_schema_registry_instance",
    "set_outbox_instance",
]
