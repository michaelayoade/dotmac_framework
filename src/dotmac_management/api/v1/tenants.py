"""
Tenant Management API

Provides comprehensive tenant lifecycle management including:
- Tenant signup and onboarding with validation
- Automated provisioning and infrastructure setup
- Multi-region deployment and scaling
- Tenant status monitoring and health checks
- Deprovisioning and cleanup workflows

Supports multi-tenant SaaS architecture with isolated tenant environments,
configurable plans, and automated resource allocation.
"""

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from dotmac.application import standard_exception_handler
from dotmac.application.dependencies.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from dotmac.core.schemas.base_schemas import PaginatedResponseSchema
from dotmac.platform.observability.logging import get_logger
from dotmac_management.models.tenant import CustomerTenant, TenantPlan, TenantStatus
from dotmac_management.use_cases import (
    ProvisionTenantInput,
    ProvisionTenantUseCase,
)
from dotmac_management.use_cases.base import UseCaseContext
from dotmac_shared.api.response import APIResponse
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

logger = get_logger(__name__)
router = APIRouter(
    prefix="/tenants",
    tags=["Tenant Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)


class TenantSignupRequest(BaseModel):
    """Tenant signup request schema"""

    # Company information
    company_name: str
    subdomain: str

    # Admin user information
    admin_name: str
    admin_email: EmailStr

    # Service configuration
    plan: TenantPlan = TenantPlan.STARTER
    region: str = "us-east-1"

    # Optional
    description: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    payment_method_id: Optional[str] = None

    # Features
    enabled_features: list[str] = []

    # Marketing/source tracking
    source: Optional[str] = None
    referrer: Optional[str] = None

    @field_validator("company_name")
    def validate_company_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Company name must be at least 2 characters")
        return v.strip()

    @field_validator("subdomain")
    def validate_subdomain(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Subdomain must be at least 3 characters")

        # Check format
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError("Invalid subdomain format")

        # Reserved subdomains
        reserved = {"api", "www", "admin", "app", "mail", "support", "help"}
        if v.lower() in reserved:
            raise ValueError("Subdomain is reserved")

        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_name": "Acme Corp",
                "subdomain": "acme-corp",
                "admin_name": "John Doe",
                "admin_email": "john@acme.com",
                "plan": "starter",
                "region": "us-east-1",
            }
        }
    )


class TenantResponse(BaseModel):
    """Tenant response schema"""

    id: UUID
    company_name: str
    subdomain: str
    status: TenantStatus
    plan: TenantPlan
    region: str
    created_at: datetime
    updated_at: datetime

    # Optional fields
    description: Optional[str] = None
    admin_email: Optional[EmailStr] = None
    billing_email: Optional[EmailStr] = None

    model_config = ConfigDict(from_attributes=True)


class TenantUpdateRequest(BaseModel):
    """Tenant update request schema"""

    company_name: Optional[str] = None
    description: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    enabled_features: Optional[list[str]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_name": "Updated Corp Name",
                "description": "Updated description",
                "billing_email": "billing@company.com",
            }
        }
    )


# ============================================================================
# Tenant Registration & Onboarding
# ============================================================================


@router.post(
    "/signup",
    response_model=APIResponse[TenantResponse],
    status_code=201,
    summary="Register new tenant",
    description="Create and provision a new tenant with automated infrastructure setup",
)
@standard_exception_handler
async def signup_tenant(
    request: TenantSignupRequest,
    background_tasks: BackgroundTasks,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[TenantResponse]:
    """
    Register a new tenant with comprehensive validation and automated provisioning.
    """
    # Create provisioning use case
    context = UseCaseContext(
        db=deps.db,
        current_user=deps.user,
        tenant_id=None,  # New tenant
    )

    use_case = ProvisionTenantUseCase(context)

    # Provision tenant
    provision_input = ProvisionTenantInput(
        company_name=request.company_name,
        subdomain=request.subdomain,
        admin_name=request.admin_name,
        admin_email=request.admin_email,
        plan=request.plan,
        region=request.region,
        description=request.description,
        billing_email=request.billing_email,
        enabled_features=request.enabled_features,
        source=request.source,
        referrer=request.referrer,
    )

    tenant = await use_case.execute(provision_input, background_tasks)
    tenant_response = TenantResponse.model_validate(tenant)

    return APIResponse(
        success=True,
        message=f"Tenant '{request.company_name}' created successfully",
        data=tenant_response,
    )


# ============================================================================
# Tenant Querying & Management
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponseSchema[TenantResponse],
    summary="List tenants",
    description="Retrieve paginated list of tenants with filtering options",
)
@standard_exception_handler
async def list_tenants(
    status_filter: Optional[TenantStatus] = Query(None, description="Filter by tenant status"),
    plan_filter: Optional[TenantPlan] = Query(None, description="Filter by subscription plan"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> PaginatedResponseSchema[TenantResponse]:
    """
    Retrieve a paginated list of tenants with optional filtering.
    """
    query = deps.db.query(CustomerTenant)

    # Apply filters
    if status_filter:
        query = query.filter(CustomerTenant.status == status_filter)
    if plan_filter:
        query = query.filter(CustomerTenant.plan == plan_filter)

    # Apply pagination
    total = query.count()
    tenants = query.offset(deps.search_params.offset).limit(deps.search_params.limit).all()

    # Convert to response models
    tenant_responses = [TenantResponse.model_validate(tenant) for tenant in tenants]

    return PaginatedResponseSchema[TenantResponse](
        items=tenant_responses,
        total=total,
        page=deps.search_params.page,
        per_page=deps.search_params.limit,
    )


@router.get(
    "/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    summary="Get tenant details",
    description="Retrieve detailed information for a specific tenant",
)
@standard_exception_handler
async def get_tenant(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[TenantResponse]:
    """Get detailed information for a specific tenant."""
    tenant = deps.db.query(CustomerTenant).filter(CustomerTenant.id == tenant_id).first()

    if not tenant:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Tenant {tenant_id} not found")

    tenant_response = TenantResponse.model_validate(tenant)
    return APIResponse(
        success=True,
        message="Tenant details retrieved successfully",
        data=tenant_response,
    )


@router.put(
    "/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    summary="Update tenant",
    description="Update tenant information and configuration",
)
@standard_exception_handler
async def update_tenant(
    request: TenantUpdateRequest,
    tenant_id: UUID = Path(..., description="Tenant ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[TenantResponse]:
    """Update tenant information and configuration."""
    tenant = deps.db.query(CustomerTenant).filter(CustomerTenant.id == tenant_id).first()

    if not tenant:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Tenant {tenant_id} not found")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)

    tenant.updated_at = datetime.now(timezone.utc)
    deps.db.commit()
    deps.db.refresh(tenant)

    tenant_response = TenantResponse.model_validate(tenant)
    return APIResponse(
        success=True,
        message="Tenant updated successfully",
        data=tenant_response,
    )


@router.delete(
    "/{tenant_id}",
    response_model=APIResponse[dict],
    summary="Delete tenant",
    description="Permanently delete tenant and associated resources",
)
@standard_exception_handler
async def delete_tenant(
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Path(..., description="Tenant ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[dict]:
    """Permanently delete tenant and associated resources."""
    tenant = deps.db.query(CustomerTenant).filter(CustomerTenant.id == tenant_id).first()

    if not tenant:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Tenant {tenant_id} not found")

    # Schedule background cleanup
    background_tasks.add_task(
        "cleanup_tenant_resources",
        tenant_id=tenant_id,
        subdomain=tenant.subdomain,
    )

    # Delete from database
    deps.db.delete(tenant)
    deps.db.commit()

    return APIResponse(
        success=True,
        message="Tenant deleted successfully",
        data={"tenant_id": str(tenant_id)},
    )


# ============================================================================
# Tenant Status Management
# ============================================================================


@router.post(
    "/{tenant_id}/activate",
    response_model=APIResponse[TenantResponse],
    summary="Activate tenant",
    description="Activate a suspended or pending tenant",
)
@standard_exception_handler
async def activate_tenant(
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Path(..., description="Tenant ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[TenantResponse]:
    """Activate a suspended or pending tenant."""
    tenant = deps.db.query(CustomerTenant).filter(CustomerTenant.id == tenant_id).first()

    if not tenant:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Tenant {tenant_id} not found")

    tenant.status = TenantStatus.ACTIVE
    tenant.updated_at = datetime.now(timezone.utc)
    deps.db.commit()

    # Schedule activation tasks
    background_tasks.add_task("activate_tenant_resources", tenant_id=tenant_id)

    tenant_response = TenantResponse.model_validate(tenant)
    return APIResponse(
        success=True,
        message="Tenant activated successfully",
        data=tenant_response,
    )


@router.post(
    "/{tenant_id}/suspend",
    response_model=APIResponse[TenantResponse],
    summary="Suspend tenant",
    description="Suspend an active tenant",
)
@standard_exception_handler
async def suspend_tenant(
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Path(..., description="Tenant ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> APIResponse[TenantResponse]:
    """Suspend an active tenant."""
    tenant = deps.db.query(CustomerTenant).filter(CustomerTenant.id == tenant_id).first()

    if not tenant:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Tenant {tenant_id} not found")

    tenant.status = TenantStatus.SUSPENDED
    tenant.updated_at = datetime.now(timezone.utc)
    deps.db.commit()

    # Schedule suspension tasks
    background_tasks.add_task("suspend_tenant_resources", tenant_id=tenant_id)

    tenant_response = TenantResponse.model_validate(tenant)
    return APIResponse(
        success=True,
        message="Tenant suspended successfully",
        data=tenant_response,
    )
