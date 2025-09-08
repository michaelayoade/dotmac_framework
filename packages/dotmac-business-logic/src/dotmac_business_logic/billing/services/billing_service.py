"""
Core billing service implementation.

This service orchestrates all billing operations including subscription management,
invoice generation, payment processing, and usage tracking.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# NOTE: Model classes (Invoice, Payment, Subscription, etc.) should be imported
# from the actual implementation packages (e.g., dotmac_isp.modules.billing.models)
# This service is designed to work with any model implementation that follows
# the expected interface. For now, we'll use type hints from protocols.
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from dateutil.relativedelta import relativedelta

# Import enums from core models
from ..core.models import (
    BillingCycle,
    BillingPeriod,
    InvoiceStatus,
    PaymentStatus,
    SubscriptionStatus,
)

if TYPE_CHECKING:
    # These would normally come from the consuming package's models
    class Invoice:
        pass

    class InvoiceLineItem:
        pass

    class Payment:
        pass

    class Subscription:
        pass

    class UsageRecord:
        pass
else:
    # Runtime type aliases - use Any for runtime
    Invoice = Any
    InvoiceLineItem = Any
    Payment = Any
    Subscription = Any
    UsageRecord = Any
from ..schemas.billing_schemas import SubscriptionCreate, UsageRecordCreate
from ..services.protocols import (
    BillingPlanRepositoryProtocol,
    CustomerRepositoryProtocol,
    DatabaseSessionProtocol,
    InvoiceRepositoryProtocol,
    NotificationServiceProtocol,
    PaymentGatewayProtocol,
    PaymentRepositoryProtocol,
    PdfGeneratorProtocol,
    SubscriptionRepositoryProtocol,
    TaxCalculationServiceProtocol,
    UsageRepositoryProtocol,
)


class BillingService:
    """Main billing service implementation."""

    @staticmethod
    def _quantize_currency(amount: Decimal) -> Decimal:
        """Quantize decimal amounts to 2 decimal places for currency precision."""
        return amount.quantize(Decimal('0.01'))

    def __init__(
        self,
        db: DatabaseSessionProtocol,
        customer_repo: CustomerRepositoryProtocol,
        plan_repo: BillingPlanRepositoryProtocol,
        subscription_repo: SubscriptionRepositoryProtocol,
        invoice_repo: InvoiceRepositoryProtocol,
        payment_repo: PaymentRepositoryProtocol,
        usage_repo: UsageRepositoryProtocol,
        payment_gateway: Optional[PaymentGatewayProtocol] = None,
        notification_service: Optional[NotificationServiceProtocol] = None,
        tax_service: Optional[TaxCalculationServiceProtocol] = None,
        pdf_generator: Optional[PdfGeneratorProtocol] = None,
        default_tenant_id: Optional[UUID] = None,
    ):
        """Initialize billing service with dependencies."""
        self.db = db
        self.customer_repo = customer_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo
        self.invoice_repo = invoice_repo
        self.payment_repo = payment_repo
        self.usage_repo = usage_repo
        self.payment_gateway = payment_gateway
        self.notification_service = notification_service
        self.tax_service = tax_service
        self.pdf_generator = pdf_generator
        self.default_tenant_id = default_tenant_id

    async def create_subscription(
        self,
        customer_id: UUID,
        plan_id: UUID,
        start_date: Optional[date] = None,
        **kwargs,
    ) -> Subscription:
        """Create a new subscription for a customer."""

        # Validate customer exists
        if start_date is None:
            start_date = date.today()

        customer = await self.customer_repo.get(customer_id, self.default_tenant_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Validate plan exists
        plan = await self.plan_repo.get(plan_id, self.default_tenant_id)
        if not plan or not plan.is_active:
            raise ValueError(f"Billing plan {plan_id} not found or inactive")

        # Set defaults

        # Calculate trial end date if plan has trial period
        trial_end_date = None
        if plan.trial_days > 0:
            trial_end_date = start_date + timedelta(days=plan.trial_days)

        # Calculate next billing date based on plan cycle
        # If there's a trial, billing starts after trial ends
        billing_start_date = trial_end_date if trial_end_date else start_date
        next_billing_date = self._calculate_next_billing_date(
            billing_start_date, plan.billing_cycle
        )

        # Create subscription data
        subscription_data = SubscriptionCreate(
            customer_id=customer_id,
            billing_plan_id=plan_id,
            start_date=start_date,
            trial_end_date=trial_end_date,
            tenant_id=self.default_tenant_id,
            **kwargs,
        )

        # Create subscription
        subscription = await self.subscription_repo.create(subscription_data)

        # Generate subscription number
        subscription.subscription_number = f"SUB-{subscription.id.hex[:8].upper()}"
        subscription.next_billing_date = next_billing_date

        await self.db.commit()
        await self.db.refresh(subscription)

        # Send notification if service is available
        if self.notification_service:
            await self.notification_service.send_subscription_notification(
                customer, subscription, "subscription_created"
            )

        return subscription

    async def cancel_subscription(
        self, subscription_id: UUID, cancellation_date: Optional[date] = None
    ) -> Subscription:
        """Cancel a subscription."""

        if cancellation_date is None:
            cancellation_date = date.today()

        subscription = await self.subscription_repo.get(
            subscription_id, self.default_tenant_id
        )
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError("Subscription is already cancelled")

        # Update subscription status
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.end_date = cancellation_date

        await self.db.commit()

        # Send notification
        if self.notification_service:
            customer = await self.customer_repo.get(subscription.customer_id)
            await self.notification_service.send_subscription_notification(
                customer, subscription, "subscription_cancelled"
            )

        return subscription

    async def generate_invoice(
        self, subscription_id: UUID, billing_period: BillingPeriod
    ) -> Invoice:
        """Generate invoice for a billing period."""

        subscription = await self.subscription_repo.get(
            subscription_id,
            self.default_tenant_id,
            load_relationships=["customer", "billing_plan"],
        )

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        customer = subscription.customer
        plan = subscription.billing_plan

        # Create invoice
        invoice = Invoice(
            customer_id=customer.id,
            subscription_id=subscription.id,
            invoice_date=billing_period.period_end,
            due_date=billing_period.period_end
            + timedelta(
                days=30
            ),  # Default 30 daysservice_period_start=billing_period.period_start,
            service_period_end=billing_period.period_end,
            currency=plan.currency,
            tenant_id=self.default_tenant_id,
        )

        # Generate invoice number
        invoice.invoice_number = f"INV-{uuid4().hex[:8].upper()}"

        # Add to session
        self.db.add(invoice)
        await self.db.flush()  # Get ID without committing

        # Create line items
        line_items = []

        # Base subscription fee
        if billing_period.base_amount > 0:
            line_item = InvoiceLineItem(
                invoice_id=invoice.id,
                description=f"{plan.name} - {billing_period.period_start} to {billing_period.period_end}",
                quantity=subscription.quantity,
                unit_price=plan.base_price,
                line_total=billing_period.base_amount,
                service_period_start=billing_period.period_start,
                service_period_end=billing_period.period_end,
                tenant_id=self.default_tenant_id,
            )
            line_items.append(line_item)

        # Usage charges
        if billing_period.usage_amount > 0:
            line_item = InvoiceLineItem(
                invoice_id=invoice.id,
                description=f"Usage charges - {billing_period.overage_usage} {plan.usage_unit}",
                quantity=billing_period.overage_usage,
                unit_price=plan.overage_price or Decimal("0"),
                line_total=billing_period.usage_amount,
                service_period_start=billing_period.period_start,
                service_period_end=billing_period.period_end,
                tenant_id=self.default_tenant_id,
            )
            line_items.append(line_item)

        # Add line items to session
        for line_item in line_items:
            self.db.add(line_item)

        # Calculate totals and line-level taxes
        invoice.subtotal = billing_period.total_amount
        total_tax_amount = Decimal("0")

        # Calculate tax per line item respecting taxable flag
        if self.tax_service:
            for line_item in line_items:
                if line_item.taxable:
                    tax_result = await self.tax_service.calculate_tax(
                        line_item.line_total, customer
                    )
                    line_tax = Decimal(str(tax_result.get("amount", 0)))
                    line_item.tax_amount = line_tax.quantize(Decimal('0.01'))
                    total_tax_amount += line_item.tax_amount

                    # Set tax type and rate on invoice from first taxable line
                    if not hasattr(invoice, 'tax_type') or not invoice.tax_type:
                        invoice.tax_type = tax_result.get("tax_type", "none")
                        invoice.tax_rate = Decimal(str(tax_result.get("rate", 0)))
                else:
                    line_item.tax_amount = Decimal("0")

        invoice.tax_amount = total_tax_amount.quantize(Decimal('0.01'))
        invoice.total_amount = (invoice.subtotal + invoice.tax_amount).quantize(Decimal('0.01'))
        invoice.amount_due = invoice.total_amount

        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def process_payment(
        self, invoice_id: UUID, payment_method_id: str, amount: Optional[Decimal] = None,
        idempotency_key: Optional[str] = None
    ) -> Payment:
        """Process payment for an invoice."""

        # Generate idempotency key if not provided
        if idempotency_key is None:
            idempotency_key = f"pay_{invoice_id}_{payment_method_id}_{int(datetime.now(timezone.utc).timestamp())}"

        # Check for existing payment with same idempotency key
        if hasattr(self.payment_repo, 'get_by_idempotency_key'):
            existing_payment = await self.payment_repo.get_by_idempotency_key(
                idempotency_key, self.default_tenant_id
            )
            if existing_payment:
                return existing_payment

        invoice = await self.invoice_repo.get(
            invoice_id, self.default_tenant_id, load_relationships=["customer"]
        )

        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        if amount is None:
            amount = invoice.amount_due.quantize(Decimal('0.01'))
        else:
            amount = amount.quantize(Decimal('0.01'))

        customer = invoice.customer

        # Create payment record
        payment = Payment(
            customer_id=customer.id,
            invoice_id=invoice.id,
            amount=amount,
            currency=invoice.currency,
            payment_method=payment_method_id,
            status=PaymentStatus.PENDING,
            payment_date=datetime.now(timezone.utc),
            tenant_id=self.default_tenant_id,
            idempotency_key=idempotency_key,
        )

        payment.payment_number = f"PAY-{uuid4().hex[:8].upper()}"

        self.db.add(payment)
        await self.db.flush()

        # Process through gateway if available
        if self.payment_gateway:
            try:
                gateway_result = await self.payment_gateway.process_payment(
                    amount=amount,
                    currency=invoice.currency,
                    payment_method_id=payment_method_id,
                    customer_id=str(customer.id),
                    idempotency_key=idempotency_key,
                    metadata={"invoice_id": str(invoice.id), "payment_id": str(payment.id)},
                )

                payment.gateway_transaction_id = gateway_result.get("transaction_id")
                payment.authorization_code = gateway_result.get("authorization_code")

                if gateway_result.get("status") == "completed":
                    payment.status = PaymentStatus.SUCCESS
                    payment.processed_date = datetime.now(timezone.utc)

                    # Update invoice amounts with quantization
                    invoice.amount_paid = (invoice.amount_paid + amount).quantize(Decimal('0.01'))
                    invoice.amount_due = max(
                        Decimal("0"), (invoice.total_amount - invoice.amount_paid).quantize(Decimal('0.01'))
                    )

                    if invoice.amount_due <= 0:
                        invoice.status = InvoiceStatus.PAID
                elif gateway_result.get("status") == "failed":
                    payment.status = PaymentStatus.FAILED
                    payment.failure_reason = gateway_result.get("error_message", "Payment failed")

            except Exception as e:
                # Handle gateway errors
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = str(e)
                # Don't re-raise to allow payment record to be saved with failure status

        await self.db.commit()

        # Send notification
        if self.notification_service and payment.status == PaymentStatus.SUCCESS:
            await self.notification_service.send_payment_notification(
                customer, payment, "payment_received"
            )
        elif self.notification_service and payment.status == PaymentStatus.FAILED:
            await self.notification_service.send_payment_notification(
                customer, payment, "payment_failed"
            )

        return payment

    async def record_usage(
        self, subscription_id: UUID, usage_data: UsageRecordCreate
    ) -> UsageRecord:
        """Record usage for a subscription."""

        subscription = await self.subscription_repo.get(
            subscription_id, self.default_tenant_id
        )
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Set subscription_id in usage data
        usage_data.subscription_id = subscription_id
        usage_data.tenant_id = self.default_tenant_id

        usage_record = await self.usage_repo.create(usage_data)

        # Update subscription current usage
        subscription.current_usage += usage_data.quantity
        await self.db.commit()

        return usage_record

    async def run_billing_cycle(
        self, billing_date: Optional[date] = None, tenant_id: Optional[UUID] = None
    ) -> dict[str, Any]:
        """Run billing cycle for due subscriptions."""

        if billing_date is None:
            billing_date = date.today()

        # Get subscriptions due for billing
        due_subscriptions = await self.subscription_repo.get_due_for_billing(
            billing_date
        )

        results = {
            "processed_count": 0,
            "failed_count": 0,
            "total_amount": Decimal("0"),
            "errors": [],
        }

        for subscription in due_subscriptions:
            # Calculate billing period
            billing_period = await self._calculate_billing_period(
                subscription, billing_date
            )

            # Generate invoice
            invoice = await self.generate_invoice(subscription.id, billing_period)

            # Update subscription next billing date
            subscription.next_billing_date = self._calculate_next_billing_date(
                billing_date, subscription.billing_plan.billing_cycle
            )

            results["processed_count"] += 1
            results["total_amount"] += invoice.total_amount

            # Mark billing period as invoiced
            billing_period.invoiced = True
            billing_period.invoice_id = invoice.id

        await self.db.commit()
        return results

    def _calculate_next_billing_date(
        self, current_date: date, billing_cycle: BillingCycle
    ) -> date:
        """Calculate the next billing date based on cycle."""

        if billing_cycle == BillingCycle.WEEKLY:
            return current_date + timedelta(weeks=1)
        elif billing_cycle == BillingCycle.MONTHLY:
            return current_date + relativedelta(months=1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return current_date + relativedelta(months=3)
        elif billing_cycle == BillingCycle.SEMI_ANNUALLY:
            return current_date + relativedelta(months=6)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return current_date + relativedelta(years=1)
        else:
            # ONE_TIME - no next billing date
            return current_date

    async def _calculate_billing_period(
        self, subscription: Subscription, billing_date: date
    ) -> BillingPeriod:
        """Calculate billing period for a subscription."""

        # Determine period start and end dates
        period_end = billing_date
        period_start = subscription.next_billing_date

        # If this is the first billing, use start date
        if period_start > period_end:
            period_start = subscription.start_date

        # Get usage for the period
        usage_records = await self.usage_repo.get_by_subscription(
            subscription.id, period_start, period_end
        )

        total_usage = sum(record.quantity for record in usage_records)
        included_usage = subscription.billing_plan.included_usage or Decimal("0")
        overage_usage = max(Decimal("0"), total_usage - included_usage)

        # Calculate amounts
        base_amount = subscription.custom_price or subscription.billing_plan.base_price
        usage_amount = overage_usage * (
            subscription.billing_plan.overage_price or Decimal("0")
        )
        total_amount = base_amount + usage_amount

        # Create billing period record
        billing_period = BillingPeriod(
            subscription_id=subscription.id,
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            usage_amount=usage_amount,
            total_amount=total_amount,
            total_usage=total_usage,
            included_usage=included_usage,
            overage_usage=overage_usage,
            tenant_id=self.default_tenant_id,
        )

        self.db.add(billing_period)
        await self.db.flush()

        return billing_period
