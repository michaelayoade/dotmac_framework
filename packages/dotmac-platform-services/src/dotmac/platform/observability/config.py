"""
Observability configuration and helpers used by platform bootstrap.

Adds explicit exporter types/config, enriched OTelConfig with resource helper,
and a create_default_config compatible with existing call sites.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class Environment(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ObservabilityConfig(BaseModel):
    """Observability configuration for logging, metrics, and tracing."""

    service_name: str = Field("dotmac-service", description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Environment")
    log_level: str = Field("INFO", description="Default log level")
    enable_structured_logging: bool = Field(True, description="Enable structured JSON logging")
    enable_correlation_ids: bool = Field(True, description="Enable correlation ID tracking")
    enable_audit_logging: bool = Field(True, description="Enable audit logging")
    custom_resource_attributes: dict[str, str] = Field(default_factory=dict)


class ExporterType(str, Enum):
    """Supported exporter types."""

    CONSOLE = "console"
    OTLP_HTTP = "otlp_http"
    OTLP_GRPC = "otlp"
    JAEGER = "jaeger"
    PROMETHEUS = "prometheus"  # Metrics only; ignored for tracing


class ExporterConfig(BaseModel):
    """Exporter configuration."""

    type: ExporterType
    endpoint: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 30000  # ms
    compression: Optional[str] = None


class OTelConfig(BaseModel):
    """OpenTelemetry configuration for bootstrap."""

    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Environment")
    custom_resource_attributes: dict[str, str] = Field(default_factory=dict)
    tracing_exporters: List[ExporterConfig] = Field(default_factory=list)
    metrics_exporters: List[ExporterConfig] = Field(default_factory=list)
    logging_exporters: List[ExporterConfig] = Field(default_factory=list)
    trace_sampler_ratio: float = Field(0.1, ge=0.0, le=1.0)
    metric_export_interval: int = Field(60, gt=0)
    enable_tracing: bool = True
    enable_metrics: bool = True
    max_export_batch_size: int = 512
    max_queue_size: int = 2048
    export_timeout: int = 30000  # ms

    @validator("environment", pre=True)
    def _normalize_env(cls, v: Any) -> Environment:  # noqa: N805
        return Environment(v) if isinstance(v, str) else v

    def get_resource(self):
        """Build an OTEL Resource if available; else return minimal dict."""
        try:
            from opentelemetry.sdk.resources import Resource

            attributes = {
                "service.name": self.service_name,
                "service.version": self.service_version,
                "deployment.environment": self.environment.value,
            }
            attributes.update(self.custom_resource_attributes)
            return Resource.create(attributes)
        except Exception:
            # Fallback object; bootstrap guards OTEL imports anyway
            return {
                "service.name": self.service_name,
                "service.version": self.service_version,
                "deployment.environment": self.environment.value,
                **self.custom_resource_attributes,
            }


def _to_exporter_config(name_or_cfg: Any, default_endpoint: Optional[str]) -> Optional[ExporterConfig]:
    """Normalize exporter spec to ExporterConfig; drop unsupported combos.

    - Strings like "otlp", "console", "jaeger", "prometheus" map to ExporterConfig.
    - Dicts with type/endpoint are passed through.
    - Unknown values return None.
    """
    if isinstance(name_or_cfg, ExporterConfig):
        return name_or_cfg

    if isinstance(name_or_cfg, str):
        key = name_or_cfg.strip().lower()
        if key in ("otlp", "otlp_grpc"):
            return ExporterConfig(type=ExporterType.OTLP_GRPC, endpoint=default_endpoint)
        if key in ("otlp_http", "otlp-http"):
            return ExporterConfig(type=ExporterType.OTLP_HTTP, endpoint=default_endpoint)
        if key == "console":
            return ExporterConfig(type=ExporterType.CONSOLE)
        if key == "jaeger":
            return ExporterConfig(type=ExporterType.JAEGER, endpoint=default_endpoint)
        if key == "prometheus":
            # Prometheus is metrics-only; allowed in metrics list, ignored in tracing
            return ExporterConfig(type=ExporterType.PROMETHEUS)
        return None

    if isinstance(name_or_cfg, dict):
        t = name_or_cfg.get("type")
        if t is None:
            return None
        try:
            et = ExporterType(str(t))
        except ValueError:
            return None
        return ExporterConfig(
            type=et,
            endpoint=name_or_cfg.get("endpoint", default_endpoint),
            headers=name_or_cfg.get("headers", {}),
            timeout=name_or_cfg.get("timeout", 30000),
            compression=name_or_cfg.get("compression"),
        )

    return None


def create_default_config(
    service_name: str,
    environment: str | Environment = Environment.DEVELOPMENT,
    service_version: str = "1.0.0",
    custom_resource_attributes: Optional[dict[str, str]] = None,
    tracing_exporters: Optional[list[Any]] = None,
    metrics_exporters: Optional[list[Any]] = None,
    otlp_endpoint: Optional[str] = None,
) -> OTelConfig:
    """Create an OTelConfig consistent with platform bootstrap expectations.

    Notes:
    - Drops Prometheus from tracing exporters automatically.
    - Defaults to console exporters in development, OTLP in non-dev environments.
    """
    env_enum = Environment(environment) if isinstance(environment, str) else environment

    # Defaults based on environment
    if tracing_exporters is None:
        tracing_exporters = ["console"] if env_enum == Environment.DEVELOPMENT else ["otlp"]
    if metrics_exporters is None:
        metrics_exporters = ["console"] if env_enum == Environment.DEVELOPMENT else ["otlp"]

    # Normalize exporters
    t_exporters: List[ExporterConfig] = []
    for e in tracing_exporters:
        cfg = _to_exporter_config(e, otlp_endpoint)
        if cfg and cfg.type != ExporterType.PROMETHEUS:  # never allow Prometheus for tracing
            t_exporters.append(cfg)

    m_exporters: List[ExporterConfig] = []
    for e in metrics_exporters:
        cfg = _to_exporter_config(e, otlp_endpoint)
        if cfg:
            m_exporters.append(cfg)

    # Sampling defaults
    trace_sampler_ratio = 1.0 if env_enum == Environment.DEVELOPMENT else 0.1

    return OTelConfig(
        service_name=service_name,
        service_version=service_version,
        environment=env_enum,
        custom_resource_attributes=custom_resource_attributes or {},
        tracing_exporters=t_exporters,
        metrics_exporters=m_exporters,
        logging_exporters=[ExporterConfig(type=ExporterType.CONSOLE)],
        trace_sampler_ratio=trace_sampler_ratio,
        metric_export_interval=60,
        enable_tracing=True,
        enable_metrics=True,
    )


# Backwards-compatible helper for callers expecting create_otel_config
def create_otel_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: Environment | str | None = None,
    custom_resource_attributes: dict[str, str] | None = None,
    tracing_exporters: list[Any] | None = None,
    metrics_exporters: list[Any] | None = None,
    logging_exporters: list[Any] | None = None,
    trace_sampler_ratio: float | None = None,
    metric_export_interval: int | None = None,
) -> OTelConfig:
    env = environment or Environment.DEVELOPMENT
    cfg = create_default_config(
        service_name=service_name,
        service_version=service_version,
        environment=env,
        custom_resource_attributes=custom_resource_attributes or {},
        tracing_exporters=tracing_exporters,
        metrics_exporters=metrics_exporters,
    )
    if trace_sampler_ratio is not None:
        cfg.trace_sampler_ratio = trace_sampler_ratio
    if metric_export_interval is not None:
        cfg.metric_export_interval = metric_export_interval
    # logging_exporters currently not used by bootstrap, ignore gracefully
    return cfg


__all__ = [
    "Environment",
    "ExporterType",
    "ExporterConfig",
    "OTelConfig",
    "ObservabilityConfig",
    "create_default_config",
    "create_otel_config",
]
