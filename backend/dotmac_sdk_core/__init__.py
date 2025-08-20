"""
DotMac SDK Core - Shared utilities for all service SDKs
"""

from .client import BaseSDKClient
from .retry import RetryPolicy, with_retry
from .exceptions import (
    SDKError,
    SDKConnectionError,
    SDKAuthenticationError,
    SDKValidationError,
    SDKRateLimitError,
    SDKTimeoutError
)
from .utils import build_headers, parse_response, handle_deprecation

__version__ = "1.0.0"

__all__ = [
    "BaseSDKClient",
    "RetryPolicy",
    "with_retry",
    "SDKError",
    "SDKConnectionError",
    "SDKAuthenticationError",
    "SDKValidationError",
    "SDKRateLimitError",
    "SDKTimeoutError",
    "build_headers",
    "parse_response",
    "handle_deprecation",
]