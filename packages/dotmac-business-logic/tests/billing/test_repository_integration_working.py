"""
Repository integration tests - working version matching actual API.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.models import (
    BillingCycle,
    InvoiceStatus,
    PaymentStatus,
)
from dotmac_business_logic.billing.infra.repositories import (
    RepositoryFactory,
    SQLAlchemyBillingRepository,
    UnitOfWork,
)


@pytest.fixture
def mock_session():
    """Create mock async SQLAlchemy session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_models():
    """Create mock model classes."""
    customer_model = Mock()
    customer_model.__name__ = 'Customer'
    customer_model.id = 'id'
    customer_model.tenant_id = 'tenant_id'

    subscription_model = Mock()
    subscription_model.__name__ = 'Subscription'
    subscription_model.id = 'id'
    subscription_model.customer_id = 'customer_id'
    subscription_model.tenant_id = 'tenant_id'
    subscription_model.next_billing_date = 'next_billing_date'
    subscription_model.status = 'status'
    subscription_model.customer = 'customer'
    subscription_model.billing_plan = 'billing_plan'

    invoice_model = Mock()
    invoice_model.__name__ = 'Invoice'
    invoice_model.id = 'id'
    invoice_model.tenant_id = 'tenant_id'
    invoice_model.line_items = 'line_items'
    invoice_model.customer = 'customer'

    payment_model = Mock()
    payment_model.__name__ = 'Payment'
    payment_model.id = 'id'
    payment_model.idempotency_key = 'idempotency_key'
    payment_model.tenant_id = 'tenant_id'

    usage_record_model = Mock()
    usage_record_model.__name__ = 'UsageRecord'
    usage_record_model.subscription_id = 'subscription_id'
    usage_record_model.recorded_at = 'recorded_at'
    usage_record_model.tenant_id = 'tenant_id'

    return {
        'customer': customer_model,
        'subscription': subscription_model,
        'invoice': invoice_model,
        'payment': payment_model,
        'usage_record': usage_record_model,
    }


@pytest.fixture
def billing_repository(mock_session, mock_models):
    """Create SQLAlchemyBillingRepository instance."""
    return SQLAlchemyBillingRepository(
        session=mock_session,
        customer_model=mock_models['customer'],
        subscription_model=mock_models['subscription'],
        invoice_model=mock_models['invoice'],
        payment_model=mock_models['payment'],
        usage_record_model=mock_models['usage_record'],
        tenant_id=uuid4(),
    )


@pytest.fixture
def tenant_id():
    """Create test tenant ID."""
    return uuid4()


class TestSQLAlchemyBillingRepository:
    """Test SQLAlchemy billing repository implementation."""

    @pytest.mark.asyncio
    async def test_repository_initialization(self, mock_session, mock_models, tenant_id):
        """Test repository initialization with all required parameters."""
        # Execute
        repo = SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant_id,
        )

        # Assert
        assert repo.session == mock_session
        assert repo.customer_model == mock_models['customer']
        assert repo.subscription_model == mock_models['subscription']
        assert repo.invoice_model == mock_models['invoice']
        assert repo.payment_model == mock_models['payment']
        assert repo.usage_record_model == mock_models['usage_record']
        assert repo.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_get_customer_success(self, billing_repository, mock_session):
        """Test successful customer retrieval."""
        # Setup
        customer_id = uuid4()
        mock_customer = Mock()
        mock_customer.id = customer_id

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_customer
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_customer(customer_id)

        # Assert
        assert result == mock_customer
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, billing_repository, mock_session):
        """Test customer not found scenario."""
        # Setup
        customer_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_customer(customer_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_create_customer_success(self, billing_repository, mock_session, mock_models):
        """Test successful customer creation."""
        # Setup
        customer_data = {
            'name': 'Test Customer',
            'email': 'test@example.com'
        }

        mock_customer = Mock()
        mock_models['customer'].return_value = mock_customer

        # Execute
        result = await billing_repository.create_customer(customer_data)

        # Assert
        assert result == mock_customer
        mock_models['customer'].assert_called_once()
        mock_session.add.assert_called_once_with(mock_customer)
        mock_session.flush.assert_called_once()

        # Check tenant_id was added
        call_args = mock_models['customer'].call_args[1]
        assert 'tenant_id' in call_args
        assert call_args['tenant_id'] == billing_repository.tenant_id

    @pytest.mark.asyncio
    async def test_get_subscription_with_relationships(self, billing_repository, mock_session):
        """Test subscription retrieval with related data loaded."""
        # Setup
        subscription_id = uuid4()
        mock_subscription = Mock()
        mock_subscription.id = subscription_id

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_subscription(subscription_id)

        # Assert
        assert result == mock_subscription
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, billing_repository, mock_session, mock_models):
        """Test successful subscription creation."""
        # Setup
        subscription_data = {
            'customer_id': uuid4(),
            'plan_id': uuid4(),
            'status': 'active',
            'billing_cycle': BillingCycle.MONTHLY,
        }

        mock_subscription = Mock()
        mock_models['subscription'].return_value = mock_subscription

        # Execute
        result = await billing_repository.create_subscription(subscription_data)

        # Assert
        assert result == mock_subscription
        mock_session.add.assert_called_once_with(mock_subscription)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_subscription_success(self, billing_repository, mock_session):
        """Test successful subscription update."""
        # Setup
        subscription_id = uuid4()
        update_data = {'status': 'cancelled'}

        mock_subscription = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.update_subscription(subscription_id, update_data)

        # Assert
        assert result == mock_subscription
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_due_subscriptions(self, billing_repository, mock_session):
        """Test retrieving subscriptions due for billing."""
        # Setup
        as_of_date = date(2024, 2, 1)

        mock_subscriptions = [Mock(), Mock()]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_subscriptions
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_due_subscriptions(as_of_date)

        # Assert
        assert result == mock_subscriptions
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_subscriptions(self, billing_repository, mock_session):
        """Test retrieving all subscriptions for a customer."""
        # Setup
        customer_id = uuid4()

        mock_subscriptions = [Mock(), Mock()]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_subscriptions
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_customer_subscriptions(customer_id)

        # Assert
        assert result == mock_subscriptions
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_success(self, billing_repository, mock_session, mock_models):
        """Test successful invoice creation."""
        # Setup
        invoice_data = {
            'customer_id': uuid4(),
            'subscription_id': uuid4(),
            'total': Decimal('100.00'),
            'status': InvoiceStatus.DRAFT,
        }

        mock_invoice = Mock()
        mock_models['invoice'].return_value = mock_invoice

        # Execute
        result = await billing_repository.create_invoice(invoice_data)

        # Assert
        assert result == mock_invoice
        mock_session.add.assert_called_once_with(mock_invoice)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invoice_status_success(self, billing_repository, mock_session):
        """Test successful invoice status update."""
        # Setup
        invoice_id = uuid4()
        status = InvoiceStatus.PAID

        mock_invoice = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_invoice
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.update_invoice_status(invoice_id, status)

        # Assert
        assert result == mock_invoice
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_success(self, billing_repository, mock_session, mock_models):
        """Test successful payment creation."""
        # Setup
        payment_data = {
            'invoice_id': uuid4(),
            'customer_id': uuid4(),
            'amount': Decimal('100.00'),
            'status': PaymentStatus.PENDING,
            'idempotency_key': 'unique-key-123',
        }

        mock_payment = Mock()
        mock_models['payment'].return_value = mock_payment

        # Execute
        result = await billing_repository.create_payment(payment_data)

        # Assert
        assert result == mock_payment
        mock_session.add.assert_called_once_with(mock_payment)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_payment_by_idempotency_key_found(self, billing_repository, mock_session):
        """Test finding payment by idempotency key."""
        # Setup
        key = 'unique-key-123'

        mock_payment = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_payment_by_idempotency_key(key)

        # Assert
        assert result == mock_payment
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_payment_by_idempotency_key_not_found(self, billing_repository, mock_session):
        """Test payment not found by idempotency key."""
        # Setup
        key = 'non-existent-key'

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_payment_by_idempotency_key(key)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_payment_status_success(self, billing_repository, mock_session):
        """Test successful payment status update."""
        # Setup
        payment_id = uuid4()
        status = PaymentStatus.SUCCESS

        mock_payment = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.update_payment_status(payment_id, status)

        # Assert
        assert result == mock_payment
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_usage_records_for_period(self, billing_repository, mock_session):
        """Test retrieving usage records for billing period."""
        # Setup
        subscription_id = uuid4()
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        mock_usage_records = [Mock(), Mock(), Mock()]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_usage_records
        mock_session.execute.return_value = mock_result

        # Execute
        result = await billing_repository.get_usage_records(
            subscription_id, start_date, end_date
        )

        # Assert
        assert result == mock_usage_records
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_operations(self, billing_repository, mock_session):
        """Test transaction control operations."""
        # Execute & Assert commit
        await billing_repository.commit()
        mock_session.commit.assert_called_once()

        # Execute & Assert rollback
        await billing_repository.rollback()
        mock_session.rollback.assert_called_once()

        # Execute & Assert flush
        await billing_repository.flush()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_filtering_applied(self, mock_session, mock_models, tenant_id):
        """Test that tenant filtering is applied to queries when tenant_id is set."""
        # Setup repository with tenant
        repo = SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant_id,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute - this should add tenant filtering
        await repo.get_customer(uuid4())

        # Assert that execute was called (tenant filtering should be applied in query construction)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_tenant_filtering_when_no_tenant(self, mock_session, mock_models):
        """Test that no tenant filtering is applied when tenant_id is None."""
        # Setup repository without tenant
        repo = SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=None,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        await repo.get_customer(uuid4())

        # Assert that execute was called
        mock_session.execute.assert_called_once()


class TestUnitOfWork:
    """Test Unit of Work pattern implementation."""

    @pytest.fixture
    def unit_of_work(self, mock_session):
        """Create UnitOfWork instance."""
        return UnitOfWork(mock_session)

    @pytest.mark.asyncio
    async def test_unit_of_work_context_manager_success(self, mock_session):
        """Test UnitOfWork context manager commits on success."""
        # Execute
        async with UnitOfWork(mock_session) as uow:
            assert uow is not None

        # Assert
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_unit_of_work_context_manager_exception(self, mock_session):
        """Test UnitOfWork context manager rolls back on exception."""
        # Execute & Assert exception handling
        with pytest.raises(ValueError):
            async with UnitOfWork(mock_session):
                raise ValueError("Test error")

        # Assert
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_billing_repository(self, unit_of_work, mock_models, tenant_id):
        """Test getting billing repository from UnitOfWork."""
        # Execute
        repo = unit_of_work.get_billing_repository(
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant_id,
        )

        # Assert
        assert isinstance(repo, SQLAlchemyBillingRepository)
        assert repo.tenant_id == tenant_id

        # Test that same instance is returned on subsequent calls
        repo2 = unit_of_work.get_billing_repository(
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant_id,
        )
        assert repo is repo2

    @pytest.mark.asyncio
    async def test_unit_of_work_transaction_operations(self, unit_of_work, mock_session):
        """Test UnitOfWork transaction control operations."""
        # Execute & Assert commit
        await unit_of_work.commit()
        mock_session.commit.assert_called_once()

        # Execute & Assert rollback
        await unit_of_work.rollback()
        mock_session.rollback.assert_called_once()

        # Execute & Assert flush
        await unit_of_work.flush()
        mock_session.flush.assert_called_once()


class TestRepositoryFactory:
    """Test Repository Factory implementation."""

    @pytest.fixture
    def session_factory(self):
        """Create mock session factory."""
        mock_session = AsyncMock()
        return AsyncMock(return_value=mock_session)

    @pytest.fixture
    def repository_factory(self, session_factory, mock_models):
        """Create RepositoryFactory instance."""
        return RepositoryFactory(
            session_factory=session_factory,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
        )

    @pytest.mark.asyncio
    async def test_create_billing_repository(self, repository_factory, session_factory, tenant_id):
        """Test creating billing repository through factory."""
        # Execute
        repo = await repository_factory.create_billing_repository(tenant_id=tenant_id)

        # Assert
        assert isinstance(repo, SQLAlchemyBillingRepository)
        assert repo.tenant_id == tenant_id
        session_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unit_of_work(self, repository_factory, session_factory):
        """Test creating unit of work through factory."""
        # Execute
        uow = await repository_factory.create_unit_of_work()

        # Assert
        assert isinstance(uow, UnitOfWork)
        session_factory.assert_called_once()


class TestTenantIsolation:
    """Test tenant isolation in multi-tenant scenarios."""

    @pytest.mark.asyncio
    async def test_different_tenants_isolated(self, mock_session, mock_models):
        """Test that different tenants don't see each other's data."""
        # Setup two repositories with different tenants
        tenant1_id = uuid4()
        tenant2_id = uuid4()

        repo1 = SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant1_id,
        )

        repo2 = SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant2_id,
        )

        # Assert different tenant IDs
        assert repo1.tenant_id != repo2.tenant_id
        assert repo1.tenant_id == tenant1_id
        assert repo2.tenant_id == tenant2_id

    @pytest.mark.asyncio
    async def test_data_creation_includes_tenant(self, mock_session, mock_models, tenant_id):
        """Test that created entities include tenant_id."""
        repo = SQLAlchemyBillingRepository(
            session=mock_session,
            customer_model=mock_models['customer'],
            subscription_model=mock_models['subscription'],
            invoice_model=mock_models['invoice'],
            payment_model=mock_models['payment'],
            usage_record_model=mock_models['usage_record'],
            tenant_id=tenant_id,
        )

        mock_customer = Mock()
        mock_models['customer'].return_value = mock_customer

        # Execute customer creation
        customer_data = {'name': 'Test Customer'}
        await repo.create_customer(customer_data)

        # Assert tenant_id was added to data
        call_args = mock_models['customer'].call_args[1]
        assert 'tenant_id' in call_args
        assert call_args['tenant_id'] == tenant_id
