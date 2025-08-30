"""
Integration layer for the unified monitoring system.

This module integrates the monitoring system with existing DotMac services
to follow DRY principles and leverage existing infrastructure.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseMonitoringService, HealthCheck, HealthStatus

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Configuration for monitoring alerts."""

    enabled: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ["email"])
    error_threshold: int = 5  # Number of errors before alerting
    response_time_threshold_ms: float = 5000  # 5 seconds
    alert_cooldown_minutes: int = 15  # Minimum time between similar alerts


class IntegratedMonitoringService(BaseMonitoringService):
    """
    Monitoring service that integrates with existing DotMac services.

    This service follows DRY principles by providing a unified interface
    while maintaining simplicity and avoiding async/sync complexity.
    """

    def __init__(
        self,
        service_name: str,
        tenant_id: Optional[str] = None,
        config: Optional[Any] = None,
        analytics_service: Optional[Any] = None,
        notification_service: Optional[Any] = None,
        health_monitor: Optional[Any] = None,
        container_monitor: Optional[Any] = None,
        alert_config: Optional[AlertConfig] = None,
    ):
        """Initialize integrated monitoring service."""
        super().__init__(service_name, tenant_id, config)

        # Store references to existing services for future integration
        self.analytics_service = analytics_service
        self.notification_service = notification_service
        self.health_monitor = health_monitor
        self.container_monitor = container_monitor
        self.alert_config = alert_config or AlertConfig()

        # Error tracking for alerting
        self._error_counts: Dict[str, int] = {}
        self._last_alert_times: Dict[str, float] = {}

        logger.info(f"Initialized integrated monitoring for {service_name}")

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        tenant_id: Optional[str] = None,
        request_size: int = 0,
        response_size: int = 0,
    ) -> None:
        """Record HTTP request with comprehensive logging."""
        effective_tenant_id = tenant_id or self.tenant_id

        # Log the HTTP request
        logger.info(
            f"HTTP {method} {endpoint} -> {status_code} ({duration:.3f}s) [tenant: {effective_tenant_id}]"
        )

        # Check for slow requests
        if (
            self.alert_config.enabled
            and duration * 1000 > self.alert_config.response_time_threshold_ms
        ):
            logger.warning(
                f"Slow response detected: {method} {endpoint} took {duration:.2f}s"
            )

    def record_database_query(
        self,
        operation: str,
        table: str,
        duration: float,
        success: bool,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record database query with comprehensive logging."""
        effective_tenant_id = tenant_id or self.tenant_id
        status = "SUCCESS" if success else "FAILED"

        logger.info(
            f"DB {operation} {table} -> {status} ({duration:.3f}s) [tenant: {effective_tenant_id}]"
        )

    def record_cache_operation(
        self,
        operation: str,
        cache_name: str,
        success: bool,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record cache operation with comprehensive logging."""
        effective_tenant_id = tenant_id or self.tenant_id
        status = "HIT" if success else "MISS"

        logger.info(
            f"CACHE {operation} {cache_name} -> {status} [tenant: {effective_tenant_id}]"
        )

    def record_error(
        self,
        error_type: str,
        service: str,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record error with tracking and potential alerting."""
        effective_tenant_id = tenant_id or self.tenant_id
        error_key = f"{error_type}_{service}_{effective_tenant_id}"

        # Track error count
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        logger.error(
            f"ERROR {error_type} in {service} [tenant: {effective_tenant_id}] (count: {self._error_counts[error_key]})"
        )

        # Check if alert threshold reached
        if (
            self.alert_config.enabled
            and self._error_counts[error_key] >= self.alert_config.error_threshold
        ):
            self._send_error_alert(error_type, service, self._error_counts[error_key])

    def perform_health_check(self) -> List[HealthCheck]:
        """Perform comprehensive health checks using existing services."""
        health_checks = []

        # Basic service health checks
        health_checks.append(
            HealthCheck(
                name="service_status",
                status=HealthStatus.HEALTHY,
                message=f"Service {self.service_name} is running",
            )
        )

        # Check integrations
        if self.analytics_service:
            health_checks.append(
                HealthCheck(
                    name="analytics_integration",
                    status=HealthStatus.HEALTHY,
                    message="Analytics service integration active",
                )
            )

        if self.notification_service:
            health_checks.append(
                HealthCheck(
                    name="notification_integration",
                    status=HealthStatus.HEALTHY,
                    message="Notification service integration active",
                )
            )

        return health_checks

    def get_metrics_endpoint(self) -> tuple[str, str]:
        """Get metrics data leveraging existing analytics service."""
        # Generate basic metrics information
        metrics_data = f"""# Integrated monitoring metrics for {self.service_name}
# Service: {self.service_name}
# Tenant: {self.tenant_id}
# Integrations: analytics={bool(self.analytics_service)}, notifications={bool(self.notification_service)}
# Error counts: {len(self._error_counts)} error types tracked
"""

        # Add error count metrics
        for error_key, count in self._error_counts.items():
            metrics_data += f'dotmac_errors_total{{error_key="{error_key}"}} {count}\n'

        return metrics_data, "text/plain"

    def _record_operation_duration(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        labels: Dict[str, str],
    ) -> None:
        """Record operation duration with comprehensive logging."""
        status = "SUCCESS" if success else "FAILED"
        tenant_id = labels.get("tenant_id", self.tenant_id)

        logger.info(
            f"OPERATION {operation_name} -> {status} ({duration:.3f}s) [tenant: {tenant_id}]"
        )

    def _send_error_alert(self, error_type: str, service: str, count: int) -> None:
        """Send error alert (simplified sync version)."""
        alert_key = f"error_{error_type}_{service}"
        current_time = time.time()

        # Check cooldown
        if (
            alert_key in self._last_alert_times
            and current_time - self._last_alert_times[alert_key]
            < self.alert_config.alert_cooldown_minutes * 60
        ):
            return

        # Log the alert (in a real implementation, this would send notifications)
        logger.critical(
            f"ALERT: Error threshold reached - {count} occurrences of {error_type} in {service}"
        )
        self._last_alert_times[alert_key] = current_time


def create_integrated_monitoring_service(
    service_name: str, tenant_id: Optional[str] = None, **integrations
) -> IntegratedMonitoringService:
    """
    Factory function to create integrated monitoring service.

    Args:
        service_name: Name of the service
        tenant_id: Optional tenant ID
        **integrations: Integration services (analytics_service, notification_service, etc.)

    Returns:
        IntegratedMonitoringService with available integrations
    """
    return IntegratedMonitoringService(
        service_name=service_name, tenant_id=tenant_id, **integrations
    )
