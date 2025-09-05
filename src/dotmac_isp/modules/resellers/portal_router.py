"""
Reseller Portal Web Interface Router - DRY Migration
Provides HTML pages for reseller portal functionality using RouterFactory patterns.
"""

from uuid import UUID

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    StandardDependencies,
    get_standard_deps,
)
from fastapi import Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .schemas import (
    ResellerResponseSchema,
)
from .services_complete import ResellerService

templates = Jinja2Templates(directory="templates/reseller")

# Create main portal router using RouterFactory
portal_router = RouterFactory.create_readonly_router(
    service_class=ResellerService,
    response_schema=ResellerResponseSchema,
    prefix="/reseller/portal",
    tags=["reseller-portal"],
    enable_search=False,
)


# === Portal Navigation ===


@portal_router.get("/", response_class=HTMLResponse)
@standard_exception_handler
async def portal_home(request: Request) -> RedirectResponse:
    """Reseller portal home page - redirects to dashboard."""
    return RedirectResponse(url="/reseller/portal/dashboard", status_code=302)


@portal_router.get("/dashboard", response_class=HTMLResponse)
@standard_exception_handler
async def portal_dashboard(
    request: Request,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> HTMLResponse:
    """Reseller dashboard page."""
    service = ResellerService(deps.db, deps.tenant_id)

    # Get reseller data for current user
    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")

    # Get dashboard metrics
    metrics = await service.get_dashboard_metrics(reseller_data.id)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "reseller": reseller_data,
            "metrics": metrics,
            "user": deps.user_id,
        },
    )


@portal_router.get("/customers", response_class=HTMLResponse)
@standard_exception_handler
async def portal_customers(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    search: str | None = Query(None, description="Search term"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> HTMLResponse:
    """Customer management page."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get paginated customer list
    customers, total = await service.get_reseller_customers(reseller_data.id, page=page, search=search)

    return templates.TemplateResponse(
        "customers.html",
        {
            "request": request,
            "customers": customers,
            "total": total,
            "page": page,
            "search": search,
            "reseller": reseller_data,
        },
    )


@portal_router.get("/commissions", response_class=HTMLResponse)
@standard_exception_handler
async def portal_commissions(
    request: Request,
    month: int | None = Query(None, ge=1, le=12, description="Month filter"),
    year: int | None = Query(None, ge=2020, description="Year filter"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> HTMLResponse:
    """Commission tracking page."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get commission data
    commissions = await service.get_commission_history(reseller_data.id, month=month, year=year)

    return templates.TemplateResponse(
        "commissions.html",
        {
            "request": request,
            "commissions": commissions,
            "reseller": reseller_data,
            "selected_month": month,
            "selected_year": year,
        },
    )


@portal_router.get("/reports", response_class=HTMLResponse)
@standard_exception_handler
async def portal_reports(
    request: Request,
    report_type: str | None = Query(None, description="Report type filter"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> HTMLResponse:
    """Reports and analytics page."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get available reports
    reports = await service.get_available_reports(reseller_data.id)

    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "reports": reports,
            "reseller": reseller_data,
            "report_type": report_type,
        },
    )


# === Customer Actions ===


@portal_router.post("/customers/create", response_class=HTMLResponse)
@standard_exception_handler
async def create_customer_form(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(...),
    service_plan: str = Form(...),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> RedirectResponse:
    """Handle customer creation form submission."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create new customer
    customer_data = {
        "name": customer_name,
        "email": customer_email,
        "service_plan": service_plan,
        "reseller_id": reseller_data.id,
    }

    customer = await service.create_customer(customer_data, deps.user_id)

    return RedirectResponse(
        url=f"/reseller/portal/customers?created={customer.id}",
        status_code=303,
    )


@portal_router.post("/customers/{customer_id}/update", response_class=HTMLResponse)
@standard_exception_handler
async def update_customer_form(
    customer_id: UUID,
    request: Request,
    service_plan: str = Form(...),
    status: str = Form(...),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> RedirectResponse:
    """Handle customer update form submission."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update customer
    update_data = {
        "service_plan": service_plan,
        "status": status,
    }

    await service.update_customer(customer_id, update_data, deps.user_id)

    return RedirectResponse(
        url=f"/reseller/portal/customers?updated={customer_id}",
        status_code=303,
    )


# === Profile Management ===


@portal_router.get("/profile", response_class=HTMLResponse)
@standard_exception_handler
async def portal_profile(
    request: Request,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> HTMLResponse:
    """Reseller profile management page."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "reseller": reseller_data,
        },
    )


@portal_router.post("/profile/update", response_class=HTMLResponse)
@standard_exception_handler
async def update_profile_form(
    request: Request,
    company_name: str = Form(...),
    contact_email: str = Form(...),
    contact_phone: str = Form(...),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> RedirectResponse:
    """Handle profile update form submission."""
    service = ResellerService(deps.db, deps.tenant_id)

    reseller_data = await service.get_reseller_for_user(deps.user_id)
    if not reseller_data:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update reseller profile
    update_data = {
        "company_name": company_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
    }

    await service.update_reseller(reseller_data.id, update_data, deps.user_id)

    return RedirectResponse(
        url="/reseller/portal/profile?updated=true",
        status_code=303,
    )


# Export the router
__all__ = ["portal_router"]
