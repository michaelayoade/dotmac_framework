"""
Workflow-specific exceptions.
"""


class WorkflowError(Exception):
    """Base exception for workflow-related errors."""

    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails."""

    pass


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails."""

    pass


class WorkflowTimeoutError(WorkflowError):
    """Raised when workflow execution times out."""

    pass


class WorkflowStepError(WorkflowError):
    """Raised when a specific workflow step fails."""

    def __init__(self, step_name: str, message: str, original_error: Exception = None):
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Step '{step_name}' failed: {message}")


class WorkflowRollbackError(WorkflowError):
    """Raised when workflow rollback fails."""

    def __init__(self, step_name: str, message: str):
        self.step_name = step_name
        super().__init__(f"Rollback failed for step '{step_name}': {message}")
