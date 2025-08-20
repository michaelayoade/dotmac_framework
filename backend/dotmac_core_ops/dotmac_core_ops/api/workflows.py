"""
Workflow API endpoints for workflow management and execution.
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
from ..contracts.workflow_contract import (
    WorkflowExecutionResponse,
)
from ..sdks.workflow import WorkflowSDK, WorkflowDefinition

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowCreateRequest(BaseModel):
    """Request model for creating a workflow."""

    name: str = Field(..., description="Workflow name")
    version: str = Field("1.0", description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")
    definition: Dict[str, Any] = Field(..., description="Workflow definition")


class WorkflowExecuteRequest(BaseModel):
    """Request model for executing a workflow."""

    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""

    id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    version: str = Field(..., description="Workflow version")
    status: str = Field(..., description="Workflow status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""

    execution_id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output data")


# Dependency injection placeholder
async def get_workflow_sdk() -> WorkflowSDK:
    """Get workflow SDK instance."""
    # This would be injected by the runtime
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Workflow SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    # This would be extracted from headers/auth
    return "default-tenant"


@router.post("/", response_model=OperationResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new workflow definition."""
    try:
        # Convert request to workflow definition
        workflow_def = WorkflowDefinition(
            id=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=request.name,
            version=request.version,
            description=request.description,
            **request.definition
        )

        workflow_id = await workflow_sdk.create_workflow(workflow_def)

        return OperationResponse(
            success=True,
            message="Workflow created successfully",
            data={"workflow_id": workflow_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.get("/", response_model=ListResponse)
async def list_workflows(
    page: int = 1,
    page_size: int = 50,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List workflow definitions."""
    try:
        # Get workflows (this would be implemented in the SDK)
        workflows = list(workflow_sdk.workflows.values())

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_workflows = workflows[start_idx:end_idx]

        # Convert to response format
        workflow_items = []
        for workflow in paginated_workflows:
            workflow_items.append({
                "id": workflow.id,
                "name": workflow.name,
                "version": workflow.version,
                "status": workflow.status.value,
                "created_at": workflow.metadata.created_at.isoformat(),
                "updated_at": workflow.metadata.updated_at.isoformat(),
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(workflows),
            total_pages=(len(workflows) + page_size - 1) // page_size,
            has_next=end_idx < len(workflows),
            has_previous=page > 1,
        )

        return ListResponse(
            items=workflow_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get workflow definition by ID."""
    try:
        workflow = workflow_sdk.workflows.get(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            version=workflow.version,
            status=workflow.status.value,
            created_at=workflow.metadata.created_at,
            updated_at=workflow.metadata.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}"
        )


@router.post("/{workflow_id}/execute", response_model=OperationResponse)
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Execute a workflow."""
    try:
        execution_id = await workflow_sdk.execute_workflow(
            workflow_id=workflow_id,
            input_data=request.input_data,
            context=None  # Would convert from request.context
        )

        return OperationResponse(
            success=True,
            message="Workflow execution started",
            data={"execution_id": execution_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.get("/{workflow_id}/executions", response_model=ListResponse)
async def list_workflow_executions(
    workflow_id: str,
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[ExecutionStatus] = None,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List workflow executions."""
    try:
        # Get executions for workflow
        executions = [
            exec for exec in workflow_sdk.executions.values()
            if exec.workflow_id == workflow_id
        ]

        # Apply status filter
        if status_filter:
            executions = [exec for exec in executions if exec.status == status_filter]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_executions = executions[start_idx:end_idx]

        # Convert to response format
        execution_items = []
        for execution in paginated_executions:
            execution_items.append({
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
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


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: str,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get workflow execution by ID."""
    try:
        execution = await workflow_sdk.get_execution(execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        return WorkflowExecutionResponse(
            execution_id=execution.execution_id,
            workflow_id=execution.workflow_id,
            status=execution.status,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            input_data=execution.input_data,
            output_data=execution.output_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}"
        )


@router.post("/executions/{execution_id}/cancel", response_model=OperationResponse)
async def cancel_workflow_execution(
    execution_id: str,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Cancel a workflow execution."""
    try:
        success = await workflow_sdk.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be cancelled"
            )

        return OperationResponse(
            success=True,
            message="Workflow execution cancelled"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.delete("/{workflow_id}", response_model=OperationResponse)
async def delete_workflow(
    workflow_id: str,
    workflow_sdk: WorkflowSDK = Depends(get_workflow_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete a workflow definition."""
    try:
        if workflow_id not in workflow_sdk.workflows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Check for running executions
        running_executions = [
            exec for exec in workflow_sdk.executions.values()
            if exec.workflow_id == workflow_id and exec.status == ExecutionStatus.RUNNING
        ]

        if running_executions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete workflow with running executions"
            )

        del workflow_sdk.workflows[workflow_id]

        return OperationResponse(
            success=True,
            message="Workflow deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {str(e)}"
        )
