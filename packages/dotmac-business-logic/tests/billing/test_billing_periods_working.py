"""
Tests for billing period calculations - working version matching actual API.
"""

from datetime import date
from unittest.mock import Mock

import pytest

from dotmac_business_logic.billing.core.models import BillingCycle, BillingPeriodValue
from dotmac_business_logic.billing.usage.periods import (
    BillingPeriodCalculator,
    BillingScheduler,
    TrialHandler,
)


class TestBillingPeriodCalculator:
    """Test BillingPeriodCalculator functionality."""

    def test_calculate_next_billing_date_monthly(self):
        """Test next billing date calculation for monthly billing."""
        # Execute
        next_date = BillingPeriodCalculator.calculate_next_billing_date(
            current_date=date(2024, 1, 15),
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert
        assert next_date == date(2024, 2, 15)

    def test_calculate_next_billing_date_end_of_month(self):
        """Test next billing date for end-of-month scenarios."""
        # Execute - January 31st should handle February correctly
        next_date = BillingPeriodCalculator.calculate_next_billing_date(
            current_date=date(2024, 1, 31),
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert - should be Feb 29 (2024 is leap year)
        assert next_date == date(2024, 2, 29)

    def test_calculate_next_billing_date_quarterly(self):
        """Test quarterly billing date calculation."""
        next_date = BillingPeriodCalculator.calculate_next_billing_date(
            current_date=date(2024, 1, 15),
            billing_cycle=BillingCycle.QUARTERLY
        )

        assert next_date == date(2024, 4, 15)

    def test_calculate_next_billing_date_annually(self):
        """Test annual billing date calculation."""
        next_date = BillingPeriodCalculator.calculate_next_billing_date(
            current_date=date(2024, 1, 15),
            billing_cycle=BillingCycle.ANNUALLY
        )

        assert next_date == date(2025, 1, 15)

    def test_calculate_next_billing_date_one_time(self):
        """Test one-time billing returns same date."""
        current = date(2024, 1, 15)
        next_date = BillingPeriodCalculator.calculate_next_billing_date(
            current_date=current,
            billing_cycle=BillingCycle.ONE_TIME
        )

        assert next_date == current

    def test_create_billing_period_with_end_date(self):
        """Test creating billing period with explicit end date."""
        # Execute
        period = BillingPeriodCalculator.create_billing_period(
            start_date=date(2024, 1, 1),
            billing_cycle=BillingCycle.MONTHLY,
            end_date=date(2024, 1, 31)
        )

        # Assert
        assert isinstance(period, BillingPeriodValue)
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 1, 31)
        assert period.cycle == BillingCycle.MONTHLY

    def test_create_billing_period_calculated_end(self):
        """Test creating billing period with calculated end date."""
        # Execute
        period = BillingPeriodCalculator.create_billing_period(
            start_date=date(2024, 1, 15),
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert
        assert isinstance(period, BillingPeriodValue)
        assert period.start_date == date(2024, 1, 15)
        assert period.end_date == date(2024, 2, 15)
        assert period.cycle == BillingCycle.MONTHLY

    def test_is_end_of_month_date(self):
        """Test end-of-month date detection."""
        # Execute & Assert
        assert BillingPeriodCalculator.is_end_of_month_date(date(2024, 1, 31)) is True   # January 31
        assert BillingPeriodCalculator.is_end_of_month_date(date(2024, 2, 29)) is True   # February 29 (leap)
        assert BillingPeriodCalculator.is_end_of_month_date(date(2024, 4, 30)) is True   # April 30
        assert BillingPeriodCalculator.is_end_of_month_date(date(2024, 1, 15)) is False  # Mid-month

    def test_get_month_end_date(self):
        """Test getting end date of month."""
        # Execute & Assert
        assert BillingPeriodCalculator.get_month_end_date(2024, 1) == date(2024, 1, 31)
        assert BillingPeriodCalculator.get_month_end_date(2024, 2) == date(2024, 2, 29)  # Leap year
        assert BillingPeriodCalculator.get_month_end_date(2023, 2) == date(2023, 2, 28)  # Non-leap year
        assert BillingPeriodCalculator.get_month_end_date(2024, 4) == date(2024, 4, 30)

    def test_calculate_prorated_period(self):
        """Test prorated period calculation."""
        # Setup base period
        base_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        # Execute - partial month starting mid-month
        prorated_period, proration_factor = BillingPeriodCalculator.calculate_prorated_period(
            base_period=base_period,
            actual_start=date(2024, 1, 15)
        )

        # Assert
        assert isinstance(prorated_period, BillingPeriodValue)
        assert prorated_period.start_date == date(2024, 1, 15)
        assert prorated_period.end_date == date(2024, 1, 31)
        assert prorated_period.cycle == BillingCycle.MONTHLY

        # Proration factor should be ~16/31 (days from 15th to 31st is 17 days, but period calculation is 16)
        expected_factor = 17 / 31  # 17 days out of 31
        assert abs(float(proration_factor) - expected_factor) < 0.01


class TestTrialHandler:
    """Test TrialHandler functionality."""

    def test_is_in_trial_active(self):
        """Test checking if subscription is in active trial."""
        # Execute & Assert
        assert TrialHandler.is_in_trial(
            current_date=date(2024, 1, 15),
            subscription_start=date(2024, 1, 1),
            trial_end_date=date(2024, 2, 1)
        ) is True

    def test_is_in_trial_expired(self):
        """Test checking trial after it has ended."""
        assert TrialHandler.is_in_trial(
            current_date=date(2024, 2, 15),
            subscription_start=date(2024, 1, 1),
            trial_end_date=date(2024, 2, 1)
        ) is False

    def test_is_in_trial_no_trial(self):
        """Test checking trial when none exists."""
        assert TrialHandler.is_in_trial(
            current_date=date(2024, 1, 15),
            subscription_start=date(2024, 1, 1),
            trial_end_date=None
        ) is False

    def test_calculate_trial_end_date(self):
        """Test calculating trial end date."""
        # Execute
        trial_end = TrialHandler.calculate_trial_end_date(
            start_date=date(2024, 1, 1),
            trial_days=14
        )

        # Assert
        assert trial_end == date(2024, 1, 15)

    def test_get_first_billing_date_with_trial(self):
        """Test getting first billing date after trial."""
        # Execute
        first_billing = TrialHandler.get_first_billing_date(
            subscription_start=date(2024, 1, 1),
            billing_cycle=BillingCycle.MONTHLY,
            trial_end_date=date(2024, 1, 15)
        )

        # Assert - should be one month after trial ends
        assert first_billing == date(2024, 2, 15)

    def test_get_first_billing_date_no_trial(self):
        """Test getting first billing date without trial."""
        first_billing = TrialHandler.get_first_billing_date(
            subscription_start=date(2024, 1, 1),
            billing_cycle=BillingCycle.MONTHLY,
            trial_end_date=None
        )

        # Assert - should be one month after start
        assert first_billing == date(2024, 2, 1)

    def test_should_bill_subscription_during_trial(self):
        """Test billing decision during trial period."""
        # Setup mock subscription
        subscription = Mock()
        subscription.trial_end_date = date(2024, 2, 1)
        subscription.next_billing_date = date(2024, 2, 1)

        # Execute & Assert - should not bill during trial
        assert TrialHandler.should_bill_subscription(
            subscription, date(2024, 1, 15)
        ) is False

    def test_should_bill_subscription_after_trial(self):
        """Test billing decision after trial ends."""
        # Setup mock subscription
        subscription = Mock()
        subscription.trial_end_date = date(2024, 1, 15)
        subscription.next_billing_date = date(2024, 1, 20)

        # Execute & Assert - should bill after trial and billing date
        assert TrialHandler.should_bill_subscription(
            subscription, date(2024, 1, 25)
        ) is True

    def test_should_bill_subscription_no_trial(self):
        """Test billing decision without trial."""
        subscription = Mock()
        subscription.trial_end_date = None
        subscription.next_billing_date = date(2024, 1, 15)

        assert TrialHandler.should_bill_subscription(
            subscription, date(2024, 1, 20)
        ) is True

    def test_create_trial_period(self):
        """Test creating trial period and first billing date."""
        # Execute
        trial_period, first_billing_date = TrialHandler.create_trial_period(
            start_date=date(2024, 1, 1),
            trial_days=14,
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert
        assert isinstance(trial_period, BillingPeriodValue)
        assert trial_period.start_date == date(2024, 1, 1)
        assert trial_period.end_date == date(2024, 1, 15)
        assert trial_period.cycle == BillingCycle.MONTHLY
        assert first_billing_date == date(2024, 2, 15)


class TestBillingScheduler:
    """Test BillingScheduler functionality."""

    @pytest.fixture
    def scheduler(self):
        """Create BillingScheduler instance."""
        return BillingScheduler(
            default_due_days=30,
            grace_period_days=7
        )

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.default_due_days == 30
        assert scheduler.grace_period_days == 7

    def test_calculate_due_date_default(self, scheduler):
        """Test calculating due date with default days."""
        # Execute
        due_date = scheduler.calculate_due_date(
            billing_period_end=date(2024, 1, 31)
        )

        # Assert - should add 30 days by default
        assert due_date == date(2024, 3, 1)  # 31 + 30 = March 1

    def test_calculate_due_date_custom(self, scheduler):
        """Test calculating due date with custom days."""
        due_date = scheduler.calculate_due_date(
            billing_period_end=date(2024, 1, 31),
            due_days=15
        )

        assert due_date == date(2024, 2, 15)

    def test_calculate_overdue_date(self, scheduler):
        """Test calculating overdue date."""
        # Execute
        overdue_date = scheduler.calculate_overdue_date(
            due_date=date(2024, 1, 31)
        )

        # Assert - should add grace period
        assert overdue_date == date(2024, 2, 7)

    def test_is_overdue_not_yet(self, scheduler):
        """Test checking overdue status when not yet overdue."""
        assert scheduler.is_overdue(
            due_date=date(2024, 1, 31),
            current_date=date(2024, 2, 5)  # Within grace period
        ) is False

    def test_is_overdue_yes(self, scheduler):
        """Test checking overdue status when overdue."""
        assert scheduler.is_overdue(
            due_date=date(2024, 1, 31),
            current_date=date(2024, 2, 10)  # Past grace period
        ) is True

    def test_get_billing_schedule_no_trial(self, scheduler):
        """Test generating billing schedule without trial."""
        # Execute
        schedule = scheduler.get_billing_schedule(
            start_date=date(2024, 1, 1),
            billing_cycle=BillingCycle.MONTHLY,
            periods_count=3
        )

        # Assert
        assert len(schedule) == 3

        # Check first period
        first_period = schedule[0]
        assert first_period['period_number'] == 1
        assert first_period['period_start'] == date(2024, 2, 1)  # First billing after start
        assert first_period['period_end'] == date(2024, 3, 1)
        assert first_period['due_date'] == date(2024, 3, 31)  # 30 days after period end

        # Check that periods are sequential
        second_period = schedule[1]
        assert second_period['period_start'] == first_period['period_end']

    def test_get_billing_schedule_with_trial(self, scheduler):
        """Test generating billing schedule with trial period."""
        # Execute
        schedule = scheduler.get_billing_schedule(
            start_date=date(2024, 1, 1),
            billing_cycle=BillingCycle.MONTHLY,
            periods_count=2,
            trial_end_date=date(2024, 1, 15)
        )

        # Assert
        assert len(schedule) == 2

        # First billing should be after trial
        first_period = schedule[0]
        assert first_period['period_start'] == date(2024, 2, 15)  # After trial


class TestBillingPeriodValue:
    """Test BillingPeriodValue model functionality."""

    def test_billing_period_creation(self):
        """Test creating BillingPeriodValue."""
        # Execute
        period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        # Assert
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 1, 31)
        assert period.cycle == BillingCycle.MONTHLY

    def test_billing_period_validation_error(self):
        """Test that invalid periods raise error."""
        with pytest.raises(ValueError, match="Start date must be before end date"):
            BillingPeriodValue(
                start_date=date(2024, 1, 31),
                end_date=date(2024, 1, 1),  # End before start
                cycle=BillingCycle.MONTHLY
            )

    def test_billing_period_days_calculation(self):
        """Test calculating days in billing period."""
        # Setup different periods
        january_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        february_period = BillingPeriodValue(
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29),  # Leap year
            cycle=BillingCycle.MONTHLY
        )

        # Execute & Assert
        assert january_period.days_in_period() == 30  # 31 - 1
        assert february_period.days_in_period() == 28  # 29 - 1

    def test_billing_period_contains_date(self):
        """Test checking if period contains a date."""
        # Setup
        period = BillingPeriodValue(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 2, 14),
            cycle=BillingCycle.MONTHLY
        )

        # Execute & Assert
        assert period.contains_date(date(2024, 1, 15)) is True   # Start date
        assert period.contains_date(date(2024, 2, 14)) is True   # End date
        assert period.contains_date(date(2024, 1, 30)) is True   # Middle
        assert period.contains_date(date(2024, 1, 14)) is False  # Before
        assert period.contains_date(date(2024, 2, 15)) is False  # After

    def test_billing_period_proration_factor(self):
        """Test calculating proration factor for partial periods."""
        # Setup full month period
        period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        # Execute - half month usage
        factor = period.get_proration_factor(
            partial_start=date(2024, 1, 15),
            partial_end=date(2024, 1, 31)
        )

        # Assert - should be roughly half (17 days out of 30)
        expected = 17 / 30
        assert abs(float(factor) - expected) < 0.01

    def test_billing_period_proration_factor_no_end(self):
        """Test proration factor when no end date provided."""
        period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        # Execute - from mid-month to period end
        factor = period.get_proration_factor(
            partial_start=date(2024, 1, 15)
        )

        # Assert - should be 17/30 days
        expected = 17 / 30
        assert abs(float(factor) - expected) < 0.01
