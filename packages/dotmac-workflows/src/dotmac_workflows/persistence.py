"""
Workflow persistence interfaces and implementations.
"""

from typing import Any, Protocol

from .types import WorkflowId


class WorkflowStateStore(Protocol):
    """Protocol for workflow state persistence."""

    async def save(self, workflow: "Workflow") -> None:
        """
        Save workflow state to persistent storage.

        Args:
            workflow: The workflow instance to save

        Raises:
            PersistenceError: If save operation fails
        """
        ...

    async def load(self, workflow_id: WorkflowId) -> "Workflow | None":
        """
        Load workflow state from persistent storage.

        Args:
            workflow_id: Unique identifier for the workflow

        Returns:
            Workflow instance if found, None otherwise

        Raises:
            PersistenceError: If load operation fails
        """
        ...

    async def delete(self, workflow_id: WorkflowId) -> bool:
        """
        Delete workflow state from persistent storage.

        Args:
            workflow_id: Unique identifier for the workflow

        Returns:
            True if workflow was deleted, False if not found

        Raises:
            PersistenceError: If delete operation fails
        """
        ...


class InMemoryStateStore:
    """Simple in-memory implementation for testing."""

    def __init__(self) -> None:
        self._store: dict[WorkflowId, dict[str, Any]] = {}

    async def save(self, workflow: "Workflow") -> None:
        """Save workflow to memory."""
        if not workflow.workflow_id:
            raise ValueError("Workflow must have an ID to be saved")

        self._store[workflow.workflow_id] = workflow.to_dict()

    async def load(self, workflow_id: WorkflowId) -> "Workflow | None":
        """Load workflow from memory."""
        data = self._store.get(workflow_id)
        if not data:
            return None

        # Import here to avoid circular imports
        from .base import Workflow

        return Workflow.from_dict(data)

    async def delete(self, workflow_id: WorkflowId) -> bool:
        """Delete workflow from memory."""
        if workflow_id in self._store:
            del self._store[workflow_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all stored workflows."""
        self._store.clear()


# Forward reference resolution
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Workflow
