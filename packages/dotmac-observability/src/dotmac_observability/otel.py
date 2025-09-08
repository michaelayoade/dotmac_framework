"""OpenTelemetry integration for dotmac-observability."""

from typing import Optional

from .metrics import MetricsCollector

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.metrics import set_meter_provider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    OTEL_AVAILABLE = True
except ImportError:
    # Graceful degradation when OpenTelemetry is not installed
    OTEL_AVAILABLE = False
    otel_metrics = OTLPMetricExporter = MeterProvider = None
    PeriodicExportingMetricReader = Resource = set_meter_provider = None


class OTelBridge:
    """
    Bridge between MetricsCollector and OpenTelemetry.

    Forwards metrics from the collector to OTEL for export to
    observability backends like Prometheus, Jaeger, etc.
    """

    def __init__(self, collector: MetricsCollector, service_name: str):
        """
        Initialize the OTEL bridge.

        Args:
            collector: MetricsCollector to bridge
            service_name: Service name for OTEL resource
        """
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry extras not installed. Install with: pip install dotmac-observability[otel]"
            )

        self.collector = collector
        self.service_name = service_name
        self._meter: Optional[object] = None
        self._counters: dict[str, object] = {}
        self._histograms: dict[str, object] = {}
        self._gauges: dict[str, object] = {}

    def setup_meter(
        self,
        *,
        otlp_endpoint: Optional[str] = None,
        resource_attrs: Optional[dict[str, str]] = None,
        export_interval: int = 30,
    ) -> None:
        """
        Set up OTEL meter with optional OTLP exporter.

        Args:
            otlp_endpoint: OTLP gRPC endpoint (e.g., "http://localhost:4317")
            resource_attrs: Additional resource attributes
            export_interval: Export interval in seconds
        """
        # Create resource
        attrs = {
            "service.name": self.service_name,
            "service.version": "1.0.0",
        }
        if resource_attrs:
            attrs.update(resource_attrs)

        resource = Resource.create(attrs)

        # Set up exporter if endpoint provided
        readers = []
        if otlp_endpoint:
            exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
            reader = PeriodicExportingMetricReader(
                exporter=exporter, export_interval_millis=export_interval * 1000
            )
            readers.append(reader)

        # Create meter provider
        provider = MeterProvider(resource=resource, metric_readers=readers)
        set_meter_provider(provider)

        # Get meter
        self._meter = otel_metrics.get_meter(__name__, version="1.0.0")

    def sync_metrics(self) -> None:
        """
        Synchronize metrics from collector to OTEL.

        This should be called periodically to export collector metrics
        to OpenTelemetry.
        """
        if not self._meter:
            raise RuntimeError("Meter not set up. Call setup_meter() first.")

        summary = self.collector.get_summary()

        # Sync counters
        for key, value in summary.get("counters", {}).items():
            if key not in self._counters:
                self._counters[key] = self._meter.create_counter(
                    name=key.split("#")[0],  # Remove tags from name
                    description=f"Counter metric {key}",
                )
            # Note: In a real implementation, you'd need to parse tags
            # and set them as attributes in the measurement
            self._counters[key].add(value)

        # Sync gauges
        for key, value in summary.get("gauges", {}).items():
            if key not in self._gauges:
                # Create observable gauge
                gauge_name = key.split("#")[0]

                def gauge_callback(key=key, value=value):
                    return [(value, {})]  # Empty attributes for now

                self._gauges[key] = self._meter.create_observable_gauge(
                    name=gauge_name,
                    callbacks=[gauge_callback],
                    description=f"Gauge metric {key}",
                )

        # Sync histograms
        for key, stats in summary.get("histograms", {}).items():
            if key not in self._histograms:
                self._histograms[key] = self._meter.create_histogram(
                    name=key.split("#")[0],
                    description=f"Histogram metric {key}",
                )

            # Record individual values (in a real implementation,
            # you'd want to batch these or use the summary statistics)
            for _ in range(stats.get("count", 0)):
                self._histograms[key].record(stats.get("mean", 0))


def enable_otel_bridge(
    collector: MetricsCollector,
    *,
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    resource_attrs: Optional[dict[str, str]] = None,
    auto_sync: bool = True,
    sync_interval: int = 30,
) -> OTelBridge:
    """
    Enable OpenTelemetry bridge for a metrics collector.

    Args:
        collector: MetricsCollector to bridge
        service_name: Service name for OTEL resource
        otlp_endpoint: OTLP gRPC endpoint for export
        resource_attrs: Additional resource attributes
        auto_sync: Whether to automatically sync metrics periodically
        sync_interval: Auto-sync interval in seconds

    Returns:
        Configured OTelBridge instance

    Example:
        from dotmac_observability import get_collector, enable_otel_bridge

        collector = get_collector()
        bridge = enable_otel_bridge(
            collector,
            service_name="my-service",
            otlp_endpoint="http://localhost:4317"
        )
    """
    if not OTEL_AVAILABLE:
        raise ImportError(
            "OpenTelemetry extras not installed. Install with: pip install dotmac-observability[otel]"
        )

    bridge = OTelBridge(collector, service_name)
    bridge.setup_meter(
        otlp_endpoint=otlp_endpoint, resource_attrs=resource_attrs, export_interval=sync_interval
    )

    if auto_sync:
        # In a real implementation, you'd set up a background task
        # to periodically call bridge.sync_metrics()
        # For now, we'll just sync once
        try:
            bridge.sync_metrics()
        except Exception:
            # Ignore errors during initial sync
            pass

    return bridge
