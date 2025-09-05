"""
Base workflow classes for ticket automation.
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import Ticket


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
    error: str | None = None
    message: str | None = None
    execution_time: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TicketWorkflow(ABC):
    """
    Base class for ticket-related workflows.

    Provides common functionality for automating ticket processes
    including assignment, escalation, and lifecycle management.
    """

    def __init__(
        self,
        workflow_id: str | None = None,
        workflow_type: str = "ticket_workflow",
        steps: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.workflow_type = workflow_type
        self.steps = steps or []
        self.metadata = metadata or {}

        # Execution state
        self.current_step_index = 0
        self.status = WorkflowStatus.PENDING
        self.results: list[WorkflowResult] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.created_at = datetime.now(timezone.utc)

        # Ticket context
        self.ticket: Ticket | None = None
        self.tenant_id: str | None = None
        self.db_session: AsyncSession | None = None

        # Configuration
        self.rollback_on_failure = True
        self.continue_on_step_failure = False

        # Callbacks
        self.on_step_started: Callable | None = None
        self.on_step_completed: Callable | None = None
        self.on_workflow_completed: Callable | None = None

    def set_ticket_context(
        self, ticket: Ticket, tenant_id: str, db_session: AsyncSession
    ):
        """Set the ticket context for this workflow."""
        self.ticket = ticket
        self.tenant_id = tenant_id
        self.db_session = db_session

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
            raise ValueError("Workflow is already running")

        if not self.ticket or not self.db_session:
            raise ValueError("Ticket context must be set before execution")

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

            result = await self.execute_step(step_name)

            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.execution_time = execution_time

            if self.on_step_completed:
                await self.on_step_completed(step_name, result, self)

            return result

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return WorkflowResult(
                success=False,
                step_name=step_name,
                error=str(e),
                message=f"Step execution failed: {str(e)}",
                execution_time=execution_time,
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

    async def should_trigger(self, ticket: Ticket) -> bool:
        """
        Determine if this workflow should be triggered for a given ticket.

        Override this method to implement workflow triggering logic.

        Args:
            ticket: The ticket to evaluate

        Returns:
            True if workflow should trigger, False otherwise
        """
        return True

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
    def execution_time(self) -> float | None:
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
            "ticket_id": self.ticket.id if self.ticket else None,
            "ticket_number": self.ticket.ticket_number if self.ticket else None,
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
