"""
DotMac Core Exceptions - Stub Implementation
"""


class DotMacError(Exception):
    """Base exception for DotMac Framework."""

    pass


class ValidationError(DotMacError):
    """Validation error."""

    pass


class AuthorizationError(DotMacError):
    """Authorization error."""

    pass


class ConfigurationError(DotMacError):
    """Configuration error."""

    pass
