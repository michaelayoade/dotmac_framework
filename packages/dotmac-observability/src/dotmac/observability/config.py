"""
Configuration management for OpenTelemetry and observability components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from typing_extensions import Literal

try:
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    Resource = Any  # type: ignore


class Environment(str, Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class ExporterType(str, Enum):
    """Available exporter types."""
    CONSOLE = "console"
    OTLP_HTTP = "otlp_http"
    OTLP_GRPC = "otlp_grpc"
    JAEGER = "jaeger"
    PROMETHEUS = "prometheus"


@dataclass
class ExporterConfig:
    """Configuration for a single exporter."""
    type: ExporterType
    endpoint: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None
    compression: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for exporter initialization."""
        config = {"type": self.type.value}
        if self.endpoint:
            config["endpoint"] = self.endpoint
        if self.headers:
            config["headers"] = self.headers
        if self.timeout:
            config["timeout"] = self.timeout
        if self.compression:
            config["compression"] = self.compression
        return config


@dataclass
class OTelConfig:
    """OpenTelemetry configuration."""
    service_name: str
    service_version: str
    environment: Environment
    
    # Resource attributes
    custom_resource_attributes: Optional[Dict[str, str]] = None
    deployment_mode: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Exporters
    tracing_exporters: List[ExporterConfig] = field(default_factory=list)
    metrics_exporters: List[ExporterConfig] = field(default_factory=list)
    logging_exporters: List[ExporterConfig] = field(default_factory=list)
    
    # Sampling and batching
    trace_sampler_ratio: float = 1.0
    max_export_batch_size: int = 512
    max_queue_size: int = 2048
    export_timeout: int = 30000  # milliseconds
    
    # Feature flags
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    
    def get_resource_attributes(self) -> Dict[str, str]:
        """Get complete resource attributes for OTEL."""
        attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "deployment.environment": self.environment.value,
        }
        
        if self.deployment_mode:
            attributes["deployment.mode"] = self.deployment_mode
        
        if self.tenant_id:
            attributes["tenant.id"] = self.tenant_id
            
        if self.custom_resource_attributes:
            attributes.update(self.custom_resource_attributes)
            
        return attributes
    
    def get_resource(self) -> Optional["Resource"]:
        """Create OpenTelemetry Resource object."""
        if not OTEL_AVAILABLE:
            return None
            
        return Resource.create(self.get_resource_attributes())


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    service_name: str
    enable_prometheus: bool = True
    prometheus_port: int = 9090
    prometheus_path: str = "/metrics"
    
    # Metric collection settings
    collection_interval: int = 30  # seconds
    retention_period: int = 86400  # 24 hours in seconds
    
    # Business metrics
    enable_business_metrics: bool = True
    enable_slo_monitoring: bool = True
    slo_evaluation_interval: int = 300  # 5 minutes


@dataclass  
class DashboardConfig:
    """Configuration for dashboard provisioning."""
    enable_provisioning: bool = False
    platform_type: Literal["signoz", "grafana"] = "signoz"
    
    # Connection settings
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Provisioning options
    auto_create_datasources: bool = True
    template_variables: Optional[Dict[str, str]] = None


def create_default_config(
    service_name: str,
    environment: Environment | str,
    service_version: str = "1.0.0",
    custom_resource_attributes: Optional[Dict[str, str]] = None,
    tracing_exporters: Optional[List[ExporterConfig]] = None,
    metrics_exporters: Optional[List[ExporterConfig]] = None,
) -> OTelConfig:
    """
    Create a default OpenTelemetry configuration based on environment.
    
    Args:
        service_name: Name of the service
        environment: Deployment environment
        service_version: Version of the service
        custom_resource_attributes: Additional resource attributes
        tracing_exporters: Custom tracing exporters (overrides defaults)
        metrics_exporters: Custom metrics exporters (overrides defaults)
        
    Returns:
        Configured OTelConfig instance
    """
    if isinstance(environment, str):
        environment = Environment(environment)
    
    # Default exporters based on environment
    if tracing_exporters is None:
        tracing_exporters = _get_default_tracing_exporters(environment)
        
    if metrics_exporters is None:
        metrics_exporters = _get_default_metrics_exporters(environment)
    
    # Environment-specific sampling
    trace_sampler_ratio = 1.0 if environment == Environment.DEVELOPMENT else 0.1
    
    return OTelConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        custom_resource_attributes=custom_resource_attributes,
        tracing_exporters=tracing_exporters,
        metrics_exporters=metrics_exporters,
        trace_sampler_ratio=trace_sampler_ratio,
    )


def _get_default_tracing_exporters(environment: Environment) -> List[ExporterConfig]:
    """Get default tracing exporters for environment."""
    if environment == Environment.DEVELOPMENT:
        return [ExporterConfig(type=ExporterType.CONSOLE)]
    elif environment == Environment.PRODUCTION:
        # Use OTLP HTTP in production with environment-based endpoint
        return [ExporterConfig(
            type=ExporterType.OTLP_HTTP,
            endpoint="http://localhost:4318/v1/traces",  # Default, should be overridden
        )]
    else:  # staging, test
        return [ExporterConfig(
            type=ExporterType.OTLP_HTTP,
            endpoint="http://localhost:4318/v1/traces",
        )]


def _get_default_metrics_exporters(environment: Environment) -> List[ExporterConfig]:
    """Get default metrics exporters for environment."""
    if environment == Environment.DEVELOPMENT:
        return [
            ExporterConfig(type=ExporterType.CONSOLE),
            ExporterConfig(type=ExporterType.PROMETHEUS),
        ]
    else:
        return [
            ExporterConfig(
                type=ExporterType.OTLP_HTTP,
                endpoint="http://localhost:4318/v1/metrics",
            ),
            ExporterConfig(type=ExporterType.PROMETHEUS),
        ]


def create_metrics_config(
    service_name: str,
    enable_prometheus: bool = True,
    enable_business_metrics: bool = True,
) -> MetricsConfig:
    """Create a default metrics configuration."""
    return MetricsConfig(
        service_name=service_name,
        enable_prometheus=enable_prometheus,
        enable_business_metrics=enable_business_metrics,
    )


def create_dashboard_config(
    platform_type: Literal["signoz", "grafana"] = "signoz",
    enable_provisioning: bool = False,
    **kwargs: Any,
) -> DashboardConfig:
    """Create a dashboard configuration."""
    return DashboardConfig(
        platform_type=platform_type,
        enable_provisioning=enable_provisioning,
        **kwargs,
    )