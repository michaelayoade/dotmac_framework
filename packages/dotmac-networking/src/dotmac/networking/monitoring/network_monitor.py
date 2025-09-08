"""
Network Monitor - Comprehensive device monitoring orchestrator
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from dotmac.core import get_logger, retry_on_failure, standard_exception_handler

from .snmp_collector import SNMPCollector

logger = get_logger(__name__)

# Optional integrations - fallback to logging if not available
try:
    from dotmac_shared.monitoring.integrations import IntegratedMonitoringService

    _HAS_NOTIFICATION_INTEGRATION = True
except ImportError:
    _HAS_NOTIFICATION_INTEGRATION = False

try:
    from dotmac_benchmarking import BenchmarkRunner

    _HAS_METRICS_INTEGRATION = True
except ImportError:
    _HAS_METRICS_INTEGRATION = False


@dataclass
class MonitoringTarget:
    """Network device monitoring target"""

    host: str
    name: str
    device_type: str = "generic"
    snmp_community: str = "public"
    snmp_version: str = "2c"
    monitoring_enabled: bool = True
    alert_thresholds: Optional[dict[str, float]] = None


@dataclass
class DeviceMetrics:
    """Device performance metrics"""

    host: str
    timestamp: datetime
    cpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    uptime: Optional[int] = None
    interfaces: Optional[list[dict[str, Any]]] = None
    system_name: Optional[str] = None
    system_description: Optional[str] = None


class NetworkMonitor:
    """
    Comprehensive network monitoring service

    Orchestrates SNMP data collection, alerting, and metrics storage
    for ISP network infrastructure.
    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        notification_service: Optional[Any] = None,
        metrics_manager: Optional[Any] = None,
    ):
        self.config = config or {}
        self.snmp_collector = SNMPCollector()
        self.targets: dict[str, MonitoringTarget] = {}
        self.running = False
        self._monitoring_tasks: list[asyncio.Task] = []

        # Initialize optional integrations
        self.notification_service = self._init_notification_service(
            notification_service
        )
        self.metrics_manager = self._init_metrics_manager(metrics_manager)

        # Default alert thresholds
        self.default_thresholds = {
            "cpu_utilization": 80.0,
            "memory_utilization": 85.0,
            "interface_utilization": 90.0,
            "interface_errors_rate": 1.0,  # errors per second
        }

    def _init_notification_service(
        self, notification_service: Optional[Any]
    ) -> Optional[Any]:
        """Initialize notification service with fallback"""
        if notification_service:
            return notification_service

        if _HAS_NOTIFICATION_INTEGRATION:
            try:
                return IntegratedMonitoringService(
                    service_name="dotmac-networking",
                    tenant_id=self.config.get("tenant_id", "default"),
                )
            except Exception as e:
                logger.warning(f"Failed to initialize notification service: {e}")

        return None

    def _init_metrics_manager(self, metrics_manager: Optional[Any]) -> Optional[Any]:
        """Initialize metrics manager with fallback"""
        if metrics_manager:
            return metrics_manager

        if _HAS_METRICS_INTEGRATION:
            try:
                return BenchmarkRunner()
            except Exception as e:
                logger.warning(f"Failed to initialize metrics manager: {e}")

        return None

    def add_target(self, target: MonitoringTarget) -> None:
        """Add a device to monitoring"""
        self.targets[target.host] = target
        logger.info(f"Added monitoring target: {target.name} ({target.host})")

    def remove_target(self, host: str) -> None:
        """Remove a device from monitoring"""
        if host in self.targets:
            del self.targets[host]
            logger.info(f"Removed monitoring target: {host}")

    async def start_monitoring(self, interval: int = 60) -> None:
        """Start continuous monitoring of all targets"""
        if self.running:
            logger.warning("Monitoring already running")
            return

        self.running = True
        logger.info(f"Starting network monitoring with {len(self.targets)} targets")

        # Start monitoring tasks for each target
        for target in self.targets.values():
            if target.monitoring_enabled:
                task = asyncio.create_task(self._monitor_device_loop(target, interval))
                self._monitoring_tasks.append(task)

        logger.info(f"Started {len(self._monitoring_tasks)} monitoring tasks")

    async def stop_monitoring(self) -> None:
        """Stop monitoring all devices"""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping network monitoring...")

        # Cancel all monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)

        self._monitoring_tasks.clear()
        logger.info("Network monitoring stopped")

    @standard_exception_handler
    @retry_on_failure(max_attempts=3, delay=1.0)
    async def collect_device_metrics(
        self, target: MonitoringTarget
    ) -> Optional[DeviceMetrics]:
        """Collect metrics from a single device"""
        try:
            # Collect basic system information
            system_info = await self.snmp_collector.get_system_info(
                target.host, target.snmp_community
            )

            # Collect performance metrics
            cpu_util = await self.snmp_collector.get_cpu_utilization(
                target.host, target.snmp_community, target.device_type
            )

            memory_util = await self.snmp_collector.get_memory_utilization(
                target.host, target.snmp_community, target.device_type
            )

            # Collect interface statistics
            interfaces = await self.snmp_collector.get_interface_statistics(
                target.host, target.snmp_community
            )

            metrics = DeviceMetrics(
                host=target.host,
                timestamp=datetime.utcnow(),
                cpu_utilization=cpu_util,
                memory_utilization=memory_util,
                uptime=system_info.get("uptime"),
                interfaces=interfaces,
                system_name=system_info.get("name"),
                system_description=system_info.get("description"),
            )

            # Check alert thresholds
            await self._check_alerts(target, metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect metrics from {target.host}: {e}")
            return None

    async def _monitor_device_loop(
        self, target: MonitoringTarget, interval: int
    ) -> None:
        """Continuous monitoring loop for a single device"""
        logger.debug(f"Starting monitoring loop for {target.name}")

        while self.running:
            try:
                metrics = await self.collect_device_metrics(target)
                if metrics:
                    # Store metrics (implement your storage backend here)
                    await self._store_metrics(metrics)
                    logger.debug(f"Collected metrics from {target.name}")

                # Wait for next collection interval
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.debug(f"Monitoring cancelled for {target.name}")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for {target.name}: {e}")
                await asyncio.sleep(interval)  # Continue after error

    async def _check_alerts(
        self, target: MonitoringTarget, metrics: DeviceMetrics
    ) -> None:
        """Check metrics against alert thresholds"""
        thresholds = target.alert_thresholds or self.default_thresholds

        alerts = []

        # Check CPU utilization
        if (
            metrics.cpu_utilization is not None
            and metrics.cpu_utilization > thresholds.get("cpu_utilization", 80.0)
        ):
            alerts.append(
                {
                    "type": "cpu_high",
                    "message": f"High CPU utilization: {metrics.cpu_utilization:.1f}%",
                    "value": metrics.cpu_utilization,
                    "threshold": thresholds["cpu_utilization"],
                }
            )

        # Check memory utilization
        if (
            metrics.memory_utilization is not None
            and metrics.memory_utilization > thresholds.get("memory_utilization", 85.0)
        ):
            alerts.append(
                {
                    "type": "memory_high",
                    "message": f"High memory utilization: {metrics.memory_utilization:.1f}%",
                    "value": metrics.memory_utilization,
                    "threshold": thresholds["memory_utilization"],
                }
            )

        # Check interface utilization and errors
        if metrics.interfaces:
            for interface in metrics.interfaces:
                if interface.get("utilization", 0) > thresholds.get(
                    "interface_utilization", 90.0
                ):
                    alerts.append(
                        {
                            "type": "interface_high_util",
                            "message": f"High interface utilization on {interface['name']}: {interface['utilization']:.1f}%",
                            "interface": interface["name"],
                            "value": interface["utilization"],
                            "threshold": thresholds["interface_utilization"],
                        }
                    )

        # Send alerts if any triggered
        if alerts:
            await self._send_alerts(target, alerts)

    async def _send_alerts(
        self, target: MonitoringTarget, alerts: list[dict[str, Any]]
    ) -> None:
        """Send alerts for threshold violations"""
        for alert in alerts:
            logger.warning(f"ALERT [{target.name}]: {alert['message']}")

            # Send through integrated notification service if available
            if self.notification_service:
                try:
                    # Check if it's an async method
                    if hasattr(self.notification_service, "_send_error_alert"):
                        self.notification_service._send_error_alert(
                            error_type=alert["type"], service=target.name, count=1
                        )
                    elif hasattr(self.notification_service, "record_error"):
                        await self.notification_service.record_error(
                            error_type=alert["type"],
                            service_name=target.name,
                            details=alert,
                        )
                    else:
                        logger.debug(
                            "Notification service available but no compatible method found"
                        )
                except Exception as e:
                    logger.error(f"Failed to send alert via notification service: {e}")
                    # Fallback to logging already done above

    async def _store_metrics(self, metrics: DeviceMetrics) -> None:
        """Store metrics to backend with integrated storage or fallback"""
        # Convert DeviceMetrics to dict for storage
        metrics_data = {
            "host": metrics.host,
            "timestamp": metrics.timestamp.isoformat(),
            "cpu_utilization": metrics.cpu_utilization,
            "memory_utilization": metrics.memory_utilization,
            "uptime": metrics.uptime,
            "system_name": metrics.system_name,
            "system_description": metrics.system_description,
            "interface_count": len(metrics.interfaces) if metrics.interfaces else 0,
        }

        # Add interface metrics summary
        if metrics.interfaces:
            total_rx_bytes = sum(
                iface.get("rx_bytes", 0) for iface in metrics.interfaces
            )
            total_tx_bytes = sum(
                iface.get("tx_bytes", 0) for iface in metrics.interfaces
            )
            total_errors = sum(iface.get("errors", 0) for iface in metrics.interfaces)

            metrics_data.update(
                {
                    "total_rx_bytes": total_rx_bytes,
                    "total_tx_bytes": total_tx_bytes,
                    "total_interface_errors": total_errors,
                }
            )

        # Store through integrated metrics manager if available
        if self.metrics_manager:
            try:
                # Check for different storage methods
                if hasattr(self.metrics_manager, "record_metric"):
                    await self.metrics_manager.record_metric(
                        metric_name="network_device_metrics",
                        value=metrics_data,
                        labels={"host": metrics.host, "device_type": "network"},
                    )
                elif hasattr(self.metrics_manager, "store_results"):
                    await self.metrics_manager.store_results(
                        results={"network_metrics": metrics_data}
                    )
                elif hasattr(self.metrics_manager, "_store_benchmark_results"):
                    # Direct access to storage method
                    benchmark_metrics = type(
                        "BenchmarkMetrics", (), {"network_data": metrics_data}
                    )()
                    await self.metrics_manager._store_benchmark_results(
                        benchmark_metrics
                    )
                else:
                    logger.debug(
                        "Metrics manager available but no compatible storage method found"
                    )
            except Exception as e:
                logger.error(f"Failed to store metrics via metrics manager: {e}")
                # Continue to fallback storage

        # Fallback: Log metrics for basic observability
        logger.info(
            f"Device metrics [{metrics.host}]: CPU={metrics.cpu_utilization}%, "
            f"Memory={metrics.memory_utilization}%, Uptime={metrics.uptime}s"
        )

    async def get_device_status(self, host: str) -> Optional[dict[str, Any]]:
        """Get current status of a monitored device"""
        if host not in self.targets:
            return None

        target = self.targets[host]
        metrics = await self.collect_device_metrics(target)

        if not metrics:
            return {"host": host, "status": "unreachable", "last_seen": None}

        return {
            "host": host,
            "name": target.name,
            "status": "online",
            "last_seen": metrics.timestamp,
            "cpu_utilization": metrics.cpu_utilization,
            "memory_utilization": metrics.memory_utilization,
            "uptime": metrics.uptime,
            "system_name": metrics.system_name,
            "interface_count": len(metrics.interfaces) if metrics.interfaces else 0,
        }

    async def get_all_device_status(self) -> list[dict[str, Any]]:
        """Get status of all monitored devices"""
        tasks = []
        for host in self.targets.keys():
            tasks.append(self.get_device_status(host))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and None results
        return [
            result
            for result in results
            if result is not None and not isinstance(result, Exception)
        ]
