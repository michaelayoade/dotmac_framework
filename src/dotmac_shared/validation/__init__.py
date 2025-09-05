"""
Validation utilities for DotMac Framework.

This module provides common validation patterns and business rule validators
that can be reused across all modules.

Usage:
    from dotmac_shared.validation import BusinessValidators

    # Validate email
    email = BusinessValidators.validate_email("user@example.com")

    # Validate phone
    phone = BusinessValidators.validate_phone("+1-555-123-4567")

    # Validate password strength
    BusinessValidators.validate_password("MyStrongPass123!")
"""

from .business_validators import BusinessValidators

__all__ = [
    "BusinessValidators",
]
