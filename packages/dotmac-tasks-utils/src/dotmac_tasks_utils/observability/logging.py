"""Structured logging for task execution."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dotmac_tasks_utils.types import TaskStatus


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "task_type"):
            log_data["task_type"] = record.task_type
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "attempt"):
            log_data["attempt"] = record.attempt
        if hasattr(record, "queue_name"):
            log_data["queue_name"] = record.queue_name
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "priority"):
            log_data["priority"] = record.priority

        return json.dumps(log_data)


def get_task_logger(name: str) -> logging.Logger:
    """Get a configured logger for task operations."""
    logger = logging.getLogger(f"dotmac_tasks.{name}")

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class TaskLogger:
    """Structured logger for task lifecycle events."""

    def __init__(self, logger_name: str = "tasks"):
        self.logger = get_task_logger(logger_name)

    def task_submitted(
        self,
        task_id: str,
        task_type: str,
        queue_name: str,
        priority: int,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log task submission."""
        self.logger.info(
            "Task submitted to queue",
            extra={
                "event": "task.submitted",
                "task_id": task_id,
                "task_type": task_type,
                "queue_name": queue_name,
                "priority": priority,
                **(extra or {})
            }
        )

    def task_started(
        self,
        task_id: str,
        task_type: str,
        attempt: int = 1,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log task execution start."""
        self.logger.info(
            "Task execution started",
            extra={
                "event": "task.started",
                "task_id": task_id,
                "task_type": task_type,
                "attempt": attempt,
                **(extra or {})
            }
        )

    def task_completed(
        self,
        task_id: str,
        task_type: str,
        duration_ms: float,
        attempt: int,
        status: TaskStatus,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log successful task completion."""
        self.logger.info(
            "Task completed successfully",
            extra={
                "event": "task.completed",
                "task_id": task_id,
                "task_type": task_type,
                "duration_ms": duration_ms,
                "attempt": attempt,
                "status": status.value,
                **(extra or {})
            }
        )

    def task_failed(
        self,
        task_id: str,
        task_type: str,
        duration_ms: float,
        attempt: int,
        error_type: str,
        error_message: str,
        will_retry: bool = False,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log task execution failure."""
        level = logging.WARNING if will_retry else logging.ERROR

        self.logger.log(
            level,
            f"Task failed: {error_message}",
            extra={
                "event": "task.failed",
                "task_id": task_id,
                "task_type": task_type,
                "duration_ms": duration_ms,
                "attempt": attempt,
                "error_type": error_type,
                "error_message": error_message,
                "will_retry": will_retry,
                **(extra or {})
            }
        )

    def task_retry(
        self,
        task_id: str,
        task_type: str,
        attempt: int,
        next_attempt_in_ms: float,
        error_type: str,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log task retry scheduling."""
        self.logger.warning(
            "Task scheduled for retry",
            extra={
                "event": "task.retry",
                "task_id": task_id,
                "task_type": task_type,
                "attempt": attempt,
                "next_attempt_in_ms": next_attempt_in_ms,
                "error_type": error_type,
                **(extra or {})
            }
        )

    def task_cancelled(
        self,
        task_id: str,
        task_type: str,
        reason: str,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log task cancellation."""
        self.logger.warning(
            f"Task cancelled: {reason}",
            extra={
                "event": "task.cancelled",
                "task_id": task_id,
                "task_type": task_type,
                "reason": reason,
                **(extra or {})
            }
        )

    def queue_operation(
        self,
        operation: str,
        queue_name: str,
        task_count: int,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log queue operations."""
        self.logger.info(
            f"Queue operation: {operation}",
            extra={
                "event": "queue.operation",
                "operation": operation,
                "queue_name": queue_name,
                "task_count": task_count,
                **(extra or {})
            }
        )

    def storage_operation(
        self,
        operation: str,
        storage_type: str,
        key: str,
        success: bool,
        duration_ms: float | None = None,
        extra: dict[str, Any] | None = None
    ) -> None:
        """Log storage backend operations."""
        level = logging.INFO if success else logging.ERROR

        self.logger.log(
            level,
            f"Storage {operation}: {'success' if success else 'failed'}",
            extra={
                "event": "storage.operation",
                "operation": operation,
                "storage_type": storage_type,
                "key": key,
                "success": success,
                "duration_ms": duration_ms,
                **(extra or {})
            }
        )
