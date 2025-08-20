"""
Client SDKs for the DotMac Core Operations package.

This module provides client SDKs for interacting with the operations platform
remotely via HTTP APIs.
"""

from .operations_client import OperationsClient
from .workflow_client import WorkflowClient
from .task_client import TaskClient
from .automation_client import AutomationClient
from .scheduler_client import SchedulerClient
from .state_machine_client import StateMachineClient
from .saga_client import SagaClient
from .job_queue_client import JobQueueClient

__all__ = [
    "OperationsClient",
    "WorkflowClient",
    "TaskClient",
    "AutomationClient",
    "SchedulerClient",
    "StateMachineClient",
    "SagaClient",
    "JobQueueClient",
]
