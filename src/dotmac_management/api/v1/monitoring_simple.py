"""
Simple monitoring API using core monitoring models and repositories.

Provides a minimal, conflict-free monitoring surface without loading
module-specific models that duplicate core tables.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, Query

from dotmac.application import standard_exception_handler
from dotmac.application.api.router_factory import RouterFactory
from dotmac_shared.api.dependencies import StandardDependencies, get_standard_deps
from dotmac_shared.api.rate_limiting_decorators import rate_limit

from ...repositories.monitoring import MonitoringRepository

# DRY Router
router = RouterFactory("Monitoring").create_router(
    prefix="/monitoring", tags=["Monitoring"]
)


@router.get("/health/recent")
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def recent_health_checks(
    deps: StandardDependencies = Depends(get_standard_deps),
    limit: int = Query(10, ge=1, le=200),
    check_type: Optional[str] = Query(None),
) -> dict[str, Any]:
    repo = MonitoringRepository(deps.db)
    checks = await repo.get_tenant_health_checks(deps.tenant_id, limit, check_type)
    return {
        "tenant_id": deps.tenant_id,
        "count": len(checks),
        "items": [
            {
                "id": str(c.id),
                "name": c.check_name,
                "type": c.check_type,
                "status": c.status.value
                if hasattr(c.status, "value")
                else str(c.status),
                "success": c.success,
                "response_time_ms": c.response_time_ms,
                "timestamp": getattr(c, "created_at", getattr(c, "timestamp", None)),
            }
            for c in checks
        ],
    }


@router.get("/alerts/active")
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def active_alerts(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    repo = MonitoringRepository(deps.db)
    alerts = await repo.get_active_alerts(deps.tenant_id)
    return {
        "tenant_id": deps.tenant_id,
        "count": len(alerts),
        "items": [
            {
                "id": str(a.id),
                "name": a.alert_name,
                "severity": a.severity.value
                if hasattr(a.severity, "value")
                else str(a.severity),
                "status": a.status.value
                if hasattr(a.status, "value")
                else str(a.status),
                "title": a.title,
                "metric_name": a.metric_name,
                "first_triggered_at": getattr(a, "first_triggered_at", None),
                "last_triggered_at": getattr(a, "last_triggered_at", None),
            }
            for a in alerts
        ],
    }


@router.get("/metrics/{metric_name}")
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def metrics_by_name(
    metric_name: str,
    deps: StandardDependencies = Depends(get_standard_deps),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    repo = MonitoringRepository(deps.db)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    metrics = await repo.get_tenant_metrics(
        deps.tenant_id, [metric_name], start_time, end_time, limit
    )
    return {
        "tenant_id": deps.tenant_id,
        "metric": metric_name,
        "count": len(metrics),
        "items": [
            {
                "id": str(m.id),
                "name": m.metric_name,
                "value": float(m.value),
                "unit": m.unit,
                "timestamp": m.timestamp,
                "labels": m.labels,
            }
            for m in metrics
        ],
    }
