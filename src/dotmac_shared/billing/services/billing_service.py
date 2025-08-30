"""
Core billing service implementation.

This service orchestrates all billing operations including subscription management,
invoice generation, payment processing, and usage tracking.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..core.models import (
    BillingCycle,
    BillingPeriod,
    BillingPlan,
    Customer,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
)
from ..schemas.billing_schemas import SubscriptionCreate, UsageRecordCreate
from ..services.protocols import (
    BillingPlanRepositoryProtocol,
    BillingServiceProtocol,
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
        customer = await self.customer_repo.get(customer_id, self.default_tenant_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Validate plan exists
        plan = await self.plan_repo.get(plan_id, self.default_tenant_id)
        if not plan or not plan.is_active:
            raise ValueError(f"Billing plan {plan_id} not found or inactive")

        # Set defaults
        if start_date is None:
            start_date = date.today()

        # Calculate next billing date based on plan cycle
        next_billing_date = self._calculate_next_billing_date(
            start_date, plan.billing_cycle
        )

        # Calculate trial end date if plan has trial period
        trial_end_date = None
        if plan.trial_days > 0:
            trial_end_date = start_date + timedelta(days=plan.trial_days)

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

        subscription = await self.subscription_repo.get(
            subscription_id, self.default_tenant_id
        )
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError("Subscription is already cancelled")

        if cancellation_date is None:
            cancellation_date = date.today()

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
            due_date=billing_period.period_end + timedelta(days=30),  # Default 30 days
            service_period_start=billing_period.period_start,
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

        # Calculate totals
        invoice.subtotal = billing_period.total_amount

        # Calculate tax if service is available
        tax_amount = Decimal("0")
        if self.tax_service:
            tax_result = await self.tax_service.calculate_tax(
                invoice.subtotal, customer
            )
            tax_amount = Decimal(str(tax_result.get("amount", 0)))
            invoice.tax_type = tax_result.get("tax_type", "none")
            invoice.tax_rate = Decimal(str(tax_result.get("rate", 0)))

        invoice.tax_amount = tax_amount
        invoice.total_amount = invoice.subtotal + tax_amount
        invoice.amount_due = invoice.total_amount

        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def process_payment(
        self, invoice_id: UUID, payment_method_id: str, amount: Optional[Decimal] = None
    ) -> Payment:
        """Process payment for an invoice."""

        invoice = await self.invoice_repo.get(
            invoice_id, self.default_tenant_id, load_relationships=["customer"]
        )

        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        if amount is None:
            amount = invoice.amount_due

        customer = invoice.customer

        # Create payment record
        payment = Payment(
            customer_id=customer.id,
            invoice_id=invoice.id,
            amount=amount,
            currency=invoice.currency,
            payment_method=payment_method_id,
            status=PaymentStatus.PENDING,
            payment_date=datetime.utcnow(),
            tenant_id=self.default_tenant_id,
        )

        payment.payment_number = f"PAY-{uuid4().hex[:8].upper()}"

        self.db.add(payment)
        await self.db.flush()

        # Process through gateway if available
        if self.payment_gateway:
            gateway_result = await self.payment_gateway.process_payment(
                amount=amount,
                currency=invoice.currency,
                payment_method_id=payment_method_id,
                customer_id=str(customer.id),
                metadata={"invoice_id": str(invoice.id), "payment_id": str(payment.id)},
            )

            payment.gateway_transaction_id = gateway_result.get("transaction_id")
            payment.authorization_code = gateway_result.get("authorization_code")

            if gateway_result.get("status") == "completed":
                payment.status = PaymentStatus.COMPLETED
                payment.processed_date = datetime.utcnow()

                # Update invoice
                invoice.amount_paid += amount
                invoice.amount_due = max(
                    Decimal("0"), invoice.total_amount - invoice.amount_paid
                )

                if invoice.amount_due <= 0:
                    invoice.status = InvoiceStatus.PAID

        await self.db.commit()

        # Send notification
        if self.notification_service and payment.status == PaymentStatus.COMPLETED:
            await self.notification_service.send_payment_notification(
                customer, payment, "payment_received"
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
    ) -> Dict[str, Any]:
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
            # Add one month
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            # Add 3 months
            new_month = current_date.month + 3
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
            return current_date.replace(year=new_year, month=new_month)
        elif billing_cycle == BillingCycle.SEMI_ANNUALLY:
            # Add 6 months
            new_month = current_date.month + 6
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
            return current_date.replace(year=new_year, month=new_month)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return current_date.replace(year=current_date.year + 1)
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
