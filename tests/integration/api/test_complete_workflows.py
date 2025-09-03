"""
Test complete API workflows for the DotMac ISP Framework.
End-to-end testing of business processes and user journeys.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from tests.utils.api_test_helpers import (
    MockAuthService,
    MockCustomerService,
    MockServicesService,
    assert_successful_response,
    assert_error_response
)


class TestCustomerOnboardingWorkflow:
    """Test complete customer onboarding workflow."""

    def test_complete_customer_onboarding_success(self, client, mock_customer_service, mock_services_service):
        """Test successful end-to-end customer onboarding."""
        with patch('dotmac_isp.modules.identity.router.CustomerService', return_value=mock_customer_service):
            with patch('dotmac_isp.modules.services.router.get_services_service', return_value=mock_services_service):
                with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                    with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                        mock_get_user.return_value = {"id": "admin-123", "tenant_id": "tenant-123"}
                        mock_perms.return_value = lambda: None
                        
                        headers = {"Authorization": "Bearer valid_token"}
                        
                        # Step 1: Create customer
                        customer_data = {
                            "email": "newcustomer@example.com",
                            "first_name": "New",
                            "last_name": "Customer",
                            "phone": "+1555123456",
                            "billing_address": {
                                "street": "123 New St",
                                "city": "New City",
                                "state": "CA",
                                "zip_code": "90210"
                            },
                            "create_user_account": True
                        }
                        
                        customer_response = client.post(
                            "/identity/customers",
                            json=customer_data,
                            headers=headers
                        )
                        
                        assert customer_response.status_code == 201
                        customer = customer_response.json()
                        customer_id = customer["id"]
                        
                        # Step 2: List available service plans
                        plans_response = client.get("/services/plans", headers=headers)
                        assert plans_response.status_code == 200
                        plans = plans_response.json()
                        assert len(plans) > 0
                        
                        selected_plan = plans[0]
                        plan_id = selected_plan["id"]
                        
                        # Step 3: Activate service for customer
                        activation_data = {
                            "customer_id": customer_id,
                            "service_plan_id": plan_id,
                            "installation_address": {
                                "street": "123 New St",
                                "city": "New City",
                                "state": "CA",
                                "zip_code": "90210"
                            },
                            "requested_activation_date": "2024-02-01T00:00:00Z",
                            "contact_phone": "+1555123456"
                        }
                        
                        activation_response = client.post(
                            "/services/activate",
                            json=activation_data,
                            headers=headers
                        )
                        
                        assert activation_response.status_code == 201
                        activation = activation_response.json()
                        service_id = activation["service_instance"]["id"]
                        
                        # Step 4: Verify customer has active service
                        customer_check = client.get(f"/identity/customers/{customer_id}", headers=headers)
                        assert customer_check.status_code == 200
                        
                        service_check = client.get(f"/services/instances/{service_id}", headers=headers)
                        assert service_check.status_code == 200

    def test_customer_onboarding_with_validation_errors(self, client):
        """Test customer onboarding with validation failures."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                mock_get_user.return_value = {"id": "admin-123"}
                mock_perms.return_value = lambda: None
                
                headers = {"Authorization": "Bearer valid_token"}
                
                # Invalid customer data
                invalid_customer_data = {
                    "email": "invalid-email",  # Invalid format
                    "first_name": "",          # Empty required field
                    # Missing last_name
                }
                
                response = client.post(
                    "/identity/customers",
                    json=invalid_customer_data,
                    headers=headers
                )
                
                assert response.status_code == 422
                error_details = response.json()["detail"]
                
                # Should have validation errors for email and required fields
                field_errors = [error["loc"][-1] for error in error_details]
                assert any("email" in str(error) for error in field_errors)

    def test_customer_onboarding_duplicate_email(self, client, mock_customer_service):
        """Test customer onboarding with duplicate email."""
        with patch('dotmac_isp.modules.identity.router.CustomerService', return_value=mock_customer_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    mock_get_user.return_value = {"id": "admin-123"}
                    mock_perms.return_value = lambda: None
                    
                    # Mock duplicate email error
                    mock_customer_service.create_customer.side_effect = Exception("Email already exists")
                    
                    headers = {"Authorization": "Bearer valid_token"}
                    customer_data = {
                        "email": "existing@example.com",
                        "first_name": "Test",
                        "last_name": "Customer"
                    }
                    
                    response = client.post(
                        "/identity/customers",
                        json=customer_data,
                        headers=headers
                    )
                    
                    assert response.status_code == 500  # Service error


class TestServiceManagementWorkflow:
    """Test service lifecycle management workflows."""

    def test_service_lifecycle_complete(self, client, mock_services_service):
        """Test complete service lifecycle from activation to cancellation."""
        with patch('dotmac_isp.modules.services.router.get_services_service', return_value=mock_services_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "admin-123", "user_id": "admin-123"}
                
                headers = {"Authorization": "Bearer valid_token"}
                
                # Step 1: Activate service
                activation_data = {
                    "customer_id": "customer-123",
                    "service_plan_id": "plan-123",
                    "installation_address": {
                        "street": "123 Test St",
                        "city": "Test City",
                        "state": "CA",
                        "zip_code": "90210"
                    }
                }
                
                activation_response = client.post(
                    "/services/activate",
                    json=activation_data,
                    headers=headers
                )
                
                assert activation_response.status_code == 201
                service_id = activation_response.json()["service_instance"]["id"]
                
                # Step 2: Update service status to active (simulate provisioning completion)
                status_update = {
                    "new_status": "active",
                    "reason": "Installation completed",
                    "effective_date": datetime.now(timezone.utc).isoformat() + "Z"
                }
                
                # Mock service instance for status updates
                active_service = {
                    "id": service_id,
                    "service_number": "SVC-001234",
                    "status": "active",
                    "customer_id": "customer-123"
                }
                mock_services_service.update_service_status.return_value = active_service
                mock_services_service.suspend_service.return_value = {**active_service, "status": "suspended"}
                mock_services_service.reactivate_service.return_value = {**active_service, "status": "active"}
                mock_services_service.cancel_service.return_value = {**active_service, "status": "cancelled"}
                
                status_response = client.patch(
                    f"/services/instances/{service_id}/status",
                    json=status_update,
                    headers=headers
                )
                
                assert status_response.status_code == 200
                assert status_response.json()["status"] == "active"
                
                # Step 3: Suspend service
                suspend_response = client.post(
                    f"/services/instances/{service_id}/suspend?reason=Maintenance",
                    headers=headers
                )
                
                assert suspend_response.status_code == 200
                assert suspend_response.json()["status"] == "suspended"
                
                # Step 4: Reactivate service
                reactivate_response = client.post(
                    f"/services/instances/{service_id}/reactivate?reason=Maintenance+complete",
                    headers=headers
                )
                
                assert reactivate_response.status_code == 200
                assert reactivate_response.json()["status"] == "active"
                
                # Step 5: Cancel service
                cancel_response = client.post(
                    f"/services/instances/{service_id}/cancel?reason=Customer+request",
                    headers=headers
                )
                
                assert cancel_response.status_code == 200
                assert cancel_response.json()["status"] == "cancelled"

    def test_bulk_service_operations_workflow(self, client, mock_services_service):
        """Test bulk service operations workflow."""
        with patch('dotmac_isp.modules.services.router.get_services_service', return_value=mock_services_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "admin-123", "user_id": "admin-123"}
                
                # Mock bulk operation responses
                def mock_suspend(service_id, reason, user_id):
                    service_numbers = {
                        "service-123": "SVC-001234",
                        "service-456": "SVC-001235",
                        "service-789": "SVC-001236"
                    }
                    return type('MockResponse', (), {
                        'service_number': service_numbers.get(str(service_id), "SVC-UNKNOWN")
                    })()
                
                mock_services_service.suspend_service.side_effect = mock_suspend
                
                headers = {"Authorization": "Bearer valid_token"}
                
                # Bulk suspend operation
                bulk_request = {
                    "service_instance_ids": ["service-123", "service-456", "service-789"],
                    "operation": "suspend",
                    "reason": "Scheduled maintenance"
                }
                
                response = client.post(
                    "/services/bulk-operation",
                    json=bulk_request,
                    headers=headers
                )
                
                assert response.status_code == 200
                result = response.json()
                
                assert result["total_requested"] == 3
                assert result["successful"] == 3
                assert result["failed"] == 0
                assert len(result["results"]) == 3
                
                # Verify all operations succeeded
                for service_result in result["results"]:
                    assert service_result["status"] == "success"

    def test_usage_data_recording_workflow(self, client, mock_services_service):
        """Test usage data recording and retrieval workflow."""
        with patch('dotmac_isp.modules.services.router.get_services_service', return_value=mock_services_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "admin-123"}
                
                headers = {"Authorization": "Bearer valid_token"}
                service_id = "service-123"
                
                # Mock usage recording and retrieval
                usage_record = {
                    "id": f"usage-{uuid4()}",
                    "service_id": service_id,
                    "usage_date": "2024-01-15",
                    "data_downloaded": 25000000000,
                    "data_uploaded": 5000000000
                }
                
                mock_services_service.record_service_usage.return_value = usage_record
                mock_services_service.get_service_usage.return_value = [usage_record]
                
                # Step 1: Record usage data
                usage_data = {
                    "usage_date": "2024-01-15",
                    "data_downloaded": 25000000000,
                    "data_uploaded": 5000000000,
                    "peak_download_speed": 950.5,
                    "peak_upload_speed": 95.2,
                    "uptime_percentage": 99.8
                }
                
                record_response = client.post(
                    f"/services/instances/{service_id}/usage",
                    json=usage_data,
                    headers=headers
                )
                
                assert record_response.status_code == 201
                recorded_usage = record_response.json()
                assert recorded_usage["data_downloaded"] == 25000000000
                
                # Step 2: Retrieve usage data
                usage_response = client.get(
                    f"/services/instances/{service_id}/usage?start_date=2024-01-15&end_date=2024-01-15",
                    headers=headers
                )
                
                assert usage_response.status_code == 200
                usage_list = usage_response.json()
                assert len(usage_list) == 1
                assert usage_list[0]["usage_date"] == "2024-01-15"


class TestAuthenticationWorkflow:
    """Test complete authentication workflows."""

    def test_login_logout_cycle(self, client, mock_auth_service):
        """Test complete login-logout cycle."""
        with patch('dotmac_isp.modules.identity.router.AuthService', return_value=mock_auth_service):
            # Step 1: Login
            login_data = {
                "username": "testuser",
                "password": "password",
                "portal_type": "admin"
            }
            
            login_response = client.post("/identity/auth/login", json=login_data)
            
            assert login_response.status_code == 200
            login_result = login_response.json()
            access_token = login_result["access_token"]
            
            assert "access_token" in login_result
            assert "user" in login_result
            assert login_result["user"]["username"] == "testuser"
            
            # Step 2: Use token to access protected endpoint
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    mock_get_user.return_value = {"id": "testuser", "username": "testuser"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": f"Bearer {access_token}"}
                    protected_response = client.get("/identity/users/testuser", headers=headers)
                    
                    assert protected_response.status_code == 200
            
            # Step 3: Logout
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "testuser", "username": "testuser"}
                
                headers = {"Authorization": f"Bearer {access_token}"}
                logout_response = client.post(
                    "/identity/auth/logout",
                    params={"session_id": "session-123"},
                    headers=headers
                )
                
                assert logout_response.status_code == 200
                assert logout_response.json()["success"] is True

    def test_failed_authentication_workflow(self, client, mock_auth_service):
        """Test failed authentication scenarios."""
        with patch('dotmac_isp.modules.identity.router.AuthService', return_value=mock_auth_service):
            # Invalid credentials
            invalid_login_data = {
                "username": "testuser",
                "password": "wrongpassword",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=invalid_login_data)
            
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

    def test_token_expiration_workflow(self, client):
        """Test token expiration and refresh workflow."""
        import jwt
        from datetime import datetime, timezone, timedelta
        
        # Create expired token
        expired_payload = {
            "sub": "testuser",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2)
        }
        
        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
        
        # Attempt to use expired token
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/identity/users/testuser", headers=headers)
        
        # Should be rejected
        assert response.status_code == 401


class TestMultiTenantWorkflows:
    """Test multi-tenant isolation workflows."""

    def test_tenant_isolation_workflow(self, client, mock_customer_service):
        """Test that tenant isolation is properly enforced."""
        with patch('dotmac_isp.modules.identity.router.CustomerService', return_value=mock_customer_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    mock_perms.return_value = lambda: None
                    
                    # User from tenant A
                    mock_get_user.return_value = {
                        "id": "user-123",
                        "tenant_id": "tenant-a"
                    }
                    
                    # Attempt to access tenant B's resources
                    headers = {
                        "Authorization": "Bearer valid_token",
                        "X-Tenant-ID": "tenant-b"  # Different tenant
                    }
                    
                    # Mock service to enforce tenant isolation
                    mock_customer_service.get_customer_by_id.return_value = None  # Not found due to isolation
                    
                    response = client.get("/identity/customers/customer-from-tenant-b", headers=headers)
                    
                    # Should not find customer from different tenant
                    assert response.status_code == 404

    def test_cross_tenant_data_access_prevention(self, client):
        """Test prevention of cross-tenant data access."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                mock_perms.return_value = lambda: None
                
                # Create tokens for different tenants
                import jwt
                from datetime import datetime, timezone, timedelta
                
                tenant_a_payload = {
                    "sub": "user-a",
                    "username": "usera",
                    "tenant_id": "tenant-a",
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1)
                }
                
                tenant_b_payload = {
                    "sub": "user-b",
                    "username": "userb", 
                    "tenant_id": "tenant-b",
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1)
                }
                
                token_a = jwt.encode(tenant_a_payload, "test-secret", algorithm="HS256")
                token_b = jwt.encode(tenant_b_payload, "test-secret", algorithm="HS256")
                
                # User A tries to access with User B's token
                mock_get_user.return_value = {"id": "user-a", "tenant_id": "tenant-a"}
                
                headers = {
                    "Authorization": f"Bearer {token_b}",  # Wrong token
                    "X-Tenant-ID": "tenant-a"
                }
                
                response = client.get("/identity/customers", headers=headers)
                
                # Should handle token/tenant mismatch appropriately
                assert response.status_code in [401, 403]


class TestErrorRecoveryWorkflows:
    """Test error recovery and rollback workflows."""

    def test_service_activation_rollback(self, client, mock_services_service):
        """Test service activation rollback on failure."""
        with patch('dotmac_isp.modules.services.router.get_services_service', return_value=mock_services_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "admin-123"}
                
                # Mock activation failure
                mock_services_service.activate_service.side_effect = Exception("Provisioning system unavailable")
                
                headers = {"Authorization": "Bearer valid_token"}
                activation_data = {
                    "customer_id": "customer-123",
                    "service_plan_id": "plan-123",
                    "installation_address": {
                        "street": "123 Test St",
                        "city": "Test City",
                        "state": "CA",
                        "zip_code": "90210"
                    }
                }
                
                response = client.post(
                    "/services/activate",
                    json=activation_data,
                    headers=headers
                )
                
                # Should handle failure gracefully
                assert response.status_code == 500

    def test_partial_bulk_operation_handling(self, client, mock_services_service):
        """Test handling of partial failures in bulk operations."""
        with patch('dotmac_isp.modules.services.router.get_services_service', return_value=mock_services_service):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "admin-123", "user_id": "admin-123"}
                
                # Mock partial failure
                def mock_suspend(service_id, reason, user_id):
                    if str(service_id) == "service-123":
                        return type('MockResponse', (), {'service_number': 'SVC-001234'})()
                    else:
                        raise Exception("Service not found")
                
                mock_services_service.suspend_service.side_effect = mock_suspend
                
                headers = {"Authorization": "Bearer valid_token"}
                bulk_request = {
                    "service_instance_ids": ["service-123", "service-456"],
                    "operation": "suspend",
                    "reason": "Test partial failure"
                }
                
                response = client.post(
                    "/services/bulk-operation",
                    json=bulk_request,
                    headers=headers
                )
                
                assert response.status_code == 200
                result = response.json()
                
                # Should handle partial success
                assert result["successful"] == 1
                assert result["failed"] == 1
                assert result["total_requested"] == 2