"""
Common schemas and data models used across all operations SDKs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class Priority(str, Enum):
    """Priority levels for operations."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ResourceIdentifier(BaseModel):
    """Resource identifier with namespace and version support."""

    id: str = Field(..., description="Resource identifier")
    namespace: Optional[str] = Field(None, description="Resource namespace")
    version: Optional[str] = Field(None, description="Resource version")
    tenant_id: str = Field(..., description="Tenant identifier")

    class Config:
        extra = "forbid"


class OperationMetadata(BaseModel):
    """Metadata for operations and executions."""

    created_by: Optional[str] = Field(None, description="Creator identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = Field(default_factory=dict, description="Resource labels")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Resource annotations")
    tags: List[str] = Field(default_factory=list, description="Resource tags")

    @validator('created_at', 'updated_at', pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    class Config:
        extra = "allow"


class RetryPolicy(BaseModel):
    """Retry policy configuration."""

    max_attempts: int = Field(3, ge=1, description="Maximum retry attempts")
    initial_delay: float = Field(1.0, ge=0, description="Initial delay in seconds")
    max_delay: float = Field(300.0, ge=0, description="Maximum delay in seconds")
    backoff_multiplier: float = Field(2.0, ge=1, description="Backoff multiplier")
    jitter: bool = Field(True, description="Add jitter to delays")
    retry_on: List[str] = Field(
        default_factory=lambda: ["timeout", "connection_error", "server_error"],
        description="Error types to retry on"
    )

    class Config:
        extra = "forbid"


class TimeoutPolicy(BaseModel):
    """Timeout policy configuration."""

    execution_timeout: Optional[float] = Field(None, ge=0, description="Execution timeout in seconds")
    step_timeout: Optional[float] = Field(None, ge=0, description="Step timeout in seconds")
    idle_timeout: Optional[float] = Field(None, ge=0, description="Idle timeout in seconds")

    class Config:
        extra = "forbid"


class ErrorInfo(BaseModel):
    """Error information structure."""

    error_type: str = Field(..., description="Error type or class")
    error_code: Optional[str] = Field(None, description="Error code")
    message: str = Field(..., description="Error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Error details")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    class Config:
        extra = "allow"


class ExecutionContext(BaseModel):
    """Execution context with environment and variables."""

    execution_id: str = Field(..., description="Execution identifier")
    parent_execution_id: Optional[str] = Field(None, description="Parent execution ID")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Context variables")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier")
    trace_id: Optional[str] = Field(None, description="Trace identifier")

    class Config:
        extra = "allow"


class ExecutionResult(BaseModel):
    """Result of an execution with output and status."""

    execution_id: str = Field(..., description="Execution identifier")
    status: ExecutionStatus = Field(..., description="Execution status")
    output: Dict[str, Any] = Field(default_factory=dict, description="Execution output")
    error: Optional[ErrorInfo] = Field(None, description="Error information if failed")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Execution duration")
    retry_count: int = Field(0, ge=0, description="Number of retries")

    @validator('started_at', 'completed_at', pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    class Config:
        extra = "allow"


class MetricsData(BaseModel):
    """Metrics data structure."""

    name: str = Field(..., description="Metric name")
    value: Union[int, float] = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    class Config:
        extra = "forbid"


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""

    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(50, ge=1, le=1000, description="Items per page")
    total_items: int = Field(0, ge=0, description="Total number of items")
    total_pages: int = Field(0, ge=0, description="Total number of pages")
    has_next: bool = Field(False, description="Has next page")
    has_previous: bool = Field(False, description="Has previous page")

    class Config:
        extra = "forbid"


class ListResponse(BaseModel):
    """Generic list response with pagination."""

    items: List[Dict[str, Any]] = Field(default_factory=list, description="List items")
    pagination: PaginationInfo = Field(..., description="Pagination information")

    class Config:
        extra = "forbid"


class OperationResponse(BaseModel):
    """Generic operation response."""

    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response data")
    error: Optional[ErrorInfo] = Field(None, description="Error information")

    class Config:
        extra = "allow"


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: HealthStatus = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime")
    checks: Dict[str, HealthStatus] = Field(default_factory=dict, description="Individual health checks")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")

    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    class Config:
        extra = "allow"
