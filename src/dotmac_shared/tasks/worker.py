"""
Distributed Task Worker Management System

Provides comprehensive worker management with:
- Multi-worker coordination and load balancing
- Worker health monitoring and auto-recovery
- Dynamic scaling based on queue depth
- Worker specialization and queue routing
- Graceful shutdown and resource cleanup
"""

import asyncio
import json
import signal
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum

from redis.asyncio import Redis as AsyncRedis

from .engine import TaskEngine, Task, TaskResult, TaskStatus, TaskError
from .queue import RedisTaskQueue
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class WorkerStatus(str, Enum):
    """Worker status enumeration."""
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerConfig:
    """Worker configuration parameters."""
    concurrency: int = 10
    max_tasks: int = 1000  # Maximum tasks before restart
    max_memory_mb: int = 512  # Maximum memory usage before restart
    heartbeat_interval: int = 30  # Seconds
    queue_poll_timeout: int = 30  # Seconds
    specialization: Set[str] = field(default_factory=set)  # Task types this worker handles
    queues: List[str] = field(default_factory=lambda: ["default"])  # Queues to process
    tenant_isolation: bool = True  # Enable tenant-specific processing
    rate_limit_per_minute: int = 0  # Rate limit (0 = no limit)
    
    def __post_init__(self):
        """Validate configuration."""
        if self.concurrency <= 0:
            raise ValueError("Concurrency must be positive")
        if self.max_tasks <= 0:
            raise ValueError("Max tasks must be positive")


@dataclass
class WorkerStats:
    """Worker runtime statistics."""
    worker_id: str
    status: WorkerStatus
    started_at: datetime
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    current_tasks: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_task_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'worker_id': self.worker_id,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'total_execution_time': self.total_execution_time,
            'current_tasks': self.current_tasks,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'last_task_at': self.last_task_at.isoformat() if self.last_task_at else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'uptime_seconds': (datetime.now(timezone.utc) - self.started_at).total_seconds(),
            'tasks_per_minute': self._calculate_tasks_per_minute(),
            'average_execution_time': self.total_execution_time / max(self.tasks_completed, 1),
            'success_rate': self.tasks_completed / max(self.tasks_completed + self.tasks_failed, 1),
        }

    def _calculate_tasks_per_minute(self) -> float:
        """Calculate tasks per minute rate."""
        uptime_minutes = (datetime.now(timezone.utc) - self.started_at).total_seconds() / 60
        if uptime_minutes > 0:
            return (self.tasks_completed + self.tasks_failed) / uptime_minutes
        return 0.0


class TaskWorker:
    """
    Individual task worker with comprehensive monitoring and management.
    
    Features:
    - Concurrent task processing with configurable limits
    - Health monitoring and resource tracking
    - Graceful shutdown with task completion
    - Specialization for specific task types
    - Rate limiting and backpressure handling
    - Automatic restart on resource limits
    """

    def __init__(
        self,
        config: WorkerConfig,
        redis_url: str = "redis://localhost:6379",
        worker_id: Optional[str] = None,
    ):
        self.config = config
        self.redis_url = redis_url
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        
        # Core components
        self._task_engine: Optional[TaskEngine] = None
        self._task_queue: Optional[RedisTaskQueue] = None
        self._redis: Optional[AsyncRedis] = None
        
        # Worker state
        self._status = WorkerStatus.STOPPED
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        self._running_tasks: Set[asyncio.Task] = set()
        
        # Statistics and monitoring
        self._stats = WorkerStats(
            worker_id=self.worker_id,
            status=self._status,
            started_at=datetime.now(timezone.utc)
        )
        
        # Rate limiting
        self._task_timestamps: List[datetime] = []
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._worker_loop_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize worker components."""
        try:
            self._status = WorkerStatus.STARTING
            self._stats.status = self._status
            
            # Initialize Redis connection
            self._redis = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                max_connections=self.config.concurrency + 10
            )
            
            await self._redis.ping()
            
            # Initialize task engine
            self._task_engine = TaskEngine(
                redis_url=self.redis_url,
                worker_name=self.worker_id,
                concurrency=self.config.concurrency
            )
            await self._task_engine.initialize()
            
            # Initialize task queue
            self._task_queue = RedisTaskQueue(self.redis_url)
            await self._task_queue.initialize()
            
            logger.info(f"Worker initialized", extra={
                'worker_id': self.worker_id,
                'concurrency': self.config.concurrency,
                'queues': self.config.queues,
                'specialization': list(self.config.specialization)
            })
            
        except Exception as e:
            self._status = WorkerStatus.ERROR
            logger.error(f"Failed to initialize worker {self.worker_id}: {e}")
            raise TaskError(f"Worker initialization failed: {e}")

    async def start(self):
        """Start the worker."""
        if self._is_running:
            return
        
        self._is_running = True
        self._status = WorkerStatus.IDLE
        self._stats.status = self._status
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._worker_loop_task = asyncio.create_task(self._worker_loop())
        
        # Register worker
        await self._register_worker()
        
        logger.info(f"Worker started", extra={'worker_id': self.worker_id})

    async def stop(self, graceful: bool = True, timeout: int = 300):
        """
        Stop the worker gracefully or forcefully.
        
        Args:
            graceful: Whether to wait for running tasks to complete
            timeout: Maximum wait time for graceful shutdown
        """
        logger.info(f"Stopping worker", extra={
            'worker_id': self.worker_id,
            'graceful': graceful,
            'running_tasks': len(self._running_tasks)
        })
        
        self._is_running = False
        self._status = WorkerStatus.STOPPING
        self._shutdown_event.set()
        
        # Cancel background tasks
        background_tasks = [
            t for t in [self._heartbeat_task, self._monitoring_task, self._worker_loop_task] 
            if t and not t.done()
        ]
        
        for task in background_tasks:
            task.cancel()
        
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        
        # Handle running tasks
        if self._running_tasks:
            if graceful:
                logger.info(f"Waiting for {len(self._running_tasks)} tasks to complete")
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._running_tasks, return_exceptions=True),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Graceful shutdown timeout, cancelling tasks")
                    for task in self._running_tasks:
                        task.cancel()
            else:
                # Force cancel all tasks
                for task in self._running_tasks:
                    task.cancel()
                
                if self._running_tasks:
                    await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        # Unregister worker
        await self._unregister_worker()
        
        # Close connections
        if self._task_engine:
            await self._task_engine.shutdown()
        
        if self._task_queue:
            await self._task_queue.close()
        
        if self._redis:
            await self._redis.close()
        
        self._status = WorkerStatus.STOPPED
        logger.info(f"Worker stopped", extra={'worker_id': self.worker_id})

    def register_task_function(self, name: str, func: Callable):
        """Register a task function for execution."""
        if self._task_engine:
            self._task_engine.register_task_function(name, func)

    async def _worker_loop(self):
        """Main worker processing loop."""
        logger.info(f"Worker loop started", extra={'worker_id': self.worker_id})
        
        try:
            while self._is_running:
                try:
                    # Check if we should process more tasks
                    if not await self._should_process_tasks():
                        await asyncio.sleep(1)
                        continue
                    
                    # Get next task from appropriate queue
                    task = await self._get_next_task()
                    
                    if task:
                        # Process task in background
                        task_coroutine = asyncio.create_task(
                            self._process_task_wrapper(task)
                        )
                        self._running_tasks.add(task_coroutine)
                        
                        # Clean up completed tasks
                        self._cleanup_completed_tasks()
                    
                except Exception as e:
                    logger.error(f"Error in worker loop: {e}")
                    await asyncio.sleep(5)  # Back off on errors
                
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled")
        except Exception as e:
            logger.error(f"Worker loop failed: {e}")
            self._status = WorkerStatus.ERROR

    async def _should_process_tasks(self) -> bool:
        """Check if worker should process more tasks."""
        # Check concurrency limit
        if len(self._running_tasks) >= self.config.concurrency:
            return False
        
        # Check rate limiting
        if self.config.rate_limit_per_minute > 0:
            if not self._check_rate_limit():
                return False
        
        # Check resource limits
        if await self._should_restart_due_to_limits():
            logger.info(f"Worker needs restart due to resource limits")
            # Trigger graceful restart (implementation depends on orchestrator)
            return False
        
        return True

    def _check_rate_limit(self) -> bool:
        """Check if worker is within rate limits."""
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old timestamps
        self._task_timestamps = [t for t in self._task_timestamps if t > minute_ago]
        
        # Check if we can process another task
        return len(self._task_timestamps) < self.config.rate_limit_per_minute

    async def _get_next_task(self) -> Optional[Task]:
        """Get the next task from appropriate queue."""
        # Try each configured queue in order
        for queue_name in self.config.queues:
            try:
                # Apply tenant isolation if configured
                tenant_id = None  # Would be determined based on worker assignment
                
                task = await self._task_queue.dequeue(
                    queue_name=queue_name,
                    timeout=self.config.queue_poll_timeout,
                    tenant_id=tenant_id,
                    worker_id=self.worker_id
                )
                
                if task:
                    # Check if worker can handle this task type
                    if self.config.specialization and task.function_name not in self.config.specialization:
                        # Requeue task for appropriate worker
                        await self._task_queue.requeue_task(task, delay_seconds=1, increment_retry=False)
                        continue
                    
                    return task
                
            except Exception as e:
                logger.error(f"Error dequeuing from {queue_name}: {e}")
        
        return None

    async def _process_task_wrapper(self, task: Task):
        """Wrapper for task processing with statistics tracking."""
        start_time = time.time()
        
        try:
            self._status = WorkerStatus.BUSY
            self._stats.current_tasks += 1
            
            # Update rate limiting
            if self.config.rate_limit_per_minute > 0:
                self._task_timestamps.append(datetime.now(timezone.utc))
            
            # Execute task
            result = await self._task_engine.execute_task(task)
            
            # Update statistics
            execution_time = time.time() - start_time
            self._stats.total_execution_time += execution_time
            self._stats.last_task_at = datetime.now(timezone.utc)
            
            if result.status == TaskStatus.COMPLETED:
                self._stats.tasks_completed += 1
                logger.debug(f"Task completed", extra={
                    'worker_id': self.worker_id,
                    'task_id': task.task_id,
                    'execution_time': execution_time
                })
            else:
                self._stats.tasks_failed += 1
                logger.warning(f"Task failed", extra={
                    'worker_id': self.worker_id,
                    'task_id': task.task_id,
                    'status': result.status.value,
                    'error': result.error
                })
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._stats.tasks_failed += 1
            self._stats.total_execution_time += execution_time
            
            logger.error(f"Task processing error", extra={
                'worker_id': self.worker_id,
                'task_id': task.task_id,
                'error': str(e)
            })
            
        finally:
            self._stats.current_tasks -= 1
            if self._stats.current_tasks == 0:
                self._status = WorkerStatus.IDLE

    def _cleanup_completed_tasks(self):
        """Remove completed tasks from tracking."""
        completed = {task for task in self._running_tasks if task.done()}
        self._running_tasks -= completed

    async def _heartbeat_loop(self):
        """Worker heartbeat loop."""
        try:
            while self._is_running:
                await self._send_heartbeat()
                await asyncio.sleep(self.config.heartbeat_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

    async def _monitoring_loop(self):
        """Worker resource monitoring loop."""
        try:
            while self._is_running:
                await self._update_resource_stats()
                await asyncio.sleep(30)  # Update every 30 seconds
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")

    async def _send_heartbeat(self):
        """Send worker heartbeat to Redis."""
        try:
            self._stats.last_heartbeat = datetime.now(timezone.utc)
            self._stats.status = self._status
            
            heartbeat_key = f"worker:heartbeat:{self.worker_id}"
            heartbeat_data = self._stats.to_dict()
            
            await self._redis.set(
                heartbeat_key,
                json.dumps(heartbeat_data),
                ex=self.config.heartbeat_interval * 3  # TTL = 3x heartbeat interval
            )
            
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")

    async def _update_resource_stats(self):
        """Update worker resource usage statistics."""
        try:
            import psutil
            
            # Get current process
            process = psutil.Process()
            
            # Update memory usage
            memory_info = process.memory_info()
            self._stats.memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # Update CPU usage
            self._stats.cpu_usage_percent = process.cpu_percent()
            
        except ImportError:
            # psutil not available, skip resource monitoring
            pass
        except Exception as e:
            logger.warning(f"Failed to update resource stats: {e}")

    async def _should_restart_due_to_limits(self) -> bool:
        """Check if worker should restart due to resource limits."""
        # Check task count limit
        total_tasks = self._stats.tasks_completed + self._stats.tasks_failed
        if total_tasks >= self.config.max_tasks:
            return True
        
        # Check memory limit
        if self.config.max_memory_mb > 0 and self._stats.memory_usage_mb > self.config.max_memory_mb:
            return True
        
        return False

    async def _register_worker(self):
        """Register worker in the worker registry."""
        try:
            registry_key = f"worker:registry:{self.worker_id}"
            worker_info = {
                'worker_id': self.worker_id,
                'config': {
                    'concurrency': self.config.concurrency,
                    'queues': self.config.queues,
                    'specialization': list(self.config.specialization),
                    'tenant_isolation': self.config.tenant_isolation,
                },
                'registered_at': datetime.now(timezone.utc).isoformat(),
            }
            
            await self._redis.set(registry_key, json.dumps(worker_info), ex=300)
            
        except Exception as e:
            logger.error(f"Failed to register worker: {e}")

    async def _unregister_worker(self):
        """Unregister worker from the worker registry."""
        try:
            registry_key = f"worker:registry:{self.worker_id}"
            await self._redis.delete(registry_key)
            
            # Also remove heartbeat
            heartbeat_key = f"worker:heartbeat:{self.worker_id}"
            await self._redis.delete(heartbeat_key)
            
        except Exception as e:
            logger.error(f"Failed to unregister worker: {e}")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.stop(graceful=True))
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except ValueError:
            # Signal handling not available (e.g., running in thread)
            pass

    def get_stats(self) -> Dict[str, Any]:
        """Get current worker statistics."""
        return self._stats.to_dict()


class WorkerManager:
    """
    Distributed worker manager for orchestrating multiple workers.
    
    Features:
    - Dynamic worker scaling based on queue depth
    - Worker health monitoring and recovery
    - Load balancing and queue distribution
    - Worker specialization management
    - Centralized configuration and deployment
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        manager_id: Optional[str] = None,
        key_prefix: str = "dotmac_workers",
    ):
        self.redis_url = redis_url
        self.manager_id = manager_id or f"manager-{uuid.uuid4().hex[:8]}"
        self.key_prefix = key_prefix
        
        # Redis connection
        self._redis: Optional[AsyncRedis] = None
        self._task_queue: Optional[RedisTaskQueue] = None
        
        # Manager state
        self._is_running = False
        self._workers: Dict[str, TaskWorker] = {}
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._scaling_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize worker manager."""
        try:
            # Initialize Redis connection
            self._redis = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                max_connections=50
            )
            
            await self._redis.ping()
            
            # Initialize task queue for monitoring
            self._task_queue = RedisTaskQueue(self.redis_url)
            await self._task_queue.initialize()
            
            logger.info(f"Worker manager initialized", extra={'manager_id': self.manager_id})
            
        except Exception as e:
            logger.error(f"Failed to initialize worker manager: {e}")
            raise TaskError(f"Worker manager initialization failed: {e}")

    async def start(self):
        """Start the worker manager."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start background monitoring and scaling
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._scaling_task = asyncio.create_task(self._scaling_loop())
        
        logger.info(f"Worker manager started", extra={'manager_id': self.manager_id})

    async def stop(self):
        """Stop the worker manager and all workers."""
        logger.info(f"Stopping worker manager", extra={'manager_id': self.manager_id})
        
        self._is_running = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._scaling_task:
            self._scaling_task.cancel()
        
        # Stop all workers
        stop_tasks = []
        for worker in self._workers.values():
            stop_tasks.append(worker.stop(graceful=True, timeout=60))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Close connections
        if self._task_queue:
            await self._task_queue.close()
        if self._redis:
            await self._redis.close()
        
        logger.info("Worker manager stopped")

    async def add_worker(self, config: WorkerConfig) -> str:
        """Add a new worker with the specified configuration."""
        try:
            worker = TaskWorker(config, self.redis_url)
            await worker.initialize()
            
            self._workers[worker.worker_id] = worker
            await worker.start()
            
            logger.info(f"Added worker", extra={
                'manager_id': self.manager_id,
                'worker_id': worker.worker_id,
                'concurrency': config.concurrency
            })
            
            return worker.worker_id
            
        except Exception as e:
            logger.error(f"Failed to add worker: {e}")
            raise TaskError(f"Add worker failed: {e}")

    async def remove_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """Remove a worker."""
        try:
            if worker_id not in self._workers:
                return False
            
            worker = self._workers[worker_id]
            await worker.stop(graceful=graceful)
            del self._workers[worker_id]
            
            logger.info(f"Removed worker", extra={
                'manager_id': self.manager_id,
                'worker_id': worker_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove worker {worker_id}: {e}")
            return False

    async def scale_workers(self, target_count: int, queue_name: str = "default"):
        """Scale workers for a specific queue."""
        current_workers = [
            w for w in self._workers.values()
            if queue_name in w.config.queues
        ]
        current_count = len(current_workers)
        
        if target_count > current_count:
            # Scale up
            for _ in range(target_count - current_count):
                config = WorkerConfig(queues=[queue_name])
                await self.add_worker(config)
                
        elif target_count < current_count:
            # Scale down
            workers_to_remove = current_workers[:current_count - target_count]
            for worker in workers_to_remove:
                await self.remove_worker(worker.worker_id, graceful=True)

    async def _monitoring_loop(self):
        """Monitor worker health and recover failed workers."""
        try:
            while self._is_running:
                await self._check_worker_health()
                await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")

    async def _scaling_loop(self):
        """Auto-scaling loop based on queue depth and worker utilization."""
        try:
            while self._is_running:
                await self._auto_scale_workers()
                await asyncio.sleep(300)  # Scale check every 5 minutes
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Scaling loop error: {e}")

    async def _check_worker_health(self):
        """Check health of all workers and recover failed ones."""
        failed_workers = []
        
        for worker_id, worker in self._workers.items():
            try:
                stats = worker.get_stats()
                
                # Check if worker is responsive
                if stats['status'] == WorkerStatus.ERROR.value:
                    logger.warning(f"Worker in error state", extra={'worker_id': worker_id})
                    failed_workers.append(worker_id)
                
                # Check heartbeat age
                if stats['last_heartbeat']:
                    last_heartbeat = datetime.fromisoformat(stats['last_heartbeat'])
                    age = datetime.now(timezone.utc) - last_heartbeat
                    
                    if age > timedelta(minutes=5):  # No heartbeat for 5 minutes
                        logger.warning(f"Worker heartbeat stale", extra={
                            'worker_id': worker_id,
                            'heartbeat_age_seconds': age.total_seconds()
                        })
                        failed_workers.append(worker_id)
                
            except Exception as e:
                logger.error(f"Failed to check worker {worker_id} health: {e}")
                failed_workers.append(worker_id)
        
        # Recover failed workers
        for worker_id in failed_workers:
            await self._recover_worker(worker_id)

    async def _recover_worker(self, worker_id: str):
        """Recover a failed worker."""
        try:
            if worker_id in self._workers:
                worker = self._workers[worker_id]
                config = worker.config
                
                # Stop failed worker
                await worker.stop(graceful=False, timeout=30)
                del self._workers[worker_id]
                
                # Start new worker with same config
                await self.add_worker(config)
                
                logger.info(f"Recovered worker", extra={'worker_id': worker_id})
                
        except Exception as e:
            logger.error(f"Failed to recover worker {worker_id}: {e}")

    async def _auto_scale_workers(self):
        """Automatically scale workers based on queue depth and utilization."""
        try:
            # Get queue statistics
            queues_stats = {}
            for queue_name in ["default", "high_priority", "background"]:  # Common queues
                try:
                    stats = await self._task_queue.get_queue_stats(queue_name)
                    queues_stats[queue_name] = stats
                except Exception as e:
                    logger.warning(f"Failed to get stats for queue {queue_name}: {e}")
            
            # Analyze scaling needs for each queue
            for queue_name, stats in queues_stats.items():
                await self._scale_queue_workers(queue_name, stats)
                
        except Exception as e:
            logger.error(f"Auto-scaling error: {e}")

    async def _scale_queue_workers(self, queue_name: str, queue_stats: Dict[str, Any]):
        """Scale workers for a specific queue based on its statistics."""
        current_size = queue_stats.get('current_size', 0)
        
        # Get current workers for this queue
        queue_workers = [
            w for w in self._workers.values()
            if queue_name in w.config.queues
        ]
        
        current_worker_count = len(queue_workers)
        
        # Simple scaling logic based on queue depth
        if current_size > 50 and current_worker_count < 10:
            # Scale up if queue is large and we have capacity
            await self.add_worker(WorkerConfig(queues=[queue_name], concurrency=5))
            logger.info(f"Scaled up {queue_name} queue workers")
            
        elif current_size == 0 and current_worker_count > 1:
            # Scale down if queue is empty and we have multiple workers
            if queue_workers:
                await self.remove_worker(queue_workers[-1].worker_id)
                logger.info(f"Scaled down {queue_name} queue workers")

    async def get_manager_stats(self) -> Dict[str, Any]:
        """Get comprehensive manager statistics."""
        worker_stats = {}
        total_workers = len(self._workers)
        active_workers = 0
        total_tasks_completed = 0
        total_tasks_failed = 0
        
        for worker_id, worker in self._workers.items():
            try:
                stats = worker.get_stats()
                worker_stats[worker_id] = stats
                
                if stats['status'] in ['idle', 'busy']:
                    active_workers += 1
                
                total_tasks_completed += stats['tasks_completed']
                total_tasks_failed += stats['tasks_failed']
                
            except Exception as e:
                logger.warning(f"Failed to get stats for worker {worker_id}: {e}")
        
        return {
            'manager_id': self.manager_id,
            'is_running': self._is_running,
            'total_workers': total_workers,
            'active_workers': active_workers,
            'total_tasks_completed': total_tasks_completed,
            'total_tasks_failed': total_tasks_failed,
            'success_rate': total_tasks_completed / max(total_tasks_completed + total_tasks_failed, 1),
            'worker_stats': worker_stats,
        }

    async def list_all_workers(self) -> List[Dict[str, Any]]:
        """List all workers across all managers."""
        try:
            pattern = "worker:heartbeat:*"
            keys = await self._redis.keys(pattern)
            
            workers = []
            for key in keys:
                try:
                    worker_data = await self._redis.get(key)
                    if worker_data:
                        workers.append(json.loads(worker_data))
                except Exception as e:
                    logger.warning(f"Failed to parse worker data from {key}: {e}")
            
            return workers
            
        except Exception as e:
            logger.error(f"Failed to list workers: {e}")
            return []