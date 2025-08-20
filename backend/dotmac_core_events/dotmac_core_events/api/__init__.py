"""
API package for dotmac_core_events.

Provides REST API endpoints for:
- Event operations (publish, subscribe, history, replay)
- Schema registry operations (register, validate, compatibility)
- Health and monitoring endpoints
- Administrative operations (topics, consumer groups, maintenance)
"""

from .admin import AdminAPI
from .events import EventsAPI
from .health import HealthAPI
from .schemas import SchemasAPI
from .security import SecurityAPI

__all__ = [
    "AdminAPI",
    "EventsAPI",
    "HealthAPI",
    "SchemasAPI",
    "SecurityAPI",
]
