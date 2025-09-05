"""
Monitoring and metrics collection for chaos engineering experiments
"""
import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from ..utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected during chaos experiments"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass
class MetricPoint:
    """Individual metric data point"""

    timestamp: datetime
    value: float
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp.isoformat(), "value": self.value, "tags": self.tags}


@dataclass
class Alert:
    """Chaos experiment alert"""

    id: str
    severity: AlertSeverity
    title: str
    message: str
    experiment_id: str
    metric_name: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    timestamp: datetime = field(default_factory=utc_now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.resolved_at:
            data["resolved_at"] = self.resolved_at.isoformat()
        return data


@dataclass
class ThresholdRule:
    """Monitoring threshold rule"""

    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    duration_seconds: int = 0  # How long condition must persist
    alert_title: str = ""
    alert_message: str = ""


class MetricsCollector:
    """Collects and stores metrics from chaos experiments"""

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics = defaultdict(lambda: deque())
        self.experiment_metrics = defaultdict(dict)
        self._cleanup_task = None

    async def start(self):
        """Start the metrics collector"""
        logger.info("Starting chaos metrics collector")
        self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())

    async def stop(self):
        """Stop the metrics collector"""
        logger.info("Stopping chaos metrics collector")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def record_metric(
        self, name: str, value: float, tags: Optional[dict[str, str]] = None, experiment_id: Optional[str] = None
    ):
        """Record a metric value"""
        tags = tags or {}
        point = MetricPoint(timestamp=utc_now(), value=value, tags=tags)

        self.metrics[name].append(point)

        if experiment_id:
            if experiment_id not in self.experiment_metrics:
                self.experiment_metrics[experiment_id] = defaultdict(list)
            self.experiment_metrics[experiment_id][name].append(point)

        logger.debug(f"Recorded metric {name}={value} tags={tags}")

    def get_metric_history(
        self, name: str, since: Optional[datetime] = None, experiment_id: Optional[str] = None
    ) -> list[MetricPoint]:
        """Get metric history"""
        if experiment_id and experiment_id in self.experiment_metrics:
            points = self.experiment_metrics[experiment_id].get(name, [])
        else:
            points = list(self.metrics[name])

        if since:
            points = [p for p in points if p.timestamp >= since]

        return sorted(points, key=lambda p: p.timestamp)

    def get_current_value(self, name: str, experiment_id: Optional[str] = None) -> Optional[float]:
        """Get the most recent value for a metric"""
        history = self.get_metric_history(name, experiment_id=experiment_id)
        return history[-1].value if history else None

    def get_metric_summary(
        self, name: str, since: Optional[datetime] = None, experiment_id: Optional[str] = None
    ) -> dict[str, float]:
        """Get statistical summary of a metric"""
        history = self.get_metric_history(name, since, experiment_id)
        values = [p.value for p in history]

        if not values:
            return {"count": 0}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
        }

    async def _cleanup_old_metrics(self):
        """Clean up old metrics periodically"""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                cutoff_time = utc_now() - timedelta(hours=self.retention_hours)

                for _, points in self.metrics.items():
                    # Remove old points
                    while points and points[0].timestamp < cutoff_time:
                        points.popleft()

                # Clean up experiment metrics
                for exp_id, exp_metrics in list(self.experiment_metrics.items()):
                    for metric_name, points in exp_metrics.items():
                        # Filter out old points
                        exp_metrics[metric_name] = [p for p in points if p.timestamp >= cutoff_time]

                    # Remove empty experiment metrics
                    if not any(exp_metrics.values()):
                        del self.experiment_metrics[exp_id]

                logger.info("Cleaned up old metrics")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during metrics cleanup: {e}")


class AlertManager:
    """Manages alerts for chaos experiments"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.active_alerts = {}
        self.alert_history = []
        self.threshold_rules = {}
        self.alert_handlers = []
        self._monitoring_task = None

    async def start(self):
        """Start the alert manager"""
        logger.info("Starting chaos alert manager")
        self._monitoring_task = asyncio.create_task(self._monitor_thresholds())

    async def stop(self):
        """Stop the alert manager"""
        logger.info("Stopping chaos alert manager")
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    def add_threshold_rule(self, rule: ThresholdRule):
        """Add a monitoring threshold rule"""
        rule_key = f"{rule.metric_name}:{rule.condition}:{rule.threshold}"
        self.threshold_rules[rule_key] = rule
        logger.info(f"Added threshold rule: {rule_key}")

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler callback"""
        self.alert_handlers.append(handler)

    async def trigger_alert(self, alert: Alert):
        """Trigger an alert"""
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)

        logger.warning(f"CHAOS ALERT [{alert.severity}]: {alert.title} - {alert.message}")

        # Notify all handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

    async def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = utc_now()
            del self.active_alerts[alert_id]
            logger.info(f"Resolved alert: {alert_id}")

    def get_active_alerts(self, experiment_id: Optional[str] = None) -> list[Alert]:
        """Get active alerts, optionally filtered by experiment"""
        alerts = list(self.active_alerts.values())
        if experiment_id:
            alerts = [a for a in alerts if a.experiment_id == experiment_id]
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    async def _monitor_thresholds(self):
        """Monitor metrics against threshold rules"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                for _rule_key, rule in self.threshold_rules.items():
                    await self._check_threshold_rule(rule)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in threshold monitoring: {e}")

    async def _check_threshold_rule(self, rule: ThresholdRule):
        """Check a specific threshold rule"""
        current_value = self.metrics_collector.get_current_value(rule.metric_name)

        if current_value is None:
            return

        condition_met = False
        if rule.condition == "gt":
            condition_met = current_value > rule.threshold
        elif rule.condition == "lt":
            condition_met = current_value < rule.threshold
        elif rule.condition == "eq":
            condition_met = current_value == rule.threshold
        elif rule.condition == "gte":
            condition_met = current_value >= rule.threshold
        elif rule.condition == "lte":
            condition_met = current_value <= rule.threshold

        if condition_met:
            alert_id = f"{rule.metric_name}_{rule.condition}_{rule.threshold}"

            # Check if alert already active
            if alert_id not in self.active_alerts:
                alert = Alert(
                    id=alert_id,
                    severity=rule.severity,
                    title=rule.alert_title or f"Threshold exceeded: {rule.metric_name}",
                    message=rule.alert_message
                    or f"{rule.metric_name} {rule.condition} {rule.threshold} (current: {current_value})",
                    experiment_id="monitoring",
                    metric_name=rule.metric_name,
                    threshold_value=rule.threshold,
                    actual_value=current_value,
                )
                await self.trigger_alert(alert)


class ChaosMonitor:
    """Main chaos monitoring system"""

    def __init__(self, retention_hours: int = 24):
        self.metrics_collector = MetricsCollector(retention_hours)
        self.alert_manager = AlertManager(self.metrics_collector)
        self.experiment_monitors = {}
        self._running = False

    async def start(self):
        """Start the chaos monitoring system"""
        if self._running:
            return

        logger.info("Starting chaos monitoring system")
        await self.metrics_collector.start()
        await self.alert_manager.start()

        # Add default threshold rules
        self._add_default_thresholds()

        self._running = True

    async def stop(self):
        """Stop the chaos monitoring system"""
        if not self._running:
            return

        logger.info("Stopping chaos monitoring system")
        await self.alert_manager.stop()
        await self.metrics_collector.stop()
        self._running = False

    def _add_default_thresholds(self):
        """Add default monitoring thresholds"""
        default_rules = [
            ThresholdRule(
                metric_name="error_rate",
                condition="gt",
                threshold=0.05,  # 5%
                severity=AlertSeverity.WARNING,
                alert_title="High Error Rate",
                alert_message="Error rate exceeded 5% threshold",
            ),
            ThresholdRule(
                metric_name="error_rate",
                condition="gt",
                threshold=0.20,  # 20%
                severity=AlertSeverity.CRITICAL,
                alert_title="Critical Error Rate",
                alert_message="Error rate exceeded 20% threshold",
            ),
            ThresholdRule(
                metric_name="response_time_p99",
                condition="gt",
                threshold=5000,  # 5 seconds
                severity=AlertSeverity.WARNING,
                alert_title="High Response Time",
                alert_message="P99 response time exceeded 5 seconds",
            ),
            ThresholdRule(
                metric_name="availability",
                condition="lt",
                threshold=0.99,  # 99%
                severity=AlertSeverity.CRITICAL,
                alert_title="Low Availability",
                alert_message="System availability below 99%",
            ),
        ]

        for rule in default_rules:
            self.alert_manager.add_threshold_rule(rule)

    def create_experiment_monitor(self, experiment_id: str) -> "ExperimentMonitor":
        """Create a monitor for a specific experiment"""
        monitor = ExperimentMonitor(experiment_id, self)
        self.experiment_monitors[experiment_id] = monitor
        return monitor

    def get_experiment_monitor(self, experiment_id: str) -> Optional["ExperimentMonitor"]:
        """Get monitor for a specific experiment"""
        return self.experiment_monitors.get(experiment_id)

    def record_metric(
        self, name: str, value: float, tags: Optional[dict[str, str]] = None, experiment_id: Optional[str] = None
    ):
        """Record a metric (delegate to collector)"""
        self.metrics_collector.record_metric(name, value, tags, experiment_id)

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health metrics"""
        health = {
            "timestamp": utc_now().isoformat(),
            "monitoring_active": self._running,
            "active_experiments": len(self.experiment_monitors),
            "active_alerts": len(self.alert_manager.active_alerts),
            "metrics_collected": len(self.metrics_collector.metrics),
        }

        # Add key metric summaries
        key_metrics = ["error_rate", "response_time_p99", "availability", "throughput"]
        for metric in key_metrics:
            summary = self.metrics_collector.get_metric_summary(metric, since=utc_now() - timedelta(minutes=5))
            health[f"{metric}_summary"] = summary

        return health


class ExperimentMonitor:
    """Monitor for a specific chaos experiment"""

    def __init__(self, experiment_id: str, chaos_monitor: ChaosMonitor):
        self.experiment_id = experiment_id
        self.chaos_monitor = chaos_monitor
        self.start_time = utc_now()
        self.metrics_snapshot = {}

    def record_baseline_metrics(self):
        """Record baseline metrics before experiment starts"""
        logger.info(f"Recording baseline metrics for experiment {self.experiment_id}")

        # Record system state
        self.record_metric("experiment_started", 1)
        self.record_metric("baseline_recorded", 1)

        # Capture current metric values as baseline
        key_metrics = ["error_rate", "response_time_avg", "throughput", "cpu_usage"]
        for metric in key_metrics:
            current = self.chaos_monitor.metrics_collector.get_current_value(metric)
            if current is not None:
                self.record_metric(f"baseline_{metric}", current)
                self.metrics_snapshot[f"baseline_{metric}"] = current

    def record_metric(self, name: str, value: float, tags: Optional[dict[str, str]] = None):
        """Record a metric for this experiment"""
        tags = tags or {}
        tags["experiment_id"] = self.experiment_id

        self.chaos_monitor.record_metric(name, value, tags, experiment_id=self.experiment_id)

    async def monitor_failure_injection(self, failure_type: str):
        """Monitor during failure injection"""
        logger.info(f"Monitoring failure injection: {failure_type}")

        self.record_metric("failure_injected", 1, {"failure_type": failure_type})

        # Monitor key resilience metrics
        monitoring_tasks = [
            self._monitor_error_rates(),
            self._monitor_response_times(),
            self._monitor_availability(),
            self._monitor_recovery_metrics(),
        ]

        # Run monitoring for duration of experiment
        try:
            await asyncio.gather(*monitoring_tasks)
        except Exception as e:
            logger.error(f"Error during failure monitoring: {e}")

    async def _monitor_error_rates(self):
        """Monitor error rates during experiment"""
        while True:
            # Simulate error rate collection
            await asyncio.sleep(5)

            # In real implementation, this would query actual services
            error_rate = 0.02  # 2% simulated error rate
            self.record_metric("error_rate", error_rate)

    async def _monitor_response_times(self):
        """Monitor response times during experiment"""
        while True:
            await asyncio.sleep(5)

            # Simulate response time collection
            response_time = 150  # 150ms simulated
            self.record_metric("response_time_avg", response_time)
            self.record_metric("response_time_p99", response_time * 2)

    async def _monitor_availability(self):
        """Monitor service availability during experiment"""
        while True:
            await asyncio.sleep(10)

            # Simulate availability check
            availability = 0.995  # 99.5% simulated
            self.record_metric("availability", availability)

    async def _monitor_recovery_metrics(self):
        """Monitor recovery-specific metrics"""
        while True:
            await asyncio.sleep(15)

            # Simulate recovery metrics
            self.record_metric("recovery_attempts", 1)
            self.record_metric("circuit_breaker_open", 0)

    def get_experiment_summary(self) -> dict[str, Any]:
        """Get summary of experiment metrics"""
        duration = (utc_now() - self.start_time).total_seconds()

        summary = {
            "experiment_id": self.experiment_id,
            "start_time": self.start_time.isoformat(),
            "duration_seconds": duration,
            "metrics_collected": {},
        }

        # Get summaries for key metrics
        key_metrics = ["error_rate", "response_time_avg", "response_time_p99", "availability", "recovery_attempts"]

        for metric in key_metrics:
            metric_summary = self.chaos_monitor.metrics_collector.get_metric_summary(
                metric, experiment_id=self.experiment_id
            )
            summary["metrics_collected"][metric] = metric_summary

        # Get alerts for this experiment
        alerts = self.chaos_monitor.alert_manager.get_active_alerts(self.experiment_id)
        summary["active_alerts"] = len(alerts)
        summary["alert_details"] = [alert.to_dict() for alert in alerts[-5:]]  # Last 5 alerts

        return summary
