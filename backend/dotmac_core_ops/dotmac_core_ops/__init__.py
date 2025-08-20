"""
DotMac Core Operations Package

A comprehensive operations plane SDK for workflow orchestration, task management,
automation, scheduling, state machines, sagas, and job queue orchestration.

This package provides:
- Workflow SDK for complex workflow orchestration
- Task SDK for distributed task management
- Automation Engine for rule-based automation
- Scheduler SDK for time-based operations
- State Machine SDK for state management
- Saga SDK for distributed transaction patterns
- Job Queue SDK for reliable job processing
- API layer for REST endpoints
- Client SDKs for easy integration
- Runtime components for deployment
"""

__version__ = "0.1.0"
__author__ = "DotMac Team"
__email__ = "team@dotmac.com"

# Core SDKs
from .sdks.workflow import WorkflowSDK, WorkflowDefinition, WorkflowExecution
from .sdks.task import TaskSDK, TaskDefinition, TaskExecution
from .sdks.automation import AutomationSDK, AutomationRule, AutomationEngine
from .sdks.scheduler import SchedulerSDK, ScheduleDefinition, JobScheduler
from .sdks.state_machine import StateMachineSDK, StateDefinition, StateMachine
from .sdks.saga import SagaSDK, SagaDefinition, SagaExecution
from .sdks.job_queue import JobQueueSDK, JobDefinition, JobExecution

# Contracts and common types
from .contracts.common_schemas import (
    ExecutionStatus,
    ExecutionResult,
    OperationMetadata,
    ResourceIdentifier,
)

# Client SDKs
from .client import (
    WorkflowClient,
    TaskClient,
    AutomationClient,
    SchedulerClient,
    StateMachineClient,
    SagaClient,
    JobQueueClient,
)

# Runtime components
from .runtime import create_ops_app, OpsConfig

__all__ = [
    # Core SDKs
    "WorkflowSDK",
    "WorkflowDefinition",
    "WorkflowExecution",
    "TaskSDK",
    "TaskDefinition",
    "TaskExecution",
    "AutomationSDK",
    "AutomationRule",
    "AutomationEngine",
    "SchedulerSDK",
    "ScheduleDefinition",
    "JobScheduler",
    "StateMachineSDK",
    "StateDefinition",
    "StateMachine",
    "SagaSDK",
    "SagaDefinition",
    "SagaExecution",
    "JobQueueSDK",
    "JobDefinition",
    "JobExecution",
    # Common types
    "ExecutionStatus",
    "ExecutionResult",
    "OperationMetadata",
    "ResourceIdentifier",
    # Client SDKs
    "WorkflowClient",
    "TaskClient",
    "AutomationClient",
    "SchedulerClient",
    "StateMachineClient",
    "SagaClient",
    "JobQueueClient",
    # Runtime
    "create_ops_app",
    "OpsConfig",
]
