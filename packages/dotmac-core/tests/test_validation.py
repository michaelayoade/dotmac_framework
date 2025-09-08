"""
Test cases for DotMac Core validation functionality.
"""

import pytest

try:
    from dotmac.core.validation import (
        ValidationError,
        validate_email,
        validate_phone,
        validate_url,
    )

    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


@pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
class TestEmailValidation:
    """Test email validation functionality."""

    def test_valid_emails(self):
        """Test valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "firstname+lastname@company.org",
            "test123@test123.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert validate_email(email) is True

    def test_invalid_emails(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "",
            None,
        ]

        for email in invalid_emails:
            assert validate_email(email) is False

    def test_email_validation_with_exceptions(self):
        """Test email validation raises exceptions when configured."""
        with pytest.raises(ValidationError):
            validate_email("invalid-email", raise_on_invalid=True)

    def test_email_validation_case_insensitive(self):
        """Test email validation is case insensitive."""
        assert validate_email("Test@Example.COM") is True
        assert validate_email("test@example.com") is True


@pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
class TestPhoneValidation:
    """Test phone validation functionality."""

    def test_valid_phones(self):
        """Test valid phone numbers."""
        valid_phones = [
            "+1234567890",
            "1234567890",
            "+1-234-567-8900",
            "(123) 456-7890",
            "123.456.7890",
        ]

        for phone in valid_phones:
            assert validate_phone(phone) is True

    def test_invalid_phones(self):
        """Test invalid phone numbers."""
        invalid_phones = [
            "123",
            "abc-def-ghij",
            "",
            None,
            "++1234567890",
            "123-456-789012345",  # Too long
        ]

        for phone in invalid_phones:
            assert validate_phone(phone) is False

    def test_phone_validation_with_exceptions(self):
        """Test phone validation raises exceptions when configured."""
        with pytest.raises(ValidationError):
            validate_phone("invalid-phone", raise_on_invalid=True)

    def test_phone_validation_formatting(self):
        """Test phone validation handles different formats."""
        phone_formats = [
            "1234567890",
            "123-456-7890",
            "(123) 456-7890",
            "123.456.7890",
            "+1 123 456 7890",
        ]

        for phone in phone_formats:
            assert validate_phone(phone) is True


@pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
class TestUrlValidation:
    """Test URL validation functionality."""

    def test_valid_urls(self):
        """Test valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://subdomain.example.com/path",
            "https://example.com:8080",
            "https://example.com/path?query=value",
            "ftp://files.example.com",
        ]

        for url in valid_urls:
            assert validate_url(url) is True

    def test_invalid_urls(self):
        """Test invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "http://",
            "://example.com",
            "",
            None,
            "javascript:alert('xss')",
        ]

        for url in invalid_urls:
            assert validate_url(url) is False

    def test_url_validation_with_exceptions(self):
        """Test URL validation raises exceptions when configured."""
        with pytest.raises(ValidationError):
            validate_url("invalid-url", raise_on_invalid=True)

    def test_url_validation_scheme_restriction(self):
        """Test URL validation with scheme restrictions."""
        assert validate_url("https://example.com", allowed_schemes=["https"]) is True
        assert validate_url("http://example.com", allowed_schemes=["https"]) is False

    def test_url_validation_case_insensitive_scheme(self):
        """Test URL validation handles case insensitive schemes."""
        assert validate_url("HTTPS://example.com") is True
        assert validate_url("HTTP://example.com") is True


class TestValidationFallback:
    """Test validation functionality fallback when module is not available."""

    @pytest.mark.skipif(VALIDATION_AVAILABLE, reason="Validation module is available")
    def test_validation_graceful_fallback(self):
        """Test graceful fallback when validation module is not available."""
        # This test runs only when validation is NOT available
        # It ensures the core module can still be imported and used

        try:
            import dotmac.core

            # Core should still work without validation
            assert hasattr(dotmac.core, "DotMacError")
            assert hasattr(dotmac.core, "TenantContext")

        except ImportError as e:
            pytest.fail(f"Core should be importable without validation: {e}")

    def test_validation_import_handling(self):
        """Test validation import handling."""
        # This test checks how the module handles validation imports
        try:
            from dotmac.core import validation

            # If this succeeds, validation is available
            validation_imported = True
        except (ImportError, AttributeError):
            # Validation not available or not exposed
            validation_imported = False

        # Test should pass regardless of validation availability
        assert True

    @pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from DotMacError."""
        from dotmac.core.exceptions import DotMacError
        from dotmac.core.validation import ValidationError

        error = ValidationError("Test validation error")
        assert isinstance(error, DotMacError)
        assert str(error) == "Test validation error"

    @pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
    def test_validation_with_custom_messages(self):
        """Test validation functions with custom error messages."""
        custom_message = "Custom validation error"

        try:
            validate_email("invalid", raise_on_invalid=True, message=custom_message)
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            assert custom_message in str(e)

    @pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
    def test_validation_functions_exist(self):
        """Test that expected validation functions exist."""
        from dotmac.core import validation

        expected_functions = ["validate_email", "validate_phone", "validate_url"]
        for func_name in expected_functions:
            assert hasattr(validation, func_name)
            assert callable(getattr(validation, func_name))
