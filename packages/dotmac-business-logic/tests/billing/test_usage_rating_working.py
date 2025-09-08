"""
Working tests for usage rating engine that match the actual API.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.models import (
    BillingCycle,
    BillingPeriodValue,
    UsageMetric,
)
from dotmac_business_logic.billing.usage.rating import (
    TieredPricingEngine,
    UsageAggregator,
    UsageRatingEngine,
)


class TestUsageAggregatorWorking:
    """Test UsageAggregator with correct API."""

    @pytest.fixture
    def aggregator(self):
        """Create UsageAggregator instance."""
        return UsageAggregator()

    @pytest.fixture
    def billing_period(self):
        """Create test billing period with required cycle parameter."""
        return BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

    @pytest.fixture
    def usage_records(self):
        """Create test usage records."""
        return [
            Mock(
                meter_type="api_calls",
                quantity=Decimal("1500"),
                unit="calls",
                peak_usage=Decimal("100"),
                service_identifier="api_calls"  # Fallback if meter_type is None
            ),
            Mock(
                meter_type="api_calls",
                quantity=Decimal("800"),
                unit="calls",
                peak_usage=Decimal("150"),
                service_identifier="api_calls"
            ),
            Mock(
                meter_type="storage",
                quantity=Decimal("50.5"),
                unit="GB",
                peak_usage=Decimal("50.5"),
                service_identifier="storage"
            )
        ]

    @pytest.mark.asyncio
    async def test_aggregate_usage_for_period(self, aggregator, billing_period, usage_records):
        """Test usage aggregation for a billing period."""
        # Execute
        result = await aggregator.aggregate_usage_for_period(
            subscription_id=uuid4(),
            billing_period=billing_period,
            usage_records=usage_records
        )

        # Assert
        assert len(result) == 2  # Two different meter types

        # Check API calls aggregation
        api_calls_metric = result["api_calls"]
        assert isinstance(api_calls_metric, UsageMetric)
        assert api_calls_metric.quantity == Decimal("2300")  # 1500 + 800
        assert api_calls_metric.unit == "calls"
        assert api_calls_metric.name == "api_calls"
        assert api_calls_metric.period == billing_period

        # Check storage aggregation
        storage_metric = result["storage"]
        assert storage_metric.quantity == Decimal("50.5")
        assert storage_metric.unit == "GB"

    @pytest.mark.asyncio
    async def test_apply_usage_allowances_no_overage(self, aggregator, billing_period):
        """Test applying allowances when usage is within limits."""
        # Setup
        usage_metrics = {
            "api_calls": UsageMetric(
                name="api_calls",
                quantity=Decimal("800"),  # Under 1000 allowance
                unit="calls",
                period=billing_period
            )
        }

        subscription_plan = Mock()
        subscription_plan.usage_allowances = {"api_calls": Decimal("1000")}

        # Execute
        result = await aggregator.apply_usage_allowances(usage_metrics, subscription_plan)

        # Assert - no overage, so empty result
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_apply_usage_allowances_with_overage(self, aggregator, billing_period):
        """Test applying allowances when usage exceeds limits."""
        # Setup
        usage_metrics = {
            "api_calls": UsageMetric(
                name="api_calls",
                quantity=Decimal("1500"),  # Over 1000 allowance
                unit="calls",
                period=billing_period
            )
        }

        subscription_plan = Mock()
        subscription_plan.usage_allowances = {"api_calls": Decimal("1000")}

        # Execute
        result = await aggregator.apply_usage_allowances(usage_metrics, subscription_plan)

        # Assert
        assert len(result) == 1
        overage_metric = result["api_calls_overage"]
        assert overage_metric.quantity == Decimal("500")  # 1500 - 1000
        assert overage_metric.name == "api_calls_overage"

    def test_calculate_average_usage(self, aggregator):
        """Test daily average usage calculation."""
        # Setup
        usage_records = [
            Mock(meter_type="api_calls", quantity=Decimal("3100"), service_identifier="api_calls"),
            Mock(meter_type="storage", quantity=Decimal("155"), service_identifier="storage"),
        ]
        period_days = 31

        # Execute
        result = aggregator.calculate_average_usage(usage_records, period_days)

        # Assert
        assert "api_calls_daily_avg" in result
        assert "storage_daily_avg" in result
        assert result["api_calls_daily_avg"] == Decimal("100")  # 3100 / 31
        assert result["storage_daily_avg"] == Decimal("5")     # 155 / 31

    def test_calculate_average_usage_edge_cases(self, aggregator):
        """Test edge cases for average usage calculation."""
        # Empty records
        result = aggregator.calculate_average_usage([], 30)
        assert result == {}

        # Zero period days
        result = aggregator.calculate_average_usage([
            Mock(meter_type="test", quantity=Decimal("100"), service_identifier="test")
        ], 0)
        assert result == {}

    def test_calculate_average_usage_fallback_identifier(self, aggregator):
        """Test usage with service_identifier fallback when meter_type is None."""
        # Setup
        usage_records = [
            Mock(meter_type=None, service_identifier="api_service", quantity=Decimal("200")),
            Mock(meter_type="bandwidth", service_identifier="bandwidth", quantity=Decimal("100")),
        ]

        # Execute
        result = aggregator.calculate_average_usage(usage_records, 10)

        # Assert
        assert "api_service_daily_avg" in result
        assert "bandwidth_daily_avg" in result
        assert result["api_service_daily_avg"] == Decimal("20")  # 200 / 10
        assert result["bandwidth_daily_avg"] == Decimal("10")   # 100 / 10


class TestTieredPricingEngineWorking:
    """Test TieredPricingEngine functionality."""

    @pytest.fixture
    def pricing_engine(self):
        """Create TieredPricingEngine instance."""
        return TieredPricingEngine()

    @pytest.fixture
    def pricing_tiers(self):
        """Create test pricing tiers."""
        return [
            {
                "name": "Tier 1",
                "min_quantity": 0,
                "max_quantity": 1000,
                "unit_price": "0.01"
            },
            {
                "name": "Tier 2",
                "min_quantity": 1000,
                "max_quantity": 5000,
                "unit_price": "0.008"
            },
            {
                "name": "Tier 3",
                "min_quantity": 5000,
                "max_quantity": float('inf'),
                "unit_price": "0.005"
            }
        ]

    def test_calculate_tiered_pricing_single_tier(self, pricing_engine, pricing_tiers):
        """Test pricing calculation within single tier."""
        # Execute - 500 units in first tier
        result = pricing_engine.calculate_tiered_pricing(
            quantity=Decimal("500"),
            pricing_tiers=pricing_tiers
        )

        # Assert
        assert result["total_charge"] == Decimal("5.00")  # 500 * 0.01
        assert result["effective_rate"] == Decimal("0.01")
        assert len(result["tier_details"]) == 1
        assert result["tier_details"][0]["quantity_in_tier"] == Decimal("500")

    def test_calculate_tiered_pricing_multiple_tiers(self, pricing_engine, pricing_tiers):
        """Test pricing calculation across multiple tiers."""
        # Execute - 3000 units across first two tiers
        result = pricing_engine.calculate_tiered_pricing(
            quantity=Decimal("3000"),
            pricing_tiers=pricing_tiers
        )

        # Assert
        # Tier 1: 1000 * 0.01 = 10.00
        # Tier 2: 2000 * 0.008 = 16.00
        # Total: 26.00
        assert result["total_charge"] == Decimal("26.00")
        assert len(result["tier_details"]) == 2

    def test_calculate_tiered_pricing_empty_tiers(self, pricing_engine):
        """Test pricing with empty tier list."""
        # Execute
        result = pricing_engine.calculate_tiered_pricing(
            quantity=Decimal("1000"),
            pricing_tiers=[]
        )

        # Assert
        assert result["total_charge"] == Decimal("0")
        assert result["effective_rate"] == Decimal("0")
        assert result["tier_details"] == []

    def test_calculate_volume_discount_applicable(self, pricing_engine):
        """Test volume discount when discount applies."""
        # Setup
        base_charge = Decimal("100.00")
        quantity = Decimal("5000")
        volume_discounts = [
            {
                "name": "Volume Discount 1",
                "min_quantity": 1000,
                "discount_percent": 10
            },
            {
                "name": "Volume Discount 2",
                "min_quantity": 5000,
                "discount_percent": 15
            }
        ]

        # Execute
        final_charge, discount_applied = pricing_engine.calculate_volume_discount(
            base_charge, quantity, volume_discounts
        )

        # Assert - should apply 15% discount (higher quantity threshold)
        assert final_charge == Decimal("85.00")  # 100 - 15
        assert discount_applied is not None
        assert discount_applied["discount_percent"] == 15
        assert discount_applied["discount_amount"] == Decimal("15.00")

    def test_calculate_volume_discount_not_applicable(self, pricing_engine):
        """Test volume discount when no discount applies."""
        # Setup
        base_charge = Decimal("100.00")
        quantity = Decimal("500")  # Below minimum
        volume_discounts = [
            {
                "name": "Volume Discount",
                "min_quantity": 1000,
                "discount_percent": 10
            }
        ]

        # Execute
        final_charge, discount_applied = pricing_engine.calculate_volume_discount(
            base_charge, quantity, volume_discounts
        )

        # Assert
        assert final_charge == base_charge
        assert discount_applied is None


class TestUsageRatingEngineWorking:
    """Test UsageRatingEngine integration."""

    @pytest.fixture
    def rating_engine(self):
        """Create UsageRatingEngine instance."""
        return UsageRatingEngine()

    @pytest.fixture
    def subscription(self):
        """Create test subscription."""
        return Mock(
            id=uuid4(),
            billing_plan=Mock(
                usage_allowances={"api_calls": Decimal("1000")},
                usage_pricing={
                    "api_calls_overage": {
                        "pricing_model": "flat",
                        "unit_price": "0.01",
                        "description": "API Call Overage",
                        "taxable": True
                    }
                }
            )
        )

    @pytest.fixture
    def billing_period(self):
        """Create test billing period."""
        return BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

    @pytest.fixture
    def usage_records_with_overage(self):
        """Create usage records that exceed allowances."""
        return [
            Mock(
                meter_type="api_calls",
                quantity=Decimal("1500"),  # 500 over allowance
                unit="calls",
                service_identifier="api_calls"
            )
        ]

    @pytest.mark.asyncio
    async def test_rate_usage_for_subscription_with_overage(self, rating_engine,
                                                           subscription, billing_period,
                                                           usage_records_with_overage):
        """Test rating usage with overage charges."""
        # Execute
        line_items = await rating_engine.rate_usage_for_subscription(
            subscription=subscription,
            billing_period=billing_period,
            usage_records=usage_records_with_overage
        )

        # Assert
        assert len(line_items) == 1
        line_item = line_items[0]
        assert line_item["amount"] == Decimal("5.00")  # 500 * 0.01
        assert line_item["quantity"] == Decimal("500")  # Overage amount
        assert line_item["taxable"] is True
        assert "API Call Overage" in line_item["description"]

    @pytest.mark.asyncio
    async def test_rate_usage_for_subscription_no_overage(self, rating_engine,
                                                         subscription, billing_period):
        """Test rating usage with no overage."""
        # Setup - usage within allowances
        usage_records = [
            Mock(
                meter_type="api_calls",
                quantity=Decimal("800"),  # Under 1000 allowance
                unit="calls",
                service_identifier="api_calls"
            )
        ]

        # Execute
        line_items = await rating_engine.rate_usage_for_subscription(
            subscription=subscription,
            billing_period=billing_period,
            usage_records=usage_records
        )

        # Assert - no line items for usage within allowances
        assert len(line_items) == 0

    @pytest.mark.asyncio
    async def test_rate_usage_with_tiered_pricing(self, rating_engine, billing_period):
        """Test rating usage with tiered pricing model."""
        # Setup subscription with tiered pricing
        subscription = Mock(
            id=uuid4(),
            billing_plan=Mock(
                usage_allowances={"api_calls": Decimal("0")},  # No free allowance
                usage_pricing={
                    "api_calls_overage": {
                        "pricing_model": "tiered",
                        "description": "API Calls",
                        "tiers": [
                            {
                                "name": "First 1000",
                                "min_quantity": 0,
                                "max_quantity": 1000,
                                "unit_price": "0.01"
                            },
                            {
                                "name": "Next 4000",
                                "min_quantity": 1000,
                                "max_quantity": 5000,
                                "unit_price": "0.008"
                            }
                        ],
                        "taxable": True
                    }
                }
            )
        )

        usage_records = [
            Mock(
                meter_type="api_calls",
                quantity=Decimal("3000"),
                unit="calls",
                service_identifier="api_calls"
            )
        ]

        # Execute
        line_items = await rating_engine.rate_usage_for_subscription(
            subscription=subscription,
            billing_period=billing_period,
            usage_records=usage_records
        )

        # Assert
        assert len(line_items) == 1
        line_item = line_items[0]
        # Tier 1: 1000 * 0.01 = 10.00
        # Tier 2: 2000 * 0.008 = 16.00
        # Total: 26.00
        assert line_item["amount"] == Decimal("26.00")

    @pytest.mark.asyncio
    async def test_calculate_usage_summary(self, rating_engine, billing_period):
        """Test usage summary generation."""
        # Setup
        subscription_id = uuid4()
        usage_records = [
            Mock(meter_type="api_calls", quantity=Decimal("1500"), service_identifier="api_calls"),
            Mock(meter_type="storage", quantity=Decimal("100"), service_identifier="storage")
        ]

        # Execute
        summary = await rating_engine.calculate_usage_summary(
            subscription_id=subscription_id,
            usage_records=usage_records,
            billing_period=billing_period
        )

        # Assert
        assert summary["subscription_id"] == subscription_id
        assert summary["total_records"] == 2
        assert "billing_period" in summary
        assert "usage_metrics" in summary
        assert "daily_averages" in summary

        # Check metrics
        assert "api_calls" in summary["usage_metrics"]
        assert "storage" in summary["usage_metrics"]
        assert summary["usage_metrics"]["api_calls"]["quantity"] == Decimal("1500")

    def test_format_usage_description(self, rating_engine):
        """Test usage description formatting."""
        # Setup
        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        usage_metric = UsageMetric(
            name="api_calls_overage",
            quantity=Decimal("500"),
            unit="calls",
            period=billing_period
        )

        pricing_config = {
            "description": "API Call Overage"
        }

        # Execute
        description = rating_engine._format_usage_description(usage_metric, pricing_config)

        # Assert
        assert "API Call Overage" in description
        assert "2024-01-01" in description
        assert "2024-01-31" in description

    def test_get_usage_pricing_config(self, rating_engine):
        """Test usage pricing configuration lookup."""
        # Setup
        billing_plan = Mock()
        billing_plan.usage_pricing = {
            "api_calls_overage": {
                "unit_price": "0.01",
                "description": "API Overage"
            }
        }

        # Execute
        config = rating_engine._get_usage_pricing_config(billing_plan, "api_calls_overage")

        # Assert
        assert config is not None
        assert config["unit_price"] == "0.01"
        assert config["description"] == "API Overage"

        # Test missing config
        missing_config = rating_engine._get_usage_pricing_config(billing_plan, "nonexistent")
        assert missing_config is None

    @pytest.mark.asyncio
    async def test_complex_usage_scenarios(self, rating_engine, billing_period):
        """Test complex usage scenarios with multiple metrics."""
        # Setup complex subscription with multiple usage types
        subscription = Mock(
            id=uuid4(),
            billing_plan=Mock(
                usage_allowances={
                    "api_calls": Decimal("1000"),
                    "bandwidth": Decimal("100")  # GB
                },
                usage_pricing={
                    "api_calls_overage": {
                        "pricing_model": "flat",
                        "unit_price": "0.01",
                        "description": "API Call Overage",
                        "taxable": True
                    },
                    "bandwidth_overage": {
                        "pricing_model": "tiered",
                        "description": "Bandwidth Overage",
                        "tiers": [
                            {
                                "min_quantity": 0,
                                "max_quantity": 100,
                                "unit_price": "0.50"
                            },
                            {
                                "min_quantity": 100,
                                "max_quantity": float('inf'),
                                "unit_price": "0.30"
                            }
                        ],
                        "taxable": True
                    }
                }
            )
        )

        usage_records = [
            Mock(meter_type="api_calls", quantity=Decimal("1200"), unit="calls", service_identifier="api_calls"),
            Mock(meter_type="bandwidth", quantity=Decimal("250"), unit="GB", service_identifier="bandwidth")
        ]

        # Execute
        line_items = await rating_engine.rate_usage_for_subscription(
            subscription=subscription,
            billing_period=billing_period,
            usage_records=usage_records
        )

        # Assert
        assert len(line_items) == 2  # Both overages should generate line items

        # Find API calls overage
        api_item = next(item for item in line_items if "API Call" in item["description"])
        assert api_item["amount"] == Decimal("2.00")  # 200 overage * 0.01

        # Find bandwidth overage
        bandwidth_item = next(item for item in line_items if "Bandwidth" in item["description"])
        # 150 GB overage: first 100 at $0.50 + next 50 at $0.30 = $50 + $15 = $65
        assert bandwidth_item["amount"] == Decimal("65.00")

    @pytest.mark.asyncio
    async def test_zero_usage_handling(self, rating_engine, billing_period):
        """Test handling of zero usage scenarios."""
        # Setup
        subscription = Mock(
            id=uuid4(),
            billing_plan=Mock(
                usage_allowances={"api_calls": Decimal("1000")},
                usage_pricing={}
            )
        )

        # No usage records
        usage_records = []

        # Execute
        line_items = await rating_engine.rate_usage_for_subscription(
            subscription=subscription,
            billing_period=billing_period,
            usage_records=usage_records
        )

        # Assert - should handle gracefully
        assert len(line_items) == 0

        # Test with zero-quantity records
        usage_records = [
            Mock(meter_type="api_calls", quantity=Decimal("0"), unit="calls", service_identifier="api_calls")
        ]

        line_items = await rating_engine.rate_usage_for_subscription(
            subscription=subscription,
            billing_period=billing_period,
            usage_records=usage_records
        )

        assert len(line_items) == 0  # No overage, no charge
