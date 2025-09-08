"""
Unit tests for dotmac_shared_core.exceptions module.
"""

import pytest

from dotmac_shared_core.exceptions import (
    ConflictError,
    CoreError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
    to_dict,
)


class TestCoreError:
    """Test the base CoreError class."""

    def test_basic_creation(self):
        """Test basic error creation with message and code."""
        error = CoreError("Something went wrong", "GENERIC_ERROR")

        assert error.message == "Something went wrong"
        assert error.error_code == "GENERIC_ERROR"
        assert error.details is None
        assert str(error) == "Something went wrong"

    def test_creation_with_details(self):
        """Test error creation with additional details."""
        details = {"field": "name", "value": "invalid"}
        error = CoreError("Validation failed", "VALIDATION_ERROR", details)

        assert error.message == "Validation failed"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.details == details

    def test_to_dict_basic(self):
        """Test error serialization without details."""
        error = CoreError("Test error", "TEST_CODE")
        result = error.to_dict()

        expected = {
            "message": "Test error",
            "error_code": "TEST_CODE",
            "details": None
        }
        assert result == expected

    def test_to_dict_with_details(self):
        """Test error serialization with details."""
        details = {"field": "email", "reason": "invalid format"}
        error = CoreError("Invalid input", "INVALID_INPUT", details)
        result = error.to_dict()

        expected = {
            "message": "Invalid input",
            "error_code": "INVALID_INPUT",
            "details": details
        }
        assert result == expected

    def test_inheritance_chain(self):
        """Test that CoreError inherits from Exception."""
        error = CoreError("Test", "CODE")
        assert isinstance(error, Exception)


class TestValidationError:
    """Test ValidationError specific functionality."""

    def test_default_code(self):
        """Test ValidationError uses correct default code."""
        error = ValidationError("Invalid data")
        assert error.error_code == "VALIDATION_ERROR"

    def test_custom_code(self):
        """Test ValidationError with custom code."""
        error = ValidationError("Invalid email", "INVALID_EMAIL")
        assert error.error_code == "INVALID_EMAIL"

    def test_with_details(self):
        """Test ValidationError with validation details."""
        details = {"field": "age", "expected": ">= 18", "actual": 15}
        error = ValidationError("Age validation failed", "AGE_INVALID", details)

        assert error.message == "Age validation failed"
        assert error.error_code == "AGE_INVALID"
        assert error.details == details


class TestNotFoundError:
    """Test NotFoundError specific functionality."""

    def test_default_code(self):
        """Test NotFoundError uses correct default code."""
        error = NotFoundError("Resource not found")
        assert error.error_code == "NOT_FOUND"

    def test_with_resource_info(self):
        """Test NotFoundError with resource details."""
        details = {"resource_type": "user", "resource_id": "12345"}
        error = NotFoundError("User not found", details=details)

        assert error.message == "User not found"
        assert error.details == details


class TestConflictError:
    """Test ConflictError specific functionality."""

    def test_default_code(self):
        """Test ConflictError uses correct default code."""
        error = ConflictError("Resource already exists")
        assert error.error_code == "CONFLICT"

    def test_with_conflict_info(self):
        """Test ConflictError with conflict details."""
        details = {"field": "email", "existing_value": "test@example.com"}
        error = ConflictError("Email already registered", details=details)

        assert error.message == "Email already registered"
        assert error.details == details


class TestUnauthorizedError:
    """Test UnauthorizedError specific functionality."""

    def test_default_code(self):
        """Test UnauthorizedError uses correct default code."""
        error = UnauthorizedError("Authentication required")
        assert error.error_code == "UNAUTHORIZED"


class TestForbiddenError:
    """Test ForbiddenError specific functionality."""

    def test_default_code(self):
        """Test ForbiddenError uses correct default code."""
        error = ForbiddenError("Access denied")
        assert error.error_code == "FORBIDDEN"


class TestExternalServiceError:
    """Test ExternalServiceError specific functionality."""

    def test_default_code(self):
        """Test ExternalServiceError uses correct default code."""
        error = ExternalServiceError("API unavailable")
        assert error.error_code == "EXTERNAL_SERVICE_ERROR"

    def test_with_service_info(self):
        """Test ExternalServiceError with service details."""
        details = {"service": "payment-api", "status_code": 503}
        error = ExternalServiceError("Payment service unavailable", details=details)

        assert error.message == "Payment service unavailable"
        assert error.details == details


class TestTimeoutError:
    """Test TimeoutError specific functionality."""

    def test_default_code(self):
        """Test TimeoutError uses correct default code."""
        error = TimeoutError("Operation timed out")
        assert error.error_code == "TIMEOUT"

    def test_with_timeout_info(self):
        """Test TimeoutError with timeout details."""
        details = {"operation": "database_query", "timeout_seconds": 30}
        error = TimeoutError("Database query timed out", details=details)

        assert error.message == "Database query timed out"
        assert error.details == details


class TestToDictFunction:
    """Test the standalone to_dict function."""

    def test_converts_core_error(self):
        """Test to_dict function with CoreError instance."""
        error = ValidationError("Invalid input", "INVALID", {"field": "name"})
        result = to_dict(error)

        expected = {
            "message": "Invalid input",
            "error_code": "INVALID",
            "details": {"field": "name"}
        }
        assert result == expected

    def test_converts_regular_exception(self):
        """Test to_dict function with regular Exception."""
        error = ValueError("Standard error")
        result = to_dict(error)

        expected = {
            "message": "Standard error",
            "error_code": "UNKNOWN_ERROR",
            "details": None
        }
        assert result == expected

    def test_converts_exception_with_no_message(self):
        """Test to_dict function with exception that has no message."""
        error = RuntimeError()
        result = to_dict(error)

        expected = {
            "message": "",
            "error_code": "UNKNOWN_ERROR",
            "details": None
        }
        assert result == expected


class TestErrorRaising:
    """Test that errors can be properly raised and caught."""

    def test_raise_and_catch_core_error(self):
        """Test raising and catching CoreError."""
        with pytest.raises(CoreError) as exc_info:
            raise CoreError("Test error", "TEST")

        assert exc_info.value.message == "Test error"
        assert exc_info.value.error_code == "TEST"

    def test_raise_and_catch_validation_error(self):
        """Test raising and catching ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid data")

        assert exc_info.value.message == "Invalid data"
        assert exc_info.value.error_code == "VALIDATION_ERROR"

    def test_catch_as_base_exception(self):
        """Test catching specific error as base CoreError."""
        with pytest.raises(CoreError) as exc_info:
            raise NotFoundError("Resource missing")

        assert exc_info.value.message == "Resource missing"
        assert exc_info.value.error_code == "NOT_FOUND"
