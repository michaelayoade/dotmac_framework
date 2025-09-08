"""
Test suite for Invoice Generation Workflow.

This module tests all aspects of the invoice generation process including
validation, calculation, creation, delivery, and payment processing.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from dotmac_business_logic.billing.core.models import InvoiceStatus, PaymentStatus
from dotmac_business_logic.workflows.base import BusinessWorkflowStatus
from dotmac_business_logic.workflows.invoice_generation import (
    InvoiceDeliveryMethod,
    InvoiceGenerationRequest,
    InvoiceGenerationType,
    InvoiceGenerationWorkflow,
)


class TestInvoiceGenerationRequest:
    """Test InvoiceGenerationRequest model validation."""

    def test_valid_subscription_request(self):
        """Test creating a valid subscription invoice request."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            subscription_id=uuid4(),
            invoice_type=InvoiceGenerationType.SUBSCRIPTION,
            billing_period_start=date(2024, 1, 1),
            billing_period_end=date(2024, 1, 31),
            due_date=date(2024, 2, 15),
        )

        assert request.customer_id is not None
        assert request.subscription_id is not None
        assert request.invoice_type == InvoiceGenerationType.SUBSCRIPTION
        assert request.auto_send is True
        assert request.auto_payment is False
        assert request.delivery_methods == [InvoiceDeliveryMethod.EMAIL]

    def test_valid_one_time_request(self):
        """Test creating a valid one-time invoice request."""
        line_items = [
            {
                "description": "Consulting Service",
                "quantity": "10",
                "unit_price": "150.00",
                "taxable": True,
            }
        ]

        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=line_items,
            auto_send=False,
            delivery_methods=[InvoiceDeliveryMethod.PORTAL_ONLY],
        )

        assert request.invoice_type == InvoiceGenerationType.ONE_TIME
        assert len(request.line_items) == 1
        assert request.auto_send is False
        assert request.delivery_methods == [InvoiceDeliveryMethod.PORTAL_ONLY]

    def test_negative_approval_threshold_validation(self):
        """Test validation of negative approval threshold."""
        with pytest.raises(ValueError, match="Approval threshold must be positive"):
            InvoiceGenerationRequest(
                customer_id=uuid4(),
                approval_threshold=Decimal("-100.00"),
            )

    def test_future_date_validation(self):
        """Test validation of dates too far in the future."""
        future_date = date.today() + timedelta(days=400)

        with pytest.raises(ValueError, match="Date cannot be more than 1 year in the future"):
            InvoiceGenerationRequest(
                customer_id=uuid4(),
                billing_period_start=future_date,
            )


class TestInvoiceGenerationWorkflow:
    """Test InvoiceGenerationWorkflow business logic."""

    @pytest.fixture
    def basic_invoice_request(self):
        """Create a basic invoice generation request for testing."""
        return InvoiceGenerationRequest(
            customer_id=uuid4(),
            subscription_id=uuid4(),
            invoice_type=InvoiceGenerationType.SUBSCRIPTION,
            billing_period_start=date(2024, 1, 1),
            billing_period_end=date(2024, 1, 31),
            due_date=date(2024, 2, 15),
        )

    @pytest.fixture
    def mock_services(self):
        """Create mock services for workflow testing."""
        return {
            "billing_service": AsyncMock(),
            "customer_service": AsyncMock(),
            "subscription_service": AsyncMock(),
            "tax_service": AsyncMock(),
            "discount_service": AsyncMock(),
            "pdf_generator": AsyncMock(),
            "notification_service": AsyncMock(),
            "payment_service": AsyncMock(),
            "file_storage_service": AsyncMock(),
        }

    @pytest.fixture
    def mock_customer(self):
        """Create a mock customer object."""
        return MagicMock(
            id=uuid4(),
            email="customer@example.com",
            name="Test Customer",
            billing_address="123 Main St",
            default_payment_method="card_123",
        )

    @pytest.fixture
    def mock_subscription(self):
        """Create a mock subscription object."""
        return MagicMock(
            id=uuid4(),
            status="active",
            billing_plan=MagicMock(
                name="Premium Plan",
                base_price=Decimal("99.99"),
                overage_price=Decimal("0.10"),
                currency="USD",
            ),
        )

    @pytest.fixture
    def mock_invoice(self):
        """Create a mock invoice object."""
        return MagicMock(
            id=uuid4(),
            invoice_number="INV-20240101-001",
            status=InvoiceStatus.DRAFT.value,
            total_amount=Decimal("119.99"),
            amount_due=Decimal("119.99"),
        )

    def test_workflow_initialization(self, basic_invoice_request, mock_services):
        """Test workflow initialization with proper configuration."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )

        assert workflow.workflow_type == "invoice_generation"
        assert len(workflow.steps) == 6
        assert workflow.steps == [
            "validate_invoice_request",
            "calculate_invoice_amounts",
            "create_invoice_record",
            "generate_invoice_document",
            "deliver_invoice",
            "process_automatic_payment",
        ]
        assert workflow.status == BusinessWorkflowStatus.PENDING
        assert workflow.request == basic_invoice_request
        assert workflow.rollback_on_failure is True

    @pytest.mark.asyncio
    async def test_validate_business_rules_success(self, basic_invoice_request, mock_services, mock_customer, mock_subscription):
        """Test successful business rules validation."""
        # Setup mocks
        mock_services["customer_service"].get_customer.return_value = mock_customer
        mock_services["subscription_service"].get_subscription.return_value = mock_subscription

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is True
        assert result.step_name == "validate_business_rules"
        assert "customer_validated" in result.data
        assert "subscription_validated" in result.data
        mock_services["customer_service"].get_customer.assert_called_once_with(basic_invoice_request.customer_id)
        mock_services["subscription_service"].get_subscription.assert_called_once_with(basic_invoice_request.subscription_id)

    @pytest.mark.asyncio
    async def test_validate_business_rules_missing_billing_service(self, basic_invoice_request, mock_services):
        """Test business rules validation with missing billing service."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            billing_service=None,  # Missing required service
            **{k: v for k, v in mock_services.items() if k != 'billing_service'}
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "Billing service is required" in result.error
        assert result.step_name == "validate_business_rules"

    @pytest.mark.asyncio
    async def test_validate_business_rules_customer_not_found(self, basic_invoice_request, mock_services):
        """Test business rules validation when customer doesn't exist."""
        mock_services["customer_service"].get_customer.return_value = None

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "Customer" in result.error and "not found" in result.error
        assert result.step_name == "validate_business_rules"

    @pytest.mark.asyncio
    async def test_validate_business_rules_invalid_billing_period(self, mock_services):
        """Test business rules validation with invalid billing period."""
        # Create request with invalid billing period (start after end)
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            billing_period_start=date(2024, 1, 31),
            billing_period_end=date(2024, 1, 1),  # End before start
        )

        mock_services["customer_service"].get_customer.return_value = MagicMock()

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "Invalid billing period" in result.error
        assert result.step_name == "validate_business_rules"

    @pytest.mark.asyncio
    async def test_validate_invoice_request_step(self, basic_invoice_request, mock_services, mock_customer):
        """Test validate_invoice_request step execution."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.customer = mock_customer

        result = await workflow.execute_step("validate_invoice_request")

        assert result.success is True
        assert result.step_name == "validate_invoice_request"
        assert "customer_id" in result.data
        assert "subscription_id" in result.data
        assert "billing_period_start" in result.data
        assert "billing_period_end" in result.data
        assert result.data["invoice_type"] == InvoiceGenerationType.SUBSCRIPTION.value

    @pytest.mark.asyncio
    async def test_validate_invoice_request_missing_billing_address(self, basic_invoice_request, mock_services):
        """Test validation failure when customer missing billing address."""
        mock_customer = MagicMock(billing_address=None)

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.customer = mock_customer

        result = await workflow.execute_step("validate_invoice_request")

        assert result.success is False
        assert "missing billing address" in result.error
        assert result.step_name == "validate_invoice_request"

    @pytest.mark.asyncio
    async def test_validate_one_time_invoice_missing_line_items(self, mock_services):
        """Test validation of one-time invoice without line items."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=[],  # Empty line items
        )

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.customer = MagicMock(billing_address="123 Main St")

        result = await workflow.execute_step("validate_invoice_request")

        assert result.success is False
        assert "One-time invoices require line items" in result.error

    @pytest.mark.asyncio
    async def test_calculate_invoice_amounts_subscription(self, basic_invoice_request, mock_services, mock_subscription):
        """Test invoice amount calculation for subscription invoice."""
        # Setup subscription with billing plan
        mock_subscription.billing_plan.base_price = Decimal("99.99")
        mock_subscription.billing_plan.overage_price = Decimal("0.10")

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.subscription = mock_subscription

        result = await workflow.execute_step("calculate_invoice_amounts")

        assert result.success is True
        assert result.step_name == "calculate_invoice_amounts"
        assert "subtotal" in result.data
        assert "total_amount" in result.data
        assert result.data["line_items_count"] == 2  # Base + overage
        assert workflow.invoice_data is not None
        assert workflow.invoice_data["subtotal"] == Decimal("104.99")  # 99.99 + (50 * 0.10)

    @pytest.mark.asyncio
    async def test_calculate_invoice_amounts_one_time(self, mock_services):
        """Test invoice amount calculation for one-time invoice."""
        line_items = [
            {"description": "Service A", "quantity": "2", "unit_price": "50.00", "taxable": True},
            {"description": "Service B", "quantity": "1", "unit_price": "25.00", "taxable": False},
        ]

        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=line_items,
        )

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        result = await workflow.execute_step("calculate_invoice_amounts")

        assert result.success is True
        assert result.data["subtotal"] == 125.0  # (2 * 50) + (1 * 25)
        assert result.data["line_items_count"] == 2
        assert workflow.invoice_data["subtotal"] == Decimal("125.00")

    @pytest.mark.asyncio
    async def test_calculate_invoice_amounts_with_tax(self, basic_invoice_request, mock_services, mock_subscription):
        """Test invoice amount calculation with tax service."""
        # Setup tax service
        mock_services["tax_service"].calculate_tax.return_value = {
            "amount": "10.50",
            "rate": "0.105",
            "tax_type": "sales_tax",
        }

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.subscription = mock_subscription
        workflow.customer = MagicMock()

        result = await workflow.execute_step("calculate_invoice_amounts")

        assert result.success is True
        assert result.data["tax_amount"] == 10.5
        assert result.data["tax_rate"] == 0.105
        assert result.data["tax_type"] == "sales_tax"
        mock_services["tax_service"].calculate_tax.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_invoice_amounts_with_discount(self, basic_invoice_request, mock_services, mock_subscription):
        """Test invoice amount calculation with discount service."""
        # Setup discount service
        mock_services["discount_service"].calculate_discounts.return_value = {
            "total_discount": "15.00",
            "discounts": [{"type": "loyalty", "amount": "15.00"}],
        }

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.subscription = mock_subscription

        result = await workflow.execute_step("calculate_invoice_amounts")

        assert result.success is True
        assert result.data["discount_amount"] == 15.0
        assert "discounts_applied" in result.data
        mock_services["discount_service"].calculate_discounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_invoice_amounts_requires_approval(self, mock_services):
        """Test invoice amount calculation triggering approval requirement."""
        line_items = [{"description": "Large Project", "quantity": "1", "unit_price": "5000.00"}]

        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=line_items,
            approval_threshold=Decimal("1000.00"),  # Trigger approval
        )

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        result = await workflow.execute_step("calculate_invoice_amounts")

        assert result.success is True
        assert result.requires_approval is True
        assert "approval_threshold" in result.approval_data
        assert result.approval_data["total_amount"] == 5000.0

    @pytest.mark.asyncio
    async def test_create_invoice_record_step(self, basic_invoice_request, mock_services, mock_invoice):
        """Test create_invoice_record step execution."""
        # Setup invoice data
        invoice_data = {
            "customer_id": uuid4(),
            "subscription_id": uuid4(),
            "invoice_date": date.today(),
            "due_date": date.today() + timedelta(days=30),
            "service_period_start": date(2024, 1, 1),
            "service_period_end": date(2024, 1, 31),
            "currency": "USD",
            "subtotal": Decimal("99.99"),
            "tax_amount": Decimal("10.00"),
            "total_amount": Decimal("109.99"),
            "amount_due": Decimal("109.99"),
            "line_items": [],
            "tenant_id": None,
            "custom_metadata": {},
            "notes": "Test invoice notes",
        }

        mock_services["billing_service"].create_invoice.return_value = mock_invoice

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice_data = invoice_data

        result = await workflow.execute_step("create_invoice_record")

        assert result.success is True
        assert result.step_name == "create_invoice_record"
        assert "invoice_id" in result.data
        assert "invoice_number" in result.data
        assert workflow.invoice == mock_invoice
        mock_services["billing_service"].create_invoice.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_record_missing_data(self, basic_invoice_request, mock_services):
        """Test create_invoice_record step without invoice data."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        # Don't set invoice_data

        result = await workflow.execute_step("create_invoice_record")

        assert result.success is False
        assert "Invoice data not available" in result.error
        assert result.step_name == "create_invoice_record"

    @pytest.mark.asyncio
    async def test_generate_invoice_document_step(self, basic_invoice_request, mock_services, mock_invoice):
        """Test generate_invoice_document step execution."""
        # Setup PDF generator
        pdf_result = MagicMock(url="/invoices/123/invoice.pdf")
        mock_services["pdf_generator"].generate_invoice_pdf.return_value = pdf_result

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.execute_step("generate_invoice_document")

        assert result.success is True
        assert result.step_name == "generate_invoice_document"
        assert result.data["pdf_generated"] is True
        assert "pdf_url" in result.data
        assert workflow.invoice_document == pdf_result
        mock_services["pdf_generator"].generate_invoice_pdf.assert_called_once_with(mock_invoice)

    @pytest.mark.asyncio
    async def test_generate_invoice_document_with_storage(self, basic_invoice_request, mock_services, mock_invoice):
        """Test document generation with file storage."""
        pdf_result = MagicMock(url="/invoices/123/invoice.pdf")
        mock_services["pdf_generator"].generate_invoice_pdf.return_value = pdf_result
        mock_services["file_storage_service"].store_invoice_document.return_value = {"stored": True}

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.execute_step("generate_invoice_document")

        assert result.success is True
        assert "storage_result" in result.data
        mock_services["file_storage_service"].store_invoice_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_deliver_invoice_step(self, mock_services, mock_invoice):
        """Test deliver_invoice step execution."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            auto_send=True,
            delivery_methods=[InvoiceDeliveryMethod.EMAIL, InvoiceDeliveryMethod.PORTAL_ONLY],
        )

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        # Add invoice_data needed for webhook delivery
        workflow.invoice_data = {"total_amount": 100.0}

        result = await workflow.execute_step("deliver_invoice")

        assert result.success is True
        assert result.step_name == "deliver_invoice"
        assert result.data["success_count"] == 2
        assert "email" in result.data["successful_deliveries"]
        assert "portal" in result.data["successful_deliveries"]

    @pytest.mark.asyncio
    async def test_deliver_invoice_auto_send_disabled(self, basic_invoice_request, mock_services, mock_invoice):
        """Test invoice delivery when auto_send is disabled."""
        basic_invoice_request.auto_send = False

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.execute_step("deliver_invoice")

        assert result.success is True
        assert result.data["auto_send"] is False
        assert "skipped" in result.message

    @pytest.mark.asyncio
    async def test_deliver_invoice_with_failures(self, mock_services, mock_invoice):
        """Test invoice delivery with some delivery method failures."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            auto_send=True,
            delivery_methods=[InvoiceDeliveryMethod.EMAIL, InvoiceDeliveryMethod.API_WEBHOOK],
        )

        # Mock email delivery to fail
        mock_services["notification_service"].send_invoice_email.side_effect = Exception("Email service unavailable")
        
        # Ensure webhook delivery succeeds (mock the notification service)
        if not hasattr(mock_services["notification_service"], 'send_webhook'):
            mock_services["notification_service"].send_webhook = AsyncMock()

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        # Add invoice_data needed for webhook delivery
        workflow.invoice_data = {"total_amount": 100.0}

        result = await workflow.execute_step("deliver_invoice")

        assert result.success is True  # At least one delivery succeeded
        assert result.data["success_count"] == 1  # Only webhook succeeded
        assert len(result.data["failed_deliveries"]) == 1
        assert result.data["failed_deliveries"][0]["method"] == "email"

    @pytest.mark.asyncio
    async def test_process_automatic_payment_step(self, mock_services, mock_invoice, mock_customer):
        """Test process_automatic_payment step execution."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            auto_payment=True,
        )

        # Setup payment processing
        payment_result = MagicMock(
            id=uuid4(),
            status=PaymentStatus.SUCCESS.value,
        )
        mock_services["payment_service"].process_payment.return_value = payment_result
        mock_services["payment_service"].get_default_payment_method = AsyncMock(return_value="test_method")

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        workflow.customer = mock_customer
        # Add invoice_data needed for payment processing
        workflow.invoice_data = {"amount_due": 100.0}

        result = await workflow.execute_step("process_automatic_payment")

        assert result.success is True
        assert result.step_name == "process_automatic_payment"
        assert result.data["payment_attempted"] is True
        assert result.data["payment_status"] == PaymentStatus.SUCCESS.value
        assert workflow.payment_result == payment_result
        mock_services["payment_service"].process_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_automatic_payment_disabled(self, basic_invoice_request, mock_services, mock_invoice):
        """Test automatic payment when auto_payment is disabled."""
        basic_invoice_request.auto_payment = False

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.execute_step("process_automatic_payment")

        assert result.success is True
        assert result.data["auto_payment"] is False
        assert "skipped" in result.message

    @pytest.mark.asyncio
    async def test_process_automatic_payment_no_default_method(self, mock_services, mock_invoice):
        """Test automatic payment when customer has no default payment method."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            auto_payment=True,
        )

        mock_customer = MagicMock(default_payment_method=None)
        mock_services["payment_service"].get_default_payment_method.return_value = None

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        workflow.customer = mock_customer

        result = await workflow.execute_step("process_automatic_payment")

        assert result.success is True
        assert result.data["default_payment_method"] is False
        assert "no default payment method" in result.message

    @pytest.mark.asyncio
    async def test_unknown_step_execution(self, basic_invoice_request, mock_services):
        """Test execution of unknown workflow step."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )

        result = await workflow.execute_step("unknown_step")

        assert result.success is False
        assert "Unknown step" in result.error
        assert result.step_name == "unknown_step"

    @pytest.mark.asyncio
    async def test_rollback_invoice_creation(self, basic_invoice_request, mock_services, mock_invoice):
        """Test rollback of invoice creation."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.rollback_step("create_invoice_record")

        assert result.success is True
        assert result.step_name == "rollback_create_invoice_record"
        mock_services["billing_service"].delete_invoice.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_invoice_delivery(self, basic_invoice_request, mock_services, mock_invoice):
        """Test rollback of invoice delivery."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.rollback_step("deliver_invoice")

        assert result.success is True
        mock_services["billing_service"].update_invoice_status.assert_called_once_with(
            invoice_id=mock_invoice.id,
            status=InvoiceStatus.DRAFT,
        )

    @pytest.mark.asyncio
    async def test_rollback_payment_processing(self, basic_invoice_request, mock_services):
        """Test rollback of payment processing."""
        payment_result = MagicMock(id=uuid4())

        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.payment_result = payment_result

        result = await workflow.rollback_step("process_automatic_payment")

        assert result.success is True
        mock_services["payment_service"].void_payment.assert_called_once_with(payment_result.id)

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self, mock_services, mock_customer, mock_subscription, mock_invoice):
        """Test complete workflow execution from start to finish."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            subscription_id=uuid4(),
            invoice_type=InvoiceGenerationType.SUBSCRIPTION,
            auto_send=True,
            auto_payment=False,  # Skip payment for simpler test
            delivery_methods=[InvoiceDeliveryMethod.EMAIL],
        )

        # Setup all mocks
        mock_services["customer_service"].get_customer.return_value = mock_customer
        mock_services["subscription_service"].get_subscription.return_value = mock_subscription
        mock_services["billing_service"].create_invoice.return_value = mock_invoice
        mock_services["pdf_generator"].generate_invoice_pdf.return_value = MagicMock(url="/pdf")

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        results = await workflow.execute()

        assert len(results) == 6  # All steps executed
        assert all(result.success for result in results)
        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        assert workflow.is_completed is True
        assert workflow.execution_time is not None

    @pytest.mark.asyncio
    async def test_workflow_execution_with_approval_gate(self, mock_services, mock_customer):
        """Test workflow execution that requires approval."""
        # Create high-value invoice requiring approval
        line_items = [{"description": "Enterprise Service", "quantity": "1", "unit_price": "10000.00"}]

        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=line_items,
            approval_threshold=Decimal("5000.00"),
        )

        mock_services["customer_service"].get_customer.return_value = mock_customer

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        results = await workflow.execute()

        # Should stop at calculate_invoice_amounts step waiting for approval
        assert len(results) == 2  # validate_business_rules + calculate_invoice_amounts
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL
        assert workflow.is_waiting_approval is True
        assert results[-1].requires_approval is True

    @pytest.mark.asyncio
    async def test_workflow_execution_with_failure(self, mock_services, mock_customer):
        """Test workflow execution with step failure."""
        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=[{"description": "Test", "quantity": "1", "unit_price": "100.00"}],
        )

        # Setup customer but make billing service fail
        mock_services["customer_service"].get_customer.return_value = mock_customer
        mock_services["billing_service"].create_invoice.side_effect = Exception("Database error")

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        results = await workflow.execute()

        # Should fail at create_invoice_record step
        assert workflow.status == BusinessWorkflowStatus.FAILED
        assert workflow.is_failed is True
        assert not results[-1].success
        assert "Database error" in results[-1].error

    @pytest.mark.asyncio
    async def test_approve_and_continue_workflow(self, mock_services, mock_customer, mock_invoice):
        """Test approving and continuing a paused workflow."""
        line_items = [{"description": "Large Service", "quantity": "1", "unit_price": "8000.00"}]

        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=line_items,
            approval_threshold=Decimal("5000.00"),
            auto_send=False,  # Simplify test
            auto_payment=False,
        )

        mock_services["customer_service"].get_customer.return_value = mock_customer
        mock_services["billing_service"].create_invoice.return_value = mock_invoice
        mock_services["pdf_generator"].generate_invoice_pdf.return_value = MagicMock(url="/pdf")

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        # Execute workflow until approval gate
        await workflow.execute()
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Approve and continue
        final_results = await workflow.approve_and_continue({"approved_by": "admin"})

        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        assert len(final_results) == 6  # All steps completed
        assert "approved_by" in final_results[1].data  # Approval data added

    @pytest.mark.asyncio
    async def test_reject_and_cancel_workflow(self, mock_services, mock_customer):
        """Test rejecting and canceling a paused workflow."""
        line_items = [{"description": "Large Service", "quantity": "1", "unit_price": "8000.00"}]

        request = InvoiceGenerationRequest(
            customer_id=uuid4(),
            invoice_type=InvoiceGenerationType.ONE_TIME,
            line_items=line_items,
            approval_threshold=Decimal("5000.00"),
        )

        mock_services["customer_service"].get_customer.return_value = mock_customer

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )

        # Execute workflow until approval gate
        await workflow.execute()
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Reject and cancel
        final_results = await workflow.reject_and_cancel("Amount too high")

        assert workflow.status == BusinessWorkflowStatus.CANCELLED
        assert not final_results[-1].success
        assert "Amount too high" in final_results[-1].error
        assert "[REJECTED]" in final_results[-1].message

    def test_workflow_to_dict(self, basic_invoice_request, mock_services):
        """Test converting workflow to dictionary representation."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )
        workflow.business_context = {"tenant": "test"}

        workflow_dict = workflow.to_dict()

        assert isinstance(workflow_dict, dict)
        assert workflow_dict["workflow_type"] == "invoice_generation"
        assert workflow_dict["status"] == BusinessWorkflowStatus.PENDING.value
        assert workflow_dict["business_context"] == {"tenant": "test"}
        assert "steps" in workflow_dict
        assert "created_at" in workflow_dict
        # rollback_on_failure is a property of the workflow instance, not in to_dict
        assert workflow.rollback_on_failure is True

    def test_workflow_properties(self, basic_invoice_request, mock_services):
        """Test workflow status properties."""
        workflow = InvoiceGenerationWorkflow(
            request=basic_invoice_request,
            **mock_services
        )

        # Test initial state
        assert workflow.is_completed is False
        assert workflow.is_failed is False
        assert workflow.is_running is False
        assert workflow.is_waiting_approval is False
        assert workflow.execution_time is None
        assert workflow.progress_percentage == 0.0

        # Test after setting status
        workflow.status = BusinessWorkflowStatus.COMPLETED
        assert workflow.is_completed is True

        workflow.status = BusinessWorkflowStatus.FAILED
        assert workflow.is_failed is True

        workflow.status = BusinessWorkflowStatus.RUNNING
        assert workflow.is_running is True

        workflow.status = BusinessWorkflowStatus.WAITING_APPROVAL
        assert workflow.is_waiting_approval is True
