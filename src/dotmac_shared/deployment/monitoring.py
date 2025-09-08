"""
Lightweight monitoring adapter for deployment modules.

Bridges deployment code to platform observability (tracing + metrics)
without relying on deprecated dotmac_shared.observability.
"""

from contextlib import contextmanager
from typing import Any, Dict, Optional

from dotmac.platform.observability import get_tracer
from dotmac.platform.observability.metrics.registry import (
    MetricsRegistry,
    MetricDefinition,
    MetricType,
    initialize_metrics_registry,
)


class MonitoringStack:
    """Minimal monitoring surface used by deployment modules."""

    def __init__(self, service_name: str = "deployment") -> None:
        self.service_name = service_name
        self.tracer = get_tracer(service_name) if get_tracer else None
        # Use a registry without Prometheus exposition
        self.metrics: MetricsRegistry = initialize_metrics_registry(
            service_name, enable_prometheus=False
        )
        # Ensure common metrics exist
        self._ensure_metric(
            MetricDefinition(
                name="pipeline_stage_duration_seconds",
                type=MetricType.HISTOGRAM,
                description="Pipeline stage duration",
                labels=["pipeline", "stage", "status"],
                unit="s",
            )
        )
        self._ensure_metric(
            MetricDefinition(
                name="pipeline_stage_errors_total",
                type=MetricType.COUNTER,
                description="Pipeline stage errors",
                labels=["pipeline", "stage", "error"],
            )
        )

    def _ensure_metric(self, definition: MetricDefinition) -> None:
        if self.metrics.get_metric(definition.name) is None:
            self.metrics.register_metric(definition)

    @contextmanager
    def create_span(self, name: str, component: Optional[str] = None):
        """Context manager that starts a tracing span if tracer is available."""
        if self.tracer is None:
            # no-op span
            class _Span:
                def set_tag(self, key: str, value: Any) -> None:  # compatibility
                    pass

                def set_attribute(self, key: str, value: Any) -> None:
                    pass

            yield _Span()
            return

        with self.tracer.start_as_current_span(name) as span:
            if component:
                try:
                    span.set_attribute("component", component)
                except Exception:
                    pass
            # Provide set_tag compatibility
            def _set_tag(k: str, v: Any) -> None:
                try:
                    span.set_attribute(k, v)
                except Exception:
                    pass

            setattr(span, "set_tag", _set_tag)
            yield span

    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        self.metrics.increment_counter(name, 1, labels or {})

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.metrics.observe_histogram(name, value, labels or {})

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.metrics.set_gauge(name, value, labels or {})

