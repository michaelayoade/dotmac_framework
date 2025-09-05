from datetime import datetime

"""
DRY Rate Limiting Decorators

Provides easy-to-use decorators that leverage the existing comprehensive
rate limiting middleware for individual router endpoints.
"""

import functools
import logging
from collections.abc import Callable
from enum import Enum


class RateLimitType(Enum):
    IP_BASED = "ip_based"
    USER_BASED = "user_based"


# from dotmac_shared.monitoring.base import get_monitoring
# TODO: Add monitoring integration once monitoring is consolidated
from fastapi import HTTPException, Request
from fastapi.security.utils import get_authorization_scheme_param

logger = logging.getLogger(__name__)


class RateLimitDecorators:
    """Singleton class providing rate limiting decorators."""

    _instance = None
    _rate_limiter = None

    def __new__(cls):
        """__new__ operation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """__init__ operation."""
        if self._rate_limiter is None:
            self._initialize_rate_limiter()

        # Initialize monitoring service (placeholder until monitoring is consolidated)
        self._monitoring = None
        self._init_rate_limiting_metrics()

    def _initialize_rate_limiter(self):
        """Initialize the rate limiter with appropriate storage backend."""
        logger.warning(
            "Rate limiting components not available - rate limiting disabled"
        )
        self._rate_limiter = None
        return

        # TODO: Re-enable when rate limiting components are available in dotmac.auth
        # try:
        #     # Try to use Redis first (for production/distributed)
        #     from dotmac_shared.core.redis import get_redis_client

        #     redis_client = get_redis_client()
        #     if redis_client:
        #         store = RedisRateLimitStore(redis_client)
        #         logger.info("Rate limiting using Redis backend")
        #     else:
        #         store = InMemoryRateLimitStore()
        #         logger.info("Rate limiting using in-memory backend")
        # except ImportError:
        #     # Fallback to in-memory
        #     store = InMemoryRateLimitStore()
        #     logger.info("Rate limiting using in-memory backend (no Redis available)")

        # # Default rate limiting rules
        # default_rules = [
        #     # Auth endpoints - strict limits
        #     RateLimitRule(
        #         rule_id="auth_endpoints",
        #         limit_type=RateLimitType.IP_BASED,
        #         max_requests=10,
        #         time_window_seconds=60,
        #         endpoints=["/auth/login", "/auth/register", "/auth/reset-password"],
        #         methods=["POST"],
        #     ),
        #     # API endpoints - moderate limits
        #     RateLimitRule(
        #         rule_id="api_endpoints",
        #         limit_type=RateLimitType.IP_BASED,
        #         max_requests=100,
        #         time_window_seconds=60,
        #         endpoints=None,  # Apply to all
        #         methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        #     ),
        #     # User-specific limits for authenticated users
        #     RateLimitRule(
        #         rule_id="user_specific",
        #         limit_type=RateLimitType.USER_BASED,
        #         max_requests=200,
        #         time_window_seconds=60,
        #     ),
        # ]

        # self._rate_limiter = RateLimiter(
        #     store=store,
        #     default_rules=default_rules,
        #     lockout_threshold=5,
        #     lockout_duration_minutes=15,
        #     enable_lockout=True,
        #     suspicious_activity_threshold=50,
        #     log_violations=True,
        # )

    def _init_rate_limiting_metrics(self):
        """Initialize rate limiting specific metrics."""
        if (
            not self._monitoring
            or not hasattr(self._monitoring, "meter")
            or not self._monitoring.meter
        ):
            logger.warning("Monitoring service not available for rate limiting metrics")
            return

        try:
            # Rate limiting specific metrics
            self.rate_limit_requests_counter = self._monitoring.meter.create_counter(
                name="rate_limit_requests_total",
                description="Total requests checked by rate limiter",
                unit="1",
            )

            self.rate_limit_violations_counter = self._monitoring.meter.create_counter(
                name="rate_limit_violations_total",
                description="Total rate limit violations",
                unit="1",
            )

            self.rate_limit_lockouts_counter = self._monitoring.meter.create_counter(
                name="rate_limit_lockouts_total",
                description="Total account lockouts due to rate limiting",
                unit="1",
            )

            self.rate_limit_remaining_gauge = (
                self._monitoring.meter.create_up_down_counter(
                    name="rate_limit_remaining_requests",
                    description="Remaining requests for current window",
                    unit="1",
                )
            )

            logger.info("Rate limiting metrics initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting metrics: {e}")
            # Set metrics to None so they're skipped in recording
            self.rate_limit_requests_counter = None
            self.rate_limit_violations_counter = None
            self.rate_limit_lockouts_counter = None
            self.rate_limit_remaining_gauge = None

    async def _extract_user_id(self, request: Request) -> str | None:
        """Extract user ID from request for user-based rate limiting."""
        try:
            # Try to get from JWT token
            authorization = request.headers.get("Authorization")
            if authorization:
                scheme, token = get_authorization_scheme_param(authorization)
                if scheme.lower() == "bearer" and token:
                    # Import JWT handling locally to avoid circular imports
                    from dotmac.platform.auth.jwt_handler import decode_token

                    payload = decode_token(token)
                    return payload.get("sub")
        except Exception:
            pass

        # Try to get from session
        return getattr(request.state, "user_id", None)

    def _record_rate_limit_metrics(
        self,
        endpoint: str,
        method: str,
        client_ip: str,
        user_id: str | None,
        is_allowed: bool,
        remaining: int,
    ):
        """Record rate limiting metrics to monitoring system."""
        try:
            # Common labels for metrics
            labels = {
                "endpoint": endpoint,
                "method": method,
                "client_ip": (
                    client_ip[:8] + "..." if len(client_ip) > 8 else client_ip
                ),  # Truncate IP for privacy
                "has_user_id": str(bool(user_id)),
            }

            # Record total requests checked
            if self.rate_limit_requests_counter:
                self.rate_limit_requests_counter.add(1, labels)

            # Record violations if request was denied
            if not is_allowed and self.rate_limit_violations_counter:
                violation_labels = {**labels, "violation_type": "rate_limit_exceeded"}
                self.rate_limit_violations_counter.add(1, violation_labels)

            # Record remaining requests
            if self.rate_limit_remaining_gauge:
                remaining_labels = {**labels, "allowed": str(is_allowed)}
                self.rate_limit_remaining_gauge.add(remaining, remaining_labels)

        except Exception as e:
            logger.error(f"Failed to record rate limiting metrics: {e}")

    def _record_lockout_metric(
        self, client_ip: str, user_id: str | None, reason: str
    ):
        """Record account lockout metrics."""
        try:
            if self.rate_limit_lockouts_counter:
                labels = {
                    "client_ip": (
                        client_ip[:8] + "..." if len(client_ip) > 8 else client_ip
                    ),
                    "has_user_id": str(bool(user_id)),
                    "reason": reason,
                }
                self.rate_limit_lockouts_counter.add(1, labels)
        except Exception as e:
            logger.error(f"Failed to record lockout metric: {e}")

    def rate_limit(
        self,
        max_requests: int | None = None,
        time_window_seconds: int | None = None,
        rule_type: RateLimitType = RateLimitType.IP_BASED,
        custom_message: str | None = None,
    ):
        """
        Decorator for applying rate limiting to individual endpoints.

        Args:
            max_requests: Maximum requests allowed (defaults to rule-based limits)
            time_window_seconds: Time window in seconds (defaults to 60)
            rule_type: Type of rate limiting (IP, user, etc.)
            custom_message: Custom error message

        Example:
            @router.get("/api/data")
            @rate_limit(max_requests=50, time_window_seconds=60)
            async def get_data():
                return {"data": "value"}
        """

        def decorator(func: Callable) -> Callable:
            """decorator operation."""

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request from args (FastAPI dependency injection pattern)
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                if not request:
                    # Try to find request in kwargs
                    request = kwargs.get("request")

                if not request:
                    logger.warning(
                        f"No request object found for rate limiting in {func.__name__}"
                    )
                    return await func(*args, **kwargs)

                # Get client IP
                client_ip = request.client.host if request.client else "unknown"

                # Get user ID if needed
                user_id = None
                if rule_type == RateLimitType.USER_BASED:
                    user_id = await self._extract_user_id(request)

                # Check rate limit
                try:
                    (
                        is_allowed,
                        remaining,
                        reset_time,
                    ) = await self._rate_limiter.is_request_allowed(
                        ip_address=client_ip,
                        user_id=user_id,
                        endpoint=str(request.url.path),
                        method=request.method,
                    )

                    # Record metrics
                    self._record_rate_limit_metrics(
                        endpoint=str(request.url.path),
                        method=request.method,
                        client_ip=client_ip,
                        user_id=user_id,
                        is_allowed=is_allowed,
                        remaining=remaining,
                    )

                    if not is_allowed:
                        message = (
                            custom_message
                            or "Rate limit exceeded. Please try again later."
                        )

                        # Add rate limit headers
                        headers = {
                            "X-RateLimit-Limit": str(max_requests or 100),
                            "X-RateLimit-Remaining": str(remaining),
                            "Retry-After": str(
                                int((reset_time - datetime.now()).total_seconds())
                            ),
                        }

                        raise HTTPException(
                            status_code=429,
                            detail={
                                "error": "RATE_LIMIT_EXCEEDED",
                                "message": message,
                                "retry_after": int(
                                    (reset_time - datetime.now()).total_seconds()
                                ),
                            },
                            headers=headers,
                        )

                    # Add rate limit info to response headers (will be added by middleware)
                    request.state.rate_limit_remaining = remaining
                    request.state.rate_limit_reset = reset_time

                except Exception as e:
                    logger.error(f"Rate limiting error in {func.__name__}: {e}")
                    # Continue execution if rate limiting fails (fail-open policy)

                return await func(*args, **kwargs)

            return wrapper

        return decorator


# Global instance for easy import
_decorators = RateLimitDecorators()


# Placeholder middleware class
class RateLimitMiddleware:
    """Placeholder middleware class for rate limiting."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


def create_rate_limiter():
    """Placeholder function to create rate limiter."""
    return None


# Export commonly used decorators
def rate_limit(
    max_requests: int | None = None,
    time_window_seconds: int = 60,
    rule_type: RateLimitType = RateLimitType.IP_BASED,
    custom_message: str | None = None,
):
    """Standard rate limiting decorator."""
    return _decorators.rate_limit(
        max_requests, time_window_seconds, rule_type, custom_message
    )


def rate_limit_strict(max_requests: int = 10, time_window_seconds: int = 60):
    """Strict rate limiting for sensitive endpoints."""
    return _decorators.rate_limit(
        max_requests=max_requests,
        time_window_seconds=time_window_seconds,
        rule_type=RateLimitType.IP_BASED,
        custom_message="Too many requests to this sensitive endpoint. Please wait before trying again.",
    )


def rate_limit_auth(max_requests: int = 5, time_window_seconds: int = 60):
    """Rate limiting specifically for auth endpoints."""
    return _decorators.rate_limit(
        max_requests=max_requests,
        time_window_seconds=time_window_seconds,
        rule_type=RateLimitType.IP_BASED,
        custom_message="Too many authentication attempts. Please wait before trying again.",
    )


def rate_limit_user(max_requests: int = 200, time_window_seconds: int = 60):
    """User-based rate limiting for authenticated endpoints."""
    return _decorators.rate_limit(
        max_requests=max_requests,
        time_window_seconds=time_window_seconds,
        rule_type=RateLimitType.USER_BASED,
        custom_message="You have exceeded your request quota. Please wait before making more requests.",
    )
