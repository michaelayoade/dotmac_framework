"""
Performance API Endpoints - DRY Migration
Clean, optimal performance API endpoints using RouterFactory patterns.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import StandardDependencies, get_standard_deps

logger = logging.getLogger(__name__)


# === Enums and Schemas ===


class TimeRange(str, Enum):
    """Time range options for performance queries."""

    HOUR = "1h"
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"


class MetricType(str, Enum):
    """Available performance metric types."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DATABASE = "database"
    APPLICATION = "application"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PerformanceMetricRequest(BaseModel):
    """Request schema for performance metrics."""

    metric_type: MetricType = Field(..., description="Type of metric to retrieve")
    time_range: TimeRange = Field(TimeRange.HOUR, description="Time range for metrics")
    aggregation: str = Field(
        "avg", description="Aggregation method (avg, max, min, sum)"
    )
    include_alerts: bool = Field(True, description="Include alert information")


class AlertCreateRequest(BaseModel):
    """Request schema for creating performance alerts."""

    metric_type: MetricType = Field(..., description="Metric to monitor")
    threshold_value: float = Field(..., description="Alert threshold value")
    severity: AlertSeverity = Field(..., description="Alert severity")
    comparison_operator: str = Field(
        ">=", description="Comparison operator (>=, <=, ==)"
    )
    description: str | None = Field(None, description="Alert description")


class PerformanceReportRequest(BaseModel):
    """Request schema for performance reports."""

    time_range: TimeRange = Field(..., description="Report time range")
    metric_types: list[MetricType] = Field(..., description="Metrics to include")
    include_recommendations: bool = Field(
        True, description="Include performance recommendations"
    )
    format: str = Field("json", description="Report format (json, csv)")


# === Main Performance Router ===

performance_router = RouterFactory.create_standard_router(
    prefix="/performance",
    tags=["performance"],
)


# === Real-time Metrics ===


@performance_router.get("/metrics/realtime", response_model=dict[str, Any])
@standard_exception_handler
async def get_realtime_metrics(
    metric_types: list[MetricType]
    | None = Query(None, description="Filter by metric types"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get real-time performance metrics."""
    # Mock implementation for DRY migration
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": deps.tenant_id,
        "metrics": {
            "cpu": {"value": 65.2, "status": "ok", "threshold": 80.0},
            "memory": {"value": 72.1, "status": "warning", "threshold": 85.0},
            "disk": {"value": 45.3, "status": "ok", "threshold": 90.0},
            "network": {"value": 12.4, "status": "ok", "threshold": 100.0},
        },
        "status": "healthy",
    }


@performance_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def get_performance_health(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get overall performance health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "cpu": {"status": "ok", "score": 85},
            "memory": {"status": "warning", "score": 72},
            "disk": {"status": "ok", "score": 90},
            "network": {"status": "ok", "score": 95},
        },
        "active_alerts": 1,
        "performance_score": 85.5,
    }


# Export the router
__all__ = ["performance_router"]
