"""
REST API for workflow migration management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
)
from pydantic import BaseModel, Field

from ..migration.workflow_migration import (
    ChangeType,
    MigrationExecution,
    MigrationStatus,
    WorkflowChange,
    WorkflowMigrationManager,
)
from ..security.auth import get_current_tenant, require_permissions

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/migration", tags=["migration"])


# Request/Response Models
class CreateMigrationPlanRequest(BaseModel):
    """Request to create a migration plan."""
    workflow_id: str = Field(..., description="Workflow ID to migrate")
    from_version: str = Field(..., description="Source version")
    to_version: str = Field(..., description="Target version")
    changes: List[Dict[str, Any]] = Field(..., description="List of changes")
    migration_strategy: str = Field(default="gradual", description="Migration strategy")
    description: Optional[str] = Field(None, description="Migration description")


class ExecuteMigrationRequest(BaseModel):
    """Request to execute a migration."""
    dry_run: bool = Field(default=False, description="Execute as dry run")
    force: bool = Field(default=False, description="Force execution even with warnings")


class RollbackMigrationRequest(BaseModel):
    """Request to rollback a migration."""
    reason: str = Field(..., description="Reason for rollback")
    force: bool = Field(default=False, description="Force rollback even with warnings")


class MigrationPlanResponse(BaseModel):
    """Migration plan response."""
    migration_id: str
    workflow_id: str
    from_version: str
    to_version: str
    tenant_id: str
    changes_count: int
    breaking_changes_count: int
    migration_strategy: str
    rollback_strategy: str
    pre_checks_count: int
    post_checks_count: int
    created_at: datetime
    created_by: Optional[str] = None


class MigrationExecutionResponse(BaseModel):
    """Migration execution response."""
    execution_id: str
    migration_id: str
    status: MigrationStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    affected_runs_count: int
    has_rollback_point: bool
    error_message: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None


class MigrationListResponse(BaseModel):
    """Migration list response."""
    executions: List[MigrationExecutionResponse]
    total_count: int
    page: int
    page_size: int


# Global migration manager (would be dependency injected in production)
migration_manager = None


def get_migration_manager() -> WorkflowMigrationManager:
    """Get migration manager dependency."""
    global migration_manager
    if migration_manager is None:
        # In production, this would be properly injected
        from ..sdks.event_bus import EventBusSDK
        migration_manager = WorkflowMigrationManager(EventBusSDK())
    return migration_manager


@router.post("/plans", response_model=MigrationPlanResponse)
async def create_migration_plan(
    request: CreateMigrationPlanRequest,
    tenant_id: str = Depends(get_current_tenant),
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager),
    _: None = Depends(require_permissions(["workflow:migration:create"]))
):
    """Create a migration plan for workflow definition changes."""
    try:
        # Parse changes
        changes = []
        for change_data in request.changes:
            change = WorkflowChange(
                change_type=ChangeType(change_data["change_type"]),
                path=change_data["path"],
                old_value=change_data.get("old_value"),
                new_value=change_data.get("new_value"),
                description=change_data["description"],
                breaking=change_data.get("breaking", False),
                rollback_action=change_data.get("rollback_action")
            )
            changes.append(change)

        # Create migration plan
        plan = await migration_mgr.create_migration_plan(
            workflow_id=request.workflow_id,
            from_version=request.from_version,
            to_version=request.to_version,
            tenant_id=tenant_id,
            changes=changes,
            migration_strategy=request.migration_strategy,
            created_by="api_user"
        )

        return MigrationPlanResponse(
            migration_id=plan.migration_id,
            workflow_id=plan.workflow_id,
            from_version=plan.from_version,
            to_version=plan.to_version,
            tenant_id=plan.tenant_id,
            changes_count=len(plan.changes),
            breaking_changes_count=len([c for c in plan.changes if c.breaking]),
            migration_strategy=plan.migration_strategy,
            rollback_strategy=plan.rollback_strategy,
            pre_checks_count=len(plan.pre_migration_checks),
            post_checks_count=len(plan.post_migration_checks),
            created_at=plan.created_at,
            created_by=plan.created_by
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create migration plan", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create migration plan: {str(e)}")


@router.get("/plans/{migration_id}")
async def get_migration_plan(
    migration_id: str = Path(..., description="Migration plan ID"),
    tenant_id: str = Depends(get_current_tenant),
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager),
    _: None = Depends(require_permissions(["workflow:migration:read"]))
):
    """Get migration plan details."""
    if migration_id not in migration_mgr.migration_plans:
        raise HTTPException(status_code=404, detail="Migration plan not found")

    plan = migration_mgr.migration_plans[migration_id]

    # Check tenant access
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return plan


@router.post("/plans/{migration_id}/execute", response_model=MigrationExecutionResponse)
async def execute_migration(
    migration_id: str = Path(..., description="Migration plan ID"),
    request: ExecuteMigrationRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    tenant_id: str = Depends(get_current_tenant),
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager),
    _: None = Depends(require_permissions(["workflow:migration:execute"]))
):
    """Execute a migration plan."""
    if migration_id not in migration_mgr.migration_plans:
        raise HTTPException(status_code=404, detail="Migration plan not found")

    plan = migration_mgr.migration_plans[migration_id]

    # Check tenant access
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if migration is already running
    if migration_id in migration_mgr.active_migrations:
        raise HTTPException(status_code=409, detail="Migration is already running")

    try:
        # Execute migration in background for long-running operations
        if request.dry_run:
            execution = await migration_mgr.execute_migration(migration_id, dry_run=True)
        else:
            # For actual migrations, run in background
            background_tasks.add_task(migration_mgr.execute_migration, migration_id, False)

            # Create initial execution record
            execution = MigrationExecution(
                migration_id=migration_id,
                status=MigrationStatus.RUNNING,
                started_at=datetime.now(timezone.utc)
            )
            migration_mgr.migration_executions[execution.execution_id] = execution
            migration_mgr.active_migrations.add(migration_id)

        return _format_execution_response(execution)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to execute migration", migration_id=migration_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to execute migration: {str(e)}")


@router.post("/executions/{execution_id}/rollback")
async def rollback_migration(
    execution_id: str = Path(..., description="Migration execution ID"),
    request: RollbackMigrationRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    tenant_id: str = Depends(get_current_tenant),
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager),
    _: None = Depends(require_permissions(["workflow:migration:rollback"]))
):
    """Rollback a migration execution."""
    if execution_id not in migration_mgr.migration_executions:
        raise HTTPException(status_code=404, detail="Migration execution not found")

    execution = migration_mgr.migration_executions[execution_id]
    plan = migration_mgr.migration_plans[execution.migration_id]

    # Check tenant access
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if rollback is possible
    if execution.status not in [MigrationStatus.COMPLETED, MigrationStatus.FAILED]:
        raise HTTPException(status_code=400, detail=f"Cannot rollback migration in status {execution.status}")

    try:
        # Execute rollback in background
        background_tasks.add_task(migration_mgr.rollback_migration, execution_id, request.reason)

        return {
            "message": f"Rollback initiated for execution {execution_id}",
            "execution_id": execution_id,
            "reason": request.reason
        }

    except Exception as e:
        logger.error("Failed to initiate rollback", execution_id=execution_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to initiate rollback: {str(e)}")


@router.get("/executions/{execution_id}", response_model=MigrationExecutionResponse)
async def get_migration_execution(
    execution_id: str = Path(..., description="Migration execution ID"),
    tenant_id: str = Depends(get_current_tenant),
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager),
    _: None = Depends(require_permissions(["workflow:migration:read"]))
):
    """Get migration execution status."""
    if execution_id not in migration_mgr.migration_executions:
        raise HTTPException(status_code=404, detail="Migration execution not found")

    execution = migration_mgr.migration_executions[execution_id]
    plan = migration_mgr.migration_plans[execution.migration_id]

    # Check tenant access
    if plan.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _format_execution_response(execution)


@router.get("/executions", response_model=MigrationListResponse)
async def list_migration_executions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    status: Optional[MigrationStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    tenant_id: str = Depends(get_current_tenant),
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager),
    _: None = Depends(require_permissions(["workflow:migration:read"]))
):
    """List migration executions with optional filters."""
    try:
        # Get filtered executions
        executions = await migration_mgr.list_migrations(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status=status
        )

        # Apply pagination
        total_count = len(executions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_executions = executions[start_idx:end_idx]

        # Format response
        execution_responses = [_format_execution_response(exec) for exec in paginated_executions]

        return MigrationListResponse(
            executions=execution_responses,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error("Failed to list migrations", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list migrations: {str(e)}")


@router.post("/validate")
async def validate_migration_changes(
    changes: List[Dict[str, Any]] = Body(..., description="List of changes to validate"),
    tenant_id: str = Depends(get_current_tenant),
    _: None = Depends(require_permissions(["workflow:migration:validate"]))
):
    """Validate migration changes."""
    try:
        validation_errors = []
        breaking_changes = 0

        for i, change_data in enumerate(changes):
            # Validate required fields
            required_fields = ["change_type", "path", "description"]
            missing_fields = [field for field in required_fields if field not in change_data]

            if missing_fields:
                validation_errors.append({
                    "change_index": i,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                })
                continue

            # Validate change type
            try:
                ChangeType(change_data["change_type"])
            except ValueError:
                validation_errors.append({
                    "change_index": i,
                    "error": f"Invalid change_type: {change_data['change_type']}"
                })

            # Count breaking changes
            if change_data.get("breaking", False):
                breaking_changes += 1

        return {
            "valid": len(validation_errors) == 0,
            "total_changes": len(changes),
            "breaking_changes": breaking_changes,
            "non_breaking_changes": len(changes) - breaking_changes,
            "validation_errors": validation_errors
        }

    except Exception as e:
        logger.error("Failed to validate changes", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to validate changes: {str(e)}")


@router.get("/templates/changes")
async def get_migration_template(
    workflow_id: str = Query(..., description="Workflow ID"),
    from_version: str = Query(..., description="Source version"),
    to_version: str = Query(..., description="Target version"),
    _: None = Depends(require_permissions(["workflow:migration:read"]))
):
    """Get a template for migration changes."""
    template = {
        "workflow_id": workflow_id,
        "from_version": from_version,
        "to_version": to_version,
        "description": f"Migration from {from_version} to {to_version}",
        "changes": [
            {
                "change_type": "add_step",
                "path": "$.steps[?]",
                "old_value": None,
                "new_value": {
                    "name": "new_step_name",
                    "type": "step_type",
                    "config": {}
                },
                "description": "Add new step",
                "breaking": False,
                "rollback_action": {
                    "type": "remove_step",
                    "path": "$.steps[?]"
                }
            },
            {
                "change_type": "modify_step",
                "path": "$.steps[0].config.timeout",
                "old_value": 30,
                "new_value": 60,
                "description": "Increase step timeout",
                "breaking": False,
                "rollback_action": {
                    "type": "set_value",
                    "path": "$.steps[0].config.timeout",
                    "value": 30
                }
            }
        ]
    }

    return {
        "template": template,
        "available_change_types": [change_type.value for change_type in ChangeType],
        "documentation": {
            "path": "JSONPath expression to the element being changed",
            "breaking": "Whether this change breaks backward compatibility",
            "rollback_action": "Custom action to perform during rollback"
        }
    }


@router.get("/health")
async def get_migration_health(
    migration_mgr: WorkflowMigrationManager = Depends(get_migration_manager)
):
    """Get migration system health status."""
    return {
        "status": "healthy",
        "active_migrations": len(migration_mgr.active_migrations),
        "total_plans": len(migration_mgr.migration_plans),
        "total_executions": len(migration_mgr.migration_executions),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _format_execution_response(execution: MigrationExecution) -> MigrationExecutionResponse:
    """Format migration execution for API response."""
    duration_seconds = None
    if execution.started_at and execution.completed_at:
        duration_seconds = (execution.completed_at - execution.started_at).total_seconds()

    return MigrationExecutionResponse(
        execution_id=execution.execution_id,
        migration_id=execution.migration_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration_seconds=duration_seconds,
        affected_runs_count=len(execution.affected_runs),
        has_rollback_point=execution.rollback_point is not None,
        error_message=execution.error_message,
        progress=execution.progress
    )
