"""
Comprehensive test suite for CustomerOffboardingWorkflow.

Tests cover all workflow steps, error scenarios, rollback behavior,
and integration with identity, billing, notification, and data export services.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dotmac_business_logic.workflows.base import BusinessWorkflowResult
from dotmac_business_logic.workflows.customer_offboarding import (
    CustomerOffboardingRequest,
    CustomerOffboardingWorkflow,
    DataRetentionPolicy,
    OffboardingReason,
)


class TestCustomerOffboardingRequest:
    """Test CustomerOffboardingRequest validation."""

    def test_valid_offboarding_request(self):
        """Test valid customer offboarding request."""
        request = CustomerOffboardingRequest(
            customer_id="cust_123",
            user_email="customer@example.com",
            offboarding_reason=OffboardingReason.VOLUNTARY,
            reason_details="Customer decided to cancel service",
            final_billing_required=True,
            process_refunds=True,
            data_retention_policy=DataRetentionPolicy.REGULATORY_RETENTION,
        )
        
        assert request.customer_id == "cust_123"
        assert request.user_email == "customer@example.com"
        assert request.offboarding_reason == OffboardingReason.VOLUNTARY
        assert request.final_billing_required is True
        assert request.process_refunds is True
        assert request.data_retention_policy == DataRetentionPolicy.REGULATORY_RETENTION

    def test_invalid_email_format(self):
        """Test invalid email format validation."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            CustomerOffboardingRequest(
                customer_id="cust_123",
                user_email="invalid-email",
                offboarding_reason=OffboardingReason.VOLUNTARY,
            )

    def test_empty_customer_id(self):
        """Test empty customer ID validation."""
        with pytest.raises(ValidationError, match="Customer ID is required"):
            CustomerOffboardingRequest(
                customer_id="",
                user_email="test@example.com",
                offboarding_reason=OffboardingReason.VOLUNTARY,
            )

    def test_invalid_data_preservation_days(self):
        """Test invalid data preservation days validation."""
        with pytest.raises(ValidationError, match="Data preservation days must be between 0 and 2555"):
            CustomerOffboardingRequest(
                customer_id="cust_123",
                user_email="test@example.com",
                offboarding_reason=OffboardingReason.VOLUNTARY,
                preserve_data_days=3000,
            )

    def test_email_normalization(self):
        """Test email normalization to lowercase."""
        request = CustomerOffboardingRequest(
            customer_id="cust_123",
            user_email="Customer@Example.COM",
            offboarding_reason=OffboardingReason.VOLUNTARY,
        )
        assert request.user_email == "customer@example.com"

    def test_default_values(self):
        """Test default values are applied correctly."""
        request = CustomerOffboardingRequest(
            customer_id="cust_123",
            user_email="test@example.com",
            offboarding_reason=OffboardingReason.VOLUNTARY,
        )
        
        assert request.immediate_deactivation is False
        assert request.grace_period_days == 0
        assert request.preserve_data_days == 30
        assert request.final_billing_required is True
        assert request.process_refunds is True
        assert request.collect_outstanding is True
        assert request.data_retention_policy == DataRetentionPolicy.REGULATORY_RETENTION
        assert request.export_customer_data is False
        assert request.send_confirmation_email is True
        assert request.approval_required is False


class TestCustomerOffboardingWorkflow:
    """Test CustomerOffboardingWorkflow functionality."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        return {
            "identity_service": AsyncMock(),
            "billing_service": AsyncMock(),
            "notification_service": AsyncMock(),
            "provisioning_service": AsyncMock(),
            "data_export_service": AsyncMock(),
        }

    @pytest.fixture
    def sample_request(self):
        """Create a sample offboarding request."""
        return CustomerOffboardingRequest(
            customer_id="cust_12345",
            user_email="customer@example.com",
            offboarding_reason=OffboardingReason.VOLUNTARY,
            reason_details="Customer decided to cancel service",
            immediate_deactivation=False,
            grace_period_days=7,
            preserve_data_days=90,
            final_billing_required=True,
            process_refunds=True,
            export_customer_data=True,
            send_confirmation_email=True,
        )

    def test_workflow_initialization(self, mock_services, sample_request):
        """Test workflow initialization."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )
        
        assert workflow.request == sample_request
        assert workflow.identity_service == mock_services["identity_service"]
        assert workflow.billing_service == mock_services["billing_service"]
        assert workflow.notification_service == mock_services["notification_service"]
        assert len(workflow.steps) == 6
        assert workflow.steps == [
            "validate_offboarding_request",
            "suspend_services", 
            "process_final_billing",
            "export_customer_data",
            "cleanup_resources",
            "finalize_offboarding",
        ]

    @pytest.mark.asyncio
    async def test_validate_business_rules(self, mock_services, sample_request):
        """Test validate_business_rules method."""
        # Mock customer data
        mock_customer = {
            "id": "cust_12345",
            "email": "customer@example.com",
            "status": "active"
        }
        mock_services["identity_service"].get_customer.return_value = mock_customer

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is True
        assert result.step_name == "validate_business_rules"
        assert "validation passed" in result.message
        assert result.data["customer_id"] == "cust_12345"

    @pytest.mark.asyncio
    async def test_validate_business_rules_involuntary_requires_approval(self, mock_services, sample_request):
        """Test business rules validation for involuntary termination."""
        sample_request.offboarding_reason = OffboardingReason.INVOLUNTARY
        sample_request.reason_details = "Policy violation"

        mock_customer = {
            "id": "cust_12345",
            "email": "customer@example.com",
            "status": "active"
        }
        mock_services["identity_service"].get_customer.return_value = mock_customer

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is True
        assert result.requires_approval is True
        assert "Involuntary termination requires approval" in result.approval_data["reasons"]

    @pytest.mark.asyncio
    async def test_validate_business_rules_long_retention_requires_approval(self, mock_services, sample_request):
        """Test business rules validation for long data retention."""
        sample_request.preserve_data_days = 500  # More than 365 days

        mock_customer = {
            "id": "cust_12345",
            "email": "customer@example.com",
            "status": "active"
        }
        mock_services["identity_service"].get_customer.return_value = mock_customer

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is True
        assert result.requires_approval is True
        assert "Long-term data retention requested" in result.approval_data["reasons"]

    @pytest.mark.asyncio
    async def test_validate_business_rules_immediate_deletion_conflict(self, mock_services, sample_request):
        """Test business rules validation for immediate deletion conflict."""
        sample_request.data_retention_policy = DataRetentionPolicy.IMMEDIATE_DELETION
        sample_request.preserve_data_days = 30  # Conflicts with immediate deletion

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "conflicts with data preservation days" in result.error

    @pytest.mark.asyncio
    async def test_validate_business_rules_involuntary_missing_reason(self, mock_services, sample_request):
        """Test business rules validation for involuntary without reason."""
        sample_request.offboarding_reason = OffboardingReason.INVOLUNTARY
        sample_request.reason_details = None  # Missing required reason

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "requires detailed reason" in result.error

    @pytest.mark.asyncio
    async def test_validate_offboarding_request_step(self, mock_services, sample_request):
        """Test validate_offboarding_request step."""
        # Mock customer data
        mock_customer = {
            "id": "cust_12345",
            "email": "customer@example.com",
            "status": "active"
        }
        mock_services["identity_service"].get_customer.return_value = mock_customer

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("validate_offboarding_request")

        assert result.success is True
        assert result.step_name == "validate_offboarding_request"
        assert "validated successfully" in result.message
        assert result.data["customer_id"] == "cust_12345"
        assert result.data["customer_status"] == "active"
        assert workflow._customer_data == mock_customer

    @pytest.mark.asyncio
    async def test_validate_offboarding_request_customer_not_found(self, mock_services, sample_request):
        """Test validate_offboarding_request when customer not found."""
        mock_services["identity_service"].get_customer.return_value = None

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("validate_offboarding_request")

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_validate_offboarding_request_customer_already_terminated(self, mock_services, sample_request):
        """Test validate_offboarding_request when customer already terminated."""
        mock_customer = {
            "id": "cust_12345",
            "email": "customer@example.com",
            "status": "terminated"
        }
        mock_services["identity_service"].get_customer.return_value = mock_customer

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("validate_offboarding_request")

        assert result.success is False
        assert "already in terminated status" in result.error

    @pytest.mark.asyncio
    async def test_suspend_services_step(self, mock_services, sample_request):
        """Test suspend_services step."""
        # Mock customer services
        mock_services_list = [
            {"id": "service_1", "type": "internet"},
            {"id": "service_2", "type": "voip"}
        ]
        mock_services["provisioning_service"].get_customer_services.return_value = mock_services_list
        mock_services["provisioning_service"].suspend_service.return_value = {"status": "suspended"}

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("suspend_services")

        assert result.success is True
        assert result.step_name == "suspend_services"
        assert "Successfully suspended 2 services" in result.message
        assert len(workflow._suspended_services) == 2
        assert workflow._suspended_services[0]["service_id"] == "service_1"
        
        # Verify suspend_service was called for each service
        assert mock_services["provisioning_service"].suspend_service.call_count == 2

    @pytest.mark.asyncio
    async def test_suspend_services_step_no_provisioning_service(self, mock_services, sample_request):
        """Test suspend_services step without provisioning service."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            identity_service=mock_services["identity_service"],
            billing_service=mock_services["billing_service"],
            notification_service=mock_services["notification_service"],
            provisioning_service=None,  # No provisioning service
        )

        result = await workflow.execute_step("suspend_services")

        assert result.success is True
        assert len(workflow._suspended_services) == 1  # Mock service
        assert workflow._suspended_services[0]["service_id"] == "mock_service_1"

    @pytest.mark.asyncio
    async def test_process_final_billing_step(self, mock_services, sample_request):
        """Test process_final_billing step."""
        # Mock billing responses
        mock_final_invoice = {
            "id": "inv_final_123",
            "customer_id": "cust_12345",
            "amount": Decimal("150.00"),
            "status": "generated"
        }
        mock_refunds = [
            {"id": "refund_1", "amount": Decimal("50.00")},
            {"id": "refund_2", "amount": Decimal("25.00")}
        ]
        mock_services["billing_service"].generate_final_invoice.return_value = mock_final_invoice
        mock_services["billing_service"].calculate_refunds.return_value = mock_refunds
        mock_services["billing_service"].process_refund.return_value = {"id": "refund_tx_1", "amount": Decimal("50.00")}
        mock_services["billing_service"].collect_outstanding_balance.return_value = {"status": "no_outstanding_balance"}

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("process_final_billing")

        assert result.success is True
        assert result.step_name == "process_final_billing"
        assert "Final billing processing completed" in result.message
        assert workflow._final_invoice == mock_final_invoice
        assert len(workflow._refund_transactions) == 2
        assert result.data["total_refund_amount"] == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_process_final_billing_step_no_billing_required(self, mock_services, sample_request):
        """Test process_final_billing step when no final billing required."""
        sample_request.final_billing_required = False
        sample_request.process_refunds = False
        sample_request.collect_outstanding = False

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("process_final_billing")

        assert result.success is True
        assert result.data["final_invoice_generated"] is False
        assert result.data["refunds_processed"] == 0

    @pytest.mark.asyncio
    async def test_export_customer_data_step(self, mock_services, sample_request):
        """Test export_customer_data step."""
        mock_export_result = {
            "export_path": "/exports/cust_12345_export.json",
            "file_size": 2048
        }
        mock_services["data_export_service"].export_customer_data.return_value = mock_export_result

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("export_customer_data")

        assert result.success is True
        assert result.step_name == "export_customer_data"
        assert "exported successfully" in result.message
        assert workflow._exported_data_path == "/exports/cust_12345_export.json"
        assert result.data["export_size"] == 2048

    @pytest.mark.asyncio
    async def test_export_customer_data_step_not_requested(self, mock_services, sample_request):
        """Test export_customer_data step when not requested."""
        sample_request.export_customer_data = False

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("export_customer_data")

        assert result.success is True
        assert "not requested" in result.message
        assert workflow._exported_data_path is None

    @pytest.mark.asyncio
    async def test_export_customer_data_step_no_service(self, mock_services, sample_request):
        """Test export_customer_data step without data export service."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            identity_service=mock_services["identity_service"],
            billing_service=mock_services["billing_service"],
            notification_service=mock_services["notification_service"],
            data_export_service=None,  # No data export service
        )

        result = await workflow.execute_step("export_customer_data")

        assert result.success is True
        assert workflow._exported_data_path is not None  # Mock path created
        assert result.data["export_size"] == 1024  # Mock size

    @pytest.mark.asyncio
    async def test_cleanup_resources_step(self, mock_services, sample_request):
        """Test cleanup_resources step."""
        sample_request.data_retention_policy = DataRetentionPolicy.IMMEDIATE_DELETION

        mock_services["identity_service"].delete_personal_data.return_value = {"deleted": True}

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("cleanup_resources")

        assert result.success is True
        assert result.step_name == "cleanup_resources"
        assert "cleanup completed" in result.message
        assert len(workflow._cleanup_actions) > 0
        assert result.data["retention_policy"] == DataRetentionPolicy.IMMEDIATE_DELETION

    @pytest.mark.asyncio
    async def test_cleanup_resources_step_regulatory_retention(self, mock_services, sample_request):
        """Test cleanup_resources step with regulatory retention."""
        sample_request.data_retention_policy = DataRetentionPolicy.REGULATORY_RETENTION

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("cleanup_resources")

        assert result.success is True
        assert result.data["retention_policy"] == DataRetentionPolicy.REGULATORY_RETENTION
        assert result.data["preserve_data_days"] == 90

    @pytest.mark.asyncio
    async def test_finalize_offboarding_step(self, mock_services, sample_request):
        """Test finalize_offboarding step."""
        mock_services["identity_service"].terminate_customer.return_value = {"status": "terminated"}

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )
        
        # Set up some workflow state to test completion data
        workflow._suspended_services = [{"service_id": "service_1"}]
        workflow._final_invoice = {"id": "inv_123"}
        workflow._refund_transactions = [{"id": "refund_1"}]
        workflow._exported_data_path = "/exports/test.json"
        workflow._cleanup_actions = ["delete_personal_data"]

        result = await workflow.execute_step("finalize_offboarding")

        assert result.success is True
        assert result.step_name == "finalize_offboarding"
        assert "completed successfully" in result.message
        assert result.data["customer_id"] == "cust_12345"
        assert result.data["services_suspended"] == 1
        assert result.data["final_invoice_generated"] is True
        assert result.data["refunds_processed"] == 1
        assert result.data["data_exported"] is True
        assert result.data["cleanup_actions_completed"] == 1
        
        # Verify notification was sent
        mock_services["notification_service"].send_offboarding_confirmation.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_offboarding_step_no_confirmation_email(self, mock_services, sample_request):
        """Test finalize_offboarding step without confirmation email."""
        sample_request.send_confirmation_email = False

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("finalize_offboarding")

        assert result.success is True
        assert result.data["confirmation_email_sent"] is False
        
        # Verify no notification was sent
        mock_services["notification_service"].send_offboarding_confirmation.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self, mock_services, sample_request):
        """Test complete workflow execution."""
        # Set up mocks for all services
        mock_services["identity_service"].get_customer.return_value = {
            "id": "cust_12345", "email": "customer@example.com", "status": "active"
        }
        mock_services["provisioning_service"].get_customer_services.return_value = [
            {"id": "service_1", "type": "internet"}
        ]
        mock_services["provisioning_service"].suspend_service.return_value = {"status": "suspended"}
        mock_services["billing_service"].generate_final_invoice.return_value = {
            "id": "inv_final_123", "amount": Decimal("100.00")
        }
        mock_services["billing_service"].calculate_refunds.return_value = []
        mock_services["data_export_service"].export_customer_data.return_value = {
            "export_path": "/exports/test.json", "file_size": 1024
        }
        mock_services["identity_service"].terminate_customer.return_value = {"status": "terminated"}

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        # Execute complete workflow
        results = await workflow.execute()
        final_result = results[-1]  # Get the last step result

        assert final_result.success is True
        assert final_result.step_name == "finalize_offboarding"
        assert "completed successfully" in final_result.message

    @pytest.mark.asyncio
    async def test_workflow_execution_with_failure(self, mock_services, sample_request):
        """Test workflow execution with failure and rollback."""
        # Set up mocks to succeed initially then fail at billing
        mock_services["identity_service"].get_customer.return_value = {
            "id": "cust_12345", "email": "customer@example.com", "status": "active"
        }
        mock_services["provisioning_service"].get_customer_services.return_value = []
        mock_services["billing_service"].generate_final_invoice.side_effect = Exception("Billing service unavailable")

        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        # Execute workflow - should fail at billing step
        results = await workflow.execute()
        final_result = results[-1]  # Get the last step result

        assert final_result.success is False
        assert "Billing service unavailable" in final_result.error
        assert final_result.step_name == "process_final_billing"

    @pytest.mark.asyncio
    async def test_rollback_suspend_services_step(self, mock_services, sample_request):
        """Test rollback of suspend_services step."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )
        
        # Set up suspended services
        workflow._suspended_services = [
            {"service_id": "service_1", "service_type": "internet"},
            {"service_id": "service_2", "service_type": "voip"}
        ]

        result = await workflow.rollback_step("suspend_services")

        assert result.success is True
        # Verify reactivate_service was called for each suspended service
        assert mock_services["provisioning_service"].reactivate_service.call_count == 2

    @pytest.mark.asyncio
    async def test_rollback_process_final_billing_step(self, mock_services, sample_request):
        """Test rollback of process_final_billing step."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )
        
        # Set up refund transactions
        workflow._refund_transactions = [
            {"id": "refund_1", "amount": Decimal("50.00")},
            {"id": "refund_2", "amount": Decimal("25.00")}
        ]

        result = await workflow.rollback_step("process_final_billing")

        assert result.success is True
        # Verify reverse_refund was called for each refund
        assert mock_services["billing_service"].reverse_refund.call_count == 2

    @pytest.mark.asyncio
    async def test_rollback_export_customer_data_step(self, mock_services, sample_request):
        """Test rollback of export_customer_data step."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )
        
        # Set up exported data path
        workflow._exported_data_path = "/exports/cust_12345_export.json"

        result = await workflow.rollback_step("export_customer_data")

        assert result.success is True
        # Verify remove_export was called
        mock_services["data_export_service"].remove_export.assert_called_once_with(
            "/exports/cust_12345_export.json"
        )

    @pytest.mark.asyncio
    async def test_rollback_finalize_offboarding_step(self, mock_services, sample_request):
        """Test rollback of finalize_offboarding step."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )
        
        # Set up customer data
        workflow._customer_data = {"id": "cust_12345", "status": "active"}

        result = await workflow.rollback_step("finalize_offboarding")

        assert result.success is True
        # Verify reactivate_customer was called
        mock_services["identity_service"].reactivate_customer.assert_called_once_with("cust_12345")

    @pytest.mark.asyncio
    async def test_unknown_step_execution(self, mock_services, sample_request):
        """Test execution of unknown step."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        result = await workflow.execute_step("unknown_step")

        assert result.success is False
        assert "Unknown step: unknown_step" in result.error

    def test_workflow_to_dict(self, mock_services, sample_request):
        """Test workflow serialization to dict."""
        workflow = CustomerOffboardingWorkflow(
            offboarding_request=sample_request,
            **mock_services
        )

        workflow_dict = workflow.to_dict()

        assert workflow_dict["workflow_type"] == "CustomerOffboardingWorkflow"
        assert workflow_dict["customer_id"] == "cust_12345"
        assert workflow_dict["offboarding_reason"] == "voluntary"
        assert len(workflow_dict["steps"]) == 6
        assert workflow_dict["current_step"] == 0


class TestOffboardingReasonEnum:
    """Test OffboardingReason enum values."""

    def test_offboarding_reason_values(self):
        """Test all OffboardingReason enum values."""
        assert OffboardingReason.VOLUNTARY == "voluntary"
        assert OffboardingReason.INVOLUNTARY == "involuntary"
        assert OffboardingReason.NON_PAYMENT == "non_payment"
        assert OffboardingReason.VIOLATION == "violation"
        assert OffboardingReason.BUSINESS_CLOSURE == "business_closure"
        assert OffboardingReason.SERVICE_DISCONTINUATION == "service_discontinuation"


class TestDataRetentionPolicyEnum:
    """Test DataRetentionPolicy enum values."""

    def test_data_retention_policy_values(self):
        """Test all DataRetentionPolicy enum values."""
        assert DataRetentionPolicy.IMMEDIATE_DELETION == "immediate_deletion"
        assert DataRetentionPolicy.REGULATORY_RETENTION == "regulatory_retention"
        assert DataRetentionPolicy.BACKUP_ONLY == "backup_only"
        assert DataRetentionPolicy.LONG_TERM_ARCHIVE == "long_term_archive"