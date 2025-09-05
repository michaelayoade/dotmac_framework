"""
Universal currency formatting utilities for DotMac Framework.

Provides consistent currency formatting across all backend services
with multi-currency and locale support.
"""

import locale
from decimal import Decimal
from typing import Optional, Union

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "CHF": "CHF",
    "CNY": "¥",
    "INR": "₹",
    "BRL": "R$",
    "MXN": "$",
    "KRW": "₩",
    "SGD": "S$",
    "HKD": "HK$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "PLN": "zł",
    "CZK": "Kč",
    "HUF": "Ft",
    "RUB": "₽",
    "TRY": "₺",
    "ZAR": "R",
    "NZD": "NZ$",
    "NGN": "₦",
}

# Currencies with no decimal places
NO_DECIMAL_CURRENCIES = {"JPY", "KRW", "CLP", "ISK", "TWD", "VND"}

# Default locale mappings for currencies
CURRENCY_LOCALES = {
    "USD": "en_US",
    "EUR": "de_DE",
    "GBP": "en_GB",
    "JPY": "ja_JP",
    "CAD": "en_CA",
    "AUD": "en_AU",
    "CHF": "de_CH",
    "CNY": "zh_CN",
    "INR": "en_IN",
    "BRL": "pt_BR",
    "MXN": "es_MX",
    "KRW": "ko_KR",
    "SGD": "en_SG",
    "HKD": "zh_HK",
    "SEK": "sv_SE",
    "NOK": "nb_NO",
    "DKK": "da_DK",
    "PLN": "pl_PL",
    "CZK": "cs_CZ",
    "HUF": "hu_HU",
    "RUB": "ru_RU",
    "TRY": "tr_TR",
    "ZAR": "en_ZA",
    "NZD": "en_NZ",
    "NGN": "en_NG",
}


def format_currency(
    amount: Union[float, Decimal, int],
    currency_code: str = "USD",
    locale_name: Optional[str] = None,
    include_symbol: bool = True,
    show_decimals: Optional[bool] = None,
) -> str:
    """
    Format currency amount with proper localization.

    Args:
        amount: The monetary amount to format
        currency_code: ISO 4217 currency code (e.g., 'USD', 'EUR')
        locale_name: Locale for formatting (defaults to currency's default locale)
        include_symbol: Whether to include currency symbol
        show_decimals: Whether to show decimals (auto-detected if None)

    Returns:
        Formatted currency string

    Examples:
        >>> format_currency(1234.56, "USD")
        '$1,234.56'
        >>> format_currency(1234.56, "EUR", "de_DE")
        '1.234,56 €'
        >>> format_currency(1234, "JPY")
        '¥1,234'
    """
    # Convert to Decimal for precision
    if locale_name is None:
        locale_name = CURRENCY_LOCALES.get(currency_code, "en_US")
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))

    currency_code = currency_code.upper()

    # Determine decimal places
    if show_decimals is None:
        show_decimals = currency_code not in NO_DECIMAL_CURRENCIES

    decimal_places = 2 if show_decimals else 0

    # Use default locale for currency if not provided
    try:
        # Set locale for formatting
        locale.setlocale(locale.LC_MONETARY, f"{locale_name}.UTF-8")

        # Format using locale
        formatted = locale.currency(
            float(amount), symbol=include_symbol, grouping=True, international=False
        )

        # Handle currencies without symbols in locale data
        if include_symbol and currency_code in CURRENCY_SYMBOLS:
            symbol = CURRENCY_SYMBOLS[currency_code]
            if symbol not in formatted:
                formatted = f"{symbol}{formatted}"

    except (locale.Error, ValueError):
        # Fallback formatting if locale not available
        formatted = _fallback_format(
            amount, currency_code, include_symbol, decimal_places
        )

    return formatted


def _fallback_format(
    amount: Decimal, currency_code: str, include_symbol: bool, decimal_places: int
) -> str:
    """Fallback currency formatting when locale is unavailable."""

    # Format number with commas
    if decimal_places > 0:
        formatted_amount = f"{amount:,.{decimal_places}f}"
    else:
        formatted_amount = f"{int(amount):,}"

    if include_symbol and currency_code in CURRENCY_SYMBOLS:
        symbol = CURRENCY_SYMBOLS[currency_code]

        # Symbol placement varies by currency
        if currency_code in {"EUR"}:
            return f"{formatted_amount} {symbol}"
        else:
            return f"{symbol}{formatted_amount}"

    return f"{formatted_amount} {currency_code}"


def get_currency_info(currency_code: str) -> dict:
    """
    Get information about a currency.

    Args:
        currency_code: ISO 4217 currency code

    Returns:
        Dictionary with currency information
    """
    currency_code = currency_code.upper()

    return {
        "code": currency_code,
        "symbol": CURRENCY_SYMBOLS.get(currency_code, currency_code),
        "has_decimals": currency_code not in NO_DECIMAL_CURRENCIES,
        "default_locale": CURRENCY_LOCALES.get(currency_code, "en_US"),
        "decimal_places": 0 if currency_code in NO_DECIMAL_CURRENCIES else 2,
    }


def validate_currency_code(currency_code: str) -> bool:
    """
    Validate if currency code is supported.

    Args:
        currency_code: ISO 4217 currency code

    Returns:
        True if currency is supported
    """
    return currency_code.upper() in CURRENCY_SYMBOLS


def get_supported_currencies() -> list[str]:
    """Get list of supported currency codes."""
    return list(CURRENCY_SYMBOLS.keys())


# Convenience functions for common currencies
def format_usd(amount: Union[float, Decimal, int]) -> str:
    """Format amount as USD currency."""
    return format_currency(amount, "USD")


def format_eur(amount: Union[float, Decimal, int]) -> str:
    """Format amount as EUR currency."""
    return format_currency(amount, "EUR")


def format_gbp(amount: Union[float, Decimal, int]) -> str:
    """Format amount as GBP currency."""
    return format_currency(amount, "GBP")
