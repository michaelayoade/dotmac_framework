"""Comprehensive monitoring and alerting system for DotMac ISP Framework."""

import logging
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from dotmac_isp.shared.cache import get_cache_manager
from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Alert data structure."""

    id: str
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.resolved_at:
            data["resolved_at"] = self.resolved_at.isoformat()
        return data


@dataclass
class MetricData:
    """Metric data point."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Centralized metrics collection."""

    def __init__(self):
        """  Init   operation."""
        self.cache_manager = get_cache_manager()
        self.metrics = {}

    def counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        self._record_metric(name, value, MetricType.COUNTER, tags)

    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric."""
        self._record_metric(name, value, MetricType.GAUGE, tags)

    def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram value."""
        self._record_metric(name, value, MetricType.HISTOGRAM, tags)

    def timer(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a timer value."""
        self._record_metric(name, value, MetricType.TIMER, tags)

    def _record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        tags: Dict[str, str] = None,
    ):
        """Record a metric data point."""
        metric = MetricData(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
        )

        # Store in cache for real-time access
        metric_key = f"metric:{name}:{int(time.time())}"
        self.cache_manager.set(metric_key, metric.to_dict(), 86400, "metrics")

        # Update latest value
        latest_key = f"metric_latest:{name}"
        self.cache_manager.set(latest_key, metric.to_dict(), 3600, "metrics")

        # For counters, maintain running total
        if metric_type == MetricType.COUNTER:
            total_key = f"metric_total:{name}"
            current_total = self.cache_manager.get(total_key, "metrics") or 0
            self.cache_manager.set(total_key, current_total + value, 86400, "metrics")

    def get_metric(self, name: str) -> Optional[Dict[str, Any]]:
        """Get latest metric value."""
        latest_key = f"metric_latest:{name}"
        return self.cache_manager.get(latest_key, "metrics")

    def get_metric_history(self, name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metric history for specified hours."""
        current_time = int(time.time())
        start_time = current_time - (hours * 3600)

        pattern = f"dotmac:metrics:metric:{name}:*"
        keys = self.cache_manager.redis_client.keys(pattern)

        history = []
        for key in keys:
            timestamp = int(key.decode().split(":")[-1])
            if timestamp >= start_time:
                metric_data = self.cache_manager.redis_client.get(key)
                if metric_data:
                    history.append(self.cache_manager._deserialize_value(metric_data))

        return sorted(history, key=lambda x: x["timestamp"])


class SystemMonitor:
    """System-level monitoring."""

    def __init__(self, metrics_collector: MetricsCollector):
        """  Init   operation."""
        self.metrics = metrics_collector

    def collect_system_metrics(self):
        """Collect system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.gauge("system.cpu.percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics.gauge("system.memory.percent", memory.percent)
            self.metrics.gauge(
                "system.memory.available_gb", memory.available / (1024**3)
            )
            self.metrics.gauge("system.memory.used_gb", memory.used / (1024**3))

            # Disk metrics
            disk = psutil.disk_usage("/")
            self.metrics.gauge("system.disk.percent", disk.percent)
            self.metrics.gauge("system.disk.free_gb", disk.free / (1024**3))
            self.metrics.gauge("system.disk.used_gb", disk.used / (1024**3))

            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                self.metrics.counter("system.network.bytes_sent", network.bytes_sent)
                self.metrics.counter("system.network.bytes_recv", network.bytes_recv)
                self.metrics.counter(
                    "system.network.packets_sent", network.packets_sent
                )
                self.metrics.counter(
                    "system.network.packets_recv", network.packets_recv
                )
            except:
                pass

            # Process metrics
            try:
                process = psutil.Process()
                self.metrics.gauge("process.cpu.percent", process.cpu_percent())
                self.metrics.gauge(
                    "process.memory.mb", process.memory_info().rss / (1024**2)
                )
                self.metrics.gauge("process.threads", process.num_threads())
            except:
                pass

        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")


class ApplicationMonitor:
    """Application-level monitoring."""

    def __init__(self, metrics_collector: MetricsCollector):
        """  Init   operation."""
        self.metrics = metrics_collector
        self.cache_manager = get_cache_manager()

    def collect_application_metrics(self):
        """Collect application performance metrics."""
        try:
            # Redis metrics
            redis_info = self.cache_manager.redis_client.info()

            self.metrics.gauge(
                "redis.connected_clients", redis_info.get("connected_clients", 0)
            )
            self.metrics.gauge(
                "redis.used_memory_mb", redis_info.get("used_memory", 0) / (1024**2)
            )
            self.metrics.counter(
                "redis.keyspace_hits", redis_info.get("keyspace_hits", 0)
            )
            self.metrics.counter(
                "redis.keyspace_misses", redis_info.get("keyspace_misses", 0)
            )
            self.metrics.gauge(
                "redis.ops_per_sec", redis_info.get("instantaneous_ops_per_sec", 0)
            )

            # Calculate cache hit ratio
            hits = redis_info.get("keyspace_hits", 0)
            misses = redis_info.get("keyspace_misses", 0)
            if hits + misses > 0:
                hit_ratio = hits / (hits + misses)
                self.metrics.gauge("redis.hit_ratio", hit_ratio)

            # Database pool metrics (would need to be implemented with actual DB connection)
            # self.metrics.gauge("database.active_connections", db_pool.active_connections)
            # self.metrics.gauge("database.idle_connections", db_pool.idle_connections)

        except Exception as e:
            logger.error(f"Application metrics collection failed: {e}")

    def record_request_metrics(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """Record HTTP request metrics."""
        tags = {"method": method, "endpoint": endpoint, "status_code": str(status_code)}

        self.metrics.counter("http.requests.total", 1, tags)
        self.metrics.histogram("http.request.duration", duration, tags)

        if status_code >= 400:
            self.metrics.counter("http.requests.errors", 1, tags)

    def record_cache_metrics(self, operation: str, hit: bool):
        """Record cache operation metrics."""
        tags = {"operation": operation}

        self.metrics.counter("cache.operations.total", 1, tags)

        if hit:
            self.metrics.counter("cache.hits", 1, tags)
        else:
            self.metrics.counter("cache.misses", 1, tags)

    def record_database_metrics(self, operation: str, duration: float, success: bool):
        """Record database operation metrics."""
        tags = {"operation": operation, "success": str(success)}

        self.metrics.counter("database.operations.total", 1, tags)
        self.metrics.histogram("database.operation.duration", duration, tags)

        if not success:
            self.metrics.counter("database.operations.errors", 1, tags)


class AlertManager:
    """Alert management and notification."""

    def __init__(self, metrics_collector: MetricsCollector):
        """  Init   operation."""
        self.metrics = metrics_collector
        self.cache_manager = get_cache_manager()
        self.alert_rules = []
        self.notification_handlers = []

    def add_alert_rule(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        severity: AlertSeverity,
        condition: str = "greater_than",
    ):
        """Add an alert rule."""
        rule = {
            "name": name,
            "metric_name": metric_name,
            "threshold": threshold,
            "severity": severity,
            "condition": condition,
        }
        self.alert_rules.append(rule)

    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """Add notification handler for alerts."""
        self.notification_handlers.append(handler)

    def check_alerts(self):
        """Check all alert rules and trigger alerts if needed."""
        for rule in self.alert_rules:
            try:
                self._check_rule(rule)
            except Exception as e:
                logger.error(f"Alert rule check failed for {rule['name']}: {e}")

    def _check_rule(self, rule: Dict[str, Any]):
        """Check a specific alert rule."""
        metric_data = self.metrics.get_metric(rule["metric_name"])

        if not metric_data:
            return

        current_value = metric_data["value"]
        threshold = rule["threshold"]
        condition = rule["condition"]

        triggered = False

        if condition == "greater_than" and current_value > threshold:
            triggered = True
        elif condition == "less_than" and current_value < threshold:
            triggered = True
        elif condition == "equals" and current_value == threshold:
            triggered = True

        if triggered:
            self._create_alert(rule, current_value)

    def _create_alert(self, rule: Dict[str, Any], current_value: float):
        """Create and send alert."""
        alert_id = f"{rule['name']}_{int(time.time())}"

        # Check if similar alert was already sent recently (deduplicate)
        recent_key = f"recent_alert:{rule['name']}"
        if self.cache_manager.exists(recent_key, "alerts"):
            return  # Skip duplicate alert

        alert = Alert(
            id=alert_id,
            name=rule["name"],
            severity=rule["severity"],
            message=f"{rule['name']}: {rule['metric_name']} is {current_value}, threshold is {rule['threshold']}",
            metric_name=rule["metric_name"],
            threshold=rule["threshold"],
            current_value=current_value,
            timestamp=datetime.now(timezone.utc),
        )

        # Store alert
        alert_key = f"alert:{alert_id}"
        self.cache_manager.set(
            alert_key, alert.to_dict(), 86400 * 7, "alerts"
        )  # Keep for 7 days

        # Set deduplication key (5 minutes)
        self.cache_manager.set(recent_key, True, 300, "alerts")

        # Send notifications
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")

        logger.warning(f"Alert triggered: {alert.message}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        pattern = "dotmac:alerts:alert:*"
        keys = self.cache_manager.redis_client.keys(pattern)

        alerts = []
        for key in keys:
            alert_data = self.cache_manager.redis_client.get(key)
            if alert_data:
                alert = self.cache_manager._deserialize_value(alert_data)
                if not alert.get("resolved", False):
                    alerts.append(alert)

        return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)

    def resolve_alert(self, alert_id: str):
        """Mark alert as resolved."""
        alert_key = f"alert:{alert_id}"
        alert_data = self.cache_manager.get(alert_key, "alerts")

        if alert_data:
            alert_data["resolved"] = True
            alert_data["resolved_at"] = datetime.now(timezone.utc).isoformat()
            self.cache_manager.set(alert_key, alert_data, 86400 * 7, "alerts")

            logger.info(f"Alert resolved: {alert_id}")


class HealthChecker:
    """Health check service."""

    def __init__(self, metrics_collector: MetricsCollector):
        """  Init   operation."""
        self.metrics = metrics_collector
        self.cache_manager = get_cache_manager()
        self.checks = []

    def add_check(
        self, name: str, check_func: Callable[[], bool], critical: bool = False
    ):
        """Add a health check."""
        self.checks.append(
            {"name": name, "check_func": check_func, "critical": critical}
        )

    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        overall_healthy = True

        for check in self.checks:
            try:
                start_time = time.time()
                healthy = check["check_func"]()
                duration = time.time() - start_time

                check_result = {
                    "healthy": healthy,
                    "duration_seconds": duration,
                    "critical": check["critical"],
                }

                if not healthy:
                    if check["critical"]:
                        overall_healthy = False
                        results["status"] = "unhealthy"
                    elif results["status"] == "healthy":
                        results["status"] = "degraded"

                # Record metrics
                self.metrics.gauge(
                    f"health.{check['name']}.healthy", 1 if healthy else 0
                )
                self.metrics.histogram(f"health.{check['name']}.duration", duration)

            except Exception as e:
                check_result = {
                    "healthy": False,
                    "error": str(e),
                    "critical": check["critical"],
                }

                if check["critical"]:
                    overall_healthy = False
                    results["status"] = "unhealthy"
                elif results["status"] == "healthy":
                    results["status"] = "degraded"

                logger.error(f"Health check {check['name']} failed: {e}")

            results["checks"][check["name"]] = check_result

        # Store health status
        self.cache_manager.set("system_health", results, 300, "system")

        return results


# Global monitoring instances
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
app_monitor = ApplicationMonitor(metrics_collector)
alert_manager = AlertManager(metrics_collector)
health_checker = HealthChecker(metrics_collector)


# Default alert rules
def setup_default_alerts():
    """Set up default alert rules."""

    # System alerts
    alert_manager.add_alert_rule(
        "High CPU Usage", "system.cpu.percent", 80.0, AlertSeverity.WARNING
    )

    alert_manager.add_alert_rule(
        "Critical CPU Usage", "system.cpu.percent", 95.0, AlertSeverity.CRITICAL
    )

    alert_manager.add_alert_rule(
        "High Memory Usage", "system.memory.percent", 85.0, AlertSeverity.WARNING
    )

    alert_manager.add_alert_rule(
        "Critical Memory Usage", "system.memory.percent", 95.0, AlertSeverity.CRITICAL
    )

    alert_manager.add_alert_rule(
        "Low Disk Space", "system.disk.percent", 85.0, AlertSeverity.WARNING
    )

    alert_manager.add_alert_rule(
        "Critical Disk Space", "system.disk.percent", 95.0, AlertSeverity.CRITICAL
    )

    # Application alerts
    alert_manager.add_alert_rule(
        "Low Cache Hit Ratio",
        "redis.hit_ratio",
        0.8,
        AlertSeverity.WARNING,
        "less_than",
    )

    alert_manager.add_alert_rule(
        "High Redis Memory Usage",
        "redis.used_memory_mb",
        1000.0,  # 1GB
        AlertSeverity.WARNING,
    )


# Default health checks
def setup_default_health_checks():
    """Set up default health checks."""

    def redis_health_check():
        """Redis Health Check operation."""
        try:
            metrics_collector.cache_manager.redis_client.ping()
            return True
        except:
            return False

    def disk_space_check():
        """Disk Space Check operation."""
        disk = psutil.disk_usage("/")
        return disk.percent < 95  # Critical if over 95%

    def memory_check():
        """Memory Check operation."""
        memory = psutil.virtual_memory()
        return memory.percent < 95  # Critical if over 95%

    health_checker.add_check("redis", redis_health_check, critical=True)
    health_checker.add_check("disk_space", disk_space_check, critical=True)
    health_checker.add_check("memory", memory_check, critical=True)


# Email notification handler
def email_notification_handler(alert: Alert):
    """Send email notification for alerts."""
    if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
        # This would integrate with email service
        logger.info(f"Would send email for {alert.severity} alert: {alert.message}")


# Initialize monitoring
setup_default_alerts()
setup_default_health_checks()
alert_manager.add_notification_handler(email_notification_handler)
