"""
Core Task Processing Engine

Provides the foundational task execution system with async patterns,
retry logic, and comprehensive error handling.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field, ConfigDict
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from dotmac_shared.core.logging import get_logger
from dotmac_shared.observability.logging import get_logger as get_observability_logger
from dotmac_shared.core.exceptions import DotMacException

logger = get_logger(__name__)
observability_logger = get_observability_logger(__name__)


class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(str, Enum):
    """Task priority levels for queue ordering."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskError(DotMacException):
    """Base exception for task processing errors."""
    pass


class TaskTimeoutError(TaskError):
    """Task execution timeout error."""
    pass


class TaskRetryError(TaskError):
    """Task retry limit exceeded error."""
    pass


@dataclass
class TaskResult:
    """Task execution result with comprehensive metadata."""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'error_details': self.error_details,
            'execution_time': self.execution_time,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """Create result from dictionary."""
        return cls(
            task_id=data['task_id'],
            status=TaskStatus(data['status']),
            result=data.get('result'),
            error=data.get('error'),
            error_details=data.get('error_details'),
            execution_time=data.get('execution_time'),
            retry_count=data.get('retry_count', 0),
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            metadata=data.get('metadata', {}),
        )


class TaskConfig(BaseModel):
    """Task configuration and execution parameters."""
    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=300.0)
    retry_backoff: float = Field(default=2.0, ge=1.0, le=10.0)
    timeout: Optional[float] = Field(default=300.0, ge=1.0, le=3600.0)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    queue_name: str = Field(default="default")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """
    Comprehensive task definition with execution context.
    
    Supports both sync and async function execution with full
    retry logic, timeout handling, and progress tracking.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    function_name: str = Field(..., min_length=1)
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    config: TaskConfig = Field(default_factory=TaskConfig)
    
    # Execution context
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Dependency tracking
    depends_on: List[str] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list)
    
    # Progress tracking
    progress_callback: Optional[str] = None
    webhook_url: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.correlation_id:
            self.correlation_id = f"{self.name}-{self.task_id[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to dictionary for queue storage."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'function_name': self.function_name,
            'args': self.args,
            'kwargs': self.kwargs,
            'config': {
                'max_retries': self.config.max_retries,
                'retry_delay': self.config.retry_delay,
                'retry_backoff': self.config.retry_backoff,
                'timeout': self.config.timeout,
                'priority': self.config.priority.value,
                'queue_name': self.config.queue_name,
                'tags': self.config.tags,
                'metadata': self.config.metadata,
            },
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'correlation_id': self.correlation_id,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'depends_on': self.depends_on,
            'blocks': self.blocks,
            'progress_callback': self.progress_callback,
            'webhook_url': self.webhook_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Deserialize task from dictionary."""
        config_data = data.get('config', {})
        config = TaskConfig(
            max_retries=config_data.get('max_retries', 3),
            retry_delay=config_data.get('retry_delay', 1.0),
            retry_backoff=config_data.get('retry_backoff', 2.0),
            timeout=config_data.get('timeout', 300.0),
            priority=TaskPriority(config_data.get('priority', 'normal')),
            queue_name=config_data.get('queue_name', 'default'),
            tags=config_data.get('tags', []),
            metadata=config_data.get('metadata', {}),
        )

        return cls(
            task_id=data['task_id'],
            name=data['name'],
            function_name=data['function_name'],
            args=data.get('args', []),
            kwargs=data.get('kwargs', {}),
            config=config,
            tenant_id=data.get('tenant_id'),
            user_id=data.get('user_id'),
            correlation_id=data.get('correlation_id'),
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            depends_on=data.get('depends_on', []),
            blocks=data.get('blocks', []),
            progress_callback=data.get('progress_callback'),
            webhook_url=data.get('webhook_url'),
        )


class TaskEngine:
    """
    Core task processing engine with Redis-based queuing.
    
    Provides comprehensive task execution with:
    - Async/await support for both sync and async functions
    - Automatic retry logic with exponential backoff
    - Timeout handling and cancellation support
    - Progress tracking and webhook notifications
    - Multi-tenant isolation and security
    - Comprehensive observability and metrics
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        worker_name: Optional[str] = None,
        concurrency: int = 10,
        heartbeat_interval: int = 30,
    ):
        self.redis_url = redis_url
        self.worker_name = worker_name or f"worker-{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency
        self.heartbeat_interval = heartbeat_interval
        
        # Connection pools
        self._redis_pool = None
        self._async_redis_pool = None
        
        # Task registry
        self._task_functions: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Worker state
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        
        # Metrics
        self._stats = {
            'tasks_executed': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retried': 0,
            'total_execution_time': 0.0,
        }

    async def initialize(self):
        """Initialize Redis connections and worker state."""
        try:
            # Initialize async Redis connection
            self._async_redis_pool = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                max_connections=20
            )
            
            # Test connection
            await self._async_redis_pool.ping()
            
            logger.info(f"Task engine initialized", extra={
                'worker_name': self.worker_name,
                'concurrency': self.concurrency,
                'redis_connected': True
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize task engine: {e}")
            raise TaskError(f"Task engine initialization failed: {e}")

    async def shutdown(self):
        """Gracefully shutdown the task engine."""
        logger.info(f"Shutting down task engine", extra={'worker_name': self.worker_name})
        
        self._is_running = False
        self._shutdown_event.set()
        
        # Cancel running tasks
        if self._running_tasks:
            logger.info(f"Cancelling {len(self._running_tasks)} running tasks")
            for task_id, task_coroutine in self._running_tasks.items():
                task_coroutine.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        # Close Redis connections
        if self._async_redis_pool:
            await self._async_redis_pool.close()
        
        logger.info("Task engine shutdown complete")

    def register_task_function(self, name: str, func: Callable):
        """Register a task function for execution."""
        self._task_functions[name] = func
        logger.debug(f"Registered task function: {name}")

    async def enqueue_task(self, task: Task) -> str:
        """
        Enqueue a task for processing.
        
        Args:
            task: Task instance to enqueue
            
        Returns:
            str: Task ID for tracking
            
        Raises:
            TaskError: If task enqueueing fails
        """
        try:
            # Validate task
            if task.expires_at and task.expires_at < datetime.now(timezone.utc):
                raise TaskError(f"Task {task.task_id} has already expired")
            
            # Store task data
            task_key = f"task:{task.task_id}"
            task_data = json.dumps(task.to_dict())
            
            await self._async_redis_pool.hset(task_key, mapping={
                'data': task_data,
                'status': TaskStatus.PENDING.value,
                'enqueued_at': datetime.now(timezone.utc).isoformat(),
                'worker': '',
                'retry_count': 0
            })
            
            # Add to priority queue
            priority_score = self._get_priority_score(task.config.priority)
            queue_key = f"queue:{task.config.queue_name}"
            
            await self._async_redis_pool.zadd(queue_key, {task.task_id: priority_score})
            
            # Set expiration if specified
            if task.expires_at:
                ttl = int((task.expires_at - datetime.now(timezone.utc)).total_seconds())
                await self._async_redis_pool.expire(task_key, ttl)
            
            # Update metrics
            await self._update_queue_metrics(task.config.queue_name, 'enqueued')
            
            logger.info(f"Task enqueued successfully", extra={
                'task_id': task.task_id,
                'task_name': task.name,
                'queue': task.config.queue_name,
                'priority': task.config.priority.value,
                'tenant_id': task.tenant_id
            })
            
            return task.task_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.task_id}: {e}")
            raise TaskError(f"Task enqueue failed: {e}")

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task with comprehensive error handling.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult: Execution result with timing and status
        """
        start_time = time.time()
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Update task status
            await self._update_task_status(task.task_id, TaskStatus.RUNNING, self.worker_name)
            
            # Get task function
            if task.function_name not in self._task_functions:
                raise TaskError(f"Task function '{task.function_name}' not registered")
            
            task_func = self._task_functions[task.function_name]
            
            # Execute with timeout
            if task.config.timeout:
                execution_result = await asyncio.wait_for(
                    self._execute_function(task_func, task.args, task.kwargs, task),
                    timeout=task.config.timeout
                )
            else:
                execution_result = await self._execute_function(task_func, task.args, task.kwargs, task)
            
            # Success
            execution_time = time.time() - start_time
            result.status = TaskStatus.COMPLETED
            result.result = execution_result
            result.execution_time = execution_time
            result.completed_at = datetime.now(timezone.utc)
            
            # Update metrics
            self._stats['tasks_completed'] += 1
            self._stats['total_execution_time'] += execution_time
            
            logger.info(f"Task completed successfully", extra={
                'task_id': task.task_id,
                'task_name': task.name,
                'execution_time': execution_time,
                'tenant_id': task.tenant_id
            })
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            result.status = TaskStatus.TIMEOUT
            result.error = f"Task timed out after {task.config.timeout}s"
            result.execution_time = execution_time
            result.completed_at = datetime.now(timezone.utc)
            
            logger.warning(f"Task timed out", extra={
                'task_id': task.task_id,
                'timeout': task.config.timeout,
                'execution_time': execution_time
            })
            
        except Exception as e:
            execution_time = time.time() - start_time
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.error_details = {
                'exception_type': type(e).__name__,
                'traceback': str(e),
                'execution_time': execution_time
            }
            result.execution_time = execution_time
            result.completed_at = datetime.now(timezone.utc)
            
            self._stats['tasks_failed'] += 1
            
            logger.error(f"Task failed with error", extra={
                'task_id': task.task_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'execution_time': execution_time
            })
        
        finally:
            # Update task result in Redis
            await self._store_task_result(result)
            
            # Send webhook notification if configured
            if task.webhook_url:
                await self._send_webhook_notification(task, result)
        
        self._stats['tasks_executed'] += 1
        return result

    async def _execute_function(
        self, 
        func: Callable, 
        args: List[Any], 
        kwargs: Dict[str, Any], 
        task: Task
    ) -> Any:
        """Execute task function with proper async/sync handling."""
        
        # Add task context to kwargs for functions that need it
        if 'task_context' not in kwargs:
            kwargs['task_context'] = {
                'task_id': task.task_id,
                'correlation_id': task.correlation_id,
                'tenant_id': task.tenant_id,
                'user_id': task.user_id,
                'progress_callback': self._create_progress_callback(task)
            }
        
        # Execute function
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _create_progress_callback(self, task: Task) -> Callable[[int, str], None]:
        """Create progress callback function for task."""
        async def progress_callback(percentage: int, message: str = ""):
            await self._update_task_progress(task.task_id, percentage, message)
        
        return progress_callback

    async def _update_task_progress(self, task_id: str, percentage: int, message: str):
        """Update task progress in Redis."""
        try:
            progress_key = f"task:{task_id}:progress"
            await self._async_redis_pool.hset(progress_key, mapping={
                'percentage': percentage,
                'message': message,
                'updated_at': datetime.now(timezone.utc).isoformat()
            })
            await self._async_redis_pool.expire(progress_key, 3600)  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Failed to update task progress: {e}")

    async def _update_task_status(self, task_id: str, status: TaskStatus, worker_name: str):
        """Update task execution status in Redis."""
        task_key = f"task:{task_id}"
        await self._async_redis_pool.hset(task_key, mapping={
            'status': status.value,
            'worker': worker_name,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

    async def _store_task_result(self, result: TaskResult):
        """Store task execution result in Redis."""
        result_key = f"task:{result.task_id}:result"
        result_data = json.dumps(result.to_dict())
        
        await self._async_redis_pool.set(result_key, result_data, ex=86400)  # 24 hour TTL
        
        # Update task status
        await self._update_task_status(result.task_id, result.status, self.worker_name)

    async def _send_webhook_notification(self, task: Task, result: TaskResult):
        """Send webhook notification for task completion."""
        try:
            import httpx
            
            payload = {
                'task_id': task.task_id,
                'task_name': task.name,
                'status': result.status.value,
                'result': result.result,
                'error': result.error,
                'execution_time': result.execution_time,
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'tenant_id': task.tenant_id,
                'correlation_id': task.correlation_id,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    task.webhook_url,
                    json=payload,
                    timeout=10.0,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                
            logger.debug(f"Webhook notification sent", extra={
                'task_id': task.task_id,
                'webhook_url': task.webhook_url
            })
            
        except Exception as e:
            logger.warning(f"Failed to send webhook notification: {e}")

    async def _update_queue_metrics(self, queue_name: str, operation: str):
        """Update queue metrics in Redis."""
        metrics_key = f"metrics:queue:{queue_name}"
        await self._async_redis_pool.hincrby(metrics_key, operation, 1)
        await self._async_redis_pool.expire(metrics_key, 86400)  # 24 hour TTL

    def _get_priority_score(self, priority: TaskPriority) -> float:
        """Convert priority to numeric score for Redis sorted set."""
        priority_scores = {
            TaskPriority.CRITICAL: 1000.0,
            TaskPriority.HIGH: 100.0,
            TaskPriority.NORMAL: 10.0,
            TaskPriority.LOW: 1.0,
        }
        base_score = priority_scores[priority]
        # Add timestamp for FIFO ordering within priority
        timestamp_score = time.time() / 10000.0  # Small timestamp component
        return base_score + timestamp_score

    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve task execution result."""
        try:
            result_key = f"task:{task_id}:result"
            result_data = await self._async_redis_pool.get(result_key)
            
            if result_data:
                return TaskResult.from_dict(json.loads(result_data))
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task result for {task_id}: {e}")
            return None

    async def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task progress information."""
        try:
            progress_key = f"task:{task_id}:progress"
            progress_data = await self._async_redis_pool.hgetall(progress_key)
            
            if progress_data:
                return {
                    'percentage': int(progress_data.get('percentage', 0)),
                    'message': progress_data.get('message', ''),
                    'updated_at': progress_data.get('updated_at')
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task progress for {task_id}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            **self._stats,
            'worker_name': self.worker_name,
            'running_tasks': len(self._running_tasks),
            'registered_functions': len(self._task_functions),
            'is_running': self._is_running,
        }

    @asynccontextmanager
    async def task_context(self):
        """Context manager for safe task execution."""
        await self.initialize()
        try:
            yield self
        finally:
            await self.shutdown()