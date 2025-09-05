"""
Coolify API Client
Handles communication with Coolify server for tenant provisioning
"""

import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from dotmac_shared.core.error_utils import service_operation
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CoolifyConfig:
    """Coolify server configuration"""

    base_url: str
    api_token: str
    project_id: Optional[str] = None
    server_id: Optional[str] = None


class CoolifyClient:
    """
    Client for Coolify API operations
    Handles tenant infrastructure provisioning
    """

    def __init__(self):
        self.config = self._load_config()
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={
                "Authorization": f"Bearer {self.config.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=60.0,
        )

    def _load_config(self) -> CoolifyConfig:
        """Load Coolify configuration from environment"""

        base_url = os.getenv("COOLIFY_API_URL", "http://localhost:8000")
        api_token = os.getenv("COOLIFY_API_TOKEN")

        if not api_token:
            raise ValueError("COOLIFY_API_TOKEN environment variable is required")

        return CoolifyConfig(
            base_url=base_url.rstrip("/"),
            api_token=api_token,
            project_id=os.getenv("COOLIFY_PROJECT_ID"),
            server_id=os.getenv("COOLIFY_SERVER_ID", "0"),
        )

    @service_operation("coolify")
    async def create_application(self, app_config: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new application in Coolify

        Args:
            app_config: Application configuration including docker-compose content

        Returns:
            Dictionary with application details including ID
        """

        try:
            payload = {
                "name": app_config["name"],
                "description": app_config.get("description", ""),
                "project_uuid": self.config.project_id,
                "server_uuid": self.config.server_id,
                "docker_compose_raw": app_config["docker_compose"],
                "environment_variables": app_config.get("environment", {}),
                "domains": app_config.get("domains", []),
                "is_static": False,
                "build_pack": "dockercompose",
                "source": {"type": "docker-compose", "docker_compose_raw": app_config["docker_compose"]},
            }

            logger.info(f"Creating Coolify application: {app_config['name']}")

            response = await self.client.post("/api/v1/applications", json=payload)

            if response.status_code not in [200, 201]:
                raise Exception(f"Coolify API error: {response.status_code} - {response.text}")

            result = response.json()
            app_id = result.get("uuid") or result.get("id")

            logger.info(f"✅ Coolify application created: {app_id}")

            return {
                "id": app_id,
                "name": app_config["name"],
                "status": "created",
                "url": f"{self.config.base_url}/project/{self.config.project_id}/application/{app_id}",
            }

        except Exception as e:
            logger.error(f"Failed to create Coolify application: {e}")
            raise

    @service_operation("coolify")
    async def deploy_application(self, app_id: str) -> dict[str, Any]:
        """
        Deploy an application in Coolify

        Args:
            app_id: Application ID

        Returns:
            Deployment status information
        """

        try:
            logger.info(f"Deploying Coolify application: {app_id}")

            response = await self.client.post(f"/api/v1/applications/{app_id}/deploy")

            if response.status_code not in [200, 201]:
                raise Exception(f"Coolify deploy error: {response.status_code} - {response.text}")

            result = response.json()

            logger.info(f"✅ Coolify application deployment started: {app_id}")

            return {"deployment_id": result.get("deployment_uuid"), "status": "deploying", "app_id": app_id}

        except Exception as e:
            logger.error(f"Failed to deploy Coolify application: {e}")
            raise

    @service_operation("coolify")
    async def get_application_status(self, app_id: str) -> dict[str, Any]:
        """
        Get application status from Coolify

        Args:
            app_id: Application ID

        Returns:
            Application status information
        """

        try:
            response = await self.client.get(f"/api/v1/applications/{app_id}")

            if response.status_code == 404:
                return {"status": "not_found"}
            elif response.status_code != 200:
                raise Exception(f"Coolify API error: {response.status_code} - {response.text}")

            result = response.json()

            return {
                "id": app_id,
                "status": result.get("status", "unknown"),
                "health": result.get("health", "unknown"),
                "url": result.get("fqdn", ""),
                "created_at": result.get("created_at"),
                "updated_at": result.get("updated_at"),
            }

        except Exception as e:
            logger.error(f"Failed to get Coolify application status: {e}")
            raise

    @service_operation("coolify")
    async def get_deployment_logs(self, app_id: str, deployment_id: Optional[str] = None) -> list[str]:
        """
        Get deployment logs from Coolify

        Args:
            app_id: Application ID
            deployment_id: Specific deployment ID (optional)

        Returns:
            List of log lines
        """

        try:
            if deployment_id:
                endpoint = f"/api/v1/applications/{app_id}/deployments/{deployment_id}/logs"
            else:
                endpoint = f"/api/v1/applications/{app_id}/logs"

            response = await self.client.get(endpoint)

            if response.status_code != 200:
                logger.warning(f"Could not fetch logs: {response.status_code}")
                return []

            result = response.json()
            return result.get("logs", [])

        except Exception as e:
            logger.error(f"Failed to get deployment logs: {e}")
            return []

    @service_operation("coolify")
    async def create_database_service(self, db_config: dict[str, Any]) -> dict[str, Any]:
        """
        Create a database service in Coolify

        Args:
            db_config: Database configuration

        Returns:
            Database service information
        """

        try:
            payload = {
                "name": db_config["name"],
                "description": db_config.get("description", ""),
                "type": "postgresql",
                "version": db_config.get("version", "15"),
                "project_uuid": self.config.project_id,
                "server_uuid": self.config.server_id,
                "environment_variables": {
                    "POSTGRES_DB": db_config["database"],
                    "POSTGRES_USER": db_config["username"],
                    "POSTGRES_PASSWORD": db_config["password"],
                },
            }

            logger.info(f"Creating Coolify database service: {db_config['name']}")

            response = await self.client.post("/api/v1/services/postgresql", json=payload)

            if response.status_code not in [200, 201]:
                raise Exception(f"Coolify database API error: {response.status_code} - {response.text}")

            result = response.json()
            service_id = result.get("uuid") or result.get("id")

            logger.info(f"✅ Coolify database service created: {service_id}")

            return {
                "id": service_id,
                "name": db_config["name"],
                "type": "postgresql",
                "connection_url": f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['name']}:5432/{db_config['database']}",
            }

        except Exception as e:
            logger.error(f"Failed to create database service: {e}")
            raise

    @service_operation("coolify")
    async def create_redis_service(self, redis_config: dict[str, Any]) -> dict[str, Any]:
        """
        Create a Redis service in Coolify

        Args:
            redis_config: Redis configuration

        Returns:
            Redis service information
        """

        try:
            payload = {
                "name": redis_config["name"],
                "description": redis_config.get("description", ""),
                "type": "redis",
                "version": redis_config.get("version", "7"),
                "project_uuid": self.config.project_id,
                "server_uuid": self.config.server_id,
                "environment_variables": {"REDIS_PASSWORD": redis_config.get("password", "")},
            }

            logger.info(f"Creating Coolify Redis service: {redis_config['name']}")

            response = await self.client.post("/api/v1/services/redis", json=payload)

            if response.status_code not in [200, 201]:
                raise Exception(f"Coolify Redis API error: {response.status_code} - {response.text}")

            result = response.json()
            service_id = result.get("uuid") or result.get("id")

            logger.info(f"✅ Coolify Redis service created: {service_id}")

            password_part = f":{redis_config['password']}@" if redis_config.get("password") else "@"
            connection_url = f"redis://{password_part}{redis_config['name']}:6379"

            return {"id": service_id, "name": redis_config["name"], "type": "redis", "connection_url": connection_url}

        except Exception as e:
            logger.error(f"Failed to create Redis service: {e}")
            raise

    @service_operation("coolify")
    async def delete_application(self, app_id: str) -> bool:
        """
        Delete an application from Coolify

        Args:
            app_id: Application ID

        Returns:
            True if successful
        """

        try:
            logger.info(f"Deleting Coolify application: {app_id}")

            response = await self.client.delete(f"/api/v1/applications/{app_id}")

            if response.status_code not in [200, 204]:
                logger.error(f"Failed to delete application: {response.status_code} - {response.text}")
                return False

            logger.info(f"✅ Coolify application deleted: {app_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete Coolify application: {e}")
            return False

    @service_operation("coolify")
    async def set_domain(self, app_id: str, domain: str) -> bool:
        """
        Set domain for an application

        Args:
            app_id: Application ID
            domain: Domain name

        Returns:
            True if successful
        """

        try:
            payload = {"domain": domain, "https": True, "redirect_to_https": True}

            response = await self.client.post(f"/api/v1/applications/{app_id}/domains", json=payload)

            if response.status_code not in [200, 201]:
                logger.error(f"Failed to set domain: {response.status_code} - {response.text}")
                return False

            logger.info(f"✅ Domain set for application {app_id}: {domain}")
            return True

        except Exception as e:
            logger.error(f"Failed to set domain: {e}")
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
