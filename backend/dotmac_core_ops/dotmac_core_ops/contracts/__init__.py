"""
Contracts and schemas for the DotMac Core Operations package.

This module contains shared data models, schemas, and contracts used across
all operations SDKs including workflows, tasks, automation, scheduling,
state machines, sagas, and job queues.
"""

from .common_schemas import (
    ExecutionStatus,
    ExecutionResult,
    OperationMetadata,
    ResourceIdentifier,
    ExecutionContext,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    HealthStatus,
    MetricsData,
)

from .workflow_contract import (
    WorkflowDefinitionRequest,
    WorkflowDefinitionResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowStepDefinition,
    WorkflowStepExecution,
)

from .task_contract import (
    TaskDefinitionRequest,
    TaskDefinitionResponse,
    TaskExecutionRequest,
    TaskExecutionResponse,
    TaskDependency,
    TaskResult,
)

from .automation_contract import (
    AutomationRuleRequest,
    AutomationRuleResponse,
    AutomationTrigger,
    AutomationAction,
    AutomationCondition,
)

from .scheduler_contract import (
    ScheduleDefinitionRequest,
    ScheduleDefinitionResponse,
    ScheduleExecutionRequest,
    ScheduleExecutionResponse,
    CronExpression,
    ScheduleTrigger,
)

__all__ = [
    # Common schemas
    "ExecutionStatus",
    "ExecutionResult",
    "OperationMetadata",
    "ResourceIdentifier",
    "ExecutionContext",
    "RetryPolicy",
    "TimeoutPolicy",
    "ErrorInfo",
    "HealthStatus",
    "MetricsData",
    # Workflow contracts
    "WorkflowDefinitionRequest",
    "WorkflowDefinitionResponse",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "WorkflowStepDefinition",
    "WorkflowStepExecution",
    # Task contracts
    "TaskDefinitionRequest",
    "TaskDefinitionResponse",
    "TaskExecutionRequest",
    "TaskExecutionResponse",
    "TaskDependency",
    "TaskResult",
    # Automation contracts
    "AutomationRuleRequest",
    "AutomationRuleResponse",
    "AutomationTrigger",
    "AutomationAction",
    "AutomationCondition",
    # Scheduler contracts
    "ScheduleDefinitionRequest",
    "ScheduleDefinitionResponse",
    "ScheduleExecutionRequest",
    "ScheduleExecutionResponse",
    "CronExpression",
    "ScheduleTrigger",
]
