"""
FastAPI router for ISP reseller management.
Provides REST endpoints for reseller operations using shared reseller service.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from dotmac_shared.api.exception_handlers import (
    Depends,
    HTTPException,
    Query,
    standard_exception_handler,
)
from dotmac_shared.api.router_factory import RouterFactory

from . import schemas
from .shared_reseller_integration import ISPResellerService, get_isp_reseller_service

logger = logging.getLogger(__name__)

# REPLACED: Direct APIRouter with RouterFactory
router = RouterFactory.create_crud_router(
    service_class=ISPResellerService,
    create_schema=schemas.ResellerCreate,
    update_schema=schemas.ResellerUpdate,
    response_schema=schemas.ResellerResponse,
    prefix="/api/v1/resellers",
    tags=["resellers"],
    enable_search=True,
    enable_bulk_operations=True,
)


async def get_reseller_service() -> ISPResellerService:
    """Get reseller service dependency."""
    # In a real implementation, tenant_id would come from authentication context
    tenant_id = "default"  # Placeholder
    service = get_isp_reseller_service(tenant_id)
    if not service._initialized:
        await service.initialize()
    return service


@router.post(
    "/",
    response_model=schemas.ResellerResponse,
    summary="Create new reseller",
    description="Create a new reseller using shared reseller service",
)
@standard_exception_handler
async def create_reseller(
    reseller_data: schemas.ResellerCreate,
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Create a new reseller."""
    try:
        result = await reseller_service.create_reseller(reseller_data.dict())

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create reseller")
        return schemas.ResellerResponse(**result)

    except Exception as e:
        logger.error(f"Error creating reseller: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/{reseller_id}",
    response_model=schemas.ResellerResponse,
    summary="Get reseller by ID",
    description="Retrieve reseller information by ID",
)
async def get_reseller(
    reseller_id: str,
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Get reseller by ID."""
    try:
        result = await reseller_service.get_reseller(reseller_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"Reseller {reseller_id} not found"
            )
        return schemas.ResellerResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reseller {reseller_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/",
    response_model=schemas.ResellerListResponse,
    summary="List resellers",
    description="List resellers with optional filtering and pagination",
)
async def list_resellers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    reseller_type: Optional[schemas.ResellerTypeEnum] = Query(None),
    reseller_tier: Optional[schemas.ResellerTierEnum] = Query(None),
    territory: Optional[str] = Query(None),
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """List resellers with filtering and pagination."""
    try:
        filters = {}
        if reseller_type:
            filters["reseller_type"] = reseller_type.value
        if reseller_tier:
            filters["reseller_tier"] = reseller_tier.value
        if territory:
            filters["territory"] = territory

        resellers = await reseller_service.list_resellers(
            limit=deps.pagination.size,
            offset=offset,
            filters=filters if filters else None,
        )
        return schemas.ResellerListResponse(
            resellers=[schemas.ResellerResponse(**reseller) for reseller in resellers],
            total=len(resellers),  # In real implementation, get actual count
            limit=deps.pagination.size,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing resellers: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/{reseller_id}/opportunities",
    response_model=schemas.ResellerOpportunityResponse,
    summary="Assign opportunity to reseller",
    description="Assign an opportunity to a reseller for management",
)
async def create_reseller_opportunity(
    reseller_id: str,
    opportunity_data: schemas.ResellerOpportunityCreate,
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Assign opportunity to reseller."""
    try:
        # Verify reseller exists
        reseller = await reseller_service.get_reseller(reseller_id)
        if not reseller:
            raise HTTPException(
                status_code=404, detail=f"Reseller {reseller_id} not found"
            )
        result = await reseller_service.create_reseller_opportunity(
            reseller_id=reseller_id, opportunity_data=opportunity_data.dict()
        )

        if not result:
            raise HTTPException(
                status_code=500, detail="Failed to assign opportunity to reseller"
            )
        return schemas.ResellerOpportunityResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reseller opportunity: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/commissions/calculate",
    response_model=schemas.CommissionCalculationResponse,
    summary="Calculate commission",
    description="Calculate commission for a reseller sale",
)
async def calculate_commission(
    calculation_data: schemas.CommissionCalculation,
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Calculate commission for a reseller sale."""
    try:
        result = await reseller_service.calculate_commission(
            reseller_id=calculation_data.reseller_id,
            sale_amount=calculation_data.sale_amount,
            commission_override=calculation_data.commission_override,
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Reseller {calculation_data.reseller_id} not found",
            )
        return schemas.CommissionCalculationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating commission: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/commissions",
    response_model=schemas.CommissionResponse,
    summary="Record commission",
    description="Record a commission payment for a reseller",
)
async def record_commission(
    commission_data: schemas.CommissionRecord,
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Record commission for a reseller."""
    try:
        result = await reseller_service.record_commission(
            reseller_id=commission_data.reseller_id,
            commission_data=commission_data.dict(),
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to record commission")
        return schemas.CommissionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording commission: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/{reseller_id}/performance",
    response_model=schemas.ResellerPerformanceResponse,
    summary="Get reseller performance",
    description="Get performance metrics for a reseller",
)
async def get_reseller_performance(
    reseller_id: str,
    start_date: Optional[str] = Query(None, description="Start date in ISO format"),
    end_date: Optional[str] = Query(None, description="End date in ISO format"),
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Get reseller performance metrics."""
    try:
        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                )
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                )
        result = await reseller_service.get_reseller_performance(
            reseller_id=reseller_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Performance data not found for reseller {reseller_id}",
            )
        return schemas.ResellerPerformanceResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reseller performance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/{reseller_id}/territories/{territory}",
    summary="Assign territory",
    description="Assign a territory to a reseller",
)
async def assign_territory(
    reseller_id: str,
    territory: str,
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Assign territory to reseller."""
    try:
        success = await reseller_service.assign_territory(
            reseller_id=reseller_id, territory=territory
        )
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to assign territory {territory} to reseller {reseller_id}",
            )
        return JSONResponse(
            content={
                "message": f"Territory {territory} assigned to reseller {reseller_id}",
                "reseller_id": reseller_id,
                "territory": territory,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning territory: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/health",
    response_model=schemas.ResellerHealthResponse,
    summary="Health check",
    description="Get health status of reseller service",
)
async def health_check(
    reseller_service: ISPResellerService = Depends(get_reseller_service),
):
    """Health check for reseller service."""
    try:
        health_data = await reseller_service.health_check()
        return schemas.ResellerHealthResponse(**health_data)

    except Exception as e:
        logger.error(f"Error getting reseller service health: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
