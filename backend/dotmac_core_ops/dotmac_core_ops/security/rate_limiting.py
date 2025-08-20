"""
Rate limiting per tenant with sliding window and token bucket algorithms.
"""

import asyncio
import time
from typing import Any, Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field

import structlog

from .tenant_isolation import TenantContext

logger = structlog.get_logger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_second: float = 10.0
    requests_per_minute: float = 600.0
    requests_per_hour: float = 36000.0
    burst_capacity: int = 100

    # Sliding window configuration
    window_size_seconds: int = 60

    # Token bucket configuration
    bucket_capacity: int = 100
    refill_rate: float = 10.0  # tokens per second


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: int
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.time)

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_retry_after(self, tokens: int = 1) -> float:
        """Get time to wait before retry."""
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class SlidingWindow:
    """Sliding window for rate limiting."""

    window_size: int
    requests: deque = field(default_factory=deque)

    def add_request(self, timestamp: float):
        """Add a request to the window."""
        self.requests.append(timestamp)
        self._cleanup_old_requests(timestamp)

    def get_request_count(self, timestamp: float) -> int:
        """Get current request count in the window."""
        self._cleanup_old_requests(timestamp)
        return len(self.requests)

    def _cleanup_old_requests(self, current_time: float):
        """Remove requests outside the window."""
        cutoff_time = current_time - self.window_size

        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()


class TenantRateLimiter:
    """Rate limiter with per-tenant limits."""

    def __init__(self, default_config: RateLimitConfig):
        self.default_config = default_config
        self.tenant_configs: Dict[str, RateLimitConfig] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, Dict[str, SlidingWindow]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def set_tenant_config(self, tenant_id: str, config: RateLimitConfig):
        """Set rate limit configuration for a specific tenant."""
        async with self._lock:
            self.tenant_configs[tenant_id] = config

            # Reset existing bucket and windows for this tenant
            self.token_buckets.pop(tenant_id, None)
            self.sliding_windows.pop(tenant_id, None)

        logger.info(
            "Rate limit config updated for tenant",
            tenant_id=tenant_id,
            requests_per_second=config.requests_per_second,
            burst_capacity=config.burst_capacity
        )

    async def check_rate_limit(
        self,
        tenant_context: TenantContext,
        operation: str = "api_request",
        tokens: int = 1
    ) -> bool:
        """Check if request is within rate limits."""
        tenant_id = tenant_context.tenant_id
        config = self.tenant_configs.get(tenant_id, self.default_config)

        current_time = time.time()

        # Check token bucket (burst protection)
        bucket_key = f"{tenant_id}:bucket"
        if bucket_key not in self.token_buckets:
            self.token_buckets[bucket_key] = TokenBucket(
                capacity=config.bucket_capacity,
                tokens=config.bucket_capacity,
                refill_rate=config.refill_rate
            )

        bucket = self.token_buckets[bucket_key]
        if not bucket.consume(tokens):
            retry_after = bucket.get_retry_after(tokens)
            raise RateLimitExceeded(
                f"Token bucket rate limit exceeded for tenant {tenant_id}",
                retry_after=retry_after
            )

        # Check sliding windows
        await self._check_sliding_window_limits(tenant_id, config, current_time, operation)

        logger.debug(
            "Rate limit check passed",
            tenant_id=tenant_id,
            operation=operation,
            tokens=tokens,
            bucket_tokens=bucket.tokens
        )

        return True

    async def _check_sliding_window_limits(
        self,
        tenant_id: str,
        config: RateLimitConfig,
        current_time: float,
        operation: str
    ):
        """Check sliding window rate limits."""
        windows = self.sliding_windows[tenant_id]

        # Check per-second limit
        second_key = f"{operation}:second"
        if second_key not in windows:
            windows[second_key] = SlidingWindow(window_size=1)

        second_window = windows[second_key]
        if second_window.get_request_count(current_time) >= config.requests_per_second:
            raise RateLimitExceeded(
                f"Per-second rate limit exceeded for tenant {tenant_id}",
                retry_after=1.0
            )

        # Check per-minute limit
        minute_key = f"{operation}:minute"
        if minute_key not in windows:
            windows[minute_key] = SlidingWindow(window_size=60)

        minute_window = windows[minute_key]
        if minute_window.get_request_count(current_time) >= config.requests_per_minute:
            raise RateLimitExceeded(
                f"Per-minute rate limit exceeded for tenant {tenant_id}",
                retry_after=60.0
            )

        # Check per-hour limit
        hour_key = f"{operation}:hour"
        if hour_key not in windows:
            windows[hour_key] = SlidingWindow(window_size=3600)

        hour_window = windows[hour_key]
        if hour_window.get_request_count(current_time) >= config.requests_per_hour:
            raise RateLimitExceeded(
                f"Per-hour rate limit exceeded for tenant {tenant_id}",
                retry_after=3600.0
            )

        # Add request to all windows
        second_window.add_request(current_time)
        minute_window.add_request(current_time)
        hour_window.add_request(current_time)

    async def get_rate_limit_status(
        self,
        tenant_context: TenantContext,
        operation: str = "api_request"
    ) -> Dict[str, Any]:
        """Get current rate limit status for a tenant."""
        tenant_id = tenant_context.tenant_id
        config = self.tenant_configs.get(tenant_id, self.default_config)
        current_time = time.time()

        # Token bucket status
        bucket_key = f"{tenant_id}:bucket"
        bucket = self.token_buckets.get(bucket_key)
        bucket_status = {
            "capacity": config.bucket_capacity,
            "available_tokens": bucket.tokens if bucket else config.bucket_capacity,
            "refill_rate": config.refill_rate
        }

        # Sliding window status
        windows = self.sliding_windows.get(tenant_id, {})
        window_status = {}

        for period, limit in [
            ("second", config.requests_per_second),
            ("minute", config.requests_per_minute),
            ("hour", config.requests_per_hour)
        ]:
            window_key = f"{operation}:{period}"
            window = windows.get(window_key)

            if window:
                current_count = window.get_request_count(current_time)
                window_status[period] = {
                    "limit": limit,
                    "used": current_count,
                    "remaining": max(0, limit - current_count),
                    "reset_time": current_time + (1 if period == "second" else 60 if period == "minute" else 3600)
                }
            else:
                window_status[period] = {
                    "limit": limit,
                    "used": 0,
                    "remaining": limit,
                    "reset_time": current_time + (1 if period == "second" else 60 if period == "minute" else 3600)
                }

        return {
            "tenant_id": tenant_id,
            "operation": operation,
            "token_bucket": bucket_status,
            "sliding_windows": window_status,
            "timestamp": current_time
        }

    async def cleanup_expired_data(self):
        """Clean up expired rate limiting data."""
        current_time = time.time()

        async with self._lock:
            # Clean up old sliding window data
            for tenant_id, windows in list(self.sliding_windows.items()):
                for window_key, window in list(windows.items()):
                    window._cleanup_old_requests(current_time)

                    # Remove empty windows
                    if not window.requests:
                        del windows[window_key]

                # Remove empty tenant entries
                if not windows:
                    del self.sliding_windows[tenant_id]

        logger.debug("Rate limiter cleanup completed")


class RateLimitMiddleware:
    """Middleware for applying rate limits to requests."""

    def __init__(self, rate_limiter: TenantRateLimiter):
        self.rate_limiter = rate_limiter

    async def __call__(
        self,
        tenant_context: TenantContext,
        operation: str,
        handler: callable,
        *args,
        **kwargs
    ):
        """Apply rate limiting to a request."""
        try:
            # Check rate limits
            await self.rate_limiter.check_rate_limit(tenant_context, operation)

            # Execute the handler
            return await handler(*args, **kwargs)

        except RateLimitExceeded as e:
            logger.warning(
                "Rate limit exceeded",
                tenant_id=tenant_context.tenant_id,
                operation=operation,
                error=str(e),
                retry_after=e.retry_after
            )
            raise


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits based on system load."""

    def __init__(self, base_limiter: TenantRateLimiter):
        self.base_limiter = base_limiter
        self.system_load_factor = 1.0
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._adaptation_lock = asyncio.Lock()

    async def update_system_load(self, load_factor: float):
        """Update system load factor (0.0 to 2.0)."""
        async with self._adaptation_lock:
            self.system_load_factor = max(0.1, min(2.0, load_factor))

        logger.info("System load factor updated", load_factor=self.system_load_factor)

    async def record_error(self, tenant_id: str, error_type: str):
        """Record an error for adaptive rate limiting."""
        current_time = time.time()
        self.error_rates[tenant_id].append((current_time, error_type))

    async def get_adaptive_config(self, tenant_id: str) -> RateLimitConfig:
        """Get adaptive rate limit configuration."""
        base_config = self.base_limiter.tenant_configs.get(
            tenant_id,
            self.base_limiter.default_config
        )

        # Calculate error rate
        current_time = time.time()
        recent_errors = [
            (ts, error_type) for ts, error_type in self.error_rates[tenant_id]
            if current_time - ts < 300  # Last 5 minutes
        ]

        error_rate = len(recent_errors) / 300.0  # errors per second

        # Adjust limits based on system load and error rate
        load_adjustment = 1.0 / self.system_load_factor
        error_adjustment = max(0.1, 1.0 - (error_rate * 10))  # Reduce limits if high error rate

        adjustment_factor = load_adjustment * error_adjustment

        return RateLimitConfig(
            requests_per_second=base_config.requests_per_second * adjustment_factor,
            requests_per_minute=base_config.requests_per_minute * adjustment_factor,
            requests_per_hour=base_config.requests_per_hour * adjustment_factor,
            burst_capacity=int(base_config.burst_capacity * adjustment_factor),
            bucket_capacity=int(base_config.bucket_capacity * adjustment_factor),
            refill_rate=base_config.refill_rate * adjustment_factor
        )

    async def check_adaptive_rate_limit(
        self,
        tenant_context: TenantContext,
        operation: str = "api_request",
        tokens: int = 1
    ) -> bool:
        """Check rate limits with adaptive configuration."""
        # Get adaptive configuration
        adaptive_config = await self.get_adaptive_config(tenant_context.tenant_id)

        # Temporarily set the adaptive config
        original_config = self.base_limiter.tenant_configs.get(tenant_context.tenant_id)
        await self.base_limiter.set_tenant_config(tenant_context.tenant_id, adaptive_config)

        try:
            return await self.base_limiter.check_rate_limit(tenant_context, operation, tokens)
        finally:
            # Restore original config if it existed
            if original_config:
                await self.base_limiter.set_tenant_config(tenant_context.tenant_id, original_config)


# Default rate limit configurations for different tenant tiers
DEFAULT_RATE_LIMITS = {
    "free": RateLimitConfig(
        requests_per_second=1.0,
        requests_per_minute=60.0,
        requests_per_hour=3600.0,
        burst_capacity=10,
        bucket_capacity=10,
        refill_rate=1.0
    ),
    "basic": RateLimitConfig(
        requests_per_second=5.0,
        requests_per_minute=300.0,
        requests_per_hour=18000.0,
        burst_capacity=50,
        bucket_capacity=50,
        refill_rate=5.0
    ),
    "premium": RateLimitConfig(
        requests_per_second=20.0,
        requests_per_minute=1200.0,
        requests_per_hour=72000.0,
        burst_capacity=200,
        bucket_capacity=200,
        refill_rate=20.0
    ),
    "enterprise": RateLimitConfig(
        requests_per_second=100.0,
        requests_per_minute=6000.0,
        requests_per_hour=360000.0,
        burst_capacity=1000,
        bucket_capacity=1000,
        refill_rate=100.0
    )
}
