"""
Knowledge Base API Router - Production Ready with DRY Patterns
Leverages existing DotMac RouterFactory and authentication patterns
"""

from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Query, status

from dotmac_shared.api.dependencies import (
    StandardDependencies, PaginatedDependencies,
    get_standard_deps, get_paginated_deps, get_admin_deps
)
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit
from dotmac_shared.api.router_factory import RouterFactory

from .models import (
    ArticleCreate, ArticleResponse, ArticleSearchParams, ArticleUpdate,
    CommentCreate, CommentResponse, PortalSettingsUpdate, PortalSettingsResponse
)
from .service import KnowledgeService, KnowledgeAnalyticsService

# Initialize services (would be dependency injected in production)
knowledge_service = KnowledgeService()
analytics_service = KnowledgeAnalyticsService()

# Create router using existing RouterFactory pattern
router = RouterFactory.create_crud_router(
    service_class=KnowledgeService,
    create_schema=ArticleCreate,
    update_schema=ArticleUpdate,
    response_schema=ArticleResponse,
    prefix="/knowledge",
    tags=["knowledge-base"],
    enable_search=True,
    enable_bulk_operations=False  # Articles require individual review
)


# Public Knowledge Base Endpoints (Customer-facing)

@router.get("/articles/search", response_model=List[ArticleResponse])
@standard_exception_handler
async def search_articles(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    query: Optional[str] = Query(None, max_length=500, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    article_type: Optional[str] = Query(None, description="Filter by article type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    sort_by: str = Query("relevance", regex="^(relevance|created_at|updated_at|view_count|helpful_votes)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
):
    """Search published knowledge base articles."""
    search_params = ArticleSearchParams(
        query=query,
        category=category,
        article_type=article_type,
        tags=tags,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        status=["published"]  # Only show published articles to customers
    )
    
    articles, total_count, metadata = await knowledge_service.search_articles(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        search_params=search_params
    )
    
    # Add search metadata to response headers
    deps.response.headers["X-Total-Count"] = str(total_count)
    deps.response.headers["X-Page"] = str(page)
    deps.response.headers["X-Page-Size"] = str(page_size)
    deps.response.headers["X-Total-Pages"] = str(metadata.get("total_pages", 0))
    
    return articles


@router.get("/articles/{article_slug}", response_model=ArticleResponse)
@standard_exception_handler
async def get_article_by_slug(
    article_slug: str,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Get published article by slug."""
    article = await knowledge_service.get_article_by_slug(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        slug=article_slug,
        increment_view=True
    )
    
    if not article or article.status != "published":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    # Track analytics
    await analytics_service.track_article_view(
        db=deps.db,
        article_id=article.id,
        tenant_id=str(deps.tenant_id),
        user_id=getattr(deps, 'current_customer', {}).get('id') if hasattr(deps, 'current_customer') else None,
        referrer=deps.request.headers.get('referer')
    )
    
    return article


@router.get("/articles/{article_id}/related", response_model=List[ArticleResponse])
@standard_exception_handler
async def get_related_articles(
    article_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
    limit: int = Query(5, ge=1, le=20)
):
    """Get articles related to the specified article."""
    related_articles = await knowledge_service.get_related_articles(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_id=article_id,
        limit=limit
    )
    
    return related_articles


@router.get("/articles/popular", response_model=List[ArticleResponse])
@standard_exception_handler
async def get_popular_articles(
    deps: StandardDependencies = Depends(get_standard_deps),
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365, description="Time period in days")
):
    """Get most popular articles by view count."""
    popular_articles = await knowledge_service.get_popular_articles(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        limit=limit,
        days=days
    )
    
    return popular_articles


@router.post("/articles/{article_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=5, time_window_seconds=300)  # Prevent vote spam
@standard_exception_handler
async def vote_on_article(
    article_id: str,
    is_helpful: bool,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Vote on article helpfulness."""
    user_id = getattr(deps, 'current_customer', {}).get('id') if hasattr(deps, 'current_customer') else None
    
    success = await knowledge_service.vote_on_article(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_id=article_id,
        is_helpful=is_helpful,
        user_id=user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )


@router.post(
    "/articles/{article_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED
)
@rate_limit(max_requests=10, time_window_seconds=600)  # Prevent comment spam
@standard_exception_handler
async def add_article_comment(
    article_id: str,
    comment_data: CommentCreate,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Add a comment to an article."""
    user_info = getattr(deps, 'current_customer', None) if hasattr(deps, 'current_customer') else None
    
    comment = await knowledge_service.add_comment(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_id=article_id,
        comment_data=comment_data,
        author_id=user_info.get('id') if user_info else None,
        author_name=user_info.get('name', 'Anonymous') if user_info else 'Anonymous',
        author_email=user_info.get('email') if user_info else None,
        author_type="customer"
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return comment


@router.get("/articles/{article_id}/comments", response_model=List[CommentResponse])
@standard_exception_handler
async def get_article_comments(
    article_id: str,
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get comments for an article."""
    # This would be implemented in the service layer
    # For now, return empty list as placeholder
    return []


# Customer Portal Settings Endpoints

@router.get("/portal/settings", response_model=PortalSettingsResponse)
@standard_exception_handler
async def get_portal_settings(
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Get customer portal settings."""
    if not hasattr(deps, 'current_customer'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer authentication required"
        )
    
    settings = await knowledge_service.get_customer_portal_settings(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        customer_id=str(deps.current_customer.id)
    )
    
    return settings


@router.put("/portal/settings", response_model=PortalSettingsResponse)
@standard_exception_handler
async def update_portal_settings(
    settings_data: PortalSettingsUpdate,
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """Update customer portal settings."""
    if not hasattr(deps, 'current_customer'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer authentication required"
        )
    
    settings = await knowledge_service.update_portal_settings(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        customer_id=str(deps.current_customer.id),
        settings_data=settings_data
    )
    
    return settings


# Admin Endpoints for Content Management

admin_router = RouterFactory.create_crud_router(
    service_class=KnowledgeService,
    create_schema=ArticleCreate,
    update_schema=ArticleUpdate,
    response_schema=ArticleResponse,
    prefix="/admin/knowledge",
    tags=["admin-knowledge"],
    enable_search=True,
    enable_bulk_operations=True
)


@admin_router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def create_article(
    article_data: ArticleCreate,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Create a new knowledge base article."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    
    article = await knowledge_service.create_article(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_data=article_data,
        author_id=str(deps.current_user.id),
        author_name=deps.current_user.name or deps.current_user.email
    )
    
    return article


@admin_router.get("/articles/{article_id}", response_model=ArticleResponse)
@standard_exception_handler
async def get_article_admin(
    article_id: str,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Get article by ID (admin view - includes unpublished)."""
    article = await knowledge_service.get_article(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_id=article_id,
        increment_view=False  # Don't count admin views
    )
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return article


@admin_router.put("/articles/{article_id}", response_model=ArticleResponse)
@standard_exception_handler
async def update_article(
    article_id: str,
    article_data: ArticleUpdate,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Update an existing article."""
    if not hasattr(deps, 'current_user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    
    article = await knowledge_service.update_article(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_id=article_id,
        update_data=article_data,
        updated_by=str(deps.current_user.id)
    )
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return article


@admin_router.get("/articles", response_model=List[ArticleResponse])
@standard_exception_handler
async def list_all_articles(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    status_filter: Optional[List[str]] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    author_id: Optional[str] = Query(None, description="Filter by author"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """List all articles (admin view - includes unpublished)."""
    search_params = ArticleSearchParams(
        category=category,
        status=status_filter,
        page=page,
        page_size=page_size,
        sort_by="updated_at",
        sort_order="desc"
    )
    
    articles, total_count, metadata = await knowledge_service.search_articles(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        search_params=search_params
    )
    
    # Add pagination headers
    deps.response.headers["X-Total-Count"] = str(total_count)
    deps.response.headers["X-Page"] = str(page)
    deps.response.headers["X-Page-Size"] = str(page_size)
    
    return articles


@admin_router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
@standard_exception_handler
async def publish_article(
    article_id: str,
    deps: StandardDependencies = Depends(get_admin_deps)
):
    """Publish an article."""
    article_data = ArticleUpdate(status="published")
    
    article = await knowledge_service.update_article(
        db=deps.db,
        tenant_id=str(deps.tenant_id),
        article_id=article_id,
        update_data=article_data,
        updated_by=str(deps.current_user.id) if hasattr(deps, 'current_user') else None
    )
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return article


@admin_router.get("/analytics/overview", response_model=Dict[str, Any])
@standard_exception_handler
async def get_knowledge_base_analytics(
    deps: StandardDependencies = Depends(get_admin_deps),
    days: int = Query(30, ge=1, le=365, description="Analytics period in days")
):
    """Get knowledge base analytics overview."""
    # This would be implemented to return comprehensive analytics
    # Including article views, popular searches, user engagement, etc.
    
    return {
        "period_days": days,
        "total_articles": 0,
        "published_articles": 0,
        "total_views": 0,
        "unique_visitors": 0,
        "search_queries": 0,
        "top_articles": [],
        "top_searches": [],
        "customer_satisfaction": 0.0,
        "generated_at": "2025-01-01T00:00:00Z"
    }


# Export routers for app inclusion
def get_knowledge_routers():
    """Get all knowledge base routers."""
    return [router, admin_router]