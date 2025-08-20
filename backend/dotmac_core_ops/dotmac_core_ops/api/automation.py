"""
Automation API endpoints for rule management and execution.
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
from ..sdks.automation import AutomationSDK, AutomationRule

router = APIRouter(prefix="/automation", tags=["automation"])


class AutomationRuleCreateRequest(BaseModel):
    """Request model for creating an automation rule."""

    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    enabled: bool = Field(True, description="Rule enabled status")
    triggers: List[Dict[str, Any]] = Field(..., description="Rule triggers")
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Rule conditions")
    actions: List[Dict[str, Any]] = Field(..., description="Rule actions")


class AutomationRuleResponse(BaseModel):
    """Response model for automation rule operations."""

    id: str = Field(..., description="Rule ID")
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    enabled: bool = Field(..., description="Rule enabled status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    execution_count: int = Field(..., description="Number of executions")
    last_execution: Optional[datetime] = Field(None, description="Last execution timestamp")


class AutomationExecutionResponse(BaseModel):
    """Response model for automation execution details."""

    execution_id: str = Field(..., description="Execution ID")
    rule_id: str = Field(..., description="Rule ID")
    status: ExecutionStatus = Field(..., description="Execution status")
    trigger_event: Dict[str, Any] = Field(..., description="Trigger event data")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    actions_executed: List[Dict[str, Any]] = Field(default_factory=list, description="Executed actions")
    error_message: Optional[str] = Field(None, description="Error message")


async def get_automation_sdk() -> AutomationSDK:
    """Get automation SDK instance."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Automation SDK not available"
    )


async def get_tenant_id() -> str:
    """Get tenant ID from request context."""
    return "default-tenant"


@router.post("/rules", response_model=OperationResponse)
async def create_automation_rule(
    request: AutomationRuleCreateRequest,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new automation rule."""
    try:
        rule = AutomationRule(
            id=f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=request.name,
            description=request.description,
            enabled=request.enabled,
            triggers=request.triggers,
            conditions=request.conditions,
            actions=request.actions,
        )

        rule_id = await automation_sdk.create_rule(rule)

        return OperationResponse(
            success=True,
            message="Automation rule created successfully",
            data={"rule_id": rule_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create automation rule: {str(e)}"
        )


@router.get("/rules", response_model=ListResponse)
async def list_automation_rules(
    page: int = 1,
    page_size: int = 50,
    enabled_only: bool = False,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List automation rules."""
    try:
        rules = list(automation_sdk.rules.values())

        # Apply filters
        if enabled_only:
            rules = [rule for rule in rules if rule.enabled]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_rules = rules[start_idx:end_idx]

        # Convert to response format
        rule_items = []
        for rule in paginated_rules:
            rule_items.append({
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "created_at": rule.metadata.created_at.isoformat(),
                "updated_at": rule.metadata.updated_at.isoformat(),
                "execution_count": rule.execution_count,
                "last_execution": rule.last_execution.isoformat() if rule.last_execution else None,
            })

        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=len(rules),
            total_pages=(len(rules) + page_size - 1) // page_size,
            has_next=end_idx < len(rules),
            has_previous=page > 1,
        )

        return ListResponse(
            items=rule_items,
            pagination=pagination
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list automation rules: {str(e)}"
        )


@router.get("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def get_automation_rule(
    rule_id: str,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get automation rule by ID."""
    try:
        rule = automation_sdk.rules.get(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation rule not found"
            )

        return AutomationRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            enabled=rule.enabled,
            created_at=rule.metadata.created_at,
            updated_at=rule.metadata.updated_at,
            execution_count=rule.execution_count,
            last_execution=rule.last_execution,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get automation rule: {str(e)}"
        )


@router.put("/rules/{rule_id}", response_model=OperationResponse)
async def update_automation_rule(
    rule_id: str,
    request: AutomationRuleCreateRequest,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Update an automation rule."""
    try:
        updated_rule = AutomationRule(
            id=rule_id,
            name=request.name,
            description=request.description,
            enabled=request.enabled,
            triggers=request.triggers,
            conditions=request.conditions,
            actions=request.actions,
        )

        success = await automation_sdk.update_rule(rule_id, updated_rule)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation rule not found"
            )

        return OperationResponse(
            success=True,
            message="Automation rule updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update automation rule: {str(e)}"
        )


@router.post("/rules/{rule_id}/enable", response_model=OperationResponse)
async def enable_automation_rule(
    rule_id: str,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Enable an automation rule."""
    try:
        rule = automation_sdk.rules.get(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation rule not found"
            )

        rule.enabled = True
        rule.metadata.updated_at = datetime.now()

        return OperationResponse(
            success=True,
            message="Automation rule enabled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable automation rule: {str(e)}"
        )


@router.post("/rules/{rule_id}/disable", response_model=OperationResponse)
async def disable_automation_rule(
    rule_id: str,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Disable an automation rule."""
    try:
        rule = automation_sdk.rules.get(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation rule not found"
            )

        rule.enabled = False
        rule.metadata.updated_at = datetime.now()

        return OperationResponse(
            success=True,
            message="Automation rule disabled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable automation rule: {str(e)}"
        )


@router.delete("/rules/{rule_id}", response_model=OperationResponse)
async def delete_automation_rule(
    rule_id: str,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete an automation rule."""
    try:
        success = await automation_sdk.delete_rule(rule_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation rule not found"
            )

        return OperationResponse(
            success=True,
            message="Automation rule deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete automation rule: {str(e)}"
        )


@router.post("/trigger", response_model=OperationResponse)
async def trigger_automation(
    event_type: str,
    event_data: Dict[str, Any],
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """Manually trigger automation rules for an event."""
    try:
        await automation_sdk.trigger_event(event_type, event_data)

        return OperationResponse(
            success=True,
            message="Automation trigger processed successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to trigger automation: {str(e)}"
        )


@router.get("/executions", response_model=ListResponse)
async def list_automation_executions(
    page: int = 1,
    page_size: int = 50,
    rule_id: Optional[str] = None,
    status_filter: Optional[ExecutionStatus] = None,
    automation_sdk: AutomationSDK = Depends(get_automation_sdk),
    tenant_id: str = Depends(get_tenant_id)
):
    """List automation executions."""
    try:
        executions = list(automation_sdk.executions.values())

        # Apply filters
        if rule_id:
            executions = [exec for exec in executions if exec.rule_id == rule_id]
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
                "rule_id": execution.rule_id,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "error_message": execution.error_message,
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
            detail=f"Failed to list automation executions: {str(e)}"
        )
