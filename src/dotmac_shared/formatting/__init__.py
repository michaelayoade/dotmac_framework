"""
Universal formatting utilities for DotMac Framework.

Provides consistent data formatting across all services and platforms.
"""

from .currency import (
    CURRENCY_LOCALES,
    CURRENCY_SYMBOLS,
    NO_DECIMAL_CURRENCIES,
    format_currency,
    format_eur,
    format_gbp,
    format_usd,
    get_currency_info,
    get_supported_currencies,
    validate_currency_code,
)

__all__ = [
    # Currency formatting
    "format_currency",
    "get_currency_info",
    "validate_currency_code",
    "get_supported_currencies",
    "format_usd",
    "format_eur",
    "format_gbp",
    "CURRENCY_SYMBOLS",
    "NO_DECIMAL_CURRENCIES",
    "CURRENCY_LOCALES",
]
