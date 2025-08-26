"""
Job Queue SDK for reliable job processing and queue orchestration.

This module provides comprehensive job queue capabilities including:
- Job definition and execution
- Queue management and routing
- Priority-based processing
- Dead letter queue handling
- Job monitoring and metrics
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
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
    ConfigDict)

logger = structlog.get_logger(__name__)


class JobType(str, Enum):
    """Job types."""

    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    RECURRING = "recurring"
    BATCH = "batch"
    STREAMING = "streaming"


class QueueType(str, Enum):
    """Queue types."""

    FIFO = "fifo"
    PRIORITY = "priority"
    DELAY = "delay"
    DEAD_LETTER = "dead_letter"


class JobDefinition(BaseModel):
    """Job definition with execution configuration."""

    id: str = Field(..., description="Job identifier")
    name: str = Field(..., description="Job name")
    job_type: JobType = Field(..., description="Job type")
    description: Optional[str] = Field(None, description="Job description")

    # Execution configuration
    handler: str = Field(..., description="Job handler function")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Input schema"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict, description="Output schema"
    )

    # Queue configuration
    queue_name: str = Field("default", description="Target queue name")
    priority: Priority = Field(Priority.NORMAL, description="Job priority")

    # Timing configuration
    delay_seconds: Optional[float] = Field(None, description="Delay before execution")
    max_age_seconds: Optional[float] = Field(None, description="Maximum job age")

    # Execution policies
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry policy")
    timeout_policy: Optional[TimeoutPolicy] = Field(None, description="Timeout policy")

    # Concurrency settings
    max_concurrent: Optional[int] = Field(None, description="Max concurrent executions")

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    model_config = ConfigDict(extra="allow")

@dataclass
class JobExecution:
    """Runtime execution state of a job."""

    execution_id: str
    job_id: str
    job_definition_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    queue_name: str = "default"
    priority: Priority = Priority.NORMAL
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    error: Optional[ErrorInfo] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    worker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "job_definition_id": self.job_definition_id,
            "status": self.status.value,
            "queue_name": self.queue_name,
            "priority": self.priority.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context.model_dump() if self.context else None,
            "error": self.error.model_dump() if self.error else None,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": (
                self.scheduled_at.isoformat() if self.scheduled_at else None
            ),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retry_count": self.retry_count,
            "worker_id": self.worker_id,
        }


class JobQueue:
    """Job queue implementation with priority and delay support."""

    def __init__(
        self,
        name: str,
        queue_type: str = "default",
        max_size: int = 1000,
    ):
        """Initialize job queue."""
        self.name = name
        self.queue_type = queue_type
        self.max_size = max_size
        self.jobs: List[JobExecution] = []
        self.delayed_jobs: List[JobExecution] = []
        self.processing_jobs: Set[str] = set()
        self.completed_jobs: Set[str] = set()
        self.failed_jobs: Set[str] = set()
        self._lock = asyncio.Lock()

    async def enqueue(self, job_execution: JobExecution) -> bool:
        """Add job to queue."""
        async with self._lock:
            if len(self.jobs) + len(self.delayed_jobs) >= self.max_size:
                return False

            job_execution.queue_name = self.name

            # Check if job should be delayed
            if (
                job_execution.scheduled_at
                and job_execution.scheduled_at > datetime.now(timezone.utc)
            ):
                self.delayed_jobs.append(job_execution)
                self._sort_delayed_jobs()
            else:
                self.jobs.append(job_execution)
                self._sort_jobs()

            return True

    async def dequeue(self) -> Optional[JobExecution]:
        """Get next job from queue."""
        async with self._lock:
            # Move ready delayed jobs to main queue
            await self._move_ready_delayed_jobs()

            if not self.jobs:
                return None

            job_execution = self.jobs.pop(0)
            self.processing_jobs.add(job_execution.execution_id)
            return job_execution

    async def _move_ready_delayed_jobs(self):
        """Move delayed jobs that are ready to the main queue."""
        now = datetime.now(timezone.utc)
        ready_jobs = []

        for job in self.delayed_jobs[:]:
            if not job.scheduled_at or job.scheduled_at <= now:
                ready_jobs.append(job)
                self.delayed_jobs.remove(job)

        for job in ready_jobs:
            self.jobs.append(job)

        if ready_jobs:
            self._sort_jobs()

    def _sort_jobs(self):
        """Sort jobs by priority and creation time."""
        if self.queue_type == QueueType.PRIORITY:
            priority_order = {
                Priority.CRITICAL: 3,
                Priority.HIGH: 2,
                Priority.NORMAL: 1,
                Priority.LOW: 0,
            }
            self.jobs.sort(
                key=lambda j: (priority_order.get(j.priority, 1), j.created_at),
                reverse=True,
            )
        elif self.queue_type == QueueType.FIFO:
            self.jobs.sort(key=lambda j: j.created_at)

    def _sort_delayed_jobs(self):
        """Sort delayed jobs by scheduled time."""
        self.delayed_jobs.sort(key=lambda j: j.scheduled_at or datetime.max)

    async def mark_completed(self, execution_id: str, success: bool):
        """Mark job as completed."""
        async with self._lock:
            self.processing_jobs.discard(execution_id)
            if success:
                self.completed_jobs.add(execution_id)
            else:
                self.failed_jobs.add(execution_id)

    async def requeue(self, job_execution: JobExecution):
        """Requeue a job (for retries)."""
        async with self._lock:
            self.processing_jobs.discard(job_execution.execution_id)
            self.jobs.append(job_execution)
            self._sort_jobs()

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "name": self.name,
            "type": self.queue_type.value,
            "pending_count": len(self.jobs),
            "delayed_count": len(self.delayed_jobs),
            "processing_count": len(self.processing_jobs),
            "completed_count": len(self.completed_jobs),
            "failed_count": len(self.failed_jobs),
            "total_capacity": self.max_size,
        }


class JobWorker:
    """Job worker for processing jobs from queues."""

    def __init__(self, worker_id: str, concurrency: int = 5):
        """  Init   operation."""
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.job_handlers: Dict[str, Callable] = {}
        self.running = False
        self.active_jobs: Set[str] = set()

    def register_handler(self, handler_name: str, handler: Callable):
        """Register a job handler."""
        self.job_handlers[handler_name] = handler

    async def process_job(
        self,
        job_def: JobDefinition,
        job_execution: JobExecution,
    ) -> bool:
        """Process a single job."""
        try:
            job_execution.status = ExecutionStatus.RUNNING
            job_execution.started_at = datetime.now(timezone.utc)
            job_execution.worker_id = self.worker_id

            # Get handler
            handler = self.job_handlers.get(job_def.handler)
            if not handler:
                raise ValueError(f"Handler {job_def.handler} not registered")

            # Apply timeout if specified
            timeout = None
            if job_def.timeout_policy and job_def.timeout_policy.execution_timeout:
                timeout = job_def.timeout_policy.execution_timeout

            # Execute with timeout
            if timeout:
                result = await asyncio.wait_for(
                    handler(job_execution.input_data, job_execution.context),
                    timeout=timeout,
                )
            else:
                result = await handler(job_execution.input_data, job_execution.context)

            # Store result
            if isinstance(result, dict):
                job_execution.output_data = result
            else:
                job_execution.output_data = {"result": result}

            job_execution.status = ExecutionStatus.COMPLETED
            job_execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Job processed successfully",
                job_id=job_def.id,
                execution_id=job_execution.execution_id,
                worker_id=self.worker_id,
            )

            return True

        except asyncio.TimeoutError:
            job_execution.status = ExecutionStatus.TIMEOUT
            job_execution.completed_at = datetime.now(timezone.utc)
            job_execution.error = ErrorInfo(
                error_type="TimeoutError",
                message=f"Job execution timed out after {timeout} seconds",
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Job processing timed out",
                job_id=job_def.id,
                execution_id=job_execution.execution_id,
                worker_id=self.worker_id,
                timeout=timeout,
            )
            return False

        except Exception as e:
            job_execution.status = ExecutionStatus.FAILED
            job_execution.completed_at = datetime.now(timezone.utc)
            job_execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Job processing failed",
                job_id=job_def.id,
                execution_id=job_execution.execution_id,
                worker_id=self.worker_id,
                error=str(e),
            )
            return False


class DeadLetterQueue:
    """Dead letter queue for failed jobs."""

    def __init__(self, name: str = "dead_letter"):
        """  Init   operation."""
        self.name = name
        self.failed_jobs: List[JobExecution] = []
        self._lock = asyncio.Lock()

    async def add_failed_job(self, job_execution: JobExecution):
        """Add a failed job to the dead letter queue."""
        async with self._lock:
            self.failed_jobs.append(job_execution)

            logger.info(
                "Job added to dead letter queue",
                execution_id=job_execution.execution_id,
                job_id=job_execution.job_id,
                retry_count=job_execution.retry_count,
            )

    async def get_failed_jobs(self, limit: int = 100) -> List[JobExecution]:
        """Get failed jobs from the dead letter queue."""
        async with self._lock:
            return self.failed_jobs[:limit]

    async def retry_job(self, execution_id: str) -> Optional[JobExecution]:
        """Remove and return a job for retry."""
        async with self._lock:
            for i, job in enumerate(self.failed_jobs):
                if job.execution_id == execution_id:
                    return self.failed_jobs.pop(i)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get dead letter queue statistics."""
        return {
            "name": self.name,
            "failed_jobs_count": len(self.failed_jobs),
        }


class JobQueueSDK:
    """SDK for job queue management and execution."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.job_definitions: Dict[str, JobDefinition] = {}
        self.job_executions: Dict[str, JobExecution] = {}
        self.queues: Dict[str, JobQueue] = {}
        self.workers: List[JobWorker] = []
        self.dead_letter_queue = DeadLetterQueue()
        self.running = False

        # Create default queue
        self.queues["default"] = JobQueue("default", QueueType.PRIORITY)

        logger.info("JobQueueSDK initialized", tenant_id=tenant_id)

    async def create_job_definition(self, job_def: JobDefinition) -> str:
        """Create a new job definition."""
        job_def.tenant_id = self.tenant_id
        job_def.metadata.updated_at = datetime.now(timezone.utc)

        self.job_definitions[job_def.id] = job_def

        # Create queue if it doesn't exist
        if job_def.queue_name not in self.queues:
            self.queues[job_def.queue_name] = JobQueue(
                job_def.queue_name, QueueType.PRIORITY
            )

        if self.storage_adapter:
            await self.storage_adapter.store_job_definition(job_def)

        logger.info(
            "Job definition created",
            job_id=job_def.id,
            tenant_id=self.tenant_id,
        )

        return job_def.id

    async def submit_job(
        self,
        job_definition_id: str,
        input_data: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        priority: Optional[Priority] = None,
        delay_seconds: Optional[float] = None,
    ) -> str:
        """Submit a job for execution."""
        job_def = self.job_definitions.get(job_definition_id)
        if not job_def:
            raise ValueError(f"Job definition {job_definition_id} not found")

        execution_id = str(uuid.uuid4())
        job_id = f"{job_definition_id}_{execution_id}"

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )

        # Calculate scheduled time
        scheduled_at = None
        if delay_seconds or job_def.delay_seconds:
            delay = delay_seconds or job_def.delay_seconds
            scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

        job_execution = JobExecution(
            execution_id=execution_id,
            job_id=job_id,
            job_definition_id=job_definition_id,
            queue_name=job_def.queue_name,
            priority=priority or job_def.priority,
            input_data=input_data,
            context=context,
            scheduled_at=scheduled_at,
        )

        self.job_executions[execution_id] = job_execution

        # Add to queue
        queue = self.queues.get(job_def.queue_name)
        if not queue:
            raise ValueError(f"Queue {job_def.queue_name} not found")

        success = await queue.enqueue(job_execution)
        if not success:
            raise ValueError(f"Queue {job_def.queue_name} is full")

        logger.info(
            "Job submitted",
            job_definition_id=job_definition_id,
            execution_id=execution_id,
            queue=job_def.queue_name,
            tenant_id=self.tenant_id,
        )

        return execution_id

    async def submit_batch(
        self,
        batch_requests: List[Dict[str, Any]],
        context: Optional[ExecutionContext] = None,
    ) -> List[str]:
        """Submit multiple jobs as a batch."""
        execution_ids = []

        for request in batch_requests:
            execution_id = await self.submit_job(
                job_definition_id=request["job_definition_id"],
                input_data=request.get("input_data", {}),
                context=context,
                priority=request.get("priority"),
                delay_seconds=request.get("delay_seconds"),
            )
            execution_ids.append(execution_id)

        return execution_ids

    def add_worker(self, worker_id: str, concurrency: int = 5) -> JobWorker:
        """Add a job worker."""
        worker = JobWorker(worker_id, concurrency)
        self.workers.append(worker)
        return worker

    async def start_processing(self):
        """Start job processing."""
        if self.running:
            return

        self.running = True

        # Start worker tasks
        tasks = []
        for worker in self.workers:
            for _ in range(worker.concurrency):
                task = asyncio.create_task(self._worker_loop(worker))
                tasks.append(task)

        logger.info("Job processing started", tenant_id=self.tenant_id)

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error("Job processing error", error=str(e), tenant_id=self.tenant_id)
        finally:
            self.running = False

    async def stop_processing(self):
        """Stop job processing."""
        self.running = False
        logger.info("Job processing stopped", tenant_id=self.tenant_id)

    async def _worker_loop(self, worker: JobWorker):
        """Worker loop for processing jobs."""
        while self.running:
            try:
                # Get job from any queue
                job_execution = None
                for queue in self.queues.values():
                    job_execution = await queue.dequeue()
                    if job_execution:
                        break

                if not job_execution:
                    await asyncio.sleep(0.1)
                    continue

                # Check if job is expired
                job_def = self.job_definitions.get(job_execution.job_definition_id)
                if not job_def:
                    await self._handle_job_failure(
                        job_execution, "Job definition not found"
                    )
                    continue

                if self._is_job_expired(job_def, job_execution):
                    await self._handle_job_failure(job_execution, "Job expired")
                    continue

                # Process job with retry
                await self._process_job_with_retry(worker, job_def, job_execution)

            except Exception as e:
                logger.error(
                    "Worker loop error",
                    worker_id=worker.worker_id,
                    error=str(e),
                    tenant_id=self.tenant_id,
                )
                await asyncio.sleep(1)

    async def _process_job_with_retry(
        self,
        worker: JobWorker,
        job_def: JobDefinition,
        job_execution: JobExecution,
    ):
        """Process job with retry logic."""
        max_retries = 0
        if job_def.retry_policy:
            max_retries = job_def.retry_policy.max_attempts - 1

        for attempt in range(max_retries + 1):
            job_execution.retry_count = attempt

            success = await worker.process_job(job_def, job_execution)

            if success:
                # Mark as completed
                queue = self.queues[job_execution.queue_name]
                await queue.mark_completed(job_execution.execution_id, True)

                if self.storage_adapter:
                    await self.storage_adapter.store_execution(job_execution)

                break
            else:
                # Check if we should retry
                if attempt < max_retries and self._should_retry(job_def, job_execution):
                    # Calculate delay
                    delay = self._calculate_retry_delay(job_def.retry_policy, attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final failure - send to dead letter queue
                    await self._handle_job_failure(
                        job_execution, "Max retries exceeded"
                    )
                    break

    async def _handle_job_failure(self, job_execution: JobExecution, reason: str):
        """Handle job failure."""
        job_execution.status = ExecutionStatus.FAILED
        job_execution.completed_at = datetime.now(timezone.utc)

        if not job_execution.error:
            job_execution.error = ErrorInfo(
                error_type="JobFailure",
                message=reason,
                timestamp=datetime.now(timezone.utc),
            )

        # Mark as failed in queue
        queue = self.queues[job_execution.queue_name]
        await queue.mark_completed(job_execution.execution_id, False)

        # Add to dead letter queue
        await self.dead_letter_queue.add_failed_job(job_execution)

        if self.storage_adapter:
            await self.storage_adapter.store_execution(job_execution)

    def _is_job_expired(
        self, job_def: JobDefinition, job_execution: JobExecution
    ) -> bool:
        """Check if job has expired."""
        if not job_def.max_age_seconds:
            return False

        age = (datetime.now(timezone.utc) - job_execution.created_at).total_seconds()
        return age > job_def.max_age_seconds

    def _should_retry(
        self, job_def: JobDefinition, job_execution: JobExecution
    ) -> bool:
        """Determine if job should be retried."""
        if not job_def.retry_policy:
            return False

        if not job_execution.error:
            return False

        error_type = job_execution.error.error_type.lower()
        retry_on = [err.lower() for err in job_def.retry_policy.retry_on]

        return any(retry_type in error_type for retry_type in retry_on)

    def _calculate_retry_delay(self, retry_policy: RetryPolicy, attempt: int) -> float:
        """Calculate retry delay with backoff."""
        delay = retry_policy.initial_delay * (retry_policy.backoff_multiplier**attempt)
        delay = min(delay, retry_policy.max_delay)

        if retry_policy.jitter:
            import secrets

            delay *= 0.5 + secrets.randbelow(1000000) / 1000000 * 0.5

        return delay

    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get job execution by ID."""
        return self.job_executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a pending or running job execution."""
        job_execution = self.job_executions.get(execution_id)
        if not job_execution:
            return False

        if job_execution.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            job_execution.status = ExecutionStatus.CANCELLED
            job_execution.completed_at = datetime.now(timezone.utc)

            # Remove from queue if pending
            for queue in self.queues.values():
                if job_execution in queue.jobs:
                    queue.jobs.remove(job_execution)
                    break
                if job_execution in queue.delayed_jobs:
                    queue.delayed_jobs.remove(job_execution)
                    break

            logger.info(
                "Job execution cancelled",
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
            return True

        return False

    async def retry_failed_job(self, execution_id: str) -> bool:
        """Retry a failed job from the dead letter queue."""
        job_execution = await self.dead_letter_queue.retry_job(execution_id)
        if not job_execution:
            return False

        # Reset job state
        job_execution.status = ExecutionStatus.PENDING
        job_execution.started_at = None
        job_execution.completed_at = None
        job_execution.error = None
        job_execution.worker_id = None

        # Re-enqueue
        queue = self.queues.get(job_execution.queue_name)
        if queue:
            success = await queue.enqueue(job_execution)
            if success:
                logger.info(
                    "Failed job retried",
                    execution_id=execution_id,
                    tenant_id=self.tenant_id,
                )
                return True

        return False

    async def get_queue_stats(self, queue_name: str = None) -> Dict[str, Any]:
        """Get queue statistics."""
        if queue_name:
            queue = self.queues.get(queue_name)
            return queue.get_stats() if queue else {}

        # Return stats for all queues
        stats = {}
        for name, queue in self.queues.items():
            stats[name] = queue.get_stats()

        # Add dead letter queue stats
        stats["dead_letter"] = self.dead_letter_queue.get_stats()

        return stats

    def register_job_handler(self, handler_name: str, handler: Callable):
        """Register a job handler for all workers."""
        for worker in self.workers:
            worker.register_handler(handler_name, handler)
