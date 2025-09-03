"""
Tests for Edge Validation

Tests for EdgeJWTValidator, middleware, and sensitivity patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request
from starlette.responses import JSONResponse

from dotmac.auth import (
    EdgeJWTValidator,
    EdgeAuthMiddleware,
    JWTService,
    SensitivityLevel,
    create_edge_validator,
    TokenNotFound,
    TenantMismatch,
    InsufficientScope,
    InsufficientRole,
    COMMON_SENSITIVITY_PATTERNS,
)


class TestSensitivityLevel:
    """Test sensitivity level constants"""
    
    def test_sensitivity_levels(self):
        """Test all sensitivity levels are defined"""
        assert SensitivityLevel.PUBLIC == "public"
        assert SensitivityLevel.AUTHENTICATED == "authenticated"
        assert SensitivityLevel.SENSITIVE == "sensitive"
        assert SensitivityLevel.ADMIN == "admin"
        assert SensitivityLevel.INTERNAL == "internal"


class TestEdgeJWTValidator:
    """Test EdgeJWTValidator functionality"""
    
    @pytest.fixture
    def jwt_service(self):
        return JWTService(algorithm="HS256", secret="test-secret")
    
    @pytest.fixture
    def validator(self, jwt_service):
        return EdgeJWTValidator(jwt_service)
    
    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {}
        request.cookies = {}
        return request
    
    def test_validator_initialization(self, jwt_service):
        """Test validator initialization"""
        validator = EdgeJWTValidator(
            jwt_service,
            default_sensitivity=SensitivityLevel.ADMIN,
            require_https=True
        )
        
        assert validator.jwt_service == jwt_service
        assert validator.default_sensitivity == SensitivityLevel.ADMIN
        assert validator.require_https is True
    
    def test_configure_sensitivity_patterns(self, validator):
        """Test sensitivity pattern configuration"""
        patterns = {
            (r"/api/public/.*", r"GET|POST"): SensitivityLevel.PUBLIC,
            (r"/api/admin/.*", r".*"): SensitivityLevel.ADMIN,
        }
        
        validator.configure_sensitivity_patterns(patterns)
        
        assert len(validator.sensitivity_patterns) == 2
        assert len(validator._compiled_patterns) == 2
    
    def test_add_sensitivity_pattern(self, validator):
        """Test adding individual sensitivity patterns"""
        validator.add_sensitivity_pattern(
            r"/api/test/.*",
            r"POST",
            SensitivityLevel.SENSITIVE
        )
        
        assert len(validator.sensitivity_patterns) == 1
        assert validator.sensitivity_patterns[0][2] == SensitivityLevel.SENSITIVE
    
    def test_get_route_sensitivity(self, validator):
        """Test route sensitivity determination"""
        validator.configure_sensitivity_patterns({
            (r"/api/public/.*", r"GET"): SensitivityLevel.PUBLIC,
            (r"/api/admin/.*", r".*"): SensitivityLevel.ADMIN,
        })
        
        # Test pattern matches
        assert validator.get_route_sensitivity("/api/public/test", "GET") == SensitivityLevel.PUBLIC
        assert validator.get_route_sensitivity("/api/admin/users", "POST") == SensitivityLevel.ADMIN
        
        # Test default sensitivity
        assert validator.get_route_sensitivity("/api/other", "GET") == validator.default_sensitivity
    
    def test_extract_token_from_request(self, validator):
        """Test token extraction from various sources"""
        request = Mock()
        request.headers = {}
        request.cookies = {}
        
        # No token
        assert validator.extract_token_from_request(request) is None
        
        # Bearer token in Authorization header
        request.headers = {"Authorization": "Bearer test-token"}
        assert validator.extract_token_from_request(request) == "test-token"
        
        # Token in cookie
        request.headers = {}
        request.cookies = {"access_token": "cookie-token"}
        assert validator.extract_token_from_request(request) == "cookie-token"
        
        # Token in custom header
        request.cookies = {}
        request.headers = {"X-Auth-Token": "header-token"}
        assert validator.extract_token_from_request(request) == "header-token"
    
    def test_extract_service_token(self, validator):
        """Test service token extraction"""
        request = Mock()
        request.headers = {"X-Service-Token": "service-token"}
        
        assert validator.extract_service_token(request) == "service-token"
    
    @pytest.mark.asyncio
    async def test_validate_public_route(self, validator, mock_request):
        """Test validation of public routes"""
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.PUBLIC
        })
        
        result = await validator.validate(mock_request)
        
        assert result["authenticated"] is False
        assert result["user_id"] is None
    
    @pytest.mark.asyncio
    async def test_validate_authenticated_route_success(self, validator, jwt_service, mock_request):
        """Test successful authentication for authenticated routes"""
        # Create valid token
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.AUTHENTICATED
        })
        
        result = await validator.validate(mock_request)
        
        assert result["authenticated"] is True
        assert result["sub"] == "user123"
        assert result["scopes"] == ["read"]
    
    @pytest.mark.asyncio
    async def test_validate_authenticated_route_no_token(self, validator, mock_request):
        """Test authentication failure when no token provided"""
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.AUTHENTICATED
        })
        
        with pytest.raises(TokenNotFound):
            await validator.validate(mock_request)
    
    @pytest.mark.asyncio
    async def test_validate_sensitive_route_insufficient_scope(self, validator, jwt_service, mock_request):
        """Test sensitive route with insufficient scope"""
        # Token without required scope
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.SENSITIVE
        })
        
        with pytest.raises(InsufficientScope):
            await validator.validate(mock_request)
    
    @pytest.mark.asyncio
    async def test_validate_admin_route_insufficient_permissions(self, validator, jwt_service, mock_request):
        """Test admin route with insufficient permissions"""
        # Token without admin permissions
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.ADMIN
        })
        
        with pytest.raises(InsufficientRole):
            await validator.validate(mock_request)
    
    @pytest.mark.asyncio
    async def test_validate_admin_route_with_admin_scope(self, validator, jwt_service, mock_request):
        """Test admin route with admin scope"""
        # Token with admin scope
        token = jwt_service.issue_access_token("user123", scopes=["admin:read"])
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.ADMIN
        })
        
        result = await validator.validate(mock_request)
        
        assert result["authenticated"] is True
        assert result["sub"] == "user123"
    
    @pytest.mark.asyncio
    async def test_tenant_validation_success(self, jwt_service):
        """Test successful tenant validation"""
        def tenant_resolver(request):
            return "tenant1"
        
        validator = EdgeJWTValidator(jwt_service, tenant_resolver=tenant_resolver)
        
        token = jwt_service.issue_access_token("user123", tenant_id="tenant1")
        request = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.cookies = {}
        
        result = await validator.validate(request)
        
        assert result["tenant_id"] == "tenant1"
    
    @pytest.mark.asyncio
    async def test_tenant_validation_mismatch(self, jwt_service):
        """Test tenant mismatch"""
        def tenant_resolver(request):
            return "tenant2"
        
        validator = EdgeJWTValidator(jwt_service, tenant_resolver=tenant_resolver)
        
        token = jwt_service.issue_access_token("user123", tenant_id="tenant1")
        request = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.cookies = {}
        
        with pytest.raises(TenantMismatch):
            await validator.validate(request)
    
    @pytest.mark.asyncio
    async def test_https_requirement_production(self, validator):
        """Test HTTPS requirement in production"""
        validator.require_https = True
        
        request = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.url.scheme = "http"  # Not HTTPS
        request.client.host = "example.com"
        
        validator.configure_sensitivity_patterns({
            (r"/api/test", r"GET"): SensitivityLevel.AUTHENTICATED
        })
        
        with pytest.raises(Exception):  # Should raise HTTPS requirement error
            await validator.validate(request)
    
    @pytest.mark.asyncio
    async def test_https_exemption_localhost(self, validator):
        """Test HTTPS exemption for localhost"""
        validator.require_https = True
        
        request = Mock()
        request.url.path = "/health"
        request.method = "GET"
        request.url.scheme = "http"
        request.client.host = "127.0.0.1"
        
        validator.configure_sensitivity_patterns({
            (r"/health", r"GET"): SensitivityLevel.PUBLIC
        })
        
        # Should not raise HTTPS error for health check on localhost
        result = await validator.validate(request)
        assert result["authenticated"] is False


class TestEdgeAuthMiddleware:
    """Test EdgeAuthMiddleware"""
    
    @pytest.fixture
    def jwt_service(self):
        return JWTService(algorithm="HS256", secret="test-secret")
    
    @pytest.fixture
    def validator(self, jwt_service):
        validator = EdgeJWTValidator(jwt_service)
        validator.configure_sensitivity_patterns({
            (r"/api/public/.*", r".*"): SensitivityLevel.PUBLIC,
            (r"/api/protected/.*", r".*"): SensitivityLevel.AUTHENTICATED,
        })
        return validator
    
    @pytest.fixture
    def middleware(self, validator):
        app = Mock()
        return EdgeAuthMiddleware(
            app,
            validator,
            service_name="test-service",
            skip_paths=["/health", "/docs"]
        )
    
    @pytest.mark.asyncio
    async def test_middleware_skip_paths(self, middleware):
        """Test middleware skips specified paths"""
        request = Mock()
        request.url.path = "/docs"
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_middleware_public_route(self, middleware):
        """Test middleware handles public routes"""
        request = Mock()
        request.url.path = "/api/public/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {}
        request.cookies = {}
        request.state = Mock()
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        assert request.state.user_claims["authenticated"] is False
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_middleware_protected_route_success(self, middleware, jwt_service):
        """Test middleware handles protected routes with valid token"""
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        
        request = Mock()
        request.url.path = "/api/protected/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.cookies = {}
        request.state = Mock()
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        assert request.state.user_claims["authenticated"] is True
        assert request.state.user_claims["sub"] == "user123"
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_middleware_protected_route_no_token(self, middleware):
        """Test middleware handles protected routes without token"""
        request = Mock()
        request.url.path = "/api/protected/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {}
        request.cookies = {}
        
        call_next = AsyncMock()
        
        response = await middleware.dispatch(request, call_next)
        
        # Should return error response, not call next
        assert isinstance(response, JSONResponse)
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_adds_user_headers(self, middleware, jwt_service):
        """Test middleware adds user headers for downstream services"""
        token = jwt_service.issue_access_token("user123", scopes=["read"], tenant_id="tenant1")
        
        request = Mock()
        request.url.path = "/api/protected/test"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {"Authorization": f"Bearer {token}"}
        request.cookies = {}
        request.state = Mock()
        
        call_next = AsyncMock()
        call_next.return_value = Mock()
        
        await middleware.dispatch(request, call_next)
        
        # Check headers were added
        assert "X-User-Id" in request.headers
        assert request.headers["X-User-Id"] == "user123"
        assert request.headers["X-User-Scopes"] == "read"
        assert request.headers["X-Tenant-Id"] == "tenant1"


class TestCreateEdgeValidator:
    """Test edge validator factory function"""
    
    def test_create_edge_validator_default(self):
        """Test creating edge validator with defaults"""
        jwt_service = JWTService(algorithm="HS256", secret="test-secret")
        
        validator = create_edge_validator(jwt_service)
        
        assert validator.jwt_service == jwt_service
        assert validator.require_https is True  # Production default
        assert len(validator._compiled_patterns) > 0  # Should have default patterns
    
    def test_create_edge_validator_development(self):
        """Test creating edge validator for development"""
        jwt_service = JWTService(algorithm="HS256", secret="test-secret")
        
        validator = create_edge_validator(
            jwt_service,
            environment="development"
        )
        
        assert validator.require_https is False  # Development default
    
    def test_create_edge_validator_custom_patterns(self):
        """Test creating edge validator with custom patterns"""
        jwt_service = JWTService(algorithm="HS256", secret="test-secret")
        
        custom_patterns = {
            (r"/custom/.*", r".*"): SensitivityLevel.PUBLIC
        }
        
        validator = create_edge_validator(
            jwt_service,
            patterns=custom_patterns
        )
        
        assert len(validator.sensitivity_patterns) == 1
        assert validator.sensitivity_patterns[0][2] == SensitivityLevel.PUBLIC
    
    def test_create_edge_validator_with_tenant_resolver(self):
        """Test creating edge validator with tenant resolver"""
        jwt_service = JWTService(algorithm="HS256", secret="test-secret")
        
        def tenant_resolver(request):
            return "tenant1"
        
        validator = create_edge_validator(
            jwt_service,
            tenant_resolver=tenant_resolver
        )
        
        assert validator.tenant_resolver == tenant_resolver


class TestCommonSensitivityPatterns:
    """Test common sensitivity patterns"""
    
    def test_common_patterns_exist(self):
        """Test that common patterns are defined"""
        assert isinstance(COMMON_SENSITIVITY_PATTERNS, dict)
        assert len(COMMON_SENSITIVITY_PATTERNS) > 0
    
    def test_health_endpoint_public(self):
        """Test that health endpoints are public"""
        patterns = COMMON_SENSITIVITY_PATTERNS
        
        # Find health pattern
        health_pattern = None
        for (path, method), sensitivity in patterns.items():
            if "health" in path:
                health_pattern = (path, method, sensitivity)
                break
        
        assert health_pattern is not None
        assert health_pattern[2] == SensitivityLevel.PUBLIC
    
    def test_admin_endpoints_protected(self):
        """Test that admin endpoints are protected"""
        patterns = COMMON_SENSITIVITY_PATTERNS
        
        # Find admin pattern
        admin_pattern = None
        for (path, method), sensitivity in patterns.items():
            if "admin" in path:
                admin_pattern = (path, method, sensitivity)
                break
        
        assert admin_pattern is not None
        assert admin_pattern[2] == SensitivityLevel.ADMIN


class TestEdgeValidationIntegration:
    """Integration tests for edge validation"""
    
    @pytest.mark.asyncio
    async def test_complete_validation_flow(self):
        """Test complete edge validation flow"""
        jwt_service = JWTService(
            algorithm="HS256",
            secret="integration-test-secret",
            issuer="test-issuer"
        )
        
        validator = EdgeJWTValidator(jwt_service)
        validator.configure_sensitivity_patterns({
            (r"/api/public/.*", r".*"): SensitivityLevel.PUBLIC,
            (r"/api/user/.*", r".*"): SensitivityLevel.AUTHENTICATED,
            (r"/api/admin/.*", r".*"): SensitivityLevel.ADMIN,
        })
        
        # Test public endpoint
        request = Mock()
        request.url.path = "/api/public/info"
        request.method = "GET"
        request.url.scheme = "https"
        request.client.host = "example.com"
        request.headers = {}
        request.cookies = {}
        
        result = await validator.validate(request)
        assert result["authenticated"] is False
        
        # Test authenticated endpoint with valid token
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        request.url.path = "/api/user/profile"
        request.headers = {"Authorization": f"Bearer {token}"}
        
        result = await validator.validate(request)
        assert result["authenticated"] is True
        assert result["sub"] == "user123"
        
        # Test admin endpoint with admin token
        admin_token = jwt_service.issue_access_token("admin123", scopes=["admin:read"])
        request.url.path = "/api/admin/users"
        request.headers = {"Authorization": f"Bearer {admin_token}"}
        
        result = await validator.validate(request)
        assert result["authenticated"] is True
        assert result["sub"] == "admin123"