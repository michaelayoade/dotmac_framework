"""
Enhanced Tenant Service with multi-application support.

Extends the existing TenantService to support multi-application tenant configurations
while maintaining full backward compatibility with existing functionality.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.exceptions import BusinessLogicError, TenantNotFoundError
from core.logging import get_logger, log_audit_event
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.services_framework.core.registry import (
    ServiceConfig,
    ServiceRegistry,
)

from ..core.application_registry import (
    get_application_registry,
    initialize_application_registry_with_services,
)
from ..core.multi_app_config import (
    ApplicationDeployment,
    ApplicationStatus,
    MultiAppTenantConfig,
)
from ..models.tenant import Tenant, TenantStatus
from ..schemas.tenant import TenantCreate, TenantUpdate
from .application_orchestrator import (
    EnhancedTenantProvisioningService,
    MultiAppProvisioningResult,
)
from .tenant_service import TenantService

logger = get_logger(__name__)


class EnhancedTenantService(TenantService):
    """Service layer - exceptions bubble up to router @standard_exception_handler."""

    """
    Enhanced tenant service with multi-application support.

    Extends existing TenantService functionality to support deploying and managing
    multiple applications within tenant containers while maintaining all
    existing single-app functionality.
    """

    def __init__(self, db: AsyncSession):
        """__init__ service method."""
        # Initialize base tenant service
        super().__init__(db)

        # Initialize service registry for application dependencies
        self.service_registry = ServiceRegistry(ServiceConfig())

        # Initialize application registry with service registry integration
        self.app_registry = initialize_application_registry_with_services(
            self.service_registry
        )

        # Initialize enhanced provisioning service
        self.enhanced_provisioning = EnhancedTenantProvisioningService(db)

        logger.info("Enhanced tenant service with multi-app support initialized")

    async def create_multi_app_tenant(
        self,
        tenant_data: TenantCreate,
        applications: List[ApplicationDeployment],
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Create a new tenant with multiple applications.

        Leverages existing tenant creation workflow and adds multi-application
        deployment on top of the existing infrastructure.
        """

        logger.info(
            f"Creating multi-app tenant: {tenant_data.name} with {len(applications)} applications"
        )

        # Step 1: Create tenant using existing service
        tenant = await super().create_tenant(tenant_data, created_by)

        # Step 2: Create multi-app configuration
        multi_app_config = MultiAppTenantConfig(
            tenant_id=str(tenant.id),
            partner_id=tenant_data.partner_id or "default",
            plan_type=tenant_data.plan_type or "standard",
            applications=applications,
        )
        # Step 3: Provision multi-app tenant using enhanced provisioning
        provisioning_result = (
            await self.enhanced_provisioning.provision_multi_app_tenant(
                multi_app_config, created_by
            )
        )
        # Step 4: Store multi-app configuration in tenant config
        if provisioning_result.success:
            await self._store_multi_app_configuration(
                tenant.id, multi_app_config, created_by
            )

        # Step 5: Log audit event
        await log_audit_event(
            event_type="tenant.multi_app_created",
            entity_type="tenant",
            entity_id=str(tenant.id),
            user_id=created_by,
            details={
                "tenant_name": tenant.name,
                "applications": [
                    f"{app.app_type}:{app.instance_name}" for app in applications
                ],
                "provisioning_success": provisioning_result.success,
                "deployment_time": provisioning_result.total_deployment_time,
            },
        )
        return {
            "tenant": tenant,
            "provisioning_result": provisioning_result,
            "success": provisioning_result.success,
        }

    async def add_application_to_tenant(
        self, tenant_id: UUID, app_deployment: ApplicationDeployment, user_id: str
    ) -> Dict[str, Any]:
        """
        Add a new application to an existing tenant.

        Leverages existing tenant infrastructure to deploy additional applications
        without disrupting existing services.
        """

        logger.info(
            f"Adding application {app_deployment.app_type}:{app_deployment.instance_name} to tenant {tenant_id}"
        )

        # Validate tenant exists and is active
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        if tenant.status != TenantStatus.ACTIVE:
            raise BusinessLogicError(f"Tenant {tenant_id} is not active")

        # Deploy application using enhanced provisioning
        deployment_result = (
            await self.enhanced_provisioning.add_application_to_existing_tenant(
                str(tenant_id), app_deployment
            )
        )
        # Update tenant configuration if successful
        if deployment_result.success:
            await self._add_application_to_tenant_config(
                tenant_id, app_deployment, user_id
            )

        # Log audit event
        await log_audit_event(
            event_type="tenant.application_added",
            entity_type="tenant",
            entity_id=str(tenant_id),
            user_id=user_id,
            details={
                "application": f"{app_deployment.app_type}:{app_deployment.instance_name}",
                "deployment_success": deployment_result.success,
                "endpoint": deployment_result.endpoint,
            },
        )
        return {
            "tenant_id": str(tenant_id),
            "application_deployment": deployment_result,
            "success": deployment_result.success,
        }

    async def get_tenant_applications(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """Get all applications deployed for a tenant."""

        # Get multi-app configuration from tenant config
        config = await self._get_multi_app_configuration(tenant_id)

        if not config:
            # Fallback to default ISP Framework for legacy tenants
            return [
                {
                    "app_type": "isp_framework",
                    "instance_name": "main",
                    "status": "running",
                    "category": "core",
                    "endpoint": f"https://main.{tenant_id}.dotmac.cloud",
                }
            ]

        # Get application details from registry
        applications = []
        for app_deployment in config.applications:
            template = self.app_registry.get_application(app_deployment.app_type)

            app_info = {
                "app_type": app_deployment.app_type,
                "instance_name": app_deployment.instance_name,
                "status": (
                    app_deployment.status.value if app_deployment.status else "unknown"
                ),
                "enabled": app_deployment.enabled,
                "category": template.category.value if template else "unknown",
                "name": template.name if template else app_deployment.app_type,
                "version": app_deployment.version
                or (template.version if template else "unknown"),
                "endpoint": app_deployment.custom_domain,
                "resource_tier": (
                    template.resource_requirements.tier.value if template else "unknown"
                ),
            }

            applications.append(app_info)

        return applications

    async def remove_application_from_tenant(
        self, tenant_id: UUID, instance_name: str, user_id: str
    ) -> Dict[str, Any]:
        """Remove application from tenant."""

        logger.info(f"Removing application {instance_name} from tenant {tenant_id}")

        # Validate tenant exists
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        # Get current configuration
        config = await self._get_multi_app_configuration(tenant_id)
        if not config:
            raise BusinessLogicError("No multi-app configuration found for tenant")

        # Find and validate application
        app_deployment = config.get_application(instance_name)
        if not app_deployment:
            raise BusinessLogicError(f"Application {instance_name} not found in tenant")

        # Prevent removal of core applications if it's the last one
        if app_deployment.app_type == "isp_framework":
            core_apps = config.get_applications_by_type("isp_framework")
            if len(core_apps) <= 1:
                raise BusinessLogicError(
                    "Cannot remove the last ISP Framework instance"
                )

        # Remove application (this would integrate with container orchestration)
        # For now, simulate successful removal
        await asyncio.sleep(0.5)

        # Update configuration
        await self._remove_application_from_tenant_config(
            tenant_id, instance_name, user_id
        )

        # Log audit event
        await log_audit_event(
            event_type="tenant.application_removed",
            entity_type="tenant",
            entity_id=str(tenant_id),
            user_id=user_id,
            details={
                "application": f"{app_deployment.app_type}:{instance_name}",
                "removal_success": True,
            },
        )
        return {
            "tenant_id": str(tenant_id),
            "instance_name": instance_name,
            "success": True,
            "removed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_service_registry_status(self) -> Dict[str, Any]:
        """Get status of service registry integration."""

        return {
            "service_registry": {
                "initialized": self.service_registry is not None,
                "services_count": (
                    len(self.service_registry.services) if self.service_registry else 0
                ),
            },
            "application_registry": self.app_registry.get_service_registry_integration(),
            "enhanced_provisioning": {
                "initialized": self.enhanced_provisioning is not None
            },
        }

    # Private helper methods

    async def _store_multi_app_configuration(
        self, tenant_id: UUID, config: MultiAppTenantConfig, created_by: str
    ) -> None:
        """Store multi-app configuration in tenant configurations."""

        await self.config_repo.create_configuration(
            tenant_id=tenant_id,
            category="applications",
            key="multi_app_config",
            value={
                "tenant_id": config.tenant_id,
                "partner_id": config.partner_id,
                "plan_type": config.plan_type,
                "applications": [
                    {
                        "app_type": app.app_type,
                        "instance_name": app.instance_name,
                        "enabled": app.enabled,
                        "status": app.status.value,
                        "version": app.version,
                        "config_overrides": app.config_overrides,
                        "environment_overrides": app.environment_overrides,
                        "custom_domain": app.custom_domain,
                    }
                    for app in config.applications
                ],
                "shared_services": config.shared_services,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": created_by,
            },
            created_by=created_by,
        )
        logger.info(f"Stored multi-app configuration for tenant {tenant_id}")

    async def _get_multi_app_configuration(
        self, tenant_id: UUID
    ) -> Optional[MultiAppTenantConfig]:
        """Get multi-app configuration from tenant configurations."""

        config_data = await self.config_repo.get_configuration_value(
            tenant_id, "applications", "multi_app_config"
        )
        if not config_data:
            return None

        # Convert stored data back to MultiAppTenantConfig
        applications = []
        for app_data in config_data.get("applications", []):
            app_deployment = ApplicationDeployment(
                app_type=app_data["app_type"],
                instance_name=app_data["instance_name"],
                enabled=app_data.get("enabled", True),
                status=ApplicationStatus(app_data.get("status", "pending")),
                version=app_data.get("version"),
                config_overrides=app_data.get("config_overrides", {}),
                environment_overrides=app_data.get("environment_overrides", {}),
                custom_domain=app_data.get("custom_domain"),
            )
            applications.append(app_deployment)

        return MultiAppTenantConfig(
            tenant_id=config_data["tenant_id"],
            partner_id=config_data.get("partner_id", "default"),
            plan_type=config_data.get("plan_type", "standard"),
            applications=applications,
            shared_services=config_data.get("shared_services", ["postgres", "redis"]),
        )

    async def _add_application_to_tenant_config(
        self, tenant_id: UUID, app_deployment: ApplicationDeployment, user_id: str
    ) -> None:
        """Add application to existing tenant configuration."""

        config = await self._get_multi_app_configuration(tenant_id)
        if config:
            config.add_application(app_deployment)
            await self._store_multi_app_configuration(tenant_id, config, user_id)
        else:
            # Create new multi-app config
            new_config = MultiAppTenantConfig(
                tenant_id=str(tenant_id), applications=[app_deployment]
            )
            await self._store_multi_app_configuration(tenant_id, new_config, user_id)

    async def _remove_application_from_tenant_config(
        self, tenant_id: UUID, instance_name: str, user_id: str
    ) -> None:
        """Remove application from tenant configuration."""

        config = await self._get_multi_app_configuration(tenant_id)
        if config:
            config.remove_application(instance_name)
            await self._store_multi_app_configuration(tenant_id, config, user_id)
