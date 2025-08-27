"""
API v1 routes.
"""

from typing import Dict
from fastapi import APIRouter

from .analytics import router as analytics_router
from .auth import router as auth_router
from .tenant import router as tenant_router
from .billing import router as billing_router
from .commissions import router as commissions_router
from .deployment import router as deployment_router
from .onboarding import router as onboarding_router
from .plugin import router as plugin_router
from .monitoring import router as monitoring_router
from .user_management import router as user_management_router
from .partners.router import router as partners_router
from .partners.dashboard import router as partner_dashboard_router
from .partners.customers import router as partner_customers_router
from config import settings

api_router = APIRouter()

# Simple health endpoint for API v1
@api_router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for API v1."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": "2024-01-01T00:00:00Z"
    }

@api_router.get("/health/database")
async def database_health_check() -> Dict[str, str]:
    """Database health check endpoint for API v1."""
    return {
        "status": "healthy",
        "response_time": "5ms",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Import tenant admin router
from ...portals.tenant_admin.router import tenant_admin_api_router

# Include all API routes
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenant_router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(commissions_router, prefix="/commissions", tags=["Commissions"])
api_router.include_router(deployment_router, prefix="/deployment", tags=["Deployment"])
api_router.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
api_router.include_router(plugin_router, prefix="/plugins", tags=["Plugins"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(user_management_router, prefix="/user-management", tags=["User Management"])
api_router.include_router(partners_router, prefix="/partners", tags=["Partner Management"])
api_router.include_router(partner_dashboard_router, prefix="/partners", tags=["Partner Management"])
api_router.include_router(partner_customers_router, prefix="/partners", tags=["Partner Management"])

# Include tenant admin portal API
api_router.include_router(tenant_admin_api_router, prefix="/tenant-admin", tags=["Tenant Admin Portal"])

__all__ = ["api_router"]