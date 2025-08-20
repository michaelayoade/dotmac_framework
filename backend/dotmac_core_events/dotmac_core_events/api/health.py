"""
Health API endpoints for dotmac_core_events.

Provides REST API for:
- Application health checks
- Component health monitoring
- Readiness and liveness probes
- System metrics
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..core.dependencies import (
    get_event_bus,
    get_outbox,
    get_schema_registry,
    get_tenant_id,
)
from ..sdks.event_bus import EventBusSDK
from ..sdks.outbox import OutboxSDK
from ..sdks.schema_registry import SchemaRegistrySDK


class HealthStatus(BaseModel):
    """Health status model."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")


class ComponentHealth(BaseModel):
    """Component health model."""

    name: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status")
    message: Optional[str] = Field(None, description="Status message")
    last_check: datetime = Field(..., description="Last health check timestamp")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")


class DetailedHealthResponse(BaseModel):
    """Detailed health response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    components: List[ComponentHealth] = Field(..., description="Component health details")


class MetricValue(BaseModel):
    """Metric value model."""

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    timestamp: datetime = Field(..., description="Metric timestamp")
    labels: Optional[Dict[str, str]] = Field(None, description="Metric labels")


class MetricsResponse(BaseModel):
    """Metrics response model."""

    metrics: List[MetricValue] = Field(..., description="System metrics")
    timestamp: datetime = Field(..., description="Metrics collection timestamp")


class HealthAPI:
    """Health and monitoring API endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/health", tags=["health"])
        self._setup_routes()
        self._start_time = datetime.now()

    def _setup_routes(self):  # noqa: PLR0915, C901
        """Set up API routes."""

        @self.router.get(
            "/",
            response_model=HealthStatus,
            summary="Basic health check",
            description="Get basic application health status"
        )
        async def health_check() -> HealthStatus:
            """Basic health check endpoint."""
            now = datetime.now()
            uptime = (now - self._start_time).total_seconds()

            return HealthStatus(
                status="healthy",
                timestamp=now,
                version="1.0.0",
                uptime_seconds=uptime,
            )

        @self.router.get(
            "/detailed",
            response_model=DetailedHealthResponse,
            summary="Detailed health check",
            description="Get detailed health status with component information"
        )
        async def detailed_health_check(
            event_bus: Optional[EventBusSDK] = Depends(get_event_bus),
            schema_registry: Optional[SchemaRegistrySDK] = Depends(get_schema_registry),
            outbox: Optional[OutboxSDK] = Depends(get_outbox)
        ) -> DetailedHealthResponse:
            """Detailed health check with component status."""
            now = datetime.now()
            uptime = (now - self._start_time).total_seconds()

            components = []
            overall_status = "healthy"

            # Check Event Bus
            if event_bus:
                try:
                    # Simple check - get metrics
                    metrics = event_bus.get_metrics()
                    components.append(ComponentHealth(
                        name="event_bus",
                        status="healthy",
                        message=f"Tenant: {metrics.get('tenant_id')}",
                        last_check=now,
                        response_time_ms=1.0,
                    ))
                except Exception as e:
                    components.append(ComponentHealth(
                        name="event_bus",
                        status="unhealthy",
                        message=str(e),
                        last_check=now,
                    ))
                    overall_status = "degraded"
            else:
                components.append(ComponentHealth(
                    name="event_bus",
                    status="unavailable",
                    message="Not configured",
                    last_check=now,
                ))

            # Check Schema Registry
            if schema_registry:
                try:
                    metrics = schema_registry.get_metrics()
                    components.append(ComponentHealth(
                        name="schema_registry",
                        status="healthy",
                        message=f"Cache hit rate: {metrics.get('cache_hit_rate', 0):.2%}",
                        last_check=now,
                        response_time_ms=1.0,
                    ))
                except Exception as e:
                    components.append(ComponentHealth(
                        name="schema_registry",
                        status="unhealthy",
                        message=str(e),
                        last_check=now,
                    ))
                    overall_status = "degraded"
            else:
                components.append(ComponentHealth(
                    name="schema_registry",
                    status="unavailable",
                    message="Not configured",
                    last_check=now,
                ))

            # Check Outbox
            if outbox:
                try:
                    metrics = outbox.get_metrics()
                    components.append(ComponentHealth(
                        name="outbox",
                        status="healthy" if metrics.get("running") else "degraded",
                        message=f"Published: {metrics.get('published_count', 0)}",
                        last_check=now,
                        response_time_ms=1.0,
                    ))
                except Exception as e:
                    components.append(ComponentHealth(
                        name="outbox",
                        status="unhealthy",
                        message=str(e),
                        last_check=now,
                    ))
                    overall_status = "degraded"
            else:
                components.append(ComponentHealth(
                    name="outbox",
                    status="unavailable",
                    message="Not configured",
                    last_check=now,
                ))

            return DetailedHealthResponse(
                status=overall_status,
                timestamp=now,
                version="1.0.0",
                uptime_seconds=uptime,
                components=components,
            )

        @self.router.get(
            "/ready",
            summary="Readiness probe",
            description="Kubernetes readiness probe endpoint"
        )
        async def readiness_probe(
            event_bus: Optional[EventBusSDK] = Depends(get_event_bus)
        ) -> Dict[str, str]:
            """Readiness probe for Kubernetes."""
            # Check if critical components are ready
            if not event_bus:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Event bus not ready"
                )

            return {"status": "ready"}

        @self.router.get(
            "/live",
            summary="Liveness probe",
            description="Kubernetes liveness probe endpoint"
        )
        async def liveness_probe() -> Dict[str, str]:
            """Liveness probe for Kubernetes."""
            return {"status": "alive"}

        @self.router.get(
            "/metrics",
            response_model=MetricsResponse,
            summary="System metrics",
            description="Get system metrics"
        )
        async def get_metrics(
            tenant_id: Optional[str] = Depends(get_tenant_id),
            event_bus: Optional[EventBusSDK] = Depends(get_event_bus),
            schema_registry: Optional[SchemaRegistrySDK] = Depends(get_schema_registry),
            outbox: Optional[OutboxSDK] = Depends(get_outbox)
        ) -> MetricsResponse:
            """Get system metrics."""
            now = datetime.now()
            metrics = []

            # Application metrics
            uptime = (now - self._start_time).total_seconds()
            metrics.append(MetricValue(
                name="app_uptime_seconds",
                value=uptime,
                unit="seconds",
                timestamp=now,
            ))

            # Event Bus metrics
            if event_bus:
                try:
                    bus_metrics = event_bus.get_metrics()
                    metrics.extend([
                        MetricValue(
                            name="event_bus_publish_count",
                            value=bus_metrics.get("publish_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": bus_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="event_bus_consume_count",
                            value=bus_metrics.get("consume_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": bus_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="event_bus_error_count",
                            value=bus_metrics.get("error_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": bus_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="event_bus_active_subscriptions",
                            value=bus_metrics.get("active_subscriptions", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": bus_metrics.get("tenant_id")},
                        ),
                    ])
                except Exception:
                    pass

            # Schema Registry metrics
            if schema_registry:
                try:
                    registry_metrics = schema_registry.get_metrics()
                    metrics.extend([
                        MetricValue(
                            name="schema_registry_registration_count",
                            value=registry_metrics.get("registration_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": registry_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="schema_registry_validation_count",
                            value=registry_metrics.get("validation_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": registry_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="schema_registry_cache_hit_rate",
                            value=registry_metrics.get("cache_hit_rate", 0),
                            unit="ratio",
                            timestamp=now,
                            labels={"tenant_id": registry_metrics.get("tenant_id")},
                        ),
                    ])
                except Exception:
                    pass

            # Outbox metrics
            if outbox:
                try:
                    outbox_metrics = outbox.get_metrics()
                    metrics.extend([
                        MetricValue(
                            name="outbox_stored_count",
                            value=outbox_metrics.get("stored_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": outbox_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="outbox_published_count",
                            value=outbox_metrics.get("published_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": outbox_metrics.get("tenant_id")},
                        ),
                        MetricValue(
                            name="outbox_failed_count",
                            value=outbox_metrics.get("failed_count", 0),
                            unit="count",
                            timestamp=now,
                            labels={"tenant_id": outbox_metrics.get("tenant_id")},
                        ),
                    ])
                except Exception:
                    pass

            return MetricsResponse(
                metrics=metrics,
                timestamp=now,
            )
