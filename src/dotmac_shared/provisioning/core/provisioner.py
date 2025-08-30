"""
Main provisioning orchestrator for the DotMac Container Provisioning Service.

Implements the core provision_isp_container function supporting the 4-minute deployment
business requirement with comprehensive health validation and rollback capability.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..adapters.docker_adapter import DockerAdapter
from ..adapters.kubernetes_adapter import KubernetesAdapter
from ..adapters.resource_calculator import ResourceCalculator
from .exceptions import (
    DeploymentError,
    InfrastructureError,
    ProvisioningError,
    RollbackError,
    TimeoutError,
)
from .models import (
    ContainerHealth,
    DeploymentArtifacts,
    DeploymentStatus,
    InfrastructureType,
    ISPConfig,
    ProvisioningRequest,
    ProvisioningResult,
    ResourceRequirements,
)
from .templates import template_manager
from .validators import HealthValidator, ProvisioningValidator

logger = structlog.get_logger(__name__)


class ContainerProvisioner:
    """Main orchestrator for container provisioning operations."""

    def __init__(self):
        self.resource_calculator = ResourceCalculator()
        self.kubernetes_adapter = KubernetesAdapter()
        self.docker_adapter = DockerAdapter()
        self.health_validator = HealthValidator()
        self.provisioning_validator = ProvisioningValidator()

        # Track active provisioning operations
        self.active_operations: Dict[UUID, ProvisioningResult] = {}

    async def provision_container(
        self, request: ProvisioningRequest
    ) -> ProvisioningResult:
        """
        Provision a new ISP Framework container.

        This is the main provisioning method that orchestrates the entire
        deployment process according to the 4-minute deployment requirement.
        """

        # Initialize result tracking
        result = ProvisioningResult(
            request_id=request.request_id,
            isp_id=request.isp_id,
            success=False,
            status=DeploymentStatus.PENDING,
            start_time=datetime.utcnow(),
        )

        # Track this operation
        self.active_operations[request.isp_id] = result

        try:
            logger.info(
                "Starting container provisioning",
                isp_id=str(request.isp_id),
                tenant_name=request.config.tenant_name,
                customer_count=request.customer_count,
                infrastructure=request.infrastructure_type.value,
            )

            result.add_log("Provisioning started", "INFO")

            # Phase 1: Pre-provisioning validation (Target: 15s)
            result.status = DeploymentStatus.PROVISIONING
            await self._validate_provisioning_request(request, result)

            # Phase 2: Resource calculation (Target: 15s)
            resources = await self._calculate_resources(request, result)
            result.allocated_resources = resources

            # Phase 3: Infrastructure provisioning (Target: 60s)
            artifacts = await self._provision_infrastructure(request, resources, result)
            result.artifacts = artifacts

            # Phase 4: Container deployment (Target: 90s)
            result.status = DeploymentStatus.DEPLOYING
            await self._deploy_container(request, resources, artifacts, result)

            # Phase 5: Service configuration (Target: 45s)
            result.status = DeploymentStatus.CONFIGURING
            await self._configure_services(request, resources, artifacts, result)

            # Phase 6: Health validation (Target: 45s)
            result.status = DeploymentStatus.VALIDATING
            await self._validate_deployment_health(request, artifacts, result)

            # Success!
            result.status = DeploymentStatus.READY
            result.success = True
            result.mark_completed(success=True)

            logger.info(
                "Container provisioning completed successfully",
                isp_id=str(request.isp_id),
                duration=result.deployment_duration,
                endpoint_url=result.endpoint_url,
            )

            result.add_log(
                f"Provisioning completed in {result.deployment_duration:.1f}s", "INFO"
            )

        except Exception as e:
            logger.error(
                "Container provisioning failed",
                isp_id=str(request.isp_id),
                error=str(e),
                stage=result.status.value,
            )

            result.success = False
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            result.error_stage = result.status.value
            result.add_log(f"Provisioning failed: {e}", "ERROR")

            # Attempt rollback if enabled
            if request.enable_rollback:
                await self._handle_rollback(request, result)

            result.mark_completed(success=False)

        finally:
            # Remove from active operations
            self.active_operations.pop(request.isp_id, None)

        return result

    async def _validate_provisioning_request(
        self, request: ProvisioningRequest, result: ProvisioningResult
    ) -> None:
        """Validate provisioning request and prerequisites."""

        result.add_log("Validating provisioning request", "INFO")

        try:
            # Validate request parameters
            await self.provisioning_validator.validate_provisioning_request(
                isp_id=request.isp_id,
                customer_count=request.customer_count,
                config=request.config,
                custom_resources=request.custom_resources,
            )

            # Validate infrastructure readiness
            await self.provisioning_validator.validate_infrastructure_readiness(
                infrastructure_type=request.infrastructure_type.value,
                region=request.region,
            )

            result.add_log("Request validation passed", "INFO")

        except Exception as e:
            raise ProvisioningError(
                f"Request validation failed: {e}",
                isp_id=request.isp_id,
                stage="validation",
            ) from e

    async def _calculate_resources(
        self, request: ProvisioningRequest, result: ProvisioningResult
    ) -> ResourceRequirements:
        """Calculate optimal resource allocation."""

        result.add_log("Calculating resource requirements", "INFO")

        try:
            if request.custom_resources:
                resources = request.custom_resources
                result.add_log("Using custom resource requirements", "INFO")
            else:
                resources = await self.resource_calculator.calculate_optimal_resources(
                    customer_count=request.customer_count,
                    plan_type=request.config.plan_type,
                    feature_flags=request.config.feature_flags,
                )
                result.add_log(
                    f"Calculated resources: {resources.cpu_cores} CPU, {resources.memory_gb}GB RAM",
                    "INFO",
                )

            return resources

        except Exception as e:
            raise ProvisioningError(
                f"Resource calculation failed: {e}",
                isp_id=request.isp_id,
                stage="resource_calculation",
            ) from e

    async def _provision_infrastructure(
        self,
        request: ProvisioningRequest,
        resources: ResourceRequirements,
        result: ProvisioningResult,
    ) -> DeploymentArtifacts:
        """Provision underlying infrastructure (namespace, storage, networking)."""

        result.add_log("Provisioning infrastructure", "INFO")

        try:
            if request.infrastructure_type == InfrastructureType.KUBERNETES:
                adapter = self.kubernetes_adapter
            else:
                adapter = self.docker_adapter

            artifacts = await adapter.provision_infrastructure(
                isp_id=request.isp_id,
                config=request.config,
                resources=resources,
                region=request.region,
            )

            result.add_log(
                f"Infrastructure provisioned: {artifacts.namespace or artifacts.container_id}",
                "INFO",
            )
            return artifacts

        except Exception as e:
            raise InfrastructureError(
                f"Infrastructure provisioning failed: {e}",
                infrastructure_type=request.infrastructure_type.value,
                isp_id=request.isp_id,
                stage="infrastructure_provisioning",
            ) from e

    async def _deploy_container(
        self,
        request: ProvisioningRequest,
        resources: ResourceRequirements,
        artifacts: DeploymentArtifacts,
        result: ProvisioningResult,
    ) -> None:
        """Deploy the ISP Framework container."""

        result.add_log("Deploying container", "INFO")

        try:
            # Get deployment adapter
            if request.infrastructure_type == InfrastructureType.KUBERNETES:
                adapter = self.kubernetes_adapter
            else:
                adapter = self.docker_adapter

            # Render deployment template
            rendered_template = await template_manager.render_template(
                template_name="isp-framework",
                infrastructure_type=request.infrastructure_type,
                isp_id=request.isp_id,
                config=request.config,
                resources=resources,
            )

            # Deploy container
            deployment_info = await adapter.deploy_container(
                template=rendered_template,
                artifacts=artifacts,
                timeout=request.provisioning_timeout,
            )

            # Update artifacts with deployment info
            artifacts.container_id = deployment_info.get("container_id")
            artifacts.internal_url = deployment_info.get("internal_url")
            artifacts.external_url = deployment_info.get("external_url")

            result.endpoint_url = artifacts.external_url
            result.add_log(f"Container deployed: {artifacts.container_id}", "INFO")

        except Exception as e:
            raise DeploymentError(
                f"Container deployment failed: {e}",
                deployment_phase="container_deployment",
                container_id=artifacts.container_id,
                isp_id=request.isp_id,
                stage="container_deployment",
            ) from e

    async def _configure_services(
        self,
        request: ProvisioningRequest,
        resources: ResourceRequirements,
        artifacts: DeploymentArtifacts,
        result: ProvisioningResult,
    ) -> None:
        """Configure additional services (ingress, SSL, monitoring)."""

        result.add_log("Configuring services", "INFO")

        try:
            # Get deployment adapter
            if request.infrastructure_type == InfrastructureType.KUBERNETES:
                adapter = self.kubernetes_adapter
            else:
                adapter = self.docker_adapter

            # Configure networking and ingress
            networking_info = await adapter.configure_networking(
                isp_id=request.isp_id, config=request.config, artifacts=artifacts
            )

            # Update URLs with networking configuration
            if networking_info.get("external_url"):
                artifacts.external_url = networking_info["external_url"]
                result.endpoint_url = artifacts.external_url

            # Configure SSL if enabled
            if request.config.network_config.ssl_enabled:
                ssl_info = await adapter.configure_ssl(
                    isp_id=request.isp_id, config=request.config, artifacts=artifacts
                )
                artifacts.ssl_certificate_name = ssl_info.get("certificate_name")

            # Set up monitoring and logging
            await adapter.configure_monitoring(
                isp_id=request.isp_id, config=request.config, artifacts=artifacts
            )

            result.add_log("Service configuration completed", "INFO")

        except Exception as e:
            raise DeploymentError(
                f"Service configuration failed: {e}",
                deployment_phase="service_configuration",
                container_id=artifacts.container_id,
                isp_id=request.isp_id,
                stage="service_configuration",
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def _validate_deployment_health(
        self,
        request: ProvisioningRequest,
        artifacts: DeploymentArtifacts,
        result: ProvisioningResult,
    ) -> None:
        """Validate that the deployed container is healthy and ready."""

        result.add_log("Validating deployment health", "INFO")

        try:
            # Wait for container to be ready
            base_url = artifacts.external_url or artifacts.internal_url
            if not base_url:
                raise ProvisioningError(
                    "No URL available for health checks",
                    isp_id=request.isp_id,
                    stage="health_validation",
                )

            # Perform comprehensive health validation
            async with HealthValidator(timeout=60) as validator:
                health_status = await validator.wait_for_healthy(
                    container_id=artifacts.container_id
                    or f"isp-{request.config.tenant_name}",
                    base_url=base_url,
                    max_wait_seconds=120,  # 2 minutes max wait
                    check_interval=5,  # Check every 5 seconds
                )

            result.health_status = health_status
            result.add_log(
                f"Health validation passed: {health_status.overall_status.value}",
                "INFO",
            )

            # Set additional URLs
            result.admin_dashboard_url = f"{base_url}/admin"
            result.api_documentation_url = f"{base_url}/docs"

        except Exception as e:
            raise ProvisioningError(
                f"Health validation failed: {e}",
                isp_id=request.isp_id,
                stage="health_validation",
            ) from e

    async def _handle_rollback(
        self, request: ProvisioningRequest, result: ProvisioningResult
    ) -> None:
        """Handle rollback on provisioning failure."""

        result.add_log("Starting rollback", "WARN")
        result.status = DeploymentStatus.ROLLING_BACK

        try:
            # Get appropriate adapter for rollback
            if request.infrastructure_type == InfrastructureType.KUBERNETES:
                adapter = self.kubernetes_adapter
            else:
                adapter = self.docker_adapter

            # Perform rollback
            rollback_success = await adapter.rollback_deployment(
                isp_id=request.isp_id,
                artifacts=result.artifacts,
                timeout=120,  # 2 minute rollback timeout
            )

            if rollback_success:
                result.rollback_completed = True
                result.status = DeploymentStatus.ROLLED_BACK
                result.add_log("Rollback completed successfully", "INFO")
                logger.info(
                    "Rollback completed successfully", isp_id=str(request.isp_id)
                )
            else:
                result.add_log("Rollback partially completed", "WARN")
                logger.warning(
                    "Rollback partially completed", isp_id=str(request.isp_id)
                )

        except Exception as rollback_error:
            logger.error(
                "Rollback failed", isp_id=str(request.isp_id), error=str(rollback_error)
            )
            result.add_log(f"Rollback failed: {rollback_error}", "ERROR")

            # Don't raise rollback errors - original error is more important

    async def get_provisioning_status(
        self, isp_id: UUID
    ) -> Optional[ProvisioningResult]:
        """Get current status of a provisioning operation."""
        return self.active_operations.get(isp_id)

    async def list_active_operations(self) -> Dict[UUID, ProvisioningResult]:
        """List all active provisioning operations."""
        return self.active_operations.copy()


# Global provisioner instance
_provisioner = ContainerProvisioner()


async def provision_isp_container(
    isp_id: UUID,
    customer_count: int,
    config: ISPConfig,
    custom_resources: Optional[ResourceRequirements] = None,
    infrastructure_type: InfrastructureType = InfrastructureType.KUBERNETES,
    region: str = "us-east-1",
    timeout: int = 300,
    enable_rollback: bool = True,
    **kwargs,
) -> ProvisioningResult:
    """
    Provision a new ISP Framework container.

    This is the main entry point for container provisioning, supporting the
    4-minute deployment business requirement.

    Args:
        isp_id: Unique identifier for the ISP instance
        customer_count: Expected number of customers (1-50,000)
        config: ISP Framework configuration
        custom_resources: Optional custom resource requirements
        infrastructure_type: Target infrastructure (Kubernetes/Docker)
        region: Deployment region
        timeout: Provisioning timeout in seconds (default: 300)
        enable_rollback: Enable automatic rollback on failure
        **kwargs: Additional parameters

    Returns:
        ProvisioningResult with deployment status and details

    Raises:
        ProvisioningError: On provisioning failure
        ValidationError: On validation failure
        TimeoutError: On timeout

    Example:
        ```python
        from uuid import uuid4
        from dotmac_shared.provisioning import provision_isp_container
        from dotmac_shared.provisioning.core.models import ISPConfig, PlanType

        config = ISPConfig(
            tenant_name="acme-isp",
            display_name="ACME Internet Services",
            plan_type=PlanType.PREMIUM
        )

        result = await provision_isp_container(
            isp_id=uuid4(),
            customer_count=1000,
            config=config
        )

        if result.success:
        else:
        ```
    """

    # Create provisioning request
    request = ProvisioningRequest(
        isp_id=isp_id,
        customer_count=customer_count,
        config=config,
        custom_resources=custom_resources,
        infrastructure_type=infrastructure_type,
        region=region,
        provisioning_timeout=timeout,
        enable_rollback=enable_rollback,
        **kwargs,
    )

    # Execute provisioning
    return await _provisioner.provision_container(request)


async def rollback_provisioning(isp_id: UUID) -> bool:
    """
    Rollback a previously provisioned container.

    Args:
        isp_id: ISP instance identifier to rollback

    Returns:
        bool: True if rollback succeeded, False otherwise
    """

    # This would implement manual rollback logic
    # For now, return False to indicate not implemented
    logger.warning("Manual rollback not yet implemented", isp_id=str(isp_id))
    return False
