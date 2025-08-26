"""Invoice domain service implementation."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import logging

from .interfaces import IInvoiceService, IBillingCalculationService
from ..models import Invoice, InvoiceStatus
from .. import schemas
from ..repository import InvoiceRepository, InvoiceLineItemRepository
from dotmac_isp.shared.exceptions import ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class InvoiceService(IInvoiceService):
    """Domain service for invoice operations."""

    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        line_item_repo: InvoiceLineItemRepository,
        calculation_service: IBillingCalculationService,
        tenant_id: UUID,
    ):
        """Initialize operation."""
        self.invoice_repo = invoice_repo
        self.line_item_repo = line_item_repo
        self.calculation_service = calculation_service
        self.tenant_id = tenant_id

    async def create_invoice(self, invoice_data: schemas.InvoiceCreate) -> Invoice:
        """Create a new invoice with proper calculations and validation."""
        try:
            logger.info(f"Creating invoice for customer {invoice_data.customer_id}")

            # Validate invoice data
            await self._validate_invoice_data(invoice_data)

            # Calculate invoice totals
            totals = await self.calculate_invoice_totals(
                invoice_data.line_items,
                invoice_data.tax_rate,
                invoice_data.discount_rate,
            )

            # Prepare invoice data
            invoice_dict = {
                "customer_id": invoice_data.customer_id,
                "issue_date": invoice_data.issue_date or date.today(),
                "due_date": invoice_data.due_date
                or (date.today() + timedelta(days=30)),
                "status": InvoiceStatus.DRAFT,
                "subtotal": totals["subtotal"],
                "tax_amount": totals["tax_amount"],
                "discount_amount": totals["discount_amount"],
                "total_amount": totals["total_amount"],
                "amount_paid": Decimal("0.00"),
                "amount_due": totals["total_amount"],
                "currency": invoice_data.currency or "USD",
                "tax_rate": invoice_data.tax_rate,
                "discount_rate": invoice_data.discount_rate,
                "notes": invoice_data.notes,
                "terms": invoice_data.terms,
                "billing_address": invoice_data.billing_address,
                "custom_fields": invoice_data.custom_fields or {},
            }

            # Create invoice
            invoice = self.invoice_repo.create(invoice_dict)

            # Create line items
            await self._create_line_items(invoice.id, invoice_data.line_items)

            logger.info(f"Invoice created successfully: {invoice.id}")
            return invoice

        except Exception as e:
            logger.error(f"Failed to create invoice: {str(e)}")
            raise ServiceError(f"Failed to create invoice: {str(e)}")

    async def get_invoice(self, invoice_id: UUID) -> Invoice:
        """Retrieve invoice by ID with validation."""
        try:
            invoice = self.invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise NotFoundError(f"Invoice not found: {invoice_id}")
            return invoice
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve invoice {invoice_id}: {str(e)}")
            raise ServiceError(f"Failed to retrieve invoice: {str(e)}")

    async def update_invoice_status(
        self, invoice_id: UUID, status: InvoiceStatus
    ) -> Invoice:
        """Update invoice status with business rule validation."""
        try:
            # Get current invoice
            invoice = await self.get_invoice(invoice_id)

            # Validate status transition
            await self._validate_status_transition(invoice.status, status)

            # Update status
            updated_invoice = self.invoice_repo.update(invoice_id, {"status": status})

            # Handle status-specific logic
            await self._handle_status_change(updated_invoice, status)

            logger.info(f"Invoice {invoice_id} status updated to {status}")
            return updated_invoice

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update invoice status: {str(e)}")
            raise ServiceError(f"Failed to update invoice status: {str(e)}")

    async def get_customer_invoices(self, customer_id: UUID) -> List[Invoice]:
        """Get all invoices for a customer."""
        try:
            return self.invoice_repo.get_by_customer_id(customer_id)
        except Exception as e:
            logger.error(f"Failed to retrieve customer invoices: {str(e)}")
            raise ServiceError(f"Failed to retrieve customer invoices: {str(e)}")

    async def get_overdue_invoices(self) -> List[Invoice]:
        """Get all overdue invoices."""
        try:
            return self.invoice_repo.get_overdue_invoices()
        except Exception as e:
            logger.error(f"Failed to retrieve overdue invoices: {str(e)}")
            raise ServiceError(f"Failed to retrieve overdue invoices: {str(e)}")

    async def calculate_invoice_totals(
        self,
        line_items: List[schemas.InvoiceLineItemCreate],
        tax_rate: Optional[Decimal] = None,
        discount_rate: Optional[Decimal] = None,
    ) -> Dict[str, Decimal]:
        """Calculate invoice totals from line items."""
        try:
            # Calculate subtotal
            subtotal = sum(
                self.calculation_service.calculate_line_item_total(
                    item.quantity, item.unit_price
                )
                for item in line_items
            )

            # Calculate tax
            tax_amount = self.calculation_service.calculate_tax(
                subtotal, tax_rate or Decimal("0.00")
            )

            # Calculate discount
            discount_amount = self.calculation_service.calculate_discount(
                subtotal, discount_rate or Decimal("0.00")
            )

            # Calculate total
            total_amount = self.calculation_service.calculate_invoice_total(
                subtotal, tax_amount, discount_amount
            )

            return {
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "discount_amount": discount_amount,
                "total_amount": total_amount,
            }

        except Exception as e:
            logger.error(f"Failed to calculate invoice totals: {str(e)}")
            raise ServiceError(f"Failed to calculate invoice totals: {str(e)}")

    async def generate_invoice_pdf(self, invoice: Invoice) -> bytes:
        """Generate PDF for invoice."""
        try:
            # Import PDF generation service
            from ..services.pdf_service import InvoicePDFService

            pdf_service = InvoicePDFService()
            return await pdf_service.generate_invoice_pdf(invoice)

        except Exception as e:
            logger.error(f"Failed to generate invoice PDF: {str(e)}")
            raise ServiceError(f"Failed to generate invoice PDF: {str(e)}")

    async def send_invoice_email(self, invoice: Invoice, customer_email: str) -> bool:
        """Send invoice via email."""
        try:
            # Import email service
            from ..services.email_service import InvoiceEmailService

            email_service = InvoiceEmailService()
            return await email_service.send_invoice_email(invoice, customer_email)

        except Exception as e:
            logger.error(f"Failed to send invoice email: {str(e)}")
            raise ServiceError(f"Failed to send invoice email: {str(e)}")

    async def _validate_invoice_data(self, invoice_data: schemas.InvoiceCreate) -> None:
        """Validate invoice creation data."""
        if not invoice_data.line_items:
            raise ValidationError("Invoice must have at least one line item")

        if invoice_data.due_date and invoice_data.issue_date:
            if invoice_data.due_date < invoice_data.issue_date:
                raise ValidationError("Due date cannot be before issue date")

        # Validate line items
        for item in invoice_data.line_items:
            if item.quantity <= 0:
                raise ValidationError(f"Invalid quantity for item: {item.description}")
            if item.unit_price < 0:
                raise ValidationError(
                    f"Invalid unit price for item: {item.description}"
                )

    async def _create_line_items(
        self, invoice_id: UUID, line_items: List[schemas.InvoiceLineItemCreate]
    ) -> None:
        """Create invoice line items."""
        for i, item_data in enumerate(line_items, 1):
            line_item_dict = {
                "invoice_id": invoice_id,
                "line_number": i,
                "description": item_data.description,
                "quantity": item_data.quantity,
                "unit_price": item_data.unit_price,
                "line_total": self.calculation_service.calculate_line_item_total(
                    item_data.quantity, item_data.unit_price
                ),
                "service_instance_id": item_data.service_instance_id,
                "billing_period_start": item_data.billing_period_start,
                "billing_period_end": item_data.billing_period_end,
                "custom_fields": item_data.custom_fields or {},
            }
            self.line_item_repo.create(line_item_dict)

    async def _validate_status_transition(
        self, current_status: InvoiceStatus, new_status: InvoiceStatus
    ) -> None:
        """Validate invoice status transitions."""
        # Define valid transitions
        valid_transitions = {
            InvoiceStatus.DRAFT: [InvoiceStatus.PENDING, InvoiceStatus.CANCELLED],
            InvoiceStatus.PENDING: [InvoiceStatus.SENT, InvoiceStatus.CANCELLED],
            InvoiceStatus.SENT: [
                InvoiceStatus.PAID,
                InvoiceStatus.OVERDUE,
                InvoiceStatus.CANCELLED,
            ],
            InvoiceStatus.OVERDUE: [InvoiceStatus.PAID, InvoiceStatus.CANCELLED],
            InvoiceStatus.PAID: [InvoiceStatus.REFUNDED],
            InvoiceStatus.CANCELLED: [],  # Terminal state
            InvoiceStatus.REFUNDED: [],  # Terminal state
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise ValidationError(
                f"Invalid status transition from {current_status} to {new_status}"
            )

    async def _handle_status_change(
        self, invoice: Invoice, new_status: InvoiceStatus
    ) -> None:
        """Handle invoice status change side effects."""
        if new_status == InvoiceStatus.SENT:
            # Send invoice email notification
            # This would be handled by an event system in production
            logger.info(f"Invoice {invoice.id} has been sent")

        elif new_status == InvoiceStatus.PAID:
            # Update amount paid and due
            self.invoice_repo.update(
                invoice.id,
                {
                    "amount_paid": invoice.total_amount,
                    "amount_due": Decimal("0.00"),
                    "paid_date": datetime.now(timezone.utc),
                },
            )
            logger.info(f"Invoice {invoice.id} has been marked as paid")

        elif new_status == InvoiceStatus.OVERDUE:
            # Send overdue notification
            logger.info(f"Invoice {invoice.id} is now overdue")

        elif new_status == InvoiceStatus.CANCELLED:
            # Handle cancellation logic
            logger.info(f"Invoice {invoice.id} has been cancelled")
