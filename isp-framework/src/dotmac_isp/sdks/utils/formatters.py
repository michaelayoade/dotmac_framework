"""Data formatting utilities."""

import re
from typing import Optional


def format_phone(phone: str, format_type: str = "us") -> str:
    """Format phone number."""
    # Remove all non-digits
    digits = re.sub(r"\D", "", phone)

    if format_type == "us" and len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif format_type == "us" and len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    return phone


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount."""
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"
