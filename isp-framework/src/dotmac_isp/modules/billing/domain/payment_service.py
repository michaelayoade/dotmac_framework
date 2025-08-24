"""Payment domain service implementation."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import logging

from .interfaces import IPaymentService
from ..models import Payment, PaymentStatus, PaymentMethod, Invoice
from .. import schemas
from ..repository import PaymentRepository, InvoiceRepository
from dotmac_isp.shared.exceptions import ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class PaymentService(IPaymentService):
    """Domain service for payment operations."""

    def __init__(
        """  Init   operation."""
        self,
        payment_repo: PaymentRepository,
        invoice_repo: InvoiceRepository,
        tenant_id: UUID,
    ):
        self.payment_repo = payment_repo
        self.invoice_repo = invoice_repo
        self.tenant_id = tenant_id

    async def process_payment(self, payment_data: schemas.PaymentCreate) -> Payment:
        """Process a payment with validation and external payment processing."""
        try:
            logger.info(f"Processing payment for invoice {payment_data.invoice_id}")

            # Get and validate invoice
            invoice = await self._get_and_validate_invoice(payment_data.invoice_id)

            # Validate payment amount
            await self.validate_payment_amount(payment_data.amount, invoice.amount_due)

            # Process external payment
            external_result = await self._process_external_payment(payment_data)

            if external_result.get("status") != "success":
                raise ServiceError(
                    f"Payment failed: {external_result.get('error', 'Unknown error')}"
                )

            # Create payment record
            payment_dict = {
                "invoice_id": payment_data.invoice_id,
                "amount": payment_data.amount,
                "payment_date": datetime.utcnow(),
                "payment_method": payment_data.payment_method,
                "status": PaymentStatus.COMPLETED,
                "transaction_id": external_result.get("transaction_id"),
                "reference_number": payment_data.reference_number,
                "processor_response": external_result,
                "notes": payment_data.notes,
                "custom_fields": payment_data.custom_fields or {},
            }

            payment = self.payment_repo.create(payment_dict)

            # Update invoice payment status
            await self._update_invoice_payment_status(invoice, payment_data.amount)

            logger.info(f"Payment processed successfully: {payment.id}")
            return payment

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to process payment: {str(e)}")
            raise ServiceError(f"Payment processing failed: {str(e)}")

    async def refund_payment(
        self, payment_id: UUID, refund_amount: Decimal, reason: str
    ) -> Payment:
        """Process a payment refund."""
        try:
            logger.info(f"Processing refund for payment {payment_id}")

            # Get payment
            payment = self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise NotFoundError(f"Payment not found: {payment_id}")

            # Validate refund
            await self._validate_refund(payment, refund_amount)

            # Process external refund
            external_result = await self._process_external_refund(
                payment, refund_amount, reason
            )

            if external_result.get("status") != "success":
                raise ServiceError(
                    f"Refund failed: {external_result.get('error', 'Unknown error')}"
                )

            # Update payment status
            refund_data = {
                "status": PaymentStatus.REFUNDED,
                "refund_amount": refund_amount,
                "refund_date": datetime.utcnow(),
                "refund_reason": reason,
                "refund_transaction_id": external_result.get("refund_id"),
                "processor_response": {
                    **payment.processor_response,
                    "refund": external_result,
                },
            }

            updated_payment = self.payment_repo.update(payment_id, refund_data)

            # Update invoice payment status
            invoice = self.invoice_repo.get_by_id(payment.invoice_id)
            if invoice:
                new_amount_paid = max(
                    Decimal("0.00"), invoice.amount_paid - refund_amount
                )
                new_amount_due = invoice.total_amount - new_amount_paid

                self.invoice_repo.update(
                    payment.invoice_id,
                    {"amount_paid": new_amount_paid, "amount_due": new_amount_due},
                )

            logger.info(f"Refund processed successfully: {payment_id}")
            return updated_payment

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to process refund: {str(e)}")
            raise ServiceError(f"Refund processing failed: {str(e)}")

    async def get_invoice_payments(self, invoice_id: UUID) -> List[Payment]:
        """Get all payments for an invoice."""
        try:
            return self.payment_repo.get_by_invoice_id(invoice_id)
        except Exception as e:
            logger.error(f"Failed to retrieve invoice payments: {str(e)}")
            raise ServiceError(f"Failed to retrieve payments: {str(e)}")

    async def get_payment_status(self, payment_id: UUID) -> PaymentStatus:
        """Get current payment status."""
        try:
            payment = self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise NotFoundError(f"Payment not found: {payment_id}")
            return payment.status
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment status: {str(e)}")
            raise ServiceError(f"Failed to get payment status: {str(e)}")

    async def validate_payment_amount(
        self, amount: Decimal, invoice_total: Decimal
    ) -> bool:
        """Validate payment amount against invoice total."""
        if amount <= Decimal("0.00"):
            raise ValidationError("Payment amount must be greater than zero")

        if amount > invoice_total:
            raise ValidationError(
                f"Payment amount ({amount}) exceeds invoice total ({invoice_total})"
            )

        return True

    async def _get_and_validate_invoice(self, invoice_id: UUID) -> Invoice:
        """Get and validate invoice for payment."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {invoice_id}")

        if invoice.amount_due <= Decimal("0.00"):
            raise ValidationError("Invoice has no outstanding balance")

        return invoice

    async def _process_external_payment(
        self, payment_data: schemas.PaymentCreate
    ) -> Dict[str, Any]:
        """Process payment with external payment processor."""
        # This would integrate with actual payment processors (Stripe, PayPal, etc.)
        # For now, we'll simulate the process

        try:
            if payment_data.payment_method == PaymentMethod.CREDIT_CARD:
                return await self._process_credit_card_payment(payment_data)
            elif payment_data.payment_method == PaymentMethod.ACH:
                return await self._process_ach_payment(payment_data)
            elif payment_data.payment_method == PaymentMethod.BANK_TRANSFER:
                return await self._process_bank_transfer_payment(payment_data)
            else:
                # Manual payment methods
                return {
                    "status": "success",
                    "transaction_id": f"MANUAL_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "processed_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"External payment processing failed: {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def _process_credit_card_payment(
        self, payment_data: schemas.PaymentCreate
    ) -> Dict[str, Any]:
        """Process credit card payment."""
        # Simulate credit card processing
        return {
            "status": "success",
            "transaction_id": f"CC_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "processor": "stripe",
            "card_last4": "4242",
            "processed_at": datetime.utcnow().isoformat(),
        }

    async def _process_ach_payment(
        self, payment_data: schemas.PaymentCreate
    ) -> Dict[str, Any]:
        """Process ACH payment."""
        # Simulate ACH processing
        return {
            "status": "success",
            "transaction_id": f"ACH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "processor": "plaid",
            "account_last4": "1234",
            "processed_at": datetime.utcnow().isoformat(),
        }

    async def _process_bank_transfer_payment(
        self, payment_data: schemas.PaymentCreate
    ) -> Dict[str, Any]:
        """Process bank transfer payment."""
        # Simulate bank transfer processing
        return {
            "status": "success",
            "transaction_id": f"WIRE_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "processor": "bank",
            "processed_at": datetime.utcnow().isoformat(),
        }

    async def _process_external_refund(
        self, payment: Payment, refund_amount: Decimal, reason: str
    ) -> Dict[str, Any]:
        """Process refund with external payment processor."""
        try:
            # This would integrate with actual payment processors
            # For now, we'll simulate the process
            return {
                "status": "success",
                "refund_id": f"REF_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "original_transaction_id": payment.transaction_id,
                "refund_amount": str(refund_amount),
                "reason": reason,
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"External refund processing failed: {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def _validate_refund(self, payment: Payment, refund_amount: Decimal) -> None:
        """Validate refund request."""
        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError(
                f"Cannot refund payment with status: {payment.status}"
            )

        if refund_amount <= Decimal("0.00"):
            raise ValidationError("Refund amount must be greater than zero")

        if refund_amount > payment.amount:
            raise ValidationError(
                f"Refund amount ({refund_amount}) exceeds payment amount ({payment.amount})"
            )

        # Check if already refunded
        if hasattr(payment, "refund_amount") and payment.refund_amount:
            available_refund = payment.amount - payment.refund_amount
            if refund_amount > available_refund:
                raise ValidationError(
                    f"Refund amount exceeds available refund ({available_refund})"
                )

    async def _update_invoice_payment_status(
        self, invoice: Invoice, payment_amount: Decimal
    ) -> None:
        """Update invoice payment status after successful payment."""
        new_amount_paid = invoice.amount_paid + payment_amount
        new_amount_due = invoice.total_amount - new_amount_paid

        update_data = {"amount_paid": new_amount_paid, "amount_due": new_amount_due}

        # If fully paid, update status and paid date
        if new_amount_due <= Decimal("0.00"):
            from ..models import InvoiceStatus

            update_data.update(
                {"status": InvoiceStatus.PAID, "paid_date": datetime.utcnow()}
            )

        self.invoice_repo.update(invoice.id, update_data)
