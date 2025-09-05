"""
Network Orchestration API Router - DRY Migration
REST API endpoints for network orchestration functionality using RouterFactory patterns.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Body, Depends, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)

from ..services.network_orchestrator import NetworkOrchestrationService

# === Request/Response Schemas ===


class ServiceProvisioningRequest(BaseModel):
    """Request model for customer service provisioning."""

    customer_id: UUID = Field(..., description="Customer ID")
    service_plan_id: str = Field(..., description="Service plan ID")
    service_address: str = Field(..., description="Service installation address")
    installation_options: dict[str, Any] | None = Field(
        None, description="Installation options"
    )
    scheduled_date: datetime | None = Field(
        None, description="Preferred installation date"
    )
    priority: str = Field("normal", description="Provisioning priority")


class ServiceModificationRequest(BaseModel):
    """Request model for service modification."""

    service_id: UUID = Field(..., description="Service ID to modify")
    new_bandwidth: str = Field(..., description="New bandwidth specification")
    effective_date: datetime | None = Field(
        None, description="When change becomes effective"
    )
    change_reason: str | None = Field(None, description="Reason for change")


class MaintenanceExecutionRequest(BaseModel):
    """Request model for maintenance execution."""

    maintenance_type: str = Field(..., description="Type of maintenance")
    target_devices: list[str] = Field(..., description="Target device IDs")
    execution_window: dict[str, datetime] = Field(
        ..., description="Execution time window"
    )
    rollback_plan: dict[str, Any] | None = Field(None, description="Rollback plan")


class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution."""

    workflow_name: str = Field(..., description="Workflow to execute")
    parameters: dict[str, Any] = Field(..., description="Workflow parameters")
    priority: str = Field("normal", description="Execution priority")
    auto_approve: bool = Field(False, description="Auto-approve workflow steps")


# === Main Orchestration Router ===

orchestration_router = RouterFactory.create_standard_router(
    prefix="/orchestration",
    tags=["network-orchestration"],
)


# === Service Provisioning Endpoints ===


@orchestration_router.post("/provision-service", response_model=dict[str, Any])
@standard_exception_handler
async def provision_customer_service(
    request: ServiceProvisioningRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Provision network service for a customer."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    result = await service.provision_customer_service(
        customer_id=request.customer_id,
        service_plan_id=request.service_plan_id,
        service_address=request.service_address,
        installation_options=request.installation_options or {},
        scheduled_date=request.scheduled_date,
        priority=request.priority,
        provisioned_by=deps.user_id,
    )

    return {
        "provisioning_id": result["provisioning_id"],
        "status": result["status"],
        "estimated_completion": result.get("estimated_completion"),
        "tracking_number": result.get("tracking_number"),
        "message": "Service provisioning initiated successfully",
    }


@orchestration_router.get(
    "/provisioning/{provisioning_id}", response_model=dict[str, Any]
)
@standard_exception_handler
async def get_provisioning_status(
    provisioning_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get status of a service provisioning request."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)
    return await service.get_provisioning_status(provisioning_id)


@orchestration_router.post(
    "/provisioning/{provisioning_id}/cancel", response_model=dict[str, Any]
)
@standard_exception_handler
async def cancel_provisioning(
    provisioning_id: UUID,
    cancellation_reason: str = Body(
        ..., embed=True, description="Reason for cancellation"
    ),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Cancel a service provisioning request."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    result = await service.cancel_provisioning(
        provisioning_id, cancellation_reason, deps.user_id
    )

    return {
        "provisioning_id": provisioning_id,
        "status": "cancelled",
        "message": result.get("message", "Provisioning cancelled successfully"),
    }


# === Service Modification Endpoints ===


@orchestration_router.post("/modify-service", response_model=dict[str, Any])
@standard_exception_handler
async def modify_customer_service(
    request: ServiceModificationRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Modify an existing customer service."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    result = await service.modify_customer_service(
        service_id=request.service_id,
        new_bandwidth=request.new_bandwidth,
        effective_date=request.effective_date,
        change_reason=request.change_reason,
        modified_by=deps.user_id,
    )

    return {
        "modification_id": result["modification_id"],
        "status": result["status"],
        "effective_date": result.get("effective_date"),
        "message": "Service modification initiated successfully",
    }


@orchestration_router.get("/modifications", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_service_modifications(
    service_id: UUID | None = Query(None, description="Filter by service ID"),
    status: str | None = Query(None, description="Filter by status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List service modifications with optional filtering."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    return await service.list_service_modifications(
        service_id=service_id,
        status=status,
        offset=deps.pagination.offset,
        limit=deps.pagination.size,
    )


# === Maintenance Orchestration ===


@orchestration_router.post("/execute-maintenance", response_model=dict[str, Any])
@standard_exception_handler
async def execute_maintenance(
    request: MaintenanceExecutionRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Execute scheduled maintenance operations."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    result = await service.execute_maintenance(
        maintenance_type=request.maintenance_type,
        target_devices=request.target_devices,
        execution_window=request.execution_window,
        rollback_plan=request.rollback_plan,
        executed_by=deps.user_id,
    )

    return {
        "maintenance_id": result["maintenance_id"],
        "status": result["status"],
        "execution_start": result.get("execution_start"),
        "estimated_duration": result.get("estimated_duration"),
        "message": "Maintenance execution initiated successfully",
    }


@orchestration_router.get(
    "/maintenance/{maintenance_id}", response_model=dict[str, Any]
)
@standard_exception_handler
async def get_maintenance_status(
    maintenance_id: UUID,
    include_logs: bool = Query(False, description="Include execution logs"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get status of a maintenance execution."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)
    return await service.get_maintenance_status(maintenance_id, include_logs)


# === Workflow Execution ===


@orchestration_router.post("/execute-workflow", response_model=dict[str, Any])
@standard_exception_handler
async def execute_workflow(
    request: WorkflowExecutionRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Execute a predefined network orchestration workflow."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    result = await service.execute_workflow(
        workflow_name=request.workflow_name,
        parameters=request.parameters,
        priority=request.priority,
        auto_approve=request.auto_approve,
        executed_by=deps.user_id,
    )

    return {
        "workflow_execution_id": result["execution_id"],
        "status": result["status"],
        "current_step": result.get("current_step"),
        "estimated_completion": result.get("estimated_completion"),
        "message": "Workflow execution started successfully",
    }


@orchestration_router.get("/workflows", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_available_workflows(
    category: str | None = Query(None, description="Filter by workflow category"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """List available orchestration workflows."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)
    return await service.get_available_workflows(category)


@orchestration_router.get("/workflow-executions", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_workflow_executions(
    workflow_name: str | None = Query(None, description="Filter by workflow name"),
    status: str | None = Query(None, description="Filter by execution status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List workflow executions with filtering."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)

    return await service.list_workflow_executions(
        workflow_name=workflow_name,
        status=status,
        offset=deps.pagination.offset,
        limit=deps.pagination.size,
    )


@orchestration_router.get(
    "/workflow-executions/{execution_id}", response_model=dict[str, Any]
)
@standard_exception_handler
async def get_workflow_execution_status(
    execution_id: UUID,
    include_step_details: bool = Query(
        False, description="Include detailed step information"
    ),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get detailed status of a workflow execution."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)
    return await service.get_workflow_execution_status(
        execution_id, include_step_details
    )


# === Orchestration Analytics ===


@orchestration_router.get("/analytics/summary", response_model=dict[str, Any])
@standard_exception_handler
async def get_orchestration_analytics(
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    include_trends: bool = Query(True, description="Include trend analysis"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get orchestration analytics and metrics."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)
    return await service.get_orchestration_analytics(period_days, include_trends)


@orchestration_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def get_orchestration_health(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get orchestration service health status."""
    service = NetworkOrchestrationService(deps.db, deps.tenant_id)
    return await service.health_check()


# Export the router
__all__ = ["orchestration_router"]
