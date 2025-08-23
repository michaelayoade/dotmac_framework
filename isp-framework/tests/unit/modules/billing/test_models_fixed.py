"""Unit tests for billing models with proper test setup."""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4, UUID

# Import test factories
from tests.factories.billing_factories import (
    InvoiceFactory, 
    InvoiceLineItemFactory,
    PaymentFactory,
    SubscriptionFactory,
    BillingAccountFactory,
    CreditNoteFactory,
    ReceiptFactory,
    LateFeeFactory
)

# Import the enums for testing
from dotmac_isp.modules.billing.models import (
    InvoiceStatus, PaymentStatus, PaymentMethod, BillingCycle, TaxType
)


@pytest.mark.unit
@pytest.mark.billing
class TestInvoiceModelWithFactory:
    """Test Invoice model using test factories."""
    
    def test_invoice_creation_with_factory(self):
        """Test invoice creation using factory."""
        # Create invoice data using factory
        invoice_data = InvoiceFactory.build()
        
        # Verify factory generates proper data structure
        assert invoice_data.invoice_number is not None
        assert invoice_data.customer_id is not None
        assert isinstance(invoice_data.subtotal, Decimal)
        assert isinstance(invoice_data.tax_amount, Decimal)
        assert isinstance(invoice_data.total_amount, Decimal)
        assert invoice_data.total_amount >= invoice_data.subtotal
        
    def test_invoice_status_enum(self):
        """Test invoice status enumeration values."""
        assert InvoiceStatus.DRAFT.value == "draft"
        assert InvoiceStatus.PENDING.value == "pending"
        assert InvoiceStatus.SENT.value == "sent"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.OVERDUE.value == "overdue"
        assert InvoiceStatus.CANCELLED.value == "cancelled"
        assert InvoiceStatus.REFUNDED.value == "refunded"

    def test_invoice_amount_calculations_with_factory(self):
        """Test invoice amount calculations using factory."""
        invoice_data = InvoiceFactory.build(
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('85.00'),
            discount_amount=Decimal('50.00'),
        )
        
        # Total is calculated in factory
        expected_total = invoice_data.subtotal + invoice_data.tax_amount - invoice_data.discount_amount
        assert invoice_data.total_amount == expected_total

    def test_invoice_dates_with_factory(self):
        """Test invoice date handling using factory."""
        invoice_data = InvoiceFactory.build()
        
        assert invoice_data.invoice_date is not None
        assert invoice_data.due_date is not None
        assert invoice_data.due_date > invoice_data.invoice_date

    def test_paid_invoice_factory(self):
        """Test paid invoice factory method."""
        invoice_data = InvoiceFactory.build_paid()
        
        assert invoice_data.status == "paid"
        assert invoice_data.paid_date is not None
        assert invoice_data.paid_amount == invoice_data.total_amount

    def test_overdue_invoice_factory(self):
        """Test overdue invoice factory method."""
        invoice_data = InvoiceFactory.build_overdue()
        
        assert invoice_data.status == "overdue"
        assert invoice_data.due_date < date.today()
        assert invoice_data.invoice_date < invoice_data.due_date


@pytest.mark.unit
@pytest.mark.billing
class TestInvoiceLineItemModelWithFactory:
    """Test InvoiceLineItem model using test factories."""

    def test_line_item_creation_with_factory(self):
        """Test line item creation using factory."""
        line_item_data = InvoiceLineItemFactory.build()
        
        assert line_item_data.description is not None
        assert isinstance(line_item_data.quantity, Decimal)
        assert isinstance(line_item_data.unit_price, Decimal)
        assert isinstance(line_item_data.line_total, Decimal)
        assert line_item_data.line_total == line_item_data.quantity * line_item_data.unit_price

    def test_line_item_tax_calculations(self):
        """Test line item tax calculations."""
        line_item_data = InvoiceLineItemFactory.build(
            quantity=Decimal('2.0'),
            unit_price=Decimal('49.99'),
            tax_rate=Decimal('0.0850')
        )
        
        expected_line_total = line_item_data.quantity * line_item_data.unit_price
        expected_tax = expected_line_total * line_item_data.tax_rate
        
        assert line_item_data.line_total == expected_line_total
        assert line_item_data.tax_amount == expected_tax


@pytest.mark.unit
@pytest.mark.billing
class TestPaymentModelWithFactory:
    """Test Payment model using test factories."""

    def test_payment_creation_with_factory(self):
        """Test payment creation using factory."""
        payment_data = PaymentFactory.build()
        
        assert payment_data.payment_number is not None
        assert payment_data.invoice_id is not None
        assert isinstance(payment_data.amount, Decimal)
        assert payment_data.payment_method is not None
        assert payment_data.status == "completed"

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

    def test_failed_payment_factory(self):
        """Test failed payment factory method."""
        payment_data = PaymentFactory.build_failed()
        
        assert payment_data.status == "failed"
        assert payment_data.failure_reason is not None
        assert payment_data.transaction_id is None

    def test_pending_payment_factory(self):
        """Test pending payment factory method."""
        payment_data = PaymentFactory.build_pending()
        
        assert payment_data.status == "pending"
        assert payment_data.transaction_id is None


@pytest.mark.unit
@pytest.mark.billing
class TestSubscriptionModelWithFactory:
    """Test Subscription model using test factories."""

    def test_subscription_creation_with_factory(self):
        """Test subscription creation using factory."""
        subscription_data = SubscriptionFactory.build()
        
        assert subscription_data.customer_id is not None
        assert subscription_data.service_instance_id is not None
        assert subscription_data.billing_cycle == "monthly"
        assert isinstance(subscription_data.amount, Decimal)
        assert subscription_data.is_active is True
        assert subscription_data.next_billing_date > subscription_data.start_date

    def test_billing_cycle_enum(self):
        """Test billing cycle enumeration."""
        assert BillingCycle.MONTHLY.value == "monthly"
        assert BillingCycle.QUARTERLY.value == "quarterly"
        assert BillingCycle.ANNUALLY.value == "annually"
        assert BillingCycle.ONE_TIME.value == "one_time"

    def test_quarterly_subscription_factory(self):
        """Test quarterly subscription factory method."""
        subscription_data = SubscriptionFactory.build_quarterly()
        
        assert subscription_data.billing_cycle == "quarterly"
        assert subscription_data.next_billing_date > date.today() + timedelta(days=80)

    def test_annual_subscription_factory(self):
        """Test annual subscription factory method."""
        subscription_data = SubscriptionFactory.build_annual()
        
        assert subscription_data.billing_cycle == "annually"
        assert subscription_data.next_billing_date > date.today() + timedelta(days=300)


@pytest.mark.unit
@pytest.mark.billing
class TestBillingAccountModelWithFactory:
    """Test BillingAccount model using test factories."""

    def test_billing_account_creation_with_factory(self):
        """Test billing account creation using factory."""
        account_data = BillingAccountFactory.build()
        
        assert account_data.customer_id is not None
        assert account_data.account_name is not None
        assert account_data.payment_method is not None
        assert account_data.is_verified is True
        assert account_data.is_active is True

    def test_credit_card_account_details(self):
        """Test credit card account details."""
        account_data = BillingAccountFactory.build(payment_method="credit_card")
        
        assert account_data.payment_method == "credit_card"
        assert account_data.card_last_four is not None
        assert account_data.card_expiry is not None
        assert account_data.stripe_payment_method_id is not None


@pytest.mark.unit
@pytest.mark.billing
class TestCreditNoteModelWithFactory:
    """Test CreditNote model using test factories."""

    def test_credit_note_creation_with_factory(self):
        """Test credit note creation using factory."""
        credit_note_data = CreditNoteFactory.build()
        
        assert credit_note_data.credit_note_number is not None
        assert credit_note_data.customer_id is not None
        assert isinstance(credit_note_data.amount, Decimal)
        assert credit_note_data.reason is not None
        assert credit_note_data.credit_date is not None


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
class TestReceiptModelWithFactory:
    """Test Receipt model using test factories."""

    def test_receipt_creation_with_factory(self):
        """Test receipt creation using factory."""
        receipt_data = ReceiptFactory.build()
        
        assert receipt_data.receipt_number is not None
        assert receipt_data.payment_id is not None
        assert isinstance(receipt_data.amount, Decimal)
        assert receipt_data.customer_name is not None
        assert receipt_data.invoice_number is not None


@pytest.mark.unit
@pytest.mark.billing
class TestLateFeeModelWithFactory:
    """Test LateFee model using test factories."""

    def test_late_fee_creation_with_factory(self):
        """Test late fee creation using factory."""
        late_fee_data = LateFeeFactory.build()
        
        assert late_fee_data.invoice_id is not None
        assert late_fee_data.customer_id is not None
        assert isinstance(late_fee_data.fee_amount, Decimal)
        assert late_fee_data.fee_date is not None
        assert late_fee_data.days_overdue is not None
        assert late_fee_data.is_waived is False


@pytest.mark.unit
@pytest.mark.billing
class TestModelValidationWithFactory:
    """Test model validation using test factories."""

    def test_invoice_required_fields_with_factory(self):
        """Test that required fields are generated by factory."""
        invoice_data = InvoiceFactory.build()
        
        assert invoice_data.id is not None
        assert invoice_data.tenant_id is not None
        assert invoice_data.customer_id is not None
        assert invoice_data.invoice_number is not None

    def test_decimal_precision_handling(self):
        """Test decimal field precision handling."""
        invoice_data = InvoiceFactory.build()
        
        # All monetary fields should be Decimal type
        assert isinstance(invoice_data.subtotal, Decimal)
        assert isinstance(invoice_data.tax_amount, Decimal)
        assert isinstance(invoice_data.total_amount, Decimal)
        assert isinstance(invoice_data.discount_amount, Decimal)
        assert isinstance(invoice_data.paid_amount, Decimal)

    def test_uuid_fields_handling(self):
        """Test UUID field handling."""
        invoice_data = InvoiceFactory.build()
        
        # ID fields should be string representations of UUIDs
        assert isinstance(invoice_data.id, str)
        assert isinstance(invoice_data.tenant_id, str)
        assert isinstance(invoice_data.customer_id, str)
        
        # Should be valid UUID strings
        uuid4(invoice_data.id)  # Will raise ValueError if invalid
        uuid4(invoice_data.tenant_id)
        uuid4(invoice_data.customer_id)

    def test_tenant_isolation_with_factory(self):
        """Test tenant isolation using factory."""
        # Create multiple invoices with different tenants
        tenant_1 = "tenant_001"
        tenant_2 = "tenant_002"
        
        invoice_1 = InvoiceFactory.build(tenant_id=tenant_1)
        invoice_2 = InvoiceFactory.build(tenant_id=tenant_2)
        
        assert invoice_1.tenant_id == tenant_1
        assert invoice_2.tenant_id == tenant_2
        assert invoice_1.tenant_id != invoice_2.tenant_id

    def test_realistic_data_generation(self):
        """Test that factory generates realistic business data."""
        invoice_data = InvoiceFactory.build()
        
        # Invoice numbers should be properly formatted
        assert "INV-" in invoice_data.invoice_number
        
        # Monetary amounts should be reasonable
        assert Decimal('0') <= invoice_data.subtotal <= Decimal('10000')
        assert invoice_data.tax_amount >= Decimal('0')
        assert invoice_data.total_amount > Decimal('0')
        
        # Dates should be logical
        assert invoice_data.due_date > invoice_data.invoice_date