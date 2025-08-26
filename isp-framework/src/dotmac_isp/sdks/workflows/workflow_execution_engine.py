"""
Refactored workflow execution engine - Extract complexity from workflow.py
Follows SRP (Single Responsibility Principle) with focused classes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Set

import structlog

from ..contracts.common_schemas import ExecutionStatus, ErrorInfo
from .workflow import (
    WorkflowDefinition,
    WorkflowExecution,
    StepExecution,
    StepDefinition,
    WorkflowEngine,
)

logger = structlog.get_logger(__name__)


@dataclass
class WorkflowExecutionRequest:
    """Strongly typed request for workflow execution - reduces parameter sprawl."""

    workflow_def: WorkflowDefinition
    execution: WorkflowExecution

    def validate(self) -> None:
        """Validate execution request."""
        if not self.workflow_def.steps:
            raise ValueError("Workflow must have steps")
        if not self.execution.execution_id:
            raise ValueError("Execution ID required")


class StepDependencyResolver:
    """Handles step dependency resolution and execution ordering."""

    def __init__(self, workflow_def: WorkflowDefinition):
        """  Init   operation."""
        self.workflow_def = workflow_def
        self.step_map = {step.id: step for step in workflow_def.steps}

    def get_initial_ready_steps(self) -> Set[str]:
        """Get steps that are ready to execute initially."""
        return {self.workflow_def.start_step}

    def find_next_ready_steps(
        self, completed_steps: Set[str], failed_steps: Set[str]
    ) -> Set[str]:
        """Find steps that are ready to execute based on completed dependencies."""
        ready_steps = set()

        for step in self.workflow_def.steps:
            if self._is_step_ready(step, completed_steps, failed_steps):
                ready_steps.add(step.id)

        return ready_steps

    def _is_step_ready(
        self, step: StepDefinition, completed_steps: Set[str], failed_steps: Set[str]
    ) -> bool:
        """Check if a step is ready to execute."""
        # Skip if already processed
        if step.id in completed_steps or step.id in failed_steps:
            return False

        # Check if all dependencies are completed
        return all(dep in completed_steps for dep in step.depends_on)


class StepExecutionOrchestrator:
    """Orchestrates execution of individual workflow steps."""

    def __init__(self, engine: WorkflowEngine):
        """  Init   operation."""
        self.engine = engine

    async def execute_step_batch(
        self,
        step_ids: Set[str],
        step_map: Dict[str, StepDefinition],
        execution: WorkflowExecution,
    ) -> Dict[str, bool]:
        """Execute a batch of steps and return success status for each."""
        results = {}

        for step_id in step_ids:
            step_def = step_map[step_id]
            success = await self._execute_single_step(step_def, execution)
            results[step_id] = success

        return results

    async def _execute_single_step(
        self, step_def: StepDefinition, execution: WorkflowExecution
    ) -> bool:
        """Execute a single step with proper state management."""
        # Create step execution
        step_execution = StepExecution(
            step_id=step_def.id,
            execution_id=execution.execution_id,
        )
        execution.step_executions[step_def.id] = step_execution
        execution.current_steps.add(step_def.id)

        try:
            # Execute step
            success = await self.engine.execute_step(
                step_def, step_execution, execution.context
            )

            execution.current_steps.discard(step_def.id)
            return success

        except Exception as e:
            execution.current_steps.discard(step_def.id)
            logger.error(
                "Step execution failed",
                step_id=step_def.id,
                execution_id=execution.execution_id,
                error=str(e),
            )
            return False


class WorkflowExecutionStateMachine:
    """Manages workflow execution state transitions."""

    def __init__(self, execution: WorkflowExecution):
        """  Init   operation."""
        self.execution = execution

    def start_execution(self) -> None:
        """Mark execution as started."""
        self.execution.status = ExecutionStatus.RUNNING

    def mark_step_completed(self, step_id: str) -> None:
        """Mark a step as completed."""
        self.execution.completed_steps.add(step_id)

    def mark_step_failed(self, step_id: str) -> None:
        """Mark a step as failed."""
        self.execution.failed_steps.add(step_id)

    def fail_execution(self, error: Exception) -> None:
        """Mark entire execution as failed."""
        self.execution.status = ExecutionStatus.FAILED
        self.execution.error = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            timestamp=datetime.now(timezone.utc),
        )
        self.execution.completed_at = datetime.now(timezone.utc)

    def complete_execution(self) -> None:
        """Mark execution as completed successfully."""
        if self.execution.status == ExecutionStatus.RUNNING:
            self.execution.status = ExecutionStatus.COMPLETED
            self.execution.output_data = self.execution.context.variables.model_copy()

        self.execution.completed_at = datetime.now(timezone.utc)

    def should_continue(self) -> bool:
        """Check if execution should continue."""
        return self.execution.status == ExecutionStatus.RUNNING


class RefactoredWorkflowExecutionEngine:
    """
    Refactored workflow execution engine with separated concerns.

    This class orchestrates workflow execution by delegating to specialized
    components, dramatically reducing complexity from the original 80+ line method.
    """

    def __init__(self, engine: WorkflowEngine, storage_adapter=None):
        """  Init   operation."""
        self.engine = engine
        self.storage_adapter = storage_adapter

    async def execute_workflow_async(
        self, workflow_def: WorkflowDefinition, execution: WorkflowExecution
    ) -> None:
        """
        Execute workflow asynchronously with clean separation of concerns.

        Complexity reduced from 80+ lines to orchestration of focused components.
        """
        # Validate request
        request = WorkflowExecutionRequest(workflow_def, execution)
        request.validate()

        # Initialize components
        dependency_resolver = StepDependencyResolver(workflow_def)
        step_orchestrator = StepExecutionOrchestrator(self.engine)
        state_machine = WorkflowExecutionStateMachine(execution)

        try:
            # Start execution
            state_machine.start_execution()
            step_map = dependency_resolver.step_map
            ready_steps = dependency_resolver.get_initial_ready_steps()

            # Execute workflow steps
            await self._execute_workflow_loop(
                ready_steps,
                step_map,
                dependency_resolver,
                step_orchestrator,
                state_machine,
            )

            # Complete execution
            state_machine.complete_execution()
            await self._persist_execution_if_needed(execution)

            logger.info(
                "Workflow execution completed",
                workflow_id=workflow_def.id,
                execution_id=execution.execution_id,
                status=execution.status.value,
                tenant_id=workflow_def.tenant_id,
            )

        except Exception as e:
            state_machine.fail_execution(e)
            logger.error(
                "Workflow execution failed",
                workflow_id=workflow_def.id,
                execution_id=execution.execution_id,
                error=str(e),
                tenant_id=workflow_def.tenant_id,
            )

    async def _execute_workflow_loop(
        self,
        ready_steps: Set[str],
        step_map: Dict[str, StepDefinition],
        dependency_resolver: StepDependencyResolver,
        step_orchestrator: StepExecutionOrchestrator,
        state_machine: WorkflowExecutionStateMachine,
    ) -> None:
        """Execute the main workflow processing loop."""
        while ready_steps and state_machine.should_continue():
            # Execute current batch of ready steps
            current_batch = ready_steps.model_copy()
            ready_steps.clear()

            step_results = await step_orchestrator.execute_step_batch(
                current_batch, step_map, state_machine.execution
            )

            # Process step results and update state
            execution_failed = self._process_step_results(step_results, state_machine)

            if execution_failed:
                break

            # Find next ready steps
            ready_steps = dependency_resolver.find_next_ready_steps(
                state_machine.execution.completed_steps,
                state_machine.execution.failed_steps,
            )

    def _process_step_results(
        self,
        step_results: Dict[str, bool],
        state_machine: WorkflowExecutionStateMachine,
    ) -> bool:
        """Process step execution results and update state."""
        for step_id, success in step_results.items():
            if success:
                state_machine.mark_step_completed(step_id)
            else:
                state_machine.mark_step_failed(step_id)
                # Fail entire execution if any step fails
                state_machine.execution.status = ExecutionStatus.FAILED
                return True

        return False

    async def _persist_execution_if_needed(self, execution: WorkflowExecution) -> None:
        """Persist execution state if storage adapter is available."""
        if self.storage_adapter:
            await self.storage_adapter.store_execution(execution)
