"""
Partner management API used by the management-reseller portal.
"""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter

from dotmac_shared.api.dependencies import PaginatedDeps, StandardDeps
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ....repositories.partner import PartnerRepository
from .schemas import (
    PaginatedPartners,
    PartnerCreate,
    PartnerResponse,
    PartnerUpdate,
    SuspendRequest,
    TierUpdateRequest,
)


router = APIRouter(prefix="/partners", tags=["Partner Management"])


@router.get("/", response_model=PaginatedPartners)
@standard_exception_handler
async def list_partners(
    deps: PaginatedDeps,
) -> PaginatedPartners:
    repo = PartnerRepository(deps.db)
    filters = deps.pagination.filters or {}
    q = filters.get("q") or filters.get("search")
    status = filters.get("status")
    tier = filters.get("tier")

    items, total = await repo.list_partners(
        skip=deps.pagination.offset,
        limit=deps.pagination.size,
        q=q,
        status=status,
        tier=tier,
    )
    return PaginatedPartners(
        items=[PartnerResponse.model_validate(x) for x in items],
        total=total,
        page=deps.pagination.page,
        size=deps.pagination.size,
    )


@router.get("/{partner_id}", response_model=PartnerResponse)
@standard_exception_handler
async def get_partner(partner_id: UUID, deps: StandardDeps) -> PartnerResponse:
    repo = PartnerRepository(deps.db)
    partner = await repo.get_by_id(partner_id)
    if not partner:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerResponse.model_validate(partner)


@router.post("/", response_model=PartnerResponse, status_code=201)
@standard_exception_handler
async def create_partner(data: PartnerCreate, deps: StandardDeps) -> PartnerResponse:
    repo = PartnerRepository(deps.db)
    obj = await repo.create(data.model_dump(), user_id=deps.user_id)
    return PartnerResponse.model_validate(obj)


@router.put("/{partner_id}", response_model=PartnerResponse)
@standard_exception_handler
async def update_partner(
    partner_id: UUID, data: PartnerUpdate, deps: StandardDeps
) -> PartnerResponse:
    repo = PartnerRepository(deps.db)
    partner = await repo.get_by_id(partner_id)
    if not partner:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Partner not found")
    update_data = data.model_dump(exclude_unset=True)
    # Direct update via model
    for k, v in update_data.items():
        setattr(partner, k, v)
    await deps.db.flush()
    await deps.db.refresh(partner)
    return PartnerResponse.model_validate(partner)


@router.delete("/{partner_id}")
@standard_exception_handler
async def delete_partner(partner_id: UUID, deps: StandardDeps) -> Dict[str, str]:
    repo = PartnerRepository(deps.db)
    partner = await repo.get_by_id(partner_id)
    if not partner:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Partner not found")
    partner.is_deleted = True
    await deps.db.flush()
    return {"message": "Partner deleted successfully"}


@router.post("/{partner_id}/approve", response_model=PartnerResponse)
@standard_exception_handler
async def approve_partner(partner_id: UUID, deps: StandardDeps) -> PartnerResponse:
    repo = PartnerRepository(deps.db)
    partner = await repo.approve(partner_id)
    if not partner:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerResponse.model_validate(partner)


@router.post("/{partner_id}/suspend", response_model=PartnerResponse)
@standard_exception_handler
async def suspend_partner(
    partner_id: UUID, data: SuspendRequest, deps: StandardDeps
) -> PartnerResponse:
    repo = PartnerRepository(deps.db)
    partner = await repo.suspend(partner_id, data.reason)
    if not partner:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerResponse.model_validate(partner)


@router.put("/{partner_id}/tier", response_model=PartnerResponse)
@standard_exception_handler
async def update_partner_tier(
    partner_id: UUID, data: TierUpdateRequest, deps: StandardDeps
) -> PartnerResponse:
    repo = PartnerRepository(deps.db)
    partner = await repo.update_tier(partner_id, data.tier)
    if not partner:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerResponse.model_validate(partner)

