"""
API v1 routes.
"""

from dotmac_shared.api.exception_handlers import standard_exception_handler

from typing import Dict
import os

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# from config import settings  # TODO: Fix config import
class MockSettings:
    app_version = "1.0.0"
    environment = "development"
settings = MockSettings()
from dotmac_shared.api.router_factory import RouterFactory

# Import existing routers (gracefully handle missing ones)
try:
    from .admin import router as admin_router
except ImportError:
    admin_router = None

try:
    from .tenants import router as tenant_router
except ImportError:
    tenant_router = None

try:
    from .public_signup import router as public_signup_router
except ImportError:
    public_signup_router = None

try:
    from .onboarding import router as onboarding_router
except ImportError:
    onboarding_router = None

try:
    from .monitoring_simple import router as monitoring_router
except ImportError:
    monitoring_router = None

try:
    from .partners.router import router as partners_router
except ImportError:
    partners_router = None

try:
    from .vps_customers import router as vps_customers_router
except ImportError:
    vps_customers_router = None

try:
    from .licensing_endpoints import router as licensing_router
except ImportError:
    licensing_router = None

# Import commission and branding routers with security enhancements
try:
    from .commission_config import router as commission_config_router
except ImportError:
    commission_config_router = None

try:
    from .partner_branding import router as partner_branding_router
except ImportError:
    partner_branding_router = None

api_router = APIRouter()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all API responses"""
    
    def __init__(self, app):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers based on environment
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-API-Version": "v1",
            "X-Service": "dotmac-management-api"
        }
        
        # Add HSTS in production
        if self.environment == "production":
            security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Apply headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


# Note: Security headers middleware should be added at the FastAPI app level, not router level


# Standardized health endpoints for API v1
@api_router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for API v1."""
    from datetime import datetime

    return {
        "status": "healthy",
        "service": "management-platform",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.get("/health/database")
@standard_exception_handler
async def database_health_check() -> Dict[str, str]:
    """Database health check endpoint for API v1."""
    from datetime import datetime

    from database import engine
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "component": "database",
        "response_time": "fast",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Import tenant admin router (gracefully handle missing)
try:
    from ...portals.tenant_admin.router import tenant_admin_api_router
except ImportError:
    tenant_admin_api_router = None

# Include existing API routes (only if they exist)
if admin_router:
    api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])

if tenant_router:
    api_router.include_router(tenant_router, prefix="/tenants", tags=["Tenants"])

if public_signup_router:
    api_router.include_router(public_signup_router, tags=["Public Signup"])

if onboarding_router:
    api_router.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])

if monitoring_router:
    api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])

if partners_router:
    api_router.include_router(partners_router, prefix="/partners", tags=["Partners"])

if vps_customers_router:
    api_router.include_router(vps_customers_router, prefix="/vps-customers", tags=["VPS Customers"])

if licensing_router:
    api_router.include_router(licensing_router, tags=["License Management"])

if commission_config_router:
    api_router.include_router(commission_config_router, prefix="/commission-config", tags=["Commission Configuration"])

if partner_branding_router:
    api_router.include_router(partner_branding_router, prefix="/partners", tags=["Partner Branding"])

# Include tenant admin portal API (if available)
if tenant_admin_api_router:
    api_router.include_router(
        tenant_admin_api_router, prefix="/tenant-admin", tags=["Tenant Admin Portal"]
    )

__all__ = ["api_router"]
