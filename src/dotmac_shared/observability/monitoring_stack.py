"""
Monitoring and Observability Stack

Provides comprehensive system monitoring and observability:
- Metrics collection and aggregation
- Distributed tracing and spans
- Logging and log aggregation
- Health checking and alerting
- Dashboard and visualization support
- Performance monitoring and SLA tracking
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..gateway.unified_api_gateway import UnifiedAPIGateway
from ..mesh.service_mesh import ServiceMesh
from ..services.performance_optimization import PerformanceOptimizationService
from ..services.service_marketplace import ServiceMarketplace

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """Represents a collected metric."""

    name: str
    value: int | float
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    help_text: str = ""

    def to_prometheus_format(self) -> str:
        """Convert metric to Prometheus format."""
        labels_str = ""
        if self.labels:
            labels_list = [f'{k}="{v}"' for k, v in self.labels.items()]
            labels_str = "{" + ",".join(labels_list) + "}"

        return f"{self.name}{labels_str} {self.value} {int(self.timestamp.timestamp() * 1000)}"


@dataclass
class TraceSpan:
    """Represents a distributed trace span."""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"

    def finish(self, status: str = "ok"):
        """Finish the span."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        if self.end_time and self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def add_log(self, message: str, level: str = "info", **fields):
        """Add a log entry to the span."""
        log_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level, "message": message, **fields}
        self.logs.append(log_entry)

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
        }


@dataclass
class Alert:
    """Represents a monitoring alert."""

    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    service_name: str
    metric_name: str
    threshold_value: int | float
    current_value: int | float
    condition: str  # "greater_than", "less_than", "equals"
    created_at: datetime
    resolved_at: datetime | None = None
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check configuration and result."""

    check_id: str
    name: str
    service_name: str
    endpoint: str
    interval_seconds: int
    timeout_seconds: int
    last_check: datetime | None = None
    status: HealthStatus = HealthStatus.UNKNOWN
    response_time_ms: float | None = None
    error_message: str | None = None
    consecutive_failures: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates metrics from various sources."""

    def __init__(self):
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.metric_definitions: dict[str, dict[str, Any]] = {}

    def register_metric(self, name: str, metric_type: MetricType, help_text: str = ""):
        """Register a new metric definition."""
        self.metric_definitions[name] = {"type": metric_type, "help": help_text}

    def record_metric(self, metric: Metric):
        """Record a metric value."""
        self.metrics[metric.name].append(metric)

    def increment_counter(self, name: str, value: int | float = 1, labels: dict[str, str] | None = None):
        """Increment a counter metric."""
        metric = Metric(name=name, value=value, metric_type=MetricType.COUNTER, labels=labels or {})
        self.record_metric(metric)

    def set_gauge(self, name: str, value: int | float, labels: dict[str, str] | None = None):
        """Set a gauge metric value."""
        metric = Metric(name=name, value=value, metric_type=MetricType.GAUGE, labels=labels or {})
        self.record_metric(metric)

    def record_histogram(self, name: str, value: int | float, labels: dict[str, str] | None = None):
        """Record a histogram metric."""
        metric = Metric(name=name, value=value, metric_type=MetricType.HISTOGRAM, labels=labels or {})
        self.record_metric(metric)

    def get_metric_values(self, name: str, time_range_minutes: int = 60) -> list[Metric]:
        """Get metric values within a time range."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_range_minutes)
        metrics = self.metrics.get(name, deque())

        return [m for m in metrics if m.timestamp >= cutoff_time]

    def get_metric_summary(self, name: str, time_range_minutes: int = 60) -> dict[str, Any]:
        """Get summary statistics for a metric."""
        values = self.get_metric_values(name, time_range_minutes)
        if not values:
            return {"count": 0, "min": None, "max": None, "avg": None, "sum": None}

        numeric_values = [v.value for v in values]
        return {
            "count": len(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
            "sum": sum(numeric_values),
            "latest": numeric_values[-1] if numeric_values else None,
        }


class DistributedTracer:
    """Handles distributed tracing across services."""

    def __init__(self):
        self.active_spans: dict[str, TraceSpan] = {}
        self.completed_spans: deque = deque(maxlen=10000)
        self.traces: dict[str, list[TraceSpan]] = defaultdict(list)

    def start_span(
        self,
        operation_name: str,
        service_name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Start a new trace span."""
        span = TraceSpan(
            span_id=str(uuid4()),
            trace_id=trace_id or str(uuid4()),
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=service_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {},
        )

        self.active_spans[span.span_id] = span
        self.traces[span.trace_id].append(span)

        return span

    def finish_span(self, span_id: str, status: str = "ok"):
        """Finish a trace span."""
        if span_id in self.active_spans:
            span = self.active_spans.pop(span_id)
            span.finish(status)
            self.completed_spans.append(span)

    def get_trace(self, trace_id: str) -> list[TraceSpan]:
        """Get all spans for a trace."""
        return self.traces.get(trace_id, [])

    def get_trace_summary(self, trace_id: str) -> dict[str, Any]:
        """Get summary information for a trace."""
        spans = self.get_trace(trace_id)
        if not spans:
            return {"trace_id": trace_id, "span_count": 0, "services": [], "duration_ms": 0}

        services = list({span.service_name for span in spans})
        total_duration = max((span.duration_ms or 0) for span in spans if span.duration_ms) if spans else 0

        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "services": services,
            "duration_ms": total_duration,
            "status": "error" if any(span.status == "error" for span in spans) else "ok",
        }


class AlertManager:
    """Manages monitoring alerts and notifications."""

    def __init__(self):
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_rules: list[dict[str, Any]] = []

    def add_alert_rule(
        self,
        name: str,
        service_name: str,
        metric_name: str,
        condition: str,
        threshold: int | float,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
    ):
        """Add an alert rule."""
        rule = {
            "name": name,
            "service_name": service_name,
            "metric_name": metric_name,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
        }
        self.alert_rules.append(rule)

    def evaluate_alerts(self, metrics_collector: MetricsCollector):
        """Evaluate alert rules against current metrics."""
        for rule in self.alert_rules:
            metric_summary = metrics_collector.get_metric_summary(rule["metric_name"])
            if not metric_summary or metric_summary["count"] == 0:
                continue

            current_value = metric_summary["latest"]
            threshold = rule["threshold"]
            condition = rule["condition"]

            should_alert = False
            if condition == "greater_than" and current_value > threshold:
                should_alert = True
            elif condition == "less_than" and current_value < threshold:
                should_alert = True
            elif condition == "equals" and current_value == threshold:
                should_alert = True

            alert_key = f"{rule['service_name']}-{rule['metric_name']}"

            if should_alert:
                if alert_key not in self.active_alerts:
                    # Create new alert
                    alert = Alert(
                        alert_id=str(uuid4()),
                        name=rule["name"],
                        description=f"{rule['metric_name']} is {current_value}, threshold: {threshold}",
                        severity=rule["severity"],
                        service_name=rule["service_name"],
                        metric_name=rule["metric_name"],
                        threshold_value=threshold,
                        current_value=current_value,
                        condition=condition,
                        created_at=datetime.now(timezone.utc),
                    )
                    self.active_alerts[alert_key] = alert
                    self.alert_history.append(alert)
                    logger.warning(f"Alert triggered: {alert.name}")
            else:
                # Resolve alert if it exists
                if alert_key in self.active_alerts:
                    alert = self.active_alerts.pop(alert_key)
                    alert.resolved_at = datetime.now(timezone.utc)
                    alert.is_active = False
                    logger.info(f"Alert resolved: {alert.name}")

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())

    def get_alert_summary(self) -> dict[str, Any]:
        """Get alert summary statistics."""
        active_alerts = list(self.active_alerts.values())
        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1

        return {
            "total_active": len(active_alerts),
            "by_severity": dict(severity_counts),
            "alert_rules": len(self.alert_rules),
        }


class HealthMonitor:
    """Monitors service health across the system."""

    def __init__(self):
        self.health_checks: dict[str, HealthCheck] = {}
        self.health_history: deque = deque(maxlen=1000)

    def register_health_check(self, health_check: HealthCheck):
        """Register a health check."""
        self.health_checks[health_check.check_id] = health_check

    async def perform_health_checks(self):
        """Perform all registered health checks."""
        for check in self.health_checks.values():
            await self._perform_single_health_check(check)

    async def _perform_single_health_check(self, check: HealthCheck):
        """Perform a single health check."""
        start_time = time.time()

        try:
            # In a real implementation, this would make an HTTP request
            # For now, simulate the check
            await asyncio.sleep(0.01)  # Simulate network delay

            response_time = (time.time() - start_time) * 1000

            check.last_check = datetime.now(timezone.utc)
            check.response_time_ms = response_time
            check.status = HealthStatus.HEALTHY
            check.consecutive_failures = 0
            check.error_message = None

        except Exception as e:
            check.last_check = datetime.now(timezone.utc)
            check.status = HealthStatus.UNHEALTHY
            check.consecutive_failures += 1
            check.error_message = str(e)

        # Record health check result
        self.health_history.append(
            {
                "check_id": check.check_id,
                "timestamp": check.last_check,
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "error": check.error_message,
            }
        )

    def get_service_health(self, service_name: str) -> dict[str, Any]:
        """Get health status for a specific service."""
        service_checks = [check for check in self.health_checks.values() if check.service_name == service_name]

        if not service_checks:
            return {"service_name": service_name, "status": "unknown", "checks": []}

        # Determine overall service health
        statuses = [check.status for check in service_checks]
        if all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = "healthy"
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "service_name": service_name,
            "status": overall_status,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "last_check": check.last_check.isoformat() if check.last_check else None,
                    "response_time_ms": check.response_time_ms,
                    "error": check.error_message,
                }
                for check in service_checks
            ],
        }

    def get_system_health_summary(self) -> dict[str, Any]:
        """Get overall system health summary."""
        all_checks = list(self.health_checks.values())
        if not all_checks:
            return {"status": "unknown", "total_checks": 0, "healthy": 0, "unhealthy": 0, "degraded": 0}

        status_counts = defaultdict(int)
        for check in all_checks:
            status_counts[check.status.value] += 1

        # Determine overall system status
        if status_counts[HealthStatus.UNHEALTHY.value] > 0:
            system_status = "unhealthy"
        elif status_counts[HealthStatus.DEGRADED.value] > 0:
            system_status = "degraded"
        else:
            system_status = "healthy"

        return {
            "status": system_status,
            "total_checks": len(all_checks),
            "healthy": status_counts[HealthStatus.HEALTHY.value],
            "unhealthy": status_counts[HealthStatus.UNHEALTHY.value],
            "degraded": status_counts[HealthStatus.DEGRADED.value],
            "unknown": status_counts[HealthStatus.UNKNOWN.value],
        }


class MonitoringStack:
    """Main monitoring and observability stack."""

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: str,
        service_marketplace: ServiceMarketplace | None = None,
        service_mesh: ServiceMesh | None = None,
        api_gateway: UnifiedAPIGateway | None = None,
        performance_service: PerformanceOptimizationService | None = None,
    ):
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.service_marketplace = service_marketplace
        self.service_mesh = service_mesh
        self.api_gateway = api_gateway
        self.performance_service = performance_service

        # Core monitoring components
        self.metrics_collector = MetricsCollector()
        self.tracer = DistributedTracer()
        self.alert_manager = AlertManager()
        self.health_monitor = HealthMonitor()

        # Configuration
        self.collection_interval = 30  # seconds
        self.retention_days = 7

        # Background tasks
        self._monitoring_task: asyncio.Task | None = None
        self._running = False

    async def initialize(self):
        """Initialize the monitoring stack."""
        # Register standard metrics
        self._register_standard_metrics()

        # Setup default alert rules
        self._setup_default_alerts()

        # Register health checks for known services
        await self._register_service_health_checks()

        # Start monitoring loop
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info(f"Monitoring stack initialized for tenant: {self.tenant_id}")

    async def shutdown(self):
        """Shutdown the monitoring stack."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoring stack shutdown complete")

    def _register_standard_metrics(self):
        """Register standard system metrics."""
        metrics = [
            ("http_requests_total", MetricType.COUNTER, "Total HTTP requests"),
            ("http_request_duration_ms", MetricType.HISTOGRAM, "HTTP request duration"),
            ("service_health_status", MetricType.GAUGE, "Service health status (1=healthy, 0=unhealthy)"),
            ("active_connections", MetricType.GAUGE, "Number of active connections"),
            ("memory_usage_bytes", MetricType.GAUGE, "Memory usage in bytes"),
            ("cpu_usage_percent", MetricType.GAUGE, "CPU usage percentage"),
            ("disk_usage_percent", MetricType.GAUGE, "Disk usage percentage"),
            ("cache_hit_rate", MetricType.GAUGE, "Cache hit rate percentage"),
            ("error_rate", MetricType.GAUGE, "Error rate percentage"),
        ]

        for name, metric_type, help_text in metrics:
            self.metrics_collector.register_metric(name, metric_type, help_text)

    def _setup_default_alerts(self):
        """Setup default alert rules."""
        default_alerts = [
            ("High Error Rate", "system", "error_rate", "greater_than", 5.0, AlertSeverity.HIGH),
            ("Low Cache Hit Rate", "system", "cache_hit_rate", "less_than", 50.0, AlertSeverity.MEDIUM),
            ("High CPU Usage", "system", "cpu_usage_percent", "greater_than", 80.0, AlertSeverity.HIGH),
            ("High Memory Usage", "system", "memory_usage_bytes", "greater_than", 1000000000, AlertSeverity.HIGH),
            ("Service Unhealthy", "system", "service_health_status", "less_than", 1.0, AlertSeverity.CRITICAL),
        ]

        for name, service, metric, condition, threshold, severity in default_alerts:
            self.alert_manager.add_alert_rule(name, service, metric, condition, threshold, severity)

    async def _register_service_health_checks(self):
        """Register health checks for discovered services."""
        if not self.service_marketplace:
            return

        try:
            services = await self.service_marketplace.discover_service()

            for service_info in services:
                service_name = service_info.get("name", "unknown")
                instances = service_info.get("instances", [])

                for i, instance in enumerate(instances):
                    health_check = HealthCheck(
                        check_id=f"{service_name}-{i}",
                        name=f"{service_name} Health Check",
                        service_name=service_name,
                        endpoint=f"http://{instance.get('host')}:{instance.get('port')}/health",
                        interval_seconds=30,
                        timeout_seconds=5,
                    )
                    self.health_monitor.register_health_check(health_check)

            logger.info(f"Registered health checks for {len(services)} services")
        except Exception as e:
            logger.error(f"Failed to register service health checks: {e}")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._collect_system_metrics()
                await self._collect_service_metrics()
                await self.health_monitor.perform_health_checks()
                self.alert_manager.evaluate_alerts(self.metrics_collector)

                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.collection_interval)

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        import psutil

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics_collector.set_gauge("cpu_usage_percent", cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics_collector.set_gauge("memory_usage_bytes", memory.used)

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        self.metrics_collector.set_gauge("disk_usage_percent", disk_percent)

    async def _collect_service_metrics(self):
        """Collect metrics from integrated services."""
        # Collect from service mesh
        if self.service_mesh:
            mesh_metrics = self.service_mesh.get_mesh_metrics()
            self.metrics_collector.set_gauge("active_connections", mesh_metrics.get("active_connections", 0))
            self.metrics_collector.set_gauge("service_success_rate", mesh_metrics.get("success_rate_percent", 0))

        # Collect from API gateway
        if self.api_gateway and hasattr(self.api_gateway, "metrics"):
            gateway_metrics = self.api_gateway.metrics.get_summary()
            self.metrics_collector.increment_counter("http_requests_total", gateway_metrics.get("total_requests", 0))
            self.metrics_collector.set_gauge("error_rate", 100 - gateway_metrics.get("success_rate", 100))

        # Collect from performance service
        if self.performance_service:
            try:
                perf_summary = await self.performance_service.get_performance_summary()
                cache_metrics = perf_summary.get("cache_stats", {})
                service_metrics = perf_summary.get("service_metrics", {})

                self.metrics_collector.set_gauge("cache_hit_rate", cache_metrics.get("hit_rate_percent", 0))
                self.metrics_collector.set_gauge("error_rate", service_metrics.get("error_rate", 0))
            except Exception as e:
                logger.warning(f"Failed to collect performance metrics: {e}")

    def create_span(
        self,
        operation_name: str,
        service_name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        **tags,
    ) -> TraceSpan:
        """Create a new trace span."""
        return self.tracer.start_span(
            operation_name=operation_name,
            service_name=service_name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            tags=tags,
        )

    def finish_span(self, span_id: str, status: str = "ok"):
        """Finish a trace span."""
        self.tracer.finish_span(span_id, status)

    def record_metric(self, name: str, value: int | float, labels: dict[str, str] | None = None):
        """Record a custom metric."""
        metric = Metric(name=name, value=value, metric_type=MetricType.GAUGE, labels=labels or {})
        self.metrics_collector.record_metric(metric)

    def get_system_overview(self) -> dict[str, Any]:
        """Get comprehensive system overview."""
        health_summary = self.health_monitor.get_system_health_summary()
        alert_summary = self.alert_manager.get_alert_summary()

        # Get key metrics
        key_metrics = {}
        for metric_name in ["cpu_usage_percent", "memory_usage_bytes", "error_rate", "cache_hit_rate"]:
            summary = self.metrics_collector.get_metric_summary(metric_name, 5)  # Last 5 minutes
            key_metrics[metric_name] = summary.get("latest", 0)

        return {
            "tenant_id": self.tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": health_summary,
            "alerts": alert_summary,
            "metrics": key_metrics,
            "active_traces": len(self.tracer.active_spans),
            "completed_traces": len(self.tracer.completed_spans),
        }

    def get_service_dashboard_data(self, service_name: str) -> dict[str, Any]:
        """Get dashboard data for a specific service."""
        health_info = self.health_monitor.get_service_health(service_name)

        # Get service-specific metrics
        service_metrics = {}
        for metric_name in ["http_requests_total", "http_request_duration_ms", "error_rate"]:
            values = self.metrics_collector.get_metric_values(metric_name, 60)
            service_values = [m for m in values if m.labels.get("service") == service_name]
            if service_values:
                service_metrics[metric_name] = [m.value for m in service_values]
            else:
                service_metrics[metric_name] = []

        return {
            "service_name": service_name,
            "health": health_info,
            "metrics": service_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        for metric_name, metric_def in self.metrics_collector.metric_definitions.items():
            # Add help text
            if metric_def["help"]:
                lines.append(f"# HELP {metric_name} {metric_def['help']}")
            lines.append(f"# TYPE {metric_name} {metric_def['type'].value}")

            # Add metric values
            recent_metrics = self.metrics_collector.get_metric_values(metric_name, 5)
            for metric in recent_metrics[-1:]:  # Only latest value
                lines.append(metric.to_prometheus_format())

            lines.append("")

        return "\n".join(lines)


class MonitoringStackFactory:
    """Factory for creating monitoring stack instances."""

    @staticmethod
    def create_monitoring_stack(db_session: AsyncSession, tenant_id: str, **integrations) -> MonitoringStack:
        """Create a monitoring stack instance."""
        return MonitoringStack(db_session=db_session, tenant_id=tenant_id, **integrations)

    @staticmethod
    def create_health_check(
        name: str, service_name: str, endpoint: str, interval_seconds: int = 30, timeout_seconds: int = 5
    ) -> HealthCheck:
        """Create a health check configuration."""
        return HealthCheck(
            check_id=f"{service_name}-{name}",
            name=name,
            service_name=service_name,
            endpoint=endpoint,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        )


async def setup_comprehensive_monitoring(
    db_session: AsyncSession,
    tenant_id: str,
    service_marketplace: ServiceMarketplace | None = None,
    service_mesh: ServiceMesh | None = None,
    api_gateway: UnifiedAPIGateway | None = None,
    performance_service: PerformanceOptimizationService | None = None,
) -> MonitoringStack:
    """Setup comprehensive monitoring for the entire system."""
    monitoring = MonitoringStackFactory.create_monitoring_stack(
        db_session=db_session,
        tenant_id=tenant_id,
        service_marketplace=service_marketplace,
        service_mesh=service_mesh,
        api_gateway=api_gateway,
        performance_service=performance_service,
    )

    await monitoring.initialize()

    logger.info("Comprehensive monitoring stack setup complete")
    return monitoring
