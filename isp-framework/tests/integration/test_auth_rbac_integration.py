"""
Integration tests for Authentication and RBAC system integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from dotmac_isp.sdks.platform.authentication_sdk import AuthenticationSDK
from dotmac_isp.sdks.platform.rbac_sdk import RBACSDK, RBACSDKConfig
from dotmac_isp.sdks.contracts.auth import AuthRequest, AuthResponse
from dotmac_isp.sdks.contracts.rbac import (
    PermissionCheckRequest,
    RoleAssignmentRequest,
    UserRolesResponse,
    UserRole
)


class TestAuthRBACIntegration:
    """Test Authentication and RBAC integration"""

    @pytest.fixture
    def auth_sdk(self):
        """Create authentication SDK instance"""
        return AuthenticationSDK()

    @pytest.fixture
    def rbac_sdk(self):
        """Create RBAC SDK instance"""
        config = RBACSDKConfig(
            cache_ttl=300,
            enable_caching=False,  # Disable for testing
            enable_audit_logging=True
        )
        return RBACSDK(config=config)

    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = Mock()
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.username = "testuser"
        user.is_active = True
        user.roles = []
        return user

    @pytest.mark.asyncio
    async def test_authentication_assigns_default_role(self, auth_sdk, rbac_sdk, mock_user):
        """Test that authentication assigns default role if none exists"""
        
        # Mock the identity SDK to return our test user
        with patch.object(auth_sdk, '_validate_credentials', return_value=mock_user), \
             patch.object(auth_sdk, '_create_tokens') as mock_create_tokens, \
             patch.object(auth_sdk, '_create_session', return_value=None):
            
            # Mock token creation
            mock_access_token = Mock()
            mock_access_token.token = "access_token_123"
            mock_access_token.expires_in_seconds = 3600
            
            mock_refresh_token = Mock()
            mock_refresh_token.token = "refresh_token_123"
            mock_refresh_token.expires_at = None
            
            mock_create_tokens.return_value = (mock_access_token, mock_refresh_token)
            
            # Create auth request
            auth_request = AuthRequest(
                portal_id="test-portal",
                credential_id="testuser",
                credential_secret="password123",
                grant_type="password",
                tenant_id="test-tenant"
            )
            
            # Authenticate user
            response = await auth_sdk.authenticate(auth_request)
            
            # Verify response
            assert response.success is True
            assert response.user_id == "test-user-123"
            assert "user" in response.roles or len(response.roles) > 0
            assert len(response.permissions) > 0

    @pytest.mark.asyncio
    async def test_rbac_permission_checking(self, rbac_sdk):
        """Test RBAC permission checking functionality"""
        
        # Assign role to user
        role_request = RoleAssignmentRequest(
            user_id="test-user-123",
            role_name="admin",
            conditions={"tenant_id": "test-tenant"}
        )
        
        assignment_response = await rbac_sdk.assign_role(role_request)
        assert assignment_response.success is True
        
        # Check permission
        perm_request = PermissionCheckRequest(
            user_id="test-user-123",
            permission="users.read",
            context={"tenant_id": "test-tenant"}
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is True
        assert "admin" in perm_response.matched_roles

    @pytest.mark.asyncio
    async def test_role_hierarchy_inheritance(self, rbac_sdk):
        """Test role hierarchy and permission inheritance"""
        
        # Assign manager role (which should inherit from user role)
        role_request = RoleAssignmentRequest(
            user_id="test-user-456",
            role_name="manager"
        )
        
        assignment_response = await rbac_sdk.assign_role(role_request)
        assert assignment_response.success is True
        
        # Check inherited permission from user role
        perm_request = PermissionCheckRequest(
            user_id="test-user-456",
            permission="profile.read"
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is True
        
        # Check manager-specific permission
        perm_request = PermissionCheckRequest(
            user_id="test-user-456",
            permission="users.write"
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is True

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, rbac_sdk):
        """Test tenant isolation in RBAC"""
        
        # Assign role with tenant A
        role_request = RoleAssignmentRequest(
            user_id="test-user-789",
            role_name="tenant_admin",
            conditions={"tenant_id": "tenant-a"}
        )
        
        assignment_response = await rbac_sdk.assign_role(role_request)
        assert assignment_response.success is True
        
        # Check permission in tenant A (should be allowed)
        perm_request = PermissionCheckRequest(
            user_id="test-user-789",
            permission="users.write",
            context={"tenant_id": "tenant-a"}
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is True
        
        # Check permission in tenant B (should be denied due to tenant isolation)
        perm_request = PermissionCheckRequest(
            user_id="test-user-789",
            permission="users.write",
            context={"tenant_id": "tenant-b"}
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        # This should be denied due to tenant isolation policy
        assert perm_response.allowed is False

    @pytest.mark.asyncio
    async def test_permission_caching(self, rbac_sdk):
        """Test permission caching functionality"""
        
        # Enable caching for this test
        rbac_sdk.config.enable_caching = True
        rbac_sdk.cache_sdk = Mock()
        rbac_sdk.cache_sdk.get = AsyncMock(return_value=None)
        rbac_sdk.cache_sdk.set = AsyncMock()
        rbac_sdk.cache_sdk.delete = AsyncMock()
        
        # Assign role
        role_request = RoleAssignmentRequest(
            user_id="cache-test-user",
            role_name="user"
        )
        
        await rbac_sdk.assign_role(role_request)
        
        # First permission check (should miss cache)
        perm_request = PermissionCheckRequest(
            user_id="cache-test-user",
            permission="profile.read"
        )
        
        response1 = await rbac_sdk.check_permission(perm_request)
        assert response1.allowed is True
        
        # Verify cache was called
        rbac_sdk.cache_sdk.get.assert_called()
        rbac_sdk.cache_sdk.set.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_permission_checking(self, rbac_sdk):
        """Test bulk permission checking"""
        
        # Assign role
        role_request = RoleAssignmentRequest(
            user_id="bulk-test-user",
            role_name="manager"
        )
        
        await rbac_sdk.assign_role(role_request)
        
        # Check multiple permissions at once
        from dotmac_isp.sdks.contracts.rbac import BulkPermissionCheckRequest
        
        bulk_request = BulkPermissionCheckRequest(
            user_id="bulk-test-user",
            permissions=[
                "profile.read",
                "users.read", 
                "users.write",
                "system.admin"  # Should be denied
            ]
        )
        
        bulk_response = await rbac_sdk.check_permissions_bulk(bulk_request)
        
        # Verify results
        assert bulk_response.allowed_count == 3  # All except system.admin
        assert bulk_response.total_count == 4
        assert bulk_response.results["profile.read"] is True
        assert bulk_response.results["users.read"] is True
        assert bulk_response.results["users.write"] is True
        assert bulk_response.results["system.admin"] is False

    @pytest.mark.asyncio
    async def test_rbac_error_handling(self, rbac_sdk):
        """Test RBAC error handling and fallbacks"""
        
        # Test permission check for non-existent user
        perm_request = PermissionCheckRequest(
            user_id="non-existent-user",
            permission="users.read"
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is False
        assert "no role assignments" in perm_response.denial_reason.lower() or \
               "insufficient permissions" in perm_response.denial_reason.lower()

    @pytest.mark.asyncio
    async def test_role_revocation(self, rbac_sdk):
        """Test role revocation functionality"""
        
        # Assign role
        role_request = RoleAssignmentRequest(
            user_id="revoke-test-user",
            role_name="admin"
        )
        
        assignment_response = await rbac_sdk.assign_role(role_request)
        assert assignment_response.success is True
        
        # Verify permission exists
        perm_request = PermissionCheckRequest(
            user_id="revoke-test-user",
            permission="system.admin"
        )
        
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is True
        
        # Revoke role
        revoke_response = await rbac_sdk.revoke_role(
            "revoke-test-user", 
            "admin"
        )
        assert revoke_response.success is True
        
        # Verify permission is now denied
        perm_response = await rbac_sdk.check_permission(perm_request)
        assert perm_response.allowed is False

    @pytest.mark.asyncio
    async def test_rbac_health_check(self, rbac_sdk):
        """Test RBAC system health check"""
        
        health_status = await rbac_sdk.health_check()
        
        assert health_status["status"] == "healthy"
        assert "response_time_ms" in health_status
        assert health_status["roles_count"] > 0
        assert health_status["permissions_count"] > 0
        assert "cache_enabled" in health_status
        assert "audit_enabled" in health_status

    def test_rbac_statistics(self, rbac_sdk):
        """Test RBAC performance statistics"""
        
        # Get initial stats
        stats = rbac_sdk.get_stats()
        
        assert "permission_checks" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "role_assignments" in stats
        assert "permission_denials" in stats
        assert "total_roles" in stats
        assert "total_permissions" in stats
        assert "cache_hit_rate" in stats