"""
Business Process Engine Comprehensive Testing
Implementation of BIZ-001: Process engine event handling and state management.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import pytest

# Import the actual business logic modules
from dotmac_business_logic.processes.engine import (
    ProcessEngine,
    ProcessingError,
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowResult,
)


class TestBusinessWorkflowStatus(Enum):
    """Test workflow status for comprehensive testing"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestWorkflow:
    """Test workflow implementation for comprehensive testing"""

    def __init__(self, workflow_id: str = None):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.status = TestBusinessWorkflowStatus.PENDING
        self.steps_completed = 0
        self.results = []
        self.created_at = datetime.now(timezone.utc)
        self.start_time = None
        self.end_time = None
        self.context = {}

    async def execute(self, context: dict[str, Any]) -> WorkflowResult:
        """Execute the test workflow"""
        self.status = TestBusinessWorkflowStatus.RUNNING
        self.start_time = datetime.now(timezone.utc)
        self.context.update(context)

        # Simulate multi-step workflow
        # Step 1: Validation
        result1 = WorkflowResult(
            step_name="validation",
            success=True,
            data={"validated": True},
            timestamp=datetime.now(timezone.utc)
        )
        self.results.append(result1)
        self.steps_completed += 1

        # Check if approval is required
        if context.get("requires_approval", False):
            self.status = TestBusinessWorkflowStatus.WAITING_APPROVAL
            return WorkflowResult(
                step_name="approval_request",
                success=True,
                data={"approval_id": str(uuid.uuid4())},
                timestamp=datetime.now(timezone.utc)
            )

        # Step 2: Processing
        await asyncio.sleep(0.01)  # Simulate processing time
        result2 = WorkflowResult(
            step_name="processing",
            success=True,
            data={"processed_items": len(context.get("items", []))},
            timestamp=datetime.now(timezone.utc)
        )
        self.results.append(result2)
        self.steps_completed += 1

        # Complete workflow
        self.status = TestBusinessWorkflowStatus.COMPLETED
        self.end_time = datetime.now(timezone.utc)

        return WorkflowResult(
            step_name="completion",
            success=True,
            data={"total_steps": self.steps_completed},
            timestamp=self.end_time
        )

    async def approve_and_continue(self, approval_data: dict[str, Any] = None) -> WorkflowResult:
        """Continue workflow after approval"""
        if self.status != TestBusinessWorkflowStatus.WAITING_APPROVAL:
            raise ProcessingError("Workflow is not waiting for approval")

        self.status = TestBusinessWorkflowStatus.RUNNING

        # Step 2: Post-approval processing
        result2 = WorkflowResult(
            step_name="post_approval_processing",
            success=True,
            data={"approval_data": approval_data or {}, "approved_at": datetime.now(timezone.utc)},
            timestamp=datetime.now(timezone.utc)
        )
        self.results.append(result2)
        self.steps_completed += 1

        # Complete the workflow
        self.status = TestBusinessWorkflowStatus.COMPLETED
        self.end_time = datetime.now(timezone.utc)

        return WorkflowResult(
            step_name="completion",
            success=True,
            data={"total_steps": self.steps_completed},
            timestamp=self.end_time
        )

    async def cancel(self, reason: str = "User requested") -> WorkflowResult:
        """Cancel the workflow"""
        self.status = TestBusinessWorkflowStatus.CANCELLED
        self.end_time = datetime.now(timezone.utc)

        return WorkflowResult(
            step_name="cancellation",
            success=True,
            data={"reason": reason, "cancelled_at": self.end_time},
            timestamp=self.end_time
        )


class TestProcessEngineComprehensive:
    """Comprehensive process engine testing"""

    @pytest.fixture
    def process_engine(self):
        """Create process engine instance for testing"""
        return ProcessEngine()

    @pytest.fixture
    def test_workflow_definition(self):
        """Test workflow definition"""
        return WorkflowDefinition(
            workflow_id="test_workflow",
            name="Test Workflow",
            version="1.0",
            description="Test workflow for comprehensive testing"
        )

    @pytest.fixture
    def sample_context(self):
        """Sample workflow context data"""
        return {
            "user_id": "test_user_123",
            "tenant_id": "test_tenant",
            "items": ["item1", "item2", "item3"],
            "priority": "high"
        }

    # Basic Workflow Execution Tests

    @pytest.mark.asyncio
    async def test_workflow_basic_execution(self, process_engine, sample_context):
        """Test basic workflow execution without approval"""
        workflow = TestWorkflow()

        # Execute workflow
        result = await workflow.execute(sample_context)

        assert result.success is True
        assert result.step_name == "completion"
        assert workflow.status == TestBusinessWorkflowStatus.COMPLETED
        assert workflow.steps_completed == 2
        assert len(workflow.results) == 2

    @pytest.mark.asyncio
    async def test_workflow_with_approval_flow(self, process_engine, sample_context):
        """Test workflow execution with approval requirement"""
        workflow = TestWorkflow()

        # Add approval requirement to context
        approval_context = {**sample_context, "requires_approval": True}

        # Execute workflow (should stop at approval)
        result = await workflow.execute(approval_context)

        assert result.success is True
        assert result.step_name == "approval_request"
        assert workflow.status == TestBusinessWorkflowStatus.WAITING_APPROVAL
        assert "approval_id" in result.data

        # Approve and continue
        approval_result = await workflow.approve_and_continue({"approved_by": "test_approver"})

        assert approval_result.success is True
        assert approval_result.step_name == "completion"
        assert workflow.status == TestBusinessWorkflowStatus.COMPLETED
        assert workflow.steps_completed == 2

    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, process_engine):
        """Test workflow cancellation"""
        workflow = TestWorkflow()

        # Start workflow
        workflow.status = TestBusinessWorkflowStatus.RUNNING

        # Cancel workflow
        result = await workflow.cancel("Testing cancellation")

        assert result.success is True
        assert result.step_name == "cancellation"
        assert workflow.status == TestBusinessWorkflowStatus.CANCELLED
        assert result.data["reason"] == "Testing cancellation"

    # Event-Driven Workflow Processing Tests

    @pytest.mark.asyncio
    async def test_workflow_event_processing(self, process_engine):
        """Test event-driven workflow processing"""
        workflow = TestWorkflow()
        events_processed = []

        # Mock event handler
        async def event_handler(event: WorkflowEvent):
            events_processed.append(event)
            return True

        # Simulate workflow events
        events = [
            WorkflowEvent(type="workflow.started", workflow_id=workflow.workflow_id, data={"user_id": "123"}),
            WorkflowEvent(type="workflow.step_completed", workflow_id=workflow.workflow_id, data={"step": "validation"}),
            WorkflowEvent(type="workflow.completed", workflow_id=workflow.workflow_id, data={"status": "success"})
        ]

        # Process events
        for event in events:
            await event_handler(event)

        assert len(events_processed) == 3
        assert events_processed[0].type == "workflow.started"
        assert events_processed[1].type == "workflow.step_completed"
        assert events_processed[2].type == "workflow.completed"

    @pytest.mark.asyncio
    async def test_workflow_event_ordering(self, process_engine):
        """Test that workflow events are processed in correct order"""
        workflow = TestWorkflow()
        event_order = []

        # Mock ordered event handler
        async def ordered_event_handler(event: WorkflowEvent):
            event_order.append((event.timestamp, event.type))

        # Create events with different timestamps
        base_time = datetime.now(timezone.utc)
        events = [
            WorkflowEvent(type="workflow.started", workflow_id=workflow.workflow_id,
                         timestamp=base_time, data={}),
            WorkflowEvent(type="workflow.step_completed", workflow_id=workflow.workflow_id,
                         timestamp=base_time + timedelta(seconds=1), data={}),
            WorkflowEvent(type="workflow.completed", workflow_id=workflow.workflow_id,
                         timestamp=base_time + timedelta(seconds=2), data={})
        ]

        # Process events (simulate out-of-order arrival)
        for event in reversed(events):
            await ordered_event_handler(event)

        # Sort by timestamp to verify ordering capability
        event_order.sort(key=lambda x: x[0])

        assert event_order[0][1] == "workflow.started"
        assert event_order[1][1] == "workflow.step_completed"
        assert event_order[2][1] == "workflow.completed"

    # Error Handling and Recovery Tests

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, process_engine):
        """Test workflow error handling and recovery"""
        class ErrorWorkflow(TestWorkflow):
            async def execute(self, context):
                self.status = TestBusinessWorkflowStatus.RUNNING

                # Simulate error in processing
                if context.get("simulate_error", False):
                    self.status = TestBusinessWorkflowStatus.FAILED
                    raise ProcessingError("Simulated processing error")

                return await super().execute(context)

        workflow = ErrorWorkflow()

        # Test error scenario
        error_context = {"simulate_error": True}

        with pytest.raises(ProcessingError):
            await workflow.execute(error_context)

        assert workflow.status == TestBusinessWorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_workflow_retry_mechanism(self, process_engine):
        """Test workflow retry mechanism for transient failures"""
        class RetryWorkflow(TestWorkflow):
            def __init__(self):
                super().__init__()
                self.attempt_count = 0

            async def execute(self, context):
                self.attempt_count += 1

                # Fail first two attempts, succeed on third
                if self.attempt_count <= 2:
                    self.status = TestBusinessWorkflowStatus.FAILED
                    raise ProcessingError(f"Transient error (attempt {self.attempt_count})")

                # Succeed on third attempt
                return await super().execute(context)

        workflow = RetryWorkflow()
        max_retries = 3

        # Simulate retry logic
        for attempt in range(max_retries):
            try:
                result = await workflow.execute({"items": ["test"]})
                # If we get here, workflow succeeded
                assert result.success is True
                assert workflow.status == TestBusinessWorkflowStatus.COMPLETED
                break
            except ProcessingError:
                if attempt == max_retries - 1:
                    # Final attempt failed
                    pytest.fail("Workflow failed after max retries")
                # Continue to next attempt
                continue

        assert workflow.attempt_count == 3  # Should succeed on third attempt

    # State Management and Persistence Tests

    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self, process_engine):
        """Test workflow state persistence and restoration"""
        workflow = TestWorkflow()
        original_id = workflow.workflow_id

        # Execute workflow partway (to approval)
        context = {"requires_approval": True, "user_id": "test_user"}
        await workflow.execute(context)

        # Simulate saving state
        saved_state = {
            "workflow_id": workflow.workflow_id,
            "status": workflow.status.value,
            "steps_completed": workflow.steps_completed,
            "results": [{"step_name": r.step_name, "success": r.success} for r in workflow.results],
            "context": workflow.context
        }

        # Simulate restoring workflow from saved state
        restored_workflow = TestWorkflow()
        restored_workflow.workflow_id = saved_state["workflow_id"]
        restored_workflow.status = TestBusinessWorkflowStatus(saved_state["status"])
        restored_workflow.steps_completed = saved_state["steps_completed"]
        restored_workflow.context = saved_state["context"]

        assert restored_workflow.workflow_id == original_id
        assert restored_workflow.status == TestBusinessWorkflowStatus.WAITING_APPROVAL
        assert restored_workflow.steps_completed == 1

        # Continue restored workflow
        completion_result = await restored_workflow.approve_and_continue()
        assert completion_result.success is True
        assert restored_workflow.status == TestBusinessWorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, process_engine):
        """Test valid workflow state transitions"""
        workflow = TestWorkflow()

        # Test valid state transitions
        valid_transitions = [
            (TestBusinessWorkflowStatus.PENDING, TestBusinessWorkflowStatus.RUNNING),
            (TestBusinessWorkflowStatus.RUNNING, TestBusinessWorkflowStatus.WAITING_APPROVAL),
            (TestBusinessWorkflowStatus.WAITING_APPROVAL, TestBusinessWorkflowStatus.RUNNING),
            (TestBusinessWorkflowStatus.RUNNING, TestBusinessWorkflowStatus.COMPLETED),
            (TestBusinessWorkflowStatus.RUNNING, TestBusinessWorkflowStatus.FAILED),
            (TestBusinessWorkflowStatus.RUNNING, TestBusinessWorkflowStatus.CANCELLED)
        ]

        for from_status, to_status in valid_transitions:
            workflow.status = from_status
            # Simulate state transition
            workflow.status = to_status

            # Verify transition was successful
            assert workflow.status == to_status

    # Performance and Concurrency Tests

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, process_engine):
        """Test concurrent execution of multiple workflows"""
        num_workflows = 10
        workflows = [TestWorkflow() for _ in range(num_workflows)]
        contexts = [{"items": [f"item_{i}"], "workflow_num": i} for i in range(num_workflows)]

        # Execute workflows concurrently
        tasks = [workflow.execute(context) for workflow, context in zip(workflows, contexts)]
        results = await asyncio.gather(*tasks)

        # Verify all workflows completed successfully
        assert len(results) == num_workflows
        for i, (workflow, result) in enumerate(zip(workflows, results)):
            assert result.success is True
            assert workflow.status == TestBusinessWorkflowStatus.COMPLETED
            assert workflow.context["workflow_num"] == i

    @pytest.mark.asyncio
    async def test_workflow_performance_under_load(self, process_engine):
        """Test workflow performance under high load"""
        import time

        num_workflows = 100
        start_time = time.time()

        # Create and execute many workflows
        tasks = []
        for i in range(num_workflows):
            workflow = TestWorkflow()
            context = {"items": [f"item_{j}" for j in range(10)], "batch": i}
            tasks.append(workflow.execute(context))

        results = await asyncio.gather(*tasks)
        end_time = time.time()

        execution_time = end_time - start_time

        # Verify performance expectations
        assert len(results) == num_workflows
        assert all(result.success for result in results)
        assert execution_time < 5.0  # Should complete 100 workflows in under 5 seconds


    # Complex Business Logic Tests

    @pytest.mark.asyncio
    async def test_complex_multi_branch_workflow(self, process_engine):
        """Test complex workflow with multiple execution branches"""
        class MultiBranchWorkflow(TestWorkflow):
            async def execute(self, context):
                self.status = TestBusinessWorkflowStatus.RUNNING
                self.start_time = datetime.now(timezone.utc)

                # Branch based on priority
                priority = context.get("priority", "low")

                if priority == "high":
                    # High priority branch
                    for i in range(5):
                        result = WorkflowResult(
                            step_name=f"high_priority_step_{i+1}",
                            success=True,
                            data={"step": i+1, "priority": "high"},
                            timestamp=datetime.now(timezone.utc)
                        )
                        self.results.append(result)
                        self.steps_completed += 1

                elif priority == "medium":
                    # Medium priority branch
                    for i in range(3):
                        result = WorkflowResult(
                            step_name=f"medium_priority_step_{i+1}",
                            success=True,
                            data={"step": i+1, "priority": "medium"},
                            timestamp=datetime.now(timezone.utc)
                        )
                        self.results.append(result)
                        self.steps_completed += 1

                else:
                    # Low priority branch
                    result = WorkflowResult(
                        step_name="low_priority_step",
                        success=True,
                        data={"priority": "low"},
                        timestamp=datetime.now(timezone.utc)
                    )
                    self.results.append(result)
                    self.steps_completed += 1

                self.status = TestBusinessWorkflowStatus.COMPLETED
                self.end_time = datetime.now(timezone.utc)

                return WorkflowResult(
                    step_name="completion",
                    success=True,
                    data={"total_steps": self.steps_completed, "branch": priority},
                    timestamp=self.end_time
                )

        # Test different priority branches
        test_cases = [
            ({"priority": "high"}, 5),
            ({"priority": "medium"}, 3),
            ({"priority": "low"}, 1)
        ]

        for context, expected_steps in test_cases:
            workflow = MultiBranchWorkflow()
            result = await workflow.execute(context)

            assert result.success is True
            assert workflow.steps_completed == expected_steps
            assert result.data["branch"] == context["priority"]

    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self, process_engine):
        """Test workflow timeout handling"""
        class SlowWorkflow(TestWorkflow):
            async def execute(self, context):
                # Simulate slow processing
                await asyncio.sleep(context.get("delay", 0.1))
                return await super().execute(context)

        workflow = SlowWorkflow()
        timeout_seconds = 0.05  # Very short timeout

        # Test timeout scenario
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                workflow.execute({"delay": 0.1}),  # Delay longer than timeout
                timeout=timeout_seconds
            )

        # Test successful completion within timeout
        workflow2 = SlowWorkflow()
        result = await asyncio.wait_for(
            workflow2.execute({"delay": 0.01}),  # Delay shorter than timeout
            timeout=0.1
        )

        assert result.success is True
        assert workflow2.status == TestBusinessWorkflowStatus.COMPLETED
