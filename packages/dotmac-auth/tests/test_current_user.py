"""
Tests for Current User Dependencies

Tests for FastAPI dependencies and user claim models.
"""

import pytest
from unittest.mock import Mock
from fastapi import HTTPException

from dotmac.auth import (
    UserClaims,
    ServiceClaims,
    get_current_user,
    get_current_service,
    get_optional_user,
    require_scopes,
    require_roles,
    require_admin,
    require_tenant_access,
    require_service_operation,
)


class TestUserClaims:
    """Test UserClaims model"""
    
    def test_user_claims_creation(self):
        """Test creating UserClaims from JWT claims"""
        claims_data = {
            "sub": "user123",
            "tenant_id": "tenant1", 
            "scopes": ["read", "write"],
            "roles": ["user", "moderator"],
            "email": "user@example.com",
            "username": "testuser",
            "iat": 1234567890,
            "exp": 1234571490,
            "jti": "token123"
        }
        
        user = UserClaims(**claims_data)
        
        assert user.user_id == "user123"
        assert user.tenant_id == "tenant1"
        assert user.scopes == ["read", "write"]
        assert user.roles == ["user", "moderator"]
        assert user.email == "user@example.com"
        assert user.username == "testuser"
        assert user.issued_at == 1234567890
        assert user.expires_at == 1234571490
        assert user.token_id == "token123"
        assert user.authenticated is True
    
    def test_user_claims_with_aliases(self):
        """Test UserClaims with JWT field aliases"""
        claims_data = {
            "sub": "user123",
            "iss": "auth-service",
            "aud": "api-service"
        }
        
        user = UserClaims(**claims_data)
        
        assert user.user_id == "user123"
        assert user.issuer == "auth-service"
        assert user.audience == "api-service"
    
    def test_is_authenticated(self):
        """Test authentication status checking"""
        # Authenticated user
        user = UserClaims(sub="user123", authenticated=True)
        assert user.is_authenticated is True
        
        # Unauthenticated user
        user = UserClaims(sub="user123", authenticated=False)
        assert user.is_authenticated is False
        
        # User with no ID (shouldn't happen but test edge case)
        user = UserClaims(sub="", authenticated=True)
        assert user.is_authenticated is False
    
    def test_has_scope(self):
        """Test scope checking"""
        user = UserClaims(sub="user123", scopes=["read", "write"])
        
        assert user.has_scope("read") is True
        assert user.has_scope("write") is True
        assert user.has_scope("delete") is False
    
    def test_has_any_scope(self):
        """Test any scope checking"""
        user = UserClaims(sub="user123", scopes=["read", "write"])
        
        assert user.has_any_scope(["read"]) is True
        assert user.has_any_scope(["read", "admin"]) is True
        assert user.has_any_scope(["admin", "delete"]) is False
        assert user.has_any_scope([]) is False
    
    def test_has_all_scopes(self):
        """Test all scopes checking"""
        user = UserClaims(sub="user123", scopes=["read", "write", "delete"])
        
        assert user.has_all_scopes(["read"]) is True
        assert user.has_all_scopes(["read", "write"]) is True
        assert user.has_all_scopes(["read", "write", "delete"]) is True
        assert user.has_all_scopes(["read", "admin"]) is False
        assert user.has_all_scopes([]) is True
    
    def test_has_role(self):
        """Test role checking"""
        user = UserClaims(sub="user123", roles=["user", "moderator"])
        
        assert user.has_role("user") is True
        assert user.has_role("moderator") is True
        assert user.has_role("admin") is False
    
    def test_has_any_role(self):
        """Test any role checking"""
        user = UserClaims(sub="user123", roles=["user", "moderator"])
        
        assert user.has_any_role(["user"]) is True
        assert user.has_any_role(["user", "admin"]) is True
        assert user.has_any_role(["admin", "super_admin"]) is False
        assert user.has_any_role([]) is False
    
    def test_has_all_roles(self):
        """Test all roles checking"""
        user = UserClaims(sub="user123", roles=["user", "moderator", "reviewer"])
        
        assert user.has_all_roles(["user"]) is True
        assert user.has_all_roles(["user", "moderator"]) is True
        assert user.has_all_roles(["user", "moderator", "reviewer"]) is True
        assert user.has_all_roles(["user", "admin"]) is False
        assert user.has_all_roles([]) is True
    
    def test_is_admin(self):
        """Test admin privilege checking"""
        # Admin role
        user = UserClaims(sub="user123", roles=["admin"])
        assert user.is_admin() is True
        
        # Super admin role
        user = UserClaims(sub="user123", roles=["super_admin"])
        assert user.is_admin() is True
        
        # Admin scope
        user = UserClaims(sub="user123", scopes=["admin:read"])
        assert user.is_admin() is True
        
        # Regular user
        user = UserClaims(sub="user123", roles=["user"], scopes=["read"])
        assert user.is_admin() is False
    
    def test_can_access_tenant(self):
        """Test tenant access checking"""
        user = UserClaims(sub="user123", tenant_id="tenant1")
        
        # Own tenant
        assert user.can_access_tenant("tenant1") is True
        
        # Other tenant (not admin)
        assert user.can_access_tenant("tenant2") is False
        
        # Admin can access any tenant
        admin_user = UserClaims(sub="admin123", tenant_id="tenant1", roles=["admin"])
        assert admin_user.can_access_tenant("tenant2") is True
        
        # Cross-tenant scope
        cross_tenant_user = UserClaims(
            sub="user123",
            tenant_id="tenant1",
            scopes=["tenant:access:tenant2"]
        )
        assert cross_tenant_user.can_access_tenant("tenant2") is True
        
        # Wildcard tenant access
        wildcard_user = UserClaims(
            sub="user123",
            tenant_id="tenant1", 
            scopes=["tenant:access:*"]
        )
        assert wildcard_user.can_access_tenant("tenant2") is True


class TestServiceClaims:
    """Test ServiceClaims model"""
    
    def test_service_claims_creation(self):
        """Test creating ServiceClaims"""
        claims_data = {
            "sub": "auth-service",
            "target_service": "api-service",
            "allowed_operations": ["read", "write"],
            "tenant_id": "tenant1",
            "identity_id": "identity123"
        }
        
        service = ServiceClaims(**claims_data)
        
        assert service.service_name == "auth-service"
        assert service.target_service == "api-service"
        assert service.allowed_operations == ["read", "write"]
        assert service.tenant_id == "tenant1"
        assert service.identity_id == "identity123"
        assert service.authenticated is True
        assert service.is_service is True
    
    def test_can_perform_operation(self):
        """Test operation checking for services"""
        service = ServiceClaims(
            sub="test-service",
            target_service="api",
            allowed_operations=["read", "write"],
            identity_id="id123"
        )
        
        assert service.can_perform_operation("read") is True
        assert service.can_perform_operation("write") is True
        assert service.can_perform_operation("delete") is False
        
        # Wildcard operations
        wildcard_service = ServiceClaims(
            sub="test-service",
            target_service="api",
            allowed_operations=["*"],
            identity_id="id123"
        )
        assert wildcard_service.can_perform_operation("any-operation") is True


class TestGetCurrentUser:
    """Test get_current_user dependency"""
    
    def test_get_current_user_success(self):
        """Test successful user retrieval"""
        request = Mock()
        request.state.user_claims = {
            "sub": "user123",
            "authenticated": True,
            "is_service": False,
            "scopes": ["read"]
        }
        
        user = get_current_user(request)
        
        assert isinstance(user, UserClaims)
        assert user.user_id == "user123"
        assert user.authenticated is True
    
    def test_get_current_user_no_claims(self):
        """Test user retrieval when no claims available"""
        request = Mock()
        # No user_claims attribute
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_not_authenticated(self):
        """Test user retrieval when not authenticated"""
        request = Mock()
        request.state.user_claims = {
            "sub": "user123",
            "authenticated": False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_user_service_token(self):
        """Test user retrieval rejects service tokens"""
        request = Mock()
        request.state.user_claims = {
            "sub": "service123",
            "authenticated": True,
            "is_service": True
        }
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        
        assert exc_info.value.status_code == 401


class TestGetCurrentService:
    """Test get_current_service dependency"""
    
    def test_get_current_service_success(self):
        """Test successful service retrieval"""
        request = Mock()
        request.state.service_claims = {
            "sub": "auth-service",
            "target_service": "api-service",
            "allowed_operations": ["read"],
            "identity_id": "id123",
            "service_authenticated": True
        }
        
        service = get_current_service(request)
        
        assert isinstance(service, ServiceClaims)
        assert service.service_name == "auth-service"
        assert service.target_service == "api-service"
    
    def test_get_current_service_no_claims(self):
        """Test service retrieval when no claims available"""
        request = Mock()
        # No service_claims attribute
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_service(request)
        
        assert exc_info.value.status_code == 401
    
    def test_get_current_service_not_authenticated(self):
        """Test service retrieval when not authenticated"""
        request = Mock()
        request.state.service_claims = {
            "sub": "service123",
            "service_authenticated": False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_service(request)
        
        assert exc_info.value.status_code == 401


class TestGetOptionalUser:
    """Test get_optional_user dependency"""
    
    def test_get_optional_user_success(self):
        """Test optional user retrieval success"""
        request = Mock()
        request.state.user_claims = {
            "sub": "user123",
            "authenticated": True,
            "is_service": False
        }
        
        user = get_optional_user(request)
        
        assert isinstance(user, UserClaims)
        assert user.user_id == "user123"
    
    def test_get_optional_user_none(self):
        """Test optional user retrieval returns None when not authenticated"""
        request = Mock()
        # No user_claims attribute
        
        user = get_optional_user(request)
        
        assert user is None


class TestRequireScopes:
    """Test require_scopes dependency factory"""
    
    def test_require_scopes_success(self):
        """Test successful scope requirement"""
        user = UserClaims(sub="user123", scopes=["read", "write"])
        
        # Create dependency
        dependency = require_scopes(["read"])
        result = dependency(user)
        
        assert result == user
    
    def test_require_scopes_failure(self):
        """Test failed scope requirement"""
        user = UserClaims(sub="user123", scopes=["read"])
        
        # Require scope user doesn't have
        dependency = require_scopes(["admin"])
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(user)
        
        assert exc_info.value.status_code == 403
    
    def test_require_all_scopes_success(self):
        """Test require all scopes success"""
        user = UserClaims(sub="user123", scopes=["read", "write", "delete"])
        
        dependency = require_scopes(["read", "write"], require_all=True)
        result = dependency(user)
        
        assert result == user
    
    def test_require_all_scopes_failure(self):
        """Test require all scopes failure"""
        user = UserClaims(sub="user123", scopes=["read"])
        
        dependency = require_scopes(["read", "write"], require_all=True)
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(user)
        
        assert exc_info.value.status_code == 403


class TestRequireRoles:
    """Test require_roles dependency factory"""
    
    def test_require_roles_success(self):
        """Test successful role requirement"""
        user = UserClaims(sub="user123", roles=["user", "moderator"])
        
        dependency = require_roles(["user"])
        result = dependency(user)
        
        assert result == user
    
    def test_require_roles_failure(self):
        """Test failed role requirement"""
        user = UserClaims(sub="user123", roles=["user"])
        
        dependency = require_roles(["admin"])
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(user)
        
        assert exc_info.value.status_code == 403
    
    def test_require_any_roles_success(self):
        """Test require any roles success"""
        user = UserClaims(sub="user123", roles=["moderator"])
        
        dependency = require_roles(["admin", "moderator"], require_all=False)
        result = dependency(user)
        
        assert result == user
    
    def test_require_all_roles_failure(self):
        """Test require all roles failure"""
        user = UserClaims(sub="user123", roles=["user"])
        
        dependency = require_roles(["user", "admin"], require_all=True)
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(user)
        
        assert exc_info.value.status_code == 403


class TestRequireAdmin:
    """Test require_admin dependency"""
    
    def test_require_admin_success_role(self):
        """Test admin requirement success with role"""
        user = UserClaims(sub="admin123", roles=["admin"])
        
        dependency = require_admin()
        result = dependency(user)
        
        assert result == user
    
    def test_require_admin_success_scope(self):
        """Test admin requirement success with scope"""
        user = UserClaims(sub="user123", scopes=["admin:read"])
        
        dependency = require_admin()
        result = dependency(user)
        
        assert result == user
    
    def test_require_admin_failure(self):
        """Test admin requirement failure"""
        user = UserClaims(sub="user123", roles=["user"], scopes=["read"])
        
        dependency = require_admin()
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(user)
        
        assert exc_info.value.status_code == 403


class TestRequireTenantAccess:
    """Test require_tenant_access dependency factory"""
    
    def test_require_tenant_access_own_tenant(self):
        """Test tenant access for own tenant"""
        user = UserClaims(sub="user123", tenant_id="tenant1")
        
        dependency = require_tenant_access("tenant1")
        result = dependency(user)
        
        assert result == user
    
    def test_require_tenant_access_other_tenant_denied(self):
        """Test tenant access denied for other tenant"""
        user = UserClaims(sub="user123", tenant_id="tenant1")
        
        dependency = require_tenant_access("tenant2")
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(user)
        
        assert exc_info.value.status_code == 403
    
    def test_require_tenant_access_admin_allowed(self):
        """Test admin can access any tenant"""
        user = UserClaims(sub="admin123", tenant_id="tenant1", roles=["admin"])
        
        dependency = require_tenant_access("tenant2")
        result = dependency(user)
        
        assert result == user


class TestRequireServiceOperation:
    """Test require_service_operation dependency factory"""
    
    def test_require_service_operation_success(self):
        """Test successful service operation requirement"""
        service = ServiceClaims(
            sub="test-service",
            target_service="api",
            allowed_operations=["read", "write"],
            identity_id="id123"
        )
        
        dependency = require_service_operation(["read"])
        result = dependency(service)
        
        assert result == service
    
    def test_require_service_operation_failure(self):
        """Test failed service operation requirement"""
        service = ServiceClaims(
            sub="test-service",
            target_service="api",
            allowed_operations=["read"],
            identity_id="id123"
        )
        
        dependency = require_service_operation(["write"])
        
        with pytest.raises(HTTPException) as exc_info:
            dependency(service)
        
        assert exc_info.value.status_code == 403
    
    def test_require_multiple_operations(self):
        """Test requiring multiple operations"""
        service = ServiceClaims(
            sub="test-service",
            target_service="api",
            allowed_operations=["read", "write"],
            identity_id="id123"
        )
        
        dependency = require_service_operation(["read", "write"])
        result = dependency(service)
        
        assert result == service
    
    def test_require_operation_with_wildcard(self):
        """Test operation requirement with wildcard"""
        service = ServiceClaims(
            sub="test-service",
            target_service="api",
            allowed_operations=["*"],
            identity_id="id123"
        )
        
        dependency = require_service_operation(["read", "write", "delete"])
        result = dependency(service)
        
        assert result == service


class TestUserClaimsIntegration:
    """Integration tests for user claims and dependencies"""
    
    def test_complex_user_permissions(self):
        """Test complex user permission scenarios"""
        # Create user with mixed permissions
        user = UserClaims(
            sub="complex_user",
            tenant_id="tenant1",
            scopes=["read", "write", "billing:read", "tenant:access:tenant2"],
            roles=["user", "billing_admin"],
            email="user@example.com"
        )
        
        # Test various permission checks
        assert user.has_scope("read") is True
        assert user.has_scope("billing:read") is True
        assert user.has_any_scope(["admin", "billing:read"]) is True
        assert user.has_all_scopes(["read", "write"]) is True
        
        assert user.has_role("user") is True
        assert user.has_any_role(["admin", "billing_admin"]) is True
        assert user.is_admin() is False  # No admin role or scope
        
        assert user.can_access_tenant("tenant1") is True
        assert user.can_access_tenant("tenant2") is True  # Has cross-tenant scope
        assert user.can_access_tenant("tenant3") is False
    
    def test_admin_user_permissions(self):
        """Test admin user permissions"""
        admin = UserClaims(
            sub="admin_user",
            tenant_id="tenant1",
            scopes=["admin:read", "admin:write"],
            roles=["admin"],
            email="admin@example.com"
        )
        
        assert admin.is_admin() is True
        assert admin.can_access_tenant("any_tenant") is True
        assert admin.has_any_scope(["admin:read"]) is True
        assert admin.has_role("admin") is True
    
    def test_service_permissions(self):
        """Test service permission scenarios"""
        service = ServiceClaims(
            sub="api-gateway",
            target_service="user-service",
            allowed_operations=["read", "write"],
            tenant_id="tenant1",
            identity_id="gateway_id"
        )
        
        assert service.can_perform_operation("read") is True
        assert service.can_perform_operation("write") is True
        assert service.can_perform_operation("delete") is False
        assert service.is_service is True
        assert service.authenticated is True