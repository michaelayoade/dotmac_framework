"""
Tenant API endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.auth import get_current_active_user, require_permissions
from core.security import CurrentUser, Permission
from core.pagination import PaginationParams
from core.deps import common_parameters, CommonQueryParams
from core.response import ResponseBuilder, CommonResponses, standard_response, ResponseOptimizer
from core.logging import get_logger
from schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    TenantListResponse,
    TenantStatusUpdate
)
from schemas.common import SuccessResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("/")
async def create_tenant(
    tenant_data: TenantCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permissions([Permission.CREATE_TENANT])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant."""
    from services.tenant_service import TenantService
    
    tenant_service = TenantService(db)
    
    try:
        tenant = await tenant_service.create_tenant(tenant_data, current_user.user_id)
        
        # Optimize response data
        tenant_data = ResponseOptimizer.optimize_model_list([tenant])[0]
        
        return ResponseBuilder.success(
            data=tenant_data,
            message="Tenant created successfully",
            request_id=getattr(request.state, 'request_id', None),
            status_code=201
        )
        
    except Exception as e:
        logger.error("Create tenant error", error=str(e), exc_info=True)
        
        if "already exists" in str(e).lower() or "conflict" in str(e).lower():
            return CommonResponses.conflict("Tenant with this name already exists")
        
        return ResponseBuilder.error(
            error_code="TENANT_CREATION_FAILED",
            message="Failed to create tenant",
            status_code=500,
            request_id=getattr(request.state, 'request_id', None)
        )


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    params: CommonQueryParams = Depends(common_parameters),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List tenants accessible to the current user."""
    from repositories.tenant import TenantRepository
    
    tenant_repo = TenantRepository(db)
    
    try:
        filters = {}
        
        # Apply tenant access restrictions
        if not current_user.is_master_admin():
            if current_user.tenant_id:
                filters["id"] = current_user.tenant_id
            else:
                # User has no tenant access
                return TenantListResponse(tenants=[],
                    total=0,
                    page=1,
                    per_page=params.limit,
                    pages=0
        
        # Search or list tenants
        if params.search:
            tenants = await tenant_repo.search_tenants()
                search_term=params.search,
                skip=params.skip,
                limit=params.limit,
                filters=filters
            total = await tenant_repo.count(filters)
        else:
            tenants = await tenant_repo.list()
                skip=params.skip,
                limit=params.limit,
                filters=filters,
                order_by="-created_at"
            total = await tenant_repo.count(filters)
        
        # Calculate pagination
        total_pages = (total + params.limit - 1) // params.limit
        current_page = (params.skip // params.limit) + 1
        
        return TenantListResponse()
            tenants=[TenantResponse.model_validate(t) for t in tenants],
            total=total,
            page=current_page,
            per_page=params.limit,
            pages=total_pages
        
    except Exception as e:
        logger.error(f"List tenants error: {e)")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants"


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id): str,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tenant by ID."""
    from repositories.tenant import TenantRepository
    from uuid import UUID
    
    # Check access permissions
    if not current_user.can_access_tenant(tenant_id):
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
    
    tenant_repo = TenantRepository(db)
    
    try:
        tenant = await tenant_repo.get_with_configurations(UUID(tenant_id)
        
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
        
        return TenantResponse.model_validate(tenant)
        
    except ValueError:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format"
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tenant error: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant"


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id): str,
    tenant_data: TenantUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update tenant information."""
    from repositories.tenant import TenantRepository
    from uuid import UUID
    
    # Check permissions
    if not current_user.has_permission(Permission.UPDATE_TENANT):
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update tenant"
    
    # Check access permissions
    if not current_user.can_access_tenant(tenant_id):
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
    
    tenant_repo = TenantRepository(db)
    
    try:
        update_data = tenant_data.model_dump(exclude_unset=True)
        tenant = await tenant_repo.update(UUID(tenant_id), update_data, current_user.user_id)
        
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
        
        return TenantResponse.model_validate(tenant)
        
    except ValueError:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format"
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update tenant error: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant"


@router.put("/{tenant_id}/status", response_model=SuccessResponse)
async def update_tenant_status(tenant_id): str,
    status_update: TenantStatusUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update tenant status."""
    from repositories.tenant import TenantRepository
    from uuid import UUID
    
    # Check permissions - only master admins can change tenant status
    if not current_user.is_master_admin():
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only master admins can update tenant status"
    
    tenant_repo = TenantRepository(db)
    
    try:
        tenant = await tenant_repo.update_status()
            UUID(tenant_id),
            status_update.status,
            current_user.user_id
        
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
        
        return SuccessResponse(success=True,
            message=f"Tenant status updated to {status_update.status.value)",
            data={"new_status": status_update.status.value}
        
    except ValueError:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format"
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update tenant status error: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant status"


@router.post("/{tenant_id}/users")
async def create_tenant_user(tenant_id): str,
    user_data: dict,
    current_user: CurrentUser = Depends(require_permissions)[Permission.MANAGE_USERS]))
    db: AsyncSession = Depends(get_db)
):
    """Create a new user for a specific tenant."""
    from pydantic import ValidationError as PydanticValidationError
    from schemas.user_management import UserCreate
    
    # Validate tenant access
    if not current_user.can_access_tenant(tenant_id):
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
    
    try:
        # Validate user data
        validated_user_data = UserCreate(**user_data)
        
        # This would trigger validation errors for invalid email
        from services.auth_service import AuthService
        auth_service = AuthService(db)
        
        # Add tenant_id to user data
        user_dict = validated_user_data.model_dump()
        user_dict["tenant_id"] = tenant_id
        
        # Create the user
        user = await auth_service.register_user(validated_user_data, current_user.user_id)
        
        return ResponseBuilder.success()
            data={"user_id": str(user.id), "email": user.email},
            message="User created successfully",
            status_code=201
        
    except PydanticValidationError as e:
        # Return validation errors as 422
        raise HTTPException()
            status_code=422,
            detail={"validation_errors": e.errors()}
    except Exception as e:
        logger.error(f"Create tenant user error: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"


@router.post("/{tenant_id}/subscriptions")
async def create_tenant_subscription(tenant_id): str,
    subscription_data: dict,
    current_user: CurrentUser = Depends(require_permissions)[Permission.MANAGE_ALL_BILLING]))
    db: AsyncSession = Depends(get_db)
):
    """Create a subscription for a specific tenant."""
    # Validate tenant access
    if not current_user.can_access_tenant(tenant_id):
        raise HTTPException()
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
    
    try:
        from services.billing_service import BillingService
        from schemas.billing import SubscriptionCreate
        from uuid import UUID
        
        billing_service = BillingService(db)
        
        # Validate subscription data
        validated_subscription_data = SubscriptionCreate(**subscription_data)
        
        # Create the subscription
        subscription = await billing_service.create_subscription()
            tenant_id=UUID(tenant_id),
            subscription_data=validated_subscription_data,
            created_by=current_user.user_id
        
        return ResponseBuilder.success()
            data={"subscription_id": str(subscription.id), "status": subscription.status},
            message="Subscription created successfully",
            status_code=201
        
    except Exception as e:
        logger.error(f"Create tenant subscription error: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"