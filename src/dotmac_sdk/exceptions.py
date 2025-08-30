"""
DotMac SDK Exception Classes
"""


class DotMacAPIError(Exception):
    """Base exception for DotMac API errors."""

    pass


class DotMacAuthError(DotMacAPIError):
    """Authentication failed."""

    pass


class DotMacConfigError(DotMacAPIError):
    """Configuration error."""

    pass


class RateLimitError(DotMacAPIError):
    """Rate limit exceeded."""

    pass


class ValidationError(DotMacAPIError):
    """Request validation failed."""

    pass
