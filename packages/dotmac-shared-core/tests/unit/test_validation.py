"""
Unit tests for dotmac_shared_core.validation module.
"""

import uuid

import pytest

from dotmac_shared_core.exceptions import ValidationError
from dotmac_shared_core.validation import (
    ensure_in,
    ensure_range,
    is_email,
    is_uuid,
    sanitize_text,
)


class TestIsEmail:
    """Test the is_email validation function."""

    def test_valid_emails(self):
        """Test various valid email formats."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.net",
            "firstname.lastname@subdomain.example.com",
            "test123@test-domain.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert is_email(email), f"Expected {email} to be valid"

    def test_invalid_emails(self):
        """Test various invalid email formats."""
        invalid_emails = [
            "invalid",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@.example.com",
            "test@example.",
            "",
            " ",
            "test@example",
            "test@@example.com",
        ]

        for email in invalid_emails:
            assert not is_email(email), f"Expected {email} to be invalid"

    def test_edge_cases(self):
        """Test edge cases for email validation."""
        assert not is_email(None)
        assert not is_email(123)
        assert not is_email([])


class TestIsUuid:
    """Test the is_uuid validation function."""

    def test_valid_uuids(self):
        """Test various valid UUID formats."""
        # Generate some real UUIDs
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid1())

        valid_uuids = [
            uuid1,
            uuid2,
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
            "12345678-1234-1234-1234-123456789012",
        ]

        for uuid_str in valid_uuids:
            assert is_uuid(uuid_str), f"Expected {uuid_str} to be valid UUID"

    def test_invalid_uuids(self):
        """Test various invalid UUID formats."""
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",  # too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # too long
            "550e8400-e29b-41d4-a716-44665544000g",  # invalid character
            "550e8400e29b41d4a716446655440000",  # no dashes
            "",
            " ",
            "12345678-1234-1234-1234-12345678901",  # one char short
        ]

        for uuid_str in invalid_uuids:
            assert not is_uuid(uuid_str), f"Expected {uuid_str} to be invalid UUID"

    def test_edge_cases(self):
        """Test edge cases for UUID validation."""
        assert not is_uuid(None)
        assert not is_uuid(123)
        assert not is_uuid([])
        assert not is_uuid(uuid.uuid4())  # UUID object, not string


class TestEnsureIn:
    """Test the ensure_in constraint validator."""

    def test_valid_values(self):
        """Test values that are in the allowed set."""
        allowed = ["red", "green", "blue"]

        # These should not raise
        ensure_in("red", allowed, "color")
        ensure_in("green", allowed, "color")
        ensure_in("blue", allowed, "color")

    def test_invalid_values(self):
        """Test values that are not in the allowed set."""
        allowed = ["red", "green", "blue"]

        with pytest.raises(ValidationError) as exc_info:
            ensure_in("yellow", allowed, "color")

        error = exc_info.value
        assert "color must be one of" in error.message
        assert "yellow" in error.message
        assert error.error_code == "VALUE_NOT_ALLOWED"
        assert error.details == {
            "field": "color",
            "value": "yellow",
            "allowed": allowed
        }

    def test_with_different_types(self):
        """Test ensure_in with different value types."""
        allowed_numbers = [1, 2, 3]
        ensure_in(2, allowed_numbers, "number")

        with pytest.raises(ValidationError):
            ensure_in(5, allowed_numbers, "number")

    def test_empty_allowed_set(self):
        """Test ensure_in with empty allowed set."""
        with pytest.raises(ValidationError):
            ensure_in("anything", [], "field")

    def test_custom_field_name(self):
        """Test ensure_in with custom field name in error."""
        allowed = ["option1", "option2"]

        with pytest.raises(ValidationError) as exc_info:
            ensure_in("bad_option", allowed, "configuration_setting")

        assert "configuration_setting must be one of" in exc_info.value.message


class TestEnsureRange:
    """Test the ensure_range constraint validator."""

    def test_valid_ranges(self):
        """Test values within valid ranges."""
        # These should not raise
        ensure_range(5, min_val=1, max_val=10, field="number")
        ensure_range(1, min_val=1, max_val=10, field="number")  # boundary
        ensure_range(10, min_val=1, max_val=10, field="number")  # boundary
        ensure_range(0, min_val=0, max_val=100, field="percentage")

    def test_below_minimum(self):
        """Test values below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            ensure_range(0, min_val=1, max_val=10, field="count")

        error = exc_info.value
        assert "count must be between 1 and 10" in error.message
        assert error.error_code == "VALUE_OUT_OF_RANGE"
        assert error.details == {
            "field": "count",
            "value": 0,
            "min_val": 1,
            "max_val": 10
        }

    def test_above_maximum(self):
        """Test values above maximum."""
        with pytest.raises(ValidationError) as exc_info:
            ensure_range(15, min_val=1, max_val=10, field="level")

        error = exc_info.value
        assert "level must be between 1 and 10" in error.message
        assert error.error_code == "VALUE_OUT_OF_RANGE"

    def test_only_minimum(self):
        """Test range validation with only minimum."""
        ensure_range(5, min_val=1, max_val=None, field="positive")
        ensure_range(100, min_val=1, max_val=None, field="positive")

        with pytest.raises(ValidationError) as exc_info:
            ensure_range(0, min_val=1, max_val=None, field="positive")

        assert "positive must be >= 1" in exc_info.value.message

    def test_only_maximum(self):
        """Test range validation with only maximum."""
        ensure_range(-5, min_val=None, max_val=10, field="bounded")
        ensure_range(5, min_val=None, max_val=10, field="bounded")

        with pytest.raises(ValidationError) as exc_info:
            ensure_range(15, min_val=None, max_val=10, field="bounded")

        assert "bounded must be <= 10" in exc_info.value.message

    def test_no_bounds(self):
        """Test range validation with no bounds (should not raise)."""
        ensure_range(-1000, min_val=None, max_val=None, field="unbounded")
        ensure_range(1000, min_val=None, max_val=None, field="unbounded")

    def test_float_values(self):
        """Test range validation with float values."""
        ensure_range(5.5, min_val=1.0, max_val=10.0, field="decimal")

        with pytest.raises(ValidationError):
            ensure_range(10.1, min_val=1.0, max_val=10.0, field="decimal")


class TestSanitizeText:
    """Test the sanitize_text utility function."""

    def test_clean_text(self):
        """Test text that needs no sanitization."""
        clean_text = "Hello, world! This is normal text."
        result = sanitize_text(clean_text)
        assert result == clean_text

    def test_control_character_removal(self):
        """Test removal of control characters."""
        # Test with various control characters
        dirty_text = "Hello\x00\x01\x02world\x08\x0c\x0e"
        result = sanitize_text(dirty_text)
        assert result == "Helloworld"

    def test_preserve_whitespace(self):
        """Test that normal whitespace is preserved."""
        text_with_whitespace = "Hello\n\t world \r\n"
        result = sanitize_text(text_with_whitespace)
        assert result == text_with_whitespace  # whitespace should be preserved

    def test_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_text("")
        assert result == ""

    def test_only_control_characters(self):
        """Test text that's only control characters."""
        control_only = "\x00\x01\x02\x03"
        result = sanitize_text(control_only)
        assert result == ""

    def test_mixed_content(self):
        """Test text with mix of normal and control characters."""
        mixed_text = "Start\x00Middle\x01End"
        result = sanitize_text(mixed_text)
        assert result == "StartMiddleEnd"

    def test_unicode_preservation(self):
        """Test that Unicode characters are preserved."""
        unicode_text = "Hello 世界! 🌍 Café"
        result = sanitize_text(unicode_text)
        assert result == unicode_text

    def test_none_input(self):
        """Test handling of None input."""
        result = sanitize_text(None)
        assert result == ""

    def test_non_string_input(self):
        """Test handling of non-string input."""
        result = sanitize_text(123)
        assert result == "123"

        result = sanitize_text(['list'])
        assert result == "['list']"


class TestValidationIntegration:
    """Integration tests for validation functions working together."""

    def test_email_validation_with_sanitization(self):
        """Test email validation after sanitization."""
        dirty_email = "test@example.com\x00\x01"
        clean_email = sanitize_text(dirty_email)
        assert is_email(clean_email)

    def test_uuid_validation_with_sanitization(self):
        """Test UUID validation after sanitization."""
        uuid_str = str(uuid.uuid4())
        dirty_uuid = uuid_str + "\x02\x03"
        clean_uuid = sanitize_text(dirty_uuid)
        assert is_uuid(clean_uuid)

    def test_validation_chain(self):
        """Test chaining multiple validation functions."""
        # Test that we can use multiple validations in sequence
        value = "red"
        allowed_colors = ["red", "green", "blue"]

        # Should not raise
        ensure_in(value, allowed_colors, "color")

        # Test numeric validation chain
        number = 5
        ensure_range(number, min_val=1, max_val=10, field="level")
        ensure_in(number, [1, 2, 3, 4, 5], "exact_level")
