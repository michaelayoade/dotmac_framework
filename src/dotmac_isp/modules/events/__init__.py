"""
Event-Driven Architecture Module.

Provides event bus, event handlers, and integration patterns for
reactive network operations and cross-service communication.
"""

from .handlers.device_event_handlers import DeviceEventHandlers
from .services.event_bus import EventBusService

__all__ = [
    "EventBusService",
    "DeviceEventHandlers",
    # Additional handler and model exports are intentionally omitted in this minimal build
]
