"""Comprehensive unit tests for middleware module - 100% coverage."""

import pytest
import uuid
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from fastapi import FastAPI, Request, Response
from starlette.responses import Response as StarletteResponse

from dotmac_isp.core.middleware import (
    RequestLoggingMiddleware,
    TenantIsolationMiddleware,
    SecurityHeadersMiddleware,
    add_middleware
)


class TestRequestLoggingMiddleware:
    """Test RequestLoggingMiddleware with 100% coverage."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        app = MagicMock()
        return RequestLoggingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request for testing."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/test"
        request.client.host = "127.0.0.1"
        request.state = MagicMock()
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response for testing."""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response

    @pytest.mark.asyncio
    async def test_dispatch_success_flow(self, middleware, mock_request, mock_response):
        """Test successful request processing flow."""
        # Mock call_next function
        call_next = AsyncMock(return_value=mock_response)

        with patch('dotmac_isp.core.middleware.time.time') as mock_time, \
             patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid, \
             patch('dotmac_isp.core.middleware.logger') as mock_logger:
            
            # Setup mocks
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__.return_value = "12345678-1234-1234-1234-123456789012"
            mock_uuid.return_value.__getitem__.return_value = "12345678"
            
            mock_time.side_effect = [1000.0, 1001.5]  # Start and end time

            # Call dispatch
            result = await middleware.dispatch(mock_request, call_next)

            # Verify request ID was set
            assert mock_request.state.request_id == "12345678"

            # Verify logging calls
            assert mock_logger.info.call_count == 2
            start_log_call = mock_logger.info.call_args_list[0]
            end_log_call = mock_logger.info.call_args_list[1]

            assert "Request 12345678: GET /api/v1/test from 127.0.0.1" in start_log_call[0][0]
            assert "Request 12345678: 200 completed in 1.500s" in end_log_call[0][0]

            # Verify response headers
            assert mock_response.headers["X-Request-ID"] == "12345678"
            assert mock_response.headers["X-Process-Time"] == "1.5"

            # Verify call_next was called
            call_next.assert_called_once_with(mock_request)

            assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_with_no_client(self, middleware, mock_request, mock_response):
        """Test request processing when client is None."""
        mock_request.client = None
        call_next = AsyncMock(return_value=mock_response)

        with patch('dotmac_isp.core.middleware.time.time') as mock_time, \
             patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid, \
             patch('dotmac_isp.core.middleware.logger') as mock_logger:
            
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__.return_value = "12345678-1234-1234-1234-123456789012"
            mock_uuid.return_value.__getitem__.return_value = "abcdefgh"
            mock_time.side_effect = [1000.0, 1000.1]

            await middleware.dispatch(mock_request, call_next)

            # Should log 'unknown' for client host
            start_log_call = mock_logger.info.call_args_list[0]
            assert "from unknown" in start_log_call[0][0]

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, middleware, mock_request):
        """Test exception handling in dispatch."""
        call_next = AsyncMock(side_effect=Exception("Test exception")

        with patch('dotmac_isp.core.middleware.time.time') as mock_time, \
             patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__.return_value = "12345678-1234-1234-1234-123456789012"
            mock_uuid.return_value.__getitem__.return_value = "testid12"
            mock_time.return_value = 1000.0

            # Exception should propagate
            with pytest.raises(Exception, match="Test exception"):
                await middleware.dispatch(mock_request, call_next)

    @pytest.mark.asyncio
    async def test_uuid_string_slicing(self, middleware, mock_request, mock_response):
        """Test UUID string slicing for request ID."""
        call_next = AsyncMock(return_value=mock_response)

        with patch('dotmac_isp.core.middleware.time.time') as mock_time, \
             patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid:
            
            # Test full UUID string slicing
            mock_uuid.return_value = "12345678-1234-5678-9abc-def123456789"
            mock_time.side_effect = [1000.0, 1001.0]
            mock_response.status_code = 200
            
            await middleware.dispatch(mock_request, call_next)

            # Should use first 8 characters of UUID string
            assert mock_request.state.request_id == "12345678"

    @pytest.mark.asyncio
    async def test_timing_precision(self, middleware, mock_request, mock_response):
        """Test timing precision in logging."""
        call_next = AsyncMock(return_value=mock_response)

        with patch('dotmac_isp.core.middleware.time.time') as mock_time, \
             patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid, \
             patch('dotmac_isp.core.middleware.logger') as mock_logger:
            
            mock_uuid.return_value = "test1234"
            mock_time.side_effect = [1000.123456, 1000.987654]  # Very precise timing

            await middleware.dispatch(mock_request, call_next)

            # Check precision in process time
            end_log_call = mock_logger.info.call_args_list[1]
            assert "0.864s" in end_log_call[0][0]  # Should be rounded to 3 decimal places


class TestTenantIsolationMiddleware:
    """Test TenantIsolationMiddleware with 100% coverage."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        app = MagicMock()
        return TenantIsolationMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request for testing."""
        request = MagicMock(spec=Request)
        request.headers = MagicMock()
        request.path_params = {}
        request.state = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_dispatch_with_header_tenant_id(self, middleware, mock_request):
        """Test tenant ID extraction from headers."""
        mock_request.headers.get.return_value = "tenant-123"
        call_next = AsyncMock(return_value=MagicMock()

        with patch('dotmac_isp.core.middleware.logger') as mock_logger:
            await middleware.dispatch(mock_request, call_next)

            assert mock_request.state.tenant_id == "tenant-123"
            mock_logger.debug.assert_called_once_with("Request for tenant: tenant-123")

    @pytest.mark.asyncio
    async def test_dispatch_with_path_param_tenant_id(self, middleware, mock_request):
        """Test tenant ID extraction from path parameters."""
        mock_request.headers.get.return_value = None  # No header
        mock_request.path_params = {"tenant_id": "tenant-456"}
        call_next = AsyncMock(return_value=MagicMock()

        with patch('dotmac_isp.core.middleware.logger') as mock_logger:
            await middleware.dispatch(mock_request, call_next)

            assert mock_request.state.tenant_id == "tenant-456"
            mock_logger.debug.assert_called_once_with("Request for tenant: tenant-456")

    @pytest.mark.asyncio
    async def test_dispatch_no_tenant_id(self, middleware, mock_request):
        """Test when no tenant ID is found."""
        mock_request.headers.get.return_value = None
        mock_request.path_params = {}
        call_next = AsyncMock(return_value=MagicMock()

        with patch('dotmac_isp.core.middleware.logger') as mock_logger:
            await middleware.dispatch(mock_request, call_next)

            assert mock_request.state.tenant_id is None
            # Should not log tenant context when no tenant ID
            mock_logger.debug.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_header_priority_over_path(self, middleware, mock_request):
        """Test that header tenant ID takes priority over path parameter."""
        mock_request.headers.get.return_value = "header-tenant"
        mock_request.path_params = {"tenant_id": "path-tenant"}
        call_next = AsyncMock(return_value=MagicMock()

        await middleware.dispatch(mock_request, call_next)

        # Header should take priority
        assert mock_request.state.tenant_id == "header-tenant"

    @pytest.mark.asyncio
    async def test_dispatch_path_params_no_get_method(self, middleware, mock_request):
        """Test when path_params doesn't have get method."""
        mock_request.headers.get.return_value = None
        mock_request.path_params = "not-a-dict"  # No get method
        call_next = AsyncMock(return_value=MagicMock()

        await middleware.dispatch(mock_request, call_next)

        # Should handle gracefully and set to None
        assert mock_request.state.tenant_id is None

    @pytest.mark.asyncio
    async def test_dispatch_exception_propagation(self, middleware, mock_request):
        """Test that exceptions from call_next are propagated."""
        mock_request.headers.get.return_value = "tenant-123"
        call_next = AsyncMock(side_effect=Exception("Downstream error")

        with pytest.raises(Exception, match="Downstream error"):
            await middleware.dispatch(mock_request, call_next)

        # Tenant ID should still be set before exception
        assert mock_request.state.tenant_id == "tenant-123"


class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware with 100% coverage."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        app = MagicMock()
        return SecurityHeadersMiddleware(app)

    @pytest.fixture
    def mock_response(self):
        """Create mock response for testing."""
        response = MagicMock(spec=Response)
        response.headers = {}
        return response

    @pytest.mark.asyncio
    async def test_dispatch_adds_security_headers(self, middleware, mock_response):
        """Test that all security headers are added."""
        mock_request = MagicMock(spec=Request)
        call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, call_next)

        # Verify all security headers are set
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }

        for header, value in expected_headers.items():
            assert mock_response.headers[header] == value

        assert result == mock_response
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_preserves_existing_headers(self, middleware, mock_response):
        """Test that existing headers are preserved."""
        mock_request = MagicMock(spec=Request)
        call_next = AsyncMock(return_value=mock_response)

        # Pre-existing headers
        mock_response.headers = {"Content-Type": "application/json"}

        await middleware.dispatch(mock_request, call_next)

        # Should preserve existing header
        assert mock_response.headers["Content-Type"] == "application/json"
        # And add security headers
        assert mock_response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_dispatch_overwrites_security_headers(self, middleware, mock_response):
        """Test that security headers overwrite existing ones."""
        mock_request = MagicMock(spec=Request)
        call_next = AsyncMock(return_value=mock_response)

        # Pre-existing security header with different value
        mock_response.headers = {"X-Frame-Options": "SAMEORIGIN"}

        await middleware.dispatch(mock_request, call_next)

        # Should overwrite with our value
        assert mock_response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_dispatch_exception_propagation(self, middleware):
        """Test that exceptions from call_next are propagated."""
        mock_request = MagicMock(spec=Request)
        call_next = AsyncMock(side_effect=Exception("Downstream error")

        with pytest.raises(Exception, match="Downstream error"):
            await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_with_different_response_types(self, middleware):
        """Test with different response types."""
        mock_request = MagicMock(spec=Request)
        
        # Test with Starlette Response
        starlette_response = MagicMock(spec=StarletteResponse)
        starlette_response.headers = {}
        call_next = AsyncMock(return_value=starlette_response)

        result = await middleware.dispatch(mock_request, call_next)

        # Should work with any response type that has headers
        assert starlette_response.headers["X-Content-Type-Options"] == "nosniff"
        assert result == starlette_response


class TestAddMiddleware:
    """Test add_middleware function with 100% coverage."""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app for testing."""
        app = MagicMock(spec=FastAPI)
        return app

    def test_add_middleware_success(self, mock_app):
        """Test successful middleware addition."""
        with patch('dotmac_isp.core.middleware.logger') as mock_logger:
            add_middleware(mock_app)

            # Verify all middleware classes are added in correct order
            expected_calls = [
                call(SecurityHeadersMiddleware),
                call(TenantIsolationMiddleware),
                call(RequestLoggingMiddleware)
            ]
            
            mock_app.add_middleware.assert_has_calls(expected_calls)
            
            # Verify logging
            mock_logger.info.assert_has_calls([
                call("Adding custom middleware..."),
                call("Custom middleware added successfully")
            ])

    def test_add_middleware_order(self, mock_app):
        """Test middleware is added in correct order (reverse execution order)."""
        add_middleware(mock_app)

        # Should add in reverse order of execution
        call_args_list = [call[0][0] for call in mock_app.add_middleware.call_args_list]
        
        assert call_args_list[0] == SecurityHeadersMiddleware  # Last to execute
        assert call_args_list[1] == TenantIsolationMiddleware  # Middle
        assert call_args_list[2] == RequestLoggingMiddleware   # First to execute

    def test_add_middleware_exception_handling(self, mock_app):
        """Test middleware addition with exception."""
        mock_app.add_middleware.side_effect = Exception("Middleware error")

        # Exception should propagate (no try-catch in add_middleware)
        with pytest.raises(Exception, match="Middleware error"):
            add_middleware(mock_app)

    def test_add_middleware_with_none_app(self):
        """Test add_middleware with None app."""
        # Should raise AttributeError when trying to call add_middleware on None
        with pytest.raises(AttributeError):
            add_middleware(None)

    def test_add_middleware_logging_calls(self, mock_app):
        """Test logging calls in add_middleware."""
        with patch('dotmac_isp.core.middleware.logger') as mock_logger:
            add_middleware(mock_app)

            # Should log start and completion
            assert mock_logger.info.call_count == 2
            start_call = mock_logger.info.call_args_list[0]
            end_call = mock_logger.info.call_args_list[1]

            assert "Adding custom middleware..." in start_call[0][0]
            assert "Custom middleware added successfully" in end_call[0][0]


class TestMiddlewareIntegration:
    """Test middleware integration and edge cases."""

    @pytest.mark.asyncio
    async def test_multiple_middleware_interaction(self):
        """Test interaction between multiple middleware."""
        app = MagicMock()
        
        # Create middleware stack
        security_middleware = SecurityHeadersMiddleware(app)
        tenant_middleware = TenantIsolationMiddleware(app)
        logging_middleware = RequestLoggingMiddleware(app)

        # Create mock request and response
        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/tenants/123/users"
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"X-Tenant-ID": "tenant-123"}
        mock_request.path_params = {}
        mock_request.state = MagicMock()

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 201
        mock_response.headers = {}

        # Mock final call_next
        final_call_next = AsyncMock(return_value=mock_response)

        with patch('dotmac_isp.core.middleware.time.time') as mock_time, \
             patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid, \
             patch('dotmac_isp.core.middleware.logger'):
            
            mock_uuid.return_value = "test-uuid-1234-5678"  # 8+ character UUID
            mock_time.side_effect = [1000.0, 1001.0]

            # Execute middleware stack (in reverse order as they would be executed)
            result = await logging_middleware.dispatch(mock_request, 
                lambda req: tenant_middleware.dispatch(req,
                    lambda req: security_middleware.dispatch(req, final_call_next))

            # Verify all middleware effects (UUID is sliced to first 8 chars)
            assert mock_request.state.request_id == "test-uui"  # First 8 chars of mock UUID
            assert mock_request.state.tenant_id == "tenant-123"
            assert mock_response.headers["X-Content-Type-Options"] == "nosniff"
            assert mock_response.headers["X-Request-ID"] == "test-uui"
            assert result == mock_response

    def test_middleware_class_inheritance(self):
        """Test middleware class inheritance from BaseHTTPMiddleware."""
        from starlette.middleware.base import BaseHTTPMiddleware
        
        assert issubclass(RequestLoggingMiddleware, BaseHTTPMiddleware)
        assert issubclass(TenantIsolationMiddleware, BaseHTTPMiddleware)
        assert issubclass(SecurityHeadersMiddleware, BaseHTTPMiddleware)

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        app = MagicMock()
        
        # All middleware should initialize without error
        RequestLoggingMiddleware(app)
        TenantIsolationMiddleware(app)
        SecurityHeadersMiddleware(app)

    @pytest.mark.asyncio
    async def test_request_state_persistence(self):
        """Test that request state persists across middleware."""
        app = MagicMock()
        middleware = TenantIsolationMiddleware(app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Tenant-ID": "persistent-tenant"}
        mock_request.path_params = {}
        mock_request.state = MagicMock()

        async def verify_state(request):
            """Verify State operation."""
            # State should be available in downstream handler
            assert request.state.tenant_id == "persistent-tenant"
            return MagicMock()

        await middleware.dispatch(mock_request, verify_state)


class TestMiddlewareErrorCases:
    """Test error cases and edge conditions."""

    @pytest.mark.asyncio
    async def test_request_with_missing_attributes(self):
        """Test middleware with request missing expected attributes."""
        app = MagicMock()
        middleware = RequestLoggingMiddleware(app)
        
        # Mock request with missing attributes
        mock_request = MagicMock()
        del mock_request.method  # Remove method attribute
        mock_request.url.path = "/test"
        mock_request.client = None
        mock_request.state = MagicMock()

        call_next = AsyncMock(return_value=MagicMock()

        with patch('dotmac_isp.core.middleware.uuid.uuid4') as mock_uuid, \
             patch('dotmac_isp.core.middleware.time.time'):
            mock_uuid.return_value = "test-id"
            
            # Should handle gracefully even with missing attributes
            with pytest.raises(AttributeError):
                await middleware.dispatch(mock_request, call_next)

    @pytest.mark.asyncio
    async def test_response_with_immutable_headers(self):
        """Test security middleware with response that can't modify headers."""
        app = MagicMock()
        middleware = SecurityHeadersMiddleware(app)
        
        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock()
        # Make headers assignment raise exception
        mock_response.headers.__setitem__ = MagicMock(side_effect=Exception("Immutable headers")
        
        call_next = AsyncMock(return_value=mock_response)

        # Should propagate the exception
        with pytest.raises(Exception, match="Immutable headers"):
            await middleware.dispatch(mock_request, call_next)

    @pytest.mark.asyncio
    async def test_tenant_middleware_with_complex_path_params(self):
        """Test tenant middleware with various path parameter structures."""
        app = MagicMock()
        middleware = TenantIsolationMiddleware(app)
        
        test_cases = [
            # Normal case
            ({"tenant_id": "normal-tenant"}, "normal-tenant"),
            # Empty path params
            ({}, None),
            # Path params with no tenant_id
            ({"user_id": "123"}, None),
            # None path params (handled by attribute error)
            (None, None),
        ]

        for path_params, expected_tenant_id in test_cases:
            mock_request = MagicMock(spec=Request)
            mock_request.headers = MagicMock()
            mock_request.headers.get.return_value = None
            mock_request.path_params = path_params
            mock_request.state = MagicMock()

            call_next = AsyncMock(return_value=MagicMock()

            if path_params is None:
                # Should handle gracefully when path_params is None
                mock_request.path_params = None
                
            await middleware.dispatch(mock_request, call_next)
            
            if path_params is not None:
                assert mock_request.state.tenant_id == expected_tenant_id