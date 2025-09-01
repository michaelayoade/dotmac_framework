"""
Reseller API router for ISP Framework

Provides REST APIs for reseller management leveraging shared patterns.
Includes website signup, reseller management, and customer assignment.
"""

from datetime import date
from typing import Dict, List, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from dotmac_shared.api.dependencies import StandardDeps, PaginatedDeps
from dotmac_shared.api.exception_handlers import standard_exception_handler

from .models import ISPReseller, ResellerApplication
from .schemas import (
    ResellerApplicationCreate,
    ResellerApplicationResponse,
    ResellerResponse
)
from .services import (
    ResellerApplicationService,
    ResellerService,
    ResellerCustomerService
)

# Create router
reseller_router = APIRouter(prefix="/resellers", tags=["Resellers"])

# === WEBSITE SIGNUP FLOW ===

@reseller_router.post(
    "/applications", 
    response_model=ResellerApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit reseller application from website"
)
@standard_exception_handler
async def submit_reseller_application(
    application: ResellerApplicationCreate,
    deps: StandardDeps
) -> ResellerApplicationResponse:
    """Submit new reseller application from website signup."""
    
    service = ResellerApplicationService(deps.db, deps.tenant_id)
    created_application = await service.create_application(application)
    
    return ResellerApplicationResponse.from_orm(created_application)


@reseller_router.get(
    "/applications",
    response_model=List[ResellerApplicationResponse],
    summary="List reseller applications for admin review"
)
@standard_exception_handler  
async def list_reseller_applications(deps: PaginatedDeps) -> List[ResellerApplicationResponse]:
    """List reseller applications for admin review."""
    
    service = ResellerApplicationService(deps.db, deps.tenant_id)
    applications = await service.get_pending_applications()
    
    return [ResellerApplicationResponse.from_orm(app) for app in applications]


class ApplicationApprovalRequest(BaseModel):
    notes: str = None


@reseller_router.post(
    "/applications/{application_id}/approve",
    summary="Approve reseller application"
)
@standard_exception_handler
async def approve_reseller_application(
    application_id: str,
    approval_request: ApplicationApprovalRequest,
    deps: StandardDeps
) -> Dict[str, Any]:
    """Approve reseller application and create reseller account."""
    
    service = ResellerApplicationService(deps.db, deps.tenant_id)
    result = await service.approve_application(
        application_id=application_id,
        reviewer_id=str(deps.user_id),
        notes=approval_request.notes
    )
    
    return {
        "message": "Application approved successfully",
        "reseller_id": result["reseller"].reseller_id
    }


# === RESELLER MANAGEMENT ===

@reseller_router.get(
    "/",
    response_model=List[ResellerResponse],
    summary="List active resellers"
)
@standard_exception_handler
async def list_resellers(deps: PaginatedDeps) -> List[ResellerResponse]:
    """List active resellers."""
    
    service = ResellerService(deps.db, deps.tenant_id)
    resellers = service.list(limit=deps.pagination.size, offset=deps.pagination.offset)
    
    return [ResellerResponse.from_orm(reseller) for reseller in resellers]


@reseller_router.get(
    "/{reseller_id}/dashboard",
    summary="Get reseller dashboard data"
)
@standard_exception_handler
async def get_reseller_dashboard(
    reseller_id: UUID,
    deps: StandardDeps
) -> Dict[str, Any]:
    """Get comprehensive dashboard data for reseller."""
    
    service = ResellerService(deps.db, deps.tenant_id)
    return await service.get_reseller_dashboard(reseller_id)


# Export router
__all__ = ["reseller_router"]