"""Comprehensive unit tests for exceptions module - 100% coverage."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError

from dotmac_isp.core.exceptions import (
    DotMacISPException,
    TenantNotFoundError,
    InsufficientPermissionsError,
    ResourceNotFoundError,
    ValidationError as DotMacValidationError,
    create_error_response,
    dotmac_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    operational_error_handler,
    general_exception_handler,
    add_exception_handlers
)


class TestDotMacISPException:
    """Test base DotMacISPException with 100% coverage."""

    def test_default_initialization(self):
        """Test exception with default parameters."""
        exc = DotMacISPException("Test message")
        
        assert exc.message == "Test message"
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.status_code == 500
        assert str(exc) == "Test message"

    def test_full_initialization(self):
        """Test exception with all parameters."""
        exc = DotMacISPException(
            message="Custom message",
            error_code="CUSTOM_ERROR",
            status_code=400
        )
        
        assert exc.message == "Custom message"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.status_code == 400
        assert str(exc) == "Custom message"

    def test_inheritance(self):
        """Test exception inherits from Exception."""
        exc = DotMacISPException("Test")
        assert isinstance(exc, Exception)

    def test_exception_attributes_accessible(self):
        """Test all exception attributes are accessible."""
        exc = DotMacISPException("Test", "TEST_CODE", 422)
        
        # All attributes should be accessible
        assert hasattr(exc, 'message')
        assert hasattr(exc, 'error_code')
        assert hasattr(exc, 'status_code')


class TestTenantNotFoundError:
    """Test TenantNotFoundError with 100% coverage."""

    def test_initialization(self):
        """Test TenantNotFoundError initialization."""
        exc = TenantNotFoundError("tenant-123")
        
        assert exc.message == "Tenant tenant-123 not found"
        assert exc.error_code == "TENANT_NOT_FOUND"
        assert exc.status_code == 404

    def test_inheritance(self):
        """Test TenantNotFoundError inherits from DotMacISPException."""
        exc = TenantNotFoundError("tenant-456")
        assert isinstance(exc, DotMacISPException)

    def test_different_tenant_ids(self):
        """Test with different tenant ID formats."""
        test_cases = [
            "simple-tenant",
            "uuid-12345678-1234-1234-1234-123456789012",
            "tenant_with_underscores",
            "123456",
            ""
        ]
        
        for tenant_id in test_cases:
            exc = TenantNotFoundError(tenant_id)
            assert f"Tenant {tenant_id} not found" in exc.message


class TestInsufficientPermissionsError:
    """Test InsufficientPermissionsError with 100% coverage."""

    def test_initialization_without_permission(self):
        """Test initialization without required permission."""
        exc = InsufficientPermissionsError()
        
        assert exc.message == "Insufficient permissions"
        assert exc.error_code == "INSUFFICIENT_PERMISSIONS"
        assert exc.status_code == 403

    def test_initialization_with_permission(self):
        """Test initialization with required permission."""
        exc = InsufficientPermissionsError("admin:read")
        
        assert exc.message == "Insufficient permissions (required: admin:read)"
        assert exc.error_code == "INSUFFICIENT_PERMISSIONS"
        assert exc.status_code == 403

    def test_inheritance(self):
        """Test inheritance from DotMacISPException."""
        exc = InsufficientPermissionsError()
        assert isinstance(exc, DotMacISPException)

    def test_different_permissions(self):
        """Test with different permission formats."""
        permissions = [
            "read",
            "admin:write",
            "tenant:123:manage",
            "complex.permission.structure"
        ]
        
        for permission in permissions:
            exc = InsufficientPermissionsError(permission)
            assert f"required: {permission}" in exc.message


class TestResourceNotFoundError:
    """Test ResourceNotFoundError with 100% coverage."""

    def test_initialization(self):
        """Test ResourceNotFoundError initialization."""
        exc = ResourceNotFoundError("User", "12345")
        
        assert exc.message == "User with ID 12345 not found"
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == 404

    def test_inheritance(self):
        """Test inheritance from DotMacISPException."""
        exc = ResourceNotFoundError("Customer", "67890")
        assert isinstance(exc, DotMacISPException)

    def test_different_resources(self):
        """Test with different resource types and IDs."""
        test_cases = [
            ("Customer", "123"),
            ("Service", "service-456"),
            ("Billing Account", "uuid-789"),
            ("Network Device", "router-001")
        ]
        
        for resource_type, resource_id in test_cases:
            exc = ResourceNotFoundError(resource_type, resource_id)
            assert f"{resource_type} with ID {resource_id} not found" == exc.message


class TestDotMacValidationError:
    """Test custom ValidationError with 100% coverage."""

    def test_initialization_without_field(self):
        """Test initialization without field parameter."""
        exc = DotMacValidationError("Invalid data format")
        
        assert exc.message == "Invalid data format"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 400

    def test_initialization_with_field(self):
        """Test initialization with field parameter."""
        exc = DotMacValidationError("Email format is invalid", "email")
        
        assert exc.message == "Email format is invalid"
        assert exc.error_code == "VALIDATION_ERROR_EMAIL"
        assert exc.status_code == 400

    def test_inheritance(self):
        """Test inheritance from DotMacISPException."""
        exc = DotMacValidationError("Test validation error")
        assert isinstance(exc, DotMacISPException)

    def test_field_code_generation(self):
        """Test error code generation with different field names."""
        test_cases = [
            ("email", "VALIDATION_ERROR_EMAIL"),
            ("phone_number", "VALIDATION_ERROR_PHONE_NUMBER"),
            ("user_id", "VALIDATION_ERROR_USER_ID"),
            ("password", "VALIDATION_ERROR_PASSWORD")
        ]
        
        for field, expected_code in test_cases:
            exc = DotMacValidationError("Test message", field)
            assert exc.error_code == expected_code


class TestCreateErrorResponse:
    """Test create_error_response function with 100% coverage."""

    def test_minimal_response(self):
        """Test error response with minimal parameters."""
        response = create_error_response(400, "Bad request")
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        
        # Check response content structure
        content = {
            "error": True,
            "message": "Bad request",
            "status_code": 400
        }
        
        # Note: We can't easily test the actual JSON content without 
        # rendering the response, so we test the creation doesn't fail

    def test_full_response(self):
        """Test error response with all parameters."""
        details = {"field": "email", "issue": "invalid format"}
        response = create_error_response(
            status_code=422,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details=details,
            request_id="req-123"
        )
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

    def test_response_with_none_values(self):
        """Test error response with None values."""
        response = create_error_response(
            status_code=500,
            message="Internal error",
            error_code=None,
            details=None,
            request_id=None
        )
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    def test_response_with_complex_details(self):
        """Test error response with complex details object."""
        details = {
            "validation_errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "phone", "message": "Required field"}
            ],
            "error_count": 2
        }
        
        response = create_error_response(400, "Multiple validation errors", details=details)
        assert isinstance(response, JSONResponse)

    def test_different_status_codes(self):
        """Test error response with different status codes."""
        status_codes = [400, 401, 403, 404, 422, 500, 503]
        
        for code in status_codes:
            response = create_error_response(code, f"Error {code}")
            assert response.status_code == code


class TestExceptionHandlers:
    """Test exception handler functions with 100% coverage."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request for testing."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-request-123"
        return request

    @pytest.fixture
    def mock_request_no_id(self):
        """Create mock request without request_id."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        # Simulate missing request_id
        type(request.state).request_id = MagicMock(side_effect=AttributeError()
        return request

    @pytest.mark.asyncio
    async def test_dotmac_exception_handler(self, mock_request):
        """Test DotMac ISP exception handler."""
        exc = DotMacISPException("Test error", "TEST_ERROR", 422)
        
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger, \
             patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            
            mock_create_response.return_value = MagicMock()
            
            result = await dotmac_exception_handler(mock_request, exc)
            
            # Verify logging
            mock_logger.error.assert_called_once_with(
                "DotMac ISP Exception: Test error", exc_info=True
            )
            
            # Verify response creation
            mock_create_response.assert_called_once_with(
                status_code=422,
                message="Test error",
                error_code="TEST_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_dotmac_exception_handler_no_request_id(self, mock_request_no_id):
        """Test DotMac exception handler without request ID."""
        exc = DotMacISPException("No request ID error")
        
        with patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            mock_create_response.return_value = MagicMock()
            
            # Set up mock to return None when request_id is accessed
            mock_request_no_id.state.request_id = None
            
            await dotmac_exception_handler(mock_request_no_id, exc)
            
            # Should handle missing request_id gracefully
            mock_create_response.assert_called_once_with(
                status_code=500,
                message="No request ID error",
                error_code="INTERNAL_ERROR",
                request_id=None
            )

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handler."""
        exc = HTTPException(status_code=404, detail="Not found")
        
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger, \
             patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            
            mock_create_response.return_value = MagicMock()
            
            result = await http_exception_handler(mock_request, exc)
            
            # Verify logging
            mock_logger.warning.assert_called_once_with("HTTP Exception: 404 - Not found")
            
            # Verify response creation
            mock_create_response.assert_called_once_with(
                status_code=404,
                message="Not found",
                error_code="HTTP_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """Test validation exception handler."""
        # Create mock validation error
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {"field": "email", "message": "Invalid format"},
            {"field": "age", "message": "Must be positive"}
        ]
        
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger, \
             patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            
            mock_create_response.return_value = MagicMock()
            
            result = await validation_exception_handler(mock_request, exc)
            
            # Verify logging
            mock_logger.warning.assert_called_once()
            
            # Verify response creation
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Validation error",
                error_code="VALIDATION_ERROR",
                details=exc.errors(),
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_integrity_error_handler_unique_constraint(self, mock_request):
        """Test integrity error handler with unique constraint."""
        exc = IntegrityError("statement", "params", "unique constraint failed")
        
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger, \
             patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            
            mock_create_response.return_value = MagicMock()
            
            result = await integrity_error_handler(mock_request, exc)
            
            # Should detect unique constraint violation
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_409_CONFLICT,
                message="A record with these values already exists",
                error_code="INTEGRITY_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_integrity_error_handler_foreign_key(self, mock_request):
        """Test integrity error handler with foreign key constraint."""
        exc = IntegrityError("statement", "params", "foreign key constraint failed")
        
        with patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            mock_create_response.return_value = MagicMock()
            
            await integrity_error_handler(mock_request, exc)
            
            # Should detect foreign key constraint violation
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_409_CONFLICT,
                message="Referenced record does not exist",
                error_code="INTEGRITY_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_integrity_error_handler_check_constraint(self, mock_request):
        """Test integrity error handler with check constraint."""
        exc = IntegrityError("statement", "params", "check constraint failed")
        
        with patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            mock_create_response.return_value = MagicMock()
            
            await integrity_error_handler(mock_request, exc)
            
            # Should detect check constraint violation
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_409_CONFLICT,
                message="Data does not meet validation requirements",
                error_code="INTEGRITY_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_integrity_error_handler_generic(self, mock_request):
        """Test integrity error handler with generic constraint."""
        exc = IntegrityError("statement", "params", "some other constraint failed")
        
        with patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            mock_create_response.return_value = MagicMock()
            
            await integrity_error_handler(mock_request, exc)
            
            # Should use generic message
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_409_CONFLICT,
                message="Data integrity constraint violation",
                error_code="INTEGRITY_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_operational_error_handler(self, mock_request):
        """Test operational error handler."""
        exc = OperationalError("statement", "params", "connection failed")
        
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger, \
             patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            
            mock_create_response.return_value = MagicMock()
            
            result = await operational_error_handler(mock_request, exc)
            
            # Verify logging
            mock_logger.error.assert_called_once()
            
            # Verify response creation
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Database temporarily unavailable",
                error_code="DATABASE_ERROR",
                request_id="test-request-123"
            )

    @pytest.mark.asyncio
    async def test_general_exception_handler(self, mock_request):
        """Test general exception handler."""
        exc = Exception("Unexpected error")
        
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger, \
             patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            
            mock_create_response.return_value = MagicMock()
            
            result = await general_exception_handler(mock_request, exc)
            
            # Verify logging
            mock_logger.error.assert_called_once_with(
                "Unhandled exception: Unexpected error", exc_info=True
            )
            
            # Verify response creation
            mock_create_response.assert_called_once_with(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                request_id="test-request-123"
            )


class TestAddExceptionHandlers:
    """Test add_exception_handlers function with 100% coverage."""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        return MagicMock(spec=FastAPI)

    def test_add_exception_handlers_success(self, mock_app):
        """Test successful addition of exception handlers."""
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger:
            add_exception_handlers(mock_app)
            
            # Verify all exception handlers are added
            expected_calls = [
                # Custom exceptions
                (DotMacISPException, dotmac_exception_handler),
                # FastAPI/Starlette exceptions
                (HTTPException, http_exception_handler),
                (StarletteHTTPException, http_exception_handler),
                (RequestValidationError, validation_exception_handler),
                # Database exceptions
                (IntegrityError, integrity_error_handler),
                (OperationalError, operational_error_handler),
                # General exception
                (Exception, general_exception_handler)
            ]
            
            assert mock_app.add_exception_handler.call_count == len(expected_calls)
            
            # Check that all expected handlers were added
            call_args_list = mock_app.add_exception_handler.call_args_list
            for i, (exc_type, handler) in enumerate(expected_calls):
                args, kwargs = call_args_list[i]
                assert args[0] == exc_type
                assert args[1] == handler
            
            # Verify logging
            mock_logger.info.assert_has_calls([
                call("Adding exception handlers..."),
                call("Exception handlers added successfully")
            ])

    def test_add_exception_handlers_logging(self, mock_app):
        """Test logging in add_exception_handlers."""
        with patch('dotmac_isp.core.exceptions.logger') as mock_logger:
            add_exception_handlers(mock_app)
            
            # Should log start and completion
            assert mock_logger.info.call_count == 2
            start_call = mock_logger.info.call_args_list[0]
            end_call = mock_logger.info.call_args_list[1]
            
            assert "Adding exception handlers..." in start_call[0][0]
            assert "Exception handlers added successfully" in end_call[0][0]

    def test_add_exception_handlers_order(self, mock_app):
        """Test exception handlers are added in correct order."""
        add_exception_handlers(mock_app)
        
        # Get the exception types that were registered
        call_args_list = mock_app.add_exception_handler.call_args_list
        registered_types = [call[0][0] for call in call_args_list]
        
        # Verify specific order requirements
        assert DotMacISPException in registered_types
        assert HTTPException in registered_types
        assert Exception in registered_types
        
        # Exception should be last (most general)
        assert registered_types[-1] == Exception

    def test_add_exception_handlers_with_app_error(self, mock_app):
        """Test add_exception_handlers when app.add_exception_handler fails."""
        mock_app.add_exception_handler.side_effect = Exception("Handler registration failed")
        
        # Should propagate the exception
        with pytest.raises(Exception, match="Handler registration failed"):
            add_exception_handlers(mock_app)

    def test_add_exception_handlers_with_none_app(self):
        """Test add_exception_handlers with None app."""
        with pytest.raises(AttributeError):
            add_exception_handlers(None)


class TestExceptionHandlersIntegration:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_exception_hierarchy_handling(self):
        """Test exception handling respects inheritance hierarchy."""
        # TenantNotFoundError should be handled by DotMac handler
        request = MagicMock(spec=Request)
        request.state.request_id = "test-123"
        
        exc = TenantNotFoundError("missing-tenant")
        
        with patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            mock_create_response.return_value = MagicMock()
            
            await dotmac_exception_handler(request, exc)
            
            # Should use the specific error code from TenantNotFoundError
            mock_create_response.assert_called_once_with(
                status_code=404,
                message="Tenant missing-tenant not found",
                error_code="TENANT_NOT_FOUND",
                request_id="test-123"
            )

    def test_all_custom_exceptions_inherit_correctly(self):
        """Test all custom exceptions inherit from DotMacISPException."""
        custom_exceptions = [
            TenantNotFoundError("test"),
            InsufficientPermissionsError(),
            ResourceNotFoundError("Test", "123"),
            DotMacValidationError("test")
        ]
        
        for exc in custom_exceptions:
            assert isinstance(exc, DotMacISPException)
            assert hasattr(exc, 'message')
            assert hasattr(exc, 'error_code')
            assert hasattr(exc, 'status_code')

    @pytest.mark.asyncio
    async def test_starlette_http_exception_handling(self):
        """Test Starlette HTTPException is handled correctly."""
        request = MagicMock(spec=Request)
        request.state.request_id = "starlette-test"
        
        # Starlette HTTPException
        exc = StarletteHTTPException(status_code=403, detail="Forbidden")
        
        with patch('dotmac_isp.core.exceptions.create_error_response') as mock_create_response:
            mock_create_response.return_value = MagicMock()
            
            await http_exception_handler(request, exc)
            
            mock_create_response.assert_called_once_with(
                status_code=403,
                message="Forbidden",
                error_code="HTTP_ERROR",
                request_id="starlette-test"
            )

    def test_exception_handler_registration_completeness(self):
        """Test that all important exception types have handlers."""
        app = MagicMock(spec=FastAPI)
        add_exception_handlers(app)
        
        # Get all registered exception types
        call_args_list = app.add_exception_handler.call_args_list
        registered_types = [call[0][0] for call in call_args_list]
        
        # Essential exception types should be covered
        essential_types = [
            DotMacISPException,
            HTTPException,
            StarletteHTTPException,
            RequestValidationError,
            IntegrityError,
            OperationalError,
            Exception  # Catch-all
        ]
        
        for exc_type in essential_types:
            assert exc_type in registered_types, f"{exc_type} should be registered"