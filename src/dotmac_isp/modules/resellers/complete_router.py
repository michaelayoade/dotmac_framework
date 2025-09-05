"""
Complete Reseller API Router - DRY Migration
Comprehensive endpoints for reseller lifecycle management using RouterFactory patterns.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from fastapi import Body, Depends, Query
from pydantic import BaseModel, EmailStr, Field

from dotmac.application import RouterFactory, standard_exception_handler

from .schemas import (
    ResellerApplicationCreateSchema,
    ResellerApplicationResponseSchema,
    ResellerCreateSchema,
    ResellerResponseSchema,
    ResellerUpdateSchema,
)
from .services_complete import (
    ResellerApplicationService,
    ResellerCustomerService,
    ResellerOnboardingService,
    ResellerService,
)

# === Additional Request/Response Schemas ===


class CustomerCreateRequest(BaseModel):
    """Request schema for creating customers under reseller."""

    name: str = Field(..., description="Customer name")
    email: EmailStr = Field(..., description="Customer email")
    service_plan: str = Field(..., description="Selected service plan")
    billing_address: dict[str, Any] | None = Field(None, description="Billing address")


class CommissionCalculationRequest(BaseModel):
    """Request schema for commission calculation."""

    period_start: datetime = Field(..., description="Start date for commission period")
    period_end: datetime = Field(..., description="End date for commission period")
    include_pending: bool = Field(False, description="Include pending commissions")


# === Main Reseller CRUD Router ===

reseller_router = RouterFactory.create_crud_router(
    service_class=ResellerService,
    create_schema=ResellerCreateSchema,
    update_schema=ResellerUpdateSchema,
    response_schema=ResellerResponseSchema,
    prefix="/resellers",
    tags=["resellers"],
    enable_search=True,
    enable_bulk_operations=True,
)


# === Reseller Application Management ===

application_router = RouterFactory.create_crud_router(
    service_class=ResellerApplicationService,
    create_schema=ResellerApplicationCreateSchema,
    update_schema=dict,  # Simple dict for updates
    response_schema=ResellerApplicationResponseSchema,
    prefix="/reseller-applications",
    tags=["reseller-applications"],
    enable_search=True,
    enable_bulk_operations=False,
)


@application_router.post(
    "/{application_id}/approve", response_model=ResellerApplicationResponseSchema
)
@standard_exception_handler
async def approve_application(
    application_id: UUID,
    approval_notes: str = Body(..., embed=True, description="Approval notes"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> ResellerApplicationResponseSchema:
    """Approve a reseller application."""
    service = ResellerApplicationService(deps.db, deps.tenant_id)
    return await service.approve_application(
        application_id, deps.user_id, approval_notes
    )


@application_router.post(
    "/{application_id}/reject", response_model=ResellerApplicationResponseSchema
)
@standard_exception_handler
async def reject_application(
    application_id: UUID,
    rejection_reason: str = Body(..., embed=True, description="Rejection reason"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> ResellerApplicationResponseSchema:
    """Reject a reseller application."""
    service = ResellerApplicationService(deps.db, deps.tenant_id)
    return await service.reject_application(
        application_id, deps.user_id, rejection_reason
    )


# === Reseller Customer Management ===


@reseller_router.get("/{reseller_id}/customers", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_reseller_customers(
    reseller_id: UUID,
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """Get all customers for a specific reseller."""
    service = ResellerCustomerService(deps.db, deps.tenant_id)
    customers, total = await service.get_customers_by_reseller(
        reseller_id,
        offset=deps.pagination.offset,
        limit=deps.pagination.size,
    )
    return customers


@reseller_router.post("/{reseller_id}/customers", response_model=dict[str, Any])
@standard_exception_handler
async def create_reseller_customer(
    reseller_id: UUID,
    customer_data: CustomerCreateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new customer under a reseller."""
    service = ResellerCustomerService(deps.db, deps.tenant_id)
    return await service.create_customer(
        reseller_id,
        customer_data.model_dump(),
        deps.user_id,
    )


@reseller_router.get(
    "/{reseller_id}/customers/{customer_id}", response_model=dict[str, Any]
)
@standard_exception_handler
async def get_reseller_customer(
    reseller_id: UUID,
    customer_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get specific customer details."""
    service = ResellerCustomerService(deps.db, deps.tenant_id)
    return await service.get_customer(reseller_id, customer_id)


# === Commission Management ===


@reseller_router.get("/{reseller_id}/commissions", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_reseller_commissions(
    reseller_id: UUID,
    month: int | None = Query(None, ge=1, le=12, description="Month filter"),
    year: int | None = Query(None, ge=2020, description="Year filter"),
    status: str | None = Query(None, description="Commission status filter"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """Get commission history for a reseller."""
    service = ResellerService(deps.db, deps.tenant_id)
    return await service.get_commission_history(
        reseller_id,
        month=month,
        year=year,
        status=status,
        offset=deps.pagination.offset,
        limit=deps.pagination.size,
    )


@reseller_router.post(
    "/{reseller_id}/commissions/calculate", response_model=dict[str, Any]
)
@standard_exception_handler
async def calculate_commissions(
    reseller_id: UUID,
    calculation_request: CommissionCalculationRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Calculate commissions for a specific period."""
    service = ResellerService(deps.db, deps.tenant_id)
    return await service.calculate_commissions(
        reseller_id,
        calculation_request.period_start,
        calculation_request.period_end,
        calculation_request.include_pending,
    )


# === Reseller Analytics ===


@reseller_router.get("/{reseller_id}/analytics", response_model=dict[str, Any])
@standard_exception_handler
async def get_reseller_analytics(
    reseller_id: UUID,
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get comprehensive analytics for a reseller."""
    service = ResellerService(deps.db, deps.tenant_id)
    return await service.get_reseller_analytics(reseller_id, period_days)


@reseller_router.get("/{reseller_id}/performance", response_model=dict[str, Any])
@standard_exception_handler
async def get_reseller_performance(
    reseller_id: UUID,
    compare_period: bool = Query(False, description="Compare with previous period"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get performance metrics for a reseller."""
    service = ResellerService(deps.db, deps.tenant_id)
    return await service.get_performance_metrics(reseller_id, compare_period)


# === Onboarding Workflows ===

onboarding_router = RouterFactory.create_standard_router(
    prefix="/reseller-onboarding",
    tags=["reseller-onboarding"],
)


@onboarding_router.post("/initiate", response_model=dict[str, Any])
@standard_exception_handler
async def initiate_onboarding(
    application_id: UUID = Body(
        ..., embed=True, description="Application ID to onboard"
    ),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Initiate onboarding process for approved application."""
    service = ResellerOnboardingService(deps.db, deps.tenant_id)
    return await service.initiate_onboarding(application_id, deps.user_id)


@onboarding_router.get("/{onboarding_id}/status", response_model=dict[str, Any])
@standard_exception_handler
async def get_onboarding_status(
    onboarding_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get current onboarding status."""
    service = ResellerOnboardingService(deps.db, deps.tenant_id)
    return await service.get_onboarding_status(onboarding_id)


@onboarding_router.post("/{onboarding_id}/complete-step", response_model=dict[str, Any])
@standard_exception_handler
async def complete_onboarding_step(
    onboarding_id: UUID,
    step_name: str = Body(..., embed=True, description="Step name to complete"),
    step_data: dict[str, Any] = Body(
        ..., embed=True, description="Step completion data"
    ),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Complete a specific onboarding step."""
    service = ResellerOnboardingService(deps.db, deps.tenant_id)
    return await service.complete_step(
        onboarding_id, step_name, step_data, deps.user_id
    )


# === Include sub-routers ===
reseller_router.include_router(application_router)
reseller_router.include_router(onboarding_router)

# Export main router
__all__ = ["reseller_router"]
