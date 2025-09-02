"""
from dotmac_shared.api.exception_handlers import standard_exception_handler
API endpoints for monitoring and health checks.
"""

from typing import Any, Dict, Optional

from core.cache import get_cache_manager
from dotmac_shared.observability.logging import get_logger
from core.monitoring import (
    HealthStatus,
    get_comprehensive_status,
    health_checker,
    metrics_collector,
    request_metrics,
)
from fastapi import APIRouter
from pydantic import BaseModel

from dotmac_shared.api.router_factory import HTTPException, Query, RouterFactory

logger = get_logger(__name__)

# REPLACED: Direct APIRouter with RouterFactory
router = RouterFactory.create_crud_router(
    service_class=V1Service,
    create_schema=schemas.V1Create,
    update_schema=schemas.V1Update,
    response_schema=schemas.V1Response,
    prefix="/monitoring",
    tags=["monitoring"],
    enable_search=True,
    enable_bulk_operations=True,
)


class HealthResponse(BaseModel):
    """Health check response model."""

    overall_status: str
    checks: Dict[str, Any]
    system_uptime_seconds: int
    timestamp: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Perform comprehensive health checks on all system components",
)
@standard_exception_handler
async def health_check(
    include_details: bool = Query(
        default=True, description="Include detailed check information"
    ),
    check_name: Optional[str] = Query(
        default=None, description="Run specific health check only"
    ),
):
    """
    Perform system health checks.

    Returns overall system health status and individual component checks.
    """
    try:
        if check_name:
            # Run specific health check
            result = await health_checker.run_check(check_name)
            return {
                "overall_status": result.status.value,
                "checks": {
                    check_name: {
                        "status": result.status.value,
                        "response_time_ms": result.response_time_ms,
                        "message": result.message,
                        "details": result.details if include_details else {},
                        "timestamp": result.timestamp.isoformat(),
                    }
                },
                "system_uptime_seconds": 0,
                "timestamp": result.timestamp.isoformat(),
            }
        else:
            # Run all health checks
            health_status = await health_checker.run_all_checks(include_details)
            return health_status

    except Exception as e:
        logger.error("Health check endpoint failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get(
    "/health/liveness",
    summary="Kubernetes liveness probe",
    description="Simple liveness check for Kubernetes",
)
async def liveness_probe():
    """
    Simple liveness probe for container orchestration.

    Returns 200 if the application is running, 503 if not.
    """
    # Very basic check - if we can respond, we're alive
    return {"status": "alive", "timestamp": "2024-01-01T00:00:00Z"}


@router.get(
    "/health/readiness",
    summary="Kubernetes readiness probe",
    description="Readiness check for Kubernetes",
)
async def readiness_probe():
    """
    Readiness probe for container orchestration.

    Returns 200 if the application is ready to serve traffic, 503 if not.
    """
    # Check critical dependencies
    db_result = await health_checker.run_check("database")

    if db_result.status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {
        "status": "ready",
        "database_status": db_result.status.value,
        "timestamp": db_result.timestamp.isoformat(),
    }


@router.get(
    "/metrics/system",
    summary="System performance metrics",
    description="Get system resource usage and performance metrics",
)
async def system_metrics(
    minutes: int = Query(default=5, ge=1, le=60, description="Time period in minutes")
):
    """
    Get system performance metrics for the specified time period.

    Returns CPU, memory, disk usage, and other system metrics.
    """
    try:
        metrics = metrics_collector.get_metrics_summary(minutes)

        if not metrics:
            # If no historical data, collect current metrics
            current = metrics_collector.collect_system_metrics()
            return {
                "period_minutes": minutes,
                "samples_count": 1,
                "cpu_usage_percent": {
                    "current": current.cpu_usage_percent,
                    "average": current.cpu_usage_percent,
                },
                "memory_usage_percent": {
                    "current": current.memory_usage_percent,
                    "average": current.memory_usage_percent,
                    "available_bytes": current.memory_available_bytes,
                },
                "disk_usage_percent": {
                    "current": current.disk_usage_percent,
                    "average": current.disk_usage_percent,
                    "available_bytes": current.disk_available_bytes,
                },
                "network_connections": current.network_connections,
                "load_average": current.load_average,
                "uptime_seconds": current.uptime_seconds,
                "timestamp": current.timestamp.isoformat(),
            }

        return metrics

    except Exception as e:
        logger.error("System metrics endpoint failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")


@router.get(
    "/status",
    summary="Comprehensive system status",
    description="Get comprehensive system status including health, metrics, and performance data",
)
async def comprehensive_status():
    """
    Get comprehensive system status.

    Returns complete system overview including health checks,
    system metrics, request metrics, and cache statistics.
    """
    status = get_comprehensive_status()

    # Add health check results
    health_results = await health_checker.run_all_checks(include_details=False)
    status["health"] = health_results

    return status
