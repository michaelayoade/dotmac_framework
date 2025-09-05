"""
Base business workflow classes and interfaces.
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class BusinessWorkflowStatus(str, Enum):
    """Business workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class BusinessWorkflowResult:
    """Result of a business workflow step or complete workflow execution."""

    success: bool
    step_name: str
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requires_approval: bool = False
    approval_data: dict[str, Any] = field(default_factory=dict)


class BusinessWorkflow(ABC):
    """
    Base class for all business workflow implementations.

    Extends basic workflow functionality with business-specific features:
    - Approval gates and human intervention
    - Business rule validation
    - Integration with business systems
    - Audit trails and compliance tracking
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        workflow_type: str = "business_workflow",
        steps: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.workflow_type = workflow_type
        self.steps = steps or []
        self.metadata = metadata or {}
        self.tenant_id = tenant_id

        # Execution state
        self.current_step_index = 0
        self.status = BusinessWorkflowStatus.PENDING
        self.results: list[BusinessWorkflowResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.created_at = datetime.now(timezone.utc)

        # Business context
        self.db_session: Optional[AsyncSession] = None
        self.business_context: dict[str, Any] = {}

        # Configuration
        self.rollback_on_failure = True
        self.continue_on_step_failure = False
        self.require_approval = False
        self.approval_threshold: Optional[float] = None  # For financial workflows

        # Callbacks
        self.on_step_started: Optional[Callable] = None
        self.on_step_completed: Optional[Callable] = None
        self.on_workflow_completed: Optional[Callable] = None
        self.on_approval_required: Optional[Callable] = None

    def set_business_context(
        self, context: dict[str, Any], db_session: AsyncSession = None
    ):
        """Set the business context for this workflow."""
        self.business_context = context
        if db_session:
            self.db_session = db_session

    @abstractmethod
    async def execute_step(self, step_name: str) -> BusinessWorkflowResult:
        """
        Execute a single business workflow step.

        Args:
            step_name: The name of the step to execute

        Returns:
            BusinessWorkflowResult with execution details
        """
        pass

    @abstractmethod
    async def validate_business_rules(self) -> BusinessWorkflowResult:
        """
        Validate business rules before workflow execution.

        Returns:
            BusinessWorkflowResult indicating validation success/failure
        """
        pass

    async def execute(self) -> list[BusinessWorkflowResult]:
        """
        Execute the complete business workflow with business logic.

        Returns:
            List of BusinessWorkflowResult for each executed step
        """
        if self.status == BusinessWorkflowStatus.RUNNING:
            raise ValueError("Workflow is already running")

        # Validate business rules first
        validation_result = await self.validate_business_rules()
        if not validation_result.success:
            self.results.append(validation_result)
            self.status = BusinessWorkflowStatus.FAILED
            return self.results

        self.status = BusinessWorkflowStatus.RUNNING
        self.start_time = datetime.now(timezone.utc)

        try:
            for i, step_name in enumerate(self.steps):
                self.current_step_index = i

                # Execute step with error handling
                result = await self._execute_step_with_handling(step_name)
                self.results.append(result)

                # Handle approval requirements
                if result.requires_approval:
                    self.status = BusinessWorkflowStatus.WAITING_APPROVAL
                    if self.on_approval_required:
                        await self.on_approval_required(self, result)
                    return self.results  # Pause workflow for approval

                # Handle step failure
                if not result.success:
                    if self.rollback_on_failure:
                        await self._rollback_executed_steps()

                    if not self.continue_on_step_failure:
                        self.status = BusinessWorkflowStatus.FAILED
                        break

            # Mark as completed if we made it through all steps
            if self.status == BusinessWorkflowStatus.RUNNING:
                self.status = BusinessWorkflowStatus.COMPLETED

        except Exception as e:
            # Handle unexpected errors
            error_result = BusinessWorkflowResult(
                success=False,
                step_name="workflow_execution",
                error=str(e),
                message=f"Business workflow execution failed: {str(e)}",
            )
            self.results.append(error_result)
            self.status = BusinessWorkflowStatus.FAILED

            if self.rollback_on_failure:
                await self._rollback_executed_steps()

        finally:
            self.end_time = datetime.now(timezone.utc)

            if self.on_workflow_completed:
                await self.on_workflow_completed(self)

        return self.results

    async def approve_and_continue(
        self, approval_data: Optional[dict[str, Any]] = None
    ) -> list[BusinessWorkflowResult]:
        """
        Approve current step and continue workflow execution.

        Args:
            approval_data: Additional data from approval process

        Returns:
            Updated list of workflow results
        """
        if self.status != BusinessWorkflowStatus.WAITING_APPROVAL:
            raise ValueError("Workflow is not waiting for approval")

        # Update the last result with approval data
        if self.results:
            self.results[-1].data.update(approval_data or {})
            self.results[-1].message += " [APPROVED]"

        self.status = BusinessWorkflowStatus.RUNNING

        # Continue execution from current step + 1
        remaining_steps = self.steps[self.current_step_index + 1 :]

        for step_name in remaining_steps:
            self.current_step_index += 1

            result = await self._execute_step_with_handling(step_name)
            self.results.append(result)

            # Handle approval requirements
            if result.requires_approval:
                self.status = BusinessWorkflowStatus.WAITING_APPROVAL
                if self.on_approval_required:
                    await self.on_approval_required(self, result)
                return self.results

            if not result.success and not self.continue_on_step_failure:
                self.status = BusinessWorkflowStatus.FAILED
                break

        if self.status == BusinessWorkflowStatus.RUNNING:
            self.status = BusinessWorkflowStatus.COMPLETED

        return self.results

    async def reject_and_cancel(
        self, rejection_reason: Optional[str] = None
    ) -> list[BusinessWorkflowResult]:
        """
        Reject current approval and cancel workflow.

        Args:
            rejection_reason: Reason for rejection

        Returns:
            Updated list of workflow results
        """
        if self.status != BusinessWorkflowStatus.WAITING_APPROVAL:
            raise ValueError("Workflow is not waiting for approval")

        # Update the last result with rejection
        if self.results:
            self.results[-1].success = False
            self.results[-1].error = rejection_reason or "Approval rejected"
            self.results[-1].message += " [REJECTED]"

        self.status = BusinessWorkflowStatus.CANCELLED
        self.end_time = datetime.now(timezone.utc)

        # Rollback executed steps
        if self.rollback_on_failure:
            await self._rollback_executed_steps()

        return self.results

    async def _execute_step_with_handling(
        self, step_name: str
    ) -> BusinessWorkflowResult:
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

            return BusinessWorkflowResult(
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

    async def rollback_step(self, step_name: str) -> BusinessWorkflowResult:
        """
        Rollback a specific business workflow step.

        Override this method to provide step-specific rollback logic.

        Args:
            step_name: The name of the step to rollback

        Returns:
            BusinessWorkflowResult indicating rollback success/failure
        """
        return BusinessWorkflowResult(
            success=True,
            step_name=f"rollback_{step_name}",
            message=f"No rollback needed for step: {step_name}",
        )

    @property
    def is_completed(self) -> bool:
        """Check if workflow is completed."""
        return self.status == BusinessWorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.status == BusinessWorkflowStatus.FAILED

    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self.status == BusinessWorkflowStatus.RUNNING

    @property
    def is_waiting_approval(self) -> bool:
        """Check if workflow is waiting for approval."""
        return self.status == BusinessWorkflowStatus.WAITING_APPROVAL

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

    def to_dict(self) -> dict[str, Any]:
        """Convert business workflow to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "steps": self.steps,
            "current_step_index": self.current_step_index,
            "progress_percentage": self.progress_percentage,
            "execution_time": self.execution_time,
            "tenant_id": self.tenant_id,
            "business_context": self.business_context,
            "require_approval": self.require_approval,
            "approval_threshold": self.approval_threshold,
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
                    "requires_approval": r.requires_approval,
                    "approval_data": r.approval_data,
                }
                for r in self.results
            ],
            "metadata": self.metadata,
        }
