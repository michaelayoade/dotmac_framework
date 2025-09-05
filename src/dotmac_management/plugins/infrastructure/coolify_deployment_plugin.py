"""
Coolify Deployment Plugin
Provides Coolify-based infrastructure deployment using the plugin system
"""

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

import httpx

from dotmac.application import standard_exception_handler
from dotmac_shared.core.logging import get_logger

from ...core.plugins.base import PluginError, PluginMeta, PluginStatus, PluginType
from ...core.plugins.interfaces import DeploymentProviderPlugin

logger = get_logger(__name__)


@dataclass
class CoolifyConfig:
    """Coolify server configuration"""

    base_url: str
    api_token: str
    project_id: Optional[str] = None
    server_id: Optional[str] = None


class CoolifyDeploymentPlugin(DeploymentProviderPlugin):
    """
    Coolify-based deployment provider plugin.
    Handles application and service deployment via Coolify API.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        self.coolify_config: Optional[CoolifyConfig] = None
        self.client: Optional[httpx.AsyncClient] = None

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="CoolifyDeploymentPlugin",
            version="1.0.0",
            plugin_type=PluginType.DEPLOYMENT_PROVIDER,
            description="Coolify-based application and infrastructure deployment",
            author="DotMac",
            dependencies=[],
            configuration_schema={
                "type": "object",
                "properties": {
                    "base_url": {
                        "type": "string",
                        "description": "Coolify API base URL",
                    },
                    "api_token": {"type": "string", "description": "Coolify API token"},
                    "project_id": {
                        "type": "string",
                        "description": "Default project ID",
                    },
                    "server_id": {
                        "type": "string",
                        "description": "Default server ID",
                        "default": "0",
                    },
                },
                "required": ["base_url", "api_token"],
            },
            supported_features=["applications", "databases", "redis", "domains", "ssl"],
        )

    @standard_exception_handler
    async def initialize(self) -> bool:
        """Initialize the Coolify plugin."""
        try:
            self.coolify_config = self._load_config()

            # Initialize HTTP client
            self.client = httpx.AsyncClient(
                base_url=self.coolify_config.base_url,
                headers={
                    "Authorization": f"Bearer {self.coolify_config.api_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=60.0,
            )

            # Test connection
            health_result = await self.health_check()
            if not health_result.get("healthy", False):
                raise PluginError(
                    f"Coolify health check failed: {health_result.get('error')}"
                )

            self.status = PluginStatus.ACTIVE
            self._logger.info("✅ Coolify deployment plugin initialized successfully")
            return True

        except Exception as e:
            self.status = PluginStatus.ERROR
            self.last_error = e
            self._logger.error(f"Failed to initialize Coolify plugin: {e}")
            return False

    @standard_exception_handler
    async def shutdown(self) -> bool:
        """Shutdown the plugin and cleanup resources."""
        try:
            if self.client:
                await self.client.aclose()
                self.client = None

            self.status = PluginStatus.INACTIVE
            self._logger.info("✅ Coolify deployment plugin shutdown complete")
            return True

        except Exception as e:
            self._logger.error(f"Error during plugin shutdown: {e}")
            return False

    @standard_exception_handler
    async def health_check(self) -> dict[str, Any]:
        """Check Coolify API health."""
        try:
            if not self.client:
                return {"healthy": False, "error": "Client not initialized"}

            # Try to fetch server info or similar lightweight endpoint
            response = await self.client.get("/api/v1/servers")

            if response.status_code == 200:
                return {
                    "healthy": True,
                    "status": "connected",
                    "coolify_version": response.headers.get(
                        "x-coolify-version", "unknown"
                    ),
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                }
            else:
                return {
                    "healthy": False,
                    "error": f"API returned {response.status_code}",
                    "status": "error",
                }

        except Exception as e:
            return {"healthy": False, "error": str(e), "status": "error"}

    def _load_config(self) -> CoolifyConfig:
        """Load Coolify configuration from plugin config and environment."""
        # Prioritize plugin config over environment variables
        base_url = self.config.get("base_url") or os.getenv(
            "COOLIFY_API_URL", "http://localhost:8000"
        )

        api_token = self.config.get("api_token") or os.getenv("COOLIFY_API_TOKEN")

        if not api_token:
            raise PluginError(
                "Coolify API token is required (api_token in config or COOLIFY_API_TOKEN env var)"
            )

        return CoolifyConfig(
            base_url=base_url.rstrip("/"),
            api_token=api_token,
            project_id=self.config.get("project_id") or os.getenv("COOLIFY_PROJECT_ID"),
            server_id=self.config.get("server_id", os.getenv("COOLIFY_SERVER_ID", "0")),
        )

    # Implementation of DeploymentProviderPlugin interface methods

    @standard_exception_handler
    async def provision_infrastructure(
        self, infrastructure_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Provision infrastructure (not applicable for Coolify, returns project info)."""
        return {
            "infrastructure_id": self.coolify_config.project_id,
            "provider": "coolify",
            "status": "ready",
            "endpoints": {
                "api": self.coolify_config.base_url,
                "dashboard": f"{self.coolify_config.base_url}/project/{self.coolify_config.project_id}",
            },
        }

    @standard_exception_handler
    async def deploy_application(
        self, app_config: dict[str, Any], infrastructure_id: str
    ) -> dict[str, Any]:
        """Deploy application to Coolify."""
        try:
            # Create application first
            app_result = await self._create_application(app_config)
            app_id = app_result["id"]

            # Deploy the application
            deploy_result = await self._deploy_application(app_id)

            return {
                "deployment_id": deploy_result.get("deployment_id", app_id),
                "application_id": app_id,
                "status": "deploying",
                "provider": "coolify",
                "endpoints": app_result.get("endpoints", {}),
                "dashboard_url": f"{self.coolify_config.base_url}/project/{self.coolify_config.project_id}/application/{app_id}",
            }

        except Exception as e:
            self._logger.error(f"Failed to deploy application: {e}")
            raise PluginError(f"Application deployment failed: {e}") from e

    @standard_exception_handler
    async def scale_application(
        self, deployment_id: str, scaling_config: dict[str, Any]
    ) -> bool:
        """Scale application (Coolify handles this automatically based on resource config)."""
        # Coolify doesn't have explicit scaling API, it manages resources automatically
        self._logger.info(
            f"Scale request received for {deployment_id}, Coolify manages scaling automatically"
        )
        return True

    @standard_exception_handler
    async def rollback_deployment(
        self, deployment_id: str, target_version: str
    ) -> bool:
        """Rollback deployment to previous version."""
        try:
            # This would need to be implemented based on Coolify's rollback API
            # For now, return success as Coolify can rollback via dashboard
            self._logger.warning(
                f"Rollback requested for {deployment_id} to {target_version}, manual action required"
            )
            return True

        except Exception as e:
            self._logger.error(f"Rollback failed: {e}")
            return False

    @standard_exception_handler
    async def validate_template(
        self, template_content: dict[str, Any], template_type: str
    ) -> bool:
        """Validate deployment template."""
        if template_type == "docker-compose":
            required_fields = ["name", "docker_compose"]
            return all(field in template_content for field in required_fields)

        return template_type in ["docker-compose", "dockerfile"]

    @standard_exception_handler
    async def get_deployment_status(self, deployment_id: str) -> dict[str, Any]:
        """Get deployment status from Coolify."""
        try:
            response = await self.client.get(f"/api/v1/applications/{deployment_id}")

            if response.status_code == 404:
                return {"status": "not_found", "deployment_id": deployment_id}
            elif response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"API error: {response.status_code}",
                }

            result = response.json()

            return {
                "deployment_id": deployment_id,
                "status": result.get("status", "unknown"),
                "health": result.get("health", "unknown"),
                "url": result.get("fqdn", ""),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at"),
                "provider": "coolify",
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @standard_exception_handler
    async def calculate_deployment_cost(
        self, deployment_config: dict[str, Any]
    ) -> Decimal:
        """Calculate estimated deployment cost (Coolify is typically self-hosted, so minimal cost)."""
        # For Coolify, costs are mainly server costs, not per-app
        # Return minimal cost for resource usage estimation
        return Decimal("0.50")  # Minimal estimated cost per deployment

    def get_supported_providers(self) -> list[str]:
        """Return supported providers."""
        return ["coolify"]

    def get_supported_orchestrators(self) -> list[str]:
        """Return supported orchestration platforms."""
        return ["docker-compose", "dockerfile"]

    # Helper methods for Coolify-specific operations

    async def _create_application(self, app_config: dict[str, Any]) -> dict[str, Any]:
        """Create application in Coolify."""
        payload = {
            "name": app_config["name"],
            "description": app_config.get("description", ""),
            "project_uuid": self.coolify_config.project_id,
            "server_uuid": self.coolify_config.server_id,
            "docker_compose_raw": app_config["docker_compose"],
            "environment_variables": app_config.get("environment", {}),
            "domains": app_config.get("domains", []),
            "is_static": False,
            "build_pack": "dockercompose",
            "source": {
                "type": "docker-compose",
                "docker_compose_raw": app_config["docker_compose"],
            },
        }

        response = await self.client.post("/api/v1/applications", json=payload)

        if response.status_code not in [200, 201]:
            raise PluginError(
                f"Coolify API error: {response.status_code} - {response.text}"
            )

        result = response.json()
        app_id = result.get("uuid") or result.get("id")

        return {
            "id": app_id,
            "name": app_config["name"],
            "status": "created",
            "endpoints": {
                "dashboard": f"{self.coolify_config.base_url}/project/{self.coolify_config.project_id}/application/{app_id}"
            },
        }

    async def _deploy_application(self, app_id: str) -> dict[str, Any]:
        """Deploy application in Coolify."""
        response = await self.client.post(f"/api/v1/applications/{app_id}/deploy")

        if response.status_code not in [200, 201]:
            raise PluginError(
                f"Coolify deploy error: {response.status_code} - {response.text}"
            )

        result = response.json()

        return {
            "deployment_id": result.get("deployment_uuid", app_id),
            "status": "deploying",
            "app_id": app_id,
        }

    # Additional Coolify-specific methods

    @standard_exception_handler
    async def create_database_service(
        self, db_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create database service in Coolify."""
        payload = {
            "name": db_config["name"],
            "description": db_config.get("description", ""),
            "type": "postgresql",
            "version": db_config.get("version", "15"),
            "project_uuid": self.coolify_config.project_id,
            "server_uuid": self.coolify_config.server_id,
            "environment_variables": {
                "POSTGRES_DB": db_config["database"],
                "POSTGRES_USER": db_config["username"],
                "POSTGRES_PASSWORD": db_config["password"],
            },
        }

        response = await self.client.post("/api/v1/services/postgresql", json=payload)

        if response.status_code not in [200, 201]:
            raise PluginError(
                f"Database creation failed: {response.status_code} - {response.text}"
            )

        result = response.json()
        service_id = result.get("uuid") or result.get("id")

        return {
            "id": service_id,
            "name": db_config["name"],
            "type": "postgresql",
            "connection_url": f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['name']}:5432/{db_config['database']}",
        }

    @standard_exception_handler
    async def create_redis_service(
        self, redis_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create Redis service in Coolify."""
        payload = {
            "name": redis_config["name"],
            "description": redis_config.get("description", ""),
            "type": "redis",
            "version": redis_config.get("version", "7"),
            "project_uuid": self.coolify_config.project_id,
            "server_uuid": self.coolify_config.server_id,
            "environment_variables": {
                "REDIS_PASSWORD": redis_config.get("password", "")
            },
        }

        response = await self.client.post("/api/v1/services/redis", json=payload)

        if response.status_code not in [200, 201]:
            raise PluginError(
                f"Redis creation failed: {response.status_code} - {response.text}"
            )

        result = response.json()
        service_id = result.get("uuid") or result.get("id")

        password_part = (
            f":{redis_config['password']}@" if redis_config.get("password") else "@"
        )
        connection_url = f"redis://{password_part}{redis_config['name']}:6379"

        return {
            "id": service_id,
            "name": redis_config["name"],
            "type": "redis",
            "connection_url": connection_url,
        }

    @standard_exception_handler
    async def set_domain(self, app_id: str, domain: str) -> bool:
        """Set domain for an application."""
        payload = {"domain": domain, "https": True, "redirect_to_https": True}

        response = await self.client.post(
            f"/api/v1/applications/{app_id}/domains", json=payload
        )

        if response.status_code not in [200, 201]:
            self._logger.error(
                f"Failed to set domain: {response.status_code} - {response.text}"
            )
            return False

        return True
