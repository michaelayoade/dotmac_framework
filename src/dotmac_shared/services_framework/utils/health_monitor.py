"""
Health monitoring utilities for the DotMac Services Framework.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

from ..core.base import BaseService, ServiceStatus
from ..core.registry import ServiceRegistry

logger = logging.getLogger(__name__)


@dataclass
class HealthAlert:
    """Health alert information."""

    service_name: str
    alert_type: str  # "status_change", "health_degraded", "service_down", "recovery"
    message: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthMonitorConfig:
    """Health monitor configuration."""

    check_interval_seconds: int = 30
    alert_threshold_seconds: int = 300  # 5 minutes
    recovery_confirmation_checks: int = 3
    max_history_entries: int = 1000
    enable_status_change_alerts: bool = True
    enable_health_degradation_alerts: bool = True
    enable_recovery_alerts: bool = True

    # Alert severity thresholds
    critical_response_time_ms: float = 5000  # 5 seconds
    warning_response_time_ms: float = 1000  # 1 second


class HealthMonitor:
    """Health monitoring utility for service registry."""

    def __init__(
        self,
        registry: ServiceRegistry,
        config: HealthMonitorConfig = None,
        alert_callback: Optional[Callable[[HealthAlert], None]] = None,
    ):
        self.registry = registry
        self.config = config or HealthMonitorConfig()
        self.alert_callback = alert_callback

        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._service_history: dict[str, list[dict[str, Any]]] = {}
        self._last_known_status: dict[str, ServiceStatus] = {}
        self._alert_history: list[HealthAlert] = []
        self._recovery_confirmations: dict[str, int] = {}

    async def start_monitoring(self):
        """Start continuous health monitoring."""
        if self._monitoring:
            logger.warning("Health monitoring is already running")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(
            f"Started health monitoring with {self.config.check_interval_seconds}s interval"
        )

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped health monitoring")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self._monitoring:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.check_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Health monitoring loop error: {e}")
            self._monitoring = False

    async def _perform_health_checks(self):
        """Perform health checks on all services."""
        try:
            # Get all services
            services = list(self.registry.services.items())

            # Run health checks in parallel
            tasks = []
            for service_name, service in services:
                task = asyncio.create_task(
                    self._check_service_health(service_name, service)
                )
                tasks.append(task)

            # Wait for all health checks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error performing health checks: {e}")

    async def _check_service_health(self, service_name: str, service: BaseService):
        """Check health of a single service."""
        try:
            start_time = time.time()

            # Get current status
            current_status = service.get_status()

            # Perform health check
            health = await service.health_check()

            response_time = time.time() - start_time

            # Record health data
            health_data = {
                "timestamp": time.time(),
                "status": current_status.value,
                "health_status": health.status.value,
                "message": health.message,
                "response_time_ms": round(response_time * 1000, 2),
                "details": health.details,
            }

            self._record_health_data(service_name, health_data)

            # Check for status changes
            await self._check_status_changes(service_name, current_status)

            # Check for health degradation
            await self._check_health_degradation(service_name, health_data)

            # Check for recovery
            await self._check_service_recovery(service_name, current_status)

        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")

            # Record error in health data
            error_data = {
                "timestamp": time.time(),
                "status": "error",
                "health_status": "error",
                "message": f"Health check failed: {e}",
                "response_time_ms": None,
                "error": str(e),
            }

            self._record_health_data(service_name, error_data)

    def _record_health_data(self, service_name: str, health_data: dict[str, Any]):
        """Record health data for a service."""
        if service_name not in self._service_history:
            self._service_history[service_name] = []

        history = self._service_history[service_name]
        history.append(health_data)

        # Limit history size
        if len(history) > self.config.max_history_entries:
            history.pop(0)  # Remove oldest entry

    async def _check_status_changes(
        self, service_name: str, current_status: ServiceStatus
    ):
        """Check for service status changes."""
        if not self.config.enable_status_change_alerts:
            return

        last_status = self._last_known_status.get(service_name)

        if last_status and last_status != current_status:
            # Status changed
            severity = self._get_status_change_severity(last_status, current_status)

            alert = HealthAlert(
                service_name=service_name,
                alert_type="status_change",
                message=f"Service {service_name} status changed from {last_status.value} to {current_status.value}",
                severity=severity,
                timestamp=time.time(),
                details={
                    "previous_status": last_status.value,
                    "current_status": current_status.value,
                },
            )

            await self._send_alert(alert)

        self._last_known_status[service_name] = current_status

    async def _check_health_degradation(
        self, service_name: str, health_data: dict[str, Any]
    ):
        """Check for health degradation."""
        if not self.config.enable_health_degradation_alerts:
            return

        response_time = health_data.get("response_time_ms")
        if response_time is None:
            return

        severity = None
        message = None

        if response_time > self.config.critical_response_time_ms:
            severity = "critical"
            message = f"Service {service_name} response time critically high: {response_time}ms"
        elif response_time > self.config.warning_response_time_ms:
            severity = "medium"
            message = (
                f"Service {service_name} response time elevated: {response_time}ms"
            )

        if severity and message:
            alert = HealthAlert(
                service_name=service_name,
                alert_type="health_degraded",
                message=message,
                severity=severity,
                timestamp=time.time(),
                details={
                    "response_time_ms": response_time,
                    "critical_threshold_ms": self.config.critical_response_time_ms,
                    "warning_threshold_ms": self.config.warning_response_time_ms,
                },
            )

            await self._send_alert(alert)

    async def _check_service_recovery(
        self, service_name: str, current_status: ServiceStatus
    ):
        """Check for service recovery."""
        if not self.config.enable_recovery_alerts:
            return

        if current_status == ServiceStatus.READY:
            # Service is ready, check if this is a recovery
            confirmations = self._recovery_confirmations.get(service_name, 0)

            if confirmations == 0:
                # First time seeing this service ready, start confirmation count
                self._recovery_confirmations[service_name] = 1
            elif confirmations < self.config.recovery_confirmation_checks:
                # Increment confirmation count
                self._recovery_confirmations[service_name] = confirmations + 1
            elif confirmations == self.config.recovery_confirmation_checks:
                # Confirmed recovery
                alert = HealthAlert(
                    service_name=service_name,
                    alert_type="recovery",
                    message=f"Service {service_name} has recovered and is healthy",
                    severity="low",
                    timestamp=time.time(),
                    details={
                        "confirmation_checks": self.config.recovery_confirmation_checks
                    },
                )

                await self._send_alert(alert)

                # Reset confirmation count
                self._recovery_confirmations[service_name] = 0
        else:
            # Service is not ready, reset confirmation count
            self._recovery_confirmations[service_name] = 0

    def _get_status_change_severity(
        self, previous: ServiceStatus, current: ServiceStatus
    ) -> str:
        """Get severity level for status changes."""
        # Critical: Any service going to ERROR or SHUTDOWN
        if current in [ServiceStatus.ERROR, ServiceStatus.SHUTDOWN]:
            return "critical"

        # High: READY service going to any non-READY state
        if previous == ServiceStatus.READY and current != ServiceStatus.READY:
            return "high"

        # Medium: Service going to INITIALIZING (potential restart)
        if current == ServiceStatus.INITIALIZING:
            return "medium"

        # Low: Other status changes
        return "low"

    async def _send_alert(self, alert: HealthAlert):
        """Send health alert."""
        # Add to alert history
        self._alert_history.append(alert)

        # Limit alert history size
        if len(self._alert_history) > self.config.max_history_entries:
            self._alert_history.pop(0)

        # Call alert callback if provided
        if self.alert_callback:
            try:
                if asyncio.iscoroutinefunction(self.alert_callback):
                    await self.alert_callback(alert)
                else:
                    self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        # Log alert
        log_level = logging.ERROR if alert.severity == "critical" else logging.WARNING
        logger.log(
            log_level, f"Health Alert [{alert.severity.upper()}]: {alert.message}"
        )

    def get_service_health_history(
        self, service_name: str, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Get health history for a service."""
        history = self._service_history.get(service_name, [])

        if limit:
            return history[-limit:]

        return history.copy()

    def get_recent_alerts(
        self, limit: int = 50, severity: Optional[str] = None
    ) -> list[HealthAlert]:
        """Get recent health alerts."""
        alerts = self._alert_history.copy()

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            return alerts[:limit]

        return alerts

    def get_service_health_summary(self, service_name: str) -> dict[str, Any]:
        """Get health summary for a service."""
        history = self._service_history.get(service_name, [])

        if not history:
            return {"service": service_name, "no_data": True}

        recent_history = history[-10:]  # Last 10 checks

        # Calculate metrics
        response_times = [
            h.get("response_time_ms")
            for h in recent_history
            if h.get("response_time_ms") is not None
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else None
        )
        max_response_time = max(response_times) if response_times else None

        # Count status distribution
        statuses = [h.get("status") for h in recent_history]
        status_counts = {}
        for status in statuses:
            status_counts[status] = status_counts.get(status, 0) + 1

        latest = history[-1]

        return {
            "service": service_name,
            "latest_check": latest,
            "recent_checks_count": len(recent_history),
            "avg_response_time_ms": (
                round(avg_response_time, 2) if avg_response_time else None
            ),
            "max_response_time_ms": max_response_time,
            "status_distribution": status_counts,
            "total_history_entries": len(history),
        }

    def get_overall_health_status(self) -> dict[str, Any]:
        """Get overall health status of all services."""
        services_summary = {}
        total_services = len(self.registry.services)
        healthy_count = 0
        ready_count = 0
        error_count = 0

        for service_name in self.registry.list_services():
            service = self.registry.get_service(service_name)
            status = service.get_status()
            is_healthy = service.is_healthy()
            is_ready = service.is_ready()

            services_summary[service_name] = {
                "status": status.value,
                "healthy": is_healthy,
                "ready": is_ready,
            }

            if is_healthy:
                healthy_count += 1
            if is_ready:
                ready_count += 1
            if status == ServiceStatus.ERROR:
                error_count += 1

        return {
            "total_services": total_services,
            "healthy_services": healthy_count,
            "ready_services": ready_count,
            "error_services": error_count,
            "health_percentage": (
                round((healthy_count / total_services * 100), 1)
                if total_services > 0
                else 0
            ),
            "monitoring_active": self._monitoring,
            "check_interval_seconds": self.config.check_interval_seconds,
            "total_alerts": len(self._alert_history),
            "recent_critical_alerts": len(
                [a for a in self._alert_history[-50:] if a.severity == "critical"]
            ),
            "services": services_summary,
        }

    def get_monitoring_stats(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "monitoring_active": self._monitoring,
            "config": {
                "check_interval_seconds": self.config.check_interval_seconds,
                "alert_threshold_seconds": self.config.alert_threshold_seconds,
                "recovery_confirmation_checks": self.config.recovery_confirmation_checks,
                "max_history_entries": self.config.max_history_entries,
            },
            "statistics": {
                "services_monitored": len(self._service_history),
                "total_health_records": sum(
                    len(history) for history in self._service_history.values()
                ),
                "total_alerts": len(self._alert_history),
                "alert_distribution": {
                    severity: len(
                        [a for a in self._alert_history if a.severity == severity]
                    )
                    for severity in ["low", "medium", "high", "critical"]
                },
            },
        }
