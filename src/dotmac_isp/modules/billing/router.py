"""
Production-ready Billing API router using mandatory DRY patterns.
All manual router patterns have been eliminated.
"""

import io
from typing import Any
from uuid import UUID

from fastapi import Depends, UploadFile
from fastapi.responses import StreamingResponse

try:
    from dotmac.application import standard_exception_handler
except Exception:  # pragma: no cover

    def standard_exception_handler(func=None, *d, **k):  # type: ignore
        def _wrap(f):
            return f

        return _wrap if func is None else func


from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    SearchParams,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from dotmac_shared.api.router_factory import BillingRouterFactory, RouterFactory

from .schemas import (
    BillingReport,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceUpdate,
    PaymentCreate,
    PaymentResponse,
    PaymentUpdate,
)
from .service import BillingService, InvoiceService, PaymentService

# === PRODUCTION-READY BILLING ROUTERS ===

# Invoice management with all CRUD operations + billing-specific endpoints
invoice_router = BillingRouterFactory.create_invoice_router(
    service_class=InvoiceService,
    schemas={
        "create": InvoiceCreate,
        "update": InvoiceUpdate,
        "response": InvoiceResponse,
    },
    prefix="/invoices",
)
# Payment management with all CRUD operations
payment_router = RouterFactory.create_crud_router(
    service_class=PaymentService,
    create_schema=PaymentCreate,
    update_schema=PaymentUpdate,
    response_schema=PaymentResponse,
    prefix="/payments",
    tags=["billing", "payments"],
    enable_search=True,
    enable_bulk_operations=True,
)
# Main billing router combining all sub-routers
router = RouterFactory.create_readonly_router(
    service_class=BillingService,
    response_schema=BillingReport,
    prefix="",
    tags=["billing"],
    enable_search=False,
)
# Include all standardized sub-routers
router.include_router(invoice_router)
router.include_router(payment_router)
# === CUSTOM BILLING ENDPOINTS ===


@router.get("/dashboard")
@standard_exception_handler
async def get_billing_dashboard(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get billing dashboard with summary statistics."""
    service = BillingService(deps.db, deps.tenant_id)
    return await service.get_dashboard_data(deps.user_id)


@router.get("/reports/revenue")
@standard_exception_handler
async def get_revenue_report(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    search: SearchParams = Depends(SearchParams),
) -> BillingReport:
    """Generate revenue report with filters."""
    service = BillingService(deps.db, deps.tenant_id)
    return await service.generate_revenue_report(
        filters=search.filters or {}, pagination=deps.pagination, user_id=deps.user_id
    )


@router.post("/invoices/{invoice_id}/pdf")
@standard_exception_handler
async def generate_invoice_pdf(
    invoice_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> StreamingResponse:
    """Generate and download invoice PDF."""
    service = BillingService(deps.db, deps.tenant_id)
    pdf_content = await service.generate_invoice_pdf(invoice_id, deps.user_id)
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename = invoice-{invoice_id}.pdf"},
    )


@router.post("/invoices/{invoice_id}/attachments")
@standard_exception_handler
async def upload_invoice_attachment(
    invoice_id: UUID,
    file: UploadFile = None,
    deps: StandardDependencies = Depends(get_standard_deps),
    # upload_params: FileUploadDeps = None,  # Not implemented
):
    """Upload attachment to invoice."""
    service = BillingService(deps.db, deps.tenant_id)
    return await service.upload_invoice_attachment(
        invoice_id=invoice_id,
        file=file,
        max_size=10 * 1024 * 1024,  # 10MB default
        allowed_types=["pdf", "jpg", "png", "doc", "docx"],  # Default allowed types
        user_id=deps.user_id,
    )


# Export aliases for backward compatibility
billing_router = router
