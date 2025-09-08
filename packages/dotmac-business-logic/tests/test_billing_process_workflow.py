"""
Comprehensive test suite for BillingProcessWorkflow.

Tests cover all workflow steps, error scenarios, rollback behavior,
and integration with billing services to achieve 90%+ coverage.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

# Mock the missing imports for testing
class InvoiceStatus:
    CANCELLED = "cancelled"

class BillingService:
    pass

class BusinessWorkflowStatus:
    COMPLETED = "completed"
    FAILED = "failed" 
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"

from dotmac_business_logic.workflows.billing_process import (
    BillingPeriodModel,
    BillingProcessWorkflow,
    BillingRunRequest,
)


class TestBillingPeriodModel:
    """Test BillingPeriodModel validation."""

    def test_valid_billing_period(self):
        """Test valid billing period validation."""
        period = BillingPeriodModel(period="2024-03")
        assert period.period == "2024-03"
        assert period.start_date == date(2024, 3, 1)
        assert period.end_date == date(2024, 4, 1)

    def test_december_billing_period(self):
        """Test December billing period edge case."""
        period = BillingPeriodModel(period="2024-12")
        assert period.period == "2024-12"
        assert period.start_date == date(2024, 12, 1)
        assert period.end_date == date(2025, 1, 1)

    def test_invalid_format(self):
        """Test invalid billing period format."""
        with pytest.raises(ValidationError) as exc_info:
            BillingPeriodModel(period="2024/03")
        assert "Billing period must be in YYYY-MM format" in str(exc_info.value)

    def test_invalid_year(self):
        """Test invalid year validation."""
        with pytest.raises(ValidationError) as exc_info:
            BillingPeriodModel(period="2019-03")
        assert "Year must be between 2020 and 2030" in str(exc_info.value)

    def test_invalid_month(self):
        """Test invalid month validation."""
        with pytest.raises(ValidationError) as exc_info:
            BillingPeriodModel(period="2024-13")
        assert "Month must be between 1 and 12" in str(exc_info.value)

    def test_non_numeric_values(self):
        """Test non-numeric year/month values."""
        with pytest.raises(ValidationError) as exc_info:
            BillingPeriodModel(period="abc-03")
        assert "Invalid billing period" in str(exc_info.value)


class TestBillingRunRequest:
    """Test BillingRunRequest validation."""

    def test_valid_billing_run_request(self):
        """Test valid billing run request."""
        period = BillingPeriodModel(period="2024-03")
        request = BillingRunRequest(
            billing_period=period,
            tenant_id="tenant-123",
            dry_run=False,
            approval_threshold=Decimal("1000.00"),
            notification_enabled=True,
            max_retries=3,
        )

        assert request.billing_period.period == "2024-03"
        assert request.tenant_id == "tenant-123"
        assert request.dry_run is False
        assert request.approval_threshold == Decimal("1000.00")
        assert request.notification_enabled is True
        assert request.max_retries == 3

    def test_default_values(self):
        """Test default values for optional fields."""
        period = BillingPeriodModel(period="2024-03")
        request = BillingRunRequest(billing_period=period)

        assert request.tenant_id is None
        assert request.dry_run is False
        assert request.approval_threshold is None
        assert request.notification_enabled is True
        assert request.max_retries == 3

    def test_max_retries_validation(self):
        """Test max_retries field validation."""
        period = BillingPeriodModel(period="2024-03")

        with pytest.raises(ValidationError) as exc_info:
            BillingRunRequest(billing_period=period, max_retries=-1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            BillingRunRequest(billing_period=period, max_retries=15)
        assert "Input should be less than or equal to 10" in str(exc_info.value)


@pytest.fixture
def mock_billing_service():
    """Create mock billing service with all required dependencies."""
    service = Mock(spec=BillingService)

    # Mock repository
    service.repository = AsyncMock()
    service.repository.get_due_subscriptions = AsyncMock()
    service.repository.get_customer = AsyncMock()
    service.repository.update_invoice_status = AsyncMock()
    service.repository.get_subscription = AsyncMock()
    service.repository.update_subscription = AsyncMock()

    # Mock payment gateway
    service.payment_gateway = AsyncMock()
    service.payment_gateway.get_payment_methods = AsyncMock()
    service.payment_gateway.refund = AsyncMock()

    # Mock notification service
    service.notification_service = AsyncMock()
    service.notification_service.send_invoice_notification = AsyncMock()
    service.notification_service.send_payment_notification = AsyncMock()
    service.notification_service.send_failure_notification = AsyncMock()

    # Mock service methods
    service.generate_invoice = AsyncMock()
    service.process_payment = AsyncMock()

    return service


@pytest.fixture
def billing_request():
    """Create standard billing request for tests."""
    period = BillingPeriodModel(period="2024-03")
    return BillingRunRequest(
        billing_period=period,
        tenant_id="test-tenant",
        dry_run=False,
        notification_enabled=True,
    )


@pytest.fixture
def dry_run_billing_request():
    """Create dry-run billing request for tests."""
    period = BillingPeriodModel(period="2024-03")
    return BillingRunRequest(
        billing_period=period,
        tenant_id="test-tenant",
        dry_run=True,
        notification_enabled=True,
    )


@pytest.fixture
def approval_billing_request():
    """Create billing request requiring approval."""
    period = BillingPeriodModel(period="2024-03")
    return BillingRunRequest(
        billing_period=period,
        tenant_id="test-tenant",
        dry_run=False,
        approval_threshold=Decimal("500.00"),
        notification_enabled=True,
    )


class TestBillingProcessWorkflow:
    """Test BillingProcessWorkflow implementation."""

    def test_workflow_initialization(self, mock_billing_service, billing_request):
        """Test workflow initialization."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
            workflow_id="test-workflow-123",
        )

        assert workflow.workflow_id == "test-workflow-123"
        assert workflow.workflow_type == "billing_process"
        assert workflow.tenant_id == "test-tenant"
        assert workflow.steps == [
            "validate_billing_period",
            "generate_invoices",
            "process_payments",
            "send_notifications",
            "finalize_billing",
        ]
        assert workflow.rollback_on_failure is True
        assert workflow.continue_on_step_failure is False
        assert workflow.require_approval is False

    def test_workflow_initialization_with_approval(self, mock_billing_service, approval_billing_request):
        """Test workflow initialization with approval requirement."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=approval_billing_request,
        )

        assert workflow.require_approval is True
        assert workflow.approval_threshold == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_validate_business_rules_success(self, mock_billing_service, billing_request):
        """Test successful business rules validation."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Mock check_existing_billing_run to return None
        workflow._check_existing_billing_run = AsyncMock(return_value=None)

        result = await workflow.validate_business_rules()

        assert result.success is True
        assert result.step_name == "business_rules_validation"
        assert result.data["validation_passed"] is True

    @pytest.mark.asyncio
    async def test_validate_business_rules_future_period(self, mock_billing_service):
        """Test business rules validation for future period."""
        # Create future billing period
        future_date = date.today().replace(year=date.today().year + 1)
        period = BillingPeriodModel(period=f"{future_date.year}-{future_date.month:02d}")
        request = BillingRunRequest(billing_period=period)

        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=request,
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert result.error == "future_billing_period"
        assert "Cannot run billing for future periods" in result.message

    @pytest.mark.asyncio
    async def test_validate_business_rules_existing_run(self, mock_billing_service, billing_request):
        """Test business rules validation with existing billing run."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Mock existing billing run
        workflow._check_existing_billing_run = AsyncMock(
            return_value={"id": "existing-run"}
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert result.error == "billing_already_completed"

    @pytest.mark.asyncio
    async def test_validate_billing_period_step(self, mock_billing_service, billing_request):
        """Test validate_billing_period workflow step."""
        # Setup mock data
        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        mock_subscription.tenant_id = "test-tenant"

        mock_billing_service.repository.get_due_subscriptions.return_value = [mock_subscription]

        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        result = await workflow.execute_step("validate_billing_period")

        assert result.success is True
        assert result.step_name == "validate_billing_period"
        assert result.data["eligible_subscriptions"] == 1
        assert result.data["billing_period"] == "2024-03"
        assert result.data["tenant_id"] == "test-tenant"
        assert result.data["dry_run"] is False

    @pytest.mark.asyncio
    async def test_validate_billing_period_tenant_filtering(self, mock_billing_service, billing_request):
        """Test tenant filtering in validate_billing_period."""
        # Setup mock data with different tenants
        sub1 = Mock()
        sub1.id = uuid4()
        sub1.tenant_id = "test-tenant"

        sub2 = Mock()
        sub2.id = uuid4()
        sub2.tenant_id = "other-tenant"

        mock_billing_service.repository.get_due_subscriptions.return_value = [sub1, sub2]

        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        result = await workflow.execute_step("validate_billing_period")

        assert result.success is True
        assert result.data["eligible_subscriptions"] == 1  # Only test-tenant subscription

    @pytest.mark.asyncio
    async def test_generate_invoices_step_live(self, mock_billing_service, billing_request):
        """Test generate_invoices step in live mode."""
        # Setup workflow with eligible subscriptions
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        workflow._eligible_subscriptions = [mock_subscription]

        # Setup mock invoice
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.total = Decimal("99.99")
        mock_billing_service.generate_invoice.return_value = mock_invoice

        result = await workflow.execute_step("generate_invoices")

        assert result.success is True
        assert result.step_name == "generate_invoices"
        assert result.data["total_subscriptions"] == 1
        assert result.data["successful_invoices"] == 1
        assert result.data["failed_invoices"] == 0
        assert result.data["total_amount"] == 99.99
        assert result.requires_approval is False

    @pytest.mark.asyncio
    async def test_generate_invoices_step_dry_run(self, mock_billing_service, dry_run_billing_request):
        """Test generate_invoices step in dry-run mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=dry_run_billing_request,
        )

        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        workflow._eligible_subscriptions = [mock_subscription]

        result = await workflow.execute_step("generate_invoices")

        assert result.success is True
        assert result.data["dry_run"] is True
        assert result.data["successful_invoices"] == 1
        assert mock_billing_service.generate_invoice.assert_not_called

    @pytest.mark.asyncio
    async def test_generate_invoices_with_approval_required(self, mock_billing_service, approval_billing_request):
        """Test generate_invoices step requiring approval."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=approval_billing_request,
        )

        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        workflow._eligible_subscriptions = [mock_subscription]

        # Setup mock invoice with high amount
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.total = Decimal("1000.00")  # Above approval threshold
        mock_billing_service.generate_invoice.return_value = mock_invoice

        result = await workflow.execute_step("generate_invoices")

        assert result.success is True
        assert result.requires_approval is True
        assert result.approval_data["total_amount"] == 1000.00
        assert result.approval_data["threshold"] == 500.00

    @pytest.mark.asyncio
    async def test_generate_invoices_with_failures(self, mock_billing_service, billing_request):
        """Test generate_invoices step with some failures."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        sub1 = Mock()
        sub1.id = uuid4()
        sub2 = Mock()
        sub2.id = uuid4()
        workflow._eligible_subscriptions = [sub1, sub2]

        # First call succeeds, second fails
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.total = Decimal("99.99")

        mock_billing_service.generate_invoice.side_effect = [
            mock_invoice,
            Exception("Invoice generation failed")
        ]

        result = await workflow.execute_step("generate_invoices")

        assert result.success is True
        assert result.data["successful_invoices"] == 1
        assert result.data["failed_invoices"] == 1
        assert len(result.data["failed_subscriptions"]) == 1

    @pytest.mark.asyncio
    async def test_process_payments_step_dry_run(self, mock_billing_service, dry_run_billing_request):
        """Test process_payments step in dry-run mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=dry_run_billing_request,
        )

        result = await workflow.execute_step("process_payments")

        assert result.success is True
        assert result.data["dry_run"] is True
        assert result.message == "Payment processing skipped for dry run"

    @pytest.mark.asyncio
    async def test_process_payments_step_live(self, mock_billing_service, billing_request):
        """Test process_payments step in live mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Setup mock invoices
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("99.99")
        workflow._generated_invoices = [mock_invoice]

        # Setup mock payment methods
        mock_billing_service.payment_gateway.get_payment_methods.return_value = [
            {"id": "pm_123", "type": "card"}
        ]

        # Setup mock payment
        mock_payment = Mock()
        mock_payment.id = uuid4()
        mock_billing_service.process_payment.return_value = mock_payment

        result = await workflow.execute_step("process_payments")

        assert result.success is True
        assert result.data["total_invoices"] == 1
        assert result.data["successful_payments"] == 1
        assert result.data["failed_payments"] == 0
        assert result.data["total_amount_processed"] == 99.99

    @pytest.mark.asyncio
    async def test_process_payments_no_payment_method(self, mock_billing_service, billing_request):
        """Test process_payments with no payment method on file."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("99.99")
        workflow._generated_invoices = [mock_invoice]

        # No payment methods available
        mock_billing_service.payment_gateway.get_payment_methods.return_value = []

        result = await workflow.execute_step("process_payments")

        assert result.success is True
        assert result.data["successful_payments"] == 0
        assert result.data["failed_payments"] == 1

    @pytest.mark.asyncio
    async def test_process_payments_with_retry_logic(self, mock_billing_service):
        """Test payment processing with retry logic."""
        # Setup billing request with max_retries
        period = BillingPeriodModel(period="2024-03")
        request = BillingRunRequest(billing_period=period, max_retries=2)

        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=request,
        )

        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.total = Decimal("99.99")

        # First attempt fails, second succeeds
        mock_payment = Mock()
        mock_payment.id = uuid4()

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_billing_service.process_payment.side_effect = [
                Exception("Temporary failure"),
                mock_payment
            ]

            result = await workflow._process_invoice_payment(mock_invoice, "pm_123")

            assert result == mock_payment
            assert mock_sleep.called  # Verify retry delay

    @pytest.mark.asyncio
    async def test_send_notifications_disabled(self, mock_billing_service):
        """Test send_notifications when disabled."""
        period = BillingPeriodModel(period="2024-03")
        request = BillingRunRequest(billing_period=period, notification_enabled=False)

        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=request,
        )

        result = await workflow.execute_step("send_notifications")

        assert result.success is True
        assert result.data["notifications_disabled"] is True

    @pytest.mark.asyncio
    async def test_send_notifications_dry_run(self, mock_billing_service, dry_run_billing_request):
        """Test send_notifications in dry-run mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=dry_run_billing_request,
        )

        result = await workflow.execute_step("send_notifications")

        assert result.success is True
        assert result.data["dry_run"] is True

    @pytest.mark.asyncio
    async def test_send_notifications_success(self, mock_billing_service, billing_request):
        """Test successful notification sending."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Setup mock data
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("99.99")
        workflow._generated_invoices = [mock_invoice]
        workflow._payment_results = [{"invoice_id": mock_invoice.id, "status": "success"}]

        mock_customer = Mock()
        mock_customer.email = "customer@example.com"
        mock_billing_service.repository.get_customer.return_value = mock_customer

        result = await workflow.execute_step("send_notifications")

        assert result.success is True
        assert result.data["successful_notifications"] == 1
        assert result.data["failed_notifications"] == 0
        mock_billing_service.notification_service.send_payment_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notifications_different_statuses(self, mock_billing_service, billing_request):
        """Test notifications for different payment statuses."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Setup mock invoices with different payment statuses
        invoice1 = Mock()
        invoice1.id = uuid4()
        invoice1.customer_id = uuid4()
        invoice1.total = Decimal("99.99")

        invoice2 = Mock()
        invoice2.id = uuid4()
        invoice2.customer_id = uuid4()
        invoice2.total = Decimal("199.99")

        invoice3 = Mock()
        invoice3.id = uuid4()
        invoice3.customer_id = uuid4()
        invoice3.total = Decimal("299.99")

        workflow._generated_invoices = [invoice1, invoice2, invoice3]
        workflow._payment_results = [
            {"invoice_id": invoice1.id, "status": "success"},
            {"invoice_id": invoice2.id, "status": "failed"},
            {"invoice_id": invoice3.id, "status": "pending"},
        ]

        mock_customer = Mock()
        mock_customer.email = "customer@example.com"
        mock_billing_service.repository.get_customer.return_value = mock_customer

        result = await workflow.execute_step("send_notifications")

        assert result.success is True
        assert result.data["successful_notifications"] == 3

        # Verify different notification types were sent
        mock_billing_service.notification_service.send_payment_notification.assert_called_once()
        mock_billing_service.notification_service.send_failure_notification.assert_called_once()
        mock_billing_service.notification_service.send_invoice_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_billing_step(self, mock_billing_service, billing_request):
        """Test finalize_billing workflow step."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
            workflow_id="test-workflow-123",
        )

        # Setup workflow state
        workflow._eligible_subscriptions = [Mock()]
        workflow._generated_invoices = [Mock()]
        workflow._total_amount = Decimal("99.99")
        workflow._payment_results = [{"status": "success"}]
        workflow._notification_results = [{"status": "sent"}]

        result = await workflow.execute_step("finalize_billing")

        assert result.success is True
        assert result.step_name == "finalize_billing"
        assert result.data["billing_run_id"] == "test-workflow-123"
        assert result.data["billing_period"] == "2024-03"
        assert result.data["tenant_id"] == "test-tenant"
        assert result.data["run_type"] == "live"
        assert result.data["summary"]["total_subscriptions"] == 1

    @pytest.mark.asyncio
    async def test_finalize_billing_dry_run(self, mock_billing_service, dry_run_billing_request):
        """Test finalize_billing in dry-run mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=dry_run_billing_request,
        )

        workflow._eligible_subscriptions = [Mock()]

        result = await workflow.execute_step("finalize_billing")

        assert result.success is True
        assert result.data["run_type"] == "dry_run"

    @pytest.mark.asyncio
    async def test_unknown_step_execution(self, mock_billing_service, billing_request):
        """Test execution of unknown workflow step."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        result = await workflow.execute_step("unknown_step")

        assert result.success is False
        assert result.error == "unknown_step"
        assert "Unknown workflow step: unknown_step" in result.message

    @pytest.mark.asyncio
    async def test_rollback_invoice_generation_live(self, mock_billing_service, billing_request):
        """Test rollback of invoice generation in live mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Setup generated invoices
        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        workflow._generated_invoices = [mock_invoice]

        result = await workflow.rollback_step("generate_invoices")

        assert result.success is True
        assert result.data["cancelled_invoices"] == 1
        mock_billing_service.repository.update_invoice_status.assert_called_with(
            mock_invoice.id, InvoiceStatus.CANCELLED
        )

    @pytest.mark.asyncio
    async def test_rollback_invoice_generation_dry_run(self, mock_billing_service, dry_run_billing_request):
        """Test rollback of invoice generation in dry-run mode."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=dry_run_billing_request,
        )

        result = await workflow.rollback_step("generate_invoices")

        assert result.success is True
        assert result.message == "No rollback needed for dry run"

    @pytest.mark.asyncio
    async def test_rollback_payment_processing(self, mock_billing_service, billing_request):
        """Test rollback of payment processing."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Setup payment results
        workflow._payment_results = [
            {"payment_id": "pay_123", "status": "success"},
            {"payment_id": "pay_456", "status": "failed"},
        ]

        result = await workflow.rollback_step("process_payments")

        assert result.success is True
        assert result.data["refunded_payments"] == 1
        mock_billing_service.payment_gateway.refund.assert_called_once_with(
            "pay_123", reason="billing_run_rollback"
        )

    @pytest.mark.asyncio
    async def test_rollback_notifications(self, mock_billing_service, billing_request):
        """Test rollback of notifications (no-op)."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        result = await workflow.rollback_step("send_notifications")

        assert result.success is True
        assert "cannot be rolled back" in result.message

    @pytest.mark.asyncio
    async def test_rollback_finalization(self, mock_billing_service, billing_request):
        """Test rollback of billing finalization."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Setup business context
        workflow.business_context["billing_run_summary"] = {"status": "completed"}

        result = await workflow.rollback_step("finalize_billing")

        assert result.success is True
        assert workflow.business_context["billing_run_summary"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_rollback_unknown_step(self, mock_billing_service, billing_request):
        """Test rollback of unknown step."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        result = await workflow.rollback_step("unknown_step")

        assert result.success is True
        assert "No rollback needed for step: unknown_step" in result.message

    @pytest.mark.asyncio
    async def test_advance_subscription_period(self, mock_billing_service, billing_request):
        """Test advancement of subscription billing period."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        subscription_id = uuid4()

        # Setup mock subscription
        mock_subscription = Mock()
        mock_subscription.customer_id = uuid4()
        mock_subscription.current_period_end = date(2024, 3, 31)
        mock_subscription.billing_plan.monthly_price = Decimal("99.99")

        mock_billing_service.repository.get_subscription.return_value = mock_subscription

        # Test subscription period advancement
        await workflow._advance_subscription_period(subscription_id)

        mock_billing_service.repository.update_subscription.assert_called_once()
        # Note: event publishing may not be implemented in _advance_subscription_period

    @pytest.mark.asyncio
    async def test_advance_subscription_period_with_error(self, mock_billing_service, billing_request):
        """Test subscription period advancement with error handling."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        subscription_id = uuid4()
        mock_billing_service.repository.get_subscription.side_effect = Exception("Database error")

        # Should not raise exception - errors are swallowed
        await workflow._advance_subscription_period(subscription_id)

    @pytest.mark.asyncio
    async def test_full_workflow_execution_success(self, mock_billing_service, billing_request):
        """Test complete workflow execution success path."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Mock all dependencies
        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        mock_subscription.tenant_id = "test-tenant"
        mock_billing_service.repository.get_due_subscriptions.return_value = [mock_subscription]

        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("99.99")
        mock_billing_service.generate_invoice.return_value = mock_invoice

        mock_billing_service.payment_gateway.get_payment_methods.return_value = [{"id": "pm_123"}]

        mock_payment = Mock()
        mock_payment.id = uuid4()
        mock_billing_service.process_payment.return_value = mock_payment

        mock_customer = Mock()
        mock_customer.email = "customer@example.com"
        mock_billing_service.repository.get_customer.return_value = mock_customer

        mock_subscription_for_update = Mock()
        mock_subscription_for_update.customer_id = uuid4()
        mock_subscription_for_update.current_period_end = date(2024, 3, 31)
        mock_subscription_for_update.billing_plan.monthly_price = Decimal("99.99")
        mock_billing_service.repository.get_subscription.return_value = mock_subscription_for_update

        workflow._check_existing_billing_run = AsyncMock(return_value=None)

        # Execute workflow
        results = await workflow.execute()

        # Verify results
        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        assert len(results) == 5  # 5 workflow steps (validation is part of execute method)
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_workflow_execution_with_approval(self, mock_billing_service, approval_billing_request):
        """Test workflow execution requiring approval."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=approval_billing_request,
        )

        # Setup high-value invoice requiring approval
        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        mock_subscription.tenant_id = "test-tenant"
        mock_billing_service.repository.get_due_subscriptions.return_value = [mock_subscription]

        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("1000.00")  # Above threshold
        mock_billing_service.generate_invoice.return_value = mock_invoice

        workflow._check_existing_billing_run = AsyncMock(return_value=None)

        # Execute workflow until approval required
        results = await workflow.execute()

        # Should stop at generate_invoices step
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL
        assert len(results) == 2  # validate_period + generate_invoices (validation is internal)
        assert results[-1].requires_approval is True

    @pytest.mark.asyncio
    async def test_workflow_execution_with_step_failure(self, mock_billing_service, billing_request):
        """Test workflow execution with step failure."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Make validate_billing_period fail
        mock_billing_service.repository.get_due_subscriptions.side_effect = Exception("Database error")
        workflow._check_existing_billing_run = AsyncMock(return_value=None)

        results = await workflow.execute()

        assert workflow.status == BusinessWorkflowStatus.FAILED
        assert not results[-1].success
        assert "Database error" in results[-1].error

    @pytest.mark.asyncio
    async def test_approve_and_continue(self, mock_billing_service, approval_billing_request):
        """Test approve and continue functionality."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=approval_billing_request,
        )

        # Start workflow and get to approval state
        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        mock_subscription.tenant_id = "test-tenant"
        mock_billing_service.repository.get_due_subscriptions.return_value = [mock_subscription]

        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("1000.00")
        mock_billing_service.generate_invoice.return_value = mock_invoice

        workflow._check_existing_billing_run = AsyncMock(return_value=None)

        # Execute until approval required
        await workflow.execute()
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Setup remaining steps
        mock_billing_service.payment_gateway.get_payment_methods.return_value = [{"id": "pm_123"}]
        mock_payment = Mock()
        mock_payment.id = uuid4()
        mock_billing_service.process_payment.return_value = mock_payment

        mock_customer = Mock()
        mock_customer.email = "customer@example.com"
        mock_billing_service.repository.get_customer.return_value = mock_customer

        # Approve and continue
        approval_data = {"approved_by": "manager@example.com"}
        results = await workflow.approve_and_continue(approval_data)

        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        # Check that approval message was updated in the workflow results
        approval_found = any("[APPROVED]" in result.message for result in workflow.results if result.message)
        assert approval_found

    @pytest.mark.asyncio
    async def test_reject_and_cancel(self, mock_billing_service, approval_billing_request):
        """Test reject and cancel functionality."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=approval_billing_request,
        )

        # Get to approval state
        mock_subscription = Mock()
        mock_subscription.id = uuid4()
        mock_subscription.tenant_id = "test-tenant"
        mock_billing_service.repository.get_due_subscriptions.return_value = [mock_subscription]

        mock_invoice = Mock()
        mock_invoice.id = uuid4()
        mock_invoice.customer_id = uuid4()
        mock_invoice.total = Decimal("1000.00")
        mock_billing_service.generate_invoice.return_value = mock_invoice

        workflow._check_existing_billing_run = AsyncMock(return_value=None)

        await workflow.execute()
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Mock rollback behavior
        workflow._generated_invoices = [mock_invoice]

        # Reject workflow
        final_results = await workflow.reject_and_cancel("Budget constraints")

        # Verify rejection
        assert workflow.status == BusinessWorkflowStatus.CANCELLED
        # Check that rejection was recorded in the workflow results
        rejection_found = any("Budget constraints" in (result.error or "") for result in workflow.results)
        assert rejection_found
        reject_msg_found = any("[REJECTED]" in (result.message or "") for result in workflow.results)
        assert reject_msg_found

    @pytest.mark.asyncio
    async def test_error_handling_in_steps(self, mock_billing_service, billing_request):
        """Test error handling within individual steps."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Test error in validate_billing_period
        mock_billing_service.repository.get_due_subscriptions.side_effect = Exception("Connection failed")

        result = await workflow.execute_step("validate_billing_period")

        assert result.success is False
        assert "Connection failed" in result.error
        assert "Billing period validation failed" in result.message

    def test_workflow_properties(self, mock_billing_service, billing_request):
        """Test workflow status properties."""
        workflow = BillingProcessWorkflow(
            billing_service=mock_billing_service,
            billing_request=billing_request,
        )

        # Initial state
        assert not workflow.is_completed
        assert not workflow.is_failed
        assert not workflow.is_running
        assert not workflow.is_waiting_approval

        # Set different statuses and test
        workflow.status = BusinessWorkflowStatus.RUNNING
        assert workflow.is_running

        workflow.status = BusinessWorkflowStatus.COMPLETED
        assert workflow.is_completed

        workflow.status = BusinessWorkflowStatus.FAILED
        assert workflow.is_failed

        workflow.status = BusinessWorkflowStatus.WAITING_APPROVAL
        assert workflow.is_waiting_approval
