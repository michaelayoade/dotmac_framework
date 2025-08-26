"""Unit tests for billing service layer."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4, UUID

from dotmac_isp.modules.billing.service import BillingService
from dotmac_isp.modules.billing import schemas
from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceLineItem, Payment, CreditNote, Subscription,
    InvoiceStatus, PaymentStatus, PaymentMethod, BillingCycle
)
from dotmac_isp.shared.exceptions import (
    ServiceError, NotFoundError, ValidationError, ConflictError
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = Mock()
    settings.tenant_id = str(uuid4())
    return settings


@pytest.fixture
def billing_service(mock_db, mock_settings):
    """Billing service instance with mocked dependencies."""
    with patch('dotmac_isp.modules.billing.service.get_settings', return_value=mock_settings):
        service = BillingService(mock_db, tenant_id=mock_settings.tenant_id)
        
        # Mock repositories
        service.invoice_repo = Mock()
        service.line_item_repo = Mock()
        service.payment_repo = Mock()
        service.subscription_repo = Mock()
        service.credit_note_repo = Mock()
        
        return service


@pytest.fixture
def sample_invoice_create():
    """Sample invoice creation data."""
    return schemas.InvoiceCreate(
        customer_id=uuid4(),
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        line_items=[
            schemas.InvoiceLineItemCreate(
                description="Internet Service",
                quantity=Decimal('1.0'),
                unit_price=Decimal('99.99')
            ),
            schemas.InvoiceLineItemCreate(
                description="Setup Fee",
                quantity=Decimal('1.0'),
                unit_price=Decimal('50.00')
            )
        ],
        tax_rate=Decimal('0.085'),
        discount_rate=Decimal('0.10')
    )


@pytest.mark.unit
@pytest.mark.billing
class TestBillingServiceInvoiceOperations:
    """Test billing service invoice operations."""

    async def test_create_invoice_success(self, billing_service, sample_invoice_create):
        """Test successful invoice creation."""
        # Mock repository responses
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = uuid4()
        mock_invoice.total_amount = Decimal('149.99')
        
        billing_service.invoice_repo.create.return_value = mock_invoice
        billing_service.line_item_repo.create_batch.return_value = []
        
        result = await billing_service.create_invoice(sample_invoice_create)
        
        assert result == mock_invoice
        billing_service.invoice_repo.create.assert_called_once()
        billing_service.line_item_repo.create_batch.assert_called_once()

    async def test_create_invoice_calculation(self, billing_service):
        """Test invoice amount calculations."""
        invoice_data = schemas.InvoiceCreate(
            customer_id=uuid4(),
            line_items=[
                schemas.InvoiceLineItemCreate(
                    description="Service",
                    quantity=Decimal('1.0'),
                    unit_price=Decimal('100.00')
                )
            ],
            tax_rate=Decimal('0.085'),  # 8.5%
            discount_rate=Decimal('0.10')  # 10%
        )
        
        # Mock successful creation
        mock_invoice = Mock(spec=Invoice)
        billing_service.invoice_repo.create.return_value = mock_invoice
        billing_service.line_item_repo.create_batch.return_value = []
        
        await billing_service.create_invoice(invoice_data)
        
        # Verify calculation was called with correct amounts
        create_call = billing_service.invoice_repo.create.call_args[0][0]
        
        # Subtotal: 100.00
        # Tax: 100.00 * 0.085 = 8.50
        # Discount: 100.00 * 0.10 = 10.00
        # Total: 100.00 + 8.50 - 10.00 = 98.50
        assert create_call['subtotal'] == Decimal('100.00')
        assert create_call['tax_amount'] == Decimal('8.50')
        assert create_call['discount_amount'] == Decimal('10.00')
        assert create_call['total_amount'] == Decimal('98.50')

    async def test_create_invoice_repository_error(self, billing_service, sample_invoice_create):
        """Test invoice creation with repository error."""
        billing_service.invoice_repo.create.side_effect = ConflictError("Duplicate invoice number")
        
        with pytest.raises(ConflictError):
            await billing_service.create_invoice(sample_invoice_create)

    async def test_get_invoice_by_id(self, billing_service):
        """Test retrieving invoice by ID."""
        invoice_id = uuid4()
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = invoice_id
        
        billing_service.invoice_repo.get_by_id.return_value = mock_invoice
        
        result = await billing_service.get_invoice(invoice_id)
        
        assert result == mock_invoice
        billing_service.invoice_repo.get_by_id.assert_called_once_with(invoice_id)

    async def test_get_invoice_not_found(self, billing_service):
        """Test retrieving non-existent invoice."""
        invoice_id = uuid4()
        billing_service.invoice_repo.get_by_id.side_effect = NotFoundError("Invoice not found")
        
        with pytest.raises(NotFoundError):
            await billing_service.get_invoice(invoice_id)

    async def test_update_invoice_status(self, billing_service):
        """Test updating invoice status."""
        invoice_id = uuid4()
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.status = InvoiceStatus.SENT
        
        billing_service.invoice_repo.update.return_value = mock_invoice
        
        result = await billing_service.update_invoice_status(invoice_id, InvoiceStatus.SENT)
        
        assert result == mock_invoice
        billing_service.invoice_repo.update.assert_called_once_with(
            invoice_id, {'status': InvoiceStatus.SENT}
        )

    async def test_get_customer_invoices(self, billing_service):
        """Test retrieving customer invoices."""
        customer_id = uuid4()
        mock_invoices = [Mock(spec=Invoice), Mock(spec=Invoice)]
        
        billing_service.invoice_repo.get_by_customer_id.return_value = mock_invoices
        
        result = await billing_service.get_customer_invoices(customer_id)
        
        assert result == mock_invoices
        billing_service.invoice_repo.get_by_customer_id.assert_called_once_with(customer_id)

    async def test_get_overdue_invoices(self, billing_service):
        """Test retrieving overdue invoices."""
        mock_invoices = [Mock(spec=Invoice)]
        
        billing_service.invoice_repo.get_overdue_invoices.return_value = mock_invoices
        
        result = await billing_service.get_overdue_invoices()
        
        assert result == mock_invoices
        billing_service.invoice_repo.get_overdue_invoices.assert_called_once()


@pytest.mark.unit
@pytest.mark.billing
class TestBillingServicePaymentOperations:
    """Test billing service payment operations."""

    async def test_process_payment_success(self, billing_service):
        """Test successful payment processing."""
        payment_data = schemas.PaymentCreate(
            invoice_id=uuid4(),
            amount=Decimal('108.50'),
            payment_method=PaymentMethod.CREDIT_CARD,
            transaction_id="TXN123456"
        )
        
        mock_payment = Mock(spec=Payment)
        mock_payment.id = uuid4()
        mock_payment.status = PaymentStatus.COMPLETED
        
        # Mock invoice exists
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.total_amount = Decimal('108.50')
        billing_service.invoice_repo.get_by_id.return_value = mock_invoice
        
        # Mock payment creation
        billing_service.payment_repo.create.return_value = mock_payment
        
        # Mock external payment processing
        with patch.object(billing_service, '_process_external_payment', 
                         return_value={'status': 'success', 'transaction_id': 'TXN123456'}):
            result = await billing_service.process_payment(payment_data)
            
            assert result == mock_payment
            billing_service.payment_repo.create.assert_called_once()

    async def test_process_payment_insufficient_amount(self, billing_service):
        """Test payment processing with insufficient amount."""
        payment_data = schemas.PaymentCreate(
            invoice_id=uuid4(),
            amount=Decimal('50.00'),  # Less than invoice total
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.total_amount = Decimal('108.50')
        billing_service.invoice_repo.get_by_id.return_value = mock_invoice
        
        with pytest.raises(ValidationError) as exc_info:
            await billing_service.process_payment(payment_data)
        
        assert "insufficient" in str(exc_info.value).lower()

    async def test_process_payment_external_failure(self, billing_service):
        """Test payment processing with external payment failure."""
        payment_data = schemas.PaymentCreate(
            invoice_id=uuid4(),
            amount=Decimal('108.50'),
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.total_amount = Decimal('108.50')
        billing_service.invoice_repo.get_by_id.return_value = mock_invoice
        
        # Mock external payment failure
        with patch.object(billing_service, '_process_external_payment', 
                         return_value={'status': 'failed', 'error': 'Card declined'}):
            with pytest.raises(ServiceError) as exc_info:
                await billing_service.process_payment(payment_data)
            
            assert "payment failed" in str(exc_info.value).lower()

    async def test_get_invoice_payments(self, billing_service):
        """Test retrieving payments for an invoice."""
        invoice_id = uuid4()
        mock_payments = [Mock(spec=Payment), Mock(spec=Payment)]
        
        billing_service.payment_repo.get_by_invoice_id.return_value = mock_payments
        
        result = await billing_service.get_invoice_payments(invoice_id)
        
        assert result == mock_payments
        billing_service.payment_repo.get_by_invoice_id.assert_called_once_with(invoice_id)

    async def test_refund_payment_success(self, billing_service):
        """Test successful payment refund."""
        payment_id = uuid4()
        refund_amount = Decimal('54.25')
        
        mock_payment = Mock(spec=Payment)
        mock_payment.amount = Decimal('108.50')
        mock_payment.status = PaymentStatus.COMPLETED
        
        billing_service.payment_repo.get_by_id.return_value = mock_payment
        billing_service.payment_repo.update.return_value = mock_payment
        
        # Mock external refund processing
        with patch.object(billing_service, '_process_external_refund',
                         return_value={'status': 'success', 'refund_id': 'REF123'}):
            result = await billing_service.refund_payment(payment_id, refund_amount)
            
            assert result == mock_payment
            billing_service.payment_repo.update.assert_called_once()

    async def test_refund_payment_invalid_amount(self, billing_service):
        """Test payment refund with invalid amount."""
        payment_id = uuid4()
        refund_amount = Decimal('200.00')  # More than payment amount
        
        mock_payment = Mock(spec=Payment)
        mock_payment.amount = Decimal('108.50')
        billing_service.payment_repo.get_by_id.return_value = mock_payment
        
        with pytest.raises(ValidationError) as exc_info:
            await billing_service.refund_payment(payment_id, refund_amount)
        
        assert "exceeds" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.billing
class TestBillingServiceSubscriptionOperations:
    """Test billing service subscription operations."""

    async def test_create_subscription(self, billing_service):
        """Test subscription creation."""
        subscription_data = schemas.SubscriptionCreate(
            customer_id=uuid4(),
            service_plan_id=uuid4(),
            billing_cycle=BillingCycle.MONTHLY,
            amount=Decimal('99.99'),
            start_date=date.today()
        )
        
        mock_subscription = Mock(spec=Subscription)
        mock_subscription.id = uuid4()
        
        billing_service.subscription_repo.create.return_value = mock_subscription
        
        result = await billing_service.create_subscription(subscription_data)
        
        assert result == mock_subscription
        billing_service.subscription_repo.create.assert_called_once()

    async def test_get_customer_subscriptions(self, billing_service):
        """Test retrieving customer subscriptions."""
        customer_id = uuid4()
        mock_subscriptions = [Mock(spec=Subscription)]
        
        billing_service.subscription_repo.get_by_customer_id.return_value = mock_subscriptions
        
        result = await billing_service.get_customer_subscriptions(customer_id)
        
        assert result == mock_subscriptions

    async def test_cancel_subscription(self, billing_service):
        """Test subscription cancellation."""
        subscription_id = uuid4()
        mock_subscription = Mock(spec=Subscription)
        mock_subscription.status = "cancelled"
        
        billing_service.subscription_repo.get_by_id.return_value = mock_subscription
        billing_service.subscription_repo.update.return_value = mock_subscription
        
        result = await billing_service.cancel_subscription(subscription_id)
        
        assert result == mock_subscription
        billing_service.subscription_repo.update.assert_called_once()

    async def test_process_recurring_billing(self, billing_service):
        """Test recurring billing processing."""
        billing_date = date.today()
        
        mock_subscriptions = [
            Mock(spec=Subscription),
            Mock(spec=Subscription)
        ]
        
        billing_service.subscription_repo.get_subscriptions_for_billing.return_value = mock_subscriptions
        
        # Mock invoice creation for each subscription
        billing_service.invoice_repo.create.side_effect = [
            Mock(spec=Invoice),
            Mock(spec=Invoice)
        ]
        
        result = await billing_service.process_recurring_billing(billing_date)
        
        assert len(result) == 2
        assert billing_service.invoice_repo.create.call_count == 2


@pytest.mark.unit
@pytest.mark.billing
class TestBillingServiceCreditNoteOperations:
    """Test billing service credit note operations."""

    async def test_create_credit_note(self, billing_service):
        """Test credit note creation."""
        credit_note_data = schemas.CreditNoteCreate(
            invoice_id=uuid4(),
            amount=Decimal('25.00'),
            reason="Service credit for downtime"
        )
        
        mock_credit_note = Mock(spec=CreditNote)
        mock_credit_note.id = uuid4()
        
        # Mock invoice exists
        mock_invoice = Mock(spec=Invoice)
        billing_service.invoice_repo.get_by_id.return_value = mock_invoice
        
        billing_service.credit_note_repo.create.return_value = mock_credit_note
        
        result = await billing_service.create_credit_note(credit_note_data)
        
        assert result == mock_credit_note
        billing_service.credit_note_repo.create.assert_called_once()

    async def test_get_invoice_credit_notes(self, billing_service):
        """Test retrieving credit notes for an invoice."""
        invoice_id = uuid4()
        mock_credit_notes = [Mock(spec=CreditNote)]
        
        billing_service.credit_note_repo.get_by_invoice_id.return_value = mock_credit_notes
        
        result = await billing_service.get_invoice_credit_notes(invoice_id)
        
        assert result == mock_credit_notes


@pytest.mark.unit
@pytest.mark.billing
class TestBillingServiceUtilities:
    """Test billing service utility methods."""

    def test_calculate_tax(self, billing_service):
        """Test tax calculation."""
        subtotal = Decimal('100.00')
        tax_rate = Decimal('0.085')  # 8.5%
        
        result = billing_service._calculate_tax(subtotal, tax_rate)
        
        assert result == Decimal('8.50')

    def test_calculate_discount(self, billing_service):
        """Test discount calculation."""
        subtotal = Decimal('100.00')
        discount_rate = Decimal('0.10')  # 10%
        
        result = billing_service._calculate_discount(subtotal, discount_rate)
        
        assert result == Decimal('10.00')

    def test_calculate_line_item_total(self, billing_service):
        """Test line item total calculation."""
        quantity = Decimal('2.5')
        unit_price = Decimal('39.99')
        
        result = billing_service._calculate_line_item_total(quantity, unit_price)
        
        assert result == Decimal('99.975')  # 2.5 * 39.99

    async def test_validate_payment_amount(self, billing_service):
        """Test payment amount validation."""
        invoice_total = Decimal('108.50')
        
        # Valid amount
        billing_service._validate_payment_amount(Decimal('108.50'), invoice_total)
        
        # Invalid amount (too high)
        with pytest.raises(ValidationError):
            billing_service._validate_payment_amount(Decimal('200.00'), invoice_total)
        
        # Invalid amount (negative)
        with pytest.raises(ValidationError):
            billing_service._validate_payment_amount(Decimal('-10.00'), invoice_total)

    async def test_generate_invoice_pdf(self, billing_service):
        """Test invoice PDF generation."""
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = uuid4()
        
        with patch.object(billing_service, '_create_pdf_document') as mock_pdf:
            mock_pdf.return_value = b"PDF content"
            
            result = await billing_service.generate_invoice_pdf(mock_invoice)
            
            assert isinstance(result, bytes)
            assert result == b"PDF content"
            mock_pdf.assert_called_once()

    async def test_send_invoice_email(self, billing_service):
        """Test invoice email sending."""
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = uuid4()
        customer_email = "customer@example.com"
        
        with patch.object(billing_service, '_send_email') as mock_email:
            mock_email.return_value = True
            
            result = await billing_service.send_invoice_email(mock_invoice, customer_email)
            
            assert result is True
            mock_email.assert_called_once()


@pytest.mark.unit
@pytest.mark.billing  
class TestBillingServiceErrorHandling:
    """Test billing service error handling."""

    async def test_service_initialization_error(self, mock_db):
        """Test service initialization with invalid tenant ID."""
        with pytest.raises(ValueError):
            BillingService(mock_db, tenant_id="invalid-uuid")

    async def test_repository_error_propagation(self, billing_service):
        """Test that repository errors are properly propagated."""
        invoice_id = uuid4()
        billing_service.invoice_repo.get_by_id.side_effect = NotFoundError("Invoice not found")
        
        with pytest.raises(NotFoundError):
            await billing_service.get_invoice(invoice_id)

    async def test_calculation_error_handling(self, billing_service):
        """Test handling of calculation errors."""
        # Test with invalid decimal values
        with pytest.raises(ValidationError):
            billing_service._calculate_tax("invalid", Decimal('0.085')

    async def test_concurrent_operation_handling(self, billing_service):
        """Test handling of concurrent operations."""
        payment_data = schemas.PaymentCreate(
            invoice_id=uuid4(),
            amount=Decimal('108.50'),
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        # Mock concurrent modification error
        billing_service.invoice_repo.get_by_id.return_value = Mock(spec=Invoice)
        billing_service.payment_repo.create.side_effect = ConflictError("Concurrent modification")
        
        with pytest.raises(ConflictError):
            await billing_service.process_payment(payment_data)