"""
Task Management Data Models

Database models and data structures for task management functionality.
These models represent persistent data structures used by the task
management system for storing metadata, audit logs, and configuration.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict
from dotmac_shared.tasks import TaskStatus, TaskPriority


class TaskOperationAuditLog(BaseModel):
    """Audit log entry for task operations"""
    model_config = ConfigDict(extra="allow")
    
    id: Optional[str] = Field(None, description="Unique audit log entry ID")
    task_id: str = Field(description="Task identifier")
    tenant_id: str = Field(description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User who performed the operation")
    
    operation: str = Field(description="Operation performed (cancel, retry, delete, etc.)")
    timestamp: datetime = Field(description="When the operation was performed")
    
    # Operation context
    source_ip: Optional[str] = Field(None, description="IP address of the requester")
    user_agent: Optional[str] = Field(None, description="User agent string")
    api_endpoint: Optional[str] = Field(None, description="API endpoint used")
    
    # Operation details
    operation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific metadata"
    )
    
    # Results
    success: bool = Field(description="Whether the operation succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional result data"
    )


class TaskMetricsSnapshot(BaseModel):
    """Point-in-time metrics snapshot for a task"""
    model_config = ConfigDict(extra="allow")
    
    task_id: str = Field(description="Task identifier")
    tenant_id: str = Field(description="Tenant identifier")
    snapshot_time: datetime = Field(description="When the snapshot was taken")
    
    # Performance metrics
    execution_time: Optional[float] = Field(None, description="Total execution time in seconds")
    queue_time: Optional[float] = Field(None, description="Time spent in queue in seconds")
    
    # Resource usage
    peak_memory_usage: Optional[int] = Field(None, description="Peak memory usage in bytes")
    avg_cpu_usage: Optional[float] = Field(None, description="Average CPU usage percentage")
    network_io: Optional[int] = Field(None, description="Network I/O in bytes")
    disk_io: Optional[int] = Field(None, description="Disk I/O in bytes")
    
    # Error metrics
    error_count: int = Field(0, description="Number of errors encountered")
    warning_count: int = Field(0, description="Number of warnings")
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific custom metrics"
    )


class SystemHealthSnapshot(BaseModel):
    """Point-in-time system health snapshot"""
    model_config = ConfigDict(extra="allow")
    
    snapshot_id: Optional[str] = Field(None, description="Unique snapshot identifier")
    timestamp: datetime = Field(description="When the snapshot was taken")
    
    # Overall system status
    overall_status: str = Field(description="Overall system health status")
    
    # Queue metrics
    total_tasks: int = Field(description="Total tasks in system")
    pending_tasks: int = Field(description="Tasks waiting to be processed")
    running_tasks: int = Field(description="Currently executing tasks")
    failed_tasks: int = Field(description="Failed tasks")
    
    # Performance metrics
    average_processing_time: float = Field(description="Average task processing time")
    throughput_per_minute: float = Field(description="Tasks processed per minute")
    error_rate: float = Field(description="System-wide error rate")
    
    # Resource metrics
    total_memory_usage: Optional[int] = Field(None, description="Total memory usage")
    total_cpu_usage: Optional[float] = Field(None, description="Total CPU usage")
    disk_usage: Optional[Dict[str, Any]] = Field(None, description="Disk usage metrics")
    
    # Worker metrics
    total_workers: int = Field(description="Total number of workers")
    active_workers: int = Field(description="Currently active workers")
    worker_utilization: float = Field(description="Worker utilization percentage")
    
    # External system health
    redis_status: str = Field(description="Redis connection status")
    database_status: str = Field(description="Database connection status")
    
    # Alerts and issues
    active_alerts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Currently active system alerts"
    )


class TenantTaskQuota(BaseModel):
    """Task execution quotas and limits for a tenant"""
    model_config = ConfigDict(extra="allow")
    
    tenant_id: str = Field(description="Tenant identifier")
    plan_type: str = Field(description="Tenant plan type")
    
    # Task limits
    max_concurrent_tasks: int = Field(description="Maximum concurrent tasks")
    max_daily_tasks: int = Field(description="Maximum tasks per day")
    max_monthly_tasks: int = Field(description="Maximum tasks per month")
    
    # Resource limits
    max_task_memory: Optional[int] = Field(None, description="Maximum memory per task in bytes")
    max_task_duration: Optional[int] = Field(None, description="Maximum task duration in seconds")
    max_queue_size: Optional[int] = Field(None, description="Maximum queue size")
    
    # Priority limits
    can_use_high_priority: bool = Field(False, description="Can use high priority tasks")
    can_use_urgent_priority: bool = Field(False, description="Can use urgent priority tasks")
    
    # Feature access
    can_cancel_tasks: bool = Field(True, description="Can cancel tasks")
    can_retry_tasks: bool = Field(True, description="Can retry failed tasks")
    can_view_system_metrics: bool = Field(False, description="Can view system-wide metrics")
    
    # Current usage
    current_concurrent_tasks: int = Field(0, description="Current concurrent tasks")
    daily_task_count: int = Field(0, description="Tasks executed today")
    monthly_task_count: int = Field(0, description="Tasks executed this month")
    
    # Reset timestamps
    daily_reset_at: datetime = Field(description="When daily counters reset")
    monthly_reset_at: datetime = Field(description="When monthly counters reset")


class TaskTemplate(BaseModel):
    """Template for creating tasks with predefined configurations"""
    model_config = ConfigDict(extra="allow")
    
    template_id: str = Field(description="Unique template identifier")
    name: str = Field(description="Human-readable template name")
    description: Optional[str] = Field(None, description="Template description")
    
    # Template metadata
    created_by: str = Field(description="User who created the template")
    created_at: datetime = Field(description="Template creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    version: str = Field("1.0", description="Template version")
    
    # Task configuration
    task_type: str = Field(description="Type of task this template creates")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Default task priority")
    max_retries: int = Field(3, description="Default maximum retries")
    timeout: Optional[int] = Field(None, description="Default task timeout in seconds")
    
    # Template parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default parameters for tasks created from this template"
    )
    
    # Parameter schema for validation
    parameter_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for validating template parameters"
    )
    
    # Usage statistics
    usage_count: int = Field(0, description="Number of times this template has been used")
    last_used_at: Optional[datetime] = Field(None, description="When template was last used")
    
    # Access control
    tenant_id: Optional[str] = Field(None, description="Tenant that owns this template")
    is_public: bool = Field(False, description="Whether template is publicly available")
    allowed_tenants: List[str] = Field(
        default_factory=list,
        description="Tenants allowed to use this template"
    )


class TaskScheduleRule(BaseModel):
    """Rule for scheduled task execution"""
    model_config = ConfigDict(extra="allow")
    
    rule_id: str = Field(description="Unique rule identifier")
    name: str = Field(description="Human-readable rule name")
    description: Optional[str] = Field(None, description="Rule description")
    
    # Schedule configuration
    cron_expression: str = Field(description="Cron expression for scheduling")
    timezone: str = Field("UTC", description="Timezone for schedule evaluation")
    enabled: bool = Field(True, description="Whether the rule is active")
    
    # Task configuration
    task_template_id: Optional[str] = Field(None, description="Template to use for created tasks")
    task_type: str = Field(description="Type of task to create")
    task_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for created tasks"
    )
    
    # Execution limits
    max_concurrent_executions: int = Field(1, description="Maximum concurrent executions")
    skip_if_previous_running: bool = Field(True, description="Skip if previous execution still running")
    
    # Metadata
    tenant_id: str = Field(description="Tenant that owns this rule")
    created_by: str = Field(description="User who created the rule")
    created_at: datetime = Field(description="Rule creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Execution tracking
    last_execution_at: Optional[datetime] = Field(None, description="Last successful execution")
    next_execution_at: Optional[datetime] = Field(None, description="Next scheduled execution")
    execution_count: int = Field(0, description="Total number of executions")
    failure_count: int = Field(0, description="Number of failed executions")


class TaskNotificationRule(BaseModel):
    """Rule for sending notifications about task events"""
    model_config = ConfigDict(extra="allow")
    
    rule_id: str = Field(description="Unique rule identifier")
    name: str = Field(description="Human-readable rule name")
    
    # Trigger conditions
    task_types: List[str] = Field(
        default_factory=list,
        description="Task types to monitor (empty = all types)"
    )
    task_statuses: List[TaskStatus] = Field(
        default_factory=list,
        description="Task statuses to trigger on (empty = all statuses)"
    )
    tenant_ids: List[str] = Field(
        default_factory=list,
        description="Tenants to monitor (empty = all tenants)"
    )
    
    # Conditions
    min_execution_time: Optional[float] = Field(
        None,
        description="Minimum execution time in seconds to trigger"
    )
    max_execution_time: Optional[float] = Field(
        None,
        description="Maximum execution time in seconds to trigger"
    )
    error_patterns: List[str] = Field(
        default_factory=list,
        description="Error message patterns to match"
    )
    
    # Notification configuration
    notification_channels: List[str] = Field(
        description="Channels to send notifications to (email, webhook, slack, etc.)"
    )
    notification_template: str = Field(description="Template for notification content")
    
    # Rate limiting
    cooldown_seconds: int = Field(300, description="Minimum time between notifications")
    max_notifications_per_hour: int = Field(10, description="Maximum notifications per hour")
    
    # Metadata
    tenant_id: Optional[str] = Field(None, description="Tenant that owns this rule")
    enabled: bool = Field(True, description="Whether the rule is active")
    created_at: datetime = Field(description="Rule creation timestamp")
    last_triggered_at: Optional[datetime] = Field(None, description="Last time rule was triggered")


class TaskDependency(BaseModel):
    """Dependency relationship between tasks"""
    model_config = ConfigDict(extra="allow")
    
    dependent_task_id: str = Field(description="Task that depends on another")
    dependency_task_id: str = Field(description="Task that must complete first")
    
    # Dependency type
    dependency_type: str = Field(
        "completion",
        description="Type of dependency (completion, success, etc.)"
    )
    
    # Conditions
    required_status: Optional[TaskStatus] = Field(
        None,
        description="Required status of dependency task"
    )
    
    timeout_seconds: Optional[int] = Field(
        None,
        description="Maximum time to wait for dependency"
    )
    
    # Metadata
    created_at: datetime = Field(description="Dependency creation timestamp")
    resolved_at: Optional[datetime] = Field(None, description="When dependency was resolved")
    
    # Status
    is_resolved: bool = Field(False, description="Whether dependency is resolved")
    resolution_result: Optional[str] = Field(None, description="How dependency was resolved")


class WorkflowTemplate(BaseModel):
    """Template for creating multi-step workflows"""
    model_config = ConfigDict(extra="allow")
    
    template_id: str = Field(description="Unique template identifier")
    name: str = Field(description="Human-readable template name")
    description: Optional[str] = Field(None, description="Template description")
    version: str = Field("1.0", description="Template version")
    
    # Workflow definition
    steps: List[Dict[str, Any]] = Field(description="Workflow steps definition")
    step_dependencies: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dependencies between workflow steps"
    )
    
    # Configuration
    parallel_execution: bool = Field(False, description="Allow parallel step execution")
    failure_strategy: str = Field(
        "stop_on_first_failure",
        description="How to handle step failures"
    )
    
    # Metadata
    tenant_id: Optional[str] = Field(None, description="Tenant that owns this template")
    created_by: str = Field(description="User who created the template")
    created_at: datetime = Field(description="Template creation timestamp")
    
    # Usage tracking
    usage_count: int = Field(0, description="Number of times template has been used")
    success_rate: float = Field(0.0, description="Success rate of workflows from this template")


# Utility models for API responses and internal data transfer

class TaskExecutionContext(BaseModel):
    """Context information for task execution"""
    model_config = ConfigDict(extra="allow")
    
    task_id: str = Field(description="Task identifier")
    tenant_id: str = Field(description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User who initiated the task")
    
    # Execution environment
    worker_id: Optional[str] = Field(None, description="Worker executing the task")
    execution_node: Optional[str] = Field(None, description="Node where task is executing")
    
    # Resource allocation
    allocated_memory: Optional[int] = Field(None, description="Allocated memory in bytes")
    allocated_cpu: Optional[float] = Field(None, description="Allocated CPU cores")
    
    # Timing
    queued_at: datetime = Field(description="When task was queued")
    started_at: Optional[datetime] = Field(None, description="When execution started")
    
    # Context data
    context_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context data for task execution"
    )


class TaskBatchInfo(BaseModel):
    """Information about a batch of related tasks"""
    model_config = ConfigDict(extra="allow")
    
    batch_id: str = Field(description="Unique batch identifier")
    name: Optional[str] = Field(None, description="Human-readable batch name")
    
    # Batch metadata
    tenant_id: str = Field(description="Tenant that owns this batch")
    created_by: str = Field(description="User who created the batch")
    created_at: datetime = Field(description="Batch creation timestamp")
    
    # Task information
    task_ids: List[str] = Field(description="Tasks in this batch")
    total_tasks: int = Field(description="Total number of tasks in batch")
    
    # Progress tracking
    completed_tasks: int = Field(0, description="Number of completed tasks")
    failed_tasks: int = Field(0, description="Number of failed tasks")
    cancelled_tasks: int = Field(0, description="Number of cancelled tasks")
    
    # Status
    batch_status: str = Field("pending", description="Overall batch status")
    progress_percentage: float = Field(0.0, description="Batch completion percentage")
    
    # Configuration
    stop_on_first_failure: bool = Field(False, description="Stop batch on first task failure")
    max_concurrent_tasks: Optional[int] = Field(None, description="Maximum concurrent tasks in batch")


class AlertRule(BaseModel):
    """Rule for generating system alerts"""
    model_config = ConfigDict(extra="allow")
    
    rule_id: str = Field(description="Unique rule identifier")
    name: str = Field(description="Human-readable rule name")
    description: Optional[str] = Field(None, description="Rule description")
    
    # Trigger conditions
    metric_name: str = Field(description="Metric to monitor")
    threshold_value: float = Field(description="Threshold value to trigger alert")
    comparison_operator: str = Field(description="Comparison operator (>, <, >=, <=, ==)")
    
    # Alert configuration
    severity: str = Field(description="Alert severity (info, warning, error, critical)")
    alert_message: str = Field(description="Message to include in alert")
    
    # Notification settings
    notification_channels: List[str] = Field(description="Channels to send alerts to")
    
    # Rate limiting
    cooldown_seconds: int = Field(300, description="Minimum time between alerts")
    max_alerts_per_hour: int = Field(5, description="Maximum alerts per hour")
    
    # Metadata
    enabled: bool = Field(True, description="Whether the rule is active")
    created_at: datetime = Field(description="Rule creation timestamp")
    last_triggered_at: Optional[datetime] = Field(None, description="Last time rule was triggered")