"""
Pure validation utilities for common data types and formats.

Provides lightweight validation functions that use only stdlib dependencies
and raise structured exceptions for consistent error handling.
"""

import re
import uuid
from typing import Any

from .exceptions import ValidationError

# Email validation regex - simple but robust for most use cases
# Prevents double dots, starting/ending with dots, etc.
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_%+-]+(?:\.[a-zA-Z0-9_%+-]+)*@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
)

# Control characters to remove from text (except common whitespace)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def is_email(value: str) -> bool:
    """
    Check if a string is a valid email address.
    
    Uses a simple regex that covers most common email formats.
    Does not perform DNS validation or catch all edge cases.
    
    Args:
        value: String to validate
        
    Returns:
        True if the value appears to be a valid email address
        
    Example:
        >>> is_email("user@example.com")
        True
        >>> is_email("invalid-email")
        False
        >>> is_email("user@")
        False
    """
    if not isinstance(value, str):
        return False

    # Basic length checks
    if len(value) < 3 or len(value) > 254:
        return False

    return bool(_EMAIL_REGEX.match(value))


def is_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Accepts UUIDs in standard hyphenated format (8-4-4-4-12).
    
    Args:
        value: String to validate
        
    Returns:
        True if the value is a valid UUID format
        
    Example:
        >>> is_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> is_uuid("not-a-uuid")
        False
        >>> is_uuid("550e8400e29b41d4a716446655440000")  # No hyphens
        False
    """
    if not isinstance(value, str):
        return False

    # Must have hyphens in the right places
    if len(value) != 36 or value.count('-') != 4:
        return False

    try:
        uuid_obj = uuid.UUID(value)
        # Verify that the string representation matches (prevents non-hyphenated)
        return str(uuid_obj) == value
    except ValueError:
        return False


def ensure_in(value: Any, allowed: list, field: str) -> None:
    """
    Ensure a value is in the allowed set.
    
    Args:
        value: Value to check
        allowed: List of allowed values
        field: Name of the field for error messages
        
    Raises:
        ValidationError: If value is not in the allowed set
        
    Example:
        >>> ensure_in("active", {"active", "inactive"}, "status")  # OK
        >>> ensure_in("pending", {"active", "inactive"}, "status")
        ValidationError: Invalid status: must be one of: active, inactive
    """
    if value not in allowed:
        allowed_str = ", ".join(str(v) for v in allowed)
        raise ValidationError(
            f"Invalid {field} '{value}': {field} must be one of: {allowed_str}",
            "VALUE_NOT_ALLOWED",
            {"field": field, "value": value, "allowed": allowed}
        )


def ensure_range(
    x: int | float,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    field: str = "value"
) -> None:
    """
    Ensure a numeric value is within the specified range.
    
    Args:
        x: Numeric value to validate
        min_val: Minimum allowed value (inclusive), if specified
        max_val: Maximum allowed value (inclusive), if specified  
        field: Name of the field for error messages
        
    Raises:
        ValidationError: If value is outside the allowed range
        
    Example:
        >>> ensure_range(5, min_val=1, max_val=10)  # OK
        >>> ensure_range(15, min_val=1, max_val=10)
        ValidationError: value must be between 1 and 10
        >>> ensure_range(-5, min_val=0)
        ValidationError: value must be at least 0
    """
    if min_val is not None and x < min_val:
        if max_val is not None:
            msg = f"{field} must be between {min_val} and {max_val}"
        else:
            msg = f"{field} must be >= {min_val}"
        raise ValidationError(
            msg,
            "VALUE_OUT_OF_RANGE",
            {"field": field, "value": x, "min_val": min_val, "max_val": max_val}
        )

    if max_val is not None and x > max_val:
        if min_val is not None:
            msg = f"{field} must be between {min_val} and {max_val}"
        else:
            msg = f"{field} must be <= {max_val}"
        raise ValidationError(
            msg,
            "VALUE_OUT_OF_RANGE",
            {"field": field, "value": x, "min_val": min_val, "max_val": max_val}
        )


def sanitize_text(value: str, *, max_length: int = 10_000) -> str:
    """
    Sanitize text by removing control characters while preserving normal whitespace.
    
    Removes control characters (except common whitespace like \\t, \\n, \\r)
    but preserves normal whitespace formatting.
    
    Args:
        value: Text to sanitize
        max_length: Maximum allowed length after sanitization
        
    Returns:
        Sanitized text
        
    Raises:
        ValidationError: If sanitized text exceeds max_length
        
    Example:
        >>> sanitize_text("Hello\\x00\\x01World")
        'HelloWorld'
        >>> sanitize_text("Hello\\n\\t World")
        'Hello\\n\\t World'
        >>> sanitize_text("x" * 20000, max_length=100)
        ValidationError: Text too long: maximum 100 characters
    """
    if value is None:
        return ""
    
    if not isinstance(value, str):
        # Convert to string for non-string types
        value = str(value)

    # Remove control characters but keep normal whitespace (tab, newline, carriage return)
    sanitized = _CONTROL_CHARS.sub("", value)

    # Check length
    if len(sanitized) > max_length:
        raise ValidationError(
            f"Text too long: maximum {max_length} characters",
            "TEXT_TOO_LONG",
            {"length": len(sanitized), "max_length": max_length}
        )

    return sanitized


__all__ = [
    "is_email",
    "is_uuid",
    "ensure_in",
    "ensure_range",
    "sanitize_text",
]
