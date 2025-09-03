"""
Unified Metrics Schema
Standardized metrics collection and export schema across all DotMac applications
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time

from opentelemetry import metrics
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, Info, Enum as PrometheusEnum

from ..core.logging import get_logger
from ..tenant.identity import TenantContext

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Standard metric types"""
    COUNTER = "counter"
    HISTOGRAM = "histogram" 
    GAUGE = "gauge"
    INFO = "info"
    ENUM = "enum"


class MetricCategory(str, Enum):
    """Metric categories for organization"""
    SYSTEM = "system"           # System-level metrics (CPU, memory, disk)
    APPLICATION = "application" # Application-level metrics (requests, errors)
    BUSINESS = "business"       # Business metrics (users, transactions, revenue)
    SECURITY = "security"       # Security metrics (auth failures, access violations)
    INFRASTRUCTURE = "infrastructure"  # Infrastructure metrics (deployments, scaling)


@dataclass
class MetricDefinition:
    """Definition of a standardized metric"""
    name: str
    type: MetricType
    category: MetricCategory
    description: str
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    tenant_scoped: bool = True
    help_text: str = ""
    
    def __post_init__(self):
        if not self.help_text:
            self.help_text = self.description
        
        # Ensure tenant_id is always a label for tenant-scoped metrics
        if self.tenant_scoped and "tenant_id" not in self.labels:
            self.labels.insert(0, "tenant_id")


class UnifiedMetricsRegistry:
    """
    Unified metrics registry that standardizes metric collection across applications.
    
    Features:
    - Standardized metric definitions
    - Tenant-scoped metrics
    - OpenTelemetry and Prometheus integration
    - Automatic labeling and categorization
    - Performance optimization with caching
    """
    
    def __init__(self, service_name: str, enable_prometheus: bool = True):
        self.service_name = service_name
        self.enable_prometheus = enable_prometheus
        
        # Metric definitions registry
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        
        # OpenTelemetry metrics
        self.otel_meter = None
        self.otel_instruments: Dict[str, Any] = {}
        
        # Prometheus metrics
        self.prometheus_registry = CollectorRegistry() if enable_prometheus else None
        self.prometheus_instruments: Dict[str, Any] = {}
        
        # Tenant context cache for performance
        self._tenant_cache = {}
        
        # Initialize standard metrics
        self._register_standard_metrics()
    
    def set_otel_meter(self, meter):
        """Set the OpenTelemetry meter for metric collection"""
        self.otel_meter = meter
        self._create_otel_instruments()
    
    def register_metric(self, metric_def: MetricDefinition) -> bool:
        """Register a metric definition"""
        try:
            # Validate metric name uniqueness
            if metric_def.name in self.metric_definitions:
                logger.warning(f"Metric {metric_def.name} already registered")
                return False
            
            # Add service prefix to metric name
            full_name = f"{self.service_name}_{metric_def.name}"
            metric_def.name = full_name
            
            # Store definition
            self.metric_definitions[full_name] = metric_def
            
            # Create OpenTelemetry instrument
            if self.otel_meter:
                self._create_otel_instrument(metric_def)
            
            # Create Prometheus instrument
            if self.enable_prometheus:
                self._create_prometheus_instrument(metric_def)
            
            logger.debug(f"Registered metric: {full_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register metric {metric_def.name}: {e}")
            return False
    
    def record_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        labels: Dict[str, str] = None,
        tenant_context: Optional[TenantContext] = None
    ):
        """Record a metric value with automatic tenant labeling"""
        try:
            full_metric_name = f"{self.service_name}_{metric_name}"
            metric_def = self.metric_definitions.get(full_metric_name)
            
            if not metric_def:
                logger.warning(f"Unknown metric: {metric_name}")
                return
            
            # Prepare labels
            final_labels = labels or {}
            
            # Add tenant labels if metric is tenant-scoped
            if metric_def.tenant_scoped and tenant_context:
                final_labels["tenant_id"] = tenant_context.tenant_id
                final_labels["tenant_type"] = "management" if tenant_context.is_management else "customer"
                if tenant_context.subdomain:
                    final_labels["subdomain"] = tenant_context.subdomain
                if tenant_context.metadata.get("plan"):
                    final_labels["tenant_plan"] = tenant_context.metadata["plan"]
            
            # Add standard service labels
            final_labels["service"] = self.service_name
            final_labels["category"] = metric_def.category.value
            
            # Record in OpenTelemetry
            if self.otel_meter and full_metric_name in self.otel_instruments:
                self._record_otel_metric(metric_def, value, final_labels)
            
            # Record in Prometheus
            if self.enable_prometheus and full_metric_name in self.prometheus_instruments:
                self._record_prometheus_metric(metric_def, value, final_labels)
            
        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {e}")
    
    def increment_counter(
        self,
        metric_name: str,
        value: Union[int, float] = 1,
        labels: Dict[str, str] = None,
        tenant_context: Optional[TenantContext] = None
    ):
        """Increment a counter metric"""
        self.record_metric(metric_name, value, labels, tenant_context)
    
    def observe_histogram(
        self,
        metric_name: str,
        value: Union[int, float],
        labels: Dict[str, str] = None,
        tenant_context: Optional[TenantContext] = None
    ):
        """Observe a histogram metric"""
        self.record_metric(metric_name, value, labels, tenant_context)
    
    def set_gauge(
        self,
        metric_name: str,
        value: Union[int, float],
        labels: Dict[str, str] = None,
        tenant_context: Optional[TenantContext] = None
    ):
        """Set a gauge metric"""
        self.record_metric(metric_name, value, labels, tenant_context)
    
    def time_operation(self, metric_name: str, labels: Dict[str, str] = None, tenant_context: Optional[TenantContext] = None):
        """Context manager for timing operations"""
        return MetricTimer(self, metric_name, labels, tenant_context)
    
    def _register_standard_metrics(self):
        """Register standard metrics that all services should have"""
        
        standard_metrics = [
            # Application metrics
            MetricDefinition(
                name="http_requests_total",
                type=MetricType.COUNTER,
                category=MetricCategory.APPLICATION,
                description="Total HTTP requests",
                labels=["method", "endpoint", "status_code"],
                help_text="Total number of HTTP requests received"
            ),
            MetricDefinition(
                name="http_request_duration_seconds",
                type=MetricType.HISTOGRAM,
                category=MetricCategory.APPLICATION,
                description="HTTP request duration in seconds",
                unit="seconds",
                labels=["method", "endpoint", "status_code"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                help_text="Duration of HTTP requests in seconds"
            ),
            MetricDefinition(
                name="active_requests",
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                description="Currently active requests",
                labels=["endpoint"],
                help_text="Number of currently active HTTP requests"
            ),
            
            # System metrics
            MetricDefinition(
                name="cpu_usage_percent",
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                description="CPU usage percentage",
                unit="percent",
                labels=["cpu_core"],
                tenant_scoped=False,
                help_text="CPU usage as a percentage"
            ),
            MetricDefinition(
                name="memory_usage_bytes",
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                description="Memory usage in bytes",
                unit="bytes",
                labels=["memory_type"],
                tenant_scoped=False,
                help_text="Memory usage in bytes"
            ),
            
            # Business metrics
            MetricDefinition(
                name="active_users",
                type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Currently active users",
                labels=["user_type"],
                help_text="Number of currently active users"
            ),
            MetricDefinition(
                name="transactions_total",
                type=MetricType.COUNTER,
                category=MetricCategory.BUSINESS,
                description="Total transactions processed",
                labels=["transaction_type", "status"],
                help_text="Total number of transactions processed"
            ),
            
            # Security metrics
            MetricDefinition(
                name="auth_attempts_total",
                type=MetricType.COUNTER,
                category=MetricCategory.SECURITY,
                description="Total authentication attempts",
                labels=["auth_type", "result"],
                help_text="Total authentication attempts"
            ),
            MetricDefinition(
                name="security_events_total",
                type=MetricType.COUNTER,
                category=MetricCategory.SECURITY,
                description="Total security events",
                labels=["event_type", "severity"],
                help_text="Total security events detected"
            ),
            
            # Infrastructure metrics
            MetricDefinition(
                name="deployments_total",
                type=MetricType.COUNTER,
                category=MetricCategory.INFRASTRUCTURE,
                description="Total deployments",
                labels=["deployment_type", "status"],
                tenant_scoped=False,
                help_text="Total number of deployments"
            ),
        ]
        
        for metric_def in standard_metrics:
            self.register_metric(metric_def)
    
    def _create_otel_instruments(self):
        """Create OpenTelemetry instruments for all registered metrics"""
        if not self.otel_meter:
            return
        
        for metric_def in self.metric_definitions.values():
            self._create_otel_instrument(metric_def)
    
    def _create_otel_instrument(self, metric_def: MetricDefinition):
        """Create an OpenTelemetry instrument for a metric"""
        try:
            if metric_def.type == MetricType.COUNTER:
                instrument = self.otel_meter.create_counter(
                    name=metric_def.name,
                    description=metric_def.description,
                    unit=metric_def.unit
                )
            elif metric_def.type == MetricType.HISTOGRAM:
                instrument = self.otel_meter.create_histogram(
                    name=metric_def.name,
                    description=metric_def.description,
                    unit=metric_def.unit
                )
            elif metric_def.type == MetricType.GAUGE:
                instrument = self.otel_meter.create_up_down_counter(
                    name=metric_def.name,
                    description=metric_def.description,
                    unit=metric_def.unit
                )
            else:
                logger.warning(f"Unsupported OTEL metric type: {metric_def.type}")
                return
            
            self.otel_instruments[metric_def.name] = instrument
            
        except Exception as e:
            logger.error(f"Failed to create OTEL instrument for {metric_def.name}: {e}")
    
    def _create_prometheus_instrument(self, metric_def: MetricDefinition):
        """Create a Prometheus instrument for a metric"""
        try:
            if metric_def.type == MetricType.COUNTER:
                instrument = Counter(
                    name=metric_def.name,
                    documentation=metric_def.help_text,
                    labelnames=metric_def.labels,
                    registry=self.prometheus_registry
                )
            elif metric_def.type == MetricType.HISTOGRAM:
                instrument = Histogram(
                    name=metric_def.name,
                    documentation=metric_def.help_text,
                    labelnames=metric_def.labels,
                    buckets=metric_def.buckets,
                    registry=self.prometheus_registry
                )
            elif metric_def.type == MetricType.GAUGE:
                instrument = Gauge(
                    name=metric_def.name,
                    documentation=metric_def.help_text,
                    labelnames=metric_def.labels,
                    registry=self.prometheus_registry
                )
            else:
                logger.warning(f"Unsupported Prometheus metric type: {metric_def.type}")
                return
            
            self.prometheus_instruments[metric_def.name] = instrument
            
        except Exception as e:
            logger.error(f"Failed to create Prometheus instrument for {metric_def.name}: {e}")
    
    def _record_otel_metric(self, metric_def: MetricDefinition, value: Union[int, float], labels: Dict[str, str]):
        """Record metric in OpenTelemetry"""
        try:
            instrument = self.otel_instruments.get(metric_def.name)
            if not instrument:
                return
            
            if metric_def.type == MetricType.COUNTER:
                instrument.add(value, labels)
            elif metric_def.type == MetricType.HISTOGRAM:
                instrument.record(value, labels)
            elif metric_def.type == MetricType.GAUGE:
                # OTEL doesn't have direct gauge support, using up_down_counter
                instrument.add(value, labels)
            
        except Exception as e:
            logger.error(f"Failed to record OTEL metric {metric_def.name}: {e}")
    
    def _record_prometheus_metric(self, metric_def: MetricDefinition, value: Union[int, float], labels: Dict[str, str]):
        """Record metric in Prometheus"""
        try:
            instrument = self.prometheus_instruments.get(metric_def.name)
            if not instrument:
                return
            
            # Filter labels to only include those defined in the metric
            filtered_labels = {k: v for k, v in labels.items() if k in metric_def.labels}
            
            if metric_def.type == MetricType.COUNTER:
                instrument.labels(**filtered_labels).inc(value)
            elif metric_def.type == MetricType.HISTOGRAM:
                instrument.labels(**filtered_labels).observe(value)
            elif metric_def.type == MetricType.GAUGE:
                instrument.labels(**filtered_labels).set(value)
            
        except Exception as e:
            logger.error(f"Failed to record Prometheus metric {metric_def.name}: {e}")
    
    def get_prometheus_registry(self):
        """Get the Prometheus registry for /metrics endpoint"""
        return self.prometheus_registry
    
    def get_metric_definitions(self) -> Dict[str, MetricDefinition]:
        """Get all registered metric definitions"""
        return self.metric_definitions.copy()


class MetricTimer:
    """Context manager for timing operations"""
    
    def __init__(self, registry: UnifiedMetricsRegistry, metric_name: str, labels: Dict[str, str] = None, tenant_context: Optional[TenantContext] = None):
        self.registry = registry
        self.metric_name = metric_name
        self.labels = labels or {}
        self.tenant_context = tenant_context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.registry.observe_histogram(
                self.metric_name,
                duration,
                self.labels,
                self.tenant_context
            )


# Global metrics registry
metrics_registry = None


def get_metrics_registry() -> UnifiedMetricsRegistry:
    """Get the global metrics registry"""
    global metrics_registry
    if not metrics_registry:
        raise RuntimeError("Metrics registry not initialized")
    return metrics_registry


def initialize_metrics_registry(service_name: str, **kwargs) -> UnifiedMetricsRegistry:
    """Initialize the global metrics registry"""
    global metrics_registry
    metrics_registry = UnifiedMetricsRegistry(service_name, **kwargs)
    return metrics_registry