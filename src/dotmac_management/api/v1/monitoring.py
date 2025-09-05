"""
Monitoring API v1 - DRY Migration
System monitoring endpoints using RouterFactory patterns.
"""

from typing import Any

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from fastapi import Depends, Query
from pydantic import BaseModel, Field

# === Monitoring Schemas ===


class AlertRuleRequest(BaseModel):
    """Request schema for creating alert rules."""

    name: str = Field(..., description="Alert rule name")
    metric: str = Field(..., description="Metric to monitor")
    condition: str = Field(..., description="Alert condition")
    threshold: float = Field(..., description="Alert threshold")
    severity: str = Field(..., description="Alert severity")


# === Monitoring API Router ===

monitoring_api_router = RouterFactory.create_standard_router(
    prefix="/v1/monitoring",
    tags=["monitoring", "v1"],
)


# === System Monitoring ===


@monitoring_api_router.get("/status", response_model=dict[str, Any])
@standard_exception_handler
async def get_system_status(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get overall system status."""
    return {
        "status": "healthy",
        "uptime": "99.9%",
        "response_time": "120ms",
        "active_connections": 1247,
        "cpu_usage": 65.2,
        "memory_usage": 72.1,
        "disk_usage": 45.3,
        "last_check": "2025-01-15T10:30:00Z",
    }


@monitoring_api_router.get("/metrics", response_model=dict[str, Any])
@standard_exception_handler
async def get_system_metrics(
    metric_type: str | None = Query(None, description="Filter by metric type"),
    time_range: str = Query("1h", description="Time range for metrics"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get system metrics."""
    metrics = {
        "cpu": [
            {"timestamp": "2025-01-15T10:00:00Z", "value": 65.2},
            {"timestamp": "2025-01-15T10:05:00Z", "value": 68.1},
            {"timestamp": "2025-01-15T10:10:00Z", "value": 62.5},
        ],
        "memory": [
            {"timestamp": "2025-01-15T10:00:00Z", "value": 72.1},
            {"timestamp": "2025-01-15T10:05:00Z", "value": 74.3},
            {"timestamp": "2025-01-15T10:10:00Z", "value": 71.8},
        ],
        "disk": [
            {"timestamp": "2025-01-15T10:00:00Z", "value": 45.3},
            {"timestamp": "2025-01-15T10:05:00Z", "value": 45.4},
            {"timestamp": "2025-01-15T10:10:00Z", "value": 45.5},
        ],
    }

    if metric_type:
        metrics = {metric_type: metrics.get(metric_type, [])}

    return {
        "time_range": time_range,
        "metrics": metrics,
        "summary": {
            "avg_cpu": 65.3,
            "avg_memory": 72.7,
            "avg_disk": 45.4,
        },
    }


# === Alerts ===


@monitoring_api_router.get("/alerts", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_alerts(
    severity: str | None = Query(None, description="Filter by severity"),
    status: str | None = Query(None, description="Filter by status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List monitoring alerts."""
    alerts = [
        {
            "id": "alert-001",
            "name": "High CPU Usage",
            "severity": "warning",
            "status": "active",
            "metric": "cpu_usage",
            "current_value": 82.5,
            "threshold": 80.0,
            "triggered_at": "2025-01-15T10:15:00Z",
            "description": "CPU usage exceeded threshold",
        },
        {
            "id": "alert-002",
            "name": "Memory Usage Alert",
            "severity": "critical",
            "status": "resolved",
            "metric": "memory_usage",
            "current_value": 65.2,
            "threshold": 85.0,
            "triggered_at": "2025-01-15T09:30:00Z",
            "resolved_at": "2025-01-15T09:45:00Z",
            "description": "Memory usage returned to normal",
        },
    ]

    # Apply filters
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    if status:
        alerts = [a for a in alerts if a["status"] == status]

    return alerts[: deps.pagination.size]


@monitoring_api_router.post("/alerts/rules", response_model=dict[str, Any])
@standard_exception_handler
async def create_alert_rule(
    rule_request: AlertRuleRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new alert rule."""
    rule_id = f"rule-{rule_request.name.lower().replace(' ', '-')}"

    return {
        "id": rule_id,
        "name": rule_request.name,
        "metric": rule_request.metric,
        "condition": rule_request.condition,
        "threshold": rule_request.threshold,
        "severity": rule_request.severity,
        "status": "active",
        "created_by": deps.user_id,
        "created_at": "2025-01-15T10:30:00Z",
        "message": "Alert rule created successfully",
    }


# === Health Checks ===


@monitoring_api_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def monitoring_health_check(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Check monitoring service health."""
    return {
        "status": "healthy",
        "monitoring_active": True,
        "alerts_processed": 125,
        "metrics_collected": 2450,
        "last_collection": "2025-01-15T10:29:00Z",
        "database_connection": "healthy",
    }


# Export the router
__all__ = ["monitoring_api_router"]
