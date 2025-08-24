"""
Strategic Observability Integration for Management Platform.

Integrates with SignOz for comprehensive monitoring of the SaaS platform including:
- API performance monitoring
- Business metrics tracking
- Tenant isolation monitoring
- Revenue and subscription tracking
- Error tracking and alerting
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
from datetime import datetime, timezone
import asyncio
import time

# OpenTelemetry core imports
from opentelemetry import trace, metrics, baggage
from opentelemetry.exporter.otlp.proto.grpc import (
    trace_exporter as otlp_trace,
    metric_exporter as otlp_metric,
    _log_exporter as otlp_log,
)
from opentelemetry.sdk import trace as trace_sdk, metrics as metrics_sdk
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, SERVICE_INSTANCE_ID
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation
from opentelemetry.trace import Status, StatusCode, SpanKind

# Instrumentation imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

# Propagation
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.composite import CompositePropagator

from ..config import get_settings

logger = logging.getLogger(__name__)


class ManagementPlatformObservability:
    """
    Strategic observability for the Management Platform SaaS.
    
    Focuses on business metrics, tenant performance, and revenue tracking.
    """

    def __init__(self):
        self.settings = get_settings()
        self.service_name = "dotmac-management-platform"
        self.service_version = "1.0.0"
        self.environment = self.settings.environment
        
        # SignOz configuration
        self.signoz_endpoint = self.settings.signoz_endpoint
        self.signoz_access_token = getattr(self.settings, 'signoz_access_token', None)
        
        # Generate instance ID
        import socket
        import uuid
        self.instance_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        
        # Setup resource attributes
        self.resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            SERVICE_INSTANCE_ID: self.instance_id,
            "deployment.environment": self.environment,
            "service.namespace": "dotmac",
            "service.type": "management_platform",
            "cloud.provider": os.getenv("CLOUD_PROVIDER", "local"),
            "cloud.region": os.getenv("CLOUD_REGION", "us-east-1"),
            "host.name": socket.gethostname(),
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        })
        
        # Headers for SignOz
        self.headers = {}
        if self.signoz_access_token:
            self.headers = {"signoz-access-token": self.signoz_access_token}
            
        # Initialize providers
        self.tracer_provider = None
        self.meter_provider = None
        self.logger_provider = None
        self.tracer = None
        self.meter = None
        
        # Business metrics storage
        self._business_metrics = {}
        self._saas_metrics = {}
        
        # Setup telemetry
        self._setup_tracing()
        self._setup_metrics()
        self._setup_logging()
        self._setup_propagation()
        self._init_business_metrics()
        
        logger.info(f"Management Platform observability initialized - SignOz endpoint: {self.signoz_endpoint}")

    def _setup_tracing(self):
        """Configure distributed tracing for Management Platform."""
        try:
            # Create OTLP trace exporter
            trace_exporter = otlp_trace.OTLPSpanExporter(
                endpoint=self.signoz_endpoint,
                headers=self.headers,
                insecure=True,  # Use insecure for development
                timeout=30,
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=self.resource)
            
            # Add span processor
            span_processor = BatchSpanProcessor(
                trace_exporter,
                max_queue_size=10000,
                max_export_batch_size=1000,
                schedule_delay_millis=1000,
                export_timeout_millis=30000,
            )
            self.tracer_provider.add_span_processor(span_processor)
            
            # Set global tracer
            trace.set_tracer_provider(self.tracer_provider)
            self.tracer = trace.get_tracer(
                instrumenting_module_name=self.service_name,
                instrumenting_library_version=self.service_version,
            )
            
            logger.info("Management Platform tracing configured")
            
        except Exception as e:
            logger.error(f"Failed to setup tracing: {e}")
            # Create a no-op tracer to prevent crashes
            self.tracer = trace.NoOpTracer()

    def _setup_metrics(self):
        """Configure metrics collection for Management Platform."""
        try:
            # Create OTLP metric exporter
            metric_exporter = otlp_metric.OTLPMetricExporter(
                endpoint=self.signoz_endpoint,
                headers=self.headers,
                insecure=True,
                timeout=30,
                preferred_temporality={
                    metrics_sdk.InstrumentType.COUNTER: metrics_sdk.AggregationTemporality.DELTA,
                    metrics_sdk.InstrumentType.HISTOGRAM: metrics_sdk.AggregationTemporality.DELTA,
                    metrics_sdk.InstrumentType.UP_DOWN_COUNTER: metrics_sdk.AggregationTemporality.CUMULATIVE,
                },
            )

            # Create metric reader
            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=30000,  # 30 seconds
                export_timeout_millis=10000,
            )

            # Define custom views for SaaS metrics
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
                    instrument_name="tenant.api.duration",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]
                    ),
                ),
            ]

            # Create meter provider
            self.meter_provider = MeterProvider(
                resource=self.resource,
                metric_readers=[metric_reader],
                views=views
            )
            
            # Set global meter
            metrics.set_meter_provider(self.meter_provider)
            self.meter = metrics.get_meter(
                name=self.service_name,
                version=self.service_version
            )
            
            logger.info("Management Platform metrics configured")
            
        except Exception as e:
            logger.error(f"Failed to setup metrics: {e}")
            # Create a no-op meter
            self.meter = metrics.NoOpMeter("")

    def _setup_logging(self):
        """Configure log collection for Management Platform."""
        try:
            # Create OTLP log exporter
            log_exporter = otlp_log.OTLPLogExporter(
                endpoint=self.signoz_endpoint,
                headers=self.headers,
                insecure=True
            )

            # Create logger provider
            self.logger_provider = LoggerProvider(resource=self.resource)
            
            # Add log processor
            log_processor = BatchLogRecordProcessor(
                log_exporter,
                max_queue_size=10000,
                schedule_delay_millis=1000,
                max_export_batch_size=512,
            )
            self.logger_provider.add_log_record_processor(log_processor)

            # Create OTLP handler
            handler = LoggingHandler(
                level=logging.INFO,
                logger_provider=self.logger_provider
            )
            
            # Add to root logger
            logging.getLogger().addHandler(handler)
            
            logger.info("Management Platform logging configured")
            
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")

    def _setup_propagation(self):
        """Setup context propagation."""
        set_global_textmap(
            CompositePropagator([
                TraceContextTextMapPropagator(),
                W3CBaggagePropagator()
            ])
        )

    def _init_business_metrics(self):
        """Initialize business and SaaS-specific metrics."""
        try:
            # API Performance metrics
            self._business_metrics["api_requests"] = self.meter.create_counter(
                name="api.requests.total",
                description="Total API requests",
                unit="1",
            )
            
            self._business_metrics["api_duration"] = self.meter.create_histogram(
                name="api.request.duration",
                description="API request duration",
                unit="ms",
            )
            
            # Tenant metrics
            self._business_metrics["tenant_operations"] = self.meter.create_counter(
                name="tenant.operations.total",
                description="Tenant operations count",
                unit="1",
            )
            
            self._business_metrics["tenant_api_calls"] = self.meter.create_counter(
                name="tenant.api.calls",
                description="API calls per tenant",
                unit="1",
            )
            
            self._business_metrics["active_tenants"] = self.meter.create_observable_gauge(
                name="tenant.active.count",
                callbacks=[self._get_active_tenants_count],
                description="Number of active tenants",
                unit="1",
            )
            
            # Revenue metrics
            self._business_metrics["subscription_revenue"] = self.meter.create_counter(
                name="revenue.subscription.total",
                description="Total subscription revenue",
                unit="USD",
            )
            
            self._business_metrics["mrr"] = self.meter.create_observable_gauge(
                name="revenue.mrr",
                callbacks=[self._get_mrr],
                description="Monthly Recurring Revenue",
                unit="USD",
            )
            
            # Billing metrics
            self._business_metrics["billing_events"] = self.meter.create_counter(
                name="billing.events.total",
                description="Billing events processed",
                unit="1",
            )
            
            self._business_metrics["payment_failures"] = self.meter.create_counter(
                name="payment.failures.total",
                description="Payment failures",
                unit="1",
            )
            
            # Plugin metrics
            self._business_metrics["plugin_installations"] = self.meter.create_counter(
                name="plugin.installations.total",
                description="Plugin installations",
                unit="1",
            )
            
            self._business_metrics["plugin_revenue"] = self.meter.create_counter(
                name="plugin.revenue.total",
                description="Plugin revenue",
                unit="USD",
            )
            
            # Deployment metrics
            self._business_metrics["deployments"] = self.meter.create_counter(
                name="deployment.operations.total",
                description="Deployment operations",
                unit="1",
            )
            
            self._business_metrics["deployment_duration"] = self.meter.create_histogram(
                name="deployment.duration",
                description="Deployment duration",
                unit="ms",
            )
            
            # System health metrics
            self._business_metrics["database_connections"] = self.meter.create_observable_gauge(
                name="database.connections.active",
                callbacks=[self._get_db_connections],
                description="Active database connections",
                unit="1",
            )
            
            logger.info("Business metrics initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize business metrics: {e}")

    def _get_active_tenants_count(self, options):
        """Get count of active tenants."""
        try:
            # This would query the database for active tenants
            # For now, return a placeholder
            return [(0, {"status": "active"})]
        except Exception:
            return [(0, {"status": "unknown"})]

    def _get_mrr(self, options):
        """Get Monthly Recurring Revenue."""
        try:
            # This would calculate MRR from subscription data
            return [(0, {"currency": "USD"})]
        except Exception:
            return [(0, {"currency": "USD"})]

    def _get_db_connections(self, options):
        """Get database connection count."""
        try:
            # This would check actual connection pool
            return [(5, {"pool": "main"})]
        except Exception:
            return [(0, {"pool": "main"})]

    def instrument_fastapi(self, app):
        """Instrument FastAPI application with comprehensive monitoring."""
        try:
            # Custom request hook for tenant context
            def request_hook(span, scope):
                if span and span.is_recording():
                    headers = dict(scope.get("headers", []))
                    
                    # Extract tenant context
                    tenant_id = headers.get(b"x-tenant-id", b"system").decode()
                    span.set_attribute("tenant.id", tenant_id)
                    baggage.set_baggage("tenant_id", tenant_id)
                    
                    # Extract user context
                    user_id = headers.get(b"x-user-id", b"anonymous").decode()
                    span.set_attribute("enduser.id", user_id)
                    
                    # API versioning
                    path = scope.get("path", "/")
                    if path.startswith("/api/v1"):
                        span.set_attribute("api.version", "v1")
                    
                    # Business context
                    span.set_attribute("service.type", "management_platform")
                    span.set_attribute("platform.type", "saas")

            # Custom response hook for metrics
            def response_hook(span, message):
                if span and span.is_recording():
                    status_code = message.get("status", 0)
                    
                    # Set span status
                    if status_code >= 400:
                        span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))
                    
                    # Record business metrics
                    self.record_api_request(
                        method=span.attributes.get("http.method", "GET"),
                        endpoint=span.attributes.get("http.target", "/"),
                        status_code=status_code,
                        tenant_id=span.attributes.get("tenant.id", "system"),
                        duration_ms=time.time() * 1000
                    )

            # Instrument FastAPI
            FastAPIInstrumentor.instrument_app(
                app,
                server_request_hook=request_hook,
                client_response_hook=response_hook,
                excluded_urls="/health,/metrics,/docs,/openapi.json",
            )
            
            # Instrument database
            SQLAlchemyInstrumentor().instrument()
            
            # Instrument Redis
            RedisInstrumentor().instrument()
            
            # Instrument HTTP clients
            HTTPXClientInstrumentor().instrument()
            RequestsInstrumentor().instrument()
            
            # Instrument Celery
            CeleryInstrumentor().instrument()
            
            # Instrument system metrics
            SystemMetricsInstrumentor().instrument()
            
            logger.info(f"FastAPI and dependencies instrumented for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")

    def record_api_request(self, method: str, endpoint: str, status_code: int, 
                          tenant_id: str, duration_ms: float):
        """Record API request metrics."""
        try:
            attributes = {
                "http.method": method,
                "http.endpoint": endpoint,
                "http.status_code": str(status_code),
                "http.status_class": f"{status_code // 100}xx",
                "tenant.id": tenant_id,
                "service.name": self.service_name,
            }
            
            # Record metrics
            self._business_metrics["api_requests"].add(1, attributes)
            self._business_metrics["api_duration"].record(duration_ms, attributes)
            
            # Record tenant-specific API usage
            tenant_attributes = {**attributes, "operation": "api_call"}
            self._business_metrics["tenant_api_calls"].add(1, tenant_attributes)
            
        except Exception as e:
            logger.error(f"Failed to record API metrics: {e}")

    def record_tenant_operation(self, operation: str, tenant_id: str, 
                               success: bool = True, **kwargs):
        """Record tenant operations for SaaS monitoring."""
        try:
            attributes = {
                "operation": operation,
                "tenant.id": tenant_id,
                "success": success,
                "service.name": self.service_name,
                **kwargs
            }
            
            # Record operation
            self._business_metrics["tenant_operations"].add(1, attributes)
            
            # Create span for important operations
            with self.tracer.start_as_current_span(
                f"tenant.{operation}",
                kind=SpanKind.INTERNAL,
                attributes=attributes
            ) as span:
                span.add_event(f"tenant_{operation}", attributes=attributes)
                if not success:
                    span.set_status(Status(StatusCode.ERROR, f"Tenant {operation} failed"))
                    
        except Exception as e:
            logger.error(f"Failed to record tenant operation: {e}")

    def record_revenue(self, amount: float, currency: str = "USD", 
                      revenue_type: str = "subscription", tenant_id: str = None):
        """Record revenue metrics for business intelligence."""
        try:
            attributes = {
                "currency": currency,
                "revenue.type": revenue_type,
                "service.name": self.service_name,
            }
            
            if tenant_id:
                attributes["tenant.id"] = tenant_id
            
            if revenue_type == "subscription":
                self._business_metrics["subscription_revenue"].add(amount, attributes)
            elif revenue_type == "plugin":
                self._business_metrics["plugin_revenue"].add(amount, attributes)
                
            # Create high-value span for revenue events
            with self.tracer.start_as_current_span(
                f"revenue.{revenue_type}",
                kind=SpanKind.INTERNAL,
                attributes={**attributes, "amount": amount}
            ) as span:
                span.add_event("revenue_recorded", attributes={"amount": amount, "currency": currency})
                
        except Exception as e:
            logger.error(f"Failed to record revenue: {e}")

    def record_billing_event(self, event_type: str, tenant_id: str, 
                           success: bool = True, amount: float = None):
        """Record billing events."""
        try:
            attributes = {
                "billing.event": event_type,
                "tenant.id": tenant_id,
                "success": success,
                "service.name": self.service_name,
            }
            
            if amount:
                attributes["amount"] = amount
            
            self._business_metrics["billing_events"].add(1, attributes)
            
            if not success:
                self._business_metrics["payment_failures"].add(1, attributes)
                
        except Exception as e:
            logger.error(f"Failed to record billing event: {e}")

    def record_deployment(self, operation: str, tenant_id: str, success: bool = True, 
                         duration_ms: float = None):
        """Record deployment operations."""
        try:
            attributes = {
                "deployment.operation": operation,
                "tenant.id": tenant_id,
                "success": success,
                "service.name": self.service_name,
            }
            
            self._business_metrics["deployments"].add(1, attributes)
            
            if duration_ms:
                self._business_metrics["deployment_duration"].record(duration_ms, attributes)
                
        except Exception as e:
            logger.error(f"Failed to record deployment: {e}")

    @contextmanager
    def trace_business_operation(self, operation: str, tenant_id: str = None, **attributes):
        """Context manager for tracing business operations."""
        operation_attributes = {
            "operation.type": "business",
            "service.name": self.service_name,
            **attributes
        }
        
        if tenant_id:
            operation_attributes["tenant.id"] = tenant_id
            
        with self.tracer.start_as_current_span(
            f"business.{operation}",
            kind=SpanKind.INTERNAL,
            attributes=operation_attributes
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

    def create_dashboards_config(self) -> Dict[str, Any]:
        """Create SignOz dashboard configurations for Management Platform."""
        return {
            "management_platform_overview": {
                "title": "Management Platform Overview",
                "description": "SaaS platform performance and business metrics",
                "widgets": [
                    {
                        "title": "API Request Rate",
                        "query": "api.requests.total",
                        "type": "timeseries",
                        "group_by": ["http.status_class"]
                    },
                    {
                        "title": "Active Tenants",
                        "query": "tenant.active.count",
                        "type": "number"
                    },
                    {
                        "title": "Monthly Recurring Revenue",
                        "query": "revenue.mrr",
                        "type": "number"
                    },
                    {
                        "title": "Tenant Operations",
                        "query": "tenant.operations.total",
                        "type": "timeseries",
                        "group_by": ["operation"]
                    }
                ]
            },
            "tenant_performance": {
                "title": "Tenant Performance Dashboard",
                "description": "Per-tenant performance and usage metrics",
                "widgets": [
                    {
                        "title": "API Calls by Tenant",
                        "query": "tenant.api.calls",
                        "type": "timeseries",
                        "group_by": ["tenant.id"]
                    },
                    {
                        "title": "Deployment Success Rate",
                        "query": "deployment.operations.total",
                        "type": "timeseries",
                        "group_by": ["success"]
                    }
                ]
            }
        }

    def shutdown(self):
        """Shutdown observability providers."""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            if self.logger_provider:
                self.logger_provider.shutdown()
                
            logger.info("Management Platform observability shutdown")
        except Exception as e:
            logger.error(f"Error during observability shutdown: {e}")


# Global instance
_observability: Optional[ManagementPlatformObservability] = None


def get_observability() -> ManagementPlatformObservability:
    """Get global observability instance."""
    global _observability
    if _observability is None:
        _observability = ManagementPlatformObservability()
    return _observability


def init_observability() -> ManagementPlatformObservability:
    """Initialize observability."""
    return get_observability()


# Convenience decorators
def trace_business_operation(name: str = None, tenant_context: bool = True):
    """Decorator for tracing business operations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            obs = get_observability()
            
            # Extract tenant_id if available
            tenant_id = None
            if tenant_context and kwargs.get('tenant_id'):
                tenant_id = kwargs['tenant_id']
                
            operation_name = name or func.__name__
            with obs.trace_business_operation(operation_name, tenant_id=tenant_id):
                return await func(*args, **kwargs)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            obs = get_observability()
            
            tenant_id = None
            if tenant_context and kwargs.get('tenant_id'):
                tenant_id = kwargs['tenant_id']
                
            operation_name = name or func.__name__
            with obs.trace_business_operation(operation_name, tenant_id=tenant_id):
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator