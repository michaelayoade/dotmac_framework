"""Unit tests for identity router endpoints."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import status

from dotmac_isp.app import create_app
from dotmac_isp.modules.identity import schemas, models
from dotmac_isp.shared.exceptions import (
    NotFoundError, 
    ValidationError, 
    ConflictError,
    ServiceError
)


@pytest.fixture
def test_client():
    """Test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_customer_service():
    """Mock customer service."""
    service = Mock()
    # Make all methods async
    service.create_customer = AsyncMock()
    service.get_customer = AsyncMock()
    service.update_customer = AsyncMock()
    service.list_customers = AsyncMock()
    service.activate_customer = AsyncMock()
    service.suspend_customer = AsyncMock()
    return service


@pytest.fixture
def mock_user_service():
    """Mock user service."""
    service = Mock()
    # Make all methods async
    service.create_user = AsyncMock()
    service.get_user = AsyncMock()
    service.update_user = AsyncMock()
    service.delete_user = AsyncMock()
    service.list_users = AsyncMock()
    return service


@pytest.fixture
def mock_auth_service():
    """Mock auth service."""
    service = Mock()
    # Make all methods async
    service.login = AsyncMock()
    service.refresh_token = AsyncMock()
    service.logout = AsyncMock()
    service.request_password_reset = AsyncMock()
    service.confirm_password_reset = AsyncMock()
    return service


@pytest.fixture
def sample_customer_response():
    """Sample customer response."""
    return schemas.CustomerResponse(
        id=uuid4(),
        customer_id=uuid4(),
        customer_number="CUST-001",
        display_name="John Doe",
        customer_type=models.CustomerType.RESIDENTIAL,
        customer_segment="standard",
        state="pending",
        account_status=models.AccountStatus.PENDING,
        tags=[],
        custom_fields={},
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        tenant_id="test-tenant"
    )


class TestCustomerEndpoints:
    """Test cases for customer endpoints."""

    @pytest.mark.unit
    def test_create_customer_success(
        self, 
        test_client, 
        mock_customer_service, 
        sample_customer_response
    ):
        """Test successful customer creation."""
        # Setup mock
        mock_customer_service.create_customer.return_value = sample_customer_response
        
        customer_data = {
            "customer_number": "CUST-001",
            "display_name": "John Doe",
            "customer_type": "residential",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.post("/identity/customers", json=customer_data)
        
        # Verify
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["customer_number"] == "CUST-001"
        assert response_data["display_name"] == "John Doe"
        mock_customer_service.create_customer.assert_called_once()

    @pytest.mark.unit
    def test_create_customer_validation_error(
        self, 
        test_client, 
        mock_customer_service
    ):
        """Test customer creation with validation error."""
        # Setup mock
        mock_customer_service.create_customer.side_effect = ValidationError("Invalid data")
        
        customer_data = {
            "customer_number": "CUST-001",
            "customer_type": "residential",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.post("/identity/customers", json=customer_data)
        
        # Verify
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid data" in response.json()["detail"]

    @pytest.mark.unit
    def test_create_customer_conflict_error(
        self, 
        test_client, 
        mock_customer_service
    ):
        """Test customer creation with conflict error."""
        # Setup mock
        mock_customer_service.create_customer.side_effect = ConflictError("Customer already exists")
        
        customer_data = {
            "customer_number": "CUST-001",
            "customer_type": "residential",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.post("/identity/customers", json=customer_data)
        
        # Verify
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Customer already exists" in response.json()["detail"]

    @pytest.mark.unit
    def test_get_customer_success(
        self, 
        test_client, 
        mock_customer_service, 
        sample_customer_response
    ):
        """Test successful customer retrieval."""
        customer_id = sample_customer_response.customer_id
        
        # Setup mock
        mock_customer_service.get_customer.return_value = sample_customer_response
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.get(f"/identity/customers/{customer_id}")
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["customer_id"] == str(customer_id)
        assert response_data["customer_number"] == "CUST-001"
        mock_customer_service.get_customer.assert_called_once_with(customer_id)

    @pytest.mark.unit
    def test_get_customer_not_found(
        self, 
        test_client, 
        mock_customer_service
    ):
        """Test customer retrieval when not found."""
        customer_id = uuid4()
        
        # Setup mock
        mock_customer_service.get_customer.side_effect = NotFoundError("Customer not found")
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.get(f"/identity/customers/{customer_id}")
        
        # Verify
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Customer not found" in response.json()["detail"]

    @pytest.mark.unit
    def test_list_customers_success(
        self, 
        test_client, 
        mock_customer_service, 
        sample_customer_response
    ):
        """Test successful customer listing."""
        # Setup mock
        mock_customer_service.list_customers.return_value = [sample_customer_response]
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.get("/identity/customers?page=1&limit=10")
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "items" in response_data
        assert len(response_data["items"]) == 1
        assert response_data["total"] == 1
        mock_customer_service.list_customers.assert_called_once()

    @pytest.mark.unit
    def test_update_customer_success(
        self, 
        test_client, 
        mock_customer_service, 
        sample_customer_response
    ):
        """Test successful customer update."""
        customer_id = sample_customer_response.customer_id
        updated_response = sample_customer_response.model_copy(
            update={"display_name": "Jane Doe Updated"}
        )
        
        # Setup mock
        mock_customer_service.update_customer.return_value = updated_response
        
        update_data = {
            "display_name": "Jane Doe Updated"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.put(f"/identity/customers/{customer_id}", json=update_data)
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["display_name"] == "Jane Doe Updated"
        mock_customer_service.update_customer.assert_called_once()

    @pytest.mark.unit
    def test_activate_customer_success(
        self, 
        test_client, 
        mock_customer_service, 
        sample_customer_response
    ):
        """Test successful customer activation."""
        customer_id = sample_customer_response.customer_id
        activated_response = sample_customer_response.model_copy(
            update={"state": "active", "account_status": models.AccountStatus.ACTIVE}
        )
        
        # Setup mock
        mock_customer_service.activate_customer.return_value = activated_response
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.post(f"/identity/customers/{customer_id}/activate")
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["state"] == "active"
        mock_customer_service.activate_customer.assert_called_once_with(customer_id)

    @pytest.mark.unit
    def test_suspend_customer_success(
        self, 
        test_client, 
        mock_customer_service, 
        sample_customer_response
    ):
        """Test successful customer suspension."""
        customer_id = sample_customer_response.customer_id
        suspended_response = sample_customer_response.model_copy(
            update={"state": "suspended", "account_status": models.AccountStatus.SUSPENDED}
        )
        
        # Setup mock
        mock_customer_service.suspend_customer.return_value = suspended_response
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.post(f"/identity/customers/{customer_id}/suspend")
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["state"] == "suspended"
        mock_customer_service.suspend_customer.assert_called_once_with(customer_id)


class TestUserEndpoints:
    """Test cases for user endpoints."""

    @pytest.mark.unit
    def test_create_user_not_implemented(
        self, 
        test_client, 
        mock_user_service
    ):
        """Test user creation returns not implemented."""
        # Setup mock
        mock_user_service.create_user.side_effect = NotImplementedError("Not implemented")
        
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "password123"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_user_service',
            return_value=mock_user_service
        ):
            response = test_client.post("/identity/users", json=user_data)
        
        # Verify - This would be a 500 error since NotImplementedError isn't handled
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.unit
    def test_get_user_not_implemented(
        self, 
        test_client, 
        mock_user_service
    ):
        """Test user retrieval returns not implemented."""
        user_id = uuid4()
        
        # Setup mock
        mock_user_service.get_user.side_effect = NotImplementedError("Not implemented")
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_user_service',
            return_value=mock_user_service
        ):
            response = test_client.get(f"/identity/users/{user_id}")
        
        # Verify
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAuthEndpoints:
    """Test cases for authentication endpoints."""

    @pytest.mark.unit
    def test_login_not_implemented(
        self, 
        test_client, 
        mock_auth_service
    ):
        """Test login returns not implemented."""
        # Setup mock
        mock_auth_service.login.side_effect = NotImplementedError("Not implemented")
        
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_auth_service',
            return_value=mock_auth_service
        ):
            response = test_client.post("/identity/auth/login", json=login_data)
        
        # Verify
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.unit
    def test_refresh_token_not_implemented(
        self, 
        test_client, 
        mock_auth_service
    ):
        """Test token refresh returns not implemented."""
        # Setup mock
        mock_auth_service.refresh_token.side_effect = NotImplementedError("Not implemented")
        
        refresh_data = {
            "refresh_token": "token"
        }
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_auth_service',
            return_value=mock_auth_service
        ):
            response = test_client.post("/identity/auth/refresh", json=refresh_data)
        
        # Verify
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestErrorHandling:
    """Test cases for error handling."""

    @pytest.mark.unit
    def test_service_error_handling(
        self, 
        test_client, 
        mock_customer_service
    ):
        """Test service error handling."""
        customer_id = uuid4()
        
        # Setup mock
        mock_customer_service.get_customer.side_effect = ServiceError("Database connection failed")
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.get(f"/identity/customers/{customer_id}")
        
        # Verify
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database connection failed" in response.json()["detail"]

    @pytest.mark.unit
    def test_validation_error_handling(
        self, 
        test_client, 
        mock_customer_service
    ):
        """Test validation error handling."""
        customer_id = uuid4()
        
        # Setup mock
        mock_customer_service.activate_customer.side_effect = ValidationError("Customer is already active")
        
        # Patch the service dependency
        with patch(
            'dotmac_isp.modules.identity.router.get_customer_service',
            return_value=mock_customer_service
        ):
            response = test_client.post(f"/identity/customers/{customer_id}/activate")
        
        # Verify
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Customer is already active" in response.json()["detail"]