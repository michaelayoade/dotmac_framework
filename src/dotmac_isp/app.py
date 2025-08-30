"""FastAPI application factory for the DotMac ISP Framework using shared factory."""

import logging
import os
from typing import Optional

from dotmac_shared.application import (
    DeploymentContext,
    DeploymentMode,
    IsolationLevel,
    ResourceLimits,
    TenantConfig,
    create_isp_framework_app,
)
from dotmac_shared.application.config import FeatureConfig

logger = logging.getLogger(__name__)


async def create_app(tenant_config: Optional[TenantConfig] = None) -> "FastAPI":
    """
    Create ISP Framework application using shared factory.

    This function creates either:
    1. A development instance (if no tenant_config provided)
    2. A tenant container instance (if tenant_config provided)
    """
    logger.info("Creating ISP Framework application using shared factory...")

    if tenant_config:
        logger.info(
            f"Creating tenant container app for tenant: {tenant_config.tenant_id}"
        )
        return await create_isp_framework_app(tenant_config)
    else:
        logger.info("Creating development ISP Framework app")
        return await create_isp_framework_app()


async def create_tenant_app(
    tenant_id: str, partner_id: str = "default", plan_type: str = "standard"
) -> "FastAPI":
    """
    Create a tenant-specific ISP Framework instance.

    This is used for containerized multi-tenant deployments where each
    tenant gets their own isolated container.
    """
    logger.info(f"Creating tenant application for {tenant_id}")

    # Get resource limits based on plan using configuration management
    resource_limits = ResourceLimits.from_plan_type(plan_type)

    # Create deployment context
    deployment_context = DeploymentContext(
        mode=DeploymentMode.TENANT_CONTAINER,
        tenant_id=tenant_id,
        isolation_level=IsolationLevel.CONTAINER,
        resource_limits=resource_limits,
        kubernetes_namespace=f"tenant-{tenant_id.lower().replace('_', '-')}",
        container_name=f"isp-framework-{tenant_id.lower().replace('_', '-')}",
    )
    # Get features based on plan using configuration management
    feature_config = FeatureConfig()
    enabled_features = feature_config.get_features_for_plan(plan_type, tenant_id)

    # Create tenant configuration
    tenant_config = TenantConfig(
        tenant_id=tenant_id,
        deployment_context=deployment_context,
        enabled_features=enabled_features,
        plan_type=plan_type,
    )
    # Feature configuration is now handled by FeatureConfig.get_features_for_plan()

    return await create_isp_framework_app(tenant_config)


# Create the default application instance
# the system will be a development instance unless overridden by environment
async def get_app_instance():
    """Get the appropriate app instance based on environment."""

    # Check if running in tenant container mode
    tenant_id = os.getenv("TENANT_ID")
    partner_id = os.getenv("PARTNER_ID", "default")
    plan_type = os.getenv("TENANT_PLAN", "standard")

    if tenant_id:
        logger.info(f"Running in tenant container mode for tenant: {tenant_id}")
        return await create_tenant_app(tenant_id, partner_id, plan_type)
    else:
        logger.info("Running in development mode")
        return await create_app()


# For compatibility with synchronous imports, we need to handle async creation
import asyncio

from dotmac_shared.api.exception_handlers import standard_exception_handler


def _create_app_sync():
    """Synchronous wrapper for app creation."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_app_instance())


# Create the application instance
app = _create_app_sync()

# Log the application creation
logger.info("✅ ISP Framework application created successfully using shared factory")
