"""
Tenant security middleware adapters for Management Platform.
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


def add_management_tenant_security_middleware(app: FastAPI):
    """Add tenant security middleware to Management Platform app.

    This is a thin adapter that configures the shared tenant security
    middleware for Management Platform specific needs.
    """
    try:
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware

        class ManagementTenantSecurityMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, tenant_security_service: TenantSecurityManager):
                super().__init__(app)
                self.tenant_security = tenant_security_service

            async def dispatch(self, request: Request, call_next):
                # Add Management Platform-specific tenant security logic here
                # For now, just pass through to the next middleware
                response = await call_next(request)
                return response

        tenant_security_service = get_tenant_security_service()
        app.add_middleware(
            ManagementTenantSecurityMiddleware,
            tenant_security_service=tenant_security_service,
        )

        logger.info("Management tenant security middleware added")

    except Exception:  # noqa: BLE001 - wrap and re-raise with context
        logger.exception("Failed to add Management tenant security middleware")
        raise


async def init_management_tenant_security():
    """Initialize tenant security for Management Platform.

    This is an adapter function that initializes the shared tenant security
    service for Management Platform usage.
    """
    try:
        get_tenant_security_service()

        # Add any Management Platform-specific tenant security initialization here
        logger.info("Management tenant security initialized")

    except Exception:  # noqa: BLE001 - wrap and re-raise with context
        logger.exception("Failed to initialize Management tenant security")
        raise
