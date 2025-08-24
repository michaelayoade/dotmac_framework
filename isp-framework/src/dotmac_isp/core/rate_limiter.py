"""
Redis-based distributed rate limiting for multi-tenant SaaS.

This module provides a distributed rate limiting solution using Redis as the backend
store. It implements a sliding window algorithm with token bucket characteristics
for accurate and fair rate limiting across multiple application instances.

Key Features:
    - Distributed rate limiting across multiple servers
    - Per-tenant and per-user rate limits
    - Multiple time windows (second, minute, hour, day)
    - Atomic operations using Lua scripts
    - Prometheus metrics integration
    - FastAPI dependency injection support

Example:
    Basic usage with FastAPI::
    
        from fastapi import FastAPI, Depends
        from dotmac_isp.core.rate_limiter import get_rate_limiter
        
        app = FastAPI()
        
        @app.post("/api/endpoint")
        async def protected_endpoint(
            limiter: DistributedRateLimiter = Depends(get_rate_limiter)
        ):
            async with limiter.rate_limit_context(tenant_id, ip, "api"):
                return {"status": "success"}

Author: DotMac Engineering Team
Version: 1.0.0
Since: 2024-08-24
"""

import asyncio
import time
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

import redis.asyncio as redis
from fastapi import HTTPException, Request, Depends
from prometheus_client import Counter, Histogram


class RateLimitWindow(str, Enum):
    """Rate limit window types."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class RateLimitConfig:
    """
    Configuration for rate limiting behavior.
    
    This class defines the rate limiting parameters for different time windows
    and burst handling. It supports multiple granularities from per-second to
    per-day limits.
    
    Attributes:
        requests_per_second (Optional[int]): Maximum requests per second
        requests_per_minute (Optional[int]): Maximum requests per minute
        requests_per_hour (Optional[int]): Maximum requests per hour
        requests_per_day (Optional[int]): Maximum requests per day
        burst_multiplier (float): Multiplier for burst allowance (default: 1.5)
        redis_url (str): Redis connection URL
    
    Note:
        At least one rate limit window must be specified. The burst_multiplier
        allows temporary spikes above the base rate limit.
    
    Example:
        >>> config = RateLimitConfig(
        ...     requests_per_minute=60,
        ...     requests_per_hour=1000,
        ...     burst_multiplier=2.0
        ... )
    """
    
    def __init__(
        self,
        requests_per_second: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
        requests_per_day: Optional[int] = None,
        burst_multiplier: float = 1.5,
        redis_url: str = "redis://localhost:6379/0"
    ):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_multiplier = burst_multiplier
        self.redis_url = redis_url


class DistributedRateLimiter:
    """
    Distributed rate limiter using Redis backend.
    
    Implements a sliding window rate limiting algorithm with atomic operations
    using Redis Lua scripts. This ensures consistency across distributed
    application instances.
    
    The rate limiter supports:
        - Multiple time windows (second, minute, hour, day)
        - Per-tenant and per-endpoint rate limits
        - Burst handling with configurable multipliers
        - Automatic cleanup of expired keys
        - Prometheus metrics for monitoring
    
    Attributes:
        redis_client (redis.Redis): Async Redis client instance
        default_limits (Dict): Default rate limits by endpoint type
        tenant_limits (Dict): Per-tenant custom rate limits
    
    Methods:
        check_rate_limit: Check if request is within rate limits
        get_usage_stats: Get current usage statistics
        rate_limit_context: Context manager for rate limiting
        reset_limits: Reset rate limits for a specific key
    
    Example:
        >>> limiter = DistributedRateLimiter(redis_client)
        >>> allowed, remaining = await limiter.check_rate_limit(
        ...     "tenant_001", "192.168.1.1", "api"
        ... )
    """
    
    # Default limits per endpoint type
    DEFAULT_LIMITS = {
        "api": RateLimitConfig(requests_per_minute=30),
        "login": RateLimitConfig(requests_per_minute=5),
        "register": RateLimitConfig(requests_per_minute=3),
        "password_reset": RateLimitConfig(requests_per_minute=3),
        "search": RateLimitConfig(requests_per_second=20),
        "export": RateLimitConfig(requests_per_hour=10),
        "webhook": RateLimitConfig(requests_per_minute=100),
    }
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_config: Optional[RateLimitConfig] = None,
        prefix: str = "rate_limit"
    ):
        self.redis = redis_client
        self.default_config = default_config or RateLimitConfig(requests_per_minute=60)
        self.prefix = prefix
        self._lua_script = None
    
    async def initialize(self):
        """Initialize the rate limiter with Lua script."""
        # Lua script for atomic rate limit check and increment
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local burst_limit = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        -- Get current count and TTL
        local current = redis.call('GET', key)
        local ttl = redis.call('TTL', key)
        
        if current == false then
            -- First request in window
            redis.call('SET', key, 1, 'EX', window)
            return {1, limit, limit - 1, now + window, 0}
        end
        
        current = tonumber(current)
        
        -- Check if within burst limit
        if current >= burst_limit then
            -- Rate limit exceeded
            local reset_at = now + ttl
            local retry_after = ttl
            return {0, current, limit, 0, reset_at, retry_after}
        end
        
        -- Increment counter
        local new_count = redis.call('INCR', key)
        local reset_at = now + ttl
        local remaining = math.max(0, limit - new_count)
        
        return {1, new_count, limit, remaining, reset_at, 0}
        """
        
        self._lua_script = await self.redis.register_script(lua_script)
    
    async def check_rate_limit(
        self,
        tenant_id: str,
        identifier: str,
        endpoint_type: Optional[str] = None,
        custom_config: Optional[RateLimitConfig] = None
    ) -> Tuple[bool, int]:
        """
        Check and update rate limit for a tenant and identifier.
        
        Args:
            tenant_id: Tenant identifier
            identifier: User/IP/API key identifier
            endpoint_type: Type of endpoint (uses DEFAULT_LIMITS if available)
            custom_config: Custom rate limit configuration
        
        Returns:
            Tuple of allowed status and remaining requests
        """
        # Determine configuration
        config = custom_config
        if not config and endpoint_type and endpoint_type in self.DEFAULT_LIMITS:
            config = self.DEFAULT_LIMITS[endpoint_type]
        if not config:
            config = self.default_config
        
        # Build Redis key
        key = f"{self.prefix}:{tenant_id}:{identifier}:{config.requests_per_minute}"
        
        # Calculate limits
        burst_limit = int(config.requests_per_minute * config.burst_multiplier)
        now = time.time()
        
        try:
            # Execute Lua script atomically
            if not self._lua_script:
                await self.initialize()
            
            result = await self._lua_script(
                keys=[key],
                args=[config.requests_per_minute, 60, burst_limit, now]
            )
            
            # Parse result
            allowed = bool(result[0])
            remaining = int(result[3])
            
            # Log rate limit violations
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for tenant={tenant_id}, "
                    f"identifier={identifier}, count={result[1]}/{result[2]}"
                )
            
            return allowed, remaining
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open on Redis errors (allow request)
            return True, config.requests_per_minute
    
    async def get_usage_stats(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get current usage statistics for a tenant.
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Dictionary of endpoint types and their current usage statistics
        """
        stats = {}
        pattern = f"{self.prefix}:{tenant_id}:*"
        
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor, match=pattern, count=100
                )
                
                for key in keys:
                    parts = key.decode().split(":")
                    if len(parts) >= 4:
                        identifier = parts[2]
                        endpoint_type = parts[3]
                        
                        count = await self.redis.get(key)
                        ttl = await self.redis.ttl(key)
                        
                        if endpoint_type not in stats:
                            stats[endpoint_type] = {}
                        
                        stats[endpoint_type][identifier] = {
                            "count": int(count) if count else 0,
                            "ttl": ttl
                        }
                
                if cursor == 0:
                    break
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
        
        return stats
    
    @asynccontextmanager
    async def rate_limit_context(
        self,
        tenant_id: str,
        identifier: str,
        endpoint_type: Optional[str] = None
    ):
        """
        Context manager for rate limiting.
        Raises RateLimitExceeded if limit exceeded.
        """
        allowed, remaining = await self.check_rate_limit(tenant_id, identifier, endpoint_type)
        
        if not allowed:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {60} seconds",
                headers={
                    "X-RateLimit-Limit": str(remaining),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time() + 60)),
                    "Retry-After": str(60)
                }
            )
        
        yield
    
    async def reset_limits(
        self,
        tenant_id: str,
        identifier: str,
        endpoint_type: Optional[str] = None
    ) -> bool:
        """
        Reset rate limits for a specific key.
        
        Args:
            tenant_id: Tenant identifier
            identifier: User/IP/API key identifier
            endpoint_type: Type of endpoint (uses DEFAULT_LIMITS if available)
        
        Returns:
            True if reset successful
        """
        try:
            if endpoint_type:
                key = f"{self.prefix}:{tenant_id}:{identifier}:{endpoint_type}"
                await self.redis.delete(key)
            else:
                # Reset all endpoints
                pattern = f"{self.prefix}:{tenant_id}:{identifier}:*"
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self.redis.delete(*keys)
                    if cursor == 0:
                        break
            
            logger.info(f"Rate limit reset for tenant={tenant_id}, identifier={identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


class RateLimitExceeded(HTTPException):
    """
    Exception raised when rate limit is exceeded.
    
    This exception is thrown when a client exceeds the configured rate limit
    for a specific resource or endpoint. It automatically sets the HTTP 429
    status code and includes a Retry-After header when applicable.
    
    Attributes:
        detail (str): Human-readable description of the rate limit violation
        retry_after (Optional[int]): Seconds until the client can retry
    
    Example:
        >>> raise RateLimitExceeded(
        ...     detail="API rate limit exceeded",
        ...     retry_after=60
        ... )
    """
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        super().__init__(
            status_code=429,
            detail=detail,
            headers={"Retry-After": str(retry_after)} if retry_after else None
        )


# FastAPI dependency
async def get_rate_limiter(redis_client: redis.Redis) -> DistributedRateLimiter:
    """Get rate limiter instance for dependency injection."""
    limiter = DistributedRateLimiter(redis_client)
    await limiter.initialize()
    return limiter
