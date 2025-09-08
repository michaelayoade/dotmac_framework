"""
Tests for base workflow implementation.
"""

import pytest

from dotmac_workflows.base import (
    Workflow,
    WorkflowConfigurationError,
    WorkflowExecutionError,
)
from dotmac_workflows.result import WorkflowResult
from dotmac_workflows.status import WorkflowStatus


class SimpleWorkflow(Workflow):
    """Simple workflow for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.executed_steps = []
        self.should_fail_step = None
        self.should_require_approval_step = None

    async def execute_step(self, step: str) -> WorkflowResult:
        """Execute step with configurable behavior."""
        self.executed_steps.append(step)

        if step.startswith("rollback_"):
            return WorkflowResult(success=True, step=step, data={"rollback": True})

        if step == self.should_fail_step:
            return WorkflowResult(
                success=False,
                step=step,
                data={},
                error="test_failure",
                message="Intentional test failure",
            )

        requires_approval = step == self.should_require_approval_step

        return WorkflowResult(
            success=True, step=step, data={"step": step}, requires_approval=requires_approval
        )


class TestWorkflowBasics:
    """Test basic workflow functionality."""

    def test_creation_with_defaults(self):
        """Test workflow creation with default values."""
        workflow = SimpleWorkflow()

        assert workflow.workflow_id is not None
        assert len(workflow.workflow_id) > 0
        assert workflow.steps == []
        assert workflow.metadata == {}
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.current_step_index == 0
        assert workflow.results == []

    def test_creation_with_parameters(self):
        """Test workflow creation with parameters."""
        workflow = SimpleWorkflow(
            workflow_id="test-id", steps=["step1", "step2"], metadata={"test": "data"}
        )

        assert workflow.workflow_id == "test-id"
        assert workflow.steps == ["step1", "step2"]
        assert workflow.metadata == {"test": "data"}

    def test_configuration(self):
        """Test workflow configuration."""
        workflow = SimpleWorkflow()

        workflow.configure(
            rollback_on_failure=False, continue_on_step_failure=True, require_approval=True
        )

        assert workflow.rollback_on_failure is False
        assert workflow.continue_on_step_failure is True
        assert workflow.require_approval is True

    def test_invalid_configuration(self):
        """Test invalid configuration raises error."""
        workflow = SimpleWorkflow()

        with pytest.raises(WorkflowConfigurationError):
            workflow.configure(rollback_on_failure=True, continue_on_step_failure=True)

    async def test_validation_success(self):
        """Test successful validation."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])

        result = await workflow.validate()
        assert result.success is True
        assert result.step == "validation"

    async def test_validation_no_steps(self):
        """Test validation fails with no steps."""
        workflow = SimpleWorkflow(workflow_id="test")

        result = await workflow.validate()
        assert result.success is False
        assert result.error == "empty_steps"

    async def test_validation_no_id(self):
        """Test validation fails with no ID."""
        workflow = SimpleWorkflow(steps=["step1"])
        # Manually set empty ID to test validation
        workflow.workflow_id = ""

        result = await workflow.validate()
        assert result.success is False
        assert result.error == "missing_id"


class TestWorkflowExecution:
    """Test workflow execution."""

    async def test_simple_execution(self):
        """Test simple successful execution."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2", "step3"])

        results = await workflow.execute()

        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.step for r in results] == ["step1", "step2", "step3"]
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.executed_steps == ["step1", "step2", "step3"]

    async def test_execution_with_failure_rollback(self):
        """Test execution with failure and rollback."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2", "step3"])
        workflow.should_fail_step = "step2"
        workflow.configure(rollback_on_failure=True)

        results = await workflow.execute()

        # Should have: step1 (success), step2 (fail), rollback_step1 (success)
        assert len(results) >= 2
        assert results[0].success is True  # step1
        assert results[1].success is False  # step2 failure
        assert workflow.status == WorkflowStatus.FAILED

    async def test_execution_continue_on_failure(self):
        """Test execution continuing on failure."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2", "step3"])
        workflow.should_fail_step = "step2"
        workflow.configure(continue_on_step_failure=True, rollback_on_failure=False)

        results = await workflow.execute()

        # Should execute all steps despite step2 failure
        assert len(results) == 3
        assert results[0].success is True  # step1
        assert results[1].success is False  # step2 failure
        assert results[2].success is True  # step3
        assert workflow.status == WorkflowStatus.COMPLETED

    async def test_execution_already_running(self):
        """Test execution fails when already running."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])
        workflow.status = WorkflowStatus.RUNNING

        with pytest.raises(WorkflowExecutionError, match="already running"):
            await workflow.execute()


class TestWorkflowApproval:
    """Test approval workflow functionality."""

    async def test_approval_workflow(self):
        """Test workflow requiring approval."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2"])
        workflow.configure(require_approval=True)
        workflow.should_require_approval_step = "step2"

        # First execution should stop at approval
        results = await workflow.execute()

        assert len(results) == 2
        assert results[0].success is True  # step1
        assert results[1].success is True  # step2
        assert results[1].requires_approval is True
        assert workflow.status == WorkflowStatus.WAITING_APPROVAL
        assert workflow.pending_approval_step == "step2"

    async def test_approve_and_continue(self):
        """Test approving and continuing workflow."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2", "step3"])
        workflow.configure(require_approval=True)
        workflow.should_require_approval_step = "step2"

        # Execute until approval needed
        await workflow.execute()
        assert workflow.status == WorkflowStatus.WAITING_APPROVAL

        # Approve and continue
        approval_data = {"approved_by": "user123"}
        results = await workflow.approve_and_continue(approval_data)

        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.approval_data == approval_data
        assert len(results) == 3  # All steps completed

    async def test_reject_and_cancel(self):
        """Test rejecting approval and cancelling."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2"])
        workflow.configure(require_approval=True)
        workflow.should_require_approval_step = "step2"

        # Execute until approval needed
        await workflow.execute()
        assert workflow.status == WorkflowStatus.WAITING_APPROVAL

        # Reject
        results = await workflow.reject_and_cancel("Not approved")

        assert workflow.status == WorkflowStatus.CANCELLED
        assert len(results) == 3  # original 2 steps + rejection result
        assert results[-1].success is False
        assert results[-1].error == "approval_rejected"

    async def test_approve_not_waiting(self):
        """Test approving when not waiting for approval fails."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])

        with pytest.raises(WorkflowExecutionError, match="not waiting for approval"):
            await workflow.approve_and_continue()

    async def test_reject_not_waiting(self):
        """Test rejecting when not waiting for approval fails."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])

        with pytest.raises(WorkflowExecutionError, match="not waiting for approval"):
            await workflow.reject_and_cancel()


class TestWorkflowCallbacks:
    """Test workflow callback functionality."""

    async def test_step_callbacks(self):
        """Test step start and completion callbacks."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1", "step2"])

        started_steps = []
        completed_steps = []

        def on_step_started(step):
            started_steps.append(step)

        def on_step_completed(result):
            completed_steps.append(result.step)

        workflow.on_step_started = on_step_started
        workflow.on_step_completed = on_step_completed

        await workflow.execute()

        assert started_steps == ["step1", "step2"]
        assert completed_steps == ["step1", "step2"]

    async def test_workflow_completed_callback(self):
        """Test workflow completion callback."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])

        completion_called = False
        completion_results = None

        def on_workflow_completed(results):
            nonlocal completion_called, completion_results
            completion_called = True
            completion_results = results

        workflow.on_workflow_completed = on_workflow_completed

        results = await workflow.execute()

        assert completion_called is True
        assert completion_results == results

    async def test_approval_required_callback(self):
        """Test approval required callback."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])
        workflow.configure(require_approval=True)
        workflow.should_require_approval_step = "step1"

        approval_step = None

        def on_approval_required(step):
            nonlocal approval_step
            approval_step = step

        workflow.on_approval_required = on_approval_required

        await workflow.execute()

        assert approval_step == "step1"


class TestWorkflowProperties:
    """Test workflow properties and utilities."""

    def test_properties_initial(self):
        """Test properties in initial state."""
        workflow = SimpleWorkflow()

        assert workflow.execution_time is None
        assert workflow.is_completed is False
        assert workflow.is_failed is False
        assert workflow.is_waiting_approval is False

    async def test_properties_completed(self):
        """Test properties after completion."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])

        await workflow.execute()

        assert workflow.execution_time is not None
        assert workflow.execution_time > 0
        assert workflow.is_completed is True
        assert workflow.is_failed is False
        assert workflow.is_waiting_approval is False

    async def test_properties_failed(self):
        """Test properties after failure."""
        workflow = SimpleWorkflow(workflow_id="test", steps=["step1"])
        workflow.should_fail_step = "step1"

        await workflow.execute()

        assert workflow.is_completed is False
        assert workflow.is_failed is True
        assert workflow.is_waiting_approval is False

    def test_serialization_roundtrip(self):
        """Test workflow serialization roundtrip."""
        original = SimpleWorkflow(
            workflow_id="test", steps=["step1", "step2"], metadata={"test": "data"}
        )
        original.current_step_index = 1
        original.approval_data = {"user": "test"}

        # Serialize and deserialize
        data = original.to_dict()
        restored = Workflow.from_dict(data)

        assert restored.workflow_id == original.workflow_id
        assert restored.steps == original.steps
        assert restored.metadata == original.metadata
        assert restored.current_step_index == original.current_step_index
        assert restored.approval_data == original.approval_data
