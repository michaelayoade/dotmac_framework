"""
Plugin API endpoints for marketplace and plugin management.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.plugin_service import PluginService
from schemas.plugin import ()
    Plugin, PluginCreate, PluginUpdate, PluginListResponse,
    PluginInstallation, PluginInstallationCreate, PluginInstallationUpdate, PluginInstallationListResponse,
    PluginHook, PluginHookCreate, PluginHookUpdate, PluginHookListResponse,
    PluginReview, PluginReviewCreate, PluginReviewUpdate, PluginReviewListResponse,
    PluginEvent, PluginEventListResponse,
    PluginInstallRequest, PluginUpdateRequest, PluginSearchRequest,
    BulkPluginOperation, PluginAnalytics, TenantPluginOverview
)
from core.auth import get_current_user, require_plugin_read, require_plugin_write, require_plugin_install, require_plugin_review
from core.pagination import PaginationParams

router = APIRouter()


# Plugin Marketplace
@router.post("/plugins", response_model=Plugin)
async def create_plugin():
    plugin_data: PluginCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Create a new plugin in the marketplace."""
    service = PluginService(db)
    return await service.create_plugin(plugin_data, current_user.user_id)


@router.post("/plugins/search", response_model=PluginListResponse)
async def search_plugins():
    search_request: PluginSearchRequest,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search plugins in the marketplace."""
    service = PluginService(db)
    
    plugins = await service.search_plugins()
        search_request=search_request,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    # Get total count for pagination
    total = await service.plugin_repo.count_search_results(search_request)
    
    return PluginListResponse()
        items=plugins,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins():
    category: Optional[str] = None,
    author: Optional[str] = None,
    is_official: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List plugins with optional filters."""
    service = PluginService(db)
    
    filters = {}
    if category:
        filters["category"] = category
    if author:
        filters["author"] = author
    if is_official is not None:
        filters["is_official"] = is_official
    if is_verified is not None:
        filters["is_verified"] = is_verified
    
    plugins = await service.plugin_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.plugin_repo.count(filters)
    
    return PluginListResponse()
        items=plugins,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/plugins/{plugin_id}", response_model=Plugin)
async def get_plugin():
    plugin_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific plugin."""
    service = PluginService(db)
    plugin = await service.plugin_repo.get_by_id(plugin_id)
    if not plugin:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    return plugin


@router.put("/plugins/{plugin_id}", response_model=Plugin)
async def update_plugin_details():
    plugin_id: UUID,
    plugin_update: PluginUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Update plugin details."""
    service = PluginService(db)
    plugin = await service.plugin_repo.update()
        plugin_id, plugin_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not plugin:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found"
        )
    return plugin


@router.get("/plugins/{plugin_id}/analytics", response_model=PluginAnalytics)
async def get_plugin_analytics():
    plugin_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """Get analytics for a plugin."""
    service = PluginService(db)
    return await service.get_plugin_analytics(plugin_id)


# Plugin Installations
@router.post("/installations", response_model=PluginInstallation)
async def install_plugin():
    tenant_id: UUID,
    install_request: PluginInstallRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_install()
):
    """Install a plugin for a tenant."""
    service = PluginService(db)
    return await service.install_plugin()
        tenant_id=tenant_id,
        install_request=install_request,
        installed_by=current_user.user_id
    )


@router.get("/installations", response_model=PluginInstallationListResponse)
async def list_plugin_installations():
    tenant_id: Optional[UUID] = None,
    plugin_id: Optional[UUID] = None,
    status: Optional[str] = None,
    enabled: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """List plugin installations with optional filters."""
    service = PluginService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if plugin_id:
        filters["plugin_id"] = plugin_id
    if status:
        filters["status"] = status
    if enabled is not None:
        filters["enabled"] = enabled
    
    installations = await service.installation_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.installation_repo.count(filters)
    
    return PluginInstallationListResponse()
        items=installations,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/installations/{installation_id}", response_model=PluginInstallation)
async def get_plugin_installation():
    installation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """Get a specific plugin installation."""
    service = PluginService(db)
    installation = await service.installation_repo.get_with_plugin(installation_id)
    if not installation:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin installation not found"
        )
    return installation


@router.put("/installations/{installation_id}", response_model=PluginInstallation)
async def update_plugin_installation():
    installation_id: UUID,
    update_request: PluginUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Update an installed plugin."""
    service = PluginService(db)
    return await service.update_plugin()
        installation_id=installation_id,
        update_request=update_request,
        updated_by=current_user.user_id
    )


@router.delete("/installations/{installation_id}")
async def uninstall_plugin():
    installation_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Uninstall a plugin."""
    service = PluginService(db)
    success = await service.uninstall_plugin()
        installation_id=installation_id,
        reason=reason,
        uninstalled_by=current_user.user_id
    )
    
    if success:
        return {"message": "Plugin uninstall initiated successfully"}
    else:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to uninstall plugin"
        )


@router.post("/installations/{installation_id}/enable")
async def enable_plugin():
    installation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Enable a plugin installation."""
    service = PluginService(db)
    installation = await service.installation_repo.update()
        installation_id, {"enabled": True}, current_user.user_id
    )
    if not installation:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin installation not found"
        )
    return {"message": "Plugin enabled successfully"}


@router.post("/installations/{installation_id}/disable")
async def disable_plugin():
    installation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Disable a plugin installation."""
    service = PluginService(db)
    installation = await service.installation_repo.update()
        installation_id, {"enabled": False}, current_user.user_id
    )
    if not installation:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin installation not found"
        )
    return {"message": "Plugin disabled successfully"}


# Plugin Hooks
@router.post("/hooks", response_model=PluginHook)
async def create_plugin_hook():
    hook_data: PluginHookCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Create a new plugin hook."""
    service = PluginService(db)
    hook_dict = hook_data.model_dump()
    hook = await service.hook_repo.create(hook_dict, current_user.user_id)
    return hook


@router.get("/hooks", response_model=PluginHookListResponse)
async def list_plugin_hooks():
    plugin_id: Optional[UUID] = None,
    hook_type: Optional[str] = None,
    active_only: bool = True,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """List plugin hooks with optional filters."""
    service = PluginService(db)
    
    filters = {}
    if plugin_id:
        filters["plugin_id"] = plugin_id
    if hook_type:
        filters["hook_type"] = hook_type
    if active_only:
        filters["is_active"] = True
    
    hooks = await service.hook_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.hook_repo.count(filters)
    
    return PluginHookListResponse()
        items=hooks,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/hooks/{hook_id}", response_model=PluginHook)
async def get_plugin_hook():
    hook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """Get a specific plugin hook."""
    service = PluginService(db)
    hook = await service.hook_repo.get_by_id(hook_id)
    if not hook:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin hook not found"
        )
    return hook


@router.put("/hooks/{hook_id}", response_model=PluginHook)
async def update_plugin_hook():
    hook_id: UUID,
    hook_update: PluginHookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Update a plugin hook."""
    service = PluginService(db)
    hook = await service.hook_repo.update()
        hook_id, hook_update.model_dump(exclude_unset=True), current_user.user_id
    )
    if not hook:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin hook not found"
        )
    return hook


@router.delete("/hooks/{hook_id}")
async def delete_plugin_hook():
    hook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Delete a plugin hook."""
    service = PluginService(db)
    success = await service.hook_repo.delete(hook_id)
    if not success:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin hook not found"
        )
    return {"message": "Plugin hook deleted successfully"}


# Plugin Reviews
@router.post("/reviews", response_model=dict)
async def submit_plugin_review():
    tenant_id: UUID,
    review_data: PluginReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_review()
):
    """Submit a plugin review."""
    service = PluginService(db)
    success = await service.submit_review()
        tenant_id=tenant_id,
        review_data=review_data,
        reviewer_id=current_user.user_id
    )
    
    if success:
        return {"message": "Review submitted successfully"}
    else:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit review"
        )


@router.get("/reviews", response_model=PluginReviewListResponse)
async def list_plugin_reviews():
    plugin_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List plugin reviews with optional filters."""
    service = PluginService(db)
    
    filters = {}
    if plugin_id:
        filters["plugin_id"] = plugin_id
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if min_rating:
        filters["rating__gte"] = min_rating
    
    reviews = await service.review_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.review_repo.count(filters)
    
    return PluginReviewListResponse()
        items=reviews,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get("/reviews/{review_id}", response_model=PluginReview)
async def get_plugin_review():
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific plugin review."""
    service = PluginService(db)
    review = await service.review_repo.get_by_id(review_id)
    if not review:
        raise HTTPException()
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin review not found"
        )
    return review


# Plugin Events
@router.get("/events", response_model=PluginEventListResponse)
async def list_plugin_events():
    installation_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    processed: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """List plugin events with optional filters."""
    service = PluginService(db)
    
    filters = {}
    if installation_id:
        filters["plugin_installation_id"] = installation_id
    if event_type:
        filters["event_type"] = event_type
    if processed is not None:
        filters["processed"] = processed
    
    events = await service.event_repo.list()
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await service.event_repo.count(filters)
    
    return PluginEventListResponse()
        items=events,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


# Bulk Operations
@router.post("/bulk-operations")
async def execute_bulk_plugin_operation():
    tenant_id: UUID,
    operation: BulkPluginOperation,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_write()
):
    """Execute bulk operations on plugins."""
    service = PluginService(db)
    results = await service.execute_bulk_operation()
        tenant_id=tenant_id,
        operation=operation,
        executed_by=current_user.user_id
    )
    return results


# Tenant Overview
@router.get("/tenants/{tenant_id}/overview", response_model=TenantPluginOverview)
async def get_tenant_plugin_overview():
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_plugin_read()
):
    """Get comprehensive plugin overview for a tenant."""
    service = PluginService(db)
    return await service.get_tenant_plugin_overview(tenant_id)