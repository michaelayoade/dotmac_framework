"""
DotMac SDK Core - Shared utilities for all service SDKs
"""

from .client import BaseSDKClient
from .retry import RetryPolicy, with_retry, CircuitBreaker
from .exceptions import (
    SDKError,
    SDKConnectionError,
    SDKAuthenticationError,
    SDKValidationError,
    SDKRateLimitError,
    SDKTimeoutError,
    ConfigurationError,
    ValidationError,
    ConsentError,
)
from .utils import build_headers, parse_response, handle_deprecation

__version__ = "1.0.0"

__all__ = [
    "BaseSDKClient",
    "RetryPolicy",
    "with_retry",
    "CircuitBreaker",
    "SDKError",
    "SDKConnectionError",
    "SDKAuthenticationError",
    "SDKValidationError",
    "SDKRateLimitError",
    "SDKTimeoutError",
    "ConfigurationError",
    "ValidationError",
    "ConsentError",
    "build_headers",
    "parse_response",
    "handle_deprecation",
]

# For backward compatibility
RetryClient = CircuitBreaker
