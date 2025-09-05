"""
Clean Rate Limiting Middleware - DRY Migration
Production-ready rate limiting using standardized patterns.
"""

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse


class RateLimitMiddleware:
    """Rate limiting middleware for IPAM operations."""

    def __init__(
        self,
        default_limits: dict[str, int] | None = None,
        tenant_limits: dict[str, dict[str, int]] | None = None,
    ):
        self.default_limits = default_limits or {
            "ip_allocation": 100,
            "subnet_creation": 50,
            "pool_management": 30,
        }
        self.tenant_limits = tenant_limits or {}

        # Storage for rate limiting data
        self._request_counts: dict[str, deque] = defaultdict(deque)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""

        # Extract tenant ID and operation from request
        tenant_id = self._extract_tenant_id(request)
        operation = self._extract_operation(request)

        if not tenant_id or not operation:
            return await call_next(request)

        # Check rate limits
        if await self._is_rate_limited(tenant_id, operation, request):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "operation": operation,
                    "retry_after": 60,
                },
            )

        # Process request
        return await call_next(request)

    def _extract_tenant_id(self, request: Request) -> str | None:
        """Extract tenant ID from request."""
        # Check headers first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # Check path parameters
        if hasattr(request, "path_params"):
            return request.path_params.get("tenant_id")

        return "default"

    def _extract_operation(self, request: Request) -> str | None:
        """Extract operation type from request path."""
        path = request.url.path

        if "/ip" in path:
            if request.method == "POST":
                return "ip_allocation"
            elif request.method == "DELETE":
                return "ip_release"
        elif "/subnet" in path:
            if request.method == "POST":
                return "subnet_creation"
        elif "/pool" in path:
            return "pool_management"

        return "general"

    async def _is_rate_limited(
        self, tenant_id: str, operation: str, request: Request
    ) -> bool:
        """Check if request should be rate limited."""

        # Get limits for this tenant and operation
        limits = self._get_limits(operation, tenant_id)
        max_requests = limits.get("max_requests", 100)
        time_window = limits.get("time_window", 60)

        # Create key for tracking
        client_ip = request.client.host if request.client else "unknown"
        key = f"{tenant_id}:{operation}:{client_ip}"

        # Clean old entries
        await self._cleanup_old_entries()

        # Get current time
        now = time.time()

        # Get request queue for this key
        request_queue = self._request_counts[key]

        # Remove old requests outside time window
        while request_queue and request_queue[0] < now - time_window:
            request_queue.popleft()

        # Check if limit exceeded
        if len(request_queue) >= max_requests:
            return True

        # Add current request
        request_queue.append(now)
        return False

    def _get_limits(self, operation: str, tenant_id: str) -> dict[str, int]:
        """Get rate limits for operation and tenant."""
        # Check for tenant-specific limits first
        if (
            tenant_id in self.tenant_limits
            and operation in self.tenant_limits[tenant_id]
        ):
            return self.tenant_limits[tenant_id][operation]

        # Fall back to default limits
        return self.default_limits.get(
            operation, {"max_requests": 100, "time_window": 60}
        )

    async def _cleanup_old_entries(self):
        """Clean up old rate limiting entries."""
        now = time.time()

        if now - self._last_cleanup < self._cleanup_interval:
            return

        # Clean entries older than maximum time window
        max_window = 300  # 5 minutes
        cutoff = now - max_window

        keys_to_remove = []
        for key, queue in self._request_counts.items():
            # Remove old entries
            while queue and queue[0] < cutoff:
                queue.popleft()

            # Remove empty queues
            if not queue:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._request_counts[key]

        self._last_cleanup = now


# Helper functions for rate limiting decorators


def rate_limit(max_requests: int = 100, time_window_seconds: int = 60):
    """Decorator for rate limiting individual endpoints."""

    def decorator(func):
        func._rate_limit_config = {
            "max_requests": max_requests,
            "time_window": time_window_seconds,
        }
        return func

    return decorator


# Export the middleware
__all__ = ["RateLimitMiddleware", "rate_limit"]
