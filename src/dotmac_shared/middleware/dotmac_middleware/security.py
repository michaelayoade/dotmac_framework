"""
Unified security middleware components for DotMac Framework.

This module consolidates security middleware implementations from:
- ISP Framework security middleware
- Management Platform security middleware
- Shared security components

Provides consistent security posture across all applications.
"""

import hashlib
import html
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import quote

import structlog
from fastapi import HTTPException, Request, Response, status
from starlette.datastructures import FormData
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


@dataclass
class SecurityConfig:
    """Configuration for security middleware components."""

    # CSRF Protection
    csrf_secret_key: str | None = None
    csrf_token_lifetime: int = 3600  # 1 hour
    csrf_excluded_paths: list[str] = field(default_factory=lambda: ["/health", "/metrics"])
    csrf_safe_methods: set[str] = field(default_factory=lambda: {"GET", "HEAD", "OPTIONS"})

    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst_size: int = 200
    rate_limit_storage_backend: str = "memory"  # "memory" or "redis"
    rate_limit_excluded_paths: list[str] = field(default_factory=list)

    # Security Headers
    content_security_policy: str | None = None
    strict_transport_security: str = "max-age=31536000; includeSubDomains"
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    referrer_policy: str = "strict-origin-when-cross-origin"

    # Input Validation
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_field_length: int = 10000
    allowed_content_types: set[str] = field(
        default_factory=lambda: {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        }
    )

    # XSS Protection
    xss_protection_enabled: bool = True
    html_sanitization_enabled: bool = True

    # Environment settings
    environment: str = "production"
    debug_mode: bool = False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Unified security headers middleware.

    Consolidates security header implementations from ISP and Management frameworks.
    """

    def __init__(self, app, config: SecurityConfig | None = None):
        super().__init__(app)
        self.config = config or SecurityConfig()

        # Generate CSP if not provided
        if not self.config.content_security_policy:
            self.config.content_security_policy = self._generate_default_csp()

    def _generate_default_csp(self) -> str:
        """Generate environment-appropriate Content Security Policy."""
        if self.config.environment == "production":
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # More permissive for development
            return "default-src 'self' 'unsafe-inline' 'unsafe-eval' data:; " "frame-ancestors 'none'"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add comprehensive security headers to all responses."""
        response = await call_next(request)

        # Core security headers
        response.headers["X-Content-Type-Options"] = self.config.x_content_type_options
        response.headers["X-Frame-Options"] = self.config.x_frame_options
        response.headers["Referrer-Policy"] = self.config.referrer_policy

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.config.content_security_policy

        # HTTPS-only headers for production
        if self.config.environment == "production":
            response.headers["Strict-Transport-Security"] = self.config.strict_transport_security

        # XSS Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Cross-Site Request Forgery protection middleware.

    Provides token-based CSRF protection with proper validation.
    """

    def __init__(self, app, config: SecurityConfig | None = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.secret_key = self.config.csrf_secret_key or secrets.token_hex(32)
        self._token_cache: dict[str, float] = {}

    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token."""
        timestamp = str(int(time.time()))
        random_data = secrets.token_hex(16)

        # Create token with timestamp for expiration
        token_data = f"{timestamp}:{random_data}"
        signature = hashlib.sha256((token_data + self.secret_key).encode()).hexdigest()

        return f"{token_data}:{signature}"

    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token and check expiration."""
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return False

            timestamp_str, random_data, signature = parts
            timestamp = int(timestamp_str)

            # Check expiration
            if time.time() - timestamp > self.config.csrf_token_lifetime:
                return False

            # Verify signature
            expected_data = f"{timestamp_str}:{random_data}"
            expected_signature = hashlib.sha256((expected_data + self.secret_key).encode()).hexdigest()

            return secrets.compare_digest(signature, expected_signature)

        except (ValueError, TypeError):
            return False

    def _should_check_csrf(self, request: Request) -> bool:
        """Determine if request should be checked for CSRF."""
        # Skip safe methods
        if request.method in self.config.csrf_safe_methods:
            return False

        # Skip excluded paths
        path = request.url.path
        for excluded_path in self.config.csrf_excluded_paths:
            if path.startswith(excluded_path):
                return False

        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CSRF protection."""
        if not self._should_check_csrf(request):
            response = await call_next(request)
            # Add CSRF token to safe requests for future use
            csrf_token = self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token
            return response

        # Extract CSRF token from headers or form data
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            # Try to get from form data
            try:
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
            except Exception:
                pass

        if not csrf_token or not self._validate_csrf_token(csrf_token):
            logger.warning(
                "CSRF token validation failed",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else None,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed",
            )

        response = await call_next(request)

        # Provide new token for next request
        new_token = self._generate_csrf_token()
        response.headers["X-CSRF-Token"] = new_token

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with sliding window implementation.

    Provides protection against API abuse and DoS attacks.
    """

    def __init__(self, app, config: SecurityConfig | None = None):
        super().__init__(app)
        self.config = config or SecurityConfig()

        # In-memory storage (should be Redis in production)
        self._request_counts: dict[str, list[float]] = {}
        self._blocked_ips: dict[str, float] = {}

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Use X-Forwarded-For if available (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited using sliding window."""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old entries
        if client_id in self._request_counts:
            self._request_counts[client_id] = [
                timestamp for timestamp in self._request_counts[client_id] if timestamp > window_start
            ]
        else:
            self._request_counts[client_id] = []

        # Check current request count
        request_count = len(self._request_counts[client_id])

        if request_count >= self.config.rate_limit_requests_per_minute:
            # Block client for additional time
            self._blocked_ips[client_id] = current_time + 300  # 5 minutes
            return True

        # Add current request
        self._request_counts[client_id].append(current_time)
        return False

    def _is_blocked(self, client_id: str) -> bool:
        """Check if client is currently blocked."""
        if client_id in self._blocked_ips:
            if time.time() < self._blocked_ips[client_id]:
                return True
            else:
                # Remove expired block
                del self._blocked_ips[client_id]
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip excluded paths
        path = request.url.path
        for excluded_path in self.config.rate_limit_excluded_paths:
            if path.startswith(excluded_path):
                return await call_next(request)

        client_id = self._get_client_identifier(request)

        # Check if client is blocked
        if self._is_blocked(client_id):
            logger.warning("Blocked client attempted request", client_id=client_id, path=path)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "300"},
            )

        # Check rate limit
        if self._is_rate_limited(client_id):
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=path,
                method=request.method,
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Input validation and sanitization middleware.

    Provides protection against various injection attacks.
    """

    def __init__(self, app, config: SecurityConfig | None = None):
        super().__init__(app)
        self.config = config or SecurityConfig()

        # Dangerous patterns to detect
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b)",
            r"(\b(UNION|HAVING|ORDER BY)\b)",
            r"(--|\#|\/\*|\*\/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        ]

        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
        ]

    def _validate_content_type(self, request: Request) -> bool:
        """Validate request content type."""
        content_type = request.headers.get("Content-Type", "")

        # Extract base content type (ignore charset, boundary, etc.)
        base_type = content_type.split(";")[0].strip().lower()

        return base_type in self.config.allowed_content_types

    def _check_request_size(self, request: Request) -> bool:
        """Check if request size is within limits."""
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                return size <= self.config.max_request_size
            except ValueError:
                return False
        return True

    def _detect_sql_injection(self, text: str) -> bool:
        """Detect potential SQL injection attempts."""
        text_upper = text.upper()
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        return False

    def _detect_xss(self, text: str) -> bool:
        """Detect potential XSS attempts."""
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string input."""
        if not self.config.html_sanitization_enabled:
            return text

        # HTML escape
        sanitized = html.escape(text)

        # Additional URL encoding for special cases
        sanitized = quote(sanitized, safe="")

        return sanitized

    async def _validate_form_data(self, form_data: FormData) -> None:
        """Validate form data fields."""
        for field_name, field_value in form_data.items():
            if isinstance(field_value, str):
                # Check field length
                if len(field_value) > self.config.max_field_length:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Field '{field_name}' exceeds maximum length",
                    )

                # Check for malicious patterns
                if self._detect_sql_injection(field_value):
                    logger.warning(
                        "SQL injection attempt detected",
                        field=field_name,
                        value=field_value[:100],
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid input detected",
                    )

                if self._detect_xss(field_value):
                    logger.warning(
                        "XSS attempt detected",
                        field=field_name,
                        value=field_value[:100],
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid input detected",
                    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with input validation."""
        # Validate content type
        if request.method in {"POST", "PUT", "PATCH"}:
            if not self._validate_content_type(request):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported content type",
                )

        # Check request size
        if not self._check_request_size(request):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large",
            )

        # Validate form data if present
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                content_type = request.headers.get("Content-Type", "")
                if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
                    form_data = await request.form()
                    await self._validate_form_data(form_data)
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Error validating form data", error=str(e))

        return await call_next(request)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Unified security middleware that combines all security components.

    This is a convenience middleware that applies multiple security measures.
    """

    def __init__(self, app, config: SecurityConfig | None = None):
        super().__init__(app)
        self.config = config or SecurityConfig()

        # Initialize individual components
        self.headers_middleware = SecurityHeadersMiddleware(app, config)
        self.csrf_middleware = CSRFMiddleware(app, config)
        self.rate_limit_middleware = RateLimitingMiddleware(app, config)
        self.input_validation_middleware = InputValidationMiddleware(app, config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply all security middleware components."""

        # Create a pipeline of security checks
        async def headers_handler(req: Request) -> Response:
            return await self.headers_middleware.dispatch(req, call_next)

        async def csrf_handler(req: Request) -> Response:
            return await self.csrf_middleware.dispatch(req, headers_handler)

        async def rate_limit_handler(req: Request) -> Response:
            return await self.rate_limit_middleware.dispatch(req, csrf_handler)

        # Start the security pipeline
        return await self.input_validation_middleware.dispatch(request, rate_limit_handler)
