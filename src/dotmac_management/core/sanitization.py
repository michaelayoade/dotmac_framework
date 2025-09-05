"""
Input sanitization and security validation utilities.

Provides comprehensive input sanitization to prevent XSS, SQL injection,
and other security vulnerabilities.
"""

import html
import logging
import re
from typing import Any, Optional
from urllib.parse import unquote

import bleach
from pydantic import field_validator

from .exceptions import SecurityValidationError

logger = logging.getLogger(__name__)

# Configuration for HTML sanitization
ALLOWED_HTML_TAGS: set[str] = {"b", "i", "u", "em", "strong", "p", "br", "span"}

ALLOWED_HTML_ATTRIBUTES: dict[str, list[str]] = {"*": ["class"], "span": ["style"]}

# Dangerous patterns to detect and block
DANGEROUS_PATTERNS = [
    # Script tags and JavaScript
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"vbscript:",
    r"on\w+\s*=",  # Event handlers like onclick=
    # SQL injection patterns
    r"(\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\bcreate\b|\balter\b).*?(\bfrom\b|\binto\b|\bset\b|\bwhere\b)",
    r";\s*(drop|delete|insert|update|create|alter)",
    r"--\s*$",  # SQL comments
    r"/\*.*?\*/",  # SQL block comments
    # Path traversal
    r"\.\./",
    r"\.\.\\",
    # LDAP injection
    r"\$\{jndi:",
    # Command injection
    r"[\|;&`]",
    # XML/XXE
    r"<!entity",
    r"<!doctype.*?\[",
]

COMPILED_DANGEROUS_PATTERNS = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in DANGEROUS_PATTERNS]


class InputSanitizer:
    """Comprehensive input sanitization utility."""

    @staticmethod
    def sanitize_html(text: str, allowed_tags: Optional[set[str]] = None) -> str:
        """
        Sanitize HTML input to prevent XSS attacks.

        Args:
            text: Input text to sanitize
            allowed_tags: Set of allowed HTML tags (defaults to ALLOWED_HTML_TAGS)

        Returns:
            Sanitized text with dangerous HTML removed
        """
        if not text:
            return text

        # Use provided tags or default safe tags
        tags = allowed_tags or ALLOWED_HTML_TAGS

        # Clean HTML using bleach
        cleaned = bleach.clean(
            text,
            tags=tags,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True,
            strip_comments=True,
        )
        # Additional HTML entity encoding for extra safety
        cleaned = html.escape(cleaned, quote=False)

        return cleaned

    @staticmethod
    def strip_html(text: str) -> str:
        """
        Strip all HTML tags from text.

        Args:
            text: Input text to strip

        Returns:
            Text with all HTML tags removed
        """
        if not text:
            return text

        # Remove all HTML tags
        cleaned = bleach.clean(text, tags=[], strip=True)

        # Decode HTML entities
        cleaned = html.unescape(cleaned)

        return cleaned

    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """
        Sanitize input to prevent SQL injection.

        Note: This is a defense-in-depth measure. Always use parameterized queries.

        Args:
            text: Input text to sanitize

        Returns:
            Sanitized text

        Raises:
            SecurityValidationError: If dangerous SQL patterns are detected
        """
        if not text:
            return text

        # Check for dangerous SQL patterns
        for pattern in COMPILED_DANGEROUS_PATTERNS[1:5]:  # SQL-related patterns
            if pattern.search(text):
                logger.warning(f"Dangerous SQL pattern detected in input: {text[:100]}...")
                raise SecurityValidationError(
                    field="sql_input",
                    reason="Potentially malicious SQL pattern detected",
                )
        # Escape single quotes for SQL safety (parameterized queries are still preferred)
        sanitized = text.replace("'", "''")

        return sanitized

    @staticmethod
    def validate_safe_input(text: str, field_name: str = "input") -> str:
        """
        Validate input for dangerous patterns and sanitize.

        Args:
            text: Input text to validate
            field_name: Name of the field being validated

        Returns:
            Sanitized text if safe

        Raises:
            SecurityValidationError: If dangerous patterns are detected
        """
        if not text:
            return text

        # Check for dangerous patterns
        for i, pattern in enumerate(COMPILED_DANGEROUS_PATTERNS):
            match = pattern.search(text)
            if match:
                logger.warning(f"Dangerous pattern {i} detected in {field_name}: {match.group()[:50]}...")
                raise SecurityValidationError(
                    field=field_name,
                    reason=f"Potentially malicious content detected: {match.group()[:50]}...",
                )
        # Basic sanitization
        sanitized = text.strip()

        # URL decode to catch encoded attacks (unquote is safe for arbitrary strings)
        decoded = unquote(sanitized)
        # Check decoded content for patterns too
        for pattern in COMPILED_DANGEROUS_PATTERNS:
            if pattern.search(decoded):
                raise SecurityValidationError(
                    field=field_name,
                    reason="Potentially malicious encoded content detected",
                )

        return sanitized

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.

        Args:
            filename: Input filename

        Returns:
            Safe filename
        """
        if not filename:
            return filename

        # Remove path components
        filename = filename.split("/")[-1].split("\\")[-1]

        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', "", filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip(". ")

        # Ensure filename is not empty
        if not filename:
            filename = "sanitized_file"

        return filename

    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Basic email sanitization.

        Args:
            email: Email address to sanitize

        Returns:
            Sanitized email

        Raises:
            SecurityValidationError: If email format is suspicious
        """
        if not email:
            return email

        # Basic email format validation
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        if not email_pattern.match(email):
            raise SecurityValidationError(field="email", reason="Invalid email format")
        # Check for dangerous patterns in email
        for pattern in COMPILED_DANGEROUS_PATTERNS:
            if pattern.search(email):
                raise SecurityValidationError(field="email", reason="Potentially malicious email content")
        return email.lower().strip()

    @staticmethod
    def sanitize_json_input(data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively sanitize JSON input data.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}

        for key, value in data.items():
            # Sanitize key
            safe_key = InputSanitizer.validate_safe_input(str(key), f"key_{key}")

            # Sanitize value based on type
            if isinstance(value, str):
                safe_value = InputSanitizer.sanitize_html(value)
            elif isinstance(value, dict):
                safe_value = InputSanitizer.sanitize_json_input(value)
            elif isinstance(value, list):
                safe_value = [
                    (
                        InputSanitizer.sanitize_html(item)
                        if isinstance(item, str)
                        else (InputSanitizer.sanitize_json_input(item) if isinstance(item, dict) else item)
                    )
                    for item in value
                ]
            else:
                safe_value = value

            sanitized[safe_key] = safe_value

        return sanitized


# Pydantic validators for common fields
def validate_safe_string(v: str, field_name: str = "field") -> str:
    """Pydantic validator for safe string input."""
    if v is None:
        return v
    return InputSanitizer.validate_safe_input(v, field_name)


def validate_html_string(v: str) -> str:
    """Pydantic validator for HTML string input."""
    if v is None:
        return v
    return InputSanitizer.sanitize_html(v)


def validate_plain_string(v: str) -> str:
    """Pydantic validator for plain text (strips HTML)."""
    if v is None:
        return v
    return InputSanitizer.strip_html(v)


def validate_email_string(v: str) -> str:
    """Pydantic validator for email input."""
    if v is None:
        return v
    return InputSanitizer.sanitize_email(v)


def validate_filename_string(v: str) -> str:
    """Pydantic validator for filename input."""
    if v is None:
        return v
    return InputSanitizer.sanitize_filename(v)


# Common field validators that can be imported and used in schemas
class SecurityValidators:
    """Collection of security validators for Pydantic models."""

    @classmethod
    def safe_string_validator(cls, field_name: str = "field"):
        """Create a validator for safe string input."""

        def validator(v: str) -> str:
            return validate_safe_string(v, field_name)

        return field_validator(field_name)(validator)

    @classmethod
    def html_string_validator(cls, field_name: str):
        """Create a validator for HTML string input."""

        def validator(v: str) -> str:
            return validate_html_string(v)

        return field_validator(field_name)(validator)

    @classmethod
    def plain_string_validator(cls, field_name: str):
        """Create a validator for plain text input."""

        def validator(v: str) -> str:
            return validate_plain_string(v)

        return field_validator(field_name)(validator)

    @classmethod
    def email_validator(cls, field_name: str = "email"):
        """Create a validator for email input."""

        def validator(v: str) -> str:
            return validate_email_string(v)

        return field_validator(field_name)(validator)

    @classmethod
    def filename_validator(cls, field_name: str = "filename"):
        """Create a validator for filename input."""

        def validator(v: str) -> str:
            return validate_filename_string(v)

        return field_validator(field_name)(validator)


# Decorator for automatic input sanitization
def sanitize_inputs(func):
    """Decorator to automatically sanitize function inputs."""

    def wrapper(*args, **kwargs):
        # Sanitize string arguments
        sanitized_args = []
        for arg in args:
            if isinstance(arg, str):
                sanitized_args.append(InputSanitizer.validate_safe_input(arg))
            elif isinstance(arg, dict):
                sanitized_args.append(InputSanitizer.sanitize_json_input(arg))
            else:
                sanitized_args.append(arg)

        # Sanitize keyword arguments
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                sanitized_kwargs[key] = InputSanitizer.validate_safe_input(value, key)
            elif isinstance(value, dict):
                sanitized_kwargs[key] = InputSanitizer.sanitize_json_input(value)
            else:
                sanitized_kwargs[key] = value

        return func(*sanitized_args, **sanitized_kwargs)

    return wrapper
