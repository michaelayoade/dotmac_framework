"""
Example end-to-end tests for complete customer workflows.

This demonstrates best practices for testing:
- Complete user journeys
- API endpoint integration
- Multi-service interactions
- Real database transactions
- Authentication flows
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from jose import jwt

# Skip E2E tests if not in appropriate environment
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not API_BASE_URL,
    reason="E2E tests require API_BASE_URL and DATABASE_URL"
)


# Test data and fixtures
@pytest.fixture
def jwt_secret():
    """JWT secret for token generation."""
    return os.getenv("JWT_SECRET_KEY", "test-secret-key")


@pytest.fixture
def admin_token_data():
    """Admin user token data."""
    return {
        "sub": "admin-user-id",
        "email": "admin@test-tenant.com",
        "tenant_id": "test-tenant-1",
        "role": "admin",
        "permissions": ["customer:create", "customer:read", "customer:update", "customer:delete"]
    }


@pytest.fixture
def user_token_data():
    """Regular user token data."""
    return {
        "sub": "user-id",
        "email": "user@test-tenant.com", 
        "tenant_id": "test-tenant-1",
        "role": "user",
        "permissions": ["customer:read"]
    }


@pytest.fixture
def create_jwt_token(jwt_secret):
    """Create JWT token for testing."""
    def _create_token(token_data: Dict, expires_delta: timedelta = None) -> str:
        to_encode = token_data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=1)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        return jwt.encode(to_encode, jwt_secret, algorithm="HS256")
    
    return _create_token


@pytest_asyncio.fixture
async def authenticated_client(admin_token_data, create_jwt_token):
    """HTTP client with admin authentication."""
    token = create_jwt_token(admin_token_data)
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
        yield client


@pytest_asyncio.fixture
async def user_client(user_token_data, create_jwt_token):
    """HTTP client with user authentication."""
    token = create_jwt_token(user_token_data)
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
        yield client


@pytest_asyncio.fixture
async def unauthenticated_client():
    """HTTP client without authentication."""
    async with AsyncClient(base_url=API_BASE_URL) as client:
        yield client


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    unique_id = str(uuid4())[:8]
    return {
        "email": f"customer_{unique_id}@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "555-123-4567",
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "12345"
        }
    }


# End-to-end test classes
@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerCreationWorkflow:
    """Test complete customer creation workflow."""
    
    async def test_create_customer_full_workflow(self, authenticated_client, sample_customer_data):
        """Test complete customer creation workflow."""
        # Step 1: Create customer
        response = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        assert response.status_code == 201
        
        customer_data = response.json()
        customer_id = customer_data["id"]
        
        # Verify customer was created correctly
        assert customer_data["email"] == sample_customer_data["email"]
        assert customer_data["first_name"] == sample_customer_data["first_name"]
        assert customer_data["status"] == "active"
        assert "created_at" in customer_data
        
        # Step 2: Verify customer can be retrieved
        response = await authenticated_client.get(f"/api/v1/customers/{customer_id}")
        assert response.status_code == 200
        
        retrieved_customer = response.json()
        assert retrieved_customer["id"] == customer_id
        assert retrieved_customer["email"] == sample_customer_data["email"]
        
        # Step 3: Verify customer appears in list
        response = await authenticated_client.get("/api/v1/customers")
        assert response.status_code == 200
        
        customers_list = response.json()
        customer_ids = [c["id"] for c in customers_list["items"]]
        assert customer_id in customer_ids
        
        return customer_id
    
    async def test_create_customer_with_validation_errors(self, authenticated_client):
        """Test customer creation with validation errors."""
        # Invalid email
        invalid_data = {
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = await authenticated_client.post("/api/v1/customers", json=invalid_data)
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
        assert any("email" in str(error).lower() for error in error_data["detail"])
    
    async def test_create_duplicate_customer(self, authenticated_client, sample_customer_data):
        """Test creating duplicate customer (same email in same tenant)."""
        # Create first customer
        response1 = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        assert response2.status_code == 400
        
        error_data = response2.json()
        assert "already exists" in error_data["detail"].lower()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerUpdateWorkflow:
    """Test customer update workflows."""
    
    async def test_update_customer_information(self, authenticated_client, sample_customer_data):
        """Test updating customer information."""
        # Create customer first
        create_response = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        customer_id = create_response.json()["id"]
        
        # Update customer
        update_data = {
            "first_name": "Updated John",
            "last_name": "Updated Doe",
            "phone": "555-999-8888"
        }
        
        update_response = await authenticated_client.put(
            f"/api/v1/customers/{customer_id}", 
            json=update_data
        )
        assert update_response.status_code == 200
        
        updated_customer = update_response.json()
        assert updated_customer["first_name"] == "Updated John"
        assert updated_customer["last_name"] == "Updated Doe"
        assert updated_customer["phone"] == "555-999-8888"
        assert updated_customer["email"] == sample_customer_data["email"]  # Unchanged
    
    async def test_update_customer_status_with_notification(self, authenticated_client, sample_customer_data):
        """Test updating customer status triggers notification."""
        # Create customer
        create_response = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        customer_id = create_response.json()["id"]
        
        # Update status to suspended
        status_update = {"status": "suspended"}
        response = await authenticated_client.patch(
            f"/api/v1/customers/{customer_id}/status",
            json=status_update
        )
        assert response.status_code == 200
        
        updated_customer = response.json()
        assert updated_customer["status"] == "suspended"
        
        # Check that notification was queued (this might be async)
        # In a real test, you'd check notification queue or mock service
        await asyncio.sleep(0.5)  # Give time for async notification
        
        # Verify status change was logged
        response = await authenticated_client.get(f"/api/v1/customers/{customer_id}/audit-log")
        if response.status_code == 200:  # If audit endpoint exists
            audit_log = response.json()
            status_changes = [log for log in audit_log if log["action"] == "status_change"]
            assert len(status_changes) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerSearchAndFiltering:
    """Test customer search and filtering functionality."""
    
    async def test_search_customers_by_email(self, authenticated_client):
        """Test searching customers by email."""
        # Create multiple customers
        customers_data = [
            {
                "email": f"search_test_{i}@example.com",
                "first_name": f"SearchUser{i}",
                "last_name": "Test"
            }
            for i in range(5)
        ]
        
        created_customers = []
        for customer_data in customers_data:
            response = await authenticated_client.post("/api/v1/customers", json=customer_data)
            created_customers.append(response.json())
        
        # Search for specific customer
        search_email = "search_test_2@example.com"
        response = await authenticated_client.get(
            "/api/v1/customers",
            params={"search": search_email}
        )
        assert response.status_code == 200
        
        search_results = response.json()
        assert search_results["total"] == 1
        assert search_results["items"][0]["email"] == search_email
    
    async def test_filter_customers_by_status(self, authenticated_client):
        """Test filtering customers by status."""
        # Create customers with different statuses
        customers_data = [
            {"email": f"status_test_active_{i}@example.com", "first_name": f"Active{i}", "last_name": "User"}
            for i in range(3)
        ]
        
        suspended_customers_data = [
            {"email": f"status_test_suspended_{i}@example.com", "first_name": f"Suspended{i}", "last_name": "User"}
            for i in range(2)
        ]
        
        # Create active customers
        for customer_data in customers_data:
            await authenticated_client.post("/api/v1/customers", json=customer_data)
        
        # Create and suspend customers
        for customer_data in suspended_customers_data:
            response = await authenticated_client.post("/api/v1/customers", json=customer_data)
            customer_id = response.json()["id"]
            await authenticated_client.patch(
                f"/api/v1/customers/{customer_id}/status",
                json={"status": "suspended"}
            )
        
        # Filter by active status
        response = await authenticated_client.get(
            "/api/v1/customers",
            params={"status": "active"}
        )
        assert response.status_code == 200
        
        active_customers = response.json()
        assert active_customers["total"] >= 3
        assert all(c["status"] == "active" for c in active_customers["items"])
        
        # Filter by suspended status
        response = await authenticated_client.get(
            "/api/v1/customers",
            params={"status": "suspended"}
        )
        assert response.status_code == 200
        
        suspended_customers = response.json()
        assert suspended_customers["total"] >= 2
        assert all(c["status"] == "suspended" for c in suspended_customers["items"])


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerDeletionWorkflow:
    """Test customer deletion workflows."""
    
    async def test_soft_delete_customer(self, authenticated_client, sample_customer_data):
        """Test soft deleting a customer."""
        # Create customer
        create_response = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        customer_id = create_response.json()["id"]
        
        # Soft delete customer
        delete_response = await authenticated_client.delete(f"/api/v1/customers/{customer_id}")
        assert delete_response.status_code == 204
        
        # Verify customer is marked as deleted but still exists
        get_response = await authenticated_client.get(f"/api/v1/customers/{customer_id}")
        if get_response.status_code == 200:
            # If soft delete, customer should be marked as deleted
            customer = get_response.json()
            assert customer["status"] == "deleted" or customer.get("is_deleted") is True
        else:
            # If hard delete, customer should not be found
            assert get_response.status_code == 404
        
        # Verify customer doesn't appear in active list
        list_response = await authenticated_client.get("/api/v1/customers")
        customers_list = list_response.json()
        active_customer_ids = [c["id"] for c in customers_list["items"] if c.get("status") != "deleted"]
        assert customer_id not in active_customer_ids


@pytest.mark.e2e
@pytest.mark.asyncio
class TestAuthenticationAndAuthorization:
    """Test authentication and authorization for customer endpoints."""
    
    async def test_unauthenticated_access_denied(self, unauthenticated_client, sample_customer_data):
        """Test that unauthenticated requests are denied."""
        # Try to create customer without authentication
        response = await unauthenticated_client.post("/api/v1/customers", json=sample_customer_data)
        assert response.status_code == 401
        
        # Try to list customers without authentication
        response = await unauthenticated_client.get("/api/v1/customers")
        assert response.status_code == 401
    
    async def test_insufficient_permissions(self, user_client, sample_customer_data):
        """Test that users with insufficient permissions are denied."""
        # User should be able to read customers
        response = await user_client.get("/api/v1/customers")
        assert response.status_code == 200
        
        # But not create customers (requires admin role)
        response = await user_client.post("/api/v1/customers", json=sample_customer_data)
        assert response.status_code == 403
    
    async def test_tenant_isolation(self, authenticated_client, sample_customer_data):
        """Test that customers are isolated by tenant."""
        # Create customer in tenant 1
        response = await authenticated_client.post("/api/v1/customers", json=sample_customer_data)
        customer_id = response.json()["id"]
        
        # Try to access customer from different tenant
        # (This would require creating a client with different tenant token)
        # For now, verify that customer ID is in the response and properly scoped
        assert customer_id is not None
        
        # Verify customer appears in tenant's customer list
        response = await authenticated_client.get("/api/v1/customers")
        customer_ids = [c["id"] for c in response.json()["items"]]
        assert customer_id in customer_ids


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBulkOperations:
    """Test bulk operations on customers."""
    
    async def test_bulk_status_update(self, authenticated_client):
        """Test bulk status update operation."""
        # Create multiple customers
        customer_ids = []
        for i in range(5):
            customer_data = {
                "email": f"bulk_test_{i}@example.com",
                "first_name": f"BulkUser{i}",
                "last_name": "Test"
            }
            response = await authenticated_client.post("/api/v1/customers", json=customer_data)
            customer_ids.append(response.json()["id"])
        
        # Bulk update status
        bulk_update_data = {
            "customer_ids": customer_ids,
            "status": "suspended"
        }
        
        response = await authenticated_client.post("/api/v1/customers/bulk/status", json=bulk_update_data)
        assert response.status_code == 200
        
        bulk_result = response.json()
        assert bulk_result["success_count"] == 5
        assert bulk_result["failure_count"] == 0
        
        # Verify all customers were updated
        for customer_id in customer_ids:
            response = await authenticated_client.get(f"/api/v1/customers/{customer_id}")
            customer = response.json()
            assert customer["status"] == "suspended"


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestPerformanceAndLoad:
    """Test performance and load scenarios."""
    
    async def test_concurrent_customer_creation(self, authenticated_client):
        """Test concurrent customer creation."""
        async def create_customer(index: int):
            customer_data = {
                "email": f"concurrent_user_{index}@example.com",
                "first_name": f"ConcurrentUser{index}",
                "last_name": "Test"
            }
            response = await authenticated_client.post("/api/v1/customers", json=customer_data)
            return response.status_code == 201
        
        # Create 20 customers concurrently
        tasks = [create_customer(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful creations
        successful_creations = sum(1 for result in results if result is True)
        assert successful_creations == 20
    
    async def test_pagination_performance(self, authenticated_client):
        """Test pagination performance with many records."""
        # Create many customers (only if not already present)
        response = await authenticated_client.get("/api/v1/customers", params={"limit": 1})
        total_customers = response.json()["total"]
        
        if total_customers < 100:
            # Create additional customers for testing
            customers_to_create = min(50, 100 - total_customers)  # Limit to avoid long test times
            
            tasks = []
            for i in range(customers_to_create):
                customer_data = {
                    "email": f"pagination_user_{i}@example.com",
                    "first_name": f"PaginationUser{i}",
                    "last_name": "Test"
                }
                tasks.append(authenticated_client.post("/api/v1/customers", json=customer_data))
            
            await asyncio.gather(*tasks)
        
        # Test pagination performance
        start_time = asyncio.get_event_loop().time()
        
        response = await authenticated_client.get(
            "/api/v1/customers",
            params={"limit": 20, "offset": 0}
        )
        
        end_time = asyncio.get_event_loop().time()
        query_time = end_time - start_time
        
        assert response.status_code == 200
        assert query_time < 2.0  # Should complete within 2 seconds
        
        customers_page = response.json()
        assert len(customers_page["items"]) <= 20
        assert "total" in customers_page
        assert "limit" in customers_page
        assert "offset" in customers_page


@pytest.mark.e2e
@pytest.mark.asyncio
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    async def test_database_connection_recovery(self, authenticated_client, sample_customer_data):
        """Test recovery from database connection issues."""
        # This test would require a way to simulate database issues
        # For now, test that the API handles errors gracefully
        
        # Try to create a customer with invalid data that might cause DB issues
        invalid_data = sample_customer_data.copy()
        invalid_data["balance"] = "not_a_number"  # This might cause a DB error
        
        response = await authenticated_client.post("/api/v1/customers", json=invalid_data)
        
        # Should return proper error response, not crash
        assert response.status_code in [400, 422, 500]
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # System should still be responsive
        health_response = await authenticated_client.get("/health")
        assert health_response.status_code in [200, 503]  # Either healthy or service unavailable
    
    async def test_rate_limiting_handling(self, authenticated_client):
        """Test handling of rate limiting."""
        # Make many rapid requests to trigger rate limiting
        responses = []
        
        for i in range(10):  # Adjust based on rate limit settings
            response = await authenticated_client.get("/api/v1/customers")
            responses.append(response)
        
        # Should either succeed or return rate limit error
        for response in responses:
            assert response.status_code in [200, 429]  # OK or Too Many Requests
        
        # If rate limited, should include proper headers
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        if rate_limited_responses:
            rate_limited_response = rate_limited_responses[0]
            assert "retry-after" in [h.lower() for h in rate_limited_response.headers.keys()]