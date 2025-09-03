"""
Tests for Service Token Management

Tests for service registration, token issuance, and service-to-service authentication.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from dotmac.auth import (
    ServiceIdentity,
    ServiceTokenManager,
    ServiceAuthMiddleware,
    create_service_token_manager,
    InvalidServiceToken,
    UnauthorizedService,
    TokenExpired,
    ConfigurationError,
)


class TestServiceIdentity:
    """Test ServiceIdentity class"""
    
    def test_service_identity_creation(self):
        """Test service identity creation"""
        identity = ServiceIdentity(
            service_name="test-service",
            service_info={"version": "1.0.0"},
            allowed_targets=["target1", "target2"],
            allowed_operations=["read", "write"]
        )
        
        assert identity.service_name == "test-service"
        assert identity.service_info == {"version": "1.0.0"}
        assert identity.allowed_targets == {"target1", "target2"}
        assert identity.allowed_operations == {"read", "write"}
        assert identity.identity_id is not None
        assert isinstance(identity.created_at, datetime)
    
    def test_can_access_target(self):
        """Test target access checking"""
        identity = ServiceIdentity(
            "test-service",
            {},
            ["target1", "target2"],
            []
        )
        
        assert identity.can_access_target("target1") is True
        assert identity.can_access_target("target3") is False
        
        # Test wildcard access
        identity_wildcard = ServiceIdentity(
            "test-service",
            {},
            ["*"],
            []
        )
        assert identity_wildcard.can_access_target("any-target") is True
    
    def test_can_perform_operation(self):
        """Test operation checking"""
        identity = ServiceIdentity(
            "test-service",
            {},
            [],
            ["read", "write"]
        )
        
        assert identity.can_perform_operation("read") is True
        assert identity.can_perform_operation("delete") is False
        
        # Test wildcard operations
        identity_wildcard = ServiceIdentity(
            "test-service",
            {},
            [],
            ["*"]
        )
        assert identity_wildcard.can_perform_operation("any-operation") is True


class TestServiceTokenManager:
    """Test ServiceTokenManager"""
    
    @pytest.fixture
    def token_manager(self):
        return ServiceTokenManager(
            signing_secret="test-service-secret",
            algorithm="HS256"
        )
    
    def test_manager_initialization_hs256(self):
        """Test manager initialization with HS256"""
        manager = ServiceTokenManager(
            signing_secret="test-secret",
            algorithm="HS256"
        )
        
        assert manager.algorithm == "HS256"
        assert manager.signing_key == "test-secret"
        assert manager.verification_key == "test-secret"
    
    def test_manager_initialization_rs256(self):
        """Test manager initialization with RS256"""
        private_key = "test-private-key"
        public_key = "test-public-key"
        
        manager = ServiceTokenManager(
            keypair=(private_key, public_key),
            algorithm="RS256"
        )
        
        assert manager.algorithm == "RS256"
        assert manager.signing_key == private_key
        assert manager.verification_key == public_key
    
    def test_missing_credentials_raises_error(self):
        """Test missing credentials raise configuration error"""
        with pytest.raises(ConfigurationError):
            ServiceTokenManager(algorithm="HS256")
        
        with pytest.raises(ConfigurationError):
            ServiceTokenManager(algorithm="RS256")
    
    def test_invalid_algorithm_raises_error(self):
        """Test invalid algorithm raises error"""
        with pytest.raises(ConfigurationError):
            ServiceTokenManager(
                signing_secret="secret",
                algorithm="INVALID"
            )
    
    def test_register_service(self, token_manager):
        """Test service registration"""
        identity = token_manager.register_service(
            "test-service",
            {"version": "1.0.0"},
            ["target1", "target2"],
            ["read", "write"]
        )
        
        assert isinstance(identity, ServiceIdentity)
        assert identity.service_name == "test-service"
        assert "test-service" in token_manager.services
    
    def test_create_service_identity(self, token_manager):
        """Test service identity creation convenience method"""
        identity = token_manager.create_service_identity(
            "test-service",
            version="2.0.0",
            description="Test service",
            allowed_targets=["api-service"],
            allowed_operations=["read"]
        )
        
        assert identity.service_name == "test-service"
        assert identity.service_info["version"] == "2.0.0"
        assert identity.service_info["description"] == "Test service"
        assert "api-service" in identity.allowed_targets
        assert "read" in identity.allowed_operations
    
    def test_get_service(self, token_manager):
        """Test getting registered service"""
        identity = token_manager.register_service(
            "test-service", {}, ["target1"], ["read"]
        )
        
        retrieved = token_manager.get_service("test-service")
        assert retrieved == identity
        
        # Non-existent service
        assert token_manager.get_service("nonexistent") is None
    
    def test_issue_service_token(self, token_manager):
        """Test service token issuance"""
        # Register service
        identity = token_manager.register_service(
            "source-service",
            {"version": "1.0.0"},
            ["target-service"],
            ["read", "write"]
        )
        
        # Issue token
        token = token_manager.issue_service_token(
            identity,
            "target-service",
            allowed_operations=["read"],
            tenant_context="tenant1",
            expires_in=30
        )
        
        assert isinstance(token, str)
        
        # Verify token
        claims = token_manager.verify_service_token(token)
        assert claims["sub"] == "source-service"
        assert claims["target_service"] == "target-service"
        assert claims["allowed_operations"] == ["read"]
        assert claims["tenant_id"] == "tenant1"
        assert claims["type"] == "service"
    
    def test_issue_token_unauthorized_target(self, token_manager):
        """Test token issuance for unauthorized target"""
        identity = token_manager.register_service(
            "source-service",
            {},
            ["allowed-target"],  # Only allowed to access this target
            ["read"]
        )
        
        with pytest.raises(UnauthorizedService):
            token_manager.issue_service_token(
                identity,
                "unauthorized-target"  # Not in allowed targets
            )
    
    def test_issue_token_unauthorized_operation(self, token_manager):
        """Test token issuance for unauthorized operation"""
        identity = token_manager.register_service(
            "source-service",
            {},
            ["target-service"],
            ["read"]  # Only allowed to read
        )
        
        with pytest.raises(UnauthorizedService):
            token_manager.issue_service_token(
                identity,
                "target-service",
                allowed_operations=["write"]  # Not allowed
            )
    
    def test_verify_service_token(self, token_manager):
        """Test service token verification"""
        # Register and issue token
        identity = token_manager.register_service(
            "source-service", {}, ["target-service"], ["read", "write"]
        )
        token = token_manager.issue_service_token(
            identity, "target-service", ["read"]
        )
        
        # Verify token
        claims = token_manager.verify_service_token(token)
        assert claims["sub"] == "source-service"
        assert claims["target_service"] == "target-service"
        
        # Verify with expected target
        claims = token_manager.verify_service_token(
            token, expected_target="target-service"
        )
        assert claims["target_service"] == "target-service"
        
        # Verify with wrong target
        with pytest.raises(UnauthorizedService):
            token_manager.verify_service_token(
                token, expected_target="wrong-target"
            )
    
    def test_verify_token_required_operations(self, token_manager):
        """Test token verification with required operations"""
        identity = token_manager.register_service(
            "source-service", {}, ["target-service"], ["read", "write"]
        )
        token = token_manager.issue_service_token(
            identity, "target-service", ["read"]
        )
        
        # Verify with allowed operation
        claims = token_manager.verify_service_token(
            token, required_operations=["read"]
        )
        assert "read" in claims["allowed_operations"]
        
        # Verify with disallowed operation
        with pytest.raises(UnauthorizedService):
            token_manager.verify_service_token(
                token, required_operations=["write"]
            )
        
        # Verify with mixed operations
        with pytest.raises(UnauthorizedService):
            token_manager.verify_service_token(
                token, required_operations=["read", "write"]
            )
    
    def test_verify_token_wildcard_operations(self, token_manager):
        """Test token verification with wildcard operations"""
        identity = token_manager.register_service(
            "source-service", {}, ["target-service"], ["*"]
        )
        token = token_manager.issue_service_token(
            identity, "target-service", ["*"]
        )
        
        # Should allow any operation
        claims = token_manager.verify_service_token(
            token, required_operations=["read", "write", "delete"]
        )
        assert claims["allowed_operations"] == ["*"]
    
    def test_verify_invalid_token(self, token_manager):
        """Test verification of invalid tokens"""
        with pytest.raises(InvalidServiceToken):
            token_manager.verify_service_token("invalid.token.here")
        
        with pytest.raises(InvalidServiceToken):
            token_manager.verify_service_token("not-a-token")
    
    def test_verify_token_unregistered_service(self, token_manager):
        """Test verification fails for unregistered service"""
        # Create token for unregistered service
        identity = token_manager.register_service(
            "temp-service", {}, ["target"], ["read"]
        )
        token = token_manager.issue_service_token(identity, "target")
        
        # Unregister service
        token_manager.revoke_service_tokens("temp-service")
        
        # Verification should fail
        with pytest.raises(UnauthorizedService):
            token_manager.verify_service_token(token)
    
    def test_revoke_service_tokens(self, token_manager):
        """Test service token revocation"""
        token_manager.register_service("test-service", {}, ["target"], ["read"])
        
        assert "test-service" in token_manager.services
        
        token_manager.revoke_service_tokens("test-service")
        
        assert "test-service" not in token_manager.services
    
    def test_list_services(self, token_manager):
        """Test listing registered services"""
        token_manager.register_service("service1", {}, [], [])
        token_manager.register_service("service2", {}, [], [])
        
        services = token_manager.list_services()
        
        assert "service1" in services
        assert "service2" in services
        assert len(services) == 2
    
    def test_get_service_info(self, token_manager):
        """Test getting service information"""
        identity = token_manager.register_service(
            "test-service",
            {"version": "1.0.0"},
            ["target1"],
            ["read"]
        )
        
        info = token_manager.get_service_info("test-service")
        
        assert info["service_name"] == "test-service"
        assert info["service_info"]["version"] == "1.0.0"
        assert info["allowed_targets"] == ["target1"]
        assert info["allowed_operations"] == ["read"]
        assert info["identity_id"] == identity.identity_id
        
        # Non-existent service
        assert token_manager.get_service_info("nonexistent") is None


class TestServiceAuthMiddleware:
    """Test ServiceAuthMiddleware"""
    
    @pytest.fixture
    def token_manager(self):
        return ServiceTokenManager(
            signing_secret="test-secret",
            algorithm="HS256"
        )
    
    @pytest.fixture
    def middleware(self, token_manager):
        app = Mock()
        return ServiceAuthMiddleware(
            app,
            token_manager,
            "target-service",
            required_operations=["read"],
            protected_paths=["/internal"]
        )
    
    @pytest.mark.asyncio
    async def test_middleware_unprotected_path(self, middleware):
        """Test middleware allows unprotected paths"""
        request = Mock()
        request.url.path = "/public/endpoint"
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_middleware_protected_path_no_token(self, middleware):
        """Test middleware blocks protected paths without token"""
        request = Mock()
        request.url.path = "/internal/endpoint"
        request.headers = {}
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(request, call_next)
        
        # Should return error response
        assert response is not None
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_protected_path_valid_token(self, middleware, token_manager):
        """Test middleware allows protected paths with valid token"""
        # Create service and token
        identity = token_manager.register_service(
            "source-service", {}, ["target-service"], ["read", "write"]
        )
        token = token_manager.issue_service_token(identity, "target-service", ["read"])
        
        request = Mock()
        request.url.path = "/internal/endpoint"
        request.headers = {"X-Service-Token": token}
        request.state = Mock()
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        # Should set service claims and call next
        assert hasattr(request.state, 'service_claims')
        assert request.state.service_authenticated is True
        assert request.state.calling_service == "source-service"
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_middleware_adds_service_headers(self, middleware, token_manager):
        """Test middleware adds service headers"""
        identity = token_manager.register_service(
            "source-service", {}, ["target-service"], ["read"]
        )
        token = token_manager.issue_service_token(
            identity, "target-service", ["read"], tenant_context="tenant1"
        )
        
        request = Mock()
        request.url.path = "/internal/endpoint"
        request.headers = {"X-Service-Token": token}
        request.state = Mock()
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        # Check service headers were added
        assert "X-Calling-Service" in request.headers
        assert request.headers["X-Calling-Service"] == "source-service"
        assert request.headers["X-Service-Operations"] == "read"
        assert request.headers["X-Service-Tenant"] == "tenant1"
    
    @pytest.mark.asyncio
    async def test_middleware_insufficient_operations(self, middleware, token_manager):
        """Test middleware blocks insufficient operations"""
        # Create token without required operations
        identity = token_manager.register_service(
            "source-service", {}, ["target-service"], ["write"]  # Has write, needs read
        )
        token = token_manager.issue_service_token(identity, "target-service", ["write"])
        
        request = Mock()
        request.url.path = "/internal/endpoint"
        request.headers = {"X-Service-Token": token}
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(request, call_next)
        
        # Should return error response
        assert response is not None
        call_next.assert_not_called()


class TestCreateServiceTokenManager:
    """Test factory function"""
    
    def test_create_manager_hs256(self):
        """Test creating HS256 manager"""
        manager = create_service_token_manager(
            algorithm="HS256",
            signing_secret="test-secret"
        )
        
        assert isinstance(manager, ServiceTokenManager)
        assert manager.algorithm == "HS256"
        assert manager.signing_key == "test-secret"
    
    def test_create_manager_rs256(self):
        """Test creating RS256 manager"""
        keypair = ("private-key", "public-key")
        manager = create_service_token_manager(
            algorithm="RS256",
            keypair=keypair
        )
        
        assert isinstance(manager, ServiceTokenManager)
        assert manager.algorithm == "RS256"
        assert manager.signing_key == "private-key"


class TestServiceTokenIntegration:
    """Integration tests for service token flow"""
    
    def test_complete_service_auth_flow(self):
        """Test complete service authentication flow"""
        # Create token manager
        manager = ServiceTokenManager(
            signing_secret="integration-test-secret",
            algorithm="HS256"
        )
        
        # Register services
        source_identity = manager.register_service(
            "auth-service",
            {"version": "1.0.0"},
            ["api-service", "user-service"],
            ["read", "write", "admin"]
        )
        
        target_identity = manager.register_service(
            "api-service",
            {"version": "1.0.0"},
            [],
            []
        )
        
        # Issue service token
        token = manager.issue_service_token(
            source_identity,
            "api-service",
            allowed_operations=["read", "write"],
            tenant_context="tenant1",
            expires_in=60
        )
        
        # Verify token as target service
        claims = manager.verify_service_token(
            token,
            expected_target="api-service",
            required_operations=["read"]
        )
        
        assert claims["sub"] == "auth-service"
        assert claims["target_service"] == "api-service"
        assert claims["tenant_id"] == "tenant1"
        assert "read" in claims["allowed_operations"]
        assert "write" in claims["allowed_operations"]
        
        # Test operation checking
        claims = manager.verify_service_token(
            token,
            required_operations=["read", "write"]
        )
        assert claims["sub"] == "auth-service"
        
        # Should fail for admin operation
        with pytest.raises(UnauthorizedService):
            manager.verify_service_token(
                token,
                required_operations=["admin"]
            )
    
    def test_service_registry_management(self):
        """Test service registry management"""
        manager = ServiceTokenManager(
            signing_secret="test-secret",
            algorithm="HS256"
        )
        
        # Register multiple services
        services_data = [
            ("auth-service", {"version": "1.0.0"}, ["*"], ["*"]),
            ("api-service", {"version": "2.0.0"}, ["user-service"], ["read"]),
            ("user-service", {"version": "1.5.0"}, [], ["read", "write"])
        ]
        
        for name, info, targets, ops in services_data:
            manager.register_service(name, info, targets, ops)
        
        # Verify all services registered
        services = manager.list_services()
        assert len(services) == 3
        assert all(name in services for name, _, _, _ in services_data)
        
        # Get service info
        auth_info = manager.get_service_info("auth-service")
        assert auth_info["service_info"]["version"] == "1.0.0"
        assert auth_info["allowed_targets"] == ["*"]
        
        # Test token issuance between services
        auth_service = manager.get_service("auth-service")
        api_service = manager.get_service("api-service")
        
        # Auth service can call anyone (has * target)
        token = manager.issue_service_token(auth_service, "api-service")
        claims = manager.verify_service_token(token)
        assert claims["sub"] == "auth-service"
        
        # API service can call user-service
        token = manager.issue_service_token(api_service, "user-service", ["read"])
        claims = manager.verify_service_token(token)
        assert claims["sub"] == "api-service"
        
        # API service cannot call auth-service (not in allowed targets)
        with pytest.raises(UnauthorizedService):
            manager.issue_service_token(api_service, "auth-service")
    
    @pytest.mark.asyncio
    async def test_middleware_integration(self):
        """Test middleware integration with service tokens"""
        manager = ServiceTokenManager(
            signing_secret="middleware-test-secret",
            algorithm="HS256"
        )
        
        # Register services
        source_service = manager.register_service(
            "client-service",
            {"version": "1.0.0"},
            ["internal-api"],
            ["read", "write"]
        )
        
        # Create middleware
        app = Mock()
        middleware = ServiceAuthMiddleware(
            app,
            manager,
            "internal-api",
            required_operations=["read"],
            protected_paths=["/internal", "/admin"]
        )
        
        # Issue token
        token = manager.issue_service_token(
            source_service,
            "internal-api",
            ["read", "write"]
        )
        
        # Test middleware with valid token
        request = Mock()
        request.url.path = "/internal/data"
        request.headers = {"X-Service-Token": token}
        request.state = Mock()
        
        call_next = AsyncMock()
        call_next.return_value = Mock(status_code=200)
        
        response = await middleware.dispatch(request, call_next)
        
        # Should succeed
        call_next.assert_called_once()
        assert request.state.service_authenticated is True
        assert request.state.calling_service == "client-service"