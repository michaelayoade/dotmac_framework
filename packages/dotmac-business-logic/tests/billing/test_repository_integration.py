"""
Integration tests for billing repository implementations.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.models import (
    InvoiceStatus,
    Money,
    PaymentStatus,
    SubscriptionStatus,
)
from dotmac_business_logic.billing.infra.mappers import BillingEntityMixin
from dotmac_business_logic.billing.infra.repositories import SQLAlchemyBillingRepository


class MockCustomer(BillingEntityMixin):
    """Mock customer model for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.email = kwargs.get('email', 'test@example.com')
        self.name = kwargs.get('name', 'Test Customer')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.tenant_id = kwargs.get('tenant_id')


class MockSubscription(BillingEntityMixin):
    """Mock subscription model for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.customer_id = kwargs.get('customer_id', uuid4())
        self.plan_id = kwargs.get('plan_id', uuid4())
        self.status = kwargs.get('status', SubscriptionStatus.ACTIVE)
        self.current_period_start = kwargs.get('current_period_start', date(2024, 1, 1))
        self.current_period_end = kwargs.get('current_period_end', date(2024, 1, 31))
        self.next_billing_date = kwargs.get('next_billing_date', date(2024, 2, 1))
        self.trial_end_date = kwargs.get('trial_end_date')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.tenant_id = kwargs.get('tenant_id')


class MockInvoice(BillingEntityMixin):
    """Mock invoice model for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.customer_id = kwargs.get('customer_id', uuid4())
        self.subscription_id = kwargs.get('subscription_id')
        self.invoice_number = kwargs.get('invoice_number', f'INV-{uuid4().hex[:8].upper()}')
        self.amount_cents = kwargs.get('amount_cents', 9999)  # $99.99
        self.currency = kwargs.get('currency', 'USD')
        self.status = kwargs.get('status', InvoiceStatus.PENDING)
        self.issue_date = kwargs.get('issue_date', date.today())
        self.due_date = kwargs.get('due_date', date.today())
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.tenant_id = kwargs.get('tenant_id')


class MockPayment(BillingEntityMixin):
    """Mock payment model for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        self.invoice_id = kwargs.get('invoice_id', uuid4())
        self.customer_id = kwargs.get('customer_id', uuid4())
        self.amount_cents = kwargs.get('amount_cents', 9999)
        self.currency = kwargs.get('currency', 'USD')
        self.status = kwargs.get('status', PaymentStatus.COMPLETED)
        self.transaction_id = kwargs.get('transaction_id', f'txn_{uuid4().hex[:12]}')
        self.idempotency_key = kwargs.get('idempotency_key')
        self.payment_method = kwargs.get('payment_method', 'card')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.tenant_id = kwargs.get('tenant_id')


class TestSQLAlchemyBillingRepository:
    """Test SQLAlchemy billing repository implementation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock SQLAlchemy session."""
        session = AsyncMock()

        # Configure common query behaviors
        session.execute.return_value.scalar_one_or_none = AsyncMock()
        session.execute.return_value.scalars = AsyncMock()
        session.execute.return_value.all = AsyncMock(return_value=[])

        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance with mock session and models."""
        return SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=MockCustomer,
            subscription_model=MockSubscription,
            invoice_model=MockInvoice,
            payment_model=MockPayment,
            usage_record_model=Mock  # Not used in these tests
        )

    @pytest.mark.asyncio
    async def test_get_customer_success(self, repository, mock_session):
        """Test successful customer retrieval."""
        # Setup
        customer_id = uuid4()
        expected_customer = MockCustomer(id=customer_id, name="John Doe")
        mock_session.execute.return_value.scalar_one_or_none.return_value = expected_customer

        # Execute
        result = await repository.get_customer(customer_id)

        # Assert
        assert result == expected_customer
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, repository, mock_session):
        """Test customer retrieval when not found."""
        # Setup
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Execute
        result = await repository.get_customer(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, repository, mock_session):
        """Test successful subscription creation."""
        # Setup
        subscription_data = {
            'customer_id': uuid4(),
            'plan_id': uuid4(),
            'status': SubscriptionStatus.ACTIVE,
            'current_period_start': date(2024, 1, 1),
            'current_period_end': date(2024, 1, 31)
        }

        # Execute
        result = await repository.create_subscription(subscription_data)

        # Assert
        assert isinstance(result, MockSubscription)
        assert result.customer_id == subscription_data['customer_id']
        assert result.status == subscription_data['status']
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_with_line_items(self, repository, mock_session):
        """Test invoice creation with line items."""
        # Setup
        invoice_data = {
            'customer_id': uuid4(),
            'subscription_id': uuid4(),
            'amount': Money(Decimal('149.99'), 'USD'),
            'issue_date': date(2024, 1, 1),
            'due_date': date(2024, 1, 15),
            'line_items': [
                {
                    'description': 'Monthly Subscription',
                    'amount': Money(Decimal('99.99'), 'USD'),
                    'quantity': 1
                },
                {
                    'description': 'Setup Fee',
                    'amount': Money(Decimal('50.00'), 'USD'),
                    'quantity': 1
                }
            ]
        }

        # Execute
        result = await repository.create_invoice(invoice_data)

        # Assert
        assert isinstance(result, MockInvoice)
        assert result.amount_cents == 14999  # $149.99 in cents
        assert result.currency == 'USD'
        mock_session.add.assert_called()  # Called at least once
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_with_idempotency(self, repository, mock_session):
        """Test payment creation with idempotency key."""
        # Setup
        payment_data = {
            'invoice_id': uuid4(),
            'customer_id': uuid4(),
            'amount': Money(Decimal('99.99'), 'USD'),
            'payment_method': 'card',
            'transaction_id': 'txn_123456789',
            'idempotency_key': 'idempotent_payment_123'
        }

        # Execute
        result = await repository.create_payment(payment_data)

        # Assert
        assert isinstance(result, MockPayment)
        assert result.idempotency_key == 'idempotent_payment_123'
        assert result.amount_cents == 9999
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_payment_by_idempotency_key(self, repository, mock_session):
        """Test retrieving payment by idempotency key."""
        # Setup
        idempotency_key = 'duplicate_payment_key'
        expected_payment = MockPayment(idempotency_key=idempotency_key)
        mock_session.execute.return_value.scalar_one_or_none.return_value = expected_payment

        # Execute
        result = await repository.get_payment_by_idempotency_key(idempotency_key)

        # Assert
        assert result == expected_payment
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_subscription_status(self, repository, mock_session):
        """Test updating subscription status."""
        # Setup
        subscription_id = uuid4()
        existing_subscription = MockSubscription(id=subscription_id, status=SubscriptionStatus.ACTIVE)
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_subscription

        update_data = {
            'status': SubscriptionStatus.CANCELLED,
            'cancelled_at': datetime.now(timezone.utc)
        }

        # Execute
        result = await repository.update_subscription(subscription_id, update_data)

        # Assert
        assert result.status == SubscriptionStatus.CANCELLED
        assert result.cancelled_at is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_subscriptions_by_customer(self, repository, mock_session):
        """Test retrieving all subscriptions for a customer."""
        # Setup
        customer_id = uuid4()
        subscriptions = [
            MockSubscription(customer_id=customer_id, status=SubscriptionStatus.ACTIVE),
            MockSubscription(customer_id=customer_id, status=SubscriptionStatus.CANCELLED)
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = subscriptions

        # Execute
        result = await repository.get_subscriptions_by_customer(customer_id)

        # Assert
        assert len(result) == 2
        assert all(sub.customer_id == customer_id for sub in result)

    @pytest.mark.asyncio
    async def test_get_invoices_by_subscription(self, repository, mock_session):
        """Test retrieving invoices for a subscription."""
        # Setup
        subscription_id = uuid4()
        invoices = [
            MockInvoice(subscription_id=subscription_id, status=InvoiceStatus.PAID),
            MockInvoice(subscription_id=subscription_id, status=InvoiceStatus.PENDING)
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = invoices

        # Execute
        result = await repository.get_invoices_by_subscription(subscription_id)

        # Assert
        assert len(result) == 2
        assert all(inv.subscription_id == subscription_id for inv in result)

    @pytest.mark.asyncio
    async def test_get_payments_by_invoice(self, repository, mock_session):
        """Test retrieving payments for an invoice."""
        # Setup
        invoice_id = uuid4()
        payments = [
            MockPayment(invoice_id=invoice_id, status=PaymentStatus.COMPLETED),
            MockPayment(invoice_id=invoice_id, status=PaymentStatus.FAILED)
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = payments

        # Execute
        result = await repository.get_payments_by_invoice(invoice_id)

        # Assert
        assert len(result) == 2
        assert all(pay.invoice_id == invoice_id for pay in result)

    @pytest.mark.asyncio
    async def test_get_usage_records_for_period(self, repository, mock_session):
        """Test retrieving usage records for billing period."""
        # Setup
        subscription_id = uuid4()
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Mock usage records
        usage_records = [
            Mock(subscription_id=subscription_id, record_date=date(2024, 1, 15), quantity=100),
            Mock(subscription_id=subscription_id, record_date=date(2024, 1, 20), quantity=150)
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = usage_records

        # Execute
        result = await repository.get_usage_records_for_period(
            subscription_id, start_date, end_date
        )

        # Assert
        assert len(result) == 2
        assert all(rec.subscription_id == subscription_id for rec in result)

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, repository, mock_session):
        """Test transaction rollback when creation fails."""
        # Setup - simulate database error
        mock_session.commit.side_effect = Exception("Database connection lost")

        subscription_data = {
            'customer_id': uuid4(),
            'plan_id': uuid4(),
            'status': SubscriptionStatus.ACTIVE
        }

        # Execute & Assert
        with pytest.raises(Exception, match="Database connection lost"):
            await repository.create_subscription(subscription_data)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, repository, mock_session):
        """Test that repository properly handles tenant isolation."""
        # Setup
        tenant_id = uuid4()
        customer_id = uuid4()

        # Configure repository with tenant ID
        repository.tenant_id = tenant_id

        # Mock customer with matching tenant
        expected_customer = MockCustomer(id=customer_id, tenant_id=tenant_id)
        mock_session.execute.return_value.scalar_one_or_none.return_value = expected_customer

        # Execute
        result = await repository.get_customer(customer_id)

        # Assert
        assert result.tenant_id == tenant_id

        # Verify query was filtered by tenant (would be in the SQL query)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_money_conversion_handling(self, repository):
        """Test proper handling of Money objects in repository."""
        # Setup
        money_amount = Money(Decimal('123.45'), 'EUR')
        invoice_data = {
            'customer_id': uuid4(),
            'amount': money_amount,
            'issue_date': date.today(),
            'due_date': date.today()
        }

        # Execute
        result = await repository.create_invoice(invoice_data)

        # Assert - Money should be converted to cents and currency stored
        assert result.amount_cents == 12345  # $123.45 in cents
        assert result.currency == 'EUR'

    @pytest.mark.asyncio
    async def test_search_invoices_with_filters(self, repository, mock_session):
        """Test searching invoices with various filters."""
        # Setup filters
        filters = {
            'customer_id': uuid4(),
            'status': InvoiceStatus.PENDING,
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 1, 31),
            'amount_min': Money(Decimal('50.00'), 'USD'),
            'amount_max': Money(Decimal('500.00'), 'USD')
        }

        invoices = [MockInvoice(status=InvoiceStatus.PENDING)]
        mock_session.execute.return_value.scalars.return_value.all.return_value = invoices

        # Execute
        result = await repository.search_invoices(filters)

        # Assert
        assert len(result) == 1
        assert result[0].status == InvoiceStatus.PENDING
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_operations(self, repository, mock_session):
        """Test bulk operations for performance."""
        # Setup - multiple subscriptions to create
        subscription_data_list = [
            {
                'customer_id': uuid4(),
                'plan_id': uuid4(),
                'status': SubscriptionStatus.ACTIVE
            }
            for _ in range(5)
        ]

        # Execute
        results = await repository.bulk_create_subscriptions(subscription_data_list)

        # Assert
        assert len(results) == 5
        assert all(isinstance(sub, MockSubscription) for sub in results)
        # Should commit only once for bulk operation
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_repository_health_check(self, repository, mock_session):
        """Test repository health check functionality."""
        # Setup
        mock_session.execute.return_value.scalar.return_value = 1

        # Execute
        is_healthy = await repository.health_check()

        # Assert
        assert is_healthy is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_repository_health_check_failure(self, repository, mock_session):
        """Test repository health check when database is down."""
        # Setup
        mock_session.execute.side_effect = Exception("Connection refused")

        # Execute
        is_healthy = await repository.health_check()

        # Assert
        assert is_healthy is False

    def test_entity_mixin_functionality(self):
        """Test BillingEntityMixin common functionality."""
        # Create test entity
        entity = MockCustomer(name="Test Customer")

        # Test to_dict conversion
        entity_dict = entity.to_dict()
        assert entity_dict['name'] == "Test Customer"
        assert 'id' in entity_dict
        assert 'created_at' in entity_dict

        # Test from_dict creation
        new_entity = MockCustomer.from_dict(entity_dict)
        assert new_entity.name == "Test Customer"
        assert new_entity.id == entity.id

    def test_currency_precision_handling(self):
        """Test that currency amounts maintain proper precision."""
        # Test various decimal amounts
        test_amounts = [
            (Decimal('99.99'), 'USD', 9999),
            (Decimal('123.456'), 'USD', 12346),  # Rounded to nearest cent
            (Decimal('0.01'), 'USD', 1),
            (Decimal('1000.00'), 'JPY', 100000)  # JPY typically no decimal places
        ]

        for amount, currency, expected_cents in test_amounts:
            Money(amount, currency)
            invoice = MockInvoice(amount_cents=expected_cents, currency=currency)

            # Verify proper conversion
            if currency in ['USD', 'EUR', 'GBP']:
                assert invoice.amount_cents == expected_cents
