"""
Core billing service implementation.

This service orchestrates all billing operations using dependency injection.
It depends only on interfaces, not concrete implementations.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from dateutil.relativedelta import relativedelta

from .events import (
    InvoiceGenerated,
    PaymentFailed,
    PaymentProcessed,
    SubscriptionRenewed,
    publish_event,
)
from .interfaces import (
    BillingRepository,
    NotificationService,
    PaymentGateway,
    TaxService,
    UsageService,
)
from .models import (
    BillingCycle,
    BillingPeriodValue,
    InvoiceStatus,
    LineItem,
    Money,
    PaymentStatus,
    SubscriptionStatus,
    TaxCalculation,
    TaxType,
)


class BillingService:
    """
    Core billing service with dependency injection.

    This service coordinates billing operations without depending on
    specific infrastructure implementations.
    """

    def __init__(
        self,
        repository: BillingRepository,
        payment_gateway: PaymentGateway,
        tax_service: TaxService,
        usage_service: UsageService,
        notification_service: Optional[NotificationService] = None,
    ):
        """Initialize billing service with injected dependencies."""
        self.repository = repository
        self.payment_gateway = payment_gateway
        self.tax_service = tax_service
        self.usage_service = usage_service
        self.notification_service = notification_service

    async def create_subscription(
        self,
        customer_id: UUID,
        plan_id: UUID,
        start_date: date,
        billing_cycle: BillingCycle,
        trial_end_date: Optional[date] = None,
    ) -> Any:
        """Create a new subscription."""
        # Calculate next billing date
        if trial_end_date and trial_end_date > start_date:
            next_billing_date = trial_end_date
        else:
            next_billing_date = self._calculate_next_billing_date(start_date, billing_cycle)

        subscription_data = {
            "customer_id": customer_id,
            "plan_id": plan_id,
            "status": SubscriptionStatus.TRIAL if trial_end_date else SubscriptionStatus.ACTIVE,
            "start_date": start_date,
            "trial_end_date": trial_end_date,
            "next_billing_date": next_billing_date,
            "billing_cycle": billing_cycle,
            "current_period_start": start_date,
            "current_period_end": trial_end_date or next_billing_date,
        }

        return await self.repository.create_subscription(subscription_data)

    async def generate_invoice(
        self,
        subscription_id: UUID,
        billing_period: Optional[BillingPeriodValue] = None,
    ) -> Any:
        """Generate an invoice for a subscription."""
        subscription = await self.repository.get_subscription(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Get billing period
        if not billing_period:
            billing_period = await self._get_billing_period_for_subscription(subscription)

        # Calculate line items
        line_items = await self._calculate_invoice_line_items(subscription, billing_period)

        # Calculate totals
        subtotal = Money(sum(item.subtotal.amount for item in line_items))
        tax_total = Money(sum(
            item.tax_calculation.tax_amount.amount
            for item in line_items
            if item.tax_calculation and item.taxable
        ))
        total = subtotal.add(tax_total)

        # Create invoice
        invoice_data = {
            "subscription_id": subscription_id,
            "customer_id": subscription.customer_id,
            "invoice_number": await self._generate_invoice_number(),
            "status": InvoiceStatus.DRAFT,
            "issue_date": datetime.now(timezone.utc).date(),
            "due_date": self._calculate_due_date(billing_period.end_date),
            "subtotal": subtotal.amount,
            "tax_amount": tax_total.amount,
            "total": total.amount,
            "currency": subtotal.currency,
            "billing_period_start": billing_period.start_date,
            "billing_period_end": billing_period.end_date,
        }

        invoice = await self.repository.create_invoice(invoice_data)

        # Emit domain event
        await publish_event(InvoiceGenerated(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            invoice_id=invoice.id,
            customer_id=subscription.customer_id,
            subscription_id=subscription_id,
            amount=total.amount,
            currency=total.currency,
            due_date=invoice_data["due_date"],
            invoice_number=invoice_data["invoice_number"],
        ))

        return invoice

    async def process_payment(
        self,
        invoice_id: UUID,
        payment_method_id: str,
        amount: Optional[Decimal] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Process a payment for an invoice."""
        # Check for duplicate payment attempt
        if idempotency_key:
            existing_payment = await self.repository.get_payment_by_idempotency_key(
                idempotency_key
            )
            if existing_payment:
                return existing_payment

        invoice = await self.repository.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        charge_amount = amount or invoice.total

        # Create payment record
        payment_data = {
            "invoice_id": invoice_id,
            "customer_id": invoice.customer_id,
            "amount": charge_amount,
            "currency": invoice.currency,
            "payment_method": payment_method_id,
            "status": PaymentStatus.PROCESSING,
            "idempotency_key": idempotency_key,
        }
        payment = await self.repository.create_payment(payment_data)

        try:
            # Process payment through gateway
            gateway_response = await self.payment_gateway.charge(
                amount=charge_amount,
                payment_method_id=payment_method_id,
                currency=invoice.currency,
                description=f"Invoice {invoice.invoice_number}",
                metadata={"invoice_id": str(invoice_id), "payment_id": str(payment.id)},
            )

            # Update payment with success
            await self.repository.update_payment_status(payment.id, PaymentStatus.SUCCESS)

            # Update invoice status if fully paid
            if charge_amount >= invoice.total:
                await self.repository.update_invoice_status(invoice_id, InvoiceStatus.PAID)

            # Emit success event
            await publish_event(PaymentProcessed(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                payment_id=payment.id,
                invoice_id=invoice_id,
                customer_id=invoice.customer_id,
                amount=charge_amount,
                currency=invoice.currency,
                payment_method=payment_method_id,
                transaction_id=gateway_response.get("transaction_id"),
            ))

            return payment

        except Exception as e:
            # Update payment with failure
            await self.repository.update_payment_status(payment.id, PaymentStatus.FAILED)

            # Emit failure event
            await publish_event(PaymentFailed(
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                payment_id=payment.id,
                invoice_id=invoice_id,
                customer_id=invoice.customer_id,
                amount=charge_amount,
                currency=invoice.currency,
                payment_method=payment_method_id,
                error_code=getattr(e, 'code', None),
                error_message=str(e),
            ))

            raise

    async def process_billing_run(self, as_of_date: Optional[date] = None) -> dict[str, Any]:
        """Process billing for all due subscriptions."""
        if not as_of_date:
            as_of_date = datetime.now(timezone.utc).date()

        due_subscriptions = await self.repository.get_due_subscriptions(as_of_date)

        results = {
            "processed": 0,
            "errors": 0,
            "invoices_generated": [],
            "errors_detail": [],
        }

        for subscription in due_subscriptions:
            try:
                invoice = await self.generate_invoice(subscription.id)
                results["invoices_generated"].append(invoice.id)
                results["processed"] += 1

                # Update subscription for next billing cycle
                await self._advance_subscription_period(subscription)

            except Exception as e:
                results["errors"] += 1
                results["errors_detail"].append({
                    "subscription_id": subscription.id,
                    "error": str(e),
                })

        return results

    async def _calculate_invoice_line_items(
        self, subscription: Any, billing_period: BillingPeriodValue
    ) -> list[LineItem]:
        """Calculate line items for an invoice."""
        line_items = []

        # Base subscription fee
        plan = subscription.billing_plan  # Assuming relationship exists
        base_amount = Money(plan.monthly_price)  # Adjust based on billing cycle

        # Apply proration if needed
        if hasattr(subscription, 'proration_start_date') and subscription.proration_start_date:
            proration_factor = billing_period.get_proration_factor(
                subscription.proration_start_date
            )
            base_amount = base_amount.multiply(proration_factor)

        # Calculate tax
        tax_calculation = None
        if plan.taxable:
            tax_amount = await self.tax_service.calculate_tax(
                base_amount.amount,
                service_type="subscription",
            )
            if tax_amount > Decimal('0'):
                tax_calculation = TaxCalculation(
                    base_amount=base_amount,
                    tax_rate=await self.tax_service.get_tax_rate(),
                    tax_amount=Money(tax_amount, base_amount.currency),
                    tax_type=TaxType.SALES_TAX,
                )

        # Create base subscription line item
        line_items.append(LineItem(
            description=f"Subscription: {plan.name}",
            quantity=Decimal('1'),
            unit_price=base_amount,
            subtotal=base_amount,
            tax_calculation=tax_calculation,
            taxable=plan.taxable,
        ))

        # Add usage-based charges
        if plan.pricing_model in ["usage_based", "hybrid"]:
            usage_charges = await self._calculate_usage_charges(subscription, billing_period)
            line_items.extend(usage_charges)

        return line_items

    async def _calculate_usage_charges(
        self, subscription: Any, billing_period: BillingPeriodValue
    ) -> list[LineItem]:
        """Calculate usage-based line items."""
        usage_data = await self.usage_service.aggregate_usage(
            subscription.id,
            billing_period.start_date,
            billing_period.end_date,
        )

        # Get pricing tiers for the plan
        pricing_tiers = subscription.billing_plan.pricing_tiers or []

        usage_line_items = await self.usage_service.calculate_usage_charges(
            usage_data, pricing_tiers
        )

        line_items = []
        for item in usage_line_items:
            amount = Money(item["amount"])

            # Calculate tax for usage charges
            tax_calculation = None
            if item.get("taxable", True):
                tax_amount = await self.tax_service.calculate_tax(
                    amount.amount,
                    service_type="usage",
                )
                if tax_amount > Decimal('0'):
                    tax_calculation = TaxCalculation(
                        base_amount=amount,
                        tax_rate=await self.tax_service.get_tax_rate(),
                        tax_amount=Money(tax_amount, amount.currency),
                        tax_type=TaxType.SALES_TAX,
                    )

            line_items.append(LineItem(
                description=item["description"],
                quantity=Decimal(str(item.get("quantity", 1))),
                unit_price=Money(item.get("unit_price", item["amount"])),
                subtotal=amount,
                tax_calculation=tax_calculation,
                taxable=item.get("taxable", True),
            ))

        return line_items

    def _calculate_next_billing_date(self, current_date: date, billing_cycle: BillingCycle) -> date:
        """Calculate next billing date based on cycle."""
        if billing_cycle == BillingCycle.MONTHLY:
            return current_date + relativedelta(months=1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return current_date + relativedelta(months=3)
        elif billing_cycle == BillingCycle.SEMI_ANNUALLY:
            return current_date + relativedelta(months=6)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return current_date + relativedelta(months=12)
        else:  # ONE_TIME
            return current_date

    def _calculate_due_date(self, billing_end_date: date, days_until_due: int = 30) -> date:
        """Calculate invoice due date."""
        return billing_end_date + relativedelta(days=days_until_due)

    async def _get_billing_period_for_subscription(self, subscription: Any) -> BillingPeriodValue:
        """Get billing period for subscription."""
        return BillingPeriodValue(
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end,
            cycle=subscription.billing_cycle,
        )

    async def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        # Simple implementation - in practice you might want more sophisticated numbering
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}"

    async def _advance_subscription_period(self, subscription: Any) -> None:
        """Advance subscription to next billing period."""
        next_start = subscription.current_period_end
        next_end = self._calculate_next_billing_date(next_start, subscription.billing_cycle)

        await self.repository.update_subscription(subscription.id, {
            "current_period_start": next_start,
            "current_period_end": next_end,
            "next_billing_date": next_end,
        })

        # Emit renewal event
        await publish_event(SubscriptionRenewed(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            subscription_id=subscription.id,
            customer_id=subscription.customer_id,
            previous_period_end=subscription.current_period_end,
            new_period_end=next_end,
            amount=subscription.billing_plan.monthly_price,  # Adjust for cycle
        ))
