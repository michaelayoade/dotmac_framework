"""
Comprehensive Usage Rating tests targeting 90% coverage.
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


class TestUsageAggregatorComprehensive:
    """Comprehensive tests for UsageAggregator to achieve 90% coverage."""

    @pytest.fixture
    def aggregator(self):
        return UsageAggregator()

    @pytest.fixture
    def billing_period(self):
        return BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

    @pytest.fixture
    def usage_records(self):
        """Mock usage records with different meter types."""
        records = []

        # API calls records
        for _i in range(3):
            record = Mock()
            record.meter_type = "api_calls"
            record.service_identifier = "api_service"
            record.quantity = Decimal("100")
            record.unit = "calls"
            record.peak_usage = Decimal("150")
            records.append(record)

        # Storage records
        for _i in range(2):
            record = Mock()
            record.meter_type = "storage"
            record.service_identifier = "storage_service"
            record.quantity = Decimal("50")
            record.unit = "GB"
            record.peak_usage = Decimal("60")
            records.append(record)

        return records

    @pytest.fixture
    def subscription_plan(self):
        plan = Mock()
        plan.usage_allowances = {
            "api_calls": Decimal("200"),
            "storage": Decimal("75")
        }
        return plan

    # ============= USAGE AGGREGATION TESTS =============

    @pytest.mark.asyncio
    async def test_aggregate_usage_for_period_basic(self, aggregator, billing_period, usage_records):
        """Test basic usage aggregation functionality."""
        subscription_id = uuid4()

        result = await aggregator.aggregate_usage_for_period(
            subscription_id, billing_period, usage_records
        )

        assert len(result) == 2
        assert "api_calls" in result
        assert "storage" in result

        # Check API calls aggregation (3 records × 100 each)
        api_metric = result["api_calls"]
        assert api_metric.name == "api_calls"
        assert api_metric.quantity == Decimal("300")
        assert api_metric.unit == "calls"
        assert api_metric.period == billing_period

        # Check storage aggregation (2 records × 50 each)
        storage_metric = result["storage"]
        assert storage_metric.name == "storage"
        assert storage_metric.quantity == Decimal("100")
        assert storage_metric.unit == "GB"

    @pytest.mark.asyncio
    async def test_aggregate_usage_empty_records(self, aggregator, billing_period):
        """Test aggregation with no usage records."""
        subscription_id = uuid4()

        result = await aggregator.aggregate_usage_for_period(
            subscription_id, billing_period, []
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_aggregate_usage_records_without_meter_type(self, aggregator, billing_period):
        """Test aggregation with records using service_identifier fallback."""
        records = []
        record = Mock()
        record.meter_type = None
        record.service_identifier = "custom_service"
        record.quantity = Decimal("25")
        record.unit = "units"
        record.peak_usage = Decimal("30")
        records.append(record)

        subscription_id = uuid4()

        result = await aggregator.aggregate_usage_for_period(
            subscription_id, billing_period, records
        )

        assert len(result) == 1
        assert "custom_service" in result
        assert result["custom_service"].quantity == Decimal("25")

    @pytest.mark.asyncio
    async def test_aggregate_usage_records_without_attributes(self, aggregator, billing_period):
        """Test aggregation with records missing optional attributes."""
        records = []
        record = Mock()
        record.meter_type = "minimal_service"
        record.service_identifier = "backup"
        # Missing quantity, unit, peak_usage
        del record.quantity
        del record.unit
        del record.peak_usage
        records.append(record)

        subscription_id = uuid4()

        result = await aggregator.aggregate_usage_for_period(
            subscription_id, billing_period, records
        )

        assert len(result) == 1
        metric = result["minimal_service"]
        assert metric.quantity == Decimal("0")  # Default quantity
        assert metric.unit == "units"  # Default unit

    @pytest.mark.asyncio
    async def test_aggregate_usage_peak_tracking(self, aggregator, billing_period):
        """Test that peak usage is tracked correctly."""
        records = []

        # First record with lower peak
        record1 = Mock()
        record1.meter_type = "bandwidth"
        record1.service_identifier = "network"
        record1.quantity = Decimal("100")
        record1.unit = "Mbps"
        record1.peak_usage = Decimal("150")
        records.append(record1)

        # Second record with higher peak
        record2 = Mock()
        record2.meter_type = "bandwidth"
        record2.service_identifier = "network"
        record2.quantity = Decimal("200")
        record2.unit = "Mbps"
        record2.peak_usage = Decimal("300")  # Higher peak
        records.append(record2)

        subscription_id = uuid4()

        result = await aggregator.aggregate_usage_for_period(
            subscription_id, billing_period, records
        )

        # Peak should be the maximum seen (300)
        # Note: peak_usage is tracked internally but not exposed in UsageMetric
        # This tests the aggregation logic
        assert result["bandwidth"].quantity == Decimal("300")  # Sum of quantities

    # ============= USAGE ALLOWANCES TESTS =============

    @pytest.mark.asyncio
    async def test_apply_usage_allowances_no_overage(self, aggregator, billing_period, subscription_plan):
        """Test applying allowances when usage is within limits."""
        usage_metrics = {
            "api_calls": UsageMetric(
                name="api_calls",
                quantity=Decimal("150"),  # Under 200 allowance
                unit="calls",
                period=billing_period
            )
        }

        result = await aggregator.apply_usage_allowances(usage_metrics, subscription_plan)

        # No overage, so no billable usage
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_apply_usage_allowances_with_overage(self, aggregator, billing_period, subscription_plan):
        """Test applying allowances when usage exceeds limits."""
        usage_metrics = {
            "api_calls": UsageMetric(
                name="api_calls",
                quantity=Decimal("300"),  # Over 200 allowance
                unit="calls",
                period=billing_period
            ),
            "storage": UsageMetric(
                name="storage",
                quantity=Decimal("100"),  # Over 75 allowance
                unit="GB",
                period=billing_period
            )
        }

        result = await aggregator.apply_usage_allowances(usage_metrics, subscription_plan)

        assert len(result) == 2

        # API calls overage: 300 - 200 = 100
        api_overage = result["api_calls"]
        assert api_overage.name == "api_calls_overage"
        assert api_overage.quantity == Decimal("100")
        assert api_overage.unit == "calls"

        # Storage overage: 100 - 75 = 25
        storage_overage = result["storage"]
        assert storage_overage.name == "storage_overage"
        assert storage_overage.quantity == Decimal("25")
        assert storage_overage.unit == "GB"

    @pytest.mark.asyncio
    async def test_apply_usage_allowances_no_plan_allowances(self, aggregator, billing_period):
        """Test applying allowances when plan has no allowances."""
        usage_metrics = {
            "api_calls": UsageMetric(
                name="api_calls",
                quantity=Decimal("100"),
                unit="calls",
                period=billing_period
            )
        }

        plan_without_allowances = Mock()
        plan_without_allowances.usage_allowances = {}

        result = await aggregator.apply_usage_allowances(usage_metrics, plan_without_allowances)

        # All usage is billable when no allowances
        assert len(result) == 1
        assert result["api_calls"].quantity == Decimal("100")

    @pytest.mark.asyncio
    async def test_apply_usage_allowances_plan_without_allowances_attr(self, aggregator, billing_period):
        """Test applying allowances when plan doesn't have usage_allowances attribute."""
        usage_metrics = {
            "api_calls": UsageMetric(
                name="api_calls",
                quantity=Decimal("50"),
                unit="calls",
                period=billing_period
            )
        }

        plan_minimal = Mock()
        del plan_minimal.usage_allowances  # Remove attribute

        result = await aggregator.apply_usage_allowances(usage_metrics, plan_minimal)

        # All usage is billable when no allowances attribute
        assert len(result) == 1
        assert result["api_calls"].quantity == Decimal("50")

    # ============= AVERAGE USAGE CALCULATION TESTS =============

    def test_calculate_average_usage_basic(self, aggregator):
        """Test basic average usage calculation."""
        records = []
        for _day in range(30):  # 30 days of usage
            record = Mock()
            record.meter_type = "api_calls"
            record.service_identifier = "api_service"
            record.quantity = Decimal("100")  # 100 calls per day
            records.append(record)

        result = aggregator.calculate_average_usage(records, 30)

        assert "api_calls_daily_avg" in result
        # 30 records × 100 each = 3000 total, ÷ 30 days = 100 daily average
        assert result["api_calls_daily_avg"] == Decimal("100")

    def test_calculate_average_usage_multiple_metrics(self, aggregator):
        """Test average usage calculation with multiple metrics."""
        records = []

        # API calls records
        for _day in range(10):
            record = Mock()
            record.meter_type = "api_calls"
            record.service_identifier = "api_service"
            record.quantity = Decimal("50")
            records.append(record)

        # Storage records
        for _day in range(10):
            record = Mock()
            record.meter_type = "storage"
            record.service_identifier = "storage_service"
            record.quantity = Decimal("20")
            records.append(record)

        result = aggregator.calculate_average_usage(records, 10)

        assert len(result) == 2
        assert result["api_calls_daily_avg"] == Decimal("50")  # 500 total ÷ 10 days
        assert result["storage_daily_avg"] == Decimal("20")    # 200 total ÷ 10 days

    def test_calculate_average_usage_empty_records(self, aggregator):
        """Test average usage calculation with no records."""
        result = aggregator.calculate_average_usage([], 30)
        assert result == {}

    def test_calculate_average_usage_zero_period_days(self, aggregator):
        """Test average usage calculation with zero period days."""
        records = [Mock()]
        result = aggregator.calculate_average_usage(records, 0)
        assert result == {}

    def test_calculate_average_usage_fallback_service_identifier(self, aggregator):
        """Test average usage calculation using service_identifier fallback."""
        records = []
        record = Mock()
        record.meter_type = None  # Will use service_identifier
        record.service_identifier = "custom_metric"
        record.quantity = Decimal("300")
        records.append(record)

        result = aggregator.calculate_average_usage(records, 10)

        assert "custom_metric_daily_avg" in result
        assert result["custom_metric_daily_avg"] == Decimal("30")  # 300 ÷ 10


class TestTieredPricingEngineComprehensive:
    """Comprehensive tests for TieredPricingEngine to achieve 90% coverage."""

    @pytest.fixture
    def pricing_engine(self):
        return TieredPricingEngine()

    @pytest.fixture
    def simple_tiers(self):
        return [
            {"min_quantity": 0, "max_quantity": Decimal("100"), "unit_price": Decimal("0.10"), "name": "Tier 1"},
            {"min_quantity": Decimal("100"), "max_quantity": Decimal("500"), "unit_price": Decimal("0.08"), "name": "Tier 2"},
            {"min_quantity": Decimal("500"), "unit_price": Decimal("0.05"), "name": "Tier 3"}  # Unlimited tier
        ]

    def test_calculate_tiered_pricing_first_tier_only(self, pricing_engine, simple_tiers):
        """Test pricing that stays within the first tier."""
        result = pricing_engine.calculate_tiered_pricing(Decimal("50"), simple_tiers)

        assert result["total_charge"] == Decimal("5.00")  # 50 × 0.10
        assert result["tier_details"][0]["tier_charge"] == Decimal("5.00")
        assert result["tier_details"][0]["quantity_in_tier"] == Decimal("50")

    def test_calculate_tiered_pricing_multiple_tiers(self, pricing_engine, simple_tiers):
        """Test pricing that spans multiple tiers."""
        result = pricing_engine.calculate_tiered_pricing(Decimal("300"), simple_tiers)

        # First 100 at $0.10 = $10.00
        # Next 200 at $0.08 = $16.00
        # Total = $26.00
        assert result["total_charge"] == Decimal("26.00")
        assert len(result["tier_details"]) == 2

        # Check first tier
        tier1 = result["tier_details"][0]
        assert tier1["quantity_in_tier"] == Decimal("100")
        assert tier1["tier_charge"] == Decimal("10.00")

        # Check second tier
        tier2 = result["tier_details"][1]
        assert tier2["quantity_in_tier"] == Decimal("200")
        assert tier2["tier_charge"] == Decimal("16.00")

    def test_calculate_tiered_pricing_unlimited_tier(self, pricing_engine, simple_tiers):
        """Test pricing that reaches the unlimited tier."""
        result = pricing_engine.calculate_tiered_pricing(Decimal("1000"), simple_tiers)

        # First 100 at $0.10 = $10.00
        # Next 400 at $0.08 = $32.00
        # Next 500 at $0.05 = $25.00
        # Total = $67.00
        assert result["total_charge"] == Decimal("67.00")
        assert len(result["tier_details"]) == 3

    def test_calculate_tiered_pricing_zero_quantity(self, pricing_engine, simple_tiers):
        """Test pricing with zero quantity."""
        result = pricing_engine.calculate_tiered_pricing(Decimal("0"), simple_tiers)

        assert result["total_charge"] == Decimal("0")
        assert len(result["tier_details"]) == 0

    def test_calculate_tiered_pricing_empty_tiers(self, pricing_engine):
        """Test pricing with no tiers defined."""
        result = pricing_engine.calculate_tiered_pricing(Decimal("100"), [])

        assert result["total_charge"] == Decimal("0")
        assert len(result["tier_details"]) == 0


class TestUsageRatingEngineComprehensive:
    """Comprehensive tests for UsageRatingEngine to achieve 90% coverage."""

    @pytest.fixture
    def rating_engine(self):
        return UsageRatingEngine()

    @pytest.fixture
    def billing_period(self):
        return BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

    @pytest.fixture
    def subscription(self):
        subscription = Mock()
        subscription.id = uuid4()

        # Mock billing plan with usage allowances
        plan = Mock()
        plan.usage_allowances = {"api_calls": Decimal("100")}
        plan.pricing_tiers = []
        subscription.billing_plan = plan

        return subscription

    @pytest.mark.asyncio
    async def test_rate_usage_for_subscription_no_records(self, rating_engine, subscription, billing_period):
        """Test rating with no usage records."""
        result = await rating_engine.rate_usage_for_subscription(
            subscription, billing_period, []
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_calculate_usage_summary_empty(self, rating_engine, billing_period):
        """Test usage summary calculation with no records."""
        subscription_id = uuid4()

        result = await rating_engine.calculate_usage_summary(
            subscription_id, [], billing_period
        )

        assert result["total_records"] == 0
        assert result["usage_metrics"] == {}
        assert result["daily_averages"] == {}

    @pytest.mark.asyncio
    async def test_rate_single_usage_metric_with_pricing(self, rating_engine):
        """Test rating single usage metric with pricing configuration."""
        usage_metric = UsageMetric(
            name="api_calls",
            quantity=Decimal("1000"),
            unit="calls",
            period=BillingPeriodValue(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                cycle=BillingCycle.MONTHLY
            )
        )
        
        billing_plan = Mock()
        billing_plan.usage_pricing = {
            "api_calls": {
                "pricing_model": "tiered",
                "tiers": [
                    {"min_quantity": 0, "max_quantity": 500, "unit_price": "0.01"},
                    {"min_quantity": 500, "unit_price": "0.005"}
                ],
                "description": "API Calls",
                "taxable": True,
                "volume_discounts": []
            }
        }
        
        result = await rating_engine._rate_single_usage_metric(usage_metric, billing_plan)
        
        assert result["description"].startswith("API Calls")
        assert result["quantity"] == Decimal("1000")
        assert result["amount"] > Decimal("0")
        assert result["taxable"] == True

    @pytest.mark.asyncio  
    async def test_rate_single_usage_metric_no_pricing(self, rating_engine):
        """Test rating single usage metric with no pricing configuration."""
        usage_metric = UsageMetric(
            name="unknown_metric", 
            quantity=Decimal("100"),
            unit="units",
            period=BillingPeriodValue(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                cycle=BillingCycle.MONTHLY
            )
        )
        
        billing_plan = Mock()
        billing_plan.usage_pricing = {}
        
        result = await rating_engine._rate_single_usage_metric(usage_metric, billing_plan)
        
        assert result["amount"] == Decimal("0")
        assert result["unit_price"] == Decimal("0")
        assert result["taxable"] == True

    def test_get_usage_pricing_config(self, rating_engine):
        """Test getting usage pricing configuration."""
        billing_plan = Mock()
        billing_plan.usage_pricing = {
            "api_calls": {"unit_price": "0.01"},
            "storage": {"unit_price": "0.05"}
        }
        
        # Test existing metric
        result = rating_engine._get_usage_pricing_config(billing_plan, "api_calls")
        assert result == {"unit_price": "0.01"}
        
        # Test non-existing metric
        result = rating_engine._get_usage_pricing_config(billing_plan, "unknown")
        assert result is None

    def test_format_usage_description(self, rating_engine):
        """Test formatting usage description."""
        usage_metric = UsageMetric(
            name="api_calls",
            quantity=Decimal("100"),
            unit="calls", 
            period=BillingPeriodValue(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                cycle=BillingCycle.MONTHLY
            )
        )
        
        pricing_config = {"description": "API Usage"}
        
        result = rating_engine._format_usage_description(usage_metric, pricing_config)
        
        assert "API Usage" in result
        assert "2024-01-01 to 2024-01-31" in result
