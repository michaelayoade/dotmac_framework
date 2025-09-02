"""
OpenTelemetry configuration and setup for SigNoz integration.
Production-ready observability with trace/log correlation and tenant context.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

logger = logging.getLogger(__name__)


class OTelConfig:
    """Configuration for OpenTelemetry."""
    
    def __init__(self):
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "dotmac-framework")
        self.service_version = os.getenv("SERVICE_VERSION", "0.0.0")
        self.environment = os.getenv("ENVIRONMENT", "dev")
        
        # SigNoz endpoints
        self.traces_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", 
            "http://otel-collector:4317"
        )
        self.metrics_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
            "http://otel-collector:4317"
        )
        
        # Sampling configuration
        self.sampling_ratio = float(os.getenv("OTEL_TRACES_SAMPLING_RATIO", "0.10"))
        
        # Security
        self.insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
        self.headers = self._parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
        
        # Feature flags
        self.enable_sql_commenter = os.getenv("OTEL_ENABLE_SQL_COMMENTER", "true").lower() == "true"
        self.enable_db_statement = os.getenv("OTEL_ENABLE_DB_STATEMENT", "true").lower() == "true"
    
    def _parse_headers(self, headers_str: str) -> dict:
        """Parse OTLP headers from environment."""
        if not headers_str:
            return {}
        
        headers = {}
        for header in headers_str.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
        return headers
    
    @property 
    def resource_attributes(self) -> dict:
        """Standard resource attributes for SigNoz grouping."""
        return {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "deployment.environment": self.environment,
            "service.namespace": "dotmac",
            "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        }


def setup_otel(app, engine=None, config: Optional[OTelConfig] = None) -> tuple:
    """
    Setup OpenTelemetry for FastAPI application with SigNoz integration.
    
    Args:
        app: FastAPI application instance
        engine: SQLAlchemy async engine (optional)
        config: OTel configuration (optional, will create default)
    
    Returns:
        Tuple of (TracerProvider, MeterProvider)
    """
    if config is None:
        config = OTelConfig()
    
    logger.info(f"Setting up OpenTelemetry for service: {config.service_name}")
    
    # Create resource
    resource = Resource.create(config.resource_attributes)
    
    # Setup tracing
    tracer_provider = _setup_tracing(config, resource)
    
    # Setup metrics
    meter_provider = _setup_metrics(config, resource)
    
    # Instrument application
    _instrument_app(app, config)
    
    # Instrument SQLAlchemy if engine provided
    if engine is not None:
        _instrument_sqlalchemy(engine, config)
    
    # Instrument HTTP clients
    _instrument_http_clients()
    
    # Setup logging instrumentation
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    logger.info("OpenTelemetry setup complete")
    return tracer_provider, meter_provider


def _setup_tracing(config: OTelConfig, resource: Resource) -> TracerProvider:
    """Setup trace provider and exporter."""
    # Configure sampling
    if config.environment == "production":
        # Parent-based sampling with ratio for production
        sampler = sampling.ParentBased(
            sampling.TraceIdRatioBased(config.sampling_ratio)
        )
    else:
        # Higher sampling for dev/staging
        sampler = sampling.ParentBased(
            sampling.TraceIdRatioBased(min(config.sampling_ratio * 2, 1.0))
        )
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    
    # Setup OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=config.traces_endpoint,
        insecure=config.insecure,
        headers=config.headers
    )
    
    # Add batch processor for performance
    batch_processor = BatchSpanProcessor(
        otlp_exporter,
        max_queue_size=512,
        max_export_batch_size=512,
        export_timeout_millis=30000,
        schedule_delay_millis=5000
    )
    
    tracer_provider.add_span_processor(batch_processor)
    trace.set_tracer_provider(tracer_provider)
    
    return tracer_provider


def _setup_metrics(config: OTelConfig, resource: Resource) -> MeterProvider:
    """Setup metrics provider and exporter."""
    # Create OTLP metric exporter
    metric_exporter = OTLPMetricExporter(
        endpoint=config.metrics_endpoint,
        insecure=config.insecure,
        headers=config.headers
    )
    
    # Create metric reader with export interval
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=60000,  # 1 minute
        export_timeout_millis=30000
    )
    
    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    
    metrics.set_meter_provider(meter_provider)
    return meter_provider


def _instrument_app(app, config: OTelConfig):
    """Instrument FastAPI application."""
    # Add ASGI middleware for low-level tracing
    app.add_middleware(OpenTelemetryMiddleware)
    
    # Instrument FastAPI routes
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,metrics,ready",  # Exclude health checks
        http_capture_headers_server_request=["x-tenant-id", "x-request-id", "user-agent"],
        http_capture_headers_server_response=["x-trace-id", "content-type"]
    )


def _instrument_sqlalchemy(engine, config: OTelConfig):
    """Instrument SQLAlchemy engine."""
    # Get sync engine for instrumentation
    sync_engine = engine.sync_engine if hasattr(engine, "sync_engine") else engine
    
    # Configure SQLAlchemy instrumentation
    commenter_options = {}
    if config.enable_sql_commenter:
        commenter_options = {
            "db_driver": True,
            "db_framework": True,
            "opentelemetry_values": True
        }
    
    SQLAlchemyInstrumentor().instrument(
        engine=sync_engine,
        enable_commenter=config.enable_sql_commenter,
        commenter_options=commenter_options,
        skip_dep_check=True
    )
    
    # Configure span attributes
    if not config.enable_db_statement:
        # Disable statement capture for security in production
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor()._original_execute = lambda *args, **kwargs: None


def _instrument_http_clients():
    """Instrument HTTP client libraries."""
    RequestsInstrumentor().instrument(
        skip_dep_check=True,
        excluded_urls="health,metrics,ready"
    )
    
    try:
        HTTPXClientInstrumentor().instrument(skip_dep_check=True)
    except Exception as e:
        logger.warning(f"Could not instrument httpx: {e}")


def get_tracer(name: str = None):
    """Get a tracer instance."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "dotmac-framework")
    return trace.get_tracer(name or service_name)


def get_meter(name: str = None):
    """Get a meter instance."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "dotmac-framework")
    return metrics.get_meter(name or service_name)


# Pre-configured meter for common metrics
dotmac_meter = get_meter("dotmac-framework")

# Common business metrics
tenant_operation_counter = dotmac_meter.create_counter(
    "dotmac.tenant.operations.total",
    description="Total tenant operations by type"
)

tenant_operation_duration = dotmac_meter.create_histogram(
    "dotmac.tenant.operation.duration_ms",
    description="Tenant operation duration in milliseconds",
    unit="ms"
)

db_operation_duration = dotmac_meter.create_histogram(
    "dotmac.db.operation.duration_ms", 
    description="Database operation duration in milliseconds",
    unit="ms"
)

commission_calculation_counter = dotmac_meter.create_counter(
    "dotmac.commission.calculations.total",
    description="Total commission calculations"
)

partner_customer_counter = dotmac_meter.create_counter(
    "dotmac.partner.customers.total",
    description="Partner customer operations by type"
)


def record_tenant_operation(operation_type: str, duration_ms: float, tenant_id: str):
    """Record tenant operation metrics."""
    labels = {"operation_type": operation_type, "tenant_id": tenant_id}
    tenant_operation_counter.add(1, labels)
    tenant_operation_duration.record(duration_ms, labels)


def record_db_operation(operation: str, duration_ms: float, table: str = None):
    """Record database operation metrics."""
    labels = {"operation": operation}
    if table:
        labels["table"] = table
    db_operation_duration.record(duration_ms, labels)