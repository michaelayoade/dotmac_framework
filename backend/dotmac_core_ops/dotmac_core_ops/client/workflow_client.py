"""
Workflow client for interacting with workflow APIs.
"""

from typing import Dict, Any, Optional
import httpx
import structlog

from ..contracts.common_schemas import ExecutionStatus

logger = structlog.get_logger(__name__)


class WorkflowClient:
    """Client for workflow operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def create_workflow(
        self,
        name: str,
        definition: Dict[str, Any],
        version: str = "1.0",
        description: Optional[str] = None
    ) -> str:
        """
        Create a new workflow definition.

        Args:
            name: Workflow name
            definition: Workflow definition
            version: Workflow version
            description: Workflow description

        Returns:
            Workflow ID
        """
        payload = {
            "name": name,
            "version": version,
            "description": description,
            "definition": definition
        }

        response = await self.client.post("/workflows/", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["workflow_id"]

    async def list_workflows(
        self,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List workflow definitions.

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            List of workflows with pagination info
        """
        params = {"page": page, "page_size": page_size}

        response = await self.client.get("/workflows/", params=params)
        response.raise_for_status()

        return response.json()

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow definition by ID.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow definition
        """
        response = await self.client.get(f"/workflows/{workflow_id}")
        response.raise_for_status()

        return response.json()

    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow ID
            input_data: Input data for execution
            context: Execution context

        Returns:
            Execution ID
        """
        payload = {
            "input_data": input_data or {},
            "context": context
        }

        response = await self.client.post(f"/workflows/{workflow_id}/execute", json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"]["execution_id"]

    async def list_executions(
        self,
        workflow_id: str,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[ExecutionStatus] = None
    ) -> Dict[str, Any]:
        """
        List workflow executions.

        Args:
            workflow_id: Workflow ID
            page: Page number
            page_size: Items per page
            status_filter: Filter by execution status

        Returns:
            List of executions with pagination info
        """
        params = {"page": page, "page_size": page_size}
        if status_filter:
            params["status_filter"] = status_filter.value

        response = await self.client.get(f"/workflows/{workflow_id}/executions", params=params)
        response.raise_for_status()

        return response.json()

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Get workflow execution details.

        Args:
            execution_id: Execution ID

        Returns:
            Execution details
        """
        response = await self.client.get(f"/workflows/executions/{execution_id}")
        response.raise_for_status()

        return response.json()

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a workflow execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled successfully
        """
        response = await self.client.post(f"/workflows/executions/{execution_id}/cancel")
        response.raise_for_status()

        result = response.json()
        return result["success"]

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow definition.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted successfully
        """
        response = await self.client.delete(f"/workflows/{workflow_id}")
        response.raise_for_status()

        result = response.json()
        return result["success"]
