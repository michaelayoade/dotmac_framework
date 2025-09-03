"""
OpenTelemetry Bootstrap System
Unified OTEL configuration and initialization for all DotMac services
"""

import os
import socket
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from opentelemetry import trace, metrics, baggage
from opentelemetry.sdk.trace import TracerProvider, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, SERVICE_INSTANCE_ID
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.composite import CompositeHTTPPropagator

from ..core.logging import get_logger
from ..tenant.identity import TenantContext

logger = get_logger(__name__)


class OtelExporter(str, Enum):
    """Available OTEL exporters"""
    CONSOLE = "console"
    OTLP = "otlp"
    PROMETHEUS = "prometheus"


@dataclass
class OtelConfig:
    """OpenTelemetry configuration"""
    service_name: str
    service_version: str = "1.0.0"
    environment: str = "production"
    
    # Tracing configuration
    tracing_enabled: bool = True
    tracing_exporters: List[OtelExporter] = None
    tracing_sample_rate: float = 1.0
    otlp_traces_endpoint: str = "http://localhost:4317"
    
    # Metrics configuration
    metrics_enabled: bool = True
    metrics_exporters: List[OtelExporter] = None
    metrics_interval: int = 30  # seconds
    prometheus_port: int = 8000
    otlp_metrics_endpoint: str = "http://localhost:4317"
    
    # Instrumentation configuration
    auto_instrument_fastapi: bool = True
    auto_instrument_sqlalchemy: bool = True
    auto_instrument_redis: bool = True
    auto_instrument_psycopg2: bool = True
    auto_instrument_requests: bool = True
    auto_instrument_httpx: bool = True
    
    # Resource attributes
    custom_resource_attributes: Dict[str, str] = None
    
    # Tenant-specific configuration
    tenant_scoped_metrics: bool = True
    tenant_trace_enrichment: bool = True
    
    def __post_init__(self):
        if self.tracing_exporters is None:
            self.tracing_exporters = [OtelExporter.CONSOLE]
        if self.metrics_exporters is None:
            self.metrics_exporters = [OtelExporter.CONSOLE]
        if self.custom_resource_attributes is None:
            self.custom_resource_attributes = {}


class OtelBootstrap:
    """
    OpenTelemetry bootstrap system for unified observability.
    
    Features:
    - Automatic service discovery and resource detection
    - Multi-exporter support (OTLP, Jaeger, Prometheus)
    - Tenant-aware tracing and metrics
    - Auto-instrumentation for common libraries
    - Unified configuration management
    - Performance optimization
    """
    
    def __init__(self, config: OtelConfig):
        self.config = config
        self.tracer_provider = None
        self.meter_provider = None
        self.tracer = None
        self.meter = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize OpenTelemetry with unified configuration"""
        try:
            if self._initialized:
                logger.warning("OTEL already initialized")
                return True
            
            # Create resource with service information
            resource = self._create_resource()
            
            # Initialize tracing
            if self.config.tracing_enabled:
                self._initialize_tracing(resource)
            
            # Initialize metrics
            if self.config.metrics_enabled:
                self._initialize_metrics(resource)
            
            # Set up propagators
            self._configure_propagators()
            
            # Auto-instrument libraries
            self._auto_instrument()
            
            self._initialized = True
            logger.info("✅ OpenTelemetry initialized successfully", extra={
                "service_name": self.config.service_name,
                "tracing_enabled": self.config.tracing_enabled,
                "metrics_enabled": self.config.metrics_enabled,
                "tracing_exporters": [e.value for e in self.config.tracing_exporters],
                "metrics_exporters": [e.value for e in self.config.metrics_exporters]
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            return False
    
    def _create_resource(self) -> Resource:
        """Create OTEL resource with service and environment information"""
        
        # Base resource attributes
        resource_attributes = {
            SERVICE_NAME: self.config.service_name,
            SERVICE_VERSION: self.config.service_version,
            SERVICE_INSTANCE_ID: self._get_instance_id(),
            "service.environment": self.config.environment,
            "service.namespace": "dotmac",
            "host.name": socket.gethostname(),
            "host.arch": os.uname().machine if hasattr(os, 'uname') else "unknown",
            "deployment.environment": self.config.environment,
        }
        
        # Add Kubernetes information if available
        k8s_info = self._detect_kubernetes_info()
        if k8s_info:
            resource_attributes.update(k8s_info)
        
        # Add custom attributes
        resource_attributes.update(self.config.custom_resource_attributes)
        
        return Resource.create(resource_attributes)
    
    def _initialize_tracing(self, resource: Resource):
        """Initialize OpenTelemetry tracing"""
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(
            resource=resource,
            sampler=trace.sampling.TraceIdRatioBased(self.config.tracing_sample_rate)
        )
        
        # Add span processors for each configured exporter
        for exporter_type in self.config.tracing_exporters:
            span_processor = self._create_span_processor(exporter_type)
            if span_processor:
                self.tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Create tracer
        self.tracer = trace.get_tracer(
            __name__,
            version=self.config.service_version
        )
        
        logger.info("Tracing initialized", extra={
            "exporters": [e.value for e in self.config.tracing_exporters],
            "sample_rate": self.config.tracing_sample_rate
        })
    
    def _initialize_metrics(self, resource: Resource):
        """Initialize OpenTelemetry metrics"""
        
        # Create metric readers for each configured exporter
        metric_readers = []
        for exporter_type in self.config.metrics_exporters:
            metric_reader = self._create_metric_reader(exporter_type)
            if metric_reader:
                metric_readers.append(metric_reader)
        
        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=metric_readers
        )
        
        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)
        
        # Create meter
        self.meter = metrics.get_meter(
            __name__,
            version=self.config.service_version
        )
        
        logger.info("Metrics initialized", extra={
            "exporters": [e.value for e in self.config.metrics_exporters],
            "interval": self.config.metrics_interval
        })
    
    def _create_span_processor(self, exporter_type: OtelExporter) -> Optional[BatchSpanProcessor]:
        """Create span processor for the specified exporter type"""
        
        try:
            if exporter_type == OtelExporter.CONSOLE:
                exporter = ConsoleSpanExporter()
            elif exporter_type == OtelExporter.OTLP:
                exporter = OTLPSpanExporter(endpoint=self.config.otlp_traces_endpoint)
            else:
                logger.warning(f"Unsupported trace exporter: {exporter_type}")
                return None
            
            return BatchSpanProcessor(exporter)
            
        except Exception as e:
            logger.error(f"Failed to create span processor for {exporter_type}: {e}")
            return None
    
    def _create_metric_reader(self, exporter_type: OtelExporter) -> Optional[object]:
        """Create metric reader for the specified exporter type"""
        
        try:
            if exporter_type == OtelExporter.CONSOLE:
                exporter = ConsoleMetricExporter()
                return PeriodicExportingMetricReader(
                    exporter=exporter,
                    export_interval_millis=self.config.metrics_interval * 1000
                )
            elif exporter_type == OtelExporter.OTLP:
                exporter = OTLPMetricExporter(endpoint=self.config.otlp_metrics_endpoint)
                return PeriodicExportingMetricReader(
                    exporter=exporter,
                    export_interval_millis=self.config.metrics_interval * 1000
                )
            elif exporter_type == OtelExporter.PROMETHEUS:
                return PrometheusMetricReader(port=self.config.prometheus_port)
            else:
                logger.warning(f"Unsupported metric exporter: {exporter_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create metric reader for {exporter_type}: {e}")
            return None
    
    def _configure_propagators(self):
        """Configure trace context propagators"""
        
        # Use composite propagator for maximum compatibility
        propagators = [
            B3MultiFormat(),
        ]
        
        set_global_textmap(CompositeHTTPPropagator(propagators))
        logger.debug("Propagators configured")
    
    def _auto_instrument(self):
        """Auto-instrument common libraries"""
        
        try:
            if self.config.auto_instrument_fastapi:
                FastAPIInstrumentor().instrument()
                logger.debug("FastAPI instrumentation enabled")
            
            if self.config.auto_instrument_sqlalchemy:
                SQLAlchemyInstrumentor().instrument()
                logger.debug("SQLAlchemy instrumentation enabled")
            
            if self.config.auto_instrument_redis:
                RedisInstrumentor().instrument()
                logger.debug("Redis instrumentation enabled")
            
            if self.config.auto_instrument_psycopg2:
                Psycopg2Instrumentor().instrument()
                logger.debug("Psycopg2 instrumentation enabled")
            
            if self.config.auto_instrument_requests:
                RequestsInstrumentor().instrument()
                logger.debug("Requests instrumentation enabled")
            
            if self.config.auto_instrument_httpx:
                HTTPXClientInstrumentor().instrument()
                logger.debug("HTTPX instrumentation enabled")
                
        except Exception as e:
            logger.warning(f"Auto-instrumentation partially failed: {e}")
    
    def _get_instance_id(self) -> str:
        """Get unique instance identifier"""
        
        # Try to get from environment (Kubernetes, Docker, etc.)
        instance_id = (
            os.getenv("HOSTNAME") or
            os.getenv("POD_NAME") or
            os.getenv("CONTAINER_ID") or
            f"{self.config.service_name}-{socket.gethostname()}"
        )
        
        return instance_id
    
    def _detect_kubernetes_info(self) -> Dict[str, str]:
        """Detect Kubernetes-specific information"""
        
        k8s_attrs = {}
        
        # Common Kubernetes environment variables
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            k8s_attrs["k8s.cluster.name"] = os.getenv("CLUSTER_NAME", "unknown")
            k8s_attrs["k8s.namespace.name"] = os.getenv("POD_NAMESPACE", "default")
            k8s_attrs["k8s.pod.name"] = os.getenv("POD_NAME", "unknown")
            k8s_attrs["k8s.deployment.name"] = os.getenv("DEPLOYMENT_NAME", "unknown")
            k8s_attrs["k8s.node.name"] = os.getenv("NODE_NAME", "unknown")
        
        return k8s_attrs
    
    def create_tenant_span(
        self, 
        operation_name: str, 
        tenant_context: Optional[TenantContext] = None,
        attributes: Dict[str, Any] = None
    ):
        """Create a span with tenant context enrichment"""
        
        if not self.tracer:
            return None
        
        span_attributes = attributes or {}
        
        # Add tenant attributes
        if tenant_context and self.config.tenant_trace_enrichment:
            span_attributes.update({
                "tenant.id": tenant_context.tenant_id,
                "tenant.subdomain": tenant_context.subdomain or "",
                "tenant.host": tenant_context.host or "",
                "tenant.is_management": tenant_context.is_management,
                "tenant.is_verified": tenant_context.is_verified
            })
        
        return self.tracer.start_span(operation_name, attributes=span_attributes)
    
    def get_tracer(self):
        """Get the configured tracer"""
        return self.tracer
    
    def get_meter(self):
        """Get the configured meter"""
        return self.meter
    
    def shutdown(self):
        """Shutdown OTEL providers gracefully"""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            
            self._initialized = False
            logger.info("OpenTelemetry shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during OTEL shutdown: {e}")


# Global OTEL bootstrap instance
otel_bootstrap = None


def initialize_otel(config: OtelConfig) -> OtelBootstrap:
    """Initialize OpenTelemetry with the provided configuration"""
    global otel_bootstrap
    otel_bootstrap = OtelBootstrap(config)
    otel_bootstrap.initialize()
    return otel_bootstrap


def get_otel_bootstrap() -> Optional[OtelBootstrap]:
    """Get the initialized OTEL bootstrap instance"""
    return otel_bootstrap


def create_default_config(
    service_name: str,
    environment: str = "production",
    **kwargs
) -> OtelConfig:
    """Create default OTEL configuration for a service"""
    
    # Environment-specific defaults
    if environment == "development":
        defaults = {
            "tracing_exporters": [OtelExporter.CONSOLE],
            "metrics_exporters": [OtelExporter.CONSOLE],
            "tracing_sample_rate": 1.0,
        }
    elif environment == "staging":
        defaults = {
            "tracing_exporters": [OtelExporter.OTLP],
            "metrics_exporters": [OtelExporter.OTLP, OtelExporter.PROMETHEUS],
            "tracing_sample_rate": 0.1,
        }
    else:  # production
        defaults = {
            "tracing_exporters": [OtelExporter.OTLP],
            "metrics_exporters": [OtelExporter.OTLP, OtelExporter.PROMETHEUS],
            "tracing_sample_rate": 0.01,
        }
    
    # Merge with user-provided kwargs
    defaults.update(kwargs)
    
    return OtelConfig(
        service_name=service_name,
        environment=environment,
        **defaults
    )