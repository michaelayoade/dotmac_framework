"""
Main Tenant Admin Portal Router.
Combines all tenant admin API endpoints.
"""

from fastapi import APIRouter

from .auth_api import tenant_auth_router
from .overview_api import tenant_overview_router
from .billing_api import tenant_billing_router
from .customer_api import tenant_customer_router

# Create main tenant admin router
tenant_admin_api_router = APIRouter()

# Include all sub-routers with their specific prefixes
tenant_admin_api_router.include_router(
    tenant_auth_router, 
    prefix="/auth", 
    tags=["Tenant Admin Authentication"]
)

tenant_admin_api_router.include_router(
    tenant_overview_router, 
    prefix="", 
    tags=["Tenant Admin Overview"]
)

tenant_admin_api_router.include_router(
    tenant_billing_router, 
    prefix="/billing", 
    tags=["Tenant Admin Billing"]
)

tenant_admin_api_router.include_router(
    tenant_customer_router, 
    prefix="/customers", 
    tags=["Tenant Admin Customers"]
)

# Health check endpoint for tenant admin API
@tenant_admin_api_router.get("/health")
async def tenant_admin_health():
    """Health check for tenant admin API."""
    return {
        "status": "healthy",
        "service": "tenant-admin-api",
        "version": "1.0.0"
    }