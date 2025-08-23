"""Rate limiting middleware using Redis for distributed rate limiting."""

import time
import logging
from typing import Callable, Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from dotmac_isp.shared.cache import get_cache_manager

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based rate limiting middleware."""

    def __init__(
        self,
        app,
        default_rate_limit: str = "100/minute",  # "number/time_unit"
        per_ip_limit: str = "60/minute",
        per_user_limit: str = "1000/minute",
        rate_limit_rules: Optional[Dict[str, str]] = None,
        exempt_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.default_rate_limit = self._parse_rate_limit(default_rate_limit)
        self.per_ip_limit = self._parse_rate_limit(per_ip_limit)
        self.per_user_limit = self._parse_rate_limit(per_user_limit)
        self.rate_limit_rules = rate_limit_rules or {}
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/redoc"]
        self.cache_manager = get_cache_manager()

    def _parse_rate_limit(self, rate_limit_str: str) -> Tuple[int, int]:
        """Parse rate limit string like '100/minute' to (count, seconds)."""
        try:
            count_str, time_unit = rate_limit_str.split("/")
            count = int(count_str)

            time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

            seconds = time_units.get(time_unit, 60)  # Default to minute
            return count, seconds

        except (ValueError, AttributeError):
            logger.warning(
                f"Invalid rate limit format: {rate_limit_str}, using default"
            )
            return 100, 60  # Default: 100 per minute

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from auth context
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Try to get tenant ID
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP from X-Forwarded-For header
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_rate_limit_for_path(self, path: str) -> Tuple[int, int]:
        """Get rate limit for specific path."""
        # Check for specific path rules
        for pattern, rate_limit_str in self.rate_limit_rules.items():
            if pattern in path:
                return self._parse_rate_limit(rate_limit_str)

        # Different limits for different endpoint types
        if "/auth/" in path:
            return 10, 60  # 10 per minute for auth endpoints
        elif "/upload" in path:
            return 5, 60  # 5 per minute for uploads
        elif "/payment" in path:
            return 20, 60  # 20 per minute for payments
        elif "/api/v1/" in path:
            return self.default_rate_limit

        return self.default_rate_limit

    def _is_rate_limited(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if client is rate limited using sliding window."""
        current_time = int(time.time())
        window_start = current_time - window

        # Use Redis sorted set for sliding window
        cache_key = f"rate_limit:{key}"

        try:
            # Remove old entries
            self.cache_manager.redis_client.zremrangebyscore(cache_key, 0, window_start)

            # Count current requests in window
            current_count = self.cache_manager.redis_client.zcard(cache_key)

            # Check if limit exceeded
            if current_count >= limit:
                # Calculate reset time
                oldest_entry = self.cache_manager.redis_client.zrange(
                    cache_key, 0, 0, withscores=True
                )
                reset_time = (
                    int(oldest_entry[0][1]) + window
                    if oldest_entry
                    else current_time + window
                )

                return True, {
                    "current_count": current_count,
                    "limit": limit,
                    "reset_time": reset_time,
                    "retry_after": reset_time - current_time,
                }

            # Add current request to window
            self.cache_manager.redis_client.zadd(
                cache_key, {str(current_time): current_time}
            )

            # Set expiration for cleanup
            self.cache_manager.redis_client.expire(cache_key, window + 10)

            return False, {
                "current_count": current_count + 1,
                "limit": limit,
                "reset_time": current_time + window,
                "retry_after": 0,
            }

        except Exception as e:
            logger.error(f"Rate limiting error for key {key}: {e}")
            # Fail open - allow request if Redis is down
            return False, {
                "current_count": 0,
                "limit": limit,
                "reset_time": current_time + window,
                "retry_after": 0,
            }

    def _should_exempt_path(self, path: str) -> bool:
        """Check if path should be exempt from rate limiting."""
        for exempt_path in self.exempt_paths:
            if exempt_path in path:
                return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        path = str(request.url.path)

        # Check if path is exempt
        if self._should_exempt_path(path):
            return await call_next(request)

        # Get client identifier and rate limits
        client_id = self._get_client_identifier(request)
        limit, window = self._get_rate_limit_for_path(path)

        # Check rate limit
        is_limited, rate_info = self._is_rate_limited(client_id, limit, window)

        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {path}: {rate_info['current_count']}/{limit}"
            )

            # Return rate limit error
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info["retry_after"]),
            }

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {rate_info['retry_after']} seconds.",
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, limit - rate_info["current_count"])
        )
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])

        return response


class RateLimitManager:
    """Manager for custom rate limiting scenarios."""

    def __init__(self):
        self.cache_manager = get_cache_manager()

    def check_rate_limit(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for custom key."""
        middleware = RateLimitMiddleware(None)
        return middleware._is_rate_limited(key, limit, window)

    def create_custom_limit(
        self, identifier: str, action: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Create custom rate limit for specific actions."""
        key = f"{identifier}:{action}"
        return self.check_rate_limit(key, limit, window)

    def limit_login_attempts(
        self, ip_address: str, username: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Specific rate limiting for login attempts."""
        # Limit by IP: 10 attempts per 5 minutes
        ip_limited, ip_info = self.check_rate_limit(f"login_ip:{ip_address}", 10, 300)

        # Limit by username: 5 attempts per 5 minutes
        user_limited, user_info = self.check_rate_limit(
            f"login_user:{username}", 5, 300
        )

        if ip_limited or user_limited:
            # Return the more restrictive limit
            if ip_limited and user_limited:
                info = (
                    ip_info
                    if ip_info["retry_after"] > user_info["retry_after"]
                    else user_info
                )
            else:
                info = ip_info if ip_limited else user_info

            return True, info

        return False, user_info

    def limit_password_reset(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """Rate limit password reset requests."""
        # Limit: 3 password resets per hour per email
        return self.check_rate_limit(f"password_reset:{email}", 3, 3600)

    def limit_api_calls(
        self, api_key: str, endpoint: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Rate limit API calls per key and endpoint."""
        # Different limits for different endpoint types
        limits = {
            "upload": (5, 60),  # 5 uploads per minute
            "payment": (20, 60),  # 20 payments per minute
            "data": (100, 60),  # 100 data requests per minute
            "analytics": (50, 60),  # 50 analytics requests per minute
        }

        endpoint_type = "data"  # default
        for type_name in limits.keys():
            if type_name in endpoint:
                endpoint_type = type_name
                break

        limit, window = limits[endpoint_type]
        return self.check_rate_limit(f"api:{api_key}:{endpoint_type}", limit, window)


# Global rate limit manager
rate_limit_manager = RateLimitManager()
