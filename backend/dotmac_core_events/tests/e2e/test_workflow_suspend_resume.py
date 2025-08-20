"""
End-to-end test for workflow suspend/resume functionality.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
import structlog

from dotmac_core_events.models.envelope import EventEnvelope
from dotmac_core_events.sdks.event_bus import EventBusSDK

logger = structlog.get_logger(__name__)


class WorkflowEngine:
    """Workflow engine with suspend/resume capabilities."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.workflows = {}
        self.suspended_workflows = {}
        self.completed_workflows = set()
        self.failed_workflows = set()

    async def start_workflow(self, workflow_id: str, workflow_type: str, tenant_id: str, data: Dict[str, Any]) -> str:
        """Start a new workflow."""

        workflow = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "tenant_id": tenant_id,
            "status": "running",
            "current_step": 0,
            "steps": self._get_workflow_steps(workflow_type),
            "data": data,
            "started_at": datetime.now(timezone.utc),
            "suspended_at": None,
            "resumed_at": None,
            "suspend_reason": None
        }

        self.workflows[workflow_id] = workflow

        # Publish workflow started event
        await self.event_bus.publish(
            event_type="workflow.started",
            data={
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "tenant_id": tenant_id,
                "steps_count": len(workflow["steps"])
            },
            partition_key=tenant_id
        )

        # Start first step
        await self._execute_step(workflow_id, 0)

        logger.info("Workflow started", workflow_id=workflow_id, type=workflow_type)
        return workflow_id

    async def suspend_workflow(self, workflow_id: str, reason: str = "manual_suspend"):
        """Suspend a running workflow."""

        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]

        if workflow["status"] != "running":
            raise ValueError(f"Cannot suspend workflow {workflow_id} with status {workflow['status']}")

        # Update workflow state
        workflow["status"] = "suspended"
        workflow["suspended_at"] = datetime.now(timezone.utc)
        workflow["suspend_reason"] = reason

        # Move to suspended workflows
        self.suspended_workflows[workflow_id] = workflow

        # Publish workflow suspended event
        await self.event_bus.publish(
            event_type="workflow.suspended",
            data={
                "workflow_id": workflow_id,
                "reason": reason,
                "current_step": workflow["current_step"],
                "suspended_at": workflow["suspended_at"].isoformat()
            },
            partition_key=workflow["tenant_id"]
        )

        logger.info("Workflow suspended", workflow_id=workflow_id, reason=reason)

    async def resume_workflow(self, workflow_id: str):
        """Resume a suspended workflow."""

        if workflow_id not in self.suspended_workflows:
            raise ValueError(f"Suspended workflow {workflow_id} not found")

        workflow = self.suspended_workflows[workflow_id]

        # Update workflow state
        workflow["status"] = "running"
        workflow["resumed_at"] = datetime.now(timezone.utc)

        # Move back to active workflows
        self.workflows[workflow_id] = workflow
        del self.suspended_workflows[workflow_id]

        # Publish workflow resumed event
        await self.event_bus.publish(
            event_type="workflow.resumed",
            data={
                "workflow_id": workflow_id,
                "resumed_at": workflow["resumed_at"].isoformat(),
                "current_step": workflow["current_step"],
                "suspend_duration_seconds": (workflow["resumed_at"] - workflow["suspended_at"]).total_seconds()
            },
            partition_key=workflow["tenant_id"]
        )

        # Continue execution from current step
        await self._execute_step(workflow_id, workflow["current_step"])

        logger.info("Workflow resumed", workflow_id=workflow_id)

    async def handle_step_completed(self, envelope: EventEnvelope):
        """Handle workflow step completion."""
        workflow_id = envelope.data.get("workflow_id")
        step_index = envelope.data.get("step_index")

        if workflow_id not in self.workflows:
            return

        workflow = self.workflows[workflow_id]

        if workflow["status"] != "running":
            return  # Workflow might be suspended

        # Move to next step
        next_step = step_index + 1
        workflow["current_step"] = next_step

        if next_step >= len(workflow["steps"]):
            # Workflow completed
            await self._complete_workflow(workflow_id)
        else:
            # Execute next step
            await self._execute_step(workflow_id, next_step)

    async def handle_step_failed(self, envelope: EventEnvelope):
        """Handle workflow step failure."""
        workflow_id = envelope.data.get("workflow_id")
        step_index = envelope.data.get("step_index")
        error = envelope.data.get("error")

        if workflow_id not in self.workflows:
            return

        workflow = self.workflows[workflow_id]
        workflow["status"] = "failed"
        workflow["failed_at"] = datetime.now(timezone.utc)
        workflow["error"] = error

        self.failed_workflows.add(workflow_id)

        # Publish workflow failed event
        await self.event_bus.publish(
            event_type="workflow.failed",
            data={
                "workflow_id": workflow_id,
                "failed_step": step_index,
                "error": error,
                "failed_at": workflow["failed_at"].isoformat()
            },
            partition_key=workflow["tenant_id"]
        )

        logger.error("Workflow failed", workflow_id=workflow_id, step=step_index, error=error)

    async def _execute_step(self, workflow_id: str, step_index: int):
        """Execute a workflow step."""
        workflow = self.workflows[workflow_id]

        if step_index >= len(workflow["steps"]):
            return

        step = workflow["steps"][step_index]

        # Publish step execution command
        await self.event_bus.publish(
            event_type=f"command.step.{step['type']}",
            data={
                "workflow_id": workflow_id,
                "step_index": step_index,
                "step_name": step["name"],
                "step_config": step.get("config", {}),
                "workflow_data": workflow["data"]
            },
            partition_key=workflow["tenant_id"]
        )

        logger.debug("Executing workflow step", workflow_id=workflow_id, step=step_index, name=step["name"])

    async def _complete_workflow(self, workflow_id: str):
        """Complete a workflow."""
        workflow = self.workflows[workflow_id]
        workflow["status"] = "completed"
        workflow["completed_at"] = datetime.now(timezone.utc)

        self.completed_workflows.add(workflow_id)

        # Publish workflow completed event
        await self.event_bus.publish(
            event_type="workflow.completed",
            data={
                "workflow_id": workflow_id,
                "completed_at": workflow["completed_at"].isoformat(),
                "duration_seconds": (workflow["completed_at"] - workflow["started_at"]).total_seconds(),
                "steps_executed": len(workflow["steps"])
            },
            partition_key=workflow["tenant_id"]
        )

        logger.info("Workflow completed", workflow_id=workflow_id)

    def _get_workflow_steps(self, workflow_type: str) -> List[Dict[str, Any]]:
        """Get workflow steps definition."""
        workflows = {
            "data_processing": [
                {"name": "validate_input", "type": "validation"},
                {"name": "transform_data", "type": "transformation"},
                {"name": "store_results", "type": "storage"},
                {"name": "notify_completion", "type": "notification"}
            ],
            "user_onboarding": [
                {"name": "create_account", "type": "account_creation"},
                {"name": "send_welcome_email", "type": "email"},
                {"name": "setup_preferences", "type": "configuration"},
                {"name": "activate_features", "type": "activation"}
            ],
            "order_processing": [
                {"name": "validate_order", "type": "validation"},
                {"name": "check_inventory", "type": "inventory"},
                {"name": "process_payment", "type": "payment"},
                {"name": "fulfill_order", "type": "fulfillment"},
                {"name": "send_confirmation", "type": "notification"}
            ]
        }

        return workflows.get(workflow_type, [])

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status."""
        if workflow_id in self.workflows:
            return self.workflows[workflow_id].copy()
        elif workflow_id in self.suspended_workflows:
            return self.suspended_workflows[workflow_id].copy()
        return None


class MockStepExecutor:
    """Mock step executor for testing."""

    def __init__(self, event_bus: EventBusSDK):
        self.event_bus = event_bus
        self.execution_delay = 0.1
        self.failure_probability = 0.0
        self.executed_steps = []

    def set_failure_probability(self, probability: float):
        """Set step failure probability."""
        self.failure_probability = max(0.0, min(1.0, probability))

    async def handle_validation_step(self, envelope: EventEnvelope):
        """Handle validation step."""
        await self._execute_step(envelope, "validation")

    async def handle_transformation_step(self, envelope: EventEnvelope):
        """Handle transformation step."""
        await self._execute_step(envelope, "transformation")

    async def handle_storage_step(self, envelope: EventEnvelope):
        """Handle storage step."""
        await self._execute_step(envelope, "storage")

    async def handle_notification_step(self, envelope: EventEnvelope):
        """Handle notification step."""
        await self._execute_step(envelope, "notification")

    async def handle_account_creation_step(self, envelope: EventEnvelope):
        """Handle account creation step."""
        await self._execute_step(envelope, "account_creation")

    async def handle_email_step(self, envelope: EventEnvelope):
        """Handle email step."""
        await self._execute_step(envelope, "email")

    async def handle_configuration_step(self, envelope: EventEnvelope):
        """Handle configuration step."""
        await self._execute_step(envelope, "configuration")

    async def handle_activation_step(self, envelope: EventEnvelope):
        """Handle activation step."""
        await self._execute_step(envelope, "activation")

    async def _execute_step(self, envelope: EventEnvelope, step_type: str):
        """Execute a step with potential failure."""
        workflow_id = envelope.data.get("workflow_id")
        step_index = envelope.data.get("step_index")
        step_name = envelope.data.get("step_name")

        # Record execution
        self.executed_steps.append({
            "workflow_id": workflow_id,
            "step_index": step_index,
            "step_name": step_name,
            "step_type": step_type,
            "executed_at": datetime.now(timezone.utc)
        })

        # Simulate execution delay
        await asyncio.sleep(self.execution_delay)

        # Maybe fail
        import secrets
        if random.random() < self.failure_probability:
            await self.event_bus.publish(
                event_type="event.step.failed",
                data={
                    "workflow_id": workflow_id,
                    "step_index": step_index,
                    "step_name": step_name,
                    "error": f"Simulated failure in {step_type} step"
                },
                partition_key=envelope.data.get("workflow_data", {}).get("tenant_id", "unknown")
            )
            return

        # Success
        await self.event_bus.publish(
            event_type="event.step.completed",
            data={
                "workflow_id": workflow_id,
                "step_index": step_index,
                "step_name": step_name,
                "result": f"{step_type} completed successfully"
            },
            partition_key=envelope.data.get("workflow_data", {}).get("tenant_id", "unknown")
        )


@pytest.fixture
async def event_bus():
    """Create mock event bus."""
    bus = AsyncMock(spec=EventBusSDK)
    bus.published_events = []

    async def mock_publish(event_type, data, **kwargs):
        envelope = EventEnvelope.create(
            event_type=event_type,
            data=data,
            tenant_id=data.get("tenant_id", "test_tenant")
        )
        bus.published_events.append(envelope)
        return {"status": "published", "message_id": f"msg_{len(bus.published_events)}"}

    bus.publish = mock_publish
    return bus


@pytest.fixture
async def workflow_engine(event_bus):
    """Create workflow engine."""
    return WorkflowEngine(event_bus)


@pytest.fixture
async def step_executor(event_bus):
    """Create mock step executor."""
    return MockStepExecutor(event_bus)


class TestWorkflowSuspendResume:
    """Test workflow suspend/resume functionality."""

    @pytest.mark.asyncio
    async def test_workflow_suspend_and_resume(self, workflow_engine, step_executor, event_bus):
        """Test basic workflow suspend and resume."""

        # Start workflow
        workflow_id = "test_workflow_001"
        tenant_id = "tenant_123"

        await workflow_engine.start_workflow(
            workflow_id=workflow_id,
            workflow_type="data_processing",
            tenant_id=tenant_id,
            data={"input_file": "test.csv"}
        )

        # Verify workflow started
        workflow = workflow_engine.get_workflow_status(workflow_id)
        assert workflow["status"] == "running"
        assert workflow["current_step"] == 0

        # Execute first step
        step_envelope = EventEnvelope.create(
            event_type="event.step.completed",
            data={
                "workflow_id": workflow_id,
                "step_index": 0,
                "step_name": "validate_input",
                "result": "validation completed"
            },
            tenant_id=tenant_id
        )
        await workflow_engine.handle_step_completed(step_envelope)

        # Verify step progression
        workflow = workflow_engine.get_workflow_status(workflow_id)
        assert workflow["current_step"] == 1

        # Suspend workflow
        await workflow_engine.suspend_workflow(workflow_id, "maintenance_window")

        # Verify suspension
        assert workflow_id not in workflow_engine.workflows
        assert workflow_id in workflow_engine.suspended_workflows

        suspended_workflow = workflow_engine.suspended_workflows[workflow_id]
        assert suspended_workflow["status"] == "suspended"
        assert suspended_workflow["suspend_reason"] == "maintenance_window"
        assert suspended_workflow["suspended_at"] is not None

        # Resume workflow
        await workflow_engine.resume_workflow(workflow_id)

        # Verify resumption
        assert workflow_id in workflow_engine.workflows
        assert workflow_id not in workflow_engine.suspended_workflows

        resumed_workflow = workflow_engine.get_workflow_status(workflow_id)
        assert resumed_workflow["status"] == "running"
        assert resumed_workflow["resumed_at"] is not None
        assert resumed_workflow["current_step"] == 1  # Should continue from where it left off

    @pytest.mark.asyncio
    async def test_suspend_resume_with_step_execution(self, workflow_engine, step_executor, event_bus):
        """Test suspend/resume with actual step execution."""

        # Set up step handlers
        handlers = {
            "command.step.validation": step_executor.handle_validation_step,
            "command.step.transformation": step_executor.handle_transformation_step,
            "command.step.storage": step_executor.handle_storage_step,
            "command.step.notification": step_executor.handle_notification_step,
            "event.step.completed": workflow_engine.handle_step_completed,
            "event.step.failed": workflow_engine.handle_step_failed
        }

        # Start workflow
        workflow_id = "test_workflow_002"
        tenant_id = "tenant_456"

        await workflow_engine.start_workflow(
            workflow_id=workflow_id,
            workflow_type="data_processing",
            tenant_id=tenant_id,
            data={"input_file": "large_dataset.csv"}
        )

        # Process first step
        published_events = event_bus.published_events.copy()
        for envelope in published_events:
            if envelope.type in handlers:
                await handlers[envelope.type](envelope)

        # Process any new events generated
        while len(event_bus.published_events) > len(published_events):
            new_events = event_bus.published_events[len(published_events):]
            published_events.extend(new_events)

            for envelope in new_events:
                if envelope.type in handlers:
                    await handlers[envelope.type](envelope)

        # Verify first step completed
        workflow = workflow_engine.get_workflow_status(workflow_id)
        assert workflow["current_step"] == 1

        # Suspend after first step
        await workflow_engine.suspend_workflow(workflow_id, "scheduled_maintenance")

        # Verify no further execution while suspended
        initial_executed_count = len(step_executor.executed_steps)
        await asyncio.sleep(0.2)  # Wait to ensure no background execution
        assert len(step_executor.executed_steps) == initial_executed_count

        # Resume workflow
        await workflow_engine.resume_workflow(workflow_id)

        # Process remaining steps
        published_events = event_bus.published_events.copy()
        for envelope in published_events:
            if envelope.type in handlers:
                await handlers[envelope.type](envelope)

        # Process any new events generated
        while len(event_bus.published_events) > len(published_events):
            new_events = event_bus.published_events[len(published_events):]
            published_events.extend(new_events)

            for envelope in new_events:
                if envelope.type in handlers:
                    await handlers[envelope.type](envelope)

        # Verify workflow completed
        assert workflow_id in workflow_engine.completed_workflows
        final_workflow = workflow_engine.get_workflow_status(workflow_id)
        assert final_workflow["status"] == "completed"

    @pytest.mark.asyncio
    async def test_multiple_suspend_resume_cycles(self, workflow_engine, event_bus):
        """Test multiple suspend/resume cycles."""

        # Start workflow
        workflow_id = "test_workflow_003"
        tenant_id = "tenant_789"

        await workflow_engine.start_workflow(
            workflow_id=workflow_id,
            workflow_type="user_onboarding",
            tenant_id=tenant_id,
            data={"user_email": "test@example.com"}
        )

        # First suspend/resume cycle
        await workflow_engine.suspend_workflow(workflow_id, "first_pause")
        await asyncio.sleep(0.1)
        await workflow_engine.resume_workflow(workflow_id)

        # Execute a step
        step_envelope = EventEnvelope.create(
            event_type="event.step.completed",
            data={
                "workflow_id": workflow_id,
                "step_index": 0,
                "step_name": "create_account"
            },
            tenant_id=tenant_id
        )
        await workflow_engine.handle_step_completed(step_envelope)

        # Second suspend/resume cycle
        await workflow_engine.suspend_workflow(workflow_id, "second_pause")
        await asyncio.sleep(0.1)
        await workflow_engine.resume_workflow(workflow_id)

        # Verify workflow state is consistent
        workflow = workflow_engine.get_workflow_status(workflow_id)
        assert workflow["status"] == "running"
        assert workflow["current_step"] == 1
        assert workflow["resumed_at"] is not None

    @pytest.mark.asyncio
    async def test_suspend_resume_with_failures(self, workflow_engine, step_executor, event_bus):
        """Test suspend/resume behavior with step failures."""

        # Set failure probability
        step_executor.set_failure_probability(0.5)

        # Set up handlers
        handlers = {
            "command.step.validation": step_executor.handle_validation_step,
            "event.step.completed": workflow_engine.handle_step_completed,
            "event.step.failed": workflow_engine.handle_step_failed
        }

        # Start workflow
        workflow_id = "test_workflow_004"
        tenant_id = "tenant_fail"

        await workflow_engine.start_workflow(
            workflow_id=workflow_id,
            workflow_type="data_processing",
            tenant_id=tenant_id,
            data={"input_file": "test.csv"}
        )

        # Process events until failure or completion
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            published_events = event_bus.published_events.copy()

            for envelope in published_events:
                if envelope.type in handlers:
                    await handlers[envelope.type](envelope)

            # Check if workflow failed or completed
            if workflow_id in workflow_engine.failed_workflows:
                break
            if workflow_id in workflow_engine.completed_workflows:
                break

            iteration += 1
            await asyncio.sleep(0.1)

        # If workflow failed, try suspend/resume (should handle gracefully)
        if workflow_id in workflow_engine.failed_workflows:
            with pytest.raises(ValueError, match="Cannot suspend workflow"):
                await workflow_engine.suspend_workflow(workflow_id, "after_failure")

    @pytest.mark.asyncio
    async def test_concurrent_workflows_suspend_resume(self, workflow_engine, event_bus):
        """Test suspend/resume with multiple concurrent workflows."""

        # Start multiple workflows
        workflow_ids = []
        for i in range(3):
            workflow_id = f"concurrent_workflow_{i}"
            await workflow_engine.start_workflow(
                workflow_id=workflow_id,
                workflow_type="order_processing",
                tenant_id=f"tenant_{i}",
                data={"order_id": f"order_{i}"}
            )
            workflow_ids.append(workflow_id)

        # Suspend some workflows
        await workflow_engine.suspend_workflow(workflow_ids[0], "suspend_first")
        await workflow_engine.suspend_workflow(workflow_ids[2], "suspend_third")

        # Verify suspension state
        assert workflow_ids[0] in workflow_engine.suspended_workflows
        assert workflow_ids[1] in workflow_engine.workflows  # Still running
        assert workflow_ids[2] in workflow_engine.suspended_workflows

        # Resume one workflow
        await workflow_engine.resume_workflow(workflow_ids[0])

        # Verify state
        assert workflow_ids[0] in workflow_engine.workflows
        assert workflow_ids[1] in workflow_engine.workflows
        assert workflow_ids[2] in workflow_engine.suspended_workflows

        # Resume remaining workflow
        await workflow_engine.resume_workflow(workflow_ids[2])

        # Verify all workflows are running
        for workflow_id in workflow_ids:
            assert workflow_id in workflow_engine.workflows
            workflow = workflow_engine.get_workflow_status(workflow_id)
            assert workflow["status"] == "running"

    @pytest.mark.asyncio
    async def test_suspend_resume_event_publishing(self, workflow_engine, event_bus):
        """Test that suspend/resume publishes appropriate events."""

        # Start workflow
        workflow_id = "test_workflow_events"
        tenant_id = "tenant_events"

        await workflow_engine.start_workflow(
            workflow_id=workflow_id,
            workflow_type="data_processing",
            tenant_id=tenant_id,
            data={"test": "data"}
        )

        initial_event_count = len(event_bus.published_events)

        # Suspend workflow
        await workflow_engine.suspend_workflow(workflow_id, "test_suspend")

        # Verify suspend event was published
        suspend_events = [e for e in event_bus.published_events[initial_event_count:]
                         if e.type == "workflow.suspended"]
        assert len(suspend_events) == 1

        suspend_event = suspend_events[0]
        assert suspend_event.data["workflow_id"] == workflow_id
        assert suspend_event.data["reason"] == "test_suspend"

        # Resume workflow
        resume_event_count = len(event_bus.published_events)
        await workflow_engine.resume_workflow(workflow_id)

        # Verify resume event was published
        resume_events = [e for e in event_bus.published_events[resume_event_count:]
                        if e.type == "workflow.resumed"]
        assert len(resume_events) == 1

        resume_event = resume_events[0]
        assert resume_event.data["workflow_id"] == workflow_id
        assert "suspend_duration_seconds" in resume_event.data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
