"""
Comprehensive test suite for CustomerOnboardingWorkflow.

Tests cover all workflow steps, error scenarios, rollback behavior,
and integration with identity, billing, and notification services.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError


# Mock the missing imports for testing
class CustomerService:
    pass

class BillingService:
    pass

class NotificationService:
    pass

class ProvisioningService:
    pass

class BusinessWorkflowStatus:
    COMPLETED = "completed"
    FAILED = "failed"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"

from dotmac_business_logic.workflows.customer_onboarding import (
    CustomerOnboardingRequest,
    CustomerOnboardingWorkflow,
    CustomerType,
    OnboardingChannel,
)


class TestCustomerOnboardingRequest:
    """Test CustomerOnboardingRequest validation."""

    def test_valid_onboarding_request(self):
        """Test valid customer onboarding request."""
        request = CustomerOnboardingRequest(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="90210",
            customer_type=CustomerType.RESIDENTIAL,
            onboarding_channel=OnboardingChannel.DIRECT,
        )

        assert request.email == "test@example.com"
        assert request.first_name == "John"
        assert request.last_name == "Doe"
        assert request.customer_type == CustomerType.RESIDENTIAL
        assert request.onboarding_channel == OnboardingChannel.DIRECT
        assert request.auto_activate is False
        assert request.send_welcome_email is True

    def test_business_customer_request(self):
        """Test business customer onboarding request."""
        request = CustomerOnboardingRequest(
            email="business@company.com",
            first_name="Jane",
            last_name="Smith",
            company_name="Acme Corp",
            tax_id="123-456-789",
            address_line1="456 Business Ave",
            city="Corporate City",
            state="NY",
            postal_code="10001",
            customer_type=CustomerType.BUSINESS,
            onboarding_channel=OnboardingChannel.RESELLER,
            plan_id="business-plan-1",
            auto_activate=True,
        )

        assert request.customer_type == CustomerType.BUSINESS
        assert request.company_name == "Acme Corp"
        assert request.tax_id == "123-456-789"
        assert request.plan_id == "business-plan-1"
        assert request.auto_activate is True

    def test_invalid_email_validation(self):
        """Test invalid email format validation."""
        with pytest.raises(ValidationError) as exc_info:
            CustomerOnboardingRequest(
                email="invalid-email",
                first_name="John",
                last_name="Doe",
                address_line1="123 Main St",
                city="Anytown",
                state="CA",
                postal_code="90210",
            )
        assert "Invalid email format" in str(exc_info.value)

    def test_empty_postal_code_validation(self):
        """Test postal code validation."""
        with pytest.raises(ValidationError) as exc_info:
            CustomerOnboardingRequest(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
                address_line1="123 Main St",
                city="Anytown",
                state="CA",
                postal_code="",
            )
        assert "Postal code is required" in str(exc_info.value)

    def test_email_normalization(self):
        """Test email normalization to lowercase."""
        request = CustomerOnboardingRequest(
            email="TEST@EXAMPLE.COM",
            first_name="John",
            last_name="Doe",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="90210",
        )
        assert request.email == "test@example.com"


@pytest.fixture
def mock_identity_service():
    """Create mock identity service."""
    service = Mock(spec=CustomerService)

    # Mock methods
    service.create_customer = AsyncMock()
    service.create_user = AsyncMock()
    service.get_customer_by_email = AsyncMock()
    service.activate_customer = AsyncMock()
    service.activate_user = AsyncMock()
    service.delete_customer = AsyncMock()
    service.delete_user = AsyncMock()
    service.suspend_customer = AsyncMock()
    service.create_portal_access = AsyncMock()
    service.update_customer_lifecycle = AsyncMock()

    return service


@pytest.fixture
def mock_billing_service():
    """Create mock billing service."""
    service = Mock(spec=BillingService)

    service.create_billing_profile = AsyncMock()
    service.delete_billing_profile = AsyncMock()
    service.get_plan = AsyncMock()

    return service


@pytest.fixture
def mock_notification_service():
    """Create mock notification service."""
    service = Mock(spec=NotificationService)

    service.send_welcome_email = AsyncMock()
    service.send_welcome_sms = AsyncMock()

    return service


@pytest.fixture
def mock_provisioning_service():
    """Create mock provisioning service."""
    service = Mock(spec=ProvisioningService)

    service.provision_customer_services = AsyncMock()
    service.deprovision_resource = AsyncMock()

    return service


@pytest.fixture
def basic_onboarding_request():
    """Create basic onboarding request."""
    return CustomerOnboardingRequest(
        email="customer@example.com",
        first_name="John",
        last_name="Doe",
        phone="+1234567890",
        address_line1="123 Main St",
        city="Anytown",
        state="CA",
        postal_code="90210",
        customer_type=CustomerType.RESIDENTIAL,
    )


@pytest.fixture
def business_onboarding_request():
    """Create business onboarding request."""
    return CustomerOnboardingRequest(
        email="business@company.com",
        first_name="Jane",
        last_name="Smith",
        company_name="Acme Corp",
        tax_id="123-456-789",
        address_line1="456 Business Ave",
        city="Corporate City",
        state="NY",
        postal_code="10001",
        customer_type=CustomerType.BUSINESS,
        plan_id="business-plan",
        approval_threshold=Decimal("500.00"),
        auto_activate=True,
    )


@pytest.fixture
def approval_onboarding_request():
    """Create onboarding request requiring approval."""
    return CustomerOnboardingRequest(
        email="enterprise@bigcorp.com",
        first_name="Robert",
        last_name="Johnson",
        company_name="BigCorp Inc",
        address_line1="789 Enterprise Blvd",
        city="Enterprise City",
        state="TX",
        postal_code="75001",
        customer_type=CustomerType.ENTERPRISE,
        plan_id="enterprise-plan",
        approval_required=True,
        approval_threshold=Decimal("1000.00"),
    )


class TestCustomerOnboardingWorkflow:
    """Test CustomerOnboardingWorkflow implementation."""

    @pytest.mark.asyncio
    async def test_workflow_initialization(self, mock_identity_service, mock_billing_service,
                                         mock_notification_service, basic_onboarding_request):
        """Test workflow initialization."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        assert workflow.workflow_type == "customer_onboarding"
        assert len(workflow.steps) == 6
        assert workflow.steps[0] == "validate_customer_data"
        assert workflow.steps[-1] == "finalize_onboarding"
        assert workflow.onboarding_request == basic_onboarding_request

    @pytest.mark.asyncio
    async def test_business_rules_validation_success(self, mock_identity_service, mock_billing_service,
                                                   mock_notification_service, basic_onboarding_request):
        """Test successful business rules validation."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        mock_identity_service.get_customer_by_email.return_value = None

        result = await workflow.validate_business_rules()

        assert result.success is True
        assert result.step_name == "business_rules_validation"
        assert "validation passed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_business_rules_validation_duplicate_customer(self, mock_identity_service, mock_billing_service,
                                                              mock_notification_service, basic_onboarding_request):
        """Test business rules validation with duplicate customer."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Mock existing customer
        mock_identity_service.get_customer_by_email.return_value = Mock(id=uuid4())

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "already exists" in result.error

    @pytest.mark.asyncio
    async def test_business_rules_validation_missing_business_info(self, mock_identity_service, mock_billing_service,
                                                                 mock_notification_service):
        """Test business rules validation with missing business information."""
        # Business customer without company name
        request = CustomerOnboardingRequest(
            email="business@example.com",
            first_name="Jane",
            last_name="Smith",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="90210",
            customer_type=CustomerType.BUSINESS,  # Business type but no company_name
        )

        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=request,
        )

        result = await workflow.validate_business_rules()

        assert result.success is False
        assert "Company name is required" in result.error

    @pytest.mark.asyncio
    async def test_validate_customer_data_step(self, mock_identity_service, mock_billing_service,
                                             mock_notification_service, basic_onboarding_request):
        """Test validate customer data step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        result = await workflow._validate_customer_data()

        assert result.success is True
        assert result.step_name == "validate_customer_data"
        assert "sanitized_data" in result.data
        assert result.data["sanitized_data"]["email"] == "customer@example.com"
        assert result.data["sanitized_data"]["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_create_customer_account_step(self, mock_identity_service, mock_billing_service,
                                              mock_notification_service, basic_onboarding_request):
        """Test create customer account step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Mock customer and user creation
        mock_customer = Mock()
        mock_customer.id = uuid4()
        mock_identity_service.create_customer.return_value = mock_customer

        mock_user = Mock()
        mock_user.id = uuid4()
        mock_identity_service.create_user.return_value = mock_user

        result = await workflow._create_customer_account()

        assert result.success is True
        assert result.step_name == "create_customer_account"
        assert workflow._customer_id == mock_customer.id
        assert workflow._user_id == mock_user.id

        # Verify service calls
        mock_identity_service.create_customer.assert_called_once()
        mock_identity_service.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_billing_profile_step(self, mock_identity_service, mock_billing_service,
                                            mock_notification_service, basic_onboarding_request):
        """Test setup billing profile step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        workflow._customer_id = uuid4()

        # Mock billing profile creation
        mock_billing_profile = Mock()
        mock_billing_profile.id = uuid4()
        mock_billing_service.create_billing_profile.return_value = mock_billing_profile

        result = await workflow._setup_billing_profile()

        assert result.success is True
        assert result.step_name == "setup_billing_profile"
        assert workflow._billing_profile_id == mock_billing_profile.id
        assert result.requires_approval is False

        mock_billing_service.create_billing_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_billing_profile_with_approval(self, mock_identity_service, mock_billing_service,
                                                      mock_notification_service, approval_onboarding_request):
        """Test setup billing profile step requiring approval."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=approval_onboarding_request,
        )

        workflow._customer_id = uuid4()

        # Mock billing profile and plan
        mock_billing_profile = Mock()
        mock_billing_profile.id = uuid4()
        mock_billing_service.create_billing_profile.return_value = mock_billing_profile

        mock_plan = Mock()
        mock_plan.monthly_price = Decimal("1500.00")  # Above threshold
        mock_billing_service.get_plan.return_value = mock_plan

        result = await workflow._setup_billing_profile()

        assert result.success is True
        assert result.requires_approval is True
        assert result.approval_data["estimated_monthly_value"] == 1500.0
        assert result.approval_data["threshold"] == 1000.0

    @pytest.mark.asyncio
    async def test_provision_services_step(self, mock_identity_service, mock_billing_service,
                                         mock_notification_service, mock_provisioning_service,
                                         basic_onboarding_request):
        """Test provision services step."""
        # Set plan_id to enable provisioning
        basic_onboarding_request.plan_id = "test-plan"
        
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
            provisioning_service=mock_provisioning_service,
        )

        workflow._customer_id = uuid4()

        # Mock service provisioning
        mock_resources = [
            {"type": "internet_service", "id": "service_123"},
            {"type": "router", "id": "router_456"},
        ]
        mock_provisioning_service.provision_customer_services.return_value = mock_resources

        # Mock portal access creation
        mock_portal_access = Mock()
        mock_portal_access.id = uuid4()
        mock_identity_service.create_portal_access.return_value = mock_portal_access

        result = await workflow._provision_services()

        assert result.success is True
        assert result.step_name == "provision_services"
        assert len(result.data["provisioned_resources"]) == 3  # 2 services + portal
        assert workflow._provisioned_resources is not None

    @pytest.mark.asyncio
    async def test_send_welcome_communications_step(self, mock_identity_service, mock_billing_service,
                                                  mock_notification_service, basic_onboarding_request):
        """Test send welcome communications step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        workflow._customer_id = uuid4()
        workflow._user_id = uuid4()

        result = await workflow._send_welcome_communications()

        assert result.success is True
        assert result.step_name == "send_welcome_communications"
        assert "welcome_email" in result.data["notifications_sent"]
        assert "welcome_sms" in result.data["notifications_sent"]

        mock_notification_service.send_welcome_email.assert_called_once()
        mock_notification_service.send_welcome_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_communications_disabled(self, mock_identity_service, mock_billing_service,
                                                      mock_notification_service):
        """Test send welcome communications when disabled."""
        request = CustomerOnboardingRequest(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="90210",
            send_welcome_email=False,
        )

        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=request,
        )

        result = await workflow._send_welcome_communications()

        assert result.success is True
        assert "skipped" in result.message.lower()
        mock_notification_service.send_welcome_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalize_onboarding_step(self, mock_identity_service, mock_billing_service,
                                          mock_notification_service, basic_onboarding_request):
        """Test finalize onboarding step."""
        # Enable auto activation
        basic_onboarding_request.auto_activate = True

        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        workflow._customer_id = uuid4()
        workflow._user_id = uuid4()
        workflow._billing_profile_id = uuid4()

        result = await workflow._finalize_onboarding()

        assert result.success is True
        assert result.step_name == "finalize_onboarding"
        assert result.data["auto_activated"] is True
        assert "customer_activated" in result.data["finalization_actions"]
        assert "user_activated" in result.data["finalization_actions"]

        mock_identity_service.activate_customer.assert_called_once()
        mock_identity_service.activate_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_workflow_execution_success(self, mock_identity_service, mock_billing_service,
                                                 mock_notification_service, basic_onboarding_request):
        """Test complete workflow execution success path."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Setup all mocks
        mock_identity_service.get_customer_by_email.return_value = None

        mock_customer = Mock(id=uuid4())
        mock_identity_service.create_customer.return_value = mock_customer

        mock_user = Mock(id=uuid4())
        mock_identity_service.create_user.return_value = mock_user

        mock_billing_profile = Mock(id=uuid4())
        mock_billing_service.create_billing_profile.return_value = mock_billing_profile

        mock_portal_access = Mock(id=uuid4())
        mock_identity_service.create_portal_access.return_value = mock_portal_access

        # Execute workflow
        results = await workflow.execute()

        # Verify results
        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        assert len(results) == 6  # All 6 workflow steps
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_workflow_execution_with_approval(self, mock_identity_service, mock_billing_service,
                                                  mock_notification_service, approval_onboarding_request):
        """Test workflow execution requiring approval."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=approval_onboarding_request,
        )

        # Setup mocks
        mock_identity_service.get_customer_by_email.return_value = None

        mock_customer = Mock(id=uuid4())
        mock_identity_service.create_customer.return_value = mock_customer

        mock_user = Mock(id=uuid4())
        mock_identity_service.create_user.return_value = mock_user

        mock_billing_profile = Mock(id=uuid4())
        mock_billing_service.create_billing_profile.return_value = mock_billing_profile

        # Mock high-value plan requiring approval
        mock_plan = Mock(monthly_price=Decimal("1500.00"))
        mock_billing_service.get_plan.return_value = mock_plan

        # Execute workflow until approval required
        results = await workflow.execute()

        # Should stop at billing setup step
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL
        assert len(results) == 3  # validate_data, create_account, setup_billing
        assert results[-1].requires_approval is True

    @pytest.mark.asyncio
    async def test_approve_and_continue(self, mock_identity_service, mock_billing_service,
                                      mock_notification_service, approval_onboarding_request):
        """Test approve and continue functionality."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=approval_onboarding_request,
        )

        # Get to approval state first
        mock_identity_service.get_customer_by_email.return_value = None
        mock_customer = Mock(id=uuid4())
        mock_identity_service.create_customer.return_value = mock_customer
        mock_user = Mock(id=uuid4())
        mock_identity_service.create_user.return_value = mock_user
        mock_billing_profile = Mock(id=uuid4())
        mock_billing_service.create_billing_profile.return_value = mock_billing_profile
        mock_plan = Mock(monthly_price=Decimal("1500.00"))
        mock_billing_service.get_plan.return_value = mock_plan

        await workflow.execute()
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Setup remaining mocks
        mock_portal_access = Mock(id=uuid4())
        mock_identity_service.create_portal_access.return_value = mock_portal_access

        # Approve and continue
        approval_data = {"approved_by": "manager@example.com"}
        await workflow.approve_and_continue(approval_data)

        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        # Check that approval message was updated in workflow results
        approval_found = any("[APPROVED]" in (result.message or "") for result in workflow.results if result.message)
        assert approval_found

    @pytest.mark.asyncio
    async def test_reject_and_cancel(self, mock_identity_service, mock_billing_service,
                                   mock_notification_service, approval_onboarding_request):
        """Test reject and cancel functionality."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=approval_onboarding_request,
        )

        # Get to approval state
        mock_identity_service.get_customer_by_email.return_value = None
        mock_customer = Mock(id=uuid4())
        mock_identity_service.create_customer.return_value = mock_customer
        mock_user = Mock(id=uuid4())
        mock_identity_service.create_user.return_value = mock_user
        mock_billing_profile = Mock(id=uuid4())
        mock_billing_service.create_billing_profile.return_value = mock_billing_profile
        mock_plan = Mock(monthly_price=Decimal("1500.00"))
        mock_billing_service.get_plan.return_value = mock_plan

        await workflow.execute()
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Reject workflow
        await workflow.reject_and_cancel("Compliance review failed")

        # Verify rejection
        assert workflow.status == BusinessWorkflowStatus.CANCELLED
        # Check that rejection was recorded in the workflow results
        rejection_found = any("Compliance review failed" in (result.error or "") for result in workflow.results)
        assert rejection_found
        reject_msg_found = any("[REJECTED]" in (result.message or "") for result in workflow.results)
        assert reject_msg_found

    @pytest.mark.asyncio
    async def test_workflow_step_failure_rollback(self, mock_identity_service, mock_billing_service,
                                                mock_notification_service, basic_onboarding_request):
        """Test workflow rollback on step failure."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Setup successful initial steps
        mock_identity_service.get_customer_by_email.return_value = None
        mock_customer = Mock(id=uuid4())
        mock_identity_service.create_customer.return_value = mock_customer
        mock_user = Mock(id=uuid4())
        mock_identity_service.create_user.return_value = mock_user

        # Make billing step fail
        mock_billing_service.create_billing_profile.side_effect = Exception("Billing service unavailable")

        results = await workflow.execute()

        # Should fail and not continue
        assert workflow.status == BusinessWorkflowStatus.FAILED
        assert len(results) == 3  # validate_data, create_account, setup_billing (failed)
        assert results[-1].success is False

    @pytest.mark.asyncio
    async def test_rollback_create_customer_account(self, mock_identity_service, mock_billing_service,
                                                  mock_notification_service, basic_onboarding_request):
        """Test rollback of create customer account step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        workflow._customer_id = uuid4()
        workflow._user_id = uuid4()

        result = await workflow.rollback_step("create_customer_account")

        assert result.success is True
        assert result.step_name == "rollback_create_customer_account"
        mock_identity_service.delete_user.assert_called_once_with(workflow._user_id)
        mock_identity_service.delete_customer.assert_called_once_with(workflow._customer_id)

    @pytest.mark.asyncio
    async def test_rollback_setup_billing_profile(self, mock_identity_service, mock_billing_service,
                                                 mock_notification_service, basic_onboarding_request):
        """Test rollback of setup billing profile step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        workflow._billing_profile_id = uuid4()

        result = await workflow.rollback_step("setup_billing_profile")

        assert result.success is True
        assert result.step_name == "rollback_setup_billing_profile"
        mock_billing_service.delete_billing_profile.assert_called_once_with(workflow._billing_profile_id)

    @pytest.mark.asyncio
    async def test_rollback_provision_services(self, mock_identity_service, mock_billing_service,
                                             mock_notification_service, mock_provisioning_service,
                                             basic_onboarding_request):
        """Test rollback of provision services step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
            provisioning_service=mock_provisioning_service,
        )

        workflow._provisioned_resources = [
            {"type": "service", "id": "service_123"},
            {"type": "router", "id": "router_456"},
        ]

        result = await workflow.rollback_step("provision_services")

        assert result.success is True
        assert result.step_name == "rollback_provision_services"
        # Should attempt to deprovision each resource
        assert mock_provisioning_service.deprovision_resource.call_count == 2

    @pytest.mark.asyncio
    async def test_helper_validate_phone_number(self, mock_identity_service, mock_billing_service,
                                               mock_notification_service, basic_onboarding_request):
        """Test phone number validation helper."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Valid phone numbers
        assert await workflow._validate_phone_number("+1234567890") is True
        assert await workflow._validate_phone_number("1234567890") is True
        assert await workflow._validate_phone_number("+44 20 7946 0958") is True

        # Invalid phone numbers
        assert await workflow._validate_phone_number("invalid") is False
        assert await workflow._validate_phone_number("") is False

    @pytest.mark.asyncio
    async def test_helper_validate_address(self, mock_identity_service, mock_billing_service,
                                         mock_notification_service, basic_onboarding_request):
        """Test address validation helper."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Valid address
        valid_address = {
            "line1": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "postal_code": "90210",
            "country": "US"
        }
        assert await workflow._validate_address(valid_address) is True

        # Invalid address (missing required field)
        invalid_address = {
            "line1": "123 Main St",
            "city": "Anytown",
            # Missing state
            "postal_code": "90210",
            "country": "US"
        }
        assert await workflow._validate_address(invalid_address) is False

    @pytest.mark.asyncio
    async def test_helper_get_plan_value(self, mock_identity_service, mock_billing_service,
                                       mock_notification_service, basic_onboarding_request):
        """Test get plan value helper."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Mock plan with price
        mock_plan = Mock(monthly_price=Decimal("99.99"))
        mock_billing_service.get_plan.return_value = mock_plan

        value = await workflow._get_plan_value("test-plan")
        assert value == Decimal("99.99")

        # Mock missing plan
        mock_billing_service.get_plan.return_value = None
        value = await workflow._get_plan_value("nonexistent-plan")
        assert value == Decimal('0')

    @pytest.mark.asyncio
    async def test_error_handling_in_steps(self, mock_identity_service, mock_billing_service,
                                         mock_notification_service, basic_onboarding_request):
        """Test error handling within individual steps."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        # Make identity service fail
        mock_identity_service.create_customer.side_effect = Exception("Database connection failed")

        result = await workflow._create_customer_account()

        assert result.success is False
        assert result.step_name == "create_customer_account"
        assert "Account creation failed" in result.error

    @pytest.mark.asyncio
    async def test_unknown_step_execution(self, mock_identity_service, mock_billing_service,
                                        mock_notification_service, basic_onboarding_request):
        """Test execution of unknown step."""
        workflow = CustomerOnboardingWorkflow(
            identity_service=mock_identity_service,
            billing_service=mock_billing_service,
            notification_service=mock_notification_service,
            onboarding_request=basic_onboarding_request,
        )

        result = await workflow.execute_step("unknown_step")

        assert result.success is False
        assert result.step_name == "unknown_step"
        assert "Unknown step" in result.error
