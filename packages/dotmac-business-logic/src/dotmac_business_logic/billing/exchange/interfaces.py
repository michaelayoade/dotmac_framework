"""
Exchange rate provider interfaces.

Defines the contract for exchange rate providers that can be
implemented with different backends (manual, API-based, etc.).
"""

from abc import abstractmethod
from datetime import date
from decimal import Decimal
from typing import Optional, Protocol


class ExchangeRateProvider(Protocol):
    """Protocol for exchange rate providers."""

    @abstractmethod
    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None,
    ) -> Optional[Decimal]:
        """
        Get exchange rate for currency pair.

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR')
            rate_date: Date for historical rates (defaults to current)

        Returns:
            Exchange rate or None if not available
        """

    @abstractmethod
    async def set_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        effective_date: Optional[date] = None,
    ) -> None:
        """
        Set exchange rate for currency pair.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate: Exchange rate
            effective_date: When rate becomes effective
        """

    @abstractmethod
    async def get_supported_currencies(self) -> list[str]:
        """Get list of supported currency codes."""

    @abstractmethod
    async def get_rate_history(
        self,
        from_currency: str,
        to_currency: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """
        Get historical exchange rates.

        Returns:
            List of rate records with date and rate
        """
