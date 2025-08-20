"""
Task API endpoints for task management and execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..contracts.common_schemas import (
    ExecutionStatus,
    Priority,
    OperationResponse,
    ListResponse,
    PaginationInfo,
)
from ..sdks.task import TaskSDK, TaskDefinition

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    """Request model for creating a task."""

    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    priority: Priority = Field(Priority.MEDIUM, description="Task priority")
    timeout_seconds: Optional[int] = Field(None, description="Task timeout")
    retry_count: int = Field(3, description="Retry count")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data")


class TaskResponse(BaseModel):
    """Response model for task operations."""

    id: str = Field(..., description="Task ID")
    name: str = Field(..., description="Task name")
    status: ExecutionStatus = Field(..., description="Task status")
    priority: Priority = Field(..., description="Task priority")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class TaskExecutionResponse(BaseModel):
    """Response model for task execution details."""

    id: str = Field(..., description="Task ID")
    name: str = Field(..., description="Task name")
    status: ExecutionStatus = Field(..., description="Task status")
    priority: Priority = Field(..., description="Task priority")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output data")
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(..., description="Current retry count")
    max_retries: int = Field(..., description="Maximum retries")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


async def get_task_sdk() -> TaskSDK:
    """Get task SDK instance."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Task SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    return "default-tenant"


@router.post("/", response_model=OperationResponse)
async def create_task(
    request: TaskCreateRequest,
    task_sdk: TaskSDK = Depends(get_task_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create and submit a new task."""
    try:
        task_def = TaskDefinition(
            id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=request.name,
            description=request.description,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            retry_count=request.retry_count,
            dependencies=request.dependencies,
            input_data=request.input_data,
        )

        task_id = await task_sdk.create_task(task_def)

        return OperationResponse(
            success=True,
            message="Task created and submitted successfully",
            data={"task_id": task_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/", response_model=ListResponse)
async def list_tasks(
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[ExecutionStatus] = None,
    priority_filter: Optional[Priority] = None,
    task_sdk: TaskSDK = Depends(get_task_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List tasks with optional filtering."""
    try:
        # Get all tasks
        tasks = list(task_sdk.tasks.values())

        # Apply filters
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]
        if priority_filter:
            tasks = [task for task in tasks if task.priority == priority_filter]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = tasks[start_idx:end_idx]

        # Convert to response format
        task_items = []
        for task in paginated_tasks:
            task_items.append({
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "priority": task.priority.value,
                "created_at": task.metadata.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(tasks),
            total_pages=(len(tasks) + page_size - 1) // page_size,
            has_next=end_idx < len(tasks),
            has_previous=page > 1,
        )

        return ListResponse(
            items=task_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskExecutionResponse)
async def get_task(
    task_id: str,
    task_sdk: TaskSDK = Depends(get_task_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get task details by ID."""
    try:
        task = task_sdk.tasks.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        return TaskExecutionResponse(
            id=task.id,
            name=task.name,
            status=task.status,
            priority=task.priority,
            input_data=task.input_data,
            output_data=task.output_data,
            error_message=task.error_message,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            dependencies=task.dependencies,
            created_at=task.metadata.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task: {str(e)}"
        )


@router.post("/{task_id}/cancel", response_model=OperationResponse)
async def cancel_task(
    task_id: str,
    task_sdk: TaskSDK = Depends(get_task_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Cancel a task."""
    try:
        success = await task_sdk.cancel_task(task_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or cannot be cancelled"
            )

        return OperationResponse(
            success=True,
            message="Task cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.post("/{task_id}/retry", response_model=OperationResponse)
async def retry_task(
    task_id: str,
    task_sdk: TaskSDK = Depends(get_task_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Retry a failed task."""
    try:
        task = task_sdk.tasks.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.status not in [ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task can only be retried if it has failed or was cancelled"
            )

        # Reset task status and resubmit
        task.status = ExecutionStatus.PENDING
        task.retry_count = 0
        task.error_message = None
        task.started_at = None
        task.completed_at = None

        await task_sdk.submit_task(task)

        return OperationResponse(
            success=True,
            message="Task retry initiated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry task: {str(e)}"
        )


@router.get("/queue/status", response_model=Dict[str, Any])
async def get_queue_status(
    task_sdk: TaskSDK = Depends(get_task_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get task queue status and statistics."""
    try:
        # Get queue statistics
        pending_count = len([t for t in task_sdk.tasks.values() if t.status == ExecutionStatus.PENDING])
        running_count = len([t for t in task_sdk.tasks.values() if t.status == ExecutionStatus.RUNNING])
        completed_count = len([t for t in task_sdk.tasks.values() if t.status == ExecutionStatus.COMPLETED])
        failed_count = len([t for t in task_sdk.tasks.values() if t.status == ExecutionStatus.FAILED])

        return {
            "queue_size": len(task_sdk.task_queue.queue),
            "pending_tasks": pending_count,
            "running_tasks": running_count,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "total_tasks": len(task_sdk.tasks),
            "worker_count": len(task_sdk.workers),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )
