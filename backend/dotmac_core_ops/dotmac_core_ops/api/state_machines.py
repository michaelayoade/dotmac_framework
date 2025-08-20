"""
State Machine API endpoints for state machine management and execution.
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
from ..sdks.state_machine import StateMachineSDK, StateMachineDefinition

router = APIRouter(prefix="/state-machines", tags=["state-machines"])


class StateMachineCreateRequest(BaseModel):
    """Request model for creating a state machine."""

    name: str = Field(..., description="State machine name")
    description: Optional[str] = Field(None, description="State machine description")
    initial_state: str = Field(..., description="Initial state")
    states: List[Dict[str, Any]] = Field(..., description="State definitions")
    transitions: List[Dict[str, Any]] = Field(..., description="Transition definitions")


class StateMachineResponse(BaseModel):
    """Response model for state machine operations."""

    id: str = Field(..., description="State machine ID")
    name: str = Field(..., description="State machine name")
    initial_state: str = Field(..., description="Initial state")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StateMachineExecutionResponse(BaseModel):
    """Response model for state machine execution."""

    execution_id: str = Field(..., description="Execution ID")
    state_machine_id: str = Field(..., description="State machine ID")
    current_state: str = Field(..., description="Current state")
    status: ExecutionStatus = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Context data")
    state_history: List[Dict[str, Any]] = Field(default_factory=list, description="State transition history")


async def get_state_machine_sdk() -> StateMachineSDK:
    """Get state machine SDK instance."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="State Machine SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    return "default-tenant"


@router.post("/", response_model=OperationResponse)
async def create_state_machine(
    request: StateMachineCreateRequest,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new state machine."""
    try:
        state_machine = StateMachineDefinition(
            id=f"sm_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=request.name,
            description=request.description,
            initial_state=request.initial_state,
            states=request.states,
            transitions=request.transitions,
        )

        sm_id = await state_machine_sdk.create_state_machine(state_machine)

        return OperationResponse(
            success=True,
            message="State machine created successfully",
            data={"state_machine_id": sm_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create state machine: {str(e)}"
        )


@router.get("/", response_model=ListResponse)
async def list_state_machines(
    page: int = 1,
    page_size: int = 50,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List state machines."""
    try:
        state_machines = list(state_machine_sdk.state_machines.values())

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_sms = state_machines[start_idx:end_idx]

        # Convert to response format
        sm_items = []
        for sm in paginated_sms:
            sm_items.append({
                "id": sm.id,
                "name": sm.name,
                "initial_state": sm.initial_state,
                "created_at": sm.metadata.created_at.isoformat(),
                "updated_at": sm.metadata.updated_at.isoformat(),
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(state_machines),
            total_pages=(len(state_machines) + page_size - 1) // page_size,
            has_next=end_idx < len(state_machines),
            has_previous=page > 1,
        )

        return ListResponse(
            items=sm_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list state machines: {str(e)}"
        )


@router.get("/{state_machine_id}", response_model=StateMachineResponse)
async def get_state_machine(
    state_machine_id: str,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get state machine by ID."""
    try:
        sm = state_machine_sdk.state_machines.get(state_machine_id)
        if not sm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State machine not found"
            )

        return StateMachineResponse(
            id=sm.id,
            name=sm.name,
            initial_state=sm.initial_state,
            created_at=sm.metadata.created_at,
            updated_at=sm.metadata.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get state machine: {str(e)}"
        )


@router.post("/{state_machine_id}/execute", response_model=OperationResponse)
async def execute_state_machine(
    state_machine_id: str,
    context_data: Dict[str, Any] = None,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Execute a state machine."""
    try:
        if context_data is None:
            context_data = {}

        execution_id = await state_machine_sdk.execute_state_machine(
            state_machine_id=state_machine_id,
            context_data=context_data
        )

        return OperationResponse(
            success=True,
            message="State machine execution started",
            data={"execution_id": execution_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to execute state machine: {str(e)}"
        )


@router.get("/{state_machine_id}/executions", response_model=ListResponse)
async def list_state_machine_executions(
    state_machine_id: str,
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[ExecutionStatus] = None,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List state machine executions."""
    try:
        executions = [
            exec for exec in state_machine_sdk.executions.values()
            if exec.state_machine_id == state_machine_id
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
                "state_machine_id": execution.state_machine_id,
                "current_state": execution.current_state,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat(),
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


@router.get("/executions/{execution_id}", response_model=StateMachineExecutionResponse)
async def get_state_machine_execution(
    execution_id: str,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get state machine execution by ID."""
    try:
        execution = state_machine_sdk.executions.get(execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        return StateMachineExecutionResponse(
            execution_id=execution.execution_id,
            state_machine_id=execution.state_machine_id,
            current_state=execution.current_state,
            status=execution.status,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            context_data=execution.context_data,
            state_history=execution.state_history,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}"
        )


@router.post("/executions/{execution_id}/event", response_model=OperationResponse)
async def send_event_to_execution(
    execution_id: str,
    event_type: str,
    event_data: Dict[str, Any] = None,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Send an event to a state machine execution."""
    try:
        if event_data is None:
            event_data = {}

        await state_machine_sdk.send_event(execution_id, event_type, event_data)

        return OperationResponse(
            success=True,
            message="Event sent successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send event: {str(e)}"
        )


@router.post("/executions/{execution_id}/cancel", response_model=OperationResponse)
async def cancel_state_machine_execution(
    execution_id: str,
    state_machine_sdk: StateMachineSDK = Depends(get_state_machine_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Cancel a state machine execution."""
    try:
        success = await state_machine_sdk.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be cancelled"
            )

        return OperationResponse(
            success=True,
            message="State machine execution cancelled"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}"
        )
