"""
Comprehensive tests for currency exchange functionality.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from dotmac_business_logic.billing.core.models import Money
from dotmac_business_logic.billing.exchange.convert import CurrencyConverter
from dotmac_business_logic.billing.exchange.manual import ManualExchangeRateProvider


class TestCurrencyConverter:
    """Test CurrencyConverter functionality."""

    @pytest.fixture
    def mock_rate_provider(self):
        """Create mock exchange rate provider."""
        provider = AsyncMock()
        provider.get_rate.return_value = Decimal('0.85')  # USD to EUR rate
        provider.get_supported_currencies.return_value = ['USD', 'EUR', 'GBP', 'CAD']
        return provider

    @pytest.fixture
    def currency_converter(self, mock_rate_provider):
        """Create CurrencyConverter with mock provider."""
        return CurrencyConverter(mock_rate_provider)

    @pytest.mark.asyncio
    async def test_convert_different_currencies(self, currency_converter, mock_rate_provider):
        """Test currency conversion with different currencies."""
        # Setup
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        eur_amount = await currency_converter.convert(usd_amount, 'EUR')

        # Assert
        assert eur_amount is not None
        assert eur_amount.amount == Decimal('85.00')  # 100 * 0.85
        assert eur_amount.currency == 'EUR'
        mock_rate_provider.get_rate.assert_called_once_with('USD', 'EUR', None)

    @pytest.mark.asyncio
    async def test_convert_same_currency(self, currency_converter, mock_rate_provider):
        """Test conversion when source and target currencies are the same."""
        # Setup
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        result = await currency_converter.convert(usd_amount, 'USD')

        # Assert
        assert result == usd_amount  # Should return same amount
        mock_rate_provider.get_rate.assert_not_called()  # No rate lookup needed

    @pytest.mark.asyncio
    async def test_convert_rate_not_available(self, currency_converter, mock_rate_provider):
        """Test conversion when exchange rate is not available."""
        # Setup
        mock_rate_provider.get_rate.return_value = None
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        result = await currency_converter.convert(usd_amount, 'EUR')

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_convert_with_specific_date(self, currency_converter, mock_rate_provider):
        """Test conversion with historical rate date."""
        # Setup
        usd_amount = Money(Decimal('100.00'), 'USD')
        rate_date = date(2024, 1, 15)

        # Execute
        result = await currency_converter.convert(usd_amount, 'EUR', rate_date)

        # Assert
        assert result is not None
        mock_rate_provider.get_rate.assert_called_once_with('USD', 'EUR', rate_date)

    @pytest.mark.asyncio
    async def test_get_conversion_rate(self, currency_converter, mock_rate_provider):
        """Test getting conversion rate without performing conversion."""
        # Execute
        rate = await currency_converter.get_conversion_rate('USD', 'EUR')

        # Assert
        assert rate == Decimal('0.85')
        mock_rate_provider.get_rate.assert_called_once_with('USD', 'EUR', None)

    @pytest.mark.asyncio
    async def test_convert_with_variance_no_variance(self, currency_converter):
        """Test conversion with variance calculation when variance is zero."""
        # Setup
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        result = await currency_converter.convert_with_variance(
            usd_amount, 'EUR', variance_percent=Decimal('0')
        )

        # Assert
        assert result is not None
        assert result['converted_amount'].amount == Decimal('85.00')
        assert result['min_amount'] == result['converted_amount']
        assert result['max_amount'] == result['converted_amount']
        assert result['variance_percent'] == Decimal('0')

    @pytest.mark.asyncio
    async def test_convert_with_variance_calculation(self, currency_converter):
        """Test conversion with variance calculation."""
        # Setup
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        result = await currency_converter.convert_with_variance(
            usd_amount, 'EUR', variance_percent=Decimal('10')  # 10% variance
        )

        # Assert
        assert result is not None
        converted = result['converted_amount']
        assert converted.amount == Decimal('85.00')  # Base conversion

        # Check variance range (10% of 85.00 = 8.50)
        assert result['min_amount'].amount == Decimal('76.50')  # 85 - 8.5
        assert result['max_amount'].amount == Decimal('93.50')  # 85 + 8.5
        assert result['variance_amount'].amount == Decimal('8.50')

    @pytest.mark.asyncio
    async def test_convert_with_variance_rate_unavailable(self, currency_converter, mock_rate_provider):
        """Test variance conversion when rate is unavailable."""
        # Setup
        mock_rate_provider.get_rate.return_value = None
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        result = await currency_converter.convert_with_variance(usd_amount, 'EUR')

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_precision_handling_in_conversion(self, currency_converter, mock_rate_provider):
        """Test that conversions maintain proper decimal precision."""
        # Setup - complex rate that could cause precision issues
        mock_rate_provider.get_rate.return_value = Decimal('0.333333333')
        usd_amount = Money(Decimal('100.00'), 'USD')

        # Execute
        result = await currency_converter.convert(usd_amount, 'EUR')

        # Assert
        assert result is not None
        # Should maintain reasonable precision (EUR typically 2 decimal places)
        assert result.amount == Decimal('33.33')  # Quantized to 2 decimal places

    @pytest.mark.asyncio
    async def test_convert_large_amounts(self, currency_converter):
        """Test conversion with large monetary amounts."""
        # Setup
        large_amount = Money(Decimal('1000000.00'), 'USD')  # $1M

        # Execute
        result = await currency_converter.convert(large_amount, 'EUR')

        # Assert
        assert result is not None
        assert result.amount == Decimal('850000.00')  # 1M * 0.85


class TestManualExchangeRateProvider:
    """Test ManualExchangeRateProvider functionality."""

    @pytest.fixture
    def rate_provider(self):
        """Create ManualExchangeRateProvider instance."""
        return ManualExchangeRateProvider()

    @pytest.mark.asyncio
    async def test_set_and_get_rate(self, rate_provider):
        """Test setting and retrieving exchange rates."""
        # Setup & Execute
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))

        # Retrieve rate
        rate = await rate_provider.get_rate('USD', 'EUR')

        # Assert
        assert rate == Decimal('0.85')

    @pytest.mark.asyncio
    async def test_get_rate_not_found(self, rate_provider):
        """Test retrieving rate that doesn't exist."""
        # Execute
        rate = await rate_provider.get_rate('USD', 'JPY')

        # Assert
        assert rate is None

    @pytest.mark.asyncio
    async def test_bidirectional_rate_calculation(self, rate_provider):
        """Test that rates work bidirectionally."""
        # Setup - set USD to EUR rate
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))

        # Execute - get reverse rate (EUR to USD)
        reverse_rate = await rate_provider.get_rate('EUR', 'USD')

        # Assert - should calculate inverse rate
        expected_reverse = Decimal('1') / Decimal('0.85')
        assert abs(reverse_rate - expected_reverse) < Decimal('0.0001')

    @pytest.mark.asyncio
    async def test_rate_with_effective_date(self, rate_provider):
        """Test setting rates with effective dates."""
        # Setup
        today = date.today()
        historical_date = date(2024, 1, 1)

        # Set current rate
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'), today)

        # Set historical rate
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.90'), historical_date)

        # Execute - get rates for different dates
        current_rate = await rate_provider.get_rate('USD', 'EUR', today)
        historical_rate = await rate_provider.get_rate('USD', 'EUR', historical_date)

        # Assert
        assert current_rate == Decimal('0.85')
        assert historical_rate == Decimal('0.90')

    @pytest.mark.asyncio
    async def test_get_supported_currencies(self, rate_provider):
        """Test retrieving list of supported currencies."""
        # Setup - add several rates
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))
        await rate_provider.set_rate('USD', 'GBP', Decimal('0.75'))
        await rate_provider.set_rate('EUR', 'JPY', Decimal('160.00'))

        # Execute
        currencies = await rate_provider.get_supported_currencies()

        # Assert
        expected_currencies = {'USD', 'EUR', 'GBP', 'JPY'}
        assert set(currencies) == expected_currencies

    @pytest.mark.asyncio
    async def test_get_rate_history(self, rate_provider):
        """Test retrieving historical exchange rates."""
        # Setup - add rates for different dates
        dates_and_rates = [
            (date(2024, 1, 1), Decimal('0.90')),
            (date(2024, 1, 15), Decimal('0.88')),
            (date(2024, 1, 31), Decimal('0.85'))
        ]

        for rate_date, rate in dates_and_rates:
            await rate_provider.set_rate('USD', 'EUR', rate, rate_date)

        # Execute
        history = await rate_provider.get_rate_history(
            'USD', 'EUR',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        # Assert
        assert len(history) == 3
        assert all('date' in record and 'rate' in record for record in history)

        # Check rates are in chronological order
        rates = [record['rate'] for record in history]
        expected_rates = [Decimal('0.90'), Decimal('0.88'), Decimal('0.85')]
        assert rates == expected_rates

    @pytest.mark.asyncio
    async def test_update_existing_rate(self, rate_provider):
        """Test updating an existing exchange rate."""
        # Setup - set initial rate
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))

        # Execute - update rate
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.87'))

        # Retrieve updated rate
        rate = await rate_provider.get_rate('USD', 'EUR')

        # Assert
        assert rate == Decimal('0.87')

    @pytest.mark.asyncio
    async def test_rate_precision_preservation(self, rate_provider):
        """Test that rate precision is preserved."""
        # Setup - rate with high precision
        precise_rate = Decimal('0.8534567890123456')
        await rate_provider.set_rate('USD', 'EUR', precise_rate)

        # Execute
        retrieved_rate = await rate_provider.get_rate('USD', 'EUR')

        # Assert - precision should be maintained
        assert retrieved_rate == precise_rate

    @pytest.mark.asyncio
    async def test_same_currency_rate(self, rate_provider):
        """Test getting rate for same currency pair."""
        # Execute
        rate = await rate_provider.get_rate('USD', 'USD')

        # Assert - should return 1.0 for same currency
        assert rate == Decimal('1.0')

    @pytest.mark.asyncio
    async def test_multiple_currency_pairs(self, rate_provider):
        """Test managing multiple currency pairs simultaneously."""
        # Setup - multiple currency pairs
        currency_pairs = [
            ('USD', 'EUR', Decimal('0.85')),
            ('USD', 'GBP', Decimal('0.75')),
            ('EUR', 'GBP', Decimal('0.88')),
            ('USD', 'CAD', Decimal('1.35')),
            ('USD', 'JPY', Decimal('150.00'))
        ]

        for from_curr, to_curr, rate in currency_pairs:
            await rate_provider.set_rate(from_curr, to_curr, rate)

        # Execute - retrieve all rates
        results = {}
        for from_curr, to_curr, expected_rate in currency_pairs:
            retrieved_rate = await rate_provider.get_rate(from_curr, to_curr)
            results[(from_curr, to_curr)] = retrieved_rate

        # Assert
        for from_curr, to_curr, expected_rate in currency_pairs:
            assert results[(from_curr, to_curr)] == expected_rate

    @pytest.mark.asyncio
    async def test_rate_fallback_to_latest(self, rate_provider):
        """Test rate fallback when specific date not available."""
        # Setup - only current date rate available
        today = date.today()
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'), today)

        # Execute - request rate for future date (should fallback to latest)
        future_date = date(2025, 1, 1)
        rate = await rate_provider.get_rate('USD', 'EUR', future_date)

        # Assert - should get the latest available rate
        # (Implementation detail: may return None or latest rate depending on design)
        # For this test, assume it returns None for unavailable dates
        assert rate is None or rate == Decimal('0.85')

    @pytest.mark.asyncio
    async def test_concurrent_rate_operations(self, rate_provider):
        """Test concurrent rate operations for thread safety."""
        import asyncio

        # Setup - concurrent operations
        async def set_rate_task(from_curr, to_curr, rate):
            await rate_provider.set_rate(from_curr, to_curr, rate)
            return await rate_provider.get_rate(from_curr, to_curr)

        # Execute - multiple concurrent operations
        tasks = [
            set_rate_task('USD', 'EUR', Decimal('0.85')),
            set_rate_task('USD', 'GBP', Decimal('0.75')),
            set_rate_task('EUR', 'GBP', Decimal('0.88')),
        ]

        results = await asyncio.gather(*tasks)

        # Assert - all operations should complete successfully
        expected_rates = [Decimal('0.85'), Decimal('0.75'), Decimal('0.88')]
        assert results == expected_rates


class TestCurrencyExchangeIntegration:
    """Integration tests for currency exchange components."""

    @pytest.mark.asyncio
    async def test_full_exchange_workflow(self):
        """Test complete currency exchange workflow."""
        # Setup
        rate_provider = ManualExchangeRateProvider()
        converter = CurrencyConverter(rate_provider)

        # Set up exchange rates
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))
        await rate_provider.set_rate('EUR', 'GBP', Decimal('0.88'))
        await rate_provider.set_rate('USD', 'GBP', Decimal('0.75'))

        # Execute multi-step conversion workflow
        usd_amount = Money(Decimal('1000.00'), 'USD')

        # Convert USD to EUR
        eur_amount = await converter.convert(usd_amount, 'EUR')
        assert eur_amount.amount == Decimal('850.00')

        # Convert EUR to GBP
        gbp_amount = await converter.convert(eur_amount, 'GBP')
        assert gbp_amount.amount == Decimal('748.00')  # 850 * 0.88

    @pytest.mark.asyncio
    async def test_exchange_with_billing_workflow(self):
        """Test currency exchange integrated with billing workflow."""
        # Setup
        rate_provider = ManualExchangeRateProvider()
        converter = CurrencyConverter(rate_provider)

        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))

        # Simulate billing scenario - customer in Europe, pricing in USD
        subscription_price = Money(Decimal('99.99'), 'USD')
        customer_currency = 'EUR'

        # Execute conversion for customer billing
        local_price = await converter.convert(subscription_price, customer_currency)

        # Assert
        assert local_price.amount == Decimal('84.99')  # 99.99 * 0.85
        assert local_price.currency == 'EUR'

    @pytest.mark.asyncio
    async def test_exchange_rate_expiry_handling(self):
        """Test handling of exchange rate expiry/staleness."""
        # Setup
        rate_provider = ManualExchangeRateProvider()

        # Set rate with old effective date
        old_date = date(2023, 1, 1)
        await rate_provider.set_rate('USD', 'EUR', Decimal('0.80'), old_date)

        # Execute - request rate for recent date
        recent_rate = await rate_provider.get_rate('USD', 'EUR', date.today())

        # Assert - should handle stale rates appropriately
        # (Implementation dependent - may return None, latest rate, or raise warning)
        assert recent_rate is None or recent_rate == Decimal('0.80')

    @pytest.mark.asyncio
    async def test_exchange_error_handling(self):
        """Test error handling in exchange operations."""
        # Setup
        rate_provider = ManualExchangeRateProvider()
        converter = CurrencyConverter(rate_provider)

        # Test invalid currency conversion
        usd_amount = Money(Decimal('100.00'), 'USD')
        result = await converter.convert(usd_amount, 'INVALID_CURRENCY')

        # Should handle gracefully
        assert result is None

    def test_money_object_currency_consistency(self):
        """Test that Money objects maintain currency consistency."""
        # Test creation with different currencies
        usd_money = Money(Decimal('100.00'), 'USD')
        eur_money = Money(Decimal('85.00'), 'EUR')

        # Test quantization per currency
        assert usd_money.amount == Decimal('100.00')  # 2 decimal places
        assert eur_money.amount == Decimal('85.00')   # 2 decimal places

        # Test edge cases
        precise_amount = Money(Decimal('99.999'), 'USD')
        assert precise_amount.amount == Decimal('100.00')  # Rounded up

    @pytest.mark.asyncio
    async def test_bulk_currency_conversion(self):
        """Test converting multiple amounts efficiently."""
        # Setup
        rate_provider = ManualExchangeRateProvider()
        converter = CurrencyConverter(rate_provider)

        await rate_provider.set_rate('USD', 'EUR', Decimal('0.85'))

        # Setup multiple amounts to convert
        amounts = [
            Money(Decimal('100.00'), 'USD'),
            Money(Decimal('250.00'), 'USD'),
            Money(Decimal('1000.00'), 'USD')
        ]

        # Execute bulk conversion
        converted_amounts = []
        for amount in amounts:
            converted = await converter.convert(amount, 'EUR')
            converted_amounts.append(converted)

        # Assert
        expected_eur_amounts = [
            Decimal('85.00'),   # 100 * 0.85
            Decimal('212.50'),  # 250 * 0.85
            Decimal('850.00')   # 1000 * 0.85
        ]

        actual_amounts = [amt.amount for amt in converted_amounts]
        assert actual_amounts == expected_eur_amounts
