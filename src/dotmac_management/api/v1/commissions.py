"""
Commissions API for management-reseller portal.

Provides comprehensive commission management including:
- Commission tracking and calculation
- Payment processing and status management
- Reporting and analytics
- Export functionality for financial records

Follows DRY patterns using dotmac packages for consistent API structure.
"""

from datetime import datetime, timezone
from io import StringIO
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError

from dotmac.application import standard_exception_handler
from dotmac.application.dependencies.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from dotmac.core.schemas.base_schemas import PaginatedResponseSchema
from dotmac.platform.observability.logging import get_logger

from ...models.billing import CommissionStatus
from ...repositories.billing import CommissionRepository

router = APIRouter(prefix="/commissions", tags=["Commissions"])
logger = get_logger(__name__)


# Response Models
class CommissionResponse:
    """Commission response model"""

    def __init__(self, commission):
        self.id = str(commission.id)
        self.reseller_id = str(commission.reseller_id)
        self.tenant_id = str(commission.tenant_id)
        self.subscription_id = (
            str(commission.subscription_id) if commission.subscription_id else None
        )
        self.invoice_id = str(commission.invoice_id) if commission.invoice_id else None
        self.base_amount_cents = commission.base_amount_cents
        self.commission_rate = float(commission.commission_rate)
        self.commission_amount_cents = commission.commission_amount_cents
        self.status = (
            commission.status.value
            if hasattr(commission.status, "value")
            else str(commission.status)
        )
        self.period_start = commission.period_start
        self.period_end = commission.period_end
        self.earned_date = commission.earned_date
        self.paid_at = commission.paid_at
        self.payment_reference = commission.payment_reference

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "reseller_id": self.reseller_id,
            "tenant_id": self.tenant_id,
            "subscription_id": self.subscription_id,
            "invoice_id": self.invoice_id,
            "base_amount_cents": self.base_amount_cents,
            "commission_rate": self.commission_rate,
            "commission_amount_cents": self.commission_amount_cents,
            "status": self.status,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "earned_date": self.earned_date,
            "paid_at": self.paid_at,
            "payment_reference": self.payment_reference,
        }


# ============================================================================
# Commission Management Endpoints
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponseSchema[dict],
    summary="List commissions",
    description="Retrieve paginated list of commissions with filtering options",
)
@standard_exception_handler
async def list_commissions(
    reseller_id: Optional[UUID] = Query(None, description="Filter by reseller ID"),
    status: Optional[CommissionStatus] = Query(
        None, description="Filter by commission status"
    ),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> PaginatedResponseSchema[dict]:
    """List commissions with optional filtering by reseller and status."""
    repo = CommissionRepository(deps.db)

    # Build filters
    filters = {}
    if status:
        filters["status"] = status
    if reseller_id:
        filters["reseller_id"] = reseller_id

    # Get paginated results
    items = await repo.list(
        filters=filters,
        skip=deps.search_params.offset,
        limit=deps.search_params.limit,
        order_by="-earned_date",
    )

    # Get total count for pagination
    total = await repo.count(filters=filters)

    # Convert to response format
    commission_responses = [CommissionResponse(item).to_dict() for item in items]

    return PaginatedResponseSchema[dict](
        items=commission_responses,
        total=total,
        page=deps.search_params.page,
        per_page=deps.search_params.limit,
    )


@router.get(
    "/{commission_id}",
    response_model=dict[str, Any],
    summary="Get commission details",
    description="Retrieve detailed information for a specific commission",
)
@standard_exception_handler
async def get_commission(
    commission_id: UUID = Path(..., description="Commission ID"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get detailed information for a specific commission."""
    repo = CommissionRepository(deps.db)
    commission = await repo.get_by_id(commission_id)

    if not commission:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Commission {commission_id} not found")

    return CommissionResponse(commission).to_dict()


@router.put(
    "/{commission_id}/status",
    response_model=dict[str, Any],
    summary="Update commission status",
    description="Update the status of a specific commission",
)
@standard_exception_handler
async def update_commission_status(
    commission_id: UUID = Path(..., description="Commission ID"),
    new_status: CommissionStatus = Query(..., description="New commission status"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Update the status of a specific commission."""
    repo = CommissionRepository(deps.db)
    commission = await repo.get_by_id(commission_id)

    if not commission:
        from dotmac.core.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"Commission {commission_id} not found")

    # Update status
    commission.status = new_status
    if new_status == CommissionStatus.PAID:
        commission.paid_at = datetime.now(timezone.utc)

    updated_commission = await repo.update(commission_id, commission)

    return {
        "success": True,
        "message": f"Commission status updated to {new_status.value}",
        "data": CommissionResponse(updated_commission).to_dict(),
    }


# ============================================================================
# Commission Analytics & Reporting
# ============================================================================


@router.get(
    "/analytics/summary",
    response_model=dict[str, Any],
    summary="Get commission analytics summary",
    description="Retrieve summary analytics for commissions",
)
@standard_exception_handler
async def get_commission_analytics(
    reseller_id: Optional[UUID] = Query(None, description="Filter by reseller ID"),
    start_date: Optional[datetime] = Query(
        None, description="Start date for analytics"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get commission analytics summary with optional filtering."""
    repo = CommissionRepository(deps.db)

    # Build date range filters
    filters = {}
    if reseller_id:
        filters["reseller_id"] = reseller_id
    if start_date:
        filters["earned_date__gte"] = start_date
    if end_date:
        filters["earned_date__lte"] = end_date

    # Get analytics data
    analytics = await repo.get_analytics_summary(filters)

    return {
        "success": True,
        "data": analytics,
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }


@router.post(
    "/export",
    response_class=StreamingResponse,
    summary="Export commissions",
    description="Export commission data to CSV format",
)
@standard_exception_handler
async def export_commissions(
    reseller_id: Optional[UUID] = Query(None, description="Filter by reseller ID"),
    status: Optional[CommissionStatus] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Start date for export"),
    end_date: Optional[datetime] = Query(None, description="End date for export"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> StreamingResponse:
    """Export commission data to CSV format."""
    repo = CommissionRepository(deps.db)

    # Build filters
    filters = {}
    if reseller_id:
        filters["reseller_id"] = reseller_id
    if status:
        filters["status"] = status
    if start_date:
        filters["earned_date__gte"] = start_date
    if end_date:
        filters["earned_date__lte"] = end_date

    # Get all commissions matching filters
    commissions = await repo.list(filters=filters, order_by="-earned_date")

    # Generate CSV content
    csv_content = StringIO()
    csv_content.write(
        "ID,Reseller ID,Tenant ID,Base Amount,Commission Rate,Commission Amount,Status,Period Start,Period End,Earned Date,Paid At\n"
    )

    for commission in commissions:
        csv_content.write(
            f"{commission.id},"
            f"{commission.reseller_id},"
            f"{commission.tenant_id},"
            f"{commission.base_amount_cents / 100:.2f},"
            f"{float(commission.commission_rate):.4f},"
            f"{commission.commission_amount_cents / 100:.2f},"
            f"{commission.status},"
            f"{commission.period_start},"
            f"{commission.period_end},"
            f"{commission.earned_date},"
            f"{commission.paid_at or ''}\n"
        )

    csv_content.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"commissions_export_{timestamp}.csv"

    return StreamingResponse(
        iter([csv_content.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================================================
# Commission Payments
# ============================================================================


@router.post(
    "/batch-payment",
    response_model=dict[str, Any],
    summary="Process batch commission payment",
    description="Mark multiple commissions as paid in batch",
)
@standard_exception_handler
async def process_batch_payment(
    commission_ids: list[UUID] = Query(
        ..., description="List of commission IDs to mark as paid"
    ),
    payment_reference: str = Query(..., description="Payment reference number"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Process batch payment for multiple commissions."""
    repo = CommissionRepository(deps.db)

    updated_count = 0
    errors = []

    for commission_id in commission_ids:
        try:
            commission = await repo.get_by_id(commission_id)
            if commission and commission.status != CommissionStatus.PAID:
                commission.status = CommissionStatus.PAID
                commission.paid_at = datetime.now(timezone.utc)
                commission.payment_reference = payment_reference

                await repo.update(commission_id, commission)
                updated_count += 1
        except SQLAlchemyError as e:
            errors.append(f"Commission {commission_id}: {str(e)}")

    return {
        "success": len(errors) == 0,
        "message": f"Processed {updated_count} commission payments",
        "data": {
            "updated_count": updated_count,
            "total_requested": len(commission_ids),
            "payment_reference": payment_reference,
            "errors": errors,
        },
    }
