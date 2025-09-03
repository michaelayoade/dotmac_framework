"""
DotMac WebSocket Gateway Package.

A comprehensive WebSocket solution with:
- Multi-tenant session management
- Horizontal scaling with Redis pub/sub
- Channel abstractions and broadcast utilities
- Authentication and authorization middleware
- Observability and health monitoring integration
- FastAPI integration for HTTP endpoints
"""

from .core.gateway import WebSocketGateway
from .core.session import SessionManager, WebSocketSession
from .core.config import WebSocketConfig, RedisConfig, AuthConfig

# Channel system
from .channels.abstractions import Channel, ChannelManager
from .channels.broadcast import BroadcastManager

# Authentication
from .auth.manager import AuthManager
from .auth.middleware import AuthMiddleware
from .auth.types import AuthResult, UserInfo

# Backends
from .backends.redis import RedisScalingBackend
from .backends.local import LocalBackend

# Middleware
from .middleware.tenant import TenantMiddleware
from .middleware.rate_limit import RateLimitMiddleware

# Try to import observability components (optional)
try:
    from .observability.hooks import (
        create_default_hooks,
        create_dotmac_observability_hooks,
        WebSocketObservabilityHooks,
    )
    from .observability.health import WebSocketHealthCheck
except ImportError:
    # Observability not available
    create_default_hooks = None
    create_dotmac_observability_hooks = None
    WebSocketObservabilityHooks = None
    WebSocketHealthCheck = None

# Try to import FastAPI integration (optional)
try:
    from .integrations.fastapi import create_fastapi_websocket_app, FastAPIWebSocketIntegration
except ImportError:
    # FastAPI not available
    create_fastapi_websocket_app = None
    FastAPIWebSocketIntegration = None

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

__all__ = [
    # Core components
    "WebSocketGateway",
    "SessionManager", 
    "WebSocketSession",
    "WebSocketConfig",
    "RedisConfig",
    "AuthConfig",
    
    # Channel system
    "Channel",
    "ChannelManager", 
    "BroadcastManager",
    
    # Authentication
    "AuthManager",
    "AuthMiddleware",
    "AuthResult",
    "UserInfo",
    
    # Backends
    "RedisScalingBackend",
    "LocalBackend",
    
    # Middleware
    "TenantMiddleware",
    "RateLimitMiddleware",
    
    # Observability (may be None if not available)
    "create_default_hooks",
    "create_dotmac_observability_hooks", 
    "WebSocketObservabilityHooks",
    "WebSocketHealthCheck",
    
    # FastAPI integration (may be None if not available)
    "create_fastapi_websocket_app",
    "FastAPIWebSocketIntegration",
]