"""
Usage aggregation and rating engine.

This module handles usage metering, aggregation, and conversion
to billable line items with tiered pricing support.
"""

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from ..core.models import BillingPeriodValue, UsageMetric


class UsageAggregator:
    """Aggregates raw usage data into billing metrics."""

    async def aggregate_usage_for_period(
        self,
        subscription_id: UUID,
        billing_period: BillingPeriodValue,
        usage_records: list[Any],
    ) -> dict[str, UsageMetric]:
        """
        Aggregate usage records for a billing period.

        Args:
            subscription_id: Subscription ID
            billing_period: Billing period to aggregate
            usage_records: Raw usage records

        Returns:
            Dictionary of usage metrics by metric name
        """
        aggregated = {}

        for record in usage_records:
            metric_name = record.meter_type or record.service_identifier

            if metric_name not in aggregated:
                aggregated[metric_name] = {
                    'total_quantity': Decimal('0'),
                    'unit': getattr(record, 'unit', 'units'),
                    'peak_usage': Decimal('0'),
                    'records_count': 0,
                }

            # Aggregate quantities
            quantity = getattr(record, 'quantity', Decimal('0'))
            aggregated[metric_name]['total_quantity'] += quantity
            aggregated[metric_name]['records_count'] += 1

            # Track peak usage
            peak = getattr(record, 'peak_usage', quantity)
            if peak > aggregated[metric_name]['peak_usage']:
                aggregated[metric_name]['peak_usage'] = peak

        # Convert to UsageMetric objects
        usage_metrics = {}
        for name, data in aggregated.items():
            usage_metrics[name] = UsageMetric(
                name=name,
                quantity=data['total_quantity'],
                unit=data['unit'],
                period=billing_period,
            )

        return usage_metrics

    async def apply_usage_allowances(
        self,
        usage_metrics: dict[str, UsageMetric],
        subscription_plan: Any,
    ) -> dict[str, UsageMetric]:
        """
        Apply subscription allowances to usage metrics.

        Args:
            usage_metrics: Raw usage metrics
            subscription_plan: Plan with allowances

        Returns:
            Usage metrics with allowances applied (overage only)
        """
        billable_usage = {}

        plan_allowances = getattr(subscription_plan, 'usage_allowances', {})

        for metric_name, metric in usage_metrics.items():
            allowance = plan_allowances.get(metric_name, Decimal('0'))

            # Calculate overage (billable usage)
            overage_quantity = max(Decimal('0'), metric.quantity - allowance)

            if overage_quantity > Decimal('0'):
                billable_usage[metric_name] = UsageMetric(
                    name=f"{metric_name}_overage",
                    quantity=overage_quantity,
                    unit=metric.unit,
                    period=metric.period,
                )

        return billable_usage

    def calculate_average_usage(
        self,
        usage_records: list[Any],
        period_days: int,
    ) -> dict[str, Decimal]:
        """Calculate average daily usage metrics."""
        if not usage_records or period_days <= 0:
            return {}

        totals = {}
        for record in usage_records:
            metric_name = record.meter_type or record.service_identifier
            quantity = getattr(record, 'quantity', Decimal('0'))

            if metric_name not in totals:
                totals[metric_name] = Decimal('0')

            totals[metric_name] += quantity

        # Calculate daily averages
        averages = {}
        for metric_name, total in totals.items():
            averages[f"{metric_name}_daily_avg"] = total / Decimal(period_days)

        return averages


class TieredPricingEngine:
    """Handles tiered pricing calculations for usage-based billing."""

    def calculate_tiered_pricing(
        self,
        quantity: Decimal,
        pricing_tiers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate charges using tiered pricing model.

        Args:
            quantity: Usage quantity to price
            pricing_tiers: List of pricing tier definitions

        Returns:
            Pricing calculation details
        """
        if not pricing_tiers:
            return {
                'total_charge': Decimal('0'),
                'tier_details': [],
                'effective_rate': Decimal('0'),
            }

        # Sort tiers by threshold
        sorted_tiers = sorted(pricing_tiers, key=lambda t: t.get('min_quantity', 0))

        total_charge = Decimal('0')
        remaining_quantity = quantity
        tier_details = []

        for i, tier in enumerate(sorted_tiers):
            tier_min = Decimal(str(tier.get('min_quantity', 0)))
            tier_max = Decimal(str(tier.get('max_quantity', float('inf'))))
            tier_rate = Decimal(str(tier.get('unit_price', 0)))

            # Skip if no quantity left to price
            if remaining_quantity <= Decimal('0'):
                break

            # Calculate quantity that falls in this tier
            if quantity <= tier_min:
                continue  # Haven't reached this tier yet

            tier_quantity = min(remaining_quantity, tier_max - tier_min)
            if i == 0:  # First tier
                tier_quantity = min(quantity, tier_max)

            tier_charge = tier_quantity * tier_rate
            total_charge += tier_charge

            tier_details.append({
                'tier_name': tier.get('name', f'Tier {i + 1}'),
                'min_quantity': tier_min,
                'max_quantity': tier_max if tier_max != float('inf') else None,
                'unit_price': tier_rate,
                'quantity_in_tier': tier_quantity,
                'tier_charge': tier_charge,
            })

            remaining_quantity -= tier_quantity

            if remaining_quantity <= Decimal('0'):
                break

        # Calculate effective rate
        effective_rate = total_charge / quantity if quantity > Decimal('0') else Decimal('0')

        return {
            'total_charge': total_charge,
            'tier_details': tier_details,
            'effective_rate': effective_rate,
        }

    def calculate_volume_discount(
        self,
        base_charge: Decimal,
        quantity: Decimal,
        volume_discounts: list[dict[str, Any]],
    ) -> tuple[Decimal, Optional[dict[str, Any]]]:
        """
        Apply volume discounts to base charge.

        Args:
            base_charge: Base charge before discount
            quantity: Total usage quantity
            volume_discounts: Volume discount tiers

        Returns:
            Tuple of (final_charge, discount_applied)
        """
        if not volume_discounts:
            return base_charge, None

        # Find applicable discount tier
        applicable_discount = None
        for discount in sorted(volume_discounts, key=lambda d: d.get('min_quantity', 0), reverse=True):
            min_quantity = Decimal(str(discount.get('min_quantity', 0)))
            if quantity >= min_quantity:
                applicable_discount = discount
                break

        if not applicable_discount:
            return base_charge, None

        # Apply discount
        discount_percent = Decimal(str(applicable_discount.get('discount_percent', 0))) / Decimal('100')
        discount_amount = base_charge * discount_percent
        final_charge = base_charge - discount_amount

        return final_charge, {
            'discount_name': applicable_discount.get('name', 'Volume Discount'),
            'discount_percent': applicable_discount['discount_percent'],
            'discount_amount': discount_amount,
            'min_quantity': applicable_discount['min_quantity'],
        }


class UsageRatingEngine:
    """Main engine for converting usage metrics to billable line items."""

    def __init__(self):
        self.aggregator = UsageAggregator()
        self.pricing_engine = TieredPricingEngine()

    async def rate_usage_for_subscription(
        self,
        subscription: Any,
        billing_period: BillingPeriodValue,
        usage_records: list[Any],
    ) -> list[dict[str, Any]]:
        """
        Convert usage records to billable line items.

        Args:
            subscription: Subscription with pricing plan
            billing_period: Billing period
            usage_records: Raw usage records

        Returns:
            List of billable line items
        """
        line_items = []

        # Aggregate usage
        usage_metrics = await self.aggregator.aggregate_usage_for_period(
            subscription.id,
            billing_period,
            usage_records,
        )

        # Apply allowances to get billable usage
        billable_usage = await self.aggregator.apply_usage_allowances(
            usage_metrics,
            subscription.billing_plan,
        )

        # Rate each usage metric
        for _metric_name, usage_metric in billable_usage.items():
            line_item = await self._rate_single_usage_metric(
                usage_metric,
                subscription.billing_plan,
            )

            if line_item['amount'] > Decimal('0'):
                line_items.append(line_item)

        return line_items

    async def _rate_single_usage_metric(
        self,
        usage_metric: UsageMetric,
        billing_plan: Any,
    ) -> dict[str, Any]:
        """Rate a single usage metric according to plan pricing."""
        # Get pricing configuration for this metric
        usage_pricing = self._get_usage_pricing_config(billing_plan, usage_metric.name)

        if not usage_pricing:
            return {
                'description': f'Usage: {usage_metric.name}',
                'quantity': usage_metric.quantity,
                'unit_price': Decimal('0'),
                'amount': Decimal('0'),
                'taxable': True,
            }

        # Calculate base pricing
        if usage_pricing.get('pricing_model') == 'tiered':
            pricing_result = self.pricing_engine.calculate_tiered_pricing(
                usage_metric.quantity,
                usage_pricing.get('tiers', []),
            )
            base_charge = pricing_result['total_charge']
            effective_rate = pricing_result['effective_rate']
        else:
            # Flat rate pricing
            unit_price = Decimal(str(usage_pricing.get('unit_price', 0)))
            base_charge = usage_metric.quantity * unit_price
            effective_rate = unit_price

        # Apply volume discounts if configured
        final_charge, volume_discount = self.pricing_engine.calculate_volume_discount(
            base_charge,
            usage_metric.quantity,
            usage_pricing.get('volume_discounts', []),
        )

        return {
            'description': self._format_usage_description(usage_metric, usage_pricing),
            'quantity': usage_metric.quantity,
            'unit': usage_metric.unit,
            'unit_price': effective_rate,
            'amount': final_charge,
            'taxable': usage_pricing.get('taxable', True),
            'usage_period_start': usage_metric.period.start_date,
            'usage_period_end': usage_metric.period.end_date,
            'pricing_details': {
                'base_charge': base_charge,
                'volume_discount': volume_discount,
                'final_charge': final_charge,
            }
        }

    def _get_usage_pricing_config(self, billing_plan: Any, metric_name: str) -> Optional[dict]:
        """Get pricing configuration for a usage metric."""
        usage_pricing = getattr(billing_plan, 'usage_pricing', {})
        return usage_pricing.get(metric_name)

    def _format_usage_description(self, usage_metric: UsageMetric, pricing_config: dict) -> str:
        """Format description for usage line item."""
        base_description = pricing_config.get('description', usage_metric.name)
        period_str = f"{usage_metric.period.start_date} to {usage_metric.period.end_date}"

        return f"{base_description} ({period_str})"

    async def calculate_usage_summary(
        self,
        subscription_id: UUID,
        usage_records: list[Any],
        billing_period: BillingPeriodValue,
    ) -> dict[str, Any]:
        """Generate usage summary for reporting."""
        usage_metrics = await self.aggregator.aggregate_usage_for_period(
            subscription_id,
            billing_period,
            usage_records,
        )

        period_days = billing_period.days_in_period()
        averages = self.aggregator.calculate_average_usage(usage_records, period_days)

        summary = {
            'subscription_id': subscription_id,
            'billing_period': {
                'start_date': billing_period.start_date,
                'end_date': billing_period.end_date,
                'days_in_period': period_days,
            },
            'usage_metrics': {},
            'daily_averages': averages,
            'total_records': len(usage_records),
        }

        # Add detailed usage metrics
        for name, metric in usage_metrics.items():
            summary['usage_metrics'][name] = {
                'name': metric.name,
                'quantity': metric.quantity,
                'unit': metric.unit,
                'is_zero': metric.is_zero(),
            }

        return summary
