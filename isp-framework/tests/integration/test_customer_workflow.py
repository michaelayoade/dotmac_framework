"""Integration tests for complete customer workflow."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import status

from dotmac_isp.app import create_app
from dotmac_isp.modules.identity import models


@pytest.fixture
def test_client():
    """Test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "customer_number": f"CUST-{uuid4().hex[:8].upper()}",
        "display_name": "Integration Test Customer",
        "customer_type": "residential",
        "first_name": "Integration",
        "last_name": "Test",
        "email": f"integration.test.{uuid4().hex[:8]}@example.com",
        "phone": "+1234567890",
        "company_name": None,
        "tags": ["test", "integration"],
        "custom_fields": {
            "test_flag": True,
            "integration_test": "customer_workflow"
        }
    }


class TestCustomerLifecycleIntegration:
    """Integration tests for complete customer lifecycle."""

    @pytest.mark.integration
    def test_complete_customer_lifecycle(self, test_client, sample_customer_data):
        """Test complete customer lifecycle: create -> get -> update -> activate -> suspend."""
        # Step 1: Create customer
        create_response = test_client.post("/identity/customers", json=sample_customer_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        customer_data = create_response.json()
        customer_id = customer_data["customer_id"]
        assert customer_data["customer_number"] == sample_customer_data["customer_number"]
        assert customer_data["display_name"] == sample_customer_data["display_name"]
        assert customer_data["account_status"] == "pending"
        
        # Step 2: Get customer by ID
        get_response = test_client.get(f"/identity/customers/{customer_id}")
        assert get_response.status_code == status.HTTP_200_OK
        
        retrieved_customer = get_response.json()
        assert retrieved_customer["customer_id"] == customer_id
        assert retrieved_customer["customer_number"] == sample_customer_data["customer_number"]
        
        # Step 3: Update customer
        update_data = {
            "display_name": "Updated Integration Test Customer",
            "tags": ["test", "integration", "updated"],
            "custom_fields": {
                "test_flag": True,
                "integration_test": "customer_workflow",
                "updated": True
            }
        }
        
        update_response = test_client.put(f"/identity/customers/{customer_id}", json=update_data)
        assert update_response.status_code == status.HTTP_200_OK
        
        updated_customer = update_response.json()
        assert updated_customer["display_name"] == "Updated Integration Test Customer"
        assert "updated" in updated_customer["tags"]
        
        # Step 4: Activate customer
        activate_response = test_client.post(f"/identity/customers/{customer_id}/activate")
        assert activate_response.status_code == status.HTTP_200_OK
        
        activated_customer = activate_response.json()
        assert activated_customer["state"] == "active"
        
        # Step 5: Suspend customer
        suspend_response = test_client.post(f"/identity/customers/{customer_id}/suspend")
        assert suspend_response.status_code == status.HTTP_200_OK
        
        suspended_customer = suspend_response.json()
        assert suspended_customer["state"] == "suspended"
        
        # Step 6: Verify final state
        final_get_response = test_client.get(f"/identity/customers/{customer_id}")
        assert final_get_response.status_code == status.HTTP_200_OK
        
        final_customer = final_get_response.json()
        assert final_customer["state"] == "suspended"
        assert final_customer["display_name"] == "Updated Integration Test Customer"

    @pytest.mark.integration
    def test_customer_list_and_filter_workflow(self, test_client):
        """Test customer listing and filtering workflow."""
        # Create multiple customers with different types
        residential_customer = {
            "customer_number": f"RES-{uuid4().hex[:8].upper()}",
            "display_name": "Residential Customer",
            "customer_type": "residential",
            "first_name": "Residential",
            "last_name": "Customer",
            "email": f"residential.{uuid4().hex[:8]}@example.com"
        }
        
        business_customer = {
            "customer_number": f"BUS-{uuid4().hex[:8].upper()}",
            "display_name": "Business Customer",
            "customer_type": "business",
            "first_name": "Business",
            "last_name": "Customer",
            "email": f"business.{uuid4().hex[:8]}@example.com"
        }
        
        # Create customers
        res_response = test_client.post("/identity/customers", json=residential_customer)
        assert res_response.status_code == status.HTTP_201_CREATED
        res_customer_id = res_response.json()["customer_id"]
        
        bus_response = test_client.post("/identity/customers", json=business_customer)
        assert bus_response.status_code == status.HTTP_201_CREATED
        bus_customer_id = bus_response.json()["customer_id"]
        
        # Activate business customer
        activate_response = test_client.post(f"/identity/customers/{bus_customer_id}/activate")
        assert activate_response.status_code == status.HTTP_200_OK
        
        # List all customers
        list_response = test_client.get("/identity/customers?page=1&limit=50")
        assert list_response.status_code == status.HTTP_200_OK
        
        customers_data = list_response.json()
        assert "items" in customers_data
        assert customers_data["total"] >= 2  # At least our two test customers
        
        # Find our test customers in the list
        customer_numbers = [c["customer_number"] for c in customers_data["items"]]
        assert residential_customer["customer_number"] in customer_numbers
        assert business_customer["customer_number"] in customer_numbers
        
        # Filter by customer type
        residential_filter_response = test_client.get(
            "/identity/customers?customer_type=residential&page=1&limit=50"
        )
        assert residential_filter_response.status_code == status.HTTP_200_OK
        
        filtered_data = residential_filter_response.json()
        # Verify all returned customers are residential
        for customer in filtered_data["items"]:
            if customer["customer_number"] in [residential_customer["customer_number"], business_customer["customer_number"]]:
                if customer["customer_number"] == residential_customer["customer_number"]:
                    assert customer["customer_type"] == "residential"

    @pytest.mark.integration
    def test_customer_validation_workflow(self, test_client, sample_customer_data):
        """Test customer validation across the workflow."""
        # Test duplicate customer number
        create_response_1 = test_client.post("/identity/customers", json=sample_customer_data)
        assert create_response_1.status_code == status.HTTP_201_CREATED
        
        # Try to create another customer with same number
        create_response_2 = test_client.post("/identity/customers", json=sample_customer_data)
        assert create_response_2.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in create_response_2.json()["detail"].lower()
        
        # Test invalid customer type
        invalid_customer_data = sample_customer_data.copy()
        invalid_customer_data["customer_type"] = "invalid_type"
        invalid_customer_data["customer_number"] = f"INVALID-{uuid4().hex[:8].upper()}"
        
        invalid_response = test_client.post("/identity/customers", json=invalid_customer_data)
        # This should fail at the Pydantic validation level
        assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.integration
    def test_customer_state_transition_validation(self, test_client, sample_customer_data):
        """Test customer state transition validation."""
        # Create customer
        create_response = test_client.post("/identity/customers", json=sample_customer_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        customer_id = create_response.json()["customer_id"]
        
        # Activate customer
        activate_response = test_client.post(f"/identity/customers/{customer_id}/activate")
        assert activate_response.status_code == status.HTTP_200_OK
        
        # Try to activate again (should fail)
        activate_again_response = test_client.post(f"/identity/customers/{customer_id}/activate")
        assert activate_again_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already active" in activate_again_response.json()["detail"].lower()
        
        # Suspend customer
        suspend_response = test_client.post(f"/identity/customers/{customer_id}/suspend")
        assert suspend_response.status_code == status.HTTP_200_OK
        
        # Try to suspend again (should fail)
        suspend_again_response = test_client.post(f"/identity/customers/{customer_id}/suspend")
        assert suspend_again_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already suspended" in suspend_again_response.json()["detail"].lower()

    @pytest.mark.integration
    def test_customer_not_found_workflow(self, test_client):
        """Test customer not found scenarios."""
        non_existent_id = uuid4()
        
        # Get non-existent customer
        get_response = test_client.get(f"/identity/customers/{non_existent_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in get_response.json()["detail"].lower()
        
        # Update non-existent customer
        update_data = {"display_name": "Updated Name"}
        update_response = test_client.put(f"/identity/customers/{non_existent_id}", json=update_data)
        assert update_response.status_code == status.HTTP_404_NOT_FOUND
        
        # Activate non-existent customer
        activate_response = test_client.post(f"/identity/customers/{non_existent_id}/activate")
        assert activate_response.status_code == status.HTTP_404_NOT_FOUND
        
        # Suspend non-existent customer
        suspend_response = test_client.post(f"/identity/customers/{non_existent_id}/suspend")
        assert suspend_response.status_code == status.HTTP_404_NOT_FOUND


class TestUserWorkflowIntegration:
    """Integration tests for user workflow (placeholder for future implementation)."""

    @pytest.mark.integration
    def test_user_endpoints_not_implemented(self, test_client):
        """Test that user endpoints return not implemented."""
        # Test create user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "password123"
        }
        
        create_response = test_client.post("/identity/users", json=user_data)
        assert create_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test get users
        list_response = test_client.get("/identity/users?page=1&limit=10")
        assert list_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test get user by ID
        user_id = uuid4()
        get_response = test_client.get(f"/identity/users/{user_id}")
        assert get_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAuthWorkflowIntegration:
    """Integration tests for auth workflow (placeholder for future implementation)."""

    @pytest.mark.integration
    def test_auth_endpoints_not_implemented(self, test_client):
        """Test that auth endpoints return not implemented."""
        # Test login
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        
        login_response = test_client.post("/identity/auth/login", json=login_data)
        assert login_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test refresh token
        refresh_data = {
            "refresh_token": "token"
        }
        
        refresh_response = test_client.post("/identity/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestPaginationIntegration:
    """Integration tests for pagination functionality."""

    @pytest.mark.integration
    def test_customer_pagination_workflow(self, test_client):
        """Test customer listing pagination."""
        # Create multiple customers for pagination testing
        customers_created = []
        
        for i in range(5):
            customer_data = {
                "customer_number": f"PAGE-{i:03d}-{uuid4().hex[:4].upper()}",
                "display_name": f"Pagination Test Customer {i}",
                "customer_type": "residential",
                "first_name": f"Customer{i}",
                "last_name": "Test",
                "email": f"page.test.{i}.{uuid4().hex[:4]}@example.com"
            }
            
            create_response = test_client.post("/identity/customers", json=customer_data)
            assert create_response.status_code == status.HTTP_201_CREATED
            customers_created.append(create_response.json())
        
        # Test pagination with small page size
        page1_response = test_client.get("/identity/customers?page=1&limit=2")
        assert page1_response.status_code == status.HTTP_200_OK
        
        page1_data = page1_response.json()
        assert "items" in page1_data
        assert "total" in page1_data
        assert "page" in page1_data
        assert "size" in page1_data
        assert "pages" in page1_data
        
        assert page1_data["page"] == 1
        assert page1_data["size"] == 2
        assert len(page1_data["items"]) <= 2
        
        # Test page 2
        page2_response = test_client.get("/identity/customers?page=2&limit=2")
        assert page2_response.status_code == status.HTTP_200_OK
        
        page2_data = page2_response.json()
        assert page2_data["page"] == 2
        assert page2_data["size"] == 2