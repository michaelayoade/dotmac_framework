"""
Task Management Schema Definitions

Pydantic models for task management API request/response validation and
documentation. Provides comprehensive type safety and API documentation
for all task-related operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from dotmac.tasks import TaskPriority, TaskStatus


class TaskOperationType(str, Enum):
    """Available task operation types"""

    CANCEL = "cancel"
    RETRY = "retry"
    DELETE = "delete"
    PAUSE = "pause"
    RESUME = "resume"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SystemHealthStatus(str, Enum):
    """System health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


# Base Models
class TaskMetadata(BaseModel):
    """Task metadata information"""

    model_config = ConfigDict(extra="allow")

    task_type: str = Field(description="Type of task being executed")
    tenant_id: Optional[str] = Field(None, description="Associated tenant ID")
    user_id: Optional[str] = Field(None, description="User who initiated the task")
    source: Optional[str] = Field(None, description="Source system or component")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class ProgressInfo(BaseModel):
    """Task progress information"""

    percentage: float = Field(ge=0, le=100, description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current step being executed")
    total_steps: Optional[int] = Field(None, description="Total number of steps")
    completed_steps: int = Field(0, description="Number of completed steps")
    message: Optional[str] = Field(None, description="Current progress message")
    eta: Optional[datetime] = Field(None, description="Estimated completion time")


# Request Models
class TaskCancelRequest(BaseModel):
    """Request to cancel a task"""

    reason: Optional[str] = Field(None, description="Reason for cancellation")
    force: bool = Field(False, description="Force cancellation even if task is running")
    notify_user: bool = Field(True, description="Send notification to user")


class TaskRetryRequest(BaseModel):
    """Request to retry a failed task"""

    reset_retry_count: bool = Field(False, description="Reset the retry counter")
    priority: Optional[TaskPriority] = Field(None, description="New priority for retry")
    delay_seconds: Optional[int] = Field(None, description="Delay before retry")
    max_retries: Optional[int] = Field(None, description="Override max retry limit")


class BulkTaskOperationRequest(BaseModel):
    """Request for bulk task operations"""

    task_ids: list[str] = Field(
        min_items=1, max_items=100, description="Task IDs to operate on"
    )
    operation: TaskOperationType = Field(description="Operation to perform")
    parameters: Optional[dict[str, Any]] = Field(
        None, description="Operation-specific parameters"
    )
    confirm_destructive: bool = Field(
        False, description="Confirm destructive operations"
    )


class TaskQueryRequest(BaseModel):
    """Request to query tasks with filters"""

    status: Optional[list[TaskStatus]] = Field(
        None, description="Filter by task status"
    )
    priority: Optional[list[TaskPriority]] = Field(
        None, description="Filter by priority"
    )
    task_type: Optional[list[str]] = Field(None, description="Filter by task type")
    tenant_id: Optional[str] = Field(None, description="Filter by tenant ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    created_after: Optional[datetime] = Field(
        None, description="Tasks created after this time"
    )
    created_before: Optional[datetime] = Field(
        None, description="Tasks created before this time"
    )
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    order_by: str = Field("created_at", description="Field to order by")
    order_direction: str = Field(
        "desc", pattern="^(asc|desc)$", description="Order direction"
    )


# Response Models
class TaskStatusResponse(BaseModel):
    """Detailed task status information"""

    task_id: str = Field(description="Unique task identifier")
    status: TaskStatus = Field(description="Current task status")
    priority: TaskPriority = Field(description="Task priority level")
    task_type: str = Field(description="Type of task")

    # Timing information
    created_at: datetime = Field(description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Task completion timestamp"
    )
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Progress and results
    progress: ProgressInfo = Field(description="Task progress information")
    result: Optional[dict[str, Any]] = Field(None, description="Task execution result")
    error: Optional[dict[str, Any]] = Field(
        None, description="Error information if failed"
    )

    # Retry information
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum retry attempts allowed")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")

    # Metadata
    metadata: TaskMetadata = Field(description="Task metadata")
    dependencies: list[str] = Field(
        default_factory=list, description="Task dependencies"
    )

    # Resource usage
    execution_time: Optional[float] = Field(
        None, description="Total execution time in seconds"
    )
    memory_usage: Optional[int] = Field(None, description="Peak memory usage in bytes")


class WorkflowStepResponse(BaseModel):
    """Workflow step information"""

    step_id: str = Field(description="Step identifier")
    name: str = Field(description="Step name")
    status: TaskStatus = Field(description="Step execution status")
    order: int = Field(description="Step execution order")
    started_at: Optional[datetime] = Field(None, description="Step start timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Step completion timestamp"
    )
    result: Optional[dict[str, Any]] = Field(None, description="Step execution result")
    error: Optional[str] = Field(None, description="Step error message")
    dependencies: list[str] = Field(
        default_factory=list, description="Step dependencies"
    )


class WorkflowStatusResponse(BaseModel):
    """Detailed workflow status information"""

    workflow_id: str = Field(description="Unique workflow identifier")
    name: str = Field(description="Workflow name")
    status: WorkflowStatus = Field(description="Current workflow status")

    # Progress information
    current_step: Optional[str] = Field(None, description="Currently executing step")
    total_steps: int = Field(description="Total number of steps")
    completed_steps: int = Field(description="Number of completed steps")
    progress: float = Field(ge=0, le=100, description="Overall progress percentage")

    # Timing information
    created_at: datetime = Field(description="Workflow creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Workflow start timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Workflow completion timestamp"
    )

    # Steps information
    steps: list[WorkflowStepResponse] = Field(description="Workflow steps")

    # Metadata
    metadata: TaskMetadata = Field(description="Workflow metadata")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Workflow context"
    )


class QueueStatsResponse(BaseModel):
    """Queue statistics and metrics"""

    # Basic counts
    total_tasks: int = Field(description="Total tasks in system")
    pending_tasks: int = Field(description="Tasks waiting to be processed")
    running_tasks: int = Field(description="Currently executing tasks")
    completed_tasks: int = Field(description="Successfully completed tasks")
    failed_tasks: int = Field(description="Failed tasks")
    cancelled_tasks: int = Field(description="Cancelled tasks")
    dead_letter_tasks: int = Field(description="Tasks in dead letter queue")

    # Performance metrics
    average_processing_time: float = Field(
        description="Average task processing time in seconds"
    )
    throughput_per_minute: float = Field(description="Tasks processed per minute")
    error_rate: float = Field(ge=0, le=1, description="Error rate as decimal")

    # Priority breakdown
    queue_depth_by_priority: dict[str, int] = Field(
        description="Queue depth by priority level"
    )

    # Time-based metrics
    oldest_pending_task: Optional[datetime] = Field(
        None, description="Timestamp of oldest pending task"
    )
    newest_task: Optional[datetime] = Field(
        None, description="Timestamp of newest task"
    )


class WorkerInfo(BaseModel):
    """Individual worker information"""

    worker_id: str = Field(description="Unique worker identifier")
    status: str = Field(description="Worker status")
    current_task: Optional[str] = Field(
        None, description="Currently processing task ID"
    )
    tasks_processed: int = Field(description="Total tasks processed by this worker")
    uptime: float = Field(description="Worker uptime in seconds")
    last_heartbeat: datetime = Field(description="Last heartbeat timestamp")
    memory_usage: Optional[int] = Field(
        None, description="Current memory usage in bytes"
    )
    cpu_usage: Optional[float] = Field(None, description="Current CPU usage percentage")


class WorkerStatsResponse(BaseModel):
    """Worker pool statistics"""

    # Worker counts
    total_workers: int = Field(description="Total number of workers")
    active_workers: int = Field(description="Currently active workers")
    idle_workers: int = Field(description="Idle workers")
    unhealthy_workers: int = Field(description="Unhealthy workers")

    # Performance metrics
    average_task_time: float = Field(
        description="Average task processing time in seconds"
    )
    tasks_per_minute: float = Field(
        description="Tasks processed per minute across all workers"
    )
    worker_utilization: float = Field(
        ge=0, le=1, description="Worker utilization percentage"
    )

    # Worker details
    worker_details: list[WorkerInfo] = Field(
        description="Individual worker information"
    )

    # Resource usage
    total_memory_usage: Optional[int] = Field(
        None, description="Total memory usage across workers"
    )
    average_cpu_usage: Optional[float] = Field(
        None, description="Average CPU usage across workers"
    )


class SystemHealthResponse(BaseModel):
    """Comprehensive system health information"""

    # Overall status
    status: SystemHealthStatus = Field(description="Overall system health status")
    last_check: datetime = Field(description="Last health check timestamp")

    # Component health
    queue_health: dict[str, Any] = Field(description="Queue system health metrics")
    worker_health: dict[str, Any] = Field(description="Worker pool health metrics")
    redis_health: dict[str, Any] = Field(description="Redis connection health")
    database_health: dict[str, Any] = Field(description="Database health metrics")

    # Resource metrics
    memory_usage: dict[str, Any] = Field(description="System memory usage")
    disk_usage: dict[str, Any] = Field(description="Disk usage metrics")
    network_health: dict[str, Any] = Field(description="Network connectivity health")

    # Performance indicators
    error_rate: float = Field(ge=0, le=1, description="System-wide error rate")
    response_time: float = Field(description="Average response time in seconds")
    sla_compliance: float = Field(ge=0, le=1, description="SLA compliance percentage")

    # Alerts and warnings
    active_alerts: list[dict[str, Any]] = Field(description="Currently active alerts")
    warnings: list[str] = Field(description="System warnings")
    recommendations: list[str] = Field(description="Performance recommendations")


class TaskListResponse(BaseModel):
    """Paginated task list response"""

    tasks: list[TaskStatusResponse] = Field(description="List of tasks")
    total_count: int = Field(description="Total number of tasks matching filters")
    page_info: dict[str, Any] = Field(description="Pagination information")
    filters_applied: dict[str, Any] = Field(description="Applied filters")


class WorkflowListResponse(BaseModel):
    """Paginated workflow list response"""

    workflows: list[WorkflowStatusResponse] = Field(description="List of workflows")
    total_count: int = Field(description="Total number of workflows matching filters")
    page_info: dict[str, Any] = Field(description="Pagination information")
    filters_applied: dict[str, Any] = Field(description="Applied filters")


class BulkOperationResponse(BaseModel):
    """Response for bulk task operations"""

    operation: TaskOperationType = Field(description="Operation that was performed")
    requested_tasks: int = Field(description="Number of tasks requested for operation")
    successful_operations: int = Field(description="Number of successful operations")
    failed_operations: int = Field(description="Number of failed operations")
    processing_time: float = Field(description="Total processing time in seconds")
    results: list[dict[str, Any]] = Field(description="Individual operation results")
    processed_at: datetime = Field(description="Operation completion timestamp")


class TaskMetricsResponse(BaseModel):
    """Task system metrics and analytics"""

    period: dict[str, Any] = Field(description="Time period for metrics")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for filtered metrics")

    # Volume metrics
    task_volume: dict[str, int] = Field(description="Task volume over time")
    completion_rate: dict[str, float] = Field(description="Task completion rates")
    error_trends: dict[str, float] = Field(description="Error rate trends")

    # Performance metrics
    processing_times: dict[str, float] = Field(
        description="Processing time percentiles"
    )
    queue_depths: dict[str, int] = Field(description="Queue depth over time")
    throughput: dict[str, float] = Field(description="Throughput metrics")

    # Resource usage
    resource_utilization: dict[str, Any] = Field(
        description="Resource utilization metrics"
    )
    cost_metrics: dict[str, float] = Field(description="Cost-related metrics")


# WebSocket Message Types
class WebSocketMessage(BaseModel):
    """Base WebSocket message"""

    message_type: str = Field(description="Type of WebSocket message")
    timestamp: datetime = Field(description="Message timestamp")


class TaskProgressMessage(WebSocketMessage):
    """Task progress WebSocket message"""

    message_type: str = Field(default="task_progress")
    task_id: str = Field(description="Task ID")
    status: TaskStatus = Field(description="Current task status")
    progress: dict[str, Any] = Field(description="Progress information")
    error: Optional[str] = Field(None, description="Error message if applicable")


class WorkflowProgressMessage(WebSocketMessage):
    """Workflow progress WebSocket message"""

    message_type: str = Field(default="workflow_progress")
    workflow_id: str = Field(description="Workflow ID")
    status: WorkflowStatus = Field(description="Current workflow status")
    current_step: Optional[str] = Field(None, description="Current step")
    progress: float = Field(ge=0, le=100, description="Progress percentage")
    completed_steps: int = Field(description="Number of completed steps")
    total_steps: int = Field(description="Total number of steps")


class SystemMetricsMessage(WebSocketMessage):
    """System metrics WebSocket message"""

    message_type: str = Field(default="system_metrics")
    queue_depth: int = Field(description="Current queue depth")
    active_tasks: int = Field(description="Number of active tasks")
    worker_utilization: float = Field(description="Worker utilization percentage")
    error_rate: float = Field(description="Current error rate")
    throughput: float = Field(description="Current throughput")
    memory_usage: dict[str, Any] = Field(description="Memory usage metrics")


class AlertMessage(WebSocketMessage):
    """Alert WebSocket message"""

    message_type: str = Field(default="alert")
    alert_level: str = Field(description="Alert severity level")
    alert_type: str = Field(description="Type of alert")
    message: str = Field(description="Alert message")
    affected_components: list[str] = Field(description="Affected system components")
    action_required: bool = Field(description="Whether action is required")
