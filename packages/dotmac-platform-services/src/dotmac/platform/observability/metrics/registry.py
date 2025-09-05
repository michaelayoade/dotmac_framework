"""
Metrics registry abstraction over OpenTelemetry and Prometheus.
"""

import logging
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.sdk.metrics import Meter

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    Meter = Any
    otel_metrics = Any

try:
    from prometheus_client import (
        CollectorRegistry,
        generate_latest,
    )
    from prometheus_client import (
        Counter as PrometheusCounter,
    )
    from prometheus_client import (
        Gauge as PrometheusGauge,
    )
    from prometheus_client import (
        Histogram as PrometheusHistogram,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CollectorRegistry = Any
    PrometheusCounter = Any
    PrometheusGauge = Any
    PrometheusHistogram = Any

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Supported metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    UP_DOWN_COUNTER = "up_down_counter"


@dataclass
class MetricDefinition:
    """Definition of a metric for registration."""

    name: str
    type: MetricType
    description: str
    labels: list[str] | None = None
    buckets: Sequence[float] | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        """Validate metric definition."""
        if self.type == MetricType.HISTOGRAM and self.buckets is None:
            # Default histogram buckets
            self.buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

        # Ensure labels is not None
        if self.labels is None:
            self.labels = []


@dataclass
class MetricInstrument:
    """Wrapper around metric instruments from different backends."""

    definition: MetricDefinition
    otel_instrument: Any | None = None
    prometheus_instrument: Any | None = None

    def record(self, value: int | float, labels: dict[str, str] | None = None) -> None:
        """Record a value for this metric."""
        labels = labels or {}

        try:
            # Record to OpenTelemetry
            if self.otel_instrument:
                if self.definition.type in (MetricType.COUNTER, MetricType.UP_DOWN_COUNTER):
                    self.otel_instrument.add(value, labels)
                elif self.definition.type == MetricType.GAUGE:
                    self.otel_instrument.set(value, labels)
                elif self.definition.type == MetricType.HISTOGRAM:
                    self.otel_instrument.record(value, labels)

            # Record to Prometheus
            if self.prometheus_instrument:
                if self.definition.labels:
                    # Extract label values in order
                    label_values = [labels.get(label, "") for label in self.definition.labels]

                    if self.definition.type == MetricType.COUNTER:
                        self.prometheus_instrument.labels(*label_values).inc(value)
                    elif self.definition.type == MetricType.UP_DOWN_COUNTER:
                        # Prometheus Counter doesn't support negative values, use Gauge
                        self.prometheus_instrument.labels(*label_values).inc(value)
                    elif self.definition.type == MetricType.GAUGE:
                        self.prometheus_instrument.labels(*label_values).set(value)
                    elif self.definition.type == MetricType.HISTOGRAM:
                        self.prometheus_instrument.labels(*label_values).observe(value)
                else:
                    # No labels
                    if self.definition.type == MetricType.COUNTER:
                        self.prometheus_instrument.inc(value)
                    elif self.definition.type == MetricType.UP_DOWN_COUNTER:
                        self.prometheus_instrument.inc(value)
                    elif self.definition.type == MetricType.GAUGE:
                        self.prometheus_instrument.set(value)
                    elif self.definition.type == MetricType.HISTOGRAM:
                        self.prometheus_instrument.observe(value)

        except Exception as e:
            logger.error(f"Failed to record metric {self.definition.name}: {e}")


class MetricsRegistry:
    """
    Unified metrics registry supporting both OpenTelemetry and Prometheus.
    """

    def __init__(
        self,
        service_name: str,
        enable_prometheus: bool = True,
        prometheus_registry: Optional["CollectorRegistry"] = None,
    ) -> None:
        self.service_name = service_name
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self._metrics: dict[str, MetricInstrument] = {}
        self._otel_meter: Meter | None = None

        # Prometheus registry
        if self.enable_prometheus:
            self._prometheus_registry = prometheus_registry or CollectorRegistry()
        else:
            self._prometheus_registry = None

        logger.info(f"Metrics registry initialized for {service_name}")

    def set_otel_meter(self, meter: Meter | None) -> None:
        """Set the OpenTelemetry meter for this registry."""
        self._otel_meter = meter

        # Re-register all metrics with the new meter
        if meter and OTEL_AVAILABLE:
            for metric_name, metric_instrument in self._metrics.items():
                try:
                    otel_instrument = self._create_otel_instrument(
                        metric_instrument.definition, meter
                    )
                    metric_instrument.otel_instrument = otel_instrument
                except Exception as e:
                    logger.error(f"Failed to re-register OTEL metric {metric_name}: {e}")

    def register_metric(self, definition: MetricDefinition) -> bool:
        """
        Register a metric with the registry.

        Args:
            definition: Metric definition

        Returns:
            True if successful, False otherwise
        """
        if definition.name in self._metrics:
            logger.warning(f"Metric {definition.name} already registered")
            return False

        try:
            # Create OpenTelemetry instrument
            otel_instrument = None
            if self._otel_meter and OTEL_AVAILABLE:
                otel_instrument = self._create_otel_instrument(definition, self._otel_meter)

            # Create Prometheus instrument
            prometheus_instrument = None
            if self.enable_prometheus:
                prometheus_instrument = self._create_prometheus_instrument(definition)

            # Create wrapper
            instrument = MetricInstrument(
                definition=definition,
                otel_instrument=otel_instrument,
                prometheus_instrument=prometheus_instrument,
            )

            self._metrics[definition.name] = instrument
            logger.debug(f"Registered metric: {definition.name} ({definition.type})")
            return True

        except Exception as e:
            logger.error(f"Failed to register metric {definition.name}: {e}")
            return False

    def get_metric(self, name: str) -> MetricInstrument | None:
        """Get a registered metric by name."""
        return self._metrics.get(name)

    def record_metric(
        self,
        name: str,
        value: int | float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Record a value for a metric.

        Args:
            name: Metric name
            value: Value to record
            labels: Optional labels
        """
        metric = self.get_metric(name)
        if metric:
            metric.record(value, labels)
        else:
            logger.warning(f"Metric {name} not found in registry")

    def increment_counter(
        self,
        name: str,
        value: int | float = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric."""
        self.record_metric(name, value, labels)

    def set_gauge(
        self,
        name: str,
        value: int | float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge metric value."""
        self.record_metric(name, value, labels)

    def observe_histogram(
        self,
        name: str,
        value: int | float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Observe a histogram metric."""
        self.record_metric(name, value, labels)

    def get_prometheus_registry(self) -> Optional["CollectorRegistry"]:
        """Get the Prometheus registry."""
        return self._prometheus_registry

    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        if not self.enable_prometheus or not self._prometheus_registry:
            return ""

        try:
            return generate_latest(self._prometheus_registry).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return ""

    def list_metrics(self) -> list[str]:
        """List all registered metric names."""
        return list(self._metrics.keys())

    def get_metrics_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all registered metrics."""
        return {
            name: {
                "type": instrument.definition.type.value,
                "description": instrument.definition.description,
                "labels": instrument.definition.labels,
                "unit": instrument.definition.unit,
            }
            for name, instrument in self._metrics.items()
        }

    def _create_otel_instrument(self, definition: MetricDefinition, meter: Meter) -> Any:
        """Create OpenTelemetry instrument."""
        kwargs = {
            "name": definition.name,
            "description": definition.description,
        }
        if definition.unit:
            kwargs["unit"] = definition.unit

        if definition.type == MetricType.COUNTER:
            return meter.create_counter(**kwargs)
        elif definition.type == MetricType.UP_DOWN_COUNTER:
            return meter.create_up_down_counter(**kwargs)
        elif definition.type == MetricType.GAUGE:
            return meter.create_gauge(**kwargs)
        elif definition.type == MetricType.HISTOGRAM:
            return meter.create_histogram(**kwargs)
        else:
            raise ValueError(f"Unsupported OTEL metric type: {definition.type}")

    def _create_prometheus_instrument(self, definition: MetricDefinition) -> Any:
        """Create Prometheus instrument."""
        if not PROMETHEUS_AVAILABLE:
            return None

        kwargs = {
            "name": definition.name,
            "documentation": definition.description,
            "labelnames": definition.labels or [],
            "registry": self._prometheus_registry,
        }

        if definition.type == MetricType.COUNTER:
            return PrometheusCounter(**kwargs)
        elif definition.type == MetricType.UP_DOWN_COUNTER:
            # Use Gauge for up-down counter in Prometheus
            return PrometheusGauge(**kwargs)
        elif definition.type == MetricType.GAUGE:
            return PrometheusGauge(**kwargs)
        elif definition.type == MetricType.HISTOGRAM:
            if definition.buckets:
                kwargs["buckets"] = definition.buckets
            return PrometheusHistogram(**kwargs)
        else:
            raise ValueError(f"Unsupported Prometheus metric type: {definition.type}")


def initialize_metrics_registry(
    service_name: str,
    enable_prometheus: bool = True,
    prometheus_registry: Optional["CollectorRegistry"] = None,
) -> MetricsRegistry:
    """
    Initialize a metrics registry.

    Args:
        service_name: Name of the service
        enable_prometheus: Whether to enable Prometheus support
        prometheus_registry: Optional existing Prometheus registry

    Returns:
        Configured MetricsRegistry
    """
    if enable_prometheus and not PROMETHEUS_AVAILABLE:
        warnings.warn(
            "Prometheus support requested but prometheus-client not installed. "
            "Install with: pip install 'dotmac-observability[prometheus]'",
            UserWarning,
            stacklevel=2,
        )
        enable_prometheus = False

    registry = MetricsRegistry(
        service_name=service_name,
        enable_prometheus=enable_prometheus,
        prometheus_registry=prometheus_registry,
    )

    # Register default system metrics
    _register_default_metrics(registry)

    return registry


def _register_default_metrics(registry: MetricsRegistry) -> None:
    """Register default system metrics."""
    default_metrics = [
        MetricDefinition(
            name="http_requests_total",
            type=MetricType.COUNTER,
            description="Total HTTP requests",
            labels=["method", "endpoint", "status_code"],
        ),
        MetricDefinition(
            name="http_request_duration_seconds",
            type=MetricType.HISTOGRAM,
            description="HTTP request duration in seconds",
            labels=["method", "endpoint"],
            unit="s",
        ),
        MetricDefinition(
            name="system_memory_usage_bytes",
            type=MetricType.GAUGE,
            description="Current memory usage in bytes",
            unit="byte",
        ),
        MetricDefinition(
            name="system_cpu_usage_percent",
            type=MetricType.GAUGE,
            description="Current CPU usage percentage",
            unit="percent",
        ),
        MetricDefinition(
            name="database_connections_active",
            type=MetricType.GAUGE,
            description="Active database connections",
        ),
        MetricDefinition(
            name="database_query_duration_seconds",
            type=MetricType.HISTOGRAM,
            description="Database query duration in seconds",
            labels=["operation", "table"],
            unit="s",
        ),
    ]

    for metric_def in default_metrics:
        registry.register_metric(metric_def)
