"""Billing calculation domain service implementation."""

import calendar
import logging
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict

from dotmac_isp.shared.exceptions import ValidationError
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..models import BillingCycle
from .interfaces import IBillingCalculationService

logger = logging.getLogger(__name__)


class BillingCalculationService(IBillingCalculationService):
    """Service layer - exceptions bubble up to router @standard_exception_handler."""

    """Domain service for billing calculations."""

    def __init__(self):
        """Init   operation."""
        # Configure decimal precision for financial calculations
        self.decimal_places = Decimal("0.01")  # 2 decimal places

    def calculate_tax(self, subtotal: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate tax amount with proper rounding."""
        if not isinstance(subtotal, Decimal):
            subtotal = Decimal(str(subtotal))
        if not isinstance(tax_rate, Decimal):
            tax_rate = Decimal(str(tax_rate))

        if tax_rate < Decimal("0.00") or tax_rate > Decimal("1.00"):
            raise ValidationError(
                f"Tax rate must be between 0.00 and 1.00, got: {tax_rate}"
            )
        tax_amount = subtotal * tax_rate
        return tax_amount.quantize(self.decimal_places, rounding=ROUND_HALF_UP)

    def calculate_discount(self, subtotal: Decimal, discount_rate: Decimal) -> Decimal:
        """Calculate discount amount with proper rounding."""
        if not isinstance(subtotal, Decimal):
            subtotal = Decimal(str(subtotal))
        if not isinstance(discount_rate, Decimal):
            discount_rate = Decimal(str(discount_rate))

        if discount_rate < Decimal("0.00") or discount_rate > Decimal("1.00"):
            raise ValidationError(
                f"Discount rate must be between 0.00 and 1.00, got: {discount_rate}"
            )
        discount_amount = subtotal * discount_rate
        return discount_amount.quantize(self.decimal_places, rounding=ROUND_HALF_UP)

    def calculate_line_item_total(
        self, quantity: Decimal, unit_price: Decimal
    ) -> Decimal:
        """Calculate line item total with proper rounding."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        if not isinstance(unit_price, Decimal):
            unit_price = Decimal(str(unit_price))

        if quantity < Decimal("0.00"):
            raise ValidationError(f"Quantity cannot be negative: {quantity}")
        if unit_price < Decimal("0.00"):
            raise ValidationError(f"Unit price cannot be negative: {unit_price}")

        total = quantity * unit_price
        return total.quantize(self.decimal_places, rounding=ROUND_HALF_UP)

    def calculate_invoice_total(
        self, subtotal: Decimal, tax_amount: Decimal, discount_amount: Decimal
    ) -> Decimal:
        """Calculate final invoice total."""
        if not isinstance(subtotal, Decimal):
            subtotal = Decimal(str(subtotal))
        if not isinstance(tax_amount, Decimal):
            tax_amount = Decimal(str(tax_amount))
        if not isinstance(discount_amount, Decimal):
            discount_amount = Decimal(str(discount_amount))

        total = subtotal + tax_amount - discount_amount

        # Ensure total is not negative
        if total < Decimal("0.00"):
            logger.warning(f"Calculated total is negative: {total}, setting to 0.00")
            total = Decimal("0.00")

        return total.quantize(self.decimal_places, rounding=ROUND_HALF_UP)

    def calculate_proration(
        self,
        amount: Decimal,
        start_date: date,
        end_date: date,
        billing_cycle: BillingCycle,
    ) -> Decimal:
        """Calculate prorated amount for partial billing periods."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if end_date <= start_date:
            raise ValidationError("End date must be after start date")

        # Calculate the number of days in the partial period
        partial_days = (end_date - start_date).days

        # Calculate the total days in the billing cycle
        total_days = self._get_billing_cycle_days(billing_cycle, start_date)

        if total_days <= 0:
            raise ValidationError(f"Invalid billing cycle days: {total_days}")

        # Calculate prorated amount
        proration_ratio = Decimal(partial_days) / Decimal(total_days)
        prorated_amount = amount * proration_ratio

        return prorated_amount.quantize(self.decimal_places, rounding=ROUND_HALF_UP)

    def calculate_late_fee(
        self, overdue_amount: Decimal, days_overdue: int, late_fee_rate: Decimal
    ) -> Decimal:
        """Calculate late fee based on overdue amount and days."""
        if not isinstance(overdue_amount, Decimal):
            overdue_amount = Decimal(str(overdue_amount))
        if not isinstance(late_fee_rate, Decimal):
            late_fee_rate = Decimal(str(late_fee_rate))

        if days_overdue <= 0:
            return Decimal("0.00")

        if late_fee_rate < Decimal("0.00") or late_fee_rate > Decimal("1.00"):
            raise ValidationError(
                f"Late fee rate must be between 0.00 and 1.00, got: {late_fee_rate}"
            )
        # Calculate daily late fee rate
        daily_rate = late_fee_rate / Decimal("365")  # Annual rate to daily rate

        # Calculate late fee
        late_fee = overdue_amount * daily_rate * Decimal(days_overdue)

        return late_fee.quantize(self.decimal_places, rounding=ROUND_HALF_UP)

    def calculate_compound_tax(
        self, base_amount: Decimal, tax_rates: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Calculate multiple taxes that may be compounded."""
        if not isinstance(base_amount, Decimal):
            base_amount = Decimal(str(base_amount))

        tax_breakdown = {}
        running_total = base_amount

        for tax_name, tax_rate in tax_rates.items():
            if not isinstance(tax_rate, Decimal):
                tax_rate = Decimal(str(tax_rate))

            tax_amount = self.calculate_tax(running_total, tax_rate)
            tax_breakdown[tax_name] = tax_amount
            running_total += tax_amount  # Compound tax calculation

        tax_breakdown["total_tax"] = running_total - base_amount
        tax_breakdown["grand_total"] = running_total

        return tax_breakdown

    def calculate_payment_schedule(
        self,
        total_amount: Decimal,
        billing_cycle: BillingCycle,
        start_date: date,
        periods: int,
    ) -> list:
        """Calculate payment schedule for installment billing."""
        if not isinstance(total_amount, Decimal):
            total_amount = Decimal(str(total_amount))

        if periods <= 0:
            raise ValidationError("Number of periods must be greater than 0")

        # Calculate installment amount
        installment_amount = (total_amount / Decimal(periods)).quantize(
            self.decimal_places, rounding=ROUND_HALF_UP
        )
        # Handle remainder from rounding
        remainder = total_amount - (installment_amount * periods)

        schedule = []
        current_date = start_date

        for period in range(periods):
            amount = installment_amount

            # Add remainder to the last payment
            if period == periods - 1:
                amount += remainder

            schedule.append(
                {"period": period + 1, "due_date": current_date, "amount": amount}
            )
            # Calculate next due date based on billing cycle
            current_date = self._get_next_billing_date(current_date, billing_cycle)

        return schedule

    def _get_billing_cycle_days(
        self, billing_cycle: BillingCycle, reference_date: date
    ) -> int:
        """Get the number of days in a billing cycle."""
        if billing_cycle == BillingCycle.MONTHLY:
            # Get days in the month of the reference date
            return calendar.monthrange(reference_date.year, reference_date.month)[1]
        elif billing_cycle == BillingCycle.QUARTERLY:
            return 90  # Approximate quarter
        elif billing_cycle == BillingCycle.ANNUALLY:
            return 366 if calendar.isleap(reference_date.year) else 365
        else:
            return 30  # Default for one-time or unknown cycles

    def _get_next_billing_date(
        self, current_date: date, billing_cycle: BillingCycle
    ) -> date:
        """Calculate the next billing date based on cycle."""
        if billing_cycle == BillingCycle.MONTHLY:
            # Add one month
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return current_date + timedelta(days=90)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return current_date.replace(year=current_date.year + 1)
        else:
            return current_date  # One-time billing

    def validate_calculation_inputs(self, **kwargs) -> None:
        """Validate common calculation inputs."""
        for key, value in kwargs.items():
            if isinstance(value, (int, float)):
                kwargs[key] = Decimal(str(value))
            elif not isinstance(value, Decimal):
                raise ValidationError(
                    f"Invalid type for {key}: expected Decimal, got {type(value)}"
                )
            if key.endswith("_rate") and (
                value < Decimal("0.00") or value > Decimal("1.00")
            ):
                raise ValidationError(f"{key} must be between 0.00 and 1.00")

            if key.endswith("_amount") and value < Decimal("0.00"):
                raise ValidationError(f"{key} cannot be negative")
