"""
Comprehensive API Rate Limiting with Tenant-Aware Quotas
Provides advanced rate limiting, quota management, and abuse prevention

SECURITY: This module prevents API abuse, DoS attacks, and ensures fair resource usage
"""

import asyncio
import hashlib
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

import redis

logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Types of rate limits"""

    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_TENANT = "per_tenant"
    PER_ENDPOINT = "per_endpoint"
    GLOBAL = "global"


class QuotaPeriod(str, Enum):
    """Quota time periods"""

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


@dataclass
class RateLimit:
    """Rate limit configuration"""

    requests: int
    period: QuotaPeriod
    burst_requests: Optional[int] = None  # Allow burst up to this limit
    cooldown_seconds: Optional[int] = None  # Cooldown after limit hit


@dataclass
class TenantQuota:
    """Tenant-specific API quotas"""

    tenant_id: str
    tier: str  # basic, premium, enterprise
    daily_requests: int
    hourly_requests: int
    minute_requests: int
    concurrent_connections: int
    burst_allowance: int
    priority_weight: float = 1.0  # Higher = better treatment


@dataclass
class RateLimitResult:
    """Result of rate limit check"""

    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after_seconds: Optional[int] = None
    quota_exceeded: bool = False
    reason: Optional[str] = None


class RedisRateLimiter:
    """
    Redis-based rate limiter with advanced features
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        redis_url: str = "redis://localhost:6379/1",
        key_prefix: str = "dotmac_rate_limit:",
        enable_metrics: bool = True,
    ):
        self.redis_client = redis_client or redis.from_url(
            redis_url, decode_responses=True
        )
        self.key_prefix = key_prefix
        self.enable_metrics = enable_metrics

        # Default rate limits by tier
        self.tenant_quotas = {
            "basic": TenantQuota(
                tenant_id="",
                tier="basic",
                daily_requests=10000,
                hourly_requests=1000,
                minute_requests=50,
                concurrent_connections=10,
                burst_allowance=100,
                priority_weight=1.0,
            ),
            "premium": TenantQuota(
                tenant_id="",
                tier="premium",
                daily_requests=100000,
                hourly_requests=10000,
                minute_requests=200,
                concurrent_connections=50,
                burst_allowance=500,
                priority_weight=2.0,
            ),
            "enterprise": TenantQuota(
                tenant_id="",
                tier="enterprise",
                daily_requests=1000000,
                hourly_requests=100000,
                minute_requests=1000,
                concurrent_connections=200,
                burst_allowance=2000,
                priority_weight=3.0,
            ),
        }

    def _get_redis_key(
        self, limit_type: RateLimitType, identifier: str, period: QuotaPeriod
    ) -> str:
        """Generate Redis key for rate limit tracking"""
        timestamp = self._get_period_timestamp(period)
        return f"{self.key_prefix}{limit_type.value}:{identifier}:{period.value}:{timestamp}"

    def _get_period_timestamp(self, period: QuotaPeriod) -> int:
        """Get timestamp aligned to period boundary"""
        now = datetime.now()

        if period == QuotaPeriod.SECOND:
            return int(now.timestamp())
        elif period == QuotaPeriod.MINUTE:
            return int(now.replace(second=0, microsecond=0).timestamp())
        elif period == QuotaPeriod.HOUR:
            return int(now.replace(minute=0, second=0, microsecond=0).timestamp())
        elif period == QuotaPeriod.DAY:
            return int(
                now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            )
        elif period == QuotaPeriod.MONTH:
            return int(
                now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                ).timestamp()
            )

        return int(now.timestamp())

    def _get_period_duration(self, period: QuotaPeriod) -> int:
        """Get period duration in seconds"""
        durations = {
            QuotaPeriod.SECOND: 1,
            QuotaPeriod.MINUTE: 60,
            QuotaPeriod.HOUR: 3600,
            QuotaPeriod.DAY: 86400,
            QuotaPeriod.MONTH: 2592000,  # 30 days
        }
        return durations[period]

    async def check_rate_limit(
        self,
        limit_type: RateLimitType,
        identifier: str,
        rate_limit: RateLimit,
        cost: int = 1,
        tenant_quota: Optional[TenantQuota] = None,
    ) -> RateLimitResult:
        """
        Check if request is within rate limits
        """
        try:
            redis_key = self._get_redis_key(limit_type, identifier, rate_limit.period)
            period_duration = self._get_period_duration(rate_limit.period)

            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Check current count
            pipe.get(redis_key)
            pipe.ttl(redis_key)
            current_data = pipe.execute()

            current_count = int(current_data[0] or 0)
            ttl = current_data[1]

            # Calculate remaining quota
            effective_limit = rate_limit.requests

            # Apply tenant quota if provided
            if tenant_quota:
                if rate_limit.period == QuotaPeriod.DAY:
                    effective_limit = min(effective_limit, tenant_quota.daily_requests)
                elif rate_limit.period == QuotaPeriod.HOUR:
                    effective_limit = min(effective_limit, tenant_quota.hourly_requests)
                elif rate_limit.period == QuotaPeriod.MINUTE:
                    effective_limit = min(effective_limit, tenant_quota.minute_requests)

            # Check if adding cost would exceed limit
            new_count = current_count + cost

            if new_count > effective_limit:
                # Check burst allowance
                burst_limit = rate_limit.burst_requests or effective_limit
                if tenant_quota:
                    burst_limit = min(burst_limit, tenant_quota.burst_allowance)

                if new_count > burst_limit:
                    # Calculate retry after
                    if ttl > 0:
                        retry_after = ttl
                    else:
                        retry_after = period_duration

                    reset_time = datetime.now() + timedelta(seconds=retry_after)

                    return RateLimitResult(
                        allowed=False,
                        remaining=max(0, effective_limit - current_count),
                        reset_time=reset_time,
                        retry_after_seconds=retry_after,
                        quota_exceeded=True,
                        reason=f"Rate limit exceeded: {current_count}/{effective_limit} requests",
                    )

            # Allow request - increment counter
            pipe = self.redis_client.pipeline()
            pipe.incrby(redis_key, cost)

            # Set expiry if this is a new key
            if ttl == -2:  # Key doesn't exist
                pipe.expire(redis_key, period_duration)

            pipe.execute()

            # Calculate reset time
            reset_time = datetime.now() + timedelta(
                seconds=ttl if ttl > 0 else period_duration
            )

            return RateLimitResult(
                allowed=True,
                remaining=max(0, effective_limit - new_count),
                reset_time=reset_time,
                quota_exceeded=False,
            )

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiter is unavailable
            return RateLimitResult(
                allowed=True,
                remaining=rate_limit.requests,
                reset_time=datetime.now() + timedelta(hours=1),
                reason=f"Rate limiter error: {str(e)}",
            )

    async def check_multiple_limits(
        self,
        checks: List[tuple[RateLimitType, str, RateLimit, int]],
        tenant_quota: Optional[TenantQuota] = None,
    ) -> List[RateLimitResult]:
        """Check multiple rate limits concurrently"""
        tasks = []

        for limit_type, identifier, rate_limit, cost in checks:
            task = self.check_rate_limit(
                limit_type, identifier, rate_limit, cost, tenant_quota
            )
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def get_tenant_quota(self, tenant_id: str) -> TenantQuota:
        """Get or create tenant quota configuration"""
        try:
            # Try to get from Redis cache first
            quota_key = f"{self.key_prefix}quota:{tenant_id}"
            cached_quota = self.redis_client.get(quota_key)

            if cached_quota:
                quota_data = json.loads(cached_quota)
                return TenantQuota(**quota_data)

            # Get tenant tier (this would normally come from database)
            # For now, default to basic
            tier = await self._get_tenant_tier(tenant_id)
            quota = self.tenant_quotas[tier]
            quota.tenant_id = tenant_id

            # Cache for 1 hour
            self.redis_client.setex(quota_key, 3600, json.dumps(asdict(quota)))

            return quota

        except Exception as e:
            logger.error(f"Error getting tenant quota: {e}")
            # Return basic quota as fallback
            quota = self.tenant_quotas["basic"]
            quota.tenant_id = tenant_id
            return quota

    async def _get_tenant_tier(self, tenant_id: str) -> str:
        """Get tenant tier from database or configuration"""
        # This would integrate with your tenant management system
        # For now, return basic
        return "basic"

    async def record_metrics(
        self, result: RateLimitResult, limit_type: RateLimitType, identifier: str
    ):
        """Record rate limiting metrics for monitoring"""
        if not self.enable_metrics:
            return

        try:
            metrics_key = f"{self.key_prefix}metrics:{limit_type.value}:{datetime.now().strftime('%Y%m%d%H')}"

            pipe = self.redis_client.pipeline()
            pipe.hincrby(metrics_key, "total_requests", 1)

            if not result.allowed:
                pipe.hincrby(metrics_key, "blocked_requests", 1)
                pipe.hincrby(
                    metrics_key,
                    "quota_exceeded" if result.quota_exceeded else "rate_limited",
                    1,
                )

            pipe.expire(metrics_key, 86400 * 7)  # Keep metrics for 7 days
            pipe.execute()

        except Exception as e:
            logger.error(f"Error recording metrics: {e}")

    async def get_rate_limit_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get current rate limit status for a tenant"""
        try:
            quota = await self.get_tenant_quota(tenant_id)

            # Check current usage across different periods
            current_usage = {}

            for period in [QuotaPeriod.MINUTE, QuotaPeriod.HOUR, QuotaPeriod.DAY]:
                key = self._get_redis_key(RateLimitType.PER_TENANT, tenant_id, period)
                usage = int(self.redis_client.get(key) or 0)
                ttl = self.redis_client.ttl(key)

                current_usage[period.value] = {
                    "used": usage,
                    "reset_in_seconds": ttl if ttl > 0 else 0,
                }

            return {
                "tenant_id": tenant_id,
                "tier": quota.tier,
                "quotas": {
                    "daily": quota.daily_requests,
                    "hourly": quota.hourly_requests,
                    "minute": quota.minute_requests,
                    "concurrent": quota.concurrent_connections,
                    "burst": quota.burst_allowance,
                },
                "current_usage": current_usage,
                "priority_weight": quota.priority_weight,
            }

        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"error": str(e)}


class APIRateLimitMiddleware:
    """
    FastAPI middleware for API rate limiting
    """

    def __init__(
        self,
        app,
        rate_limiter: RedisRateLimiter,
        default_rate_limits: Dict[str, RateLimit],
        get_tenant_id: Callable[[Request], Optional[str]],
        get_user_id: Callable[[Request], Optional[str]],
        exempt_paths: Optional[List[str]] = None,
        enable_per_endpoint_limits: bool = True,
    ):
        self.app = app
        self.rate_limiter = rate_limiter
        self.default_rate_limits = default_rate_limits
        self.get_tenant_id = get_tenant_id
        self.get_user_id = get_user_id
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]
        self.enable_per_endpoint_limits = enable_per_endpoint_limits

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting"""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    async def get_request_cost(self, request: Request) -> int:
        """Calculate request cost (default 1, can be higher for expensive operations)"""
        # Expensive operations cost more
        if request.method in ["POST", "PUT", "PATCH"]:
            return 2
        elif request.method == "DELETE":
            return 3
        elif "/export" in request.url.path or "/report" in request.url.path:
            return 5
        else:
            return 1

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Skip exempt paths
            if self.is_exempt(request.url.path):
                await self.app(scope, receive, send)
                return

            try:
                # Extract identifiers
                tenant_id = self.get_tenant_id(request)
                user_id = self.get_user_id(request)
                client_ip = request.client.host if request.client else "unknown"

                # Calculate request cost
                request_cost = await self.get_request_cost(request)

                # Get tenant quota
                tenant_quota = None
                if tenant_id:
                    tenant_quota = await self.rate_limiter.get_tenant_quota(tenant_id)

                # Prepare rate limit checks
                checks = []

                # Per-IP limit (prevent abuse from single IP)
                if "per_ip" in self.default_rate_limits:
                    checks.append(
                        (
                            RateLimitType.PER_IP,
                            client_ip,
                            self.default_rate_limits["per_ip"],
                            request_cost,
                        )
                    )

                # Per-tenant limit
                if tenant_id and "per_tenant" in self.default_rate_limits:
                    checks.append(
                        (
                            RateLimitType.PER_TENANT,
                            tenant_id,
                            self.default_rate_limits["per_tenant"],
                            request_cost,
                        )
                    )

                # Per-user limit
                if user_id and "per_user" in self.default_rate_limits:
                    checks.append(
                        (
                            RateLimitType.PER_USER,
                            user_id,
                            self.default_rate_limits["per_user"],
                            request_cost,
                        )
                    )

                # Per-endpoint limit
                if (
                    self.enable_per_endpoint_limits
                    and "per_endpoint" in self.default_rate_limits
                ):
                    endpoint_key = f"{request.method}:{request.url.path}"
                    checks.append(
                        (
                            RateLimitType.PER_ENDPOINT,
                            endpoint_key,
                            self.default_rate_limits["per_endpoint"],
                            request_cost,
                        )
                    )

                # Check all rate limits
                if checks:
                    results = await self.rate_limiter.check_multiple_limits(
                        checks, tenant_quota
                    )

                    # Find any failed checks
                    failed_check = next((r for r in results if not r.allowed), None)

                    if failed_check:
                        # Record metrics
                        await self.rate_limiter.record_metrics(
                            failed_check,
                            RateLimitType.PER_TENANT,
                            tenant_id or client_ip,
                        )

                        # Return rate limit error
                        error_response = JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={
                                "error": "Rate limit exceeded",
                                "message": failed_check.reason,
                                "retry_after": failed_check.retry_after_seconds,
                                "reset_time": failed_check.reset_time.isoformat(),
                                "remaining": failed_check.remaining,
                            },
                            headers={
                                "Retry-After": str(
                                    failed_check.retry_after_seconds or 60
                                ),
                                "X-RateLimit-Remaining": str(failed_check.remaining),
                                "X-RateLimit-Reset": str(
                                    int(failed_check.reset_time.timestamp())
                                ),
                            },
                        )
                        await error_response(scope, receive, send)
                        return

                    # Add rate limit headers to successful responses
                    best_result = min(results, key=lambda r: r.remaining)

                    async def send_wrapper(message):
                        if message["type"] == "http.response.start":
                            headers = dict(message.get("headers", []))
                            headers.update(
                                {
                                    b"x-ratelimit-remaining": str(
                                        best_result.remaining
                                    ).encode(),
                                    b"x-ratelimit-reset": str(
                                        int(best_result.reset_time.timestamp())
                                    ).encode(),
                                }
                            )
                            message["headers"] = list(headers.items())

                        await send(message)

                    await self.app(scope, receive, send_wrapper)
                else:
                    await self.app(scope, receive, send)

            except Exception as e:
                logger.error(f"Rate limiting middleware error: {e}")
                # Fail open - allow request if middleware fails
                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


# Factory functions
def create_rate_limiter(
    redis_url: str = "redis://localhost:6379/1", **kwargs
) -> RedisRateLimiter:
    """Create a Redis rate limiter instance"""
    return RedisRateLimiter(redis_url=redis_url, **kwargs)


def create_rate_limit_middleware(
    rate_limiter: RedisRateLimiter,
    default_rate_limits: Dict[str, RateLimit],
    get_tenant_id: Callable[[Request], Optional[str]],
    get_user_id: Callable[[Request], Optional[str]],
    **kwargs,
) -> Callable:
    """Factory for creating rate limit middleware"""

    def middleware_factory(app):
        """middleware_factory operation."""
        return APIRateLimitMiddleware(
            app=app,
            rate_limiter=rate_limiter,
            default_rate_limits=default_rate_limits,
            get_tenant_id=get_tenant_id,
            get_user_id=get_user_id,
            **kwargs,
        )

    return middleware_factory


# Default rate limit configurations
DEFAULT_RATE_LIMITS = {
    "per_ip": RateLimit(requests=1000, period=QuotaPeriod.HOUR, burst_requests=1500),
    "per_user": RateLimit(requests=500, period=QuotaPeriod.HOUR, burst_requests=750),
    "per_tenant": RateLimit(
        requests=10000, period=QuotaPeriod.HOUR, burst_requests=15000
    ),
    "per_endpoint": RateLimit(
        requests=100, period=QuotaPeriod.MINUTE, burst_requests=150
    ),
}
