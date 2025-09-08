"""
DotMac Core Exceptions - Stub Implementation
"""


class DotMacError(Exception):
    """Base exception for DotMac Framework."""


class ValidationError(DotMacError):
    """Validation error."""


class AuthorizationError(DotMacError):
    """Authorization error."""


class ConfigurationError(DotMacError):
    """Configuration error."""
