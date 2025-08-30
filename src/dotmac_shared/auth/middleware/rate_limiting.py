"""
Rate Limiting Middleware

Implements comprehensive rate limiting and brute force protection:
- Per-IP rate limiting
- Per-user rate limiting
- Account lockout policies
- Distributed rate limiting with Redis
- Configurable time windows and limits
- Suspicious activity detection
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limiting."""

    IP_BASED = "ip"
    USER_BASED = "user"
    ENDPOINT_BASED = "endpoint"
    GLOBAL = "global"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""

    rule_id: str
    limit_type: RateLimitType
    max_requests: int
    time_window_seconds: int
    endpoints: Optional[List[str]] = None  # Specific endpoints to apply to
    methods: Optional[List[str]] = None  # HTTP methods to apply to
    enabled: bool = True

    def matches_request(self, path: str, method: str) -> bool:
        """Check if rule applies to request."""
        if not self.enabled:
            return False

        if self.endpoints and path not in self.endpoints:
            return False

        if self.methods and method not in self.methods:
            return False

        return True


@dataclass
class RateLimitAttempt:
    """Rate limit attempt record."""

    timestamp: datetime
    ip_address: str
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    user_agent: Optional[str] = None


class RateLimitStore(ABC):
    """Abstract rate limiting storage interface."""

    @abstractmethod
    async def increment_counter(
        self, key: str, window_seconds: int, max_requests: int
    ) -> Tuple[int, bool]:
        """
        Increment rate limit counter.

        Args:
            key: Rate limit key
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed

        Returns:
            Tuple of (current_count, is_allowed)
        """
        pass

    @abstractmethod
    async def get_counter(self, key: str) -> int:
        """Get current counter value."""
        pass

    @abstractmethod
    async def reset_counter(self, key: str) -> bool:
        """Reset counter for key."""
        pass

    @abstractmethod
    async def add_lockout(self, key: str, duration_seconds: int) -> bool:
        """Add lockout for key."""
        pass

    @abstractmethod
    async def is_locked_out(self, key: str) -> bool:
        """Check if key is locked out."""
        pass

    @abstractmethod
    async def remove_lockout(self, key: str) -> bool:
        """Remove lockout for key."""
        pass


class RedisRateLimitStore(RateLimitStore):
    """Redis-based rate limiting storage."""

    def __init__(self, redis_client: Any, key_prefix: str = "ratelimit"):
        """
        Initialize Redis rate limit store.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis keys
        """
        self.redis = redis_client
        self.key_prefix = key_prefix

    def _get_key(self, key: str) -> str:
        """Get Redis key with prefix."""
        return f"{self.key_prefix}:{key}"

    def _get_lockout_key(self, key: str) -> str:
        """Get lockout key."""
        return f"{self.key_prefix}_lockout:{key}"

    async def increment_counter(
        self, key: str, window_seconds: int, max_requests: int
    ) -> Tuple[int, bool]:
        """Increment rate limit counter using sliding window."""
        try:
            redis_key = self._get_key(key)
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=window_seconds)

            # Use Redis sorted set for sliding window
            pipe = self.redis.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start.timestamp())

            # Add current request
            pipe.zadd(redis_key, {str(now.timestamp()): now.timestamp()})

            # Count requests in window
            pipe.zcount(redis_key, window_start.timestamp(), now.timestamp())

            # Set expiration
            pipe.expire(redis_key, window_seconds + 1)

            results = await pipe.execute()
            current_count = results[2]  # zcount result

            is_allowed = current_count <= max_requests

            return current_count, is_allowed

        except Exception as e:
            logger.error(f"Failed to increment rate limit counter: {e}")
            # Fail open - allow request on storage errors
            return 1, True

    async def get_counter(self, key: str) -> int:
        """Get current counter value."""
        try:
            redis_key = self._get_key(key)
            return await self.redis.zcard(redis_key)
        except Exception as e:
            logger.error(f"Failed to get counter: {e}")
            return 0

    async def reset_counter(self, key: str) -> bool:
        """Reset counter for key."""
        try:
            redis_key = self._get_key(key)
            await self.redis.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset counter: {e}")
            return False

    async def add_lockout(self, key: str, duration_seconds: int) -> bool:
        """Add lockout for key."""
        try:
            lockout_key = self._get_lockout_key(key)
            await self.redis.setex(lockout_key, duration_seconds, "locked")
            return True
        except Exception as e:
            logger.error(f"Failed to add lockout: {e}")
            return False

    async def is_locked_out(self, key: str) -> bool:
        """Check if key is locked out."""
        try:
            lockout_key = self._get_lockout_key(key)
            return await self.redis.exists(lockout_key)
        except Exception as e:
            logger.error(f"Failed to check lockout: {e}")
            return False

    async def remove_lockout(self, key: str) -> bool:
        """Remove lockout for key."""
        try:
            lockout_key = self._get_lockout_key(key)
            await self.redis.delete(lockout_key)
            return True
        except Exception as e:
            logger.error(f"Failed to remove lockout: {e}")
            return False


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory rate limiting storage for development."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._counters: Dict[str, List[datetime]] = {}
        self._lockouts: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def increment_counter(
        self, key: str, window_seconds: int, max_requests: int
    ) -> Tuple[int, bool]:
        """Increment rate limit counter."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=window_seconds)

            if key not in self._counters:
                self._counters[key] = []

            # Remove old entries
            self._counters[key] = [
                timestamp
                for timestamp in self._counters[key]
                if timestamp > window_start
            ]

            # Add current request
            self._counters[key].append(now)

            current_count = len(self._counters[key])
            is_allowed = current_count <= max_requests

            return current_count, is_allowed

    async def get_counter(self, key: str) -> int:
        """Get current counter value."""
        async with self._lock:
            return len(self._counters.get(key, []))

    async def reset_counter(self, key: str) -> bool:
        """Reset counter for key."""
        async with self._lock:
            if key in self._counters:
                del self._counters[key]
            return True

    async def add_lockout(self, key: str, duration_seconds: int) -> bool:
        """Add lockout for key."""
        async with self._lock:
            lockout_until = datetime.now(timezone.utc) + timedelta(
                seconds=duration_seconds
            )
            self._lockouts[key] = lockout_until
            return True

    async def is_locked_out(self, key: str) -> bool:
        """Check if key is locked out."""
        async with self._lock:
            if key not in self._lockouts:
                return False

            lockout_until = self._lockouts[key]
            if datetime.now(timezone.utc) >= lockout_until:
                del self._lockouts[key]
                return False

            return True

    async def remove_lockout(self, key: str) -> bool:
        """Remove lockout for key."""
        async with self._lock:
            if key in self._lockouts:
                del self._lockouts[key]
            return True


class RateLimiter:
    """
    Comprehensive rate limiting system.

    Features:
    - Multiple rate limiting strategies
    - Configurable rules per endpoint
    - Account lockout protection
    - Suspicious activity detection
    - Distributed storage support
    """

    def __init__(
        self,
        store: RateLimitStore,
        default_rules: Optional[List[RateLimitRule]] = None,
        lockout_threshold: int = 10,
        lockout_duration_minutes: int = 15,
        enable_lockout: bool = True,
        suspicious_activity_threshold: int = 100,
        log_violations: bool = True,
    ):
        """
        Initialize rate limiter.

        Args:
            store: Rate limiting storage backend
            default_rules: Default rate limiting rules
            lockout_threshold: Failed attempts before lockout
            lockout_duration_minutes: Lockout duration in minutes
            enable_lockout: Enable automatic lockout
            suspicious_activity_threshold: Threshold for suspicious activity
            log_violations: Log rate limit violations
        """
        self.store = store
        self.lockout_threshold = lockout_threshold
        self.lockout_duration_seconds = lockout_duration_minutes * 60
        self.enable_lockout = enable_lockout
        self.suspicious_activity_threshold = suspicious_activity_threshold
        self.log_violations = log_violations

        # Initialize default rules
        self.rules = default_rules or self._get_default_rules()

        logger.info(f"Rate Limiter initialized with {len(self.rules)} rules")

    def _get_default_rules(self) -> List[RateLimitRule]:
        """Get default rate limiting rules."""
        return [
            # Authentication endpoints - stricter limits
            RateLimitRule(
                rule_id="auth_login",
                limit_type=RateLimitType.IP_BASED,
                max_requests=5,
                time_window_seconds=300,  # 5 minutes
                endpoints=["/api/auth/login", "/auth/login"],
                methods=["POST"],
            ),
            RateLimitRule(
                rule_id="auth_mfa",
                limit_type=RateLimitType.USER_BASED,
                max_requests=10,
                time_window_seconds=900,  # 15 minutes
                endpoints=["/api/auth/mfa/validate", "/auth/mfa"],
                methods=["POST"],
            ),
            # Password reset - prevent abuse
            RateLimitRule(
                rule_id="password_reset",
                limit_type=RateLimitType.IP_BASED,
                max_requests=3,
                time_window_seconds=3600,  # 1 hour
                endpoints=["/api/auth/password/reset"],
                methods=["POST"],
            ),
            # API endpoints - moderate limits
            RateLimitRule(
                rule_id="api_general",
                limit_type=RateLimitType.USER_BASED,
                max_requests=1000,
                time_window_seconds=3600,  # 1 hour
                endpoints=None,  # All endpoints
                methods=None,  # All methods
            ),
            # Per-IP global limit
            RateLimitRule(
                rule_id="ip_global",
                limit_type=RateLimitType.IP_BASED,
                max_requests=2000,
                time_window_seconds=3600,  # 1 hour
                endpoints=None,
                methods=None,
            ),
        ]

    def add_rule(self, rule: RateLimitRule):
        """Add rate limiting rule."""
        # Remove existing rule with same ID
        self.rules = [r for r in self.rules if r.rule_id != rule.rule_id]
        self.rules.append(rule)

        logger.info(f"Added rate limiting rule: {rule.rule_id}")

    def remove_rule(self, rule_id: str):
        """Remove rate limiting rule."""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Removed rate limiting rule: {rule_id}")

    async def check_rate_limits(
        self,
        ip_address: str,
        user_id: Optional[str],
        path: str,
        method: str,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Check rate limits for request.

        Args:
            ip_address: Client IP address
            user_id: User identifier (if authenticated)
            path: Request path
            method: HTTP method
            user_agent: User agent string

        Returns:
            Tuple of (is_allowed, rule_violated, retry_after_seconds)
        """
        try:
            # Check lockouts first
            if await self._is_locked_out(ip_address, user_id):
                return False, "lockout", self.lockout_duration_seconds

            # Check each applicable rule
            for rule in self.rules:
                if not rule.matches_request(path, method):
                    continue

                # Generate key based on rule type
                key = self._generate_key(rule, ip_address, user_id, path)

                # Check rate limit
                current_count, is_allowed = await self.store.increment_counter(
                    key, rule.time_window_seconds, rule.max_requests
                )

                if not is_allowed:
                    # Log violation
                    if self.log_violations:
                        logger.warning(
                            f"Rate limit violation: {rule.rule_id} for {ip_address} "
                            f"({current_count}/{rule.max_requests} in {rule.time_window_seconds}s)"
                        )

                    # Check for lockout conditions
                    if self.enable_lockout and await self._should_lockout(
                        ip_address, user_id, current_count
                    ):
                        await self._add_lockout(ip_address, user_id)
                        return False, "lockout", self.lockout_duration_seconds

                    return False, rule.rule_id, rule.time_window_seconds

            return True, None, None

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request on errors
            return True, None, None

    def _generate_key(
        self, rule: RateLimitRule, ip_address: str, user_id: Optional[str], path: str
    ) -> str:
        """Generate rate limiting key."""
        if rule.limit_type == RateLimitType.IP_BASED:
            return f"ip:{self._hash_ip(ip_address)}:{rule.rule_id}"
        elif rule.limit_type == RateLimitType.USER_BASED and user_id:
            return f"user:{user_id}:{rule.rule_id}"
        elif rule.limit_type == RateLimitType.ENDPOINT_BASED:
            return f"endpoint:{path}:{rule.rule_id}"
        elif rule.limit_type == RateLimitType.GLOBAL:
            return f"global:{rule.rule_id}"
        else:
            # Fallback to IP-based
            return f"ip:{self._hash_ip(ip_address)}:{rule.rule_id}"

    def _hash_ip(self, ip_address: str) -> str:
        """Hash IP address for privacy."""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

    async def _is_locked_out(self, ip_address: str, user_id: Optional[str]) -> bool:
        """Check if IP or user is locked out."""
        ip_key = f"lockout:ip:{self._hash_ip(ip_address)}"
        ip_locked = await self.store.is_locked_out(ip_key)

        if user_id:
            user_key = f"lockout:user:{user_id}"
            user_locked = await self.store.is_locked_out(user_key)
            return ip_locked or user_locked

        return ip_locked

    async def _should_lockout(
        self, ip_address: str, user_id: Optional[str], current_count: int
    ) -> bool:
        """Check if lockout should be triggered."""
        # Simple threshold check (can be made more sophisticated)
        return current_count >= self.lockout_threshold

    async def _add_lockout(self, ip_address: str, user_id: Optional[str]):
        """Add lockout for IP and/or user."""
        ip_key = f"lockout:ip:{self._hash_ip(ip_address)}"
        await self.store.add_lockout(ip_key, self.lockout_duration_seconds)

        if user_id:
            user_key = f"lockout:user:{user_id}"
            await self.store.add_lockout(user_key, self.lockout_duration_seconds)

        logger.warning(f"Added lockout for IP {ip_address}, user {user_id}")

    async def remove_lockout(
        self, ip_address: Optional[str] = None, user_id: Optional[str] = None
    ):
        """Remove lockout for IP and/or user."""
        if ip_address:
            ip_key = f"lockout:ip:{self._hash_ip(ip_address)}"
            await self.store.remove_lockout(ip_key)

        if user_id:
            user_key = f"lockout:user:{user_id}"
            await self.store.remove_lockout(user_key)

        logger.info(f"Removed lockout for IP {ip_address}, user {user_id}")

    async def reset_user_limits(self, user_id: str):
        """Reset rate limits for specific user."""
        for rule in self.rules:
            if rule.limit_type == RateLimitType.USER_BASED:
                key = f"user:{user_id}:{rule.rule_id}"
                await self.store.reset_counter(key)

        logger.info(f"Reset rate limits for user {user_id}")

    async def get_user_limit_status(
        self, user_id: str, ip_address: str
    ) -> Dict[str, Any]:
        """Get rate limit status for user."""
        status = {
            "user_id": user_id,
            "ip_address": self._hash_ip(ip_address),
            "is_locked_out": await self._is_locked_out(ip_address, user_id),
            "rules": {},
        }

        for rule in self.rules:
            if rule.limit_type in [RateLimitType.USER_BASED, RateLimitType.IP_BASED]:
                key = self._generate_key(rule, ip_address, user_id, "")
                current_count = await self.store.get_counter(key)

                status["rules"][rule.rule_id] = {
                    "current_count": current_count,
                    "max_requests": rule.max_requests,
                    "time_window_seconds": rule.time_window_seconds,
                    "percentage_used": (current_count / rule.max_requests) * 100,
                }

        return status


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware for rate limiting.

    Automatically applies rate limiting rules to requests and returns
    appropriate HTTP 429 responses for violations.
    """

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        exclude_paths: Optional[List[str]] = None,
        include_headers: bool = True,
        custom_response_handler: Optional[callable] = None,
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: ASGI application
            rate_limiter: Rate limiter instance
            exclude_paths: Paths to exclude from rate limiting
            include_headers: Include rate limit headers in response
            custom_response_handler: Custom response handler for violations
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.exclude_paths = exclude_paths or []
        self.include_headers = include_headers
        self.custom_response_handler = custom_response_handler

        logger.info("Rate Limiting Middleware initialized")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through rate limiter."""
        try:
            # Skip excluded paths
            if request.url.path in self.exclude_paths:
                return await call_next(request)

            # Extract request information
            ip_address = self._get_client_ip(request)
            user_id = self._get_user_id(request)
            path = request.url.path
            method = request.method
            user_agent = request.headers.get("user-agent")

            # Check rate limits
            is_allowed, rule_violated, retry_after = (
                await self.rate_limiter.check_rate_limits(
                    ip_address, user_id, path, method, user_agent
                )
            )

            if not is_allowed:
                # Handle rate limit violation
                if self.custom_response_handler:
                    return await self.custom_response_handler(
                        request, rule_violated, retry_after
                    )

                return self._create_rate_limit_response(rule_violated, retry_after)

            # Process request
            response = await call_next(request)

            # Add rate limit headers if enabled
            if self.include_headers:
                self._add_rate_limit_headers(response, ip_address, user_id)

            return response

        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Continue processing on middleware errors
            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client
        return request.client.host if request.client else "127.0.0.1"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request state."""
        # Check if user is set by authentication middleware
        if hasattr(request.state, "user") and request.state.user:
            if isinstance(request.state.user, dict):
                return request.state.user.get("user_id")
            else:
                return getattr(request.state.user, "user_id", None)

        return None

    def _create_rate_limit_response(
        self, rule_violated: str, retry_after: Optional[int]
    ) -> Response:
        """Create HTTP 429 response for rate limit violations."""
        status_code = HTTP_429_TOO_MANY_REQUESTS
        message = "Rate limit exceeded"

        if rule_violated == "lockout":
            status_code = HTTP_403_FORBIDDEN
            message = "Account temporarily locked due to excessive requests"

        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            headers["X-RateLimit-Reset"] = str(
                int(
                    (
                        datetime.now(timezone.utc) + timedelta(seconds=retry_after)
                    ).timestamp()
                )
            )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": "rate_limit_exceeded",
                "message": message,
                "rule_violated": rule_violated,
                "retry_after": retry_after,
            },
            headers=headers,
        )

    async def _add_rate_limit_headers(
        self, response: Response, ip_address: str, user_id: Optional[str]
    ):
        """Add rate limit headers to response."""
        try:
            # Add basic rate limit information
            response.headers["X-RateLimit-Middleware"] = "dotmac-auth-service"

            if user_id:
                # Get user-specific rate limit status
                status = await self.rate_limiter.get_user_limit_status(
                    user_id, ip_address
                )

                # Add headers for most restrictive rule
                most_restrictive = None
                highest_percentage = 0

                for rule_id, rule_status in status.get("rules", {}).items():
                    percentage = rule_status.get("percentage_used", 0)
                    if percentage > highest_percentage:
                        highest_percentage = percentage
                        most_restrictive = rule_status

                if most_restrictive:
                    response.headers["X-RateLimit-Limit"] = str(
                        most_restrictive["max_requests"]
                    )
                    response.headers["X-RateLimit-Remaining"] = str(
                        max(
                            0,
                            most_restrictive["max_requests"]
                            - most_restrictive["current_count"],
                        )
                    )
                    response.headers["X-RateLimit-Window"] = str(
                        most_restrictive["time_window_seconds"]
                    )

        except Exception as e:
            logger.error(f"Failed to add rate limit headers: {e}")
            # Don't fail the response for header errors
