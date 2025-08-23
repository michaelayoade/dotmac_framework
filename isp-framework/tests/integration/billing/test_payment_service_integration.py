"""Integration tests for payment domain service."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.modules.billing.domain.payment_service import PaymentService
from dotmac_isp.modules.billing.repository import PaymentRepository, InvoiceRepository
from dotmac_isp.modules.billing import schemas
from dotmac_isp.modules.billing.models import PaymentStatus, PaymentMethod, InvoiceStatus, Invoice
from dotmac_isp.shared.exceptions import ValidationError, NotFoundError, ServiceError


@pytest.mark.integration
@pytest.mark.billing
@pytest.mark.payment
class TestPaymentServiceIntegration:
    """Integration tests for payment service with real database."""
    
    @pytest.fixture
    async def tenant_id(self):
        """Test tenant ID."""
        return uuid4()
    
    @pytest.fixture
    async def payment_service(self, db_session: AsyncSession, tenant_id):
        """Payment service instance with real repositories."""
        payment_repo = PaymentRepository(db_session, tenant_id)
        invoice_repo = InvoiceRepository(db_session, tenant_id)
        
        return PaymentService(
            payment_repo=payment_repo,
            invoice_repo=invoice_repo,
            tenant_id=tenant_id
        )
    
    @pytest.fixture
    async def sample_invoice(self, db_session: AsyncSession, tenant_id):
        """Create a sample invoice for testing."""
        invoice_repo = InvoiceRepository(db_session, tenant_id)
        
        invoice_data = {
            'customer_id': uuid4(),
            'invoice_number': f'INV-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
            'invoice_date': datetime.now().date(),
            'due_date': (datetime.now() + timedelta(days=30)).date(),
            'subtotal': Decimal('100.00'),
            'tax_amount': Decimal('8.50'),
            'discount_amount': Decimal('0.00'),
            'total_amount': Decimal('108.50'),
            'amount_paid': Decimal('0.00'),
            'amount_due': Decimal('108.50'),
            'status': InvoiceStatus.SENT,
            'currency': 'USD'
        }
        
        return invoice_repo.create(invoice_data)
    
    @pytest.fixture
    def sample_payment_data(self, sample_invoice):
        """Sample payment creation data."""
        return schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('108.50'),
            payment_method=PaymentMethod.CREDIT_CARD,
            reference_number='TEST-REF-123',
            notes='Test payment'
        )
    
    async def test_process_payment_credit_card_success(self, payment_service, sample_payment_data):
        """Test successful credit card payment processing."""
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_20240101_123456',
                'processor': 'stripe',
                'card_last4': '4242'
            }
            
            payment = await payment_service.process_payment(sample_payment_data)
            
            # Verify payment was created
            assert payment is not None
            assert payment.invoice_id == sample_payment_data.invoice_id
            assert payment.amount == sample_payment_data.amount
            assert payment.payment_method == PaymentMethod.CREDIT_CARD
            assert payment.status == PaymentStatus.COMPLETED
            assert payment.transaction_id == 'CC_20240101_123456'
            assert payment.reference_number == 'TEST-REF-123'
            assert payment.notes == 'Test payment'
            
            # Verify external payment was called
            mock_external.assert_called_once_with(sample_payment_data)
            
            # Verify invoice was updated
            invoice = payment_service.invoice_repo.get_by_id(sample_payment_data.invoice_id)
            assert invoice.amount_paid == Decimal('108.50')
            assert invoice.amount_due == Decimal('0.00')
            assert invoice.status == InvoiceStatus.PAID
            assert invoice.paid_date is not None
    
    async def test_process_payment_ach_success(self, payment_service, sample_invoice):
        """Test successful ACH payment processing."""
        payment_data = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('108.50'),
            payment_method=PaymentMethod.ACH,
            reference_number='ACH-REF-456'
        )
        
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'ACH_20240101_123456',
                'processor': 'plaid',
                'account_last4': '1234'
            }
            
            payment = await payment_service.process_payment(payment_data)
            
            assert payment.payment_method == PaymentMethod.ACH
            assert payment.transaction_id == 'ACH_20240101_123456'
            assert 'plaid' in payment.processor_response['processor']
    
    async def test_process_payment_external_failure(self, payment_service, sample_payment_data):
        """Test payment processing with external payment failure."""
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'failed',
                'error': 'Card declined'
            }
            
            with pytest.raises(ServiceError) as exc_info:
                await payment_service.process_payment(sample_payment_data)
            
            assert "Payment failed" in str(exc_info.value)
            assert "Card declined" in str(exc_info.value)
    
    async def test_process_payment_insufficient_amount(self, payment_service, sample_invoice):
        """Test payment processing with insufficient amount."""
        payment_data = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('50.00'),  # Less than invoice total
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await payment_service.process_payment(payment_data)
        
        assert "exceeds invoice total" in str(exc_info.value)
    
    async def test_process_payment_excessive_amount(self, payment_service, sample_invoice):
        """Test payment processing with amount exceeding invoice total."""
        payment_data = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('200.00'),  # More than invoice total
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await payment_service.process_payment(payment_data)
        
        assert "exceeds invoice total" in str(exc_info.value)
    
    async def test_process_payment_negative_amount(self, payment_service, sample_invoice):
        """Test payment processing with negative amount."""
        payment_data = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('-10.00'),  # Negative amount
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await payment_service.process_payment(payment_data)
        
        assert "greater than zero" in str(exc_info.value)
    
    async def test_process_payment_nonexistent_invoice(self, payment_service):
        """Test payment processing with non-existent invoice."""
        payment_data = schemas.PaymentCreate(
            invoice_id=uuid4(),  # Non-existent invoice
            amount=Decimal('100.00'),
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        with pytest.raises(NotFoundError) as exc_info:
            await payment_service.process_payment(payment_data)
        
        assert "Invoice not found" in str(exc_info.value)
    
    async def test_partial_payment_processing(self, payment_service, sample_invoice):
        """Test partial payment processing."""
        # Process first partial payment
        payment_data_1 = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('50.00'),  # Partial payment
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_PARTIAL_1'
            }
            
            payment1 = await payment_service.process_payment(payment_data_1)
            assert payment1.amount == Decimal('50.00')
            
            # Verify invoice updated correctly
            invoice = payment_service.invoice_repo.get_by_id(sample_invoice.id)
            assert invoice.amount_paid == Decimal('50.00')
            assert invoice.amount_due == Decimal('58.50')
            assert invoice.status == InvoiceStatus.SENT  # Still not fully paid
        
        # Process second partial payment to complete
        payment_data_2 = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('58.50'),  # Remaining balance
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_PARTIAL_2'
            }
            
            payment2 = await payment_service.process_payment(payment_data_2)
            assert payment2.amount == Decimal('58.50')
            
            # Verify invoice is now fully paid
            invoice = payment_service.invoice_repo.get_by_id(sample_invoice.id)
            assert invoice.amount_paid == Decimal('108.50')
            assert invoice.amount_due == Decimal('0.00')
            assert invoice.status == InvoiceStatus.PAID
            assert invoice.paid_date is not None
    
    async def test_refund_payment_success(self, payment_service, sample_payment_data):
        """Test successful payment refund."""
        # First create a payment
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_123456'
            }
            
            payment = await payment_service.process_payment(sample_payment_data)
        
        # Now refund the payment
        refund_amount = Decimal('54.25')  # Partial refund
        refund_reason = "Customer request"
        
        with patch.object(payment_service, '_process_external_refund') as mock_refund:
            mock_refund.return_value = {
                'status': 'success',
                'refund_id': 'REF_123456',
                'original_transaction_id': 'CC_123456'
            }
            
            refunded_payment = await payment_service.refund_payment(
                payment.id, refund_amount, refund_reason
            )
            
            # Verify refund was processed
            assert refunded_payment.status == PaymentStatus.REFUNDED
            assert refunded_payment.refund_amount == refund_amount
            assert refunded_payment.refund_reason == refund_reason
            assert refunded_payment.refund_transaction_id == 'REF_123456'
            assert refunded_payment.refund_date is not None
            
            # Verify external refund was called
            mock_refund.assert_called_once_with(payment, refund_amount, refund_reason)
            
            # Verify invoice payment status was updated
            invoice = payment_service.invoice_repo.get_by_id(sample_payment_data.invoice_id)
            expected_amount_paid = Decimal('108.50') - refund_amount  # 54.25
            expected_amount_due = Decimal('108.50') - expected_amount_paid  # 54.25
            
            assert invoice.amount_paid == expected_amount_paid
            assert invoice.amount_due == expected_amount_due
    
    async def test_refund_payment_excessive_amount(self, payment_service, sample_payment_data):
        """Test refund with amount exceeding payment amount."""
        # First create a payment
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_123456'
            }
            
            payment = await payment_service.process_payment(sample_payment_data)
        
        # Try to refund more than payment amount
        excessive_refund = Decimal('200.00')
        
        with pytest.raises(ValidationError) as exc_info:
            await payment_service.refund_payment(payment.id, excessive_refund, "Test refund")
        
        assert "exceeds payment amount" in str(exc_info.value)
    
    async def test_refund_payment_external_failure(self, payment_service, sample_payment_data):
        """Test refund processing with external refund failure."""
        # First create a payment
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_123456'
            }
            
            payment = await payment_service.process_payment(sample_payment_data)
        
        # Mock external refund failure
        with patch.object(payment_service, '_process_external_refund') as mock_refund:
            mock_refund.return_value = {
                'status': 'failed',
                'error': 'Refund not allowed'
            }
            
            with pytest.raises(ServiceError) as exc_info:
                await payment_service.refund_payment(payment.id, Decimal('50.00'), "Test refund")
            
            assert "Refund failed" in str(exc_info.value)
            assert "Refund not allowed" in str(exc_info.value)
    
    async def test_get_invoice_payments(self, payment_service, sample_invoice):
        """Test retrieving all payments for an invoice."""
        # Create multiple payments for the invoice
        payment_data_1 = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('50.00'),
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        payment_data_2 = schemas.PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal('58.50'),
            payment_method=PaymentMethod.ACH
        )
        
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.side_effect = [
                {'status': 'success', 'transaction_id': 'CC_1'},
                {'status': 'success', 'transaction_id': 'ACH_1'}
            ]
            
            await payment_service.process_payment(payment_data_1)
            await payment_service.process_payment(payment_data_2)
        
        # Retrieve all payments for the invoice
        payments = await payment_service.get_invoice_payments(sample_invoice.id)
        
        assert len(payments) == 2
        
        # Verify payments are for the correct invoice
        for payment in payments:
            assert payment.invoice_id == sample_invoice.id
        
        # Verify payment amounts
        amounts = [payment.amount for payment in payments]
        assert Decimal('50.00') in amounts
        assert Decimal('58.50') in amounts
        
        # Verify payment methods
        methods = [payment.payment_method for payment in payments]
        assert PaymentMethod.CREDIT_CARD in methods
        assert PaymentMethod.ACH in methods
    
    async def test_get_payment_status(self, payment_service, sample_payment_data):
        """Test retrieving payment status."""
        # Create payment
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.return_value = {
                'status': 'success',
                'transaction_id': 'CC_123456'
            }
            
            payment = await payment_service.process_payment(sample_payment_data)
        
        # Get payment status
        status = await payment_service.get_payment_status(payment.id)
        assert status == PaymentStatus.COMPLETED
        
        # Test with non-existent payment
        with pytest.raises(NotFoundError):
            await payment_service.get_payment_status(uuid4())
    
    async def test_validate_payment_amount(self, payment_service):
        """Test payment amount validation."""
        invoice_total = Decimal('100.00')
        
        # Valid amount
        assert await payment_service.validate_payment_amount(Decimal('100.00'), invoice_total)
        assert await payment_service.validate_payment_amount(Decimal('50.00'), invoice_total)
        
        # Invalid amounts
        with pytest.raises(ValidationError):
            await payment_service.validate_payment_amount(Decimal('0.00'), invoice_total)
        
        with pytest.raises(ValidationError):
            await payment_service.validate_payment_amount(Decimal('-10.00'), invoice_total)
        
        with pytest.raises(ValidationError):
            await payment_service.validate_payment_amount(Decimal('150.00'), invoice_total)
    
    async def test_concurrent_payment_processing(self, payment_service):
        """Test concurrent payment processing for different invoices."""
        import asyncio
        
        # Create multiple invoices
        invoices = []
        for i in range(3):
            invoice_repo = payment_service.invoice_repo
            invoice_data = {
                'customer_id': uuid4(),
                'invoice_number': f'INV-CONCURRENT-{i}',
                'invoice_date': datetime.now().date(),
                'due_date': (datetime.now() + timedelta(days=30)).date(),
                'subtotal': Decimal('100.00'),
                'tax_amount': Decimal('8.50'),
                'total_amount': Decimal('108.50'),
                'amount_paid': Decimal('0.00'),
                'amount_due': Decimal('108.50'),
                'status': InvoiceStatus.SENT,
                'currency': 'USD'
            }
            invoice = invoice_repo.create(invoice_data)
            invoices.append(invoice)
        
        # Create payment tasks for each invoice
        tasks = []
        for i, invoice in enumerate(invoices):
            payment_data = schemas.PaymentCreate(
                invoice_id=invoice.id,
                amount=Decimal('108.50'),
                payment_method=PaymentMethod.CREDIT_CARD
            )
            tasks.append(payment_service.process_payment(payment_data))
        
        # Mock external payment processing
        with patch.object(payment_service, '_process_external_payment') as mock_external:
            mock_external.side_effect = [
                {'status': 'success', 'transaction_id': f'CC_CONCURRENT_{i}'}
                for i in range(3)
            ]
            
            # Process all payments concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all payments were processed successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert result.status == PaymentStatus.COMPLETED
            assert result.amount == Decimal('108.50')
        
        # Verify all invoices were updated correctly
        for invoice in invoices:
            updated_invoice = payment_service.invoice_repo.get_by_id(invoice.id)
            assert updated_invoice.status == InvoiceStatus.PAID
            assert updated_invoice.amount_paid == Decimal('108.50')
            assert updated_invoice.amount_due == Decimal('0.00')