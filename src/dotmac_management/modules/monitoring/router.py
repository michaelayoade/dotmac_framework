"""
Monitoring Module Router - DRY Migration
Comprehensive monitoring endpoints using RouterFactory patterns.
"""

from typing import Any
from uuid import UUID

from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from fastapi import Depends, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler

from .schemas import (
    MonitoringCreateSchema,
    MonitoringResponseSchema,
    MonitoringUpdateSchema,
)
from .service import MonitoringService

# === Additional Monitoring Schemas ===


class AlertRuleRequest(BaseModel):
    """Request schema for creating alert rules."""

    metric_name: str = Field(..., description="Metric to monitor")
    condition: str = Field(..., description="Alert condition")
    threshold: float = Field(..., description="Alert threshold value")
    severity: str = Field(..., description="Alert severity level")


class HealthCheckRequest(BaseModel):
    """Request schema for health check configuration."""

    endpoint_url: str = Field(..., description="Endpoint to monitor")
    check_interval: int = Field(60, description="Check interval in seconds")
    timeout: int = Field(30, description="Request timeout in seconds")
    expected_status: int = Field(200, description="Expected HTTP status code")


# === Main Monitoring Router ===

monitoring_router = RouterFactory.create_crud_router(
    service_class=MonitoringService,
    create_schema=MonitoringCreateSchema,
    update_schema=MonitoringUpdateSchema,
    response_schema=MonitoringResponseSchema,
    prefix="/monitoring",
    tags=["monitoring"],
    enable_search=True,
    enable_bulk_operations=True,
)


# === System Metrics ===


@monitoring_router.get("/metrics/system", response_model=dict[str, Any])
@standard_exception_handler
async def get_system_metrics(
    metric_types: list[str] | None = Query(None, description="Filter by metric types"),
    time_window: str = Query("1h", description="Time window for metrics"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get current system metrics."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.get_system_metrics(metric_types, time_window)


@monitoring_router.get("/metrics/applications", response_model=dict[str, Any])
@standard_exception_handler
async def get_application_metrics(
    application_id: UUID | None = Query(None, description="Filter by application"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get application-specific metrics."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.get_application_metrics(application_id)


# === Alert Management ===


@monitoring_router.get("/alerts", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_alerts(
    severity: str | None = Query(None, description="Filter by severity"),
    status: str | None = Query(None, description="Filter by status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List monitoring alerts with filtering."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.list_alerts(
        severity=severity,
        status=status,
        offset=deps.pagination.offset,
        limit=deps.pagination.size,
    )


@monitoring_router.post("/alerts/rules", response_model=dict[str, Any])
@standard_exception_handler
async def create_alert_rule(
    request: AlertRuleRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new alert rule."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.create_alert_rule(
        metric_name=request.metric_name,
        condition=request.condition,
        threshold=request.threshold,
        severity=request.severity,
        created_by=deps.user_id,
    )


@monitoring_router.post("/alerts/{alert_id}/acknowledge", response_model=dict[str, Any])
@standard_exception_handler
async def acknowledge_alert(
    alert_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Acknowledge a monitoring alert."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.acknowledge_alert(alert_id, deps.user_id)


# === Health Checks ===


@monitoring_router.get("/health-checks", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_health_checks(
    status: str | None = Query(None, description="Filter by status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List configured health checks."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.list_health_checks(
        status=status,
        offset=deps.pagination.offset,
        limit=deps.pagination.size,
    )


@monitoring_router.post("/health-checks", response_model=dict[str, Any])
@standard_exception_handler
async def create_health_check(
    request: HealthCheckRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new health check."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.create_health_check(
        endpoint_url=request.endpoint_url,
        check_interval=request.check_interval,
        timeout=request.timeout,
        expected_status=request.expected_status,
        created_by=deps.user_id,
    )


@monitoring_router.get(
    "/health-checks/{check_id}/status", response_model=dict[str, Any]
)
@standard_exception_handler
async def get_health_check_status(
    check_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get health check status and history."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.get_health_check_status(check_id)


# === Monitoring Dashboard ===


@monitoring_router.get("/dashboard", response_model=dict[str, Any])
@standard_exception_handler
async def get_monitoring_dashboard(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get monitoring dashboard data."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.get_dashboard_data()


@monitoring_router.get("/summary", response_model=dict[str, Any])
@standard_exception_handler
async def get_monitoring_summary(
    time_period: str = Query("24h", description="Time period for summary"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get monitoring summary for specified time period."""
    service = MonitoringService(deps.db, deps.tenant_id)
    return await service.get_monitoring_summary(time_period)


# === Export ===

__all__ = ["monitoring_router"]
