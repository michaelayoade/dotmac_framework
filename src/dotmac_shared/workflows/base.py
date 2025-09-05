"""
Base workflow classes and interfaces.

Provides the foundation for all workflow implementations in the DotMac platform.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .exceptions import WorkflowError, WorkflowTimeoutError, WorkflowTransientError, WorkflowValidationError


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class WorkflowResult:
    """Result of a workflow step or complete workflow execution."""

    success: bool
    step_name: str
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    message: Optional[str] = None
    execution_time: Optional[float] = None
    code: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkflowStep:
    """Individual workflow step definition."""

    name: str
    description: str = ""
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    rollback_enabled: bool = True
    prerequisites: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseWorkflow(ABC):
    """
    Base class for all workflow implementations.

    Provides common workflow functionality including:
    - Step execution and orchestration
    - Error handling and rollback
    - Progress tracking
    - Async execution support
    """

    def __init__(
        self,
        workflow_id: str,
        workflow_type: str,
        steps: list[str],
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.workflow_type = workflow_type
        self.steps = steps
        self.metadata = metadata or {}

        # Execution state
        self.current_step_index = 0
        self.status = WorkflowStatus.PENDING
        self.results: list[WorkflowResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.created_at = datetime.now(timezone.utc)

        # Configuration
        self.rollback_on_failure = True
        self.continue_on_step_failure = False

        # Callbacks
        self.on_step_started: Optional[Callable] = None
        self.on_step_completed: Optional[Callable] = None
        self.on_workflow_completed: Optional[Callable] = None

    @abstractmethod
    async def execute_step(self, step_name: str) -> WorkflowResult:
        """
        Execute a single workflow step.

        Args:
            step_name: The name of the step to execute

        Returns:
            WorkflowResult with execution details
        """
        pass

    async def execute(self) -> list[WorkflowResult]:
        """
        Execute the complete workflow.

        Returns:
            List of WorkflowResult for each executed step
        """
        if self.status == WorkflowStatus.RUNNING:
            raise WorkflowError("Workflow is already running")

        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now(timezone.utc)

        try:
            for i, step_name in enumerate(self.steps):
                self.current_step_index = i

                # Execute step with error handling
                result = await self._execute_step_with_handling(step_name)
                self.results.append(result)

                # Handle step failure
                if not result.success:
                    if self.rollback_on_failure:
                        await self._rollback_executed_steps()

                    if not self.continue_on_step_failure:
                        self.status = WorkflowStatus.FAILED
                        break

            # Mark as completed if we made it through all steps
            if self.status == WorkflowStatus.RUNNING:
                self.status = WorkflowStatus.COMPLETED

        except Exception as e:
            # Handle unexpected errors
            error_result = WorkflowResult(
                success=False,
                step_name="workflow_execution",
                error=str(e),
                message=f"Workflow execution failed: {str(e)}",
            )
            self.results.append(error_result)
            self.status = WorkflowStatus.FAILED

            if self.rollback_on_failure:
                await self._rollback_executed_steps()

        finally:
            self.end_time = datetime.now(timezone.utc)

            if self.on_workflow_completed:
                await self.on_workflow_completed(self)

        return self.results

    async def _execute_step_with_handling(self, step_name: str) -> WorkflowResult:
        """Execute a step with proper error handling and callbacks."""
        start_time = datetime.now(timezone.utc)

        try:
            if self.on_step_started:
                await self.on_step_started(step_name, self)

            # Optional per-step timeout via metadata timeouts dict
            timeout: Optional[float] = None
            timeouts = self.metadata.get("timeouts") if isinstance(self.metadata, dict) else None
            if isinstance(timeouts, dict):
                maybe = timeouts.get(step_name)
                if isinstance(maybe, (int, float)) and maybe > 0:
                    timeout = float(maybe)

            if timeout:
                try:
                    result = await asyncio.wait_for(self.execute_step(step_name), timeout=timeout)
                except asyncio.TimeoutError as e:
                    raise WorkflowTimeoutError(f"Step timed out after {timeout}s") from e
            else:
                result = await self.execute_step(step_name)

            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.execution_time = execution_time

            if self.on_step_completed:
                await self.on_step_completed(step_name, result, self)

            return result

        except WorkflowValidationError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Step validation failed: {str(e)}",
                execution_time=execution_time,
                code="validation_error",
            )
        except WorkflowTimeoutError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Step execution timed out: {str(e)}",
                execution_time=execution_time,
                code="timeout",
            )
        except WorkflowTransientError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Step transient failure: {str(e)}",
                execution_time=execution_time,
                code="transient_error",
            )
        except WorkflowError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Step execution failed: {str(e)}",
                execution_time=execution_time,
                code="workflow_error",
            )
        except asyncio.CancelledError:
            # Bubble up cancellations
            raise
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Step execution failed: {str(e)}",
                execution_time=execution_time,
                code="unexpected_error",
            )

    async def _rollback_executed_steps(self):
        """Rollback previously executed steps in reverse order."""
        rollback_steps = self.results[:-1]  # Exclude the failed step
        rollback_steps.reverse()

        for result in rollback_steps:
            if result.success:
                try:
                    rollback_result = await self.rollback_step(result.step_name)
                    if not rollback_result.success:
                        # Log rollback failure but continue
                        pass
                except Exception:
                    # Log rollback error but continue with other rollbacks
                    pass

    async def rollback_step(self, step_name: str) -> WorkflowResult:
        """
        Rollback a specific workflow step.

        Override this method to provide step-specific rollback logic.

        Args:
            step_name: The name of the step to rollback

        Returns:
            WorkflowResult indicating rollback success/failure
        """
        return WorkflowResult(
            success=True,
            step_name=f"rollback_{step_name}",
            message=f"No rollback needed for step: {step_name}",
        )

    async def pause(self):
        """Pause workflow execution."""
        if self.status == WorkflowStatus.RUNNING:
            self.status = WorkflowStatus.PAUSED

    async def resume(self):
        """Resume paused workflow execution."""
        if self.status == WorkflowStatus.PAUSED:
            self.status = WorkflowStatus.RUNNING
            # Continue execution from current step
            remaining_steps = self.steps[self.current_step_index :]
            for step_name in remaining_steps:
                result = await self._execute_step_with_handling(step_name)
                self.results.append(result)

                if not result.success and not self.continue_on_step_failure:
                    self.status = WorkflowStatus.FAILED
                    break

            if self.status == WorkflowStatus.RUNNING:
                self.status = WorkflowStatus.COMPLETED

    async def cancel(self):
        """Cancel workflow execution."""
        self.status = WorkflowStatus.CANCELLED
        self.end_time = datetime.now(timezone.utc)

    @property
    def is_completed(self) -> bool:
        """Check if workflow is completed."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.status == WorkflowStatus.FAILED

    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self.status == WorkflowStatus.RUNNING

    @property
    def execution_time(self) -> Optional[float]:
        """Get total workflow execution time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def progress_percentage(self) -> float:
        """Get workflow progress as percentage (0.0 to 1.0)."""
        if not self.steps:
            return 0.0
        return len(self.results) / len(self.steps)

    def get_step_result(self, step_name: str) -> Optional[WorkflowResult]:
        """Get result for a specific step."""
        for result in self.results:
            if result.step_name == step_name:
                return result
        return None

    def get_failed_steps(self) -> list[WorkflowResult]:
        """Get all failed step results."""
        return [result for result in self.results if not result.success]

    def to_dict(self) -> dict[str, Any]:
        """Convert workflow to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "steps": self.steps,
            "current_step_index": self.current_step_index,
            "progress_percentage": self.progress_percentage,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "results": [
                {
                    "success": r.success,
                    "step_name": r.step_name,
                    "data": r.data,
                    "error": r.error,
                    "message": r.message,
                    "execution_time": r.execution_time,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.results
            ],
            "metadata": self.metadata,
        }
