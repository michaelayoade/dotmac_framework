"""Enhanced security middleware for DotMac ISP Framework.

This module provides comprehensive security protection including:
- Enhanced security headers
- Input validation and sanitization
- CSRF protection
- Request size limiting
- XSS protection
"""

import logging
import re
import secrets
import hashlib
import time
import html
from typing import Callable, Dict, Any, Optional, List, Set
from urllib.parse import quote

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import FormData

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.cache import get_cache_manager

logger = logging.getLogger(__name__)


class EnhancedSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enhanced security headers middleware with production-ready settings."""

    def __init__(self, app):
        """  Init   operation."""
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add comprehensive security headers to response."""
        response = await call_next(request)

        # Core security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Enhanced Content Security Policy
        if self.settings.environment == "production":
            # Strict CSP for production
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'nonce-{nonce}'; "
                "style-src 'self' 'nonce-{nonce}'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "media-src 'self'; "
                "frame-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # Development CSP (slightly more permissive for development tools)
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* 127.0.0.1:*; "
                "style-src 'self' 'unsafe-inline' localhost:* 127.0.0.1:*; "
                "img-src 'self' data: https: localhost:* 127.0.0.1:*; "
                "connect-src 'self' ws: wss: localhost:* 127.0.0.1:*; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'self'"
            )

        response.headers["Content-Security-Policy"] = csp

        # Strict Transport Security (HSTS)
        if request.url.scheme == "https" or self.settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Force HTTPS in production
        if self.settings.environment == "production" and request.url.scheme != "https":
            # Redirect to HTTPS
            https_url = str(request.url).replace("http://", "https://", 1)
            response.headers["Location"] = https_url
            response.status_code = 301

        # Permissions Policy (formerly Feature Policy)
        permissions_policy = (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "camera=(), "
            "cross-origin-isolated=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), "
            "fullscreen=(self), "
            "geolocation=(), "
            "gyroscope=(), "
            "keyboard-map=(), "
            "magnetometer=(), "
            "microphone=(), "
            "midi=(), "
            "navigation-override=(), "
            "payment=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(), "
            "screen-wake-lock=(), "
            "sync-xhr=(), "
            "usb=(), "
            "web-share=(), "
            "xr-spatial-tracking=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy

        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Cache control for sensitive content
        if any(path in str(request.url.path) for path in ["/auth", "/admin", "/api"]):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Server signature hiding
        response.headers["Server"] = "DotMac-ISP"

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Comprehensive input validation and sanitization middleware."""

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        """  Init   operation."""
        super().__init__(app)
        self.max_request_size = max_request_size
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"vbscript:", re.IGNORECASE),
            re.compile(r"onload\s*=", re.IGNORECASE),
            re.compile(r"onerror\s*=", re.IGNORECASE),
            re.compile(r"onclick\s*=", re.IGNORECASE),
            re.compile(r"onmouseover\s*=", re.IGNORECASE),
            re.compile(r"<iframe", re.IGNORECASE),
            re.compile(r"<object", re.IGNORECASE),
            re.compile(r"<embed", re.IGNORECASE),
        ]
        self.sql_injection_patterns = [
            re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
            re.compile(r"(\bSELECT\b.*\bFROM\b)", re.IGNORECASE),
            re.compile(r"(\bINSERT\b.*\bINTO\b)", re.IGNORECASE),
            re.compile(r"(\bDELETE\b.*\bFROM\b)", re.IGNORECASE),
            re.compile(r"(\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
            re.compile(r"(\bEXEC\b|\bEXECUTE\b)", re.IGNORECASE),
            re.compile(r"('|\")[^'\"]*('|\")", re.IGNORECASE),
        ]
        self.safe_paths = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate and sanitize incoming requests."""

        # Skip validation for safe paths
        if request.url.path in self.safe_paths:
            return await call_next(request)

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                f"Request too large: {content_length} bytes from {self._get_client_ip(request)}"
            )
            raise HTTPException(status_code=413, detail="Request entity too large")

        # Validate headers
        self._validate_headers(request)

        # Validate query parameters
        self._validate_query_params(request)

        # For POST/PUT requests, validate body
        if request.method in ["POST", "PUT", "PATCH"]:
            request = await self._validate_body(request)

        return await call_next(request)

    def _validate_headers(self, request: Request):
        """Validate request headers for malicious content."""
        dangerous_headers = ["user-agent", "referer", "x-forwarded-for"]

        for header_name in dangerous_headers:
            header_value = request.headers.get(header_name, "")
            if self._contains_malicious_content(header_value):
                logger.warning(
                    f"Malicious content in header {header_name}: {header_value}"
                )
                raise HTTPException(status_code=400, detail="Invalid header content")

    def _validate_query_params(self, request: Request):
        """Validate query parameters for malicious content."""
        for param, value in request.query_params.items():
            if isinstance(value, str):
                if self._contains_malicious_content(value):
                    logger.warning(f"Malicious content in query param {param}: {value}")
                    raise HTTPException(
                        status_code=400, detail=f"Invalid query parameter: {param}"
                    )

                # Additional validation for specific parameter types
                if param.lower().endswith("_id") and not self._is_valid_id(value):
                    raise HTTPException(
                        status_code=400, detail=f"Invalid ID format: {param}"
                    )

    async def _validate_body(self, request: Request) -> Request:
        """Validate and sanitize request body."""
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # JSON validation is handled by FastAPI/Pydantic
            pass
        elif (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            # For form data, we need to be more careful
            body = await request.body()
            if body:
                body_str = body.decode("utf-8", errors="ignore")
                if self._contains_malicious_content(body_str):
                    logger.warning(
                        f"Malicious content in form data from {self._get_client_ip(request)}"
                    )
                    raise HTTPException(
                        status_code=400, detail="Invalid form data content"
                    )

        return request

    def _contains_malicious_content(self, content: str) -> bool:
        """Check if content contains malicious patterns."""
        if not content:
            return False

        # Check for XSS patterns
        for pattern in self.xss_patterns:
            if pattern.search(content):
                return True

        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if pattern.search(content):
                return True

        # Check for path traversal
        if "../" in content or "..\\" in content:
            return True

        # Check for null bytes
        if "\x00" in content:
            return True

        return False

    def _is_valid_id(self, value: str) -> bool:
        """Validate ID formats (UUID, alphanumeric, etc.)."""
        # UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if uuid_pattern.match(value):
            return True

        # Alphanumeric with limited special characters
        safe_id_pattern = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")
        if safe_id_pattern.match(value):
            return True

        return False

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware with token validation."""

    def __init__(self, app, exempt_paths: Optional[List[str]] = None):
        """  Init   operation."""
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",  # Initial auth endpoints
            "/api/v1/identity/auth/login",   # Identity module login
            "/api/v1/identity/auth/logout",  # Identity module logout
        ]
        self.cache_manager = get_cache_manager()
        self.token_duration = 3600  # 1 hour

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF tokens for state-changing requests."""

        # Skip CSRF for safe methods and exempt paths
        if request.method in ["GET", "HEAD", "OPTIONS"] or any(
            request.url.path.startswith(path) for path in self.exempt_paths
        ):
            response = await call_next(request)
            # Add CSRF token to response for subsequent requests
            if request.method == "GET":
                self._add_csrf_token_to_response(request, response)
            return response

        # Validate CSRF token for state-changing requests
        if not self._validate_csrf_token(request):
            logger.warning(
                f"CSRF token validation failed for {request.url.path} from {self._get_client_ip(request)}"
            )
            raise HTTPException(status_code=403, detail="CSRF token validation failed")

        response = await call_next(request)
        return response

    def _validate_csrf_token(self, request: Request) -> bool:
        """Validate CSRF token from request."""
        # Try to get token from header first
        csrf_token = request.headers.get("X-CSRF-Token")

        # Fallback to form data or query params
        if not csrf_token:
            csrf_token = request.query_params.get("csrf_token")

        if not csrf_token:
            return False

        # Get session ID or client identifier
        session_id = self._get_session_id(request)
        if not session_id:
            return False

        # Validate token against stored value
        stored_token_key = f"csrf_token:{session_id}"
        stored_token = self.cache_manager.get(stored_token_key, "security")

        if not stored_token or stored_token != csrf_token:
            return False

        return True

    def _add_csrf_token_to_response(self, request: Request, response: Response):
        """Add CSRF token to response headers/cookies."""
        session_id = self._get_session_id(request)
        if not session_id:
            return

        # Generate new CSRF token
        csrf_token = secrets.token_urlsafe(32)

        # Store token in cache
        token_key = f"csrf_token:{session_id}"
        self.cache_manager.set(token_key, csrf_token, self.token_duration, "security")

        # Add token to response header
        response.headers["X-CSRF-Token"] = csrf_token

        # Optionally add as cookie (for form-based requests)
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            max_age=self.token_duration,
            secure=True,  # Only over HTTPS
            httponly=False,  # Accessible to JavaScript for AJAX requests
            samesite="strict",
        )

    def _get_session_id(self, request: Request) -> Optional[str]:
        """Get session ID from request."""
        # Try to get from session cookie
        session_id = request.cookies.get("session_id") or request.cookies.get(
            "dotmac_session"
        )

        # Fallback to generating from client identifier
        if not session_id:
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            session_data = f"{client_ip}:{user_agent}"
            session_id = hashlib.sha256(session_data.encode().hexdigest()[:16])

        return session_id

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request sizes and prevent DoS attacks."""

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        """  Init   operation."""
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Limit request size to prevent DoS attacks."""

        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        f"Request size {size} exceeds limit {self.max_request_size}"
                    )
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request entity too large. Maximum size: {self.max_request_size} bytes",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid Content-Length header"
                )

        return await call_next(request)


class ProductionSecurityEnforcementMiddleware(BaseHTTPMiddleware):
    """Enforce production security requirements."""

    def __init__(self, app):
        """  Init   operation."""
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enforce production security requirements."""

        # In production, enforce HTTPS
        if (
            self.settings.environment == "production"
            and request.url.scheme != "https"
            and not request.url.path.startswith("/health")
        ):

            # Force HTTPS redirect
            https_url = str(request.url).replace("http://", "https://", 1)
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url=https_url, status_code=301)

        # Check for required security configurations in production
        if self.settings.environment == "production":
            if not self.settings.jwt_secret_key:
                logger.critical("JWT_SECRET_KEY not set in production!")
                raise HTTPException(
                    status_code=500, detail="Server configuration error"
                )

            if self.settings.debug:
                logger.critical("Debug mode enabled in production!")
                raise HTTPException(
                    status_code=500, detail="Server configuration error"
                )

        return await call_next(request)


def setup_enhanced_security_middleware(app):
    """Setup all enhanced security middleware."""

    # Add middleware in reverse order (last added is executed first)

    # 1. Production security enforcement (first line of defense)
    app.add_middleware(ProductionSecurityEnforcementMiddleware)

    # 2. Request size limiting
    app.add_middleware(RequestSizeLimitMiddleware, max_request_size=10 * 1024 * 1024)

    # 3. CSRF protection
    app.add_middleware(CSRFProtectionMiddleware)

    # 4. Input validation and sanitization
    app.add_middleware(InputValidationMiddleware)

    # 5. Enhanced security headers (applied to all responses)
    app.add_middleware(EnhancedSecurityHeadersMiddleware)

    logger.info("🔒 Enhanced security middleware configured successfully")


# Utility functions for manual validation
def sanitize_html(text: str) -> str:
    """Sanitize HTML content to prevent XSS."""
    if not text:
        return text

    # HTML escape
    sanitized = html.escape(text)

    # Remove any remaining script tags or javascript
    sanitized = re.sub(
        r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)

    return sanitized


def validate_input_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize input data dictionary."""
    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Basic XSS prevention
            sanitized_value = sanitize_html(value)

            # Length limits
            if len(sanitized_value) > 10000:  # 10KB limit for string fields
                raise ValueError(f"Field {key} exceeds maximum length")

            sanitized[key] = sanitized_value
        elif isinstance(value, dict):
            sanitized[key] = validate_input_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_html(item) if isinstance(item, str) else item for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized

