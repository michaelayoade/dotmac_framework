"""
Rate limiting middleware for API protection.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    """

    def __init__(self):
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed based on rate limit.

        Args:
            key: Unique identifier for rate limiting (e.g., IP + endpoint)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        async with self._lock:
            now = time.time()
            window_start = now - window_seconds

            # Clean old requests
            requests = self._requests[key]
            while requests and requests[0] <= window_start:
                requests.popleft()

            current_count = len(requests)

            if current_count >= limit:
                # Rate limit exceeded
                oldest_request = requests[0] if requests else now
                reset_time = int(oldest_request + window_seconds)

                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": reset_time,
                    "retry_after": max(1, int(reset_time - now))
                }

            # Allow request
            requests.append(now)

            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset": int(now + window_seconds),
                "retry_after": 0
            }

    async def cleanup_expired(self, max_age_seconds: int = 3600):
        """Clean up expired rate limit entries."""
        async with self._lock:
            now = time.time()
            expired_keys = []

            for key, requests in self._requests.items():
                # Remove requests older than max_age
                cutoff = now - max_age_seconds
                while requests and requests[0] <= cutoff:
                    requests.popleft()

                # Remove empty entries
                if not requests:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._requests[key]

            if expired_keys:
                logger.debug("Cleaned up expired rate limit entries", count=len(expired_keys))


class RateLimitConfig:
    """Rate limiting configuration."""

    def __init__(
        self,
        global_limit: int = 1000,
        global_window: int = 60,
        per_ip_limit: int = 100,
        per_ip_window: int = 60,
        per_tenant_limit: int = 500,
        per_tenant_window: int = 60,
        endpoint_limits: Optional[Dict[str, Tuple[int, int]]] = None
    ):
        self.global_limit = global_limit
        self.global_window = global_window
        self.per_ip_limit = per_ip_limit
        self.per_ip_window = per_ip_window
        self.per_tenant_limit = per_tenant_limit
        self.per_tenant_window = per_tenant_window
        self.endpoint_limits = endpoint_limits or {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with multiple rate limiting strategies.
    """

    def __init__(self, app, config: RateLimitConfig):
        super().__init__(app)
        self.config = config
        self.limiter = InMemoryRateLimiter()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def startup(self):
        """Start the middleware."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Rate limiting middleware started")

    async def shutdown(self):
        """Stop the middleware."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Rate limiting middleware stopped")

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)

        # Extract rate limiting keys
        client_ip = self._get_client_ip(request)
        tenant_id = self._get_tenant_id(request)
        endpoint = self._get_endpoint_key(request)

        # Check multiple rate limits
        rate_limit_checks = [
            ("global", "global", self.config.global_limit, self.config.global_window),
            ("ip", client_ip, self.config.per_ip_limit, self.config.per_ip_window),
        ]

        if tenant_id:
            rate_limit_checks.append(
                ("tenant", tenant_id, self.config.per_tenant_limit, self.config.per_tenant_window)
            )

        # Check endpoint-specific limits
        if endpoint in self.config.endpoint_limits:
            limit, window = self.config.endpoint_limits[endpoint]
            rate_limit_checks.append(
                ("endpoint", f"{client_ip}:{endpoint}", limit, window)
            )

        # Apply rate limits
        for limit_type, key, limit, window in rate_limit_checks:
            allowed, info = await self.limiter.is_allowed(key, limit, window)

            if not allowed:
                logger.warning(
                    "Rate limit exceeded",
                    limit_type=limit_type,
                    key=key,
                    limit=limit,
                    window=window,
                    client_ip=client_ip,
                    tenant_id=tenant_id,
                    endpoint=endpoint
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests for {limit_type}",
                        "limit": info["limit"],
                        "remaining": info["remaining"],
                        "reset": info["reset"],
                        "retry_after": info["retry_after"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset"]),
                        "Retry-After": str(info["retry_after"])
                    }
                )

        # Process request
        response = await call_next(request)

        # Add rate limit headers for successful requests
        if hasattr(response, "headers"):
            # Use the most restrictive limit info for headers
            _, info = await self.limiter.is_allowed(
                client_ip,
                self.config.per_ip_limit,
                self.config.per_ip_window
            )

            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        # Try header first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # Try to extract from JWT (simplified)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                import jwt
                token = auth_header[7:]  # Remove "Bearer "
                # Decode without verification for rate limiting purposes only
                payload = jwt.decode(token, options={"verify_signature": False})
                return payload.get("tenant_id")
            except Exception:
                pass

        return None

    def _get_endpoint_key(self, request: Request) -> str:
        """Generate endpoint key for rate limiting."""
        method = request.method
        path = request.url.path

        # Normalize path (remove path parameters)
        normalized_path = path
        for pattern, replacement in [
            (r"/events/\d+", "/events/{id}"),
            (r"/topics/[^/]+", "/topics/{topic}"),
            (r"/admin/topics/[^/]+", "/admin/topics/{topic}"),
        ]:
            import re
            normalized_path = re.sub(pattern, replacement, normalized_path)

        return f"{method}:{normalized_path}"

    async def _cleanup_loop(self):
        """Periodic cleanup of expired rate limit entries."""
        while self._running:
            try:
                await self.limiter.cleanup_expired()
                await asyncio.sleep(300)  # Clean up every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Rate limit cleanup error", error=str(e))
                await asyncio.sleep(60)


def create_default_rate_limit_config() -> RateLimitConfig:
    """Create default rate limiting configuration."""
    return RateLimitConfig(
        global_limit=10000,      # 10k requests per minute globally
        global_window=60,
        per_ip_limit=100,        # 100 requests per minute per IP
        per_ip_window=60,
        per_tenant_limit=1000,   # 1k requests per minute per tenant
        per_tenant_window=60,
        endpoint_limits={
            # Stricter limits for sensitive endpoints
            "POST:/api/v1/events/publish": (50, 60),      # 50 publishes per minute
            "POST:/api/v1/admin/topics": (10, 60),        # 10 topic creations per minute
            "DELETE:/api/v1/admin/topics/{topic}": (5, 60), # 5 deletions per minute
        }
    )


def create_production_rate_limit_config() -> RateLimitConfig:
    """Create production rate limiting configuration."""
    return RateLimitConfig(
        global_limit=50000,      # Higher limits for production
        global_window=60,
        per_ip_limit=500,
        per_ip_window=60,
        per_tenant_limit=5000,
        per_tenant_window=60,
        endpoint_limits={
            "POST:/api/v1/events/publish": (200, 60),
            "POST:/api/v1/admin/topics": (20, 60),
            "DELETE:/api/v1/admin/topics/{topic}": (10, 60),
        }
    )
