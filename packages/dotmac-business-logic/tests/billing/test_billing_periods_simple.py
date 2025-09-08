"""
Tests for billing period calculations - simplified version.
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

    @pytest.fixture
    def calculator(self):
        """Create BillingPeriodCalculator instance."""
        return BillingPeriodCalculator()

    def test_calculate_next_billing_date_monthly(self, calculator):
        """Test next billing date calculation for monthly billing."""
        # Execute
        next_date = calculator.calculate_next_billing_date(
            current_date=date(2024, 1, 15),
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert
        assert next_date == date(2024, 2, 15)  # Same day next month

    def test_calculate_next_billing_date_end_of_month(self, calculator):
        """Test next billing date for end-of-month scenarios."""
        # Execute - January 31st should handle February correctly
        next_date = calculator.calculate_next_billing_date(
            current_date=date(2024, 1, 31),
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert - should be Feb 29 (2024 is leap year)
        assert next_date == date(2024, 2, 29)

    def test_create_billing_period(self, calculator):
        """Test creating billing period."""
        # Execute
        period = calculator.create_billing_period(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        # Assert
        assert isinstance(period, BillingPeriodValue)
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 1, 31)

    def test_is_end_of_month_date(self, calculator):
        """Test end-of-month date detection."""
        # Execute & Assert
        assert calculator.is_end_of_month_date(date(2024, 1, 31)) is True   # January 31
        assert calculator.is_end_of_month_date(date(2024, 2, 29)) is True   # February 29 (leap)
        assert calculator.is_end_of_month_date(date(2024, 4, 30)) is True   # April 30
        assert calculator.is_end_of_month_date(date(2024, 1, 15)) is False  # Mid-month

    def test_get_month_end_date(self, calculator):
        """Test getting end date of month."""
        # Execute & Assert
        assert calculator.get_month_end_date(2024, 1) == date(2024, 1, 31)
        assert calculator.get_month_end_date(2024, 2) == date(2024, 2, 29)  # Leap year
        assert calculator.get_month_end_date(2023, 2) == date(2023, 2, 28)  # Non-leap year
        assert calculator.get_month_end_date(2024, 4) == date(2024, 4, 30)

    def test_calculate_prorated_period(self, calculator):
        """Test prorated period calculation."""
        # Execute - partial month billing
        start_date = date(2024, 1, 15)
        full_period_days = 31

        period = calculator.calculate_prorated_period(
            start_date=start_date,
            full_period_days=full_period_days,
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert
        assert isinstance(period, BillingPeriodValue)
        assert period.start_date == start_date


class TestTrialHandler:
    """Test TrialHandler functionality."""

    @pytest.fixture
    def trial_handler(self):
        """Create TrialHandler instance."""
        return TrialHandler()

    def test_is_in_trial(self, trial_handler):
        """Test checking if subscription is in trial."""
        # Setup mock subscription
        trial_subscription = Mock()
        trial_subscription.trial_end_date = date(2024, 2, 1)

        active_subscription = Mock()
        active_subscription.trial_end_date = None

        # Execute & Assert
        assert trial_handler.is_in_trial(trial_subscription, date(2024, 1, 15)) is True
        assert trial_handler.is_in_trial(trial_subscription, date(2024, 2, 15)) is False
        assert trial_handler.is_in_trial(active_subscription, date(2024, 1, 15)) is False

    def test_calculate_trial_end_date(self, trial_handler):
        """Test calculating trial end date."""
        # Execute
        trial_end = trial_handler.calculate_trial_end_date(
            start_date=date(2024, 1, 1),
            trial_days=14
        )

        # Assert
        assert trial_end == date(2024, 1, 15)  # 14 days after start

    def test_get_first_billing_date_after_trial(self, trial_handler):
        """Test getting first billing date after trial ends."""
        # Execute
        first_billing = trial_handler.get_first_billing_date(
            trial_end_date=date(2024, 1, 15),
            billing_day=1,  # Bill on 1st of month
            billing_cycle=BillingCycle.MONTHLY
        )

        # Assert - should be Feb 1st (next billing cycle)
        assert first_billing == date(2024, 2, 1)

    def test_should_bill_subscription_trial_active(self, trial_handler):
        """Test billing decision during trial period."""
        # Setup
        trial_subscription = Mock()
        trial_subscription.trial_end_date = date(2024, 2, 1)
        trial_subscription.next_billing_date = date(2024, 2, 1)

        # Execute & Assert - should not bill during trial
        assert trial_handler.should_bill_subscription(
            trial_subscription, date(2024, 1, 15)
        ) is False

    def test_should_bill_subscription_trial_ended(self, trial_handler):
        """Test billing decision after trial ends."""
        # Setup
        post_trial_subscription = Mock()
        post_trial_subscription.trial_end_date = date(2024, 1, 15)
        post_trial_subscription.next_billing_date = date(2024, 1, 20)

        # Execute & Assert - should bill after trial
        assert trial_handler.should_bill_subscription(
            post_trial_subscription, date(2024, 1, 25)
        ) is True

    def test_create_trial_period(self, trial_handler):
        """Test creating trial period object."""
        # Execute
        trial_period = trial_handler.create_trial_period(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15)
        )

        # Assert
        assert isinstance(trial_period, BillingPeriodValue)
        assert trial_period.start_date == date(2024, 1, 1)
        assert trial_period.end_date == date(2024, 1, 15)


class TestBillingScheduler:
    """Test BillingScheduler functionality."""

    @pytest.fixture
    def scheduler(self):
        """Create BillingScheduler instance."""
        return BillingScheduler(
            default_due_days=30,
            grace_period_days=3
        )

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.grace_period_days == 3
        assert scheduler.overdue_threshold_days == 30

    def test_calculate_due_date(self, scheduler):
        """Test calculating invoice due date."""
        # Execute
        due_date = scheduler.calculate_due_date(
            issue_date=date(2024, 1, 1),
            payment_terms_days=30
        )

        # Assert
        assert due_date == date(2024, 1, 31)

    def test_calculate_overdue_date(self, scheduler):
        """Test calculating overdue date."""
        # Execute
        overdue_date = scheduler.calculate_overdue_date(
            due_date=date(2024, 1, 31)
        )

        # Assert - should add grace period
        assert overdue_date == date(2024, 2, 3)  # 31 + 3 days grace

    def test_is_overdue(self, scheduler):
        """Test checking if invoice is overdue."""
        # Setup
        due_date = date(2024, 1, 31)

        # Execute & Assert
        assert scheduler.is_overdue(due_date, date(2024, 1, 31)) is False  # Due date
        assert scheduler.is_overdue(due_date, date(2024, 2, 2)) is False   # Within grace
        assert scheduler.is_overdue(due_date, date(2024, 2, 4)) is True    # Past grace

    def test_get_billing_schedule(self, scheduler):
        """Test generating billing schedule."""
        # Execute
        schedule = scheduler.get_billing_schedule(
            subscription_start=date(2024, 1, 1),
            billing_cycle=BillingCycle.MONTHLY,
            periods_count=3
        )

        # Assert
        assert len(schedule) == 3
        assert all('period_start' in period and 'period_end' in period for period in schedule)

        # Check first period
        first_period = schedule[0]
        assert first_period['period_start'] == date(2024, 1, 1)


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
        assert january_period.days_in_period() == 31
        assert february_period.days_in_period() == 29

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

    def test_billing_period_is_current(self):
        """Test checking if period is current."""
        # Setup
        current_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        # Execute & Assert
        assert current_period.is_current(date(2024, 1, 15)) is True
        assert current_period.is_current(date(2024, 2, 1)) is False

    def test_billing_period_overlap_detection(self):
        """Test detecting overlapping periods."""
        # Setup
        period1 = BillingPeriodValue(date(2024, 1, 1), date(2024, 1, 31), BillingCycle.MONTHLY)
        period2 = BillingPeriodValue(date(2024, 1, 15), date(2024, 2, 14), BillingCycle.MONTHLY)
        period3 = BillingPeriodValue(date(2024, 2, 1), date(2024, 2, 29), BillingCycle.MONTHLY)

        # Execute & Assert
        assert period1.overlaps_with(period2) is True   # Overlapping
        assert period2.overlaps_with(period3) is True   # Adjacent overlapping
        assert period1.overlaps_with(period3) is False  # Non-overlapping
