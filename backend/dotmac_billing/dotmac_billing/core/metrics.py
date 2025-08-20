"""
Performance monitoring and metrics export for platform integration.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat()
        }


class MetricsCollector:
    """Collects and manages metrics for the billing system."""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels or {})
            self._counters[key] += value

            metric = Metric(name, self._counters[key], MetricType.COUNTER, labels or {})
            self._metrics[key].append(metric)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self._lock:
            key = self._make_key(name, labels or {})
            self._gauges[key] = value

            metric = Metric(name, value, MetricType.GAUGE, labels or {})
            self._metrics[key].append(metric)

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a value to histogram metric."""
        with self._lock:
            key = self._make_key(name, labels or {})
            self._histograms[key].append(value)

            metric = Metric(name, value, MetricType.HISTOGRAM, labels or {})
            self._metrics[key].append(metric)

    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            key = self._make_key(name, labels or {})

            with self._lock:
                metric = Metric(name, duration, MetricType.TIMER, labels or {})
                self._metrics[key].append(metric)

    def get_metrics(self, name_filter: Optional[str] = None) -> List[Metric]:
        """Get collected metrics."""
        with self._lock:
            metrics = []
            for key, metric_deque in self._metrics.items():
                if name_filter is None or name_filter in key:
                    metrics.extend(list(metric_deque))
            return metrics

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        with self._lock:
            summary = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
                "total_metrics": sum(len(deque) for deque in self._metrics.values())
            }

            # Calculate histogram statistics
            for key, values in self._histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values)
                    }

            return summary

    def clear(self):
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for the metric."""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class BillingMetrics:
    """Billing-specific metrics collection."""

    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.collector = collector or MetricsCollector()

    # Request metrics
    def record_api_request(self, endpoint: str, method: str, tenant_id: str, status_code: int, duration: float):
        """Record API request metrics."""
        labels = {
            "endpoint": endpoint,
            "method": method,
            "tenant": tenant_id,
            "status": str(status_code)
        }

        self.collector.counter("billing_requests_total", 1.0, labels)
        self.collector.histogram("billing_request_duration_seconds", duration, labels)

        if status_code >= 400:
            self.collector.counter("billing_errors_total", 1.0, labels)

    # Business metrics
    def record_invoice_created(self, tenant_id: str, amount: float, currency: str):
        """Record invoice creation."""
        labels = {"tenant": tenant_id, "currency": currency}
        self.collector.counter("billing_invoices_created_total", 1.0, labels)
        self.collector.histogram("billing_invoice_amount", amount, labels)

    def record_payment_processed(self, tenant_id: str, amount: float, currency: str, gateway: str, success: bool):
        """Record payment processing."""
        labels = {
            "tenant": tenant_id,
            "currency": currency,
            "gateway": gateway,
            "status": "success" if success else "failed"
        }

        self.collector.counter("billing_payments_total", 1.0, labels)
        if success:
            self.collector.histogram("billing_payment_amount", amount, labels)
        else:
            self.collector.counter("billing_payment_failures_total", 1.0, labels)

    def record_dunning_action(self, tenant_id: str, action_type: str, account_id: int):
        """Record dunning action."""
        labels = {
            "tenant": tenant_id,
            "action_type": action_type,
            "account_id": str(account_id)
        }
        self.collector.counter("billing_dunning_actions_total", 1.0, labels)

    # System metrics
    def record_database_operation(self, operation: str, table: str, duration: float, success: bool):
        """Record database operation metrics."""
        labels = {
            "operation": operation,
            "table": table,
            "status": "success" if success else "error"
        }

        self.collector.counter("billing_db_operations_total", 1.0, labels)
        self.collector.histogram("billing_db_operation_duration_seconds", duration, labels)

    def record_gateway_operation(self, gateway: str, operation: str, duration: float, success: bool):
        """Record payment gateway operation metrics."""
        labels = {
            "gateway": gateway,
            "operation": operation,
            "status": "success" if success else "error"
        }

        self.collector.counter("billing_gateway_operations_total", 1.0, labels)
        self.collector.histogram("billing_gateway_operation_duration_seconds", duration, labels)

    # Resource metrics
    def update_active_accounts(self, tenant_id: str, count: int):
        """Update active accounts gauge."""
        self.collector.gauge("billing_active_accounts", count, {"tenant": tenant_id})

    def update_pending_invoices(self, tenant_id: str, count: int):
        """Update pending invoices gauge."""
        self.collector.gauge("billing_pending_invoices", count, {"tenant": tenant_id})

    def update_overdue_invoices(self, tenant_id: str, count: int, total_amount: float):
        """Update overdue invoices metrics."""
        labels = {"tenant": tenant_id}
        self.collector.gauge("billing_overdue_invoices_count", count, labels)
        self.collector.gauge("billing_overdue_amount_total", total_amount, labels)

    def get_metrics(self) -> List[Metric]:
        """Get all billing metrics."""
        return self.collector.get_metrics()

    def get_summary(self) -> Dict[str, Any]:
        """Get billing metrics summary."""
        return self.collector.get_summary()


class PrometheusExporter:
    """Export metrics in Prometheus format."""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def export(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Add header
        lines.append("# Prometheus metrics export for DotMac Billing")
        lines.append(f"# Generated at {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        # Group metrics by name
        metrics_by_name = defaultdict(list)
        for metric in self.collector.get_metrics():
            metrics_by_name[metric.name].append(metric)

        for name, metrics in metrics_by_name.items():
            # Add help and type comments
            lines.append(f"# HELP {name} Billing system metric")

            # Determine type based on first metric
            if metrics:
                metric_type = metrics[0].metric_type
                prom_type = self._convert_type(metric_type)
                lines.append(f"# TYPE {name} {prom_type}")

            # Add metric values
            for metric in metrics:
                labels_str = ""
                if metric.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"

                lines.append(f"{name}{labels_str} {metric.value}")

            lines.append("")

        return "\n".join(lines)

    def _convert_type(self, metric_type: MetricType) -> str:
        """Convert metric type to Prometheus type."""
        mapping = {
            MetricType.COUNTER: "counter",
            MetricType.GAUGE: "gauge",
            MetricType.HISTOGRAM: "histogram",
            MetricType.TIMER: "histogram"
        }
        return mapping.get(metric_type, "gauge")


class MetricsMiddleware:
    """Middleware to collect API request metrics."""

    def __init__(self, metrics: BillingMetrics):
        self.metrics = metrics

    async def __call__(self, request, call_next):
        """Process request and collect metrics."""
        start_time = time.time()

        # Extract request info
        method = request.method
        endpoint = request.url.path
        tenant_id = request.headers.get("x-tenant-id", "unknown")

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            self.metrics.record_api_request(
                endpoint=endpoint,
                method=method,
                tenant_id=tenant_id,
                status_code=response.status_code,
                duration=duration
            )

            return response

        except Exception:
            duration = time.time() - start_time

            # Record error metrics
            self.metrics.record_api_request(
                endpoint=endpoint,
                method=method,
                tenant_id=tenant_id,
                status_code=500,
                duration=duration
            )

            raise


# Global metrics instance
_billing_metrics: Optional[BillingMetrics] = None


def get_billing_metrics() -> BillingMetrics:
    """Get global billing metrics instance."""
    global _billing_metrics
    if _billing_metrics is None:
        _billing_metrics = BillingMetrics()
    return _billing_metrics


def set_billing_metrics(metrics: BillingMetrics):
    """Set global billing metrics instance."""
    global _billing_metrics
    _billing_metrics = metrics
