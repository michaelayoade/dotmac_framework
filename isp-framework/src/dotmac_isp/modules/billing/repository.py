"""Repository pattern for billing database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from decimal import Decimal

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
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class InvoiceRepository:
    """Repository for invoice database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, invoice_data: Dict[str, Any]) -> Invoice:
        """Create a new invoice."""
        try:
            # Generate invoice number if not provided
            if not invoice_data.get("invoice_number"):
                invoice_data["invoice_number"] = self._generate_invoice_number()

            invoice = Invoice(id=uuid4(), tenant_id=self.tenant_id, **invoice_data)

            self.db.add(invoice)
            self.db.commit()
            self.db.refresh(invoice)
            return invoice

        except IntegrityError as e:
            self.db.rollback()
            if "invoice_number" in str(e):
                raise ConflictError(
                    f"Invoice number {invoice_data.get('invoice_number')} already exists"
                )
            raise ConflictError("Invoice creation failed due to data conflict")

    def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        """Get invoice by ID."""
        return (
            self.db.query(Invoice)
            .filter(and_(Invoice.id == invoice_id, Invoice.tenant_id == self.tenant_id))
            .first()
        )

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        return (
            self.db.query(Invoice)
            .filter(
                and_(
                    Invoice.invoice_number == invoice_number,
                    Invoice.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_invoices(
        self,
        customer_id: Optional[UUID] = None,
        status: Optional[InvoiceStatus] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Invoice]:
        """List invoices with filtering."""
        query = self.db.query(Invoice).filter(Invoice.tenant_id == self.tenant_id)

        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)
        if status:
            query = query.filter(Invoice.status == status)
        if due_date_from:
            query = query.filter(Invoice.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(Invoice.due_date <= due_date_to)

        return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

    def update_status(
        self, invoice_id: UUID, status: InvoiceStatus
    ) -> Optional[Invoice]:
        """Update invoice status."""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None

        invoice.status = status
        invoice.updated_at = datetime.utcnow()

        if status == InvoiceStatus.PAID:
            invoice.paid_date = datetime.utcnow()

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def update_amounts(
        self, invoice_id: UUID, amount_paid: Decimal
    ) -> Optional[Invoice]:
        """Update invoice payment amounts."""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None

        invoice.amount_paid += amount_paid
        invoice.amount_due = invoice.total_amount - invoice.amount_paid

        # Update status based on payment
        if invoice.amount_due <= 0:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_date = datetime.utcnow()
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIAL_PAID

        invoice.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        today = date.today()
        count = (
            self.db.query(func.count(Invoice.id))
            .filter(
                and_(
                    Invoice.tenant_id == self.tenant_id,
                    func.date(Invoice.created_at) == today,
                )
            )
            .scalar()
        )

        return f"INV-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class InvoiceLineItemRepository:
    """Repository for invoice line item database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, line_item_data: Dict[str, Any]) -> InvoiceLineItem:
        """Create a new invoice line item."""
        line_item = InvoiceLineItem(
            id=uuid4(), tenant_id=self.tenant_id, **line_item_data
        )

        self.db.add(line_item)
        self.db.commit()
        self.db.refresh(line_item)
        return line_item

    def list_by_invoice(self, invoice_id: UUID) -> List[InvoiceLineItem]:
        """List line items for an invoice."""
        return (
            self.db.query(InvoiceLineItem)
            .filter(
                and_(
                    InvoiceLineItem.invoice_id == invoice_id,
                    InvoiceLineItem.tenant_id == self.tenant_id,
                )
            )
            .order_by(InvoiceLineItem.line_number)
            .all()
        )


class PaymentRepository:
    """Repository for payment database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, payment_data: Dict[str, Any]) -> Payment:
        """Create a new payment."""
        try:
            # Generate payment reference if not provided
            if not payment_data.get("payment_reference"):
                payment_data["payment_reference"] = self._generate_payment_reference()

            payment = Payment(id=uuid4(), tenant_id=self.tenant_id, **payment_data)

            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            return payment

        except IntegrityError as e:
            self.db.rollback()
            if "payment_reference" in str(e):
                raise ConflictError(
                    f"Payment reference {payment_data.get('payment_reference')} already exists"
                )
            raise ConflictError("Payment creation failed due to data conflict")

    def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """Get payment by ID."""
        return (
            self.db.query(Payment)
            .filter(and_(Payment.id == payment_id, Payment.tenant_id == self.tenant_id))
            .first()
        )

    def get_by_reference(self, payment_reference: str) -> Optional[Payment]:
        """Get payment by reference."""
        return (
            self.db.query(Payment)
            .filter(
                and_(
                    Payment.payment_reference == payment_reference,
                    Payment.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_payments(
        self,
        customer_id: Optional[UUID] = None,
        invoice_id: Optional[UUID] = None,
        status: Optional[PaymentStatus] = None,
        payment_method: Optional[PaymentMethod] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Payment]:
        """List payments with filtering."""
        query = self.db.query(Payment).filter(Payment.tenant_id == self.tenant_id)

        if customer_id:
            query = query.filter(Payment.customer_id == customer_id)
        if invoice_id:
            query = query.filter(Payment.invoice_id == invoice_id)
        if status:
            query = query.filter(Payment.status == status)
        if payment_method:
            query = query.filter(Payment.payment_method == payment_method)

        return (
            query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()
        )

    def update_status(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        gateway_response: Optional[Dict] = None,
    ) -> Optional[Payment]:
        """Update payment status."""
        payment = self.get_by_id(payment_id)
        if not payment:
            return None

        payment.status = status
        payment.updated_at = datetime.utcnow()

        if gateway_response:
            payment.gateway_response = gateway_response

        if status == PaymentStatus.COMPLETED:
            payment.processed_date = datetime.utcnow()

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def _generate_payment_reference(self) -> str:
        """Generate unique payment reference."""
        today = date.today()
        count = (
            self.db.query(func.count(Payment.id))
            .filter(
                and_(
                    Payment.tenant_id == self.tenant_id,
                    func.date(Payment.created_at) == today,
                )
            )
            .scalar()
        )

        return f"PAY-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class SubscriptionRepository:
    """Repository for subscription database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, subscription_data: Dict[str, Any]) -> Subscription:
        """Create a new subscription."""
        subscription = Subscription(
            id=uuid4(), tenant_id=self.tenant_id, **subscription_data
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID."""
        return (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.id == subscription_id,
                    Subscription.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_by_customer(self, customer_id: UUID) -> List[Subscription]:
        """List subscriptions for a customer."""
        return (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.customer_id == customer_id,
                    Subscription.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

    def list_active_subscriptions(self) -> List[Subscription]:
        """List all active subscriptions."""
        return (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.is_active == True,
                    Subscription.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

    def update(
        self, subscription_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Subscription]:
        """Update subscription."""
        subscription = self.get_by_id(subscription_id)
        if not subscription:
            return None

        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        subscription.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(subscription)
        return subscription


class CreditNoteRepository:
    """Repository for credit note database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, credit_note_data: Dict[str, Any]) -> CreditNote:
        """Create a new credit note."""
        try:
            # Generate credit note number if not provided
            if not credit_note_data.get("credit_note_number"):
                credit_note_data["credit_note_number"] = (
                    self._generate_credit_note_number()
                )

            credit_note = CreditNote(
                id=uuid4(), tenant_id=self.tenant_id, **credit_note_data
            )

            self.db.add(credit_note)
            self.db.commit()
            self.db.refresh(credit_note)
            return credit_note

        except IntegrityError as e:
            self.db.rollback()
            if "credit_note_number" in str(e):
                raise ConflictError(
                    f"Credit note number {credit_note_data.get('credit_note_number')} already exists"
                )
            raise ConflictError("Credit note creation failed due to data conflict")

    def get_by_id(self, credit_note_id: UUID) -> Optional[CreditNote]:
        """Get credit note by ID."""
        return (
            self.db.query(CreditNote)
            .filter(
                and_(
                    CreditNote.id == credit_note_id,
                    CreditNote.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_by_customer(self, customer_id: UUID) -> List[CreditNote]:
        """List credit notes for a customer."""
        return (
            self.db.query(CreditNote)
            .filter(
                and_(
                    CreditNote.customer_id == customer_id,
                    CreditNote.tenant_id == self.tenant_id,
                )
            )
            .order_by(CreditNote.created_at.desc())
            .all()
        )

    def _generate_credit_note_number(self) -> str:
        """Generate unique credit note number."""
        today = date.today()
        count = (
            self.db.query(func.count(CreditNote.id))
            .filter(
                and_(
                    CreditNote.tenant_id == self.tenant_id,
                    func.date(CreditNote.created_at) == today,
                )
            )
            .scalar()
        )

        return f"CN-{today.strftime('%Y%m%d')}-{count + 1:04d}"
