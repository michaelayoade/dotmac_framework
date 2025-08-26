"""Comprehensive business logic tests for Portal ID System.

Tests cover:
- Portal ID generation and uniqueness
- Authentication workflows
- Password security and validation
- Account lockout mechanisms
- Multi-tenant isolation
- Portal management operations
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.portal_id
@pytest.mark.unit
class TestPortalIDGeneration:
    """Test Portal ID generation algorithms and uniqueness."""
    
    @pytest.mark.asyncio
    async def test_portal_id_generation_format(self, db_session: AsyncSession):
        """Test that Portal IDs are generated in correct format."""
        # Portal ID format should be: {PREFIX}_{TYPE}_{SEQUENCE}
        # Example: ADMIN_PORTAL_001, CUST_PORTAL_001, etc.
        
        from dotmac_isp.modules.portal_management.services import PortalIDService
        
        service = PortalIDService(db_session)
        
        # Test admin portal ID generation
        admin_portal_id = await service.generate_portal_id("admin")
        assert admin_portal_id.startswith("ADMIN_PORTAL_")
        assert len(admin_portal_id.split("_") == 3
        assert admin_portal_id.split("_")[2].isdigit()
        
        # Test customer portal ID generation
        customer_portal_id = await service.generate_portal_id("customer")
        assert customer_portal_id.startswith("CUST_PORTAL_")
        
        # Test reseller portal ID generation
        reseller_portal_id = await service.generate_portal_id("reseller")
        assert reseller_portal_id.startswith("RESELLER_PORTAL_")
    
    @pytest.mark.asyncio
    async def test_portal_id_uniqueness(self, db_session: AsyncSession):
        """Test that Portal IDs are unique across the system."""
        from dotmac_isp.modules.portal_management.services import PortalIDService
        
        service = PortalIDService(db_session)
        
        # Generate multiple Portal IDs
        portal_ids = set()
        for _ in range(100):
            portal_id = await service.generate_portal_id("customer")
            assert portal_id not in portal_ids, f"Duplicate Portal ID generated: {portal_id}"
            portal_ids.add(portal_id)
    
    @pytest.mark.asyncio
    async def test_portal_id_tenant_isolation(self, db_session: AsyncSession):
        """Test that Portal IDs respect tenant isolation."""
        from dotmac_isp.modules.portal_management.services import PortalIDService
        
        service = PortalIDService(db_session)
        
        # Generate Portal IDs for different tenants
        tenant1_portal = await service.generate_portal_id("customer", tenant_id="tenant_001")
        tenant2_portal = await service.generate_portal_id("customer", tenant_id="tenant_002")
        
        # Portal IDs should be different even for same type
        assert tenant1_portal != tenant2_portal
        
        # Verify tenant information is embedded or tracked
        portal1_info = await service.get_portal_info(tenant1_portal)
        portal2_info = await service.get_portal_info(tenant2_portal)
        
        assert portal1_info["tenant_id"] == "tenant_001"
        assert portal2_info["tenant_id"] == "tenant_002"


@pytest.mark.portal_id
@pytest.mark.integration
class TestAuthenticationWorkflows:
    """Test complete authentication workflows for Portal ID system."""
    
    @pytest.mark.asyncio
    async def test_customer_portal_login_workflow(self, async_client, sample_customer_data):
        """Test complete customer portal login workflow."""
        
        # 1. Customer registration
        registration_data = {
            **sample_customer_data,
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == 201
        
        registration_result = response.json()
        assert "portal_id" in registration_result
        assert registration_result["portal_id"].startswith("CUST_PORTAL_")
        
        # 2. Email verification (mocked)
        portal_id = registration_result["portal_id"]
        verify_response = await async_client.post(
            f"/api/v1/auth/verify-email",
            json={"portal_id": portal_id, "verification_code": "123456"}
        )
        assert verify_response.status_code == 200
        
        # 3. Login with Portal ID
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "portal_id": portal_id,
                "password": "SecurePass123!"
            }
        )
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "refresh_token" in login_result
        assert login_result["user"]["portal_id"] == portal_id
    
    @pytest.mark.asyncio
    async def test_admin_portal_authentication(self, async_client, admin_user_data):
        """Test admin portal authentication with enhanced security."""
        
        # Admin login should require additional security measures
        login_response = await async_client.post(
            "/api/v1/auth/admin/login",
            json={
                "portal_id": admin_user_data["portal_id"],
                "password": "AdminPass123!",
                "mfa_code": "123456"  # Multi-factor authentication
            }
        )
        
        assert login_response.status_code == 200
        result = login_response.json()
        
        # Admin tokens should have shorter expiration
        assert result["token_type"] == "bearer"
        assert result["expires_in"] < 3600  # Less than 1 hour
        
        # Verify admin privileges
        auth_headers = {"Authorization": f"Bearer {result['access_token']}"}
        profile_response = await async_client.get(
            "/api/v1/auth/profile", 
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["role"] == "admin"
        assert profile["is_superuser"] == True
    
    @pytest.mark.asyncio
    async def test_reseller_portal_authentication(self, async_client, reseller_user_data):
        """Test reseller portal authentication with commission tracking."""
        
        login_response = await async_client.post(
            "/api/v1/auth/reseller/login",
            json={
                "portal_id": reseller_user_data["portal_id"], 
                "password": "ResellerPass123!"
            }
        )
        
        assert login_response.status_code == 200
        result = login_response.json()
        
        # Verify reseller-specific features in token
        auth_headers = {"Authorization": f"Bearer {result['access_token']}"}
        
        # Should have access to reseller dashboard
        dashboard_response = await async_client.get(
            "/api/v1/reseller/dashboard",
            headers=auth_headers
        )
        assert dashboard_response.status_code == 200
        
        # Should have commission tracking
        commission_response = await async_client.get(
            "/api/v1/reseller/commissions",
            headers=auth_headers
        )
        assert commission_response.status_code == 200


@pytest.mark.portal_id 
@pytest.mark.security
class TestPasswordSecurity:
    """Test password security and validation requirements."""
    
    @pytest.mark.asyncio
    async def test_password_complexity_requirements(self, async_client):
        """Test password complexity validation."""
        
        weak_passwords = [
            "123456",           # Too simple
            "password",         # Dictionary word
            "abc123",          # Too short
            "ALLUPPERCASE",    # No lowercase
            "alllowercase",    # No uppercase
            "NoNumbers!",      # No numbers
            "NoSpecial123",    # No special characters
        ]
        
        for weak_password in weak_passwords:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email_primary": "test@example.com",
                    "password": weak_password,
                    "confirm_password": weak_password,
                    "first_name": "Test",
                    "last_name": "User",
                }
            )
            
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            assert any("password" in str(error).lower() for error in error_detail)
    
    @pytest.mark.asyncio
    async def test_password_strength_validation(self, async_client):
        """Test strong password acceptance."""
        
        strong_passwords = [
            "StrongPass123!",
            "MySecure#Pass789",
            "Complex$Password2024",
        ]
        
        for strong_password in strong_passwords:
            response = await async_client.post(
                "/api/v1/auth/validate-password",
                json={"password": strong_password}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["is_valid"] == True
            assert result["strength_score"] >= 3  # Strong password score
    
    @pytest.mark.asyncio 
    async def test_password_history_prevention(self, async_client, sample_customer_data):
        """Test that users cannot reuse recent passwords."""
        
        # Create user account
        registration_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **sample_customer_data,
                "password": "OldPassword123!",
                "confirm_password": "OldPassword123!",
            }
        )
        
        assert registration_response.status_code == 201
        portal_id = registration_response.json()["portal_id"]
        
        # Login to get auth token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"portal_id": portal_id, "password": "OldPassword123!"}
        )
        
        auth_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # Try to change to new password
        change_response = await async_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewPassword123!",
            },
            headers=auth_headers
        )
        assert change_response.status_code == 200
        
        # Try to change back to old password (should fail)
        revert_response = await async_client.post(
            "/api/v1/auth/change-password", 
            json={
                "current_password": "NewPassword123!",
                "new_password": "OldPassword123!",  # Previously used
            },
            headers=auth_headers
        )
        
        assert revert_response.status_code == 422
        error = revert_response.json()
        assert "password history" in str(error).lower()


@pytest.mark.portal_id
@pytest.mark.security  
class TestAccountLockoutMechanisms:
    """Test account security and lockout mechanisms."""
    
    @pytest.mark.asyncio
    async def test_failed_login_attempt_tracking(self, async_client, sample_customer_data):
        """Test tracking and limiting failed login attempts."""
        
        # Create user account
        registration_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **sample_customer_data,
                "password": "CorrectPass123!",
                "confirm_password": "CorrectPass123!",
            }
        )
        
        portal_id = registration_response.json()["portal_id"]
        
        # Attempt multiple failed logins
        max_attempts = 5
        for attempt in range(max_attempts):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "portal_id": portal_id,
                    "password": "WrongPassword123!"
                }
            )
            
            if attempt < max_attempts - 1:
                assert response.status_code == 401
                result = response.json()
                assert "attempts_remaining" in result
                assert result["attempts_remaining"] == max_attempts - attempt - 1
            else:
                # Final attempt should lock account
                assert response.status_code == 423  # Locked
                result = response.json()
                assert "account locked" in result["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_account_lockout_duration(self, async_client, sample_customer_data):
        """Test account lockout duration and automatic unlock."""
        
        # Create and lock account (similar to above test)
        registration_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **sample_customer_data,
                "password": "CorrectPass123!",
                "confirm_password": "CorrectPass123!",
            }
        )
        
        portal_id = registration_response.json()["portal_id"]
        
        # Lock the account with failed attempts
        for _ in range(5):
            await async_client.post(
                "/api/v1/auth/login",
                json={"portal_id": portal_id, "password": "Wrong!"}
            )
        
        # Verify account is locked
        locked_response = await async_client.post(
            "/api/v1/auth/login",
            json={"portal_id": portal_id, "password": "CorrectPass123!"}
        )
        assert locked_response.status_code == 423
        
        # Check lockout status
        status_response = await async_client.get(
            f"/api/v1/auth/lockout-status/{portal_id}"
        )
        assert status_response.status_code == 200
        
        status = status_response.json()
        assert status["is_locked"] == True
        assert "unlock_time" in status
        assert status["failed_attempts"] == 5
    
    @pytest.mark.asyncio
    async def test_manual_account_unlock(self, async_client, admin_user_data, sample_customer_data):
        """Test admin manual account unlock functionality."""
        
        # Create and lock customer account
        registration_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                **sample_customer_data,
                "password": "CorrectPass123!",
                "confirm_password": "CorrectPass123!",
            }
        )
        
        portal_id = registration_response.json()["portal_id"]
        
        # Lock account
        for _ in range(5):
            await async_client.post(
                "/api/v1/auth/login",
                json={"portal_id": portal_id, "password": "Wrong!"}
            )
        
        # Admin login
        admin_login = await async_client.post(
            "/api/v1/auth/admin/login",
            json={
                "portal_id": admin_user_data["portal_id"],
                "password": "AdminPass123!",
                "mfa_code": "123456"
            }
        )
        
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        # Admin unlocks customer account
        unlock_response = await async_client.post(
            f"/api/v1/admin/accounts/{portal_id}/unlock",
            headers=admin_headers
        )
        assert unlock_response.status_code == 200
        
        # Verify account is unlocked
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"portal_id": portal_id, "password": "CorrectPass123!"}
        )
        assert login_response.status_code == 200


@pytest.mark.portal_id
@pytest.mark.tenant_isolation 
class TestMultiTenantIsolation:
    """Test multi-tenant isolation for Portal ID system."""
    
    @pytest.mark.asyncio
    async def test_cross_tenant_portal_access_prevention(self, async_client, tenant_data):
        """Test that users cannot access portals from other tenants."""
        
        # Create users in different tenants
        tenant1_user = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email_primary": "user1@tenant1.com",
                "password": "Pass123!",
                "confirm_password": "Pass123!",
                "first_name": "User",
                "last_name": "One",
                "tenant_id": "tenant_001",
            }
        )
        
        tenant2_user = await async_client.post(
            "/api/v1/auth/register", 
            json={
                "email_primary": "user2@tenant2.com",
                "password": "Pass123!",
                "confirm_password": "Pass123!",
                "first_name": "User",
                "last_name": "Two",
                "tenant_id": "tenant_002",
            }
        )
        
        tenant1_portal = tenant1_user.json()["portal_id"]
        tenant2_portal = tenant2_user.json()["portal_id"]
        
        # Login as tenant 1 user
        login1 = await async_client.post(
            "/api/v1/auth/login",
            json={"portal_id": tenant1_portal, "password": "Pass123!"}
        )
        
        tenant1_headers = {"Authorization": f"Bearer {login1.json()['access_token']}"}
        
        # Try to access tenant 2 user's data (should fail)
        access_response = await async_client.get(
            f"/api/v1/users/{tenant2_portal}/profile",
            headers=tenant1_headers
        )
        
        assert access_response.status_code == 403  # Forbidden
        
        # Verify cannot access tenant 2 resources
        tenant2_customers = await async_client.get(
            "/api/v1/customers",
            headers=tenant1_headers,
            params={"tenant_id": "tenant_002"}
        )
        
        assert tenant2_customers.status_code in [403, 404]  # No access to other tenant data
    
    @pytest.mark.asyncio
    async def test_tenant_data_isolation_in_database(self, db_session, tenant_data):
        """Test that database queries respect tenant isolation."""
        
        from dotmac_isp.modules.portal_management.services import PortalService
        
        service = PortalService(db_session)
        
        # Create portals for different tenants
        portal1 = await service.create_portal({
            "portal_type": "customer",
            "tenant_id": "tenant_001",
            "user_data": {"email": "user1@tenant1.com"}
        })
        
        portal2 = await service.create_portal({
            "portal_type": "customer", 
            "tenant_id": "tenant_002",
            "user_data": {"email": "user2@tenant2.com"}
        })
        
        # Query portals with tenant isolation
        tenant1_portals = await service.list_portals(tenant_id="tenant_001")
        tenant2_portals = await service.list_portals(tenant_id="tenant_002")
        
        # Verify isolation
        assert len(tenant1_portals) == 1
        assert len(tenant2_portals) == 1
        assert tenant1_portals[0]["portal_id"] != tenant2_portals[0]["portal_id"]
        
        # Verify cross-tenant queries return no results
        cross_tenant_query = await service.get_portal_by_id(
            portal1["portal_id"], 
            tenant_id="tenant_002"  # Wrong tenant
        )
        assert cross_tenant_query is None


@pytest.mark.portal_id
@pytest.mark.integration
class TestPortalManagementOperations:
    """Test portal management CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_portal_creation_workflow(self, async_client, admin_user_data):
        """Test complete portal creation workflow."""
        
        # Admin login
        admin_login = await async_client.post(
            "/api/v1/auth/admin/login",
            json={
                "portal_id": admin_user_data["portal_id"],
                "password": "AdminPass123!",
                "mfa_code": "123456"
            }
        )
        
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        # Create new customer portal
        portal_data = {
            "portal_type": "customer",
            "customer_data": {
                "first_name": "New",
                "last_name": "Customer",
                "email_primary": "newcust@example.com",
                "phone_primary": "555-0123",
            },
            "services": [
                {
                    "service_type": "internet",
                    "plan": "basic_100",
                    "monthly_rate": 59.99,
                }
            ],
            "billing_info": {
                "billing_method": "credit_card",
                "auto_pay": True,
            }
        }
        
        creation_response = await async_client.post(
            "/api/v1/admin/portals",
            json=portal_data,
            headers=admin_headers
        )
        
        assert creation_response.status_code == 201
        result = creation_response.json()
        
        # Verify portal creation
        assert "portal_id" in result
        assert result["portal_type"] == "customer" 
        assert result["status"] == "pending_activation"
        
        # Verify customer account creation
        portal_id = result["portal_id"]
        customer_response = await async_client.get(
            f"/api/v1/admin/portals/{portal_id}/customer",
            headers=admin_headers
        )
        
        assert customer_response.status_code == 200
        customer = customer_response.json()
        assert customer["email_primary"] == "newcust@example.com"
        
        # Verify service provisioning initiated
        services_response = await async_client.get(
            f"/api/v1/admin/portals/{portal_id}/services",
            headers=admin_headers
        )
        
        assert services_response.status_code == 200
        services = services_response.json()
        assert len(services) == 1
        assert services[0]["service_type"] == "internet"
    
    @pytest.mark.asyncio
    async def test_portal_status_management(self, async_client, admin_user_data):
        """Test portal status transitions and management."""
        
        # Setup admin authentication
        admin_login = await async_client.post(
            "/api/v1/auth/admin/login", 
            json={
                "portal_id": admin_user_data["portal_id"],
                "password": "AdminPass123!",
                "mfa_code": "123456"
            }
        )
        
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        # Create test portal
        portal_response = await async_client.post(
            "/api/v1/admin/portals",
            json={
                "portal_type": "customer",
                "customer_data": {
                    "first_name": "Test",
                    "last_name": "User",
                    "email_primary": "testuser@example.com",
                }
            },
            headers=admin_headers
        )
        
        portal_id = portal_response.json()["portal_id"]
        
        # Test status transitions
        status_transitions = [
            ("pending_activation", "active"),
            ("active", "suspended"),
            ("suspended", "active"),
            ("active", "cancelled"),
        ]
        
        for from_status, to_status in status_transitions:
            status_response = await async_client.patch(
                f"/api/v1/admin/portals/{portal_id}/status",
                json={
                    "status": to_status,
                    "reason": f"Testing transition from {from_status} to {to_status}",
                    "notes": "Automated test status change"
                },
                headers=admin_headers
            )
            
            assert status_response.status_code == 200
            result = status_response.json()
            assert result["status"] == to_status
            
            # Verify status change was logged
            history_response = await async_client.get(
                f"/api/v1/admin/portals/{portal_id}/status-history",
                headers=admin_headers
            )
            
            assert history_response.status_code == 200
            history = history_response.json()
            assert len(history) > 0
            assert history[0]["to_status"] == to_status
    
    @pytest.mark.asyncio
    async def test_bulk_portal_operations(self, async_client, admin_user_data):
        """Test bulk portal management operations."""
        
        # Setup admin authentication
        admin_login = await async_client.post(
            "/api/v1/auth/admin/login",
            json={
                "portal_id": admin_user_data["portal_id"],
                "password": "AdminPass123!",
                "mfa_code": "123456"
            }
        )
        
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        # Create multiple portals for bulk operations
        portal_ids = []
        for i in range(5):
            portal_response = await async_client.post(
                "/api/v1/admin/portals",
                json={
                    "portal_type": "customer",
                    "customer_data": {
                        "first_name": f"Bulk{i}",
                        "last_name": "User",
                        "email_primary": f"bulk{i}@example.com",
                    }
                },
                headers=admin_headers
            )
            portal_ids.append(portal_response.json()["portal_id"])
        
        # Test bulk status update
        bulk_update_response = await async_client.post(
            "/api/v1/admin/portals/bulk-update",
            json={
                "portal_ids": portal_ids,
                "updates": {
                    "status": "active",
                    "notes": "Bulk activation for testing"
                }
            },
            headers=admin_headers
        )
        
        assert bulk_update_response.status_code == 200
        results = bulk_update_response.json()
        assert results["updated_count"] == 5
        assert results["failed_count"] == 0
        
        # Verify all portals were updated
        for portal_id in portal_ids:
            portal_response = await async_client.get(
                f"/api/v1/admin/portals/{portal_id}",
                headers=admin_headers
            )
            assert portal_response.json()["status"] == "active"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])