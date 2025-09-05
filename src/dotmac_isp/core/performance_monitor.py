"""
Clean, optimal performance monitoring for dotMAC Framework.
Zero legacy dependencies, pure production implementation.
"""

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from dotmac_isp.shared.cache import get_cache_manager
from sqlalchemy import event
from sqlalchemy.engine import Engine

from dotmac.platform.observability.core.signoz_integration import get_signoz

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Performance metric types."""

    LATENCY = "latency"  # Response times, query duration
    THROUGHPUT = "throughput"  # Requests per second, queries per second
    ERROR_RATE = "error_rate"  # Error percentage
    SATURATION = "saturation"  # CPU, memory, disk usage
    CUSTOM = "custom"  # Business-specific metrics


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Clean performance metric structure."""

    name: str
    value: float
    metric_type: MetricType
    unit: str
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "context": self.context,
        }


@dataclass
class PerformanceAlert:
    """Performance alert structure."""

    metric_name: str
    current_value: float
    threshold_value: float
    alert_level: AlertLevel
    message: str
    timestamp: datetime
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "alert_level": self.alert_level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class OptimalPerformanceCollector:
    """High-performance metrics collection with zero overhead."""

    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.signoz = get_signoz()

        # High-performance in-memory buffers
        self.metric_buffer: list[PerformanceMetric] = []
        self.buffer_size = 1000
        self.flush_interval = 30  # seconds

        # Performance thresholds (optimal for ISP workloads)
        self.thresholds = {
            "database_query_p95": 200,  # 200ms 95th percentile
            "database_query_p99": 500,  # 500ms 99th percentile
            "http_request_p95": 300,  # 300ms HTTP response
            "http_request_p99": 1000,  # 1s HTTP response
            "error_rate_threshold": 0.5,  # 0.5% error rate
            "cpu_utilization": 80,  # 80% CPU
            "memory_utilization": 85,  # 85% memory
            "cache_hit_rate_min": 90,  # 90% cache hit rate
        }

        # Start async processing
        asyncio.create_task(self._start_background_processing())

    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record performance metric with zero-copy optimization."""
        # Add to buffer (thread-safe for single writer)
        self.metric_buffer.append(metric)

        # Check thresholds immediately for critical metrics
        if metric.metric_type in [MetricType.LATENCY, MetricType.ERROR_RATE]:
            self._check_immediate_thresholds(metric)

        # Auto-flush if buffer full
        if len(self.metric_buffer) >= self.buffer_size:
            asyncio.create_task(self._flush_metrics())

    async def _flush_metrics(self) -> None:
        """Flush metrics buffer to storage systems."""
        if not self.metric_buffer:
            return

        # Atomic buffer swap
        current_buffer = self.metric_buffer
        self.metric_buffer = []

        try:
            # Batch process metrics
            await self._process_metric_batch(current_buffer)

        except Exception as e:
            logger.error(f"Metrics flush error: {e}")
            # Re-add failed metrics to buffer if critical
            critical_metrics = [
                m for m in current_buffer if m.metric_type == MetricType.ERROR_RATE
            ]
            self.metric_buffer.extend(critical_metrics[:100])  # Limit backlog

    async def _process_metric_batch(self, metrics: list[PerformanceMetric]) -> None:
        """Process batch of metrics efficiently."""
        # Group by metric name for efficient processing
        metric_groups = {}
        for metric in metrics:
            if metric.name not in metric_groups:
                metric_groups[metric.name] = []
            metric_groups[metric.name].append(metric)

        # Process each group
        for metric_name, metric_list in metric_groups.items():
            await self._process_metric_group(metric_name, metric_list)

    async def _process_metric_group(
        self, metric_name: str, metrics: list[PerformanceMetric]
    ) -> None:
        """Process group of same-named metrics."""
        try:
            # Calculate aggregations
            values = [m.value for m in metrics]
            aggregation = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": statistics.mean(values),
                "p50": statistics.median(values),
                "p95": (
                    statistics.quantiles(values, n=20)[18]
                    if len(values) >= 20
                    else max(values)
                ),
                "p99": (
                    statistics.quantiles(values, n=100)[98]
                    if len(values) >= 100
                    else max(values)
                ),
            }

            # Store in cache for real-time access
            cache_key = f"metrics:{metric_name}:{int(time.time())}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.cache_manager.set,
                cache_key,
                {
                    "aggregation": aggregation,
                    "raw_metrics": [
                        m.to_dict() for m in metrics[-10:]
                    ],  # Last 10 samples
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                3600,  # 1 hour TTL
                "performance_metrics",
            )
            # Send to SignOz if available
            if self.signoz and self.signoz.enabled:
                await self._send_to_signoz(metric_name, aggregation, metrics[0])

            # Check performance thresholds
            await self._check_performance_thresholds(metric_name, aggregation)

        except Exception as e:
            logger.error(f"Error processing metric group {metric_name}: {e}")

    async def _send_to_signoz(
        self, metric_name: str, aggregation: dict, sample_metric: PerformanceMetric
    ) -> None:
        """Send metrics to SignOz efficiently."""
        try:
            # Send key aggregations to SignOz
            for agg_type, value in aggregation.items():
                if agg_type in ["avg", "p95", "p99", "max"]:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.signoz.record_business_event,
                        f"performance_{metric_name}_{agg_type}",
                        "system",
                        value,
                        {
                            "metric_type": sample_metric.metric_type.value,
                            "unit": sample_metric.unit,
                            **sample_metric.tags,
                        },
                    )
        except Exception as e:
            logger.error(f"SignOz export error: {e}")

    def _check_immediate_thresholds(self, metric: PerformanceMetric) -> None:
        """Check critical thresholds immediately."""
        threshold_key = f"{metric.name}_{metric.metric_type.value}"
        threshold = self.thresholds.get(threshold_key)

        if not threshold:
            return

        # Check if threshold exceeded
        if self._is_threshold_exceeded(metric, threshold):
            alert = PerformanceAlert(
                metric_name=metric.name,
                current_value=metric.value,
                threshold_value=threshold,
                alert_level=self._determine_alert_level(metric, threshold),
                message=f"{metric.name} exceeded threshold: {metric.value}{metric.unit} > {threshold}{metric.unit}",
                timestamp=metric.timestamp,
                context=metric.context,
            )
            # Fire alert immediately
            asyncio.create_task(self._fire_alert(alert))

    async def _check_performance_thresholds(
        self, metric_name: str, aggregation: dict
    ) -> None:
        """Check performance thresholds against aggregated data."""
        # Check P95 thresholds
        p95_key = f"{metric_name}_p95"
        if p95_key in self.thresholds:
            p95_value = aggregation.get("p95", 0)
            threshold = self.thresholds[p95_key]

            if p95_value > threshold:
                alert = PerformanceAlert(
                    metric_name=f"{metric_name}_p95",
                    current_value=p95_value,
                    threshold_value=threshold,
                    alert_level=AlertLevel.WARNING,
                    message=f"{metric_name} P95 exceeded threshold: {p95_value:.1f} > {threshold}",
                    timestamp=datetime.now(timezone.utc),
                )
                await self._fire_alert(alert)

        # Check P99 thresholds
        p99_key = f"{metric_name}_p99"
        if p99_key in self.thresholds:
            p99_value = aggregation.get("p99", 0)
            threshold = self.thresholds[p99_key]

            if p99_value > threshold:
                alert = PerformanceAlert(
                    metric_name=f"{metric_name}_p99",
                    current_value=p99_value,
                    threshold_value=threshold,
                    alert_level=AlertLevel.CRITICAL,
                    message=f"{metric_name} P99 exceeded threshold: {p99_value:.1f} > {threshold}",
                    timestamp=datetime.now(timezone.utc),
                )
                await self._fire_alert(alert)

    def _is_threshold_exceeded(
        self, metric: PerformanceMetric, threshold: float
    ) -> bool:
        """Check if metric exceeds threshold."""
        if metric.metric_type == MetricType.ERROR_RATE:
            return metric.value > threshold
        elif metric.metric_type in [MetricType.LATENCY, MetricType.SATURATION]:
            return metric.value > threshold
        elif metric.metric_type == MetricType.THROUGHPUT:
            return metric.value < threshold  # Lower throughput is bad
        else:
            return metric.value > threshold

    def _determine_alert_level(
        self, metric: PerformanceMetric, threshold: float
    ) -> AlertLevel:
        """Determine appropriate alert level."""
        if metric.metric_type == MetricType.ERROR_RATE:
            if metric.value > threshold * 3:  # 3x threshold
                return AlertLevel.CRITICAL
            elif metric.value > threshold * 1.5:  # 1.5x threshold
                return AlertLevel.WARNING
        elif metric.metric_type == MetricType.LATENCY:
            if metric.value > threshold * 2:  # 2x threshold
                return AlertLevel.CRITICAL
            elif metric.value > threshold * 1.5:  # 1.5x threshold
                return AlertLevel.WARNING

        return AlertLevel.INFO

    async def _fire_alert(self, alert: PerformanceAlert) -> None:
        """Fire performance alert through available channels."""
        try:
            # Store alert in cache
            alert_key = f"alert:{alert.metric_name}:{int(time.time())}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.cache_manager.set,
                alert_key,
                alert.to_dict(),
                86400,  # 24 hours
                "performance_alerts",
            )
            # Log alert
            log_level = (
                logging.WARNING
                if alert.alert_level == AlertLevel.WARNING
                else logging.ERROR
            )
            logger.log(log_level, f"🚨 Performance Alert: {alert.message}")

            # Send to SignOz if available
            if self.signoz and self.signoz.enabled:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.signoz.record_business_event,
                    "performance_alert",
                    "system",
                    1,
                    alert.to_dict(),
                )
        except Exception as e:
            logger.error(f"Alert firing error: {e}")

    async def _start_background_processing(self) -> None:
        """Start background metric processing."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_metrics()
            except Exception as e:
                logger.error(f"Background processing error: {e}")
                await asyncio.sleep(5)  # Short delay before retry


class DatabasePerformanceMonitor:
    """Optimal database performance monitoring."""

    def __init__(self, collector: OptimalPerformanceCollector):
        self.collector = collector
        self.setup_sqlalchemy_monitoring()

    def setup_sqlalchemy_monitoring(self) -> None:
        """Setup SQLAlchemy event monitoring for optimal performance."""

        @event.listens_for(Engine, "before_cursor_execute")
        def before_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time."""
            context._query_start = time.perf_counter()
            context._query_statement = statement

        @event.listens_for(Engine, "after_cursor_execute")
        def after_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query performance."""
            try:
                duration = (
                    time.perf_counter() - context._query_start
                ) * 1000  # Convert to ms

                # Extract query info
                query_type = self._extract_query_type(statement)
                table_name = self._extract_table_name(statement)

                # Create performance metric
                metric = PerformanceMetric(
                    name="database_query",
                    value=duration,
                    metric_type=MetricType.LATENCY,
                    unit="ms",
                    timestamp=datetime.now(timezone.utc),
                    tags={
                        "query_type": query_type,
                        "table": table_name,
                        "status": "success",
                    },
                    context={
                        "statement": statement[:200],  # Truncated for storage
                        "has_parameters": bool(parameters),
                    },
                )
                self.collector.record_metric(metric)

            except Exception as e:
                logger.error(f"Database monitoring error: {e}")

        @event.listens_for(Engine, "handle_error")
        def handle_error(exception_context):
            """Record database errors."""
            try:
                metric = PerformanceMetric(
                    name="database_errors",
                    value=1,
                    metric_type=MetricType.ERROR_RATE,
                    unit="count",
                    timestamp=datetime.now(timezone.utc),
                    tags={
                        "error_type": type(
                            exception_context.original_exception
                        ).__name__,
                        "status": "error",
                    },
                    context={
                        "statement": (
                            str(exception_context.statement)[:200]
                            if exception_context.statement
                            else "unknown"
                        ),
                        "error": str(exception_context.original_exception)[:500],
                    },
                )
                self.collector.record_metric(metric)

            except Exception as e:
                logger.error(f"Database error monitoring error: {e}")

    def _extract_query_type(self, statement: str) -> str:
        """Extract query type from SQL statement."""
        statement_upper = statement.strip().upper()
        if statement_upper.startswith("SELECT"):
            return "SELECT"
        elif statement_upper.startswith("INSERT"):
            return "INSERT"
        elif statement_upper.startswith("UPDATE"):
            return "UPDATE"
        elif statement_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "OTHER"

    def _extract_table_name(self, statement: str) -> str:
        """Extract primary table name from SQL statement."""
        try:
            words = statement.strip().upper().split()
            if len(words) > 2 and words[0] in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                if words[0] == "SELECT":
                    from_idx = next(
                        (i for i, w in enumerate(words) if w == "FROM"), None
                    )
                    if from_idx and from_idx + 1 < len(words):
                        return words[from_idx + 1].split(".")[0]
                elif words[0] in ["INSERT", "UPDATE"]:
                    if words[1] in ["INTO", "TABLE"] and len(words) > 2:
                        return words[2].split(".")[0]
                    elif len(words) > 1:
                        return words[1].split(".")[0]
                elif words[0] == "DELETE" and "FROM" in words:
                    from_idx = words.index("FROM")
                    if from_idx + 1 < len(words):
                        return words[from_idx + 1].split(".")[0]
            return "unknown"
        except Exception:
            return "unknown"


class HTTPPerformanceMonitor:
    """Optimal HTTP request performance monitoring."""

    def __init__(self, collector: OptimalPerformanceCollector):
        self.collector = collector

    def record_request(
        self, method: str, path: str, status_code: int, duration_ms: float, **context
    ) -> None:
        """Record HTTP request performance."""
        # Request duration metric
        latency_metric = PerformanceMetric(
            name="http_request",
            value=duration_ms,
            metric_type=MetricType.LATENCY,
            unit="ms",
            timestamp=datetime.now(timezone.utc),
            tags={
                "method": method,
                "endpoint": self._normalize_endpoint(path),
                "status_class": f"{status_code // 100}xx",
                "status": "success" if status_code < 400 else "error",
            },
            context=context,
        )
        self.collector.record_metric(latency_metric)

        # Error rate metric
        if status_code >= 400:
            error_metric = PerformanceMetric(
                name="http_errors",
                value=1,
                metric_type=MetricType.ERROR_RATE,
                unit="count",
                timestamp=datetime.now(timezone.utc),
                tags={
                    "method": method,
                    "endpoint": self._normalize_endpoint(path),
                    "status_code": str(status_code),
                },
                context=context,
            )
            self.collector.record_metric(error_metric)

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for consistent metrics."""
        # Replace IDs with placeholders
        import re

        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            path,
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)
        return path


# Global performance monitoring system
performance_collector = OptimalPerformanceCollector()
database_monitor = DatabasePerformanceMonitor(performance_collector)
http_monitor = HTTPPerformanceMonitor(performance_collector)

# Clean exports
__all__ = [
    "OptimalPerformanceCollector",
    "DatabasePerformanceMonitor",
    "HTTPPerformanceMonitor",
    "PerformanceMetric",
    "PerformanceAlert",
    "MetricType",
    "AlertLevel",
    "performance_collector",
    "database_monitor",
    "http_monitor",
]
