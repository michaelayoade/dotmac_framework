"""
Workflow status enumeration.
"""

from enum import Enum


class WorkflowStatus(Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"

    def __str__(self) -> str:
        return self.value
