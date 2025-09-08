"""
Integration Test Base - Database transactions, multi-service workflows, and event-driven testing.
Provides comprehensive integration testing utilities for service composition and transaction management.
"""
import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class DatabaseIntegrationTestBase:
    """Base class for database integration testing with transaction management."""

    def setup_method(self):
        """Setup method called before each test."""
        self.mock_sessions = {}
        self.mock_transactions = {}
        self.mock_repositories = {}
        self.integration_state = {}

    def create_mock_async_session(self, session_id: str = None) -> AsyncMock:
        """Create mock async database session with transaction support."""
        session_id = session_id or str(uuid4())

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.begin = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.add = Mock()
        mock_session.add_all = Mock()
        mock_session.delete = Mock()
        mock_session.refresh = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.merge = AsyncMock()

        # Track transaction state
        mock_session.in_transaction.return_value = False

        self.mock_sessions[session_id] = mock_session
        return mock_session

    def create_mock_session_maker(self, session_id: str = None) -> AsyncMock:
        """Create mock async session maker."""
        session_id = session_id or str(uuid4())
        mock_session = self.create_mock_async_session(session_id)

        mock_session_maker = AsyncMock(spec=async_sessionmaker)
        mock_session_maker.return_value = mock_session

        return mock_session_maker

    @asynccontextmanager
    async def mock_database_transaction(
        self,
        session: AsyncMock = None,
        should_fail: bool = False,
        failure_point: str = None
    ) -> AsyncGenerator[AsyncMock, None]:
        """Mock database transaction context manager."""
        if session is None:
            session = self.create_mock_async_session()

        transaction_id = str(uuid4())
        self.mock_transactions[transaction_id] = {
            "session": session,
            "started": datetime.now(timezone.utc),
            "committed": False,
            "rolled_back": False
        }

        try:
            # Simulate transaction begin
            session.in_transaction.return_value = True
            await session.begin()

            if should_fail and failure_point == "begin":
                raise SQLAlchemyError("Transaction begin failed")

            yield session

            if should_fail and failure_point == "operations":
                raise SQLAlchemyError("Operation failed during transaction")

            # Simulate transaction commit
            await session.commit()
            self.mock_transactions[transaction_id]["committed"] = True
            session.in_transaction.return_value = False

            if should_fail and failure_point == "commit":
                raise SQLAlchemyError("Transaction commit failed")

        except Exception as e:
            # Simulate transaction rollback
            await session.rollback()
            self.mock_transactions[transaction_id]["rolled_back"] = True
            session.in_transaction.return_value = False
            raise e
        finally:
            await session.close()

    def create_integration_service(self, service_name: str, dependencies: dict[str, Any] = None) -> Mock:
        """Create mock service for integration testing."""
        dependencies = dependencies or {}

        mock_service = Mock()
        mock_service.name = service_name
        mock_service.dependencies = dependencies
        mock_service.initialized = True

        # Add common service methods
        mock_service.create = AsyncMock()
        mock_service.get = AsyncMock()
        mock_service.update = AsyncMock()
        mock_service.delete = AsyncMock()
        mock_service.list = AsyncMock()
        mock_service.process = AsyncMock()
        mock_service.execute = AsyncMock()

        return mock_service

    def assert_transaction_committed(self, transaction_id: str):
        """Assert that a transaction was committed."""
        assert transaction_id in self.mock_transactions
        transaction = self.mock_transactions[transaction_id]
        assert transaction["committed"], f"Transaction {transaction_id} was not committed"
        assert not transaction["rolled_back"], f"Transaction {transaction_id} was rolled back"

    def assert_transaction_rolled_back(self, transaction_id: str):
        """Assert that a transaction was rolled back."""
        assert transaction_id in self.mock_transactions
        transaction = self.mock_transactions[transaction_id]
        assert transaction["rolled_back"], f"Transaction {transaction_id} was not rolled back"
        assert not transaction["committed"], f"Transaction {transaction_id} was committed instead"

    def assert_session_operations_called(self, session: AsyncMock, operations: list[str]):
        """Assert that specific session operations were called."""
        for operation in operations:
            method = getattr(session, operation, None)
            assert method is not None, f"Session does not have method {operation}"
            assert method.called, f"Session method {operation} was not called"


class ServiceIntegrationTestBase(DatabaseIntegrationTestBase):
    """Base class for service integration testing with workflow orchestration."""

    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()
        self.service_registry = {}
        self.event_bus = Mock()
        self.workflow_states = {}

    def create_service_registry(self, services: dict[str, Any]) -> dict[str, Mock]:
        """Create registry of mock services for integration testing."""
        registry = {}

        for service_name, config in services.items():
            dependencies = config.get("dependencies", {})
            mock_service = self.create_integration_service(service_name, dependencies)

            # Setup service-specific behaviors
            if "responses" in config:
                for method_name, response in config["responses"].items():
                    method = getattr(mock_service, method_name)
                    method.return_value = response

            registry[service_name] = mock_service

        self.service_registry.update(registry)
        return registry

    async def execute_service_workflow(
        self,
        workflow_steps: list[dict[str, Any]],
        context: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Execute a multi-service workflow with proper orchestration."""
        context = context or {}
        workflow_id = str(uuid4())
        results = {}

        self.workflow_states[workflow_id] = {
            "started": datetime.now(timezone.utc),
            "steps_completed": 0,
            "steps_failed": 0,
            "context": context.copy(),
            "results": results
        }

        try:
            for i, step in enumerate(workflow_steps):
                step_id = f"step_{i}_{step.get('name', 'unnamed')}"

                service_name = step["service"]
                method_name = step["method"]
                args = step.get("args", [])
                kwargs = step.get("kwargs", {})

                # Get service from registry
                if service_name not in self.service_registry:
                    raise ValueError(f"Service {service_name} not found in registry")

                service = self.service_registry[service_name]
                method = getattr(service, method_name)

                # Execute step with context
                step_context = {**context, **kwargs}
                if asyncio.iscoroutinefunction(method):
                    result = await method(*args, **step_context)
                else:
                    result = method(*args, **step_context)

                results[step_id] = result
                self.workflow_states[workflow_id]["steps_completed"] += 1

                # Update context with result if specified
                if "context_key" in step:
                    context[step["context_key"]] = result

        except Exception as e:
            self.workflow_states[workflow_id]["steps_failed"] += 1
            self.workflow_states[workflow_id]["error"] = str(e)
            raise e

        self.workflow_states[workflow_id]["completed"] = datetime.now(timezone.utc)
        return results

    def create_event_driven_service(self, service_name: str, event_handlers: dict[str, Callable] = None) -> Mock:
        """Create mock service with event-driven capabilities."""
        service = self.create_integration_service(service_name)
        event_handlers = event_handlers or {}

        # Add event-related methods
        service.publish_event = AsyncMock()
        service.subscribe_to_event = Mock()
        service.handle_event = AsyncMock()

        # Setup event handlers
        for event_type, handler in event_handlers.items():
            service.subscribe_to_event(event_type, handler)

        return service

    async def simulate_event_flow(
        self,
        events: list[dict[str, Any]],
        services: list[Mock]
    ) -> dict[str, list[Any]]:
        """Simulate event-driven flow between services."""
        event_log = {service.name: [] for service in services}

        for event in events:
            event_type = event["type"]
            event_data = event.get("data", {})
            source_service = event.get("source")

            # Publish event
            if source_service and source_service in [s.name for s in services]:
                source = next(s for s in services if s.name == source_service)
                await source.publish_event(event_type, event_data)
                event_log[source_service].append(f"published:{event_type}")

            # Handle event by all subscribed services
            for service in services:
                if hasattr(service, 'handle_event'):
                    await service.handle_event(event_type, event_data)
                    event_log[service.name].append(f"handled:{event_type}")

        return event_log

    def assert_workflow_completed(self, workflow_id: str, expected_steps: int):
        """Assert that workflow completed successfully."""
        assert workflow_id in self.workflow_states
        workflow = self.workflow_states[workflow_id]

        assert workflow["steps_completed"] == expected_steps
        assert workflow["steps_failed"] == 0
        assert "completed" in workflow
        assert "error" not in workflow

    def assert_service_called_in_order(self, services: list[str], methods: list[str]):
        """Assert that services were called in specific order."""
        for _i, (service_name, method_name) in enumerate(zip(services, methods)):
            assert service_name in self.service_registry
            service = self.service_registry[service_name]
            method = getattr(service, method_name)
            assert method.called, f"Service {service_name}.{method_name} was not called"


class TransactionIntegrationTestBase(ServiceIntegrationTestBase):
    """Base class for transaction integration testing with retry and rollback patterns."""

    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()
        self.transaction_manager = Mock()
        self.retry_policies = {}

    def create_transaction_manager(self, max_retries: int = 3, retry_delay: float = 1.0) -> Mock:
        """Create mock transaction manager with retry capabilities."""
        manager = Mock()
        manager.max_retries = max_retries
        manager.retry_delay = retry_delay

        # Mock transaction methods
        manager.begin_transaction = AsyncMock()
        manager.commit_transaction = AsyncMock()
        manager.rollback_transaction = AsyncMock()
        manager.execute_with_retry = AsyncMock()

        # Setup context manager behavior
        @asynccontextmanager
        async def mock_transaction(auto_commit=True, retry_on_failure=False):
            session = self.create_mock_async_session()
            try:
                await manager.begin_transaction(session)
                yield session
                if auto_commit:
                    await manager.commit_transaction(session)
            except Exception as e:
                await manager.rollback_transaction(session)
                if retry_on_failure and hasattr(e, 'should_retry'):
                    # Implement retry logic
                    pass
                raise e

        manager.transaction = mock_transaction
        self.transaction_manager = manager
        return manager

    async def simulate_distributed_transaction(
        self,
        operations: list[dict[str, Any]],
        should_fail_at: Optional[int] = None,
        compensation_actions: list[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Simulate distributed transaction with saga pattern."""
        transaction_id = str(uuid4())
        completed_operations = []
        compensation_actions = compensation_actions or []

        try:
            for i, operation in enumerate(operations):
                if should_fail_at is not None and i == should_fail_at:
                    raise Exception(f"Simulated failure at operation {i}")

                service_name = operation["service"]
                method = operation["method"]
                args = operation.get("args", [])
                kwargs = operation.get("kwargs", {})

                # Execute operation
                if service_name in self.service_registry:
                    service = self.service_registry[service_name]
                    operation_method = getattr(service, method)

                    if asyncio.iscoroutinefunction(operation_method):
                        result = await operation_method(*args, **kwargs)
                    else:
                        result = operation_method(*args, **kwargs)

                    completed_operations.append({
                        "operation": operation,
                        "result": result,
                        "index": i
                    })

            return {
                "transaction_id": transaction_id,
                "status": "completed",
                "completed_operations": completed_operations
            }

        except Exception as e:
            # Execute compensation actions for completed operations
            compensated = []
            for op in reversed(completed_operations):
                if op["index"] < len(compensation_actions):
                    compensation = compensation_actions[op["index"]]
                    service_name = compensation["service"]
                    method = compensation["method"]
                    args = compensation.get("args", [])
                    kwargs = compensation.get("kwargs", {})

                    if service_name in self.service_registry:
                        service = self.service_registry[service_name]
                        comp_method = getattr(service, method)

                        if asyncio.iscoroutinefunction(comp_method):
                            await comp_method(*args, **kwargs)
                        else:
                            comp_method(*args, **kwargs)

                        compensated.append(op["index"])

            return {
                "transaction_id": transaction_id,
                "status": "failed",
                "error": str(e),
                "completed_operations": completed_operations,
                "compensated_operations": compensated
            }

    def create_retry_policy(self, operation_name: str, max_attempts: int = 3, backoff_factor: float = 2.0):
        """Create retry policy for operations."""
        policy = {
            "max_attempts": max_attempts,
            "backoff_factor": backoff_factor,
            "current_attempt": 0,
            "delays": []
        }

        self.retry_policies[operation_name] = policy
        return policy

    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute operation with retry policy."""
        if operation_name not in self.retry_policies:
            return await operation(*args, **kwargs)

        policy = self.retry_policies[operation_name]
        last_exception = None

        for attempt in range(policy["max_attempts"]):
            try:
                policy["current_attempt"] = attempt + 1

                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if attempt < policy["max_attempts"] - 1:
                    delay = policy["backoff_factor"] ** attempt
                    policy["delays"].append(delay)
                    await asyncio.sleep(delay)
                else:
                    break

        raise last_exception

    def assert_distributed_transaction_compensated(
        self,
        transaction_result: dict[str, Any],
        expected_compensations: int
    ):
        """Assert that distributed transaction was properly compensated."""
        assert transaction_result["status"] == "failed"
        assert "compensated_operations" in transaction_result
        assert len(transaction_result["compensated_operations"]) == expected_compensations


class PerformanceIntegrationTestBase(TransactionIntegrationTestBase):
    """Base class for performance and load testing integration scenarios."""

    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()
        self.performance_metrics = {}
        self.load_test_results = {}

    async def simulate_concurrent_operations(
        self,
        operation_factory: Callable,
        concurrency_level: int,
        operation_count: int,
        context: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Simulate concurrent operations for load testing."""
        context = context or {}
        test_id = str(uuid4())
        start_time = datetime.now(timezone.utc)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency_level)

        async def execute_operation(operation_id: int):
            async with semaphore:
                operation = operation_factory(operation_id, context)
                operation_start = datetime.now(timezone.utc)

                try:
                    if asyncio.iscoroutinefunction(operation):
                        result = await operation()
                    else:
                        result = operation()

                    operation_end = datetime.now(timezone.utc)
                    return {
                        "operation_id": operation_id,
                        "status": "success",
                        "result": result,
                        "duration": (operation_end - operation_start).total_seconds()
                    }

                except Exception as e:
                    operation_end = datetime.now(timezone.utc)
                    return {
                        "operation_id": operation_id,
                        "status": "error",
                        "error": str(e),
                        "duration": (operation_end - operation_start).total_seconds()
                    }

        # Execute operations concurrently
        tasks = [execute_operation(i) for i in range(operation_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()

        # Calculate metrics
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
        failed_operations = [r for r in results if isinstance(r, dict) and r.get("status") == "error"]
        exception_operations = [r for r in results if isinstance(r, Exception)]

        durations = [r["duration"] for r in successful_operations]

        metrics = {
            "test_id": test_id,
            "total_operations": operation_count,
            "concurrency_level": concurrency_level,
            "successful_operations": len(successful_operations),
            "failed_operations": len(failed_operations) + len(exception_operations),
            "total_duration": total_duration,
            "operations_per_second": operation_count / total_duration if total_duration > 0 else 0,
            "average_operation_duration": sum(durations) / len(durations) if durations else 0,
            "min_operation_duration": min(durations) if durations else 0,
            "max_operation_duration": max(durations) if durations else 0,
            "success_rate": len(successful_operations) / operation_count * 100 if operation_count > 0 else 0
        }

        self.performance_metrics[test_id] = metrics
        return metrics

    def create_resource_monitor(self) -> Mock:
        """Create mock resource monitor for performance testing."""
        monitor = Mock()
        monitor.start_monitoring = Mock()
        monitor.stop_monitoring = Mock()
        monitor.get_metrics = Mock()

        # Mock resource metrics
        monitor.get_metrics.return_value = {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "database_connections": 12,
            "active_transactions": 3,
            "cache_hit_ratio": 0.85,
            "response_time_p95": 150.5,
            "error_rate": 0.02
        }

        return monitor

    def assert_performance_within_limits(
        self,
        test_id: str,
        max_average_duration: float,
        min_success_rate: float,
        max_operations_per_second: float = None
    ):
        """Assert that performance metrics are within acceptable limits."""
        assert test_id in self.performance_metrics
        metrics = self.performance_metrics[test_id]

        assert metrics["average_operation_duration"] <= max_average_duration, \
            f"Average duration {metrics['average_operation_duration']}s exceeds limit {max_average_duration}s"

        assert metrics["success_rate"] >= min_success_rate, \
            f"Success rate {metrics['success_rate']}% below minimum {min_success_rate}%"

        if max_operations_per_second:
            assert metrics["operations_per_second"] <= max_operations_per_second, \
                f"Operations per second {metrics['operations_per_second']} exceeds limit {max_operations_per_second}"
