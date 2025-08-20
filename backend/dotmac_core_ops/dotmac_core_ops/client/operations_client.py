"""
Main operations client for interacting with the DotMac Core Operations platform.
"""

from typing import Dict, Any, Optional
import httpx
import structlog

from .workflow_client import WorkflowClient
from .task_client import TaskClient
from .automation_client import AutomationClient
from .scheduler_client import SchedulerClient
from .state_machine_client import StateMachineClient
from .saga_client import SagaClient
from .job_queue_client import JobQueueClient

logger = structlog.get_logger(__name__)


class OperationsClient:
    """
    Main client for the DotMac Core Operations platform.

    Provides access to all operations SDKs through a unified interface.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        tenant_id: str = "default-tenant",
        timeout: float = 30.0,
        **kwargs
    ):
        """
        Initialize the operations client.

        Args:
            base_url: Base URL of the operations platform
            api_key: API key for authentication
            tenant_id: Tenant ID for multi-tenancy
            timeout: Request timeout in seconds
            **kwargs: Additional httpx client options
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.timeout = timeout

        # Setup HTTP client
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": tenant_id,
        }

        if api_key:
            headers["X-API-Key"] = api_key

        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v1",
            headers=headers,
            timeout=timeout,
            **kwargs
        )

        # Initialize sub-clients
        self.workflows = WorkflowClient(self._client)
        self.tasks = TaskClient(self._client)
        self.automation = AutomationClient(self._client)
        self.scheduler = SchedulerClient(self._client)
        self.state_machines = StateMachineClient(self._client)
        self.sagas = SagaClient(self._client)
        self.job_queues = JobQueueClient(self._client)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the operations platform.

        Returns:
            Health status information
        """
        try:
            response = await httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            raise

    async def readiness_check(self) -> Dict[str, Any]:
        """
        Check if the operations platform is ready to serve requests.

        Returns:
            Readiness status information
        """
        try:
            response = await httpx.get(f"{self.base_url}/ready", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            raise

    async def get_platform_info(self) -> Dict[str, Any]:
        """
        Get platform information and capabilities.

        Returns:
            Platform information
        """
        health = await self.health_check()
        readiness = await self.readiness_check()

        return {
            "health": health,
            "readiness": readiness,
            "client_info": {
                "base_url": self.base_url,
                "tenant_id": self.tenant_id,
                "timeout": self.timeout,
            }
        }
