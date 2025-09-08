"""Async task runner for dotmac-tasks-utils."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from .types import AsyncTaskFunction, TaskId, TaskOptions, TaskResult, TaskStatus


class AsyncTaskRunner:
    """
    Simple async task runner with result management.

    Provides in-memory task execution with status tracking and result storage.
    """

    def __init__(self, max_concurrent: int = 10) -> None:
        """
        Initialize the task runner.

        Args:
            max_concurrent: Maximum number of concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self._tasks: dict[TaskId, TaskResult[Any]] = {}
        self._running_tasks: dict[TaskId, asyncio.Task[Any]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def submit(
        self,
        func: AsyncTaskFunction,
        *args: Any,
        task_id: TaskId | None = None,
        options: TaskOptions | None = None,
        **kwargs: Any,
    ) -> TaskId:
        """
        Submit a task for execution.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            task_id: Optional custom task ID
            options: Task execution options
            **kwargs: Keyword arguments for the function

        Returns:
            Task ID for tracking
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        if options is None:
            options = TaskOptions()

        # Create task result
        result = TaskResult[Any](
            task_id=task_id,
            status=TaskStatus.PENDING,
            max_attempts=options.max_attempts,
        )

        self._tasks[task_id] = result

        # Apply delay if specified
        if options.delay and options.delay > 0:
            await asyncio.sleep(options.delay)

        # Start the task
        task = asyncio.create_task(self._execute_task(task_id, func, args, kwargs, options))
        self._running_tasks[task_id] = task

        return task_id

    async def get_result(self, task_id: TaskId, timeout: float | None = None) -> TaskResult[Any]:
        """
        Get task result, waiting for completion if necessary.

        Args:
            task_id: Task ID to get result for
            timeout: Optional timeout in seconds

        Returns:
            Task result

        Raises:
            KeyError: If task ID not found
            asyncio.TimeoutError: If timeout exceeded
        """
        if task_id not in self._tasks:
            msg = f"Task {task_id} not found"
            raise KeyError(msg)

        # If task is still running, wait for it
        if task_id in self._running_tasks:
            try:
                if timeout:
                    await asyncio.wait_for(self._running_tasks[task_id], timeout=timeout)
                else:
                    await self._running_tasks[task_id]
            except asyncio.TimeoutError:
                # Task is still running, return current status
                pass

        return self._tasks[task_id]

    def get_status(self, task_id: TaskId) -> TaskResult[Any]:
        """
        Get current task status without waiting.

        Args:
            task_id: Task ID to check

        Returns:
            Current task result

        Raises:
            KeyError: If task ID not found
        """
        if task_id not in self._tasks:
            msg = f"Task {task_id} not found"
            raise KeyError(msg)

        return self._tasks[task_id]

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int | None = None,
    ) -> list[TaskResult[Any]]:
        """
        List tasks with optional filtering.

        Args:
            status: Optional status filter
            limit: Optional limit on number of results

        Returns:
            List of task results
        """
        tasks = list(self._tasks.values())

        # Apply status filter
        if status:
            tasks = [task for task in tasks if task.status == status]

        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.started_at or datetime.min, reverse=True)

        # Apply limit
        if limit:
            tasks = tasks[:limit]

        return tasks

    async def cancel(self, task_id: TaskId) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled, False if not running
        """
        if task_id not in self._running_tasks:
            return False

        task = self._running_tasks[task_id]
        task.cancel()

        # Update result
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.CANCELLED
            self._tasks[task_id].completed_at = datetime.utcnow()

        return True

    def cleanup_completed(self, max_age_seconds: float = 3600) -> int:
        """
        Remove completed tasks older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of tasks removed
        """
        cutoff_time = datetime.utcnow().timestamp() - max_age_seconds
        removed_count = 0

        # Find tasks to remove
        tasks_to_remove = []
        for task_id, result in self._tasks.items():
            if (
                result.is_complete() and
                result.completed_at and
                result.completed_at.timestamp() < cutoff_time
            ):
                tasks_to_remove.append(task_id)

        # Remove them
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            removed_count += 1

        return removed_count

    async def _execute_task(
        self,
        task_id: TaskId,
        func: AsyncTaskFunction,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        options: TaskOptions,
    ) -> None:
        """Execute a task with retry logic and error handling."""
        result = self._tasks[task_id]

        async with self._semaphore:  # Limit concurrent executions
            for attempt in range(1, options.max_attempts + 1):
                result.attempts = attempt
                result.status = TaskStatus.RUNNING
                result.started_at = datetime.utcnow()

                try:
                    # Execute with timeout if specified
                    if options.timeout:
                        task_result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=options.timeout
                        )
                    else:
                        task_result = await func(*args, **kwargs)

                    # Success
                    result.result = task_result
                    result.status = TaskStatus.SUCCESS
                    result.completed_at = datetime.utcnow()
                    break

                except asyncio.CancelledError:
                    result.status = TaskStatus.CANCELLED
                    result.completed_at = datetime.utcnow()
                    break

                except asyncio.TimeoutError:
                    error_msg = f"Task timed out after {options.timeout}s"
                    result.error = error_msg

                    if attempt < options.max_attempts:
                        result.status = TaskStatus.RETRY
                        # Simple exponential backoff
                        await asyncio.sleep(min(2 ** attempt, 60))
                    else:
                        result.status = TaskStatus.FAILED
                        result.completed_at = datetime.utcnow()

                except Exception as e:  # noqa: BLE001
                    result.error = str(e)

                    if attempt < options.max_attempts:
                        result.status = TaskStatus.RETRY
                        # Simple exponential backoff
                        await asyncio.sleep(min(2 ** attempt, 60))
                    else:
                        result.status = TaskStatus.FAILED
                        result.completed_at = datetime.utcnow()

        # Remove from running tasks
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]
