"""
Manual exchange rate provider.

Simple in-memory exchange rate provider for manual rate management.
In production, rates would typically be stored in database.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .interfaces import ExchangeRateProvider


class ManualExchangeRateProvider(ExchangeRateProvider):
    """In-memory manual exchange rate provider."""

    def __init__(self):
        """Initialize with empty rate storage."""
        self._rates: dict[tuple[str, str, date], Decimal] = {}
        self._supported_currencies = {'USD'}  # Default base currency

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None,
    ) -> Optional[Decimal]:
        """Get exchange rate for currency pair."""
        if from_currency == to_currency:
            return Decimal('1.0')

        if not rate_date:
            rate_date = datetime.now().date()

        # Try exact date match first
        key = (from_currency, to_currency, rate_date)
        if key in self._rates:
            return self._rates[key]

        # Try to find most recent rate before the requested date
        matching_rates = [
            (stored_date, rate)
            for (from_curr, to_curr, stored_date), rate in self._rates.items()
            if from_curr == from_currency and to_curr == to_currency and stored_date <= rate_date
        ]

        if matching_rates:
            # Return most recent rate
            matching_rates.sort(key=lambda x: x[0], reverse=True)
            return matching_rates[0][1]

        # Try inverse rate
        inverse_key = (to_currency, from_currency, rate_date)
        if inverse_key in self._rates:
            return Decimal('1.0') / self._rates[inverse_key]

        # Try to find inverse rate in history
        inverse_matching = [
            (stored_date, rate)
            for (from_curr, to_curr, stored_date), rate in self._rates.items()
            if from_curr == to_currency and to_curr == from_currency and stored_date <= rate_date
        ]

        if inverse_matching:
            inverse_matching.sort(key=lambda x: x[0], reverse=True)
            return Decimal('1.0') / inverse_matching[0][1]

        return None

    async def set_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        effective_date: Optional[date] = None,
    ) -> None:
        """Set exchange rate for currency pair."""
        if not effective_date:
            effective_date = datetime.now().date()

        key = (from_currency, to_currency, effective_date)
        self._rates[key] = rate

        # Track supported currencies
        self._supported_currencies.add(from_currency)
        self._supported_currencies.add(to_currency)

    async def get_supported_currencies(self) -> list[str]:
        """Get list of supported currency codes."""
        return sorted(self._supported_currencies)

    async def get_rate_history(
        self,
        from_currency: str,
        to_currency: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Get historical exchange rates."""
        history = []

        for (from_curr, to_curr, stored_date), rate in self._rates.items():
            if (from_curr == from_currency and
                to_curr == to_currency and
                start_date <= stored_date <= end_date):

                history.append({
                    'date': stored_date,
                    'from_currency': from_curr,
                    'to_currency': to_curr,
                    'rate': rate,
                })

        # Sort by date
        history.sort(key=lambda x: x['date'])
        return history

    def load_initial_rates(self, rates_data: dict[str, dict[str, Decimal]]) -> None:
        """
        Load initial exchange rates.

        Args:
            rates_data: Dictionary in format {from_currency: {to_currency: rate}}
        """
        today = datetime.now().date()

        for from_currency, currency_rates in rates_data.items():
            for to_currency, rate in currency_rates.items():
                self._rates[(from_currency, to_currency, today)] = rate
                self._supported_currencies.add(from_currency)
                self._supported_currencies.add(to_currency)
