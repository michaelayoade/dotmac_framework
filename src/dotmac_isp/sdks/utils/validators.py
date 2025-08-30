"""Data validation utilities."""

import re
from typing import Optional


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    # Simple validation - digits and common separators
    pattern = r"^[\d\s\-\(\)\+\.]{10,15}$"
    return bool(re.match(pattern, phone))
