"""
Task Management Module

Provides comprehensive task management and monitoring capabilities for the
DotMac Management Platform, including background task processing, workflow
orchestration, and real-time monitoring.

This module includes:
- RESTful API endpoints for task management
- WebSocket endpoints for real-time monitoring
- Comprehensive data models and schemas
- Business logic services
- Integration with the shared task system
"""

from .models import (
    SystemHealthSnapshot,
    TaskMetricsSnapshot,
    TaskOperationAuditLog,
    TaskScheduleRule,
    TaskTemplate,
    TenantTaskQuota,
)
from .router import router
from .schemas import (
    BulkTaskOperationRequest,
    QueueStatsResponse,
    SystemHealthResponse,
    TaskCancelRequest,
    TaskQueryRequest,
    TaskRetryRequest,
    TaskStatusResponse,
    WorkerStatsResponse,
    WorkflowStatusResponse,
)
from .service import TaskManagementService

__all__ = [
    # Main router
    "router",
    # Service layer
    "TaskManagementService",
    # API schemas
    "TaskStatusResponse",
    "WorkflowStatusResponse",
    "QueueStatsResponse",
    "WorkerStatsResponse",
    "SystemHealthResponse",
    "TaskCancelRequest",
    "TaskRetryRequest",
    "BulkTaskOperationRequest",
    "TaskQueryRequest",
    # Data models
    "TaskOperationAuditLog",
    "TaskMetricsSnapshot",
    "SystemHealthSnapshot",
    "TenantTaskQuota",
    "TaskTemplate",
    "TaskScheduleRule",
]
