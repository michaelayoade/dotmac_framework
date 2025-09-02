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

from .router import router
from .service import TaskManagementService
from .schemas import (
    TaskStatusResponse, WorkflowStatusResponse, QueueStatsResponse,
    WorkerStatsResponse, SystemHealthResponse, TaskCancelRequest,
    TaskRetryRequest, BulkTaskOperationRequest, TaskQueryRequest
)
from .models import (
    TaskOperationAuditLog, TaskMetricsSnapshot, SystemHealthSnapshot,
    TenantTaskQuota, TaskTemplate, TaskScheduleRule
)

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
    "TaskScheduleRule"
]