"""
Test CRUD operations for the DotMac ISP Framework API.
Comprehensive testing of Create, Read, Update, Delete operations across key entities.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestCustomerCRUD:
    """Test CRUD operations for customer management."""

    @pytest.fixture
    def sample_customer_data(self):
        """Sample customer data for testing."""
        return {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "company_name": "Doe Industries",
            "create_user_account": True,
            "password_hash": "hashed_password",
            "billing_address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "90210",
                "country": "USA"
            },
            "service_address": {
                "street": "123 Main St", 
                "city": "Anytown",
                "state": "CA",
                "zip_code": "90210",
                "country": "USA"
            }
        }

    @pytest.fixture
    def sample_customer_response(self):
        """Sample customer response for testing."""
        return {
            "id": "customer-123",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "company_name": "Doe Industries",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

    def test_create_customer_success(self, client, sample_customer_data, sample_customer_response):
        """Test successful customer creation."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac.auth.dependencies.require_permissions') as mock_perms:
                    # Setup mocks
                    mock_instance = AsyncMock()
                    mock_instance.create_customer.return_value = sample_customer_response
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123", "tenant_id": "tenant-123"}
                    mock_perms.return_value = lambda: None
                    
                    # Make request
                    headers = {
                        "Authorization": "Bearer test_token",
                        "X-Tenant-ID": "tenant-123"
                    }
                    
                    response = client.post(
                        "/identity/customers",
                        json=sample_customer_data,
                        headers=headers
                    )
                    
                    assert response.status_code == 201
                    data = response.json()
                    assert data["email"] == "john.doe@example.com"
                    assert data["first_name"] == "John"
                    assert data["status"] == "active"
                    
                    # Verify service was called correctly
                    mock_instance.create_customer.assert_called_once()

    def test_create_customer_validation_errors(self, client):
        """Test customer creation with validation errors."""
        invalid_data = {
            "email": "invalid-email",  # Invalid email format
            "first_name": "",  # Empty required field
            # Missing last_name
        }
        
        headers = {"Authorization": "Bearer test_token"}
        response = client.post("/identity/customers", json=invalid_data, headers=headers)
        
        assert response.status_code == 422
        assert "validation error" in response.json()["detail"][0]["type"]

    def test_get_customer_success(self, client, sample_customer_response):
        """Test successful customer retrieval."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac.auth.dependencies.require_permissions') as mock_perms:
                    # Setup mocks
                    mock_instance = AsyncMock()
                    mock_instance.get_customer_by_id.return_value = sample_customer_response
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123", "tenant_id": "tenant-123"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": "Bearer test_token"}
                    response = client.get("/identity/customers/customer-123", headers=headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["id"] == "customer-123"
                    assert data["email"] == "john.doe@example.com"

    def test_get_customer_not_found(self, client):
        """Test customer retrieval when customer doesn't exist."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac.auth.dependencies.require_permissions') as mock_perms:
                    # Setup mocks
                    mock_instance = AsyncMock()
                    mock_instance.get_customer_by_id.return_value = None
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": "Bearer test_token"}
                    response = client.get("/identity/customers/nonexistent-123", headers=headers)
                    
                    assert response.status_code == 404
                    assert "Customer not found" in response.json()["detail"]

    def test_list_customers_success(self, client, sample_customer_response):
        """Test successful customer listing."""
        customers_list = [sample_customer_response, {
            "id": "customer-456",
            "email": "jane.smith@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "status": "active"
        }]
        
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac.auth.dependencies.require_permissions') as mock_perms:
                    # Setup mocks
                    mock_instance = AsyncMock()
                    mock_instance.get_customers_by_status.return_value = customers_list
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": "Bearer test_token"}
                    response = client.get("/identity/customers", headers=headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert len(data) == 2
                    assert data[0]["id"] == "customer-123"
                    assert data[1]["id"] == "customer-456"

    def test_list_customers_with_filters(self, client):
        """Test customer listing with search and status filters."""
        search_results = [{
            "id": "customer-789",
            "email": "search@example.com",
            "first_name": "Search",
            "last_name": "Result"
        }]
        
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac.auth.dependencies.require_permissions') as mock_perms:
                    # Setup mocks
                    mock_instance = AsyncMock()
                    mock_instance.search_customers.return_value = search_results
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": "Bearer test_token"}
                    response = client.get("/identity/customers?search=search", headers=headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert len(data) == 1
                    assert data[0]["email"] == "search@example.com"
                    
                    # Verify service method was called with search term
                    mock_instance.search_customers.assert_called_once_with("search")


class TestServicePlansCRUD:
    """Test CRUD operations for service plans."""

    @pytest.fixture
    def sample_service_plan_data(self):
        """Sample service plan data for testing."""
        return {
            "name": "Premium Internet",
            "description": "High-speed internet with unlimited data",
            "service_type": "internet",
            "speed_down": 1000,
            "speed_up": 100,
            "data_limit": None,
            "price": 99.99,
            "currency": "USD",
            "billing_cycle": "monthly",
            "is_active": True,
            "is_public": True,
            "features": ["unlimited_data", "static_ip", "24x7_support"],
            "terms_conditions": "Standard terms apply"
        }

    @pytest.fixture
    def sample_service_plan_response(self):
        """Sample service plan response."""
        return {
            "id": "plan-123",
            "name": "Premium Internet",
            "description": "High-speed internet with unlimited data",
            "service_type": "internet",
            "speed_down": 1000,
            "speed_up": 100,
            "price": 99.99,
            "currency": "USD",
            "is_active": True,
            "is_public": True,
            "created_at": "2024-01-01T00:00:00Z"
        }

    def test_create_service_plan_success(self, client, sample_service_plan_data, sample_service_plan_response):
        """Test successful service plan creation."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.create_service_plan.return_value = sample_service_plan_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "tenant_id": "tenant-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/plans",
                    json=sample_service_plan_data,
                    headers=headers
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "Premium Internet"
                assert data["service_type"] == "internet"
                assert data["speed_down"] == 1000
                assert data["price"] == 99.99

    def test_get_service_plan_success(self, client, sample_service_plan_response):
        """Test successful service plan retrieval."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.get_service_plan.return_value = sample_service_plan_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.get("/services/plans/plan-123", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == "plan-123"
                assert data["name"] == "Premium Internet"

    def test_get_service_plan_not_found(self, client):
        """Test service plan retrieval when plan doesn't exist."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.get_service_plan.return_value = None
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.get("/services/plans/nonexistent-123", headers=headers)
                
                assert response.status_code == 404
                assert "Service plan not found" in response.json()["detail"]

    def test_list_service_plans_success(self, client, sample_service_plan_response):
        """Test successful service plans listing."""
        plans_list = [sample_service_plan_response, {
            "id": "plan-456",
            "name": "Basic Internet",
            "service_type": "internet",
            "speed_down": 100,
            "speed_up": 10,
            "price": 29.99,
            "is_active": True,
            "is_public": True
        }]
        
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.list_service_plans.return_value = plans_list
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.get("/services/plans", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["name"] == "Premium Internet"
                assert data[1]["name"] == "Basic Internet"

    def test_list_service_plans_with_filters(self, client):
        """Test service plans listing with filters."""
        filtered_plans = [{
            "id": "plan-internet-123",
            "name": "Internet Plan",
            "service_type": "internet",
            "is_active": True
        }]
        
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.list_service_plans.return_value = filtered_plans
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.get(
                    "/services/plans?service_type=internet&is_active=true",
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["service_type"] == "internet"
                
                # Verify service was called with correct filters
                expected_filters = {"service_type": "internet", "is_active": True}
                mock_service.list_service_plans.assert_called_once()
                call_args = mock_service.list_service_plans.call_args
                assert call_args[1]["filters"] == expected_filters


class TestServiceInstancesCRUD:
    """Test CRUD operations for service instances."""

    @pytest.fixture
    def sample_activation_data(self):
        """Sample service activation data."""
        return {
            "customer_id": "customer-123",
            "service_plan_id": "plan-123",
            "installation_address": {
                "street": "456 Oak Ave",
                "city": "Techtown", 
                "state": "CA",
                "zip_code": "90211"
            },
            "requested_activation_date": "2024-02-01T00:00:00Z",
            "special_instructions": "Install during business hours",
            "contact_phone": "+1234567890"
        }

    @pytest.fixture
    def sample_service_instance_response(self):
        """Sample service instance response."""
        return {
            "id": "service-123",
            "service_number": "SVC-001234",
            "customer_id": "customer-123",
            "service_plan_id": "plan-123",
            "status": "active",
            "activation_date": "2024-02-01T00:00:00Z",
            "monthly_price": 99.99,
            "created_at": "2024-01-15T00:00:00Z"
        }

    def test_activate_service_success(self, client, sample_activation_data, sample_service_instance_response):
        """Test successful service activation."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                activation_response = {
                    "service_instance": sample_service_instance_response,
                    "activation_id": "activation-123",
                    "status": "pending_installation"
                }
                mock_service.activate_service.return_value = activation_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/activate",
                    json=sample_activation_data,
                    headers=headers
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["service_instance"]["service_number"] == "SVC-001234"
                assert data["status"] == "pending_installation"

    def test_get_service_instance_success(self, client, sample_service_instance_response):
        """Test successful service instance retrieval."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.get_service_instance.return_value = sample_service_instance_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.get("/services/instances/service-123", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == "service-123"
                assert data["status"] == "active"

    def test_update_service_status_success(self, client, sample_service_instance_response):
        """Test successful service status update."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                updated_response = {**sample_service_instance_response, "status": "suspended"}
                mock_service.update_service_status.return_value = updated_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                status_update = {
                    "new_status": "suspended",
                    "reason": "Non-payment",
                    "effective_date": "2024-02-15T00:00:00Z"
                }
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.patch(
                    "/services/instances/service-123/status",
                    json=status_update,
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "suspended"

    def test_suspend_service_success(self, client, sample_service_instance_response):
        """Test successful service suspension."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                suspended_response = {**sample_service_instance_response, "status": "suspended"}
                mock_service.suspend_service.return_value = suspended_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/instances/service-123/suspend?reason=Non-payment",
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "suspended"
                
                # Verify service was called with correct parameters
                mock_service.suspend_service.assert_called_once()

    def test_reactivate_service_success(self, client, sample_service_instance_response):
        """Test successful service reactivation."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                reactivated_response = {**sample_service_instance_response, "status": "active"}
                mock_service.reactivate_service.return_value = reactivated_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/instances/service-123/reactivate?reason=Payment+received",
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "active"

    def test_cancel_service_success(self, client, sample_service_instance_response):
        """Test successful service cancellation."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                cancelled_response = {**sample_service_instance_response, "status": "cancelled"}
                mock_service.cancel_service.return_value = cancelled_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/instances/service-123/cancel?reason=Customer+request&effective_date=2024-03-01T00:00:00Z",
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "cancelled"


class TestUsageDataCRUD:
    """Test CRUD operations for service usage data."""

    @pytest.fixture
    def sample_usage_data(self):
        """Sample usage data for testing."""
        return {
            "usage_date": "2024-01-15",
            "data_downloaded": 25000000000,  # 25GB in bytes
            "data_uploaded": 5000000000,     # 5GB in bytes
            "peak_download_speed": 950.5,
            "peak_upload_speed": 95.2,
            "uptime_percentage": 99.8,
            "downtime_minutes": 3,
            "additional_metrics": {
                "ping_avg": 12.5,
                "jitter_avg": 2.1,
                "packet_loss": 0.01
            }
        }

    @pytest.fixture
    def sample_usage_response(self):
        """Sample usage response for testing."""
        return {
            "id": "usage-123",
            "service_id": "service-123",
            "usage_date": "2024-01-15",
            "data_downloaded": 25000000000,
            "data_uploaded": 5000000000,
            "peak_download_speed_mbps": 950.5,
            "peak_upload_speed_mbps": 95.2,
            "uptime_minutes": 1436,
            "downtime_minutes": 3,
            "created_at": "2024-01-16T00:00:00Z"
        }

    def test_record_service_usage_success(self, client, sample_usage_data, sample_usage_response):
        """Test successful usage data recording."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.record_service_usage.return_value = sample_usage_response
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/instances/service-123/usage",
                    json=sample_usage_data,
                    headers=headers
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["data_downloaded"] == 25000000000
                assert data["peak_download_speed_mbps"] == 950.5

    def test_get_service_usage_success(self, client, sample_usage_response):
        """Test successful usage data retrieval."""
        usage_list = [sample_usage_response, {
            "id": "usage-456",
            "service_id": "service-123",
            "usage_date": "2024-01-16",
            "data_downloaded": 30000000000,
            "data_uploaded": 6000000000
        }]
        
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                mock_service.get_service_usage.return_value = usage_list
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.get(
                    "/services/instances/service-123/usage?start_date=2024-01-15&end_date=2024-01-16",
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["usage_date"] == "2024-01-15"
                assert data[1]["usage_date"] == "2024-01-16"


class TestBulkOperations:
    """Test bulk CRUD operations."""

    def test_bulk_service_suspension_success(self, client):
        """Test successful bulk service suspension."""
        bulk_request = {
            "service_instance_ids": ["service-123", "service-456", "service-789"],
            "operation": "suspend",
            "reason": "Maintenance window",
            "effective_date": None
        }
        
        expected_response = {
            "total_requested": 3,
            "successful": 3,
            "failed": 0,
            "results": [
                {"service_id": "service-123", "status": "success", "service_number": "SVC-001234"},
                {"service_id": "service-456", "status": "success", "service_number": "SVC-001235"},
                {"service_id": "service-789", "status": "success", "service_number": "SVC-001236"}
            ],
            "operation_id": "operation-123"
        }
        
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                
                def mock_suspend(service_id, reason, user_id):
                    service_numbers = {
                        "service-123": "SVC-001234",
                        "service-456": "SVC-001235", 
                        "service-789": "SVC-001236"
                    }
                    return type('MockResponse', (), {
                        'service_number': service_numbers[str(service_id)]
                    })()
                
                mock_service.suspend_service.side_effect = mock_suspend
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/bulk-operation",
                    json=bulk_request,
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_requested"] == 3
                assert data["successful"] == 3
                assert data["failed"] == 0
                assert len(data["results"]) == 3

    def test_bulk_operation_partial_failure(self, client):
        """Test bulk operation with partial failures."""
        bulk_request = {
            "service_instance_ids": ["service-123", "service-456"],
            "operation": "suspend",
            "reason": "Test suspension"
        }
        
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
                # Setup mocks
                mock_service = AsyncMock()
                
                def mock_suspend(service_id, reason, user_id):
                    if str(service_id) == "service-123":
                        return type('MockResponse', (), {'service_number': 'SVC-001234'})()
                    else:
                        raise Exception("Service not found")
                
                mock_service.suspend_service.side_effect = mock_suspend
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                headers = {"Authorization": "Bearer test_token"}
                response = client.post(
                    "/services/bulk-operation",
                    json=bulk_request,
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_requested"] == 2
                assert data["successful"] == 1
                assert data["failed"] == 1
                assert data["results"][0]["status"] == "success"
                assert data["results"][1]["status"] == "failed"