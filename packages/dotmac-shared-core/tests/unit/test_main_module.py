"""
Unit tests for dotmac_shared_core main module (__init__.py).
"""

import dotmac_shared_core
from dotmac_shared_core import (
    JSON,
    ConflictError,
    CoreError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    Result,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
    common,
    ensure_in,
    ensure_range,
    exceptions,
    is_email,
    is_uuid,
    sanitize_text,
    to_dict,
    types,
    validation,
)


class TestMainModuleVersion:
    """Test module version information."""

    def test_version_available(self):
        """Test that __version__ is available."""
        assert hasattr(dotmac_shared_core, '__version__')
        assert dotmac_shared_core.__version__ == "1.0.0"

    def test_version_in_all(self):
        """Test that __version__ is in __all__ exports."""
        assert "__version__" in dotmac_shared_core.__all__


class TestMainModuleImports:
    """Test that all expected imports are available."""

    def test_submodule_imports(self):
        """Test that submodules are available."""
        assert common is not None
        assert exceptions is not None
        assert types is not None
        assert validation is not None

    def test_exception_imports(self):
        """Test that exception classes are directly importable."""
        # Test that all exception classes are available
        assert CoreError is not None
        assert ValidationError is not None
        assert NotFoundError is not None
        assert ConflictError is not None
        assert UnauthorizedError is not None
        assert ForbiddenError is not None
        assert ExternalServiceError is not None
        assert TimeoutError is not None
        assert to_dict is not None

        # Test inheritance
        assert issubclass(ValidationError, CoreError)
        assert issubclass(NotFoundError, CoreError)

    def test_type_imports(self):
        """Test that type definitions are directly importable."""
        assert JSON is not None
        assert Result is not None

    def test_validation_imports(self):
        """Test that validation functions are directly importable."""
        assert callable(is_email)
        assert callable(is_uuid)
        assert callable(ensure_in)
        assert callable(ensure_range)
        assert callable(sanitize_text)


class TestMainModuleAll:
    """Test __all__ exports."""

    def test_all_exports_complete(self):
        """Test that __all__ includes all expected exports."""
        expected_exports = {
            # Version
            "__version__",

            # Modules
            "common",
            "exceptions",
            "types",
            "validation",

            # Direct imports from exceptions
            "CoreError",
            "ValidationError",
            "NotFoundError",
            "ConflictError",
            "UnauthorizedError",
            "ForbiddenError",
            "ExternalServiceError",
            "TimeoutError",
            "to_dict",

            # Direct imports from types
            "JSON",
            "Result",

            # Direct imports from validation
            "is_email",
            "is_uuid",
            "ensure_in",
            "ensure_range",
            "sanitize_text",
        }

        actual_exports = set(dotmac_shared_core.__all__)
        assert actual_exports == expected_exports

    def test_all_exports_available(self):
        """Test that all declared exports are actually available."""
        for export_name in dotmac_shared_core.__all__:
            assert hasattr(dotmac_shared_core, export_name), f"Export {export_name} not available"


class TestMainModuleFunctionality:
    """Test basic functionality through main module imports."""

    def test_exception_functionality(self):
        """Test exception functionality through main module."""
        # Create and use exceptions
        error = ValidationError("Test error", "TEST")
        assert error.message == "Test error"
        assert error.error_code == "TEST"

        # Test to_dict function
        error_dict = to_dict(error)
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST"

    def test_validation_functionality(self):
        """Test validation functionality through main module."""
        # Test email validation
        assert is_email("test@example.com")
        assert not is_email("invalid")

        # Test UUID validation
        import uuid
        test_uuid = str(uuid.uuid4())
        assert is_uuid(test_uuid)
        assert not is_uuid("not-a-uuid")

        # Test sanitize_text
        clean = sanitize_text("clean text\x00dirty")
        assert clean == "clean textdirty"

    def test_constraint_validation_functionality(self):
        """Test constraint validation through main module."""
        # Test ensure_in - should not raise
        ensure_in("red", ["red", "green", "blue"], "color")

        # Test ensure_range - should not raise
        ensure_range(5, min_val=1, max_val=10, field="number")

    def test_types_functionality(self):
        """Test types functionality through main module."""
        # Test Result creation
        success = Result.success("test value")
        assert success.ok
        assert success.value == "test value"

        error_result = Result.failure(ValidationError("Error", "CODE"))
        assert not error_result.ok
        assert error_result.error.message == "Error"

    def test_common_module_access(self):
        """Test access to common submodules."""
        # Test that we can access submodules through main import
        uuid_obj = common.ids.new_uuid()
        assert uuid_obj is not None

        current_time = common.time.utcnow()
        assert current_time is not None

        from pathlib import Path
        safe_path = common.paths.safe_join(Path("/tmp"), "test")
        assert safe_path is not None


class TestMainModuleDocstring:
    """Test module docstring and metadata."""

    def test_module_docstring(self):
        """Test that module has descriptive docstring."""
        assert dotmac_shared_core.__doc__ is not None
        assert len(dotmac_shared_core.__doc__.strip()) > 0

        # Check that docstring contains key information
        docstring = dotmac_shared_core.__doc__
        assert "DotMac Shared Core" in docstring
        assert "foundational utilities" in docstring.lower()

    def test_module_examples_in_docstring(self):
        """Test that module docstring contains usage examples."""
        docstring = dotmac_shared_core.__doc__
        assert "Example:" in docstring
        assert ">>>" in docstring  # Contains example code


class TestMainModuleIntegration:
    """Integration tests for main module imports working together."""

    def test_full_workflow_example(self):
        """Test a complete workflow using main module imports."""
        # Generate an ID
        new_id = common.ids.new_uuid()

        # Validate and sanitize some input
        email = sanitize_text("user@example.com\x00")
        assert is_email(email)

        # Create a result
        result = Result.success({"id": str(new_id), "email": email})
        assert result.ok

        # Handle potential error case
        try:
            ensure_range(150, min_val=1, max_val=100, field="percentage")
        except ValidationError as e:
            error_result = Result.failure(e)
            assert not error_result.ok
            assert error_result.error.error_code == "VALUE_OUT_OF_RANGE"

    def test_error_handling_workflow(self):
        """Test error handling workflow using main module."""
        # Create various errors
        validation_err = ValidationError("Invalid data")
        not_found_err = NotFoundError("Resource missing")

        # Convert to dict format
        val_dict = to_dict(validation_err)
        nf_dict = to_dict(not_found_err)

        assert val_dict["error_code"] == "VALIDATION_ERROR"
        assert nf_dict["error_code"] == "NOT_FOUND"

        # Use in Results
        val_result = Result.failure(validation_err)
        nf_result = Result.failure(not_found_err)

        assert not val_result.ok
        assert not nf_result.ok

        # Test unwrap_or for error cases
        default_value = "default"
        assert val_result.unwrap_or(default_value) == default_value
        assert nf_result.unwrap_or(default_value) == default_value
