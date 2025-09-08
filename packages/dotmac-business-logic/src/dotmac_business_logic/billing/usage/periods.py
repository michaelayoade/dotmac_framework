"""
Billing period calculations and trial handling.

This module provides utilities for calculating billing periods,
handling end-of-month scenarios, and managing trial periods.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from dateutil.relativedelta import relativedelta

from ..core.models import BillingCycle, BillingPeriodValue


class BillingPeriodCalculator:
    """Handles billing period calculations with proper EOM handling."""

    @staticmethod
    def calculate_next_billing_date(
        current_date: date,
        billing_cycle: BillingCycle,
        preserve_day_of_month: bool = True,
    ) -> date:
        """
        Calculate next billing date with proper end-of-month handling.

        Args:
            current_date: Current billing date
            billing_cycle: Billing cycle (monthly, quarterly, etc.)
            preserve_day_of_month: Whether to preserve day of month when possible

        Returns:
            Next billing date
        """
        if billing_cycle == BillingCycle.ONE_TIME:
            return current_date

        # Use relativedelta to handle month-end scenarios correctly
        if billing_cycle == BillingCycle.MONTHLY:
            return current_date + relativedelta(months=1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return current_date + relativedelta(months=3)
        elif billing_cycle == BillingCycle.SEMI_ANNUALLY:
            return current_date + relativedelta(months=6)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return current_date + relativedelta(years=1)
        else:
            raise ValueError(f"Unsupported billing cycle: {billing_cycle}")

    @classmethod
    def create_billing_period(
        cls,
        start_date: date,
        billing_cycle: BillingCycle,
        end_date: Optional[date] = None,
    ) -> BillingPeriodValue:
        """
        Create a billing period with calculated end date.

        Args:
            start_date: Period start date
            billing_cycle: Billing cycle
            end_date: Optional explicit end date

        Returns:
            BillingPeriodValue object
        """
        if not end_date:
            end_date = cls.calculate_next_billing_date(start_date, billing_cycle)

        return BillingPeriodValue(
            start_date=start_date,
            end_date=end_date,
            cycle=billing_cycle,
        )

    @staticmethod
    def is_end_of_month_date(check_date: date) -> bool:
        """Check if a date is the last day of its month."""
        # Get the first day of next month and subtract one day
        first_of_next_month = check_date.replace(day=1) + relativedelta(months=1)
        last_day_of_month = first_of_next_month - relativedelta(days=1)
        return check_date == last_day_of_month

    @staticmethod
    def get_month_end_date(year: int, month: int) -> date:
        """Get the last day of a given month/year."""
        # First day of next month, then subtract one day
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)

        return next_month_first - relativedelta(days=1)

    @classmethod
    def calculate_prorated_period(
        cls,
        base_period: BillingPeriodValue,
        actual_start: date,
        actual_end: Optional[date] = None,
    ) -> tuple[BillingPeriodValue, Decimal]:
        """
        Calculate prorated billing period and proration factor.

        Args:
            base_period: Full billing period
            actual_start: Actual service start date
            actual_end: Actual service end date (optional)

        Returns:
            Tuple of (prorated_period, proration_factor)
        """
        # Determine actual period boundaries
        period_start = max(base_period.start_date, actual_start)
        period_end = min(base_period.end_date, actual_end) if actual_end else base_period.end_date

        # Create prorated period
        prorated_period = BillingPeriodValue(
            start_date=period_start,
            end_date=period_end,
            cycle=base_period.cycle,
        )

        # Calculate proration factor
        proration_factor = base_period.get_proration_factor(period_start, period_end)

        return prorated_period, proration_factor


class TrialHandler:
    """Handles trial period logic and transitions."""

    @staticmethod
    def is_in_trial(
        current_date: date,
        subscription_start: date,
        trial_end_date: Optional[date],
    ) -> bool:
        """Check if subscription is currently in trial period."""
        if not trial_end_date:
            return False

        return subscription_start <= current_date <= trial_end_date

    @staticmethod
    def calculate_trial_end_date(
        start_date: date,
        trial_days: int,
    ) -> date:
        """Calculate trial end date from start date and trial length."""
        return start_date + relativedelta(days=trial_days)

    @classmethod
    def get_first_billing_date(
        cls,
        subscription_start: date,
        billing_cycle: BillingCycle,
        trial_end_date: Optional[date] = None,
    ) -> date:
        """
        Calculate the first billing date respecting trial period.

        Args:
            subscription_start: When subscription started
            billing_cycle: Billing cycle for the subscription
            trial_end_date: End of trial period (optional)

        Returns:
            Date of first billing
        """
        if trial_end_date and trial_end_date > subscription_start:
            # First billing happens after trial ends
            return BillingPeriodCalculator.calculate_next_billing_date(
                trial_end_date, billing_cycle
            )
        else:
            # No trial, bill according to normal cycle
            return BillingPeriodCalculator.calculate_next_billing_date(
                subscription_start, billing_cycle
            )

    @staticmethod
    def should_bill_subscription(
        subscription: any,
        check_date: date,
    ) -> bool:
        """
        Determine if a subscription should be billed on a given date.

        Args:
            subscription: Subscription object with trial information
            check_date: Date to check billing eligibility

        Returns:
            True if subscription should be billed
        """
        # Don't bill during trial period
        if hasattr(subscription, 'trial_end_date') and subscription.trial_end_date:
            if check_date <= subscription.trial_end_date:
                return False

        # Check if it's the billing date
        if hasattr(subscription, 'next_billing_date'):
            return check_date >= subscription.next_billing_date

        return False

    @classmethod
    def create_trial_period(
        cls,
        start_date: date,
        trial_days: int,
        billing_cycle: BillingCycle,
    ) -> tuple[BillingPeriodValue, date]:
        """
        Create trial period and calculate first billing date.

        Args:
            start_date: Subscription start date
            trial_days: Length of trial in days
            billing_cycle: Billing cycle after trial

        Returns:
            Tuple of (trial_period, first_billing_date)
        """
        trial_end = cls.calculate_trial_end_date(start_date, trial_days)
        first_billing_date = cls.get_first_billing_date(
            start_date, billing_cycle, trial_end
        )

        trial_period = BillingPeriodValue(
            start_date=start_date,
            end_date=trial_end,
            cycle=billing_cycle,  # Keep cycle for consistency
        )

        return trial_period, first_billing_date


class BillingScheduler:
    """Manages billing schedules and due date calculations."""

    def __init__(
        self,
        default_due_days: int = 30,
        grace_period_days: int = 7,
    ):
        """
        Initialize billing scheduler.

        Args:
            default_due_days: Default days until invoice is due
            grace_period_days: Grace period before marking overdue
        """
        self.default_due_days = default_due_days
        self.grace_period_days = grace_period_days

    def calculate_due_date(
        self,
        billing_period_end: date,
        due_days: Optional[int] = None,
    ) -> date:
        """Calculate invoice due date from billing period end."""
        days = due_days or self.default_due_days
        return billing_period_end + relativedelta(days=days)

    def calculate_overdue_date(
        self,
        due_date: date,
        grace_days: Optional[int] = None,
    ) -> date:
        """Calculate when invoice becomes overdue."""
        grace = grace_days or self.grace_period_days
        return due_date + relativedelta(days=grace)

    def is_overdue(
        self,
        due_date: date,
        current_date: Optional[date] = None,
        grace_days: Optional[int] = None,
    ) -> bool:
        """Check if an invoice is overdue."""
        if not current_date:
            current_date = datetime.now().date()

        overdue_date = self.calculate_overdue_date(due_date, grace_days)
        return current_date > overdue_date

    def get_billing_schedule(
        self,
        start_date: date,
        billing_cycle: BillingCycle,
        periods_count: int,
        trial_end_date: Optional[date] = None,
    ) -> list[dict]:
        """
        Generate billing schedule for multiple periods.

        Args:
            start_date: Subscription start date
            billing_cycle: Billing cycle
            periods_count: Number of periods to generate
            trial_end_date: Optional trial end date

        Returns:
            List of billing schedule entries
        """
        schedule = []

        # Determine first billing date
        current_billing_date = TrialHandler.get_first_billing_date(
            start_date, billing_cycle, trial_end_date
        )

        for period_num in range(periods_count):
            period_start = current_billing_date
            period_end = BillingPeriodCalculator.calculate_next_billing_date(
                current_billing_date, billing_cycle
            )

            due_date = self.calculate_due_date(period_end)
            overdue_date = self.calculate_overdue_date(due_date)

            schedule.append({
                "period_number": period_num + 1,
                "period_start": period_start,
                "period_end": period_end,
                "billing_date": period_end,
                "due_date": due_date,
                "overdue_date": overdue_date,
            })

            # Move to next period
            current_billing_date = period_end

        return schedule
