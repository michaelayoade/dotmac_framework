"""
Workflow definition migration and rollback system.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from ..sdks.event_bus import EventBusSDK

logger = structlog.get_logger(__name__)


class MigrationStatus(str, Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"


class ChangeType(str, Enum):
    """Type of workflow definition change."""
    ADD_STEP = "add_step"
    REMOVE_STEP = "remove_step"
    MODIFY_STEP = "modify_step"
    REORDER_STEPS = "reorder_steps"
    ADD_CONDITION = "add_condition"
    REMOVE_CONDITION = "remove_condition"
    MODIFY_CONDITION = "modify_condition"
    ADD_VARIABLE = "add_variable"
    REMOVE_VARIABLE = "remove_variable"
    MODIFY_VARIABLE = "modify_variable"
    CHANGE_TIMEOUT = "change_timeout"
    CHANGE_RETRY_POLICY = "change_retry_policy"


class WorkflowChange(BaseModel):
    """Individual workflow change definition."""
    change_id: str = Field(default_factory=lambda: str(uuid4()))
    change_type: ChangeType
    path: str = Field(..., description="JSONPath to the changed element")
    old_value: Optional[Any] = Field(None, description="Previous value")
    new_value: Optional[Any] = Field(None, description="New value")
    description: str = Field(..., description="Human-readable change description")
    breaking: bool = Field(False, description="Whether this is a breaking change")
    rollback_action: Optional[Dict[str, Any]] = Field(None, description="Custom rollback action")


class WorkflowDefinition(BaseModel):
    """Workflow definition with versioning."""
    workflow_id: str
    version: str
    schema_version: str = "1.0"
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    conditions: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    timeouts: Optional[Dict[str, Any]] = None
    retry_policies: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None


class MigrationPlan(BaseModel):
    """Migration plan for workflow definition changes."""
    migration_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    from_version: str
    to_version: str
    tenant_id: str
    changes: List[WorkflowChange]
    migration_strategy: str = Field(default="gradual", description="Migration strategy")
    rollback_strategy: str = Field(default="immediate", description="Rollback strategy")
    validation_rules: List[Dict[str, Any]] = Field(default_factory=list)
    pre_migration_checks: List[str] = Field(default_factory=list)
    post_migration_checks: List[str] = Field(default_factory=list)
    rollback_timeout: int = Field(default=300, description="Rollback timeout in seconds")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None


class MigrationExecution(BaseModel):
    """Migration execution tracking."""
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    migration_id: str
    status: MigrationStatus = MigrationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    affected_runs: List[str] = Field(default_factory=list)
    rollback_point: Optional[Dict[str, Any]] = None
    progress: Dict[str, Any] = Field(default_factory=dict)


class WorkflowMigrationManager:
    """Manager for workflow definition migrations."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.workflow_definitions = {}  # In production, this would be a database
        self.migration_plans = {}
        self.migration_executions = {}
        self.active_migrations = set()

    async def create_migration_plan(
        self,
        workflow_id: str,
        from_version: str,
        to_version: str,
        tenant_id: str,
        changes: List[WorkflowChange],
        migration_strategy: str = "gradual",
        created_by: Optional[str] = None
    ) -> MigrationPlan:
        """Create a migration plan for workflow definition changes."""

        # Validate workflow versions exist
        from_def = await self._get_workflow_definition(workflow_id, from_version, tenant_id)
        to_def = await self._get_workflow_definition(workflow_id, to_version, tenant_id)

        if not from_def:
            raise ValueError(f"Source workflow version {from_version} not found")
        if not to_def:
            raise ValueError(f"Target workflow version {to_version} not found")

        # Generate validation rules based on changes
        validation_rules = self._generate_validation_rules(changes)

        # Generate pre/post migration checks
        pre_checks = self._generate_pre_migration_checks(changes)
        post_checks = self._generate_post_migration_checks(changes)

        plan = MigrationPlan(
            workflow_id=workflow_id,
            from_version=from_version,
            to_version=to_version,
            tenant_id=tenant_id,
            changes=changes,
            migration_strategy=migration_strategy,
            validation_rules=validation_rules,
            pre_migration_checks=pre_checks,
            post_migration_checks=post_checks,
            created_by=created_by
        )

        self.migration_plans[plan.migration_id] = plan

        # Publish migration plan created event
        await self.event_bus.publish(
            event_type="workflow.migration.plan.created",
            data={
                "migration_id": plan.migration_id,
                "workflow_id": workflow_id,
                "from_version": from_version,
                "to_version": to_version,
                "changes_count": len(changes),
                "breaking_changes": len([c for c in changes if c.breaking]),
                "migration_strategy": migration_strategy,
                "tenant_id": tenant_id
            },
            partition_key=tenant_id
        )

        logger.info("Migration plan created",
                   migration_id=plan.migration_id,
                   workflow_id=workflow_id,
                   from_version=from_version,
                   to_version=to_version)

        return plan

    async def execute_migration(
        self,
        migration_id: str,
        dry_run: bool = False
    ) -> MigrationExecution:
        """Execute a migration plan."""

        if migration_id not in self.migration_plans:
            raise ValueError(f"Migration plan {migration_id} not found")

        if migration_id in self.active_migrations:
            raise ValueError(f"Migration {migration_id} is already running")

        plan = self.migration_plans[migration_id]

        execution = MigrationExecution(
            migration_id=migration_id,
            status=MigrationStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )

        self.migration_executions[execution.execution_id] = execution
        self.active_migrations.add(migration_id)

        try:
            # Publish migration started event
            await self.event_bus.publish(
                event_type="workflow.migration.started",
                data={
                    "execution_id": execution.execution_id,
                    "migration_id": migration_id,
                    "workflow_id": plan.workflow_id,
                    "dry_run": dry_run,
                    "tenant_id": plan.tenant_id
                },
                partition_key=plan.tenant_id
            )

            # Execute pre-migration checks
            await self._execute_pre_migration_checks(plan, execution)

            # Create rollback point
            rollback_point = await self._create_rollback_point(plan)
            execution.rollback_point = rollback_point

            # Execute migration steps
            if not dry_run:
                await self._execute_migration_steps(plan, execution)
            else:
                await self._simulate_migration_steps(plan, execution)

            # Execute post-migration checks
            await self._execute_post_migration_checks(plan, execution)

            # Mark as completed
            execution.status = MigrationStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)

            # Publish migration completed event
            await self.event_bus.publish(
                event_type="workflow.migration.completed",
                data={
                    "execution_id": execution.execution_id,
                    "migration_id": migration_id,
                    "workflow_id": plan.workflow_id,
                    "duration_seconds": (execution.completed_at - execution.started_at).total_seconds(),
                    "affected_runs": len(execution.affected_runs),
                    "dry_run": dry_run,
                    "tenant_id": plan.tenant_id
                },
                partition_key=plan.tenant_id
            )

            logger.info("Migration completed successfully",
                       execution_id=execution.execution_id,
                       migration_id=migration_id,
                       workflow_id=plan.workflow_id)

        except Exception as e:
            execution.status = MigrationStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)

            # Publish migration failed event
            await self.event_bus.publish(
                event_type="workflow.migration.failed",
                data={
                    "execution_id": execution.execution_id,
                    "migration_id": migration_id,
                    "workflow_id": plan.workflow_id,
                    "error": str(e),
                    "tenant_id": plan.tenant_id
                },
                partition_key=plan.tenant_id
            )

            logger.error("Migration failed",
                        execution_id=execution.execution_id,
                        migration_id=migration_id,
                        error=str(e))

            # Attempt automatic rollback if configured
            if plan.rollback_strategy == "immediate":
                await self._attempt_rollback(plan, execution)

        finally:
            self.active_migrations.discard(migration_id)

        return execution

    async def rollback_migration(
        self,
        execution_id: str,
        reason: str = "Manual rollback"
    ) -> bool:
        """Rollback a migration."""

        if execution_id not in self.migration_executions:
            raise ValueError(f"Migration execution {execution_id} not found")

        execution = self.migration_executions[execution_id]
        plan = self.migration_plans[execution.migration_id]

        if execution.status not in [MigrationStatus.COMPLETED, MigrationStatus.FAILED]:
            raise ValueError(f"Cannot rollback migration in status {execution.status}")

        try:
            # Publish rollback started event
            await self.event_bus.publish(
                event_type="workflow.migration.rollback.started",
                data={
                    "execution_id": execution_id,
                    "migration_id": execution.migration_id,
                    "workflow_id": plan.workflow_id,
                    "reason": reason,
                    "tenant_id": plan.tenant_id
                },
                partition_key=plan.tenant_id
            )

            # Execute rollback
            success = await self._execute_rollback(plan, execution, reason)

            if success:
                execution.status = MigrationStatus.ROLLED_BACK

                await self.event_bus.publish(
                    event_type="workflow.migration.rollback.completed",
                    data={
                        "execution_id": execution_id,
                        "migration_id": execution.migration_id,
                        "workflow_id": plan.workflow_id,
                        "tenant_id": plan.tenant_id
                    },
                    partition_key=plan.tenant_id
                )

                logger.info("Migration rolled back successfully",
                           execution_id=execution_id,
                           migration_id=execution.migration_id)
            else:
                execution.status = MigrationStatus.ROLLBACK_FAILED

                await self.event_bus.publish(
                    event_type="workflow.migration.rollback.failed",
                    data={
                        "execution_id": execution_id,
                        "migration_id": execution.migration_id,
                        "workflow_id": plan.workflow_id,
                        "tenant_id": plan.tenant_id
                    },
                    partition_key=plan.tenant_id
                )

                logger.error("Migration rollback failed",
                            execution_id=execution_id,
                            migration_id=execution.migration_id)

            return success

        except Exception as e:
            execution.status = MigrationStatus.ROLLBACK_FAILED
            execution.error_message = f"Rollback failed: {str(e)}"

            logger.error("Migration rollback error",
                        execution_id=execution_id,
                        error=str(e))

            return False

    async def get_migration_status(self, execution_id: str) -> Optional[MigrationExecution]:
        """Get migration execution status."""
        return self.migration_executions.get(execution_id)

    async def list_migrations(
        self,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[MigrationStatus] = None
    ) -> List[MigrationExecution]:
        """List migration executions with optional filters."""
        executions = list(self.migration_executions.values())

        if workflow_id:
            executions = [e for e in executions
                         if self.migration_plans[e.migration_id].workflow_id == workflow_id]

        if tenant_id:
            executions = [e for e in executions
                         if self.migration_plans[e.migration_id].tenant_id == tenant_id]

        if status:
            executions = [e for e in executions if e.status == status]

        return sorted(executions, key=lambda x: x.started_at or datetime.min, reverse=True)

    async def _get_workflow_definition(
        self,
        workflow_id: str,
        version: str,
        tenant_id: str
    ) -> Optional[WorkflowDefinition]:
        """Get workflow definition by ID and version."""
        key = f"{tenant_id}:{workflow_id}:{version}"
        return self.workflow_definitions.get(key)

    def _generate_validation_rules(self, changes: List[WorkflowChange]) -> List[Dict[str, Any]]:
        """Generate validation rules based on changes."""
        rules = []

        for change in changes:
            if change.change_type == ChangeType.REMOVE_STEP:
                rules.append({
                    "type": "no_active_runs_on_step",
                    "step_path": change.path,
                    "description": f"No active runs should be executing step at {change.path}"
                })

            elif change.change_type == ChangeType.MODIFY_STEP and change.breaking:
                rules.append({
                    "type": "step_compatibility_check",
                    "step_path": change.path,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                    "description": f"Step modification at {change.path} must be backward compatible"
                })

        return rules

    def _generate_pre_migration_checks(self, changes: List[WorkflowChange]) -> List[str]:
        """Generate pre-migration checks."""
        checks = ["validate_workflow_syntax", "check_active_runs", "verify_dependencies"]

        breaking_changes = [c for c in changes if c.breaking]
        if breaking_changes:
            checks.extend(["drain_active_runs", "backup_current_state"])

        return checks

    def _generate_post_migration_checks(self, changes: List[WorkflowChange]) -> List[str]:
        """Generate post-migration checks."""
        return ["validate_new_definition", "test_workflow_execution", "verify_metrics"]

    async def _execute_pre_migration_checks(
        self,
        plan: MigrationPlan,
        execution: MigrationExecution
    ):
        """Execute pre-migration checks."""
        execution.progress["pre_checks"] = {"total": len(plan.pre_migration_checks), "completed": 0}

        for check in plan.pre_migration_checks:
            await self._execute_check(check, plan, execution, "pre")
            execution.progress["pre_checks"]["completed"] += 1

    async def _execute_post_migration_checks(
        self,
        plan: MigrationPlan,
        execution: MigrationExecution
    ):
        """Execute post-migration checks."""
        execution.progress["post_checks"] = {"total": len(plan.post_migration_checks), "completed": 0}

        for check in plan.post_migration_checks:
            await self._execute_check(check, plan, execution, "post")
            execution.progress["post_checks"]["completed"] += 1

    async def _execute_check(
        self,
        check: str,
        plan: MigrationPlan,
        execution: MigrationExecution,
        phase: str
    ):
        """Execute a specific check."""
        # Simulate check execution
        await asyncio.sleep(0.1)

        logger.debug(f"Executed {phase}-migration check",
                    check=check,
                    migration_id=plan.migration_id)

    async def _create_rollback_point(self, plan: MigrationPlan) -> Dict[str, Any]:
        """Create a rollback point before migration."""
        current_def = await self._get_workflow_definition(
            plan.workflow_id,
            plan.from_version,
            plan.tenant_id
        )

        rollback_point = {
            "workflow_definition": current_def.dict() if current_def else None,
            "active_runs": [],  # In production, capture active runs
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return rollback_point

    async def _execute_migration_steps(
        self,
        plan: MigrationPlan,
        execution: MigrationExecution
    ):
        """Execute actual migration steps."""
        execution.progress["migration_steps"] = {"total": len(plan.changes), "completed": 0}

        for change in plan.changes:
            await self._apply_change(change, plan, execution)
            execution.progress["migration_steps"]["completed"] += 1

    async def _simulate_migration_steps(
        self,
        plan: MigrationPlan,
        execution: MigrationExecution
    ):
        """Simulate migration steps for dry run."""
        execution.progress["simulation"] = {"total": len(plan.changes), "completed": 0}

        for change in plan.changes:
            # Simulate applying change
            await asyncio.sleep(0.05)
            logger.debug("Simulated change application",
                        change_id=change.change_id,
                        change_type=change.change_type)
            execution.progress["simulation"]["completed"] += 1

    async def _apply_change(
        self,
        change: WorkflowChange,
        plan: MigrationPlan,
        execution: MigrationExecution
    ):
        """Apply a specific workflow change."""
        # Simulate change application
        await asyncio.sleep(0.1)

        logger.info("Applied workflow change",
                   change_id=change.change_id,
                   change_type=change.change_type,
                   path=change.path)

    async def _attempt_rollback(
        self,
        plan: MigrationPlan,
        execution: MigrationExecution
    ):
        """Attempt automatic rollback after migration failure."""
        try:
            await self.rollback_migration(execution.execution_id, "Automatic rollback after failure")
        except Exception as e:
            logger.error("Automatic rollback failed",
                        execution_id=execution.execution_id,
                        error=str(e))

    async def _execute_rollback(
        self,
        plan: MigrationPlan,
        execution: MigrationExecution,
        reason: str
    ) -> bool:
        """Execute rollback to previous state."""
        if not execution.rollback_point:
            logger.error("No rollback point available", execution_id=execution.execution_id)
            return False

        try:
            # Restore previous workflow definition
            # In production, this would restore from the rollback point
            await asyncio.sleep(0.2)  # Simulate rollback time

            logger.info("Rollback executed successfully",
                       execution_id=execution.execution_id,
                       reason=reason)

            return True

        except Exception as e:
            logger.error("Rollback execution failed",
                        execution_id=execution.execution_id,
                        error=str(e))
            return False
