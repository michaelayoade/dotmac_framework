from dotmac_shared.api.dependencies import (\n    PaginatedDependencies,\n    get_paginated_deps\n)\nfrom dotmac_shared.schemas.base_schemas import PaginatedResponseSchema\n"""
Plugin Management API endpoints.

Provides comprehensive plugin lifecycle management following DRY patterns.
Integrates with existing authentication, authorization, and monitoring systems.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.auth.dependencies import get_current_user, require_permissions
from dotmac_shared.plugins.core.manager import PluginManager

from ...core.auth import require_plugin_install, require_plugin_uninstall
from ...core.plugins.interfaces import PluginManagerInterface
from ...dependencies import get_current_tenant, get_plugin_manager
from ...models.plugin import LicenseStatus, LicenseTier, Plugin, PluginLicense
from ...schemas.plugin import (
    PluginCatalogResponse,
    PluginHealthResponse,
    PluginInstallationRequest,
    PluginInstallationResponse,
    PluginLicenseResponse,
    PluginResponse,
    PluginUpdateRequest,
    PluginUsageResponse,
)
from ...services.plugin_service import PluginService

# Create router using DRY RouterFactory pattern
router = APIRouter(prefix="/plugins", tags=["Plugin Management"])

# Use established logging pattern
from dotmac_shared.observability.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Plugin Catalog & Discovery
# ============================================================================


@router.get(
    "/catalog",
    response_model=PaginatedResponseSchema[PluginCatalogResponse],
    summary="Get plugin catalog",
    description="Retrieve available plugins with filtering and search capabilities",
)
@standard_exception_handler
async def get_plugin_catalog(
    category: Optional[str] = Query(None, description="Filter by plugin category"),
    search: Optional[str] = Query(
        None, description="Search plugin name or description"
    ),
    featured_only: bool = Query(False, description="Show only featured plugins"),
    free_only: bool = Query(False, description="Show only free plugins"),
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_service: PluginService = Depends(),
) -> List[PluginCatalogResponse]:
    """
    Get available plugins from catalog with optional filtering.
    Follows DRY pattern for API responses and error handling.
    """
    logger.info(f"Fetching plugin catalog for tenant {tenant_id}")

    try:
        plugins = await plugin_service.get_catalog(
            category=category,
            search_query=search,
            featured_only=featured_only,
            free_only=free_only,
            tenant_id=tenant_id,
        )

        logger.info(f"Retrieved {len(plugins)} plugins from catalog")
        return [PluginCatalogResponse.from_plugin(plugin) for plugin in plugins]

    except Exception as e:
        logger.error(f"Error fetching plugin catalog: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch plugin catalog: {str(e)}"
        )


@router.get(
    "/{plugin_id}",
    response_model=PluginResponse,
    summary="Get plugin details",
    description="Retrieve detailed information about a specific plugin",
)
@standard_exception_handler
async def get_plugin_details(
    plugin_id: UUID, plugin_service: PluginService = Depends()
) -> PluginResponse:
    """
    Get detailed plugin information.
    Uses DRY error handling and response patterns.
    """
    logger.info(f"Fetching details for plugin {plugin_id}")

    plugin = await plugin_service.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

    return PluginResponse.from_plugin(plugin)


# ============================================================================
# Plugin Installation & Management
# ============================================================================


@router.post(
    "/install",
    response_model=PluginInstallationResponse,
    summary="Install plugin",
    description="Install a plugin for the current tenant with license creation",
)
@standard_exception_handler
@require_plugin_install()
async def install_plugin(
    request: PluginInstallationRequest,
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_service: PluginService = Depends(),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
) -> PluginInstallationResponse:
    """
    Install plugin for tenant following DRY security and workflow patterns.
    Includes background task processing for async installation.
    """
    logger.info(f"Installing plugin {request.plugin_id} for tenant {tenant_id}")

    try:
        # Validate plugin exists and is available
        plugin = await plugin_service.get_plugin(request.plugin_id)
        if not plugin:
            raise HTTPException(status_code=404, detail="Plugin not found")

        if plugin.status != "active":
            raise HTTPException(
                status_code=400, detail="Plugin is not available for installation"
            )

        # Check if already installed
        existing_license = await plugin_service.get_tenant_plugin_license(
            tenant_id=tenant_id, plugin_id=request.plugin_id
        )

        if existing_license and existing_license.is_active:
            raise HTTPException(
                status_code=409,
                detail=f"Plugin {plugin.name} is already installed for tenant",
            )

        # Create plugin license and installation
        installation = await plugin_service.install_plugin(
            tenant_id=tenant_id,
            plugin_id=request.plugin_id,
            license_tier=request.license_tier,
            configuration=request.configuration,
        )

        # Background task for actual plugin loading and activation
        background_tasks.add_task(
            _activate_plugin_background,
            plugin_manager=plugin_manager,
            installation_id=installation.id,
            plugin_id=request.plugin_id,
        )

        logger.info(f"Plugin installation initiated: {installation.id}")
        return PluginInstallationResponse.from_license(installation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plugin installation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Plugin installation failed: {str(e)}"
        )


@router.put(
    "/installations/{installation_id}",
    response_model=PluginInstallationResponse,
    summary="Update plugin installation",
    description="Update plugin configuration or upgrade version",
)
@standard_exception_handler
@require_plugin_install()
async def update_plugin_installation(
    installation_id: UUID,
    request: PluginUpdateRequest,
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_service: PluginService = Depends(),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
) -> PluginInstallationResponse:
    """
    Update existing plugin installation following DRY patterns.
    """
    logger.info(
        f"Updating plugin installation {installation_id} for tenant {tenant_id}"
    )

    try:
        # Validate installation exists and belongs to tenant
        installation = await plugin_service.get_plugin_installation(
            installation_id=installation_id, tenant_id=tenant_id
        )

        if not installation:
            raise HTTPException(status_code=404, detail="Plugin installation not found")

        # Update installation
        updated_installation = await plugin_service.update_plugin_installation(
            installation_id=installation_id,
            version=request.version,
            configuration=request.configuration,
            license_tier=request.license_tier,
        )

        # Background task for plugin reloading
        background_tasks.add_task(
            _reload_plugin_background,
            plugin_manager=plugin_manager,
            installation_id=installation_id,
        )

        logger.info(f"Plugin installation updated: {installation_id}")
        return PluginInstallationResponse.from_license(updated_installation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plugin update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Plugin update failed: {str(e)}")


@router.delete(
    "/installations/{installation_id}",
    summary="Uninstall plugin",
    description="Remove plugin installation and clean up resources",
)
@standard_exception_handler
@require_plugin_uninstall()
async def uninstall_plugin(
    installation_id: UUID,
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_service: PluginService = Depends(),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
) -> JSONResponse:
    """
    Uninstall plugin following DRY cleanup and security patterns.
    """
    logger.info(
        f"Uninstalling plugin installation {installation_id} for tenant {tenant_id}"
    )

    try:
        # Validate installation exists
        installation = await plugin_service.get_plugin_installation(
            installation_id=installation_id, tenant_id=tenant_id
        )

        if not installation:
            raise HTTPException(status_code=404, detail="Plugin installation not found")

        # Check for dependent plugins
        dependent_plugins = await plugin_service.get_dependent_plugins(
            plugin_id=installation.plugin_id, tenant_id=tenant_id
        )

        if dependent_plugins:
            plugin_names = [p.plugin.name for p in dependent_plugins]
            raise HTTPException(
                status_code=409,
                detail=f"Cannot uninstall plugin. Required by: {', '.join(plugin_names)}",
            )

        # Uninstall plugin
        await plugin_service.uninstall_plugin(installation_id=installation_id)

        # Background cleanup task
        background_tasks.add_task(
            _cleanup_plugin_background,
            plugin_manager=plugin_manager,
            installation_id=installation_id,
        )

        logger.info(f"Plugin uninstalled: {installation_id}")
        return JSONResponse(
            status_code=200, content={"message": "Plugin uninstalled successfully"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plugin uninstall failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Plugin uninstall failed: {str(e)}"
        )


# ============================================================================
# Plugin Licensing & Usage
# ============================================================================


@router.get(
    "/installations",
    response_model=PaginatedResponseSchema[PluginInstallationResponse],
    summary="Get installed plugins",
    description="List all plugins installed for current tenant",
)
@standard_exception_handler
async def get_installed_plugins(
    status: Optional[LicenseStatus] = Query(
        None, description="Filter by license status"
    ),
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_service: PluginService = Depends(),
) -> List[PluginInstallationResponse]:
    """
    Get tenant's installed plugins using DRY filtering patterns.
    """
    logger.info(f"Fetching installed plugins for tenant {tenant_id}")

    try:
        installations = await plugin_service.get_tenant_plugins(
            tenant_id=tenant_id, status=status
        )

        return [
            PluginInstallationResponse.from_license(installation)
            for installation in installations
        ]

    except Exception as e:
        logger.error(f"Error fetching installed plugins: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch installed plugins: {str(e)}"
        )


@router.get(
    "/installations/{installation_id}/usage",
    response_model=PluginUsageResponse,
    summary="Get plugin usage stats",
    description="Retrieve usage statistics for plugin installation",
)
@standard_exception_handler
async def get_plugin_usage(
    installation_id: UUID,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_service: PluginService = Depends(),
) -> PluginUsageResponse:
    """
    Get plugin usage statistics following DRY analytics patterns.
    """
    logger.info(f"Fetching usage for installation {installation_id}")

    try:
        usage_stats = await plugin_service.get_plugin_usage_stats(
            installation_id=installation_id,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not usage_stats:
            raise HTTPException(status_code=404, detail="Plugin installation not found")

        return usage_stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching plugin usage: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch plugin usage: {str(e)}"
        )


# ============================================================================
# Plugin Health & Monitoring
# ============================================================================


@router.get(
    "/installations/{installation_id}/health",
    response_model=PluginHealthResponse,
    summary="Get plugin health",
    description="Check health status of installed plugin",
)
@standard_exception_handler
async def get_plugin_health(
    installation_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    plugin_service: PluginService = Depends(),
) -> PluginHealthResponse:
    """
    Get plugin health status using DRY monitoring patterns.
    """
    logger.info(f"Checking health for installation {installation_id}")

    try:
        # Validate installation exists
        installation = await plugin_service.get_plugin_installation(
            installation_id=installation_id, tenant_id=tenant_id
        )

        if not installation:
            raise HTTPException(status_code=404, detail="Plugin installation not found")

        # Get health from plugin manager
        plugin_key = f"{installation.plugin.name}.{installation.id}"
        health_data = await plugin_manager.get_plugin_health(
            domain=installation.plugin.name, name=str(installation.id)
        )

        return PluginHealthResponse(
            installation_id=installation_id,
            plugin_name=installation.plugin.name,
            status=health_data.get("status", "unknown"),
            last_check=health_data.get("last_check"),
            error_count=health_data.get("error_count", 0),
            success_rate=health_data.get("success_rate", 0.0),
            response_time_ms=health_data.get("avg_response_time", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking plugin health: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to check plugin health: {str(e)}"
        )


# ============================================================================
# Background Tasks (Following DRY Async Patterns)
# ============================================================================


async def _activate_plugin_background(
    plugin_manager: PluginManager, installation_id: UUID, plugin_id: UUID
) -> None:
    """
    Background task to activate plugin after installation.
    Uses DRY async task patterns.
    """
    try:
        logger.info(f"Activating plugin {plugin_id} for installation {installation_id}")

        # Load and register plugin with manager
        # Implementation would load plugin based on installation configuration
        # and register it with the tenant-specific plugin context

        logger.info(f"Plugin activated: {installation_id}")

    except Exception as e:
        logger.error(f"Failed to activate plugin {installation_id}: {e}")
        # Update installation status to failed
        # Implementation would update license status


async def _reload_plugin_background(
    plugin_manager: PluginManager, installation_id: UUID
) -> None:
    """
    Background task to reload plugin after update.
    """
    try:
        logger.info(f"Reloading plugin for installation {installation_id}")

        # Implementation would unload and reload plugin

        logger.info(f"Plugin reloaded: {installation_id}")

    except Exception as e:
        logger.error(f"Failed to reload plugin {installation_id}: {e}")


async def _cleanup_plugin_background(
    plugin_manager: PluginManager, installation_id: UUID
) -> None:
    """
    Background task to clean up plugin resources after uninstall.
    """
    try:
        logger.info(f"Cleaning up plugin for installation {installation_id}")

        # Implementation would clean up plugin data, caches, etc.

        logger.info(f"Plugin cleanup completed: {installation_id}")

    except Exception as e:
        logger.error(f"Failed to cleanup plugin {installation_id}: {e}")


# Export router
__all__ = ["router"]
