"""
Core module for DotMac API Gateway.

Provides configuration management, exception handling, and core utilities.
"""

from .config import GatewayConfig, load_config
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    GatewayError,
    RateLimitError,
    RoutingError,
    UpstreamError,
)

__all__ = [
    # Configuration
    "GatewayConfig",
    "load_config",
    # Exceptions
    "GatewayError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "RoutingError",
    "UpstreamError",
    "ConfigurationError",
]

from .datetime_utils import utc_now, utc_now_iso, is_expired, expires_in_hours, expires_in_days
