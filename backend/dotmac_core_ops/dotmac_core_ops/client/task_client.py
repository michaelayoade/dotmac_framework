"""
Task client for interacting with task APIs.
"""

from typing import Dict, Any, List, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus, Priority

logger = structlog.get_logger(__name__)


class TaskClient:
    """Client for task operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_task(
        self,
        name: str,
        description: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        timeout_seconds: Optional[int] = None,
        retry_count: int = 3,
        dependencies: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create and submit a new task.

        Args:
            name: Task name
            description: Task description
            priority: Task priority
            timeout_seconds: Task timeout
            retry_count: Retry count
            dependencies: Task dependencies
            input_data: Input data

        Returns:
            Task ID
        """
        payload = {
            "name": name,
            "description": description,
            "priority": priority.value,
            "timeout_seconds": timeout_seconds,
            "retry_count": retry_count,
            "dependencies": dependencies or [],
            "input_data": input_data or {}
        }

        response = await self.client.post("/tasks/", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["task_id"]

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[ExecutionStatus] = None,
        priority_filter: Optional[Priority] = None
    ) -> Dict[str, Any]:
        """
        List tasks with optional filtering.

        Args:
            page: Page number
            page_size: Items per page
            status_filter: Filter by status
            priority_filter: Filter by priority

        Returns:
            List of tasks with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if status_filter:
            params["status_filter"] = status_filter.value
        if priority_filter:
            params["priority_filter"] = priority_filter.value

        response = await self.client.get("/tasks/", params=params)
        response.raise_for_status()

        return response.json()

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get task details by ID.

        Args:
            task_id: Task ID

        Returns:
            Task details
        """
        response = await self.client.get(f"/tasks/{task_id}")
        response.raise_for_status()

        return response.json()

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled successfully
        """
        response = await self.client.post(f"/tasks/{task_id}/cancel")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task.

        Args:
            task_id: Task ID

        Returns:
            True if retry initiated successfully
        """
        response = await self.client.post(f"/tasks/{task_id}/retry")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get task queue status and statistics.

        Returns:
            Queue status information
        """
        response = await self.client.get("/tasks/queue/status")
        response.raise_for_status()

        return response.json()
