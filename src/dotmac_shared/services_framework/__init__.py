"""
DotMac Services Framework

Universal service lifecycle management system providing:
- Service registration and discovery
- Health monitoring and status management
- Configuration management and validation
- Dependency injection and initialization ordering
- Deployment-aware service creation
- Platform-agnostic business service architecture

This framework standardizes service architecture across all DotMac modules.
"""

from .core.base import BaseService, ConfigurableService, ServiceHealth, ServiceStatus
from .core.factory import (
    DeploymentAwareServiceFactory,
    ServiceCreationResult,
    ServiceFactory,
)
from .core.registry import ServiceConfig, ServiceRegistry

# Notification service now consolidated in dotmac_shared.notifications.core
from .services.analytics_service import (
    AnalyticsService,
    AnalyticsServiceConfig,
    create_analytics_service,
)
from .services.auth_service import AuthService, AuthServiceConfig, create_auth_service
from .services.payment_service import (
    PaymentService,
    PaymentServiceConfig,
    create_payment_service,
)
from .utils.discovery import ServiceDiscovery
from .utils.health_monitor import HealthMonitor

__version__ = "1.0.0"

__all__ = [
    # Core components
    "BaseService",
    "ConfigurableService",
    "ServiceStatus",
    "ServiceHealth",
    "ServiceRegistry",
    "ServiceConfig",
    "ServiceFactory",
    "DeploymentAwareServiceFactory",
    "ServiceCreationResult",
    # Business services
    "AuthService",
    "AuthServiceConfig",
    "PaymentService",
    "PaymentServiceConfig",
    # "NotificationService",  # Now in dotmac_shared.notifications.core
    # "None  # TODO: Fix None  # TODO: Fix NotificationServiceConfig",  # Now in dotmac_shared.notifications.core
    "AnalyticsService",
    "AnalyticsServiceConfig",
    # Service creators
    "create_auth_service",
    "create_payment_service",
    # "None  # TODO: Fix None  # TODO: Fix create_notification_service",  # Now in dotmac_shared.notifications.core
    "create_analytics_service",
    # Utilities
    "ServiceDiscovery",
    "HealthMonitor",
]
