"""
Base Integration Service following DRY patterns
Enforces standardized integration patterns
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar
from uuid import UUID

from dotmac.application import standard_exception_handler
from dotmac.core.schemas.base_schemas import BaseResponseSchema
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseResponseSchema)


class IntegrationConfig(BaseModel):
    """Base configuration for integrations."""

    name: str
    description: str
    version: str
    enabled: bool = True
    auth_type: str = "none"  # none, api_key, oauth, jwt
    rate_limits: dict[str, int] = {}
    retry_config: dict[str, Any] = {"max_retries": 3, "backoff_factor": 2, "timeout": 30}


class IntegrationMetrics(BaseModel):
    """Integration performance metrics."""

    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    avg_response_time: float = 0.0
    last_success: Optional[str] = None
    last_error: Optional[str] = None


class BaseIntegration(ABC):
    """
    Base class for all integrations following DRY patterns.

    MANDATORY: All integrations MUST inherit from this class.
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID, config: IntegrationConfig):
        self.db = db
        self.tenant_id = tenant_id
        self.config = config
        self.metrics = IntegrationMetrics()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the integration. Returns True if successful."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check integration health. Must return status dict."""
        pass

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        """Authenticate with the external service."""
        pass

    @abstractmethod
    async def sync_data(self) -> dict[str, Any]:
        """Sync data from external service."""
        pass

    @standard_exception_handler
    async def get_metrics(self) -> IntegrationMetrics:
        """Get integration performance metrics."""
        return self.metrics

    @standard_exception_handler
    async def update_config(self, new_config: IntegrationConfig) -> bool:
        """Update integration configuration."""
        try:
            self.config = new_config
            self.logger.info(f"Updated configuration for {self.config.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update config: {str(e)}")
            return False

    @standard_exception_handler
    async def enable(self) -> bool:
        """Enable the integration."""
        self.config.enabled = True
        self.logger.info(f"Enabled integration: {self.config.name}")
        return True

    @standard_exception_handler
    async def disable(self) -> bool:
        """Disable the integration."""
        self.config.enabled = False
        self.logger.info(f"Disabled integration: {self.config.name}")
        return True

    def _record_success(self, response_time: float = 0.0):
        """Record successful request metrics."""
        self.metrics.requests_total += 1
        self.metrics.requests_success += 1
        if response_time > 0:
            # Simple moving average
            total_time = self.metrics.avg_response_time * (self.metrics.requests_total - 1)
            self.metrics.avg_response_time = (total_time + response_time) / self.metrics.requests_total
        self.metrics.last_success = "now"  # In production, use actual timestamp

    def _record_error(self, error: str):
        """Record failed request metrics."""
        self.metrics.requests_total += 1
        self.metrics.requests_failed += 1
        self.metrics.last_error = error
        self.logger.error(f"Integration error: {error}")

    @standard_exception_handler
    async def test_connection(self) -> dict[str, Any]:
        """Test connection to external service."""
        try:
            health = await self.health_check()
            self._record_success()
            return {"status": "connected", "details": health}
        except Exception as e:
            self._record_error(str(e))
            return {"status": "failed", "error": str(e)}


class ApiIntegration(BaseIntegration):
    """Base class for API-based integrations."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, config: IntegrationConfig):
        super().__init__(db, tenant_id, config)
        self.base_url: Optional[str] = None
        self.headers: dict[str, str] = {}

    @abstractmethod
    async def setup_auth_headers(self) -> dict[str, str]:
        """Setup authentication headers for API requests."""
        pass

    async def make_request(
        self, method: str, endpoint: str, data: Optional[dict[str, Any]] = None, params: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """Make authenticated API request with error handling."""
        import time

        import aiohttp

        if not self.config.enabled:
            raise Exception("Integration is disabled")

        if not self.base_url:
            raise Exception("Base URL not configured")

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {**self.headers, **(await self.setup_auth_headers())}

        start_time = time.time()

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.retry_config["timeout"]),
                ) as response:
                    response_time = time.time() - start_time

                    if response.status < 400:
                        result = (
                            await response.json()
                            if response.content_type == "application/json"
                            else await response.text()
                        )
                        self._record_success(response_time)
                        return result
                    else:
                        error_msg = f"API request failed with status {response.status}"
                        self._record_error(error_msg)
                        raise Exception(error_msg)

        except Exception as e:
            self._record_error(str(e))
            raise


class WebhookIntegration(BaseIntegration):
    """Base class for webhook-based integrations."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, config: IntegrationConfig):
        super().__init__(db, tenant_id, config)
        self.webhook_endpoints: list[str] = []
        self.webhook_secret: Optional[str] = None

    @abstractmethod
    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature."""
        pass

    @abstractmethod
    async def process_webhook_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Process incoming webhook event."""
        pass

    async def register_webhook_endpoint(self, endpoint: str) -> bool:
        """Register a new webhook endpoint."""
        if endpoint not in self.webhook_endpoints:
            self.webhook_endpoints.append(endpoint)
            self.logger.info(f"Registered webhook endpoint: {endpoint}")
            return True
        return False

    async def unregister_webhook_endpoint(self, endpoint: str) -> bool:
        """Unregister a webhook endpoint."""
        if endpoint in self.webhook_endpoints:
            self.webhook_endpoints.remove(endpoint)
            self.logger.info(f"Unregistered webhook endpoint: {endpoint}")
            return True
        return False
