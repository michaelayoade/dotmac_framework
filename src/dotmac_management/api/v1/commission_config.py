"""
Commission configuration API for management portal.
Allows admins to configure all reseller commission structures.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Path, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    get_standard_deps,
    get_paginated_deps
)
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import (
    rate_limit_user,
    rate_limit_strict,
    RateLimitType
)
from dotmac_shared.observability.logging import get_logger
from dotmac_shared.schemas.base_schemas import PaginatedResponseSchema

from ...models.commission_config import (
    CommissionConfig,
    RevenueModel,
    CommissionConfigCreate,
    CommissionConfigUpdate,
    CommissionConfigResponse,
    RevenueModelCreate,
    RevenueModelUpdate,
    RevenueModelResponse,
)


router = APIRouter(
    prefix="/commission-config",
    tags=["Commission Configuration"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)
logger = get_logger(__name__)


# === COMMISSION CONFIG ENDPOINTS ===

@router.post(
    "/",
    response_model=CommissionConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Commission Configuration",
    description="""
    Create a new commission configuration for reseller partners.
    
    This endpoint allows administrators to create commission structures that define:
    - Commission rates and tiers
    - Revenue sharing models
    - Territory-specific configurations
    - Reseller type-specific rules
    
    **Business Context:**
    Commission configurations control how resellers earn commissions from sales.
    Each configuration can be set as default for new partners or assigned specifically.
    """,
    responses={
        201: {
            "description": "Commission configuration created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Standard Partner Commission",
                        "commission_rate": 0.15,
                        "is_default": True,
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid commission configuration data"},
        409: {"description": "Commission configuration already exists"},
        500: {"description": "Internal server error"}
    },
    tags=["Commission Configuration"],
    operation_id="createCommissionConfig"
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Financial data - strict limits
@standard_exception_handler
async def create_commission_config(
    config_data: CommissionConfigCreate,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> CommissionConfigResponse:
    """
    Create a new commission configuration for reseller partners.
    
    Args:
        config_data: Commission configuration details including rates, tiers, and rules
        deps: Standard dependencies including database session and authentication
        
    Returns:
        CommissionConfigResponse: The created commission configuration with generated ID
        
    Raises:
        HTTPException: 409 if configuration name conflicts
        HTTPException: 500 if database operation fails
    """
    
    logger.info(f"Creating commission config: {config_data.name} for user {deps.user_id}")
    
    try:
        # If setting as default, unset other defaults
        if config_data.is_default:
            logger.info("Setting as default, unsetting other default configs")
            await _unset_default_configs(deps.db)
        
        config = CommissionConfig(**config_data.model_dump())
        deps.db.add(config)
        await deps.db.commit()
        await deps.db.refresh(config)
        
        logger.info(f"Commission config created successfully: {config.id}")
        return CommissionConfigResponse.model_validate(config)
        
    except Exception as e:
        logger.error(f"Failed to create commission config: {e}")
        await deps.db.rollback()
        raise


@router.get(
    "/",
    response_model=List[CommissionConfigResponse],
    summary="List Commission Configurations",
    description="""
    Retrieve a paginated list of commission configurations with optional filtering.
    
    **Business Context:**
    This endpoint provides access to all commission configurations in the system,
    allowing administrators to review, compare, and manage different commission structures.
    
    **Filtering Options:**
    - Filter by active status to see only currently used configurations
    - Filter by reseller type to view type-specific commission structures  
    - Filter by territory to see region-specific configurations
    """,
    responses={
        200: {
            "description": "List of commission configurations retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Standard Partner Commission",
                            "commission_rate": 0.15,
                            "reseller_type": "partner",
                            "territory": "US",
                            "is_active": True,
                            "is_default": True
                        }
                    ]
                }
            }
        },
        500: {"description": "Internal server error"}
    },
    tags=["Commission Configuration"],
    operation_id="listCommissionConfigs"
)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Read operations - normal user limits
@standard_exception_handler
async def list_commission_configs(
    deps: StandardDependencies = Depends(get_standard_deps),
    is_active: Optional[bool] = Query(
        None,
        description="Filter configurations by active status. True for active only, False for inactive only",
        example=True
    ),
    reseller_type: Optional[str] = Query(
        None,
        description="Filter by reseller type (e.g., 'partner', 'enterprise', 'small_business')",
        example="partner"
    ),
    territory: Optional[str] = Query(
        None,
        description="Filter by territory/region code (e.g., 'US', 'EU', 'APAC')",
        example="US"
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number for pagination (starts from 1)",
        example=1
    ),
    size: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of items per page (maximum 100)",
        example=20
    )
) -> List[CommissionConfigResponse]:
    """
    Retrieve a paginated list of commission configurations with optional filtering.
    
    Args:
        deps: Standard dependencies including database session and authentication
        is_active: Optional filter for active status
        reseller_type: Optional filter for specific reseller types
        territory: Optional filter for specific territories
        page: Page number for pagination (starts from 1)
        size: Number of items per page (1-100)
        
    Returns:
        List[CommissionConfigResponse]: Paginated list of commission configurations
        
    Raises:
        HTTPException: 500 if database operation fails
    """
    
    query = select(CommissionConfig)
    
    # Apply filters
    if is_active is not None:
        query = query.where(CommissionConfig.is_active == is_active)
    if reseller_type:
        query = query.where(CommissionConfig.reseller_type == reseller_type)
    if territory:
        query = query.where(CommissionConfig.territory == territory)
    
    # Pagination
    query = query.order_by(CommissionConfig.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    
    result = await deps.db.execute(query)
    configs = result.scalars().all()
    
    return [CommissionConfigResponse.model_validate(config) for config in configs]


@router.get(
    "/default",
    response_model=CommissionConfigResponse,
    summary="Get Default Commission Configuration",
    description="""
    Retrieve the currently active default commission configuration.
    
    **Business Context:**
    The default commission configuration is automatically applied to new reseller partners
    unless a specific configuration is assigned. This endpoint is commonly used during
    partner onboarding and system initialization.
    """,
    responses={
        200: {
            "description": "Default commission configuration retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Default Partner Commission",
                        "commission_rate": 0.15,
                        "is_default": True,
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        404: {"description": "No default commission configuration found"},
        500: {"description": "Internal server error"}
    },
    tags=["Commission Configuration"],
    operation_id="getDefaultCommissionConfig"
)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Read operations - normal user limits
@standard_exception_handler
async def get_default_commission_config(
    deps: StandardDependencies = Depends(get_standard_deps)
) -> CommissionConfigResponse:
    """
    Retrieve the currently active default commission configuration.
    
    Args:
        deps: Standard dependencies including database session and authentication
        
    Returns:
        CommissionConfigResponse: The default commission configuration
        
    Raises:
        HTTPException: 404 if no default configuration exists
        HTTPException: 500 if database operation fails
    """
    
    query = select(CommissionConfig).where(
        CommissionConfig.is_default == True,
        CommissionConfig.is_active == True
    )
    
    result = await deps.db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default commission configuration found"
        )
    
    return CommissionConfigResponse.model_validate(config)


@router.get(
    "/{config_id}",
    response_model=CommissionConfigResponse,
    summary="Get Commission Configuration by ID",
    description="""
    Retrieve a specific commission configuration by its unique identifier.
    
    **Business Context:**
    This endpoint provides detailed information about a specific commission configuration,
    including all rates, tiers, and rules. Used for configuration review, editing, and
    partner assignment workflows.
    """,
    responses={
        200: {
            "description": "Commission configuration retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Enterprise Partner Commission",
                        "commission_rate": 0.20,
                        "tiers": [
                            {"min_volume": 0, "max_volume": 10000, "rate": 0.15},
                            {"min_volume": 10000, "max_volume": None, "rate": 0.20}
                        ],
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        404: {"description": "Commission configuration not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Commission Configuration"],
    operation_id="getCommissionConfig"
)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Read operations - normal user limits
@standard_exception_handler
async def get_commission_config(
    config_id: UUID = Path(
        ...,
        description="Unique identifier of the commission configuration",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> CommissionConfigResponse:
    """
    Retrieve a specific commission configuration by its unique identifier.
    
    Args:
        config_id: The UUID of the commission configuration to retrieve
        deps: Standard dependencies including database session and authentication
        
    Returns:
        CommissionConfigResponse: The requested commission configuration
        
    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 500 if database operation fails
    """
    
    query = select(CommissionConfig).where(CommissionConfig.id == config_id)
    result = await deps.db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commission configuration not found"
        )
    
    return CommissionConfigResponse.model_validate(config)


@router.put(
    "/{config_id}",
    response_model=CommissionConfigResponse,
    summary="Update Commission Configuration",
    description="""
    Update an existing commission configuration with new rates, rules, or settings.
    
    **Business Context:**
    Commission configurations may need updates for market changes, partner negotiations,
    or business strategy adjustments. This endpoint allows administrators to modify
    existing configurations while maintaining audit trails.
    
    **Important Notes:**
    - Setting is_default=true will automatically unset other default configurations
    - Changes affect future commission calculations, not historical ones
    - Active configurations being used by partners can be safely updated
    """,
    responses={
        200: {
            "description": "Commission configuration updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Updated Partner Commission",
                        "commission_rate": 0.18,
                        "is_active": True,
                        "updated_at": "2024-01-16T14:20:00Z"
                    }
                }
            }
        },
        404: {"description": "Commission configuration not found"},
        400: {"description": "Invalid update data provided"},
        500: {"description": "Internal server error"}
    },
    tags=["Commission Configuration"],
    operation_id="updateCommissionConfig"
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Financial data updates - strict limits
@standard_exception_handler
async def update_commission_config(
    config_data: CommissionConfigUpdate,
    config_id: UUID = Path(
        ...,
        description="Unique identifier of the commission configuration to update",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> CommissionConfigResponse:
    """
    Update an existing commission configuration with new rates, rules, or settings.
    
    Args:
        config_id: The UUID of the commission configuration to update
        config_data: Updated commission configuration data (only modified fields)
        deps: Standard dependencies including database session and authentication
        
    Returns:
        CommissionConfigResponse: The updated commission configuration
        
    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 400 if update data is invalid
        HTTPException: 500 if database operation fails
    """
    
    query = select(CommissionConfig).where(CommissionConfig.id == config_id)
    result = await deps.db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commission configuration not found"
        )
    
    # If setting as default, unset other defaults
    update_data = config_data.model_dump(exclude_unset=True)
    if update_data.get("is_default"):
        await _unset_default_configs(deps.db, exclude_id=config_id)
    
    # Update fields
    for field, value in update_data.items():
        setattr(config, field, value)
    
    await deps.db.commit()
    await deps.db.refresh(config)
    
    return CommissionConfigResponse.model_validate(config)


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Commission Configuration",
    description="""
    Permanently delete a commission configuration from the system.
    
    **Business Context:**
    This operation permanently removes a commission configuration and cannot be undone.
    Use with caution as it may affect reporting and audit trails.
    
    **Important Notes:**
    - Cannot delete configurations currently assigned to active partners
    - Cannot delete the default configuration if it's the only one
    - Consider deactivating instead of deleting for audit purposes
    """,
    responses={
        204: {"description": "Commission configuration deleted successfully"},
        404: {"description": "Commission configuration not found"},
        409: {"description": "Cannot delete configuration in use"},
        500: {"description": "Internal server error"}
    },
    tags=["Commission Configuration"],
    operation_id="deleteCommissionConfig"
)
@rate_limit_strict(max_requests=5, time_window_seconds=60)  # Delete operations - very strict limits
@standard_exception_handler
async def delete_commission_config(
    config_id: UUID = Path(
        ...,
        description="Unique identifier of the commission configuration to delete",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """
    Permanently delete a commission configuration from the system.
    
    Args:
        config_id: The UUID of the commission configuration to delete
        deps: Standard dependencies including database session and authentication
        
    Returns:
        None: Returns 204 No Content on successful deletion
        
    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 409 if configuration is in use and cannot be deleted
        HTTPException: 500 if database operation fails
    """
    
    query = select(CommissionConfig).where(CommissionConfig.id == config_id)
    result = await deps.db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commission configuration not found"
        )
    
    await deps.db.delete(config)
    await deps.db.commit()


# === REVENUE MODEL ENDPOINTS ===

@router.post(
    "/revenue-models",
    response_model=RevenueModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Revenue Model",
    description="""
    Create a new revenue model that defines how commissions are calculated.
    
    **Business Context:**
    Revenue models define the mathematical rules for commission calculations,
    including percentage rates, fixed fees, tiered structures, and bonus criteria.
    Each model can be linked to commission configurations.
    """,
    responses={
        201: {
            "description": "Revenue model created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "456e7890-e89b-12d3-a456-426614174000",
                        "name": "Tiered Percentage Model",
                        "model_type": "tiered_percentage",
                        "base_rate": 0.10,
                        "is_active": True
                    }
                }
            }
        },
        400: {"description": "Invalid revenue model data"},
        500: {"description": "Internal server error"}
    },
    tags=["Revenue Models"],
    operation_id="createRevenueModel"
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Financial model creation - strict limits
@standard_exception_handler
async def create_revenue_model(
    model_data: RevenueModelCreate,
    deps: StandardDependencies = Depends(get_standard_deps)
) -> RevenueModelResponse:
    """
    Create a new revenue model that defines how commissions are calculated.
    
    Args:
        model_data: Revenue model details including calculation rules and rates
        deps: Standard dependencies including database session and authentication
        
    Returns:
        RevenueModelResponse: The created revenue model with generated ID
        
    Raises:
        HTTPException: 400 if model data is invalid
        HTTPException: 500 if database operation fails
    """
    
    model = RevenueModel(**model_data.model_dump())
    deps.db.add(model)
    await deps.db.commit()
    await deps.db.refresh(model)
    
    return RevenueModelResponse.model_validate(model)


@router.get(
    "/revenue-models",
    response_model=List[RevenueModelResponse],
    summary="List Revenue Models",
    description="""
    Retrieve a paginated list of revenue models with optional filtering.
    
    **Business Context:**
    Revenue models define calculation logic for commissions. This endpoint allows
    administrators to browse available models, compare calculation methods, and
    select appropriate models for commission configurations.
    """,
    responses={
        200: {
            "description": "List of revenue models retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "456e7890-e89b-12d3-a456-426614174000",
                            "name": "Standard Percentage Model",
                            "model_type": "percentage",
                            "base_rate": 0.15,
                            "service_type": "software",
                            "territory": "US",
                            "is_active": True
                        }
                    ]
                }
            }
        },
        500: {"description": "Internal server error"}
    },
    tags=["Revenue Models"],
    operation_id="listRevenueModels"
)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Read operations - normal user limits
@standard_exception_handler
async def list_revenue_models(
    deps: StandardDependencies = Depends(get_standard_deps),
    service_type: Optional[str] = Query(
        None,
        description="Filter by service type (e.g., 'software', 'hardware', 'consulting')",
        example="software"
    ),
    territory: Optional[str] = Query(
        None,
        description="Filter by territory/region code (e.g., 'US', 'EU', 'APAC')",
        example="US"
    ),
    is_active: Optional[bool] = Query(
        None,
        description="Filter models by active status. True for active only, False for inactive only",
        example=True
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number for pagination (starts from 1)",
        example=1
    ),
    size: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of items per page (maximum 100)",
        example=20
    )
) -> List[RevenueModelResponse]:
    """
    Retrieve a paginated list of revenue models with optional filtering.
    
    Args:
        deps: Standard dependencies including database session and authentication
        service_type: Optional filter for specific service types
        territory: Optional filter for specific territories
        is_active: Optional filter for active status
        page: Page number for pagination (starts from 1)
        size: Number of items per page (1-100)
        
    Returns:
        List[RevenueModelResponse]: Paginated list of revenue models
        
    Raises:
        HTTPException: 500 if database operation fails
    """
    
    query = select(RevenueModel)
    
    # Apply filters
    if service_type:
        query = query.where(RevenueModel.service_type == service_type)
    if territory:
        query = query.where(RevenueModel.territory == territory)
    if is_active is not None:
        query = query.where(RevenueModel.is_active == is_active)
    
    # Pagination
    query = query.order_by(RevenueModel.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    
    result = await deps.db.execute(query)
    models = result.scalars().all()
    
    return [RevenueModelResponse.model_validate(model) for model in models]


@router.get(
    "/revenue-models/{model_id}",
    response_model=RevenueModelResponse,
    summary="Get Revenue Model by ID",
    description="""
    Retrieve a specific revenue model by its unique identifier.
    
    **Business Context:**
    Revenue models contain the calculation logic for commissions. This endpoint
    provides detailed information about calculation rules, rates, and tiers.
    """,
    responses={
        200: {
            "description": "Revenue model retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "456e7890-e89b-12d3-a456-426614174000",
                        "name": "Enterprise Tiered Model",
                        "model_type": "tiered_percentage",
                        "tiers": [
                            {"min_amount": 0, "max_amount": 5000, "rate": 0.10},
                            {"min_amount": 5000, "max_amount": None, "rate": 0.15}
                        ],
                        "is_active": True
                    }
                }
            }
        },
        404: {"description": "Revenue model not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Revenue Models"],
    operation_id="getRevenueModel"
)
@rate_limit_user(max_requests=100, time_window_seconds=60)  # Read operations - normal user limits
@standard_exception_handler
async def get_revenue_model(
    model_id: UUID = Path(
        ...,
        description="Unique identifier of the revenue model",
        example="456e7890-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> RevenueModelResponse:
    """
    Retrieve a specific revenue model by its unique identifier.
    
    Args:
        model_id: The UUID of the revenue model to retrieve
        deps: Standard dependencies including database session and authentication
        
    Returns:
        RevenueModelResponse: The requested revenue model
        
    Raises:
        HTTPException: 404 if model not found
        HTTPException: 500 if database operation fails
    """
    
    query = select(RevenueModel).where(RevenueModel.id == model_id)
    result = await deps.db.execute(query)
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revenue model not found"
        )
    
    return RevenueModelResponse.model_validate(model)


@router.put(
    "/revenue-models/{model_id}",
    response_model=RevenueModelResponse,
    summary="Update Revenue Model",
    description="""
    Update an existing revenue model with new calculation rules or rates.
    
    **Business Context:**
    Revenue models may need updates for business strategy changes or market adjustments.
    Changes affect future commission calculations for configurations using this model.
    """,
    responses={
        200: {
            "description": "Revenue model updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "456e7890-e89b-12d3-a456-426614174000",
                        "name": "Updated Tiered Model",
                        "base_rate": 0.12,
                        "updated_at": "2024-01-16T14:20:00Z"
                    }
                }
            }
        },
        404: {"description": "Revenue model not found"},
        400: {"description": "Invalid update data provided"},
        500: {"description": "Internal server error"}
    },
    tags=["Revenue Models"],
    operation_id="updateRevenueModel"
)
@rate_limit_strict(max_requests=10, time_window_seconds=60)  # Financial model updates - strict limits
@standard_exception_handler
async def update_revenue_model(
    model_data: RevenueModelUpdate,
    model_id: UUID = Path(
        ...,
        description="Unique identifier of the revenue model to update",
        example="456e7890-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
) -> RevenueModelResponse:
    """
    Update an existing revenue model with new calculation rules or rates.
    
    Args:
        model_id: The UUID of the revenue model to update
        model_data: Updated revenue model data (only modified fields)
        deps: Standard dependencies including database session and authentication
        
    Returns:
        RevenueModelResponse: The updated revenue model
        
    Raises:
        HTTPException: 404 if model not found
        HTTPException: 400 if update data is invalid
        HTTPException: 500 if database operation fails
    """
    
    query = select(RevenueModel).where(RevenueModel.id == model_id)
    result = await deps.db.execute(query)
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revenue model not found"
        )
    
    # Update fields
    update_data = model_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)
    
    await deps.db.commit()
    await deps.db.refresh(model)
    
    return RevenueModelResponse.model_validate(model)


@router.delete(
    "/revenue-models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Revenue Model",
    description="""
    Permanently delete a revenue model from the system.
    
    **Business Context:**
    This operation permanently removes a revenue model. Use with caution as it may
    affect commission configurations and historical calculations.
    
    **Important Notes:**
    - Cannot delete models currently used by active commission configurations
    - Consider deactivating instead of deleting for audit purposes
    """,
    responses={
        204: {"description": "Revenue model deleted successfully"},
        404: {"description": "Revenue model not found"},
        409: {"description": "Cannot delete model in use"},
        500: {"description": "Internal server error"}
    },
    tags=["Revenue Models"],
    operation_id="deleteRevenueModel"
)
@rate_limit_strict(max_requests=5, time_window_seconds=60)  # Delete operations - very strict limits
@standard_exception_handler
async def delete_revenue_model(
    model_id: UUID = Path(
        ...,
        description="Unique identifier of the revenue model to delete",
        example="456e7890-e89b-12d3-a456-426614174000"
    ),
    deps: StandardDependencies = Depends(get_standard_deps)
):
    """
    Permanently delete a revenue model from the system.
    
    Args:
        model_id: The UUID of the revenue model to delete
        deps: Standard dependencies including database session and authentication
        
    Returns:
        None: Returns 204 No Content on successful deletion
        
    Raises:
        HTTPException: 404 if model not found
        HTTPException: 409 if model is in use and cannot be deleted
        HTTPException: 500 if database operation fails
    """
    
    query = select(RevenueModel).where(RevenueModel.id == model_id)
    result = await deps.db.execute(query)
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revenue model not found"
        )
    
    await deps.db.delete(model)
    await deps.db.commit()


# === HELPER FUNCTIONS ===

async def _unset_default_configs(db: AsyncSession, exclude_id: Optional[UUID] = None):
    """Unset all default configurations except the specified one."""
    query = select(CommissionConfig).where(CommissionConfig.is_default == True)
    
    if exclude_id:
        query = query.where(CommissionConfig.id != exclude_id)
    
    result = await db.execute(query)
    configs = result.scalars().all()
    
    for config in configs:
        config.is_default = False
    
    await db.commit()