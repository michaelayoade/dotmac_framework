"""
Utility functions and common patterns for DotMac monitoring system.

This module provides shared utilities to eliminate code duplication
and ensure consistent patterns across the monitoring package.
"""

import time
from typing import Any, Optional, TypeVar


def get_logger(name: str):
    """
    Get a logger instance with consistent configuration.

    Tries to use structlog if available, falls back to standard logging.
    """
    try:
        import structlog

        return structlog.get_logger(name)
    except ImportError:
        import logging

        return logging.getLogger(name)


# Type variable for generic validation
T = TypeVar("T")


def safe_import(module_name: str, class_name: Optional[str] = None, default_value: Any = None):
    """
    Safely import a module or class, returning default_value if import fails.

    Args:
        module_name: Name of the module to import
        class_name: Optional class name to import from the module
        default_value: Value to return if import fails

    Returns:
        The imported module/class or default_value
    """
    try:
        module = __import__(module_name, fromlist=[class_name] if class_name else [])
        if class_name:
            return getattr(module, class_name)
        return module
    except ImportError:
        return default_value


def validate_required_field(value: Any, field_name: str, expected_type: Optional[type] = None) -> Any:
    """
    Validate a required field with optional type checking.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        expected_type: Optional type to check against

    Returns:
        The validated value

    Raises:
        ValueError: If validation fails
    """
    if value is None:
        raise ValueError(f"{field_name} is required")

    if expected_type and not isinstance(value, expected_type):
        raise ValueError(f"{field_name} must be of type {expected_type.__name__}")

    return value


def safe_cast(value: Any, target_type: type[T], default: Optional[T] = None) -> Optional[T]:
    """
    Safely cast a value to target type, returning default if cast fails.

    Args:
        value: Value to cast
        target_type: Type to cast to
        default: Default value if cast fails

    Returns:
        Casted value or default
    """
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return default


def get_current_timestamp() -> float:
    """Get current timestamp in a consistent format."""
    return time.time()


def format_duration_ms(start_time: float, end_time: Optional[float] = None) -> float:
    """
    Calculate duration in milliseconds between two timestamps.

    Args:
        start_time: Start timestamp
        end_time: End timestamp (current time if None)

    Returns:
        Duration in milliseconds
    """
    if end_time is None:
        end_time = get_current_timestamp()
    return (end_time - start_time) * 1000


def sanitize_dict(data: dict[str, Any], sensitive_keys: Optional[set] = None) -> dict[str, Any]:
    """
    Sanitize a dictionary by redacting sensitive keys.

    Args:
        data: Dictionary to sanitize
        sensitive_keys: Set of keys to redact (case-insensitive)

    Returns:
        Sanitized dictionary
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
            "csrf",
            "api_key",
            "auth_token",
        }

    sensitive_keys = {key.lower() for key in sensitive_keys}

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "<redacted>"
        else:
            sanitized[key] = value

    return sanitized


def truncate_string(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length with suffix.

    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def deep_merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries, with dict2 taking precedence.

    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge in

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


class StorageError(Exception):
    """Exception raised for storage-related errors."""

    pass


# Common constants
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRY_ATTEMPTS = 3

# Production-ready logging configuration
PRODUCTION_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        "simple": {"format": "%(levelname)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "/var/log/dotmac/monitoring.log",
            "mode": "a",
        },
    },
    "loggers": {
        "dotmac_shared.monitoring": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        }
    },
    "root": {"level": "WARNING", "handlers": ["console"]},
}


__all__ = [
    # Utilities
    "get_logger",
    "safe_import",
    "validate_required_field",
    "safe_cast",
    "get_current_timestamp",
    "format_duration_ms",
    "sanitize_dict",
    "truncate_string",
    "deep_merge_dicts",
    # Exceptions
    "ConfigurationError",
    "ValidationError",
    "StorageError",
    # Constants
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_RETRY_ATTEMPTS",
    "PRODUCTION_LOG_CONFIG",
]
