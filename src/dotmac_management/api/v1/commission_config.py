"""
Commission configuration API for management portal.
Allows admins to configure all reseller commission structures.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from dotmac_shared.api.dependencies import StandardDeps
from dotmac_shared.api.exception_handlers import standard_exception_handler

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


router = APIRouter(prefix="/commission-config", tags=["Commission Configuration"])


# === COMMISSION CONFIG ENDPOINTS ===

@router.post("/", response_model=CommissionConfigResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def create_commission_config(
    config_data: CommissionConfigCreate,
    deps: StandardDeps,
) -> CommissionConfigResponse:
    """Create new commission configuration."""
    
    # If setting as default, unset other defaults
    if config_data.is_default:
        await _unset_default_configs(deps.db)
    
    config = CommissionConfig(**config_data.model_dump())
    deps.db.add(config)
    await deps.db.commit()
    await deps.db.refresh(config)
    
    return CommissionConfigResponse.model_validate(config)


@router.get("/", response_model=List[CommissionConfigResponse])
@standard_exception_handler
async def list_commission_configs(
    deps: StandardDeps,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    reseller_type: Optional[str] = Query(None, description="Filter by reseller type"),
    territory: Optional[str] = Query(None, description="Filter by territory"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> List[CommissionConfigResponse]:
    """List commission configurations with filtering."""
    
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


@router.get("/default", response_model=CommissionConfigResponse)
@standard_exception_handler
async def get_default_commission_config(deps: StandardDeps) -> CommissionConfigResponse:
    """Get the default commission configuration."""
    
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


@router.get("/{config_id}", response_model=CommissionConfigResponse)
@standard_exception_handler
async def get_commission_config(
    config_id: UUID,
    deps: StandardDeps
) -> CommissionConfigResponse:
    """Get commission configuration by ID."""
    
    query = select(CommissionConfig).where(CommissionConfig.id == config_id)
    result = await deps.db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commission configuration not found"
        )
    
    return CommissionConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=CommissionConfigResponse)
@standard_exception_handler
async def update_commission_config(
    config_id: UUID,
    config_data: CommissionConfigUpdate,
    deps: StandardDeps
) -> CommissionConfigResponse:
    """Update commission configuration."""
    
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


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
@standard_exception_handler
async def delete_commission_config(
    config_id: UUID,
    deps: StandardDeps
):
    """Delete commission configuration."""
    
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

@router.post("/revenue-models", response_model=RevenueModelResponse, status_code=status.HTTP_201_CREATED)
@standard_exception_handler
async def create_revenue_model(
    model_data: RevenueModelCreate,
    deps: StandardDeps
) -> RevenueModelResponse:
    """Create new revenue model."""
    
    model = RevenueModel(**model_data.model_dump())
    deps.db.add(model)
    await deps.db.commit()
    await deps.db.refresh(model)
    
    return RevenueModelResponse.model_validate(model)


@router.get("/revenue-models", response_model=List[RevenueModelResponse])
@standard_exception_handler
async def list_revenue_models(
    deps: StandardDeps,
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    territory: Optional[str] = Query(None, description="Filter by territory"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> List[RevenueModelResponse]:
    """List revenue models with filtering."""
    
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


@router.get("/revenue-models/{model_id}", response_model=RevenueModelResponse)
@standard_exception_handler
async def get_revenue_model(
    model_id: UUID,
    deps: StandardDeps
) -> RevenueModelResponse:
    """Get revenue model by ID."""
    
    query = select(RevenueModel).where(RevenueModel.id == model_id)
    result = await deps.db.execute(query)
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revenue model not found"
        )
    
    return RevenueModelResponse.model_validate(model)


@router.put("/revenue-models/{model_id}", response_model=RevenueModelResponse)
@standard_exception_handler
async def update_revenue_model(
    model_id: UUID,
    model_data: RevenueModelUpdate,
    deps: StandardDeps
) -> RevenueModelResponse:
    """Update revenue model."""
    
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


@router.delete("/revenue-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
@standard_exception_handler
async def delete_revenue_model(
    model_id: UUID,
    deps: StandardDeps
):
    """Delete revenue model."""
    
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