"""
Cross-Platform Integration Tests

Tests the integration between ISP Framework and Management Platform,
validating that both platforms work together correctly for critical workflows.
"""

import asyncio
import pytest
import httpx
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta

from tests.conftest import (
    isp_framework_client,
    management_platform_client,
    test_database,
    cleanup_test_data
)


class TestCrossPlatformIntegration:
    """Integration tests for ISP Framework ↔ Management Platform"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_customer_lifecycle_across_platforms(
        self,
        isp_framework_client: httpx.AsyncClient,
        management_platform_client: httpx.AsyncClient
    ):
        """
        Test complete customer lifecycle across both platforms:
        1. Management Platform creates tenant
        2. ISP Framework provisions customer
        3. Customer uses services
        4. Billing data flows back to Management Platform
        """
        # Step 1: Create tenant in Management Platform
        tenant_data = {
            "name": f"Test ISP {uuid4()}",
            "domain": "test-isp.local",
            "admin_email": "admin@test-isp.local",
            "billing_enabled": True
        }
        
        mgmt_response = await management_platform_client.post(
            "/api/v1/tenants/",
            json=tenant_data
        )
        assert mgmt_response.status_code == 201
        tenant = mgmt_response.json()
        tenant_id = tenant["id"]
        
        try:
            # Step 2: Create customer in ISP Framework
            customer_data = {
                "tenant_id": tenant_id,
                "customer_number": f"CUS-{uuid4().hex[:8].upper()}",
                "display_name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1-555-123-4567",
                "billing_address": {
                    "street": "123 Main St",
                    "city": "Anytown", 
                    "state": "CA",
                    "zip": "12345",
                    "country": "US"
                }
            }
            
            isp_response = await isp_framework_client.post(
                "/api/v1/customers/",
                json=customer_data,
                headers={"X-Tenant-ID": tenant_id}
            )
            assert isp_response.status_code == 201
            customer = isp_response.json()
            customer_id = customer["customer_id"]
            
            # Step 3: Provision service for customer
            service_data = {
                "customer_id": customer_id,
                "service_type": "internet",
                "bandwidth_mbps": 100,
                "monthly_cost": "49.99",
                "contract_length_months": 12
            }
            
            service_response = await isp_framework_client.post(
                "/api/v1/services/",
                json=service_data,
                headers={"X-Tenant-ID": tenant_id}
            )
            assert service_response.status_code == 201
            service = service_response.json()
            
            # Step 4: Simulate usage and billing
            usage_data = {
                "customer_id": customer_id,
                "service_id": service["service_id"],
                "usage_gb": 150.5,
                "billing_period_start": datetime.utcnow().isoformat(),
                "billing_period_end": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            usage_response = await isp_framework_client.post(
                "/api/v1/billing/usage/",
                json=usage_data,
                headers={"X-Tenant-ID": tenant_id}
            )
            assert usage_response.status_code == 201
            
            # Step 5: Verify data sync to Management Platform
            # Wait for async processing
            await asyncio.sleep(2)
            
            # Check if customer data synced to Management Platform
            sync_response = await management_platform_client.get(
                f"/api/v1/tenants/{tenant_id}/customers/{customer_id}"
            )
            assert sync_response.status_code == 200
            synced_customer = sync_response.json()
            assert synced_customer["email"] == customer_data["email"]
            
            # Check if billing data synced
            billing_response = await management_platform_client.get(
                f"/api/v1/tenants/{tenant_id}/billing/usage",
                params={"customer_id": customer_id}
            )
            assert billing_response.status_code == 200
            billing_data = billing_response.json()
            assert len(billing_data["usage_records"]) > 0
            
        finally:
            # Cleanup: Delete tenant (cascades to customer and services)
            cleanup_response = await management_platform_client.delete(
                f"/api/v1/tenants/{tenant_id}"
            )
            assert cleanup_response.status_code in [200, 204]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_monitoring_integration(
        self,
        isp_framework_client: httpx.AsyncClient,
        management_platform_client: httpx.AsyncClient
    ):
        """Test network monitoring data flows between platforms"""
        
        # Create test tenant
        tenant_data = {
            "name": f"Network Test ISP {uuid4()}",
            "domain": "network-test.local",
            "admin_email": "admin@network-test.local"
        }
        
        mgmt_response = await management_platform_client.post(
            "/api/v1/tenants/",
            json=tenant_data
        )
        assert mgmt_response.status_code == 201
        tenant_id = mgmt_response.json()["id"]
        
        try:
            # Add network device in ISP Framework
            device_data = {
                "tenant_id": tenant_id,
                "device_type": "router",
                "ip_address": "192.168.1.1",
                "snmp_community": "public",
                "location": "Main POP"
            }
            
            device_response = await isp_framework_client.post(
                "/api/v1/network/devices/",
                json=device_data,
                headers={"X-Tenant-ID": tenant_id}
            )
            assert device_response.status_code == 201
            device = device_response.json()
            
            # Simulate network metrics collection
            metrics_data = {
                "device_id": device["device_id"],
                "metrics": {
                    "cpu_usage": 45.2,
                    "memory_usage": 67.8,
                    "bandwidth_utilization": 34.5,
                    "uptime_seconds": 864000
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            metrics_response = await isp_framework_client.post(
                "/api/v1/network/metrics/",
                json=metrics_data,
                headers={"X-Tenant-ID": tenant_id}
            )
            assert metrics_response.status_code == 201
            
            # Verify metrics appear in Management Platform dashboard
            await asyncio.sleep(1)
            
            dashboard_response = await management_platform_client.get(
                f"/api/v1/tenants/{tenant_id}/dashboard/network-status"
            )
            assert dashboard_response.status_code == 200
            dashboard_data = dashboard_response.json()
            
            # Should have at least one device with recent metrics
            assert len(dashboard_data["devices"]) >= 1
            device_status = dashboard_data["devices"][0]
            assert device_status["device_id"] == device["device_id"]
            assert "cpu_usage" in device_status["latest_metrics"]
            
        finally:
            # Cleanup
            cleanup_response = await management_platform_client.delete(
                f"/api/v1/tenants/{tenant_id}"
            )
            assert cleanup_response.status_code in [200, 204]
    
    @pytest.mark.integration
    @pytest.mark.asyncio  
    async def test_billing_aggregation_integration(
        self,
        isp_framework_client: httpx.AsyncClient,
        management_platform_client: httpx.AsyncClient
    ):
        """Test billing data aggregation across platforms"""
        
        # Create tenant with multiple customers
        tenant_data = {
            "name": f"Billing Test ISP {uuid4()}",
            "domain": "billing-test.local",
            "admin_email": "admin@billing-test.local"
        }
        
        mgmt_response = await management_platform_client.post(
            "/api/v1/tenants/",
            json=tenant_data
        )
        assert mgmt_response.status_code == 201
        tenant_id = mgmt_response.json()["id"]
        
        try:
            customer_ids = []
            total_expected_revenue = 0
            
            # Create multiple customers with different service tiers
            for i in range(3):
                customer_data = {
                    "tenant_id": tenant_id,
                    "customer_number": f"CUS-BILL-{i:03d}",
                    "display_name": f"Customer {i}",
                    "email": f"customer{i}@example.com",
                    "phone": f"+1-555-100-000{i}"
                }
                
                customer_response = await isp_framework_client.post(
                    "/api/v1/customers/",
                    json=customer_data,
                    headers={"X-Tenant-ID": tenant_id}
                )
                assert customer_response.status_code == 201
                customer = customer_response.json()
                customer_ids.append(customer["customer_id"])
                
                # Different service tiers
                service_costs = ["29.99", "49.99", "99.99"]
                service_data = {
                    "customer_id": customer["customer_id"],
                    "service_type": "internet",
                    "bandwidth_mbps": (i + 1) * 50,
                    "monthly_cost": service_costs[i],
                    "contract_length_months": 12
                }
                
                service_response = await isp_framework_client.post(
                    "/api/v1/services/",
                    json=service_data,
                    headers={"X-Tenant-ID": tenant_id}
                )
                assert service_response.status_code == 201
                total_expected_revenue += float(service_costs[i])
            
            # Generate billing data
            for customer_id in customer_ids:
                billing_data = {
                    "customer_id": customer_id,
                    "billing_period": "2024-01",
                    "generate_invoice": True
                }
                
                billing_response = await isp_framework_client.post(
                    "/api/v1/billing/generate/",
                    json=billing_data,
                    headers={"X-Tenant-ID": tenant_id}
                )
                assert billing_response.status_code == 201
            
            # Wait for aggregation processing
            await asyncio.sleep(3)
            
            # Verify aggregated revenue in Management Platform
            revenue_response = await management_platform_client.get(
                f"/api/v1/tenants/{tenant_id}/analytics/revenue",
                params={"period": "2024-01"}
            )
            assert revenue_response.status_code == 200
            revenue_data = revenue_response.json()
            
            # Should match expected revenue (within small margin for taxes/fees)
            actual_revenue = float(revenue_data["total_revenue"])
            assert abs(actual_revenue - total_expected_revenue) <= 10.0, \
                f"Revenue mismatch: expected ~{total_expected_revenue}, got {actual_revenue}"
            
            # Verify customer count
            assert revenue_data["customer_count"] == 3
            
        finally:
            # Cleanup
            cleanup_response = await management_platform_client.delete(
                f"/api/v1/tenants/{tenant_id}"
            )
            assert cleanup_response.status_code in [200, 204]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_authentication_integration(
        self,
        isp_framework_client: httpx.AsyncClient,
        management_platform_client: httpx.AsyncClient
    ):
        """Test authentication and authorization across platforms"""
        
        # Create tenant admin user in Management Platform
        admin_data = {
            "email": "tenant-admin@example.com",
            "password": "SecurePass123!",
            "first_name": "Tenant",
            "last_name": "Admin",
            "role": "tenant_admin"
        }
        
        admin_response = await management_platform_client.post(
            "/api/v1/auth/register/",
            json=admin_data
        )
        assert admin_response.status_code == 201
        
        # Login to get JWT token
        login_response = await management_platform_client.post(
            "/api/v1/auth/login/",
            json={
                "email": admin_data["email"],
                "password": admin_data["password"]
            }
        )
        assert login_response.status_code == 200
        auth_data = login_response.json()
        jwt_token = auth_data["access_token"]
        
        # Verify token works in Management Platform
        profile_response = await management_platform_client.get(
            "/api/v1/auth/profile/",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert profile_response.status_code == 200
        
        # Verify same token works in ISP Framework (cross-platform auth)
        isp_profile_response = await isp_framework_client.get(
            "/api/v1/auth/profile/",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert isp_profile_response.status_code == 200
        
        # Both should return same user data
        mgmt_profile = profile_response.json()
        isp_profile = isp_profile_response.json()
        assert mgmt_profile["email"] == isp_profile["email"]
        assert mgmt_profile["user_id"] == isp_profile["user_id"]


@pytest.mark.integration
class TestServiceDependencies:
    """Test dependencies between services"""
    
    @pytest.mark.asyncio
    async def test_database_consistency(self, test_database):
        """Test that both platforms maintain database consistency"""
        # This would test shared database scenarios
        # and ensure ACID properties are maintained
        pass
    
    @pytest.mark.asyncio 
    async def test_message_queue_integration(self):
        """Test Redis pub/sub between platforms"""
        # Test that events published by one platform
        # are received by the other
        pass
    
    @pytest.mark.asyncio
    async def test_secrets_management_integration(self):
        """Test OpenBao secrets sharing between platforms"""
        # Test that secrets stored by one platform
        # can be accessed by the other with proper permissions
        pass


@pytest.mark.contract
class TestAPIContracts:
    """Test API contracts between platforms"""
    
    def test_isp_framework_openapi_schema(self):
        """Validate ISP Framework OpenAPI schema"""
        # Load and validate OpenAPI spec
        pass
    
    def test_management_platform_openapi_schema(self):
        """Validate Management Platform OpenAPI schema"""
        # Load and validate OpenAPI spec 
        pass
    
    def test_cross_platform_api_compatibility(self):
        """Test that APIs are compatible for integration"""
        # Test that shared data models are compatible
        pass