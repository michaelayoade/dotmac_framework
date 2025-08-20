"""
Saga API endpoints for saga pattern management and execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..contracts.common_schemas import (
    ExecutionStatus,
    OperationResponse,
    ListResponse,
    PaginationInfo,
)
from ..sdks.saga import SagaSDK, SagaDefinition

router = APIRouter(prefix="/sagas", tags=["sagas"])


class SagaCreateRequest(BaseModel):
    """Request model for creating a saga."""

    name: str = Field(..., description="Saga name")
    description: Optional[str] = Field(None, description="Saga description")
    steps: List[Dict[str, Any]] = Field(..., description="Saga step definitions")
    timeout_seconds: Optional[int] = Field(None, description="Saga timeout")


class SagaResponse(BaseModel):
    """Response model for saga operations."""

    id: str = Field(..., description="Saga ID")
    name: str = Field(..., description="Saga name")
    step_count: int = Field(..., description="Number of steps")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SagaExecutionResponse(BaseModel):
    """Response model for saga execution."""

    execution_id: str = Field(..., description="Execution ID")
    saga_id: str = Field(..., description="Saga ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    current_step: int = Field(..., description="Current step index")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output data")
    step_results: List[Dict[str, Any]] = Field(default_factory=list, description="Step execution results")
    compensation_executed: bool = Field(..., description="Whether compensation was executed")


async def get_saga_sdk() -> SagaSDK:
    """Get saga SDK instance."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Saga SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    return "default-tenant"


@router.post("/", response_model=OperationResponse)
async def create_saga(
    request: SagaCreateRequest,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new saga definition."""
    try:
        saga = SagaDefinition(
            id=f"saga_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=request.name,
            description=request.description,
            steps=request.steps,
            timeout_seconds=request.timeout_seconds,
        )

        saga_id = await saga_sdk.create_saga(saga)

        return OperationResponse(
            success=True,
            message="Saga created successfully",
            data={"saga_id": saga_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create saga: {str(e)}"
        )


@router.get("/", response_model=ListResponse)
async def list_sagas(
    page: int = 1,
    page_size: int = 50,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List saga definitions."""
    try:
        sagas = list(saga_sdk.sagas.values())

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_sagas = sagas[start_idx:end_idx]

        # Convert to response format
        saga_items = []
        for saga in paginated_sagas:
            saga_items.append({
                "id": saga.id,
                "name": saga.name,
                "step_count": len(saga.steps),
                "created_at": saga.metadata.created_at.isoformat(),
                "updated_at": saga.metadata.updated_at.isoformat(),
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(sagas),
            total_pages=(len(sagas) + page_size - 1) // page_size,
            has_next=end_idx < len(sagas),
            has_previous=page > 1,
        )

        return ListResponse(
            items=saga_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sagas: {str(e)}"
        )


@router.get("/{saga_id}", response_model=SagaResponse)
async def get_saga(
    saga_id: str,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get saga definition by ID."""
    try:
        saga = saga_sdk.sagas.get(saga_id)
        if not saga:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saga not found"
            )

        return SagaResponse(
            id=saga.id,
            name=saga.name,
            step_count=len(saga.steps),
            created_at=saga.metadata.created_at,
            updated_at=saga.metadata.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saga: {str(e)}"
        )


@router.post("/{saga_id}/execute", response_model=OperationResponse)
async def execute_saga(
    saga_id: str,
    input_data: Dict[str, Any] = None,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Execute a saga."""
    try:
        if input_data is None:
            input_data = {}

        execution_id = await saga_sdk.execute_saga(
            saga_id=saga_id,
            input_data=input_data
        )

        return OperationResponse(
            success=True,
            message="Saga execution started",
            data={"execution_id": execution_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to execute saga: {str(e)}"
        )


@router.get("/{saga_id}/executions", response_model=ListResponse)
async def list_saga_executions(
    saga_id: str,
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[ExecutionStatus] = None,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List saga executions."""
    try:
        executions = [
            exec for exec in saga_sdk.executions.values()
            if exec.saga_id == saga_id
        ]

        # Apply status filter
        if status_filter:
            executions = [exec for exec in executions if exec.status == status_filter]

        # Sort by start time (most recent first)
        executions.sort(key=lambda x: x.started_at, reverse=True)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_executions = executions[start_idx:end_idx]

        # Convert to response format
        execution_items = []
        for execution in paginated_executions:
            execution_items.append({
                "execution_id": execution.execution_id,
                "saga_id": execution.saga_id,
                "status": execution.status.value,
                "current_step": execution.current_step,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "compensation_executed": execution.compensation_executed,
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(executions),
            total_pages=(len(executions) + page_size - 1) // page_size,
            has_next=end_idx < len(executions),
            has_previous=page > 1,
        )

        return ListResponse(
            items=execution_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list executions: {str(e)}"
        )


@router.get("/executions/{execution_id}", response_model=SagaExecutionResponse)
async def get_saga_execution(
    execution_id: str,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get saga execution by ID."""
    try:
        execution = saga_sdk.executions.get(execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        return SagaExecutionResponse(
            execution_id=execution.execution_id,
            saga_id=execution.saga_id,
            status=execution.status,
            current_step=execution.current_step,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            input_data=execution.input_data,
            output_data=execution.output_data,
            step_results=execution.step_results,
            compensation_executed=execution.compensation_executed,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}"
        )


@router.post("/executions/{execution_id}/compensate", response_model=OperationResponse)
async def compensate_saga_execution(
    execution_id: str,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Manually trigger compensation for a saga execution."""
    try:
        success = await saga_sdk.compensate_saga(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or compensation not applicable"
            )

        return OperationResponse(
            success=True,
            message="Saga compensation initiated"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compensate saga: {str(e)}"
        )


@router.post("/executions/{execution_id}/cancel", response_model=OperationResponse)
async def cancel_saga_execution(
    execution_id: str,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Cancel a saga execution."""
    try:
        success = await saga_sdk.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be cancelled"
            )

        return OperationResponse(
            success=True,
            message="Saga execution cancelled"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.delete("/{saga_id}", response_model=OperationResponse)
async def delete_saga(
    saga_id: str,
    saga_sdk: SagaSDK = Depends(get_saga_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete a saga definition."""
    try:
        if saga_id not in saga_sdk.sagas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saga not found"
            )

        # Check for running executions
        running_executions = [
            exec for exec in saga_sdk.executions.values()
            if exec.saga_id == saga_id and exec.status == ExecutionStatus.RUNNING
        ]

        if running_executions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete saga with running executions"
            )

        del saga_sdk.sagas[saga_id]

        return OperationResponse(
            success=True,
            message="Saga deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saga: {str(e)}"
        )
