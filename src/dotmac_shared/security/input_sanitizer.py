"""
Comprehensive Input Sanitization for DotMac Platform
Prevents XSS, SQL Injection, and other input-based attacks

SECURITY: This module provides enterprise-grade input sanitization
Applied automatically to all user inputs across the platform
"""

import html
import json
import logging
import re
from collections.abc import Callable
from typing import Any, Optional, Union

import bleach

logger = logging.getLogger(__name__)


class SecuritySanitizer:
    """
    Comprehensive input sanitization with multiple security layers

    Features:
    - HTML/Script injection prevention
    - SQL injection prevention
    - Path traversal prevention
    - Command injection prevention
    - NoSQL injection prevention
    - File upload sanitization
    """

    # Dangerous patterns that should never appear in user input
    DANGEROUS_PATTERNS = [
        # Script injections
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"data:text/html",
        r"on\w+\s*=",  # Event handlers
        # SQL injections
        r"(\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\bcreate\b|\balter\b).*(\bfrom\b|\binto\b|\bset\b|\bwhere\b|\btable\b)",
        r"\'.*(\bor\b|\band\b).*\'",
        r"--.*$",
        r"/\*.*\*/",
        # Command injections
        r"[;&|`${}()]",
        r"\$\(.+\)",
        r"`[^`]*`",
        # Path traversals
        r"\.\./+",
        r"\.\.\\+",
        r"~/",
        # NoSQL injections
        r"\$where",
        r"\$ne",
        r"\$gt",
        r"\$regex",
    ]

    # Allowed HTML tags for rich text (very restrictive)
    ALLOWED_HTML_TAGS = {"b", "i", "strong", "em", "p", "br", "ul", "ol", "li"}

    # Allowed HTML attributes (very restrictive)
    ALLOWED_HTML_ATTRS = {
        "*": ["class"],
        "a": ["href"],
    }

    @classmethod
    def sanitize_string(cls, value: str, context: str = "default") -> str:
        """
        Sanitize a string value based on context

        Args:
            value: Input string to sanitize
            context: Context type ('email', 'password', 'html', 'json', 'sql', 'filename')
        """
        if not isinstance(value, str):
            return str(value) if value is not None else ""

        # Basic HTML escaping for all contexts
        sanitized = html.escape(value, quote=True)

        # Context-specific sanitization
        if context == "html":
            return cls._sanitize_html(sanitized)
        elif context == "email":
            return cls._sanitize_email(sanitized)
        elif context == "filename":
            return cls._sanitize_filename(sanitized)
        elif context == "json":
            return cls._sanitize_json(sanitized)
        elif context == "sql":
            return cls._sanitize_sql(sanitized)
        elif context == "password":
            return cls._sanitize_password(sanitized)
        else:
            return cls._sanitize_default(sanitized)

    @classmethod
    def _sanitize_html(cls, value: str) -> str:
        """Sanitize HTML content allowing only safe tags"""
        # Use bleach for HTML sanitization
        cleaned = bleach.clean(
            value,
            tags=cls.ALLOWED_HTML_TAGS,
            attributes=cls.ALLOWED_HTML_ATTRS,
            strip=True,
        )
        return cleaned

    @classmethod
    def _sanitize_email(cls, value: str) -> str:
        """Sanitize email addresses"""
        # Remove HTML entities and normalize
        sanitized = html.unescape(value).lower().strip()

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, sanitized):
            logger.warning(f"Invalid email format blocked: {value[:20]}...")
            return ""

        return sanitized

    @classmethod
    def _sanitize_filename(cls, value: str) -> str:
        """Sanitize filenames for safe storage"""
        # Remove path traversal attempts
        sanitized = value.replace("..", "").replace("/", "").replace("\\", "")

        # Only allow alphanumeric, dots, dashes, underscores
        sanitized = re.sub(r"[^\w\-_\.]", "", sanitized)

        # Prevent hidden files and system files
        if sanitized.startswith(".") or sanitized.lower() in [
            "con",
            "prn",
            "aux",
            "nul",
        ]:
            sanitized = "safe_" + sanitized

        # Limit length
        return sanitized[:255]

    @classmethod
    def _sanitize_json(cls, value: str) -> str:
        """Sanitize JSON strings"""
        try:
            # Parse and re-serialize to remove potentially dangerous content
            parsed = json.loads(value)
            if isinstance(parsed, (dict, list)):
                # Recursively sanitize nested structures
                cleaned = cls.sanitize_dict(parsed)
                return json.dumps(cleaned)
            else:
                return cls._sanitize_default(str(parsed))
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON blocked: {value[:50]}...")
            return "{}"

    @classmethod
    def _sanitize_sql(cls, value: str) -> str:
        """Sanitize SQL-related strings (for search queries, etc.)"""
        # Remove SQL metacharacters
        sanitized = re.sub(r'[\'";\\]', "", value)

        # Remove SQL keywords that shouldn't be in user input
        sql_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER", "EXEC"]
        for keyword in sql_keywords:
            sanitized = re.sub(rf"\b{keyword}\b", "", sanitized, flags=re.IGNORECASE)

        return sanitized.strip()

    @classmethod
    def _sanitize_password(cls, value: str) -> str:
        """Light sanitization for passwords (preserve special chars)"""
        # Only remove obviously dangerous patterns but preserve password complexity
        sanitized = value

        # Remove HTML/script content
        sanitized = re.sub(r"<[^>]+>", "", sanitized)
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)

        return sanitized

    @classmethod
    def _sanitize_default(cls, value: str) -> str:
        """Default sanitization for general strings"""
        sanitized = value

        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Remove control characters except newlines and tabs
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        return sanitized

    @classmethod
    def sanitize_dict(
        cls, data: dict[str, Any], context_map: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Sanitize all string values in a dictionary

        Args:
            data: Dictionary to sanitize
            context_map: Map field names to sanitization contexts
        """
        if not isinstance(data, dict):
            return data

        context_map = context_map or {}
        sanitized = {}

        for key, value in data.items():
            # Sanitize the key itself
            safe_key = cls._sanitize_default(str(key)) if isinstance(key, str) else key

            # Determine context for this field
            context = context_map.get(key, "default")
            if key.lower() in ["email", "email_address"]:
                context = "email"
            elif key.lower() in ["password", "passwd", "pwd"]:
                context = "password"
            elif "filename" in key.lower() or "file_name" in key.lower():
                context = "filename"
            elif "html" in key.lower() or "content" in key.lower():
                context = "html"

            # Sanitize the value
            if isinstance(value, str):
                sanitized[safe_key] = cls.sanitize_string(value, context)
            elif isinstance(value, dict):
                sanitized[safe_key] = cls.sanitize_dict(value, context_map)
            elif isinstance(value, list):
                sanitized[safe_key] = cls.sanitize_list(value, context_map)
            else:
                # Numbers, booleans, None - pass through
                sanitized[safe_key] = value

        return sanitized

    @classmethod
    def sanitize_list(
        cls, data: list[Any], context_map: Optional[dict[str, str]] = None
    ) -> list[Any]:
        """Sanitize all values in a list"""
        if not isinstance(data, list):
            return data

        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(cls.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, context_map))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, context_map))
            else:
                sanitized.append(item)

        return sanitized

    @classmethod
    def validate_and_sanitize(
        cls, data: Any, rules: Optional[dict[str, Callable]] = None
    ) -> tuple[bool, Any, list[str]]:
        """
        Validate and sanitize data with custom rules

        Returns:
            (is_valid, sanitized_data, errors)
        """
        errors = []

        try:
            # Basic sanitization
            if isinstance(data, dict):
                sanitized = cls.sanitize_dict(data)
            elif isinstance(data, list):
                sanitized = cls.sanitize_list(data)
            elif isinstance(data, str):
                sanitized = cls.sanitize_string(data)
            else:
                sanitized = data

            # Apply custom validation rules
            if rules and isinstance(sanitized, dict):
                for field, validator in rules.items():
                    if field in sanitized:
                        try:
                            if not validator(sanitized[field]):
                                errors.append(f"Validation failed for field: {field}")
                        except Exception as e:
                            errors.append(f"Validation error for {field}: {str(e)}")

            return len(errors) == 0, sanitized, errors

        except Exception as e:
            logger.error(f"Sanitization failed: {e}")
            return False, data, [f"Sanitization failed: {str(e)}"]

    @classmethod
    def is_safe_input(cls, value: str) -> bool:
        """
        Quick check if input contains dangerous patterns
        Use this for early detection before full sanitization
        """
        if not isinstance(value, str):
            return True

        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, flags=re.IGNORECASE | re.DOTALL):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return False

        return True


# Convenience functions for common use cases
def sanitize_user_input(data: Union[str, dict, list]) -> Any:
    """Sanitize any user input data"""
    if isinstance(data, str):
        return SecuritySanitizer.sanitize_string(data)
    elif isinstance(data, dict):
        return SecuritySanitizer.sanitize_dict(data)
    elif isinstance(data, list):
        return SecuritySanitizer.sanitize_list(data)
    else:
        return data


def sanitize_search_query(query: str) -> str:
    """Sanitize search queries to prevent SQL injection"""
    return SecuritySanitizer.sanitize_string(query, "sql")


def sanitize_filename(filename: str) -> str:
    """Sanitize filenames for safe storage"""
    return SecuritySanitizer.sanitize_string(filename, "filename")


def sanitize_email(email: str) -> str:
    """Sanitize and validate email addresses"""
    return SecuritySanitizer.sanitize_string(email, "email")


def is_input_safe(data: Any) -> bool:
    """Check if input is safe before processing"""
    if isinstance(data, str):
        return SecuritySanitizer.is_safe_input(data)
    elif isinstance(data, dict):
        return all(
            SecuritySanitizer.is_safe_input(str(v))
            for v in data.values()
            if isinstance(v, str)
        )
    elif isinstance(data, list):
        return all(
            SecuritySanitizer.is_safe_input(str(item))
            for item in data
            if isinstance(item, str)
        )
    else:
        return True
