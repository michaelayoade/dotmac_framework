"""
Workflow analytics router for standardized endpoints.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query
from pydantic import BaseModel

from dotmac_shared.api import StandardDependencies, standard_exception_handler
from dotmac_shared.api.dependencies import get_standard_deps

from ..workflow_analytics import (
    WorkflowAnalyticsService,
    WorkflowMetrics,
    WorkflowStatus,
    WorkflowType,
)

router = APIRouter(prefix="/workflow-analytics", tags=["Workflow Analytics"])


class TrackWorkflowRequest(BaseModel):
    workflow_id: UUID
    workflow_type: WorkflowType
    event_type: str
    status: WorkflowStatus
    step_name: Optional[str] = None
    duration_ms: Optional[float] = None
    input_data: dict[str, Any] = {}
    output_data: dict[str, Any] = {}
    error_details: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = {}


def create_workflow_analytics_router(service: WorkflowAnalyticsService) -> APIRouter:
    @router.post("/events")
    @standard_exception_handler
    async def track_workflow_event(
        request: TrackWorkflowRequest = Body(...),
        deps: StandardDependencies = Depends(get_standard_deps),
    ) -> dict[str, str]:
        await service.track_workflow_event(
            workflow_id=request.workflow_id,
            workflow_type=request.workflow_type,
            event_type=request.event_type,
            status=request.status,
            step_name=request.step_name,
            user_id=deps.user_id,
            duration_ms=request.duration_ms,
            input_data=request.input_data,
            output_data=request.output_data,
            error_details=request.error_details,
            metadata=request.metadata,
        )
        return {"workflow_id": str(request.workflow_id)}

    @router.get("/metrics/{workflow_type}")
    @standard_exception_handler
    async def get_workflow_metrics(
        workflow_type: WorkflowType = Path(..., description="Workflow type"),
        period_start: Optional[datetime] = Query(None, description="Period start"),
        period_end: Optional[datetime] = Query(None, description="Period end"),
        deps: StandardDependencies = Depends(get_standard_deps),
    ) -> WorkflowMetrics:
        return await service.get_workflow_metrics(
            workflow_type=workflow_type,
            period_start=period_start,
            period_end=period_end,
            tenant_id=deps.tenant_id,
        )

    @router.get("/dashboard")
    @standard_exception_handler
    async def get_analytics_dashboard(
        period_days: int = Query(7, ge=1, le=90, description="Period in days"),
        deps: StandardDependencies = Depends(get_standard_deps),
    ) -> dict[str, Any]:
        return await service.get_workflow_analytics_dashboard(period_days=period_days, tenant_id=deps.tenant_id)

    @router.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok"}

    return router
