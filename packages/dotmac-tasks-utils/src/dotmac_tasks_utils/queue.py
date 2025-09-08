"""Redis-based task queue for dotmac-tasks-utils."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from .types import TaskId, TaskOptions, TaskResult, TaskStatus

try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    Redis = Any  # Type placeholder
    REDIS_AVAILABLE = False


class RedisTaskQueue:
    """
    Redis-based task queue with priority support.

    Provides persistent task queueing with Redis as the backend.
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        queue_name: str = "dotmac:tasks",
        result_ttl: int = 3600,
    ) -> None:
        """
        Initialize the Redis task queue.

        Args:
            redis_client: Redis client instance
            queue_name: Base name for Redis keys
            result_ttl: TTL for task results in seconds

        Raises:
            ImportError: If Redis is not installed
        """
        if not REDIS_AVAILABLE:
            msg = "Redis not available. Install with: pip install dotmac-tasks-utils[redis]"
            raise ImportError(msg)

        if redis_client is None:
            redis_client = redis.Redis(
                host="localhost",
                port=6379,
                db=0,
                decode_responses=True
            )

        self.redis = redis_client
        self.queue_name = queue_name
        self.result_ttl = result_ttl

        # Redis key patterns
        self._queue_key = f"{queue_name}:queue"
        self._result_key_pattern = f"{queue_name}:result:"
        self._status_key_pattern = f"{queue_name}:status:"

    async def enqueue(
        self,
        task_data: dict[str, Any],
        task_id: TaskId | None = None,
        options: TaskOptions | None = None,
    ) -> TaskId:
        """
        Enqueue a task for processing.

        Args:
            task_data: Task data to enqueue
            task_id: Optional custom task ID
            options: Task execution options

        Returns:
            Task ID for tracking
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        if options is None:
            options = TaskOptions()

        # Create task payload
        payload = {
            "task_id": task_id,
            "data": task_data,
            "options": {
                "priority": options.priority.value,
                "max_attempts": options.max_attempts,
                "timeout": options.timeout,
                "delay": options.delay,
                "tags": options.tags or {},
            },
            "enqueued_at": datetime.utcnow().isoformat(),
            "attempts": 0,
        }

        # Store initial status
        await self._set_task_status(task_id, TaskStatus.PENDING)

        # Add to priority queue (higher priority = higher score)
        score = options.priority.value
        self.redis.zadd(self._queue_key, {json.dumps(payload): score})

        return task_id

    async def dequeue(self, timeout: float | None = None) -> dict[str, Any] | None:
        """
        Dequeue the highest priority task.

        Args:
            timeout: Optional blocking timeout in seconds

        Returns:
            Task payload or None if no tasks available
        """
        if timeout:
            # Blocking pop with timeout
            result = self.redis.bzpopmax(self._queue_key, timeout=int(timeout))
            if result:
                _, task_json, _ = result
                return json.loads(task_json)
            return None
        # Non-blocking pop
        result = self.redis.zpopmax(self._queue_key, count=1)
        if result:
            task_json, _ = result[0]
            return json.loads(task_json)
        return None

    async def get_status(self, task_id: TaskId) -> TaskResult[Any]:
        """
        Get task status and result.

        Args:
            task_id: Task ID to check

        Returns:
            Task result

        Raises:
            KeyError: If task not found
        """
        status_key = f"{self._status_key_pattern}{task_id}"
        result_key = f"{self._result_key_pattern}{task_id}"

        status_data = self.redis.get(status_key)
        if not status_data:
            msg = f"Task {task_id} not found"
            raise KeyError(msg)

        status_info = json.loads(status_data)
        result_data = self.redis.get(result_key)

        return TaskResult[Any](
            task_id=task_id,
            status=TaskStatus(status_info["status"]),
            result=json.loads(result_data) if result_data else None,
            error=status_info.get("error"),
            started_at=self._parse_datetime(status_info.get("started_at")),
            completed_at=self._parse_datetime(status_info.get("completed_at")),
            attempts=status_info.get("attempts", 0),
            max_attempts=status_info.get("max_attempts", 1),
        )

    async def set_result(
        self,
        task_id: TaskId,
        result: Any,
        status: TaskStatus,
        error: str | None = None,
    ) -> None:
        """
        Set task result and status.

        Args:
            task_id: Task ID
            result: Task result data
            status: Final task status
            error: Optional error message
        """
        result_key = f"{self._result_key_pattern}{task_id}"

        # Store result
        if result is not None:
            self.redis.setex(result_key, self.result_ttl, json.dumps(result))

        # Update status
        await self._set_task_status(task_id, status, error=error, completed=True)

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[TaskResult[Any]]:
        """
        List tasks with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of task results
        """
        # Get all task status keys
        pattern = f"{self._status_key_pattern}*"
        keys = self.redis.keys(pattern)

        tasks = []
        for key in keys[:limit]:  # Limit to avoid memory issues
            try:
                task_id = key.split(":")[-1]
                task_result = await self.get_status(task_id)

                if status is None or task_result.status == status:
                    tasks.append(task_result)

            except (KeyError, json.JSONDecodeError):
                continue  # Skip invalid entries

        return tasks

    def get_queue_size(self) -> int:
        """
        Get the current queue size.

        Returns:
            Number of tasks in queue
        """
        return self.redis.zcard(self._queue_key)

    def clear_queue(self) -> int:
        """
        Clear all tasks from the queue.

        Returns:
            Number of tasks removed
        """
        return self.redis.delete(self._queue_key)

    async def _set_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        error: str | None = None,
        completed: bool = False,
    ) -> None:
        """Set task status in Redis."""
        status_key = f"{self._status_key_pattern}{task_id}"

        # Get existing status or create new
        existing = self.redis.get(status_key)
        if existing:
            status_info = json.loads(existing)
        else:
            status_info = {
                "task_id": task_id,
                "attempts": 0,
                "max_attempts": 1,
            }

        # Update status
        status_info["status"] = status.value
        if error:
            status_info["error"] = error
        if status == TaskStatus.RUNNING and "started_at" not in status_info:
            status_info["started_at"] = datetime.utcnow().isoformat()
        if completed:
            status_info["completed_at"] = datetime.utcnow().isoformat()

        # Store with TTL
        self.redis.setex(status_key, self.result_ttl, json.dumps(status_info))

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return None


# Simple factory function
def create_redis_queue(
    redis_url: str | None = None,
    queue_name: str = "dotmac:tasks",
    **kwargs: Any,
) -> RedisTaskQueue:
    """
    Create a Redis task queue instance.

    Args:
        redis_url: Redis connection URL
        queue_name: Queue name prefix
        **kwargs: Additional Redis client options

    Returns:
        Configured RedisTaskQueue instance

    Raises:
        ImportError: If Redis is not installed
    """
    if not REDIS_AVAILABLE:
        msg = "Redis not available. Install with: pip install dotmac-tasks-utils[redis]"
        raise ImportError(msg)

    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=True, **kwargs)
    else:
        redis_client = redis.Redis(decode_responses=True, **kwargs)

    return RedisTaskQueue(redis_client, queue_name)
