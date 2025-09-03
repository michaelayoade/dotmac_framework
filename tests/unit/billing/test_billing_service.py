"""
Comprehensive unit tests for the Billing Service.

Tests cover:
- Dashboard data aggregation
- Invoice management and processing
- Payment processing workflows
- Subscription lifecycle management
- Usage tracking and billing cycles
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, List

from dotmac_isp.modules.billing.service import BillingService
from dotmac_isp.modules.billing.models import (
    Invoice, Payment, BillingCustomer, Subscription, UsageRecord,
    InvoiceStatus, PaymentStatus, SubscriptionStatus, BillingCycle
)
from dotmac_isp.modules.billing.repository import (
    BillingCustomerRepository, InvoiceRepository, PaymentRepository,
    SubscriptionRepository, UsageRecordRepository
)


class TestBillingServiceInitialization:
    """Test BillingService initialization and setup."""
    
    @pytest.fixture
    def mock_db_session(self):
        return Mock()
    
    @pytest.fixture
    def tenant_id(self):
        return str(uuid4())
    
    @pytest.fixture
    def billing_service(self, mock_db_session, tenant_id):
        return BillingService(mock_db_session, tenant_id)
    
    def test_service_initialization(self, billing_service, tenant_id):
        """Test billing service initialization with repositories."""
        assert billing_service.tenant_id == tenant_id
        assert isinstance(billing_service.customer_repo, BillingCustomerRepository)
        assert isinstance(billing_service.invoice_repo, InvoiceRepository)
        assert isinstance(billing_service.payment_repo, PaymentRepository)
        assert isinstance(billing_service.subscription_repo, SubscriptionRepository)
        assert isinstance(billing_service.usage_repo, UsageRecordRepository)
    
    def test_service_inherits_base_service(self, billing_service):
        """Test that billing service inherits from BaseService."""
        from dotmac_isp.shared.base_service import BaseService
        assert isinstance(billing_service, BaseService)


class TestBillingDashboard:
    """Test billing dashboard functionality."""
    
    @pytest.fixture
    def billing_service(self):
        service = Mock(spec=BillingService)
        service.get_dashboard_data = AsyncMock()
        service.invoice_repo = Mock()
        service.payment_repo = Mock()
        service.customer_repo = Mock()
        service.subscription_repo = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self, billing_service):
        """Test successful dashboard data retrieval."""
        user_id = str(uuid4())
        expected_data = {
            "total_revenue": Decimal("50000.00"),
            "monthly_revenue": Decimal("12000.00"),
            "invoice_count": 45,
            "pending_payments": 8,
            "active_subscriptions": 120,
            "overdue_invoices": 3,
            "revenue_growth": Decimal("15.5"),
            "customer_count": 85,
            "churn_rate": Decimal("2.1")
        }
        
        billing_service.get_dashboard_data.return_value = expected_data
        
        result = await billing_service.get_dashboard_data(user_id)
        
        assert result == expected_data
        assert result["total_revenue"] == Decimal("50000.00")
        assert result["invoice_count"] == 45
        assert result["active_subscriptions"] == 120
        billing_service.get_dashboard_data.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data_with_filters(self, billing_service):
        """Test dashboard data with date range filters."""
        user_id = str(uuid4())
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        filtered_data = {
            "total_revenue": Decimal("8500.00"),
            "monthly_revenue": Decimal("8500.00"),
            "invoice_count": 12,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }
        
        billing_service.get_dashboard_data.return_value = filtered_data
        
        result = await billing_service.get_dashboard_data(user_id)
        
        assert result["total_revenue"] == Decimal("8500.00")
        assert result["invoice_count"] == 12
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data_empty_results(self, billing_service):
        """Test dashboard data with no billing data."""
        user_id = str(uuid4())
        empty_data = {
            "total_revenue": Decimal("0.00"),
            "monthly_revenue": Decimal("0.00"),
            "invoice_count": 0,
            "pending_payments": 0,
            "active_subscriptions": 0,
            "customer_count": 0
        }
        
        billing_service.get_dashboard_data.return_value = empty_data
        
        result = await billing_service.get_dashboard_data(user_id)
        
        assert result["total_revenue"] == Decimal("0.00")
        assert result["invoice_count"] == 0
        assert result["active_subscriptions"] == 0


class TestInvoiceManagement:
    """Test invoice management functionality."""
    
    @pytest.fixture
    def mock_billing_service(self):
        service = Mock(spec=BillingService)
        service.invoice_repo = Mock()
        service.customer_repo = Mock()
        service.create_invoice = AsyncMock()
        service.process_invoice = AsyncMock()
        service.get_invoice = AsyncMock()
        service.update_invoice_status = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_invoice_data(self):
        return {
            "customer_id": str(uuid4()),
            "billing_period_start": datetime(2024, 1, 1),
            "billing_period_end": datetime(2024, 1, 31),
            "line_items": [
                {
                    "description": "Monthly Service Plan",
                    "quantity": 1,
                    "unit_price": Decimal("99.99"),
                    "total": Decimal("99.99")
                },
                {
                    "description": "Overage Charges",
                    "quantity": 50,
                    "unit_price": Decimal("0.10"),
                    "total": Decimal("5.00")
                }
            ],
            "subtotal": Decimal("104.99"),
            "tax_amount": Decimal("10.50"),
            "total_amount": Decimal("115.49")
        }
    
    @pytest.mark.asyncio
    async def test_create_invoice_success(self, mock_billing_service, sample_invoice_data):
        """Test successful invoice creation."""
        invoice_id = uuid4()
        expected_invoice = Invoice(
            id=invoice_id,
            customer_id=sample_invoice_data["customer_id"],
            total_amount=sample_invoice_data["total_amount"],
            status=InvoiceStatus.DRAFT,
            created_at=datetime.now()
        )
        
        mock_billing_service.create_invoice.return_value = expected_invoice
        
        result = await mock_billing_service.create_invoice(sample_invoice_data)
        
        assert result.id == invoice_id
        assert result.total_amount == Decimal("115.49")
        assert result.status == InvoiceStatus.DRAFT
        mock_billing_service.create_invoice.assert_called_once_with(sample_invoice_data)
    
    @pytest.mark.asyncio
    async def test_process_invoice_success(self, mock_billing_service):
        """Test successful invoice processing."""
        invoice_id = uuid4()
        processed_invoice = Invoice(
            id=invoice_id,
            status=InvoiceStatus.SENT,
            sent_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=30)
        )
        
        mock_billing_service.process_invoice.return_value = processed_invoice
        
        result = await mock_billing_service.process_invoice(invoice_id)
        
        assert result.status == InvoiceStatus.SENT
        assert result.sent_at is not None
        assert result.due_date is not None
        mock_billing_service.process_invoice.assert_called_once_with(invoice_id)
    
    @pytest.mark.asyncio
    async def test_get_invoice_by_id(self, mock_billing_service):
        """Test getting invoice by ID."""
        invoice_id = uuid4()
        expected_invoice = Invoice(
            id=invoice_id,
            customer_id=str(uuid4()),
            total_amount=Decimal("299.99"),
            status=InvoiceStatus.PAID
        )
        
        mock_billing_service.get_invoice.return_value = expected_invoice
        
        result = await mock_billing_service.get_invoice(invoice_id)
        
        assert result.id == invoice_id
        assert result.total_amount == Decimal("299.99")
        assert result.status == InvoiceStatus.PAID
    
    @pytest.mark.asyncio
    async def test_update_invoice_status(self, mock_billing_service):
        """Test updating invoice status."""
        invoice_id = uuid4()
        updated_invoice = Invoice(
            id=invoice_id,
            status=InvoiceStatus.OVERDUE,
            updated_at=datetime.now()
        )
        
        mock_billing_service.update_invoice_status.return_value = updated_invoice
        
        result = await mock_billing_service.update_invoice_status(
            invoice_id, InvoiceStatus.OVERDUE
        )
        
        assert result.status == InvoiceStatus.OVERDUE
        assert result.updated_at is not None
        mock_billing_service.update_invoice_status.assert_called_once_with(
            invoice_id, InvoiceStatus.OVERDUE
        )
    
    @pytest.mark.asyncio
    async def test_create_invoice_with_validation_error(self, mock_billing_service):
        """Test invoice creation with validation errors."""
        invalid_data = {
            "customer_id": "invalid-uuid",  # Invalid UUID format
            "total_amount": Decimal("-100.00")  # Negative amount
        }
        
        mock_billing_service.create_invoice.side_effect = ValueError("Invalid invoice data")
        
        with pytest.raises(ValueError, match="Invalid invoice data"):
            await mock_billing_service.create_invoice(invalid_data)


class TestPaymentProcessing:
    """Test payment processing functionality."""
    
    @pytest.fixture
    def mock_billing_service(self):
        service = Mock(spec=BillingService)
        service.payment_repo = Mock()
        service.process_payment = AsyncMock()
        service.refund_payment = AsyncMock()
        service.get_payment_methods = AsyncMock()
        service.add_payment_method = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_payment_data(self):
        return {
            "invoice_id": str(uuid4()),
            "customer_id": str(uuid4()),
            "amount": Decimal("115.49"),
            "payment_method": "credit_card",
            "payment_details": {
                "card_last_four": "1234",
                "payment_gateway": "stripe",
                "transaction_id": "tx_123456789"
            }
        }
    
    @pytest.mark.asyncio
    async def test_process_payment_success(self, mock_billing_service, sample_payment_data):
        """Test successful payment processing."""
        payment_id = uuid4()
        processed_payment = Payment(
            id=payment_id,
            invoice_id=sample_payment_data["invoice_id"],
            customer_id=sample_payment_data["customer_id"],
            amount=sample_payment_data["amount"],
            status=PaymentStatus.COMPLETED,
            processed_at=datetime.now()
        )
        
        mock_billing_service.process_payment.return_value = processed_payment
        
        result = await mock_billing_service.process_payment(sample_payment_data)
        
        assert result.id == payment_id
        assert result.amount == Decimal("115.49")
        assert result.status == PaymentStatus.COMPLETED
        assert result.processed_at is not None
        mock_billing_service.process_payment.assert_called_once_with(sample_payment_data)
    
    @pytest.mark.asyncio
    async def test_process_payment_failure(self, mock_billing_service, sample_payment_data):
        """Test payment processing failure."""
        failed_payment = Payment(
            id=uuid4(),
            invoice_id=sample_payment_data["invoice_id"],
            amount=sample_payment_data["amount"],
            status=PaymentStatus.FAILED,
            failure_reason="Insufficient funds",
            failed_at=datetime.now()
        )
        
        mock_billing_service.process_payment.return_value = failed_payment
        
        result = await mock_billing_service.process_payment(sample_payment_data)
        
        assert result.status == PaymentStatus.FAILED
        assert result.failure_reason == "Insufficient funds"
        assert result.failed_at is not None
    
    @pytest.mark.asyncio
    async def test_refund_payment(self, mock_billing_service):
        """Test payment refund processing."""
        payment_id = uuid4()
        refund_amount = Decimal("50.00")
        
        refunded_payment = Payment(
            id=payment_id,
            status=PaymentStatus.REFUNDED,
            refunded_amount=refund_amount,
            refunded_at=datetime.now(),
            refund_reason="Customer request"
        )
        
        mock_billing_service.refund_payment.return_value = refunded_payment
        
        result = await mock_billing_service.refund_payment(payment_id, refund_amount, "Customer request")
        
        assert result.status == PaymentStatus.REFUNDED
        assert result.refunded_amount == refund_amount
        assert result.refund_reason == "Customer request"
        mock_billing_service.refund_payment.assert_called_once_with(
            payment_id, refund_amount, "Customer request"
        )
    
    @pytest.mark.asyncio
    async def test_get_payment_methods(self, mock_billing_service):
        """Test getting customer payment methods."""
        customer_id = str(uuid4())
        payment_methods = [
            {
                "id": str(uuid4()),
                "type": "credit_card",
                "last_four": "1234",
                "expiry_month": 12,
                "expiry_year": 2025,
                "is_default": True
            },
            {
                "id": str(uuid4()),
                "type": "bank_account",
                "last_four": "5678",
                "account_type": "checking",
                "is_default": False
            }
        ]
        
        mock_billing_service.get_payment_methods.return_value = payment_methods
        
        result = await mock_billing_service.get_payment_methods(customer_id)
        
        assert len(result) == 2
        assert result[0]["type"] == "credit_card"
        assert result[0]["is_default"] is True
        assert result[1]["type"] == "bank_account"
        mock_billing_service.get_payment_methods.assert_called_once_with(customer_id)


class TestSubscriptionManagement:
    """Test subscription management functionality."""
    
    @pytest.fixture
    def mock_billing_service(self):
        service = Mock(spec=BillingService)
        service.subscription_repo = Mock()
        service.create_subscription = AsyncMock()
        service.update_subscription = AsyncMock()
        service.cancel_subscription = AsyncMock()
        service.renew_subscription = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_subscription_data(self):
        return {
            "customer_id": str(uuid4()),
            "plan_id": str(uuid4()),
            "billing_cycle": BillingCycle.MONTHLY,
            "start_date": datetime.now(),
            "monthly_amount": Decimal("99.99"),
            "features": ["unlimited_bandwidth", "24x7_support", "static_ip"]
        }
    
    @pytest.mark.asyncio
    async def test_create_subscription(self, mock_billing_service, sample_subscription_data):
        """Test subscription creation."""
        subscription_id = uuid4()
        created_subscription = Subscription(
            id=subscription_id,
            customer_id=sample_subscription_data["customer_id"],
            plan_id=sample_subscription_data["plan_id"],
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=sample_subscription_data["billing_cycle"],
            monthly_amount=sample_subscription_data["monthly_amount"],
            start_date=sample_subscription_data["start_date"],
            next_billing_date=sample_subscription_data["start_date"] + timedelta(days=30)
        )
        
        mock_billing_service.create_subscription.return_value = created_subscription
        
        result = await mock_billing_service.create_subscription(sample_subscription_data)
        
        assert result.id == subscription_id
        assert result.status == SubscriptionStatus.ACTIVE
        assert result.monthly_amount == Decimal("99.99")
        assert result.billing_cycle == BillingCycle.MONTHLY
        mock_billing_service.create_subscription.assert_called_once_with(sample_subscription_data)
    
    @pytest.mark.asyncio
    async def test_update_subscription(self, mock_billing_service):
        """Test subscription updates."""
        subscription_id = uuid4()
        update_data = {
            "monthly_amount": Decimal("149.99"),
            "billing_cycle": BillingCycle.ANNUAL,
            "features": ["unlimited_bandwidth", "24x7_support", "static_ip", "priority_routing"]
        }
        
        updated_subscription = Subscription(
            id=subscription_id,
            monthly_amount=update_data["monthly_amount"],
            billing_cycle=update_data["billing_cycle"],
            status=SubscriptionStatus.ACTIVE,
            updated_at=datetime.now()
        )
        
        mock_billing_service.update_subscription.return_value = updated_subscription
        
        result = await mock_billing_service.update_subscription(subscription_id, update_data)
        
        assert result.monthly_amount == Decimal("149.99")
        assert result.billing_cycle == BillingCycle.ANNUAL
        assert result.updated_at is not None
        mock_billing_service.update_subscription.assert_called_once_with(subscription_id, update_data)
    
    @pytest.mark.asyncio
    async def test_cancel_subscription(self, mock_billing_service):
        """Test subscription cancellation."""
        subscription_id = uuid4()
        cancellation_reason = "Customer downgrade request"
        
        cancelled_subscription = Subscription(
            id=subscription_id,
            status=SubscriptionStatus.CANCELLED,
            cancelled_at=datetime.now(),
            cancellation_reason=cancellation_reason,
            end_date=datetime.now() + timedelta(days=30)  # End of current billing cycle
        )
        
        mock_billing_service.cancel_subscription.return_value = cancelled_subscription
        
        result = await mock_billing_service.cancel_subscription(subscription_id, cancellation_reason)
        
        assert result.status == SubscriptionStatus.CANCELLED
        assert result.cancellation_reason == cancellation_reason
        assert result.cancelled_at is not None
        assert result.end_date is not None
        mock_billing_service.cancel_subscription.assert_called_once_with(subscription_id, cancellation_reason)
    
    @pytest.mark.asyncio
    async def test_renew_subscription(self, mock_billing_service):
        """Test subscription renewal."""
        subscription_id = uuid4()
        
        renewed_subscription = Subscription(
            id=subscription_id,
            status=SubscriptionStatus.ACTIVE,
            renewed_at=datetime.now(),
            next_billing_date=datetime.now() + timedelta(days=30),
            renewal_count=1
        )
        
        mock_billing_service.renew_subscription.return_value = renewed_subscription
        
        result = await mock_billing_service.renew_subscription(subscription_id)
        
        assert result.status == SubscriptionStatus.ACTIVE
        assert result.renewed_at is not None
        assert result.renewal_count == 1
        mock_billing_service.renew_subscription.assert_called_once_with(subscription_id)


class TestUsageTracking:
    """Test usage tracking and billing."""
    
    @pytest.fixture
    def mock_billing_service(self):
        service = Mock(spec=BillingService)
        service.usage_repo = Mock()
        service.record_usage = AsyncMock()
        service.get_usage_summary = AsyncMock()
        service.calculate_overage_charges = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_usage_data(self):
        return {
            "customer_id": str(uuid4()),
            "subscription_id": str(uuid4()),
            "usage_type": "bandwidth",
            "amount": Decimal("1024.50"),  # GB
            "unit": "GB",
            "recorded_at": datetime.now(),
            "billing_period_start": datetime(2024, 1, 1),
            "billing_period_end": datetime(2024, 1, 31)
        }
    
    @pytest.mark.asyncio
    async def test_record_usage(self, mock_billing_service, sample_usage_data):
        """Test usage recording."""
        usage_record_id = uuid4()
        usage_record = UsageRecord(
            id=usage_record_id,
            customer_id=sample_usage_data["customer_id"],
            subscription_id=sample_usage_data["subscription_id"],
            usage_type=sample_usage_data["usage_type"],
            amount=sample_usage_data["amount"],
            unit=sample_usage_data["unit"],
            recorded_at=sample_usage_data["recorded_at"]
        )
        
        mock_billing_service.record_usage.return_value = usage_record
        
        result = await mock_billing_service.record_usage(sample_usage_data)
        
        assert result.id == usage_record_id
        assert result.usage_type == "bandwidth"
        assert result.amount == Decimal("1024.50")
        assert result.unit == "GB"
        mock_billing_service.record_usage.assert_called_once_with(sample_usage_data)
    
    @pytest.mark.asyncio
    async def test_get_usage_summary(self, mock_billing_service):
        """Test usage summary retrieval."""
        customer_id = str(uuid4())
        billing_period_start = datetime(2024, 1, 1)
        billing_period_end = datetime(2024, 1, 31)
        
        usage_summary = {
            "customer_id": customer_id,
            "period_start": billing_period_start,
            "period_end": billing_period_end,
            "total_usage": {
                "bandwidth": {"amount": Decimal("2048.75"), "unit": "GB"},
                "storage": {"amount": Decimal("500.00"), "unit": "GB"},
                "api_calls": {"amount": Decimal("150000"), "unit": "requests"}
            },
            "plan_limits": {
                "bandwidth": {"limit": Decimal("2000.00"), "unit": "GB"},
                "storage": {"limit": Decimal("1000.00"), "unit": "GB"},
                "api_calls": {"limit": Decimal("100000"), "unit": "requests"}
            },
            "overages": {
                "bandwidth": {"amount": Decimal("48.75"), "unit": "GB"},
                "api_calls": {"amount": Decimal("50000"), "unit": "requests"}
            }
        }
        
        mock_billing_service.get_usage_summary.return_value = usage_summary
        
        result = await mock_billing_service.get_usage_summary(
            customer_id, billing_period_start, billing_period_end
        )
        
        assert result["customer_id"] == customer_id
        assert result["total_usage"]["bandwidth"]["amount"] == Decimal("2048.75")
        assert result["overages"]["bandwidth"]["amount"] == Decimal("48.75")
        mock_billing_service.get_usage_summary.assert_called_once_with(
            customer_id, billing_period_start, billing_period_end
        )
    
    @pytest.mark.asyncio
    async def test_calculate_overage_charges(self, mock_billing_service):
        """Test overage charge calculation."""
        customer_id = str(uuid4())
        overage_data = {
            "bandwidth": {"amount": Decimal("48.75"), "rate": Decimal("0.10")},
            "api_calls": {"amount": Decimal("50000"), "rate": Decimal("0.001")}
        }
        
        overage_charges = {
            "bandwidth_charges": Decimal("4.88"),  # 48.75 * 0.10
            "api_call_charges": Decimal("50.00"),  # 50000 * 0.001
            "total_overage_charges": Decimal("54.88"),
            "breakdown": overage_data
        }
        
        mock_billing_service.calculate_overage_charges.return_value = overage_charges
        
        result = await mock_billing_service.calculate_overage_charges(customer_id, overage_data)
        
        assert result["total_overage_charges"] == Decimal("54.88")
        assert result["bandwidth_charges"] == Decimal("4.88")
        assert result["api_call_charges"] == Decimal("50.00")
        mock_billing_service.calculate_overage_charges.assert_called_once_with(customer_id, overage_data)


class TestBillingServiceErrorHandling:
    """Test error handling in billing service."""
    
    @pytest.fixture
    def mock_billing_service(self):
        return Mock(spec=BillingService)
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_billing_service):
        """Test handling of database connection errors."""
        mock_billing_service.get_dashboard_data.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await mock_billing_service.get_dashboard_data("user123")
    
    @pytest.mark.asyncio
    async def test_invalid_customer_id(self, mock_billing_service):
        """Test handling of invalid customer ID."""
        mock_billing_service.create_invoice.side_effect = ValueError("Invalid customer ID")
        
        with pytest.raises(ValueError, match="Invalid customer ID"):
            await mock_billing_service.create_invoice({"customer_id": "invalid"})
    
    @pytest.mark.asyncio
    async def test_payment_gateway_error(self, mock_billing_service):
        """Test handling of payment gateway errors."""
        payment_data = {"amount": Decimal("100.00")}
        mock_billing_service.process_payment.side_effect = Exception("Payment gateway timeout")
        
        with pytest.raises(Exception, match="Payment gateway timeout"):
            await mock_billing_service.process_payment(payment_data)
    
    @pytest.mark.asyncio
    async def test_subscription_not_found(self, mock_billing_service):
        """Test handling of subscription not found errors."""
        subscription_id = uuid4()
        mock_billing_service.cancel_subscription.side_effect = ValueError("Subscription not found")
        
        with pytest.raises(ValueError, match="Subscription not found"):
            await mock_billing_service.cancel_subscription(subscription_id, "test reason")


@pytest.mark.asyncio
async def test_billing_service_comprehensive_workflow():
    """Test a comprehensive billing service workflow."""
    # Initialize mock service
    billing_service = Mock(spec=BillingService)
    
    # Setup mock methods
    billing_service.create_subscription = AsyncMock()
    billing_service.record_usage = AsyncMock()
    billing_service.create_invoice = AsyncMock()
    billing_service.process_payment = AsyncMock()
    billing_service.get_dashboard_data = AsyncMock()
    
    # Test data
    customer_id = str(uuid4())
    subscription_id = uuid4()
    invoice_id = uuid4()
    payment_id = uuid4()
    
    # Step 1: Create subscription
    subscription = Subscription(
        id=subscription_id,
        customer_id=customer_id,
        status=SubscriptionStatus.ACTIVE,
        monthly_amount=Decimal("99.99")
    )
    billing_service.create_subscription.return_value = subscription
    
    created_subscription = await billing_service.create_subscription({
        "customer_id": customer_id,
        "monthly_amount": Decimal("99.99")
    })
    assert created_subscription.id == subscription_id
    
    # Step 2: Record usage
    usage_record = UsageRecord(
        id=uuid4(),
        customer_id=customer_id,
        subscription_id=str(subscription_id),
        usage_type="bandwidth",
        amount=Decimal("1500.00")
    )
    billing_service.record_usage.return_value = usage_record
    
    recorded_usage = await billing_service.record_usage({
        "customer_id": customer_id,
        "subscription_id": str(subscription_id),
        "usage_type": "bandwidth",
        "amount": Decimal("1500.00")
    })
    assert recorded_usage.amount == Decimal("1500.00")
    
    # Step 3: Create invoice
    invoice = Invoice(
        id=invoice_id,
        customer_id=customer_id,
        total_amount=Decimal("109.99"),  # Base + overage
        status=InvoiceStatus.SENT
    )
    billing_service.create_invoice.return_value = invoice
    
    created_invoice = await billing_service.create_invoice({
        "customer_id": customer_id,
        "total_amount": Decimal("109.99")
    })
    assert created_invoice.id == invoice_id
    
    # Step 4: Process payment
    payment = Payment(
        id=payment_id,
        invoice_id=str(invoice_id),
        customer_id=customer_id,
        amount=Decimal("109.99"),
        status=PaymentStatus.COMPLETED
    )
    billing_service.process_payment.return_value = payment
    
    processed_payment = await billing_service.process_payment({
        "invoice_id": str(invoice_id),
        "amount": Decimal("109.99")
    })
    assert processed_payment.status == PaymentStatus.COMPLETED
    
    # Step 5: Get dashboard data
    dashboard_data = {
        "total_revenue": Decimal("109.99"),
        "active_subscriptions": 1,
        "paid_invoices": 1
    }
    billing_service.get_dashboard_data.return_value = dashboard_data
    
    final_dashboard = await billing_service.get_dashboard_data("admin_user")
    assert final_dashboard["total_revenue"] == Decimal("109.99")
    assert final_dashboard["active_subscriptions"] == 1
    
    # Verify all methods were called
    billing_service.create_subscription.assert_called_once()
    billing_service.record_usage.assert_called_once()
    billing_service.create_invoice.assert_called_once()
    billing_service.process_payment.assert_called_once()
    billing_service.get_dashboard_data.assert_called_once()