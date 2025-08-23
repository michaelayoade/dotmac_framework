"""Service interfaces for billing domain."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

from ..models import (
    Invoice,
    InvoiceLineItem,
    Payment,
    CreditNote,
    Subscription,
    InvoiceStatus,
    PaymentStatus,
    PaymentMethod,
    BillingCycle,
)
from .. import schemas


class IInvoiceService(ABC):
    """Interface for invoice domain service."""

    @abstractmethod
    async def create_invoice(self, invoice_data: schemas.InvoiceCreate) -> Invoice:
        """Create a new invoice with calculations."""

    @abstractmethod
    async def get_invoice(self, invoice_id: UUID) -> Invoice:
        """Retrieve invoice by ID."""

    @abstractmethod
    async def update_invoice_status(
        self, invoice_id: UUID, status: InvoiceStatus
    ) -> Invoice:
        """Update invoice status."""

    @abstractmethod
    async def get_customer_invoices(self, customer_id: UUID) -> List[Invoice]:
        """Get all invoices for a customer."""

    @abstractmethod
    async def get_overdue_invoices(self) -> List[Invoice]:
        """Get all overdue invoices."""

    @abstractmethod
    async def calculate_invoice_totals(
        self,
        line_items: List[schemas.InvoiceLineItemCreate],
        tax_rate: Optional[Decimal] = None,
        discount_rate: Optional[Decimal] = None,
    ) -> Dict[str, Decimal]:
        """Calculate invoice totals from line items."""

    @abstractmethod
    async def generate_invoice_pdf(self, invoice: Invoice) -> bytes:
        """Generate PDF for invoice."""

    @abstractmethod
    async def send_invoice_email(self, invoice: Invoice, customer_email: str) -> bool:
        """Send invoice via email."""


class IPaymentService(ABC):
    """Interface for payment domain service."""

    @abstractmethod
    async def process_payment(self, payment_data: schemas.PaymentCreate) -> Payment:
        """Process a payment."""

    @abstractmethod
    async def refund_payment(
        self, payment_id: UUID, refund_amount: Decimal, reason: str
    ) -> Payment:
        """Process a payment refund."""

    @abstractmethod
    async def get_invoice_payments(self, invoice_id: UUID) -> List[Payment]:
        """Get all payments for an invoice."""

    @abstractmethod
    async def get_payment_status(self, payment_id: UUID) -> PaymentStatus:
        """Get current payment status."""

    @abstractmethod
    async def validate_payment_amount(
        self, amount: Decimal, invoice_total: Decimal
    ) -> bool:
        """Validate payment amount against invoice total."""


class ISubscriptionService(ABC):
    """Interface for subscription domain service."""

    @abstractmethod
    async def create_subscription(
        self, subscription_data: schemas.SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription."""

    @abstractmethod
    async def cancel_subscription(
        self, subscription_id: UUID, reason: str
    ) -> Subscription:
        """Cancel a subscription."""

    @abstractmethod
    async def update_subscription(
        self, subscription_id: UUID, update_data: schemas.SubscriptionUpdate
    ) -> Subscription:
        """Update subscription details."""

    @abstractmethod
    async def get_customer_subscriptions(
        self, customer_id: UUID, active_only: bool = True
    ) -> List[Subscription]:
        """Get customer subscriptions."""

    @abstractmethod
    async def get_subscriptions_for_billing(
        self, billing_date: date
    ) -> List[Subscription]:
        """Get subscriptions ready for billing."""

    @abstractmethod
    async def calculate_next_billing_date(
        self, current_date: date, billing_cycle: BillingCycle
    ) -> date:
        """Calculate next billing date based on cycle."""


class ICreditNoteService(ABC):
    """Interface for credit note domain service."""

    @abstractmethod
    async def create_credit_note(
        self, credit_note_data: schemas.CreditNoteCreate
    ) -> CreditNote:
        """Create a credit note."""

    @abstractmethod
    async def apply_credit_note(self, credit_note_id: UUID) -> bool:
        """Apply credit note to invoice."""

    @abstractmethod
    async def get_invoice_credit_notes(self, invoice_id: UUID) -> List[CreditNote]:
        """Get credit notes for an invoice."""

    @abstractmethod
    async def calculate_remaining_credit(self, invoice_id: UUID) -> Decimal:
        """Calculate remaining credit for an invoice."""


class IBillingCalculationService(ABC):
    """Interface for billing calculation service."""

    @abstractmethod
    def calculate_tax(self, subtotal: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate tax amount."""

    @abstractmethod
    def calculate_discount(self, subtotal: Decimal, discount_rate: Decimal) -> Decimal:
        """Calculate discount amount."""

    @abstractmethod
    def calculate_line_item_total(
        self, quantity: Decimal, unit_price: Decimal
    ) -> Decimal:
        """Calculate line item total."""

    @abstractmethod
    def calculate_invoice_total(
        self, subtotal: Decimal, tax_amount: Decimal, discount_amount: Decimal
    ) -> Decimal:
        """Calculate final invoice total."""

    @abstractmethod
    def calculate_proration(
        self,
        amount: Decimal,
        start_date: date,
        end_date: date,
        billing_cycle: BillingCycle,
    ) -> Decimal:
        """Calculate prorated amount for partial billing periods."""


class IBillingNotificationService(ABC):
    """Interface for billing notification service."""

    @abstractmethod
    async def send_invoice_created_notification(self, invoice: Invoice) -> bool:
        """Send notification when invoice is created."""

    @abstractmethod
    async def send_payment_received_notification(self, payment: Payment) -> bool:
        """Send notification when payment is received."""

    @abstractmethod
    async def send_overdue_invoice_notification(self, invoice: Invoice) -> bool:
        """Send overdue invoice notification."""

    @abstractmethod
    async def send_subscription_cancelled_notification(
        self, subscription: Subscription
    ) -> bool:
        """Send subscription cancellation notification."""

    @abstractmethod
    async def send_credit_note_created_notification(
        self, credit_note: CreditNote
    ) -> bool:
        """Send credit note creation notification."""


class IBillingReportService(ABC):
    """Interface for billing reporting service."""

    @abstractmethod
    async def generate_revenue_report(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate revenue report for date range."""

    @abstractmethod
    async def generate_aging_report(self, as_of_date: date) -> Dict[str, Any]:
        """Generate accounts receivable aging report."""

    @abstractmethod
    async def generate_subscription_report(
        self, customer_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Generate subscription analysis report."""

    @abstractmethod
    async def generate_payment_summary(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate payment summary report."""


class IRecurringBillingService(ABC):
    """Interface for recurring billing service."""

    @abstractmethod
    async def process_recurring_billing(self, billing_date: date) -> List[Invoice]:
        """Process all recurring billing for a date."""

    @abstractmethod
    async def generate_subscription_invoice(
        self, subscription: Subscription, billing_date: date
    ) -> Invoice:
        """Generate invoice for a subscription."""

    @abstractmethod
    async def update_subscription_next_billing_date(
        self, subscription: Subscription
    ) -> Subscription:
        """Update subscription's next billing date."""

    @abstractmethod
    async def handle_failed_recurring_payment(
        self, subscription: Subscription, error: str
    ) -> bool:
        """Handle failed recurring payment."""
