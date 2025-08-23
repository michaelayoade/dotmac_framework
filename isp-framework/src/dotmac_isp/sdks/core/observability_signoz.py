"""
SignOz-native observability for DotMac services.
Unified metrics, traces, and logs using OpenTelemetry with SignOz as the sole backend.
Replaces Prometheus/Grafana with SignOz's native capabilities.
"""

import os
import logging
import time
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from contextlib import contextmanager
from datetime import datetime, timezone
import json

# OpenTelemetry imports
from opentelemetry import trace, metrics, baggage
from opentelemetry.exporter.otlp.proto.grpc import (
    trace_exporter as otlp_trace,
    metric_exporter as otlp_metric,
    _log_exporter as otlp_log,
)
from opentelemetry.sdk import trace as trace_sdk, metrics as metrics_sdk
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import (
    Resource,
    SERVICE_NAME,
    SERVICE_VERSION,
    SERVICE_INSTANCE_ID,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation

# Instrumentation imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

# Propagation
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.composite import CompositePropagator

logger = logging.getLogger(__name__)


class SignOzTelemetry:
    """
    Unified SignOz telemetry configuration for DotMac services.
    Replaces Prometheus/Grafana with SignOz-native observability.
    """

    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: Optional[str] = None,
        signoz_endpoint: Optional[str] = None,
        signoz_access_token: Optional[str] = None,
        enable_metrics: bool = True,
        enable_traces: bool = True,
        enable_logs: bool = True,
        enable_profiling: bool = False,
        insecure: bool = True,
        custom_attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize SignOz telemetry.

        Args:
            service_name: Name of the service
            service_version: Service version
            environment: Deployment environment (dev/staging/prod)
            signoz_endpoint: SignOz collector endpoint
            signoz_access_token: SignOz access token (for SaaS)
            enable_metrics: Enable metrics collection
            enable_traces: Enable distributed tracing
            enable_logs: Enable log collection
            enable_profiling: Enable continuous profiling
            insecure: Use insecure connection (for local dev)
            custom_attributes: Additional resource attributes
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.signoz_endpoint = signoz_endpoint or os.getenv(
            "SIGNOZ_ENDPOINT", "localhost:4317"  # Default SignOz OTLP endpoint
        )
        self.signoz_access_token = signoz_access_token or os.getenv(
            "SIGNOZ_ACCESS_TOKEN"
        )
        self.insecure = insecure

        # Instance ID for service discovery
        import socket
        import uuid

        self.instance_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

        # Build resource attributes for SignOz
        resource_attributes = {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            SERVICE_INSTANCE_ID: self.instance_id,
            "deployment.environment": self.environment,
            "service.namespace": "dotmac",
            "cloud.provider": os.getenv("CLOUD_PROVIDER", "local"),
            "cloud.region": os.getenv("CLOUD_REGION", "us-east-1"),
            "host.name": socket.gethostname(),
            "host.type": os.getenv("HOST_TYPE", "container"),
            "os.type": os.name,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "1.25.0",
        }

        # Add custom attributes
        if custom_attributes:
            resource_attributes.update(custom_attributes)

        self.resource = Resource.create(resource_attributes)

        # Headers for SignOz SaaS
        self.headers = {}
        if self.signoz_access_token:
            self.headers = {"signoz-access-token": self.signoz_access_token}

        # Initialize providers
        self.tracer_provider = None
        self.meter_provider = None
        self.logger_provider = None
        self.tracer = None
        self.meter = None
        self.otel_logger = None

        # Metrics storage for SignOz
        self._metrics = {}

        # Setup telemetry components
        if enable_traces:
            self._setup_tracing()

        if enable_metrics:
            self._setup_metrics()

        if enable_logs:
            self._setup_logging()

        if enable_profiling:
            self._setup_profiling()

        # Setup context propagation
        self._setup_propagators()

        # Initialize custom SignOz metrics
        self._init_signoz_metrics()

        logger.info(
            f"SignOz telemetry initialized for {service_name} at {self.signoz_endpoint}"
        )

    def _setup_tracing(self):
        """Configure distributed tracing for SignOz."""
        # Create OTLP trace exporter for SignOz
        trace_exporter = otlp_trace.OTLPSpanExporter(
            endpoint=self.signoz_endpoint,
            headers=self.headers,
            insecure=self.insecure,
            timeout=30,
        )

        # Create tracer provider with SignOz resource
        self.tracer_provider = TracerProvider(resource=self.resource)

        # Add batch span processor optimized for SignOz
        span_processor = BatchSpanProcessor(
            trace_exporter,
            max_queue_size=10000,  # Increased for high throughput
            max_export_batch_size=1000,
            schedule_delay_millis=1000,
            export_timeout_millis=30000,
        )
        self.tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(
            instrumenting_module_name=self.service_name,
            instrumenting_library_version=self.service_version,
        )

        logger.info(f"SignOz tracing configured for {self.service_name}")

    def _setup_metrics(self):
        """Configure metrics collection for SignOz (replaces Prometheus)."""
        # Create OTLP metric exporter for SignOz
        metric_exporter = otlp_metric.OTLPMetricExporter(
            endpoint=self.signoz_endpoint,
            headers=self.headers,
            insecure=self.insecure,
            timeout=30,
            preferred_temporality={
                metrics_sdk.InstrumentType.COUNTER: metrics_sdk.AggregationTemporality.DELTA,
                metrics_sdk.InstrumentType.HISTOGRAM: metrics_sdk.AggregationTemporality.DELTA,
                metrics_sdk.InstrumentType.UP_DOWN_COUNTER: metrics_sdk.AggregationTemporality.CUMULATIVE,
                metrics_sdk.InstrumentType.OBSERVABLE_COUNTER: metrics_sdk.AggregationTemporality.DELTA,
                metrics_sdk.InstrumentType.OBSERVABLE_GAUGE: metrics_sdk.AggregationTemporality.CUMULATIVE,
                metrics_sdk.InstrumentType.OBSERVABLE_UP_DOWN_COUNTER: metrics_sdk.AggregationTemporality.CUMULATIVE,
            },
        )

        # Create periodic exporting metric reader for SignOz
        metric_reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=30000,  # 30 seconds
            export_timeout_millis=10000,
        )

        # Define views for custom histogram buckets (SignOz optimization)
        views = [
            View(
                instrument_type=metrics_sdk.InstrumentType.HISTOGRAM,
                instrument_name="http.server.duration",
                aggregation=ExplicitBucketHistogramAggregation(
                    boundaries=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
                ),
            ),
            View(
                instrument_type=metrics_sdk.InstrumentType.HISTOGRAM,
                instrument_name="db.client.duration",
                aggregation=ExplicitBucketHistogramAggregation(
                    boundaries=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
                ),
            ),
        ]

        # Create meter provider for SignOz
        self.meter_provider = MeterProvider(
            resource=self.resource, metric_readers=[metric_reader], views=views
        )

        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)

        # Get meter
        self.meter = metrics.get_meter(
            name=self.service_name, version=self.service_version
        )

        # Initialize system metrics for SignOz
        SystemMetricsInstrumentor().instrument()

        logger.info(f"SignOz metrics configured for {self.service_name}")

    def _setup_logging(self):
        """Configure log collection for SignOz (replaces Loki)."""
        # Create OTLP log exporter for SignOz
        log_exporter = otlp_log.OTLPLogExporter(
            endpoint=self.signoz_endpoint, headers=self.headers, insecure=self.insecure
        )

        # Create logger provider for SignOz
        self.logger_provider = LoggerProvider(resource=self.resource)

        # Add batch log processor
        log_processor = BatchLogRecordProcessor(
            log_exporter,
            max_queue_size=10000,
            schedule_delay_millis=1000,
            max_export_batch_size=512,
        )
        self.logger_provider.add_log_record_processor(log_processor)

        # Create OTLP handler for Python logging
        handler = LoggingHandler(
            level=logging.INFO, logger_provider=self.logger_provider
        )

        # Attach to root logger for automatic log collection
        logging.getLogger().addHandler(handler)

        # Format logs with trace context for SignOz correlation
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s",
            level=logging.INFO,
        )

        # Get OpenTelemetry logger
        self.otel_logger = self.logger_provider.get_logger(self.service_name)

        logger.info(f"SignOz logging configured for {self.service_name}")

    def _setup_profiling(self):
        """Configure continuous profiling for SignOz (optional)."""
        try:
            # SignOz supports pyroscope for profiling
            import pyroscope

            pyroscope.configure(
                application_name=f"{self.service_name}.{self.environment}",
                server_address=os.getenv("PYROSCOPE_SERVER", "http://localhost:4040"),
                tags={
                    "service": self.service_name,
                    "environment": self.environment,
                    "version": self.service_version,
                },
            )

            logger.info(f"SignOz profiling configured for {self.service_name}")
        except ImportError:
            logger.warning("Pyroscope not installed, profiling disabled")

    def _setup_propagators(self):
        """Setup context propagation for SignOz distributed tracing."""
        # Use W3C Trace Context and Baggage for SignOz
        set_global_textmap(
            CompositePropagator(
                [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
            )
        )

    def _init_signoz_metrics(self):
        """Initialize SignOz-optimized metrics (replaces Prometheus metrics)."""
        # HTTP metrics (RED method)
        self._metrics["request_counter"] = self.meter.create_counter(
            name="http.server.request.count",
            description="Total HTTP requests",
            unit="1",
        )

        self._metrics["request_duration"] = self.meter.create_histogram(
            name="http.server.duration", description="HTTP request duration", unit="ms"
        )

        self._metrics["active_requests"] = self.meter.create_up_down_counter(
            name="http.server.active_requests",
            description="Active HTTP requests",
            unit="1",
        )

        # Database metrics
        self._metrics["db_duration"] = self.meter.create_histogram(
            name="db.client.duration", description="Database query duration", unit="ms"
        )

        self._metrics["db_connections"] = self.meter.create_observable_gauge(
            name="db.client.connections",
            callbacks=[self._get_db_connections],
            description="Active database connections",
            unit="1",
        )

        # Business metrics
        self._metrics["business_events"] = self.meter.create_counter(
            name="business.events.count", description="Business events", unit="1"
        )

        self._metrics["revenue"] = self.meter.create_counter(
            name="business.revenue.total", description="Total revenue", unit="USD"
        )

        # Cache metrics
        self._metrics["cache_hits"] = self.meter.create_counter(
            name="cache.hits", description="Cache hits", unit="1"
        )

        self._metrics["cache_misses"] = self.meter.create_counter(
            name="cache.misses", description="Cache misses", unit="1"
        )

        # Queue metrics
        self._metrics["queue_size"] = self.meter.create_observable_gauge(
            name="queue.size",
            callbacks=[self._get_queue_size],
            description="Queue size",
            unit="1",
        )

        logger.info("SignOz metrics initialized")

    def _get_db_connections(self, options):
        """Callback for database connections metric."""
        # This would query actual connection pool
        return [(10, {"pool": "primary"}), (5, {"pool": "replica"})]

    def _get_queue_size(self, options):
        """Callback for queue size metric."""
        # This would query actual queue
        return [(100, {"queue": "tasks"}), (50, {"queue": "events"})]

    def instrument_fastapi(self, app):
        """
        Instrument FastAPI application for SignOz.

        Args:
            app: FastAPI application instance
        """

        # Custom request hook for SignOz attributes
        def request_hook(span, scope):
            if span and span.is_recording():
                # Add SignOz-specific attributes
                headers = dict(scope.get("headers", []))

                # Extract tenant context
                tenant_id = headers.get(b"x-tenant-id", b"default").decode()
                span.set_attribute("tenant.id", tenant_id)
                baggage.set_baggage("tenant_id", tenant_id)

                # Extract user context
                user_id = headers.get(b"x-user-id", b"anonymous").decode()
                span.set_attribute("enduser.id", user_id)

                # Add custom business attributes
                span.set_attribute("app.endpoint.name", scope.get("path", "/"))
                span.set_attribute("app.api.version", "v1")

        # Custom response hook for SignOz metrics
        def response_hook(span, message):
            if span and span.is_recording():
                status_code = message.get("status", 0)

                # Set span status for SignOz
                if status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))

                # Record SignOz metrics
                self.record_http_metrics(
                    method=span.attributes.get("http.method", "GET"),
                    path=span.attributes.get("http.target", "/"),
                    status_code=status_code,
                    duration=time.time() * 1000,  # Convert to ms for SignOz
                )

        # Instrument with SignOz configuration
        FastAPIInstrumentor.instrument_app(
            app,
            server_request_hook=request_hook,
            client_response_hook=response_hook,
            excluded_urls="/health,/metrics,/docs,/openapi.json,/favicon.ico",
        )

        logger.info(f"FastAPI instrumented for SignOz: {self.service_name}")

    def record_http_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        tenant_id: str = "default",
    ):
        """Record HTTP metrics for SignOz dashboards."""
        attributes = {
            "http.method": method,
            "http.route": path,
            "http.status_code": str(status_code),
            "http.status_class": f"{status_code // 100}xx",
            "tenant.id": tenant_id,
            "service.name": self.service_name,
        }

        # Increment request counter
        self._metrics["request_counter"].add(1, attributes)

        # Record duration
        self._metrics["request_duration"].record(duration, attributes)

    def record_business_event(
        self,
        event_type: str,
        tenant_id: str,
        value: float = 1.0,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Record business event for SignOz.

        Args:
            event_type: Type of business event
            tenant_id: Tenant identifier
            value: Event value (default 1)
            attributes: Additional attributes
        """
        event_attributes = {
            "event.type": event_type,
            "tenant.id": tenant_id,
            "service.name": self.service_name,
            **(attributes or {}),
        }

        # Record metric
        self._metrics["business_events"].add(value, event_attributes)

        # Create span for important events
        with self.tracer.start_as_current_span(
            f"business.{event_type}",
            kind=SpanKind.INTERNAL,
            attributes=event_attributes,
        ) as span:
            span.add_event(name=event_type, attributes={"value": value})

    def record_revenue(
        self,
        amount: float,
        currency: str = "USD",
        tenant_id: str = "default",
        transaction_type: str = "payment",
    ):
        """Record revenue metrics for SignOz business dashboards."""
        self._metrics["revenue"].add(
            amount,
            {
                "currency": currency,
                "tenant.id": tenant_id,
                "transaction.type": transaction_type,
                "service.name": self.service_name,
            },
        )

    def record_cache_operation(
        self, operation: str, hit: bool, key: str, duration_ms: float
    ):
        """Record cache metrics for SignOz."""
        if hit:
            self._metrics["cache_hits"].add(1, {"operation": operation})
        else:
            self._metrics["cache_misses"].add(1, {"operation": operation})

        # Trace cache operation
        with self.tracer.start_as_current_span(
            f"cache.{operation}", kind=SpanKind.CLIENT
        ) as span:
            span.set_attribute("cache.key", key)
            span.set_attribute("cache.hit", hit)
            span.set_attribute("cache.duration_ms", duration_ms)

    @contextmanager
    def trace_operation(
        self,
        name: str,
        operation_type: str = "business",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing operations in SignOz.

        Args:
            name: Operation name
            operation_type: Type of operation
            attributes: Additional attributes
        """
        with self.tracer.start_as_current_span(
            f"{operation_type}.{name}",
            kind=SpanKind.INTERNAL,
            attributes=attributes or {},
        ) as span:
            start_time = time.time()
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration_ms)

    def create_signoz_dashboard(self) -> Dict[str, Any]:
        """
        Create SignOz dashboard configuration for this service.
        Returns dashboard JSON that can be imported into SignOz.
        """
        return {
            "title": f"{self.service_name} Dashboard",
            "description": f"SignOz dashboard for {self.service_name}",
            "tags": ["service", self.service_name, self.environment],
            "widgets": [
                {
                    "title": "Request Rate",
                    "type": "graph",
                    "query": {
                        "queryType": "metric",
                        "metric": "http.server.request.count",
                        "aggregation": "rate",
                        "groupBy": ["http.status_class"],
                        "filters": {"service.name": self.service_name},
                    },
                },
                {
                    "title": "Request Duration (P95)",
                    "type": "graph",
                    "query": {
                        "queryType": "metric",
                        "metric": "http.server.duration",
                        "aggregation": "p95",
                        "groupBy": ["http.route"],
                        "filters": {"service.name": self.service_name},
                    },
                },
                {
                    "title": "Error Rate",
                    "type": "graph",
                    "query": {
                        "queryType": "trace",
                        "aggregation": "count",
                        "groupBy": ["serviceName"],
                        "filters": {
                            "serviceName": self.service_name,
                            "statusCode": "ERROR",
                        },
                    },
                },
                {
                    "title": "Business Events",
                    "type": "graph",
                    "query": {
                        "queryType": "metric",
                        "metric": "business.events.count",
                        "aggregation": "sum",
                        "groupBy": ["event.type"],
                        "filters": {"service.name": self.service_name},
                    },
                },
            ],
        }

    def shutdown(self):
        """Shutdown SignOz telemetry providers."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()

        if self.meter_provider:
            self.meter_provider.shutdown()

        if self.logger_provider:
            self.logger_provider.shutdown()

        logger.info(f"SignOz telemetry shutdown for {self.service_name}")


# Global SignOz telemetry instance
_signoz_telemetry: Optional[SignOzTelemetry] = None


def init_signoz(
    service_name: str, service_version: str = "1.0.0", **kwargs
) -> SignOzTelemetry:
    """
    Initialize global SignOz telemetry instance.

    Args:
        service_name: Service name
        service_version: Service version
        **kwargs: Additional configuration

    Returns:
        SignOz telemetry instance
    """
    global _signoz_telemetry
    _signoz_telemetry = SignOzTelemetry(
        service_name=service_name, service_version=service_version, **kwargs
    )
    return _signoz_telemetry


def get_signoz() -> Optional[SignOzTelemetry]:
    """Get global SignOz telemetry instance."""
    return _signoz_telemetry


# Convenience decorators for SignOz
def trace(name: Optional[str] = None):
    """Decorator for tracing functions with SignOz."""

    def decorator(func):
        if _signoz_telemetry:
            span_name = name or f"{_signoz_telemetry.service_name}.{func.__name__}"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with _signoz_telemetry.trace_operation(span_name):
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with _signoz_telemetry.trace_operation(span_name):
                    return func(*args, **kwargs)

            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return func

    return decorator
