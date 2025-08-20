"""
Job Queue API endpoints for job queue management and execution.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..contracts.common_schemas import (
    ExecutionStatus,
    Priority,
    OperationResponse,
    ListResponse,
    PaginationInfo,
)
from ..sdks.job_queue import JobQueueSDK, JobDefinition

router = APIRouter(prefix="/job-queues", tags=["job-queues"])


class JobDefinitionCreateRequest(BaseModel):
    """Request model for creating a job definition."""

    name: str = Field(..., description="Job definition name")
    description: Optional[str] = Field(None, description="Job description")
    queue_name: str = Field("default", description="Queue name")
    priority: Priority = Field(Priority.MEDIUM, description="Job priority")
    timeout_seconds: Optional[int] = Field(None, description="Job timeout")
    retry_count: int = Field(3, description="Retry count")
    delay_seconds: int = Field(0, description="Delay before execution")


class JobSubmitRequest(BaseModel):
    """Request model for submitting a job."""

    job_definition_id: str = Field(..., description="Job definition ID")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Job input data")
    priority: Optional[Priority] = Field(None, description="Override priority")
    delay_seconds: Optional[int] = Field(None, description="Override delay")


class JobDefinitionResponse(BaseModel):
    """Response model for job definition operations."""

    id: str = Field(..., description="Job definition ID")
    name: str = Field(..., description="Job definition name")
    queue_name: str = Field(..., description="Queue name")
    priority: Priority = Field(..., description="Job priority")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class JobResponse(BaseModel):
    """Response model for job operations."""

    id: str = Field(..., description="Job ID")
    job_definition_id: str = Field(..., description="Job definition ID")
    queue_name: str = Field(..., description="Queue name")
    status: ExecutionStatus = Field(..., description="Job status")
    priority: Priority = Field(..., description="Job priority")
    submitted_at: datetime = Field(..., description="Submission timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    retry_count: int = Field(..., description="Current retry count")
    error_message: Optional[str] = Field(None, description="Error message")


async def get_job_queue_sdk() -> JobQueueSDK:
    """Get job queue SDK instance."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Job Queue SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    return "default-tenant"


@router.post("/definitions", response_model=OperationResponse)
async def create_job_definition(
    request: JobDefinitionCreateRequest,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new job definition."""
    try:
        job_def = JobDefinition(
            id=f"jobdef_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=request.name,
            description=request.description,
            queue_name=request.queue_name,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
            delay_seconds=request.delay_seconds,
        )

        job_def_id = await job_queue_sdk.create_job_definition(job_def)

        return OperationResponse(
            success=True,
            message="Job definition created successfully",
            data={"job_definition_id": job_def_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create job definition: {str(e)}"
        )


@router.get("/definitions", response_model=ListResponse)
async def list_job_definitions(
    page: int = 1,
    page_size: int = 50,
    queue_name: Optional[str] = None,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List job definitions."""
    try:
        job_defs = list(job_queue_sdk.job_definitions.values())

        # Apply filters
        if queue_name:
            job_defs = [jd for jd in job_defs if jd.queue_name == queue_name]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_job_defs = job_defs[start_idx:end_idx]

        # Convert to response format
        job_def_items = []
        for job_def in paginated_job_defs:
            job_def_items.append({
                "id": job_def.id,
                "name": job_def.name,
                "queue_name": job_def.queue_name,
                "priority": job_def.priority.value,
                "created_at": job_def.metadata.created_at.isoformat(),
                "updated_at": job_def.metadata.updated_at.isoformat(),
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(job_defs),
            total_pages=(len(job_defs) + page_size - 1) // page_size,
            has_next=end_idx < len(job_defs),
            has_previous=page > 1,
        )

        return ListResponse(
            items=job_def_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list job definitions: {str(e)}"
        )


@router.post("/jobs", response_model=OperationResponse)
async def submit_job(
    request: JobSubmitRequest,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Submit a job for execution."""
    try:
        job_id = await job_queue_sdk.submit_job(
            job_definition_id=request.job_definition_id,
            input_data=request.input_data,
            priority=request.priority,
            delay_seconds=request.delay_seconds
        )

        return OperationResponse(
            success=True,
            message="Job submitted successfully",
            data={"job_id": job_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.get("/jobs", response_model=ListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 50,
    queue_name: Optional[str] = None,
    status_filter: Optional[ExecutionStatus] = None,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List jobs."""
    try:
        jobs = list(job_queue_sdk.jobs.values())

        # Apply filters
        if queue_name:
            jobs = [job for job in jobs if job.queue_name == queue_name]
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]

        # Sort by submission time (most recent first)
        jobs.sort(key=lambda x: x.submitted_at, reverse=True)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs[start_idx:end_idx]

        # Convert to response format
        job_items = []
        for job in paginated_jobs:
            job_items.append({
                "id": job.id,
                "job_definition_id": job.job_definition_id,
                "queue_name": job.queue_name,
                "status": job.status.value,
                "priority": job.priority.value,
                "submitted_at": job.submitted_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "retry_count": job.retry_count,
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
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get job details by ID."""
    try:
        job = job_queue_sdk.jobs.get(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        return JobResponse(
            id=job.id,
            job_definition_id=job.job_definition_id,
            queue_name=job.queue_name,
            status=job.status,
            priority=job.priority,
            submitted_at=job.submitted_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            retry_count=job.retry_count,
            error_message=job.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )


@router.post("/jobs/{job_id}/cancel", response_model=OperationResponse)
async def cancel_job(
    job_id: str,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Cancel a job."""
    try:
        success = await job_queue_sdk.cancel_job(job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or cannot be cancelled"
            )

        return OperationResponse(
            success=True,
            message="Job cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.post("/jobs/{job_id}/retry", response_model=OperationResponse)
async def retry_job(
    job_id: str,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Retry a failed job."""
    try:
        job = job_queue_sdk.jobs.get(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        if job.status not in [ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job can only be retried if it has failed or was cancelled"
            )

        # Reset job status and resubmit
        job.status = ExecutionStatus.PENDING
        job.retry_count = 0
        job.error_message = None
        job.started_at = None
        job.completed_at = None

        await job_queue_sdk.process_job(job)

        return OperationResponse(
            success=True,
            message="Job retry initiated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}"
        )


@router.get("/queues", response_model=Dict[str, Any])
async def list_queues(
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List all job queues and their status."""
    try:
        queue_stats = {}

        # Get all unique queue names
        queue_names = set()
        for job_def in job_queue_sdk.job_definitions.values():
            queue_names.add(job_def.queue_name)
        for job in job_queue_sdk.jobs.values():
            queue_names.add(job.queue_name)

        # Calculate statistics for each queue
        for queue_name in queue_names:
            queue_jobs = [job for job in job_queue_sdk.jobs.values() if job.queue_name == queue_name]

            pending_count = len([j for j in queue_jobs if j.status == ExecutionStatus.PENDING])
            running_count = len([j for j in queue_jobs if j.status == ExecutionStatus.RUNNING])
            completed_count = len([j for j in queue_jobs if j.status == ExecutionStatus.COMPLETED])
            failed_count = len([j for j in queue_jobs if j.status == ExecutionStatus.FAILED])

            queue_stats[queue_name] = {
                "pending_jobs": pending_count,
                "running_jobs": running_count,
                "completed_jobs": completed_count,
                "failed_jobs": failed_count,
                "total_jobs": len(queue_jobs),
                "worker_count": len([w for w in job_queue_sdk.workers if w.queue_name == queue_name]),
            }

        return {
            "queues": queue_stats,
            "total_workers": len(job_queue_sdk.workers),
            "dead_letter_queue_size": len(job_queue_sdk.dead_letter_queue.queue),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list queues: {str(e)}"
        )


@router.get("/dead-letter-queue", response_model=ListResponse)
async def list_dead_letter_jobs(
    page: int = 1,
    page_size: int = 50,
    job_queue_sdk: JobQueueSDK = Depends(get_job_queue_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List jobs in the dead letter queue."""
    try:
        dlq_jobs = list(job_queue_sdk.dead_letter_queue.queue)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = dlq_jobs[start_idx:end_idx]

        # Convert to response format
        job_items = []
        for job in paginated_jobs:
            job_items.append({
                "id": job.id,
                "job_definition_id": job.job_definition_id,
                "queue_name": job.queue_name,
                "status": job.status.value,
                "submitted_at": job.submitted_at.isoformat(),
                "failed_at": job.completed_at.isoformat() if job.completed_at else None,
                "retry_count": job.retry_count,
                "error_message": job.error_message,
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(dlq_jobs),
            total_pages=(len(dlq_jobs) + page_size - 1) // page_size,
            has_next=end_idx < len(dlq_jobs),
            has_previous=page > 1,
        )

        return ListResponse(
            items=job_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dead letter queue: {str(e)}"
        )
