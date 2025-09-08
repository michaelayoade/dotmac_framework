"""
dotmac-workflows: Base workflow engine for business processes.

This package provides core workflow types for building business processes with support for:
- Sequential step execution
- Approval workflows
- Rollback on failure
- Resumable execution
- Pluggable persistence

Example:
    from dotmac_workflows import Workflow, WorkflowResult

    class MyWorkflow(Workflow):
        async def execute_step(self, step: str) -> WorkflowResult:
            if step == "validate":
                return WorkflowResult(success=True, step=step, data={"valid": True})
            return WorkflowResult(success=False, step=step, error="unknown_step")

    workflow = MyWorkflow(steps=["validate"])
    results = await workflow.execute()
"""

from .base import Workflow, WorkflowConfigurationError, WorkflowError, WorkflowExecutionError
from .persistence import InMemoryStateStore, WorkflowStateStore
from .result import WorkflowResult
from .status import WorkflowStatus
from .types import AsyncWorkflowCallback, StepName, WorkflowCallback, WorkflowId

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

__all__ = [
    # Core classes
    "Workflow",
    "WorkflowResult",
    "WorkflowStatus",
    # Exceptions
    "WorkflowError",
    "WorkflowExecutionError",
    "WorkflowConfigurationError",
    # Persistence
    "WorkflowStateStore",
    "InMemoryStateStore",
    # Types
    "WorkflowId",
    "StepName",
    "WorkflowCallback",
    "AsyncWorkflowCallback",
]
