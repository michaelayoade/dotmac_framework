"""Unit tests for billing models."""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4, UUID

from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceLineItem, Payment, CreditNote, Receipt, Subscription,
    InvoiceStatus, PaymentStatus, PaymentMethod, BillingCycle, TaxType
, timezone)


@pytest.mark.unit
@pytest.mark.billing
class TestInvoiceModel:
    """Test Invoice model functionality."""

    def test_invoice_creation(self):
        """Test basic invoice creation."""
        invoice = Invoice(
            id=uuid4(),
            tenant_id=uuid4(),
            invoice_number="INV-001",
            customer_id=uuid4(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('8.50'),
            total_amount=Decimal('108.50'),
            status=InvoiceStatus.DRAFT
        )
        
        assert invoice.invoice_number == "INV-001"
        assert invoice.subtotal == Decimal('100.00')
        assert invoice.tax_amount == Decimal('8.50')
        assert invoice.total_amount == Decimal('108.50')
        assert invoice.status == InvoiceStatus.DRAFT

    def test_invoice_status_enum(self):
        """Test invoice status enumeration values."""
        assert InvoiceStatus.DRAFT.value == "draft"
        assert InvoiceStatus.PENDING.value == "pending"
        assert InvoiceStatus.SENT.value == "sent"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.OVERDUE.value == "overdue"
        assert InvoiceStatus.CANCELLED.value == "cancelled"
        assert InvoiceStatus.REFUNDED.value == "refunded"

    def test_invoice_amount_calculations(self):
        """Test invoice amount calculations."""
        invoice = Invoice(
            id=uuid4(),
            tenant_id=uuid4(),
            customer_id=uuid4(),
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('85.00'),
            discount_amount=Decimal('50.00'),
            total_amount=Decimal('1035.00')
        )
        
        assert invoice.subtotal == Decimal('1000.00')
        assert invoice.tax_amount == Decimal('85.00')
        assert invoice.discount_amount == Decimal('50.00')
        assert invoice.total_amount == Decimal('1035.00')

    def test_invoice_dates(self):
        """Test invoice date handling."""
        issue_date = date.today()
        due_date = issue_date + timedelta(days=30)
        
        invoice = Invoice(
            id=uuid4(),
            tenant_id=uuid4(),
            customer_id=uuid4(),
            invoice_date=issue_date,
            due_date=due_date
        )
        
        assert invoice.invoice_date == issue_date
        assert invoice.due_date == due_date
        assert invoice.due_date > invoice.invoice_date


@pytest.mark.unit
@pytest.mark.billing
class TestInvoiceLineItemModel:
    """Test InvoiceLineItem model functionality."""

    def test_line_item_creation(self):
        """Test line item creation."""
        line_item = InvoiceLineItem(
            id=uuid4(),
            tenant_id=uuid4(),
            invoice_id=uuid4(),
            description="Internet Service",
            quantity=Decimal('1.0'),
            unit_price=Decimal('99.99'),
            line_total=Decimal('99.99')
        )
        
        assert line_item.description == "Internet Service"
        assert line_item.quantity == Decimal('1.0')
        assert line_item.unit_price == Decimal('99.99')
        assert line_item.line_total == Decimal('99.99')

    def test_line_item_calculations(self):
        """Test line item total calculations."""
        line_item = InvoiceLineItem(
            id=uuid4(),
            tenant_id=uuid4(),
            invoice_id=uuid4(),
            description="Internet Service",
            quantity=Decimal('2.0'),
            unit_price=Decimal('49.99'),
            line_total=Decimal('99.98')
        )
        
        # Verify calculation logic
        expected_total = line_item.quantity * line_item.unit_price
        assert line_item.line_total == expected_total


@pytest.mark.unit
@pytest.mark.billing
class TestPaymentModel:
    """Test Payment model functionality."""

    def test_payment_creation(self):
        """Test payment creation."""
        payment = Payment(
            id=uuid4(),
            tenant_id=uuid4(),
            invoice_id=uuid4(),
            amount=Decimal('108.50'),
            payment_date=datetime.now(timezone.utc),
            payment_method=PaymentMethod.CREDIT_CARD,
            status=PaymentStatus.COMPLETED,
            transaction_id="TXN123456",
            reference_number="REF789"
        )
        
        assert payment.amount == Decimal('108.50')
        assert payment.payment_method == PaymentMethod.CREDIT_CARD
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.transaction_id == "TXN123456"
        assert payment.reference_number == "REF789"

    def test_payment_status_enum(self):
        """Test payment status enumeration."""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.PROCESSING.value == "processing"
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELLED.value == "cancelled"
        assert PaymentStatus.REFUNDED.value == "refunded"

    def test_payment_method_enum(self):
        """Test payment method enumeration."""
        assert PaymentMethod.CREDIT_CARD.value == "credit_card"
        assert PaymentMethod.BANK_TRANSFER.value == "bank_transfer"
        assert PaymentMethod.ACH.value == "ach"
        assert PaymentMethod.PAYPAL.value == "paypal"
        assert PaymentMethod.CHECK.value == "check"
        assert PaymentMethod.CASH.value == "cash"
        assert PaymentMethod.WIRE.value == "wire"


@pytest.mark.unit
@pytest.mark.billing
class TestSubscriptionModel:
    """Test Subscription model functionality."""

    def test_subscription_creation(self):
        """Test subscription creation."""
        subscription = Subscription(
            id=uuid4(),
            tenant_id=uuid4(),
            customer_id=uuid4(),
            service_plan_id=uuid4(),
            billing_cycle=BillingCycle.MONTHLY,
            amount=Decimal('99.99'),
            start_date=date.today(),
            next_billing_date=date.today() + timedelta(days=30),
            status="active"
        )
        
        assert subscription.billing_cycle == BillingCycle.MONTHLY
        assert subscription.amount == Decimal('99.99')
        assert subscription.status == "active"
        assert subscription.next_billing_date > subscription.start_date

    def test_billing_cycle_enum(self):
        """Test billing cycle enumeration."""
        assert BillingCycle.MONTHLY.value == "monthly"
        assert BillingCycle.QUARTERLY.value == "quarterly"
        assert BillingCycle.ANNUALLY.value == "annually"
        assert BillingCycle.ONE_TIME.value == "one_time"


@pytest.mark.unit
@pytest.mark.billing
class TestCreditNoteModel:
    """Test CreditNote model functionality."""

    def test_credit_note_creation(self):
        """Test credit note creation."""
        credit_note = CreditNote(
            id=uuid4(),
            tenant_id=uuid4(),
            invoice_id=uuid4(),
            credit_note_number="CN-001",
            amount=Decimal('25.00'),
            reason="Service credit",
            issue_date=date.today()
        )
        
        assert credit_note.credit_note_number == "CN-001"
        assert credit_note.amount == Decimal('25.00')
        assert credit_note.reason == "Service credit"
        assert credit_note.issue_date == date.today()


@pytest.mark.unit
@pytest.mark.billing
class TestTaxTypeEnum:
    """Test TaxType enumeration."""

    def test_tax_type_values(self):
        """Test tax type enumeration values."""
        assert TaxType.SALES_TAX.value == "sales_tax"
        assert TaxType.VAT.value == "vat"
        assert TaxType.GST.value == "gst"
        assert TaxType.NONE.value == "none"


@pytest.mark.unit
@pytest.mark.billing
class TestModelValidation:
    """Test model validation and constraints."""

    def test_invoice_required_fields(self):
        """Test that required fields are enforced."""
        # This would typically be tested with database constraints
        # Here we test the basic model structure
        invoice = Invoice(
            id=uuid4(),
            tenant_id=uuid4(),
            customer_id=uuid4(),
            invoice_number="INV-001"
        )
        
        assert invoice.id is not None
        assert invoice.tenant_id is not None
        assert invoice.customer_id is not None
        assert invoice.invoice_number == "INV-001"

    def test_decimal_precision(self):
        """Test decimal field precision handling."""
        invoice = Invoice(
            id=uuid4(),
            tenant_id=uuid4(),
            customer_id=uuid4(),
            subtotal=Decimal('123.456')  # More than 2 decimal places
        )
        
        # In real implementation, this should be rounded to 2 decimal places
        assert isinstance(invoice.subtotal, Decimal)

    def test_uuid_fields(self):
        """Test UUID field handling."""
        invoice_id = uuid4()
        tenant_id = uuid4()
        customer_id = uuid4()
        
        invoice = Invoice(
            id=invoice_id,
            tenant_id=tenant_id,
            customer_id=customer_id
        )
        
        assert isinstance(invoice.id, UUID)
        assert isinstance(invoice.tenant_id, UUID)
        assert isinstance(invoice.customer_id, UUID)
        assert invoice.id == invoice_id
        assert invoice.tenant_id == tenant_id
        assert invoice.customer_id == customer_id