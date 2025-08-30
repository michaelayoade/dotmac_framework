"""
Authentication middleware.

This module contains middleware components for integrating authentication
with web frameworks and providing security features:
- FastAPI middleware integration
- Rate limiting and brute force protection
- Authentication audit logging
"""

from .audit_logging import AuditLoggingMiddleware
from .fastapi_middleware import AuthenticationMiddleware
from .rate_limiting import RateLimitingMiddleware

__all__ = [
    "AuthenticationMiddleware",
    "RateLimitingMiddleware",
    "AuditLoggingMiddleware",
]
