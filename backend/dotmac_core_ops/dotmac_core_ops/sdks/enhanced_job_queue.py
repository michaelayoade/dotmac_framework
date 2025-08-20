"""
Enhanced job queue system with priority fairness, visibility timeout, backoff + jitter,
DLQ for poison jobs, and ordering by key preservation.
"""

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict, deque
import heapq

import structlog

from ..contracts.common_schemas import (
    Priority,
    ErrorInfo
)

logger = structlog.get_logger(__name__)


class JobStatus(str, Enum):
    """Enhanced job status enumeration."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class VisibilityState(str, Enum):
    """Job visibility states."""

    VISIBLE = "visible"
    INVISIBLE = "invisible"
    EXPIRED = "expired"


@dataclass
class JobMessage:
    """Enhanced job message with visibility and ordering."""

    job_id: str
    tenant_id: str
    queue_name: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    ordering_key: Optional[str] = None  # For FIFO ordering within key

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    visibility_timeout: Optional[datetime] = None

    # Processing state
    status: JobStatus = JobStatus.QUEUED
    attempt_count: int = 0
    max_attempts: int = 3

    # Backoff configuration
    initial_delay: float = 1.0
    max_delay: float = 300.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    # Error tracking
    last_error: Optional[ErrorInfo] = None
    error_history: List[ErrorInfo] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_next_retry_delay(self) -> float:
        """Calculate next retry delay with exponential backoff and jitter."""
        delay = self.initial_delay * (self.backoff_multiplier ** (self.attempt_count - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add jitter: ±25% of the delay
            jitter_range = delay * 0.25
            delay += (secrets.randbelow(int((jitter_range) * 1000)) / 1000)
            delay = max(0.1, delay)  # Ensure minimum delay

        return delay

    def is_visible(self, current_time: datetime) -> bool:
        """Check if job is visible for processing."""
        if self.status != JobStatus.QUEUED:
            return False

        if self.scheduled_at > current_time:
            return False

        if self.visibility_timeout and current_time < self.visibility_timeout:
            return False

        return True

    def make_invisible(self, visibility_timeout_seconds: int):
        """Make job invisible for processing."""
        self.visibility_timeout = datetime.now(timezone.utc) + timedelta(seconds=visibility_timeout_seconds)
        self.status = JobStatus.PROCESSING

    def make_visible(self):
        """Make job visible again."""
        self.visibility_timeout = None
        self.status = JobStatus.QUEUED

    def add_error(self, error: ErrorInfo):
        """Add error to history."""
        self.last_error = error
        self.error_history.append(error)

        # Keep only recent errors
        if len(self.error_history) > 10:
            self.error_history = self.error_history[-10:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "queue_name": self.queue_name,
            "payload": self.payload,
            "priority": self.priority.value,
            "ordering_key": self.ordering_key,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat(),
            "visibility_timeout": self.visibility_timeout.isoformat() if self.visibility_timeout else None,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error.dict() if self.last_error else None,
            "error_count": len(self.error_history),
            "metadata": self.metadata
        }


class PriorityQueue:
    """Priority queue with fairness and ordering guarantees."""

    def __init__(self):
        # Priority heaps for each priority level
        self.priority_heaps: Dict[Priority, List] = {
            Priority.CRITICAL: [],
            Priority.HIGH: [],
            Priority.NORMAL: [],
            Priority.LOW: []
        }

        # Ordering queues for FIFO within ordering keys
        self.ordering_queues: Dict[str, deque] = defaultdict(deque)

        # Fairness tracking
        self.priority_counters: Dict[Priority, int] = defaultdict(int)
        self.fairness_threshold = 10  # Process N high priority before allowing lower

        # Metrics
        self.total_jobs = 0
        self.jobs_by_priority: Dict[Priority, int] = defaultdict(int)

    def enqueue(self, job: JobMessage):
        """Add job to priority queue with ordering support."""
        if job.ordering_key:
            # Use FIFO queue for ordered jobs
            self.ordering_queues[job.ordering_key].append(job)
        else:
            # Use priority heap for unordered jobs
            # Use negative timestamp for min-heap behavior (earliest first)
            heap_item = (
                -job.scheduled_at.timestamp(),
                job.job_id,  # Tie breaker
                job
            )
            heapq.heappush(self.priority_heaps[job.priority], heap_item)

        self.total_jobs += 1
        self.jobs_by_priority[job.priority] += 1

        logger.debug(
            "Job enqueued",
            job_id=job.job_id,
            priority=job.priority.value,
            ordering_key=job.ordering_key,
            queue_size=self.total_jobs
        )

    def dequeue(self, current_time: datetime) -> Optional[JobMessage]:  # noqa: C901
        """Dequeue next job with priority fairness and visibility checks."""
        # Try ordering queues first (FIFO within key)
        for ordering_key, queue in list(self.ordering_queues.items()):
            if queue:
                job = queue[0]  # Peek at first job
                if job.is_visible(current_time):
                    job = queue.popleft()
                    if not queue:  # Clean up empty queue
                        del self.ordering_queues[ordering_key]

                    self.total_jobs -= 1
                    self.jobs_by_priority[job.priority] -= 1
                    return job

        # Try priority queues with fairness
        for priority in self._get_fair_priority_order():
            heap = self.priority_heaps[priority]

            # Find first visible job in this priority level
            visible_jobs = []
            invisible_jobs = []

            while heap:
                _, job_id, job = heapq.heappop(heap)

                if job.is_visible(current_time):
                    visible_jobs.append((_, job_id, job))
                else:
                    invisible_jobs.append((_, job_id, job))

            # Put invisible jobs back
            for item in invisible_jobs:
                heapq.heappush(heap, item)

            # Return first visible job
            if visible_jobs:
                # Put other visible jobs back
                for item in visible_jobs[1:]:
                    heapq.heappush(heap, item)

                _, _, job = visible_jobs[0]
                self.total_jobs -= 1
                self.jobs_by_priority[job.priority] -= 1
                self.priority_counters[priority] += 1

                return job

        return None

    def _get_fair_priority_order(self) -> List[Priority]:
        """Get priority order with fairness considerations."""
        # Check if we need to enforce fairness
        high_processed = self.priority_counters[Priority.HIGH]
        critical_processed = self.priority_counters[Priority.CRITICAL]

        # Reset counters periodically
        if (high_processed + critical_processed) >= self.fairness_threshold:
            self.priority_counters.clear()

        # Standard priority order with fairness adjustments
        if high_processed >= self.fairness_threshold:
            # Give lower priorities a chance
            return [Priority.CRITICAL, Priority.NORMAL, Priority.HIGH, Priority.LOW]
        else:
            # Normal priority order
            return [Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]

    def peek_next(self, current_time: datetime) -> Optional[JobMessage]:
        """Peek at next job without removing it."""
        # This is a simplified version - in practice you'd want to implement
        # a more efficient peek that doesn't modify the queue structure
        job = self.dequeue(current_time)
        if job:
            # Put it back (this is inefficient but works for demo)
            self.enqueue(job)
        return job

    def size(self) -> int:
        """Get total queue size."""
        return self.total_jobs

    def size_by_priority(self) -> Dict[Priority, int]:
        """Get queue size by priority."""
        return dict(self.jobs_by_priority)

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "total_jobs": self.total_jobs,
            "jobs_by_priority": {p.value: count for p, count in self.jobs_by_priority.items()},
            "ordering_queues": len(self.ordering_queues),
            "priority_counters": {p.value: count for p, count in self.priority_counters.items()}
        }


class DeadLetterQueue:
    """Dead letter queue for poison messages."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.messages: Dict[str, JobMessage] = {}
        self.insertion_order: deque = deque()

    def add_message(self, job: JobMessage):
        """Add message to DLQ."""
        job.status = JobStatus.DEAD_LETTER

        # Remove oldest if at capacity
        if len(self.messages) >= self.max_size:
            oldest_id = self.insertion_order.popleft()
            self.messages.pop(oldest_id, None)

        self.messages[job.job_id] = job
        self.insertion_order.append(job.job_id)

        logger.warning(
            "Job moved to dead letter queue",
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            queue_name=job.queue_name,
            attempt_count=job.attempt_count,
            error_count=len(job.error_history)
        )

    def get_message(self, job_id: str) -> Optional[JobMessage]:
        """Get message from DLQ."""
        return self.messages.get(job_id)

    def remove_message(self, job_id: str) -> bool:
        """Remove message from DLQ."""
        if job_id in self.messages:
            del self.messages[job_id]
            try:
                self.insertion_order.remove(job_id)
            except ValueError:
                pass
            return True
        return False

    def list_messages(self, limit: int = 100) -> List[JobMessage]:
        """List messages in DLQ."""
        messages = []
        for job_id in list(self.insertion_order)[-limit:]:
            if job_id in self.messages:
                messages.append(self.messages[job_id])
        return messages

    def size(self) -> int:
        """Get DLQ size."""
        return len(self.messages)

    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        if not self.messages:
            return {"size": 0, "by_queue": {}, "by_tenant": {}}

        by_queue = defaultdict(int)
        by_tenant = defaultdict(int)

        for job in self.messages.values():
            by_queue[job.queue_name] += 1
            by_tenant[job.tenant_id] += 1

        return {
            "size": len(self.messages),
            "by_queue": dict(by_queue),
            "by_tenant": dict(by_tenant)
        }


class EnhancedJobQueue:
    """Enhanced job queue with all advanced features."""

    def __init__(
        self,
        name: str,
        tenant_id: str,
        visibility_timeout_seconds: int = 30,
        max_concurrent_jobs: int = 10,
        storage_adapter=None
    ):
        self.name = name
        self.tenant_id = tenant_id
        self.visibility_timeout_seconds = visibility_timeout_seconds
        self.max_concurrent_jobs = max_concurrent_jobs
        self.storage_adapter = storage_adapter

        # Queue components
        self.priority_queue = PriorityQueue()
        self.dead_letter_queue = DeadLetterQueue()
        self.processing_jobs: Dict[str, JobMessage] = {}
        self.completed_jobs: Set[str] = set()

        # Job handlers
        self.job_handlers: Dict[str, Callable] = {}

        # Metrics
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "jobs_completed": 0,
            "jobs_dead_lettered": 0,
            "avg_processing_time": 0.0,
            "queue_lag_seconds": 0.0
        }

        # Background tasks
        self.running = False
        self.processor_task: Optional[asyncio.Task] = None
        self.visibility_monitor_task: Optional[asyncio.Task] = None

        logger.info(
            "Enhanced job queue initialized",
            queue_name=name,
            tenant_id=tenant_id,
            visibility_timeout=visibility_timeout_seconds
        )

    async def enqueue(
        self,
        job_id: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        ordering_key: Optional[str] = None,
        delay_seconds: int = 0,
        max_attempts: int = 3,
        **kwargs
    ) -> bool:
        """Enqueue a job with enhanced options."""
        try:
            scheduled_at = datetime.now(timezone.utc)
            if delay_seconds > 0:
                scheduled_at += timedelta(seconds=delay_seconds)

            job = JobMessage(
                job_id=job_id,
                tenant_id=self.tenant_id,
                queue_name=self.name,
                payload=payload,
                priority=priority,
                ordering_key=ordering_key,
                scheduled_at=scheduled_at,
                max_attempts=max_attempts,
                **kwargs
            )

            self.priority_queue.enqueue(job)

            if self.storage_adapter:
                await self.storage_adapter.store_job(job)

            # Update queue lag metric
            self._update_queue_lag()

            logger.info(
                "Job enqueued",
                job_id=job_id,
                queue_name=self.name,
                priority=priority.value,
                ordering_key=ordering_key,
                delay_seconds=delay_seconds
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to enqueue job",
                job_id=job_id,
                queue_name=self.name,
                error=str(e)
            )
            return False

    async def start_processing(self):
        """Start background job processing."""
        if self.running:
            return

        self.running = True

        # Start background tasks
        self.processor_task = asyncio.create_task(self._job_processor())
        self.visibility_monitor_task = asyncio.create_task(self._visibility_monitor())

        logger.info("Job queue processing started", queue_name=self.name)

    async def stop_processing(self):
        """Stop background job processing."""
        self.running = False

        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass

        if self.visibility_monitor_task:
            self.visibility_monitor_task.cancel()
            try:
                await self.visibility_monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Job queue processing stopped", queue_name=self.name)

    async def _job_processor(self):
        """Main job processing loop."""
        while self.running:
            try:
                # Check if we can process more jobs
                if len(self.processing_jobs) >= self.max_concurrent_jobs:
                    await asyncio.sleep(0.1)
                    continue

                # Get next job
                current_time = datetime.now(timezone.utc)
                job = self.priority_queue.dequeue(current_time)

                if not job:
                    await asyncio.sleep(0.1)
                    continue

                # Make job invisible and start processing
                job.make_invisible(self.visibility_timeout_seconds)
                self.processing_jobs[job.job_id] = job

                # Process job asynchronously
                asyncio.create_task(self._process_job(job))

            except Exception as e:
                logger.error(
                    "Job processor error",
                    queue_name=self.name,
                    error=str(e)
                )
                await asyncio.sleep(1)

    async def _process_job(self, job: JobMessage):
        """Process a single job."""
        start_time = datetime.now(timezone.utc)

        try:
            job.attempt_count += 1

            # Get handler
            handler_name = job.payload.get("handler")
            if not handler_name or handler_name not in self.job_handlers:
                raise ValueError(f"Handler '{handler_name}' not found")

            handler = self.job_handlers[handler_name]

            # Execute job
            result = await handler(job.payload, job.metadata)

            # Job completed successfully
            job.status = JobStatus.COMPLETED
            self.processing_jobs.pop(job.job_id, None)
            self.completed_jobs.add(job.job_id)

            # Update metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._update_metrics("completed", processing_time)

            if self.storage_adapter:
                await self.storage_adapter.update_job_status(job.job_id, JobStatus.COMPLETED, result)

            logger.info(
                "Job completed successfully",
                job_id=job.job_id,
                queue_name=self.name,
                processing_time=processing_time,
                attempt=job.attempt_count
            )

        except Exception as e:
            # Job failed
            error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc)
            )

            job.add_error(error)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            if job.attempt_count >= job.max_attempts:
                # Move to dead letter queue
                job.status = JobStatus.DEAD_LETTER
                self.processing_jobs.pop(job.job_id, None)
                self.dead_letter_queue.add_message(job)

                self._update_metrics("dead_lettered", processing_time)

                if self.storage_adapter:
                    await self.storage_adapter.update_job_status(job.job_id, JobStatus.DEAD_LETTER, error.dict())

            else:
                # Schedule for retry
                job.status = JobStatus.RETRYING
                retry_delay = job.calculate_next_retry_delay()
                job.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
                job.make_visible()

                # Re-enqueue for retry
                self.processing_jobs.pop(job.job_id, None)
                self.priority_queue.enqueue(job)

                self._update_metrics("failed", processing_time)

                if self.storage_adapter:
                    await self.storage_adapter.update_job_status(job.job_id, JobStatus.RETRYING, error.dict())

                logger.warning(
                    "Job failed, scheduling retry",
                    job_id=job.job_id,
                    queue_name=self.name,
                    attempt=job.attempt_count,
                    max_attempts=job.max_attempts,
                    retry_delay=retry_delay,
                    error=str(e)
                )

    async def _visibility_monitor(self):
        """Monitor and handle visibility timeouts."""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                expired_jobs = []

                # Find expired jobs
                for job_id, job in self.processing_jobs.items():
                    if job.visibility_timeout and current_time >= job.visibility_timeout:
                        expired_jobs.append(job)

                # Handle expired jobs
                for job in expired_jobs:
                    logger.warning(
                        "Job visibility timeout expired",
                        job_id=job.job_id,
                        queue_name=self.name,
                        processing_time=(current_time - job.visibility_timeout).total_seconds()
                    )

                    # Make job visible again for retry
                    job.make_visible()
                    self.processing_jobs.pop(job.job_id, None)
                    self.priority_queue.enqueue(job)

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(
                    "Visibility monitor error",
                    queue_name=self.name,
                    error=str(e)
                )
                await asyncio.sleep(5)

    def _update_metrics(self, outcome: str, processing_time: float):
        """Update queue metrics."""
        self.metrics["jobs_processed"] += 1

        if outcome == "completed":
            self.metrics["jobs_completed"] += 1
        elif outcome == "failed":
            self.metrics["jobs_failed"] += 1
        elif outcome == "dead_lettered":
            self.metrics["jobs_dead_lettered"] += 1

        # Update average processing time
        total_jobs = self.metrics["jobs_processed"]
        current_avg = self.metrics["avg_processing_time"]
        self.metrics["avg_processing_time"] = (
            (current_avg * (total_jobs - 1) + processing_time) / total_jobs
        )

    def _update_queue_lag(self):
        """Update queue lag metric."""
        current_time = datetime.now(timezone.utc)
        next_job = self.priority_queue.peek_next(current_time)

        if next_job:
            lag = (current_time - next_job.scheduled_at).total_seconds()
            self.metrics["queue_lag_seconds"] = max(0, lag)
        else:
            self.metrics["queue_lag_seconds"] = 0.0

    def register_handler(self, handler_name: str, handler: Callable):
        """Register a job handler."""
        self.job_handlers[handler_name] = handler
        logger.info("Job handler registered", handler_name=handler_name, queue_name=self.name)

    async def replay_dlq_message(self, job_id: str) -> bool:
        """Replay a message from the dead letter queue."""
        job = self.dead_letter_queue.get_message(job_id)
        if not job:
            return False

        # Reset job for replay
        job.status = JobStatus.QUEUED
        job.attempt_count = 0
        job.scheduled_at = datetime.now(timezone.utc)
        job.make_visible()
        job.error_history.clear()
        job.last_error = None

        # Remove from DLQ and re-enqueue
        self.dead_letter_queue.remove_message(job_id)
        self.priority_queue.enqueue(job)

        logger.info("DLQ message replayed", job_id=job_id, queue_name=self.name)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        return {
            "queue_name": self.name,
            "tenant_id": self.tenant_id,
            "queue_stats": self.priority_queue.get_stats(),
            "dlq_stats": self.dead_letter_queue.get_stats(),
            "processing_jobs": len(self.processing_jobs),
            "completed_jobs": len(self.completed_jobs),
            "metrics": self.metrics.copy(),
            "visibility_timeout_seconds": self.visibility_timeout_seconds,
            "max_concurrent_jobs": self.max_concurrent_jobs
        }
