"""
Scheduler SDK for time-based job scheduling and cron-like functionality.

This module provides comprehensive scheduling capabilities including:
- Cron-based scheduling
- One-time and recurring jobs
- Job queue management
- Schedule validation and parsing
- Timezone support
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
from croniter import croniter
from pydantic import BaseModel, Field, field_validator

from ..contracts.common_schemas import (
    ExecutionContext,
    OperationMetadata,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    Priority,
)

logger = structlog.get_logger(__name__)


class ScheduleType(str, Enum):
    """Schedule types."""

    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class JobStatus(str, Enum):
    """Job status enumeration."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    SKIPPED = "skipped"


class ScheduleDefinition(BaseModel):
    """Schedule definition with timing configuration."""

    id: str = Field(..., description="Schedule identifier")
    name: str = Field(..., description="Schedule name")
    schedule_type: ScheduleType = Field(..., description="Schedule type")
    description: Optional[str] = Field(None, description="Schedule description")

    # Timing configuration
    cron_expression: Optional[str] = Field(None, description="Cron expression")
    interval_seconds: Optional[int] = Field(
        None, ge=1, description="Interval in seconds"
    )
    start_time: Optional[datetime] = Field(None, description="Schedule start time")
    end_time: Optional[datetime] = Field(None, description="Schedule end time")
    timezone: str = Field("UTC", description="Timezone for schedule")

    # Job configuration
    job_handler: str = Field(..., description="Job handler function")
    job_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Job parameters"
    )

    # Execution settings
    enabled: bool = Field(True, description="Schedule enabled status")
    max_instances: int = Field(1, ge=1, description="Maximum concurrent instances")
    priority: Priority = Field(Priority.NORMAL, description="Job priority")

    # Policies
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry policy")
    timeout_policy: Optional[TimeoutPolicy] = Field(None, description="Timeout policy")

    # Metadata
    tenant_id: str = Field(..., description="Tenant identifier")
    metadata: OperationMetadata = Field(default_factory=OperationMetadata)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v, info):
        """Validate Cron Expression operation."""
        if v and info.data.get("schedule_type") == ScheduleType.CRON:
            try:
                croniter(v)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {e}")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v, info):
        """Validate End Time operation."""
        start_time = info.data.get("start_time")
        if v and start_time and v <= start_time:
            raise ValueError("End time must be after start time")
        return v

    class Config:
        """Class for Config operations."""
        extra = "allow"


@dataclass
class JobExecution:
    """Runtime execution state of a scheduled job."""

    execution_id: str
    schedule_id: str
    job_id: str
    status: JobStatus = JobStatus.SCHEDULED
    scheduled_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    error: Optional[ErrorInfo] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "schedule_id": self.schedule_id,
            "job_id": self.job_id,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context.dict() if self.context else None,
            "error": self.error.dict() if self.error else None,
            "retry_count": self.retry_count,
        }


class CronScheduler:
    """Cron-based scheduler implementation."""

    def __init__(self):
        """  Init   operation."""
        self.schedules: Dict[str, ScheduleDefinition] = {}
        self.next_runs: Dict[str, datetime] = {}

    def add_schedule(self, schedule: ScheduleDefinition):
        """Add a schedule to the scheduler."""
        self.schedules[schedule.id] = schedule
        self._calculate_next_run(schedule)

    def remove_schedule(self, schedule_id: str):
        """Remove a schedule from the scheduler."""
        self.schedules.pop(schedule_id, None)
        self.next_runs.pop(schedule_id, None)

    def get_due_schedules(self, current_time: datetime) -> List[ScheduleDefinition]:
        """Get schedules that are due to run."""
        due_schedules = []

        for schedule_id, schedule in self.schedules.items():
            if not schedule.enabled:
                continue

            next_run = self.next_runs.get(schedule_id)
            if next_run and current_time >= next_run:
                due_schedules.append(schedule)
                self._calculate_next_run(schedule)

        return due_schedules

    def _calculate_next_run(self, schedule: ScheduleDefinition):
        """
        Calculate next run time for a schedule using strategy pattern.
        
        REFACTORED: Replaced 14-complexity if-elif chain with strategy pattern call.
        Complexity reduced from 14→3.
        """
        from .schedule_strategies import create_schedule_engine
        
        schedule_engine = create_schedule_engine()
        next_run = schedule_engine.calculate_next_run(schedule)
        
        if next_run:
            self.next_runs[schedule.id] = next_run
        else:
            # Schedule should not run again, remove from next_runs
            self.next_runs.pop(schedule.id, None)


class JobQueue:
    """Queue for managing scheduled job executions."""

    def __init__(self, max_concurrent: int = 10):
        """  Init   operation."""
        self.max_concurrent = max_concurrent
        self.pending_jobs: List[JobExecution] = []
        self.running_jobs: Set[str] = set()
        self.completed_jobs: Set[str] = set()
        self.failed_jobs: Set[str] = set()

    async def enqueue(self, job_execution: JobExecution):
        """Add job to queue."""
        # Insert based on priority and scheduled time
        inserted = False
        for i, existing_job in enumerate(self.pending_jobs):
            if self._compare_priority(job_execution, existing_job) > 0 or (
                self._compare_priority(job_execution, existing_job) == 0
                and job_execution.scheduled_time < existing_job.scheduled_time
            ):
                self.pending_jobs.insert(i, job_execution)
                inserted = True
                break

        if not inserted:
            self.pending_jobs.append(job_execution)

    async def dequeue(self) -> Optional[JobExecution]:
        """Get next job from queue if capacity allows."""
        if len(self.running_jobs) >= self.max_concurrent:
            return None

        now = datetime.now(timezone.utc)

        # Find first job that is due
        for i, job_execution in enumerate(self.pending_jobs):
            if job_execution.scheduled_time <= now:
                job_execution = self.pending_jobs.pop(i)
                self.running_jobs.add(job_execution.execution_id)
                return job_execution

        return None

    def mark_completed(self, execution_id: str, success: bool):
        """Mark job as completed."""
        self.running_jobs.discard(execution_id)
        if success:
            self.completed_jobs.add(execution_id)
        else:
            self.failed_jobs.add(execution_id)

    def _compare_priority(self, job1: JobExecution, job2: JobExecution) -> int:
        """Compare job priorities."""
        priority_order = {
            Priority.LOW: 0,
            Priority.NORMAL: 1,
            Priority.HIGH: 2,
            Priority.CRITICAL: 3,
        }

        # Get priority from context or use normal as default
        p1 = (
            getattr(job1.context, "priority", Priority.NORMAL)
            if job1.context
            else Priority.NORMAL
        )
        p2 = (
            getattr(job2.context, "priority", Priority.NORMAL)
            if job2.context
            else Priority.NORMAL
        )

        return priority_order.get(p1, 1) - priority_order.get(p2, 1)


class JobScheduler:
    """Job scheduler for executing scheduled jobs."""

    def __init__(self):
        """  Init   operation."""
        self.job_handlers: Dict[str, Callable] = {}
        self.running_instances: Dict[str, Set[str]] = {}  # schedule_id -> execution_ids

    def register_handler(self, handler_name: str, handler: Callable):
        """Register a job handler."""
        self.job_handlers[handler_name] = handler

    async def execute_job(
        self,
        schedule: ScheduleDefinition,
        job_execution: JobExecution,
    ) -> bool:
        """Execute a scheduled job."""
        try:
            # Check max instances
            if not self._can_start_instance(schedule, job_execution.execution_id):
                job_execution.status = JobStatus.SKIPPED
                job_execution.completed_at = datetime.now(timezone.utc)

                logger.info(
                    "Job execution skipped - max instances reached",
                    schedule_id=schedule.id,
                    execution_id=job_execution.execution_id,
                )
                return True

            job_execution.status = JobStatus.RUNNING
            job_execution.started_at = datetime.now(timezone.utc)

            # Get handler
            handler = self.job_handlers.get(schedule.job_handler)
            if not handler:
                raise ValueError(f"Handler {schedule.job_handler} not registered")

            # Prepare input data
            input_data = schedule.job_parameters.copy()
            input_data.update(job_execution.input_data)

            # Apply timeout if specified
            timeout = None
            if schedule.timeout_policy and schedule.timeout_policy.execution_timeout:
                timeout = schedule.timeout_policy.execution_timeout

            # Execute with timeout
            if timeout:
                result = await asyncio.wait_for(
                    handler(input_data, job_execution.context), timeout=timeout
                )
            else:
                result = await handler(input_data, job_execution.context)

            # Store result
            if isinstance(result, dict):
                job_execution.output_data = result
            else:
                job_execution.output_data = {"result": result}

            job_execution.status = JobStatus.COMPLETED
            job_execution.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Job executed successfully",
                schedule_id=schedule.id,
                execution_id=job_execution.execution_id,
            )

            return True

        except asyncio.TimeoutError:
            job_execution.status = JobStatus.FAILED
            job_execution.completed_at = datetime.now(timezone.utc)
            job_execution.error = ErrorInfo(
                error_type="TimeoutError",
                message=f"Job execution timed out after {timeout} seconds",
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Job execution timed out",
                schedule_id=schedule.id,
                execution_id=job_execution.execution_id,
                timeout=timeout,
            )
            return False

        except Exception as e:
            job_execution.status = JobStatus.FAILED
            job_execution.completed_at = datetime.now(timezone.utc)
            job_execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                timestamp=datetime.now(timezone.utc),
            )

            logger.error(
                "Job execution failed",
                schedule_id=schedule.id,
                execution_id=job_execution.execution_id,
                error=str(e),
            )
            return False

        finally:
            self._remove_instance(schedule.id, job_execution.execution_id)

    def _can_start_instance(
        self, schedule: ScheduleDefinition, execution_id: str
    ) -> bool:
        """Check if a new instance can be started."""
        if schedule.id not in self.running_instances:
            self.running_instances[schedule.id] = set()

        running_count = len(self.running_instances[schedule.id])
        if running_count >= schedule.max_instances:
            return False

        self.running_instances[schedule.id].add(execution_id)
        return True

    def _remove_instance(self, schedule_id: str, execution_id: str):
        """Remove instance from running instances."""
        if schedule_id in self.running_instances:
            self.running_instances[schedule_id].discard(execution_id)

            if not self.running_instances[schedule_id]:
                del self.running_instances[schedule_id]


class SchedulerSDK:
    """SDK for job scheduling and management."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.cron_scheduler = CronScheduler()
        self.job_scheduler = JobScheduler()
        self.job_queue = JobQueue()
        self.schedules: Dict[str, ScheduleDefinition] = {}
        self.executions: Dict[str, JobExecution] = {}
        self.running = False

        logger.info("SchedulerSDK initialized", tenant_id=tenant_id)

    async def create_schedule(self, schedule: ScheduleDefinition) -> str:
        """Create a new schedule."""
        schedule.tenant_id = self.tenant_id
        schedule.metadata.updated_at = datetime.now(timezone.utc)

        self.schedules[schedule.id] = schedule
        self.cron_scheduler.add_schedule(schedule)

        if self.storage_adapter:
            await self.storage_adapter.store_schedule(schedule)

        logger.info(
            "Schedule created",
            schedule_id=schedule.id,
            tenant_id=self.tenant_id,
        )

        return schedule.id

    async def update_schedule(self, schedule: ScheduleDefinition) -> bool:
        """Update an existing schedule."""
        if schedule.id not in self.schedules:
            return False

        schedule.tenant_id = self.tenant_id
        schedule.metadata.updated_at = datetime.now(timezone.utc)

        self.schedules[schedule.id] = schedule
        self.cron_scheduler.add_schedule(schedule)  # This will update the schedule

        if self.storage_adapter:
            await self.storage_adapter.store_schedule(schedule)

        logger.info(
            "Schedule updated",
            schedule_id=schedule.id,
            tenant_id=self.tenant_id,
        )

        return True

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if schedule_id not in self.schedules:
            return False

        del self.schedules[schedule_id]
        self.cron_scheduler.remove_schedule(schedule_id)

        if self.storage_adapter:
            await self.storage_adapter.delete_schedule(schedule_id)

        logger.info(
            "Schedule deleted",
            schedule_id=schedule_id,
            tenant_id=self.tenant_id,
        )

        return True

    async def trigger_schedule(
        self,
        schedule_id: str,
        input_data: Dict[str, Any] = None,
        context: Optional[ExecutionContext] = None,
    ) -> Optional[str]:
        """Manually trigger a schedule."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None

        execution_id = str(uuid.uuid4())
        job_id = f"{schedule_id}_{execution_id}"

        if not context:
            context = ExecutionContext(
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )

        job_execution = JobExecution(
            execution_id=execution_id,
            schedule_id=schedule_id,
            job_id=job_id,
            scheduled_time=datetime.now(timezone.utc),
            input_data=input_data or {},
            context=context,
        )

        self.executions[execution_id] = job_execution
        await self.job_queue.enqueue(job_execution)

        logger.info(
            "Schedule triggered manually",
            schedule_id=schedule_id,
            execution_id=execution_id,
            tenant_id=self.tenant_id,
        )

        return execution_id

    async def start_scheduler(self):
        """Start the scheduler."""
        if self.running:
            return

        self.running = True

        # Start scheduler loop and job processor
        scheduler_task = asyncio.create_task(self._scheduler_loop())
        processor_task = asyncio.create_task(self._job_processor())

        logger.info("Scheduler started", tenant_id=self.tenant_id)

        try:
            await asyncio.gather(scheduler_task, processor_task)
        except Exception as e:
            logger.error("Scheduler error", error=str(e), tenant_id=self.tenant_id)
        finally:
            self.running = False

    async def stop_scheduler(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped", tenant_id=self.tenant_id)

    async def _scheduler_loop(self):
        """Main scheduler loop that checks for due schedules."""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                due_schedules = self.cron_scheduler.get_due_schedules(current_time)

                for schedule in due_schedules:
                    execution_id = str(uuid.uuid4())
                    job_id = f"{schedule.id}_{execution_id}"

                    context = ExecutionContext(
                        execution_id=execution_id,
                        tenant_id=self.tenant_id,
                    )

                    job_execution = JobExecution(
                        execution_id=execution_id,
                        schedule_id=schedule.id,
                        job_id=job_id,
                        scheduled_time=current_time,
                        input_data=schedule.job_parameters.copy(),
                        context=context,
                    )

                    self.executions[execution_id] = job_execution
                    await self.job_queue.enqueue(job_execution)

                    logger.debug(
                        "Job scheduled for execution",
                        schedule_id=schedule.id,
                        execution_id=execution_id,
                        tenant_id=self.tenant_id,
                    )

                # Sleep for a short interval before checking again
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(
                    "Scheduler loop error",
                    error=str(e),
                    tenant_id=self.tenant_id,
                )
                await asyncio.sleep(5)

    async def _job_processor(self):
        """Process jobs from the queue."""
        while self.running:
            try:
                job_execution = await self.job_queue.dequeue()
                if not job_execution:
                    await asyncio.sleep(0.1)
                    continue

                schedule = self.schedules.get(job_execution.schedule_id)
                if not schedule:
                    job_execution.status = JobStatus.FAILED
                    job_execution.error = ErrorInfo(
                        error_type="ScheduleNotFound",
                        message=f"Schedule {job_execution.schedule_id} not found",
                        timestamp=datetime.now(timezone.utc),
                    )
                    self.job_queue.mark_completed(job_execution.execution_id, False)
                    continue

                # Execute job with retry
                asyncio.create_task(
                    self._execute_job_with_retry(schedule, job_execution)
                )

            except Exception as e:
                logger.error(
                    "Job processor error",
                    error=str(e),
                    tenant_id=self.tenant_id,
                )
                await asyncio.sleep(1)

    async def _execute_job_with_retry(
        self,
        schedule: ScheduleDefinition,
        job_execution: JobExecution,
    ):
        """Execute job with retry logic."""
        max_retries = 0
        if schedule.retry_policy:
            max_retries = schedule.retry_policy.max_attempts - 1

        for attempt in range(max_retries + 1):
            job_execution.retry_count = attempt

            success = await self.job_scheduler.execute_job(schedule, job_execution)

            if success:
                self.job_queue.mark_completed(job_execution.execution_id, True)

                if self.storage_adapter:
                    await self.storage_adapter.store_execution(job_execution)

                break
            else:
                # Check if we should retry
                if attempt < max_retries and self._should_retry(
                    schedule, job_execution
                ):
                    # Calculate delay
                    delay = self._calculate_retry_delay(schedule.retry_policy, attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final failure
                    self.job_queue.mark_completed(job_execution.execution_id, False)

                    if self.storage_adapter:
                        await self.storage_adapter.store_execution(job_execution)

                    break

    def _should_retry(
        self, schedule: ScheduleDefinition, job_execution: JobExecution
    ) -> bool:
        """Determine if job should be retried."""
        if not schedule.retry_policy:
            return False

        if not job_execution.error:
            return False

        error_type = job_execution.error.error_type.lower()
        retry_on = [err.lower() for err in schedule.retry_policy.retry_on]

        return any(retry_type in error_type for retry_type in retry_on)

    def _calculate_retry_delay(self, retry_policy: RetryPolicy, attempt: int) -> float:
        """Calculate retry delay with backoff."""
        delay = retry_policy.initial_delay * (retry_policy.backoff_multiplier**attempt)
        delay = min(delay, retry_policy.max_delay)

        if retry_policy.jitter:
            import secrets

            delay *= 0.5 + secrets.randbelow(1000000) / 1000000 * 0.5

        return delay

    def register_job_handler(self, handler_name: str, handler: Callable):
        """Register a job handler function."""
        self.job_scheduler.register_handler(handler_name, handler)

    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get job execution by ID."""
        return self.executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a pending or running job execution."""
        job_execution = self.executions.get(execution_id)
        if not job_execution:
            return False

        if job_execution.status in [JobStatus.SCHEDULED, JobStatus.RUNNING]:
            job_execution.status = JobStatus.CANCELLED
            job_execution.completed_at = datetime.now(timezone.utc)

            # Remove from queue if pending
            if job_execution in self.job_queue.pending_jobs:
                self.job_queue.pending_jobs.remove(job_execution)

            logger.info(
                "Job execution cancelled",
                execution_id=execution_id,
                tenant_id=self.tenant_id,
            )
            return True

        return False

    async def get_schedule_status(self, schedule_id: str) -> Dict[str, Any]:
        """Get schedule status information."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return {}

        next_run = self.cron_scheduler.next_runs.get(schedule_id)
        running_instances = len(
            self.job_scheduler.running_instances.get(schedule_id, set())
        )

        return {
            "schedule_id": schedule_id,
            "enabled": schedule.enabled,
            "next_run": next_run.isoformat() if next_run else None,
            "running_instances": running_instances,
            "max_instances": schedule.max_instances,
        }
