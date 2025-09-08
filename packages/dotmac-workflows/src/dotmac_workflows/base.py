"""
Base workflow implementation.
"""

import time
import uuid
from typing import Any

from .result import WorkflowResult
from .status import WorkflowStatus
from .types import StepName, WorkflowCallback, WorkflowId


class WorkflowError(Exception):
    """Base exception for workflow errors."""

    pass


class WorkflowExecutionError(WorkflowError):
    """Error during workflow execution."""

    pass


class WorkflowConfigurationError(WorkflowError):
    """Error in workflow configuration."""

    pass


class Workflow:
    """
    Base workflow class for sequential step execution.

    Supports approvals, rollback, callbacks, and resumability.
    """

    def __init__(
        self,
        workflow_id: WorkflowId | None = None,
        steps: list[StepName] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize workflow.

        Args:
            workflow_id: Unique identifier (generated if None)
            steps: List of step names to execute
            metadata: Additional workflow metadata
        """
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.steps = steps or []
        self.metadata = metadata or {}

        # Execution state
        self.status = WorkflowStatus.PENDING
        self.current_step_index = 0
        self.results: list[WorkflowResult] = []
        self.pending_approval_step: StepName | None = None
        self.approval_data: dict[str, Any] | None = None

        # Configuration
        self.rollback_on_failure = True
        self.continue_on_step_failure = False
        self.require_approval = False

        # Callbacks
        self.on_step_started: WorkflowCallback | None = None
        self.on_step_completed: WorkflowCallback | None = None
        self.on_workflow_completed: WorkflowCallback | None = None
        self.on_approval_required: WorkflowCallback | None = None
        self.on_rollback_started: WorkflowCallback | None = None

        # Internal state
        self._start_time: float | None = None
        self._end_time: float | None = None

    def configure(
        self,
        *,
        rollback_on_failure: bool = True,
        continue_on_step_failure: bool = False,
        require_approval: bool = False,
    ) -> None:
        """
        Configure workflow execution behavior.

        Args:
            rollback_on_failure: If True, rollback on step failure
            continue_on_step_failure: If True, continue on step failure
            require_approval: If True, require approval for execution
        """
        if continue_on_step_failure and rollback_on_failure:
            raise WorkflowConfigurationError(
                "Cannot enable both continue_on_step_failure and rollback_on_failure"
            )

        self.rollback_on_failure = rollback_on_failure
        self.continue_on_step_failure = continue_on_step_failure
        self.require_approval = require_approval

    async def validate(self) -> WorkflowResult:
        """
        Validate workflow configuration before execution.

        Override this method to add custom validation logic.

        Returns:
            ValidationError result if validation fails, success result otherwise
        """
        if not self.steps:
            return WorkflowResult(
                success=False,
                step="validation",
                data={},
                error="empty_steps",
                message="Workflow has no steps to execute",
            )

        if not self.workflow_id:
            return WorkflowResult(
                success=False,
                step="validation",
                data={},
                error="missing_id",
                message="Workflow must have an ID",
            )

        return WorkflowResult(success=True, step="validation", data={"validated": True})

    async def execute_step(self, step: StepName) -> WorkflowResult:
        """
        Execute a single workflow step.

        This is an abstract method that must be implemented by subclasses.

        Args:
            step: Name of the step to execute

        Returns:
            Result of step execution
        """
        raise NotImplementedError("Subclasses must implement execute_step method")

    async def execute(self) -> list[WorkflowResult]:
        """
        Execute the complete workflow.

        Returns:
            List of step results

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        if self.status in (WorkflowStatus.RUNNING, WorkflowStatus.WAITING_APPROVAL):
            raise WorkflowExecutionError(
                f"Workflow {self.workflow_id} is already running or waiting for approval"
            )

        # Validate workflow
        validation_result = await self.validate()
        if not validation_result.success:
            self.status = WorkflowStatus.FAILED
            self.results = [validation_result]
            return self.results

        try:
            self.status = WorkflowStatus.RUNNING
            self._start_time = time.time()

            # Execute steps from current position
            while self.current_step_index < len(self.steps):
                step = self.steps[self.current_step_index]

                # Execute the step
                result = await self._execute_single_step(step)
                self.results.append(result)

                # Check if this step requires approval
                if self.require_approval and result.requires_approval:
                    self.status = WorkflowStatus.WAITING_APPROVAL
                    self.pending_approval_step = step
                    if self.on_approval_required:
                        try:
                            self.on_approval_required(step)
                        except Exception:
                            pass  # Ignore callback exceptions
                    return self.results

                # Handle step failure
                if not result.success:
                    await self._handle_step_failure(step, result)
                    if not self.continue_on_step_failure:
                        break

                self.current_step_index += 1

            # If we completed all steps successfully
            if self.current_step_index >= len(self.steps):
                self.status = WorkflowStatus.COMPLETED
                self._end_time = time.time()
                if self.on_workflow_completed:
                    try:
                        self.on_workflow_completed(self.results)
                    except Exception:
                        pass  # Ignore callback exceptions

            return self.results

        except Exception as e:
            self.status = WorkflowStatus.FAILED
            error_result = WorkflowResult(
                success=False,
                step=f"step_{self.current_step_index}",
                data={},
                error="execution_error",
                message=f"Workflow execution failed: {e}",
            )
            self.results.append(error_result)
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e

    async def approve_and_continue(
        self, approval_data: dict[str, Any] | None = None
    ) -> list[WorkflowResult]:
        """
        Approve pending step and continue execution.

        Args:
            approval_data: Additional data from the approval

        Returns:
            List of step results from continuation

        Raises:
            WorkflowExecutionError: If workflow is not waiting for approval
        """
        if self.status != WorkflowStatus.WAITING_APPROVAL:
            raise WorkflowExecutionError(f"Workflow {self.workflow_id} is not waiting for approval")

        self.approval_data = approval_data or {}
        self.pending_approval_step = None

        # Move to next step since current step was approved
        self.current_step_index += 1

        # Continue from where we left off
        return await self._continue_execution()

    async def reject_and_cancel(self, reason: str | None = None) -> list[WorkflowResult]:
        """
        Reject pending approval and cancel workflow.

        Args:
            reason: Reason for rejection

        Returns:
            List of current step results

        Raises:
            WorkflowExecutionError: If workflow is not waiting for approval
        """
        if self.status != WorkflowStatus.WAITING_APPROVAL:
            raise WorkflowExecutionError(f"Workflow {self.workflow_id} is not waiting for approval")

        self.status = WorkflowStatus.CANCELLED

        # Add rejection result
        rejection_result = WorkflowResult(
            success=False,
            step=self.pending_approval_step or "approval",
            data={"reason": reason or "Approval rejected"},
            error="approval_rejected",
            message=f"Workflow cancelled: {reason or 'Approval rejected'}",
        )
        self.results.append(rejection_result)

        self.pending_approval_step = None
        return self.results

    async def _continue_execution(self) -> list[WorkflowResult]:
        """Continue execution from current position (used for approval continuations)."""
        self.status = WorkflowStatus.RUNNING

        try:
            # Execute steps from current position
            while self.current_step_index < len(self.steps):
                step = self.steps[self.current_step_index]

                # Execute the step
                result = await self._execute_single_step(step)
                self.results.append(result)

                # Check if this step requires approval
                if self.require_approval and result.requires_approval:
                    self.status = WorkflowStatus.WAITING_APPROVAL
                    self.pending_approval_step = step
                    if self.on_approval_required:
                        try:
                            self.on_approval_required(step)
                        except Exception:
                            pass  # Ignore callback exceptions
                    return self.results

                # Handle step failure
                if not result.success:
                    await self._handle_step_failure(step, result)
                    if not self.continue_on_step_failure:
                        break

                self.current_step_index += 1

            # If we completed all steps successfully
            if self.current_step_index >= len(self.steps):
                self.status = WorkflowStatus.COMPLETED
                self._end_time = time.time()
                if self.on_workflow_completed:
                    try:
                        self.on_workflow_completed(self.results)
                    except Exception:
                        pass  # Ignore callback exceptions

            return self.results

        except Exception as e:
            self.status = WorkflowStatus.FAILED
            error_result = WorkflowResult(
                success=False,
                step=f"step_{self.current_step_index}",
                data={},
                error="execution_error",
                message=f"Workflow execution failed: {e}",
            )
            self.results.append(error_result)
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e

    async def _execute_single_step(self, step: StepName) -> WorkflowResult:
        """Execute a single step with timing and callbacks."""
        start_time = time.time()

        # Call step started callback (ignore exceptions)
        if self.on_step_started:
            try:
                self.on_step_started(step)
            except Exception:
                pass  # Ignore callback exceptions

        try:
            result = await self.execute_step(step)
            result.execution_time = time.time() - start_time

            # Call step completed callback (ignore exceptions)
            if self.on_step_completed:
                try:
                    self.on_step_completed(result)
                except Exception:
                    pass  # Ignore callback exceptions

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_result = WorkflowResult(
                success=False,
                step=step,
                data={},
                error="step_execution_error",
                message=f"Step {step} failed: {e}",
                execution_time=execution_time,
            )

            # Call step completed callback (ignore exceptions)
            if self.on_step_completed:
                try:
                    self.on_step_completed(error_result)
                except Exception:
                    pass  # Ignore callback exceptions

            return error_result

    async def _handle_step_failure(self, step: StepName, result: WorkflowResult) -> None:
        """Handle failure of a workflow step."""
        if self.continue_on_step_failure:
            # Just return, don't increment - the main loop will handle it
            return

        if self.rollback_on_failure:
            if self.on_rollback_started:
                try:
                    self.on_rollback_started(step)
                except Exception:
                    pass  # Ignore callback exceptions
            await self._rollback_steps()

        self.status = WorkflowStatus.FAILED

    async def _rollback_steps(self) -> None:
        """
        Rollback successfully completed steps.

        Override this method to implement custom rollback logic.
        """
        # Default implementation: mark rollback attempt
        for i, result in enumerate(reversed(self.results[:-1])):  # Skip the failed step
            if result.success:
                rollback_step = f"rollback_{result.step}"
                try:
                    rollback_result = await self.execute_step(rollback_step)
                    self.results.append(rollback_result)
                except NotImplementedError:
                    # Rollback step not implemented - just log it
                    rollback_result = WorkflowResult(
                        success=True,
                        step=rollback_step,
                        data={"original_step": result.step},
                        message=f"No rollback implementation for {result.step}",
                    )
                    self.results.append(rollback_result)

    def to_dict(self) -> dict[str, Any]:
        """Convert workflow to dictionary for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "steps": self.steps,
            "metadata": self.metadata,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "results": [r.to_dict() for r in self.results],
            "pending_approval_step": self.pending_approval_step,
            "approval_data": self.approval_data,
            "rollback_on_failure": self.rollback_on_failure,
            "continue_on_step_failure": self.continue_on_step_failure,
            "require_approval": self.require_approval,
            "start_time": self._start_time,
            "end_time": self._end_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workflow":
        """Create workflow from dictionary."""
        workflow = cls(
            workflow_id=data["workflow_id"], steps=data["steps"], metadata=data["metadata"]
        )

        workflow.status = WorkflowStatus(data["status"])
        workflow.current_step_index = data["current_step_index"]
        workflow.results = [WorkflowResult.from_dict(r) for r in data["results"]]
        workflow.pending_approval_step = data["pending_approval_step"]
        workflow.approval_data = data["approval_data"]
        workflow.rollback_on_failure = data["rollback_on_failure"]
        workflow.continue_on_step_failure = data["continue_on_step_failure"]
        workflow.require_approval = data["require_approval"]
        workflow._start_time = data["start_time"]
        workflow._end_time = data["end_time"]

        return workflow

    @property
    def execution_time(self) -> float | None:
        """Get total execution time if completed."""
        if self._start_time and self._end_time:
            return self._end_time - self._start_time
        return None

    @property
    def is_completed(self) -> bool:
        """Check if workflow is completed."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.status == WorkflowStatus.FAILED

    @property
    def is_waiting_approval(self) -> bool:
        """Check if workflow is waiting for approval."""
        return self.status == WorkflowStatus.WAITING_APPROVAL
