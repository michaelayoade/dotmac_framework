"""Unit tests for billing repository layer."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from dotmac_isp.modules.billing.repository import (
    InvoiceRepository, InvoiceLineItemRepository, PaymentRepository,
    SubscriptionRepository, CreditNoteRepository
)
from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceLineItem, Payment, CreditNote, Subscription,
    InvoiceStatus, PaymentStatus, PaymentMethod, BillingCycle
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def tenant_id():
    """Sample tenant ID."""
    return uuid4()


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        'customer_id': uuid4(),
        'invoice_number': 'INV-001',
        'invoice_date': date.today(),
        'due_date': date.today() + timedelta(days=30),
        'subtotal': Decimal('100.00'),
        'tax_amount': Decimal('8.50'),
        'total_amount': Decimal('108.50'),
        'status': InvoiceStatus.DRAFT
    }


@pytest.mark.unit
@pytest.mark.billing
class TestInvoiceRepository:
    """Test InvoiceRepository functionality."""

    def test_init(self, mock_db_session, tenant_id):
        """Test repository initialization."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        assert repo.db == mock_db_session
        assert repo.tenant_id == tenant_id

    def test_create_invoice_success(self, mock_db_session, tenant_id, sample_invoice_data):
        """Test successful invoice creation."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        # Mock database operations
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        # Mock invoice number generation
        with patch.object(repo, '_generate_invoice_number', return_value='INV-001'):
            result = repo.create(sample_invoice_data)
            
            # Verify invoice creation
            assert isinstance(result, Invoice)
            assert result.tenant_id == tenant_id
            assert result.invoice_number == 'INV-001'
            assert result.customer_id == sample_invoice_data['customer_id']
            assert result.subtotal == sample_invoice_data['subtotal']
            
            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    def test_create_invoice_with_generated_number(self, mock_db_session, tenant_id):
        """Test invoice creation with auto-generated invoice number."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        invoice_data = {
            'customer_id': uuid4(),
            'subtotal': Decimal('100.00')
        }
        
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        with patch.object(repo, '_generate_invoice_number', return_value='INV-AUTO-001'):
            result = repo.create(invoice_data)
            
            assert result.invoice_number == 'INV-AUTO-001'

    def test_create_invoice_integrity_error(self, mock_db_session, tenant_id, sample_invoice_data):
        """Test invoice creation with integrity error."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        # Mock IntegrityError on commit
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock(side_effect=IntegrityError(None, None, None)
        mock_db_session.rollback = Mock()
        
        with pytest.raises(ConflictError):
            repo.create(sample_invoice_data)
        
        mock_db_session.rollback.assert_called_once()

    def test_get_by_id_found(self, mock_db_session, tenant_id):
        """Test retrieving invoice by ID when found."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        invoice_id = uuid4()
        
        # Mock invoice object
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = tenant_id
        
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_invoice
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_by_id(invoice_id)
        
        assert result == mock_invoice
        mock_db_session.query.assert_called_once_with(Invoice)

    def test_get_by_id_not_found(self, mock_db_session, tenant_id):
        """Test retrieving invoice by ID when not found."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        invoice_id = uuid4()
        
        # Mock empty query result
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        with pytest.raises(NotFoundError):
            repo.get_by_id(invoice_id)

    def test_get_by_invoice_number(self, mock_db_session, tenant_id):
        """Test retrieving invoice by invoice number."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        invoice_number = "INV-001"
        
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.invoice_number = invoice_number
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_invoice
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_by_invoice_number(invoice_number)
        
        assert result == mock_invoice

    def test_get_by_customer_id(self, mock_db_session, tenant_id):
        """Test retrieving invoices by customer ID."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        customer_id = uuid4()
        
        mock_invoices = [Mock(spec=Invoice), Mock(spec=Invoice)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_invoices
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_by_customer_id(customer_id)
        
        assert result == mock_invoices
        assert len(result) == 2

    def test_update_invoice(self, mock_db_session, tenant_id):
        """Test updating invoice."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        invoice_id = uuid4()
        
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = tenant_id
        
        # Mock query to find existing invoice
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_invoice
        mock_db_session.query.return_value = mock_query
        
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        update_data = {'status': InvoiceStatus.SENT}
        result = repo.update(invoice_id, update_data)
        
        assert result == mock_invoice
        assert mock_invoice.status == InvoiceStatus.SENT
        mock_db_session.commit.assert_called_once()

    def test_delete_invoice(self, mock_db_session, tenant_id):
        """Test deleting invoice."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        invoice_id = uuid4()
        
        mock_invoice = Mock(spec=Invoice)
        mock_invoice.id = invoice_id
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_invoice
        mock_db_session.query.return_value = mock_query
        
        mock_db_session.delete = Mock()
        mock_db_session.commit = Mock()
        
        result = repo.delete(invoice_id)
        
        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_invoice)
        mock_db_session.commit.assert_called_once()

    def test_get_overdue_invoices(self, mock_db_session, tenant_id):
        """Test retrieving overdue invoices."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        mock_invoices = [Mock(spec=Invoice), Mock(spec=Invoice)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_invoices
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_overdue_invoices()
        
        assert result == mock_invoices
        assert len(result) == 2

    def test_generate_invoice_number(self, mock_db_session, tenant_id):
        """Test invoice number generation."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        # Mock the method to test number generation logic
        with patch('dotmac_isp.modules.billing.repository.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101"
            
            # Mock database query to check for existing numbers
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 5  # 5 existing invoices today
            mock_db_session.query.return_value = mock_query
            
            result = repo._generate_invoice_number()
            
            # Should generate INV-20240101-006 (next number after 5 existing)
            assert result.startswith("INV-")
            assert "20240101" in result


@pytest.mark.unit
@pytest.mark.billing
class TestPaymentRepository:
    """Test PaymentRepository functionality."""

    def test_init(self, mock_db_session, tenant_id):
        """Test repository initialization."""
        repo = PaymentRepository(mock_db_session, tenant_id)
        
        assert repo.db == mock_db_session
        assert repo.tenant_id == tenant_id

    def test_create_payment(self, mock_db_session, tenant_id):
        """Test payment creation."""
        repo = PaymentRepository(mock_db_session, tenant_id)
        
        payment_data = {
            'invoice_id': uuid4(),
            'amount': Decimal('108.50'),
            'payment_method': PaymentMethod.CREDIT_CARD,
            'transaction_id': 'TXN123'
        }
        
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        result = repo.create(payment_data)
        
        assert isinstance(result, Payment)
        assert result.tenant_id == tenant_id
        assert result.amount == payment_data['amount']
        assert result.payment_method == payment_data['payment_method']

    def test_get_payments_by_invoice(self, mock_db_session, tenant_id):
        """Test retrieving payments by invoice ID."""
        repo = PaymentRepository(mock_db_session, tenant_id)
        invoice_id = uuid4()
        
        mock_payments = [Mock(spec=Payment), Mock(spec=Payment)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_payments
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_by_invoice_id(invoice_id)
        
        assert result == mock_payments
        assert len(result) == 2


@pytest.mark.unit
@pytest.mark.billing
class TestSubscriptionRepository:
    """Test SubscriptionRepository functionality."""

    def test_create_subscription(self, mock_db_session, tenant_id):
        """Test subscription creation."""
        repo = SubscriptionRepository(mock_db_session, tenant_id)
        
        subscription_data = {
            'customer_id': uuid4(),
            'service_plan_id': uuid4(),
            'billing_cycle': BillingCycle.MONTHLY,
            'amount': Decimal('99.99'),
            'start_date': date.today()
        }
        
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        result = repo.create(subscription_data)
        
        assert isinstance(result, Subscription)
        assert result.tenant_id == tenant_id
        assert result.billing_cycle == BillingCycle.MONTHLY
        assert result.amount == Decimal('99.99')

    def test_get_active_subscriptions(self, mock_db_session, tenant_id):
        """Test retrieving active subscriptions."""
        repo = SubscriptionRepository(mock_db_session, tenant_id)
        
        mock_subscriptions = [Mock(spec=Subscription)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_subscriptions
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_active_subscriptions()
        
        assert result == mock_subscriptions

    def test_get_subscriptions_for_billing(self, mock_db_session, tenant_id):
        """Test retrieving subscriptions ready for billing."""
        repo = SubscriptionRepository(mock_db_session, tenant_id)
        billing_date = date.today()
        
        mock_subscriptions = [Mock(spec=Subscription)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_subscriptions
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_subscriptions_for_billing(billing_date)
        
        assert result == mock_subscriptions


@pytest.mark.unit
@pytest.mark.billing
class TestCreditNoteRepository:
    """Test CreditNoteRepository functionality."""

    def test_create_credit_note(self, mock_db_session, tenant_id):
        """Test credit note creation."""
        repo = CreditNoteRepository(mock_db_session, tenant_id)
        
        credit_note_data = {
            'invoice_id': uuid4(),
            'amount': Decimal('25.00'),
            'reason': 'Service credit',
            'issue_date': date.today()
        }
        
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        with patch.object(repo, '_generate_credit_note_number', return_value='CN-001'):
            result = repo.create(credit_note_data)
            
            assert isinstance(result, CreditNote)
            assert result.tenant_id == tenant_id
            assert result.amount == Decimal('25.00')
            assert result.credit_note_number == 'CN-001'

    def test_get_credit_notes_by_invoice(self, mock_db_session, tenant_id):
        """Test retrieving credit notes by invoice ID."""
        repo = CreditNoteRepository(mock_db_session, tenant_id)
        invoice_id = uuid4()
        
        mock_credit_notes = [Mock(spec=CreditNote)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_credit_notes
        mock_db_session.query.return_value = mock_query
        
        result = repo.get_by_invoice_id(invoice_id)
        
        assert result == mock_credit_notes


@pytest.mark.unit
@pytest.mark.billing
class TestRepositoryErrorHandling:
    """Test repository error handling."""

    def test_database_error_handling(self, mock_db_session, tenant_id):
        """Test handling of database errors."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        # Mock database exception
        mock_db_session.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception):
            repo.get_by_id(uuid4()

    def test_transaction_rollback_on_error(self, mock_db_session, tenant_id, sample_invoice_data):
        """Test transaction rollback on error."""
        repo = InvoiceRepository(mock_db_session, tenant_id)
        
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock(side_effect=IntegrityError(None, None, None)
        mock_db_session.rollback = Mock()
        
        with pytest.raises(ConflictError):
            repo.create(sample_invoice_data)
        
        mock_db_session.rollback.assert_called_once()

    def test_tenant_isolation(self, mock_db_session):
        """Test that repositories enforce tenant isolation."""
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        
        repo1 = InvoiceRepository(mock_db_session, tenant1_id)
        repo2 = InvoiceRepository(mock_db_session, tenant2_id)
        
        assert repo1.tenant_id != repo2.tenant_id
        assert repo1.tenant_id == tenant1_id
        assert repo2.tenant_id == tenant2_id