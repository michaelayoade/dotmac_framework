"""
Comprehensive test cases for DotMac Core validation functionality.
"""

import pytest

from dotmac.core.exceptions import ValidationError

try:
    from dotmac.core.validation import CommonValidators

    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


@pytest.mark.skipif(not VALIDATION_AVAILABLE, reason="Validation module not available")
class TestCommonValidators:
    """Test CommonValidators class comprehensively."""

    class TestEmailValidation:
        """Test email validation."""

        def test_valid_emails(self):
            """Test valid email addresses."""
            valid_emails = [
                "test@example.com",
                "user.name@domain.co.uk",
                "firstname+lastname@company.org",
                "test123@test123.com",
                "a@b.co",
                "user+tag@example.com",
                "user-name@example-domain.com",
            ]

            for email in valid_emails:
                result = CommonValidators.validate_email_address(email)
                assert result is not None
                assert "@" in result

        def test_invalid_emails(self):
            """Test invalid email addresses."""
            invalid_emails = [
                "invalid-email",
                "@example.com",
                "user@",
                "user..name@example.com",
                "user@.com",
                "",
                "user@domain",
                "user name@example.com",
                "user@domain..com",
            ]

            for email in invalid_emails:
                with pytest.raises(ValidationError) as exc_info:
                    CommonValidators.validate_email_address(email)
                assert "Invalid email address" in str(exc_info.value)

        def test_email_normalization(self):
            """Test email address normalization."""
            # Test that emails are normalized properly
            result = CommonValidators.validate_email_address("TEST@EXAMPLE.COM")
            assert result.lower() == result  # Should be normalized to lowercase

    class TestSubdomainValidation:
        """Test subdomain validation."""

        def test_valid_subdomains(self):
            """Test valid subdomains."""
            valid_subdomains = [
                "test",
                "my-company",
                "test123",
                "a",
                "valid-subdomain-name",
                "123",
                "a1b2c3",
            ]

            for subdomain in valid_subdomains:
                result = CommonValidators.validate_subdomain(subdomain)
                assert result == subdomain.lower()

        def test_invalid_subdomains(self):
            """Test invalid subdomains."""
            invalid_cases = [
                ("", "Subdomain cannot be empty"),
                ("-test", "Cannot start or end with a hyphen"),
                ("test-", "Cannot start or end with a hyphen"),
                ("test_underscore", "must contain only lowercase letters"),
                ("Test", "lowercase letters"),
                ("test.domain", "must contain only lowercase letters"),
                ("a" * 64, "cannot exceed 63 characters"),
            ]

            for subdomain, expected_error in invalid_cases:
                with pytest.raises(ValidationError) as exc_info:
                    CommonValidators.validate_subdomain(subdomain)
                assert expected_error in str(exc_info.value)

        def test_reserved_subdomains(self):
            """Test reserved subdomains are rejected."""
            reserved_subdomains = ["www", "api", "admin", "mail", "ftp", "localhost"]

            for subdomain in reserved_subdomains:
                with pytest.raises(ValidationError) as exc_info:
                    CommonValidators.validate_subdomain(subdomain)
                assert f"Subdomain '{subdomain}' is reserved" in str(exc_info.value)

        def test_subdomain_normalization(self):
            """Test subdomain normalization."""
            result = CommonValidators.validate_subdomain("  TEST  ")
            assert result == "test"

    class TestTenantIdValidation:
        """Test tenant ID validation."""

        def test_valid_tenant_ids(self):
            """Test valid tenant IDs."""
            valid_tenant_ids = [
                "abc",
                "test-tenant",
                "tenant_123",
                "a1b2c3",
                "my-company_2024",
                "t123",
                "valid-tenant-id-name-123",
            ]

            for tenant_id in valid_tenant_ids:
                result = CommonValidators.validate_tenant_id(tenant_id)
                assert result == tenant_id.lower()

        def test_invalid_tenant_ids(self):
            """Test invalid tenant IDs."""
            invalid_cases = [
                ("", "Tenant ID cannot be empty"),
                ("ab", "3-32 characters"),
                ("a" * 33, "3-32 characters"),
                ("-test", "must start with alphanumeric"),
                ("_test", "must start with alphanumeric"),
                ("test.", "contain only lowercase letters"),
                ("Test", "lowercase letters"),
                ("test space", "contain only lowercase letters"),
            ]

            for tenant_id, expected_error in invalid_cases:
                with pytest.raises(ValidationError) as exc_info:
                    CommonValidators.validate_tenant_id(tenant_id)
                assert expected_error in str(exc_info.value)

        def test_tenant_id_normalization(self):
            """Test tenant ID normalization."""
            result = CommonValidators.validate_tenant_id("  TEST-TENANT  ")
            assert result == "test-tenant"

    class TestPhoneValidation:
        """Test phone number validation."""

        def test_valid_phone_numbers(self):
            """Test valid phone numbers."""
            valid_phones = [
                "+1234567890",
                "1234567890",
                "+1-234-567-8900",
                "(123) 456-7890",
                "123.456.7890",
                "123 456 7890",
                "+44 20 7946 0958",
                "555-123-4567",
            ]

            for phone in valid_phones:
                result = CommonValidators.validate_phone_number(phone)
                assert result is not None
                # Result should only contain digits and optional +
                assert all(c.isdigit() or c == "+" for c in result)

        def test_invalid_phone_numbers(self):
            """Test invalid phone numbers."""
            invalid_cases = [
                ("", "Phone number cannot be empty"),
                ("123", "Invalid phone number format"),
                ("abc-def-ghij", "Invalid phone number format"),
                ("++1234567890", "Invalid phone number format"),
                ("123-456-789012345678", "Invalid phone number format"),
                ("12345", "Invalid phone number format"),
            ]

            for phone, expected_error in invalid_cases:
                with pytest.raises(ValidationError) as exc_info:
                    CommonValidators.validate_phone_number(phone)
                assert expected_error in str(exc_info.value)

        def test_phone_normalization(self):
            """Test phone number normalization."""
            result = CommonValidators.validate_phone_number("+1 (234) 567-8900")
            assert result == "+12345678900"

    class TestRequiredFieldsValidation:
        """Test required fields validation."""

        def test_valid_required_fields(self):
            """Test validation passes when all required fields present."""
            data = {"name": "Test User", "email": "test@example.com", "phone": "123-456-7890"}
            required_fields = ["name", "email"]

            # Should not raise an exception
            CommonValidators.validate_required_fields(data, required_fields)

        def test_missing_required_fields(self):
            """Test validation fails when required fields missing."""
            data = {"name": "Test User"}
            required_fields = ["name", "email", "phone"]

            with pytest.raises(ValidationError) as exc_info:
                CommonValidators.validate_required_fields(data, required_fields)

            error_msg = str(exc_info.value)
            assert "Missing required fields" in error_msg
            assert "email" in error_msg
            assert "phone" in error_msg

        def test_empty_required_fields(self):
            """Test validation fails when required fields empty."""
            data = {"name": "", "email": "   ", "phone": "123-456-7890"}
            required_fields = ["name", "email", "phone"]

            with pytest.raises(ValidationError) as exc_info:
                CommonValidators.validate_required_fields(data, required_fields)

            error_msg = str(exc_info.value)
            assert "Empty required fields" in error_msg
            assert "name" in error_msg
            assert "email" in error_msg

        def test_mixed_missing_and_empty_fields(self):
            """Test validation with both missing and empty fields."""
            data = {"name": "", "phone": "123-456-7890"}
            required_fields = ["name", "email", "address"]

            with pytest.raises(ValidationError) as exc_info:
                CommonValidators.validate_required_fields(data, required_fields)

            error_msg = str(exc_info.value)
            assert "Missing required fields" in error_msg
            assert "Empty required fields" in error_msg
            assert "email" in error_msg
            assert "name" in error_msg

    class TestStringLengthValidation:
        """Test string length validation."""

        def test_valid_string_lengths(self):
            """Test validation passes for valid string lengths."""
            # Should not raise exceptions
            CommonValidators.validate_string_length("hello", "test", min_length=3, max_length=10)
            CommonValidators.validate_string_length("test", "test", min_length=4)
            CommonValidators.validate_string_length("test", "test", max_length=10)
            CommonValidators.validate_string_length("test", "test")

        def test_string_too_short(self):
            """Test validation fails when string too short."""
            with pytest.raises(ValidationError) as exc_info:
                CommonValidators.validate_string_length("hi", "username", min_length=5)

            assert "username must be at least 5 characters long" in str(exc_info.value)

        def test_string_too_long(self):
            """Test validation fails when string too long."""
            long_string = "a" * 20
            with pytest.raises(ValidationError) as exc_info:
                CommonValidators.validate_string_length(long_string, "password", max_length=10)

            assert "password cannot exceed 10 characters" in str(exc_info.value)

        def test_string_length_edge_cases(self):
            """Test string length validation edge cases."""
            # Exactly minimum length
            CommonValidators.validate_string_length("hello", "test", min_length=5)

            # Exactly maximum length
            CommonValidators.validate_string_length("hello", "test", max_length=5)

            # Empty string with no constraints
            CommonValidators.validate_string_length("", "test")

        def test_string_length_with_both_constraints(self):
            """Test string length validation with both min and max."""
            # Valid length
            CommonValidators.validate_string_length("hello", "test", min_length=3, max_length=10)

            # Too short
            with pytest.raises(ValidationError):
                CommonValidators.validate_string_length("hi", "test", min_length=3, max_length=10)

            # Too long
            with pytest.raises(ValidationError):
                CommonValidators.validate_string_length(
                    "hello world!", "test", min_length=3, max_length=10
                )

    class TestPatterns:
        """Test regex patterns."""

        def test_subdomain_pattern(self):
            """Test subdomain regex pattern."""
            pattern = CommonValidators.SUBDOMAIN_PATTERN

            # Valid matches
            valid_cases = ["a", "test", "my-domain", "test123", "123test", "a1b2c3"]
            for case in valid_cases:
                assert pattern.match(case) is not None

            # Invalid matches
            invalid_cases = ["-test", "test-", "test_", "Test", "test.domain", ""]
            for case in invalid_cases:
                assert pattern.match(case) is None

        def test_tenant_id_pattern(self):
            """Test tenant ID regex pattern."""
            pattern = CommonValidators.TENANT_ID_PATTERN

            # Valid matches
            valid_cases = ["abc", "test-tenant", "tenant_123", "a1b2c3"]
            for case in valid_cases:
                assert pattern.match(case) is not None

            # Invalid matches
            invalid_cases = ["-test", "_test", "ab", "Test", "test.domain", ""]
            for case in invalid_cases:
                assert pattern.match(case) is None

        def test_phone_pattern(self):
            """Test phone regex pattern."""
            pattern = CommonValidators.PHONE_PATTERN

            # Valid matches
            valid_cases = ["1234567890", "+1234567890", "123456789", "+123456789012345"]
            for case in valid_cases:
                assert pattern.match(case) is not None

            # Invalid matches
            invalid_cases = ["123", "12345678901234567", "abc", "", "+"]
            for case in invalid_cases:
                assert pattern.match(case) is None
