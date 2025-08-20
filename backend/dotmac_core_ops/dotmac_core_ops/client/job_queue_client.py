"""
Job Queue client for interacting with job queue APIs.
"""

from typing import Dict, Any, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus, Priority

logger = structlog.get_logger(__name__)


class JobQueueClient:
    """Client for job queue operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_job_definition(
        self,
        name: str,
        description: Optional[str] = None,
        queue_name: str = "default",
        priority: Priority = Priority.MEDIUM,
        timeout_seconds: Optional[int] = None,
        retry_count: int = 3,
        delay_seconds: int = 0
    ) -> str:
        """
        Create a new job definition.

        Args:
            name: Job definition name
            description: Job description
            queue_name: Queue name
            priority: Job priority
            timeout_seconds: Job timeout
            retry_count: Retry count
            delay_seconds: Delay before execution

        Returns:
            Job definition ID
        """
        payload = {
            "name": name,
            "description": description,
            "queue_name": queue_name,
            "priority": priority.value,
            "timeout_seconds": timeout_seconds,
            "retry_count": retry_count,
            "delay_seconds": delay_seconds
        }

        response = await self.client.post("/job-queues/definitions", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["job_definition_id"]

    async def list_job_definitions(
        self,
        page: int = 1,
        page_size: int = 50,
        queue_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List job definitions.

        Args:
            page: Page number
            page_size: Items per page
            queue_name: Filter by queue name

        Returns:
            List of job definitions with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if queue_name:
            params["queue_name"] = queue_name

        response = await self.client.get("/job-queues/definitions", params=params)
        response.raise_for_status()

        return response.json()

    async def submit_job(
        self,
        job_definition_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        priority: Optional[Priority] = None,
        delay_seconds: Optional[int] = None
    ) -> str:
        """
        Submit a job for execution.

        Args:
            job_definition_id: Job definition ID
            input_data: Job input data
            priority: Override priority
            delay_seconds: Override delay

        Returns:
            Job ID
        """
        payload = {
            "job_definition_id": job_definition_id,
            "input_data": input_data or {},
            "priority": priority.value if priority else None,
            "delay_seconds": delay_seconds
        }

        response = await self.client.post("/job-queues/jobs", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["job_id"]

    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 50,
        queue_name: Optional[str] = None,
        status_filter: Optional[ExecutionStatus] = None
    ) -> Dict[str, Any]:
        """
        List jobs.

        Args:
            page: Page number
            page_size: Items per page
            queue_name: Filter by queue name
            status_filter: Filter by execution status

        Returns:
            List of jobs with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if queue_name:
            params["queue_name"] = queue_name
        if status_filter:
            params["status_filter"] = status_filter.value

        response = await self.client.get("/job-queues/jobs", params=params)
        response.raise_for_status()

        return response.json()

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get job details by ID.

        Args:
            job_id: Job ID

        Returns:
            Job details
        """
        response = await self.client.get(f"/job-queues/jobs/{job_id}")
        response.raise_for_status()

        return response.json()

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled successfully
        """
        response = await self.client.post(f"/job-queues/jobs/{job_id}/cancel")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def retry_job(self, job_id: str) -> bool:
        """
        Retry a failed job.

        Args:
            job_id: Job ID

        Returns:
            True if retry initiated successfully
        """
        response = await self.client.post(f"/job-queues/jobs/{job_id}/retry")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def list_queues(self) -> Dict[str, Any]:
        """
        List all job queues and their status.

        Returns:
            Queue status information
        """
        response = await self.client.get("/job-queues/queues")
        response.raise_for_status()

        return response.json()

    async def list_dead_letter_jobs(
        self,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List jobs in the dead letter queue.

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            List of dead letter jobs with pagination info
        """
        params = {"page": page, "page_size": page_size}

        response = await self.client.get("/job-queues/dead-letter-queue", params=params)
        response.raise_for_status()

        return response.json()
