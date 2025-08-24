"""
Task SDK for distributed task management and orchestration.

This module provides comprehensive task management capabilities including:
- Task definition and execution
- Dependency management
- Distributed task coordination
- Task queuing and scheduling
- Result aggregation and monitoring
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
from pydantic import BaseModel, Field

from ..contracts.common_schemas import (
    ExecutionContext,
    ExecutionStatus,
    OperationMetadata,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    Priority,
)

logger = structlog.get_logger(__name__)


class TaskType(str, Enum):
    """Task types."""

    COMPUTE = "compute"
    IO = "io"
    NETWORK = "network"
    BATCH = "batch"
    STREAMING = "streaming"
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    HUMAN = "human"


class DependencyType(str, Enum):
    """Task dependency types."""

    HARD = "hard"  # Must complete successfully
    SOFT = "soft"  # Can fail but still proceed
    DATA = "data"  # Data dependency
    RESOURCE = "resource"  # Resource dependency


class TaskDependency(BaseModel):
    """Task dependency definition."""

    task_id: str = Field(..., description="Dependent task ID")
    dependency_type: DependencyType = Field(
        DependencyType.HARD, description="Dependency type"
    )
    condition: Optional[str] = Field(None, description="Dependency condition")
    timeout_seconds: Optional[float] = Field(None, description="Dependency timeout")

    class Config:
        """Class for Config operations."""
        extra = "forbid"


class ResourceRequirement(BaseModel):
    """Resource requirements for task execution."""

    cpu_cores: Optional[float] = Field(None, ge=0, description="CPU cores required")
    memory_mb: Optional[int] = Field(None, ge=0, description="Memory in MB")
    disk_mb: Optional[int] = Field(None, ge=0, description="Disk space in MB")
    gpu_count: Optional[int] = Field(None, ge=0, description="GPU count")
    network_bandwidth_mbps: Optional[float] = Field(
        None, ge=0, description="Network bandwidth"
    )
    custom_resources: Dict[str, Any] = Field(
        default_factory=dict, description="Custom resources"
    )

    class Config:
        """Class for Config operations."""
        extra = "allow"


class TaskDefinition(BaseModel):
    """Definition of a task."""

    id: str = Field(..., description="Task identifier")
    name: str = Field(..., description="Task name")
    task_type: TaskType = Field(..., description="Task type")
    description: Optional[str] = Field(None, description="Task description")

    # Execution configuration
    handler: str = Field(..., description="Task handler function or service")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Input schema"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Output schema"
    )

    # Dependencies
    dependencies: List[TaskDependency] = Field(
        default_factory=list, description="Task dependencies"
    )

    # Resource requirements
    resources: Optional[ResourceRequirement] = Field(
        None, description="Resource requirements"
    )

    # Execution policies
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry policy")
    timeout_policy: Optional[TimeoutPolicy] = Field(None, description="Timeout policy")
    priority: Priority = Field(Priority.NORMAL, description="Task priority")

    # Scheduling
    max_concurrent: Optional[int] = Field(
        None, ge=1, description="Max concurrent executions"
    )
    queue_name: Optional[str] = Field(None, description="Execution queue")

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    class Config:
        """Class for Config operations."""
        extra = "allow"


@dataclass
class TaskExecution:
    """Runtime execution state of a task."""

    execution_id: str
    task_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    error: Optional[ErrorInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    worker_id: Optional[str] = None
    queue_name: Optional[str] = None
    priority: Priority = Priority.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context.dict() if self.context else None,
            "error": self.error.dict() if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retry_count": self.retry_count,
            "worker_id": self.worker_id,
            "queue_name": self.queue_name,
            "priority": self.priority.value,
        }


class TaskQueue:
    """Task queue for managing task execution order."""

    def __init__(self, name: str, max_concurrent: int = 10):
        """  Init   operation."""
        self.name = name
        self.max_concurrent = max_concurrent
        self.pending_tasks: List[TaskExecution] = []
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()

    async def enqueue(self, task_execution: TaskExecution):
        """Add task to queue."""
        task_execution.queue_name = self.name

        # Insert based on priority
        inserted = False
        for i, existing_task in enumerate(self.pending_tasks):
            if (
                self._compare_priority(task_execution.priority, existing_task.priority)
                > 0
            ):
                self.pending_tasks.insert(i, task_execution)
                inserted = True
                break

        if not inserted:
            self.pending_tasks.append(task_execution)

    async def dequeue(self) -> Optional[TaskExecution]:
        """Get next task from queue if capacity allows."""
        if len(self.running_tasks) >= self.max_concurrent:
            return None

        if not self.pending_tasks:
            return None

        task_execution = self.pending_tasks.pop(0)
        self.running_tasks.add(task_execution.execution_id)
        return task_execution

    def mark_completed(self, execution_id: str, success: bool):
        """Mark task as completed."""
        self.running_tasks.discard(execution_id)
        if success:
            self.completed_tasks.add(execution_id)
        else:
            self.failed_tasks.add(execution_id)

    def _compare_priority(self, p1: Priority, p2: Priority) -> int:
        """Compare priorities (-1: p1 < p2, 0: equal, 1: p1 > p2)."""
        priority_order = {
            Priority.LOW: 0,
            Priority.NORMAL: 1,
            Priority.HIGH: 2,
            Priority.CRITICAL: 3,
        }
        return priority_order[p1] - priority_order[p2]


class TaskEngine:
    """Task execution engine."""

    def __init__(self):
        """  Init   operation."""
        self.task_handlers: Dict[str, Callable] = {}
        self.condition_evaluator: Optional[Callable] = None

    def register_handler(self, handler_name: str, handler: Callable):
        """Register a task handler."""
        self.task_handlers[handler_name] = handler

    def set_condition_evaluator(self, evaluator: Callable):
        """Set condition evaluator function."""
        self.condition_evaluator = evaluator

    async def execute_task(
        self,
        task_def: TaskDefinition,
        task_execution: TaskExecution,
    ) -> bool:
        """Execute a single task."""
        try:
            task_execution.status = ExecutionStatus.RUNNING
            task_execution.started_at = datetime.now(timezone.utc)

            # Get handler
            handler = self.task_handlers.get(task_def.handler)
            if not handler:
                raise ValueError(f"Handler {task_def.handler} not registered")

            # Apply timeout if specified
            timeout = None
            if task_def.timeout_policy and task_def.timeout_policy.execution_timeout:
                timeout = task_def.timeout_policy.execution_timeout

            # Execute with timeout
            if timeout:
                result = await asyncio.wait_for(
                    handler(task_execution.input_data, task_execution.context),
                    timeout=timeout,
                )
            else:
                result = await handler(
                    task_execution.input_data, task_execution.context
                )

            # Store result
            if isinstance(result, dict):
                task_execution.output_data = result
            else:
                task_execution.output_data = {"result": result}

            task_execution.status = ExecutionStatus.COMPLETED
            task_execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Task executed successfully",
                task_id=task_def.id,
                execution_id=task_execution.execution_id,
            )

            return True

        except asyncio.TimeoutError:
            task_execution.status = ExecutionStatus.TIMEOUT
            task_execution.completed_at = datetime.now(timezone.utc)
            task_execution.error = ErrorInfo(
                error_type="TimeoutError",
                message=f"Task execution timed out after {timeout} seconds",
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Task execution timed out",
                task_id=task_def.id,
                execution_id=task_execution.execution_id,
                timeout=timeout,
            )
            return False

        except Exception as e:
            task_execution.status = ExecutionStatus.FAILED
            task_execution.completed_at = datetime.now(timezone.utc)
            task_execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Task execution failed",
                task_id=task_def.id,
                execution_id=task_execution.execution_id,
                error=str(e),
            )
            return False


class DependencyResolver:
    """Resolves task dependencies."""

    def __init__(self):
        """  Init   operation."""
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.task_results: Dict[str, Dict[str, Any]] = {}

    def mark_task_completed(
        self, task_id: str, success: bool, result: Dict[str, Any] = None
    ):
        """Mark a task as completed."""
        if success:
            self.completed_tasks.add(task_id)
            if result:
                self.task_results[task_id] = result
        else:
            self.failed_tasks.add(task_id)

    def are_dependencies_satisfied(
        self,
        dependencies: List[TaskDependency],
        condition_evaluator: Optional[Callable] = None,
    ) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in dependencies:
            if not self._is_dependency_satisfied(dep, condition_evaluator):
                return False
        return True

    def _is_dependency_satisfied(
        self,
        dependency: TaskDependency,
        condition_evaluator: Optional[Callable] = None,
    ) -> bool:
        """Check if a single dependency is satisfied."""
        task_id = dependency.task_id

        if dependency.dependency_type == DependencyType.HARD:
            if task_id not in self.completed_tasks:
                return False
        elif dependency.dependency_type == DependencyType.SOFT:
            if task_id not in self.completed_tasks and task_id not in self.failed_tasks:
                return False

        # Check condition if specified
        if dependency.condition and condition_evaluator:
            context = {
                "task_results": self.task_results,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
            }
            return condition_evaluator(dependency.condition, context)

        return True


class TaskSDK:
    """SDK for task management and execution."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.engine = TaskEngine()
        self.dependency_resolver = DependencyResolver()
        self.task_definitions: Dict[str, TaskDefinition] = {}
        self.task_executions: Dict[str, TaskExecution] = {}
        self.queues: Dict[str, TaskQueue] = {}
        self.running = False

        # Default queue
        self.queues["default"] = TaskQueue("default")

        logger.info("TaskSDK initialized", tenant_id=tenant_id)

    async def create_task(self, task_def: TaskDefinition) -> str:
        """Create a new task definition."""
        task_def.tenant_id = self.tenant_id
        task_def.metadata.updated_at = datetime.now(timezone.utc)

        self.task_definitions[task_def.id] = task_def

        if self.storage_adapter:
            await self.storage_adapter.store_task(task_def)

        logger.info(
            "Task created",
            task_id=task_def.id,
            tenant_id=self.tenant_id,
        )

        return task_def.id

    async def execute_task(
        self,
        task_id: str,
        input_data: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        priority: Optional[Priority] = None,
    ) -> str:
        """Submit task for execution."""
        task_def = self.task_definitions.get(task_id)
        if not task_def:
            raise ValueError(f"Task {task_id} not found")

        execution_id = str(uuid.uuid4())

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
        else:
            context.execution_id = execution_id

        task_execution = TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            input_data=input_data,
            context=context,
            priority=priority or task_def.priority,
        )

        self.task_executions[execution_id] = task_execution

        # Add to appropriate queue
        queue_name = task_def.queue_name or "default"
        if queue_name not in self.queues:
            self.queues[queue_name] = TaskQueue(queue_name)

        await self.queues[queue_name].enqueue(task_execution)

        logger.info(
            "Task submitted for execution",
            task_id=task_id,
            execution_id=execution_id,
            queue=queue_name,
            tenant_id=self.tenant_id,
        )

        return execution_id

    async def execute_batch(
        self,
        batch_requests: List[Dict[str, Any]],
        context: Optional[ExecutionContext] = None,
    ) -> List[str]:
        """Execute multiple tasks as a batch."""
        execution_ids = []

        for request in batch_requests:
            execution_id = await self.execute_task(
                task_id=request["task_id"],
                input_data=request.get("input_data", {}),
                context=context,
                priority=request.get("priority"),
            )
            execution_ids.append(execution_id)

        return execution_ids

    async def start_processing(self):
        """Start task processing."""
        if self.running:
            return

        self.running = True

        # Start queue processors
        tasks = []
        for queue in self.queues.values():
            task = asyncio.create_task(self._process_queue(queue))
            tasks.append(task)

        logger.info("Task processing started", tenant_id=self.tenant_id)

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(
                "Task processing error", error=str(e), tenant_id=self.tenant_id
            )
        finally:
            self.running = False

    async def stop_processing(self):
        """Stop task processing."""
        self.running = False
        logger.info("Task processing stopped", tenant_id=self.tenant_id)

    async def _process_queue(self, queue: TaskQueue):
        """Process tasks in a queue."""
        while self.running:
            try:
                # Get next task
                task_execution = await queue.dequeue()
                if not task_execution:
                    await asyncio.sleep(0.1)
                    continue

                # Check dependencies
                task_def = self.task_definitions[task_execution.task_id]
                if not self.dependency_resolver.are_dependencies_satisfied(
                    task_def.dependencies,
                    self.engine.condition_evaluator,
                ):
                    # Re-queue task
                    await queue.enqueue(task_execution)
                    await asyncio.sleep(0.5)
                    continue

                # Execute task
                asyncio.create_task(
                    self._execute_task_with_retry(task_def, task_execution, queue)
                )

            except Exception as e:
                logger.error(
                    "Queue processing error",
                    queue=queue.name,
                    error=str(e),
                    tenant_id=self.tenant_id,
                )
                await asyncio.sleep(1)

    async def _execute_task_with_retry(
        self,
        task_def: TaskDefinition,
        task_execution: TaskExecution,
        queue: TaskQueue,
    ):
        """Execute task with retry logic."""
        max_retries = 0
        if task_def.retry_policy:
            max_retries = task_def.retry_policy.max_attempts - 1

        for attempt in range(max_retries + 1):
            task_execution.retry_count = attempt

            success = await self.engine.execute_task(task_def, task_execution)

            if success:
                queue.mark_completed(task_execution.execution_id, True)
                self.dependency_resolver.mark_task_completed(
                    task_execution.task_id,
                    True,
                    task_execution.output_data,
                )

                if self.storage_adapter:
                    await self.storage_adapter.store_execution(task_execution)

                break
            else:
                # Check if we should retry
                if attempt < max_retries and self._should_retry(
                    task_def, task_execution
                ):
                    # Calculate delay
                    delay = self._calculate_retry_delay(task_def.retry_policy, attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final failure
                    queue.mark_completed(task_execution.execution_id, False)
                    self.dependency_resolver.mark_task_completed(
                        task_execution.task_id,
                        False,
                    )

                    if self.storage_adapter:
                        await self.storage_adapter.store_execution(task_execution)

                    break

    def _should_retry(
        self, task_def: TaskDefinition, task_execution: TaskExecution
    ) -> bool:
        """Determine if task should be retried."""
        if not task_def.retry_policy:
            return False

        if not task_execution.error:
            return False

        error_type = task_execution.error.error_type.lower()
        retry_on = [err.lower() for err in task_def.retry_policy.retry_on]

        return any(retry_type in error_type for retry_type in retry_on)

    def _calculate_retry_delay(self, retry_policy: RetryPolicy, attempt: int) -> float:
        """Calculate retry delay with backoff."""
        delay = retry_policy.initial_delay * (retry_policy.backoff_multiplier**attempt)
        delay = min(delay, retry_policy.max_delay)

        if retry_policy.jitter:
            import secrets

            delay *= 0.5 + secrets.randbelow(1000000) / 1000000 * 0.5

        return delay

    async def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """Get task execution by ID."""
        return self.task_executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a pending or running task execution."""
        task_execution = self.task_executions.get(execution_id)
        if not task_execution:
            return False

        if task_execution.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            task_execution.status = ExecutionStatus.CANCELLED
            task_execution.completed_at = datetime.now(timezone.utc)

            # Remove from queue if pending
            for queue in self.queues.values():
                if task_execution in queue.pending_tasks:
                    queue.pending_tasks.remove(task_execution)
                    break

            logger.info(
                "Task execution cancelled",
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
            return True

        return False

    def register_task_handler(self, handler_name: str, handler: Callable):
        """Register a task handler function."""
        self.engine.register_handler(handler_name, handler)

    def set_condition_evaluator(self, evaluator: Callable):
        """Set condition evaluator function."""
        self.engine.set_condition_evaluator(evaluator)

    async def get_queue_status(self, queue_name: str = "default") -> Dict[str, Any]:
        """Get queue status information."""
        queue = self.queues.get(queue_name)
        if not queue:
            return {}

        return {
            "name": queue.name,
            "max_concurrent": queue.max_concurrent,
            "pending_count": len(queue.pending_tasks),
            "running_count": len(queue.running_tasks),
            "completed_count": len(queue.completed_tasks),
            "failed_count": len(queue.failed_tasks),
        }
