"""Tests for shared utility functions."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from uuid import UUID
import hashlib
import string
import math

from dotmac_isp.shared.utils import (
    generate_uuid, generate_random_string, generate_random_password,
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, validate_email, validate_phone, format_phone, slugify,
    calculate_hash, mask_sensitive_data, generate_invoice_number,
    generate_ticket_number, calculate_distance, format_currency,
    parse_boolean, sanitize_filename, chunk_list
, timezone)


class TestUUIDGeneration:
    """Test UUID generation functions."""
    
    def test_generate_uuid_returns_uuid4(self):
        """Test that generate_uuid returns a valid UUID4."""
        result = generate_uuid()
        
        assert isinstance(result, UUID)
        assert result.version == 4
    
    def test_generate_uuid_unique_values(self):
        """Test that generate_uuid returns unique values."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert uuid1 != uuid2


class TestRandomStringGeneration:
    """Test random string generation functions."""
    
    def test_generate_random_string_default_length(self):
        """Test generate_random_string with default length."""
        result = generate_random_string()
        
        assert len(result) == 8
        assert all(c in string.ascii_letters + string.digits for c in result)
    
    def test_generate_random_string_custom_length(self):
        """Test generate_random_string with custom length."""
        lengths = [1, 5, 12, 20, 50]
        
        for length in lengths:
            result = generate_random_string(length)
            assert len(result) == length
            assert all(c in string.ascii_letters + string.digits for c in result)
    
    def test_generate_random_string_uniqueness(self):
        """Test that generate_random_string produces unique values."""
        results = [generate_random_string(10) for _ in range(100)]
        
        # Should be highly unlikely to have duplicates
        assert len(set(results) > 95
    
    def test_generate_random_password_default_length(self):
        """Test generate_random_password with default length."""
        result = generate_random_password()
        
        assert len(result) == 12
        expected_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        assert all(c in expected_chars for c in result)
    
    def test_generate_random_password_custom_length(self):
        """Test generate_random_password with custom length."""
        lengths = [6, 8, 16, 24]
        expected_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        
        for length in lengths:
            result = generate_random_password(length)
            assert len(result) == length
            assert all(c in expected_chars for c in result)
    
    def test_generate_random_password_contains_variety(self):
        """Test that generated passwords contain character variety."""
        # Generate multiple passwords and check they're not all the same type
        passwords = [generate_random_password(20) for _ in range(10)]
        
        # At least some should contain special characters
        has_special = any(any(c in "!@#$%^&*" for c in pwd) for pwd in passwords)
        assert has_special, "Should generate passwords with special characters"


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original
    
    def test_hash_password_different_for_same_input(self):
        """Test that hashing the same password twice gives different results."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # bcrypt includes salt, so hashes should be different
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "correct_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        original = "correct_password"
        wrong = "wrong_password"
        hashed = hash_password(original)
        
        assert verify_password(wrong, hashed) is False
    
    def test_verify_password_empty_strings(self):
        """Test password verification with empty strings."""
        empty_hash = hash_password("")
        
        assert verify_password("", empty_hash) is True
        assert verify_password("not_empty", empty_hash) is False


class TestJWTTokens:
    """Test JWT token creation and decoding."""
    
    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry."""
        data = {"user_id": "123", "username": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["user_id"] == "123"
        assert decoded["username"] == "testuser"
        assert decoded["type"] == "access"
        assert "exp" in decoded
    
    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"user_id": "456"}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta)
        
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["user_id"] == "456"
        
        # Check expiry is approximately 2 hours from now
        exp_time = datetime.fromtimestamp(decoded["exp"])
        expected_time = datetime.now(timezone.utc) + expires_delta
        time_diff = abs((exp_time - expected_time).total_seconds()
        assert time_diff < 60  # Within 1 minute tolerance
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"user_id": "789", "scope": "refresh"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["user_id"] == "789"
        assert decoded["scope"] == "refresh"
        assert decoded["type"] == "refresh"
        assert "exp" in decoded
    
    def test_decode_token_invalid(self):
        """Test decoding invalid token."""
        invalid_tokens = [
            "invalid.token.string",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "not_a_jwt_at_all"
        ]
        
        for invalid_token in invalid_tokens:
            result = decode_token(invalid_token)
            assert result is None
    
    @patch('dotmac_isp.shared.utils.jwt.decode')
    def test_decode_token_jwt_error(self, mock_decode):
        """Test decode_token handling JWTError."""
        from jose import JWTError
        mock_decode.side_effect = JWTError("Invalid token")
        
        result = decode_token("some.token.here")
        assert result is None


class TestValidationFunctions:
    """Test validation utility functions."""
    
    def test_validate_email_valid_emails(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com",
            "user_name@domain-name.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True, f"Should be valid: {email}"
    
    def test_validate_email_invalid_emails(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid",
            "@domain.com",
            "user@",
            "user.domain.com",
            "user@domain",
            "",
            "user@.com",
            "user@domain.",
            "user space@domain.com"
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False, f"Should be invalid: {email}"
    
    def test_validate_phone_valid_numbers(self):
        """Test phone validation with valid numbers."""
        valid_phones = [
            "1234567890",
            "(123) 456-7890",
            "+1-234-567-8900",
            "123.456.7890",
            "123 456 7890",
            "+1 (123) 456-7890",
            "12345678901234"  # 14 digits
        ]
        
        for phone in valid_phones:
            assert validate_phone(phone) is True, f"Should be valid: {phone}"
    
    def test_validate_phone_invalid_numbers(self):
        """Test phone validation with invalid numbers."""
        invalid_phones = [
            "123456789",  # Too short
            "1234567890123456",  # Too long
            "",
            "abc-def-ghij",
            "123-45",
            "+1"
        ]
        
        for phone in invalid_phones:
            assert validate_phone(phone) is False, f"Should be invalid: {phone}"
    
    def test_format_phone_10_digits(self):
        """Test phone formatting for 10-digit numbers."""
        inputs_outputs = [
            ("1234567890", "(123) 456-7890"),
            ("123-456-7890", "(123) 456-7890"),
            ("(123) 456-7890", "(123) 456-7890")
        ]
        
        for input_phone, expected in inputs_outputs:
            result = format_phone(input_phone)
            assert result == expected, f"Input: {input_phone}, Expected: {expected}, Got: {result}"
    
    def test_format_phone_11_digits(self):
        """Test phone formatting for 11-digit numbers starting with 1."""
        inputs_outputs = [
            ("11234567890", "+1 (123) 456-7890"),
            ("1-123-456-7890", "+1 (123) 456-7890"),
            ("+1 123 456 7890", "+1 (123) 456-7890")
        ]
        
        for input_phone, expected in inputs_outputs:
            result = format_phone(input_phone)
            assert result == expected, f"Input: {input_phone}, Expected: {expected}, Got: {result}"
    
    def test_format_phone_invalid_formats(self):
        """Test phone formatting for invalid formats."""
        invalid_phones = [
            "21234567890",  # 11 digits not starting with 1
            "123456789",    # 9 digits
            "invalid"
        ]
        
        for phone in invalid_phones:
            result = format_phone(phone)
            assert result == phone  # Should return unchanged


class TestTextProcessing:
    """Test text processing utility functions."""
    
    def test_slugify_basic(self):
        """Test basic slugify functionality."""
        test_cases = [
            ("Hello World", "hello-world"),
            ("Test Title", "test-title"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("Special!@#Characters", "specialcharacters"),
            ("Mixed-Case_Text", "mixed-case_text")
        ]
        
        for input_text, expected in test_cases:
            result = slugify(input_text)
            assert result == expected, f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
    
    def test_slugify_edge_cases(self):
        """Test slugify edge cases."""
        edge_cases = [
            ("", ""),
            ("   ", ""),
            ("---", ""),
            ("!@#$%", ""),
            ("   leading-and-trailing   ", "leading-and-trailing")
        ]
        
        for input_text, expected in edge_cases:
            result = slugify(input_text)
            assert result == expected, f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
    
    def test_calculate_hash(self):
        """Test SHA-256 hash calculation."""
        test_data = "test data for hashing"
        expected_hash = hashlib.sha256(test_data.encode().hexdigest()
        
        result = calculate_hash(test_data)
        assert result == expected_hash
        assert len(result) == 64  # SHA-256 produces 64-character hex string
    
    def test_calculate_hash_different_inputs(self):
        """Test hash calculation for different inputs."""
        inputs = ["", "a", "test", "longer test string", "123456"]
        
        hashes = [calculate_hash(data) for data in inputs]
        
        # All hashes should be different
        assert len(set(hashes) == len(hashes)
        
        # All should be 64 characters
        assert all(len(h) == 64 for h in hashes)
    
    def test_mask_sensitive_data_default(self):
        """Test masking sensitive data with default parameters."""
        test_cases = [
            ("1234567890", "******7890"),
            ("abcdefghij", "******ghij"),
            ("short", "*hort"),  # Shorter than visible chars
            ("test", "****"),    # Equal to visible chars
            ("hi", "**")         # Very short
        ]
        
        for input_data, expected in test_cases:
            result = mask_sensitive_data(input_data)
            assert result == expected, f"Input: '{input_data}', Expected: '{expected}', Got: '{result}'"
    
    def test_mask_sensitive_data_custom_visible(self):
        """Test masking with custom visible characters."""
        data = "1234567890"
        
        test_cases = [
            (1, "*********0"),
            (2, "********90"),
            (3, "*******890"),
            (6, "****567890"),
            (10, "**********"),  # More than data length - all masked
            (15, "**********")   # More than data length - all masked
        ]
        
        for visible_chars, expected in test_cases:
            result = mask_sensitive_data(data, visible_chars)
            assert result == expected, f"Visible: {visible_chars}, Expected: '{expected}', Got: '{result}'"


class TestNumberGeneration:
    """Test number generation functions."""
    
    @patch('dotmac_isp.shared.utils.datetime')
    @patch('dotmac_isp.shared.utils.generate_random_string')
    def test_generate_invoice_number_default_prefix(self, mock_random, mock_datetime):
        """Test invoice number generation with default prefix."""
        mock_datetime.now.return_value.strftime.return_value = "20231215143052"
        mock_random.return_value = "ABCD"
        
        result = generate_invoice_number()
        
        assert result == "INV-20231215143052-ABCD"
        mock_random.assert_called_once_with(4)
    
    @patch('dotmac_isp.shared.utils.datetime')
    @patch('dotmac_isp.shared.utils.generate_random_string')
    def test_generate_invoice_number_custom_prefix(self, mock_random, mock_datetime):
        """Test invoice number generation with custom prefix."""
        mock_datetime.now.return_value.strftime.return_value = "20231215143052"
        mock_random.return_value = "XYZ1"
        
        result = generate_invoice_number("BILL")
        
        assert result == "BILL-20231215143052-XYZ1"
    
    @patch('dotmac_isp.shared.utils.datetime')
    @patch('dotmac_isp.shared.utils.generate_random_string')
    def test_generate_ticket_number_default_prefix(self, mock_random, mock_datetime):
        """Test ticket number generation with default prefix."""
        mock_datetime.now.return_value.strftime.return_value = "20231215"
        mock_random.return_value = "TICKET"
        
        result = generate_ticket_number()
        
        assert result == "TKT-20231215-TICKET"
        mock_random.assert_called_once_with(6)
    
    @patch('dotmac_isp.shared.utils.datetime')
    @patch('dotmac_isp.shared.utils.generate_random_string')
    def test_generate_ticket_number_custom_prefix(self, mock_random, mock_datetime):
        """Test ticket number generation with custom prefix."""
        mock_datetime.now.return_value.strftime.return_value = "20231215"
        mock_random.return_value = "HELP01"
        
        result = generate_ticket_number("SUP")
        
        assert result == "SUP-20231215-HELP01"


class TestGeospatial:
    """Test geospatial utility functions."""
    
    def test_calculate_distance_same_point(self):
        """Test distance calculation for same point."""
        lat, lon = 40.7128, -74.0060  # New York
        
        result = calculate_distance(lat, lon, lat, lon)
        assert result == 0.0
    
    def test_calculate_distance_known_points(self):
        """Test distance calculation for known points."""
        # New York to Los Angeles (approximately 3944 km)
        ny_lat, ny_lon = 40.7128, -74.0060
        la_lat, la_lon = 34.0522, -118.2437
        
        result = calculate_distance(ny_lat, ny_lon, la_lat, la_lon)
        
        # Allow for some tolerance in the calculation
        assert 3900 < result < 4000, f"Expected ~3944 km, got {result}"
    
    def test_calculate_distance_short_distance(self):
        """Test distance calculation for short distances."""
        # Two points close together
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7589, -73.9851  # About 50km away
        
        result = calculate_distance(lat1, lon1, lat2, lon2)
        
        # Should be roughly 5km (these points are actually much closer)
        assert 5 < result < 6, f"Expected ~5.4 km, got {result}"
    
    def test_calculate_distance_negative_coordinates(self):
        """Test distance calculation with negative coordinates."""
        # Southern hemisphere and western hemisphere
        lat1, lon1 = -33.8688, 151.2093  # Sydney
        lat2, lon2 = -37.8136, 144.9631  # Melbourne
        
        result = calculate_distance(lat1, lon1, lat2, lon2)
        
        # Sydney to Melbourne is approximately 713 km
        assert 700 < result < 730, f"Expected ~713 km, got {result}"


class TestUtilityFunctions:
    """Test various utility functions."""
    
    def test_format_currency_usd_default(self):
        """Test currency formatting for USD (default)."""
        test_cases = [
            (100.0, "$100.00"),
            (1234.56, "$1,234.56"),
            (0.99, "$0.99"),
            (1000000.0, "$1,000,000.00"),
            (0.0, "$0.00")
        ]
        
        for amount, expected in test_cases:
            result = format_currency(amount)
            assert result == expected, f"Amount: {amount}, Expected: '{expected}', Got: '{result}'"
    
    def test_format_currency_other_currencies(self):
        """Test currency formatting for other currencies."""
        test_cases = [
            (100.0, "EUR", "100.00 EUR"),
            (1234.56, "GBP", "1,234.56 GBP"),
            (99.99, "CAD", "99.99 CAD")
        ]
        
        for amount, currency, expected in test_cases:
            result = format_currency(amount, currency)
            assert result == expected, f"Amount: {amount}, Currency: {currency}, Expected: '{expected}', Got: '{result}'"
    
    def test_parse_boolean_bool_inputs(self):
        """Test boolean parsing with boolean inputs."""
        assert parse_boolean(True) is True
        assert parse_boolean(False) is False
    
    def test_parse_boolean_string_inputs(self):
        """Test boolean parsing with string inputs."""
        true_strings = ["true", "True", "TRUE", "yes", "YES", "1", "on", "ON", "enabled", "ENABLED"]
        false_strings = ["false", "False", "FALSE", "no", "NO", "0", "off", "OFF", "disabled", "random"]
        
        for s in true_strings:
            assert parse_boolean(s) is True, f"String '{s}' should be True"
        
        for s in false_strings:
            assert parse_boolean(s) is False, f"String '{s}' should be False"
    
    def test_parse_boolean_numeric_inputs(self):
        """Test boolean parsing with numeric inputs."""
        true_numbers = [1, 1.0, 5, -1, 0.1]
        false_numbers = [0, 0.0]
        
        for n in true_numbers:
            assert parse_boolean(n) is True, f"Number {n} should be True"
        
        for n in false_numbers:
            assert parse_boolean(n) is False, f"Number {n} should be False"
    
    def test_parse_boolean_other_inputs(self):
        """Test boolean parsing with other input types."""
        other_inputs = [None, [], {}, object()]
        
        for inp in other_inputs:
            assert parse_boolean(inp) is False, f"Input {inp} should be False"
    
    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        test_cases = [
            ("document.txt", "document.txt"),
            ("my file.pdf", "my_file.pdf"),
            ("test-file_v2.doc", "test-file_v2.doc"),
            ("file with spaces.xlsx", "file_with_spaces.xlsx")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Input: '{input_name}', Expected: '{expected}', Got: '{result}'"
    
    def test_sanitize_filename_dangerous_chars(self):
        """Test filename sanitization with dangerous characters."""
        dangerous_inputs = [
            ("../../../etc/passwd", "etcpasswd"),
            ("file/with/slashes.txt", "filewithslashes.txt"),
            ("file<>:|*?.txt", "file.txt"),
            ("CON.txt", "CON.txt"),  # Windows reserved name - basic sanitization only
            ("file...name.txt", "file.name.txt")
        ]
        
        for input_name, expected in dangerous_inputs:
            result = sanitize_filename(input_name)
            assert result == expected, f"Input: '{input_name}', Expected: '{expected}', Got: '{result}'"
    
    def test_sanitize_filename_edge_cases(self):
        """Test filename sanitization edge cases."""
        edge_cases = [
            ("...", ""),
            ("___", ""),
            ("", ""),
            ("   ", ""),
            ("...file...", "file")
        ]
        
        for input_name, expected in edge_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Input: '{input_name}', Expected: '{expected}', Got: '{result}'"
    
    def test_chunk_list_basic(self):
        """Test basic list chunking."""
        input_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        chunk_size = 3
        expected = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]
        
        result = chunk_list(input_list, chunk_size)
        assert result == expected
    
    def test_chunk_list_exact_division(self):
        """Test list chunking with exact division."""
        input_list = [1, 2, 3, 4, 5, 6]
        chunk_size = 2
        expected = [[1, 2], [3, 4], [5, 6]]
        
        result = chunk_list(input_list, chunk_size)
        assert result == expected
    
    def test_chunk_list_single_chunk(self):
        """Test list chunking where chunk size >= list size."""
        input_list = [1, 2, 3]
        chunk_size = 5
        expected = [[1, 2, 3]]
        
        result = chunk_list(input_list, chunk_size)
        assert result == expected
    
    def test_chunk_list_empty_list(self):
        """Test chunking empty list."""
        input_list = []
        chunk_size = 3
        expected = []
        
        result = chunk_list(input_list, chunk_size)
        assert result == expected
    
    def test_chunk_list_chunk_size_one(self):
        """Test chunking with chunk size of 1."""
        input_list = [1, 2, 3, 4]
        chunk_size = 1
        expected = [[1], [2], [3], [4]]
        
        result = chunk_list(input_list, chunk_size)
        assert result == expected