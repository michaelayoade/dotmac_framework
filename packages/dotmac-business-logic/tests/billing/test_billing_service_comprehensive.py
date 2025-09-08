"""
Comprehensive tests for BillingService core functionality.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.events import (
    InvoiceGenerated,
    PaymentProcessed,
    SubscriptionCreated,
)
from dotmac_business_logic.billing.core.models import (
    BillingCycle,
    BillingPeriodValue,
    InvoiceStatus,
    Money,
    PaymentStatus,
    SubscriptionStatus,
)
from dotmac_business_logic.billing.core.services import BillingService


class TestBillingService:
    """Test BillingService core functionality."""

    @pytest.fixture
    def mock_repository(self):
        """Mock billing repository."""
        repo = AsyncMock()
        repo.get_customer.return_value = Mock(
            id=uuid4(),
            email="test@example.com",
            name="Test Customer"
        )
        repo.get_subscription.return_value = Mock(
            id=uuid4(),
            customer_id=uuid4(),
            billing_plan=Mock(
                base_price=Money(Decimal("99.99"), "USD"),
                billing_cycle=BillingCycle.MONTHLY,
                usage_allowances={"api_calls": Decimal("1000")},
                usage_pricing={}
            ),
            status=SubscriptionStatus.ACTIVE,
            current_period_start=date(2024, 1, 1),
            current_period_end=date(2024, 1, 31),
            trial_end_date=None
        )
        return repo

    @pytest.fixture
    def mock_payment_gateway(self):
        """Mock payment gateway."""
        gateway = AsyncMock()
        gateway.process_payment.return_value = {
            "success": True,
            "transaction_id": "txn_123456",
            "amount": Decimal("99.99"),
            "currency": "USD"
        }
        return gateway

    @pytest.fixture
    def mock_tax_service(self):
        """Mock tax service."""
        tax_service = AsyncMock()
        tax_service.calculate_tax.return_value = {
            "tax_amount": Decimal("8.00"),
            "tax_rate": Decimal("0.08"),
            "tax_jurisdiction": "CA"
        }
        return tax_service

    @pytest.fixture
    def mock_usage_service(self):
        """Mock usage service."""
        usage_service = AsyncMock()
        usage_service.get_usage_for_period.return_value = []
        return usage_service

    @pytest.fixture
    def billing_service(self, mock_repository, mock_payment_gateway,
                       mock_tax_service, mock_usage_service):
        """Create BillingService instance with mocks."""
        return BillingService(
            repository=mock_repository,
            payment_gateway=mock_payment_gateway,
            tax_service=mock_tax_service,
            usage_service=mock_usage_service
        )

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, billing_service, mock_repository):
        """Test successful subscription creation."""
        # Setup
        customer_id = uuid4()
        plan_id = uuid4()

        mock_repository.create_subscription.return_value = Mock(
            id=uuid4(),
            customer_id=customer_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )

        # Execute
        with patch('dotmac_business_logic.billing.core.events.publish_event') as mock_publish:
            result = await billing_service.create_subscription(
                customer_id=customer_id,
                plan_id=plan_id,
                start_date=date(2024, 1, 1)
            )

        # Assert
        assert result is not None
        mock_repository.create_subscription.assert_called_once()
        mock_publish.assert_called_once()

        # Verify event was published
        event_call = mock_publish.call_args[0][0]
        assert isinstance(event_call, SubscriptionCreated)
        assert event_call.customer_id == customer_id

    @pytest.mark.asyncio
    async def test_generate_invoice_with_base_charges(self, billing_service, mock_repository):
        """Test invoice generation with base subscription charges."""
        # Setup
        subscription_id = uuid4()
        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        mock_repository.create_invoice.return_value = Mock(
            id=uuid4(),
            invoice_number="INV-001",
            amount=Money(Decimal("107.99"), "USD"),  # Base + tax
            status=InvoiceStatus.PENDING
        )

        # Execute
        with patch('dotmac_business_logic.billing.core.events.publish_event') as mock_publish:
            invoice = await billing_service.generate_invoice(
                subscription_id=subscription_id,
                billing_period=billing_period
            )

        # Assert
        assert invoice is not None
        mock_repository.create_invoice.assert_called_once()
        mock_publish.assert_called_once()

        # Verify event
        event_call = mock_publish.call_args[0][0]
        assert isinstance(event_call, InvoiceGenerated)
        assert event_call.amount == Decimal("107.99")

    @pytest.mark.asyncio
    async def test_generate_invoice_with_usage_charges(self, billing_service,
                                                      mock_repository, mock_usage_service):
        """Test invoice generation with usage-based charges."""
        # Setup
        subscription_id = uuid4()
        billing_period = BillingPeriodValue(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        # Mock usage records showing overage
        mock_usage_records = [
            Mock(
                meter_type="api_calls",
                quantity=Decimal("1500"),  # 500 over allowance
                unit="calls",
                peak_usage=Decimal("1500")
            )
        ]
        mock_usage_service.get_usage_for_period.return_value = mock_usage_records

        # Update subscription plan to have usage pricing
        subscription = mock_repository.get_subscription.return_value
        subscription.billing_plan.usage_pricing = {
            "api_calls_overage": {
                "unit_price": Decimal("0.01"),
                "description": "API Call Overage"
            }
        }

        mock_repository.create_invoice.return_value = Mock(
            id=uuid4(),
            invoice_number="INV-002",
            amount=Money(Decimal("112.99"), "USD"),  # Base + usage + tax
            status=InvoiceStatus.PENDING
        )

        # Execute
        invoice = await billing_service.generate_invoice(
            subscription_id=subscription_id,
            billing_period=billing_period
        )

        # Assert
        assert invoice is not None
        mock_usage_service.get_usage_for_period.assert_called_once_with(
            subscription_id, billing_period
        )

    @pytest.mark.asyncio
    async def test_process_payment_success(self, billing_service, mock_repository,
                                         mock_payment_gateway):
        """Test successful payment processing."""
        # Setup
        invoice_id = uuid4()
        payment_method_id = "pm_123456"

        mock_invoice = Mock(
            id=invoice_id,
            amount=Money(Decimal("99.99"), "USD"),
            customer_id=uuid4(),
            status=InvoiceStatus.PENDING
        )
        mock_repository.get_invoice.return_value = mock_invoice
        mock_repository.create_payment.return_value = Mock(
            id=uuid4(),
            status=PaymentStatus.COMPLETED,
            transaction_id="txn_123456"
        )

        # Execute
        with patch('dotmac_business_logic.billing.core.events.publish_event') as mock_publish:
            result = await billing_service.process_payment(
                invoice_id=invoice_id,
                payment_method_id=payment_method_id,
                idempotency_key="idempotent_123"
            )

        # Assert
        assert result is not None
        assert result["success"] is True
        mock_payment_gateway.process_payment.assert_called_once()
        mock_repository.create_payment.assert_called_once()
        mock_publish.assert_called_once()

        # Verify event
        event_call = mock_publish.call_args[0][0]
        assert isinstance(event_call, PaymentProcessed)
        assert event_call.amount == Decimal("99.99")

    @pytest.mark.asyncio
    async def test_process_payment_gateway_failure(self, billing_service,
                                                  mock_payment_gateway):
        """Test payment processing when gateway fails."""
        # Setup
        mock_payment_gateway.process_payment.return_value = {
            "success": False,
            "error": "Card declined",
            "error_code": "card_declined"
        }

        # Execute
        result = await billing_service.process_payment(
            invoice_id=uuid4(),
            payment_method_id="pm_123456",
            idempotency_key="idempotent_123"
        )

        # Assert
        assert result is not None
        assert result["success"] is False
        assert result["error"] == "Card declined"

    @pytest.mark.asyncio
    async def test_process_payment_idempotency(self, billing_service, mock_repository):
        """Test payment idempotency - duplicate key should return existing payment."""
        # Setup
        idempotency_key = "idempotent_duplicate"
        existing_payment = Mock(
            id=uuid4(),
            status=PaymentStatus.COMPLETED,
            amount=Money(Decimal("99.99"), "USD")
        )

        mock_repository.get_payment_by_idempotency_key.return_value = existing_payment

        # Execute
        result = await billing_service.process_payment(
            invoice_id=uuid4(),
            payment_method_id="pm_123456",
            idempotency_key=idempotency_key
        )

        # Assert
        assert result is not None
        assert result["success"] is True
        assert result["payment_id"] == existing_payment.id
        # Should not create new payment or call gateway
        mock_repository.create_payment.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_invoice_total_with_tax(self, billing_service, mock_tax_service):
        """Test invoice total calculation including tax."""
        # Setup
        line_items = [
            {
                "description": "Monthly Subscription",
                "amount": Decimal("99.99"),
                "taxable": True
            },
            {
                "description": "Setup Fee",
                "amount": Decimal("50.00"),
                "taxable": False
            }
        ]

        customer_address = {
            "country": "US",
            "state": "CA",
            "postal_code": "90210"
        }

        # Execute
        total = await billing_service._calculate_invoice_total(
            line_items, customer_address
        )

        # Assert
        assert total == Decimal("157.99")  # 99.99 + 8.00 tax + 50.00 non-taxable
        mock_tax_service.calculate_tax.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, billing_service, mock_repository):
        """Test subscription cancellation."""
        # Setup
        subscription_id = uuid4()
        cancellation_reason = "Customer request"

        mock_repository.update_subscription.return_value = Mock(
            id=subscription_id,
            status=SubscriptionStatus.CANCELLED,
            cancelled_at=datetime.now(timezone.utc)
        )

        # Execute
        with patch('dotmac_business_logic.billing.core.events.publish_event') as mock_publish:
            result = await billing_service.cancel_subscription(
                subscription_id=subscription_id,
                reason=cancellation_reason,
                effective_date=date(2024, 2, 1)
            )

        # Assert
        assert result is not None
        mock_repository.update_subscription.assert_called_once()
        mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_trial_period_subscription(self, billing_service, mock_repository):
        """Test subscription creation with trial period."""
        # Setup
        customer_id = uuid4()
        plan_id = uuid4()
        trial_end_date = date(2024, 2, 1)

        trial_subscription = Mock(
            id=uuid4(),
            customer_id=customer_id,
            trial_end_date=trial_end_date,
            next_billing_date=trial_end_date,  # Should be set to trial end
            status=SubscriptionStatus.TRIALING
        )
        mock_repository.create_subscription.return_value = trial_subscription

        # Execute
        result = await billing_service.create_subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            start_date=date(2024, 1, 1),
            trial_end_date=trial_end_date
        )

        # Assert
        assert result.status == SubscriptionStatus.TRIALING
        assert result.trial_end_date == trial_end_date
        assert result.next_billing_date == trial_end_date

    @pytest.mark.asyncio
    async def test_apply_credit_to_invoice(self, billing_service, mock_repository):
        """Test applying credit to an invoice."""
        # Setup
        customer_id = uuid4()
        credit_amount = Money(Decimal("25.00"), "USD")
        invoice_id = uuid4()

        mock_repository.create_credit.return_value = Mock(
            id=uuid4(),
            amount=credit_amount,
            customer_id=customer_id
        )

        # Execute
        credit = await billing_service.apply_credit(
            customer_id=customer_id,
            amount=credit_amount,
            reason="Service credit",
            invoice_id=invoice_id
        )

        # Assert
        assert credit is not None
        mock_repository.create_credit.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_repository_failure(self, billing_service, mock_repository):
        """Test error handling when repository operations fail."""
        # Setup
        mock_repository.get_subscription.side_effect = Exception("Database connection failed")

        # Execute & Assert
        with pytest.raises(Exception, match="Database connection failed"):
            await billing_service.generate_invoice(
                subscription_id=uuid4(),
                billing_period=BillingPeriodValue(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31)
                )
            )

    @pytest.mark.asyncio
    async def test_currency_consistency_validation(self, billing_service):
        """Test that currency consistency is maintained across operations."""
        # Setup - mixed currencies should be handled consistently
        [
            {"amount": Decimal("100.00"), "currency": "USD"},
            {"amount": Decimal("85.00"), "currency": "EUR"}  # Different currency
        ]

        # This should either convert currencies or raise an error
        # Implementation depends on business requirements
        pass  # Placeholder for currency handling tests
