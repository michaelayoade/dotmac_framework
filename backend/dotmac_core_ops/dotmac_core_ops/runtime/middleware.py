"""
Middleware setup for the DotMac Core Operations application.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from .config import OpsConfig

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=process_time,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time

            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=process_time,
                exc_info=e,
            )

            raise


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant isolation and context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract tenant ID from headers
        tenant_id = request.headers.get("X-Tenant-ID", "default-tenant")

        # Add tenant ID to request state
        request.state.tenant_id = tenant_id

        # Log tenant context
        logger.debug(
            "Tenant context set",
            tenant_id=tenant_id,
            request_id=getattr(request.state, "request_id", None),
        )

        response = await call_next(request)

        # Add tenant ID to response headers
        response.headers["X-Tenant-ID"] = tenant_id

        return response


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers and API key validation."""

    def __init__(self, app, config: OpsConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip security for health endpoints
        if request.url.path in ["/health", "/ready", "/live"]:
            return await call_next(request)

        # API Key validation
        if self.config.security.api_keys:
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key not in self.config.security.api_keys:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing API key"
                )

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""

    def __init__(self, app, config: OpsConfig):
        super().__init__(app)
        self.config = config
        self.request_count = 0
        self.request_duration_sum = 0.0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.config.observability.enable_metrics:
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)

            # Update metrics
            self.request_count += 1
            duration = time.time() - start_time
            self.request_duration_sum += duration

            # Log metrics (in a real implementation, this would go to a metrics backend)
            logger.debug(
                "Request metrics",
                request_count=self.request_count,
                avg_duration=self.request_duration_sum / self.request_count,
                current_duration=duration,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )

            return response

        except Exception as e:
            # Update error metrics
            self.request_count += 1
            duration = time.time() - start_time
            self.request_duration_sum += duration

            logger.debug(
                "Request error metrics",
                request_count=self.request_count,
                avg_duration=self.request_duration_sum / self.request_count,
                current_duration=duration,
                method=request.method,
                path=request.url.path,
                error=str(e),
            )

            raise


def setup_middleware(app: FastAPI, config: OpsConfig):
    """Setup all middleware for the FastAPI application."""

    # CORS middleware
    if config.security.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=config.security.cors_methods,
            allow_headers=config.security.cors_headers,
        )

    # Trusted host middleware (if not in debug mode)
    if not config.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure based on your deployment
        )

    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(MetricsMiddleware, config=config)
    app.add_middleware(SecurityMiddleware, config=config)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Middleware setup completed")
