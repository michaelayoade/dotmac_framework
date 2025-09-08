"""
Tests for workflow status enumeration.
"""

from dotmac_workflows.status import WorkflowStatus


class TestWorkflowStatus:
    """Test workflow status enum."""

    def test_status_values(self):
        """Test all status values are correct."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
        assert WorkflowStatus.WAITING_APPROVAL.value == "waiting_approval"
        assert WorkflowStatus.PAUSED.value == "paused"

    def test_string_conversion(self):
        """Test string conversion returns value."""
        assert str(WorkflowStatus.PENDING) == "pending"
        assert str(WorkflowStatus.RUNNING) == "running"
        assert str(WorkflowStatus.COMPLETED) == "completed"

    def test_all_statuses_present(self):
        """Test all expected statuses are present."""
        expected_statuses = {
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            "waiting_approval",
            "paused",
        }
        actual_statuses = {status.value for status in WorkflowStatus}
        assert actual_statuses == expected_statuses
