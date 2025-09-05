"""
Background Operations Manager - Core orchestration for idempotency and saga workflows.

This module provides the main BackgroundOperationsManager class that handles
idempotent operations, saga workflow orchestration, and operation registry.
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from .models import (
    BackgroundOperation,
    IdempotencyKey,
    OperationStatus,
    SagaHistoryEntry,
    SagaStep,
    SagaStepStatus,
    SagaWorkflow,
)
from .storage.base import LockAcquisitionError, Storage
from .storage.memory import MemoryStorage

logger = logging.getLogger(__name__)


class BackgroundOperationsManager:
    """
    Core manager for background operations, idempotency, and saga workflows.

    This manager provides:
    - Idempotent operations with configurable TTL
    - Saga workflow orchestration with compensation
    - Operation registry and handlers
    - Background cleanup tasks
    - Distributed locking for saga execution
    """

    def __init__(
        self,
        storage: Optional[Storage] = None,
        default_idempotency_ttl: int = 86400,  # 24 hours
        saga_timeout: int = 7200,  # 2 hours
        cleanup_interval: int = 3600,  # 1 hour
        enable_background_cleanup: bool = True,
    ) -> None:
        """
        Initialize the BackgroundOperationsManager.

        Args:
            storage: Storage backend (defaults to MemoryStorage)
            default_idempotency_ttl: Default TTL for idempotency keys in seconds
            saga_timeout: Default timeout for saga execution in seconds
            cleanup_interval: Interval between cleanup tasks in seconds
            enable_background_cleanup: Whether to run background cleanup
        """
        self.storage = storage or MemoryStorage()
        self.default_idempotency_ttl = default_idempotency_ttl
        self.saga_timeout = saga_timeout
        self.cleanup_interval = cleanup_interval
        self.enable_background_cleanup = enable_background_cleanup

        # Operation and compensation handlers
        self._operation_handlers: dict[str, Callable] = {}
        self._compensation_handlers: dict[str, Callable] = {}

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

        # In-memory locks for saga execution (best effort)
        self._saga_locks: dict[str, asyncio.Lock] = {}

    async def start(self) -> None:
        """Start the background operations manager."""
        if self._is_running:
            return

        self._is_running = True

        if self.enable_background_cleanup:
            self._cleanup_task = asyncio.create_task(self._background_cleanup())

        logger.info("BackgroundOperationsManager started")

    async def stop(self) -> None:
        """Stop the background operations manager."""
        if not self._is_running:
            return

        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        await self.storage.close()

        logger.info("BackgroundOperationsManager stopped")

    # Idempotency Methods

    def generate_idempotency_key(
        self,
        tenant_id: str,
        user_id: Optional[str],
        operation_type: str,
        parameters: dict[str, Any],
    ) -> str:
        """
        Generate a deterministic idempotency key.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier (optional)
            operation_type: Type of operation
            parameters: Operation parameters

        Returns:
            Deterministic idempotency key
        """
        # Create deterministic string from inputs
        key_data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "operation_type": operation_type,
            "parameters": parameters,
        }

        # Sort parameters to ensure consistent ordering
        key_string = json.dumps(key_data, sort_keys=True, default=str)

        # Generate SHA256 hash
        hash_obj = hashlib.sha256(key_string.encode("utf-8"))
        return hash_obj.hexdigest()

    async def check_idempotency(self, key: str) -> Optional[IdempotencyKey]:
        """
        Check if an idempotency key exists.

        Args:
            key: The idempotency key

        Returns:
            IdempotencyKey object if found, None otherwise
        """
        try:
            data = await self.storage.get_idempotency(key)
            if data:
                return IdempotencyKey.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to check idempotency key {key}: {e}")
            return None

    async def create_idempotency_key(
        self,
        tenant_id: str,
        user_id: Optional[str],
        operation_type: str,
        key: Optional[str] = None,
        ttl: Optional[int] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> IdempotencyKey:
        """
        Create an idempotency key.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier (optional)
            operation_type: Type of operation
            key: Explicit key (if None, will be generated)
            ttl: Time to live in seconds (uses default if None)
            parameters: Operation parameters for key generation

        Returns:
            Created IdempotencyKey object
        """
        if key is None:
            if parameters is None:
                parameters = {}
            key = self.generate_idempotency_key(
                tenant_id, user_id, operation_type, parameters
            )

        ttl_seconds = ttl or self.default_idempotency_ttl
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        idempotency_key = IdempotencyKey(
            key=key,
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=operation_type,
            created_at=now,
            expires_at=expires_at,
            status=OperationStatus.PENDING,
        )

        # Store in backend
        await self.storage.set_idempotency(key, idempotency_key.to_dict(), ttl_seconds)

        # Index for cleanup
        await self.storage.index_idempotency(key, now.timestamp())

        logger.debug(f"Created idempotency key: {key}")
        return idempotency_key

    async def complete_idempotent_operation(
        self, key: str, result: dict[str, Any], error: Optional[str] = None
    ) -> bool:
        """
        Complete an idempotent operation.

        Args:
            key: The idempotency key
            result: Operation result
            error: Error message if operation failed

        Returns:
            True if operation was completed successfully
        """
        try:
            # Get current data
            current_data = await self.storage.get_idempotency(key)
            if not current_data:
                logger.warning(f"Idempotency key {key} not found")
                return False

            # Update status and result
            current_data["result"] = result
            current_data["status"] = (
                OperationStatus.FAILED.value
                if error
                else OperationStatus.COMPLETED.value
            )
            if error:
                current_data["error"] = error

            # Calculate remaining TTL
            expires_at = datetime.fromisoformat(current_data["expires_at"])
            now = datetime.now(timezone.utc)
            remaining_ttl = int((expires_at - now).total_seconds())

            if remaining_ttl > 0:
                await self.storage.set_idempotency(key, current_data, remaining_ttl)
                logger.debug(f"Completed idempotent operation: {key}")
                return True
            else:
                logger.warning(f"Idempotency key {key} has expired")
                return False

        except Exception as e:
            logger.error(f"Failed to complete idempotent operation {key}: {e}")
            return False

    # Saga Workflow Methods

    async def create_saga_workflow(
        self,
        tenant_id: str,
        workflow_type: str,
        steps: list[dict[str, Any]],
        idempotency_key: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> SagaWorkflow:
        """
        Create a saga workflow.

        Args:
            tenant_id: Tenant identifier
            workflow_type: Type of workflow
            steps: List of step definitions
            idempotency_key: Associated idempotency key (optional)
            timeout_seconds: Workflow timeout (uses default if None)

        Returns:
            Created SagaWorkflow object
        """
        saga_id = str(uuid4())
        timeout = timeout_seconds or self.saga_timeout

        # Convert step dictionaries to SagaStep objects
        saga_steps = []
        for i, step_data in enumerate(steps):
            step = SagaStep(
                step_id=step_data.get("step_id", f"step_{i}"),
                name=step_data["name"],
                operation=step_data["operation"],
                parameters=step_data.get("parameters", {}),
                compensation_operation=step_data.get("compensation_operation"),
                compensation_parameters=step_data.get("compensation_parameters", {}),
                max_retries=step_data.get("max_retries", 3),
            )
            saga_steps.append(step)

        # Create saga workflow
        saga = SagaWorkflow(
            saga_id=saga_id,
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            steps=saga_steps,
            idempotency_key=idempotency_key,
            timeout_seconds=timeout,
        )

        # Store in backend
        await self.storage.set_saga(saga_id, saga.to_dict())

        logger.info(f"Created saga workflow: {saga_id} ({workflow_type})")
        return saga

    def register_operation_handler(
        self, operation_type: str, handler: Callable
    ) -> None:
        """
        Register a handler for an operation type.

        Args:
            operation_type: Type of operation
            handler: Async callable to handle the operation
        """
        self._operation_handlers[operation_type] = handler
        logger.debug(f"Registered operation handler: {operation_type}")

    def register_compensation_handler(
        self, operation_type: str, handler: Callable
    ) -> None:
        """
        Register a compensation handler for an operation type.

        Args:
            operation_type: Type of operation
            handler: Async callable to handle compensation
        """
        self._compensation_handlers[operation_type] = handler
        logger.debug(f"Registered compensation handler: {operation_type}")

    async def execute_saga_workflow(self, saga_id: str) -> bool:
        """
        Execute a saga workflow.

        Args:
            saga_id: The saga workflow ID

        Returns:
            True if saga completed successfully, False otherwise
        """
        # Acquire lock for saga execution
        lock_key = f"saga_execution_{saga_id}"

        if not await self.storage.acquire_lock(lock_key, self.saga_timeout):
            logger.warning(f"Could not acquire lock for saga {saga_id}")
            raise LockAcquisitionError(f"Saga {saga_id} is already being executed")

        try:
            return await self._execute_saga_workflow_locked(saga_id)
        finally:
            await self.storage.release_lock(lock_key)

    async def _execute_saga_workflow_locked(self, saga_id: str) -> bool:
        """Execute saga workflow with lock already acquired."""
        try:
            # Load saga
            saga_data = await self.storage.get_saga(saga_id)
            if not saga_data:
                logger.error(f"Saga {saga_id} not found")
                return False

            saga = SagaWorkflow.from_dict(saga_data)

            # Check if saga is already completed or failed
            if saga.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
                logger.info(f"Saga {saga_id} is already {saga.status}")
                return saga.status == OperationStatus.COMPLETED

            # Check for timeout
            if saga.is_timed_out():
                logger.error(f"Saga {saga_id} has timed out")
                saga.status = OperationStatus.FAILED
                await self.storage.set_saga(saga_id, saga.to_dict())
                await self._record_saga_history(
                    saga_id, "timeout", "saga", SagaStepStatus.FAILED, "Saga timed out"
                )
                return False

            logger.info(f"Executing saga {saga_id} from step {saga.current_step}")

            # Execute steps forward
            success = await self._execute_saga_steps_forward(saga)

            if success:
                saga.status = OperationStatus.COMPLETED
                logger.info(f"Saga {saga_id} completed successfully")
            else:
                # Execute compensation steps backward
                saga.status = OperationStatus.COMPENSATING
                await self.storage.set_saga(saga_id, saga.to_dict())

                await self._execute_saga_compensation(saga)
                saga.status = OperationStatus.COMPENSATED
                logger.info(f"Saga {saga_id} compensated after failure")

            # Save final state
            await self.storage.set_saga(saga_id, saga.to_dict())
            return success

        except Exception as e:
            logger.error(f"Error executing saga {saga_id}: {e}")

            # Mark saga as failed and try to load it for compensation
            try:
                saga_data = await self.storage.get_saga(saga_id)
                if saga_data:
                    saga = SagaWorkflow.from_dict(saga_data)
                    saga.status = OperationStatus.COMPENSATING
                    await self.storage.set_saga(saga_id, saga.to_dict())
                    await self._execute_saga_compensation(saga)
                    saga.status = OperationStatus.COMPENSATED
                    await self.storage.set_saga(saga_id, saga.to_dict())
            except Exception as comp_error:
                logger.error(f"Failed to compensate saga {saga_id}: {comp_error}")

            return False

    async def _execute_saga_steps_forward(self, saga: SagaWorkflow) -> bool:
        """Execute saga steps in forward direction."""
        while saga.current_step < len(saga.steps):
            step = saga.steps[saga.current_step]

            # Skip already completed steps
            if step.status == SagaStepStatus.COMPLETED:
                saga.advance_step()
                continue

            logger.debug(f"Executing step {step.step_id}: {step.name}")

            # Execute step with retries
            success = await self._execute_saga_step(saga, step)

            if success:
                step.status = SagaStepStatus.COMPLETED
                step.completed_at = datetime.now(timezone.utc)

                await self._record_saga_history(
                    saga.saga_id,
                    step.step_id,
                    step.name,
                    SagaStepStatus.COMPLETED,
                    None,
                    step.retry_count,
                )

                # Save progress
                await self.storage.set_saga(saga.saga_id, saga.to_dict())

                # Advance to next step
                if not saga.advance_step():
                    break  # No more steps
            else:
                # Step failed
                step.status = SagaStepStatus.FAILED
                step.completed_at = datetime.now(timezone.utc)

                await self._record_saga_history(
                    saga.saga_id,
                    step.step_id,
                    step.name,
                    SagaStepStatus.FAILED,
                    step.error,
                    step.retry_count,
                )

                await self.storage.set_saga(saga.saga_id, saga.to_dict())
                return False

        return True

    async def _execute_saga_step(self, saga: SagaWorkflow, step: SagaStep) -> bool:
        """Execute a single saga step with retries."""
        step.started_at = datetime.now(timezone.utc)
        step.status = SagaStepStatus.EXECUTING

        for attempt in range(step.max_retries + 1):
            try:
                step.retry_count = attempt

                # Get operation handler
                handler = self._operation_handlers.get(step.operation)
                if not handler:
                    step.error = (
                        f"No handler registered for operation: {step.operation}"
                    )
                    logger.error(step.error)
                    return False

                # Execute operation
                logger.debug(f"Executing step {step.step_id} (attempt {attempt + 1})")

                result = await handler(step.parameters)
                step.result = result
                return True

            except Exception as e:
                error_msg = f"Step {step.step_id} attempt {attempt + 1} failed: {e}"
                logger.warning(error_msg)
                step.error = str(e)

                if attempt < step.max_retries:
                    # Wait before retry (exponential backoff)
                    wait_time = min(2**attempt, 60)  # Max 60 seconds
                    await asyncio.sleep(wait_time)
                else:
                    # All retries exhausted
                    logger.error(f"Step {step.step_id} failed after all retries")
                    return False

        return False

    async def _execute_saga_compensation(self, saga: SagaWorkflow) -> None:
        """Execute compensation steps in reverse order."""
        logger.info(f"Starting compensation for saga {saga.saga_id}")

        # Get completed steps in reverse order
        completed_steps = [
            step for step in saga.steps if step.status == SagaStepStatus.COMPLETED
        ]

        for step in reversed(completed_steps):
            if not step.can_compensate():
                logger.debug(f"Step {step.step_id} cannot be compensated")
                continue

            logger.debug(f"Compensating step {step.step_id}: {step.name}")

            try:
                step.status = SagaStepStatus.COMPENSATING

                # Get compensation handler
                handler = self._compensation_handlers.get(step.compensation_operation)
                if not handler:
                    logger.warning(
                        f"No compensation handler for {step.compensation_operation}"
                    )
                    step.status = SagaStepStatus.FAILED
                    continue

                # Execute compensation
                await handler(step.compensation_parameters)
                step.status = SagaStepStatus.COMPENSATED

                await self._record_saga_history(
                    saga.saga_id, step.step_id, step.name, SagaStepStatus.COMPENSATED
                )

            except Exception as e:
                logger.error(f"Compensation failed for step {step.step_id}: {e}")
                step.status = SagaStepStatus.FAILED

                await self._record_saga_history(
                    saga.saga_id, step.step_id, step.name, SagaStepStatus.FAILED, str(e)
                )

    async def _record_saga_history(
        self,
        saga_id: str,
        step_id: str,
        step_name: str,
        status: SagaStepStatus,
        error: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """Record an entry in saga execution history."""
        entry = SagaHistoryEntry(
            timestamp=datetime.now(timezone.utc),
            step_id=step_id,
            step_name=step_name,
            status=status,
            error=error,
            retry_count=retry_count,
        )

        await self.storage.append_saga_history(saga_id, entry.to_dict())

    # Operation Registry Methods

    async def get_operation_status(
        self, operation_id: str
    ) -> Optional[BackgroundOperation]:
        """
        Get the status of a background operation.

        Args:
            operation_id: The operation ID

        Returns:
            BackgroundOperation object if found, None otherwise
        """
        try:
            data = await self.storage.get_operation(operation_id)
            if data:
                return BackgroundOperation.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get operation status {operation_id}: {e}")
            return None

    async def create_operation(
        self,
        tenant_id: str,
        user_id: Optional[str],
        operation_type: str,
        saga_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> BackgroundOperation:
        """Create a new background operation record."""
        operation_id = str(uuid4())
        now = datetime.now(timezone.utc)

        operation = BackgroundOperation(
            operation_id=operation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=operation_type,
            status=OperationStatus.PENDING,
            created_at=now,
            updated_at=now,
            saga_id=saga_id,
            idempotency_key=idempotency_key,
        )

        await self.storage.set_operation(operation_id, operation.to_dict())
        return operation

    # Storage Management

    def use_storage(self, storage: Storage) -> None:
        """
        Switch storage backends.

        Args:
            storage: New storage backend to use
        """
        # Stop any background tasks first
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        self.storage = storage
        logger.info(f"Switched to storage backend: {storage.__class__.__name__}")

    # Background Tasks

    async def _background_cleanup(self) -> None:
        """Background task for cleaning up expired data."""
        while self._is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if not self._is_running:
                    break

                cleaned_count = await self.storage.cleanup_expired_data()
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired items")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")
                # Continue running even if cleanup fails

    async def cleanup_now(self) -> int:
        """Manually trigger cleanup of expired data."""
        return await self.storage.cleanup_expired_data()

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the manager and storage."""
        storage_health = await self.storage.health_check()

        return {
            "status": "healthy"
            if storage_health.get("status") == "healthy"
            else "unhealthy",
            "manager": {
                "is_running": self._is_running,
                "registered_operations": len(self._operation_handlers),
                "registered_compensations": len(self._compensation_handlers),
                "background_cleanup": self.enable_background_cleanup,
            },
            "storage": storage_health,
        }
