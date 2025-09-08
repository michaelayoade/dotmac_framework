"""
Tests for workflow result dataclass.
"""

import pytest

from dotmac_workflows.result import WorkflowResult


class TestWorkflowResult:
    """Test workflow result class."""

    def test_basic_creation(self):
        """Test basic result creation."""
        result = WorkflowResult(success=True, step="test_step", data={"key": "value"})

        assert result.success is True
        assert result.step == "test_step"
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.message is None
        assert result.execution_time is None
        assert result.requires_approval is False

    def test_full_creation(self):
        """Test result creation with all fields."""
        result = WorkflowResult(
            success=False,
            step="test_step",
            data={"result": "failed"},
            error="test_error",
            message="Test message",
            execution_time=1.5,
            requires_approval=True,
        )

        assert result.success is False
        assert result.step == "test_step"
        assert result.data == {"result": "failed"}
        assert result.error == "test_error"
        assert result.message == "Test message"
        assert result.execution_time == 1.5
        assert result.requires_approval is True

    def test_invalid_data_type(self):
        """Test that non-dict data raises TypeError."""
        with pytest.raises(TypeError, match="data must be a dictionary"):
            WorkflowResult(
                success=True,
                step="test_step",
                data="not a dict",  # type: ignore
            )

    def test_invalid_step_empty(self):
        """Test that empty step raises ValueError."""
        with pytest.raises(ValueError, match="step must be a non-empty string"):
            WorkflowResult(success=True, step="", data={})

    def test_invalid_step_type(self):
        """Test that non-string step raises ValueError."""
        with pytest.raises(ValueError, match="step must be a non-empty string"):
            WorkflowResult(
                success=True,
                step=None,  # type: ignore
                data={},
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = WorkflowResult(
            success=True,
            step="test_step",
            data={"key": "value"},
            error="test_error",
            message="Test message",
            execution_time=2.0,
            requires_approval=True,
        )

        expected = {
            "success": True,
            "step": "test_step",
            "data": {"key": "value"},
            "error": "test_error",
            "message": "Test message",
            "execution_time": 2.0,
            "requires_approval": True,
        }

        assert result.to_dict() == expected

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "success": False,
            "step": "test_step",
            "data": {"error": "failed"},
            "error": "test_error",
            "message": "Test message",
            "execution_time": 1.5,
            "requires_approval": True,
        }

        result = WorkflowResult.from_dict(data)

        assert result.success is False
        assert result.step == "test_step"
        assert result.data == {"error": "failed"}
        assert result.error == "test_error"
        assert result.message == "Test message"
        assert result.execution_time == 1.5
        assert result.requires_approval is True

    def test_from_dict_minimal(self):
        """Test creation from minimal dictionary."""
        data = {"success": True, "step": "test_step", "data": {"result": "success"}}

        result = WorkflowResult.from_dict(data)

        assert result.success is True
        assert result.step == "test_step"
        assert result.data == {"result": "success"}
        assert result.error is None
        assert result.message is None
        assert result.execution_time is None
        assert result.requires_approval is False

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip."""
        original = WorkflowResult(
            success=True,
            step="roundtrip_test",
            data={"test": "data"},
            error="some_error",
            message="Some message",
            execution_time=3.14,
            requires_approval=True,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = WorkflowResult.from_dict(data)

        # Should be identical
        assert restored.success == original.success
        assert restored.step == original.step
        assert restored.data == original.data
        assert restored.error == original.error
        assert restored.message == original.message
        assert restored.execution_time == original.execution_time
        assert restored.requires_approval == original.requires_approval
