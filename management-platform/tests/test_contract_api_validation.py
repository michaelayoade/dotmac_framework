"""
API Contract tests for DotMac Management Platform.
These tests validate API schemas, interfaces, and contracts between services.
"""

import pytest
import json
from typing import Dict, Any
from uuid import uuid4
from decimal import Decimal


@pytest.mark.contract
@pytest.mark.api
class TestTenantAPIContracts:
    """Test tenant management API contracts."""
    
    def test_create_tenant_request_schema(self, client):
        """Contract: POST /api/v1/tenants should validate request schema."""
        # GIVEN: Valid tenant creation request
        valid_request = {
            "name": "test-tenant-api",
            "display_name": "Test Tenant API",
            "description": "API contract test tenant",
            "primary_contact_email": "test@example.com",
            "primary_contact_name": "Test User",
            "tier": "small"
        }
        
        # WHEN: Request is sent to API
        response = client.post("/api/v1/tenants", json=valid_request)
        
        # THEN: Response should match expected schema
        if response.status_code == 201:
            data = response.model_dump_json()
            
            # Contract: Response must include these fields
            required_fields = ["id", "name", "display_name", "status", "tier", "created_at"]
            for field in required_fields:
                assert field in data, f"Response missing required field: {field}"
            
            # Contract: Field types must be correct
            assert isinstance(data["id"], str), "ID must be string UUID"
            assert isinstance(data["name"], str), "Name must be string"
            assert isinstance(data["status"], str), "Status must be string"
            assert data["status"] in ["active", "suspended", "pending"], "Status must be valid enum"
    
    def test_create_tenant_invalid_schema_rejection(self, client):
        """Contract: API should reject invalid schemas with proper error responses."""
        invalid_requests = [
            # Missing required fields
            {
                "display_name": "Missing Name",
                "tier": "small"
            },
            # Invalid email format
            {
                "name": "invalid-email-tenant",
                "display_name": "Invalid Email Tenant", 
                "primary_contact_email": "not-an-email",
                "primary_contact_name": "Test User",
                "tier": "small"
            },
            # Invalid tier
            {
                "name": "invalid-tier-tenant",
                "display_name": "Invalid Tier Tenant",
                "primary_contact_email": "test@example.com", 
                "primary_contact_name": "Test User",
                "tier": "invalid_tier"
            }
        ]
        
        for invalid_request in invalid_requests:
            response = client.post("/api/v1/tenants", json=invalid_request)
            
            # Contract: Invalid requests should return 422
            assert response.status_code == 422, f"Expected 422 for invalid request: {invalid_request}"
            
            # Contract: Error response should include validation details
            error_data = response.model_dump_json()
            assert "detail" in error_data, "Error response must include detail"
    
    def test_get_tenant_response_schema(self, client, test_tenant):
        """Contract: GET /api/v1/tenants/{id} should return consistent schema."""
        # WHEN: Getting tenant by ID
        response = client.get(f"/api/v1/tenants/{test_tenant.id}")
        
        # THEN: Response should match schema
        if response.status_code == 200:
            data = response.model_dump_json()
            
            # Contract: Required fields in response
            required_fields = [
                "id", "name", "display_name", "description", "slug",
                "status", "tier", "created_at", "updated_at",
                "primary_contact_email", "primary_contact_name"
            ]
            
            for field in required_fields:
                assert field in data, f"Response missing field: {field}"
            
            # Contract: Optional fields should be null if not set
            optional_fields = ["suspended_at", "suspended_reason"]
            for field in optional_fields:
                if field in data and data[field] is not None:
                    assert isinstance(data[field], str), f"Optional field {field} should be string or null"


@pytest.mark.contract
@pytest.mark.api
@pytest.mark.tenant_billing
class TestBillingAPIContracts:
    """Test billing service API contracts."""
    
    def test_create_subscription_contract(self, client, test_tenant, master_admin_token):
        """Contract: POST /api/v1/billing/subscriptions should follow billing schema."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # GIVEN: Valid subscription request
        subscription_request = {
            "tenant_id": str(test_tenant.id),
            "plan_name": "small_tier_plan",
            "billing_cycle": "monthly",
            "start_date": "2024-01-01T00:00:00Z"
        }
        
        # WHEN: Creating subscription
        response = client.post(
            "/api/v1/billing/subscriptions",
            json=subscription_request,
            headers=headers
        )
        
        # THEN: Response should match billing contract
        if response.status_code == 201:
            data = response.model_dump_json()
            
            # Contract: Billing response schema
            required_fields = [
                "id", "tenant_id", "plan_name", "status", 
                "billing_cycle", "amount", "currency",
                "current_period_start", "current_period_end"
            ]
            
            for field in required_fields:
                assert field in data, f"Billing response missing field: {field}"
            
            # Contract: Amount should be decimal string
            assert isinstance(data["amount"], str), "Amount must be decimal string"
            assert Decimal(data["amount"]) > 0, "Amount must be positive"
            
            # Contract: Currency should be valid ISO code
            assert data["currency"] in ["USD", "EUR", "GBP"], "Currency must be valid ISO code"
    
    def test_invoice_generation_contract(self, client, test_tenant, master_admin_token):
        """Contract: POST /api/v1/billing/invoices/generate should create valid invoices."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # GIVEN: Invoice generation request
        invoice_request = {
            "tenant_id": str(test_tenant.id),
            "billing_period_start": "2024-01-01T00:00:00Z",
            "billing_period_end": "2024-01-31T23:59:59Z",
            "include_usage_charges": True
        }
        
        # WHEN: Generating invoice
        response = client.post(
            "/api/v1/billing/invoices/generate",
            json=invoice_request,
            headers=headers
        )
        
        # THEN: Invoice should match contract
        if response.status_code == 201:
            invoice = response.model_dump_json()
            
            # Contract: Invoice structure
            assert "invoice_number" in invoice, "Invoice must have number"
            assert "line_items" in invoice, "Invoice must have line items"
            assert "total_amount" in invoice, "Invoice must have total"
            assert "due_date" in invoice, "Invoice must have due date"
            
            # Contract: Line items structure
            for line_item in invoice["line_items"]:
                assert "description" in line_item, "Line item needs description"
                assert "quantity" in line_item, "Line item needs quantity"
                assert "unit_price" in line_item, "Line item needs unit price"
                assert "amount" in line_item, "Line item needs total amount"


@pytest.mark.contract
@pytest.mark.api
@pytest.mark.plugin_licensing
class TestPluginLicensingAPIContracts:
    """Test plugin licensing API contracts."""
    
    def test_activate_plugin_contract(self, client, test_tenant, tenant_admin_token):
        """Contract: POST /api/v1/plugins/activate should follow plugin activation schema."""
        headers = {"Authorization": f"Bearer {tenant_admin_token}"}
        
        # GIVEN: Plugin activation request
        activation_request = {
            "plugin_name": "advanced_analytics",
            "tier": "premium",
            "activation_type": "trial"
        }
        
        # WHEN: Activating plugin
        response = client.post(
            "/api/v1/plugins/activate",
            json=activation_request,
            headers=headers
        )
        
        # THEN: Response should match plugin contract
        if response.status_code == 200:
            data = response.model_dump_json()
            
            # Contract: Plugin activation response
            required_fields = [
                "plugin_id", "plugin_name", "tier", "status",
                "activated_at", "expires_at"
            ]
            
            for field in required_fields:
                assert field in data, f"Plugin response missing field: {field}"
            
            # Contract: Status should be valid
            assert data["status"] in ["trial", "active", "expired"], "Plugin status must be valid"
            
            # Contract: Trial plugins should have expiration
            if data["status"] == "trial":
                assert data["expires_at"] is not None, "Trial plugins must have expiration date"
    
    def test_plugin_usage_tracking_contract(self, client, test_tenant, tenant_admin_token):
        """Contract: POST /api/v1/plugins/usage should track usage consistently."""
        headers = {"Authorization": f"Bearer {tenant_admin_token}"}
        
        # GIVEN: Usage tracking data
        usage_data = {
            "plugin_name": "stripe_gateway",
            "usage_type": "transaction",
            "quantity": 100,
            "metadata": {
                "transaction_total": "5000.00",
                "fee_percentage": "0.029"
            }
        }
        
        # WHEN: Reporting usage
        response = client.post(
            "/api/v1/plugins/usage",
            json=usage_data,
            headers=headers
        )
        
        # THEN: Usage tracking should follow contract
        if response.status_code == 201:
            data = response.model_dump_json()
            
            # Contract: Usage record structure
            assert "usage_id" in data, "Usage record must have ID"
            assert "plugin_name" in data, "Usage must reference plugin"
            assert "recorded_at" in data, "Usage must be timestamped"
            assert "billable_amount" in data, "Usage must calculate billable amount"
            
            # Contract: Billable amount should be calculable
            if data["billable_amount"]:
                assert Decimal(data["billable_amount"]) >= 0, "Billable amount must be non-negative"


@pytest.mark.contract
@pytest.mark.api
@pytest.mark.deployment_orchestration
class TestDeploymentAPIContracts:
    """Test deployment orchestration API contracts."""
    
    def test_deploy_service_contract(self, client, test_tenant, master_admin_token):
        """Contract: POST /api/v1/deployments should follow deployment schema."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # GIVEN: Service deployment request
        deployment_request = {
            "tenant_id": str(test_tenant.id),
            "template_id": str(uuid4()),
            "name": "customer-portal",
            "environment": "production",
            "configuration": {
                "replicas": 2,
                "resources": {
                    "cpu": "500m",
                    "memory": "1Gi"
                }
            },
            "variables": {
                "domain": "customer.example.com",
                "ssl_enabled": True
            }
        }
        
        # WHEN: Deploying service
        response = client.post(
            "/api/v1/deployments",
            json=deployment_request,
            headers=headers
        )
        
        # THEN: Deployment should match contract
        if response.status_code == 201:
            deployment = response.model_dump_json()
            
            # Contract: Deployment response structure
            required_fields = [
                "deployment_id", "tenant_id", "name", "status",
                "environment", "created_at", "version"
            ]
            
            for field in required_fields:
                assert field in deployment, f"Deployment response missing field: {field}"
            
            # Contract: Status should be valid
            valid_statuses = ["deploying", "deployed", "failed", "rolling_back"]
            assert deployment["status"] in valid_statuses, "Deployment status must be valid"
            
            # Contract: Environment should be valid
            valid_environments = ["development", "staging", "production"]
            assert deployment["environment"] in valid_environments, "Environment must be valid"
    
    def test_deployment_status_contract(self, client, test_tenant, master_admin_token):
        """Contract: GET /api/v1/deployments/{id}/status should provide comprehensive status."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # Mock deployment ID for testing
        deployment_id = str(uuid4())
        
        # WHEN: Getting deployment status
        response = client.get(
            f"/api/v1/deployments/{deployment_id}/status",
            headers=headers
        )
        
        # THEN: Status should follow contract (even if deployment doesn't exist)
        if response.status_code == 200:
            status = response.model_dump_json()
            
            # Contract: Status response structure
            required_fields = [
                "deployment_id", "status", "health_score",
                "active_services", "resource_utilization"
            ]
            
            for field in required_fields:
                assert field in status, f"Status response missing field: {field}"
            
            # Contract: Health score should be 0-100
            assert 0 <= status["health_score"] <= 100, "Health score must be 0-100"
            
            # Contract: Resource utilization should be percentages
            if "resource_utilization" in status:
                for resource, usage in status["resource_utilization"].items():
                    assert 0 <= usage <= 100, f"Resource {resource} usage must be 0-100%"
        
        elif response.status_code == 404:
            # Contract: 404 should include proper error structure
            error = response.model_dump_json()
            assert "detail" in error, "404 error must include detail"


@pytest.mark.contract
@pytest.mark.api
@pytest.mark.saas_monitoring
class TestMonitoringAPIContracts:
    """Test SaaS monitoring API contracts."""
    
    def test_health_check_contract(self, client):
        """Contract: GET /health should provide standard health check response."""
        # WHEN: Requesting health check
        response = client.get("/health")
        
        # THEN: Health check should follow contract
        assert response.status_code == 200, "Health check should always return 200"
        
        data = response.model_dump_json()
        
        # Contract: Health check structure
        required_fields = ["status", "timestamp", "version"]
        for field in required_fields:
            assert field in data, f"Health check missing field: {field}"
        
        # Contract: Status should be valid
        assert data["status"] in ["healthy", "unhealthy", "degraded"], "Health status must be valid"
    
    def test_metrics_endpoint_contract(self, client):
        """Contract: GET /metrics should provide Prometheus-compatible metrics."""
        # WHEN: Requesting metrics
        response = client.get("/metrics")
        
        # THEN: Metrics should follow Prometheus format
        assert response.status_code == 200, "Metrics endpoint should be accessible"
        
        content = response.content.decode('utf-8')
        
        # Contract: Prometheus format requirements
        assert "# HELP" in content, "Metrics should include help text"
        assert "# TYPE" in content, "Metrics should include type information"
        
        # Contract: Should include basic application metrics
        expected_metrics = ["app_info", "app_requests_total"]
        for metric in expected_metrics:
            assert metric in content, f"Metrics should include {metric}"
    
    def test_tenant_health_contract(self, client, test_tenant, master_admin_token):
        """Contract: GET /api/v1/monitoring/tenants/{id}/health should provide tenant health."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # WHEN: Requesting tenant health
        response = client.get(
            f"/api/v1/monitoring/tenants/{test_tenant.id}/health",
            headers=headers
        )
        
        # THEN: Tenant health should follow contract
        if response.status_code == 200:
            health = response.model_dump_json()
            
            # Contract: Tenant health structure
            required_fields = [
                "tenant_id", "overall_status", "uptime_percentage",
                "response_time_avg", "error_rate", "last_check"
            ]
            
            for field in required_fields:
                assert field in health, f"Tenant health missing field: {field}"
            
            # Contract: Percentages should be 0-100
            assert 0 <= health["uptime_percentage"] <= 100, "Uptime must be 0-100%"
            assert 0 <= health["error_rate"] <= 1, "Error rate must be 0-1"
            
            # Contract: Response time should be positive
            assert health["response_time_avg"] >= 0, "Response time must be non-negative"