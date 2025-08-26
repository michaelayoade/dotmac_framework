"""API client for communicating with DotMac Management Platform."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import httpx
from httpx import AsyncClient, HTTPStatusError, TimeoutException
from pydantic import BaseModel, Field

from dotmac_isp.core.enhanced_settings import get_settings


logger = logging.getLogger(__name__, timezone)


class PluginLicenseStatus(BaseModel):
    """Plugin license status response."""

    plugin_id: str
    tenant_id: str
    is_valid: bool
    license_status: str
    tier: str
    features: List[str] = Field(default_factory=list)
    usage_limits: Dict[str, int] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    reason: Optional[str] = None


class HealthStatusUpdate(BaseModel):
    """Health status update payload."""

    tenant_id: str
    component: str
    status: str  # healthy, unhealthy, warning
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[str] = None


class ConfigValidationRequest(BaseModel):
    """Configuration validation request."""

    tenant_id: str
    config_data: Dict[str, Any]
    config_version: Optional[str] = None
    validation_level: str = "standard"  # basic, standard, strict


class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""

    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_config: Optional[Dict[str, Any]] = None


class UsageMetric(BaseModel):
    """Usage metric report."""

    plugin_id: str
    metric_name: str
    usage_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ManagementPlatformClient:
    """Client for communicating with DotMac Management Platform."""

    def __init__(self):
        """  Init   operation."""
        self.settings = get_settings()
        self.base_url = os.getenv(
            "MANAGEMENT_PLATFORM_URL", "http://management-platform:8000"
        )
        self.api_key = os.getenv("MANAGEMENT_PLATFORM_API_KEY")
        self.tenant_id = os.getenv("ISP_TENANT_ID")
        self.timeout = httpx.Timeout(30.0)
        self._client: Optional[AsyncClient] = None

        if not self.tenant_id:
            logger.warning("ISP_TENANT_ID not configured - some features may not work")

        if not self.api_key:
            logger.warning(
                "MANAGEMENT_PLATFORM_API_KEY not configured - using internal communication"
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"DotMac-ISP-Framework/{self.tenant_id or 'unknown'}",
            }

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            if self.tenant_id:
                headers["X-Tenant-ID"] = self.tenant_id

            self._client = AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            )

    async def validate_plugin_license(
        self, plugin_id: str, feature: Optional[str] = None
    ) -> PluginLicenseStatus:
        """Validate plugin license with Management Platform.

        Args:
            plugin_id: Plugin identifier
            feature: Specific feature to validate (optional)

        Returns:
            PluginLicenseStatus: License validation result
        """
        try:
            await self._ensure_client()

            params = {"plugin_id": plugin_id}
            if feature:
                params["feature"] = feature

            response = await self._client.get(
                f"/api/v1/plugin-licensing/validate/{self.tenant_id}", params=params
            )
            response.raise_for_status()

            data = response.model_dump_json()
            return PluginLicenseStatus(**data)

        except HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Plugin license not found: {plugin_id}")
                return PluginLicenseStatus(
                    plugin_id=plugin_id,
                    tenant_id=self.tenant_id,
                    is_valid=False,
                    license_status="not_found",
                    tier="free",
                    reason="License not found",
                )
            elif e.response.status_code == 403:
                logger.warning(f"Plugin license expired or invalid: {plugin_id}")
                return PluginLicenseStatus(
                    plugin_id=plugin_id,
                    tenant_id=self.tenant_id,
                    is_valid=False,
                    license_status="expired",
                    tier="free",
                    reason="License expired or invalid",
                )
            else:
                logger.error(f"HTTP error validating license {plugin_id}: {e}")
                raise
        except TimeoutException:
            logger.error(f"Timeout validating license {plugin_id}")
            # Return cached/default response on timeout
            return PluginLicenseStatus(
                plugin_id=plugin_id,
                tenant_id=self.tenant_id,
                is_valid=False,
                license_status="validation_failed",
                tier="free",
                reason="Validation timeout",
            )
        except Exception as e:
            logger.error(f"Error validating plugin license {plugin_id}: {str(e)}")
            raise

    async def report_plugin_usage(
        self, plugin_id: str, metrics: List[UsageMetric]
    ) -> bool:
        """Report plugin usage metrics to Management Platform.

        Args:
            plugin_id: Plugin identifier
            metrics: List of usage metrics to report

        Returns:
            bool: True if reported successfully
        """
        try:
            await self._ensure_client()

            payload = {
                "tenant_id": self.tenant_id,
                "plugin_id": plugin_id,
                "metrics": [metric.model_dump() for metric in metrics],
            }

            response = await self._client.post(
                "/api/v1/plugin-licensing/usage", json=payload
            )
            response.raise_for_status()

            logger.debug(
                f"Reported {len(metrics)} usage metrics for plugin {plugin_id}"
            )
            return True

        except HTTPStatusError as e:
            logger.error(f"HTTP error reporting usage for {plugin_id}: {e}")
            return False
        except TimeoutException:
            logger.warning(f"Timeout reporting usage for {plugin_id}")
            return False
        except Exception as e:
            logger.error(f"Error reporting plugin usage {plugin_id}: {str(e)}")
            return False

    async def report_health_status(
        self,
        component: str,
        status: str,
        metrics: Dict[str, Any],
        details: Optional[str] = None,
    ) -> bool:
        """Report health status to Management Platform.

        Args:
            component: Component name (e.g., 'database', 'redis', 'api')
            status: Health status ('healthy', 'unhealthy', 'warning')
            metrics: Health metrics
            details: Optional details about the status

        Returns:
            bool: True if reported successfully
        """
        try:
            await self._ensure_client()

            health_update = HealthStatusUpdate(
                tenant_id=self.tenant_id,
                component=component,
                status=status,
                metrics=metrics,
                details=details,
            )

            response = await self._client.post(
                "/api/v1/saas-monitoring/health-status", json=health_update.model_dump()
            )
            response.raise_for_status()

            logger.debug(f"Reported health status for {component}: {status}")
            return True

        except HTTPStatusError as e:
            logger.error(f"HTTP error reporting health status: {e}")
            return False
        except TimeoutException:
            logger.warning(f"Timeout reporting health status for {component}")
            return False
        except Exception as e:
            logger.error(f"Error reporting health status: {str(e)}")
            return False

    async def validate_configuration(
        self, config_data: Dict[str, Any], config_version: Optional[str] = None
    ) -> ConfigValidationResponse:
        """Validate configuration with Management Platform.

        Args:
            config_data: Configuration data to validate
            config_version: Optional config version

        Returns:
            ConfigValidationResponse: Validation result
        """
        try:
            await self._ensure_client()

            request = ConfigValidationRequest(
                tenant_id=self.tenant_id,
                config_data=config_data,
                config_version=config_version,
            )

            response = await self._client.post(
                "/api/v1/config/validate", json=request.model_dump()
            )
            response.raise_for_status()

            data = response.model_dump_json()
            return ConfigValidationResponse(**data)

        except HTTPStatusError as e:
            logger.error(f"HTTP error validating configuration: {e}")
            return ConfigValidationResponse(
                is_valid=False,
                validation_errors=[f"HTTP error: {e.response.status_code}"],
            )
        except TimeoutException:
            logger.warning("Timeout validating configuration")
            return ConfigValidationResponse(
                is_valid=False, validation_errors=["Configuration validation timeout"]
            )
        except Exception as e:
            logger.error(f"Error validating configuration: {str(e)}")
            return ConfigValidationResponse(
                is_valid=False, validation_errors=[f"Validation error: {str(e)}"]
            )

    async def get_tenant_configuration(self) -> Dict[str, Any]:
        """Get current tenant configuration from Management Platform.

        Returns:
            Dict[str, Any]: Current tenant configuration
        """
        try:
            await self._ensure_client()

            response = await self._client.get(f"/api/v1/config/tenant/{self.tenant_id}")
            response.raise_for_status()

            return response.model_dump_json()

        except HTTPStatusError as e:
            logger.error(f"HTTP error getting tenant config: {e}")
            return {}
        except TimeoutException:
            logger.warning("Timeout getting tenant configuration")
            return {}
        except Exception as e:
            logger.error(f"Error getting tenant configuration: {str(e)}")
            return {}

    async def report_configuration_applied(
        self, config_version: str, success: bool, errors: Optional[List[str]] = None
    ) -> bool:
        """Report configuration application result to Management Platform.

        Args:
            config_version: Version of config that was applied
            success: Whether configuration was applied successfully
            errors: Any errors encountered during application

        Returns:
            bool: True if reported successfully
        """
        try:
            await self._ensure_client()

            payload = {
                "tenant_id": self.tenant_id,
                "config_version": config_version,
                "success": success,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "errors": errors or [],
            }

            response = await self._client.post("/api/v1/config/applied", json=payload)
            response.raise_for_status()

            logger.info(
                f"Reported config application: {config_version} success={success}"
            )
            return True

        except Exception as e:
            logger.error(f"Error reporting config application: {str(e)}")
            return False

    async def ping(self) -> bool:
        """Ping Management Platform to check connectivity.

        Returns:
            bool: True if Management Platform is reachable
        """
        try:
            await self._ensure_client()

            response = await self._client.get("/health")
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"Management Platform ping failed: {str(e)}")
            return False


# Global client instance
_management_client: Optional[ManagementPlatformClient] = None


async def get_management_client() -> ManagementPlatformClient:
    """Get global Management Platform client instance."""
    global _management_client
    if _management_client is None:
        _management_client = ManagementPlatformClient()
    return _management_client


async def close_management_client():
    """Close global Management Platform client."""
    global _management_client
    if _management_client and _management_client._client:
        await _management_client._client.aclose()
        _management_client = None
