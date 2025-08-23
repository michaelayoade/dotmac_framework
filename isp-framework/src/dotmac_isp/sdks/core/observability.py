"""
OpenTelemetry instrumentation for DotMac services.
Provides automatic instrumentation for FastAPI, SQLAlchemy, Redis, and custom spans.
"""

import os
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager
import json

from opentelemetry import trace, metrics, baggage
from opentelemetry.exporter.otlp.proto.grpc import (
    trace_exporter as otlp_trace,
    metric_exporter as otlp_metric,
)
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk import trace as trace_sdk, metrics as metrics_sdk
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.composite import CompositePropagator
from prometheus_client import Counter, Histogram, Gauge, Info

logger = logging.getLogger(__name__)


class DotMacTelemetry:
    """
    Centralized telemetry configuration for DotMac services.
    """

    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: Optional[str] = None,
        otel_endpoint: Optional[str] = None,
        enable_metrics: bool = True,
        enable_traces: bool = True,
        enable_logs: bool = True,
        custom_attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize telemetry with service configuration.

        Args:
            service_name: Name of the service
            service_version: Service version
            environment: Deployment environment
            otel_endpoint: OpenTelemetry collector endpoint
            enable_metrics: Enable metrics collection
            enable_traces: Enable distributed tracing
            enable_logs: Enable log correlation
            custom_attributes: Additional resource attributes
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.otel_endpoint = otel_endpoint or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        )

        # Build resource attributes
        resource_attributes = {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": self.environment,
            "service.namespace": "dotmac",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
            "host.name": os.getenv("HOSTNAME", "localhost"),
        }

        if custom_attributes:
            resource_attributes.update(custom_attributes)

        self.resource = Resource.create(resource_attributes)

        # Initialize providers
        self.tracer_provider = None
        self.meter_provider = None
        self.tracer = None
        self.meter = None

        if enable_traces:
            self._setup_tracing()

        if enable_metrics:
            self._setup_metrics()

        if enable_logs:
            self._setup_logging()

        # Setup propagators for distributed tracing
        self._setup_propagators()

        # Custom metrics
        self._init_custom_metrics()

    def _setup_tracing(self):
        """Configure distributed tracing."""
        # Create OTLP trace exporter
        trace_exporter = otlp_trace.OTLPSpanExporter(
            endpoint=self.otel_endpoint, insecure=True  # Use TLS in production
        )

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=self.resource)

        # Add batch span processor
        span_processor = BatchSpanProcessor(
            trace_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=1000,
        )
        self.tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(self.service_name, self.service_version)

        logger.info(f"Tracing initialized for {self.service_name}")

    def _setup_metrics(self):
        """Configure metrics collection."""
        # Create OTLP metric exporter
        metric_exporter = otlp_metric.OTLPMetricExporter(
            endpoint=self.otel_endpoint, insecure=True
        )

        # Create Prometheus exporter for local scraping
        prometheus_reader = PrometheusMetricReader()

        # Create meter provider with both exporters
        self.meter_provider = MeterProvider(
            resource=self.resource, metric_readers=[prometheus_reader], views=[]
        )

        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)

        # Get meter
        self.meter = metrics.get_meter(self.service_name, self.service_version)

        logger.info(f"Metrics initialized for {self.service_name}")

    def _setup_logging(self):
        """Configure log correlation with traces."""
        LoggingInstrumentor().instrument(
            set_logging_format=True, log_level=logging.INFO
        )

        logger.info(f"Log correlation initialized for {self.service_name}")

    def _setup_propagators(self):
        """Setup context propagation for distributed tracing."""
        set_global_textmap(
            CompositePropagator(
                [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
            )
        )

    def _init_custom_metrics(self):
        """Initialize custom business metrics."""
        # Request metrics
        self.request_counter = Counter(
            "dotmac_requests_total",
            "Total number of requests",
            ["service", "method", "endpoint", "status", "tenant_id"],
        )

        self.request_duration = Histogram(
            "dotmac_request_duration_seconds",
            "Request duration in seconds",
            ["service", "method", "endpoint", "tenant_id"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
        )

        # Business metrics
        self.business_events = Counter(
            "dotmac_business_events_total",
            "Business events counter",
            ["service", "event_type", "tenant_id", "status"],
        )

        self.active_connections = Gauge(
            "dotmac_active_connections",
            "Number of active connections",
            ["service", "connection_type"],
        )

        # Service info
        self.service_info = Info("dotmac_service", "Service information")
        self.service_info.info(
            {
                "service": self.service_name,
                "version": self.service_version,
                "environment": self.environment,
            }
        )

    def instrument_fastapi(self, app):
        """
        Instrument FastAPI application.

        Args:
            app: FastAPI application instance
        """

        # Custom request attributes extractor
        def request_hook(span, scope):
            if span and span.is_recording():
                # Add custom attributes
                span.set_attribute("http.scheme", scope.get("scheme", "http"))
                span.set_attribute("http.host", scope.get("server", ["", ""])[0])
                span.set_attribute("http.flavor", scope.get("http_version", "1.1"))

                # Extract tenant from headers
                headers = dict(scope.get("headers", []))
                tenant_id = headers.get(b"x-tenant-id", b"").decode()
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                    baggage.set_baggage("tenant_id", tenant_id)

                # Extract user context
                user_id = headers.get(b"x-user-id", b"").decode()
                if user_id:
                    span.set_attribute("user.id", user_id)

        # Custom response attributes extractor
        def response_hook(span, message):
            if span and span.is_recording():
                status_code = message.get("status", 0)
                span.set_attribute("http.status_code", status_code)

                # Set span status based on HTTP status
                if status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            server_request_hook=request_hook,
            client_response_hook=response_hook,
            excluded_urls="/health,/metrics,/docs,/openapi.json",
        )

        logger.info(f"FastAPI instrumented for {self.service_name}")

    def instrument_sqlalchemy(self, engine):
        """
        Instrument SQLAlchemy engine.

        Args:
            engine: SQLAlchemy engine instance
        """
        SQLAlchemyInstrumentor().instrument(
            engine=engine, service=f"{self.service_name}-db"
        )

        logger.info(f"SQLAlchemy instrumented for {self.service_name}")

    def instrument_redis(self, redis_client):
        """
        Instrument Redis client.

        Args:
            redis_client: Redis client instance
        """
        RedisInstrumentor().instrument(tracer_provider=self.tracer_provider)

        logger.info(f"Redis instrumented for {self.service_name}")

    def instrument_httpx(self):
        """Instrument HTTPX client for outgoing HTTP requests."""
        HTTPXClientInstrumentor().instrument()

        logger.info(f"HTTPX instrumented for {self.service_name}")

    def instrument_psycopg2(self):
        """Instrument psycopg2 for PostgreSQL."""
        Psycopg2Instrumentor().instrument()

        logger.info(f"Psycopg2 instrumented for {self.service_name}")

    def instrument_asyncio(self):
        """Instrument asyncio for async operations."""
        AsyncioInstrumentor().instrument()

        logger.info(f"Asyncio instrumented for {self.service_name}")

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a custom span context manager.

        Args:
            name: Span name
            kind: Span kind
            attributes: Span attributes

        Yields:
            Span instance
        """
        with self.tracer.start_as_current_span(
            name, kind=kind, attributes=attributes or {}
        ) as span:
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def trace(self, name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL):
        """
        Decorator for tracing functions.

        Args:
            name: Span name (defaults to function name)
            kind: Span kind
        """

        def decorator(func):
            span_name = name or f"{self.service_name}.{func.__name__}"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.span(span_name, kind) as span:
                    # Add function arguments as attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    result = await func(*args, **kwargs)
                    return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.span(span_name, kind) as span:
                    # Add function arguments as attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    result = func(*args, **kwargs)
                    return result

            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def record_business_event(
        self,
        event_type: str,
        tenant_id: str,
        status: str = "success",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a business event metric.

        Args:
            event_type: Type of business event
            tenant_id: Tenant identifier
            status: Event status
            attributes: Additional attributes
        """
        self.business_events.labels(
            service=self.service_name,
            event_type=event_type,
            tenant_id=tenant_id,
            status=status,
        ).inc()

        # Also create a span for the event
        with self.span(
            f"business.event.{event_type}",
            attributes={
                "event.type": event_type,
                "tenant.id": tenant_id,
                "event.status": status,
                **(attributes or {}),
            },
        ) as span:
            span.add_event(name=event_type, attributes=attributes or {})

    def set_connection_gauge(self, connection_type: str, value: int):
        """
        Set active connections gauge.

        Args:
            connection_type: Type of connection
            value: Number of active connections
        """
        self.active_connections.labels(
            service=self.service_name, connection_type=connection_type
        ).set(value)

    def get_current_span(self) -> Optional[trace.Span]:
        """Get the current active span."""
        return trace.get_current_span()

    def set_span_attribute(self, key: str, value: Any):
        """Set attribute on current span."""
        span = self.get_current_span()
        if span and span.is_recording():
            span.set_attribute(key, value)

    def add_span_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to current span."""
        span = self.get_current_span()
        if span and span.is_recording():
            span.add_event(name, attributes=attributes or {})

    def shutdown(self):
        """Shutdown telemetry providers."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()

        if self.meter_provider:
            self.meter_provider.shutdown()

        logger.info(f"Telemetry shutdown for {self.service_name}")


# Global telemetry instance
_telemetry: Optional[DotMacTelemetry] = None


def init_telemetry(
    service_name: str, service_version: str = "1.0.0", **kwargs
) -> DotMacTelemetry:
    """
    Initialize global telemetry instance.

    Args:
        service_name: Service name
        service_version: Service version
        **kwargs: Additional configuration

    Returns:
        Telemetry instance
    """
    global _telemetry
    _telemetry = DotMacTelemetry(
        service_name=service_name, service_version=service_version, **kwargs
    )
    return _telemetry


def get_telemetry() -> Optional[DotMacTelemetry]:
    """Get global telemetry instance."""
    return _telemetry


# Convenience decorators
def trace_method(name: Optional[str] = None):
    """Decorator for tracing methods."""

    def decorator(func):
        if _telemetry:
            return _telemetry.trace(name)(func)
        return func

    return decorator


def record_event(event_type: str, tenant_id: str, **kwargs):
    """Record business event."""
    if _telemetry:
        _telemetry.record_business_event(event_type, tenant_id, **kwargs)
