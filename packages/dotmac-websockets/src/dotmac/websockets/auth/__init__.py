"""
Authentication components for WebSocket gateway.
"""

from .types import AuthResult, UserInfo
from .manager import AuthManager

# Try to import middleware (optional)
try:
    from .middleware import AuthMiddleware
except ImportError:
    AuthMiddleware = None

__all__ = [
    "AuthResult",
    "UserInfo", 
    "AuthManager",
    "AuthMiddleware",  # May be None if JWT not available
]