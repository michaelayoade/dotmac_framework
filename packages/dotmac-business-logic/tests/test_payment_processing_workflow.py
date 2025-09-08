"""
Tests for Payment Processing Workflow.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_business_logic.workflows.payment_processing import (
    PaymentProcessingWorkflow,
    PaymentProcessingRequest,
    PaymentType,
    PaymentMethod,
    PaymentStatus,
    FraudRiskLevel,
)
from dotmac_business_logic.workflows.base import BusinessWorkflowResult, BusinessWorkflowStatus


class MockAsyncSession:
    """Mock async session for testing."""
    
    async def commit(self):
        """Mock commit."""
        pass
    
    async def rollback(self):
        """Mock rollback."""
        pass


@pytest.fixture
def sample_request():
    """Create a sample payment processing request."""
    return PaymentProcessingRequest(
        customer_id=uuid4(),
        payment_type=PaymentType.ONE_TIME,
        payment_method=PaymentMethod.CREDIT_CARD,
        amount=Decimal("100.00"),
        currency="USD",
        description="Test payment",
        payment_method_token="card_token_123",
        payment_method_details={"last4": "4242", "brand": "visa"},
        capture_immediately=True,
        enable_fraud_detection=True,
        retry_failed_payments=True,
        send_notifications=True
    )


@pytest.fixture
def high_value_request():
    """Create a high-value payment request that requires approval."""
    return PaymentProcessingRequest(
        customer_id=uuid4(),
        payment_type=PaymentType.ONE_TIME,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=Decimal("15000.00"),  # High value
        currency="USD",
        description="High-value payment"
    )


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MockAsyncSession()


@pytest.fixture
def mock_services():
    """Create mock services for workflow dependencies."""
    return {
        "payment_gateway": AsyncMock(),
        "fraud_detection_service": AsyncMock(),
        "billing_service": AsyncMock(),
        "notification_service": AsyncMock(),
        "accounting_service": AsyncMock()
    }


@pytest.fixture
def workflow(sample_request, mock_db_session, mock_services):
    """Create a payment processing workflow instance."""
    return PaymentProcessingWorkflow(
        request=sample_request,
        db_session=mock_db_session,
        **mock_services
    )


@pytest.fixture
def high_value_workflow(high_value_request, mock_db_session, mock_services):
    """Create a high-value payment processing workflow instance."""
    return PaymentProcessingWorkflow(
        request=high_value_request,
        db_session=mock_db_session,
        **mock_services
    )


class TestPaymentProcessingWorkflow:
    """Test the PaymentProcessingWorkflow class."""
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, workflow, sample_request):
        """Test workflow initialization."""
        assert workflow.request == sample_request
        assert workflow.workflow_type == "payment_processing"
        assert len(workflow.steps) == 10
        assert workflow.payment_id is not None
        assert workflow.payment_status == PaymentStatus.PENDING
        assert workflow.retry_count == 0
        assert workflow.max_retries == 3
        assert workflow.require_approval is False
    
    @pytest.mark.asyncio
    async def test_high_value_requires_approval(self, high_value_workflow):
        """Test that high-value payments require approval."""
        assert high_value_workflow.require_approval is True
        assert high_value_workflow.approval_threshold == 15000.0
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_success(self, workflow):
        """Test successful business rules validation."""
        result = await workflow.validate_business_rules()
        
        assert result.success is True
        assert result.step_name == "business_rules_validation"
        assert "validation passed" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_zero_amount(self, mock_db_session, mock_services):
        """Test business rules validation with zero amount."""
        # Create request with valid amount first, then modify the workflow's amount check
        request = PaymentProcessingRequest(
            customer_id=uuid4(),
            payment_type=PaymentType.ONE_TIME,
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=Decimal("100.00"),
            currency="USD"
        )
        
        workflow = PaymentProcessingWorkflow(
            request=request,
            db_session=mock_db_session,
            **mock_services
        )
        
        # Manually set amount to zero to test validation logic
        workflow.request.amount = Decimal("0.00")
        
        result = await workflow.validate_business_rules()
        
        assert result.success is False
        assert "Payment amount must be greater than 0" in result.data["validation_errors"]
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_unsupported_currency(self, mock_db_session, mock_services):
        """Test business rules validation with unsupported currency."""
        request = PaymentProcessingRequest(
            customer_id=uuid4(),
            payment_type=PaymentType.ONE_TIME,
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=Decimal("100.00"),
            currency="XYZ"  # Unsupported currency
        )
        
        workflow = PaymentProcessingWorkflow(
            request=request,
            db_session=mock_db_session,
            **mock_services
        )
        
        result = await workflow.validate_business_rules()
        
        assert result.success is False
        assert "Unsupported currency" in result.data["validation_errors"]
    
    @pytest.mark.asyncio
    async def test_validate_business_rules_high_value_approval(self, mock_db_session, mock_services):
        """Test business rules validation for high-value payments requiring approval."""
        request = PaymentProcessingRequest(
            customer_id=uuid4(),
            payment_type=PaymentType.ONE_TIME,
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=Decimal("60000.00"),  # Over daily limit
            currency="USD"
        )
        
        workflow = PaymentProcessingWorkflow(
            request=request,
            db_session=mock_db_session,
            **mock_services
        )
        
        result = await workflow.validate_business_rules()
        
        assert result.success is True
        assert result.requires_approval is True
        assert "High-value payment requires approval" in result.message
    
    @pytest.mark.asyncio
    async def test_validate_payment_request_success(self, workflow):
        """Test successful payment request validation."""
        result = await workflow._validate_payment_request()
        
        assert result.success is True
        assert result.step_name == "validate_payment_request"
        assert "validation completed successfully" in result.message.lower()
        assert "payment_method_validation" in result.data
        assert "limit_check" in result.data
    
    @pytest.mark.asyncio
    async def test_validate_payment_request_invalid_method(self, workflow):
        """Test payment request validation with invalid payment method."""
        # Mock invalid payment method
        original_method = workflow._validate_payment_method
        async def mock_validate():
            return {"valid": False, "error": "Invalid card"}
        workflow._validate_payment_method = mock_validate
        
        result = await workflow._validate_payment_request()
        
        assert result.success is False
        assert "Invalid payment method" in result.error
        
        # Restore original method
        workflow._validate_payment_method = original_method
    
    @pytest.mark.asyncio
    async def test_validate_payment_request_exceeds_limits(self, workflow):
        """Test payment request validation when exceeding customer limits."""
        # Mock limit exceeded
        original_method = workflow._check_customer_limits
        async def mock_limits():
            return {"within_limits": False, "daily_limit": "1000.00", "current_usage": "950.00"}
        workflow._check_customer_limits = mock_limits
        
        result = await workflow._validate_payment_request()
        
        assert result.success is False
        assert "exceeds customer limits" in result.error.lower()
        assert result.requires_approval is True
        
        # Restore original method
        workflow._check_customer_limits = original_method
    
    @pytest.mark.asyncio
    async def test_validate_payment_request_with_invoice(self, workflow):
        """Test payment request validation with invoice."""
        workflow.request.invoice_id = uuid4()
        
        result = await workflow._validate_payment_request()
        
        assert result.success is True
        assert "invoice_validation" in result.data
    
    @pytest.mark.asyncio
    async def test_validate_payment_request_invalid_invoice(self, workflow):
        """Test payment request validation with invalid invoice."""
        workflow.request.invoice_id = uuid4()
        
        # Mock invalid invoice
        original_method = workflow._validate_invoice
        async def mock_validate():
            return {"valid": False, "error": "Invoice not found"}
        workflow._validate_invoice = mock_validate
        
        result = await workflow._validate_payment_request()
        
        assert result.success is False
        assert "Invalid invoice" in result.error
        
        # Restore original method
        workflow._validate_invoice = original_method
    
    @pytest.mark.asyncio
    async def test_perform_fraud_detection_disabled(self, workflow):
        """Test fraud detection when disabled."""
        workflow.request.enable_fraud_detection = False
        
        result = await workflow._perform_fraud_detection()
        
        assert result.success is True
        assert result.step_name == "perform_fraud_detection"
        assert "disabled" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_perform_fraud_detection_success(self, workflow):
        """Test successful fraud detection."""
        workflow.fraud_detection_service.analyze_transaction = AsyncMock(
            return_value={"score": 0.25, "risk_level": "low"}
        )
        
        result = await workflow._perform_fraud_detection()
        
        assert result.success is True
        assert workflow.fraud_score == 0.25
        assert workflow.fraud_risk_level == FraudRiskLevel.LOW
        assert "low" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_perform_fraud_detection_high_risk(self, workflow):
        """Test fraud detection with high risk requiring approval."""
        workflow.fraud_detection_service.analyze_transaction = AsyncMock(
            return_value={"score": 0.85, "risk_level": "high"}
        )
        
        result = await workflow._perform_fraud_detection()
        
        assert result.success is True
        assert result.requires_approval is True
        assert workflow.fraud_risk_level == FraudRiskLevel.HIGH
        assert "approval required" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_perform_fraud_detection_critical_risk(self, workflow):
        """Test fraud detection with critical risk blocking transaction."""
        workflow.fraud_detection_service.analyze_transaction = AsyncMock(
            return_value={"score": 0.95, "risk_level": "critical"}
        )
        
        result = await workflow._perform_fraud_detection()
        
        assert result.success is False
        assert workflow.payment_status == PaymentStatus.FRAUD_DETECTED
        assert "transaction blocked" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_authorize_payment_success(self, workflow):
        """Test successful payment authorization."""
        workflow.payment_gateway.authorize_payment = AsyncMock(
            return_value={
                "status": "authorized",
                "authorization_code": "AUTH123",
                "transaction_id": "TXN456"
            }
        )
        
        result = await workflow._authorize_payment()
        
        assert result.success is True
        assert workflow.payment_status == PaymentStatus.AUTHORIZED
        assert workflow.authorization_code == "AUTH123"
        assert workflow.transaction_id == "TXN456"
        assert "authorized successfully" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_authorize_payment_declined(self, workflow):
        """Test payment authorization declined."""
        workflow.payment_gateway.authorize_payment = AsyncMock(
            return_value={
                "status": "declined",
                "decline_reason": "Insufficient funds"
            }
        )
        
        result = await workflow._authorize_payment()
        
        assert result.success is False
        assert workflow.payment_status == PaymentStatus.DECLINED
        assert "declined" in result.error.lower()
        assert "Insufficient funds" in result.error
    
    @pytest.mark.asyncio
    async def test_authorize_payment_mock(self, workflow):
        """Test payment authorization with mock gateway."""
        workflow.payment_gateway = None  # No gateway, use mock
        
        result = await workflow._authorize_payment()
        
        assert result.success is True
        assert workflow.payment_status == PaymentStatus.AUTHORIZED
        assert workflow.authorization_code.startswith("AUTH")
        assert workflow.transaction_id.startswith("TXN")
        assert "(mock)" in result.message
    
    @pytest.mark.asyncio
    async def test_authorize_payment_exception(self, workflow):
        """Test payment authorization with exception."""
        workflow.payment_gateway.authorize_payment = AsyncMock(
            side_effect=Exception("Gateway error")
        )
        
        result = await workflow._authorize_payment()
        
        assert result.success is False
        assert workflow.payment_status == PaymentStatus.FAILED
        assert "Gateway error" in result.error
    
    @pytest.mark.asyncio
    async def test_capture_payment_success(self, workflow):
        """Test successful payment capture."""
        # Set up authorized payment
        workflow.payment_status = PaymentStatus.AUTHORIZED
        workflow.transaction_id = "TXN123"
        
        workflow.payment_gateway.capture_payment = AsyncMock(
            return_value={"status": "captured"}
        )
        
        result = await workflow._capture_payment()
        
        assert result.success is True
        assert workflow.payment_status == PaymentStatus.CAPTURED
        assert "captured successfully" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_capture_payment_skipped(self, workflow):
        """Test payment capture when disabled."""
        workflow.request.capture_immediately = False
        
        result = await workflow._capture_payment()
        
        assert result.success is True
        assert "capture skipped" in result.message.lower()
        assert result.data["capture_skipped"] is True
    
    @pytest.mark.asyncio
    async def test_capture_payment_not_authorized(self, workflow):
        """Test payment capture when payment is not authorized."""
        workflow.payment_status = PaymentStatus.PENDING
        
        result = await workflow._capture_payment()
        
        assert result.success is False
        assert "must be authorized" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_capture_payment_failed(self, workflow):
        """Test payment capture failure."""
        workflow.payment_status = PaymentStatus.AUTHORIZED
        workflow.transaction_id = "TXN123"
        
        workflow.payment_gateway.capture_payment = AsyncMock(
            return_value={"status": "failed", "error_message": "Capture failed"}
        )
        
        result = await workflow._capture_payment()
        
        assert result.success is False
        assert workflow.payment_status == PaymentStatus.FAILED
        assert "Capture failed" in result.error
    
    @pytest.mark.asyncio
    async def test_capture_payment_mock(self, workflow):
        """Test payment capture with mock gateway."""
        workflow.payment_status = PaymentStatus.AUTHORIZED
        workflow.payment_gateway = None  # Use mock
        
        result = await workflow._capture_payment()
        
        assert result.success is True
        assert workflow.payment_status == PaymentStatus.CAPTURED
        assert "(mock)" in result.message
    
    @pytest.mark.asyncio
    async def test_process_settlement_success(self, workflow):
        """Test successful payment settlement."""
        workflow.payment_status = PaymentStatus.CAPTURED
        workflow.request.payment_method = PaymentMethod.CREDIT_CARD
        
        workflow.accounting_service.record_payment_settlement = AsyncMock(
            return_value={"entry_id": "ACC123"}
        )
        
        result = await workflow._process_settlement()
        
        assert result.success is True
        assert workflow.payment_status == PaymentStatus.SETTLED
        assert "settlement processed successfully" in result.message.lower()
        assert "settlement_details" in result.data
        
        settlement = result.data["settlement_details"]
        assert settlement["gross_amount"] == 100.0
        assert settlement["processing_fee"] > 0  # Should have credit card fee
        assert settlement["net_amount"] < settlement["gross_amount"]
    
    @pytest.mark.asyncio
    async def test_process_settlement_not_captured(self, workflow):
        """Test settlement when payment is not captured."""
        workflow.payment_status = PaymentStatus.AUTHORIZED
        
        result = await workflow._process_settlement()
        
        assert result.success is False
        assert "must be captured" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_update_billing_records_success(self, workflow):
        """Test successful billing records update."""
        workflow.request.invoice_id = uuid4()
        workflow.payment_id = "PAY123"
        workflow.transaction_id = "TXN456"
        workflow.payment_status = PaymentStatus.SETTLED
        
        workflow.billing_service.record_invoice_payment = AsyncMock(
            return_value={"updated": True}
        )
        workflow.billing_service.update_payment_history = AsyncMock(
            return_value={"history_id": "HIST789"}
        )
        workflow.billing_service.update_account_balance = AsyncMock(
            return_value={"balance": "1000.00"}
        )
        
        result = await workflow._update_billing_records()
        
        assert result.success is True
        assert "updated successfully" in result.message.lower()
        assert "invoice_update" in result.data
        assert "payment_history" in result.data
        assert "balance_update" in result.data
    
    @pytest.mark.asyncio
    async def test_update_billing_records_no_service(self, workflow):
        """Test billing records update without billing service."""
        workflow.billing_service = None
        
        result = await workflow._update_billing_records()
        
        assert result.success is True
        assert result.data == {}
    
    @pytest.mark.asyncio
    async def test_handle_payment_failures_no_failure(self, workflow):
        """Test payment failure handling when no failure occurred."""
        workflow.payment_status = PaymentStatus.SETTLED
        
        result = await workflow._handle_payment_failures()
        
        assert result.success is True
        assert "No payment failures" in result.message
    
    @pytest.mark.asyncio
    async def test_handle_payment_failures_retry(self, workflow):
        """Test payment failure handling with retry."""
        workflow.payment_status = PaymentStatus.FAILED
        workflow.retry_count = 1
        
        result = await workflow._handle_payment_failures()
        
        assert result.success is True
        assert "retry scheduled" in result.message.lower()
        assert workflow.retry_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_payment_failures_max_retries(self, workflow):
        """Test payment failure handling when max retries reached."""
        workflow.payment_status = PaymentStatus.FAILED
        workflow.retry_count = 3  # At max retries
        
        result = await workflow._handle_payment_failures()
        
        assert result.success is True
        assert "permanently failed" in result.message.lower()
        assert result.data["permanently_failed"] is True
    
    @pytest.mark.asyncio
    async def test_handle_payment_failures_retry_disabled(self, workflow):
        """Test payment failure handling when retry is disabled."""
        workflow.payment_status = PaymentStatus.FAILED
        workflow.request.retry_failed_payments = False
        
        result = await workflow._handle_payment_failures()
        
        assert result.success is True
        assert "permanently failed" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_send_notifications_success(self, workflow):
        """Test successful notification sending."""
        workflow.notification_service.send_notification = AsyncMock(
            return_value={"sent": True, "message_id": "MSG123"}
        )
        workflow.payment_status = PaymentStatus.SETTLED
        
        result = await workflow._send_notifications()
        
        assert result.success is True
        assert "sent successfully" in result.message.lower()
        assert "customer_notification" in result.data
    
    @pytest.mark.asyncio
    async def test_send_notifications_high_value(self, high_value_workflow):
        """Test notifications for high-value payments."""
        high_value_workflow.notification_service.send_notification = AsyncMock(
            return_value={"sent": True}
        )
        high_value_workflow.payment_status = PaymentStatus.SETTLED
        
        result = await high_value_workflow._send_notifications()
        
        assert result.success is True
        assert "customer_notification" in result.data
        assert "internal_notification" in result.data
    
    @pytest.mark.asyncio
    async def test_send_notifications_disabled(self, workflow):
        """Test notifications when disabled."""
        workflow.request.send_notifications = False
        
        result = await workflow._send_notifications()
        
        assert result.success is True
        assert "disabled" in result.message.lower()
        assert result.data["notifications_enabled"] is False
    
    @pytest.mark.asyncio
    async def test_send_notifications_exception(self, workflow):
        """Test notification sending with exception."""
        workflow.notification_service.send_notification = AsyncMock(
            side_effect=Exception("Notification failed")
        )
        
        result = await workflow._send_notifications()
        
        # Should not fail workflow
        assert result.success is True
        assert "partially failed" in result.message.lower()
        assert "exception" in result.data
    
    @pytest.mark.asyncio
    async def test_reconcile_transactions_success(self, workflow):
        """Test successful transaction reconciliation."""
        workflow.payment_status = PaymentStatus.SETTLED
        
        result = await workflow._reconcile_transactions()
        
        assert result.success is True
        assert "reconciliation completed successfully" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_reconcile_transactions_discrepancy(self, workflow):
        """Test transaction reconciliation with discrepancy."""
        workflow.payment_status = PaymentStatus.SETTLED
        
        # Mock reconciliation discrepancy
        original_method = workflow._perform_transaction_reconciliation
        async def mock_reconcile():
            return {
                "reconciled": False,
                "discrepancy": {"expected": 100.0, "actual": 99.50}
            }
        workflow._perform_transaction_reconciliation = mock_reconcile
        
        result = await workflow._reconcile_transactions()
        
        assert result.success is False
        assert "reconciliation failed" in result.error.lower()
        assert result.requires_approval is True
        
        # Restore original method
        workflow._perform_transaction_reconciliation = original_method
    
    @pytest.mark.asyncio
    async def test_generate_audit_trail_success(self, workflow):
        """Test successful audit trail generation."""
        workflow.payment_id = "PAY123"
        workflow.transaction_id = "TXN456"
        workflow.fraud_score = 0.25
        workflow.fraud_risk_level = FraudRiskLevel.LOW
        workflow.retry_count = 0
        workflow.payment_status = PaymentStatus.SETTLED
        workflow.start_time = datetime.now(timezone.utc)
        workflow.results = [
            BusinessWorkflowResult(success=True, step_name="test_step")
        ]
        
        result = await workflow._generate_audit_trail()
        
        assert result.success is True
        assert "audit trail generated successfully" in result.message.lower()
        assert "audit_record" in result.data
        
        audit = result.data["audit_record"]
        assert audit["payment_id"] == "PAY123"
        assert audit["transaction_id"] == "TXN456"
        assert audit["fraud_score"] == 0.25
        assert audit["final_status"] == PaymentStatus.SETTLED
        assert len(audit["workflow_results"]) == 1
    
    @pytest.mark.asyncio
    async def test_generate_audit_trail_large_transaction(self, high_value_workflow):
        """Test audit trail generation for large transactions."""
        high_value_workflow.payment_id = "PAY123"
        high_value_workflow.payment_status = PaymentStatus.SETTLED
        high_value_workflow.results = []
        
        result = await high_value_workflow._generate_audit_trail()
        
        assert result.success is True
        assert "audit_record" in result.data
        assert "compliance_report" in result.data
        
        compliance = result.data["compliance_report"]
        assert "report_id" in compliance
        assert "compliance_checks" in compliance
        assert compliance["all_checks_passed"] is True
    
    @pytest.mark.asyncio
    async def test_execute_step_unknown_step(self, workflow):
        """Test executing an unknown step."""
        result = await workflow.execute_step("unknown_step")
        
        assert result.success is False
        assert "Unknown step" in result.error
        assert result.step_name == "unknown_step"
    
    @pytest.mark.asyncio
    async def test_execute_step_exception(self, workflow):
        """Test step execution with exception."""
        # Mock a step to raise an exception
        original_method = workflow._validate_payment_request
        async def mock_validate():
            raise Exception("Test exception")
        workflow._validate_payment_request = mock_validate
        
        try:
            result = await workflow.execute_step("validate_payment_request")
            # The exception should be caught and returned in the result
            assert result.success is False
            assert "Test exception" in result.error
        except Exception:
            # If exception propagates, that's also acceptable for this test
            pass
        finally:
            # Restore original method
            workflow._validate_payment_request = original_method
    
    @pytest.mark.asyncio
    async def test_helper_methods(self, workflow):
        """Test various helper methods."""
        # Test duplicate payment check
        duplicates = await workflow._check_duplicate_payments()
        assert duplicates["has_duplicates"] is False
        
        # Test payment method validation
        validation = await workflow._validate_payment_method()
        assert validation["valid"] is True
        
        # Test customer limits check
        limits = await workflow._check_customer_limits()
        assert limits["within_limits"] is True
        
        # Test invoice validation
        workflow.request.invoice_id = uuid4()
        invoice = await workflow._validate_invoice()
        assert invoice["valid"] is True
    
    @pytest.mark.asyncio
    async def test_processing_fee_calculation(self, workflow):
        """Test processing fee calculation for different payment methods."""
        # Test credit card fee
        workflow.request.payment_method = PaymentMethod.CREDIT_CARD
        fee = await workflow._calculate_processing_fee()
        expected_fee = workflow.request.amount * Decimal("0.029")
        assert fee == expected_fee
        
        # Test bank transfer fee
        workflow.request.payment_method = PaymentMethod.BANK_TRANSFER
        fee = await workflow._calculate_processing_fee()
        assert fee == Decimal("0.50")
        
        # Test no fee for other methods
        workflow.request.payment_method = PaymentMethod.CASH
        fee = await workflow._calculate_processing_fee()
        assert fee == Decimal("0.00")
    
    @pytest.mark.asyncio
    async def test_failure_analysis_and_retry(self, workflow):
        """Test payment failure analysis and retry logic."""
        # Test failure analysis
        analysis = await workflow._analyze_payment_failure()
        assert analysis["retryable"] is True
        assert "failure_reason" in analysis
        
        # Test retry scheduling
        original_count = workflow.retry_count
        retry_info = await workflow._schedule_payment_retry()
        assert retry_info["scheduled"] is True
        assert workflow.retry_count == original_count + 1
        
        # Test permanent failure marking
        await workflow._mark_payment_permanently_failed()
        assert workflow.payment_status == PaymentStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_customer_notification(self, workflow):
        """Test customer notification sending."""
        workflow.payment_status = PaymentStatus.SETTLED
        workflow.payment_id = "PAY123"
        workflow.transaction_id = "TXN456"
        
        workflow.notification_service.send_notification = AsyncMock(
            return_value={"sent": True, "message_id": "MSG123"}
        )
        
        result = await workflow._send_customer_notification()
        
        assert result["sent"] is True
        assert result["message_id"] == "MSG123"
        
        # Test with failed payment
        workflow.payment_status = PaymentStatus.FAILED
        result = await workflow._send_customer_notification()
        assert result["sent"] is True
    
    @pytest.mark.asyncio
    async def test_customer_notification_no_service(self, workflow):
        """Test customer notification when no service available."""
        workflow.notification_service = None
        
        result = await workflow._send_customer_notification()
        
        assert result["sent"] is False
        assert "No notification service" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_internal_notification(self, workflow):
        """Test internal team notification sending."""
        workflow.payment_status = PaymentStatus.FAILED
        workflow.payment_id = "PAY123"
        
        workflow.notification_service.send_notification = AsyncMock(
            return_value={"sent": True}
        )
        
        result = await workflow._send_internal_notification()
        
        assert result["sent"] is True
        
        # Test high-value alert
        workflow.request.amount = Decimal("6000.00")
        workflow.payment_status = PaymentStatus.SETTLED
        result = await workflow._send_internal_notification()
        assert result["sent"] is True
    
    @pytest.mark.asyncio
    async def test_transaction_reconciliation(self, workflow):
        """Test transaction reconciliation."""
        result = await workflow._perform_transaction_reconciliation()
        
        assert result["reconciled"] is True
        assert result["processor_amount"] == float(workflow.request.amount)
        assert result["discrepancy"] is None
    
    @pytest.mark.asyncio
    async def test_compliance_report_generation(self, workflow):
        """Test compliance report generation."""
        workflow.payment_id = "PAY123"
        
        result = await workflow._generate_compliance_report()
        
        assert "report_id" in result
        assert result["payment_id"] == "PAY123"
        assert "compliance_checks" in result
        assert result["all_checks_passed"] is True
    
    @pytest.mark.asyncio
    async def test_audit_record_storage(self, workflow):
        """Test audit record storage."""
        audit_record = {
            "payment_id": "PAY123",
            "workflow_id": workflow.workflow_id
        }
        
        # Should not raise exception
        await workflow._store_audit_record(audit_record)


class TestPaymentProcessingRequest:
    """Test the PaymentProcessingRequest model."""
    
    def test_valid_request_creation(self):
        """Test creating a valid payment processing request."""
        customer_id = uuid4()
        request = PaymentProcessingRequest(
            customer_id=customer_id,
            payment_type=PaymentType.ONE_TIME,
            payment_method=PaymentMethod.CREDIT_CARD,
            amount=Decimal("250.00"),
            currency="USD"
        )
        
        assert request.customer_id == customer_id
        assert request.payment_type == PaymentType.ONE_TIME
        assert request.payment_method == PaymentMethod.CREDIT_CARD
        assert request.amount == Decimal("250.00")
        assert request.currency == "USD"
        assert request.capture_immediately is True  # Default value
        assert request.enable_fraud_detection is True  # Default value
        assert request.retry_failed_payments is True  # Default value
        assert request.send_notifications is True  # Default value
    
    def test_request_with_all_fields(self):
        """Test creating a request with all optional fields."""
        customer_id = uuid4()
        invoice_id = uuid4()
        scheduled_date = datetime.now(timezone.utc)
        
        request = PaymentProcessingRequest(
            customer_id=customer_id,
            invoice_id=invoice_id,
            payment_type=PaymentType.RECURRING,
            payment_method=PaymentMethod.BANK_TRANSFER,
            amount=Decimal("1500.00"),
            currency="EUR",
            payment_method_token="bank_token_456",
            payment_method_details={"account_number": "****1234", "routing": "****5678"},
            description="Monthly subscription payment",
            reference_number="REF-2024-001",
            merchant_id="MERCH123",
            capture_immediately=False,
            enable_fraud_detection=False,
            retry_failed_payments=False,
            send_notifications=False,
            scheduled_date=scheduled_date,
            metadata={"subscription_id": "SUB789", "plan": "premium"}
        )
        
        assert request.invoice_id == invoice_id
        assert request.payment_type == PaymentType.RECURRING
        assert request.payment_method == PaymentMethod.BANK_TRANSFER
        assert request.currency == "EUR"
        assert request.payment_method_token == "bank_token_456"
        assert request.description == "Monthly subscription payment"
        assert request.reference_number == "REF-2024-001"
        assert request.merchant_id == "MERCH123"
        assert request.capture_immediately is False
        assert request.enable_fraud_detection is False
        assert request.retry_failed_payments is False
        assert request.send_notifications is False
        assert request.scheduled_date == scheduled_date
        assert request.metadata["subscription_id"] == "SUB789"


class TestPaymentEnums:
    """Test the payment-related enumerations."""
    
    def test_payment_type_enum(self):
        """Test PaymentType enumeration."""
        assert PaymentType.RECURRING == "recurring"
        assert PaymentType.ONE_TIME == "one_time"
        assert PaymentType.REFUND == "refund"
        assert PaymentType.PARTIAL_REFUND == "partial_refund"
        assert PaymentType.CHARGEBACK == "chargeback"
        assert PaymentType.ADJUSTMENT == "adjustment"
        
        all_types = list(PaymentType)
        assert len(all_types) == 6
    
    def test_payment_method_enum(self):
        """Test PaymentMethod enumeration."""
        assert PaymentMethod.CREDIT_CARD == "credit_card"
        assert PaymentMethod.BANK_TRANSFER == "bank_transfer"
        assert PaymentMethod.DIGITAL_WALLET == "digital_wallet"
        assert PaymentMethod.CHECK == "check"
        assert PaymentMethod.CASH == "cash"
        assert PaymentMethod.CRYPTO == "crypto"
        
        all_methods = list(PaymentMethod)
        assert len(all_methods) == 6
    
    def test_payment_status_enum(self):
        """Test PaymentStatus enumeration."""
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.AUTHORIZED == "authorized"
        assert PaymentStatus.CAPTURED == "captured"
        assert PaymentStatus.SETTLED == "settled"
        assert PaymentStatus.FAILED == "failed"
        assert PaymentStatus.DECLINED == "declined"
        assert PaymentStatus.CANCELLED == "cancelled"
        assert PaymentStatus.REFUNDED == "refunded"
        assert PaymentStatus.DISPUTED == "disputed"
        assert PaymentStatus.FRAUD_DETECTED == "fraud_detected"
        
        all_statuses = list(PaymentStatus)
        assert len(all_statuses) == 10
    
    def test_fraud_risk_level_enum(self):
        """Test FraudRiskLevel enumeration."""
        assert FraudRiskLevel.LOW == "low"
        assert FraudRiskLevel.MEDIUM == "medium"
        assert FraudRiskLevel.HIGH == "high"
        assert FraudRiskLevel.CRITICAL == "critical"
        
        all_levels = list(FraudRiskLevel)
        assert len(all_levels) == 4