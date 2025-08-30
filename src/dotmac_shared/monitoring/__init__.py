"""
DotMac Unified Monitoring System

This package provides a consolidated monitoring interface that eliminates
duplication across services while providing comprehensive observability.

Main Components:
- BaseMonitoringService: Abstract base class for all monitoring implementations
- SignOzMonitoringService: Native SignOz monitoring with OpenTelemetry
- NoOpMonitoringService: No-operation monitoring for testing/disabled environments
- ContainerHealthMonitor: Comprehensive container health monitoring
"""

# Import audit functionality
from .audit import (
    AuditActor,
    AuditContext,
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditOutcome,
    AuditResource,
    AuditSeverity,
    AuditStore,
    InMemoryAuditStore,
    create_audit_event,
    create_audit_logger,
    get_audit_logger,
    init_audit_logger,
)
from .audit_config import (
    APIConfig,
    AuditConfig,
    ComplianceConfig,
    MiddlewareConfig,
    StorageConfig,
    create_audit_config_from_env,
    get_audit_config,
    init_audit_config,
)
from .base import (
    OPENTELEMETRY_AVAILABLE,
    SIGNOZ_AVAILABLE,
    BaseMonitoringService,
    HealthCheck,
    HealthStatus,
    MetricConfig,
    MetricType,
    NoOpMonitoringService,
    SignOzMonitoringService,
    create_monitoring_service,
    get_monitoring,
    init_monitoring,
)
from .config import (
    MonitoringConfig,
    MonitoringSettings,
    create_monitoring_config,
    load_monitoring_settings,
)
from .integrations import (
    AlertConfig,
    IntegratedMonitoringService,
    create_integrated_monitoring_service,
)

# Import utilities and configuration
from .utils import ConfigurationError, StorageError, ValidationError, get_logger

try:
    from .audit_api import FASTAPI_AVAILABLE as AUDIT_API_AVAILABLE
    from .audit_api import (
        AuditComplianceReport,
        AuditEventListResponse,
        AuditEventQuery,
        AuditEventResponse,
        AuditStatsResponse,
        create_audit_api_router,
        create_audit_health_router,
    )
except ImportError:
    AUDIT_API_AVAILABLE = False
    AuditEventQuery = AuditEventResponse = AuditEventListResponse = None
    AuditStatsResponse = AuditComplianceReport = None
    create_audit_api_router = create_audit_health_router = None

try:
    from .audit_middleware import FASTAPI_AVAILABLE as AUDIT_MIDDLEWARE_AVAILABLE
    from .audit_middleware import (
        AuditEventCollector,
        AuditMiddleware,
        create_audit_middleware,
    )
except ImportError:
    AUDIT_MIDDLEWARE_AVAILABLE = False
    AuditMiddleware = AuditEventCollector = create_audit_middleware = None

# Import container monitoring if available
try:
    from ..container_monitoring.core.health_monitor import (
        ContainerHealthMonitor,
        HealthReport,
        monitor_container_health,
    )

    CONTAINER_MONITORING_AVAILABLE = True
except ImportError:
    CONTAINER_MONITORING_AVAILABLE = False
    ContainerHealthMonitor = None
    HealthReport = None
    monitor_container_health = None

__all__ = [
    # Base monitoring classes
    "BaseMonitoringService",
    "SignOzMonitoringService",
    "NoOpMonitoringService",
    "SIGNOZ_AVAILABLE",
    "OPENTELEMETRY_AVAILABLE",
    # Configuration and types
    "MetricType",
    "MetricConfig",
    "HealthStatus",
    "HealthCheck",
    "MonitoringConfig",
    "MonitoringSettings",
    "create_monitoring_config",
    "load_monitoring_settings",
    # Integrated monitoring
    "IntegratedMonitoringService",
    "AlertConfig",
    "create_integrated_monitoring_service",
    # Factory and global functions
    "create_monitoring_service",
    "get_monitoring",
    "init_monitoring",
    # Container monitoring (if available)
    "ContainerHealthMonitor",
    "HealthReport",
    "monitor_container_health",
    "CONTAINER_MONITORING_AVAILABLE",
    # Audit functionality
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "AuditOutcome",
    "AuditActor",
    "AuditResource",
    "AuditContext",
    "AuditLogger",
    "AuditStore",
    "InMemoryAuditStore",
    "create_audit_logger",
    "create_audit_event",
    "get_audit_logger",
    "init_audit_logger",
    # Audit API (if available)
    "AuditEventQuery",
    "AuditEventResponse",
    "AuditEventListResponse",
    "AuditStatsResponse",
    "AuditComplianceReport",
    "create_audit_api_router",
    "create_audit_health_router",
    "AUDIT_API_AVAILABLE",
    # Audit middleware (if available)
    "AuditMiddleware",
    "AuditEventCollector",
    "create_audit_middleware",
    "AUDIT_MIDDLEWARE_AVAILABLE",
    # Utilities and configuration
    "get_logger",
    "ConfigurationError",
    "ValidationError",
    "StorageError",
    "AuditConfig",
    "StorageConfig",
    "APIConfig",
    "MiddlewareConfig",
    "ComplianceConfig",
    "create_audit_config_from_env",
    "init_audit_config",
    "get_audit_config",
]
