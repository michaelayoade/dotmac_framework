"""
Enhanced security patterns and middleware for dotmac-application.
Provides comprehensive security decorators and utilities.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Security constants
SENSITIVE_ENDPOINTS = [
    "/auth/login",
    "/auth/register",
    "/auth/reset-password",
    "/auth/change-password",
    "/admin",
    "/api/admin",
]


class SecurityDecorators:
    """Collection of security decorators for endpoint protection."""

    @staticmethod
    def require_admin(func: Callable) -> Callable:
        """Decorator to require admin permissions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from args/kwargs
            deps = None
            for arg in args:
                if hasattr(arg, 'current_user') and hasattr(arg, 'db'):
                    deps = arg
                    break

            if not deps:
                # Try to find in kwargs
                deps = kwargs.get('deps')

            if not deps or not hasattr(deps, 'current_user'):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing authentication dependencies"
                )

            # Check admin status
            if not deps.current_user.get('is_admin', False):
                logger.warning(
                    f"Non-admin user {deps.current_user.get('user_id')} attempted to access admin endpoint {func.__name__}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin permissions required"
                )

            return await func(*args, **kwargs)
        return wrapper

    @staticmethod
    def require_active_user(func: Callable) -> Callable:
        """Decorator to require active user account."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies
            deps = None
            for arg in args:
                if hasattr(arg, 'current_user'):
                    deps = arg
                    break

            if not deps:
                deps = kwargs.get('deps')

            if not deps or not hasattr(deps, 'current_user'):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing authentication dependencies"
                )

            # Check if user is active
            if not deps.current_user.get('is_active', False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive"
                )

            return await func(*args, **kwargs)
        return wrapper

    @staticmethod
    def require_tenant_access(func: Callable) -> Callable:
        """Decorator to verify tenant access permissions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            deps = None
            for arg in args:
                if hasattr(arg, 'current_user') and hasattr(arg, 'tenant_id'):
                    deps = arg
                    break

            if not deps:
                deps = kwargs.get('deps')

            if not deps:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing dependencies"
                )

            # Check tenant access (basic implementation)
            user_tenant = deps.current_user.get('tenant_id')
            required_tenant = deps.tenant_id

            if user_tenant != required_tenant:
                logger.warning(
                    f"User {deps.current_user.get('user_id')} attempted to access tenant {required_tenant}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this tenant"
                )

            return await func(*args, **kwargs)
        return wrapper

    @staticmethod
    def validate_entity_ownership(entity_id_param: str = "entity_id"):
        """Decorator to validate entity ownership."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get entity ID from kwargs
                entity_id = kwargs.get(entity_id_param)
                if not entity_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing {entity_id_param}"
                    )

                # Extract dependencies
                deps = None
                for arg in args:
                    if hasattr(arg, 'current_user') and hasattr(arg, 'db'):
                        deps = arg
                        break

                if not deps:
                    deps = kwargs.get('deps')

                if not deps:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Missing dependencies"
                    )

                # TODO: Add entity ownership validation logic
                # This would typically query the database to verify ownership
                logger.debug(
                    f"Validating ownership of {entity_id_param}={entity_id} for user {deps.current_user.get('user_id')}"
                )

                return await func(*args, **kwargs)
            return wrapper
        return decorator


class SecurityHeaders:
    """Security headers middleware and utilities."""

    STANDARD_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    @classmethod
    def apply_security_headers(cls, response):
        """Apply standard security headers to response."""
        for header, value in cls.STANDARD_HEADERS.items():
            response.headers[header] = value
        return response


class InputSanitizer:
    """Input sanitization utilities."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        # Strip whitespace
        value = value.strip()

        # Check length
        if len(value) > max_length:
            raise ValidationError(f"Value exceeds maximum length of {max_length}")

        # Remove potentially dangerous characters
        dangerous_chars = ["<", ">", "&", '"', "'", "\x00"]
        for char in dangerous_chars:
            value = value.replace(char, "")

        return value

    @staticmethod
    def validate_uuid(value: str | UUID) -> UUID:
        """Validate UUID input."""
        if isinstance(value, UUID):
            return value

        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError as e:
                raise ValidationError("Invalid UUID format") from e

        raise ValidationError("Value must be a valid UUID")

    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email address."""
        email = email.lower().strip()

        # Basic validation (more comprehensive validation should be done with EmailStr)
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValidationError("Invalid email format")

        return email


class APIKeyValidator:
    """API key validation utilities."""

    def __init__(self):
        self.security = HTTPBearer()

    async def validate_api_key(self, credentials: HTTPAuthorizationCredentials) -> dict[str, Any]:
        """Validate API key credentials."""
        token = credentials.credentials

        # TODO: Implement actual API key validation
        # This would typically involve:
        # 1. Checking against database/cache
        # 2. Validating expiration
        # 3. Checking permissions

        if token == "valid_api_key":
            return {
                "user_id": "api_user",
                "email": "api@example.com",
                "is_active": True,
                "is_admin": False,
                "api_key": True,
            }

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


def apply_security_middleware(app):
    """Apply comprehensive security middleware to FastAPI app."""

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        """Security middleware for all requests."""

        # Add security headers to response
        response = await call_next(request)
        SecurityHeaders.apply_security_headers(response)

        # Add rate limiting headers if available
        if hasattr(request.state, 'rate_limit_remaining'):
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)

        if hasattr(request.state, 'rate_limit_reset'):
            response.headers["X-RateLimit-Reset"] = str(int(request.state.rate_limit_reset.timestamp()))

        return response

    logger.info("Security middleware applied to application")


# Convenient decorator exports
require_admin = SecurityDecorators.require_admin
require_active_user = SecurityDecorators.require_active_user
require_tenant_access = SecurityDecorators.require_tenant_access
validate_entity_ownership = SecurityDecorators.validate_entity_ownership

# Export utilities
__all__ = [
    "SecurityDecorators",
    "SecurityHeaders",
    "InputSanitizer",
    "APIKeyValidator",
    "apply_security_middleware",
    "require_admin",
    "require_active_user",
    "require_tenant_access",
    "validate_entity_ownership",
    "SENSITIVE_ENDPOINTS",
]

