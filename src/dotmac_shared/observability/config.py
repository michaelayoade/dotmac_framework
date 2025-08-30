"""
Observability Configuration Management

Centralized configuration for all observability components including
tracing, metrics, health monitoring, and external integrations.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ObservabilityBackend(Enum):
    """Supported observability backends."""

    PROMETHEUS = "prometheus"
    SIGNOZ = "signoz"
    DATADOG = "datadog"
    NEWRELIC = "newrelic"
    CUSTOM = "custom"


class TracingBackend(Enum):
    """Supported tracing backends."""

    OPENTELEMETRY = "opentelemetry"
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    SIGNOZ = "signoz"


@dataclass
class TracingConfig:
    """Configuration for distributed tracing."""

    enabled: bool = True
    backend: TracingBackend = TracingBackend.OPENTELEMETRY
    service_name: str = "dotmac-service"
    service_version: str = "1.0.0"
    sampling_rate: float = 1.0
    max_spans_per_trace: int = 1000
    export_timeout_ms: int = 30000
    export_batch_size: int = 512
    export_interval_ms: int = 5000

    # OpenTelemetry specific
    otlp_endpoint: Optional[str] = None
    otlp_headers: Dict[str, str] = field(default_factory=dict)
    otlp_insecure: bool = True

    # Jaeger specific
    jaeger_endpoint: Optional[str] = None
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6832

    # Custom attributes
    resource_attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""

    enabled: bool = True
    backends: List[ObservabilityBackend] = field(
        default_factory=lambda: [ObservabilityBackend.PROMETHEUS]
    )

    # Export configuration
    export_interval_ms: int = 30000
    export_timeout_ms: int = 10000

    # Histogram configuration
    histogram_buckets: List[float] = field(
        default_factory=lambda: [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1,
            2.5,
            5,
            10,
        ]
    )

    # Prometheus specific
    prometheus_enabled: bool = True
    prometheus_port: int = 8000
    prometheus_path: str = "/metrics"

    # SignOz specific
    signoz_enabled: bool = False
    signoz_endpoint: Optional[str] = None
    signoz_headers: Dict[str, str] = field(default_factory=dict)
    signoz_insecure: bool = True

    # Custom metrics
    enable_business_metrics: bool = True
    enable_system_metrics: bool = True
    enable_database_metrics: bool = True
    enable_cache_metrics: bool = True


@dataclass
class HealthConfig:
    """Configuration for health monitoring."""

    enabled: bool = True
    reporting_interval: int = 60  # seconds
    auto_start: bool = True

    # Health check configuration
    include_system_metrics: bool = True
    include_database_health: bool = True
    include_redis_health: bool = True
    include_network_health: bool = True
    include_application_health: bool = True
    include_business_metrics: bool = True

    # Thresholds
    cpu_warning_threshold: float = 70.0
    cpu_critical_threshold: float = 90.0
    memory_warning_threshold: float = 70.0
    memory_critical_threshold: float = 90.0
    disk_warning_threshold: float = 80.0
    disk_critical_threshold: float = 90.0

    # Database thresholds
    db_response_warning_ms: float = 1000.0
    db_response_critical_ms: float = 5000.0

    # Redis thresholds
    redis_response_warning_ms: float = 100.0
    redis_response_critical_ms: float = 1000.0


@dataclass
class SignOzConfig:
    """Configuration for SignOz integration."""

    enabled: bool = False
    endpoint: str = "localhost:4317"
    access_token: Optional[str] = None
    insecure: bool = True

    # Feature flags
    enable_traces: bool = True
    enable_metrics: bool = True
    enable_logs: bool = True
    enable_profiling: bool = False

    # Export configuration
    export_timeout_ms: int = 30000
    max_queue_size: int = 10000
    max_export_batch_size: int = 1000

    # Resource attributes
    environment: str = "development"
    deployment_environment: Optional[str] = None
    cloud_provider: Optional[str] = None
    cloud_region: Optional[str] = None


@dataclass
class CorrelationConfig:
    """Configuration for correlation and context propagation."""

    enabled: bool = True

    # Header names for correlation
    trace_id_header: str = "X-Trace-Id"
    span_id_header: str = "X-Span-Id"
    correlation_id_header: str = "X-Correlation-Id"
    causation_id_header: str = "X-Causation-Id"
    tenant_id_header: str = "X-Tenant-Id"
    user_id_header: str = "X-User-Id"
    request_id_header: str = "X-Request-Id"

    # Baggage configuration
    baggage_header: str = "X-Trace-Baggage"
    max_baggage_items: int = 10
    max_baggage_size: int = 1024  # bytes


@dataclass
class ObservabilityConfig:
    """Comprehensive observability configuration."""

    # Component configurations
    tracing: TracingConfig = field(default_factory=TracingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    signoz: SignOzConfig = field(default_factory=SignOzConfig)
    correlation: CorrelationConfig = field(default_factory=CorrelationConfig)

    # Global settings
    service_name: str = "dotmac-service"
    service_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Tenant configuration
    tenant_aware: bool = True
    tenant_isolation: bool = True

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create configuration from environment variables."""
        return cls(
            service_name=os.getenv("SERVICE_NAME", "dotmac-service"),
            service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            # Tracing configuration
            tracing=TracingConfig(
                enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
                service_name=os.getenv("SERVICE_NAME", "dotmac-service"),
                service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
                sampling_rate=float(os.getenv("TRACING_SAMPLING_RATE", "1.0")),
                otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
                otlp_insecure=os.getenv("OTLP_INSECURE", "true").lower() == "true",
            ),
            # Metrics configuration
            metrics=MetricsConfig(
                enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
                prometheus_enabled=os.getenv("PROMETHEUS_ENABLED", "true").lower()
                == "true",
                prometheus_port=int(os.getenv("PROMETHEUS_PORT", "8000")),
                signoz_enabled=os.getenv("SIGNOZ_METRICS_ENABLED", "false").lower()
                == "true",
            ),
            # Health configuration
            health=HealthConfig(
                enabled=os.getenv("HEALTH_ENABLED", "true").lower() == "true",
                reporting_interval=int(os.getenv("HEALTH_REPORTING_INTERVAL", "60")),
                auto_start=os.getenv("HEALTH_AUTO_START", "true").lower() == "true",
            ),
            # SignOz configuration
            signoz=SignOzConfig(
                enabled=os.getenv("SIGNOZ_ENABLED", "false").lower() == "true",
                endpoint=os.getenv("SIGNOZ_ENDPOINT", "localhost:4317"),
                access_token=os.getenv("SIGNOZ_ACCESS_TOKEN"),
                insecure=os.getenv("SIGNOZ_INSECURE", "true").lower() == "true",
                environment=os.getenv("ENVIRONMENT", "development"),
                cloud_provider=os.getenv("CLOUD_PROVIDER"),
                cloud_region=os.getenv("CLOUD_REGION"),
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "environment": self.environment,
            "debug": self.debug,
            "tenant_aware": self.tenant_aware,
            "tenant_isolation": self.tenant_isolation,
            "tracing": {
                "enabled": self.tracing.enabled,
                "backend": self.tracing.backend.value,
                "service_name": self.tracing.service_name,
                "service_version": self.tracing.service_version,
                "sampling_rate": self.tracing.sampling_rate,
                "max_spans_per_trace": self.tracing.max_spans_per_trace,
                "export_timeout_ms": self.tracing.export_timeout_ms,
                "otlp_endpoint": self.tracing.otlp_endpoint,
                "otlp_insecure": self.tracing.otlp_insecure,
            },
            "metrics": {
                "enabled": self.metrics.enabled,
                "backends": [b.value for b in self.metrics.backends],
                "export_interval_ms": self.metrics.export_interval_ms,
                "histogram_buckets": self.metrics.histogram_buckets,
                "prometheus_enabled": self.metrics.prometheus_enabled,
                "prometheus_port": self.metrics.prometheus_port,
                "signoz_enabled": self.metrics.signoz_enabled,
            },
            "health": {
                "enabled": self.health.enabled,
                "reporting_interval": self.health.reporting_interval,
                "auto_start": self.health.auto_start,
                "include_system_metrics": self.health.include_system_metrics,
                "include_business_metrics": self.health.include_business_metrics,
            },
            "signoz": {
                "enabled": self.signoz.enabled,
                "endpoint": self.signoz.endpoint,
                "insecure": self.signoz.insecure,
                "enable_traces": self.signoz.enable_traces,
                "enable_metrics": self.signoz.enable_metrics,
                "enable_logs": self.signoz.enable_logs,
                "environment": self.signoz.environment,
            },
            "correlation": {
                "enabled": self.correlation.enabled,
                "trace_id_header": self.correlation.trace_id_header,
                "correlation_id_header": self.correlation.correlation_id_header,
                "tenant_id_header": self.correlation.tenant_id_header,
            },
        }


def get_default_config() -> ObservabilityConfig:
    """Get default observability configuration."""
    return ObservabilityConfig()


def get_env_config() -> ObservabilityConfig:
    """Get configuration from environment variables."""
    return ObservabilityConfig.from_env()


# Configuration validation functions
def validate_config(config: ObservabilityConfig) -> List[str]:
    """Validate observability configuration and return any errors."""
    errors = []

    # Validate service name
    if not config.service_name or not isinstance(config.service_name, str):
        errors.append("Service name must be a non-empty string")

    # Validate sampling rate
    if not 0.0 <= config.tracing.sampling_rate <= 1.0:
        errors.append("Tracing sampling rate must be between 0.0 and 1.0")

    # Validate histogram buckets
    if config.metrics.histogram_buckets:
        buckets = config.metrics.histogram_buckets
        if not all(isinstance(b, (int, float)) and b > 0 for b in buckets):
            errors.append("All histogram buckets must be positive numbers")
        if buckets != sorted(buckets):
            errors.append("Histogram buckets must be in ascending order")

    # Validate health thresholds
    health = config.health
    if health.cpu_warning_threshold >= health.cpu_critical_threshold:
        errors.append("CPU warning threshold must be less than critical threshold")
    if health.memory_warning_threshold >= health.memory_critical_threshold:
        errors.append("Memory warning threshold must be less than critical threshold")

    # Validate SignOz configuration
    if config.signoz.enabled:
        if not config.signoz.endpoint:
            errors.append("SignOz endpoint is required when SignOz is enabled")

    return errors


# Environment variable helpers
def get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def get_int_env(key: str, default: int = 0) -> int:
    """Get integer value from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_float_env(key: str, default: float = 0.0) -> float:
    """Get float value from environment variable."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_list_env(
    key: str, separator: str = ",", default: Optional[List[str]] = None
) -> List[str]:
    """Get list value from environment variable."""
    value = os.getenv(key)
    if value:
        return [item.strip() for item in value.split(separator) if item.strip()]
    return default or []
