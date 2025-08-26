"""Common schema definitions."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pydantic import ConfigDict


class ExecutionStatus(str, Enum):
    """Workflow execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


class Priority(str, Enum):
    """Task/workflow priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


@dataclass
class APIResponse:
    """Standard API response schema."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    error_code: Optional[str] = None


@dataclass
class PaginationInfo:
    """Pagination information."""

    page: int = 1
    per_page: int = 20
    total: int = 0
    pages: int = 0


@dataclass
class ErrorInfo:
    """Error information schema."""

    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


@dataclass
class ExecutionContext:
    """Workflow execution context."""

    workflow_id: str
    step_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: ExecutionStatus = ExecutionStatus.PENDING


@dataclass
class OperationMetadata:
    """Metadata for operations and workflows."""

    operation_id: str
    operation_type: str
    initiated_by: Optional[str] = None
    tenant_id: Optional[str] = None
    timestamp: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    context: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on_exceptions: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize default retry exceptions."""
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = [
                "NetworkError",
                "TimeoutError",
                "ServiceUnavailableError",
            ]


@dataclass
class TimeoutPolicy:
    """Timeout policy configuration for operations."""

    connection_timeout: float = 10.0  # seconds
    read_timeout: float = 30.0  # seconds
    total_timeout: float = 60.0  # seconds
    keep_alive_timeout: float = 5.0  # seconds
