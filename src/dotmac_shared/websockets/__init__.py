"""
DotMac WebSocket Service Package

A comprehensive, production-ready WebSocket service for real-time communication
with multi-tenant support, horizontal scaling, and service integration.

Key Features:
- Multi-tenant WebSocket connection management
- Real-time event broadcasting and routing
- Horizontal scaling with Redis backend
- Service registry integration
- Cross-package integration support
"""

from typing import TYPE_CHECKING

from .core.config import WebSocketConfig
from .core.events import EventManager, WebSocketEvent
from .core.manager import WebSocketManager
from .integration.service_factory import (
    UnifiedServiceFactory,
    WebSocketServiceFactory,
    create_websocket_service,
)
from .patterns.broadcasting import BroadcastManager
from .patterns.rooms import RoomManager
from .scaling.redis_backend import RedisWebSocketBackend

if TYPE_CHECKING:
    from .core.service_integration import WebSocketService

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"
__email__ = "dev@dotmac.dev"

# Main exports for easy importing
__all__ = [
    # Core components
    "WebSocketConfig",
    "WebSocketManager",
    "EventManager",
    "WebSocketEvent",
    # Pattern implementations
    "RoomManager",
    "BroadcastManager",
    # Scaling components
    "RedisWebSocketBackend",
    # Service integration
    "WebSocketServiceFactory",
    "UnifiedServiceFactory",
    "create_websocket_service",
    # Package metadata
    "__version__",
    "__author__",
    "__email__",
]

# Package-level configuration
DEFAULT_CONFIG = {
    "max_connections": 10000,
    "heartbeat_interval": 30,
    "message_ttl": 300,
    "enable_persistence": True,
    "cors_origins": ["*"],
    "redis_url": "redis://localhost:6379",
}


def get_version() -> str:
    """Get package version."""
    return __version__


def get_config() -> dict:
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()
