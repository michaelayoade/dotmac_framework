"""
Saga client for interacting with saga APIs.
"""

from typing import Dict, Any, List, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus

logger = structlog.get_logger(__name__)


class SagaClient:
    """Client for saga operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_saga(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> str:
        """
        Create a new saga definition.

        Args:
            name: Saga name
            steps: Saga step definitions
            description: Saga description
            timeout_seconds: Saga timeout

        Returns:
            Saga ID
        """
        payload = {
            "name": name,
            "description": description,
            "steps": steps,
            "timeout_seconds": timeout_seconds
        }

        response = await self.client.post("/sagas/", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["saga_id"]

    async def list_sagas(
        self,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List saga definitions.

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            List of sagas with pagination info
        """
        params = {"page": page, "page_size": page_size}

        response = await self.client.get("/sagas/", params=params)
        response.raise_for_status()

        return response.json()

    async def get_saga(self, saga_id: str) -> Dict[str, Any]:
        """
        Get saga definition by ID.

        Args:
            saga_id: Saga ID

        Returns:
            Saga details
        """
        response = await self.client.get(f"/sagas/{saga_id}")
        response.raise_for_status()

        return response.json()

    async def execute_saga(
        self,
        saga_id: str,
        input_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a saga.

        Args:
            saga_id: Saga ID
            input_data: Input data

        Returns:
            Execution ID
        """
        payload = {"input_data": input_data or {}}

        response = await self.client.post(f"/sagas/{saga_id}/execute", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["execution_id"]

    async def list_executions(
        self,
        saga_id: str,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[ExecutionStatus] = None
    ) -> Dict[str, Any]:
        """
        List saga executions.

        Args:
            saga_id: Saga ID
            page: Page number
            page_size: Items per page
            status_filter: Filter by execution status

        Returns:
            List of executions with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if status_filter:
            params["status_filter"] = status_filter.value

        response = await self.client.get(f"/sagas/{saga_id}/executions", params=params)
        response.raise_for_status()

        return response.json()

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Get saga execution details.

        Args:
            execution_id: Execution ID

        Returns:
            Execution details
        """
        response = await self.client.get(f"/sagas/executions/{execution_id}")
        response.raise_for_status()

        return response.json()

    async def compensate_saga(self, execution_id: str) -> bool:
        """
        Manually trigger compensation for a saga execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if compensation initiated successfully
        """
        response = await self.client.post(f"/sagas/executions/{execution_id}/compensate")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a saga execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled successfully
        """
        response = await self.client.post(f"/sagas/executions/{execution_id}/cancel")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def delete_saga(self, saga_id: str) -> bool:
        """
        Delete a saga definition.

        Args:
            saga_id: Saga ID

        Returns:
            True if deleted successfully
        """
        response = await self.client.delete(f"/sagas/{saga_id}")
        response.raise_for_status()

        result = response.json()
        return result["success"]
