"""
Currency conversion utilities.

Provides high-level currency conversion functionality using
exchange rate providers.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from ..core.models import Money
from .interfaces import ExchangeRateProvider


class CurrencyConverter:
    """Currency converter using exchange rate providers."""

    def __init__(self, rate_provider: ExchangeRateProvider):
        """
        Initialize converter with rate provider.

        Args:
            rate_provider: Exchange rate provider implementation
        """
        self.rate_provider = rate_provider

    async def convert(
        self,
        amount: Money,
        to_currency: str,
        rate_date: Optional[date] = None,
    ) -> Optional[Money]:
        """
        Convert money amount to target currency.

        Args:
            amount: Money amount to convert
            to_currency: Target currency code
            rate_date: Date for exchange rate lookup

        Returns:
            Converted Money amount or None if rate unavailable
        """
        if amount.currency == to_currency:
            return amount

        rate = await self.rate_provider.get_rate(
            amount.currency,
            to_currency,
            rate_date,
        )

        if rate is None:
            return None

        converted_amount = amount.amount * rate
        return Money(converted_amount, to_currency)

    async def get_conversion_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None,
    ) -> Optional[Decimal]:
        """
        Get conversion rate between currencies.

        Args:
            from_currency: Source currency
            to_currency: Target currency
            rate_date: Date for rate lookup

        Returns:
            Exchange rate or None if unavailable
        """
        return await self.rate_provider.get_rate(
            from_currency,
            to_currency,
            rate_date,
        )

    async def convert_with_variance(
        self,
        amount: Money,
        to_currency: str,
        rate_date: Optional[date] = None,
        variance_percent: Decimal = Decimal('0'),
    ) -> Optional[dict]:
        """
        Convert with variance calculation for budgeting.

        Args:
            amount: Money amount to convert
            to_currency: Target currency
            rate_date: Date for rate lookup
            variance_percent: Variance percentage for range calculation

        Returns:
            Dictionary with converted amount and variance range
        """
        base_conversion = await self.convert(amount, to_currency, rate_date)
        if base_conversion is None:
            return None

        if variance_percent == Decimal('0'):
            return {
                'converted_amount': base_conversion,
                'min_amount': base_conversion,
                'max_amount': base_conversion,
                'variance_percent': variance_percent,
            }

        # Calculate variance range
        variance_multiplier = variance_percent / Decimal('100')
        variance_amount = base_conversion.amount * variance_multiplier

        min_amount = Money(
            base_conversion.amount - variance_amount,
            base_conversion.currency
        )
        max_amount = Money(
            base_conversion.amount + variance_amount,
            base_conversion.currency
        )

        return {
            'converted_amount': base_conversion,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'variance_percent': variance_percent,
            'variance_amount': Money(variance_amount, base_conversion.currency),
        }
