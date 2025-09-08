"""
Security headers middleware and configuration
Implements production-ready security headers
"""

import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment == "production"

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # HSTS (HTTP Strict Transport Security)
        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # CSP (Content Security Policy) - Restrict to known origins
        csp_policy = self._build_csp_policy(request)
        response.headers["Content-Security-Policy"] = csp_policy

        # X-Frame-Options - Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # X-Content-Type-Options - Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer Policy - Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # X-XSS-Protection - Enable XSS filtering
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Permissions Policy - Restrict feature access
        permissions_policy = "geolocation=(), microphone=(), camera=(), payment=()"
        response.headers["Permissions-Policy"] = permissions_policy

        # Remove server identification
        response.headers["Server"] = "DotMac/1.0"

        return response

    def _build_csp_policy(self, request: Request) -> str:
        """Build Content Security Policy based on environment"""

        # Get allowed origins from environment
        cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
        cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

        # Base CSP policy
        policy_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts for admin panels
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles
            "img-src 'self' data: https:",  # Allow images from self, data URLs, and HTTPS
            "font-src 'self' data:",  # Allow fonts from self and data URLs
            "connect-src 'self'",  # Allow connections to self
            "media-src 'self'",  # Allow media from self
            "object-src 'none'",  # Disable plugins
            "frame-src 'self'",  # Allow frames from self
            "base-uri 'self'",  # Restrict base URI
            "form-action 'self'",  # Restrict form actions
        ]

        # Add allowed origins to connect-src for API calls
        if cors_origins:
            connect_sources = ["'self'"] + cors_origins
            policy_parts = [
                p if not p.startswith("connect-src") else f"connect-src {' '.join(connect_sources)}"
                for p in policy_parts
            ]

        # In development, be more permissive
        if not self.is_production:
            # Allow localhost and development servers
            dev_sources = [
                "http://localhost:*",
                "http://127.0.0.1:*",
                "ws://localhost:*",
            ]
            policy_parts = [
                p.replace("'self'", "'self' " + " ".join(dev_sources)) if "connect-src" in p else p
                for p in policy_parts
            ]

        return "; ".join(policy_parts)


class CORSConfig:
    """
    CORS configuration for production security
    """

    @staticmethod
    def get_cors_config() -> dict:
        """Get CORS configuration based on environment"""

        environment = os.getenv("ENVIRONMENT", "development")
        cors_origins = os.getenv("CORS_ORIGINS", "")

        if environment == "production":
            # Production: Only allow exact domains
            if not cors_origins:
                raise ValueError("CORS_ORIGINS must be set in production")

            allowed_origins = [origin.strip() for origin in cors_origins.split(",")]

            return {
                "allow_origins": allowed_origins,
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": [
                    "Accept",
                    "Accept-Language",
                    "Content-Language",
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "X-CSRF-Token",
                    "X-Tenant-ID",
                    "X-Correlation-ID",
                ],
                "expose_headers": [
                    "X-Total-Count",
                    "X-Page-Count",
                    "X-Rate-Limit-Remaining",
                    "X-Rate-Limit-Reset",
                ],
            }
        else:
            # Development: More permissive
            return {
                "allow_origins": ["http://localhost:*", "http://127.0.0.1:*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }


class CookieConfig:
    """
    Secure cookie configuration
    """

    @staticmethod
    def get_cookie_config() -> dict:
        """Get secure cookie configuration"""

        environment = os.getenv("ENVIRONMENT", "development")
        is_production = environment == "production"

        # For multi-tenant cross-origin scenarios, SameSite policy needs consideration
        samesite_policy = "none" if is_production else "lax"  # None requires Secure=True

        return {
            "secure": is_production,  # Only send over HTTPS in production
            "httponly": True,  # Prevent XSS access to cookies
            "samesite": samesite_policy,  # None for cross-origin, lax for dev
            "max_age": 3600 * 24 * 7,  # 7 days
            "domain": os.getenv("COOKIE_DOMAIN") if is_production else None,
            "path": "/",
        }


def validate_security_config():
    """
    Validate security configuration on startup
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        required_vars = [
            "SECRET_KEY",
            "CORS_ORIGINS",
            "DATABASE_URL",
            "BASE_DOMAIN",  # Required for tenant provisioning
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(f"Missing required production environment variables: {missing_vars}")

        # Validate SECRET_KEY length
        secret_key = os.getenv("SECRET_KEY", "")
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")

        # Validate CORS origins format
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if cors_origins:
            origins = [origin.strip() for origin in cors_origins.split(",")]
            for origin in origins:
                if not (origin.startswith("https://") or origin.startswith("http://")):
                    raise ValueError(f"Invalid CORS origin format: {origin}")

        # Validate BASE_DOMAIN format
        base_domain = os.getenv("BASE_DOMAIN", "")
        if base_domain:
            # Check it's a valid domain format (basic validation)
            if not base_domain.replace("-", "").replace(".", "").replace("_", "").isalnum():
                raise ValueError(f"Invalid BASE_DOMAIN format: {base_domain}")
            if base_domain.startswith(".") or base_domain.endswith("."):
                raise ValueError(f"BASE_DOMAIN cannot start or end with dot: {base_domain}")
            if ".." in base_domain:
                raise ValueError(f"BASE_DOMAIN cannot contain consecutive dots: {base_domain}")
    import logging

    logging.getLogger(__name__).info("✅ Security configuration validated")
