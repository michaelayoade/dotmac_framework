"""
Comprehensive BillingService tests targeting 90% coverage.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.models import (
    BillingCycle,
    BillingPeriodValue,
    InvoiceStatus,
    PaymentStatus,
    SubscriptionStatus,
)
from dotmac_business_logic.billing.core.services import BillingService


class TestBillingServiceComprehensive:
    """Comprehensive tests for BillingService to achieve 90% coverage."""

    @pytest.fixture
    def mock_repository(self):
        """Complete mock billing repository."""
        repo = AsyncMock()

        # Mock subscription
        subscription_mock = Mock()
        subscription_mock.id = uuid4()
        subscription_mock.customer_id = uuid4()
        subscription_mock.status = SubscriptionStatus.ACTIVE
        subscription_mock.billing_cycle = BillingCycle.MONTHLY
        subscription_mock.current_period_start = date(2024, 1, 1)
        subscription_mock.current_period_end = date(2024, 1, 31)
        subscription_mock.next_billing_date = date(2024, 2, 1)
        subscription_mock.trial_end_date = None
        subscription_mock.proration_start_date = None

        # Mock billing plan
        billing_plan_mock = Mock()
        billing_plan_mock.id = uuid4()
        billing_plan_mock.name = "Premium Plan"
        billing_plan_mock.monthly_price = Decimal("99.99")
        billing_plan_mock.taxable = True
        billing_plan_mock.pricing_model = "flat_rate"
        billing_plan_mock.pricing_tiers = None
        subscription_mock.billing_plan = billing_plan_mock

        repo.get_subscription.return_value = subscription_mock
        repo.create_subscription.return_value = subscription_mock

        # Mock invoice
        invoice_mock = Mock()
        invoice_mock.id = uuid4()
        invoice_mock.invoice_number = "INV-20240101"
        invoice_mock.customer_id = subscription_mock.customer_id
        invoice_mock.subscription_id = subscription_mock.id
        invoice_mock.total = Decimal("107.99")
        invoice_mock.currency = "USD"
        invoice_mock.status = InvoiceStatus.PENDING
        repo.create_invoice.return_value = invoice_mock
        repo.get_invoice.return_value = invoice_mock

        # Mock payment
        payment_mock = Mock()
        payment_mock.id = uuid4()
        payment_mock.status = PaymentStatus.PROCESSING
        payment_mock.amount = Decimal("107.99")
        repo.create_payment.return_value = payment_mock
        repo.get_payment_by_idempotency_key.return_value = None

        # Mock due subscriptions for billing run
        repo.get_due_subscriptions.return_value = [subscription_mock]

        return repo

    @pytest.fixture
    def mock_payment_gateway(self):
        """Mock payment gateway."""
        gateway = AsyncMock()
        gateway.charge.return_value = {
            "success": True,
            "transaction_id": "txn_123456789",
            "amount": Decimal("107.99"),
            "currency": "USD",
            "payment_id": str(uuid4())
        }
        return gateway

    @pytest.fixture
    def mock_tax_service(self):
        """Mock tax service with mathematically consistent values."""
        tax_service = AsyncMock()

        # For base amount of $99.99 * 8% tax rate = $7.9992 ≈ $8.00
        # For usage charges: $10.00 * 8% = $0.80, $25.00 * 8% = $2.00
        def calculate_tax_side_effect(amount, service_type=None):
            # Round to 2 decimal places for currency
            return (amount * Decimal("0.08")).quantize(Decimal("0.01"))

        tax_service.calculate_tax.side_effect = calculate_tax_side_effect
        tax_service.get_tax_rate.return_value = Decimal("0.08")
        return tax_service

    @pytest.fixture
    def mock_usage_service(self):
        """Mock usage service."""
        usage_service = AsyncMock()
        usage_service.aggregate_usage.return_value = [
            Mock(meter_type="api_calls", quantity=Decimal("1000"), unit="calls"),
            Mock(meter_type="storage", quantity=Decimal("50"), unit="GB")
        ]
        usage_service.calculate_usage_charges.return_value = [
            {
                "description": "API Calls",
                "amount": Decimal("10.00"),
                "quantity": 1000,
                "unit_price": Decimal("0.01"),
                "taxable": True
            },
            {
                "description": "Storage",
                "amount": Decimal("25.00"),
                "quantity": 50,
                "unit_price": Decimal("0.50"),
                "taxable": True
            }
        ]
        return usage_service

    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service."""
        return AsyncMock()

    @pytest.fixture
    def billing_service(self, mock_repository, mock_payment_gateway, mock_tax_service,
                       mock_usage_service, mock_notification_service):
        """Create BillingService with all mocks."""
        return BillingService(
            repository=mock_repository,
            payment_gateway=mock_payment_gateway,
            tax_service=mock_tax_service,
            usage_service=mock_usage_service,
            notification_service=mock_notification_service,
        )

    # ============= CREATE SUBSCRIPTION TESTS =============

    @pytest.mark.asyncio
    async def test_create_subscription_basic(self, billing_service, mock_repository):
        """Test basic subscription creation."""
        customer_id = uuid4()
        plan_id = uuid4()
        start_date = date(2024, 1, 1)

        result = await billing_service.create_subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            start_date=start_date,
            billing_cycle=BillingCycle.MONTHLY
        )

        assert result is not None
        mock_repository.create_subscription.assert_called_once()
        call_args = mock_repository.create_subscription.call_args[0][0]
        assert call_args["customer_id"] == customer_id
        assert call_args["status"] == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_subscription_with_trial(self, billing_service, mock_repository):
        """Test subscription creation with trial period."""
        customer_id = uuid4()
        plan_id = uuid4()
        start_date = date(2024, 1, 1)
        trial_end_date = date(2024, 1, 15)

        await billing_service.create_subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            start_date=start_date,
            billing_cycle=BillingCycle.MONTHLY,
            trial_end_date=trial_end_date
        )

        call_args = mock_repository.create_subscription.call_args[0][0]
        assert call_args["status"] == SubscriptionStatus.TRIAL
        assert call_args["trial_end_date"] == trial_end_date
        assert call_args["next_billing_date"] == trial_end_date

    # ============= GENERATE INVOICE TESTS =============

    @pytest.mark.asyncio
    async def test_generate_invoice_basic(self, billing_service, mock_repository, mock_tax_service):
        """Test basic invoice generation."""
        subscription_id = uuid4()

        result = await billing_service.generate_invoice(subscription_id)

        assert result is not None
        mock_repository.get_subscription.assert_called_once_with(subscription_id)
        mock_repository.create_invoice.assert_called_once()
        mock_tax_service.calculate_tax.assert_called()

    @pytest.mark.asyncio
    async def test_generate_invoice_with_billing_period(self, billing_service, mock_repository):
        """Test invoice generation with specific billing period."""
        subscription_id = uuid4()
        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        result = await billing_service.generate_invoice(subscription_id, billing_period)

        assert result is not None
        mock_repository.create_invoice.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_invoice_subscription_not_found(self, billing_service, mock_repository):
        """Test invoice generation with non-existent subscription."""
        mock_repository.get_subscription.return_value = None
        subscription_id = uuid4()

        with pytest.raises(ValueError, match="Subscription .* not found"):
            await billing_service.generate_invoice(subscription_id)

    @pytest.mark.asyncio
    async def test_generate_invoice_with_usage_charges(self, billing_service, mock_repository, mock_usage_service):
        """Test invoice generation with usage-based charges."""
        subscription_id = uuid4()

        # Setup subscription with usage-based pricing
        subscription_mock = mock_repository.get_subscription.return_value
        subscription_mock.billing_plan.pricing_model = "usage_based"
        subscription_mock.billing_plan.pricing_tiers = [
            {"tier": 1, "rate": Decimal("0.01"), "limit": 1000}
        ]

        result = await billing_service.generate_invoice(subscription_id)

        assert result is not None
        mock_usage_service.aggregate_usage.assert_called_once()
        mock_usage_service.calculate_usage_charges.assert_called_once()

    # ============= PROCESS PAYMENT TESTS =============

    @pytest.mark.asyncio
    async def test_process_payment_success(self, billing_service, mock_repository, mock_payment_gateway):
        """Test successful payment processing."""
        invoice_id = uuid4()
        payment_method_id = "pm_test_123"

        result = await billing_service.process_payment(invoice_id, payment_method_id)

        assert result is not None
        mock_repository.create_payment.assert_called_once()
        mock_payment_gateway.charge.assert_called_once()
        mock_repository.update_payment_status.assert_called_with(
            result.id, PaymentStatus.SUCCESS
        )

    @pytest.mark.asyncio
    async def test_process_payment_with_amount(self, billing_service, mock_repository, mock_payment_gateway):
        """Test payment processing with specific amount."""
        invoice_id = uuid4()
        payment_method_id = "pm_test_123"
        amount = Decimal("50.00")

        await billing_service.process_payment(invoice_id, payment_method_id, amount)

        # Verify charge was called with correct amount
        charge_call = mock_payment_gateway.charge.call_args
        assert charge_call[1]["amount"] == amount

    @pytest.mark.asyncio
    async def test_process_payment_with_idempotency_key(self, billing_service, mock_repository):
        """Test payment processing with idempotency key."""
        invoice_id = uuid4()
        payment_method_id = "pm_test_123"
        idempotency_key = "idempotent_123"

        # First call - no existing payment
        existing_payment = Mock()
        mock_repository.get_payment_by_idempotency_key.return_value = existing_payment

        result = await billing_service.process_payment(
            invoice_id, payment_method_id, idempotency_key=idempotency_key
        )

        assert result == existing_payment
        mock_repository.get_payment_by_idempotency_key.assert_called_with(idempotency_key)

    @pytest.mark.asyncio
    async def test_process_payment_gateway_failure(self, billing_service, mock_repository, mock_payment_gateway):
        """Test payment processing with gateway failure."""
        invoice_id = uuid4()
        payment_method_id = "pm_test_123"

        # Mock payment gateway to raise exception
        mock_payment_gateway.charge.side_effect = Exception("Gateway error")

        with pytest.raises(Exception, match="Gateway error"):
            await billing_service.process_payment(invoice_id, payment_method_id)

        # Verify payment status updated to failed
        payment_id = mock_repository.create_payment.return_value.id
        mock_repository.update_payment_status.assert_called_with(
            payment_id, PaymentStatus.FAILED
        )

    @pytest.mark.asyncio
    async def test_process_payment_invoice_not_found(self, billing_service, mock_repository):
        """Test payment processing with non-existent invoice."""
        mock_repository.get_invoice.return_value = None
        invoice_id = uuid4()

        with pytest.raises(ValueError, match="Invoice .* not found"):
            await billing_service.process_payment(invoice_id, "pm_test_123")

    @pytest.mark.asyncio
    async def test_process_payment_full_payment_updates_invoice(self, billing_service, mock_repository, mock_payment_gateway):
        """Test that full payment updates invoice status to paid."""
        invoice_id = uuid4()
        payment_method_id = "pm_test_123"

        # Mock invoice with specific total
        invoice_mock = mock_repository.get_invoice.return_value
        invoice_mock.total = Decimal("107.99")

        await billing_service.process_payment(invoice_id, payment_method_id, Decimal("107.99"))

        # Should update invoice to PAID status
        mock_repository.update_invoice_status.assert_called_with(invoice_id, InvoiceStatus.PAID)

    # ============= PROCESS BILLING RUN TESTS =============

    @pytest.mark.asyncio
    async def test_process_billing_run_default_date(self, billing_service, mock_repository):
        """Test billing run processing with default date."""
        result = await billing_service.process_billing_run()

        assert "processed" in result
        assert "errors" in result
        assert "invoices_generated" in result
        assert "errors_detail" in result
        mock_repository.get_due_subscriptions.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_billing_run_specific_date(self, billing_service, mock_repository):
        """Test billing run processing with specific date."""
        as_of_date = date(2024, 1, 31)

        result = await billing_service.process_billing_run(as_of_date)

        mock_repository.get_due_subscriptions.assert_called_once_with(as_of_date)
        assert result["processed"] >= 0

    @pytest.mark.asyncio
    async def test_process_billing_run_with_errors(self, billing_service, mock_repository):
        """Test billing run processing with subscription errors."""
        # Make generate_invoice fail for testing error handling
        mock_repository.create_invoice.side_effect = Exception("Database error")

        result = await billing_service.process_billing_run()

        assert result["errors"] > 0
        assert len(result["errors_detail"]) > 0
        assert "Database error" in str(result["errors_detail"])

    @pytest.mark.asyncio
    async def test_process_billing_run_advances_subscription_period(self, billing_service, mock_repository):
        """Test that billing run advances subscription periods."""
        await billing_service.process_billing_run()

        # Should update subscription for next period
        mock_repository.update_subscription.assert_called()

    # ============= PRIVATE METHOD TESTS =============

    @pytest.mark.asyncio
    async def test_calculate_invoice_line_items_flat_rate(self, billing_service, mock_tax_service):
        """Test line item calculation for flat rate billing."""
        subscription = Mock()
        subscription.proration_start_date = None
        subscription.billing_plan = Mock()
        subscription.billing_plan.name = "Basic Plan"
        subscription.billing_plan.monthly_price = Decimal("29.99")
        subscription.billing_plan.taxable = True
        subscription.billing_plan.pricing_model = "flat_rate"

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_invoice_line_items(subscription, billing_period)

        assert len(line_items) >= 1
        assert any(item.description == "Subscription: Basic Plan" for item in line_items)
        mock_tax_service.calculate_tax.assert_called()

    @pytest.mark.asyncio
    async def test_calculate_invoice_line_items_with_proration(self, billing_service, mock_tax_service):
        """Test line item calculation with proration."""
        subscription = Mock()
        subscription.proration_start_date = date(2024, 1, 15)  # Mid-month start
        subscription.billing_plan = Mock()
        subscription.billing_plan.name = "Pro Plan"
        subscription.billing_plan.monthly_price = Decimal("99.99")
        subscription.billing_plan.taxable = True
        subscription.billing_plan.pricing_model = "flat_rate"

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_invoice_line_items(subscription, billing_period)

        assert len(line_items) >= 1
        # Should have proration applied
        base_item = next(item for item in line_items if "Subscription:" in item.description)
        assert base_item.subtotal.amount < Decimal("99.99")  # Prorated amount

    @pytest.mark.asyncio
    async def test_calculate_usage_charges(self, billing_service, mock_usage_service):
        """Test usage charge calculation."""
        subscription = Mock()
        subscription.id = uuid4()
        subscription.billing_plan = Mock()
        subscription.billing_plan.pricing_tiers = [
            {"tier": 1, "rate": Decimal("0.01"), "limit": 1000}
        ]

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_usage_charges(subscription, billing_period)

        assert len(line_items) >= 1
        mock_usage_service.aggregate_usage.assert_called_once()
        mock_usage_service.calculate_usage_charges.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_billing_period_for_subscription(self, billing_service):
        """Test getting billing period for subscription."""
        subscription = Mock()
        subscription.current_period_start = date(2024, 1, 1)
        subscription.current_period_end = date(2024, 1, 31)
        subscription.billing_cycle = BillingCycle.MONTHLY

        period = await billing_service._get_billing_period_for_subscription(subscription)

        assert isinstance(period, BillingPeriodValue)
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 1, 31)
        assert period.cycle == BillingCycle.MONTHLY

    @pytest.mark.asyncio
    async def test_generate_invoice_number(self, billing_service):
        """Test invoice number generation."""
        invoice_number = await billing_service._generate_invoice_number()

        assert invoice_number.startswith("INV-")
        assert len(invoice_number) > 10  # Should have timestamp

    def test_calculate_next_billing_date(self, billing_service):
        """Test next billing date calculation."""
        current_date = date(2024, 1, 1)

        # Test different billing cycles
        monthly = billing_service._calculate_next_billing_date(current_date, BillingCycle.MONTHLY)
        assert monthly == date(2024, 2, 1)

        quarterly = billing_service._calculate_next_billing_date(current_date, BillingCycle.QUARTERLY)
        assert quarterly == date(2024, 4, 1)

        annually = billing_service._calculate_next_billing_date(current_date, BillingCycle.ANNUALLY)
        assert annually == date(2025, 1, 1)

        one_time = billing_service._calculate_next_billing_date(current_date, BillingCycle.ONE_TIME)
        assert one_time == current_date

    def test_calculate_due_date(self, billing_service):
        """Test due date calculation."""
        billing_end_date = date(2024, 1, 31)

        due_date = billing_service._calculate_due_date(billing_end_date)
        assert due_date == date(2024, 3, 1)  # 30 days after end date

        custom_due_date = billing_service._calculate_due_date(billing_end_date, 15)
        assert custom_due_date == date(2024, 2, 15)  # 15 days after end date

    @pytest.mark.asyncio
    async def test_advance_subscription_period(self, billing_service, mock_repository):
        """Test advancing subscription to next billing period."""
        subscription = Mock()
        subscription.id = uuid4()
        subscription.customer_id = uuid4()
        subscription.current_period_end = date(2024, 1, 31)
        subscription.billing_cycle = BillingCycle.MONTHLY
        subscription.billing_plan = Mock()
        subscription.billing_plan.monthly_price = Decimal("99.99")

        await billing_service._advance_subscription_period(subscription)

        mock_repository.update_subscription.assert_called_once()
        update_call = mock_repository.update_subscription.call_args
        update_data = update_call[0][1]

        assert update_data["current_period_start"] == date(2024, 1, 31)
        assert update_data["current_period_end"] == date(2024, 2, 29)  # Next month end
        assert update_data["next_billing_date"] == date(2024, 2, 29)

    # ============= EDGE CASE AND ERROR HANDLING TESTS =============

    @pytest.mark.asyncio
    async def test_calculate_invoice_line_items_no_tax(self, billing_service, mock_tax_service):
        """Test line item calculation with no tax."""
        mock_tax_service.calculate_tax.return_value = Decimal("0.00")

        subscription = Mock()
        subscription.proration_start_date = None
        subscription.billing_plan = Mock()
        subscription.billing_plan.name = "Tax-Free Plan"
        subscription.billing_plan.monthly_price = Decimal("50.00")
        subscription.billing_plan.taxable = False
        subscription.billing_plan.pricing_model = "flat_rate"

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_invoice_line_items(subscription, billing_period)

        base_item = line_items[0]
        assert base_item.tax_calculation is None

    @pytest.mark.asyncio
    async def test_calculate_invoice_line_items_hybrid_pricing(self, billing_service, mock_usage_service, mock_tax_service):
        """Test line item calculation with hybrid pricing model."""
        subscription = Mock()
        subscription.proration_start_date = None
        subscription.billing_plan = Mock()
        subscription.billing_plan.name = "Hybrid Plan"
        subscription.billing_plan.monthly_price = Decimal("19.99")
        subscription.billing_plan.taxable = True
        subscription.billing_plan.pricing_model = "hybrid"
        subscription.billing_plan.pricing_tiers = [{"tier": 1, "rate": Decimal("0.10")}]

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_invoice_line_items(subscription, billing_period)

        # Should have base subscription + usage charges
        assert len(line_items) > 1
        mock_usage_service.aggregate_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_usage_charges_with_tax(self, billing_service, mock_usage_service, mock_tax_service):
        """Test usage charges with tax calculation."""
        mock_usage_service.calculate_usage_charges.return_value = [
            {
                "description": "Premium API",
                "amount": Decimal("15.00"),
                "quantity": 100,
                "unit_price": Decimal("0.15"),
                "taxable": True
            }
        ]

        subscription = Mock()
        subscription.id = uuid4()
        subscription.billing_plan = Mock()
        subscription.billing_plan.pricing_tiers = []

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_usage_charges(subscription, billing_period)

        assert len(line_items) == 1
        item = line_items[0]
        assert item.description == "Premium API"
        assert item.tax_calculation is not None
        mock_tax_service.calculate_tax.assert_called_with(Decimal("15.00"), service_type="usage")

    @pytest.mark.asyncio
    async def test_usage_charges_non_taxable(self, billing_service, mock_usage_service, mock_tax_service):
        """Test usage charges that are non-taxable."""
        mock_usage_service.calculate_usage_charges.return_value = [
            {
                "description": "Free Tier Usage",
                "amount": Decimal("0.00"),
                "quantity": 50,
                "unit_price": Decimal("0.00"),
                "taxable": False
            }
        ]

        subscription = Mock()
        subscription.id = uuid4()
        subscription.billing_plan = Mock()
        subscription.billing_plan.pricing_tiers = []

        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            cycle=BillingCycle.MONTHLY
        )

        line_items = await billing_service._calculate_usage_charges(subscription, billing_period)

        assert len(line_items) == 1
        item = line_items[0]
        assert item.taxable is False
        assert item.tax_calculation is None
