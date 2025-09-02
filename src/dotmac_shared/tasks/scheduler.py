"""
Advanced Task Scheduler with Cron-like Scheduling

Provides comprehensive task scheduling capabilities:
- Cron expression parsing and scheduling
- Distributed scheduling with leader election
- Schedule persistence and recovery
- Timezone-aware scheduling
- Schedule monitoring and metrics
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from croniter import croniter

from redis.asyncio import Redis as AsyncRedis

from .engine import Task, TaskConfig, TaskPriority, TaskError
from .queue import RedisTaskQueue
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CronSchedule:
    """Cron schedule configuration."""
    expression: str
    timezone: str = "UTC"
    enabled: bool = True
    max_instances: int = 1  # Maximum concurrent instances
    overlap_policy: str = "skip"  # "skip", "allow", "replace"
    jitter: int = 0  # Random jitter in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate cron expression."""
        try:
            croniter(self.expression)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{self.expression}': {e}")

    def next_run_time(self, base_time: Optional[datetime] = None) -> datetime:
        """Calculate next run time."""
        base_time = base_time or datetime.now(timezone.utc)
        
        # Convert to specified timezone if needed
        if self.timezone != "UTC":
            import pytz
            tz = pytz.timezone(self.timezone)
            if base_time.tzinfo is None:
                base_time = timezone.utc.localize(base_time)
            base_time = base_time.astimezone(tz)
        
        cron = croniter(self.expression, base_time)
        next_time = cron.get_next(datetime)
        
        # Add jitter if specified
        if self.jitter > 0:
            import random
            jitter_seconds = random.randint(0, self.jitter)
            next_time += timedelta(seconds=jitter_seconds)
        
        return next_time

    def is_due(self, last_run: Optional[datetime] = None, now: Optional[datetime] = None) -> bool:
        """Check if schedule is due for execution."""
        now = now or datetime.now(timezone.utc)
        
        if not self.enabled:
            return False
        
        if last_run is None:
            return True
        
        next_run = self.next_run_time(last_run)
        return now >= next_run


class ScheduledTask:
    """
    Represents a scheduled task with its configuration.
    """

    def __init__(
        self,
        task_id: str,
        name: str,
        function_name: str,
        schedule: CronSchedule,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        task_config: TaskConfig = None,
        tenant_id: Optional[str] = None,
        description: str = "",
        tags: List[str] = None,
    ):
        self.task_id = task_id
        self.name = name
        self.function_name = function_name
        self.schedule = schedule
        self.args = args or []
        self.kwargs = kwargs or {}
        self.task_config = task_config or TaskConfig()
        self.tenant_id = tenant_id
        self.description = description
        self.tags = tags or []
        
        # Runtime state
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count: int = 0
        self.failure_count: int = 0
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'function_name': self.function_name,
            'schedule': {
                'expression': self.schedule.expression,
                'timezone': self.schedule.timezone,
                'enabled': self.schedule.enabled,
                'max_instances': self.schedule.max_instances,
                'overlap_policy': self.schedule.overlap_policy,
                'jitter': self.schedule.jitter,
                'metadata': self.schedule.metadata,
            },
            'args': self.args,
            'kwargs': self.kwargs,
            'task_config': {
                'max_retries': self.task_config.max_retries,
                'retry_delay': self.task_config.retry_delay,
                'retry_backoff': self.task_config.retry_backoff,
                'timeout': self.task_config.timeout,
                'priority': self.task_config.priority.value,
                'queue_name': self.task_config.queue_name,
                'tags': self.task_config.tags,
                'metadata': self.task_config.metadata,
            },
            'tenant_id': self.tenant_id,
            'description': self.description,
            'tags': self.tags,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'failure_count': self.failure_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledTask':
        """Create from dictionary."""
        schedule_data = data['schedule']
        schedule = CronSchedule(
            expression=schedule_data['expression'],
            timezone=schedule_data.get('timezone', 'UTC'),
            enabled=schedule_data.get('enabled', True),
            max_instances=schedule_data.get('max_instances', 1),
            overlap_policy=schedule_data.get('overlap_policy', 'skip'),
            jitter=schedule_data.get('jitter', 0),
            metadata=schedule_data.get('metadata', {}),
        )

        task_config_data = data.get('task_config', {})
        task_config = TaskConfig(
            max_retries=task_config_data.get('max_retries', 3),
            retry_delay=task_config_data.get('retry_delay', 1.0),
            retry_backoff=task_config_data.get('retry_backoff', 2.0),
            timeout=task_config_data.get('timeout', 300.0),
            priority=TaskPriority(task_config_data.get('priority', 'normal')),
            queue_name=task_config_data.get('queue_name', 'default'),
            tags=task_config_data.get('tags', []),
            metadata=task_config_data.get('metadata', {}),
        )

        task = cls(
            task_id=data['task_id'],
            name=data['name'],
            function_name=data['function_name'],
            schedule=schedule,
            args=data.get('args', []),
            kwargs=data.get('kwargs', {}),
            task_config=task_config,
            tenant_id=data.get('tenant_id'),
            description=data.get('description', ''),
            tags=data.get('tags', []),
        )

        # Restore runtime state
        task.last_run = datetime.fromisoformat(data['last_run']) if data.get('last_run') else None
        task.next_run = datetime.fromisoformat(data['next_run']) if data.get('next_run') else None
        task.run_count = data.get('run_count', 0)
        task.failure_count = data.get('failure_count', 0)
        task.created_at = datetime.fromisoformat(data['created_at'])
        task.updated_at = datetime.fromisoformat(data['updated_at'])

        return task


class TaskScheduler:
    """
    Advanced distributed task scheduler with Redis backend.
    
    Features:
    - Cron expression parsing and scheduling
    - Leader election for distributed scheduling
    - Schedule persistence and recovery
    - Timezone-aware scheduling
    - Overlap handling and concurrency control
    - Schedule monitoring and health checks
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        scheduler_id: str = None,
        key_prefix: str = "dotmac_scheduler",
        poll_interval: int = 60,
        leader_timeout: int = 300,
        enable_leader_election: bool = True,
    ):
        self.redis_url = redis_url
        self.scheduler_id = scheduler_id or f"scheduler-{int(time.time())}-{id(self)}"
        self.key_prefix = key_prefix
        self.poll_interval = poll_interval
        self.leader_timeout = leader_timeout
        self.enable_leader_election = enable_leader_election
        
        # Redis connection
        self._redis: Optional[AsyncRedis] = None
        self._task_queue: Optional[RedisTaskQueue] = None
        
        # Scheduler state
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._is_running = False
        self._is_leader = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._leader_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            'schedules_processed': 0,
            'tasks_scheduled': 0,
            'scheduling_errors': 0,
            'leader_elections': 0,
        }

    async def initialize(self):
        """Initialize scheduler and Redis connections."""
        try:
            # Initialize Redis connection
            self._redis = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                max_connections=20
            )
            
            # Test connection
            await self._redis.ping()
            
            # Initialize task queue
            self._task_queue = RedisTaskQueue(self.redis_url)
            await self._task_queue.initialize()
            
            # Load persisted schedules
            await self._load_schedules()
            
            logger.info(f"Task scheduler initialized", extra={
                'scheduler_id': self.scheduler_id,
                'loaded_schedules': len(self._scheduled_tasks),
                'leader_election_enabled': self.enable_leader_election
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize task scheduler: {e}")
            raise TaskError(f"Scheduler initialization failed: {e}")

    async def start(self):
        """Start the scheduler."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start leader election if enabled
        if self.enable_leader_election:
            self._leader_task = asyncio.create_task(self._leader_election_loop())
        else:
            self._is_leader = True
        
        # Start scheduler loop
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info(f"Task scheduler started", extra={'scheduler_id': self.scheduler_id})

    async def stop(self):
        """Stop the scheduler."""
        logger.info(f"Stopping task scheduler", extra={'scheduler_id': self.scheduler_id})
        
        self._is_running = False
        
        # Cancel tasks
        if self._scheduler_task:
            self._scheduler_task.cancel()
        
        if self._leader_task:
            self._leader_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self._scheduler_task, self._leader_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Release leadership
        if self._is_leader:
            await self._release_leadership()
        
        # Close connections
        if self._task_queue:
            await self._task_queue.close()
        
        if self._redis:
            await self._redis.close()
        
        logger.info("Task scheduler stopped")

    async def add_schedule(
        self,
        name: str,
        cron_expression: str,
        function_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        task_config: TaskConfig = None,
        tenant_id: Optional[str] = None,
        description: str = "",
        timezone: str = "UTC",
        enabled: bool = True,
        tags: List[str] = None,
        **schedule_options
    ) -> str:
        """
        Add a new scheduled task.
        
        Args:
            name: Unique schedule name
            cron_expression: Cron schedule expression
            function_name: Task function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            task_config: Task execution configuration
            tenant_id: Optional tenant isolation
            description: Schedule description
            timezone: Schedule timezone
            enabled: Whether schedule is enabled
            tags: Schedule tags for filtering
            **schedule_options: Additional schedule options
            
        Returns:
            str: Schedule ID
        """
        try:
            # Create schedule configuration
            schedule = CronSchedule(
                expression=cron_expression,
                timezone=timezone,
                enabled=enabled,
                max_instances=schedule_options.get('max_instances', 1),
                overlap_policy=schedule_options.get('overlap_policy', 'skip'),
                jitter=schedule_options.get('jitter', 0),
                metadata=schedule_options.get('metadata', {}),
            )
            
            # Create scheduled task
            task_id = f"schedule-{name}-{int(time.time())}"
            scheduled_task = ScheduledTask(
                task_id=task_id,
                name=name,
                function_name=function_name,
                schedule=schedule,
                args=args or [],
                kwargs=kwargs or {},
                task_config=task_config or TaskConfig(),
                tenant_id=tenant_id,
                description=description,
                tags=tags or [],
            )
            
            # Calculate next run time
            scheduled_task.next_run = schedule.next_run_time()
            
            # Store schedule
            self._scheduled_tasks[task_id] = scheduled_task
            await self._persist_schedule(scheduled_task)
            
            logger.info(f"Schedule added", extra={
                'schedule_name': name,
                'task_id': task_id,
                'cron_expression': cron_expression,
                'next_run': scheduled_task.next_run.isoformat() if scheduled_task.next_run else None
            })
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to add schedule '{name}': {e}")
            raise TaskError(f"Add schedule failed: {e}")

    async def remove_schedule(self, name: str) -> bool:
        """
        Remove a scheduled task by name.
        
        Args:
            name: Schedule name to remove
            
        Returns:
            bool: Success status
        """
        try:
            # Find schedule by name
            task_id = None
            for tid, scheduled_task in self._scheduled_tasks.items():
                if scheduled_task.name == name:
                    task_id = tid
                    break
            
            if not task_id:
                logger.warning(f"Schedule not found: {name}")
                return False
            
            # Remove from memory
            del self._scheduled_tasks[task_id]
            
            # Remove from Redis
            schedule_key = f"{self.key_prefix}:schedules:{task_id}"
            await self._redis.delete(schedule_key)
            
            logger.info(f"Schedule removed", extra={
                'schedule_name': name,
                'task_id': task_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove schedule '{name}': {e}")
            return False

    async def get_schedule(self, name: str) -> Optional[ScheduledTask]:
        """Get schedule by name."""
        for scheduled_task in self._scheduled_tasks.values():
            if scheduled_task.name == name:
                return scheduled_task
        return None

    async def list_schedules(self, tenant_id: Optional[str] = None) -> List[ScheduledTask]:
        """List all schedules, optionally filtered by tenant."""
        schedules = list(self._scheduled_tasks.values())
        
        if tenant_id:
            schedules = [s for s in schedules if s.tenant_id == tenant_id]
        
        return schedules

    async def enable_schedule(self, name: str) -> bool:
        """Enable a schedule."""
        return await self._toggle_schedule(name, True)

    async def disable_schedule(self, name: str) -> bool:
        """Disable a schedule."""
        return await self._toggle_schedule(name, False)

    async def _toggle_schedule(self, name: str, enabled: bool) -> bool:
        """Toggle schedule enabled state."""
        try:
            scheduled_task = await self.get_schedule(name)
            if not scheduled_task:
                return False
            
            scheduled_task.schedule.enabled = enabled
            scheduled_task.updated_at = datetime.now(timezone.utc)
            
            # Recalculate next run if enabling
            if enabled:
                scheduled_task.next_run = scheduled_task.schedule.next_run_time()
            
            await self._persist_schedule(scheduled_task)
            
            logger.info(f"Schedule {'enabled' if enabled else 'disabled'}", extra={
                'schedule_name': name,
                'next_run': scheduled_task.next_run.isoformat() if scheduled_task.next_run else None
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to toggle schedule '{name}': {e}")
            return False

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        try:
            while self._is_running:
                if self._is_leader:
                    await self._process_schedules()
                
                # Update scheduler heartbeat
                await self._update_heartbeat()
                
                # Wait for next poll
                await asyncio.sleep(self.poll_interval)
                
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")

    async def _process_schedules(self):
        """Process all schedules and enqueue due tasks."""
        now = datetime.now(timezone.utc)
        processed = 0
        scheduled = 0
        errors = 0
        
        try:
            for task_id, scheduled_task in self._scheduled_tasks.items():
                try:
                    if await self._should_schedule_task(scheduled_task, now):
                        success = await self._schedule_task(scheduled_task, now)
                        if success:
                            scheduled += 1
                        else:
                            errors += 1
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing schedule {scheduled_task.name}: {e}")
                    errors += 1
            
            # Update statistics
            self._stats['schedules_processed'] += processed
            self._stats['tasks_scheduled'] += scheduled
            self._stats['scheduling_errors'] += errors
            
            if processed > 0:
                logger.debug(f"Processed {processed} schedules, scheduled {scheduled} tasks, {errors} errors")
            
        except Exception as e:
            logger.error(f"Error in schedule processing: {e}")

    async def _should_schedule_task(self, scheduled_task: ScheduledTask, now: datetime) -> bool:
        """Determine if a task should be scheduled."""
        if not scheduled_task.schedule.enabled:
            return False
        
        # Check if it's time to run
        if scheduled_task.next_run and now >= scheduled_task.next_run:
            return True
        
        return False

    async def _schedule_task(self, scheduled_task: ScheduledTask, now: datetime) -> bool:
        """Schedule a task for execution."""
        try:
            # Check overlap policy
            if scheduled_task.schedule.max_instances > 0:
                running_count = await self._get_running_instance_count(scheduled_task)
                
                if running_count >= scheduled_task.schedule.max_instances:
                    if scheduled_task.schedule.overlap_policy == 'skip':
                        logger.debug(f"Skipping {scheduled_task.name} due to max instances")
                        # Update next run time
                        scheduled_task.next_run = scheduled_task.schedule.next_run_time(now)
                        await self._persist_schedule(scheduled_task)
                        return True
                    elif scheduled_task.schedule.overlap_policy == 'replace':
                        # Cancel existing instances (implementation depends on task tracking)
                        pass
            
            # Create task instance
            task = Task(
                name=f"{scheduled_task.name}-{now.strftime('%Y%m%d-%H%M%S')}",
                function_name=scheduled_task.function_name,
                args=scheduled_task.args,
                kwargs=scheduled_task.kwargs,
                config=scheduled_task.task_config,
                tenant_id=scheduled_task.tenant_id,
                correlation_id=f"schedule-{scheduled_task.task_id}-{int(now.timestamp())}",
                scheduled_at=now,
            )
            
            # Add schedule metadata
            task.config.metadata.update({
                'schedule_name': scheduled_task.name,
                'schedule_id': scheduled_task.task_id,
                'scheduled_run': True,
                'cron_expression': scheduled_task.schedule.expression,
            })
            
            # Enqueue task
            await self._task_queue.enqueue(task)
            
            # Update schedule state
            scheduled_task.last_run = now
            scheduled_task.next_run = scheduled_task.schedule.next_run_time(now)
            scheduled_task.run_count += 1
            scheduled_task.updated_at = now
            
            await self._persist_schedule(scheduled_task)
            
            logger.info(f"Scheduled task", extra={
                'schedule_name': scheduled_task.name,
                'task_id': task.task_id,
                'next_run': scheduled_task.next_run.isoformat() if scheduled_task.next_run else None
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule task {scheduled_task.name}: {e}")
            scheduled_task.failure_count += 1
            await self._persist_schedule(scheduled_task)
            return False

    async def _get_running_instance_count(self, scheduled_task: ScheduledTask) -> int:
        """Get count of currently running instances of a scheduled task."""
        # This would require task tracking in Redis
        # For now, return 0 (no overlap control)
        return 0

    async def _leader_election_loop(self):
        """Leader election loop using Redis."""
        logger.info("Leader election loop started")
        
        try:
            while self._is_running:
                try:
                    # Try to acquire leadership
                    if not self._is_leader:
                        success = await self._acquire_leadership()
                        if success:
                            self._is_leader = True
                            self._stats['leader_elections'] += 1
                            logger.info(f"Acquired leadership", extra={
                                'scheduler_id': self.scheduler_id
                            })
                    
                    # Maintain leadership
                    if self._is_leader:
                        await self._maintain_leadership()
                    
                except Exception as e:
                    logger.error(f"Leader election error: {e}")
                    self._is_leader = False
                
                await asyncio.sleep(30)  # Check leadership every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("Leader election loop cancelled")

    async def _acquire_leadership(self) -> bool:
        """Try to acquire scheduler leadership."""
        leader_key = f"{self.key_prefix}:leader"
        
        try:
            # Try to set leader key with expiration
            result = await self._redis.set(
                leader_key,
                self.scheduler_id,
                ex=self.leader_timeout,
                nx=True  # Only set if key doesn't exist
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to acquire leadership: {e}")
            return False

    async def _maintain_leadership(self) -> bool:
        """Maintain leadership by updating TTL."""
        leader_key = f"{self.key_prefix}:leader"
        
        try:
            # Check if we're still the leader
            current_leader = await self._redis.get(leader_key)
            
            if current_leader != self.scheduler_id:
                logger.warning(f"Lost leadership to {current_leader}")
                self._is_leader = False
                return False
            
            # Extend leadership
            await self._redis.expire(leader_key, self.leader_timeout)
            return True
            
        except Exception as e:
            logger.error(f"Failed to maintain leadership: {e}")
            self._is_leader = False
            return False

    async def _release_leadership(self):
        """Release leadership."""
        leader_key = f"{self.key_prefix}:leader"
        
        try:
            # Only release if we're the current leader
            current_leader = await self._redis.get(leader_key)
            if current_leader == self.scheduler_id:
                await self._redis.delete(leader_key)
                logger.info("Released leadership")
            
        except Exception as e:
            logger.error(f"Failed to release leadership: {e}")

    async def _persist_schedule(self, scheduled_task: ScheduledTask):
        """Persist schedule to Redis."""
        schedule_key = f"{self.key_prefix}:schedules:{scheduled_task.task_id}"
        schedule_data = json.dumps(scheduled_task.to_dict())
        
        await self._redis.set(schedule_key, schedule_data)

    async def _load_schedules(self):
        """Load persisted schedules from Redis."""
        try:
            pattern = f"{self.key_prefix}:schedules:*"
            keys = await self._redis.keys(pattern)
            
            loaded_count = 0
            for key in keys:
                try:
                    schedule_data = await self._redis.get(key)
                    if schedule_data:
                        data = json.loads(schedule_data)
                        scheduled_task = ScheduledTask.from_dict(data)
                        
                        # Recalculate next run time
                        if scheduled_task.schedule.enabled:
                            scheduled_task.next_run = scheduled_task.schedule.next_run_time()
                        
                        self._scheduled_tasks[scheduled_task.task_id] = scheduled_task
                        loaded_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to load schedule from {key}: {e}")
            
            logger.info(f"Loaded {loaded_count} persisted schedules")
            
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")

    async def _update_heartbeat(self):
        """Update scheduler heartbeat."""
        heartbeat_key = f"{self.key_prefix}:heartbeat:{self.scheduler_id}"
        
        heartbeat_data = {
            'scheduler_id': self.scheduler_id,
            'is_leader': self._is_leader,
            'schedule_count': len(self._scheduled_tasks),
            'last_heartbeat': datetime.now(timezone.utc).isoformat(),
            'stats': self._stats,
        }
        
        await self._redis.set(
            heartbeat_key,
            json.dumps(heartbeat_data),
            ex=300  # 5 minute TTL
        )

    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get comprehensive scheduler statistics."""
        return {
            'scheduler_id': self.scheduler_id,
            'is_running': self._is_running,
            'is_leader': self._is_leader,
            'schedule_count': len(self._scheduled_tasks),
            'enabled_schedules': len([s for s in self._scheduled_tasks.values() if s.schedule.enabled]),
            'stats': self._stats.copy(),
            'next_runs': [
                {
                    'name': s.name,
                    'next_run': s.next_run.isoformat() if s.next_run else None,
                    'enabled': s.schedule.enabled
                }
                for s in sorted(self._scheduled_tasks.values(), key=lambda x: x.next_run or datetime.max.replace(tzinfo=timezone.utc))[:10]
            ]
        }

    async def get_all_scheduler_heartbeats(self) -> List[Dict[str, Any]]:
        """Get heartbeats from all active schedulers."""
        try:
            pattern = f"{self.key_prefix}:heartbeat:*"
            keys = await self._redis.keys(pattern)
            
            heartbeats = []
            for key in keys:
                try:
                    heartbeat_data = await self._redis.get(key)
                    if heartbeat_data:
                        heartbeats.append(json.loads(heartbeat_data))
                except Exception as e:
                    logger.warning(f"Failed to parse heartbeat from {key}: {e}")
            
            return heartbeats
            
        except Exception as e:
            logger.error(f"Failed to get scheduler heartbeats: {e}")
            return []