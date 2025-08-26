"""Unit tests for identity service layer."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from dotmac_isp.modules.identity.service import CustomerService, UserService, AuthService
from dotmac_isp.modules.identity import schemas, models
from dotmac_isp.shared.exceptions import (
    NotFoundError, 
    ValidationError, 
    ConflictError,
    ServiceError
)
from dotmac_isp.sdks.identity import CustomerResponse


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_sdk_registry():
    """Mock SDK registry with customer management."""
    registry = Mock()
    registry.customers = AsyncMock()
    return registry


@pytest.fixture
def customer_service(mock_db, mock_sdk_registry):
    """Customer service instance with mocked dependencies."""
    with patch('dotmac_isp.modules.identity.service.create_sdk_registry', return_value=mock_sdk_registry):
        service = CustomerService(mock_db, tenant_id="test-tenant")
        service.sdk_registry = mock_sdk_registry
        return service


@pytest.fixture
def sample_customer_create():
    """Sample customer creation data."""
    return schemas.CustomerCreate(
        customer_number="CUST-001",
        display_name="John Doe",
        customer_type=models.CustomerType.RESIDENTIAL,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890"
    )


@pytest.fixture
def sample_customer_response():
    """Sample SDK customer response."""
    return CustomerResponse(
        customer_id=uuid4(),
        customer_number="CUST-001",
        display_name="John Doe",
        customer_type="residential",
        customer_segment="standard",
        state="pending",
        tags=[],
        custom_fields={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
        prospect_date=None,
        activation_date=None,
        churn_date=None,
        monthly_recurring_revenue=None,
        lifetime_value=None
    )


class TestCustomerService:
    """Test cases for CustomerService."""

    @pytest.mark.unit
    async def test_create_customer_success(
        self, 
        customer_service, 
        sample_customer_create, 
        sample_customer_response
    ):
        """Test successful customer creation."""
        # Setup mock
        customer_service.sdk_registry.customers.create_customer.return_value = sample_customer_response
        customer_service._check_customer_number_exists = AsyncMock(return_value=False)
        customer_service._check_customer_email_exists = AsyncMock(return_value=False)
        
        # Execute
        result = await customer_service.create_customer(sample_customer_create)
        
        # Verify
        assert result.customer_number == "CUST-001"
        assert result.display_name == "John Doe"
        assert result.customer_type == models.CustomerType.RESIDENTIAL
        customer_service.sdk_registry.customers.create_customer.assert_called_once()

    @pytest.mark.unit
    async def test_create_customer_duplicate_number(
        self, 
        customer_service, 
        sample_customer_create
    ):
        """Test customer creation with duplicate number."""
        # Setup mock
        customer_service._check_customer_number_exists = AsyncMock(return_value=True)
        
        # Execute & Verify
        with pytest.raises(ConflictError, match="Customer number .* already exists"):
            await customer_service.create_customer(sample_customer_create)

    @pytest.mark.unit
    async def test_create_customer_duplicate_email(
        self, 
        customer_service, 
        sample_customer_create
    ):
        """Test customer creation with duplicate email."""
        # Setup mock
        customer_service._check_customer_number_exists = AsyncMock(return_value=False)
        customer_service._check_customer_email_exists = AsyncMock(return_value=True)
        
        # Execute & Verify
        with pytest.raises(ConflictError, match="Email .* already exists"):
            await customer_service.create_customer(sample_customer_create)

    @pytest.mark.unit
    async def test_get_customer_success(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test successful customer retrieval."""
        customer_id = sample_customer_response.customer_id
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = sample_customer_response
        
        # Execute
        result = await customer_service.get_customer(customer_id)
        
        # Verify
        assert result.customer_id == customer_id
        assert result.customer_number == "CUST-001"
        customer_service.sdk_registry.customers.get_customer.assert_called_once_with(customer_id)

    @pytest.mark.unit
    async def test_get_customer_not_found(self, customer_service):
        """Test customer retrieval when customer doesn't exist."""
        customer_id = uuid4()
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = None
        
        # Execute & Verify
        with pytest.raises(NotFoundError, match=f"Customer {customer_id} not found"):
            await customer_service.get_customer(customer_id)

    @pytest.mark.unit
    async def test_update_customer_success(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test successful customer update."""
        customer_id = sample_customer_response.customer_id
        update_data = schemas.CustomerUpdate(
            display_name="Jane Doe Updated",
            customer_type=models.CustomerType.BUSINESS
        )
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = sample_customer_response
        customer_service.sdk_registry.customers.update_customer.return_value = sample_customer_response
        customer_service._check_customer_email_exists = AsyncMock(return_value=False)
        
        # Execute
        result = await customer_service.update_customer(customer_id, update_data)
        
        # Verify
        assert result.customer_id == customer_id
        customer_service.sdk_registry.customers.update_customer.assert_called_once()

    @pytest.mark.unit
    async def test_update_customer_not_found(self, customer_service):
        """Test customer update when customer doesn't exist."""
        customer_id = uuid4()
        update_data = schemas.CustomerUpdate(display_name="Updated Name")
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = None
        
        # Execute & Verify
        with pytest.raises(NotFoundError):
            await customer_service.update_customer(customer_id, update_data)

    @pytest.mark.unit
    async def test_list_customers_success(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test successful customer listing."""
        # Setup mock
        customer_service.sdk_registry.customers.list_customers.return_value = [sample_customer_response]
        
        # Execute
        result = await customer_service.list_customers(limit=10, offset=0)
        
        # Verify
        assert len(result) == 1
        assert result[0].customer_id == sample_customer_response.customer_id
        customer_service.sdk_registry.customers.list_customers.assert_called_once()

    @pytest.mark.unit
    async def test_list_customers_with_filters(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test customer listing with filters."""
        filters = schemas.CustomerFilters(
            customer_type=models.CustomerType.RESIDENTIAL,
            account_status=models.AccountStatus.ACTIVE
        )
        
        # Setup mock
        customer_service.sdk_registry.customers.list_customers.return_value = [sample_customer_response]
        
        # Execute
        result = await customer_service.list_customers(filters=filters)
        
        # Verify
        assert len(result) == 1
        customer_service.sdk_registry.customers.list_customers.assert_called_once()

    @pytest.mark.unit
    async def test_activate_customer_success(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test successful customer activation."""
        customer_id = sample_customer_response.customer_id
        activated_response = sample_customer_response.model_copy(update={"state": "active"})
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = sample_customer_response
        customer_service.sdk_registry.customers.activate_customer.return_value = activated_response
        
        # Execute
        result = await customer_service.activate_customer(customer_id)
        
        # Verify
        assert result.customer_id == customer_id
        customer_service.sdk_registry.customers.activate_customer.assert_called_once_with(customer_id)

    @pytest.mark.unit
    async def test_activate_customer_already_active(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test activating a customer that's already active."""
        customer_id = sample_customer_response.customer_id
        active_response = sample_customer_response.model_copy(update={"state": "active"})
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = active_response
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Customer is already active"):
            await customer_service.activate_customer(customer_id)

    @pytest.mark.unit
    async def test_suspend_customer_success(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test successful customer suspension."""
        customer_id = sample_customer_response.customer_id
        suspended_response = sample_customer_response.model_copy(update={"state": "suspended"})
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = sample_customer_response
        customer_service.sdk_registry.customers.suspend_customer.return_value = suspended_response
        
        # Execute
        result = await customer_service.suspend_customer(customer_id)
        
        # Verify
        assert result.customer_id == customer_id
        customer_service.sdk_registry.customers.suspend_customer.assert_called_once_with(customer_id)

    @pytest.mark.unit
    async def test_suspend_customer_already_suspended(
        self, 
        customer_service, 
        sample_customer_response
    ):
        """Test suspending a customer that's already suspended."""
        customer_id = sample_customer_response.customer_id
        suspended_response = sample_customer_response.model_copy(update={"state": "suspended"})
        
        # Setup mock
        customer_service.sdk_registry.customers.get_customer.return_value = suspended_response
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Customer is already suspended"):
            await customer_service.suspend_customer(customer_id)

    @pytest.mark.unit
    async def test_check_customer_number_exists_true(self, customer_service, sample_customer_response):
        """Test checking existing customer number."""
        # Setup mock
        customer_service.sdk_registry.customers.list_customers.return_value = [sample_customer_response]
        
        # Execute
        result = await customer_service._check_customer_number_exists("CUST-001")
        
        # Verify
        assert result is True

    @pytest.mark.unit
    async def test_check_customer_number_exists_false(self, customer_service, sample_customer_response):
        """Test checking non-existing customer number."""
        # Setup mock
        customer_service.sdk_registry.customers.list_customers.return_value = [sample_customer_response]
        
        # Execute
        result = await customer_service._check_customer_number_exists("CUST-999")
        
        # Verify
        assert result is False

    @pytest.mark.unit
    async def test_check_customer_email_exists_true(self, customer_service, sample_customer_response):
        """Test checking existing customer email."""
        # Setup mock - add email to custom fields
        sample_customer_response.custom_fields["email"] = "john.doe@example.com"
        customer_service.sdk_registry.customers.list_customers.return_value = [sample_customer_response]
        
        # Execute
        result = await customer_service._check_customer_email_exists("john.doe@example.com")
        
        # Verify
        assert result is True

    @pytest.mark.unit
    async def test_check_customer_email_exists_false(self, customer_service, sample_customer_response):
        """Test checking non-existing customer email."""
        # Setup mock - add different email to custom fields
        sample_customer_response.custom_fields["email"] = "john.doe@example.com"
        customer_service.sdk_registry.customers.list_customers.return_value = [sample_customer_response]
        
        # Execute
        result = await customer_service._check_customer_email_exists("jane.doe@example.com")
        
        # Verify
        assert result is False

    @pytest.mark.unit
    async def test_service_error_handling(self, customer_service, sample_customer_create):
        """Test service error handling."""
        # Setup mock to raise exception
        customer_service.sdk_registry.customers.create_customer.side_effect = Exception("SDK Error")
        customer_service._check_customer_number_exists = AsyncMock(return_value=False)
        customer_service._check_customer_email_exists = AsyncMock(return_value=False)
        
        # Execute & Verify
        with pytest.raises(ServiceError, match="Failed to create customer"):
            await customer_service.create_customer(sample_customer_create)


class TestUserService:
    """Test cases for UserService."""

    @pytest.fixture
    def user_service(self, mock_db):
        """User service instance with mocked dependencies."""
        return UserService(mock_db, tenant_id="test-tenant")

    @pytest.mark.unit
    async def test_create_user_not_implemented(self, user_service):
        """Test user creation throws NotImplementedError."""
        user_data = schemas.UserCreate(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="password123"
        )
        
        with pytest.raises(NotImplementedError):
            await user_service.create_user(user_data)

    @pytest.mark.unit
    async def test_get_user_not_implemented(self, user_service):
        """Test user retrieval throws NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await user_service.get_user(uuid4()

    @pytest.mark.unit
    async def test_update_user_not_implemented(self, user_service):
        """Test user update throws NotImplementedError."""
        update_data = schemas.UserUpdate(first_name="Updated")
        
        with pytest.raises(NotImplementedError):
            await user_service.update_user(uuid4(), update_data)

    @pytest.mark.unit
    async def test_delete_user_not_implemented(self, user_service):
        """Test user deletion throws NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await user_service.delete_user(uuid4()

    @pytest.mark.unit
    async def test_list_users_not_implemented(self, user_service):
        """Test user listing throws NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await user_service.list_users()


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def auth_service(self, mock_db):
        """Auth service instance with mocked dependencies."""
        return AuthService(mock_db, tenant_id="test-tenant")

    @pytest.mark.unit
    async def test_login_not_implemented(self, auth_service):
        """Test login throws NotImplementedError."""
        login_data = schemas.LoginRequest(
            username="testuser",
            password="password123"
        )
        
        with pytest.raises(NotImplementedError):
            await auth_service.login(login_data)

    @pytest.mark.unit
    async def test_refresh_token_not_implemented(self, auth_service):
        """Test token refresh throws NotImplementedError."""
        refresh_data = schemas.TokenRefreshRequest(refresh_token="token")
        
        with pytest.raises(NotImplementedError):
            await auth_service.refresh_token(refresh_data)

    @pytest.mark.unit
    async def test_logout_not_implemented(self, auth_service):
        """Test logout throws NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await auth_service.logout("token")

    @pytest.mark.unit
    async def test_request_password_reset_not_implemented(self, auth_service):
        """Test password reset request throws NotImplementedError."""
        reset_data = schemas.PasswordResetRequest(email="test@example.com")
        
        with pytest.raises(NotImplementedError):
            await auth_service.request_password_reset(reset_data)

    @pytest.mark.unit
    async def test_confirm_password_reset_not_implemented(self, auth_service):
        """Test password reset confirmation throws NotImplementedError."""
        confirm_data = schemas.PasswordResetConfirm(
            token="reset-token",
            new_password="newpassword123"
        )
        
        with pytest.raises(NotImplementedError):
            await auth_service.confirm_password_reset(confirm_data)