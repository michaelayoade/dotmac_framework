"""
Scheduler API endpoints for schedule and job management.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..contracts.common_schemas import (
    ExecutionStatus,
    OperationResponse,
    ListResponse,
    PaginationInfo,
)
from ..sdks.scheduler import SchedulerSDK, ScheduleDefinition

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class ScheduleCreateRequest(BaseModel):
    """Request model for creating a schedule."""

    name: str = Field(..., description="Schedule name")
    description: Optional[str] = Field(None, description="Schedule description")
    cron_expression: str = Field(..., description="Cron expression")
    timezone: str = Field("UTC", description="Timezone")
    enabled: bool = Field(True, description="Schedule enabled status")
    job_data: Dict[str, Any] = Field(default_factory=dict, description="Job data")
    max_instances: int = Field(1, description="Maximum concurrent instances")


class ScheduleResponse(BaseModel):
    """Response model for schedule operations."""

    id: str = Field(..., description="Schedule ID")
    name: str = Field(..., description="Schedule name")
    cron_expression: str = Field(..., description="Cron expression")
    timezone: str = Field(..., description="Timezone")
    enabled: bool = Field(..., description="Schedule enabled status")
    next_run: Optional[datetime] = Field(None, description="Next scheduled run")
    last_run: Optional[datetime] = Field(None, description="Last run timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class JobResponse(BaseModel):
    """Response model for job operations."""

    id: str = Field(..., description="Job ID")
    schedule_id: str = Field(..., description="Schedule ID")
    status: ExecutionStatus = Field(..., description="Job status")
    scheduled_at: datetime = Field(..., description="Scheduled timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Job output")
    error_message: Optional[str] = Field(None, description="Error message")


async def get_scheduler_sdk() -> SchedulerSDK:
    """Get scheduler SDK instance."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Scheduler SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    return "default-tenant"


@router.post("/schedules", response_model=OperationResponse)
async def create_schedule(
    request: ScheduleCreateRequest,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new schedule."""
    try:
        schedule = ScheduleDefinition(
            id=f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=request.name,
            description=request.description,
            cron_expression=request.cron_expression,
            timezone=request.timezone,
            enabled=request.enabled,
            job_data=request.job_data,
            max_instances=request.max_instances,
        )

        schedule_id = await scheduler_sdk.create_schedule(schedule)

        return OperationResponse(
            success=True,
            message="Schedule created successfully",
            data={"schedule_id": schedule_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create schedule: {str(e)}"
        )


@router.get("/schedules", response_model=ListResponse)
async def list_schedules(
    page: int = 1,
    page_size: int = 50,
    enabled_only: bool = False,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List schedules."""
    try:
        schedules = list(scheduler_sdk.schedules.values())

        # Apply filters
        if enabled_only:
            schedules = [schedule for schedule in schedules if schedule.enabled]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_schedules = schedules[start_idx:end_idx]

        # Convert to response format
        schedule_items = []
        for schedule in paginated_schedules:
            schedule_items.append({
                "id": schedule.id,
                "name": schedule.name,
                "cron_expression": schedule.cron_expression,
                "timezone": schedule.timezone,
                "enabled": schedule.enabled,
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "created_at": schedule.metadata.created_at.isoformat(),
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(schedules),
            total_pages=(len(schedules) + page_size - 1) // page_size,
            has_next=end_idx < len(schedules),
            has_previous=page > 1,
        )

        return ListResponse(
            items=schedule_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schedules: {str(e)}"
        )


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get schedule by ID."""
    try:
        schedule = scheduler_sdk.schedules.get(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )

        return ScheduleResponse(
            id=schedule.id,
            name=schedule.name,
            cron_expression=schedule.cron_expression,
            timezone=schedule.timezone,
            enabled=schedule.enabled,
            next_run=schedule.next_run,
            last_run=schedule.last_run,
            created_at=schedule.metadata.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schedule: {str(e)}"
        )


@router.put("/schedules/{schedule_id}", response_model=OperationResponse)
async def update_schedule(
    schedule_id: str,
    request: ScheduleCreateRequest,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Update a schedule."""
    try:
        updated_schedule = ScheduleDefinition(
            id=schedule_id,
            name=request.name,
            description=request.description,
            cron_expression=request.cron_expression,
            timezone=request.timezone,
            enabled=request.enabled,
            job_data=request.job_data,
            max_instances=request.max_instances,
        )

        success = await scheduler_sdk.update_schedule(schedule_id, updated_schedule)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )

        return OperationResponse(
            success=True,
            message="Schedule updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update schedule: {str(e)}"
        )


@router.post("/schedules/{schedule_id}/trigger", response_model=OperationResponse)
async def trigger_schedule(
    schedule_id: str,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Manually trigger a schedule."""
    try:
        job_id = await scheduler_sdk.trigger_schedule(schedule_id)

        return OperationResponse(
            success=True,
            message="Schedule triggered successfully",
            data={"job_id": job_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to trigger schedule: {str(e)}"
        )


@router.delete("/schedules/{schedule_id}", response_model=OperationResponse)
async def delete_schedule(
    schedule_id: str,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete a schedule."""
    try:
        success = await scheduler_sdk.delete_schedule(schedule_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )

        return OperationResponse(
            success=True,
            message="Schedule deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schedule: {str(e)}"
        )


@router.get("/jobs", response_model=ListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 50,
    schedule_id: Optional[str] = None,
    status_filter: Optional[ExecutionStatus] = None,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List scheduled jobs."""
    try:
        jobs = list(scheduler_sdk.jobs.values())

        # Apply filters
        if schedule_id:
            jobs = [job for job in jobs if job.schedule_id == schedule_id]
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]

        # Sort by scheduled time (most recent first)
        jobs.sort(key=lambda x: x.scheduled_at, reverse=True)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs[start_idx:end_idx]

        # Convert to response format
        job_items = []
        for job in paginated_jobs:
            job_items.append({
                "id": job.id,
                "schedule_id": job.schedule_id,
                "status": job.status.value,
                "scheduled_at": job.scheduled_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(jobs),
            total_pages=(len(jobs) + page_size - 1) // page_size,
            has_next=end_idx < len(jobs),
            has_previous=page > 1,
        )

        return ListResponse(
            items=job_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    scheduler_sdk: SchedulerSDK = Depends(get_scheduler_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get job details by ID."""
    try:
        job = scheduler_sdk.jobs.get(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        return JobResponse(
            id=job.id,
            schedule_id=job.schedule_id,
            status=job.status,
            scheduled_at=job.scheduled_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            output_data=job.output_data,
            error_message=job.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )
