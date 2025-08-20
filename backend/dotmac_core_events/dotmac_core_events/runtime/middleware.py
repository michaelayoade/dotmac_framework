"""
Middleware setup for dotmac_core_events FastAPI application.

Provides middleware configuration for:
- CORS handling
- Request/response logging
- Error handling
- Performance monitoring
- Security headers
"""

import time
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import RuntimeConfig
from .rate_limiting import RateLimitMiddleware, create_default_rate_limit_config
from .security_monitoring import SecurityMonitoringMiddleware, get_security_monitor

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()

        # Log request
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time,
        )

        # Add performance header
        response.headers["X-Process-Time"] = str(process_time)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add CSP header for API
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors and return appropriate responses."""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                "Unhandled error in request",
                method=request.method,
                url=str(request.url),
                error=str(e),
                exc_info=True,
            )

            # Return generic error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", None),
                }
            )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for adding request IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state and response headers."""
        import uuid

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response
        response.headers["X-Request-ID"] = request_id

        return response


def setup_middleware(app: FastAPI, config: RuntimeConfig) -> None:
    """
    Setup middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        config: Runtime configuration
    """
    # Request ID middleware (first)
    app.add_middleware(RequestIDMiddleware)

    # Security monitoring middleware
    security_monitor = get_security_monitor()
    app.add_middleware(SecurityMonitoringMiddleware, monitor=security_monitor)

    # Rate limiting middleware
    rate_limit_config = create_default_rate_limit_config()
    rate_limit_middleware = RateLimitMiddleware(app, rate_limit_config)
    app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

    # CORS middleware - only add if origins are explicitly configured
    if config.security.cors_origins and config.security.cors_origins != [""]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=config.security.cors_methods,
            allow_headers=config.security.cors_headers,
        )
        logger.info("CORS enabled", origins=config.security.cors_origins)
    else:
        logger.info("CORS disabled - no origins configured")

    # Trusted host middleware for production
    if not config.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure based on deployment
        )

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Logging middleware (last, so it captures all processing)
    if config.observability.enable_logging:
        app.add_middleware(LoggingMiddleware)

    logger.info("Middleware setup completed")
