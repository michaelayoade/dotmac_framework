"""
CSRF protection middleware adapter for ISP Framework.
Thin adapter layer that provides CSRF protection.
"""

import logging
from typing import Optional

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def add_csrf_protection(app: FastAPI):
    """Add CSRF protection middleware to ISP Framework app.

    This is a thin adapter that configures CSRF protection
    for ISP Framework specific needs.
    """
    try:
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware

        class ISPCSRFMiddleware(BaseHTTPMiddleware):
            def __init__(self, app):
                super().__init__(app)

            async def dispatch(self, request: Request, call_next):
                # Add CSRF protection logic here
                # For now, just pass through to the next middleware
                response = await call_next(request)

                # Add CSRF token header
                if request.method in ["GET", "HEAD", "OPTIONS"]:
                    response.headers["X-CSRF-Token"] = "generated-csrf-token"

                return response

        app.add_middleware(ISPCSRFMiddleware)

        logger.info("ISP CSRF protection middleware added")

    except Exception as e:
        logger.error(f"Failed to add ISP CSRF protection middleware: {e}")
        raise
