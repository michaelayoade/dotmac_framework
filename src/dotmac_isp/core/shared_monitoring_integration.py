"""
Shared monitoring integration for ISP modules.
Provides unified monitoring across all ISP services using dotmac_shared.monitoring.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from dotmac.communications.events import EventBus
from dotmac.communications.notifications import (
    NotificationService as UnifiedNotificationService,
)
from dotmac_shared.monitoring.integrations import (
    AlertConfig,
    IntegratedMonitoringService,
    create_integrated_monitoring_service,
)
from dotmac_shared.services_framework.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class ISPMonitoringManager:
    """
    Centralized monitoring manager for all ISP modules.
    Provides consistent monitoring and alerting across ISP services.
    """

    def __init__(
        self,
        tenant_id: str,
        analytics_service: Optional[AnalyticsService] = None,
        notification_service: Optional[UnifiedNotificationService] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.tenant_id = tenant_id
        self.analytics_service = analytics_service
        self.notification_service = notification_service
        self.event_bus = event_bus

        # ISP-specific monitoring services for each module
        self._module_monitors: dict[str, IntegratedMonitoringService] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the monitoring manager and all module monitors."""
        try:
            # Initialize monitoring for core ISP modules
            await self._initialize_module_monitoring()

            self._initialized = True
            logger.info(f"✅ ISP Monitoring Manager initialized for tenant {self.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize ISP Monitoring Manager: {e}")
            return False

    async def _initialize_module_monitoring(self):
        """Initialize monitoring for each ISP module."""

        # ISP-specific alert configurations
        isp_alert_config = AlertConfig(
            enabled=True,
            notification_channels=["email", "sms"],
            error_threshold=3,  # Lower threshold for ISP services
            response_time_threshold_ms=2000,  # 2 seconds for ISP services
            alert_cooldown_minutes=10,
        )
        # Core ISP modules to monitor
        isp_modules = [
            "billing",
            "identity",
            "network_monitoring",
            "network_integration",
            "network_visualization",
            "captive_portal",
            "services",
            "portal_management",
            "analytics",
        ]

        for module in isp_modules:
            try:
                monitor = create_integrated_monitoring_service(
                    service_name=f"isp_{module}",
                    tenant_id=self.tenant_id,
                    analytics_service=self.analytics_service,
                    notification_service=self.notification_service,
                    alert_config=isp_alert_config,
                )
                self._module_monitors[module] = monitor
                logger.info(f"✅ Initialized monitoring for ISP module: {module}")

            except Exception as e:
                logger.error(f"❌ Failed to initialize monitoring for module {module}: {e}")

    def get_module_monitor(self, module: str) -> Optional[IntegratedMonitoringService]:
        """Get monitoring service for a specific ISP module."""
        return self._module_monitors.get(module)

    # Billing monitoring
    async def record_billing_operation(
        self,
        operation: str,
        duration: float,
        success: bool,
        customer_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ):
        """Record billing operation metrics."""
        monitor = self.get_module_monitor("billing")
        if monitor:
            monitor.record_http_request(
                method="POST",
                endpoint=f"/billing/{operation}",
                status_code=200 if success else 500,
                duration=duration,
                tenant_id=self.tenant_id,
            )
            # Publish event for cross-service tracking
            if self.event_bus:
                await self.event_bus.publish(
                    "monitoring.billing_operation",
                    {
                        "operation": operation,
                        "success": success,
                        "duration": duration,
                        "customer_id": customer_id,
                        "invoice_id": invoice_id,
                        "tenant_id": self.tenant_id,
                    },
                )

    # Identity monitoring
    async def record_identity_operation(
        self,
        operation: str,
        duration: float,
        success: bool,
        customer_id: Optional[str] = None,
    ):
        """Record identity operation metrics."""
        monitor = self.get_module_monitor("identity")
        if monitor:
            monitor.record_http_request(
                method="POST",
                endpoint=f"/identity/{operation}",
                status_code=200 if success else 500,
                duration=duration,
                tenant_id=self.tenant_id,
            )

    # Network monitoring
    async def record_network_check(
        self,
        device_id: str,
        check_type: str,
        duration: float,
        success: bool,
        metrics: Optional[dict[str, Any]] = None,
    ):
        """Record network monitoring check."""
        monitor = self.get_module_monitor("network_monitoring")
        if monitor:
            monitor.record_database_query(
                operation=f"network_check_{check_type}",
                table="network_devices",
                duration=duration,
                success=success,
                tenant_id=self.tenant_id,
            )
            # Record network-specific metrics
            if success and metrics:
                if self.analytics_service:
                    await self.analytics_service.track_event(
                        event_type="network_device_metrics",
                        entity_id=device_id,
                        metadata={
                            "check_type": check_type,
                            "metrics": metrics,
                            "tenant_id": self.tenant_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

    # Service provisioning monitoring
    async def record_service_provisioning(
        self,
        customer_id: str,
        service_type: str,
        duration: float,
        success: bool,
        error_details: Optional[str] = None,
    ):
        """Record service provisioning metrics."""
        monitor = self.get_module_monitor("services")
        if monitor:
            if not success:
                monitor.record_error(
                    error_type="service_provisioning_failed",
                    service="isp_services",
                    tenant_id=self.tenant_id,
                )
            else:
                monitor.record_http_request(
                    method="POST",
                    endpoint="/services/provision",
                    status_code=200,
                    duration=duration,
                    tenant_id=self.tenant_id,
                )

    # Captive portal monitoring
    async def record_captive_portal_auth(
        self,
        auth_method: str,
        duration: float,
        success: bool,
        user_count: Optional[int] = None,
    ):
        """Record captive portal authentication metrics."""
        monitor = self.get_module_monitor("captive_portal")
        if monitor:
            monitor.record_http_request(
                method="POST",
                endpoint=f"/captive-portal/auth/{auth_method}",
                status_code=200 if success else 401,
                duration=duration,
                tenant_id=self.tenant_id,
            )

    # Error tracking across all modules
    async def record_module_error(
        self,
        module: str,
        error_type: str,
        error_details: Optional[str] = None,
        customer_id: Optional[str] = None,
    ):
        """Record error from any ISP module."""
        monitor = self.get_module_monitor(module)
        if monitor:
            monitor.record_error(error_type=error_type, service=f"isp_{module}", tenant_id=self.tenant_id)
            # Log for troubleshooting
            logger.error(f"ISP {module} error: {error_type} - {error_details}")

            # Publish event for potential automated remediation
            if self.event_bus:
                await self.event_bus.publish(
                    f"monitoring.{module}_error",
                    {
                        "error_type": error_type,
                        "error_details": error_details,
                        "customer_id": customer_id,
                        "tenant_id": self.tenant_id,
                        "module": module,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

    # Health checks
    async def get_all_health_checks(self) -> dict[str, Any]:
        """Get health checks from all monitored ISP modules."""
        health_checks = {
            "monitoring_manager": {
                "status": "healthy" if self._initialized else "not_initialized",
                "tenant_id": self.tenant_id,
                "modules_monitored": len(self._module_monitors),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        # Get health from each module monitor
        for module, monitor in self._module_monitors.items():
            try:
                module_health = monitor.perform_health_check()
                health_checks[f"isp_{module}"] = {
                    "status": ("healthy" if all(hc.status.value == "healthy" for hc in module_health) else "degraded"),
                    "checks": [
                        {
                            "name": hc.name,
                            "status": hc.status.value,
                            "message": hc.message,
                        }
                        for hc in module_health
                    ],
                }
            except Exception as e:
                health_checks[f"isp_{module}"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        return health_checks

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get aggregated performance metrics from all ISP modules."""
        try:
            metrics = {
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "modules": {},
            }

            for module, monitor in self._module_monitors.items():
                try:
                    module_metrics, _ = monitor.get_metrics_endpoint()
                    metrics["modules"][module] = {
                        "status": "available",
                        "metrics_data": module_metrics,
                    }
                except Exception as e:
                    metrics["modules"][module] = {
                        "status": "unavailable",
                        "error": str(e),
                    }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e), "tenant_id": self.tenant_id}


# Global monitoring managers per tenant (will be managed by application factory)
_monitoring_managers: dict[str, ISPMonitoringManager] = {}


def get_isp_monitoring_manager(tenant_id: str) -> ISPMonitoringManager:
    """Get or create ISP monitoring manager for tenant."""
    if tenant_id not in _monitoring_managers:
        _monitoring_managers[tenant_id] = ISPMonitoringManager(tenant_id)
    return _monitoring_managers[tenant_id]


async def initialize_isp_monitoring_managers() -> bool:
    """Initialize all monitoring managers."""
    try:
        for monitoring_manager in _monitoring_managers.values():
            await monitoring_manager.initialize()
        logger.info("✅ All ISP monitoring managers initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize ISP monitoring managers: {e}")
        return False
