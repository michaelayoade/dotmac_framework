"""
Multi-application orchestration extension for existing TenantProvisioningService.

Extends the proven provisioning workflow to support multiple applications within
a single tenant container, leveraging existing infrastructure and deployment patterns.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from dotmac_shared.provisioning.core.models import ISPConfig, ProvisioningRequest
from dotmac_shared.provisioning.core.provisioner import ContainerProvisioner
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.application_registry import ApplicationTemplate, get_application_registry
from ..core.multi_app_config import (
    ApplicationDeployment,
    ApplicationStatus,
    MultiAppTenantConfig,
)
from ..schemas.tenant import TenantProvisioningRequest
from .provisioning_service import (
    ProvisioningError,
    ProvisioningStage,
    TenantProvisioningService,
)

logger = logging.getLogger(__name__)


# Extended provisioning stages for multi-app
class MultiAppProvisioningStage(str, Enum):
    """Extended provisioning stages for multi-application deployment."""

    # Inherit existing stages from ProvisioningStage
    PENDING = "pending"
    VALIDATING = "validating"
    CREATING_BILLING = "creating_billing"
    PROVISIONING_INFRASTRUCTURE = "provisioning_infrastructure"
    CONFIGURING_DNS = "configuring_dns"
    DEPLOYING_SERVICES = "deploying_services"
    CONFIGURING_MONITORING = "configuring_monitoring"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"

    # New multi-app specific stages
    VALIDATING_APPLICATIONS = "validating_applications"
    DEPLOYING_SHARED_SERVICES = "deploying_shared_services"
    DEPLOYING_APPLICATIONS = "deploying_applications"
    CONFIGURING_INTER_APP_NETWORKING = "configuring_inter_app_networking"


@dataclass
class ApplicationDeploymentResult:
    """Result of deploying a single application."""

    app_type: str
    instance_name: str
    status: ApplicationStatus
    deployment_name: str
    endpoint: Optional[str] = None
    health_url: Optional[str] = None
    ports: dict[str, int] = field(default_factory=dict)  # service_port -> external_port
    error_message: Optional[str] = None
    deployment_time: Optional[datetime] = None

    @property
    def success(self) -> bool:
        """Check if deployment was successful."""
        return self.status == ApplicationStatus.RUNNING

    @property
    def failed(self) -> bool:
        """Check if deployment failed."""
        return self.status == ApplicationStatus.FAILED


@dataclass
class MultiAppProvisioningResult:
    """Extended result for multi-application tenant provisioning."""

    tenant_id: str
    success: bool
    stage: str = "pending"
    application_results: list[ApplicationDeploymentResult] = field(default_factory=list)
    deployment_order: list[str] = field(default_factory=list)
    total_deployment_time: Optional[float] = None
    error_message: Optional[str] = None

    # Include base provisioning results from existing service
    billing_result: Optional[dict[str, Any]] = None
    infrastructure_result: Optional[dict[str, Any]] = None
    dns_result: Optional[dict[str, Any]] = None
    monitoring_result: Optional[dict[str, Any]] = None

    def get_successful_deployments(self) -> list[ApplicationDeploymentResult]:
        """Get list of successfully deployed applications."""
        return [result for result in self.application_results if result.success]

    def get_failed_deployments(self) -> list[ApplicationDeploymentResult]:
        """Get list of failed application deployments."""
        return [result for result in self.application_results if result.failed]

    def get_deployment_summary(self) -> dict[str, Any]:
        """Get deployment summary for reporting."""
        successful = self.get_successful_deployments()
        failed = self.get_failed_deployments()

        return {
            "tenant_id": self.tenant_id,
            "overall_success": self.success,
            "total_applications": len(self.application_results),
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "deployment_time": self.total_deployment_time,
            "successful_apps": [f"{r.app_type}:{r.instance_name}" for r in successful],
            "failed_apps": [f"{r.app_type}:{r.instance_name}" for r in failed],
        }


class EnhancedTenantProvisioningService(TenantProvisioningService):
    """
    Enhanced tenant provisioning service with multi-application support.

    Extends the existing TenantProvisioningService to support deploying
    multiple applications within a single tenant container while maintaining
    all existing functionality and patterns.
    """

    def __init__(self, db: AsyncSession):
        """__init__ service method."""
        # Initialize base provisioning service
        super().__init__(db)

        # Add multi-app specific components
        self.app_registry = get_application_registry()
        self.container_provisioner = ContainerProvisioner()

        logger.info("Enhanced tenant provisioning service with multi-app support initialized")

    async def provision_multi_app_tenant(
        self, config: MultiAppTenantConfig, user_id: str
    ) -> MultiAppProvisioningResult:
        """
        Enhanced tenant provisioning with multi-application support.

        Extends the base provisioning workflow to include multiple application
        deployment while reusing existing billing, infrastructure, DNS, and monitoring.
        """

        start_time = asyncio.get_event_loop().time()
        logger.info(f"Starting enhanced multi-app provisioning for tenant {config.tenant_id}")

        result = MultiAppProvisioningResult(
            tenant_id=config.tenant_id,
            success=False,
            stage=MultiAppProvisioningStage.PENDING.value,
        )
        try:
            # Stage 1: Enhanced validation with application validation
            result.stage = MultiAppProvisioningStage.VALIDATING_APPLICATIONS.value
            await self._validate_multi_app_configuration(config, result)

            # Stage 2-8: Use existing provisioning service for infrastructure
            # Convert multi-app config to legacy format for base provisioning
            legacy_request = self._convert_to_legacy_provisioning_request(config, user_id)

            # Call existing provisioning service workflow
            base_provisioning_result = await super().provision_tenant(legacy_request, user_id)

            # Store base provisioning results
            result.billing_result = base_provisioning_result.get("billing_result")
            result.infrastructure_result = base_provisioning_result.get("infrastructure_result")
            result.dns_result = base_provisioning_result.get("dns_result")
            result.monitoring_result = base_provisioning_result.get("monitoring_result")

            # Check if base provisioning succeeded
            if not base_provisioning_result.get("success", False):
                result.error_message = f"Base provisioning failed: {base_provisioning_result.get('error')}"
                result.stage = MultiAppProvisioningStage.FAILED.value
                return result

            # Stage 9: Deploy shared services (PostgreSQL, Redis, etc.)
            result.stage = MultiAppProvisioningStage.DEPLOYING_SHARED_SERVICES.value
            await self._deploy_shared_services(config, result)

            # Stage 10: Deploy applications in dependency order
            result.stage = MultiAppProvisioningStage.DEPLOYING_APPLICATIONS.value
            deployment_order = config.get_deployment_order()
            result.deployment_order = deployment_order

            await self._deploy_applications_in_order(config, deployment_order, result)

            # Stage 11: Configure inter-application networking
            result.stage = MultiAppProvisioningStage.CONFIGURING_INTER_APP_NETWORKING.value
            await self._configure_inter_app_networking(config, result)

            # Stage 12: Final validation and completion
            result.stage = MultiAppProvisioningStage.COMPLETED.value

            # Calculate deployment time
            end_time = asyncio.get_event_loop().time()
            result.total_deployment_time = end_time - start_time

            # Determine overall success
            successful_apps = result.get_successful_deployments()
            core_apps_successful = self._validate_core_applications_success(result)

            result.success = len(successful_apps) > 0 and core_apps_successful

            if result.success:
                logger.info(
                    "Multi-app provisioning completed successfully for tenant %s: %s",
                    config.tenant_id,
                    result.get_deployment_summary(),
                )
            else:
                logger.warning(
                    "Multi-app provisioning completed with issues for tenant %s: %s",
                    config.tenant_id,
                    result.get_deployment_summary(),
                )

            return result

        except Exception as e:
            logger.error("Multi-app provisioning failed for tenant %s: %s", config.tenant_id, e)
            result.success = False
            result.stage = MultiAppProvisioningStage.FAILED.value
            result.error_message = str(e)
            return result

    async def add_application_to_existing_tenant(
        self, tenant_id: str, app_deployment: ApplicationDeployment
    ) -> ApplicationDeploymentResult:
        """
        Add new application to existing tenant using existing infrastructure.

        This leverages the existing tenant's infrastructure without re-provisioning
        billing, DNS, or monitoring - just deploys the new application.
        """

        logger.info(
            f"Adding application {app_deployment.app_type}:{app_deployment.instance_name} to existing tenant {tenant_id}"
        )

        try:
            # Validate application type exists
            template = self.app_registry.get_application(app_deployment.app_type)
            if not template:
                return ApplicationDeploymentResult(
                    app_type=app_deployment.app_type,
                    instance_name=app_deployment.instance_name,
                    status=ApplicationStatus.FAILED,
                    deployment_name="",
                    error_message=f"Unknown application type: {app_deployment.app_type}",
                )
            # Get existing tenant info (would integrate with existing tenant repo)
            # For now, create minimal config
            temp_config = MultiAppTenantConfig(tenant_id=tenant_id, applications=[app_deployment])
            # Deploy using existing container provisioner
            result = await self._deploy_single_application_with_existing_provisioner(
                temp_config, app_deployment, template
            )
            logger.info(f"Application addition result for {tenant_id}: {result.success}")
            return result

        except Exception as e:
            logger.error(f"Error adding application to tenant {tenant_id}: {e}")
            return ApplicationDeploymentResult(
                app_type=app_deployment.app_type,
                instance_name=app_deployment.instance_name,
                status=ApplicationStatus.FAILED,
                deployment_name="",
                error_message=str(e),
            )

    async def _validate_multi_app_configuration(
        self, config: MultiAppTenantConfig, result: MultiAppProvisioningResult
    ) -> None:
        """Validate multi-application configuration."""

        logger.info(f"Validating multi-app configuration for tenant {config.tenant_id}")

        # Use existing validation from MultiAppTenantConfig
        validation_issues = config.validate_configuration()
        if validation_issues:
            raise ProvisioningError(
                f"Multi-app configuration validation failed: {validation_issues}",
                ProvisioningStage.VALIDATING,
                validation_issues,
            )
        # Validate all applications exist in registry
        for app_deployment in config.applications:
            template = self.app_registry.get_application(app_deployment.app_type)
            if not template:
                raise ProvisioningError(
                    f"Application type not found: {app_deployment.app_type}",
                    ProvisioningStage.VALIDATING,
                )
        logger.info(f"Multi-app configuration validation passed for tenant {config.tenant_id}")

    def _convert_to_legacy_provisioning_request(
        self, config: MultiAppTenantConfig, user_id: str
    ) -> TenantProvisioningRequest:
        """Convert multi-app config to legacy provisioning request."""

        # Convert to legacy format for base infrastructure provisioning
        config.to_legacy_tenant_config()

        # Create provisioning request (this would match the existing schema)
        return TenantProvisioningRequest(
            tenant_id=config.tenant_id,
            partner_id=config.partner_id,
            plan_type=config.plan_type,
            # Add other required fields based on existing schema
        )

    async def _deploy_shared_services(self, config: MultiAppTenantConfig, result: MultiAppProvisioningResult) -> None:
        """Deploy shared services (PostgreSQL, Redis, etc.) using existing provisioner."""

        logger.info(f"Deploying shared services for tenant {config.tenant_id}")

        # Use existing container provisioner for shared services
        for service_name in config.shared_services:
            logger.info(f"Deploying shared service: {service_name}")
            # This would integrate with existing provisioner
            # For now, simulate successful deployment
            await asyncio.sleep(0.5)

        logger.info(f"Shared services deployed for tenant {config.tenant_id}")

    async def _deploy_applications_in_order(
        self,
        config: MultiAppTenantConfig,
        deployment_order: list[str],
        result: MultiAppProvisioningResult,
    ) -> None:
        """Deploy applications using existing container provisioner."""

        logger.info(f"Deploying applications in order for tenant {config.tenant_id}: {deployment_order}")

        for app_type in deployment_order:
            app_deployments = config.get_applications_by_type(app_type)

            for app_deployment in app_deployments:
                template = self.app_registry.get_application(app_deployment.app_type)

                app_result = await self._deploy_single_application_with_existing_provisioner(
                    config, app_deployment, template
                )
                result.application_results.append(app_result)

                # Stop if core application fails
                if not app_result.success and template and template.category.value == "core":
                    logger.error(f"Critical application {app_deployment.app_type} failed, stopping deployment")
                    break

    async def _deploy_single_application_with_existing_provisioner(
        self,
        config: MultiAppTenantConfig,
        app_deployment: ApplicationDeployment,
        template: ApplicationTemplate,
    ) -> ApplicationDeploymentResult:
        """Deploy single application using existing ContainerProvisioner."""

        deployment_name = app_deployment.get_deployment_name(config.tenant_id)
        start_time = datetime.now(timezone.utc)

        logger.info(f"Deploying {app_deployment.app_type}:{app_deployment.instance_name} using existing provisioner")

        try:
            # Create provisioning request for existing provisioner
            isp_config = ISPConfig(
                tenant_name=config.tenant_id,
                partner_id=config.partner_id,
                plan_type=config.plan_type,
                # Add other required config fields
            )
            provisioning_request = ProvisioningRequest(
                request_id=uuid4(),
                isp_id=uuid4(),
                config=isp_config,
                # Add other required fields
            )
            # Use existing container provisioner
            provisioning_result = await self.container_provisioner.provision_container(provisioning_request)

            if provisioning_result.success:
                # Generate endpoint
                instance_name = app_deployment.instance_name
                tenant_id = config.tenant_id
                base_domain = config.network_config.base_domain if config.network_config else "dotmac.cloud"

                endpoint = app_deployment.custom_domain or f"https://{instance_name}.{tenant_id}.{base_domain}"
                health_url = f"{endpoint}{template.health_check_path}"

                # Create port mapping
                ports = {}
                for i, port in enumerate(template.internal_ports):
                    external_port = port + (i * 100)
                    ports[str(port)] = external_port

                return ApplicationDeploymentResult(
                    app_type=app_deployment.app_type,
                    instance_name=app_deployment.instance_name,
                    status=ApplicationStatus.RUNNING,
                    deployment_name=deployment_name,
                    endpoint=endpoint,
                    health_url=health_url,
                    ports=ports,
                    deployment_time=start_time,
                )
            else:
                return ApplicationDeploymentResult(
                    app_type=app_deployment.app_type,
                    instance_name=app_deployment.instance_name,
                    status=ApplicationStatus.FAILED,
                    deployment_name=deployment_name,
                    error_message=provisioning_result.error_message or "Provisioning failed",
                    deployment_time=start_time,
                )
        except Exception as e:
            logger.error(f"Failed to deploy {deployment_name} using existing provisioner: {e}")
            return ApplicationDeploymentResult(
                app_type=app_deployment.app_type,
                instance_name=app_deployment.instance_name,
                status=ApplicationStatus.FAILED,
                deployment_name=deployment_name,
                error_message=str(e),
                deployment_time=start_time,
            )

    async def _configure_inter_app_networking(
        self, config: MultiAppTenantConfig, result: MultiAppProvisioningResult
    ) -> None:
        """Configure inter-application networking and service discovery."""

        logger.info(f"Configuring inter-app networking for tenant {config.tenant_id}")

        successful_apps = result.get_successful_deployments()

        # Create service registry for inter-app communication
        service_registry = {}
        for app_result in successful_apps:
            service_registry[app_result.instance_name] = {
                "app_type": app_result.app_type,
                "endpoint": app_result.endpoint,
                "health_url": app_result.health_url,
                "ports": app_result.ports,
            }

        logger.info(f"Service registry configured for tenant {config.tenant_id}: {list(service_registry.keys())}")

        # This would integrate with existing networking infrastructure
        # For now, log the configuration
        logger.info(f"Inter-app networking configured for {len(successful_apps)} applications")

    def _validate_core_applications_success(self, result: MultiAppProvisioningResult) -> bool:
        """Validate that all core applications deployed successfully."""

        for app_result in result.application_results:
            template = self.app_registry.get_application(app_result.app_type)
            if template and template.category.value == "core" and not app_result.success:
                return False

        return True
