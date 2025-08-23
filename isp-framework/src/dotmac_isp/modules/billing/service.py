"""Service layer for billing operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings
from dotmac_isp.modules.billing import schemas
from dotmac_isp.modules.billing.models import (
    Invoice,
    InvoiceLineItem,
    Payment,
    CreditNote,
    Receipt,
    Subscription,
    InvoiceStatus,
    PaymentStatus,
    PaymentMethod,
    BillingCycle,
)
from dotmac_isp.modules.billing.repository import (
    InvoiceRepository,
    InvoiceLineItemRepository,
    PaymentRepository,
    SubscriptionRepository,
    CreditNoteRepository,
)
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)


class BillingService:
    """Service layer for billing operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize billing service."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)

        # Repositories
        self.invoice_repo = InvoiceRepository(db, self.tenant_id)
        self.line_item_repo = InvoiceLineItemRepository(db, self.tenant_id)
        self.payment_repo = PaymentRepository(db, self.tenant_id)
        self.subscription_repo = SubscriptionRepository(db, self.tenant_id)
        self.credit_note_repo = CreditNoteRepository(db, self.tenant_id)

    # Invoice Management
    async def create_invoice(self, invoice_data: schemas.InvoiceCreate) -> Invoice:
        """Create a new invoice."""
        try:
            # Calculate totals from line items
            subtotal = sum(
                item.quantity * item.unit_price for item in invoice_data.line_items
            )

            # Calculate tax
            tax_total = self._calculate_tax(
                subtotal, invoice_data.tax_rate or Decimal("0")
            )

            # Calculate discounts
            discount_total = self._calculate_discount(
                subtotal, invoice_data.discount_rate or Decimal("0")
            )

            # Calculate final total
            total_amount = subtotal + tax_total - discount_total

            # Prepare invoice data
            invoice_dict = {
                "customer_id": invoice_data.customer_id,
                "issue_date": invoice_data.issue_date or date.today(),
                "due_date": invoice_data.due_date
                or (date.today() + timedelta(days=30)),
                "status": InvoiceStatus.DRAFT,
                "subtotal": subtotal,
                "tax_total": tax_total,
                "discount_total": discount_total,
                "total_amount": total_amount,
                "amount_paid": Decimal("0"),
                "amount_due": total_amount,
                "currency": invoice_data.currency or "USD",
                "tax_rate": invoice_data.tax_rate,
                "discount_rate": invoice_data.discount_rate,
                "notes": invoice_data.notes,
                "terms": invoice_data.terms,
                "billing_address": invoice_data.billing_address,
                "custom_fields": invoice_data.custom_fields,
            }

            # Create invoice
            invoice = self.invoice_repo.create(invoice_dict)

            # Create line items
            for item_data in invoice_data.line_items:
                line_item_dict = {
                    "invoice_id": invoice.id,
                    "line_number": item_data.line_number,
                    "description": item_data.description,
                    "quantity": item_data.quantity,
                    "unit_price": item_data.unit_price,
                    "total_price": item_data.quantity * item_data.unit_price,
                    "service_instance_id": item_data.service_instance_id,
                    "billing_period_start": item_data.billing_period_start,
                    "billing_period_end": item_data.billing_period_end,
                    "custom_fields": item_data.custom_fields,
                }
                self.line_item_repo.create(line_item_dict)

            return invoice

        except Exception as e:
            raise ServiceError(f"Failed to create invoice: {str(e)}")

    async def get_invoice(self, invoice_id: UUID) -> Invoice:
        """Get invoice by ID."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {invoice_id}")
        return invoice

    async def get_invoice_by_number(self, invoice_number: str) -> Invoice:
        """Get invoice by invoice number."""
        invoice = self.invoice_repo.get_by_invoice_number(invoice_number)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {invoice_number}")
        return invoice

    async def list_invoices(
        self,
        customer_id: Optional[UUID] = None,
        status: Optional[InvoiceStatus] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Invoice]:
        """List invoices with filtering."""
        return self.invoice_repo.list_invoices(
            customer_id=customer_id,
            status=status,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
            skip=skip,
            limit=limit,
        )

    async def send_invoice(self, invoice_id: UUID) -> Invoice:
        """Mark invoice as sent."""
        invoice = self.invoice_repo.update_status(invoice_id, InvoiceStatus.SENT)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {invoice_id}")

        # Here you would integrate with email service to send the invoice
        # For now, just update the status

        return invoice

    async def void_invoice(self, invoice_id: UUID, reason: str) -> Invoice:
        """Void an invoice."""
        invoice = await self.get_invoice(invoice_id)

        if invoice.status == InvoiceStatus.PAID:
            raise ValidationError("Cannot void a paid invoice")

        invoice = self.invoice_repo.update_status(invoice_id, InvoiceStatus.VOID)

        # Log the void reason (could be stored in notes or audit log)

        return invoice

    # Payment Management
    async def process_payment(self, payment_data: schemas.PaymentCreate) -> Payment:
        """Process a payment."""
        try:
            # Validate invoice exists and is payable
            invoice = await self.get_invoice(payment_data.invoice_id)

            if invoice.status == InvoiceStatus.PAID:
                raise ValidationError("Invoice is already paid")

            if invoice.status == InvoiceStatus.VOID:
                raise ValidationError("Cannot pay a void invoice")

            # Validate payment amount
            if payment_data.amount <= 0:
                raise ValidationError("Payment amount must be positive")

            if payment_data.amount > invoice.amount_due:
                raise ValidationError("Payment amount exceeds amount due")

            # Create payment record
            payment_dict = {
                "customer_id": payment_data.customer_id,
                "invoice_id": payment_data.invoice_id,
                "amount": payment_data.amount,
                "payment_method": payment_data.payment_method,
                "payment_date": payment_data.payment_date or datetime.utcnow(),
                "status": PaymentStatus.PENDING,
                "gateway_transaction_id": payment_data.gateway_transaction_id,
                "gateway_response": payment_data.gateway_response,
                "notes": payment_data.notes,
                "custom_fields": payment_data.custom_fields,
            }

            payment = self.payment_repo.create(payment_dict)

            # Process payment through gateway (mock for now)
            gateway_result = await self._process_payment_gateway(payment, payment_data)

            if gateway_result["success"]:
                # Update payment status to completed
                payment = self.payment_repo.update_status(
                    payment.id, PaymentStatus.COMPLETED, gateway_result.get("response")
                )

                # Update invoice amounts
                self.invoice_repo.update_amounts(invoice.id, payment_data.amount)

            else:
                # Update payment status to failed
                payment = self.payment_repo.update_status(
                    payment.id, PaymentStatus.FAILED, gateway_result.get("response")
                )

            return payment

        except Exception as e:
            raise ServiceError(f"Failed to process payment: {str(e)}")

    async def get_payment(self, payment_id: UUID) -> Payment:
        """Get payment by ID."""
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError(f"Payment not found: {payment_id}")
        return payment

    async def list_payments(
        self,
        customer_id: Optional[UUID] = None,
        invoice_id: Optional[UUID] = None,
        status: Optional[PaymentStatus] = None,
        payment_method: Optional[PaymentMethod] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Payment]:
        """List payments with filtering."""
        return self.payment_repo.list_payments(
            customer_id=customer_id,
            invoice_id=invoice_id,
            status=status,
            payment_method=payment_method,
            skip=skip,
            limit=limit,
        )

    # Subscription Management
    async def create_subscription(
        self, subscription_data: schemas.SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription."""
        try:
            # Calculate next billing date
            next_billing_date = self._calculate_next_billing_date(
                subscription_data.start_date, subscription_data.billing_cycle
            )

            subscription_dict = {
                "customer_id": subscription_data.customer_id,
                "service_instance_id": subscription_data.service_instance_id,
                "subscription_plan_id": subscription_data.subscription_plan_id,
                "start_date": subscription_data.start_date,
                "end_date": subscription_data.end_date,
                "billing_cycle": subscription_data.billing_cycle,
                "amount": subscription_data.amount,
                "currency": subscription_data.currency or "USD",
                "next_billing_date": next_billing_date,
                "is_active": True,
                "auto_renew": subscription_data.auto_renew,
                "proration_enabled": subscription_data.proration_enabled,
                "custom_fields": subscription_data.custom_fields,
            }

            subscription = self.subscription_repo.create(subscription_dict)

            return subscription

        except Exception as e:
            raise ServiceError(f"Failed to create subscription: {str(e)}")

    async def get_subscription(self, subscription_id: UUID) -> Subscription:
        """Get subscription by ID."""
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise NotFoundError(f"Subscription not found: {subscription_id}")
        return subscription

    async def cancel_subscription(
        self, subscription_id: UUID, cancel_date: Optional[date] = None
    ) -> Subscription:
        """Cancel a subscription."""
        subscription = await self.get_subscription(subscription_id)

        cancel_date = cancel_date or date.today()

        update_data = {
            "is_active": False,
            "end_date": cancel_date,
            "cancellation_date": cancel_date,
        }

        updated_subscription = self.subscription_repo.update(
            subscription_id, update_data
        )
        if not updated_subscription:
            raise ServiceError("Failed to cancel subscription")

        return updated_subscription

    # Credit Note Management
    async def create_credit_note(
        self, credit_note_data: schemas.CreditNoteCreate
    ) -> CreditNote:
        """Create a credit note."""
        try:
            credit_note_dict = {
                "customer_id": credit_note_data.customer_id,
                "invoice_id": credit_note_data.invoice_id,
                "amount": credit_note_data.amount,
                "reason": credit_note_data.reason,
                "issue_date": credit_note_data.issue_date or date.today(),
                "currency": credit_note_data.currency or "USD",
                "notes": credit_note_data.notes,
                "custom_fields": credit_note_data.custom_fields,
            }

            credit_note = self.credit_note_repo.create(credit_note_dict)

            # If linked to an invoice, update the invoice amounts
            if credit_note_data.invoice_id:
                invoice = await self.get_invoice(credit_note_data.invoice_id)
                # Apply credit to invoice (reduce amount due)
                new_amount_due = max(
                    Decimal("0"), invoice.amount_due - credit_note_data.amount
                )
                self.invoice_repo.update_amounts(
                    credit_note_data.invoice_id, Decimal("0")
                )

            return credit_note

        except Exception as e:
            raise ServiceError(f"Failed to create credit note: {str(e)}")

    # Private helper methods
    def _calculate_tax(self, subtotal: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate tax amount."""
        return subtotal * (tax_rate / Decimal("100"))

    def _calculate_discount(self, subtotal: Decimal, discount_rate: Decimal) -> Decimal:
        """Calculate discount amount."""
        return subtotal * (discount_rate / Decimal("100"))

    def _calculate_next_billing_date(
        self, start_date: date, billing_cycle: BillingCycle
    ) -> date:
        """Calculate next billing date based on cycle."""
        if billing_cycle == BillingCycle.MONTHLY:
            return start_date + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return start_date + timedelta(days=90)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return start_date + timedelta(days=365)
        else:  # WEEKLY
            return start_date + timedelta(days=7)

    async def _process_payment_gateway(
        self, payment: Payment, payment_data: schemas.PaymentCreate
    ) -> Dict[str, Any]:
        """Process payment through payment gateway (mock implementation)."""
        # This would integrate with actual payment gateways like Stripe, PayPal, etc.
        # For now, simulate a successful payment

        import random

        success = random.choice([True, True, True, False])  # 75% success rate for demo

        if success:
            return {
                "success": True,
                "response": {
                    "transaction_id": f"txn_{uuid4().hex[:12]}",
                    "gateway": "mock_gateway",
                    "status": "completed",
                    "processed_at": datetime.utcnow().isoformat(),
                },
            }
        else:
            return {
                "success": False,
                "response": {
                    "error_code": "PAYMENT_DECLINED",
                    "error_message": "Payment was declined by the bank",
                    "gateway": "mock_gateway",
                    "processed_at": datetime.utcnow().isoformat(),
                },
            }


class SubscriptionBillingService:
    """Service for automated subscription billing."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize subscription billing service."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)
        self.billing_service = BillingService(db, tenant_id)
        self.subscription_repo = SubscriptionRepository(db, self.tenant_id)

    async def process_recurring_billing(self) -> Dict[str, Any]:
        """Process recurring billing for all active subscriptions."""
        try:
            # Get all subscriptions due for billing
            active_subscriptions = self.subscription_repo.list_active_subscriptions()
            due_subscriptions = [
                sub
                for sub in active_subscriptions
                if sub.next_billing_date <= date.today()
            ]

            results = {
                "processed": 0,
                "failed": 0,
                "total": len(due_subscriptions),
                "details": [],
            }

            for subscription in due_subscriptions:
                try:
                    # Generate invoice for subscription
                    invoice_data = self._create_subscription_invoice_data(subscription)
                    invoice = await self.billing_service.create_invoice(invoice_data)

                    # Send invoice
                    await self.billing_service.send_invoice(invoice.id)

                    # Update next billing date
                    next_billing_date = (
                        self.billing_service._calculate_next_billing_date(
                            subscription.next_billing_date, subscription.billing_cycle
                        )
                    )

                    self.subscription_repo.update(
                        subscription.id,
                        {
                            "next_billing_date": next_billing_date,
                            "last_billing_date": date.today(),
                        },
                    )

                    results["processed"] += 1
                    results["details"].append(
                        {
                            "subscription_id": str(subscription.id),
                            "customer_id": str(subscription.customer_id),
                            "invoice_id": str(invoice.id),
                            "amount": float(subscription.amount),
                            "status": "success",
                        }
                    )

                except Exception as e:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "subscription_id": str(subscription.id),
                            "customer_id": str(subscription.customer_id),
                            "error": str(e),
                            "status": "failed",
                        }
                    )

            return results

        except Exception as e:
            raise ServiceError(f"Failed to process recurring billing: {str(e)}")

    def _create_subscription_invoice_data(
        self, subscription: Subscription
    ) -> schemas.InvoiceCreate:
        """Create invoice data from subscription."""
        # Calculate billing period
        period_start = subscription.next_billing_date
        if subscription.billing_cycle == BillingCycle.MONTHLY:
            period_end = period_start + timedelta(days=30)
        elif subscription.billing_cycle == BillingCycle.QUARTERLY:
            period_end = period_start + timedelta(days=90)
        elif subscription.billing_cycle == BillingCycle.ANNUALLY:
            period_end = period_start + timedelta(days=365)
        else:  # WEEKLY
            period_end = period_start + timedelta(days=7)

        # Create line item for subscription
        line_item = schemas.InvoiceLineItemCreate(
            line_number=1,
            description=f"Subscription billing for {subscription.billing_cycle.value} period",
            quantity=Decimal("1"),
            unit_price=subscription.amount,
            service_instance_id=subscription.service_instance_id,
            billing_period_start=period_start,
            billing_period_end=period_end,
        )

        return schemas.InvoiceCreate(
            customer_id=subscription.customer_id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            currency=subscription.currency,
            line_items=[line_item],
            notes=f"Automated billing for subscription {subscription.id}",
        )
