"""
Health check API endpoints.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..contracts.common_schemas import HealthStatus

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Component health status")


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool = Field(..., description="Application readiness status")
    timestamp: datetime = Field(..., description="Readiness check timestamp")
    components: Dict[str, bool] = Field(default_factory=dict, description="Component readiness status")


# Application start time for uptime calculation
_start_time = datetime.now()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the overall health status of the application and its components.
    """
    now = datetime.now()
    uptime = (now - _start_time).total_seconds()

    # Check component health (placeholder implementation)
    components = {
        "workflow_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "Workflow SDK is operational",
            "last_check": now.isoformat()
        },
        "task_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "Task SDK is operational",
            "last_check": now.isoformat()
        },
        "automation_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "Automation SDK is operational",
            "last_check": now.isoformat()
        },
        "scheduler_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "Scheduler SDK is operational",
            "last_check": now.isoformat()
        },
        "state_machine_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "State Machine SDK is operational",
            "last_check": now.isoformat()
        },
        "saga_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "Saga SDK is operational",
            "last_check": now.isoformat()
        },
        "job_queue_sdk": {
            "status": HealthStatus.HEALTHY.value,
            "message": "Job Queue SDK is operational",
            "last_check": now.isoformat()
        }
    }

    # Determine overall health status
    overall_status = HealthStatus.HEALTHY
    for component_health in components.values():
        if component_health["status"] == HealthStatus.UNHEALTHY.value:
            overall_status = HealthStatus.UNHEALTHY
            break
        elif component_health["status"] == HealthStatus.DEGRADED.value:
            overall_status = HealthStatus.DEGRADED

    return HealthResponse(
        status=overall_status,
        timestamp=now,
        version="0.1.0",  # This would come from config
        uptime_seconds=uptime,
        components=components
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint.

    Returns whether the application is ready to serve traffic.
    """
    now = datetime.now()

    # Check component readiness (placeholder implementation)
    components = {
        "workflow_sdk": True,
        "task_sdk": True,
        "automation_sdk": True,
        "scheduler_sdk": True,
        "state_machine_sdk": True,
        "saga_sdk": True,
        "job_queue_sdk": True,
        "database": True,  # Would check actual database connectivity
        "cache": True,     # Would check actual cache connectivity
    }

    # Application is ready if all components are ready
    ready = all(components.values())

    return ReadinessResponse(
        ready=ready,
        timestamp=now,
        components=components
    )


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.

    Simple endpoint that returns 200 OK if the application is alive.
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}
