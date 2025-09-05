"""
Plugin Health Monitoring System
Provides comprehensive health monitoring for infrastructure plugins
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from dotmac.application import standard_exception_handler
from dotmac_shared.core.logging import get_logger

from .base import BasePlugin, PluginStatus
from .infrastructure_manager import InfrastructurePluginManager

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric."""

    name: str
    value: Any
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@dataclass
class PluginHealthReport:
    """Comprehensive health report for a plugin."""

    plugin_name: str
    plugin_type: str
    overall_status: HealthStatus
    last_check: datetime
    check_duration_ms: float
    metrics: list[HealthMetric] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider_specific_data: dict[str, Any] = field(default_factory=dict)


class PluginHealthMonitor:
    """
    Monitors the health of infrastructure plugins.
    Provides periodic health checks, alerting, and detailed health reports.
    """

    def __init__(self, infrastructure_manager: InfrastructurePluginManager):
        self.infrastructure_manager = infrastructure_manager
        self.health_reports: dict[str, PluginHealthReport] = {}
        self.monitoring_active = False
        self.check_interval = 60  # Default 60 seconds
        self.alert_callbacks: list[Callable] = []
        self._monitoring_task: Optional[asyncio.Task] = None

        # Health check thresholds
        self.response_time_warning = 5000  # ms
        self.response_time_critical = 10000  # ms

    @standard_exception_handler
    async def start_monitoring(self, check_interval: Optional[int] = None) -> bool:
        """Start the health monitoring service."""
        try:
            if self.monitoring_active:
                logger.info("Plugin health monitoring is already active")
                return True

            if check_interval:
                self.check_interval = check_interval

            self.monitoring_active = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

            logger.info(
                f"✅ Started plugin health monitoring (interval: {self.check_interval}s)"
            )
            return True

        except (OSError, RuntimeError):
            logger.exception("Failed to start health monitoring")
            return False

    async def stop_monitoring(self):
        """Stop the health monitoring service."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("✅ Stopped plugin health monitoring")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self.monitoring_active:
                await self.check_all_plugins_health()
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
        except (OSError, RuntimeError):
            logger.exception("Error in health monitoring loop")

    @standard_exception_handler
    async def check_all_plugins_health(self) -> dict[str, PluginHealthReport]:
        """Check health of all registered plugins."""
        reports = {}

        # Check deployment providers
        for provider_name in self.infrastructure_manager.list_deployment_providers():
            provider = self.infrastructure_manager.get_deployment_provider(
                provider_name
            )
            if provider:
                report = await self._check_plugin_health(
                    provider, provider_name, "deployment"
                )
                reports[provider_name] = report

        # Check DNS providers
        for provider_name in self.infrastructure_manager.list_dns_providers():
            provider = self.infrastructure_manager.get_dns_provider(provider_name)
            if provider:
                report = await self._check_plugin_health(provider, provider_name, "dns")
                reports[provider_name] = report

        # Update stored reports
        self.health_reports.update(reports)

        # Check for alerts
        await self._process_health_alerts(reports)

        logger.debug(f"Health check completed for {len(reports)} plugins")
        return reports

    async def _check_plugin_health(
        self, plugin: BasePlugin, provider_name: str, plugin_type: str
    ) -> PluginHealthReport:
        """Perform comprehensive health check for a single plugin."""
        start_time = datetime.now(timezone.utc)

        report = PluginHealthReport(
            plugin_name=provider_name,
            plugin_type=plugin_type,
            overall_status=HealthStatus.UNKNOWN,
            last_check=start_time,
            check_duration_ms=0,
        )

        try:
            # Basic plugin status check
            if plugin.status == PluginStatus.ERROR:
                report.overall_status = HealthStatus.UNHEALTHY
                report.errors.append(f"Plugin is in ERROR status: {plugin.last_error}")
                return report
            elif plugin.status != PluginStatus.ACTIVE:
                report.overall_status = HealthStatus.DEGRADED
                report.warnings.append(
                    f"Plugin is not ACTIVE (status: {plugin.status})"
                )

            # Provider-specific health check
            health_result = await plugin.health_check()
            check_duration = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            report.check_duration_ms = check_duration

            # Analyze health check results
            if health_result.get("healthy", False):
                # Check response time
                response_time = health_result.get("response_time_ms", check_duration)

                if response_time > self.response_time_critical:
                    report.overall_status = HealthStatus.DEGRADED
                    report.warnings.append(f"High response time: {response_time:.1f}ms")
                elif response_time > self.response_time_warning:
                    report.overall_status = HealthStatus.DEGRADED
                    report.warnings.append(
                        f"Elevated response time: {response_time:.1f}ms"
                    )
                else:
                    report.overall_status = HealthStatus.HEALTHY

                # Add response time metric
                report.metrics.append(
                    HealthMetric(
                        name="response_time",
                        value=response_time,
                        unit="ms",
                        status=self._get_response_time_status(response_time),
                        threshold_warning=self.response_time_warning,
                        threshold_critical=self.response_time_critical,
                    )
                )

            else:
                report.overall_status = HealthStatus.UNHEALTHY
                error_msg = health_result.get("error", "Health check failed")
                report.errors.append(error_msg)

            # Store provider-specific data
            report.provider_specific_data = {
                k: v
                for k, v in health_result.items()
                if k not in ["healthy", "error", "response_time_ms"]
            }

            # Type-specific health checks
            await self._add_type_specific_metrics(plugin, plugin_type, report)

        except (OSError, TimeoutError, ConnectionError) as e:
            report.overall_status = HealthStatus.UNHEALTHY
            report.errors.append(f"Health check exception: {e}")
            report.check_duration_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            logger.exception("Health check failed for %s", provider_name)

        return report

    def _get_response_time_status(self, response_time: float) -> HealthStatus:
        """Determine health status based on response time."""
        if response_time > self.response_time_critical:
            return HealthStatus.UNHEALTHY
        elif response_time > self.response_time_warning:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def _add_type_specific_metrics(
        self, plugin: BasePlugin, plugin_type: str, report: PluginHealthReport
    ):
        """Add type-specific health metrics."""
        if plugin_type == "deployment":
            # Deployment provider specific metrics
            if hasattr(plugin, "get_supported_providers"):
                providers = plugin.get_supported_providers()
                report.metrics.append(
                    HealthMetric(
                        name="supported_providers",
                        value=len(providers),
                        status=HealthStatus.HEALTHY,
                        message=f"Providers: {', '.join(providers)}",
                    )
                )

            if hasattr(plugin, "get_supported_orchestrators"):
                orchestrators = plugin.get_supported_orchestrators()
                report.metrics.append(
                    HealthMetric(
                        name="supported_orchestrators",
                        value=len(orchestrators),
                        status=HealthStatus.HEALTHY,
                        message=f"Orchestrators: {', '.join(orchestrators)}",
                    )
                )

        elif plugin_type == "dns":
            # DNS provider specific metrics
            if hasattr(plugin, "get_supported_record_types"):
                record_types = plugin.get_supported_record_types()
                report.metrics.append(
                    HealthMetric(
                        name="supported_record_types",
                        value=len(record_types),
                        status=HealthStatus.HEALTHY,
                        message=f"Types: {', '.join(record_types)}",
                    )
                )

    async def _process_health_alerts(self, reports: dict[str, PluginHealthReport]):
        """Process health reports and trigger alerts if needed."""
        for provider_name, report in reports.items():
            # Check for status changes
            previous_report = self.health_reports.get(provider_name)

            if (
                previous_report
                and previous_report.overall_status != report.overall_status
            ):
                await self._trigger_alert(
                    "status_change",
                    provider_name,
                    f"Status changed from {previous_report.overall_status} to {report.overall_status}",
                    report,
                )

            # Check for new errors
            if report.overall_status == HealthStatus.UNHEALTHY:
                await self._trigger_alert(
                    "unhealthy",
                    provider_name,
                    f"Plugin is unhealthy: {', '.join(report.errors)}",
                    report,
                )

    async def _trigger_alert(
        self,
        alert_type: str,
        provider_name: str,
        message: str,
        report: PluginHealthReport,
    ):
        """Trigger health alert callbacks."""
        alert_data = {
            "type": alert_type,
            "provider": provider_name,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "report": report,
        }

        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except (OSError, RuntimeError):
                logger.exception("Alert callback failed for %s", callback.__name__)

    def add_alert_callback(self, callback: Callable):
        """Add a callback for health alerts."""
        self.alert_callbacks.append(callback)
        logger.info(f"Added health alert callback: {callback.__name__}")

    def remove_alert_callback(self, callback: Callable):
        """Remove a health alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            logger.info(f"Removed health alert callback: {callback.__name__}")

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall health summary."""
        if not self.health_reports:
            return {
                "overall_status": HealthStatus.UNKNOWN,
                "total_plugins": 0,
                "healthy_count": 0,
                "degraded_count": 0,
                "unhealthy_count": 0,
                "last_check": None,
            }

        healthy_count = sum(
            1
            for r in self.health_reports.values()
            if r.overall_status == HealthStatus.HEALTHY
        )
        degraded_count = sum(
            1
            for r in self.health_reports.values()
            if r.overall_status == HealthStatus.DEGRADED
        )
        unhealthy_count = sum(
            1
            for r in self.health_reports.values()
            if r.overall_status == HealthStatus.UNHEALTHY
        )

        # Determine overall status
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        elif healthy_count > 0:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        last_check = (
            max(r.last_check for r in self.health_reports.values())
            if self.health_reports
            else None
        )

        return {
            "overall_status": overall_status,
            "total_plugins": len(self.health_reports),
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "unknown_count": len(self.health_reports)
            - healthy_count
            - degraded_count
            - unhealthy_count,
            "last_check": last_check.isoformat() if last_check else None,
            "monitoring_active": self.monitoring_active,
            "check_interval": self.check_interval,
        }

    def get_plugin_health(self, plugin_name: str) -> Optional[PluginHealthReport]:
        """Get health report for a specific plugin."""
        return self.health_reports.get(plugin_name)

    def get_unhealthy_plugins(self) -> list[PluginHealthReport]:
        """Get all unhealthy plugins."""
        return [
            report
            for report in self.health_reports.values()
            if report.overall_status == HealthStatus.UNHEALTHY
        ]

    def get_degraded_plugins(self) -> list[PluginHealthReport]:
        """Get all degraded plugins."""
        return [
            report
            for report in self.health_reports.values()
            if report.overall_status == HealthStatus.DEGRADED
        ]

    @standard_exception_handler
    async def force_health_check(
        self, plugin_name: Optional[str] = None
    ) -> dict[str, PluginHealthReport]:
        """Force an immediate health check for specific plugin or all plugins."""
        if plugin_name:
            # Check specific plugin
            provider = self.infrastructure_manager.get_deployment_provider(
                plugin_name
            ) or self.infrastructure_manager.get_dns_provider(plugin_name)

            if not provider:
                raise ValueError(f"Plugin not found: {plugin_name}")

            plugin_type = (
                "deployment"
                if plugin_name
                in self.infrastructure_manager.list_deployment_providers()
                else "dns"
            )
            report = await self._check_plugin_health(provider, plugin_name, plugin_type)
            self.health_reports[plugin_name] = report

            return {plugin_name: report}
        else:
            # Check all plugins
            return await self.check_all_plugins_health()

    def export_health_data(self) -> dict[str, Any]:
        """Export all health data for analysis or storage."""
        return {
            "summary": self.get_health_summary(),
            "reports": {
                name: {
                    "plugin_name": report.plugin_name,
                    "plugin_type": report.plugin_type,
                    "overall_status": report.overall_status.value,
                    "last_check": report.last_check.isoformat(),
                    "check_duration_ms": report.check_duration_ms,
                    "metrics": [
                        {
                            "name": metric.name,
                            "value": metric.value,
                            "unit": metric.unit,
                            "timestamp": metric.timestamp.isoformat(),
                            "status": metric.status.value,
                            "message": metric.message,
                        }
                        for metric in report.metrics
                    ],
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "provider_data": report.provider_specific_data,
                }
                for name, report in self.health_reports.items()
            },
        }
