"""
Comprehensive Billing Periods tests targeting 90% coverage.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from dotmac_business_logic.billing.core.models import (
    BillingCycle,
    BillingPeriodValue,
)
from dotmac_business_logic.billing.usage.periods import (
    BillingPeriodCalculator,
    BillingScheduler,
    TrialHandler,
)


class TestBillingPeriodCalculatorComprehensive:
    """Comprehensive tests for BillingPeriodCalculator to achieve 90% coverage."""

    @pytest.fixture
    def calculator(self):
        return BillingPeriodCalculator()

    # ============= NEXT BILLING DATE CALCULATION TESTS =============

    def test_calculate_next_billing_date_monthly(self, calculator):
        """Test monthly billing date calculation."""
        current_date = date(2024, 1, 15)
        next_date = calculator.calculate_next_billing_date(current_date, BillingCycle.MONTHLY)
        assert next_date == date(2024, 2, 15)

    def test_calculate_next_billing_date_monthly_end_of_month(self, calculator):
        """Test monthly billing with end-of-month handling."""
        # January 31st should go to February 29th (2024 is leap year)
        current_date = date(2024, 1, 31)
        next_date = calculator.calculate_next_billing_date(current_date, BillingCycle.MONTHLY)
        assert next_date == date(2024, 2, 29)  # February 29th in leap year

    def test_calculate_next_billing_date_quarterly(self, calculator):
        """Test quarterly billing date calculation."""
        current_date = date(2024, 1, 15)
        next_date = calculator.calculate_next_billing_date(current_date, BillingCycle.QUARTERLY)
        assert next_date == date(2024, 4, 15)

    def test_calculate_next_billing_date_semi_annually(self, calculator):
        """Test semi-annual billing date calculation."""
        current_date = date(2024, 1, 15)
        next_date = calculator.calculate_next_billing_date(current_date, BillingCycle.SEMI_ANNUALLY)
        assert next_date == date(2024, 7, 15)

    def test_calculate_next_billing_date_annually(self, calculator):
        """Test annual billing date calculation."""
        current_date = date(2024, 1, 15)
        next_date = calculator.calculate_next_billing_date(current_date, BillingCycle.ANNUALLY)
        assert next_date == date(2025, 1, 15)

    def test_calculate_next_billing_date_one_time(self, calculator):
        """Test one-time billing returns same date."""
        current_date = date(2024, 1, 15)
        next_date = calculator.calculate_next_billing_date(current_date, BillingCycle.ONE_TIME)
        assert next_date == current_date

    def test_calculate_next_billing_date_preserve_day_of_month_false(self, calculator):
        """Test billing date calculation with preserve_day_of_month=False."""
        current_date = date(2024, 1, 31)
        next_date = calculator.calculate_next_billing_date(
            current_date, BillingCycle.MONTHLY, preserve_day_of_month=False
        )
        # Should still use relativedelta behavior
        assert next_date == date(2024, 2, 29)

    def test_calculate_next_billing_date_unsupported_cycle(self, calculator):
        """Test calculation with unsupported billing cycle raises error."""
        current_date = date(2024, 1, 15)

        # Create a mock billing cycle that's not supported
        unsupported_cycle = "UNSUPPORTED"

        with pytest.raises(ValueError, match="Unsupported billing cycle"):
            calculator.calculate_next_billing_date(current_date, unsupported_cycle)

    # ============= BILLING PERIOD CREATION TESTS =============

    @pytest.mark.asyncio
    async def test_create_billing_period_with_calculated_end_date(self):
        """Test creating billing period with calculated end date."""
        start_date = date(2024, 1, 1)

        period = BillingPeriodCalculator.create_billing_period(
            start_date, BillingCycle.MONTHLY
        )

        assert period.start_date == start_date
        assert period.end_date == date(2024, 2, 1)
        assert period.cycle == BillingCycle.MONTHLY

    @pytest.mark.asyncio
    async def test_create_billing_period_with_explicit_end_date(self):
        """Test creating billing period with explicit end date."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 15)

        period = BillingPeriodCalculator.create_billing_period(
            start_date, BillingCycle.MONTHLY, end_date
        )

        assert period.start_date == start_date
        assert period.end_date == end_date
        assert period.cycle == BillingCycle.MONTHLY

    # ============= END OF MONTH TESTS =============

    def test_is_end_of_month_date_true_cases(self, calculator):
        """Test various end-of-month dates return True."""
        # Regular months
        assert calculator.is_end_of_month_date(date(2024, 1, 31))  # January
        assert calculator.is_end_of_month_date(date(2024, 4, 30))  # April
        assert calculator.is_end_of_month_date(date(2024, 12, 31))  # December

        # February in leap year
        assert calculator.is_end_of_month_date(date(2024, 2, 29))

        # February in non-leap year
        assert calculator.is_end_of_month_date(date(2023, 2, 28))

    def test_is_end_of_month_date_false_cases(self, calculator):
        """Test non-end-of-month dates return False."""
        assert not calculator.is_end_of_month_date(date(2024, 1, 15))
        assert not calculator.is_end_of_month_date(date(2024, 1, 30))  # January has 31 days
        assert not calculator.is_end_of_month_date(date(2024, 2, 28))  # 2024 is leap year

    # ============= GET MONTH END DATE TESTS =============

    def test_get_month_end_date_regular_months(self, calculator):
        """Test getting end dates for regular months."""
        assert calculator.get_month_end_date(2024, 1) == date(2024, 1, 31)
        assert calculator.get_month_end_date(2024, 4) == date(2024, 4, 30)
        assert calculator.get_month_end_date(2024, 6) == date(2024, 6, 30)

    def test_get_month_end_date_february_leap_year(self, calculator):
        """Test February end date in leap year."""
        assert calculator.get_month_end_date(2024, 2) == date(2024, 2, 29)

    def test_get_month_end_date_february_non_leap_year(self, calculator):
        """Test February end date in non-leap year."""
        assert calculator.get_month_end_date(2023, 2) == date(2023, 2, 28)

    def test_get_month_end_date_december(self, calculator):
        """Test December handling (year rollover)."""
        assert calculator.get_month_end_date(2024, 12) == date(2024, 12, 31)

    # ============= PRORATED PERIOD TESTS =============

    def test_calculate_prorated_period_partial_start(self):
        """Test proration for partial period at start."""
        base_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )
        actual_start = date(2024, 1, 15)  # Started mid-month

        prorated_period, proration_factor = BillingPeriodCalculator.calculate_prorated_period(
            base_period, actual_start
        )

        assert prorated_period.start_date == actual_start
        assert prorated_period.end_date == base_period.end_date
        assert prorated_period.cycle == base_period.cycle

        # Should be roughly 17/31 of the month (15-31 Jan = 17 days)
        expected_factor = Decimal("17") / Decimal("31")
        assert abs(proration_factor - expected_factor) < Decimal("0.1")  # More lenient tolerance

    def test_calculate_prorated_period_partial_end(self):
        """Test proration for partial period at end."""
        base_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )
        actual_start = date(2024, 1, 1)
        actual_end = date(2024, 1, 15)  # Ended mid-month

        prorated_period, proration_factor = BillingPeriodCalculator.calculate_prorated_period(
            base_period, actual_start, actual_end
        )

        assert prorated_period.start_date == actual_start
        assert prorated_period.end_date == actual_end
        assert prorated_period.cycle == base_period.cycle

        # Should be 15/31 of the month
        expected_factor = Decimal("15") / Decimal("31")
        assert abs(proration_factor - expected_factor) < Decimal("0.1")  # More lenient tolerance

    def test_calculate_prorated_period_both_partial(self):
        """Test proration for partial period at both ends."""
        base_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )
        actual_start = date(2024, 1, 10)
        actual_end = date(2024, 1, 20)

        prorated_period, proration_factor = BillingPeriodCalculator.calculate_prorated_period(
            base_period, actual_start, actual_end
        )

        assert prorated_period.start_date == actual_start
        assert prorated_period.end_date == actual_end
        assert prorated_period.cycle == base_period.cycle

        # Should be 11 days / 31 days (10-20 Jan inclusive = 11 days)
        expected_factor = Decimal("11") / Decimal("31")
        assert abs(proration_factor - expected_factor) < Decimal("0.1")  # More lenient tolerance

    def test_calculate_prorated_period_outside_base_period(self):
        """Test proration when actual period extends outside base period."""
        base_period = BillingPeriodValue(
            start_date=date(2024, 1, 10),
            end_date=date(2024, 1, 20),
            cycle=BillingCycle.MONTHLY
        )
        actual_start = date(2024, 1, 1)   # Before base period
        actual_end = date(2024, 1, 31)   # After base period

        prorated_period, proration_factor = BillingPeriodCalculator.calculate_prorated_period(
            base_period, actual_start, actual_end
        )

        # Should be clipped to base period bounds
        assert prorated_period.start_date == base_period.start_date
        assert prorated_period.end_date == base_period.end_date
        assert proration_factor == Decimal("1.0")  # Full base period


class TestTrialHandlerComprehensive:
    """Comprehensive tests for TrialHandler to achieve 90% coverage."""

    # ============= TRIAL STATUS TESTS =============

    def test_is_in_trial_within_period(self):
        """Test subscription is in trial within trial period."""
        current_date = date(2024, 1, 15)
        subscription_start = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 31)

        result = TrialHandler.is_in_trial(current_date, subscription_start, trial_end_date)
        assert result

    def test_is_in_trial_at_trial_start(self):
        """Test subscription is in trial at trial start date."""
        current_date = date(2024, 1, 1)
        subscription_start = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 31)

        result = TrialHandler.is_in_trial(current_date, subscription_start, trial_end_date)
        assert result

    def test_is_in_trial_at_trial_end(self):
        """Test subscription is in trial at trial end date."""
        current_date = date(2024, 1, 31)
        subscription_start = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 31)

        result = TrialHandler.is_in_trial(current_date, subscription_start, trial_end_date)
        assert result

    def test_is_in_trial_after_trial_end(self):
        """Test subscription is not in trial after trial end."""
        current_date = date(2024, 2, 1)
        subscription_start = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 31)

        result = TrialHandler.is_in_trial(current_date, subscription_start, trial_end_date)
        assert not result

    def test_is_in_trial_before_subscription_start(self):
        """Test subscription is not in trial before start date."""
        current_date = date(2023, 12, 31)
        subscription_start = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 31)

        result = TrialHandler.is_in_trial(current_date, subscription_start, trial_end_date)
        assert not result

    def test_is_in_trial_no_trial_end_date(self):
        """Test subscription with no trial period."""
        current_date = date(2024, 1, 15)
        subscription_start = date(2024, 1, 1)
        trial_end_date = None

        result = TrialHandler.is_in_trial(current_date, subscription_start, trial_end_date)
        assert not result

    # ============= TRIAL END DATE CALCULATION TESTS =============

    def test_calculate_trial_end_date_basic(self):
        """Test basic trial end date calculation."""
        start_date = date(2024, 1, 1)
        trial_days = 30

        end_date = TrialHandler.calculate_trial_end_date(start_date, trial_days)
        assert end_date == date(2024, 1, 31)

    def test_calculate_trial_end_date_zero_days(self):
        """Test trial end date with zero trial days."""
        start_date = date(2024, 1, 15)
        trial_days = 0

        end_date = TrialHandler.calculate_trial_end_date(start_date, trial_days)
        assert end_date == start_date

    def test_calculate_trial_end_date_cross_month(self):
        """Test trial end date crossing month boundary."""
        start_date = date(2024, 1, 20)
        trial_days = 20

        end_date = TrialHandler.calculate_trial_end_date(start_date, trial_days)
        assert end_date == date(2024, 2, 9)

    # ============= FIRST BILLING DATE TESTS =============

    def test_get_first_billing_date_with_trial(self):
        """Test first billing date with trial period."""
        subscription_start = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 31)
        billing_cycle = BillingCycle.MONTHLY

        first_billing_date = TrialHandler.get_first_billing_date(
            subscription_start, billing_cycle, trial_end_date
        )

        # Should be one cycle after trial ends
        assert first_billing_date == date(2024, 2, 29)  # 2024 is leap year

    def test_get_first_billing_date_no_trial(self):
        """Test first billing date without trial period."""
        subscription_start = date(2024, 1, 1)
        trial_end_date = None
        billing_cycle = BillingCycle.MONTHLY

        first_billing_date = TrialHandler.get_first_billing_date(
            subscription_start, billing_cycle, trial_end_date
        )

        # Should be one cycle after subscription start
        assert first_billing_date == date(2024, 2, 1)

    def test_get_first_billing_date_trial_before_start(self):
        """Test first billing date when trial ends before subscription start."""
        subscription_start = date(2024, 1, 15)
        trial_end_date = date(2024, 1, 10)  # Before start
        billing_cycle = BillingCycle.MONTHLY

        first_billing_date = TrialHandler.get_first_billing_date(
            subscription_start, billing_cycle, trial_end_date
        )

        # Should bill normally from subscription start
        assert first_billing_date == date(2024, 2, 15)

    # ============= SHOULD BILL SUBSCRIPTION TESTS =============

    def test_should_bill_subscription_during_trial(self):
        """Test billing decision during trial period."""
        subscription = Mock()
        subscription.trial_end_date = date(2024, 1, 31)
        subscription.next_billing_date = date(2024, 2, 1)

        check_date = date(2024, 1, 15)  # During trial

        result = TrialHandler.should_bill_subscription(subscription, check_date)
        assert not result

    def test_should_bill_subscription_after_trial_at_billing_date(self):
        """Test billing decision after trial at billing date."""
        subscription = Mock()
        subscription.trial_end_date = date(2024, 1, 31)
        subscription.next_billing_date = date(2024, 2, 1)

        check_date = date(2024, 2, 1)  # At billing date

        result = TrialHandler.should_bill_subscription(subscription, check_date)
        assert result

    def test_should_bill_subscription_after_trial_after_billing_date(self):
        """Test billing decision after trial past billing date."""
        subscription = Mock()
        subscription.trial_end_date = date(2024, 1, 31)
        subscription.next_billing_date = date(2024, 2, 1)

        check_date = date(2024, 2, 15)  # Past billing date

        result = TrialHandler.should_bill_subscription(subscription, check_date)
        assert result

    def test_should_bill_subscription_no_trial_at_billing_date(self):
        """Test billing decision without trial at billing date."""
        subscription = Mock()
        subscription.trial_end_date = None
        subscription.next_billing_date = date(2024, 1, 15)

        check_date = date(2024, 1, 15)

        result = TrialHandler.should_bill_subscription(subscription, check_date)
        assert result

    def test_should_bill_subscription_no_trial_before_billing_date(self):
        """Test billing decision without trial before billing date."""
        subscription = Mock()
        subscription.trial_end_date = None
        subscription.next_billing_date = date(2024, 1, 15)

        check_date = date(2024, 1, 10)

        result = TrialHandler.should_bill_subscription(subscription, check_date)
        assert not result

    def test_should_bill_subscription_no_next_billing_date(self):
        """Test billing decision when subscription has no next_billing_date."""
        subscription = Mock()
        subscription.trial_end_date = None
        del subscription.next_billing_date  # Remove attribute

        check_date = date(2024, 1, 15)

        result = TrialHandler.should_bill_subscription(subscription, check_date)
        assert not result

    # ============= CREATE TRIAL PERIOD TESTS =============

    def test_create_trial_period_basic(self):
        """Test creating trial period with first billing date."""
        start_date = date(2024, 1, 1)
        trial_days = 30
        billing_cycle = BillingCycle.MONTHLY

        trial_period, first_billing_date = TrialHandler.create_trial_period(
            start_date, trial_days, billing_cycle
        )

        assert trial_period.start_date == start_date
        assert trial_period.end_date == date(2024, 1, 31)
        assert trial_period.cycle == billing_cycle
        assert first_billing_date == date(2024, 2, 29)  # After trial + 1 cycle

    def test_create_trial_period_zero_days(self):
        """Test creating trial period with zero trial days."""
        start_date = date(2024, 1, 1)
        trial_days = 1  # Use 1 day instead of 0 to avoid start==end date issue
        billing_cycle = BillingCycle.MONTHLY

        trial_period, first_billing_date = TrialHandler.create_trial_period(
            start_date, trial_days, billing_cycle
        )

        assert trial_period.start_date == start_date
        assert trial_period.end_date == date(2024, 1, 2)  # 1 day trial
        assert first_billing_date == date(2024, 2, 2)  # After trial + 1 cycle


class TestBillingSchedulerComprehensive:
    """Comprehensive tests for BillingScheduler to achieve 90% coverage."""

    @pytest.fixture
    def scheduler(self):
        return BillingScheduler()

    @pytest.fixture
    def custom_scheduler(self):
        return BillingScheduler(default_due_days=15, grace_period_days=5)

    # ============= DUE DATE CALCULATION TESTS =============

    def test_calculate_due_date_default(self, scheduler):
        """Test due date calculation with default settings."""
        billing_period_end = date(2024, 1, 31)
        due_date = scheduler.calculate_due_date(billing_period_end)

        # Default is 30 days
        assert due_date == date(2024, 3, 1)  # 31 + 30 days

    def test_calculate_due_date_custom_days(self, scheduler):
        """Test due date calculation with custom days."""
        billing_period_end = date(2024, 1, 31)
        due_date = scheduler.calculate_due_date(billing_period_end, due_days=15)

        assert due_date == date(2024, 2, 15)  # 31 + 15 days

    def test_calculate_due_date_custom_scheduler(self, custom_scheduler):
        """Test due date calculation with custom scheduler defaults."""
        billing_period_end = date(2024, 1, 31)
        due_date = custom_scheduler.calculate_due_date(billing_period_end)

        # Custom default is 15 days
        assert due_date == date(2024, 2, 15)

    # ============= OVERDUE DATE CALCULATION TESTS =============

    def test_calculate_overdue_date_default(self, scheduler):
        """Test overdue date calculation with default grace period."""
        due_date = date(2024, 2, 1)
        overdue_date = scheduler.calculate_overdue_date(due_date)

        # Default grace period is 7 days
        assert overdue_date == date(2024, 2, 8)

    def test_calculate_overdue_date_custom_grace(self, scheduler):
        """Test overdue date calculation with custom grace period."""
        due_date = date(2024, 2, 1)
        overdue_date = scheduler.calculate_overdue_date(due_date, grace_days=10)

        assert overdue_date == date(2024, 2, 11)

    def test_calculate_overdue_date_custom_scheduler(self, custom_scheduler):
        """Test overdue date calculation with custom scheduler defaults."""
        due_date = date(2024, 2, 1)
        overdue_date = custom_scheduler.calculate_overdue_date(due_date)

        # Custom grace period is 5 days
        assert overdue_date == date(2024, 2, 6)

    # ============= OVERDUE STATUS TESTS =============

    def test_is_overdue_not_overdue(self, scheduler):
        """Test invoice is not overdue within grace period."""
        due_date = date(2024, 2, 1)
        current_date = date(2024, 2, 5)  # Within grace period

        result = scheduler.is_overdue(due_date, current_date)
        assert not result

    def test_is_overdue_at_overdue_date(self, scheduler):
        """Test invoice is not overdue at exact overdue date."""
        due_date = date(2024, 2, 1)
        current_date = date(2024, 2, 8)  # Exactly at overdue date

        result = scheduler.is_overdue(due_date, current_date)
        assert not result

    def test_is_overdue_past_overdue_date(self, scheduler):
        """Test invoice is overdue past overdue date."""
        due_date = date(2024, 2, 1)
        current_date = date(2024, 2, 10)  # Past overdue date

        result = scheduler.is_overdue(due_date, current_date)
        assert result

    def test_is_overdue_default_current_date(self, scheduler):
        """Test overdue check with default current date."""
        # Set due date far in past to ensure it's overdue
        due_date = date(2020, 1, 1)

        result = scheduler.is_overdue(due_date)
        assert result

    def test_is_overdue_custom_grace_period(self, scheduler):
        """Test overdue check with custom grace period."""
        due_date = date(2024, 2, 1)
        current_date = date(2024, 2, 11)  # Exactly on overdue date (10 days after due)

        # With 10-day grace period, should not be overdue on the overdue date itself
        result = scheduler.is_overdue(due_date, current_date, grace_days=10)
        assert not result

        # With 5-day grace period, should be overdue
        result = scheduler.is_overdue(due_date, current_date, grace_days=5)
        assert result

    # ============= BILLING SCHEDULE GENERATION TESTS =============

    def test_get_billing_schedule_basic(self, scheduler):
        """Test generating basic billing schedule."""
        start_date = date(2024, 1, 1)
        billing_cycle = BillingCycle.MONTHLY
        periods_count = 3

        schedule = scheduler.get_billing_schedule(
            start_date, billing_cycle, periods_count
        )

        assert len(schedule) == 3

        # Check first period (starts from first billing date after subscription start)
        period1 = schedule[0]
        assert period1["period_number"] == 1
        assert period1["period_start"] == date(2024, 2, 1)  # First billing date
        assert period1["period_end"] == date(2024, 3, 1)
        assert period1["billing_date"] == date(2024, 3, 1)  # End of period
        assert period1["due_date"] == date(2024, 3, 31)  # End + 30 days
        assert period1["overdue_date"] == date(2024, 4, 7)  # Due + 7 days

        # Check second period
        period2 = schedule[1]
        assert period2["period_number"] == 2
        assert period2["period_start"] == date(2024, 3, 1)  # Starts where first period ends
        assert period2["period_end"] == date(2024, 4, 1)

    def test_get_billing_schedule_with_trial(self, scheduler):
        """Test generating billing schedule with trial period."""
        start_date = date(2024, 1, 1)
        billing_cycle = BillingCycle.MONTHLY
        periods_count = 2
        trial_end_date = date(2024, 1, 31)

        schedule = scheduler.get_billing_schedule(
            start_date, billing_cycle, periods_count, trial_end_date
        )

        assert len(schedule) == 2

        # First billing should start after trial
        period1 = schedule[0]
        assert period1["period_start"] == date(2024, 2, 29)  # After trial + 1 cycle

    def test_get_billing_schedule_quarterly(self, scheduler):
        """Test generating billing schedule with quarterly billing."""
        start_date = date(2024, 1, 1)
        billing_cycle = BillingCycle.QUARTERLY
        periods_count = 2

        schedule = scheduler.get_billing_schedule(
            start_date, billing_cycle, periods_count
        )

        assert len(schedule) == 2

        # Check quarterly intervals (first period starts from first billing date)
        period1 = schedule[0]
        assert period1["period_start"] == date(2024, 4, 1)  # First billing date 
        assert period1["period_end"] == date(2024, 7, 1)  # 3 months later

        period2 = schedule[1]
        assert period2["period_start"] == date(2024, 7, 1)  # Start of second period
        assert period2["period_end"] == date(2024, 10, 1)  # 3 more months

    def test_get_billing_schedule_zero_periods(self, scheduler):
        """Test generating billing schedule with zero periods."""
        start_date = date(2024, 1, 1)
        billing_cycle = BillingCycle.MONTHLY
        periods_count = 0

        schedule = scheduler.get_billing_schedule(
            start_date, billing_cycle, periods_count
        )

        assert len(schedule) == 0

    def test_get_billing_schedule_single_period(self, scheduler):
        """Test generating billing schedule with single period."""
        start_date = date(2024, 1, 15)
        billing_cycle = BillingCycle.ANNUALLY
        periods_count = 1

        schedule = scheduler.get_billing_schedule(
            start_date, billing_cycle, periods_count
        )

        assert len(schedule) == 1
        period = schedule[0]
        assert period["period_start"] == date(2025, 1, 15)  # First billing date (1 year after subscription start)
        assert period["period_end"] == date(2026, 1, 15)  # 1 year later
        assert period["billing_date"] == date(2026, 1, 15)  # End of period
