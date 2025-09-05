"""
Plugin Management API endpoints.

Provides comprehensive plugin lifecycle management following DRY patterns.
Integrates with existing authentication, authorization, and monitoring systems.
"""

from typing import Optional
from uuid import UUID

from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from fastapi import BackgroundTasks, Depends, Query

from dotmac.application import standard_exception_handler
from dotmac.application.api.router_factory import RouterFactory
from dotmac.application.dependencies.dependencies import (
    StandardDependencies,
    get_standard_deps,
)
from dotmac.core.schemas.base_schemas import PaginatedResponseSchema
from dotmac.platform.observability.logging import get_logger

from ...core.auth import require_plugin_install, require_plugin_uninstall

# Note: Dependency helpers are available if needed in future extensions
from ...schemas.plugin import (
    PluginCatalogResponse,
    PluginHealthResponse,
    PluginInstallationRequest,
    PluginInstallationResponse,
    PluginResponse,
    PluginUpdateRequest,
    PluginUsageResponse,
)
from ...services.plugin_service import PluginService

# Create router using DRY RouterFactory pattern
router_factory = RouterFactory("Plugin Management")
router = router_factory.create_router(prefix="/plugins", tags=["Plugin Management"])

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
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_plugin_catalog(
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: Optional[bool] = None,
    free_only: bool = Query(False, description="Show only free plugins"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PaginatedResponseSchema[PluginCatalogResponse]:
    """
    Get available plugins from catalog with optional filtering.
    Follows DRY pattern using RouterFactory and StandardDependencies.
    """
    plugin_service = PluginService(deps.db, deps.tenant_id)

    plugins = await plugin_service.get_catalog(
        category=category,
        search=search,
        featured_only=featured_only,
        free_only=free_only,
    )

    return PaginatedResponseSchema[PluginCatalogResponse](
        items=plugins,
        total=len(plugins),
        page=1,
        per_page=len(plugins),
    )


@router.get(
    "/installed",
    response_model=PaginatedResponseSchema[PluginResponse],
    summary="Get installed plugins",
    description="List all plugins installed for current tenant",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_installed_plugins(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PaginatedResponseSchema[PluginResponse]:
    """Get installed plugins for current tenant."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    plugins = await plugin_service.get_installed_plugins(deps.tenant_id)

    return PaginatedResponseSchema[PluginResponse](
        items=plugins,
        total=len(plugins),
        page=1,
        per_page=len(plugins),
    )


@router.get(
    "/{plugin_id}",
    response_model=PluginResponse,
    summary="Get plugin details",
)
@rate_limit(max_requests=180, time_window_seconds=60)
@standard_exception_handler
async def get_plugin(
    plugin_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PluginResponse:
    """Get detailed information about a specific plugin."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    plugin = await plugin_service.get_plugin(plugin_id)
    return plugin


# ============================================================================
# Plugin Installation & Lifecycle
# ============================================================================


@router.post(
    "/{plugin_id}/install",
    response_model=PluginInstallationResponse,
    summary="Install plugin",
)
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def install_plugin(
    plugin_id: UUID,
    request: PluginInstallationRequest,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps),
    _: None = Depends(require_plugin_install),
) -> PluginInstallationResponse:
    """Install a plugin for the current tenant."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    result = await plugin_service.install_plugin(
        plugin_id=plugin_id,
        tenant_id=deps.tenant_id,
        config=request.config,
        background_tasks=background_tasks,
    )

    return result


@router.delete(
    "/{plugin_id}/uninstall",
    response_model=dict,
    summary="Uninstall plugin",
)
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def uninstall_plugin(
    plugin_id: UUID,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps),
    _: None = Depends(require_plugin_uninstall),
) -> dict:
    """Uninstall a plugin from the current tenant."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    await plugin_service.uninstall_plugin(
        plugin_id=plugin_id,
        tenant_id=deps.tenant_id,
        background_tasks=background_tasks,
    )

    return {"status": "success", "message": "Plugin uninstalled successfully"}


@router.put(
    "/{plugin_id}",
    response_model=PluginResponse,
    summary="Update plugin configuration",
)
@rate_limit_strict(max_requests=60, time_window_seconds=60)
@standard_exception_handler
async def update_plugin(
    plugin_id: UUID,
    request: PluginUpdateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PluginResponse:
    """Update plugin configuration."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    updated_plugin = await plugin_service.update_plugin(
        plugin_id=plugin_id,
        tenant_id=deps.tenant_id,
        config_updates=request.config,
    )

    return updated_plugin


# ============================================================================
# Plugin Health & Monitoring
# ============================================================================


@router.get(
    "/{plugin_id}/health",
    response_model=PluginHealthResponse,
    summary="Check plugin health",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_plugin_health(
    plugin_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PluginHealthResponse:
    """Check the health status of a plugin."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    health_status = await plugin_service.get_plugin_health(plugin_id, deps.tenant_id)
    return health_status


@router.get(
    "/{plugin_id}/usage",
    response_model=PluginUsageResponse,
    summary="Get plugin usage statistics",
)
@rate_limit(max_requests=120, time_window_seconds=60)
@standard_exception_handler
async def get_plugin_usage(
    plugin_id: UUID,
    days: int = Query(30, description="Number of days to retrieve usage data"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> PluginUsageResponse:
    """Get usage statistics for a plugin."""
    plugin_service = PluginService(deps.db, deps.tenant_id)

    usage_data = await plugin_service.get_plugin_usage(
        plugin_id=plugin_id,
        tenant_id=deps.tenant_id,
        days=days,
    )

    return usage_data
