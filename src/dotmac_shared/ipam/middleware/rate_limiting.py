"""
IPAM Rate Limiting Middleware - Protect allocation endpoints from abuse.
"""

import asyncio
import hashlib
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    HTTPException = None
    Request = None
    JSONResponse = None


class IPAMRateLimiter:
    """
    Rate limiter for IPAM operations with multiple rate limiting strategies.

    Supports both Redis-backed distributed rate limiting and in-memory
    rate limiting for single-instance deployments.
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        default_limits: Optional[Dict[str, Dict[str, int]]] = None,
        key_prefix: str = "ipam_rate_limit",
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting
            default_limits: Default rate limits per operation type
            key_prefix: Redis key prefix
        """
        self.redis_client = redis_client if REDIS_AVAILABLE else None
        self.key_prefix = key_prefix
        self.use_redis = self.redis_client is not None

        # In-memory storage for non-Redis mode
        self._memory_store = defaultdict(list)
        self._lock = asyncio.Lock()

        # Default rate limits per operation
        self.default_limits = default_limits or {
            "allocate_ip": {
                "requests": 100,  # requests per window
                "window": 3600,  # window in seconds (1 hour)
                "burst": 10,  # burst allowance
            },
            "reserve_ip": {"requests": 200, "window": 3600, "burst": 20},
            "release_allocation": {"requests": 50, "window": 3600, "burst": 5},
            "create_network": {"requests": 10, "window": 3600, "burst": 2},
            "bulk_allocation": {"requests": 5, "window": 3600, "burst": 1},
        }

        # Per-tenant custom limits
        self.tenant_limits: Dict[str, Dict[str, Dict[str, int]]] = {}

    def set_tenant_limits(self, tenant_id: str, limits: Dict[str, Dict[str, int]]):
        """Set custom rate limits for a specific tenant."""
        self.tenant_limits[tenant_id] = limits

    def _get_limits(self, operation: str, tenant_id: str) -> Dict[str, int]:
        """Get rate limits for operation and tenant."""
        # Check for tenant-specific limits first
        if (
            tenant_id in self.tenant_limits
            and operation in self.tenant_limits[tenant_id]
        ):
            return self.tenant_limits[tenant_id][operation]

        # Fall back to default limits
        return self.default_limits.get(
            operation, {"requests": 50, "window": 3600, "burst": 5}
        )

    def _generate_key(
        self, operation: str, tenant_id: str, user_id: Optional[str] = None
    ) -> str:
        """Generate rate limiting key."""
        key_parts = [self.key_prefix, operation, tenant_id]
        if user_id:
            key_parts.append(user_id)
        return ":".join(key_parts)

    async def _check_rate_limit_redis(
        self, key: str, limits: Dict[str, int], current_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check rate limit using Redis backend."""
        if not self.use_redis:
            return {"allowed": True, "remaining": limits["requests"]}

        if current_time is None:
            current_time = time.time()

        window = limits["window"]
        max_requests = limits["requests"]
        burst_allowance = limits.get("burst", max_requests // 10)

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        window_start = int(current_time - window)

        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(current_time): current_time})

        # Set expiration
        pipe.expire(key, window + 60)  # Extra 60 seconds buffer

        results = pipe.execute()
        current_count = results[1]

        # Check if within limits
        effective_limit = max_requests + burst_allowance
        allowed = current_count <= effective_limit

        if not allowed:
            # Remove the request we just added since it's rejected
            self.redis_client.zrem(key, str(current_time))

        return {
            "allowed": allowed,
            "remaining": max(0, effective_limit - current_count),
            "reset_time": int(current_time + window),
            "current_count": current_count,
            "limit": effective_limit,
        }

    async def _check_rate_limit_memory(
        self, key: str, limits: Dict[str, int], current_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check rate limit using in-memory storage."""
        if current_time is None:
            current_time = time.time()

        window = limits["window"]
        max_requests = limits["requests"]
        burst_allowance = limits.get("burst", max_requests // 10)

        async with self._lock:
            # Clean expired entries
            window_start = current_time - window
            self._memory_store[key] = [
                timestamp
                for timestamp in self._memory_store[key]
                if timestamp > window_start
            ]

            current_count = len(self._memory_store[key])
            effective_limit = max_requests + burst_allowance

            if current_count < effective_limit:
                self._memory_store[key].append(current_time)
                allowed = True
                remaining = effective_limit - (current_count + 1)
            else:
                allowed = False
                remaining = 0

            return {
                "allowed": allowed,
                "remaining": remaining,
                "reset_time": int(current_time + window),
                "current_count": current_count + (1 if allowed else 0),
                "limit": effective_limit,
            }

    async def check_rate_limit(
        self,
        operation: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check if operation is within rate limits.

        Args:
            operation: Operation type (e.g., 'allocate_ip')
            tenant_id: Tenant identifier
            user_id: Optional user identifier for per-user limiting
            current_time: Optional current timestamp

        Returns:
            Dict with rate limit status and metadata
        """
        limits = self._get_limits(operation, tenant_id)
        key = self._generate_key(operation, tenant_id, user_id)

        if self.use_redis:
            return await self._check_rate_limit_redis(key, limits, current_time)
        else:
            return await self._check_rate_limit_memory(key, limits, current_time)

    async def reset_rate_limit(
        self, operation: str, tenant_id: str, user_id: Optional[str] = None
    ):
        """Reset rate limit for specific key (admin operation)."""
        key = self._generate_key(operation, tenant_id, user_id)

        if self.use_redis:
            await self.redis_client.delete(key)
        else:
            async with self._lock:
                if key in self._memory_store:
                    del self._memory_store[key]

    async def get_rate_limit_status(
        self, operation: str, tenant_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current rate limit status without incrementing counter."""
        limits = self._get_limits(operation, tenant_id)
        key = self._generate_key(operation, tenant_id, user_id)
        current_time = time.time()

        if self.use_redis:
            window_start = int(current_time - limits["window"])
            self.redis_client.zremrangebyscore(key, 0, window_start)
            current_count = self.redis_client.zcard(key)

            effective_limit = limits["requests"] + limits.get(
                "burst", limits["requests"] // 10
            )

            return {
                "current_count": current_count,
                "limit": effective_limit,
                "remaining": max(0, effective_limit - current_count),
                "reset_time": int(current_time + limits["window"]),
                "window": limits["window"],
            }
        else:
            async with self._lock:
                window_start = current_time - limits["window"]
                valid_requests = [
                    timestamp
                    for timestamp in self._memory_store[key]
                    if timestamp > window_start
                ]

                current_count = len(valid_requests)
                effective_limit = limits["requests"] + limits.get(
                    "burst", limits["requests"] // 10
                )

                return {
                    "current_count": current_count,
                    "limit": effective_limit,
                    "remaining": max(0, effective_limit - current_count),
                    "reset_time": int(current_time + limits["window"]),
                    "window": limits["window"],
                }


class IPAMRateLimitMiddleware:
    """FastAPI middleware for IPAM rate limiting."""

    def __init__(self, rate_limiter: IPAMRateLimiter, enabled: bool = True):
        """Initialize middleware with rate limiter."""
        self.rate_limiter = rate_limiter
        self.enabled = enabled

        # Map endpoints to operations
        self.endpoint_operations = {
            "/api/ipam/allocations": "allocate_ip",
            "/api/ipam/reservations": "reserve_ip",
            "/api/ipam/networks": "create_network",
            "/api/ipam/bulk-allocations": "bulk_allocation",
        }

    def _extract_tenant_id(self, request: Any) -> str:
        """Extract tenant ID from request."""
        # Try various methods to get tenant ID
        if hasattr(request, "headers"):
            tenant_id = request.headers.get("X-Tenant-ID")
            if tenant_id:
                return tenant_id

        # Try from path parameters
        if hasattr(request, "path_params"):
            tenant_id = request.path_params.get("tenant_id")
            if tenant_id:
                return tenant_id

        # Try from query parameters
        if hasattr(request, "query_params"):
            tenant_id = request.query_params.get("tenant_id")
            if tenant_id:
                return tenant_id

        # Default fallback
        return "default"

    def _extract_user_id(self, request: Any) -> Optional[str]:
        """Extract user ID from request."""
        if hasattr(request, "headers"):
            user_id = request.headers.get("X-User-ID")
            if user_id:
                return user_id

        # Try to get from JWT or other auth mechanism
        if hasattr(request, "state") and hasattr(request.state, "user"):
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "id"):
                return str(user.id)

        return None

    def _get_operation_from_request(self, request: Any) -> Optional[str]:
        """Map request to operation type."""
        if not hasattr(request, "url"):
            return None

        path = str(request.url.path)
        method = request.method if hasattr(request, "method") else "GET"

        # Map based on path and method
        for endpoint_pattern, operation in self.endpoint_operations.items():
            if endpoint_pattern in path:
                if method == "POST":
                    return operation
                elif method == "DELETE" and "allocations" in path:
                    return "release_allocation"

        return None

    async def __call__(self, request: Any, call_next: Callable) -> Any:
        """Process request through rate limiting."""
        if not (self.enabled and FASTAPI_AVAILABLE):
            return await call_next(request)

        operation = self._get_operation_from_request(request)

        # Only apply rate limiting to IPAM operations
        if not operation:
            return await call_next(request)

        tenant_id = self._extract_tenant_id(request)
        user_id = self._extract_user_id(request)

        # Check rate limit
        try:
            rate_limit_result = await self.rate_limiter.check_rate_limit(
                operation, tenant_id, user_id
            )

            if not rate_limit_result["allowed"]:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many {operation} requests",
                        "retry_after": rate_limit_result["reset_time"]
                        - int(time.time()),
                        "limit": rate_limit_result["limit"],
                        "remaining": 0,
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(rate_limit_result["reset_time"]),
                        "Retry-After": str(
                            rate_limit_result["reset_time"] - int(time.time())
                        ),
                    },
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
                response.headers["X-RateLimit-Remaining"] = str(
                    rate_limit_result["remaining"]
                )
                response.headers["X-RateLimit-Reset"] = str(
                    rate_limit_result["reset_time"]
                )

            return response

        except Exception as e:
            # Rate limiting failed, allow request through but log error
            import logging

            logging.getLogger(__name__).error(f"Rate limiting error: {e}")
            return await call_next(request)


# Utility functions for integration
def create_redis_rate_limiter(redis_url: str, **kwargs) -> IPAMRateLimiter:
    """Create rate limiter with Redis backend."""
    if not REDIS_AVAILABLE:
        raise ImportError("Redis is required for distributed rate limiting")

    redis_client = redis.from_url(redis_url)
    return IPAMRateLimiter(redis_client=redis_client, **kwargs)


def create_memory_rate_limiter(**kwargs) -> IPAMRateLimiter:
    """Create rate limiter with in-memory backend."""
    return IPAMRateLimiter(redis_client=None, **kwargs)
