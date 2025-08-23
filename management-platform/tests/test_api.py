"""
Integration tests for API endpoints.
"""

import json
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_register_user_success(self, client: TestClient, test_tenant, master_admin_token):
        """Test successful user registration."""
        # Auth registration is public - no authorization header needed
        
        register_data = {
            "email": "apitest@example.com",
            "password": "SecurePassword123!",
            "full_name": "API Test User",
            "role": "tenant_user",
            "tenant_id": str(test_tenant.id)
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json=register_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "apitest@example.com"
        assert data["full_name"] == "API Test User"
        assert data["role"] == "tenant_user"
        assert "id" in data
    
    def test_register_invalid_email(self, client: TestClient, test_tenant, master_admin_token):
        """Test registration with invalid email."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        register_data = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "first_name": "Invalid",
            "last_name": "Email"
        }
        
        response = client.post(
            f"/api/v1/tenants/{test_tenant.id}/users",
            json=register_data,
            headers=headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user.email
    
    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Test login with invalid credentials."""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["detail"]
    
    def test_protected_endpoint_no_token(self, client: TestClient):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 403
    
    def test_protected_endpoint_with_token(self, client: TestClient, tenant_user_token):
        """Test accessing protected endpoint with valid token."""
        headers = {"Authorization": f"Bearer {tenant_user_token}"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data


@pytest.mark.integration
class TestTenantEndpoints:
    """Test tenant management API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_tenant_success(self, client: TestClient, master_admin_token):
        """Test successful tenant creation."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        tenant_data = {
            "name": "api-test-tenant",
            "display_name": "API Test Tenant",
            "description": "Created via API test",
            "primary_contact_email": "contact@api-test-tenant.com",
            "primary_contact_name": "API Test Contact"
        }
        
        response = client.post("/api/v1/tenants", json=tenant_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # The response follows ResponseBuilder format with 'data' containing the tenant
        assert data["status"] == "success"
        tenant_data_response = data["data"]
        assert tenant_data_response["name"] == "api-test-tenant"
        assert tenant_data_response["display_name"] == "API Test Tenant"
        assert tenant_data_response["status"] == "pending"
    
    def test_create_tenant_unauthorized(self, client: TestClient, tenant_user_token):
        """Test tenant creation with insufficient permissions."""
        headers = {"Authorization": f"Bearer {tenant_user_token}"}
        
        tenant_data = {
            "name": "unauthorized-tenant",
            "display_name": "Should Fail",
        }
        
        response = client.post("/api/v1/tenants", json=tenant_data, headers=headers)
        
        assert response.status_code == 403
    
    def test_list_tenants_master_admin(self, client: TestClient, master_admin_token):
        """Test listing tenants as master admin."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        response = client.get("/api/v1/tenants", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "tenants" in data
        assert "total" in data
        assert isinstance(data["tenants"], list)
    
    def test_get_tenant_details(self, client: TestClient, test_tenant, master_admin_token):
        """Test getting tenant details."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        response = client.get(f"/api/v1/tenants/{test_tenant.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_tenant.id)
        assert data["name"] == test_tenant.name
    
    def test_update_tenant_success(self, client: TestClient, test_tenant, master_admin_token):
        """Test successful tenant update."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        update_data = {
            "display_name": "Updated via API",
            "description": "Updated description"
        }
        
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated via API"
        assert data["description"] == "Updated description"
    
    def test_tenant_isolation_violation(self, client: TestClient, test_tenant, tenant_admin_token):
        """Test that tenants cannot access other tenant data."""
        from uuid import uuid4
        
        headers = {"Authorization": f"Bearer {tenant_admin_token}"}
        fake_tenant_id = str(uuid4())
        
        response = client.get(f"/api/v1/tenants/{fake_tenant_id}", headers=headers)
        
        assert response.status_code == 403


@pytest.mark.integration
class TestBillingEndpoints:
    """Test billing API endpoints."""
    
    def test_create_subscription_success(self, client: TestClient, test_tenant, master_admin_token):
        """Test successful subscription creation."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        subscription_data = {
            "plan_name": "premium",
            "billing_cycle": "monthly",
            "price": 199.99,
            "currency": "USD"
        }
        
        response = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscriptions",
            json=subscription_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["plan_name"] == "premium"
        assert data["tenant_id"] == str(test_tenant.id)
        assert data["status"] == "active"
    
    def test_get_tenant_billing_overview(self, client: TestClient, test_tenant, tenant_admin_token):
        """Test getting tenant billing overview."""
        headers = {"Authorization": f"Bearer {tenant_admin_token}"}
        
        response = client.get(f"/api/v1/billing/overview/{test_tenant.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data
        assert "current_subscription" in data
        assert "total_invoices" in data
    
    def test_get_tenant_invoices(self, client: TestClient, test_tenant, tenant_admin_token):
        """Test getting tenant invoices."""
        headers = {"Authorization": f"Bearer {tenant_admin_token}"}
        
        response = client.get(f"/api/v1/billing/{test_tenant.id}/invoices", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration  
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test basic health check."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_database_health_check(self, client: TestClient):
        """Test database health check."""
        response = client.get("/api/v1/health/database")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "response_time" in data
    
    def test_metrics_endpoint(self, client: TestClient):
        """Test metrics endpoint for monitoring."""
        response = client.get("/metrics")
        
        # Should return Prometheus-style metrics
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


@pytest.mark.integration
class TestRateLimiting:
    """Test API rate limiting."""
    
    def test_rate_limiting_enforcement(self, client: TestClient):
        """Test that rate limiting is enforced.""" 
        # Make multiple rapid requests
        responses = []
        for _ in range(150):  # Exceed limit of 100/minute from config
            response = client.get("/api/v1/health")
            responses.append(response)
        
        # Should eventually get rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0
    
    def test_rate_limit_headers(self, client: TestClient):
        """Test that rate limit headers are present."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        # Should include rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


@pytest.mark.integration
class TestCORSHandling:
    """Test CORS handling."""
    
    def test_cors_preflight_request(self, client: TestClient):
        """Test CORS preflight request."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        
        response = client.options("/api/v1/tenants", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
    
    def test_cors_actual_request(self, client: TestClient, master_admin_token):
        """Test actual request with CORS headers."""
        headers = {
            "Origin": "http://localhost:3000",
            "Authorization": f"Bearer {master_admin_token}"
        }
        
        response = client.get("/api/v1/tenants", headers=headers)
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"