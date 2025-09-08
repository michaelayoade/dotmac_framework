"""
DotMac Communications - Comprehensive Communication System

This package provides integrated communication capabilities:
- Multi-channel notifications (email, SMS, push, webhooks)
- Real-time WebSocket communication
- Event-driven messaging and bus
- Template-based messaging
- Delivery tracking and retries
- Authentication and authorization
"""
from typing import Optional

try:
    from .notifications import NotificationRequest, NotificationResponse
    from .notifications import NotificationStatus as DeliveryStatus
    from .notifications import NotificationTemplate
    from .notifications import NotificationType as NotificationChannel
    from .notifications import UnifiedNotificationService as NotificationService

    # Backwards compatibility aliases
    EmailNotifier = SMSNotifier = PushNotifier = WebhookNotifier = NotificationService
except ImportError as e:
    import warnings

    warnings.warn(f"Notifications not available: {e}")
    NotificationService = EmailNotifier = SMSNotifier = None
    PushNotifier = WebhookNotifier = NotificationTemplate = None
    DeliveryStatus = NotificationChannel = NotificationRequest = NotificationResponse = None

try:
    from .websockets import AuthManager as WebSocketAuthManager
    from .websockets import BroadcastManager, ChannelManager
    from .websockets import SessionManager as ConnectionManager
    from .websockets import WebSocketConfig
    from .websockets import WebSocketGateway as WebSocketManager
    from .websockets import WebSocketSession as ConnectionState
except ImportError as e:
    import warnings

    warnings.warn(f"WebSockets not available: {e}")
    WebSocketManager = ChannelManager = BroadcastManager = None
    ConnectionManager = WebSocketAuthManager = WebSocketConfig = None
    ConnectionState = None

try:
    from .events.adapters.base import BaseAdapter as EventAdapter
    from .events.bus import EventBus
    from .events.codecs import JsonCodec as MessageCodec
    from .events.consumer import ConsumerOptions as EventConsumer
    from .events.consumer import RetryPolicy
    from .events.dlq import DLQ as DeadLetterQueue
    from .events.message import Event as EventMessage

    # EventObservability may not exist yet - make it optional
    EventObservability = None
    try:
        from .events.observability import EventObservability
    except ImportError:
        pass
except ImportError as e:
    import warnings

    warnings.warn(f"Events not available: {e}")
    EventBus = EventConsumer = EventMessage = None
    EventAdapter = MessageCodec = DeadLetterQueue = None
    RetryPolicy = EventObservability = None

# Configuration and observability
try:
    from .config import CommunicationsConfig, load_config, validate_config
    from .observability import CommunicationsObservability, get_observability
except ImportError as e:
    import warnings

    warnings.warn(f"Configuration/observability not available: {e}")
    CommunicationsConfig = None
    load_config = None
    validate_config = None
    get_observability = None
    CommunicationsObservability = None

# Version and metadata
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Notifications
    "NotificationService",
    "EmailNotifier",
    "SMSNotifier",
    "PushNotifier",
    "WebhookNotifier",
    "NotificationTemplate",
    "DeliveryStatus",
    "NotificationChannel",
    # WebSockets
    "WebSocketManager",
    "ChannelManager",
    "BroadcastManager",
    "ConnectionManager",
    "WebSocketAuthManager",
    "WebSocketConfig",
    "ConnectionState",
    # Events
    "EventBus",
    "EventConsumer",
    "EventMessage",
    "EventAdapter",
    "MessageCodec",
    "DeadLetterQueue",
    "RetryPolicy",
    "EventObservability",
    # Configuration & Observability
    "CommunicationsConfig",
    "CommunicationsObservability",
    "load_config",
    "validate_config",
    "get_observability",
    # Unified Service
    "CommunicationsService",
    "create_communications_service",
    "create_notification_service",
    "create_websocket_manager",
    "create_event_bus",
    # Utilities
    "get_version",
    "get_default_config",
    # Version
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "notifications": {
        "default_template_engine": "jinja2",
        "retry_attempts": 3,
        "retry_delay": 60,  # seconds
        "delivery_timeout": 300,  # seconds
        "track_delivery": True,
    },
    "websockets": {
        "connection_timeout": 60,
        "heartbeat_interval": 30,
        "max_connections_per_tenant": 1000,
        "message_size_limit": 1048576,  # 1MB
        "enable_compression": True,
    },
    "events": {
        "default_adapter": "memory",
        "retry_policy": "exponential_backoff",
        "max_retries": 5,
        "dead_letter_enabled": True,
        "event_ttl": 3600,  # seconds
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "connection_pool_size": 10,
    },
}


def get_version():
    """Get communications package version."""
    return __version__


def get_default_config():
    """Get default communications configuration."""
    return DEFAULT_CONFIG.copy()


class CommunicationsService:
    """Unified communications service providing notifications, websockets, and events."""

    def __init__(self, config: Optional[dict] = None):
        # Validate and load configuration
        if config and validate_config:
            self.config = validate_config(config)
        elif config:
            self.config = config
        else:
            self.config = get_default_config()

        self._notifications = None
        self._websockets = None
        self._events = None
        self._observability = None

    @property
    def notifications(self):
        """Get notifications service."""
        if self._notifications is None:
            if NotificationService:
                # UnifiedNotificationService doesn't require config, just instantiate
                self._notifications = NotificationService()
        return self._notifications

    @property
    def websockets(self):
        """Get websockets manager."""
        if self._websockets is None:
            if WebSocketManager and WebSocketConfig:
                try:
                    # Create WebSocketConfig from our config
                    websocket_config_dict = (
                        self.config.get("websockets", {}) if isinstance(self.config, dict)
                        else self.config.websockets if hasattr(self.config, 'websockets')
                        else {}
                    )
                    ws_config = WebSocketConfig(**websocket_config_dict)
                    self._websockets = WebSocketManager(ws_config)
                except Exception as e:
                    import warnings
                    warnings.warn(f"Failed to create WebSocket manager: {e}")
                    # Create a stub that won't break when used
                    self._websockets = None
        return self._websockets

    @property
    def events(self):
        """Get event bus."""
        if self._events is None:
            if EventBus:
                try:
                    # Select adapter based on config
                    if isinstance(self.config, dict):
                        events_config = self.config.get("events", {})
                        adapter = events_config.get("default_adapter", "memory")
                    elif hasattr(self.config, 'events') and self.config.events:
                        events_config = self.config.events
                        adapter = getattr(events_config, 'default_adapter', 'memory')
                    else:
                        events_config = {}
                        adapter = "memory"

                    if adapter == "memory":
                        from .events.adapters import create_memory_bus
                        self._events = create_memory_bus(events_config)
                    elif adapter == "redis":
                        try:
                            from .events.adapters import create_redis_bus
                            self._events = create_redis_bus(events_config)
                        except ImportError:
                            import warnings
                            warnings.warn("Redis adapter not available, falling back to memory")
                            from .events.adapters import create_memory_bus
                            self._events = create_memory_bus(events_config)
                    else:
                        import warnings
                        warnings.warn(f"Unknown adapter {adapter}, using memory")
                        from .events.adapters import create_memory_bus
                        self._events = create_memory_bus(events_config)
                except Exception as e:
                    import warnings
                    warnings.warn(f"Failed to create event bus: {e}")
                    self._events = None
        return self._events

    @property
    def observability(self):
        """Get observability service."""
        if self._observability is None and get_observability:
            self._observability = get_observability()
        return self._observability

    async def cleanup(self):
        """Cleanup resources."""
        cleanup_tasks = []

        if self._notifications and hasattr(self._notifications, "cleanup"):
            cleanup_tasks.append(self._notifications.cleanup())

        if self._websockets and hasattr(self._websockets, "cleanup"):
            cleanup_tasks.append(self._websockets.cleanup())

        if self._events and hasattr(self._events, "cleanup"):
            cleanup_tasks.append(self._events.cleanup())

        if cleanup_tasks:
            import asyncio

            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def get_health_status(self):
        """Get health status of all services."""
        if self.observability:
            return await self.observability.get_health_status()
        return {"healthy": True, "services": "observability_not_available"}

    def get_health_status_sync(self):
        """Get health status synchronously (runs async version)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, schedule as task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_health_status())
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(self.get_health_status())
        except RuntimeError:
            # No event loop, create new one
            return asyncio.run(self.get_health_status())

    def get_metrics(self):
        """Get metrics from all services."""
        if self.observability:
            return self.observability.get_metrics_summary()
        return {"metrics": "observability_not_available"}


def create_communications_service(config: Optional[dict] = None) -> CommunicationsService:
    """Create a configured communications service."""
    return CommunicationsService(config)


def create_notification_service(config: Optional[dict] = None):
    """Create a standalone notification service."""
    if not NotificationService:
        raise ImportError("Notification service not available")

    # UnifiedNotificationService doesn't take config, just return instance
    return NotificationService()


def create_websocket_manager(config: Optional[dict] = None):
    """Create a standalone websocket manager."""
    if not WebSocketManager or not WebSocketConfig:
        raise ImportError("WebSocket manager not available")

    config = config or get_default_config().get("websockets", {})
    ws_config = WebSocketConfig(**config)
    return WebSocketManager(ws_config)


def create_event_bus(config: Optional[dict] = None):
    """Create a standalone event bus."""
    if not EventBus:
        raise ImportError("Event bus not available")

    config = config or get_default_config().get("events", {})
    adapter = config.get("default_adapter", "memory")

    if adapter == "memory":
        from .events.adapters import create_memory_bus
        return create_memory_bus(config)
    elif adapter == "redis":
        try:
            from .events.adapters import create_redis_bus
            return create_redis_bus(config)
        except ImportError:
            import warnings
            warnings.warn("Redis adapter not available, falling back to memory")
            from .events.adapters import create_memory_bus
            return create_memory_bus(config)
    else:
        raise ValueError(f"Unknown event adapter: {adapter}")
