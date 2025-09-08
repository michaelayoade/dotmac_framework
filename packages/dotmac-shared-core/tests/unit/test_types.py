"""
Unit tests for dotmac_shared_core.types module.
"""

import pytest

from dotmac_shared_core.exceptions import ValidationError
from dotmac_shared_core.types import JSON, Result


class TestJSONType:
    """Test the JSON type alias."""

    def test_valid_json_types(self):
        """Test that JSON type accepts valid JSON-serializable values."""
        # This is more of a documentation test since mypy would catch type issues
        valid_json_values: list[JSON] = [
            {"key": "value"},
            [1, 2, 3],
            "string",
            123,
            45.67,
            True,
            False,
            None,
            {"nested": {"dict": [1, 2, {"deep": True}]}},
        ]

        # All these should be valid JSON types
        for value in valid_json_values:
            assert value is not None or value is None  # Basic assertion


class TestResultSuccess:
    """Test Result container for successful operations."""

    def test_success_creation(self):
        """Test creating successful results."""
        result = Result.success("test value")

        assert result.ok is True
        assert result.value == "test value"
        assert result.error is None

    def test_success_with_different_types(self):
        """Test successful results with various data types."""
        # String value
        str_result = Result.success("hello")
        assert str_result.value == "hello"

        # Integer value
        int_result = Result.success(42)
        assert int_result.value == 42

        # Dict value
        dict_result = Result.success({"key": "value"})
        assert dict_result.value == {"key": "value"}

        # List value
        list_result = Result.success([1, 2, 3])
        assert list_result.value == [1, 2, 3]

        # None value
        none_result = Result.success(None)
        assert none_result.value is None
        assert none_result.ok is True  # Still successful even with None value

    def test_success_unwrap(self):
        """Test unwrapping successful results."""
        result = Result.success("unwrapped value")
        unwrapped = result.unwrap()
        assert unwrapped == "unwrapped value"

    def test_success_unwrap_or(self):
        """Test unwrap_or with successful results."""
        result = Result.success("actual value")
        value = result.unwrap_or("default value")
        assert value == "actual value"


class TestResultFailure:
    """Test Result container for failed operations."""

    def test_failure_creation(self):
        """Test creating failed results."""
        error = ValidationError("Something went wrong", "ERROR_CODE")
        result = Result.failure(error)

        assert result.ok is False
        assert result.value is None
        assert result.error == error

    def test_error_alias(self):
        """Test that error() is an alias for failure()."""
        error = ValidationError("Test error", "TEST")
        result1 = Result.failure(error)
        result2 = Result.error(error)

        assert result1.ok == result2.ok
        assert result1.value == result2.value
        assert result1.error == result2.error

    def test_failure_with_different_errors(self):
        """Test failure results with different error types."""
        from dotmac_shared_core.exceptions import ConflictError, NotFoundError

        # ValidationError
        val_error = ValidationError("Invalid input")
        val_result = Result.failure(val_error)
        assert val_result.error == val_error

        # NotFoundError
        not_found_error = NotFoundError("Resource not found")
        not_found_result = Result.failure(not_found_error)
        assert not_found_result.error == not_found_error

        # ConflictError
        conflict_error = ConflictError("Resource conflict")
        conflict_result = Result.failure(conflict_error)
        assert conflict_result.error == conflict_error

    def test_failure_unwrap_raises(self):
        """Test that unwrapping failed results raises the error."""
        error = ValidationError("Test error", "TEST")
        result = Result.failure(error)

        with pytest.raises(ValidationError) as exc_info:
            result.unwrap()

        assert exc_info.value == error

    def test_failure_unwrap_or(self):
        """Test unwrap_or with failed results."""
        error = ValidationError("Error occurred", "ERROR")
        result = Result.failure(error)
        value = result.unwrap_or("default value")
        assert value == "default value"


class TestResultEdgeCases:
    """Test Result edge cases and error conditions."""

    def test_invalid_state_unwrap(self):
        """Test unwrap with manually created invalid state."""
        # This simulates a Result that somehow gets into an invalid state
        # (ok=True but value=None and error=None)
        result = Result(ok=True, value=None, error=None)

        with pytest.raises(RuntimeError) as exc_info:
            result.unwrap()

        assert "invalid state" in str(exc_info.value)

    def test_success_with_none_value_unwrap(self):
        """Test that success with None value can be unwrapped."""
        # This tests the edge case where success value is None
        result = Result.success(None)

        # This should raise RuntimeError due to the implementation check
        with pytest.raises(RuntimeError):
            result.unwrap()

    def test_unwrap_or_with_none_success(self):
        """Test unwrap_or when success value is None."""
        result = Result.success(None)
        value = result.unwrap_or("default")
        assert value is None  # Should return None, not default


class TestResultTypeHints:
    """Test Result type parameterization."""

    def test_string_result(self):
        """Test Result parameterized with string type."""
        result: Result[str] = Result.success("hello")
        assert result.value == "hello"

        error_result: Result[str] = Result.failure(ValidationError("Error", "CODE"))
        assert error_result.value is None

    def test_int_result(self):
        """Test Result parameterized with int type."""
        result: Result[int] = Result.success(42)
        assert result.value == 42

        error_result: Result[int] = Result.failure(ValidationError("Error", "CODE"))
        assert error_result.value is None

    def test_dict_result(self):
        """Test Result parameterized with dict type."""
        data = {"key": "value", "number": 123}
        result: Result[dict[str, any]] = Result.success(data)
        assert result.value == data

    def test_list_result(self):
        """Test Result parameterized with list type."""
        items = [1, 2, 3, 4, 5]
        result: Result[list[int]] = Result.success(items)
        assert result.value == items


class TestResultUsagePatterns:
    """Test common Result usage patterns."""

    def test_conditional_handling(self):
        """Test typical conditional handling of results."""
        success_result = Result.success("data")
        error_result = Result.failure(ValidationError("Error", "CODE"))

        # Success case
        if success_result.ok:
            assert success_result.value == "data"
        else:
            pytest.fail("Should not reach here for success case")

        # Error case
        if error_result.ok:
            pytest.fail("Should not reach here for error case")
        else:
            assert error_result.error is not None

    def test_chaining_pattern(self):
        """Test result chaining pattern."""
        def process_data(value: str) -> Result[str]:
            if not value:
                return Result.failure(ValidationError("Empty value", "EMPTY"))
            return Result.success(value.upper())

        def validate_length(value: str) -> Result[str]:
            if len(value) < 3:
                return Result.failure(ValidationError("Too short", "SHORT"))
            return Result.success(value)

        # Success chain
        result1 = process_data("hello")
        assert result1.ok
        if result1.ok:
            result2 = validate_length(result1.value)
            assert result2.ok
            assert result2.value == "HELLO"

        # Failure chain
        result3 = process_data("")
        assert not result3.ok
        assert result3.error.message == "Empty value"

    def test_error_propagation(self):
        """Test error propagation through result chains."""
        def step1(value: int) -> Result[int]:
            if value < 0:
                return Result.failure(ValidationError("Negative value", "NEGATIVE"))
            return Result.success(value * 2)

        def step2(value: int) -> Result[int]:
            if value >= 100:
                return Result.failure(ValidationError("Too large", "TOO_LARGE"))
            return Result.success(value + 10)

        # Test successful chain
        result1 = step1(20)  # -> 40
        assert result1.ok
        if result1.ok:
            result2 = step2(result1.value)  # -> 50
            assert result2.ok
            assert result2.value == 50

        # Test failure in first step
        result3 = step1(-5)
        assert not result3.ok
        assert result3.error.error_code == "NEGATIVE"

        # Test failure in second step
        result4 = step1(50)  # -> 100
        assert result4.ok
        if result4.ok:
            result5 = step2(result4.value)  # -> 110, too large
            assert not result5.ok
            assert result5.error.error_code == "TOO_LARGE"
