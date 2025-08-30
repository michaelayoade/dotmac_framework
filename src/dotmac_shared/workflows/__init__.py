"""
Shared workflow base classes and utilities.

This module provides common workflow infrastructure used across
all DotMac workflow implementations.
"""

from .automation import (
    AutomationRule,
    AutomationWorkflow,
    TriggerType,
    create_automation_workflow,
    create_simple_rule,
)
from .base import BaseWorkflow, WorkflowResult, WorkflowStatus, WorkflowStep
from .exceptions import (
    WorkflowError,
    WorkflowExecutionError,
    WorkflowTimeoutError,
    WorkflowValidationError,
)
from .task import (
    SequentialTaskWorkflow,
    TaskWorkflow,
    create_sequential_workflow,
    create_task_workflow,
)

__all__ = [
    # Base classes
    "BaseWorkflow",
    "WorkflowResult",
    "WorkflowStep",
    "WorkflowStatus",
    # Exceptions
    "WorkflowError",
    "WorkflowValidationError",
    "WorkflowExecutionError",
    "WorkflowTimeoutError",
    # Task workflows
    "TaskWorkflow",
    "SequentialTaskWorkflow",
    "create_task_workflow",
    "create_sequential_workflow",
    # Automation workflows
    "AutomationWorkflow",
    "AutomationRule",
    "TriggerType",
    "create_automation_workflow",
    "create_simple_rule",
]
