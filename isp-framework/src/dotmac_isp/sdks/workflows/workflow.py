"""
Workflow SDK for orchestrating complex business processes and workflows.

This module provides comprehensive workflow management capabilities including:
- Workflow definition and execution
- Step orchestration and dependencies
- Conditional branching and parallel execution
- Error handling and compensation
- State persistence and recovery
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..contracts.common_schemas import (
    ExecutionContext,
    ExecutionStatus,
    OperationMetadata,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    Priority)

logger = structlog.get_logger(__name__)


class StepType(str, Enum):
    """Workflow step types."""

    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    LOOP = "loop"
    SWITCH = "switch"
    WAIT = "wait"
    WEBHOOK = "webhook"
    HUMAN_TASK = "human_task"
    COMPENSATION = "compensation"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class StepDefinition(BaseModel):
    """Definition of a workflow step."""

    id: str = Field(..., description="Step identifier")
    name: str = Field(..., description="Step name")
    step_type: StepType = Field(..., description="Step type")
    description: Optional[str] = Field(None, description="Step description")

    # Execution configuration
    handler: Optional[str] = Field(None, description="Handler function or service")
    input_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Input variable mapping"
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Output variable mapping"
    )

    # Dependencies and flow control
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")
    condition: Optional[str] = Field(None, description="Execution condition")

    # Policies
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry policy")
    timeout_policy: Optional[TimeoutPolicy] = Field(None, description="Timeout policy")

    # Parallel execution
    parallel_steps: List["StepDefinition"] = Field(
        default_factory=list, description="Parallel sub-steps"
    )

    # Loop configuration
    loop_condition: Optional[str] = Field(None, description="Loop condition")
    max_iterations: Optional[int] = Field(None, description="Maximum loop iterations")

    # Compensation
    compensation_handler: Optional[str] = Field(
        None, description="Compensation handler"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Step metadata")

    model_config = ConfigDict(extra="allow")

class WorkflowDefinition(BaseModel):
    """Workflow definition with steps and configuration."""

    id: str = Field(..., description="Workflow identifier")
    name: str = Field(..., description="Workflow name")
    version: str = Field("1.0", description="Workflow version")
    description: Optional[str] = Field(None, description="Workflow description")

    # Steps and flow
    steps: List[StepDefinition] = Field(..., description="Workflow steps")
    start_step: str = Field(..., description="Starting step ID")

    # Configuration
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Input schema"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Output schema"
    )

    # Policies
    default_retry_policy: Optional[RetryPolicy] = Field(
        None, description="Default retry policy"
    )
    default_timeout_policy: Optional[TimeoutPolicy] = Field(
        None, description="Default timeout policy"
    )

    # Workflow settings
    status: WorkflowStatus = Field(WorkflowStatus.DRAFT, description="Workflow status")
    priority: Priority = Field(Priority.NORMAL, description="Default priority")

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v):
        """Validate Steps operation."""
        if not v:
            raise ValueError("Workflow must have at least one step")

        step_ids = {step.id for step in v}

        # Validate start step exists
        start_step = values.get("start_step")
        if start_step and start_step not in step_ids:
            raise ValueError(f"Start step '{start_step}' not found in workflow steps")

        # Validate dependencies
        for step in v:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Step '{step.id}' depends on non-existent step '{dep}'"
                    )

        return v

    model_config = ConfigDict(extra="allow")

@dataclass
class StepExecution:
    """Runtime execution state of a workflow step."""

    step_id: str
    execution_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error.model_dump() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retry_count": self.retry_count,
        }


@dataclass
class WorkflowExecution:
    """Runtime execution state of a workflow."""

    execution_id: str
    workflow_id: str
    workflow_version: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    step_executions: Dict[str, StepExecution] = field(default_factory=dict)
    current_steps: Set[str] = field(default_factory=set)
    completed_steps: Set[str] = field(default_factory=set)
    failed_steps: Set[str] = field(default_factory=set)
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context.model_dump() if self.context else None,
            "step_executions": {
                k: v.to_dict() for k, v in self.step_executions.items()
            },
            "current_steps": list(self.current_steps),
            "completed_steps": list(self.completed_steps),
            "failed_steps": list(self.failed_steps),
            "error": self.error.model_dump() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class WorkflowEngine:
    """Workflow execution engine."""

    def __init__(self):
        """  Init   operation."""
        self.step_handlers: Dict[str, Callable] = {}
        self.condition_evaluator: Optional[Callable] = None

    def register_handler(self, handler_name: str, handler: Callable):
        """Register a step handler."""
        self.step_handlers[handler_name] = handler

    def set_condition_evaluator(self, evaluator: Callable):
        """Set condition evaluator function."""
        self.condition_evaluator = evaluator

    async def execute_step(
        self,
        step_def: StepDefinition,
        step_execution: StepExecution,
        context: ExecutionContext,
    ) -> bool:
        """Execute a single workflow step."""
        try:
            step_execution.status = ExecutionStatus.RUNNING
            step_execution.started_at = datetime.now(timezone.utc)

            # Check condition if specified
            if step_def.condition and self.condition_evaluator:
                if not await self.condition_evaluator(step_def.condition, context):
                    step_execution.status = ExecutionStatus.SKIPPED
                    step_execution.completed_at = datetime.now(timezone.utc)
                    return True

            # Execute based on step type
            if step_def.step_type == StepType.TASK:
                await self._execute_task_step(step_def, step_execution, context)
            elif step_def.step_type == StepType.PARALLEL:
                await self._execute_parallel_step(step_def, step_execution, context)
            elif step_def.step_type == StepType.CONDITION:
                await self._execute_condition_step(step_def, step_execution, context)
            elif step_def.step_type == StepType.WAIT:
                await self._execute_wait_step(step_def, step_execution, context)
            else:
                raise NotImplementedError(
                    f"Step type {step_def.step_type} not implemented"
                )

            step_execution.status = ExecutionStatus.COMPLETED
            step_execution.completed_at = datetime.now(timezone.utc)
            return True

        except Exception as e:
            step_execution.status = ExecutionStatus.FAILED
            step_execution.completed_at = datetime.now(timezone.utc)
            step_execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Step execution failed",
                step_id=step_def.id,
                execution_id=step_execution.execution_id,
                error=str(e),
            )
            return False

    async def _execute_task_step(
        self,
        step_def: StepDefinition,
        step_execution: StepExecution,
        context: ExecutionContext,
    ):
        """Execute a task step."""
        if not step_def.handler:
            raise ValueError(f"Task step {step_def.id} missing handler")

        handler = self.step_handlers.get(step_def.handler)
        if not handler:
            raise ValueError(f"Handler {step_def.handler} not registered")

        # Map input data
        input_data = self._map_data(step_def.input_mapping, context.variables)
        step_execution.input_data = input_data

        # Execute handler
        result = await handler(input_data, context)

        # Map output data
        if isinstance(result, dict):
            output_data = self._map_data(step_def.output_mapping, result)
            step_execution.output_data = output_data

            # Update context variables
            context.variables.update(output_data)

    async def _execute_parallel_step(
        self,
        step_def: StepDefinition,
        step_execution: StepExecution,
        context: ExecutionContext,
    ):
        """Execute parallel sub-steps."""
        if not step_def.parallel_steps:
            return

        # Create sub-executions
        sub_executions = []
        for sub_step in step_def.parallel_steps:
            sub_execution = StepExecution(
                step_id=sub_step.id,
                execution_id=f"{step_execution.execution_id}_{sub_step.id}",
            )
            sub_executions.append((sub_step, sub_execution))

        # Execute in parallel
        tasks = [
            self.execute_step(sub_step, sub_execution, context)
            for sub_step, sub_execution in sub_executions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        failed_count = sum(
            1 for result in results if isinstance(result, Exception) or not result
        )
        if failed_count > 0:
            raise Exception(f"{failed_count} parallel steps failed")

    async def _execute_condition_step(
        self,
        step_def: StepDefinition,
        step_execution: StepExecution,
        context: ExecutionContext,
    ):
        """Execute a condition step."""
        if not step_def.condition or not self.condition_evaluator:
            raise ValueError("Condition step requires condition and evaluator")

        result = await self.condition_evaluator(step_def.condition, context)
        step_execution.output_data = {"condition_result": result}
        context.variables["condition_result"] = result

    async def _execute_wait_step(
        self,
        step_def: StepDefinition,
        step_execution: StepExecution,
        context: ExecutionContext,
    ):
        """Execute a wait step."""
        wait_seconds = step_def.metadata.get("wait_seconds", 1)
        await asyncio.sleep(wait_seconds)
        step_execution.output_data = {"waited_seconds": wait_seconds}

    def _map_data(
        self, mapping: Dict[str, str], source_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map data using field mapping configuration."""
        if not mapping:
            return source_data

        result = {}
        for target_field, source_field in mapping.items():
            if source_field in source_data:
                result[target_field] = source_data[source_field]

        return result


class WorkflowSDK:
    """SDK for workflow management and execution."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.engine = WorkflowEngine()
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}

        logger.info("WorkflowSDK initialized", tenant_id=tenant_id)

    async def create_workflow(self, workflow_def: WorkflowDefinition) -> str:
        """Create a new workflow definition."""
        workflow_def.tenant_id = self.tenant_id
        workflow_def.metadata.updated_at = datetime.now(timezone.utc)

        self.workflows[workflow_def.id] = workflow_def

        if self.storage_adapter:
            await self.storage_adapter.store_workflow(workflow_def)

        logger.info(
            "Workflow created",
            workflow_id=workflow_def.id,
            tenant_id=self.tenant_id,
        )

        return workflow_def.id

    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> str:
        """Start workflow execution."""
        workflow_def = self.workflows.get(workflow_id)
        if not workflow_def:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow_def.status != WorkflowStatus.ACTIVE:
            raise ValueError(f"Workflow {workflow_id} is not active")

        execution_id = str(uuid.uuid4())

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.tenant_id,
                variables=input_data.model_copy(),
            )
        else:
            context.execution_id = execution_id
            context.variables.update(input_data)

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow_version=workflow_def.version,
            input_data=input_data,
            context=context,
            started_at=datetime.now(timezone.utc),
        )

        self.executions[execution_id] = execution

        # Start execution asynchronously
        asyncio.create_task(self._execute_workflow_async(workflow_def, execution))

        logger.info(
            "Workflow execution started",
            workflow_id=workflow_id,
            execution_id=execution_id,
            tenant_id=self.tenant_id,
        )

        return execution_id

    async def _execute_workflow_async(
        self,
        workflow_def: WorkflowDefinition,
        execution: WorkflowExecution,
    ):
        """Execute workflow asynchronously using refactored execution engine."""
        from .workflow_execution_engine import RefactoredWorkflowExecutionEngine

        execution_engine = RefactoredWorkflowExecutionEngine(
            self.engine, self.storage_adapter
        )

        await execution_engine.execute_workflow_async(workflow_def, execution)

    async def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID."""
        return self.executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running workflow execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            return False

        if execution.status in [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]:
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Workflow execution cancelled",
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
            return True

        return False

    def register_step_handler(self, handler_name: str, handler: Callable):
        """Register a step handler function."""
        self.engine.register_handler(handler_name, handler)

    def set_condition_evaluator(self, evaluator: Callable):
        """Set condition evaluator function."""
        self.engine.set_condition_evaluator(evaluator)
