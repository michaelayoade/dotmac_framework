"""
Tenant security middleware adapters for ISP Framework.
Thin adapter layer that uses the shared tenant security implementation.
"""

import logging
from typing import Optional

from dotmac.platform.auth.core.tenant_security import TenantSecurityManager
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Global tenant security service instance
_tenant_security_service: Optional[TenantSecurityManager] = None


def get_tenant_security_service() -> TenantSecurityManager:
    """Get or create the tenant security service."""
    global _tenant_security_service

    if _tenant_security_service is None:
        _tenant_security_service = TenantSecurityManager()

    return _tenant_security_service


def add_tenant_security_middleware(app: FastAPI):
    """Add tenant security middleware to ISP Framework app.

    This is a thin adapter that configures the shared tenant security
    middleware for ISP Framework specific needs.
    """
    try:
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware

        class ISPTenantSecurityMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, tenant_security_service: TenantSecurityManager):
                super().__init__(app)
                self.tenant_security = tenant_security_service

            async def dispatch(self, request: Request, call_next):
                # Add ISP-specific tenant security logic here
                # For now, just pass through to the next middleware
                response = await call_next(request)
                return response

        tenant_security_service = get_tenant_security_service()
        app.add_middleware(ISPTenantSecurityMiddleware, tenant_security_service=tenant_security_service)

        logger.info("ISP tenant security middleware added")

    except Exception as e:
        logger.error(f"Failed to add ISP tenant security middleware: {e}")
        raise


async def init_tenant_security(engine, session):
    """Initialize tenant security for ISP Framework.

    This is an adapter function that initializes the shared tenant security
    service for ISP Framework usage.

    Args:
        engine: Database engine
        session: Database session
    """
    try:
        get_tenant_security_service()

        # Add any ISP-specific tenant security initialization here
        logger.info("ISP tenant security initialized")

    except Exception as e:
        logger.error(f"Failed to initialize ISP tenant security: {e}")
        raise
