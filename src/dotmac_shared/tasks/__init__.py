"""
DotMac Comprehensive Background Task Processing System

This module provides a production-ready background task processing system with:
- Redis-based task queuing and distributed processing
- Async task execution with retry logic and failure handling
- Complex workflow orchestration for multi-step processes
- Task monitoring, logging, and progress tracking
- Task prioritization and rate limiting
- Webhook and notification systems for task completion

Key Components:
- TaskEngine: Core task execution and queuing engine
- TaskQueue: Redis-based distributed task queue
- WorkflowOrchestrator: Multi-step process orchestration
- TaskMonitor: Task monitoring and progress tracking
- TaskScheduler: Cron-like task scheduling
- TaskWorker: Distributed worker management
"""

from .engine import TaskEngine, Task, TaskResult, TaskStatus, TaskPriority
from .queue import TaskQueue, RedisTaskQueue
from .scheduler import TaskScheduler, CronSchedule
from .worker import TaskWorker, WorkerManager
from .monitor import TaskMonitor, TaskMetrics
from .workflow import WorkflowOrchestrator, WorkflowStep, WorkflowStatus
from .notifications import TaskNotificationService, NotificationChannel
from .decorators import (
    task,
    scheduled_task,
    high_priority_task,
    background_task,
    retry_on_failure
)

__all__ = [
    # Core Engine
    'TaskEngine',
    'Task',
    'TaskResult', 
    'TaskStatus',
    'TaskPriority',
    
    # Queue Management
    'TaskQueue',
    'RedisTaskQueue',
    
    # Scheduling
    'TaskScheduler',
    'CronSchedule',
    
    # Workers
    'TaskWorker',
    'WorkerManager',
    
    # Monitoring
    'TaskMonitor',
    'TaskMetrics',
    
    # Workflows
    'WorkflowOrchestrator',
    'WorkflowStep',
    'WorkflowStatus',
    
    # Notifications
    'TaskNotificationService',
    'NotificationChannel',
    
    # Decorators
    'task',
    'scheduled_task',
    'high_priority_task',
    'background_task',
    'retry_on_failure',
]