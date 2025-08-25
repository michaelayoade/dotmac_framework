"""Redis-based middleware for caching and session management."""

import time
import uuid
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import logging

from dotmac_isp.shared.cache import get_cache_manager, get_session_manager

logger = logging.getLogger(__name__)


class RedisCacheMiddleware(BaseHTTPMiddleware):
    """Middleware for Redis-based HTTP response caching."""

    def __init__(self, app, cache_ttl: int = 300, cache_private: bool = False):
        """  Init   operation."""
        super().__init__(app)
        self.cache_manager = get_cache_manager()
        self.cache_ttl = cache_ttl
        self.cache_private = cache_private
        self.namespace = "http_cache"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle HTTP request with caching."""

        # Skip caching for non-GET requests or private requests
        if request.method != "GET" or self.cache_private:
            return await call_next(request)

        # Skip caching for authenticated requests (if they have auth headers)
        if request.headers.get("authorization"):
            return await call_next(request)

        # Create cache key from URL and query parameters
        cache_key = f"http:{request.url.path}:{str(request.query_params)}"

        # Try to get cached response
        cached_response = self.cache_manager.get(cache_key, self.namespace)
        if cached_response:
            logger.debug(f"Cache HIT for {request.url.path}")
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"],
                media_type=cached_response["media_type"],
            )

        # Execute request
        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            # Read response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Prepare cached response data
            cached_data = {
                "content": response_body.decode() if response_body else "",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type,
            }

            # Store in cache
            self.cache_manager.set(
                cache_key, cached_data, self.cache_ttl, self.namespace
            )
            logger.debug(f"Cache MISS - cached {request.url.path}")

            # Return response with original body
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type,
            )

        return response


class RedisSessionMiddleware(BaseHTTPMiddleware):
    """Middleware for Redis-based session management."""

    def __init__(
        self,
        app,
        session_cookie: str = "session_id",
        secure: bool = False,
        httponly: bool = True,
    ):
        """Initialize Redis session middleware."""
        super().__init__(app)
        self.session_manager = get_session_manager()
        self.session_cookie = session_cookie
        self.secure = secure
        self.httponly = httponly

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle request with session management."""

        # Get session ID from cookie
        session_id = request.cookies.get(self.session_cookie)
        session_data = None

        if session_id:
            session_data = self.session_manager.get_session(session_id)
            if not session_data:
                # Invalid session ID
                session_id = None

        # Create new session if needed
        if not session_id:
            session_id = str(uuid.uuid4())
            session_data = {}

        # Add session data to request state
        request.state.session_id = session_id
        request.state.session = session_data or {}

        # Process request
        response = await call_next(request)

        # Save session data if it was modified
        if (
            hasattr(request.state, "session_modified")
            and request.state.session_modified
        ):
            if request.state.session:
                # Update existing session
                if session_data:
                    self.session_manager.update_session(
                        session_id, request.state.session
                    )
                else:
                    # Create new session
                    self.session_manager.create_session(
                        session_id,
                        request.state.session.get("user_id", "anonymous"),
                        request.state.session,
                    )
            else:
                # Delete session
                self.session_manager.delete_session(session_id)
                response.delete_cookie(self.session_cookie)
                return response

        # Set session cookie
        if not request.cookies.get(self.session_cookie):
            response.set_cookie(
                key=self.session_cookie,
                value=session_id,
                httponly=self.httponly,
                secure=self.secure,
                samesite="lax",
                max_age=1800,  # 30 minutes
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based rate limiting middleware."""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        """  Init   operation."""
        super().__init__(app)
        self.cache_manager = get_cache_manager()
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.namespace = "rate_limit"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle request with rate limiting."""

        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)

        # Check rate limit
        if not self._check_rate_limit(client_id):
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.window_seconds)},
            )

        return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try to get authenticated user ID first
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        try:
            # Get current request count
            key = f"requests:{client_id}"
            current_count = self.cache_manager.get(key, self.namespace) or 0

            if current_count >= self.max_requests:
                return False

            # Increment counter
            new_count = self.cache_manager.increment(key, 1, self.namespace)

            # Set TTL on first request
            if new_count == 1:
                # Reset counter after window expires
                self.cache_manager.redis_client.expire(
                    self.cache_manager._serialize_key(key, self.namespace),
                    self.window_seconds,
                )

            return True

        except Exception as e:
            logger.error(f"Rate limiting error for {client_id}: {e}")
            # Allow request on error
            return True


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests with Redis-based analytics."""

    def __init__(self, app):
        """  Init   operation."""
        super().__init__(app)
        self.cache_manager = get_cache_manager()
        self.namespace = "analytics"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle request with logging and analytics."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log request data
        try:
            self._log_request(request, response, process_time)
        except Exception as e:
            logger.error(f"Request logging error: {e}")

        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)

        return response

    def _log_request(self, request: Request, response: Response, process_time: float):
        """Log request data to Redis for analytics."""
        timestamp = int(time.time())
        date_key = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

        # Log basic request metrics
        metrics = {
            "total_requests": 1,
            "response_times": [process_time],
            f"status_{response.status_code}": 1,
            f"method_{request.method}": 1,
        }

        # Aggregate daily metrics
        for metric, value in metrics.items():
            if metric == "response_times":
                # Store response times for average calculation
                key = f"metrics:{date_key}:response_times"
                self.cache_manager.redis_client.lpush(
                    self.cache_manager._serialize_key(key, self.namespace), process_time
                )
                # Keep only last 1000 response times
                self.cache_manager.redis_client.ltrim(
                    self.cache_manager._serialize_key(key, self.namespace), 0, 999
                )
            else:
                # Increment counters
                key = f"metrics:{date_key}:{metric}"
                self.cache_manager.increment(key, value, self.namespace)

        # Log endpoint-specific metrics
        endpoint_key = f"endpoint:{request.url.path}:{date_key}"
        endpoint_metrics = {
            "requests": 1,
            "avg_response_time": process_time,
            f"status_{response.status_code}": 1,
        }

        for metric, value in endpoint_metrics.items():
            key = f"{endpoint_key}:{metric}"
            if metric == "avg_response_time":
                # Store for average calculation
                self.cache_manager.redis_client.lpush(
                    self.cache_manager._serialize_key(key, self.namespace), process_time
                )
            else:
                self.cache_manager.increment(key, value, self.namespace)


# Helper functions for session management
def get_session(request: Request) -> Dict[str, Any]:
    """Get session data from request."""
    return getattr(request.state, "session", {})


def set_session(request: Request, key: str, value: Any):
    """Set session data."""
    if not hasattr(request.state, "session"):
        request.state.session = {}

    request.state.session[key] = value
    request.state.session_modified = True


def clear_session(request: Request):
    """Clear session data."""
    request.state.session = {}
    request.state.session_modified = True


def get_session_user_id(request: Request) -> Optional[str]:
    """Get user ID from session."""
    session = get_session(request)
    return session.get("user_id")


def set_session_user_id(request: Request, user_id: str):
    """Set user ID in session."""
    set_session(request, "user_id", user_id)
