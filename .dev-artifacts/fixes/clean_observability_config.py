"""
Clean Observability Config - DRY Migration
Production-ready observability configuration using standardized patterns.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class OTelConfig(BaseModel):
    """OpenTelemetry configuration."""
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Environment")
    custom_resource_attributes: Dict[str, str] = Field(default_factory=dict)
    tracing_exporters: List[str] = Field(default_factory=list)
    metrics_exporters: List[str] = Field(default_factory=list)
    logging_exporters: List[str] = Field(default_factory=list)
    trace_sampler_ratio: float = Field(0.1, ge=0.0, le=1.0)
    metric_export_interval: int = Field(60, gt=0)


def create_otel_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: Optional[Environment] = None,
    custom_resource_attributes: Optional[Dict[str, str]] = None,
    tracing_exporters: Optional[List[str]] = None,
    metrics_exporters: Optional[List[str]] = None,
    logging_exporters: Optional[List[str]] = None,
    trace_sampler_ratio: Optional[float] = None,
    metric_export_interval: Optional[int] = None,
) -> OTelConfig:
    """Create OpenTelemetry configuration with environment-specific defaults."""
    
    # Set defaults
    environment = environment or Environment.DEVELOPMENT
    custom_resource_attributes = custom_resource_attributes or {}
    tracing_exporters = tracing_exporters or ["console"]
    metrics_exporters = metrics_exporters or ["console"] 
    logging_exporters = logging_exporters or ["console"]
    
    # Convert string to enum if needed
    if isinstance(environment, str):
        environment = Environment(environment)

    # Environment-specific sampling
    if trace_sampler_ratio is None:
        trace_sampler_ratio = 1.0 if environment == Environment.DEVELOPMENT else 0.1

    return OTelConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        custom_resource_attributes=custom_resource_attributes,
        tracing_exporters=tracing_exporters,
        metrics_exporters=metrics_exporters,
        logging_exporters=logging_exporters,
        trace_sampler_ratio=trace_sampler_ratio,
        metric_export_interval=metric_export_interval or 60,
    )


# Export the configuration
__all__ = ["OTelConfig", "Environment", "create_otel_config"]