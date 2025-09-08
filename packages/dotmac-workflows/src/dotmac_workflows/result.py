"""
Workflow execution results.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowResult:
    """Result of a workflow step execution."""

    success: bool
    step: str
    data: dict[str, Any]
    error: str | None = None
    message: str | None = None
    execution_time: float | None = None
    requires_approval: bool = False

    def __post_init__(self) -> None:
        """Validate result data."""
        if not isinstance(self.data, dict):
            raise TypeError("data must be a dictionary")
        if not isinstance(self.step, str) or not self.step:
            raise ValueError("step must be a non-empty string")

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "step": self.step,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "execution_time": self.execution_time,
            "requires_approval": self.requires_approval,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowResult":
        """Create result from dictionary."""
        return cls(
            success=data["success"],
            step=data["step"],
            data=data["data"],
            error=data.get("error"),
            message=data.get("message"),
            execution_time=data.get("execution_time"),
            requires_approval=data.get("requires_approval", False),
        )
