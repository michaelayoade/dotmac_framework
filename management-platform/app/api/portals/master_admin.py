"""
Master Admin Portal API endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...core.deps import require_master_admin, CommonQueryParams, common_parameters
from ...core.security import CurrentUser
from ...schemas.common import SuccessResponse, HealthResponse
from ...schemas.tenant import TenantListResponse, TenantResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=dict)
async def get_dashboard_overview(
    current_user: CurrentUser = Depends(require_master_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get master admin dashboard overview."""
    from ...repositories.tenant import TenantRepository
    from ...repositories.user import UserRepository
    from ...models.tenant import TenantStatus
    
    tenant_repo = TenantRepository(db)
    user_repo = UserRepository(db)
    
    try:
        # Get tenant counts by status
        tenant_counts = await tenant_repo.get_tenant_count_by_status()
        
        # Get total users
        total_users = await user_repo.count()
        
        # Get active tenants
        active_tenants = await tenant_repo.get_active_tenants(limit=10)
        
        return {
            "tenant_summary": {
                "total": sum(tenant_counts.values()),
                "active": tenant_counts.get(TenantStatus.ACTIVE, 0),
                "pending": tenant_counts.get(TenantStatus.PENDING, 0),
                "suspended": tenant_counts.get(TenantStatus.SUSPENDED, 0),
            },
            "user_summary": {
                "total": total_users,
            },
            "recent_tenants": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                }
                for t in active_tenants
            ],
            "platform_health": {
                "status": "healthy",
                "uptime": "99.9%",
                "response_time_ms": 150,
            }
        }
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard overview"
        )


@router.get("/tenants", response_model=TenantListResponse)
async def list_all_tenants(
    params: CommonQueryParams = Depends(common_parameters),
    status_filter: Optional[str] = Query(None, alias="status"),
    tier_filter: Optional[str] = Query(None, alias="tier"),
    current_user: CurrentUser = Depends(require_master_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all tenants with filtering and pagination."""
    from ...repositories.tenant import TenantRepository
    from ...models.tenant import TenantStatus, TenantTier
    
    tenant_repo = TenantRepository(db)
    
    try:
        filters = {}
        
        if status_filter:
            try:
                filters["status"] = TenantStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        if tier_filter:
            try:
                filters["tier"] = TenantTier(tier_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tier: {tier_filter}"
                )
        
        # Search or list tenants
        if params.search:
            tenants = await tenant_repo.search_tenants(
                search_term=params.search,
                skip=params.skip,
                limit=params.limit,
                filters=filters
            )
            total = await tenant_repo.count(filters)  # Approximate for search
        else:
            tenants = await tenant_repo.list(
                skip=params.skip,
                limit=params.limit,
                filters=filters,
                order_by="-created_at"
            )
            total = await tenant_repo.count(filters)
        
        # Calculate pagination
        total_pages = (total + params.limit - 1) // params.limit
        current_page = (params.skip // params.limit) + 1
        
        return TenantListResponse(
            tenants=[TenantResponse.model_validate(t) for t in tenants],
            total=total,
            page=current_page,
            per_page=params.limit,
            pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List tenants error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants"
        )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant_details(
    tenant_id: str,
    current_user: CurrentUser = Depends(require_master_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific tenant."""
    from ...repositories.tenant import TenantRepository
    from uuid import UUID
    
    tenant_repo = TenantRepository(db)
    
    try:
        tenant = await tenant_repo.get_with_configurations(UUID(tenant_id))
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return TenantResponse.model_validate(tenant)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tenant details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant details"
        )


@router.get("/health", response_model=HealthResponse)
async def get_platform_health(
    current_user: CurrentUser = Depends(require_master_admin)
):
    """Get platform health status."""
    from datetime import datetime
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        details={
            "uptime_seconds": 86400,  # Example: 24 hours
            "active_connections": 50,
            "database_status": "connected",
            "redis_status": "connected",
            "memory_usage_mb": 512,
            "cpu_usage_percent": 25.0
        }
    )


@router.get("/stats", response_model=dict)
async def get_platform_statistics(
    current_user: CurrentUser = Depends(require_master_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide statistics."""
    from ...repositories.tenant import TenantRepository
    from ...repositories.user import UserRepository
    
    tenant_repo = TenantRepository(db)
    user_repo = UserRepository(db)
    
    try:
        # Get basic counts
        total_tenants = await tenant_repo.count()
        total_users = await user_repo.count()
        tenant_counts = await tenant_repo.get_tenant_count_by_status()
        
        return {
            "tenants": {
                "total": total_tenants,
                "by_status": tenant_counts,
                "growth_rate": 5.2  # Placeholder
            },
            "users": {
                "total": total_users,
                "active_last_30_days": int(total_users * 0.8),  # Placeholder
            },
            "revenue": {
                "monthly_recurring": 125000.00,  # Placeholder
                "annual_run_rate": 1500000.00,   # Placeholder
                "average_per_tenant": 2500.00     # Placeholder
            },
            "system": {
                "api_requests_today": 15000,      # Placeholder
                "avg_response_time_ms": 150,      # Placeholder
                "error_rate_percent": 0.1         # Placeholder
            }
        }
        
    except Exception as e:
        logger.error(f"Get platform statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get platform statistics"
        )