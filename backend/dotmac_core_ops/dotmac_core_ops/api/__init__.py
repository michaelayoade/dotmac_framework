"""
API layer for the DotMac Core Operations package.

This module provides REST API endpoints for all operations SDKs including
workflows, tasks, automation, scheduling, state machines, sagas, and job queues.
"""

from .workflows import router as workflows_router
from .tasks import router as tasks_router
from .automation import router as automation_router
from .scheduler import router as scheduler_router
from .state_machines import router as state_machines_router
from .sagas import router as sagas_router
from .job_queues import router as job_queues_router
from .health import router as health_router

__all__ = [
    "workflows_router",
    "tasks_router",
    "automation_router",
    "scheduler_router",
    "state_machines_router",
    "sagas_router",
    "job_queues_router",
    "health_router",
]
