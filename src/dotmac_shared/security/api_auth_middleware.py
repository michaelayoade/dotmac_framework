"""
API Authentication Middleware for DotMac Framework
"""

import logging
import time
from typing import Any, Optional

import jwt
from fastapi import Request

logger = logging.getLogger(__name__)


class APIAuthMiddleware:
    """JWT-based API authentication middleware."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """__init__ operation."""
        self.secret_key = secret_key
        self.algorithm = algorithm

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                return auth_header.split(" ", 1)[1]
            return None
        except Exception:
            return None

    def _validate_token(self, token: str) -> Optional[dict[str, Any]]:
        """Validate JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    async def authenticate_request(self, request: Request) -> dict[str, Any]:
        """Authenticate incoming request."""
        try:
            token = self._extract_token(request)

            if not token:
                return {
                    "authenticated": False,
                    "error": "Missing or invalid Authorization header",
                }

            payload = self._validate_token(token)

            if not payload:
                return {"authenticated": False, "error": "Invalid or expired token"}

            return {
                "authenticated": True,
                "user_id": payload.get("user_id"),
                "payload": payload,
            }

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {"authenticated": False, "error": f"Authentication failed: {str(e)}"}

    def _check_permissions(
        self, payload: dict[str, Any], required_scope: Optional[str] = None
    ) -> bool:
        """Check if user has required permissions."""
        if not required_scope:
            return True

        user_scopes = payload.get("scope", [])
        return required_scope in user_scopes

    def generate_token(
        self, user_id: str, scopes: Optional[list] = None, expires_in: int = 3600
    ) -> str:
        """Generate JWT token for user."""
        now = int(time.time())
        payload = {
            "user_id": user_id,
            "iat": now,
            "exp": now + expires_in,
            "scope": scopes or [],
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


class RateLimiter:
    """Rate limiting middleware."""

    def __init__(self, redis_client, requests_per_minute: int = 60):
        """__init__ operation."""
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute in seconds

    async def check_rate_limit(self, identifier: str) -> bool:
        """Check if request is within rate limit."""
        try:
            key = f"rate_limit:{identifier}"

            # Get current count
            current_count = await self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0

            if current_count >= self.requests_per_minute:
                return False

            # Increment counter
            await self.redis_client.incr(key)

            # Set expiry on first request
            if current_count == 0:
                await self.redis_client.expire(key, self.window_size)

            return True

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open - allow request if Redis is down
            return True

    async def get_rate_limit_status(self, identifier: str) -> dict[str, Any]:
        """Get current rate limit status."""
        try:
            key = f"rate_limit:{identifier}"

            current_count = await self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0

            ttl = await self.redis_client.ttl(key)

            return {
                "requests_made": current_count,
                "requests_remaining": max(0, self.requests_per_minute - current_count),
                "reset_time": ttl if ttl > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return {
                "requests_made": 0,
                "requests_remaining": self.requests_per_minute,
                "reset_time": 0,
            }

    async def reset_rate_limit(self, identifier: str):
        """Reset rate limit for identifier."""
        try:
            key = f"rate_limit:{identifier}"
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Rate limit reset error: {e}")


class SecurityHeaders:
    """Security headers middleware."""

    def __init__(self, csp_policy: Optional[str] = None, enable_hsts: bool = True):
        """__init__ operation."""
        self.csp_policy = csp_policy or "default-src 'self'"
        self.enable_hsts = enable_hsts

    def add_security_headers(self, response):
        """Add security headers to response."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": self.csp_policy,
        }

        if self.enable_hsts:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        for header, value in headers.items():
            response.headers[header] = value


class InputSanitizer:
    """Input sanitization utilities."""

    def __init__(self):
        """__init__ operation."""
        pass

    def sanitize_html(
        self, html_content: str, allowed_tags: Optional[list] = None
    ) -> str:
        """Sanitize HTML content."""
        try:
            import bleach

            if allowed_tags is None:
                allowed_tags = ["p", "br", "strong", "em", "ul", "ol", "li"]

            return bleach.clean(html_content, tags=allowed_tags, strip=True)

        except ImportError:
            # Fallback: simple tag removal
            import re

            return re.sub(r"<[^>]+>", "", html_content)

    def sanitize_sql_input(self, user_input: str) -> str:
        """Basic SQL injection prevention."""
        dangerous_patterns = [
            ";",
            "--",
            "/*",
            "*/",
            "xp_",
            "sp_",
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "SELECT",
        ]

        sanitized = user_input
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, "")

        return sanitized.strip()

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        import re

        # Remove path traversal attempts
        sanitized = filename.replace("..", "").replace("/", "").replace("\\", "")
        # Keep only alphanumeric and safe characters
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", sanitized)
        return sanitized

    def sanitize_url(self, url: str) -> dict[str, Any]:
        """Sanitize and validate URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)

            # Check for safe schemes
            safe_schemes = ["http", "https"]
            if parsed.scheme not in safe_schemes:
                return {"is_valid": False, "error": "Unsafe URL scheme"}

            return {"is_valid": True, "sanitized_url": url}

        except Exception as e:
            return {"is_valid": False, "error": str(e)}

    def escape_html_entities(self, text: str) -> str:
        """Escape HTML entities in text."""
        import html

        return html.escape(text)
