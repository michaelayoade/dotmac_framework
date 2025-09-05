"""Domain Management API Router for the Management Platform."""

from typing import Optional

from dotmac.application import RouterFactory, rate_limit, rate_limit_strict, standard_exception_handler
from fastapi import Depends, Query

from ...dependencies import get_current_user, get_domain_service
from ...models.domain_management import DomainStatus
from ...schemas.domain_schemas import DomainCreate, DomainListResponse, DomainResponse
from ...services.domain_service import DomainService

# Create router using RouterFactory
router = RouterFactory("Domain Management").create_router(
    prefix="/domains",
    tags=["Domain Management"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=DomainResponse)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def create_domain(
    domain_data: DomainCreate,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service),
):
    """Create a new domain."""
    result = await domain_service.create_domain(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        domain_name=domain_data.domain_name,
        subdomain=domain_data.subdomain,
        dns_provider=domain_data.dns_provider,
        is_primary=domain_data.is_primary,
        auto_ssl=domain_data.auto_ssl,
    )
    return DomainResponse(**result["domain"].__dict__)


@router.get("/", response_model=DomainListResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def list_domains(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    status: Optional[DomainStatus] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service),
):
    """List domains for the current tenant."""
    domains, total = await domain_service.list_domains(
        tenant_id=current_user["tenant_id"], status=status, page=page, size=size
    )
    return DomainListResponse(
        items=[DomainResponse(**d.__dict__) for d in domains],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{domain_id}", response_model=DomainResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def get_domain(
    domain_id: str,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service),
):
    """Get domain details."""
    result = await domain_service.get_domain(
        domain_id=domain_id, tenant_id=current_user["tenant_id"], user_id=current_user["user_id"]
    )
    return DomainResponse(**result["domain"].__dict__)
