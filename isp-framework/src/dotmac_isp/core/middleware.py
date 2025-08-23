"""Custom middleware for DotMac ISP Framework."""

import time
import uuid
from typing import Callable, Dict, Optional
from collections import defaultdict, deque

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from dotmac_isp.core.logging_config import log_api_call
from dotmac_isp.core.redis_middleware import (
    RedisCacheMiddleware,
    RedisSessionMiddleware,
    RateLimitMiddleware as RedisRateLimitMiddleware,
    RequestLoggingMiddleware as RedisRequestLoggingMiddleware,
)

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests with timing and request IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # Process request
        response = await call_next(request)

        # Log request completion with structured data
        process_time = time.time() - start_time

        # Use structured logging
        log_api_call(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=process_time,
            request_id=request_id,
            tenant_id=getattr(request.state, "tenant_id", None),
            client_ip=request.client.host if request.client else "unknown",
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle tenant isolation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract and validate tenant information."""
        # Extract tenant ID from headers or path
        tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id and hasattr(request.path_params, "get"):
            tenant_id = request.path_params.get("tenant_id")

        # Store tenant ID in request state for use in dependencies
        request.state.tenant_id = tenant_id

        # Log tenant context
        if tenant_id:
            logger.debug(f"Request for tenant: {tenant_id}")

        return await call_next(request)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting per IP address."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_times: Dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean up old requests (older than 1 minute)
        cutoff_time = current_time - 60
        while (
            self.request_times[client_ip]
            and self.request_times[client_ip][0] < cutoff_time
        ):
            self.request_times[client_ip].popleft()

        # Check if rate limit exceeded
        if len(self.request_times[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "60"},
            )

        # Add current request time
        self.request_times[client_ip].append(current_time)

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(
            0, self.requests_per_minute - len(self.request_times[client_ip])
        )
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:;"
        )

        return response


def add_middleware(app: FastAPI) -> None:
    """Add custom middleware to the FastAPI application."""
    logger.info("Adding custom middleware...")

    # Add middleware in reverse order (last added is executed first)
    app.add_middleware(SecurityHeadersMiddleware)

    # Use Redis-based rate limiting for better scalability
    app.add_middleware(RedisRateLimitMiddleware, max_requests=100, window_seconds=60)

    # Add Redis session management
    app.add_middleware(
        RedisSessionMiddleware,
        session_cookie="dotmac_session",
        secure=False,
        httponly=True,
    )

    # Add Redis-based request logging for analytics
    app.add_middleware(RedisRequestLoggingMiddleware)

    # Add tenant isolation
    app.add_middleware(TenantIsolationMiddleware)

    # Keep the original request logging for immediate logging needs
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Custom middleware added successfully with Redis integration")


def get_current_tenant_id(request: Request) -> str:
    """Get current tenant ID from request state or headers."""
    # Try to get tenant ID from request state (set by middleware)
    if hasattr(request.state, "tenant_id") and request.state.tenant_id:
        return request.state.tenant_id


def get_tenant_id_dependency(request: Request) -> str:
    """Dependency function to get tenant ID for FastAPI routes."""
    # Try to get tenant ID from request state (set by middleware)
    if hasattr(request.state, "tenant_id") and request.state.tenant_id:
        return request.state.tenant_id

    # Try to get from headers
    tenant_id = request.headers.get("x-tenant-id")
    if tenant_id:
        return tenant_id

    # Try to get from query parameters
    tenant_id = request.query_params.get("tenant_id")
    if tenant_id:
        return tenant_id

    # Default tenant for development (using a valid UUID)
    return "00000000-0000-0000-0000-000000000001"
