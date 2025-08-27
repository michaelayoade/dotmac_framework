"""
Tests for plugin-based billing service.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from services.plugin_billing_service import PluginBillingService
from models.billing import (
    PricingPlan, Subscription, Invoice, Payment, UsageRecord,
    SubscriptionStatus, InvoiceStatus, PaymentStatus, PricingPlanType
)
from models.customer import Customer, CustomerStatus
from core.exceptions import (
    SubscriptionNotFoundError, ActiveSubscriptionExistsError,
    PaymentProcessingError, BusinessLogicError, ResourceNotFoundError
)


@pytest.fixture
def db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def billing_service(db_session):
    """Plugin billing service fixture."""
    return PluginBillingService(db_session)


@pytest.fixture
def sample_pricing_plan():
    """Sample pricing plan fixture."""
    return PricingPlan(
        id=uuid4(),
        name="Standard Plan",
        slug="standard",
        description="Standard billing plan",
        plan_type=PricingPlanType.FIXED,
        base_price_cents=5000,  # $50.00
        setup_fee_cents=0,
        billing_interval="monthly",
        billing_interval_count=1,
        trial_days=14,
        max_tenants=1,
        max_users=10,
        max_storage_gb=100,
        max_bandwidth_gb=1000,
        max_api_calls=100000,
        is_active=True,
        is_public=True,
        features=["billing", "customer_management", "api_access"],
        usage_limits={"api_calls": 100000, "storage_gb": 100},
        pricing_tiers=[],
        stripe_price_id="price_test123",
        stripe_product_id="prod_test123"
    )


@pytest.fixture
def sample_customer():
    """Sample customer fixture."""
    return Customer(
        id=uuid4(),
        tenant_id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="Customer",
        company_name="Test Corp",
        phone="+1-555-0123",
        status=CustomerStatus.ACTIVE,
        address_line1="123 Test St",
        city="Test City",
        state="TS",
        postal_code="12345",
        country="US",
        account_number="ACC-001",
        customer_since=datetime.now(timezone.utc),
        payment_status="current",
        notes="Test customer",
        tags=["test"],
        preferences={"notifications": True}
    )


@pytest.fixture
def sample_subscription(sample_pricing_plan):
    """Sample subscription fixture."""
    start_date = datetime.now(timezone.utc)
    return Subscription(
        id=uuid4(),
        tenant_id=uuid4(),
        pricing_plan_id=sample_pricing_plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start_date,
        current_period_end=start_date + timedelta(days=30),
        trial_start=None,
        trial_end=None,
        billing_cycle_day=1,
        cancel_at_period_end=False,
        cancelled_at=None,
        cancel_reason=None,
        current_usage={},
        default_payment_method_id=None,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        pricing_plan=sample_pricing_plan
    )


class TestPluginBillingService:
    """Test cases for PluginBillingService."""

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, billing_service, sample_pricing_plan, sample_customer):
        """Test successful subscription creation."""
        tenant_id = uuid4()
        plan_id = sample_pricing_plan.id
        customer_id = sample_customer.id
        
        # Mock repository responses
        billing_service.plan_repo.get_by_id = AsyncMock(return_value=sample_pricing_plan)
        billing_service.subscription_repo.get_active_subscription = AsyncMock(return_value=None)
        billing_service.customer_repo.get_by_id = AsyncMock(return_value=sample_customer)
        billing_service.subscription_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
        
        # Mock service integration
        billing_service.service_integration.create_subscription_via_plugin = AsyncMock(
            return_value={"subscription_id": "sub_test123", "customer_id": "cus_test123"}
        )
        
        with patch('services.plugin_billing_service.database_transaction') as mock_tx:
            mock_tx.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_tx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await billing_service.create_subscription(
                tenant_id=tenant_id,
                plan_id=plan_id,
                customer_id=customer_id,
                payment_method={"type": "card", "token": "tok_123"},
                created_by="test_user"
            )
            
            assert result is not None
            billing_service.plan_repo.get_by_id.assert_called_once_with(plan_id)
            billing_service.subscription_repo.get_active_subscription.assert_called_once_with(tenant_id)
            billing_service.customer_repo.get_by_id.assert_called_once_with(customer_id)

    @pytest.mark.asyncio
    async def test_create_subscription_plan_not_found(self, billing_service):
        """Test subscription creation with non-existent plan."""
        tenant_id = uuid4()
        plan_id = uuid4()
        customer_id = uuid4()
        
        billing_service.plan_repo.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await billing_service.create_subscription(
                tenant_id=tenant_id,
                plan_id=plan_id,
                customer_id=customer_id,
                created_by="test_user"
            )
        
        assert "Billing Plan" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_subscription_active_exists(self, billing_service, sample_pricing_plan, sample_subscription):
        """Test subscription creation when active subscription already exists."""
        tenant_id = uuid4()
        plan_id = sample_pricing_plan.id
        customer_id = uuid4()
        
        billing_service.plan_repo.get_by_id = AsyncMock(return_value=sample_pricing_plan)
        billing_service.subscription_repo.get_active_subscription = AsyncMock(return_value=sample_subscription)
        
        with pytest.raises(ActiveSubscriptionExistsError):
            await billing_service.create_subscription(
                tenant_id=tenant_id,
                plan_id=plan_id,
                customer_id=customer_id,
                created_by="test_user"
            )

    @pytest.mark.asyncio
    async def test_process_payment_success(self, billing_service):
        """Test successful payment processing."""
        invoice_id = uuid4()
        invoice = MagicMock()
        invoice.id = invoice_id
        invoice.status = InvoiceStatus.DRAFT
        invoice.total_cents = 5000
        invoice.subscription = MagicMock()
        invoice.subscription.tenant_id = uuid4()
        invoice.subscription_id = uuid4()
        
        payment_method = {"type": "card", "token": "tok_123", "last4": "4242", "brand": "visa"}
        
        billing_service.invoice_repo.get_by_id = AsyncMock(return_value=invoice)
        billing_service.service_integration.process_payment_via_plugin = AsyncMock(
            return_value={
                "success": True,
                "amount": 50.0,
                "currency": "USD",
                "payment_intent_id": "pi_123",
                "charge_id": "ch_123",
                "fees": 1.5
            }
        )
        billing_service.payment_repo.create = AsyncMock(return_value=MagicMock(
            id=uuid4(),
            status=PaymentStatus.SUCCEEDED,
            amount_cents=5000,
            processed_at=datetime.now(timezone.utc)
        ))
        billing_service.invoice_repo.update = AsyncMock()
        billing_service.subscription_repo.get_by_id = AsyncMock()
        
        result = await billing_service.process_payment(
            invoice_id=invoice_id,
            payment_method=payment_method,
            payment_provider="stripe",
            created_by="test_user"
        )
        
        assert result is not None
        billing_service.service_integration.process_payment_via_plugin.assert_called_once()
        billing_service.payment_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_payment_invoice_not_found(self, billing_service):
        """Test payment processing with non-existent invoice."""
        invoice_id = uuid4()
        payment_method = {"type": "card", "token": "tok_123"}
        
        billing_service.invoice_repo.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ResourceNotFoundError):
            await billing_service.process_payment(
                invoice_id=invoice_id,
                payment_method=payment_method,
                created_by="test_user"
            )

    @pytest.mark.asyncio
    async def test_process_payment_already_paid(self, billing_service):
        """Test payment processing for already paid invoice."""
        invoice_id = uuid4()
        invoice = MagicMock()
        invoice.status = InvoiceStatus.PAID
        
        billing_service.invoice_repo.get_by_id = AsyncMock(return_value=invoice)
        
        with pytest.raises(BusinessLogicError) as exc_info:
            await billing_service.process_payment(
                invoice_id=invoice_id,
                payment_method={"type": "card"},
                created_by="test_user"
            )
        
        assert "already paid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calculate_usage_billing_success(self, billing_service, sample_subscription, sample_pricing_plan):
        """Test successful usage billing calculation."""
        tenant_id = uuid4()
        usage_data = [
            {
                "metric_name": "api_calls",
                "quantity": 50000,
                "unit_price": 0.001,
                "cost": 50.0,
                "description": "API usage",
                "metadata": {"source": "api_gateway"}
            }
        ]
        
        sample_subscription.pricing_plan = sample_pricing_plan
        billing_service.subscription_repo.get_active_subscription = AsyncMock(return_value=sample_subscription)
        billing_service.plan_repo.get_by_id = AsyncMock(return_value=sample_pricing_plan)
        billing_service.service_integration.calculate_billing_via_plugin = AsyncMock(return_value=Decimal("50.00"))
        billing_service.usage_repo.create = AsyncMock()
        
        result = await billing_service.calculate_usage_billing(
            tenant_id=tenant_id,
            usage_data=usage_data,
            calculator_name="standard"
        )
        
        assert result["total_usage_cost"] == 50.0
        assert result["base_cost"] == 50.0  # From plan base_price_cents / 100
        assert result["total_cost"] == 100.0
        assert result["usage_items"] == 1
        assert result["calculator_used"] == "standard"

    @pytest.mark.asyncio
    async def test_calculate_usage_billing_no_subscription(self, billing_service):
        """Test usage billing calculation with no active subscription."""
        tenant_id = uuid4()
        usage_data = []
        
        billing_service.subscription_repo.get_active_subscription = AsyncMock(return_value=None)
        
        with pytest.raises(SubscriptionNotFoundError):
            await billing_service.calculate_usage_billing(
                tenant_id=tenant_id,
                usage_data=usage_data
            )

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, billing_service, sample_subscription):
        """Test successful subscription cancellation."""
        subscription_id = sample_subscription.id
        
        billing_service.subscription_repo.get_by_id = AsyncMock(return_value=sample_subscription)
        billing_service.service_integration.cancel_subscription_via_plugin = AsyncMock(return_value=True)
        billing_service.subscription_repo.update = AsyncMock(return_value=sample_subscription)
        
        with patch.object(billing_service, '_process_cancellation_refund') as mock_refund:
            result = await billing_service.cancel_subscription(
                subscription_id=subscription_id,
                reason="Customer request",
                immediate=True,
                updated_by="test_user"
            )
            
            assert result is not None
            billing_service.subscription_repo.update.assert_called_once()
            mock_refund.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_subscription_not_found(self, billing_service):
        """Test cancellation of non-existent subscription."""
        subscription_id = uuid4()
        
        billing_service.subscription_repo.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(SubscriptionNotFoundError):
            await billing_service.cancel_subscription(subscription_id=subscription_id)

    @pytest.mark.asyncio
    async def test_cancel_subscription_already_cancelled(self, billing_service, sample_subscription):
        """Test cancellation of already cancelled subscription."""
        subscription_id = sample_subscription.id
        sample_subscription.status = SubscriptionStatus.CANCELLED
        
        billing_service.subscription_repo.get_by_id = AsyncMock(return_value=sample_subscription)
        
        with pytest.raises(BusinessLogicError) as exc_info:
            await billing_service.cancel_subscription(subscription_id=subscription_id)
        
        assert "already cancelled" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_available_payment_providers(self, billing_service):
        """Test getting available payment providers."""
        mock_plugin = MagicMock()
        mock_plugin.meta.name = "stripe"
        mock_plugin.meta.description = "Stripe payment provider"
        mock_plugin.get_supported_currencies.return_value = ["USD", "EUR"]
        mock_plugin.get_supported_payment_methods.return_value = ["card", "ach"]
        mock_plugin.status.value = "active"
        
        billing_service.service_integration.registry.get_plugins_by_type = MagicMock(
            return_value=[mock_plugin]
        )
        
        with patch('services.plugin_billing_service.PaymentProviderPlugin') as MockProvider:
            MockProvider.__instancecheck__ = lambda _, obj: True
            
            providers = await billing_service.get_available_payment_providers()
            
            assert len(providers) == 1
            assert providers[0]["name"] == "stripe"
            assert providers[0]["supported_currencies"] == ["USD", "EUR"]

    @pytest.mark.asyncio
    async def test_get_tenant_billing_overview(self, billing_service, sample_subscription, sample_pricing_plan):
        """Test getting tenant billing overview."""
        tenant_id = uuid4()
        sample_subscription.pricing_plan = sample_pricing_plan
        
        billing_service.subscription_repo.get_active_subscription = AsyncMock(return_value=sample_subscription)
        billing_service.invoice_repo.get_tenant_invoices = AsyncMock(return_value=[])
        billing_service.payment_repo.get_tenant_payments = AsyncMock(return_value=[])
        billing_service.usage_repo.get_subscription_usage = AsyncMock(return_value=[])
        
        with patch.object(billing_service, '_calculate_outstanding_balance', return_value=Decimal("0.00")):
            overview = await billing_service.get_tenant_billing_overview(tenant_id)
            
            assert overview["tenant_id"] == str(tenant_id)
            assert overview["subscription"]["id"] == str(sample_subscription.id)
            assert overview["subscription"]["plan_name"] == sample_pricing_plan.name
            assert overview["outstanding_balance"] == 0.0
            assert "usage_summary" in overview
            assert "recent_invoices" in overview
            assert "recent_payments" in overview

    @pytest.mark.asyncio
    async def test_generate_subscription_invoice(self, billing_service, sample_subscription, sample_pricing_plan):
        """Test subscription invoice generation."""
        subscription_id = sample_subscription.id
        
        billing_service.subscription_repo.get_by_id = AsyncMock(return_value=sample_subscription)
        billing_service.plan_repo.get_by_id = AsyncMock(return_value=sample_pricing_plan)
        billing_service.invoice_repo.count = AsyncMock(return_value=100)
        billing_service.invoice_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
        
        result = await billing_service._generate_subscription_invoice(
            subscription_id=subscription_id,
            created_by="test_user"
        )
        
        assert result is not None
        billing_service.invoice_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_outstanding_balance(self, billing_service):
        """Test outstanding balance calculation."""
        tenant_id = uuid4()
        unpaid_invoices = [
            MagicMock(total_cents=5000),  # $50.00
            MagicMock(total_cents=2500),  # $25.00
        ]
        
        billing_service.invoice_repo.get_unpaid_invoices = AsyncMock(return_value=unpaid_invoices)
        
        balance = await billing_service._calculate_outstanding_balance(tenant_id)
        
        assert balance == Decimal("75.00")

    def test_service_initialization(self, db_session):
        """Test service initialization with dependencies."""
        service = PluginBillingService(db_session)
        
        assert service.db == db_session
        assert service.plan_repo is not None
        assert service.subscription_repo is not None
        assert service.invoice_repo is not None
        assert service.payment_repo is not None
        assert service.usage_repo is not None
        assert service.customer_repo is not None
        assert service.service_integration is not None


@pytest.mark.integration
class TestPluginBillingServiceIntegration:
    """Integration tests for plugin billing service."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_subscription_flow(self, billing_service, sample_pricing_plan, sample_customer):
        """Test complete subscription lifecycle."""
        tenant_id = uuid4()
        
        # Mock all dependencies for end-to-end flow
        billing_service.plan_repo.get_by_id = AsyncMock(return_value=sample_pricing_plan)
        billing_service.subscription_repo.get_active_subscription = AsyncMock(return_value=None)
        billing_service.customer_repo.get_by_id = AsyncMock(return_value=sample_customer)
        billing_service.subscription_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
        billing_service.service_integration.create_subscription_via_plugin = AsyncMock(
            return_value={"subscription_id": "sub_123", "customer_id": "cus_123"}
        )
        
        with patch('services.plugin_billing_service.database_transaction') as mock_tx:
            mock_tx.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_tx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Create subscription
            subscription = await billing_service.create_subscription(
                tenant_id=tenant_id,
                plan_id=sample_pricing_plan.id,
                customer_id=sample_customer.id,
                payment_method={"type": "card", "token": "tok_123"},
                created_by="test_user"
            )
            
            assert subscription is not None
            
            # Verify all steps were called
            billing_service.plan_repo.get_by_id.assert_called_once()
            billing_service.subscription_repo.get_active_subscription.assert_called_once()
            billing_service.customer_repo.get_by_id.assert_called_once()
            billing_service.subscription_repo.create.assert_called_once()