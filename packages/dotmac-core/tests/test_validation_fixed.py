"""
Comprehensive test coverage for validation.py module.
This addresses the 0% coverage issue and provides complete validation testing.
"""

import pytest

from dotmac.core.validation import CommonValidators
from dotmac.core import ValidationError


class TestCommonValidators:
    """Test suite for CommonValidators class."""

    class TestEmailValidation:
        """Test email validation functionality."""

        def test_valid_emails(self):
            """Test various valid email formats."""
            valid_emails = [
                "test@gmail.com",
                "user+tag@yahoo.co.uk", 
                "first.last@outlook.com",
                "123@hotmail.com",
                "test@protonmail.com",
            ]
            
            for email in valid_emails:
                result = CommonValidators.validate_email_address(email)
                assert result == email.lower()  # Should normalize to lowercase

        def test_email_normalization(self):
            """Test email validation (preserves original case)."""
            # Email validator preserves case, doesn't normalize
            result = CommonValidators.validate_email_address("TEST@GMAIL.COM")
            assert result == "TEST@gmail.com"  # Domain is lowercased by email-validator
            
            # Test with mixed case
            result = CommonValidators.validate_email_address("User.Test@Yahoo.Com")
            assert result == "User.Test@yahoo.com"  # Domain is lowercased

        def test_invalid_emails(self):
            """Test various invalid email formats."""
            invalid_emails = [
                "",  # Empty string
                "invalid",  # No @ symbol
                "@example.com",  # Missing local part
                "user@",  # Missing domain
                "user@.com",  # Invalid domain
                "user space@example.com",  # Space in local part
                "user@example",  # Missing TLD
                "user@@example.com",  # Double @ symbol
            ]
            
            for email in invalid_emails:
                with pytest.raises(ValidationError, match="Invalid email address"):
                    CommonValidators.validate_email_address(email)

    class TestSubdomainValidation:
        """Test subdomain validation functionality."""

        def test_valid_subdomains(self):
            """Test various valid subdomain formats."""
            valid_subdomains = [
                "app",
                "my-app", 
                "app123",
                "123app",
                "very-long-subdomain-name-that-is-still-valid",
                "a",  # Single character
            ]
            
            for subdomain in valid_subdomains:
                result = CommonValidators.validate_subdomain(subdomain)
                assert result == subdomain.lower()

        def test_subdomain_normalization(self):
            """Test subdomain normalization (lowercase, trimming)."""
            result = CommonValidators.validate_subdomain("  MY-APP  ")
            assert result == "my-app"
            
            result = CommonValidators.validate_subdomain("UPPERCASE")
            assert result == "uppercase"

        def test_invalid_subdomains(self):
            """Test various invalid subdomain formats."""
            invalid_subdomains = [
                "",  # Empty string
                "-app",  # Starts with hyphen
                "app-",  # Ends with hyphen
                "app_underscore",  # Contains underscore
                "app space",  # Contains space
                "app.dot",  # Contains dot
                "app@symbol",  # Contains @ symbol
            ]
            
            for subdomain in invalid_subdomains:
                with pytest.raises(ValidationError):
                    CommonValidators.validate_subdomain(subdomain)

        def test_subdomain_length_limits(self):
            """Test subdomain length validation."""
            # Valid length (63 chars)
            valid_subdomain = "a" * 63
            result = CommonValidators.validate_subdomain(valid_subdomain)
            assert result == valid_subdomain
            
            # Too long (64 chars) - fails pattern check first since pattern limits to 63
            too_long = "a" * 64
            with pytest.raises(ValidationError, match="must contain only lowercase letters"):
                CommonValidators.validate_subdomain(too_long)

        def test_reserved_subdomains(self):
            """Test rejection of reserved subdomain names."""
            reserved_subdomains = ["www", "api", "admin", "mail", "ftp", "localhost"]
            
            for subdomain in reserved_subdomains:
                with pytest.raises(ValidationError, match=f"Subdomain '{subdomain}' is reserved"):
                    CommonValidators.validate_subdomain(subdomain)

    class TestTenantIdValidation:
        """Test tenant ID validation functionality."""

        def test_valid_tenant_ids(self):
            """Test various valid tenant ID formats."""
            valid_tenant_ids = [
                "abc",  # Minimum length
                "my-tenant",
                "tenant123", 
                "123tenant",
                "my_tenant_with_underscores",
                "tenant-with-hyphens-123",
                "a" * 32,  # Maximum length
            ]
            
            for tenant_id in valid_tenant_ids:
                result = CommonValidators.validate_tenant_id(tenant_id)
                assert result == tenant_id.lower()

        def test_tenant_id_normalization(self):
            """Test tenant ID normalization."""
            result = CommonValidators.validate_tenant_id("  MY-TENANT  ")
            assert result == "my-tenant"

        def test_invalid_tenant_ids(self):
            """Test various invalid tenant ID formats."""
            invalid_tenant_ids = [
                "",  # Empty string
                "ab",  # Too short (< 3 chars)
                "a" * 33,  # Too long (> 32 chars)
                "-tenant",  # Starts with hyphen
                "_tenant",  # Starts with underscore
                "tenant space",  # Contains space
                "tenant.dot",  # Contains dot
                "tenant@symbol",  # Contains @ symbol
            ]
            
            for tenant_id in invalid_tenant_ids:
                with pytest.raises(ValidationError):
                    CommonValidators.validate_tenant_id(tenant_id)

    class TestPhoneValidation:
        """Test phone number validation functionality."""

        def test_valid_phone_numbers(self):
            """Test various valid phone number formats."""
            valid_phones = [
                "1234567890",  # 10 digits
                "+1234567890",  # With country code
                "12345678901234",  # 14 digits
                "+123456789012345",  # 15 digits with +
            ]
            
            for phone in valid_phones:
                result = CommonValidators.validate_phone_number(phone)
                # Should remove all non-digits except +
                expected = phone if phone.startswith('+') else phone
                assert result == expected

        def test_phone_number_cleaning(self):
            """Test phone number cleaning functionality."""
            # Test removal of formatting characters
            result = CommonValidators.validate_phone_number("(123) 456-7890")
            assert result == "1234567890"
            
            result = CommonValidators.validate_phone_number("+1 (123) 456-7890")
            assert result == "+11234567890"
            
            result = CommonValidators.validate_phone_number("123.456.7890 ext 123")
            assert result == "1234567890123"

        def test_invalid_phone_numbers(self):
            """Test various invalid phone number formats."""
            invalid_phones = [
                "",  # Empty string
                "12345678",  # Too short (< 9 digits)
                "+12345678",  # Too short with country code  
                "abcdefghij",  # Non-numeric
                "++1234567890",  # Multiple + signs
            ]
            
            for phone in invalid_phones:
                with pytest.raises(ValidationError):
                    CommonValidators.validate_phone_number(phone)

        def test_empty_phone_number(self):
            """Test empty phone number handling."""
            with pytest.raises(ValidationError, match="Phone number cannot be empty"):
                CommonValidators.validate_phone_number("")

    class TestRequiredFieldsValidation:
        """Test required fields validation functionality."""

        def test_valid_required_fields(self):
            """Test validation with all required fields present."""
            data = {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30
            }
            required_fields = ["name", "email", "age"]
            
            # Should not raise any exception
            CommonValidators.validate_required_fields(data, required_fields)

        def test_missing_required_fields(self):
            """Test validation with missing required fields."""
            data = {
                "name": "John Doe",
                "age": 30
            }
            required_fields = ["name", "email", "age"]
            
            with pytest.raises(ValidationError, match="Missing required fields: email"):
                CommonValidators.validate_required_fields(data, required_fields)

        def test_empty_required_fields(self):
            """Test validation with empty required fields."""
            data = {
                "name": "",  # Empty string
                "email": "   ",  # Whitespace only
                "age": 30
            }
            required_fields = ["name", "email", "age"]
            
            with pytest.raises(ValidationError, match="Empty required fields: name, email"):
                CommonValidators.validate_required_fields(data, required_fields)

        def test_multiple_missing_and_empty_fields(self):
            """Test validation with both missing and empty fields."""
            data = {
                "name": "",  # Empty
                # email missing
                "age": 30
            }
            required_fields = ["name", "email", "phone"]
            
            with pytest.raises(ValidationError) as exc_info:
                CommonValidators.validate_required_fields(data, required_fields)
            
            error_msg = str(exc_info.value)
            assert "Missing required fields" in error_msg
            assert "Empty required fields" in error_msg

    class TestStringLengthValidation:
        """Test string length validation functionality."""

        def test_valid_string_lengths(self):
            """Test validation with valid string lengths."""
            # Valid with min and max
            CommonValidators.validate_string_length("hello", "greeting", min_length=3, max_length=10)
            
            # Valid with min only
            CommonValidators.validate_string_length("hello world", "message", min_length=5)
            
            # Valid with max only  
            CommonValidators.validate_string_length("hi", "greeting", max_length=10)
            
            # Valid with no constraints
            CommonValidators.validate_string_length("any length string", "message")

        def test_string_too_short(self):
            """Test validation with string too short."""
            with pytest.raises(ValidationError, match="greeting must be at least 5 characters long"):
                CommonValidators.validate_string_length("hi", "greeting", min_length=5)

        def test_string_too_long(self):
            """Test validation with string too long."""
            with pytest.raises(ValidationError, match="greeting cannot exceed 3 characters"):
                CommonValidators.validate_string_length("hello", "greeting", max_length=3)

        def test_string_length_edge_cases(self):
            """Test edge cases for string length validation."""
            # Exactly at minimum length
            CommonValidators.validate_string_length("hello", "greeting", min_length=5)
            
            # Exactly at maximum length
            CommonValidators.validate_string_length("hello", "greeting", max_length=5)
            
            # Empty string with no constraints
            CommonValidators.validate_string_length("", "message")
            
            # Empty string with min_length=0
            CommonValidators.validate_string_length("", "message", min_length=0)


class TestValidationPatterns:
    """Test the regex patterns used in validation."""

    def test_subdomain_pattern(self):
        """Test the subdomain regex pattern directly."""
        pattern = CommonValidators.SUBDOMAIN_PATTERN
        
        # Valid cases
        assert pattern.match("app")
        assert pattern.match("my-app")
        assert pattern.match("app123")
        assert pattern.match("123app")
        
        # Invalid cases
        assert not pattern.match("-app")  # Starts with hyphen
        assert not pattern.match("app-")  # Ends with hyphen
        assert not pattern.match("app_test")  # Contains underscore
        assert not pattern.match("")  # Empty

    def test_tenant_id_pattern(self):
        """Test the tenant ID regex pattern directly."""
        pattern = CommonValidators.TENANT_ID_PATTERN
        
        # Valid cases
        assert pattern.match("abc")
        assert pattern.match("my-tenant")
        assert pattern.match("tenant_123")
        assert pattern.match("123tenant")
        
        # Invalid cases
        assert not pattern.match("-tenant")  # Starts with hyphen
        assert not pattern.match("ab")  # Too short
        assert not pattern.match("a" * 33)  # Too long

    def test_phone_pattern(self):
        """Test the phone regex pattern directly."""
        pattern = CommonValidators.PHONE_PATTERN
        
        # Valid cases  
        assert pattern.match("1234567890")  # 10 digits
        assert pattern.match("+1234567890")  # With +
        assert pattern.match("123456789")  # 9 digits (minimum)
        assert pattern.match("123456789012345")  # 15 digits (maximum)
        
        # Invalid cases
        assert not pattern.match("12345678")  # 8 digits (too short)
        assert not pattern.match("12345678901234567")  # 17 digits (too long)
        assert not pattern.match("abcdefghij")  # Non-numeric
        assert not pattern.match("++1234567890")  # Multiple + signs