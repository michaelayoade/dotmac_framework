"""
Observability components for WebSocket gateway.
"""

# Try to import observability components (optional dependencies)
try:
    from .hooks import (
        create_default_hooks,
        create_dotmac_observability_hooks,
        WebSocketObservabilityHooks,
    )
    from .health import WebSocketHealthCheck
    from .metrics import WebSocketMetrics
    
    OBSERVABILITY_AVAILABLE = True
except ImportError as e:
    # Observability dependencies not available
    create_default_hooks = None
    create_dotmac_observability_hooks = None
    WebSocketObservabilityHooks = None
    WebSocketHealthCheck = None
    WebSocketMetrics = None
    
    OBSERVABILITY_AVAILABLE = False

__all__ = [
    "create_default_hooks",
    "create_dotmac_observability_hooks", 
    "WebSocketObservabilityHooks",
    "WebSocketHealthCheck",
    "WebSocketMetrics",
    "OBSERVABILITY_AVAILABLE",
]