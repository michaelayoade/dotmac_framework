"""
Enhanced scheduler with RRULE + TZ + DST correctness, jitter, and catch-up functionality.
"""

import asyncio
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import structlog
from dateutil.rrule import rrulestr
from pydantic import BaseModel, Field, field_validator

from ..contracts.common_schemas import (
    ExecutionContext,
    OperationMetadata,
    RetryPolicy,
    TimeoutPolicy,
    ErrorInfo,
    Priority,
    ConfigDict
)

logger = structlog.get_logger(__name__)


class ScheduleDriftMetrics:
    """Metrics for tracking scheduler drift."""

    def __init__(self):
        """  Init   operation."""
        self.drift_measurements: List[float] = []
        self.max_measurements = 1000
        self.alert_threshold_seconds = 60.0
        self.p95_threshold_seconds = 60.0

    def record_drift(self, scheduled_time: datetime, actual_time: datetime):
        """Record drift measurement."""
        drift_seconds = abs((actual_time - scheduled_time).total_seconds())
        self.drift_measurements.append(drift_seconds)

        # Keep only recent measurements
        if len(self.drift_measurements) > self.max_measurements:
            self.drift_measurements = self.drift_measurements[-self.max_measurements :]

        # Check for alert threshold
        if drift_seconds > self.alert_threshold_seconds:
            logger.warning(
                "Scheduler drift alert",
                drift_seconds=drift_seconds,
                scheduled_time=scheduled_time.isoformat(),
                actual_time=actual_time.isoformat(),
            )

    def get_p95_drift(self) -> float:
        """Get 95th percentile drift."""
        if not self.drift_measurements:
            return 0.0

        sorted_measurements = sorted(self.drift_measurements)
        p95_index = int(len(sorted_measurements) * 0.95)
        return (
            sorted_measurements[p95_index]
            if p95_index < len(sorted_measurements)
            else sorted_measurements[-1]
        )

    def get_drift_stats(self) -> Dict[str, float]:
        """Get drift statistics."""
        if not self.drift_measurements:
            return {"count": 0, "avg": 0.0, "p95": 0.0, "max": 0.0}

        return {
            "count": len(self.drift_measurements),
            "avg": sum(self.drift_measurements) / len(self.drift_measurements),
            "p95": self.get_p95_drift(),
            "max": max(self.drift_measurements),
        }


class EnhancedScheduleDefinition(BaseModel):
    """Enhanced schedule definition with RRULE and timezone support."""

    id: str = Field(..., description="Schedule identifier")
    name: str = Field(..., description="Schedule name")
    description: Optional[str] = Field(None, description="Schedule description")

    # Enhanced timing configuration
    rrule_expression: Optional[str] = Field(
        None, description="RRULE expression for complex recurrence"
    )
    cron_expression: Optional[str] = Field(
        None, description="Cron expression (legacy support)"
    )
    interval_seconds: Optional[int] = Field(
        None, ge=1, description="Simple interval in seconds"
    )

    # Timezone and DST handling
    timezone: str = Field(
        "UTC", description="Timezone for schedule (e.g., 'America/New_York')"
    )
    dst_aware: bool = Field(True, description="Handle daylight saving time transitions")

    # Time boundaries
    start_time: Optional[datetime] = Field(None, description="Schedule start time")
    end_time: Optional[datetime] = Field(None, description="Schedule end time")

    # Jitter and catch-up configuration
    jitter_seconds: Optional[int] = Field(
        None, ge=0, description="Maximum jitter in seconds"
    )
    catch_up_missed: bool = Field(
        True, description="Catch up missed executions on startup"
    )
    max_catch_up_executions: int = Field(
        5, ge=0, description="Maximum missed executions to catch up"
    )

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

    @field_validator("rrule_expression")
    @classmethod
    def validate_rrule_expression(cls, v):
        """Validate Rrule Expression operation."""
        if v:
            try:
                rrulestr(v)
            except Exception as e:
                raise ValueError(f"Invalid RRULE expression: {e}")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v):
        """Validate Timezone operation."""
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError(f"Invalid timezone: {e}")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v, info):
        """Validate End Time operation."""
        start_time = info.data.get("start_time")
        if v and start_time and v <= start_time:
            raise ValueError("End time must be after start time")
        return v

    model_config = ConfigDict(extra="allow")

@dataclass
class ScheduleExecution:
    """Enhanced execution state with drift tracking."""

    execution_id: str
    schedule_id: str
    job_id: str
    status: str = "scheduled"
    scheduled_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actual_start_time: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    error: Optional[ErrorInfo] = None
    retry_count: int = 0
    drift_seconds: Optional[float] = None
    is_catch_up: bool = False

    def calculate_drift(self):
        """Calculate and record drift."""
        if self.actual_start_time:
            self.drift_seconds = abs(
                (self.actual_start_time - self.scheduled_time).total_seconds()
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "schedule_id": self.schedule_id,
            "job_id": self.job_id,
            "status": self.status,
            "scheduled_time": self.scheduled_time.isoformat(),
            "actual_start_time": (
                self.actual_start_time.isoformat() if self.actual_start_time else None
            ),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context.model_dump() if self.context else None,
            "error": self.error.model_dump() if self.error else None,
            "retry_count": self.retry_count,
            "drift_seconds": self.drift_seconds,
            "is_catch_up": self.is_catch_up,
        }


class EnhancedCronScheduler:
    """Enhanced scheduler with RRULE, timezone, and DST support."""

    def __init__(self):
        """  Init   operation."""
        self.schedules: Dict[str, EnhancedScheduleDefinition] = {}
        self.next_runs: Dict[str, datetime] = {}
        self.last_runs: Dict[str, datetime] = {}
        self.drift_metrics = ScheduleDriftMetrics()

    def add_schedule(self, schedule: EnhancedScheduleDefinition):
        """Add a schedule to the scheduler."""
        self.schedules[schedule.id] = schedule
        self._calculate_next_run(schedule)
        logger.info(
            "Schedule added", schedule_id=schedule.id, timezone=schedule.timezone
        )

    def remove_schedule(self, schedule_id: str):
        """Remove a schedule from the scheduler."""
        self.schedules.pop(schedule_id, None)
        self.next_runs.pop(schedule_id, None)
        self.last_runs.pop(schedule_id, None)

    def get_due_schedules(
        self, current_time: datetime
    ) -> List[EnhancedScheduleDefinition]:
        """Get schedules that are due to run."""
        due_schedules = []

        for schedule_id, schedule in self.schedules.items():
            if not schedule.enabled:
                continue

            next_run = self.next_runs.get(schedule_id)
            if next_run and current_time >= next_run:
                due_schedules.append(schedule)

                # Record last run and calculate next
                self.last_runs[schedule_id] = current_time
                self._calculate_next_run(schedule)

                # Record drift
                self.drift_metrics.record_drift(next_run, current_time)

        return due_schedules

    def get_catch_up_executions(
        self,
        schedule: EnhancedScheduleDefinition,
        last_run: Optional[datetime],
        current_time: datetime,
    ) -> List[datetime]:
        """Get missed executions that need to be caught up."""
        if not schedule.catch_up_missed or not last_run:
            return []

        catch_up_times = []

        try:
            if schedule.rrule_expression:
                # Use RRULE for catch-up
                rule = rrulestr(schedule.rrule_expression)
                tz = ZoneInfo(schedule.timezone)

                # Get all occurrences between last run and now
                start_time = last_run.astimezone(tz)
                end_time = current_time.astimezone(tz)

                occurrences = list(rule.between(start_time, end_time, inc=False))
                catch_up_times = [occ.astimezone(timezone.utc) for occ in occurrences]

            elif schedule.cron_expression:
                # Use croniter for catch-up (if available)
                from croniter import croniter

                cron = croniter(schedule.cron_expression, last_run)

                while len(catch_up_times) < schedule.max_catch_up_executions:
                    next_time = cron.get_next(datetime)
                    if next_time >= current_time:
                        break
                    catch_up_times.append(next_time)

            elif schedule.interval_seconds:
                # Simple interval catch-up
                next_time = last_run + timedelta(seconds=schedule.interval_seconds)
                while (
                    next_time < current_time
                    and len(catch_up_times) < schedule.max_catch_up_executions
                ):
                    catch_up_times.append(next_time)
                    next_time += timedelta(seconds=schedule.interval_seconds)

        except Exception as e:
            logger.error(
                "Error calculating catch-up executions",
                schedule_id=schedule.id,
                error=str(e),
            )

        # Limit catch-up executions
        return catch_up_times[: schedule.max_catch_up_executions]

    def _calculate_next_run(self, schedule: EnhancedScheduleDefinition):  # noqa: C901
        """Calculate next run time with timezone and DST awareness."""
        try:
            now = datetime.now(timezone.utc)
            tz = ZoneInfo(schedule.timezone)

            # Convert current time to schedule timezone
            local_now = now.astimezone(tz)

            next_run = None

            if schedule.rrule_expression:
                # Use RRULE for complex recurrence patterns
                rule = rrulestr(schedule.rrule_expression)

                # Get next occurrence after current time
                next_occurrence = rule.after(local_now, inc=False)
                if next_occurrence:
                    next_run = next_occurrence.astimezone(timezone.utc)

            elif schedule.cron_expression:
                # Legacy cron support
                from croniter import croniter

                cron = croniter(schedule.cron_expression, local_now)
                next_occurrence = cron.get_next(datetime)
                next_run = next_occurrence.astimezone(timezone.utc)

            elif schedule.interval_seconds:
                # Simple interval scheduling
                if schedule.start_time:
                    start_time = schedule.start_time.astimezone(tz)
                    if start_time > local_now:
                        next_run = start_time.astimezone(timezone.utc)
                    else:
                        # Calculate next interval
                        elapsed = (local_now - start_time).total_seconds()
                        intervals_passed = int(elapsed // schedule.interval_seconds)
                        next_occurrence = start_time + timedelta(
                            seconds=(intervals_passed + 1) * schedule.interval_seconds
                        )
                        next_run = next_occurrence.astimezone(timezone.utc)
                else:
                    next_run = now + timedelta(seconds=schedule.interval_seconds)

            # Apply jitter if configured
            if next_run and schedule.jitter_seconds:
                jitter = secrets.randbelow(int((schedule.jitter_seconds) * 1000)) / 1000
                next_run += timedelta(seconds=jitter)

            # Check end time boundary
            if next_run and schedule.end_time and next_run > schedule.end_time:
                next_run = None

            # Store next run time
            if next_run:
                self.next_runs[schedule.id] = next_run
                logger.debug(
                    "Next run calculated",
                    schedule_id=schedule.id,
                    next_run=next_run.isoformat(),
                    timezone=schedule.timezone,
                )
            else:
                self.next_runs.pop(schedule.id, None)

        except Exception as e:
            logger.error(
                "Error calculating next run", schedule_id=schedule.id, error=str(e)
            )
            # Fallback: remove from next runs
            self.next_runs.pop(schedule.id, None)

    def get_drift_stats(self) -> Dict[str, Any]:
        """Get scheduler drift statistics."""
        return self.drift_metrics.get_drift_stats()

    def is_drift_alert_triggered(self) -> bool:
        """Check if drift alert should be triggered."""
        p95_drift = self.drift_metrics.get_p95_drift()
        return p95_drift > self.drift_metrics.p95_threshold_seconds


class EnhancedSchedulerSDK:
    """Enhanced scheduler SDK with RRULE, timezone, DST, jitter, and catch-up support."""

    def __init__(self, tenant_id: str, storage_adapter=None):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.storage_adapter = storage_adapter
        self.cron_scheduler = EnhancedCronScheduler()
        self.schedules: Dict[str, EnhancedScheduleDefinition] = {}
        self.executions: Dict[str, ScheduleExecution] = {}
        self.job_handlers: Dict[str, Callable] = {}
        self.running = False
        self.startup_time = datetime.now(timezone.utc)

        logger.info("Enhanced SchedulerSDK initialized", tenant_id=tenant_id)

    async def create_schedule(self, schedule: EnhancedScheduleDefinition) -> str:
        """Create a new enhanced schedule."""
        schedule.tenant_id = self.tenant_id
        schedule.metadata.updated_at = datetime.now(timezone.utc)

        self.schedules[schedule.id] = schedule
        self.cron_scheduler.add_schedule(schedule)

        if self.storage_adapter:
            await self.storage_adapter.store_schedule(schedule)

        logger.info(
            "Enhanced schedule created",
            schedule_id=schedule.id,
            tenant_id=self.tenant_id,
            timezone=schedule.timezone,
            rrule=schedule.rrule_expression,
            jitter_seconds=schedule.jitter_seconds,
        )

        return schedule.id

    async def start_scheduler(self):
        """Start the enhanced scheduler with catch-up logic."""
        if self.running:
            return

        self.running = True

        # Perform catch-up for missed executions
        await self._perform_startup_catchup()

        # Start scheduler loop
        scheduler_task = asyncio.create_task(self._enhanced_scheduler_loop())
        processor_task = asyncio.create_task(self._job_processor())
        drift_monitor_task = asyncio.create_task(self._drift_monitor())

        logger.info("Enhanced scheduler started", tenant_id=self.tenant_id)

        try:
            await asyncio.gather(scheduler_task, processor_task, drift_monitor_task)
        except Exception as e:
            logger.error(
                "Enhanced scheduler error", error=str(e), tenant_id=self.tenant_id
            )
        finally:
            self.running = False

    async def _perform_startup_catchup(self):
        """Perform catch-up for missed executions on startup."""
        current_time = datetime.now(timezone.utc)

        for schedule in self.schedules.values():
            if not schedule.enabled or not schedule.catch_up_missed:
                continue

            # Get last run time from storage or use startup time
            last_run = None
            if self.storage_adapter:
                last_run = await self.storage_adapter.get_last_execution_time(
                    schedule.id
                )

            if not last_run:
                # Use a reasonable lookback period (e.g., 1 hour)
                last_run = current_time - timedelta(hours=1)

            # Get missed executions
            catch_up_times = self.cron_scheduler.get_catch_up_executions(
                schedule, last_run, current_time
            )

            # Schedule catch-up executions
            for catch_up_time in catch_up_times:
                execution_id = str(uuid.uuid4())
                job_id = f"{schedule.id}_{execution_id}"

                context = ExecutionContext(
                    execution_id=execution_id,
                    tenant_id=self.tenant_id,
                )

                execution = ScheduleExecution(
                    execution_id=execution_id,
                    schedule_id=schedule.id,
                    job_id=job_id,
                    scheduled_time=catch_up_time,
                    input_data=schedule.job_parameters.model_copy(),
                    context=context,
                    is_catch_up=True,
                )

                self.executions[execution_id] = execution

                # Execute immediately (catch-up)
                asyncio.create_task(self._execute_job_with_retry(schedule, execution))

                logger.info(
                    "Catch-up execution scheduled",
                    schedule_id=schedule.id,
                    execution_id=execution_id,
                    scheduled_time=catch_up_time.isoformat(),
                )

    async def _enhanced_scheduler_loop(self):
        """Enhanced scheduler loop with drift monitoring."""
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

                    execution = ScheduleExecution(
                        execution_id=execution_id,
                        schedule_id=schedule.id,
                        job_id=job_id,
                        scheduled_time=current_time,
                        actual_start_time=current_time,
                        input_data=schedule.job_parameters.model_copy(),
                        context=context,
                    )

                    execution.calculate_drift()
                    self.executions[execution_id] = execution

                    # Execute job
                    asyncio.create_task(
                        self._execute_job_with_retry(schedule, execution)
                    )

                    logger.debug(
                        "Enhanced job scheduled",
                        schedule_id=schedule.id,
                        execution_id=execution_id,
                        drift_seconds=execution.drift_seconds,
                    )

                # Sleep for a short interval
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(
                    "Enhanced scheduler loop error",
                    error=str(e),
                    tenant_id=self.tenant_id,
                )
                await asyncio.sleep(5)

    async def _job_processor(self):
        """Process jobs with enhanced error handling."""
        # Implementation similar to original but with enhanced features
        pass

    async def _drift_monitor(self):
        """Monitor scheduler drift and trigger alerts."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                if self.cron_scheduler.is_drift_alert_triggered():
                    drift_stats = self.cron_scheduler.get_drift_stats()
                    logger.warning(
                        "Scheduler drift alert triggered",
                        tenant_id=self.tenant_id,
                        drift_stats=drift_stats,
                    )

                    # Here you could send alerts to monitoring systems

            except Exception as e:
                logger.error("Drift monitor error", error=str(e))
                await asyncio.sleep(60)

    async def _execute_job_with_retry(  # noqa: C901
        self, schedule: EnhancedScheduleDefinition, execution: ScheduleExecution
    ):
        """Execute job with enhanced retry logic."""
        max_retries = 0
        if schedule.retry_policy:
            max_retries = schedule.retry_policy.max_attempts - 1

        for attempt in range(max_retries + 1):
            execution.retry_count = attempt

            try:
                execution.status = "running"
                execution.started_at = datetime.now(timezone.utc)

                # Get handler
                handler = self.job_handlers.get(schedule.job_handler)
                if not handler:
                    raise ValueError(f"Handler {schedule.job_handler} not registered")

                # Prepare input data
                input_data = schedule.job_parameters.model_copy()
                input_data.update(execution.input_data)

                # Execute with timeout
                timeout = None
                if (
                    schedule.timeout_policy
                    and schedule.timeout_policy.execution_timeout
                ):
                    timeout = schedule.timeout_policy.execution_timeout

                if timeout:
                    result = await asyncio.wait_for(
                        handler(input_data, execution.context), timeout=timeout
                    )
                else:
                    result = await handler(input_data, execution.context)

                # Store result
                if isinstance(result, dict):
                    execution.output_data = result
                else:
                    execution.output_data = {"result": result}

                execution.status = "completed"
                execution.completed_at = datetime.now(timezone.utc)

                if self.storage_adapter:
                    await self.storage_adapter.store_execution(execution)

                logger.info(
                    "Enhanced job executed successfully",
                    schedule_id=schedule.id,
                    execution_id=execution.execution_id,
                    drift_seconds=execution.drift_seconds,
                    is_catch_up=execution.is_catch_up,
                )

                break

            except Exception as e:
                execution.status = "failed"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error = ErrorInfo(
                    error_type=type(e).__name__,
                    message=str(e),
                    timestamp=datetime.now(timezone.utc),
                )

                if attempt < max_retries and self._should_retry(schedule, execution):
                    delay = self._calculate_retry_delay(schedule.retry_policy, attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    if self.storage_adapter:
                        await self.storage_adapter.store_execution(execution)

                    logger.error(
                        "Enhanced job execution failed",
                        schedule_id=schedule.id,
                        execution_id=execution.execution_id,
                        error=str(e),
                        retry_count=execution.retry_count,
                    )
                    break

    def _should_retry(
        self, schedule: EnhancedScheduleDefinition, execution: ScheduleExecution
    ) -> bool:
        """Determine if job should be retried."""
        if not schedule.retry_policy or not execution.error:
            return False

        error_type = execution.error.error_type.lower()
        retry_on = [err.lower() for err in schedule.retry_policy.retry_on]

        return any(retry_type in error_type for retry_type in retry_on)

    def _calculate_retry_delay(self, retry_policy: RetryPolicy, attempt: int) -> float:
        """Calculate retry delay with backoff and jitter."""
        delay = retry_policy.initial_delay * (retry_policy.backoff_multiplier**attempt)
        delay = min(delay, retry_policy.max_delay)

        if retry_policy.jitter:
            delay *= 0.5 + secrets.randbelow(1000000) / 1000000 * 0.5

        return delay

    def register_job_handler(self, handler_name: str, handler: Callable):
        """Register a job handler function."""
        self.job_handlers[handler_name] = handler

    async def get_drift_statistics(self) -> Dict[str, Any]:
        """Get comprehensive drift statistics."""
        return {
            "drift_stats": self.cron_scheduler.get_drift_stats(),
            "alert_triggered": self.cron_scheduler.is_drift_alert_triggered(),
            "p95_threshold": self.cron_scheduler.drift_metrics.p95_threshold_seconds,
            "alert_threshold": self.cron_scheduler.drift_metrics.alert_threshold_seconds,
        }

    async def stop_scheduler(self):
        """Stop the enhanced scheduler."""
        self.running = False
        logger.info("Enhanced scheduler stopped", tenant_id=self.tenant_id)
