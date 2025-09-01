"""
Commissions API for management-reseller portal.
"""

from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from dotmac_shared.api.dependencies import PaginatedDeps, StandardDeps
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ...models.billing import CommissionStatus
from ...repositories.billing import CommissionRepository


router = APIRouter(prefix="/commissions", tags=["Commissions"])


def _serialize_commission(c) -> Dict[str, Any]:
    return {
        "id": str(c.id),
        "reseller_id": str(c.reseller_id),
        "tenant_id": str(c.tenant_id),
        "subscription_id": str(c.subscription_id) if c.subscription_id else None,
        "invoice_id": str(c.invoice_id) if c.invoice_id else None,
        "base_amount_cents": c.base_amount_cents,
        "commission_rate": float(c.commission_rate),
        "commission_amount_cents": c.commission_amount_cents,
        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
        "period_start": c.period_start,
        "period_end": c.period_end,
        "earned_date": c.earned_date,
        "paid_at": c.paid_at,
        "payment_reference": c.payment_reference,
    }


@router.get("/", response_model=Dict[str, Any])
@standard_exception_handler
async def list_commissions(
    deps: PaginatedDeps,
    reseller_id: Optional[UUID] = Query(None),
    status: Optional[CommissionStatus] = Query(None),
) -> Dict[str, Any]:
    repo = CommissionRepository(deps.db)
    skip = deps.pagination.offset
    limit = deps.pagination.size

    items: List[Any] = []
    total = 0

    if reseller_id:
        items = await repo.get_by_reseller(
            reseller_id, status=status, skip=skip, limit=limit
        )
        # no efficient total count readily available; approximate by page size
        total = len(items)
    else:
        # Generic list using base repository filters
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status
        items = await repo.list(filters=filters, skip=skip, limit=limit, order_by="-earned_date")
        total = len(items)

    return {
        "items": [_serialize_commission(c) for c in items],
        "total": total,
        "page": deps.pagination.page,
        "size": deps.pagination.size,
    }


@router.get("/{commission_id}", response_model=Dict[str, Any])
@standard_exception_handler
async def get_commission(commission_id: UUID, deps: StandardDeps) -> Dict[str, Any]:
    repo = CommissionRepository(deps.db)
    c = await repo.get_by_id(commission_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commission not found")
    return _serialize_commission(c)


@router.post("/{commission_id}/approve", response_model=Dict[str, Any])
@standard_exception_handler
async def approve_single(commission_id: UUID, deps: StandardDeps) -> Dict[str, Any]:
    repo = CommissionRepository(deps.db)
    updated = await repo.approve_commissions([commission_id], user_id=deps.user_id)
    if updated == 0:
        raise HTTPException(status_code=400, detail="Commission not approvable")
    c = await repo.get_by_id(commission_id)
    return _serialize_commission(c)


@router.post("/bulk-approve", response_model=Dict[str, Any])
@standard_exception_handler
async def bulk_approve(request: Dict[str, List[UUID]], deps: StandardDeps) -> Dict[str, Any]:
    ids = request.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No commission IDs provided")
    repo = CommissionRepository(deps.db)
    count = await repo.approve_commissions(ids, user_id=deps.user_id)
    return {"message": f"Approved {count} commissions", "count": count}


@router.post("/{commission_id}/process", response_model=Dict[str, Any])
@standard_exception_handler
async def process_single(
    commission_id: UUID, deps: StandardDeps, payment_reference: Optional[str] = None
) -> Dict[str, Any]:
    repo = CommissionRepository(deps.db)
    ref = payment_reference or f"single-{commission_id}-{int(datetime.now(timezone.utc).timestamp())}"
    count = await repo.mark_as_paid([commission_id], payment_reference=ref, user_id=deps.user_id)
    if count == 0:
        raise HTTPException(status_code=400, detail="Commission not payable")
    c = await repo.get_by_id(commission_id)
    return _serialize_commission(c)


@router.post("/bulk-process", response_model=Dict[str, Any])
@standard_exception_handler
async def bulk_process(request: Dict[str, List[UUID]], deps: StandardDeps) -> Dict[str, Any]:
    ids = request.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No commission IDs provided")
    repo = CommissionRepository(deps.db)
    ref = f"bulk-{int(datetime.now(timezone.utc).timestamp())}"
    count = await repo.mark_as_paid(ids, payment_reference=ref, user_id=deps.user_id)
    return {"message": f"Processed {count} commissions", "count": count, "payment_reference": ref}


@router.post("/{commission_id}/dispute", response_model=Dict[str, Any])
@standard_exception_handler
async def dispute_single(
    commission_id: UUID, deps: StandardDeps, reason: Optional[str] = None
) -> Dict[str, Any]:
    repo = CommissionRepository(deps.db)
    c = await repo.get_by_id(commission_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commission not found")
    # Store dispute reason and set status to CANCELLED for simplicity
    meta = dict(getattr(c, "metadata_json", {}) or {})
    if reason:
        meta["dispute_reason"] = reason
    c.metadata_json = meta
    c.status = CommissionStatus.CANCELLED
    await deps.db.flush()
    await deps.db.refresh(c)
    return _serialize_commission(c)


@router.get("/summary", response_model=Dict[str, Any])
@standard_exception_handler
async def commissions_summary(
    deps: StandardDeps, reseller_id: Optional[UUID] = Query(None)
) -> Dict[str, Any]:
    repo = CommissionRepository(deps.db)
    summary: Dict[str, Any] = {"counts": {}, "totals": {}}
    # Counts by status (basic approach)
    items = await repo.list(filters={}, limit=1000)
    for c in items:
        key = c.status.value if hasattr(c.status, "value") else str(c.status)
        summary["counts"][key] = summary["counts"].get(key, 0) + 1
    # Totals for approved/paid for reseller if provided
    if reseller_id:
        for st in [CommissionStatus.APPROVED, CommissionStatus.PAID]:
            total = await repo.calculate_total_commission(reseller_id, status=st)
            summary["totals"][st.value] = float(total)
    return summary


@router.post("/approve", response_model=Dict[str, Any])
@standard_exception_handler
async def approve_generic(request: Dict[str, List[UUID]], deps: StandardDeps) -> Dict[str, Any]:
    return await bulk_approve(request, deps)


@router.post("/process", response_model=Dict[str, Any])
@standard_exception_handler
async def process_generic(request: Dict[str, List[UUID]], deps: StandardDeps) -> Dict[str, Any]:
    return await bulk_process(request, deps)


@router.post("/validate-bulk-action", response_model=Dict[str, Any])
@standard_exception_handler
async def validate_bulk_action(request: Dict[str, List[UUID]], deps: StandardDeps) -> Dict[str, Any]:
    ids = request.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    repo = CommissionRepository(deps.db)
    # Very simple validation: all IDs must exist and be PENDING or APPROVED
    invalid: List[str] = []
    eligible: List[str] = []
    for cid in ids:
        c = await repo.get_by_id(cid)
        if not c:
            invalid.append(str(cid))
        else:
            if c.status in (CommissionStatus.PENDING, CommissionStatus.APPROVED):
                eligible.append(str(cid))
            else:
                invalid.append(str(cid))
    return {"eligible": eligible, "invalid": invalid}


@router.get("/export")
@standard_exception_handler
async def export_commissions(
    deps: StandardDeps,
    reseller_id: Optional[UUID] = Query(None),
    status: Optional[CommissionStatus] = Query(None),
) -> StreamingResponse:
    repo = CommissionRepository(deps.db)
    if reseller_id:
        items = await repo.get_by_reseller(reseller_id, status=status, skip=0, limit=1000)
    else:
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status
        items = await repo.list(filters=filters, skip=0, limit=1000, order_by="-earned_date")
    # Generate CSV
    buf = StringIO()
    headers = [
        "id",
        "reseller_id",
        "tenant_id",
        "subscription_id",
        "invoice_id",
        "commission_amount_cents",
        "status",
        "earned_date",
    ]
    buf.write(",".join(headers) + "\n")
    for c in items:
        row = [
            str(c.id),
            str(c.reseller_id),
            str(c.tenant_id),
            str(c.subscription_id or ""),
            str(c.invoice_id or ""),
            str(c.commission_amount_cents),
            c.status.value if hasattr(c.status, "value") else str(c.status),
            (c.earned_date or datetime.now(timezone.utc)).isoformat(),
        ]
        buf.write(",".join(row) + "\n")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commissions.csv"},
    )


@router.post("/export-advanced", response_model=Dict[str, str])
@standard_exception_handler
async def export_advanced(_: Dict[str, Any]) -> Dict[str, str]:
    # Stub: return a fake download URL (in real system would generate a file)
    return {"download_url": "/api/v1/commissions/export"}

