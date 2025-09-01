"""
Reseller Portal Web Interface Router
Provides HTML pages for reseller portal functionality
"""

from datetime import date
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Request, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.database.session import get_async_db
from dotmac_shared.auth.current_user import get_current_tenant, get_current_user
from dotmac_shared.api.standard_responses import standard_exception_handler

from .portal_interface import ResellerPortalService, ResellerPortalRenderer
from .services_complete import ResellerService


# Initialize templates (this would be configured in main app)
templates = Jinja2Templates(directory="templates")

# Create portal router
portal_router = APIRouter(
    prefix="/reseller/portal",
    tags=["reseller-portal"],
    responses={404: {"description": "Not found"}}
)


@portal_router.get("/", response_class=HTMLResponse)
@standard_exception_handler
async def portal_home(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Reseller portal home page - redirects to dashboard"""
    return RedirectResponse(url="/reseller/portal/dashboard", status_code=302)


@portal_router.get("/dashboard", response_class=HTMLResponse)
@standard_exception_handler
async def portal_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Reseller dashboard page"""
    
    # Get reseller ID from user context (would be linked to user account)
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Get dashboard data
    portal_service = ResellerPortalService(db, tenant_id)
    dashboard_data = await portal_service.get_dashboard_data(reseller_id)
    
    # Render dashboard
    renderer = ResellerPortalRenderer(templates)
    return renderer.render_dashboard(request, dashboard_data)


@portal_router.get("/customers", response_class=HTMLResponse)
@standard_exception_handler
async def portal_customers(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=10, le=100),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Customer management page"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Get customer data
    portal_service = ResellerPortalService(db, tenant_id)
    customer_data = await portal_service.get_customer_list(reseller_id, page, limit)
    
    # Render customers page
    renderer = ResellerPortalRenderer(templates)
    return renderer.render_customers(request, customer_data)


@portal_router.get("/commissions", response_class=HTMLResponse)
@standard_exception_handler
async def portal_commissions(
    request: Request,
    months: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Commission history and payments page"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Get commission data
    portal_service = ResellerPortalService(db, tenant_id)
    commission_data = await portal_service.get_commission_history(reseller_id, months)
    
    # Render commissions page
    renderer = ResellerPortalRenderer(templates)
    return renderer.render_commissions(request, commission_data)


@portal_router.get("/analytics", response_class=HTMLResponse)
@standard_exception_handler
async def portal_analytics(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Performance analytics and reporting page"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Get analytics data
    portal_service = ResellerPortalService(db, tenant_id)
    analytics_data = await portal_service.get_performance_analytics(reseller_id)
    
    # Render analytics page
    renderer = ResellerPortalRenderer(templates)
    return renderer.render_analytics(request, analytics_data)


@portal_router.get("/profile", response_class=HTMLResponse)
@standard_exception_handler
async def portal_profile(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Reseller profile and account settings"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Get reseller data
    reseller_service = ResellerService(db, tenant_id)
    reseller = await reseller_service.get_by_id(reseller_id)
    
    if not reseller:
        raise HTTPException(status_code=404, detail="Reseller not found")
    
    return templates.TemplateResponse(
        "reseller/profile.html",
        {
            "request": request,
            "reseller": {
                "id": reseller.id,
                "reseller_id": reseller.reseller_id,
                "company_name": reseller.company_name,
                "primary_contact_name": reseller.primary_contact_name,
                "primary_contact_email": reseller.primary_contact_email,
                "primary_contact_phone": reseller.primary_contact_phone,
                "business_address": reseller.business_address,
                "commission_rate": float(reseller.base_commission_rate or 0),
                "status": reseller.status.value,
                "created_at": reseller.created_at,
                "territories": reseller.assigned_territories,
                "capabilities": reseller.technical_capabilities
            }
        }
    )


@portal_router.post("/profile/update")
@standard_exception_handler
async def update_profile(
    contact_name: str = Form(...),
    contact_email: str = Form(...),
    contact_phone: Optional[str] = Form(None),
    business_address: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update reseller profile information"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Update reseller information
    reseller_service = ResellerService(db, tenant_id)
    update_data = {
        'primary_contact_name': contact_name,
        'primary_contact_email': contact_email,
        'primary_contact_phone': contact_phone,
        'business_address': business_address
    }
    
    await reseller_service.update_reseller(reseller_id, update_data)
    
    return RedirectResponse(url="/reseller/portal/profile?updated=1", status_code=302)


@portal_router.get("/reports/download")
@standard_exception_handler
async def download_report(
    report_type: str = Query(..., regex="^(customers|commissions|performance)$"),
    format: str = Query("csv", regex="^(csv|pdf)$"),
    months: Optional[int] = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Download reports in CSV or PDF format"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    portal_service = ResellerPortalService(db, tenant_id)
    
    if report_type == "customers":
        # Generate customer report
        customer_data = await portal_service.get_customer_list(reseller_id, limit=10000)
        
        if format == "csv":
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow([
                'Customer ID', 'Company Name', 'Contact Name', 'Contact Email',
                'Service Type', 'Monthly Revenue', 'Status', 'Created Date'
            ])
            
            # Data rows
            for customer in customer_data['customers']:
                writer.writerow([
                    customer['customer_id'],
                    customer['company_name'],
                    customer['primary_contact'],
                    customer['primary_contact_email'],
                    customer['service_type'],
                    customer['mrr'],
                    customer['status'],
                    customer['created_at']
                ])
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=customers_{reseller_id}.csv"}
            )
    
    elif report_type == "commissions":
        # Generate commission report
        commission_data = await portal_service.get_commission_history(reseller_id, months or 12)
        
        if format == "csv":
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow(['Month', 'Earnings', 'Customers', 'Status', 'Payment Date'])
            
            # Data rows
            for month_data in commission_data['monthly_breakdown']:
                writer.writerow([
                    month_data['month'],
                    month_data['earnings'],
                    month_data['customers'],
                    month_data['status'],
                    month_data['payment_date'] or 'Pending'
                ])
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=commissions_{reseller_id}.csv"}
            )
    
    # Default fallback
    raise HTTPException(status_code=400, detail="Invalid report type or format")


# API endpoints for AJAX requests
@portal_router.get("/api/metrics")
@standard_exception_handler
async def get_metrics_api(
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """API endpoint for dashboard metrics (for AJAX updates)"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    portal_service = ResellerPortalService(db, tenant_id)
    dashboard_data = await portal_service.get_dashboard_data(reseller_id)
    
    return {
        "metrics": dashboard_data['metrics'],
        "financial": dashboard_data['financial']
    }


@portal_router.get("/api/customers/search")
@standard_exception_handler
async def search_customers_api(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str = Depends(get_current_tenant),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """API endpoint for customer search"""
    
    reseller_id = current_user.get('reseller_id')
    if not reseller_id:
        raise HTTPException(status_code=403, detail="No reseller account associated with user")
    
    # Simple search implementation - in production would use full-text search
    portal_service = ResellerPortalService(db, tenant_id)
    customer_data = await portal_service.get_customer_list(reseller_id, limit=1000)
    
    # Filter customers by search term
    search_results = [
        customer for customer in customer_data['customers']
        if q.lower() in customer['company_name'].lower() or
           q.lower() in customer['primary_contact'].lower() or
           q.lower() in customer['customer_id'].lower()
    ]
    
    return {"customers": search_results[:20]}  # Limit to 20 results


# Export router
__all__ = ["portal_router"]