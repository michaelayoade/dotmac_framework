"""Type definitions for dotmac-tasks-utils."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from datetime import datetime

T = TypeVar("T")


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class TaskResult(Generic[T]):
    """Result of a task execution."""

    task_id: str
    status: TaskStatus
    result: T | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0
    max_attempts: int = 1

    def is_complete(self) -> bool:
        """Check if task is in a final state."""
        return self.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_successful(self) -> bool:
        """Check if task completed successfully."""
        return self.status == TaskStatus.SUCCESS

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return (
            self.status == TaskStatus.FAILED and
            self.attempts < self.max_attempts
        )


@dataclass
class TaskOptions:
    """Task execution options."""

    priority: TaskPriority = TaskPriority.NORMAL
    max_attempts: int = 1
    timeout: float | None = None
    delay: float | None = None
    tags: dict[str, str] | None = None

    def __post_init__(self):
        """Validate options after initialization."""
        if self.max_attempts < 1:
            msg = "max_attempts must be at least 1"
            raise ValueError(msg)
        if self.timeout is not None and self.timeout <= 0:
            msg = "timeout must be positive"
            raise ValueError(msg)
        if self.delay is not None and self.delay < 0:
            msg = "delay must be non-negative"
            raise ValueError(msg)


# Type aliases
TaskFunction = Callable[..., Any]
AsyncTaskFunction = Callable[..., Any]  # Awaitable[Any]
TaskId = str
Tags = dict[str, str] | None
