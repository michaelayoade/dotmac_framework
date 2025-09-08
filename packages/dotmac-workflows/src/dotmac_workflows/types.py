"""
Common types for workflows.
"""

from collections.abc import Awaitable
from typing import Callable, Protocol

WorkflowId = str
StepName = str
WorkflowCallback = Callable[..., None]
AsyncWorkflowCallback = Callable[..., Awaitable[None]]


class WorkflowStateStore(Protocol):
    """Protocol for workflow state persistence."""

    async def save(self, workflow: "Workflow") -> None:
        """Save workflow state."""
        ...

    async def load(self, workflow_id: str) -> "Workflow | None":
        """Load workflow state by ID."""
        ...


# Forward reference - will be resolved when importing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Workflow
