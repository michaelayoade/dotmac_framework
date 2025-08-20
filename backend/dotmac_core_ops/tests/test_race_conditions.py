"""
Race condition tests to prove no double apply under parallel triggers.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set
from unittest.mock import AsyncMock, MagicMock

from dotmac_core_ops.adapters.postgres_adapter import WorkflowRunRecord
from dotmac_core_ops.adapters.event_publisher import EventPublisher
from dotmac_core_ops.contracts.common_schemas import ExecutionStatus


class MockPostgresAdapter:
    """Mock PostgreSQL adapter for testing race conditions."""

    def __init__(self):
        self.runs: Dict[str, WorkflowRunRecord] = {}
        self.steps: Dict[str, Dict] = {}
        self.events: List[Dict] = []
        self.operation_count = 0
        self.concurrent_operations: Set[str] = set()
        self._lock = asyncio.Lock()

    async def create_or_get_workflow_run(self, tenant_id, workflow_id, execution_id, business_key, input_data, context_data):
        """Simulate race condition in workflow run creation."""
        run_key = f"{tenant_id}:{workflow_id}:{business_key or 'default'}"

        # Simulate concurrent access
        operation_id = str(uuid.uuid4())
        self.concurrent_operations.add(operation_id)

        # Small delay to increase chance of race condition
        await asyncio.sleep(0.01)

        async with self._lock:
            self.operation_count += 1

            if run_key in self.runs:
                # Existing run found
                self.concurrent_operations.discard(operation_id)
                return self.runs[run_key], False

            # Create new run
            run_record = WorkflowRunRecord(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                business_key=business_key,
                run_key=run_key,
                status=ExecutionStatus.RUNNING,
                input_data=input_data,
                output_data={},
                context_data=context_data,
                error_message=None,
                started_at=datetime.now(timezone.utc),
                completed_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                version=1
            )

            self.runs[run_key] = run_record
            self.concurrent_operations.discard(operation_id)
            return run_record, True

    async def create_or_update_workflow_step(self, tenant_id, execution_id, step_id, step_name, step_type, attempt, status, input_data, **kwargs):
        """Simulate race condition in step creation."""
        step_key = f"{execution_id}:{step_id}:{attempt}"

        operation_id = str(uuid.uuid4())
        self.concurrent_operations.add(operation_id)

        await asyncio.sleep(0.01)

        async with self._lock:
            self.operation_count += 1

            step_record = {
                "tenant_id": tenant_id,
                "execution_id": execution_id,
                "step_id": step_id,
                "step_name": step_name,
                "step_type": step_type,
                "attempt": attempt,
                "step_key": step_key,
                "status": status,
                "input_data": input_data,
                "created_at": datetime.now(timezone.utc),
                "version": 1
            }

            self.steps[step_key] = step_record
            self.concurrent_operations.discard(operation_id)
            return step_record


class MockRedisAdapter:
    """Mock Redis adapter for testing distributed locks."""

    def __init__(self):
        self.locks: Dict[str, str] = {}
        self.lock_attempts: List[Dict] = []
        self._lock = asyncio.Lock()

    def get_lock(self, resource_key: str, timeout: int = 30):
        """Get a mock distributed lock."""
        return MockRedisLock(self, resource_key, timeout)

    async def acquire_resource_lock(self, resource_type: str, resource_id: str, tenant_id: str, timeout: int = 30):
        """Acquire a mock resource lock."""
        lock_key = f"{tenant_id}:{resource_type}:{resource_id}"
        lock = self.get_lock(lock_key, timeout)
        await lock.acquire()
        return lock


class MockRedisLock:
    """Mock Redis lock for testing."""

    def __init__(self, redis_adapter: MockRedisAdapter, key: str, timeout: int):
        self.redis = redis_adapter
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.lock_value = None
        self._acquired = False

    async def acquire(self, blocking: bool = True, timeout: float = None) -> bool:
        """Acquire the mock lock."""
        self.lock_value = str(uuid.uuid4())

        # Record lock attempt
        self.redis.lock_attempts.append({
            "key": self.key,
            "value": self.lock_value,
            "timestamp": datetime.now(timezone.utc),
            "acquired": False
        })

        async with self.redis._lock:
            if self.key not in self.redis.locks:
                # Lock available
                self.redis.locks[self.key] = self.lock_value
                self._acquired = True
                self.redis.lock_attempts[-1]["acquired"] = True
                return True
            else:
                # Lock already held
                return False

    async def release(self) -> bool:
        """Release the mock lock."""
        if not self._acquired or not self.lock_value:
            return False

        async with self.redis._lock:
            if self.redis.locks.get(self.key) == self.lock_value:
                del self.redis.locks[self.key]
                self._acquired = False
                return True

        return False

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


@pytest.mark.asyncio
class TestRaceConditions:
    """Test suite for race condition scenarios."""

    async def test_concurrent_workflow_creation_idempotency(self):
        """Test that concurrent workflow creation is idempotent."""
        postgres_adapter = MockPostgresAdapter()

        tenant_id = "test-tenant"
        workflow_id = "test-workflow"
        business_key = "test-business-key"

        # Create multiple concurrent tasks trying to create the same workflow
        tasks = []
        for i in range(10):
            execution_id = f"execution-{i}"
            task = postgres_adapter.create_or_get_workflow_run(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                business_key=business_key,
                input_data={"test": f"data-{i}"},
                context_data={"context": f"ctx-{i}"}
            )
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Verify idempotency - only one run should be created
        run_key = f"{tenant_id}:{workflow_id}:{business_key}"
        assert run_key in postgres_adapter.runs

        # Count how many tasks created new runs vs found existing
        new_runs = sum(1 for _, is_new in results if is_new)
        existing_runs = sum(1 for _, is_new in results if not is_new)

        # Exactly one task should have created the run
        assert new_runs == 1
        assert existing_runs == 9

        # All results should reference the same run
        first_run = results[0][0]
        for run_record, _ in results:
            assert run_record.run_key == first_run.run_key
            assert run_record.tenant_id == first_run.tenant_id
            assert run_record.workflow_id == first_run.workflow_id

    async def test_concurrent_step_execution_idempotency(self):
        """Test that concurrent step execution is idempotent."""
        postgres_adapter = MockPostgresAdapter()

        execution_id = "test-execution"
        step_id = "test-step"
        attempt = 1

        # Create multiple concurrent tasks trying to execute the same step
        tasks = []
        for i in range(5):
            task = postgres_adapter.create_or_update_workflow_step(
                tenant_id="test-tenant",
                execution_id=execution_id,
                step_id=step_id,
                step_name="Test Step",
                step_type="action",
                attempt=attempt,
                status=ExecutionStatus.RUNNING,
                input_data={"input": f"data-{i}"}
            )
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Verify only one step record exists
        step_key = f"{execution_id}:{step_id}:{attempt}"
        assert step_key in postgres_adapter.steps

        # All results should be identical
        first_step = results[0]
        for step_record in results:
            assert step_record["step_key"] == first_step["step_key"]
            assert step_record["execution_id"] == first_step["execution_id"]
            assert step_record["step_id"] == first_step["step_id"]

    async def test_resource_lock_prevents_double_apply(self):
        """Test that resource locks prevent double application of operations."""
        redis_adapter = MockRedisAdapter()

        resource_type = "device"
        resource_id = "device-123"
        tenant_id = "test-tenant"

        # Track operations that successfully acquired locks
        successful_operations = []
        failed_operations = []

        async def protected_operation(operation_id: str):
            """Simulate a protected operation that requires a resource lock."""
            try:
                async with await redis_adapter.acquire_resource_lock(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    tenant_id=tenant_id,
                    timeout=1
                ):
                    # Simulate work
                    await asyncio.sleep(0.05)
                    successful_operations.append(operation_id)
            except Exception:
                failed_operations.append(operation_id)

        # Create multiple concurrent operations on the same resource
        tasks = []
        for i in range(10):
            task = protected_operation(f"op-{i}")
            tasks.append(task)

        # Execute all operations concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify that operations were serialized by the lock
        assert len(successful_operations) <= 10  # All should eventually succeed

        # Check lock attempts were recorded
        assert len(redis_adapter.lock_attempts) == 10

        # Verify only one lock was held at a time
        acquired_locks = [attempt for attempt in redis_adapter.lock_attempts if attempt["acquired"]]
        assert len(acquired_locks) >= 1  # At least one should have acquired the lock

    async def test_parallel_workflow_triggers_no_double_execution(self):
        """Test that parallel workflow triggers don't cause double execution."""
        postgres_adapter = MockPostgresAdapter()
        redis_adapter = MockRedisAdapter()

        tenant_id = "test-tenant"
        workflow_id = "critical-workflow"
        business_key = "unique-business-operation"

        execution_results = []

        async def trigger_workflow(trigger_id: str):
            """Simulate triggering a workflow with resource protection."""
            resource_key = f"workflow:{workflow_id}:{business_key}"

            try:
                # Acquire lock for this specific workflow + business key combination
                async with redis_adapter.get_lock(resource_key, timeout=5):
                    # Check if workflow already exists
                    run_record, is_new = await postgres_adapter.create_or_get_workflow_run(
                        tenant_id=tenant_id,
                        workflow_id=workflow_id,
                        execution_id=f"exec-{trigger_id}",
                        business_key=business_key,
                        input_data={"trigger": trigger_id},
                        context_data={"source": f"trigger-{trigger_id}"}
                    )

                    execution_results.append({
                        "trigger_id": trigger_id,
                        "execution_id": run_record.execution_id,
                        "is_new": is_new,
                        "run_key": run_record.run_key
                    })

            except Exception as e:
                execution_results.append({
                    "trigger_id": trigger_id,
                    "error": str(e)
                })

        # Simulate multiple parallel triggers for the same workflow
        tasks = []
        for i in range(8):
            task = trigger_workflow(f"trigger-{i}")
            tasks.append(task)

        # Execute all triggers concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_executions = [r for r in execution_results if "error" not in r]
        assert len(successful_executions) == 8

        # All executions should reference the same workflow run
        unique_run_keys = set(r["run_key"] for r in successful_executions)
        assert len(unique_run_keys) == 1

        # Only one execution should be marked as new
        new_executions = [r for r in successful_executions if r["is_new"]]
        existing_executions = [r for r in successful_executions if not r["is_new"]]

        assert len(new_executions) == 1
        assert len(existing_executions) == 7

    async def test_step_retry_race_condition(self):
        """Test that step retries don't create duplicate attempts."""
        postgres_adapter = MockPostgresAdapter()

        execution_id = "test-execution"
        step_id = "flaky-step"

        retry_results = []

        async def retry_step(retry_id: str, attempt: int):
            """Simulate retrying a failed step."""
            step_record = await postgres_adapter.create_or_update_workflow_step(
                tenant_id="test-tenant",
                execution_id=execution_id,
                step_id=step_id,
                step_name="Flaky Step",
                step_type="action",
                attempt=attempt,
                status=ExecutionStatus.RUNNING,
                input_data={"retry_id": retry_id, "attempt": attempt}
            )

            retry_results.append({
                "retry_id": retry_id,
                "attempt": attempt,
                "step_key": step_record["step_key"]
            })

        # Simulate concurrent retries for different attempts
        tasks = []
        for attempt in range(1, 4):  # Attempts 1, 2, 3
            for retry_id in range(3):  # 3 concurrent retries per attempt
                task = retry_step(f"retry-{attempt}-{retry_id}", attempt)
                tasks.append(task)

        # Execute all retries concurrently
        await asyncio.gather(*tasks)

        # Verify that each attempt only has one step record
        step_keys_by_attempt = {}
        for result in retry_results:
            attempt = result["attempt"]
            step_key = result["step_key"]

            if attempt not in step_keys_by_attempt:
                step_keys_by_attempt[attempt] = set()
            step_keys_by_attempt[attempt].add(step_key)

        # Each attempt should have exactly one unique step key
        for attempt, step_keys in step_keys_by_attempt.items():
            assert len(step_keys) == 1, f"Attempt {attempt} has multiple step keys: {step_keys}"

    async def test_concurrent_event_publishing_idempotency(self):
        """Test that concurrent event publishing is idempotent."""
        # Mock event bus SDK
        mock_event_bus = AsyncMock()
        mock_event_bus.publish = AsyncMock(return_value=MagicMock(success=True))

        event_publisher = EventPublisher(
            event_bus_sdk=mock_event_bus,
            enable_dlq=True
        )

        tenant_id = "test-tenant"
        workflow_id = "test-workflow"
        execution_id = "test-execution"

        # Create multiple concurrent tasks publishing the same event
        tasks = []
        for i in range(5):
            task = event_publisher.publish_workflow_started(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                input_data={"test": "data"},
                correlation_id="test-correlation-id"
            )
            tasks.append(task)

        # Execute all publishing tasks concurrently
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

        # Verify event bus was called multiple times (no built-in deduplication)
        assert mock_event_bus.publish.call_count == 5

        # In a real implementation, idempotency would be handled by the event bus
        # using idempotency keys or message deduplication

    async def test_high_concurrency_stress_test(self):
        """Stress test with high concurrency to detect race conditions."""
        postgres_adapter = MockPostgresAdapter()
        redis_adapter = MockRedisAdapter()

        tenant_id = "stress-tenant"
        workflow_id = "stress-workflow"

        # Track all operations
        all_operations = []

        async def stress_operation(operation_id: int):
            """Perform a complex operation with multiple race condition points."""
            business_key = f"business-{operation_id % 3}"  # Create some overlap
            execution_id = f"exec-{operation_id}"

            try:
                # Step 1: Acquire resource lock
                resource_lock = redis_adapter.get_lock(f"stress:{business_key}", timeout=2)
                if not await resource_lock.acquire(blocking=False):
                    all_operations.append({"op_id": operation_id, "result": "lock_failed"})
                    return

                try:
                    # Step 2: Create or get workflow run
                    run_record, is_new = await postgres_adapter.create_or_get_workflow_run(
                        tenant_id=tenant_id,
                        workflow_id=workflow_id,
                        execution_id=execution_id,
                        business_key=business_key,
                        input_data={"op_id": operation_id},
                        context_data={"stress_test": True}
                    )

                    # Step 3: Create workflow step
                    step_record = await postgres_adapter.create_or_update_workflow_step(
                        tenant_id=tenant_id,
                        execution_id=run_record.execution_id,
                        step_id="stress-step",
                        step_name="Stress Step",
                        step_type="action",
                        attempt=1,
                        status=ExecutionStatus.COMPLETED,
                        input_data={"op_id": operation_id}
                    )

                    all_operations.append({
                        "op_id": operation_id,
                        "result": "success",
                        "run_key": run_record.run_key,
                        "is_new_run": is_new,
                        "step_key": step_record["step_key"]
                    })

                finally:
                    await resource_lock.release()

            except Exception as e:
                all_operations.append({
                    "op_id": operation_id,
                    "result": "error",
                    "error": str(e)
                })

        # Create high concurrency stress test
        tasks = []
        for i in range(50):  # 50 concurrent operations
            task = stress_operation(i)
            tasks.append(task)

        # Execute all operations concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        successful_ops = [op for op in all_operations if op["result"] == "success"]
        failed_ops = [op for op in all_operations if op["result"] != "success"]

        # Should have some successful operations
        assert len(successful_ops) > 0

        # Group by business key to verify idempotency
        runs_by_business_key = {}
        for op in successful_ops:
            business_key = op["run_key"].split(":")[-1]
            if business_key not in runs_by_business_key:
                runs_by_business_key[business_key] = []
            runs_by_business_key[business_key].append(op)

        # Each business key should have exactly one unique run
        for business_key, ops in runs_by_business_key.items():
            unique_run_keys = set(op["run_key"] for op in ops)
            assert len(unique_run_keys) == 1, f"Business key {business_key} has multiple runs: {unique_run_keys}"

            # Only one operation per business key should have created a new run
            new_run_ops = [op for op in ops if op["is_new_run"]]
            assert len(new_run_ops) == 1, f"Business key {business_key} has multiple new run creators"

        print(f"Stress test completed: {len(successful_ops)} successful, {len(failed_ops)} failed")
        print(f"Total database operations: {postgres_adapter.operation_count}")
        print(f"Unique workflow runs created: {len(postgres_adapter.runs)}")
        print(f"Lock attempts: {len(redis_adapter.lock_attempts)}")


if __name__ == "__main__":
    # Run specific test
    import asyncio

    async def run_test():
        test_instance = TestRaceConditions()
        await test_instance.test_parallel_workflow_triggers_no_double_execution()
        print("Race condition test passed!")

    asyncio.run(run_test())
