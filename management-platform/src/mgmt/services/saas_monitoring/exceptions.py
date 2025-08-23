"""Exception classes for SaaS monitoring service."""


class MonitoringError(Exception):
    """Base exception for monitoring service errors."""
    pass


class HealthCheckFailedError(MonitoringError):
    """Raised when health checks fail."""
    pass


class AlertingError(MonitoringError):
    """Raised when alerting operations fail."""
    pass


class MetricsCollectionError(MonitoringError):
    """Raised when metrics collection fails."""
    pass


class SLAViolationError(MonitoringError):
    """Raised when SLA thresholds are violated."""
    pass


class TenantMonitoringError(MonitoringError):
    """Raised when tenant-specific monitoring fails."""
    pass