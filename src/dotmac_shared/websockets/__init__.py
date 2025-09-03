"""
DEPRECATED: dotmac_shared.websockets module

This module is deprecated and will be removed in a future version.
Please migrate to the new dotmac.websockets package.

Migration guide:
    
Old import:
    from dotmac_shared.websockets import WebSocketGateway, WebSocketConfig
    
New import:
    from dotmac.websockets import WebSocketGateway, WebSocketConfig

The new package provides:
    - Enhanced session management
    - Multi-instance scaling with Redis
    - Advanced channel system with broadcast utilities
    - Built-in authentication and authorization
    - Tenant isolation and multi-tenancy support
    - Rate limiting and middleware system
    - Comprehensive observability and health monitoring
    - FastAPI integration for HTTP endpoints
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "dotmac_shared.websockets is deprecated and will be removed in the next minor release. "
    "Please migrate to dotmac.websockets package. "
    "Install with: pip install dotmac-websockets",
    DeprecationWarning,
    stacklevel=2
)

# Try to provide backward compatibility by importing from new package
try:
    from dotmac.websockets import (
        # Core components
        WebSocketGateway,
        WebSocketConfig,
        RedisConfig,
        AuthConfig,
        SessionManager,
        WebSocketSession,
        
        # Channel system
        ChannelManager,
        BroadcastManager,
        
        # Authentication
        AuthManager,
        AuthResult,
        UserInfo,
        
        # Middleware
        TenantMiddleware,
        RateLimitMiddleware,
        
        # Backends
        RedisScalingBackend,
        LocalBackend,
        
        # Observability
        create_default_hooks,
        create_dotmac_observability_hooks,
        WebSocketHealthCheck,
        
        # Configuration helpers
        create_development_config,
        create_production_config,
    )
    
    # Provide backward compatibility aliases for old names
    WebSocketManager = WebSocketGateway  # Legacy alias
    EventManager = BroadcastManager  # Legacy alias
    RoomManager = ChannelManager  # Legacy alias
    RedisWebSocketBackend = RedisScalingBackend  # Legacy alias
    
    # Provide migration helpers
    def migrate_to_new_api():
        """
        Helper function to show migration examples.
        """
        print("Migration examples:")
        print("")
        print("OLD: from dotmac_shared.websockets import WebSocketManager")
        print("NEW: from dotmac.websockets import WebSocketGateway")
        print("")
        print("OLD: from dotmac_shared.websockets import EventManager")
        print("NEW: from dotmac.websockets import BroadcastManager")
        print("")
        print("OLD: from dotmac_shared.websockets import RoomManager")
        print("NEW: from dotmac.websockets import ChannelManager")
        print("")
        print("OLD: config = WebSocketConfig(host='0.0.0.0', port=8765)")
        print("NEW: config = create_development_config(host='0.0.0.0', port=8765)")
        print("")
        print("OLD: manager = WebSocketManager(config)")
        print("NEW: gateway = WebSocketGateway(config)")
        print("")
        print("Enhanced features in new package:")
        print("- Redis scaling: config.backend_type = BackendType.REDIS")
        print("- Authentication: config.auth_config.enabled = True")
        print("- Rate limiting: config.rate_limit_config.enabled = True")
        print("- Observability: gateway.set_observability_hooks(create_default_hooks())")
        print("- Health checks: health = await gateway.health_check()")
    
    def create_websocket_service(*args, **kwargs):
        """Legacy function - creates WebSocketGateway."""
        warnings.warn("create_websocket_service is deprecated, use WebSocketGateway directly", DeprecationWarning)
        config = create_development_config(**kwargs)
        return WebSocketGateway(config)
    
except ImportError:
    # New package not available - provide stubs that show migration message
    warnings.warn(
        "dotmac.websockets package not found. Please install: pip install dotmac-websockets",
        UserWarning
    )
    
    class _DeprecatedStub:
        """Stub class that shows deprecation message."""
        
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "This component has been moved to dotmac.websockets package. "
                "Please install: pip install dotmac-websockets and update your imports."
            )
    
    # Provide stubs for common classes
    WebSocketGateway = _DeprecatedStub
    WebSocketManager = _DeprecatedStub  # Legacy alias
    WebSocketConfig = _DeprecatedStub
    SessionManager = _DeprecatedStub
    WebSocketSession = _DeprecatedStub
    ChannelManager = _DeprecatedStub
    RoomManager = _DeprecatedStub  # Legacy alias
    BroadcastManager = _DeprecatedStub
    EventManager = _DeprecatedStub  # Legacy alias
    AuthManager = _DeprecatedStub
    RedisScalingBackend = _DeprecatedStub
    RedisWebSocketBackend = _DeprecatedStub  # Legacy alias
    
    def migrate_to_new_api():
        print("Please install dotmac.websockets package: pip install dotmac-websockets")
        print("Then update your imports from dotmac_shared.websockets to dotmac.websockets")
    
    def create_websocket_service(*args, **kwargs):
        raise ImportError("Please install dotmac.websockets package: pip install dotmac-websockets")

# Legacy configuration for backward compatibility
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
    return "1.0.0-deprecated"

def get_config() -> dict:
    """Get default configuration."""
    warnings.warn("Use create_development_config() from dotmac.websockets instead", DeprecationWarning)
    return DEFAULT_CONFIG.copy()

__all__ = [
    # Core components
    "WebSocketGateway",
    "WebSocketManager",  # Legacy alias
    "WebSocketConfig",
    "RedisConfig", 
    "AuthConfig",
    "SessionManager",
    "WebSocketSession",
    
    # Channel system
    "ChannelManager",
    "RoomManager",  # Legacy alias
    "BroadcastManager",
    "EventManager",  # Legacy alias
    
    # Authentication
    "AuthManager",
    "AuthResult",
    "UserInfo",
    
    # Middleware
    "TenantMiddleware",
    "RateLimitMiddleware",
    
    # Backends
    "RedisScalingBackend",
    "RedisWebSocketBackend",  # Legacy alias
    "LocalBackend",
    
    # Observability
    "create_default_hooks",
    "create_dotmac_observability_hooks",
    "WebSocketHealthCheck",
    
    # Configuration helpers
    "create_development_config",
    "create_production_config",
    "create_websocket_service",  # Legacy function
    
    # Legacy functions
    "get_version",
    "get_config",
    
    # Migration helper
    "migrate_to_new_api",
]