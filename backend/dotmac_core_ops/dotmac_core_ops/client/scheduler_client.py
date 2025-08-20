"""
Scheduler client for interacting with scheduler APIs.
"""

from typing import Dict, Any, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus

logger = structlog.get_logger(__name__)


class SchedulerClient:
    """Client for scheduler operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_schedule(
        self,
        name: str,
        cron_expression: str,
        job_data: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        timezone: str = "UTC",
        enabled: bool = True,
        max_instances: int = 1
    ) -> str:
        """
        Create a new schedule.

        Args:
            name: Schedule name
            cron_expression: Cron expression
            job_data: Job data
            description: Schedule description
            timezone: Timezone
            enabled: Schedule enabled status
            max_instances: Maximum concurrent instances

        Returns:
            Schedule ID
        """
        payload = {
            "name": name,
            "description": description,
            "cron_expression": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
            "job_data": job_data or {},
            "max_instances": max_instances
        }

        response = await self.client.post("/scheduler/schedules", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["schedule_id"]

    async def list_schedules(
        self,
        page: int = 1,
        page_size: int = 50,
        enabled_only: bool = False
    ) -> Dict[str, Any]:
        """
        List schedules.

        Args:
            page: Page number
            page_size: Items per page
            enabled_only: Show only enabled schedules

        Returns:
            List of schedules with pagination info
        """
        params = {"page": page, "page_size": page_size, "enabled_only": enabled_only}

        response = await self.client.get("/scheduler/schedules", params=params)
        response.raise_for_status()

        return response.json()

    async def get_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """
        Get schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule details
        """
        response = await self.client.get(f"/scheduler/schedules/{schedule_id}")
        response.raise_for_status()

        return response.json()

    async def update_schedule(
        self,
        schedule_id: str,
        name: str,
        cron_expression: str,
        job_data: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        timezone: str = "UTC",
        enabled: bool = True,
        max_instances: int = 1
    ) -> bool:
        """
        Update a schedule.

        Args:
            schedule_id: Schedule ID
            name: Schedule name
            cron_expression: Cron expression
            job_data: Job data
            description: Schedule description
            timezone: Timezone
            enabled: Schedule enabled status
            max_instances: Maximum concurrent instances

        Returns:
            True if updated successfully
        """
        payload = {
            "name": name,
            "description": description,
            "cron_expression": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
            "job_data": job_data or {},
            "max_instances": max_instances
        }

        response = await self.client.put(f"/scheduler/schedules/{schedule_id}", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def trigger_schedule(self, schedule_id: str) -> str:
        """
        Manually trigger a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            Job ID
        """
        response = await self.client.post(f"/scheduler/schedules/{schedule_id}/trigger")
        response.raise_for_status()

        result = response.json()
        return result["data"]["job_id"]

    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if deleted successfully
        """
        response = await self.client.delete(f"/scheduler/schedules/{schedule_id}")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 50,
        schedule_id: Optional[str] = None,
        status_filter: Optional[ExecutionStatus] = None
    ) -> Dict[str, Any]:
        """
        List scheduled jobs.

        Args:
            page: Page number
            page_size: Items per page
            schedule_id: Filter by schedule ID
            status_filter: Filter by execution status

        Returns:
            List of jobs with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if schedule_id:
            params["schedule_id"] = schedule_id
        if status_filter:
            params["status_filter"] = status_filter.value

        response = await self.client.get("/scheduler/jobs", params=params)
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
        response = await self.client.get(f"/scheduler/jobs/{job_id}")
        response.raise_for_status()

        return response.json()
