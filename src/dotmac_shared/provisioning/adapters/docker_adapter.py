"""
Docker deployment adapter for the DotMac Container Provisioning Service.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
import yaml

import docker

from ..core.exceptions import ConfigurationError, DeploymentError, InfrastructureError
from ..core.models import (
    DeploymentArtifacts,
    InfrastructureType,
    ISPConfig,
    ResourceRequirements,
)

logger = structlog.get_logger(__name__)


class DockerAdapter:
    """Handles Docker-specific deployment operations."""

    def __init__(self):
        self.docker_client = None
        self.initialized = False

    async def _initialize_client(self) -> None:
        """Initialize Docker client."""
        if self.initialized:
            return

        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()

            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.docker_client.ping
            )

            self.initialized = True
            logger.info("Docker client initialized successfully")

        except Exception as e:
            raise InfrastructureError(
                f"Failed to initialize Docker client: {e}", infrastructure_type="docker"
            ) from e

    async def provision_infrastructure(
        self,
        isp_id: UUID,
        config: ISPConfig,
        resources: ResourceRequirements,
        region: str = "us-east-1",
    ) -> DeploymentArtifacts:
        """
        Provision Docker infrastructure for ISP deployment.

        Creates:
        - Docker network
        - Volume mounts
        - Environment configuration
        """

        await self._initialize_client()

        logger.info(
            "Provisioning Docker infrastructure",
            isp_id=str(isp_id),
            tenant_name=config.tenant_name,
        )

        artifacts = DeploymentArtifacts()

        try:
            # Generate resource names
            network_name = f"tenant-{config.tenant_name}-network"
            container_name = f"isp-framework-{config.tenant_name}"

            artifacts.container_id = container_name

            # Create Docker network for tenant isolation
            await self._create_docker_network(network_name, config, artifacts)

            # Create data volumes
            await self._create_volumes(config.tenant_name, artifacts)

            # Prepare environment configuration
            await self._prepare_environment_config(isp_id, config, artifacts)

            logger.info(
                "Docker infrastructure provisioning completed",
                container_name=container_name,
                network=network_name,
            )

            return artifacts

        except Exception as e:
            # Clean up any partially created resources
            await self._cleanup_infrastructure(artifacts)
            raise InfrastructureError(
                f"Docker infrastructure provisioning failed: {e}",
                infrastructure_type="docker",
                resource_name=artifacts.container_id,
            ) from e

    async def _create_docker_network(
        self, network_name: str, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> None:
        """Create Docker network for tenant isolation."""

        try:
            # Check if network already exists
            try:
                existing_network = await asyncio.get_event_loop().run_in_executor(
                    None, self.docker_client.networks.get, network_name
                )
                logger.warning("Network already exists", network=network_name)
                return
            except docker.errors.NotFound:
                pass  # Network doesn't exist, create it

            # Create network
            network = await asyncio.get_event_loop().run_in_executor(
                None,
                self.docker_client.networks.create,
                network_name,
                driver="bridge",
                labels={
                    "tenant": config.tenant_name,
                    "managed-by": "dotmac-provisioning",
                    "created-at": datetime.now(timezone.utc).isoformat(),
                },
            )

            artifacts.created_resources.append(
                {"kind": "Network", "name": network_name, "id": network.id}
            )

            logger.debug("Docker network created", network=network_name, id=network.id)

        except Exception as e:
            raise InfrastructureError(
                f"Failed to create Docker network: {e}",
                infrastructure_type="docker",
                resource_name=network_name,
            ) from e

    async def _create_volumes(
        self, tenant_name: str, artifacts: DeploymentArtifacts
    ) -> None:
        """Create Docker volumes for persistent storage."""

        volume_names = [
            f"tenant-{tenant_name}-postgres-data",
            f"tenant-{tenant_name}-redis-data",
            f"tenant-{tenant_name}-uploads",
        ]

        for volume_name in volume_names:
            try:
                # Check if volume already exists
                try:
                    existing_volume = await asyncio.get_event_loop().run_in_executor(
                        None, self.docker_client.volumes.get, volume_name
                    )
                    continue  # Volume exists, skip
                except docker.errors.NotFound:
                    pass  # Volume doesn't exist, create it

                volume = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.docker_client.volumes.create,
                    name=volume_name,
                    labels={"tenant": tenant_name, "managed-by": "dotmac-provisioning"},
                )

                artifacts.created_resources.append(
                    {"kind": "Volume", "name": volume_name, "id": volume.id}
                )

                logger.debug("Docker volume created", volume=volume_name, id=volume.id)

            except Exception as e:
                logger.warning(
                    "Failed to create volume", volume=volume_name, error=str(e)
                )

    async def _prepare_environment_config(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> None:
        """Prepare environment configuration for containers."""

        # Base environment variables
        env_config = {
            "TENANT_ID": config.tenant_name,
            "ISP_ID": str(isp_id),
            "PLAN_TYPE": config.plan_type.value,
            "DISPLAY_NAME": config.display_name,
            "ENVIRONMENT": "production",
            "DATABASE_URL": f"postgresql://tenant_{config.tenant_name}:password@postgres:5432/tenant_{config.tenant_name}",
            "REDIS_URL": "redis://redis:6379/0",
            "JWT_SECRET_KEY": "generated-jwt-secret-key-32-chars-minimum",
            "ENCRYPTION_KEY": "generated-encryption-key-32-chars",
        }

        # Add feature flags
        if config.feature_flags:
            feature_config = {
                f"FEATURE_{feature.upper()}": (
                    "true" if getattr(config.feature_flags, feature) else "false"
                )
                for feature in [
                    "customer_portal",
                    "technician_portal",
                    "admin_portal",
                    "billing_system",
                    "notification_system",
                    "analytics_dashboard",
                    "api_webhooks",
                    "bulk_operations",
                    "advanced_reporting",
                    "multi_language",
                ]
            }
            env_config.update(feature_config)

        # Add custom environment variables
        env_config.update(config.environment_variables)

        # Add secrets (in production, these would be handled more securely)
        env_config.update(config.secrets)

        # Store environment config in artifacts for later use
        artifacts.created_resources.append(
            {
                "kind": "EnvironmentConfig",
                "name": f"{config.tenant_name}-env",
                "config": env_config,
            }
        )

        logger.debug(
            "Environment configuration prepared",
            tenant=config.tenant_name,
            env_vars=len(env_config),
        )

    async def deploy_container(
        self,
        template: Dict[str, Any],
        artifacts: DeploymentArtifacts,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Deploy ISP Framework container using Docker Compose template."""

        logger.info(
            "Deploying container using Docker", container=artifacts.container_id
        )

        try:
            # Parse Docker Compose template
            compose_spec = self._parse_docker_compose_template(template)

            # Create temporary compose file
            compose_file_path = await self._create_compose_file(compose_spec, artifacts)

            # Deploy using docker-compose
            deployment_result = await self._deploy_with_compose(
                compose_file_path, artifacts, timeout
            )

            # Generate URLs
            internal_url = f"http://localhost:8000"
            external_url = f"http://localhost:{template.get('external_port', 8000)}"

            return {
                "container_id": artifacts.container_id,
                "internal_url": internal_url,
                "external_url": external_url,
                "compose_file": str(compose_file_path),
            }

        except Exception as e:
            raise DeploymentError(
                f"Docker container deployment failed: {e}",
                deployment_phase="container_deployment",
                container_id=artifacts.container_id,
            ) from e

    def _parse_docker_compose_template(
        self, template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and enhance Docker Compose template."""

        # If template is already a compose spec, use it directly
        if "services" in template:
            return template

        # Otherwise, create a basic compose spec
        tenant_name = template.get("tenant_name", "default")
        container_name = template.get("container_name", f"isp-framework-{tenant_name}")
        network_name = template.get("network_name", f"tenant-{tenant_name}-network")

        return {
            "version": "3.8",
            "services": {
                "isp-framework": {
                    "image": "registry.dotmac.app/isp-framework:latest",
                    "container_name": container_name,
                    "restart": "unless-stopped",
                    "ports": [f"{template.get('external_port', 8000)}:8000"],
                    "environment": template.get("environment_vars", {}),
                    "depends_on": ["postgres", "redis"],
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "60s",
                    },
                    "deploy": {
                        "resources": {
                            "limits": {
                                "cpus": str(template.get("cpu_limit", 1.0)),
                                "memory": template.get("memory_limit", "2g"),
                            }
                        }
                    },
                    "networks": [network_name],
                },
                "postgres": {
                    "image": "postgres:15-alpine",
                    "container_name": f"{container_name}-postgres",
                    "restart": "unless-stopped",
                    "environment": {
                        "POSTGRES_DB": template.get(
                            "database_name", f"tenant_{tenant_name}_db"
                        ),
                        "POSTGRES_USER": template.get(
                            "database_user", f"tenant_{tenant_name}_user"
                        ),
                        "POSTGRES_PASSWORD": "password",  # In production, use secrets
                    },
                    "volumes": [
                        f"tenant-{tenant_name}-postgres-data:/var/lib/postgresql/data"
                    ],
                    "networks": [network_name],
                    "healthcheck": {
                        "test": [
                            "CMD-SHELL",
                            "pg_isready -U $POSTGRES_USER -d $POSTGRES_DB",
                        ],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                    },
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "container_name": f"{container_name}-redis",
                    "restart": "unless-stopped",
                    "volumes": [f"tenant-{tenant_name}-redis-data:/data"],
                    "networks": [network_name],
                    "healthcheck": {
                        "test": ["CMD", "redis-cli", "ping"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                    },
                },
            },
            "volumes": {
                f"tenant-{tenant_name}-postgres-data": {"external": True},
                f"tenant-{tenant_name}-redis-data": {"external": True},
            },
            "networks": {network_name: {"external": True}},
        }

    async def _create_compose_file(
        self, compose_spec: Dict[str, Any], artifacts: DeploymentArtifacts
    ) -> Path:
        """Create temporary Docker Compose file."""

        # Get environment config from artifacts
        env_config = {}
        for resource in artifacts.created_resources:
            if resource.get("kind") == "EnvironmentConfig":
                env_config = resource["config"]
                break

        # Update environment variables in compose spec
        if "isp-framework" in compose_spec.get("services", {}):
            compose_spec["services"]["isp-framework"]["environment"] = env_config

        # Create temporary file
        temp_dir = Path(tempfile.gettempdir()) / "dotmac-provisioning"
        temp_dir.mkdir(exist_ok=True)

        compose_file_path = temp_dir / f"docker-compose-{artifacts.container_id}.yml"

        with open(compose_file_path, "w") as f:
            yaml.dump(compose_spec, f, default_flow_style=False)

        artifacts.created_resources.append(
            {
                "kind": "ComposeFile",
                "name": str(compose_file_path),
                "path": str(compose_file_path),
            }
        )

        logger.debug("Docker Compose file created", path=str(compose_file_path))
        return compose_file_path

    async def _deploy_with_compose(
        self, compose_file_path: Path, artifacts: DeploymentArtifacts, timeout: int
    ) -> Dict[str, Any]:
        """Deploy using docker-compose."""

        try:
            # Run docker-compose up
            process = await asyncio.create_subprocess_exec(
                "docker-compose",
                "-f",
                str(compose_file_path),
                "up",
                "-d",
                "--remove-orphans",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            if process.returncode != 0:
                raise DeploymentError(
                    f"docker-compose up failed: {stderr.decode()}",
                    deployment_phase="compose_up",
                    container_id=artifacts.container_id,
                )

            logger.info(
                "Docker Compose deployment completed", container=artifacts.container_id
            )

            # Wait for containers to be healthy
            await self._wait_for_containers_healthy(compose_file_path, timeout)

            return {"status": "deployed", "compose_output": stdout.decode()}

        except asyncio.TimeoutError:
            raise DeploymentError(
                f"Docker deployment timed out after {timeout} seconds",
                deployment_phase="compose_up",
                container_id=artifacts.container_id,
            )
        except Exception as e:
            raise DeploymentError(
                f"Docker deployment failed: {e}",
                deployment_phase="compose_up",
                container_id=artifacts.container_id,
            ) from e

    async def _wait_for_containers_healthy(
        self, compose_file_path: Path, timeout: int
    ) -> None:
        """Wait for all containers to be healthy."""

        logger.info("Waiting for containers to be healthy")

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Check container health using docker-compose ps
                process = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-f",
                    str(compose_file_path),
                    "ps",
                    "--format",
                    "json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    # Parse container status
                    containers_status = []
                    for line in stdout.decode().strip().split("\n"):
                        if line:
                            try:
                                container_info = json.loads(line)
                                containers_status.append(container_info)
                            except json.JSONDecodeError:
                                continue

                    # Check if all containers are healthy
                    all_healthy = True
                    for container in containers_status:
                        status = container.get("State", "unknown")
                        health = container.get("Health", "unknown")

                        if status != "running" or (
                            health not in ["unknown", "healthy"]
                        ):
                            all_healthy = False
                            break

                    if all_healthy and containers_status:
                        logger.info("All containers are healthy")
                        return

                await asyncio.sleep(10)

            except Exception as e:
                logger.warning("Error checking container health", error=str(e))
                await asyncio.sleep(10)

        raise DeploymentError(
            f"Containers did not become healthy within {timeout} seconds",
            deployment_phase="waiting_for_healthy",
        )

    async def configure_networking(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> Dict[str, Any]:
        """Configure networking for Docker deployment."""

        logger.info("Configuring networking", container=artifacts.container_id)

        # For Docker, networking is handled by the compose file
        # Just return the configured URLs
        port = config.network_config.port_mapping.get(8000, 8000)
        protocol = "https" if config.network_config.ssl_enabled else "http"

        if config.network_config.domain:
            external_url = f"{protocol}://{config.network_config.domain}"
        else:
            external_url = f"{protocol}://localhost:{port}"

        artifacts.external_url = external_url

        return {"external_url": external_url}

    async def configure_ssl(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> Dict[str, Any]:
        """Configure SSL for Docker deployment."""

        logger.info("Configuring SSL", container=artifacts.container_id)

        # For Docker development, SSL is typically handled by reverse proxy
        # Return basic SSL configuration
        return {
            "certificate_name": f"{config.tenant_name}-ssl",
            "status": "development_mode",
            "note": "SSL handled by reverse proxy in production",
        }

    async def configure_monitoring(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> Dict[str, Any]:
        """Configure monitoring for Docker deployment."""

        logger.info("Configuring monitoring", container=artifacts.container_id)

        # Add monitoring labels to containers if possible
        # For now, just return basic monitoring configuration
        return {
            "monitoring_enabled": True,
            "logging_enabled": True,
            "method": "docker_logs",
        }

    async def rollback_deployment(
        self, isp_id: UUID, artifacts: Optional[DeploymentArtifacts], timeout: int = 120
    ) -> bool:
        """Rollback Docker deployment by stopping and removing containers."""

        if not artifacts or not artifacts.container_id:
            return False

        logger.info("Rolling back Docker deployment", container=artifacts.container_id)

        try:
            # Find compose file
            compose_file_path = None
            for resource in artifacts.created_resources:
                if resource.get("kind") == "ComposeFile":
                    compose_file_path = Path(resource["path"])
                    break

            if compose_file_path and compose_file_path.exists():
                # Stop and remove containers using docker-compose
                process = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-f",
                    str(compose_file_path),
                    "down",
                    "-v",
                    "--remove-orphans",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    logger.info("Docker containers stopped and removed")
                else:
                    logger.warning(
                        "Failed to stop containers with compose", error=stderr.decode()
                    )

            # Clean up additional resources
            await self._cleanup_infrastructure(artifacts)

            logger.info("Rollback completed", container=artifacts.container_id)
            return True

        except Exception as e:
            logger.error(
                "Rollback failed", container=artifacts.container_id, error=str(e)
            )
            return False

    async def _cleanup_infrastructure(self, artifacts: DeploymentArtifacts) -> None:
        """Clean up Docker infrastructure resources."""

        if not artifacts.created_resources:
            return

        logger.info("Cleaning up Docker infrastructure")

        await self._initialize_client()

        for resource in artifacts.created_resources:
            try:
                if resource["kind"] == "Network":
                    network = self.docker_client.networks.get(resource["name"])
                    await asyncio.get_event_loop().run_in_executor(None, network.remove)
                    logger.debug("Network removed", network=resource["name"])

                elif resource["kind"] == "Volume":
                    volume = self.docker_client.volumes.get(resource["name"])
                    await asyncio.get_event_loop().run_in_executor(None, volume.remove)
                    logger.debug("Volume removed", volume=resource["name"])

                elif resource["kind"] == "ComposeFile":
                    compose_path = Path(resource["path"])
                    if compose_path.exists():
                        compose_path.unlink()
                        logger.debug("Compose file removed", path=resource["path"])

            except Exception as e:
                logger.warning(
                    "Failed to cleanup resource",
                    resource=resource["name"],
                    error=str(e),
                )
