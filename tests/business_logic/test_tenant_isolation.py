"""
Critical Business Logic Tests for Multi-Tenant Data Isolation

These tests validate that tenant data isolation is maintained across all operations.
Data leakage between tenants would be a critical security and business failure.
"""

import pytest
import asyncio
from uuid import uuid4
from typing import List, Dict, Any
from decimal import Decimal

from hypothesis import given, strategies as st, settings, assume
from tests.conftest import async_test_client, test_database, cleanup_test_data


class TestTenantDataIsolation:
    """Test critical tenant isolation business rules"""
    
    @pytest.mark.business_critical
    @pytest.mark.asyncio
    async def test_customer_data_isolation(self, async_test_client):
        """
        CRITICAL: Ensure customers from one tenant cannot see data from another tenant
        """
        # Create two separate tenants
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())
        
        # Create customers in each tenant
        customer_a_data = {
            "tenant_id": tenant_a_id,
            "customer_number": "TENANT-A-001",
            "display_name": "Alice from Tenant A",
            "email": "alice@tenant-a.com",
            "phone": "+1-555-AAA-0001"
        }
        
        customer_b_data = {
            "tenant_id": tenant_b_id,
            "customer_number": "TENANT-B-001", 
            "display_name": "Bob from Tenant B",
            "email": "bob@tenant-b.com",
            "phone": "+1-555-BBB-0001"
        }
        
        # Create customer A
        response_a = await async_test_client.post(
            "/api/v1/customers/",
            json=customer_a_data,
            headers={"X-Tenant-ID": tenant_a_id}
        )
        assert response_a.status_code == 201
        customer_a = response_a.json()
        
        # Create customer B  
        response_b = await async_test_client.post(
            "/api/v1/customers/",
            json=customer_b_data,
            headers={"X-Tenant-ID": tenant_b_id}
        )
        assert response_b.status_code == 201
        customer_b = response_b.json()
        
        try:
            # CRITICAL TEST: Tenant A should not see Tenant B's customer
            tenant_a_customers = await async_test_client.get(
                "/api/v1/customers/",
                headers={"X-Tenant-ID": tenant_a_id}
            )
            assert tenant_a_customers.status_code == 200
            customers_a = tenant_a_customers.json()
            
            # Should only see their own customer
            assert len(customers_a["customers"]) == 1
            assert customers_a["customers"][0]["customer_id"] == customer_a["customer_id"]
            assert customers_a["customers"][0]["email"] == "alice@tenant-a.com"
            
            # CRITICAL TEST: Tenant B should not see Tenant A's customer
            tenant_b_customers = await async_test_client.get(
                "/api/v1/customers/", 
                headers={"X-Tenant-ID": tenant_b_id}
            )
            assert tenant_b_customers.status_code == 200
            customers_b = tenant_b_customers.json()
            
            # Should only see their own customer
            assert len(customers_b["customers"]) == 1
            assert customers_b["customers"][0]["customer_id"] == customer_b["customer_id"]
            assert customers_b["customers"][0]["email"] == "bob@tenant-b.com"
            
            # CRITICAL TEST: Tenant A cannot access Tenant B's customer directly
            unauthorized_access = await async_test_client.get(
                f"/api/v1/customers/{customer_b['customer_id']}/",
                headers={"X-Tenant-ID": tenant_a_id}
            )
            assert unauthorized_access.status_code == 404, \
                "Tenant A should not be able to access Tenant B's customer"
            
            # CRITICAL TEST: Tenant B cannot access Tenant A's customer directly
            unauthorized_access_2 = await async_test_client.get(
                f"/api/v1/customers/{customer_a['customer_id']}/",
                headers={"X-Tenant-ID": tenant_b_id}
            )
            assert unauthorized_access_2.status_code == 404, \
                "Tenant B should not be able to access Tenant A's customer"
                
        finally:
            # Cleanup
            await cleanup_test_data([customer_a["customer_id"], customer_b["customer_id"]])
    
    @pytest.mark.business_critical
    @pytest.mark.asyncio
    async def test_billing_data_isolation(self, async_test_client):
        """
        CRITICAL: Billing data must be completely isolated between tenants
        """
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())
        
        # Create customers and services for each tenant
        customer_a_data = {
            "tenant_id": tenant_a_id,
            "customer_number": "BILL-A-001",
            "display_name": "Alice Billing",
            "email": "alice-bill@tenant-a.com"
        }
        
        customer_b_data = {
            "tenant_id": tenant_b_id,
            "customer_number": "BILL-B-001",
            "display_name": "Bob Billing", 
            "email": "bob-bill@tenant-b.com"
        }
        
        # Create customers
        customer_a_resp = await async_test_client.post(
            "/api/v1/customers/",
            json=customer_a_data,
            headers={"X-Tenant-ID": tenant_a_id}
        )
        customer_a = customer_a_resp.json()
        
        customer_b_resp = await async_test_client.post(
            "/api/v1/customers/",
            json=customer_b_data,
            headers={"X-Tenant-ID": tenant_b_id}
        )
        customer_b = customer_b_resp.json()
        
        try:
            # Create high-value service for Tenant A (confidential pricing)
            service_a_data = {
                "customer_id": customer_a["customer_id"],
                "service_type": "enterprise_fiber",
                "bandwidth_mbps": 1000,
                "monthly_cost": "2999.99",  # High-value enterprise customer
                "contract_length_months": 24
            }
            
            service_a_resp = await async_test_client.post(
                "/api/v1/services/",
                json=service_a_data,
                headers={"X-Tenant-ID": tenant_a_id}
            )
            service_a = service_a_resp.json()
            
            # Create standard service for Tenant B
            service_b_data = {
                "customer_id": customer_b["customer_id"],
                "service_type": "residential_cable",
                "bandwidth_mbps": 100,
                "monthly_cost": "49.99",
                "contract_length_months": 12
            }
            
            service_b_resp = await async_test_client.post(
                "/api/v1/services/",
                json=service_b_data,
                headers={"X-Tenant-ID": tenant_b_id}
            )
            service_b = service_b_resp.json()
            
            # Generate billing records
            billing_a_data = {
                "customer_id": customer_a["customer_id"],
                "service_id": service_a["service_id"],
                "usage_gb": 5000.0,
                "billing_period": "2024-01",
                "amount": "2999.99"
            }
            
            billing_b_data = {
                "customer_id": customer_b["customer_id"],
                "service_id": service_b["service_id"],
                "usage_gb": 150.0,
                "billing_period": "2024-01", 
                "amount": "49.99"
            }
            
            # Create billing records
            await async_test_client.post(
                "/api/v1/billing/records/",
                json=billing_a_data,
                headers={"X-Tenant-ID": tenant_a_id}
            )
            
            await async_test_client.post(
                "/api/v1/billing/records/",
                json=billing_b_data,
                headers={"X-Tenant-ID": tenant_b_id}
            )
            
            # CRITICAL TEST: Tenant A billing data is isolated
            billing_a_resp = await async_test_client.get(
                "/api/v1/billing/records/",
                headers={"X-Tenant-ID": tenant_a_id}
            )
            assert billing_a_resp.status_code == 200
            billing_a_records = billing_a_resp.json()
            
            # Should only see their own $2999.99 record
            assert len(billing_a_records["records"]) == 1
            assert billing_a_records["records"][0]["amount"] == "2999.99"
            assert billing_a_records["records"][0]["customer_id"] == customer_a["customer_id"]
            
            # CRITICAL TEST: Tenant B billing data is isolated  
            billing_b_resp = await async_test_client.get(
                "/api/v1/billing/records/",
                headers={"X-Tenant-ID": tenant_b_id}
            )
            assert billing_b_resp.status_code == 200
            billing_b_records = billing_b_resp.json()
            
            # Should only see their own $49.99 record
            assert len(billing_b_records["records"]) == 1
            assert billing_b_records["records"][0]["amount"] == "49.99"
            assert billing_b_records["records"][0]["customer_id"] == customer_b["customer_id"]
            
            # CRITICAL TEST: Revenue totals are isolated
            revenue_a_resp = await async_test_client.get(
                "/api/v1/analytics/revenue/",
                params={"period": "2024-01"},
                headers={"X-Tenant-ID": tenant_a_id}
            )
            revenue_a = revenue_a_resp.json()
            assert float(revenue_a["total_revenue"]) >= 2999.99
            
            revenue_b_resp = await async_test_client.get(
                "/api/v1/analytics/revenue/",
                params={"period": "2024-01"},
                headers={"X-Tenant-ID": tenant_b_id}
            )
            revenue_b = revenue_b_resp.json()
            assert float(revenue_b["total_revenue"]) <= 100.00  # Should be around $49.99
            
        finally:
            # Cleanup
            await cleanup_test_data([
                customer_a["customer_id"], 
                customer_b["customer_id"],
                service_a["service_id"] if 'service_a' in locals() else None,
                service_b["service_id"] if 'service_b' in locals() else None
            ])
    
    @given(
        tenant_count=st.integers(min_value=2, max_value=5),
        customers_per_tenant=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=50, deadline=30000)
    @pytest.mark.property_based
    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_property(
        self, 
        async_test_client,
        tenant_count: int, 
        customers_per_tenant: int
    ):
        """
        Property-based test: Multi-tenant data isolation should hold
        regardless of number of tenants or customers per tenant
        """
        tenant_ids = [str(uuid4()) for _ in range(tenant_count)]
        all_customers = {}  # tenant_id -> [customer_ids]
        
        try:
            # Create customers for each tenant
            for tenant_id in tenant_ids:
                tenant_customers = []
                
                for i in range(customers_per_tenant):
                    customer_data = {
                        "tenant_id": tenant_id,
                        "customer_number": f"{tenant_id[:8]}-{i:03d}",
                        "display_name": f"Customer {i} of {tenant_id[:8]}",
                        "email": f"customer{i}@{tenant_id[:8]}.com"
                    }
                    
                    response = await async_test_client.post(
                        "/api/v1/customers/",
                        json=customer_data,
                        headers={"X-Tenant-ID": tenant_id}
                    )
                    
                    if response.status_code == 201:
                        customer = response.json()
                        tenant_customers.append(customer["customer_id"])
                
                all_customers[tenant_id] = tenant_customers
            
            # PROPERTY: Each tenant should only see their own customers
            for tenant_id in tenant_ids:
                customers_resp = await async_test_client.get(
                    "/api/v1/customers/",
                    headers={"X-Tenant-ID": tenant_id}
                )
                
                if customers_resp.status_code == 200:
                    customers_data = customers_resp.json()
                    visible_customer_ids = [
                        c["customer_id"] for c in customers_data.get("customers", [])
                    ]
                    
                    # Should only see own customers
                    expected_customer_ids = set(all_customers[tenant_id])
                    actual_customer_ids = set(visible_customer_ids)
                    
                    assert actual_customer_ids == expected_customer_ids, \
                        f"Tenant {tenant_id[:8]} sees wrong customers: " \
                        f"expected {expected_customer_ids}, got {actual_customer_ids}"
                    
                    # Should not see any other tenant's customers
                    for other_tenant_id, other_customer_ids in all_customers.items():
                        if other_tenant_id != tenant_id:
                            overlap = actual_customer_ids.intersection(set(other_customer_ids))
                            assert len(overlap) == 0, \
                                f"Data leak: Tenant {tenant_id[:8]} can see " \
                                f"customers from {other_tenant_id[:8]}: {overlap}"
        
        finally:
            # Cleanup all created customers
            all_customer_ids = []
            for customer_list in all_customers.values():
                all_customer_ids.extend(customer_list)
            await cleanup_test_data(all_customer_ids)


class TestBusinessRuleValidation:
    """Test critical business rules that must always be enforced"""
    
    @pytest.mark.business_critical
    @pytest.mark.asyncio
    async def test_duplicate_customer_numbers_prevented(self, async_test_client):
        """
        CRITICAL: Customer numbers must be unique within a tenant
        but can be duplicated across tenants
        """
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4()) 
        duplicate_customer_number = "DUP-TEST-001"
        
        # Create customer with specific number in Tenant A
        customer_a_data = {
            "tenant_id": tenant_a_id,
            "customer_number": duplicate_customer_number,
            "display_name": "First Customer",
            "email": "first@tenant-a.com"
        }
        
        response_a = await async_test_client.post(
            "/api/v1/customers/",
            json=customer_a_data,
            headers={"X-Tenant-ID": tenant_a_id}
        )
        assert response_a.status_code == 201
        customer_a = response_a.json()
        
        try:
            # Try to create another customer with same number in Tenant A (should fail)
            duplicate_data = {
                "tenant_id": tenant_a_id,
                "customer_number": duplicate_customer_number,
                "display_name": "Duplicate Customer",
                "email": "duplicate@tenant-a.com"
            }
            
            duplicate_response = await async_test_client.post(
                "/api/v1/customers/",
                json=duplicate_data,
                headers={"X-Tenant-ID": tenant_a_id}
            )
            assert duplicate_response.status_code == 409, \
                "Duplicate customer number should be rejected within same tenant"
            
            # Create customer with same number in different tenant (should succeed)
            customer_b_data = {
                "tenant_id": tenant_b_id,
                "customer_number": duplicate_customer_number,  # Same number, different tenant
                "display_name": "Different Tenant Customer",
                "email": "customer@tenant-b.com"
            }
            
            response_b = await async_test_client.post(
                "/api/v1/customers/",
                json=customer_b_data,
                headers={"X-Tenant-ID": tenant_b_id}
            )
            assert response_b.status_code == 201, \
                "Same customer number should be allowed in different tenant"
            customer_b = response_b.json()
            
            # Verify both customers exist with same number but different tenants
            assert customer_a["customer_number"] == customer_b["customer_number"]
            assert customer_a["tenant_id"] != customer_b["tenant_id"]
            
        finally:
            # Cleanup
            await cleanup_test_data([
                customer_a["customer_id"],
                customer_b["customer_id"] if 'customer_b' in locals() else None
            ])
    
    @pytest.mark.business_critical
    @pytest.mark.asyncio 
    async def test_negative_billing_amounts_rejected(self, async_test_client):
        """
        CRITICAL: System must reject negative billing amounts
        (credits should use separate credit system)
        """
        tenant_id = str(uuid4())
        
        # Create customer and service
        customer_data = {
            "tenant_id": tenant_id,
            "customer_number": "NEG-BILL-001",
            "display_name": "Negative Billing Test",
            "email": "negbill@test.com"
        }
        
        customer_resp = await async_test_client.post(
            "/api/v1/customers/",
            json=customer_data,
            headers={"X-Tenant-ID": tenant_id}
        )
        customer = customer_resp.json()
        
        try:
            # Try to create billing record with negative amount
            negative_billing_data = {
                "customer_id": customer["customer_id"],
                "amount": "-50.00",  # Negative amount should be rejected
                "billing_period": "2024-01",
                "description": "Attempted negative billing"
            }
            
            negative_response = await async_test_client.post(
                "/api/v1/billing/records/",
                json=negative_billing_data,
                headers={"X-Tenant-ID": tenant_id}
            )
            
            assert negative_response.status_code == 400, \
                "Negative billing amounts should be rejected"
            
            error_data = negative_response.json()
            assert "negative" in error_data["detail"].lower() or \
                   "amount" in error_data["detail"].lower(), \
                "Error message should mention negative amount issue"
                
        finally:
            # Cleanup
            await cleanup_test_data([customer["customer_id"]])