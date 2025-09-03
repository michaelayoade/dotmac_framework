"""
Tests for saga workflow functionality.
"""

import asyncio
import pytest
from datetime import datetime, timezone

from dotmac.tasks import (
    BackgroundOperationsManager,
    MemoryStorage,
    OperationStatus,
    SagaStepStatus,
)
from dotmac.tasks.storage.base import LockAcquisitionError


class TestSagaWorkflows:
    """Test saga workflow operations."""

    @pytest.fixture
    async def manager(self):
        """Create manager with memory storage."""
        storage = MemoryStorage()
        manager = BackgroundOperationsManager(storage=storage)
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.fixture
    def mock_handlers(self, manager):
        """Set up mock operation handlers."""
        results = {}
        
        async def send_email_handler(params):
            email_id = f"email_{params['to']}"
            results[email_id] = params
            return {"message_id": email_id, "status": "sent"}
        
        async def create_user_handler(params):
            user_id = f"user_{params['username']}"
            results[user_id] = params
            return {"user_id": user_id, "status": "created"}
        
        async def provision_service_handler(params):
            service_id = f"service_{params['type']}"
            results[service_id] = params
            return {"service_id": service_id, "status": "provisioned"}
        
        async def send_email_compensation(params):
            # Mark email as cancelled
            email_id = f"email_{params['to']}"
            if email_id in results:
                results[email_id]["cancelled"] = True
        
        async def delete_user_compensation(params):
            # Remove user
            user_id = f"user_{params['username']}"
            results.pop(user_id, None)
        
        async def deprovision_service_compensation(params):
            # Remove service
            service_id = f"service_{params['type']}"
            results.pop(service_id, None)
        
        # Register handlers
        manager.register_operation_handler("send_email", send_email_handler)
        manager.register_operation_handler("create_user", create_user_handler)
        manager.register_operation_handler("provision_service", provision_service_handler)
        
        # Register compensations
        manager.register_compensation_handler("send_email", send_email_compensation)
        manager.register_compensation_handler("create_user", delete_user_compensation)
        manager.register_compensation_handler("provision_service", deprovision_service_compensation)
        
        return results

    async def test_create_saga_workflow(self, manager):
        """Test creating saga workflows."""
        steps = [
            {
                "name": "Send Welcome Email",
                "operation": "send_email",
                "parameters": {"to": "user@example.com", "template": "welcome"},
                "compensation_operation": "send_email",
                "compensation_parameters": {"to": "user@example.com", "template": "welcome_cancelled"},
            },
            {
                "name": "Create User Account", 
                "operation": "create_user",
                "parameters": {"username": "testuser", "email": "user@example.com"},
                "compensation_operation": "create_user",
                "compensation_parameters": {"username": "testuser"},
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="user_onboarding",
            steps=steps
        )
        
        assert saga.tenant_id == "tenant1"
        assert saga.workflow_type == "user_onboarding"
        assert len(saga.steps) == 2
        assert saga.status == OperationStatus.PENDING
        assert saga.current_step == 0
        
        # Check steps were created properly
        step1 = saga.steps[0]
        assert step1.name == "Send Welcome Email"
        assert step1.operation == "send_email"
        assert step1.status == SagaStepStatus.PENDING

    async def test_saga_successful_execution(self, manager, mock_handlers):
        """Test successful saga execution."""
        steps = [
            {
                "name": "Create User",
                "operation": "create_user", 
                "parameters": {"username": "testuser", "email": "user@example.com"},
                "compensation_operation": "create_user",
                "compensation_parameters": {"username": "testuser"},
            },
            {
                "name": "Send Welcome Email",
                "operation": "send_email",
                "parameters": {"to": "user@example.com", "template": "welcome"},
                "compensation_operation": "send_email",
                "compensation_parameters": {"to": "user@example.com", "template": "cancelled"},
            },
            {
                "name": "Provision Service",
                "operation": "provision_service",
                "parameters": {"type": "basic", "user": "testuser"},
                "compensation_operation": "provision_service", 
                "compensation_parameters": {"type": "basic", "user": "testuser"},
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="user_onboarding", 
            steps=steps
        )
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is True
        
        # Check final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        final_saga = type(saga).from_dict(final_saga_data)
        
        assert final_saga.status == OperationStatus.COMPLETED
        assert final_saga.current_step == len(steps)
        
        # Check all steps completed
        for step in final_saga.steps:
            assert step.status == SagaStepStatus.COMPLETED
            assert step.result is not None
            assert step.error is None
        
        # Check handlers were called
        assert "user_testuser" in mock_handlers
        assert "email_user@example.com" in mock_handlers
        assert "service_basic" in mock_handlers

    async def test_saga_failure_with_compensation(self, manager, mock_handlers):
        """Test saga failure triggers compensation."""
        # Add a failing handler
        async def failing_handler(params):
            raise RuntimeError("Service provisioning failed")
        
        manager.register_operation_handler("failing_operation", failing_handler)
        
        steps = [
            {
                "name": "Create User",
                "operation": "create_user",
                "parameters": {"username": "testuser", "email": "user@example.com"},
                "compensation_operation": "create_user",
                "compensation_parameters": {"username": "testuser"},
            },
            {
                "name": "Send Welcome Email",
                "operation": "send_email",
                "parameters": {"to": "user@example.com", "template": "welcome"},
                "compensation_operation": "send_email",
                "compensation_parameters": {"to": "user@example.com", "template": "cancelled"},
            },
            {
                "name": "Failing Step",
                "operation": "failing_operation",
                "parameters": {"data": "test"},
                "max_retries": 1,  # Fail quickly
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="failing_workflow",
            steps=steps
        )
        
        # Execute saga (should fail and compensate)
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is False
        
        # Check final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        final_saga = type(saga).from_dict(final_saga_data)
        
        assert final_saga.status == OperationStatus.COMPENSATED
        
        # Check step states
        assert final_saga.steps[0].status == SagaStepStatus.COMPENSATED  # User creation compensated
        assert final_saga.steps[1].status == SagaStepStatus.COMPENSATED  # Email compensated
        assert final_saga.steps[2].status == SagaStepStatus.FAILED       # Failing step failed
        
        # Check compensation was executed
        assert "user_testuser" not in mock_handlers  # User was deleted
        assert mock_handlers.get("email_user@example.com", {}).get("cancelled") is True

    async def test_saga_step_retries(self, manager, mock_handlers):
        """Test saga step retry logic."""
        call_count = 0
        
        async def flaky_handler(params):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise RuntimeError(f"Attempt {call_count} failed")
            return {"result": f"success_on_attempt_{call_count}"}
        
        manager.register_operation_handler("flaky_operation", flaky_handler)
        
        steps = [
            {
                "name": "Flaky Operation",
                "operation": "flaky_operation", 
                "parameters": {"data": "test"},
                "max_retries": 3,  # Allow 3 retries (4 total attempts)
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="retry_test",
            steps=steps
        )
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is True
        
        # Check final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        final_saga = type(saga).from_dict(final_saga_data)
        
        assert final_saga.status == OperationStatus.COMPLETED
        assert final_saga.steps[0].status == SagaStepStatus.COMPLETED
        assert final_saga.steps[0].retry_count == 2  # 2 retries (3rd attempt succeeded)
        assert call_count == 3

    async def test_saga_step_max_retries_exceeded(self, manager):
        """Test saga step failure after max retries."""
        async def always_failing_handler(params):
            raise RuntimeError("Always fails")
        
        manager.register_operation_handler("always_failing", always_failing_handler)
        
        steps = [
            {
                "name": "Always Failing",
                "operation": "always_failing",
                "parameters": {"data": "test"},
                "max_retries": 2,
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="max_retries_test",
            steps=steps
        )
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is False
        
        # Check final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        final_saga = type(saga).from_dict(final_saga_data)
        
        assert final_saga.status == OperationStatus.COMPENSATED
        assert final_saga.steps[0].status == SagaStepStatus.FAILED
        assert final_saga.steps[0].retry_count == 2  # Max retries reached
        assert "Always fails" in final_saga.steps[0].error

    async def test_saga_with_idempotency_key(self, manager, mock_handlers):
        """Test saga with associated idempotency key."""
        # Create idempotency key first
        idempotency_key = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user1",
            operation_type="user_onboarding",
            parameters={"username": "testuser"}
        )
        
        steps = [
            {
                "name": "Create User",
                "operation": "create_user",
                "parameters": {"username": "testuser", "email": "user@example.com"},
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="user_onboarding",
            steps=steps,
            idempotency_key=idempotency_key.key
        )
        
        assert saga.idempotency_key == idempotency_key.key
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is True

    async def test_saga_concurrent_execution_lock(self, manager, mock_handlers):
        """Test saga concurrent execution prevention."""
        steps = [
            {
                "name": "Slow Operation",
                "operation": "create_user",
                "parameters": {"username": "testuser", "email": "user@example.com"},
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="concurrent_test",
            steps=steps
        )
        
        # Start first execution
        execution1_task = asyncio.create_task(
            manager.execute_saga_workflow(saga.saga_id)
        )
        
        # Wait a bit to ensure first execution starts
        await asyncio.sleep(0.1)
        
        # Try to start second execution (should fail to acquire lock)
        with pytest.raises(LockAcquisitionError):
            await manager.execute_saga_workflow(saga.saga_id)
        
        # Wait for first execution to complete
        success = await execution1_task
        assert success is True

    async def test_saga_history_tracking(self, manager, mock_handlers):
        """Test saga execution history tracking."""
        steps = [
            {
                "name": "Step 1",
                "operation": "create_user",
                "parameters": {"username": "testuser", "email": "user@example.com"},
            },
            {
                "name": "Step 2", 
                "operation": "send_email",
                "parameters": {"to": "user@example.com", "template": "welcome"},
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="history_test",
            steps=steps
        )
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is True
        
        # Check history
        history = await manager.storage.get_saga_history(saga.saga_id)
        assert len(history) >= 2  # At least one entry per step
        
        # Check history entries
        for entry in history:
            assert "timestamp" in entry
            assert "step_id" in entry
            assert "step_name" in entry
            assert "status" in entry

    async def test_saga_timeout(self, manager):
        """Test saga timeout handling."""
        steps = [
            {
                "name": "Normal Step",
                "operation": "create_user",
                "parameters": {"username": "testuser", "email": "user@example.com"},
            }
        ]
        
        # Create saga with very short timeout
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="timeout_test",
            steps=steps,
            timeout_seconds=1
        )
        
        # Manually set created_at to past time to simulate timeout
        saga_data = saga.to_dict()
        saga_data["created_at"] = (
            datetime.now(timezone.utc) - 
            timedelta(seconds=2)
        ).isoformat()
        await manager.storage.set_saga(saga.saga_id, saga_data)
        
        # Execute should detect timeout
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is False
        
        # Check final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        final_saga = type(saga).from_dict(final_saga_data)
        
        assert final_saga.status == OperationStatus.FAILED

    async def test_saga_missing_handler(self, manager):
        """Test saga with missing operation handler."""
        steps = [
            {
                "name": "Missing Handler",
                "operation": "nonexistent_operation",
                "parameters": {"data": "test"},
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="missing_handler_test",
            steps=steps
        )
        
        # Execute should fail due to missing handler
        success = await manager.execute_saga_workflow(saga.saga_id)
        assert success is False
        
        # Check final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        final_saga = type(saga).from_dict(final_saga_data)
        
        assert final_saga.status == OperationStatus.COMPENSATED
        assert final_saga.steps[0].status == SagaStepStatus.FAILED
        assert "No handler registered" in final_saga.steps[0].error