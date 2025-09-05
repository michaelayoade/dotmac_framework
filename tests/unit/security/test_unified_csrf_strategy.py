"""
Comprehensive unit tests for the Unified CSRF Strategy system.

Tests cover:
- CSRF mode configurations (API, SSR, Hybrid)
- Token generation and validation
- Portal-specific configurations
- Double-submit cookie pattern
- Error handling and security edge cases
"""

import time

import pytest
from dotmac_shared.security.unified_csrf_strategy import (
    CSRFConfig,
    CSRFError,
    CSRFMode,
    CSRFToken,
    CSRFTokenDelivery,
    CSRFTokenExpiredError,
    CSRFTokenMismatchError,
    CSRFValidationResult,
    CSRFViolation,
    UnifiedCSRFMiddleware,
    get_portal_csrf_config,
)
from fastapi import HTTPException, Request, Response
from starlette.datastructures import FormData, Headers


class TestCSRFMode:
    """Test CSRF mode enum."""
    
    def test_csrf_modes(self):
        """Test CSRF mode values."""
        assert CSRFMode.API_ONLY == "api_only"
        assert CSRFMode.SSR_ONLY == "ssr_only"
        assert CSRFMode.HYBRID == "hybrid"
        assert CSRFMode.DISABLED == "disabled"


class TestCSRFTokenDelivery:
    """Test CSRF token delivery enum."""
    
    def test_token_delivery_modes(self):
        """Test token delivery mode values."""
        assert CSRFTokenDelivery.HEADER_ONLY == "header_only"
        assert CSRFTokenDelivery.COOKIE_ONLY == "cookie_only"
        assert CSRFTokenDelivery.BOTH == "both"
        assert CSRFTokenDelivery.META_TAG == "meta_tag"


class TestCSRFConfig:
    """Test CSRF configuration."""
    
    def test_default_config(self):
        """Test default CSRF configuration."""
        config = CSRFConfig()
        assert config.mode == CSRFMode.HYBRID
        assert config.token_delivery == CSRFTokenDelivery.BOTH
        assert config.secret_key is None
        assert config.token_lifetime_seconds == 3600
        assert config.cookie_name == "csrftoken"
        assert config.header_name == "X-CSRF-Token"
        assert config.form_field_name == "csrfmiddlewaretoken"
        assert config.cookie_secure is True
        assert config.cookie_samesite == "Strict"
        assert config.require_https is True
    
    def test_custom_config(self):
        """Test custom CSRF configuration."""
        config = CSRFConfig(
            mode=CSRFMode.API_ONLY,
            token_delivery=CSRFTokenDelivery.HEADER_ONLY,
            secret_key="custom-secret-key",
            token_lifetime_seconds=1800,
            cookie_name="custom_csrf",
            header_name="X-Custom-CSRF",
            require_https=False
        )
        assert config.mode == CSRFMode.API_ONLY
        assert config.token_delivery == CSRFTokenDelivery.HEADER_ONLY
        assert config.secret_key == "custom-secret-key"
        assert config.token_lifetime_seconds == 1800
        assert config.cookie_name == "custom_csrf"
        assert config.header_name == "X-Custom-CSRF"
        assert config.require_https is False
    
    def test_portal_specific_config(self):
        """Test portal-specific configurations."""
        # Test admin portal config
        admin_config = get_portal_csrf_config("admin")
        assert admin_config.mode == CSRFMode.HYBRID
        assert admin_config.token_delivery == CSRFTokenDelivery.BOTH
        assert admin_config.require_https is True
        
        # Test customer portal config
        customer_config = get_portal_csrf_config("customer")
        assert customer_config.mode == CSRFMode.HYBRID
        assert customer_config.token_lifetime_seconds == 7200  # Longer for customers
        
        # Test API-only portal config
        api_config = get_portal_csrf_config("api")
        assert api_config.mode == CSRFMode.API_ONLY
        assert api_config.token_delivery == CSRFTokenDelivery.HEADER_ONLY


class TestCSRFToken:
    """Test CSRF token generation and validation."""
    
    @pytest.fixture
    def csrf_token(self):
        return CSRFToken(secret_key="test-secret-key-123")
    
    def test_token_initialization(self, csrf_token):
        """Test CSRF token initialization."""
        assert csrf_token.secret_key == "test-secret-key-123"
        assert csrf_token.token_length == 32
        assert csrf_token.timestamp_tolerance == 300
    
    def test_generate_token(self, csrf_token):
        """Test token generation."""
        token = csrf_token.generate()
        assert isinstance(token, str)
        assert len(token) > 0
        # Token should be deterministic for same timestamp and secret
        assert csrf_token.generate() != token  # Different due to random component
    
    def test_validate_token_success(self, csrf_token):
        """Test successful token validation."""
        token = csrf_token.generate()
        
        # Validation should succeed immediately
        result = csrf_token.validate(token)
        assert result.valid is True
        assert result.error is None
    
    def test_validate_token_invalid_format(self, csrf_token):
        """Test validation with invalid token format."""
        result = csrf_token.validate("invalid-token")
        assert result.valid is False
        assert "Invalid token format" in result.error
    
    def test_validate_token_expired(self, csrf_token):
        """Test validation with expired token."""
        # Generate token with short lifetime
        short_lived_token = CSRFToken(
            secret_key="test-secret",
            token_lifetime=1,  # 1 second lifetime
            timestamp_tolerance=0
        )
        
        token = short_lived_token.generate()
        
        # Wait for token to expire
        time.sleep(2)
        
        result = short_lived_token.validate(token)
        assert result.valid is False
        assert "Token expired" in result.error
    
    def test_validate_token_wrong_secret(self):
        """Test validation with wrong secret key."""
        token_generator = CSRFToken(secret_key="correct-secret")
        token_validator = CSRFToken(secret_key="wrong-secret")
        
        token = token_generator.generate()
        result = token_validator.validate(token)
        
        assert result.valid is False
        assert "Invalid token signature" in result.error
    
    def test_token_binding(self, csrf_token):
        """Test token binding to specific values."""
        user_id = "user123"
        session_id = "session456"
        
        token = csrf_token.generate_bound(user_id=user_id, session_id=session_id)
        
        # Validation should succeed with correct binding
        result = csrf_token.validate_bound(token, user_id=user_id, session_id=session_id)
        assert result.valid is True
        
        # Validation should fail with wrong binding
        result = csrf_token.validate_bound(token, user_id="wrong_user", session_id=session_id)
        assert result.valid is False


class TestCSRFValidationResult:
    """Test CSRF validation result."""
    
    def test_valid_result(self):
        """Test valid CSRF result."""
        result = CSRFValidationResult(valid=True)
        assert result.valid is True
        assert result.error is None
        assert result.violation is None
    
    def test_invalid_result_with_error(self):
        """Test invalid CSRF result with error."""
        result = CSRFValidationResult(
            valid=False,
            error="Token mismatch",
            violation=CSRFViolation.TOKEN_MISMATCH
        )
        assert result.valid is False
        assert result.error == "Token mismatch"
        assert result.violation == CSRFViolation.TOKEN_MISMATCH


class TestCSRFViolation:
    """Test CSRF violation types."""
    
    def test_violation_types(self):
        """Test CSRF violation enum values."""
        assert CSRFViolation.MISSING_TOKEN == "missing_token"
        assert CSRFViolation.TOKEN_MISMATCH == "token_mismatch"
        assert CSRFViolation.TOKEN_EXPIRED == "token_expired"
        assert CSRFViolation.INVALID_ORIGIN == "invalid_origin"
        assert CSRFViolation.MISSING_REFERER == "missing_referer"


class TestUnifiedCSRFMiddleware:
    """Test UnifiedCSRFMiddleware."""
    
    @pytest.fixture
    def csrf_config(self):
        return CSRFConfig(
            mode=CSRFMode.HYBRID,
            secret_key="test-middleware-secret",
            require_https=False  # For testing
        )
    
    @pytest.fixture
    def mock_app(self):
        async def app(request):
            return Response("OK", status_code=200)
        return app
    
    @pytest.fixture
    def middleware(self, mock_app, csrf_config):
        return UnifiedCSRFMiddleware(mock_app, csrf_config)
    
    def test_middleware_initialization(self, middleware, csrf_config):
        """Test middleware initialization."""
        assert middleware.config == csrf_config
        assert middleware.token_generator is not None
        assert len(middleware.exempt_paths) > 0
    
    @pytest.mark.asyncio
    async def test_get_request_no_csrf(self, middleware):
        """Test GET request doesn't require CSRF token."""
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
        })
        
        response = await middleware.dispatch(request, lambda r: Response("OK"))
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_post_request_missing_token(self, middleware):
        """Test POST request with missing CSRF token."""
        request = Request({
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [],
        })
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, lambda r: Response("OK"))
        
        assert exc_info.value.status_code == 403
        assert "CSRF" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_post_request_valid_header_token(self, middleware):
        """Test POST request with valid CSRF token in header."""
        token = middleware.token_generator.generate()
        
        request = Request({
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [
                (b"x-csrf-token", token.encode()),
            ],
        })
        
        response = await middleware.dispatch(request, lambda r: Response("OK"))
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_post_request_valid_cookie_token(self, middleware):
        """Test POST request with valid CSRF token in cookie."""
        token = middleware.token_generator.generate()
        
        request = Request({
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [
                (b"cookie", f"csrftoken={token}".encode()),
            ],
        })
        
        # Mock form data with CSRF token
        async def mock_form():
            return FormData([("csrfmiddlewaretoken", token)])
        
        request._form = mock_form
        
        response = await middleware.dispatch(request, lambda r: Response("OK"))
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_exempt_path(self, middleware):
        """Test that exempt paths bypass CSRF protection."""
        request = Request({
            "type": "http",
            "method": "POST",
            "path": "/health",
            "headers": [],
        })
        
        response = await middleware.dispatch(request, lambda r: Response("OK"))
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_disabled_mode(self, mock_app):
        """Test middleware in disabled mode."""
        config = CSRFConfig(mode=CSRFMode.DISABLED)
        middleware = UnifiedCSRFMiddleware(mock_app, config)
        
        request = Request({
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [],
        })
        
        response = await middleware.dispatch(request, lambda r: Response("OK"))
        assert response.status_code == 200
    
    def test_is_safe_method(self, middleware):
        """Test safe method detection."""
        assert middleware.is_safe_method("GET") is True
        assert middleware.is_safe_method("HEAD") is True
        assert middleware.is_safe_method("OPTIONS") is True
        assert middleware.is_safe_method("POST") is False
        assert middleware.is_safe_method("PUT") is False
        assert middleware.is_safe_method("DELETE") is False
    
    def test_is_exempt_path(self, middleware):
        """Test exempt path detection."""
        assert middleware.is_exempt_path("/health") is True
        assert middleware.is_exempt_path("/api/health") is True
        assert middleware.is_exempt_path("/admin/login") is True
        assert middleware.is_exempt_path("/regular/path") is False
    
    def test_extract_token_from_header(self, middleware):
        """Test token extraction from header."""
        headers = Headers([("x-csrf-token", "test-token-123")])
        token = middleware.extract_token_from_header(headers)
        assert token == "test-token-123"
        
        # Test with no header
        empty_headers = Headers([])
        token = middleware.extract_token_from_header(empty_headers)
        assert token is None
    
    def test_extract_token_from_cookie(self, middleware):
        """Test token extraction from cookie."""
        headers = Headers([("cookie", "csrftoken=cookie-token-123; other=value")])
        token = middleware.extract_token_from_cookie(headers)
        assert token == "cookie-token-123"
        
        # Test with no CSRF cookie
        headers = Headers([("cookie", "other=value")])
        token = middleware.extract_token_from_cookie(headers)
        assert token is None
    
    @pytest.mark.asyncio
    async def test_extract_token_from_form(self, middleware):
        """Test token extraction from form data."""
        # Create a mock request with form data
        request = Request({
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [("content-type", "application/x-www-form-urlencoded")],
        })
        
        # Mock form method to return form with CSRF token
        async def mock_form():
            return FormData([("csrfmiddlewaretoken", "form-token-123")])
        
        request._form = mock_form
        
        token = await middleware.extract_token_from_form(request)
        assert token == "form-token-123"


class TestCSRFErrorHandling:
    """Test CSRF error handling and exceptions."""
    
    def test_csrf_error(self):
        """Test base CSRF error."""
        error = CSRFError("Test CSRF error")
        assert str(error) == "Test CSRF error"
    
    def test_csrf_token_expired_error(self):
        """Test CSRF token expired error."""
        error = CSRFTokenExpiredError("Token expired at 2024-01-01")
        assert "Token expired" in str(error)
        assert isinstance(error, CSRFError)
    
    def test_csrf_token_mismatch_error(self):
        """Test CSRF token mismatch error."""
        error = CSRFTokenMismatchError("Header token doesn't match cookie token")
        assert "mismatch" in str(error).lower()
        assert isinstance(error, CSRFError)


class TestPortalConfigurations:
    """Test portal-specific CSRF configurations."""
    
    def test_admin_portal_config(self):
        """Test admin portal CSRF configuration."""
        config = get_portal_csrf_config("admin")
        assert config.mode == CSRFMode.HYBRID
        assert config.require_https is True
        assert config.cookie_secure is True
        assert config.cookie_samesite == "Strict"
        assert config.token_lifetime_seconds == 3600
    
    def test_customer_portal_config(self):
        """Test customer portal CSRF configuration."""
        config = get_portal_csrf_config("customer")
        assert config.mode == CSRFMode.HYBRID
        assert config.token_lifetime_seconds == 7200  # Longer for customer sessions
        assert config.cookie_samesite == "Lax"  # More permissive for customer flows
    
    def test_management_portal_config(self):
        """Test management portal CSRF configuration."""
        config = get_portal_csrf_config("management")
        assert config.mode == CSRFMode.HYBRID
        assert config.require_https is True
        assert config.token_delivery == CSRFTokenDelivery.BOTH
    
    def test_reseller_portal_config(self):
        """Test reseller portal CSRF configuration."""
        config = get_portal_csrf_config("reseller")
        assert config.mode == CSRFMode.HYBRID
        assert config.token_lifetime_seconds == 3600
    
    def test_technician_portal_config(self):
        """Test technician portal CSRF configuration."""
        config = get_portal_csrf_config("technician")
        assert config.mode == CSRFMode.HYBRID
        # Technician portal might have slightly relaxed settings for mobile use
        assert config.cookie_samesite in ["Lax", "Strict"]
    
    def test_api_only_config(self):
        """Test API-only CSRF configuration."""
        config = get_portal_csrf_config("api")
        assert config.mode == CSRFMode.API_ONLY
        assert config.token_delivery == CSRFTokenDelivery.HEADER_ONLY
    
    def test_unknown_portal_config(self):
        """Test configuration for unknown portal falls back to default."""
        config = get_portal_csrf_config("unknown_portal")
        assert config.mode == CSRFMode.HYBRID  # Safe default
        assert config.require_https is True


class TestCSRFIntegrationScenarios:
    """Test CSRF integration scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_double_submit_cookie_pattern(self):
        """Test the double-submit cookie pattern."""
        config = CSRFConfig(
            mode=CSRFMode.HYBRID,
            token_delivery=CSRFTokenDelivery.BOTH,
            secret_key="integration-test-key"
        )
        
        csrf_token = CSRFToken(secret_key=config.secret_key)
        token = csrf_token.generate()
        
        # Simulate the double-submit pattern where:
        # 1. Token is in cookie
        # 2. Same token is sent in header or form
        
        # Both tokens should match
        header_token = token
        cookie_token = token
        
        assert header_token == cookie_token
        
        # Validation should pass for both
        header_result = csrf_token.validate(header_token)
        cookie_result = csrf_token.validate(cookie_token)
        
        assert header_result.valid is True
        assert cookie_result.valid is True
    
    def test_token_rotation_scenario(self):
        """Test token rotation for enhanced security."""
        csrf_token = CSRFToken(secret_key="rotation-test-key")
        
        # Generate initial token
        token1 = csrf_token.generate()
        
        # Simulate time passing
        time.sleep(1)
        
        # Generate new token
        token2 = csrf_token.generate()
        
        # Tokens should be different due to timestamp component
        assert token1 != token2
        
        # Both should still be valid (within tolerance)
        assert csrf_token.validate(token1).valid is True
        assert csrf_token.validate(token2).valid is True
    
    @pytest.mark.asyncio
    async def test_csrf_with_content_types(self):
        """Test CSRF protection with different content types."""
        config = CSRFConfig(secret_key="content-type-test")
        app = lambda request: Response("OK")
        middleware = UnifiedCSRFMiddleware(app, config)
        
        token = middleware.token_generator.generate()
        
        # Test JSON API request
        json_request = Request({
            "type": "http",
            "method": "POST",
            "path": "/api/data",
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-csrf-token", token.encode()),
            ],
        })
        
        response = await middleware.dispatch(json_request, lambda r: Response("OK"))
        assert response.status_code == 200
        
        # Test form submission
        form_request = Request({
            "type": "http",
            "method": "POST",
            "path": "/submit",
            "headers": [
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"cookie", f"csrftoken={token}".encode()),
            ],
        })
        
        # Mock form data
        async def mock_form():
            return FormData([("csrfmiddlewaretoken", token)])
        
        form_request._form = mock_form
        
        response = await middleware.dispatch(form_request, lambda r: Response("OK"))
        assert response.status_code == 200
    
    def test_csrf_logging_and_monitoring(self):
        """Test CSRF violation logging and monitoring."""
        config = CSRFConfig(secret_key="logging-test")
        csrf_token = CSRFToken(secret_key=config.secret_key)
        
        # Test successful validation logging
        token = csrf_token.generate()
        result = csrf_token.validate(token)
        assert result.valid is True
        
        # Test violation logging
        invalid_result = csrf_token.validate("invalid-token")
        assert invalid_result.valid is False
        assert invalid_result.violation is not None
        assert invalid_result.error is not None


@pytest.mark.asyncio
async def test_csrf_comprehensive_workflow():
    """Test a comprehensive CSRF protection workflow."""
    # Setup configuration for a typical web application
    config = CSRFConfig(
        mode=CSRFMode.HYBRID,
        token_delivery=CSRFTokenDelivery.BOTH,
        secret_key="comprehensive-workflow-test",
        require_https=False,  # For testing
    )
    
    # Create middleware
    app = lambda request: Response("Success")
    middleware = UnifiedCSRFMiddleware(app, config)
    
    # Step 1: GET request to obtain CSRF token (should succeed)
    get_request = Request({
        "type": "http",
        "method": "GET",
        "path": "/form",
        "headers": [],
    })
    
    get_response = await middleware.dispatch(get_request, lambda r: Response("Form"))
    assert get_response.status_code == 200
    
    # Step 2: Generate token for subsequent requests
    token = middleware.token_generator.generate()
    
    # Step 3: POST request with valid CSRF token (should succeed)
    post_request = Request({
        "type": "http",
        "method": "POST",
        "path": "/submit",
        "headers": [
            (b"x-csrf-token", token.encode()),
            (b"cookie", f"csrftoken={token}".encode()),
        ],
    })
    
    post_response = await middleware.dispatch(post_request, lambda r: Response("Success"))
    assert post_response.status_code == 200
    
    # Step 4: POST request without CSRF token (should fail)
    invalid_request = Request({
        "type": "http",
        "method": "POST",
        "path": "/submit",
        "headers": [],
    })
    
    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(invalid_request, lambda r: Response("Success"))
    
    assert exc_info.value.status_code == 403