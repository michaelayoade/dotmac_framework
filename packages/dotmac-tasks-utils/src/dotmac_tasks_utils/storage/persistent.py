"""Persistent storage backends for long-term task result storage."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from dotmac_tasks_utils.types import TaskResult, TaskStatus


class PersistentStore(ABC):
    """Abstract interface for long-term task result storage."""

    @abstractmethod
    async def store_task_result(self, result: TaskResult[Any]) -> None:
        """Store task result for long-term persistence."""

    @abstractmethod
    async def get_task_history(
        self,
        task_id: str,
        limit: int = 100
    ) -> list[TaskResult[Any]]:
        """Get execution history for a specific task."""

    @abstractmethod
    async def query_tasks(
        self,
        status: TaskStatus | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        task_type: str | None = None,
        limit: int = 1000
    ) -> list[TaskResult[Any]]:
        """Query tasks with filters."""

    @abstractmethod
    async def cleanup_old_results(self, older_than: datetime) -> int:
        """Remove task results older than specified date."""


class JsonFilePersistentStore(PersistentStore):
    """File-based persistent storage using JSON."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the storage file exists."""
        try:
            with open(self.file_path) as f:
                pass
        except FileNotFoundError:
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def _load_results(self) -> list[dict[str, Any]]:
        """Load all results from file."""
        try:
            with open(self.file_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_results(self, results: list[dict[str, Any]]) -> None:
        """Save results to file."""
        with open(self.file_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

    def _task_result_to_dict(self, result: TaskResult[Any]) -> dict[str, Any]:
        """Convert TaskResult to dictionary."""
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": result.error,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "attempts": result.attempts,
            "max_attempts": result.max_attempts,
            "stored_at": datetime.utcnow().isoformat()
        }

    def _dict_to_task_result(self, data: dict[str, Any]) -> TaskResult[Any]:
        """Convert dictionary to TaskResult."""
        return TaskResult(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 1)
        )

    async def store_task_result(self, result: TaskResult[Any]) -> None:
        """Store task result in JSON file."""
        results = self._load_results()

        # Remove existing result with same task_id
        results = [r for r in results if r["task_id"] != result.task_id]

        # Add new result
        results.append(self._task_result_to_dict(result))

        self._save_results(results)

    async def get_task_history(
        self,
        task_id: str,
        limit: int = 100
    ) -> list[TaskResult[Any]]:
        """Get execution history for a specific task."""
        results = self._load_results()

        # Filter by task_id and sort by stored_at
        task_results = [
            self._dict_to_task_result(r)
            for r in results
            if r["task_id"] == task_id
        ]

        # Sort by completion time
        task_results.sort(
            key=lambda r: r.completed_at or datetime.min,
            reverse=True
        )

        return task_results[:limit]

    async def query_tasks(
        self,
        status: TaskStatus | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        task_type: str | None = None,
        limit: int = 1000
    ) -> list[TaskResult[Any]]:
        """Query tasks with filters."""
        results = self._load_results()

        filtered_results = []
        for data in results:
            # Filter by status
            if status and data["status"] != status.value:
                continue

            # Filter by time range
            completed_at = None
            if data.get("completed_at"):
                completed_at = datetime.fromisoformat(data["completed_at"])

            if start_time and (not completed_at or completed_at < start_time):
                continue

            if end_time and (not completed_at or completed_at > end_time):
                continue

            # Filter by task type (basic heuristic from task_id)
            if task_type and not data["task_id"].startswith(task_type):
                continue

            filtered_results.append(self._dict_to_task_result(data))

        # Sort by completion time
        filtered_results.sort(
            key=lambda r: r.completed_at or datetime.min,
            reverse=True
        )

        return filtered_results[:limit]

    async def cleanup_old_results(self, older_than: datetime) -> int:
        """Remove task results older than specified date."""
        results = self._load_results()
        initial_count = len(results)

        # Filter out old results
        filtered_results = []
        for data in results:
            stored_at = datetime.fromisoformat(data.get("stored_at", "1970-01-01"))
            if stored_at >= older_than:
                filtered_results.append(data)

        self._save_results(filtered_results)
        return initial_count - len(filtered_results)


# Placeholder for future PostgreSQL implementation
class PostgreSQLPersistentStore(PersistentStore):
    """PostgreSQL implementation of persistent task storage."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        msg = "PostgreSQL persistent store not yet implemented"
        raise NotImplementedError(msg)

    async def store_task_result(self, result: TaskResult[Any]) -> None:
        msg = "PostgreSQL persistent store not yet implemented"
        raise NotImplementedError(msg)

    async def get_task_history(self, task_id: str, limit: int = 100) -> list[TaskResult[Any]]:
        msg = "PostgreSQL persistent store not yet implemented"
        raise NotImplementedError(msg)

    async def query_tasks(
        self,
        status: TaskStatus | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        task_type: str | None = None,
        limit: int = 1000
    ) -> list[TaskResult[Any]]:
        msg = "PostgreSQL persistent store not yet implemented"
        raise NotImplementedError(msg)

    async def cleanup_old_results(self, older_than: datetime) -> int:
        msg = "PostgreSQL persistent store not yet implemented"
        raise NotImplementedError(msg)
