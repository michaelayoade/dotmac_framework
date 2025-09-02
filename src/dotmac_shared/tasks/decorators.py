"""
Task Decorators and Helper Utilities

Provides convenient decorators for creating and configuring background tasks:
- @task decorator for simple task registration
- @scheduled_task for cron-scheduled tasks
- @high_priority_task for urgent processing
- @retry_on_failure for automatic retry configuration
- Progress tracking and context utilities
"""

import asyncio
import functools
import inspect
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from .engine import Task, TaskConfig, TaskPriority, TaskStatus, TaskError
from .scheduler import CronSchedule, ScheduledTask
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)

# Global task registry
_TASK_REGISTRY: Dict[str, Callable] = {}
_SCHEDULED_TASKS: Dict[str, ScheduledTask] = {}


def task(
    name: Optional[str] = None,
    queue: str = "default",
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: Optional[float] = 300.0,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None
):
    """
    Decorator to register a function as a background task.
    
    Args:
        name: Task name (defaults to function name)
        queue: Queue name for task execution
        priority: Task priority level
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        timeout: Task timeout in seconds
        tags: Task tags for filtering
        metadata: Additional task metadata
        
    Example:
        @task(name="send_email", priority=TaskPriority.HIGH)
        async def send_email_task(recipient: str, subject: str, body: str):
            # Task implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__
        
        # Create task configuration
        config = TaskConfig(
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            priority=priority,
            queue_name=queue,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Register task function
        _TASK_REGISTRY[task_name] = func
        
        # Add task metadata to function
        func._task_name = task_name
        func._task_config = config
        func._is_background_task = True
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # For sync calls, return task creation helper
            return create_task_instance(task_name, args, kwargs, config)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For async calls, return task creation helper
            return create_task_instance(task_name, args, kwargs, config)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


def scheduled_task(
    cron_expression: str,
    name: Optional[str] = None,
    queue: str = "scheduled",
    priority: TaskPriority = TaskPriority.NORMAL,
    timezone: str = "UTC",
    max_instances: int = 1,
    overlap_policy: str = "skip",
    enabled: bool = True,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None
):
    """
    Decorator to register a function as a scheduled task.
    
    Args:
        cron_expression: Cron expression for scheduling
        name: Task name (defaults to function name)
        queue: Queue name for task execution
        priority: Task priority level
        timezone: Timezone for schedule evaluation
        max_instances: Maximum concurrent instances
        overlap_policy: How to handle overlapping executions
        enabled: Whether schedule is initially enabled
        tags: Task tags for filtering
        metadata: Additional task metadata
        
    Example:
        @scheduled_task("0 */6 * * *", name="cleanup_logs")
        async def cleanup_old_logs():
            # Cleanup implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or func.__name__
        
        # Register as regular task first
        task_decorator = task(
            name=task_name,
            queue=queue,
            priority=priority,
            tags=tags,
            metadata=metadata
        )
        decorated_func = task_decorator(func)
        
        # Create schedule configuration
        schedule = CronSchedule(
            expression=cron_expression,
            timezone=timezone,
            enabled=enabled,
            max_instances=max_instances,
            overlap_policy=overlap_policy,
            metadata=metadata or {}
        )
        
        # Create scheduled task
        scheduled_task_obj = ScheduledTask(
            task_id=f"scheduled-{task_name}-{int(time.time())}",
            name=task_name,
            function_name=task_name,
            schedule=schedule,
            task_config=decorated_func._task_config,
            tags=tags or []
        )
        
        # Register scheduled task
        _SCHEDULED_TASKS[task_name] = scheduled_task_obj
        
        # Add schedule metadata to function
        decorated_func._is_scheduled_task = True
        decorated_func._schedule = schedule
        decorated_func._scheduled_task = scheduled_task_obj
        
        return decorated_func
    
    return decorator


def high_priority_task(
    name: Optional[str] = None,
    queue: str = "high_priority",
    max_retries: int = 5,
    timeout: Optional[float] = 600.0,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None
):
    """
    Decorator for high-priority tasks that need urgent processing.
    
    Args:
        name: Task name (defaults to function name)
        queue: Queue name (defaults to high_priority)
        max_retries: Maximum retry attempts
        timeout: Task timeout in seconds
        tags: Task tags for filtering
        metadata: Additional task metadata
        
    Example:
        @high_priority_task(name="process_payment")
        async def process_payment(payment_id: str):
            # Payment processing implementation
            pass
    """
    return task(
        name=name,
        queue=queue,
        priority=TaskPriority.HIGH,
        max_retries=max_retries,
        timeout=timeout,
        tags=tags,
        metadata=metadata
    )


def background_task(
    name: Optional[str] = None,
    queue: str = "background",
    priority: TaskPriority = TaskPriority.LOW,
    timeout: Optional[float] = 1800.0,  # 30 minutes
    tags: List[str] = None,
    metadata: Dict[str, Any] = None
):
    """
    Decorator for background tasks that can run with lower priority.
    
    Args:
        name: Task name (defaults to function name)
        queue: Queue name (defaults to background)
        priority: Task priority (defaults to LOW)
        timeout: Task timeout in seconds
        tags: Task tags for filtering
        metadata: Additional task metadata
        
    Example:
        @background_task(name="generate_reports")
        async def generate_monthly_reports():
            # Report generation implementation
            pass
    """
    return task(
        name=name,
        queue=queue,
        priority=priority,
        timeout=timeout,
        tags=tags,
        metadata=metadata
    )


def retry_on_failure(
    max_retries: int = 5,
    retry_delay: float = 2.0,
    exponential_backoff: bool = True,
    exceptions: List[Exception] = None
):
    """
    Decorator to add retry configuration to existing tasks.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries
        exponential_backoff: Whether to use exponential backoff
        exceptions: Specific exceptions to retry on
        
    Example:
        @task(name="api_call")
        @retry_on_failure(max_retries=5, exponential_backoff=True)
        async def call_external_api(url: str):
            # API call implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Update task configuration if it exists
        if hasattr(func, '_task_config'):
            func._task_config.max_retries = max_retries
            func._task_config.retry_delay = retry_delay
            
            # Add retry configuration to metadata
            retry_config = {
                'exponential_backoff': exponential_backoff,
                'retry_exceptions': [e.__name__ for e in (exceptions or [])]
            }
            func._task_config.metadata.update(retry_config)
        
        # Add retry metadata to function
        func._retry_config = {
            'max_retries': max_retries,
            'retry_delay': retry_delay,
            'exponential_backoff': exponential_backoff,
            'exceptions': exceptions or []
        }
        
        return func
    
    return decorator


def progress_callback(callback_url: Optional[str] = None):
    """
    Decorator to add progress callback configuration to tasks.
    
    Args:
        callback_url: URL to receive progress updates
        
    Example:
        @task(name="data_processing")
        @progress_callback("https://api.example.com/progress")
        async def process_large_dataset(data: List[Dict]):
            # Processing with progress updates
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Add progress callback to function metadata
        func._progress_callback_url = callback_url
        func._has_progress_callback = True
        
        return func
    
    return decorator


def tenant_isolated(tenant_id_param: str = "tenant_id"):
    """
    Decorator to ensure task execution is tenant-isolated.
    
    Args:
        tenant_id_param: Parameter name containing tenant ID
        
    Example:
        @task(name="tenant_operation")
        @tenant_isolated(tenant_id_param="tenant_id")
        async def process_tenant_data(tenant_id: str, data: Dict):
            # Tenant-specific processing
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Add tenant isolation metadata
        func._tenant_isolated = True
        func._tenant_id_param = tenant_id_param
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract tenant ID from parameters
            tenant_id = None
            
            # Check kwargs first
            if tenant_id_param in kwargs:
                tenant_id = kwargs[tenant_id_param]
            else:
                # Check positional args based on function signature
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                if tenant_id_param in param_names:
                    param_index = param_names.index(tenant_id_param)
                    if param_index < len(args):
                        tenant_id = args[param_index]
            
            # Add tenant context to task execution
            if 'task_context' not in kwargs:
                kwargs['task_context'] = {}
            
            kwargs['task_context']['tenant_id'] = tenant_id
            
            # Call original function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def rate_limited(max_calls: int, time_window: int = 60):
    """
    Decorator to add rate limiting to task execution.
    
    Args:
        max_calls: Maximum calls allowed in time window
        time_window: Time window in seconds
        
    Example:
        @task(name="api_heavy_operation")
        @rate_limited(max_calls=10, time_window=60)
        async def heavy_api_operation():
            # Rate-limited operation
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Add rate limiting metadata
        func._rate_limited = True
        func._rate_limit_config = {
            'max_calls': max_calls,
            'time_window': time_window
        }
        
        # Update task config if available
        if hasattr(func, '_task_config'):
            func._task_config.metadata.update({
                'rate_limited': True,
                'rate_limit_max_calls': max_calls,
                'rate_limit_time_window': time_window
            })
        
        return func
    
    return decorator


def conditional_task(condition_func: Callable[..., bool]):
    """
    Decorator to add conditional execution to tasks.
    
    Args:
        condition_func: Function that returns True if task should execute
        
    Example:
        def should_process(data_size: int) -> bool:
            return data_size > 1000
            
        @task(name="conditional_processing")
        @conditional_task(should_process)
        async def process_if_large(data: List[Dict]):
            # Only runs if data is large enough
            pass
    """
    def decorator(func: Callable) -> Callable:
        func._conditional_execution = True
        func._condition_func = condition_func
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check condition before execution
            if not condition_func(*args, **kwargs):
                logger.info(f"Task {func.__name__} skipped due to condition")
                return {"status": "skipped", "reason": "condition_not_met"}
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Utility functions


def create_task_instance(
    task_name: str,
    args: tuple,
    kwargs: dict,
    config: TaskConfig,
    tenant_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Task:
    """
    Create a Task instance from decorated function call.
    
    Args:
        task_name: Name of the task
        args: Positional arguments
        kwargs: Keyword arguments
        config: Task configuration
        tenant_id: Optional tenant ID
        correlation_id: Optional correlation ID
        
    Returns:
        Task instance ready for queuing
    """
    return Task(
        name=task_name,
        function_name=task_name,
        args=list(args),
        kwargs=kwargs,
        config=config,
        tenant_id=tenant_id,
        correlation_id=correlation_id or f"{task_name}-{uuid.uuid4().hex[:8]}"
    )


def get_registered_tasks() -> Dict[str, Callable]:
    """Get all registered task functions."""
    return _TASK_REGISTRY.copy()


def get_scheduled_tasks() -> Dict[str, ScheduledTask]:
    """Get all registered scheduled tasks."""
    return _SCHEDULED_TASKS.copy()


def register_task_function(name: str, func: Callable):
    """Manually register a task function."""
    _TASK_REGISTRY[name] = func
    logger.info(f"Manually registered task function: {name}")


def unregister_task_function(name: str) -> bool:
    """Unregister a task function."""
    if name in _TASK_REGISTRY:
        del _TASK_REGISTRY[name]
        logger.info(f"Unregistered task function: {name}")
        return True
    return False


def is_background_task(func: Callable) -> bool:
    """Check if function is a registered background task."""
    return hasattr(func, '_is_background_task') and func._is_background_task


def is_scheduled_task(func: Callable) -> bool:
    """Check if function is a scheduled task."""
    return hasattr(func, '_is_scheduled_task') and func._is_scheduled_task


def get_task_config(func: Callable) -> Optional[TaskConfig]:
    """Get task configuration from decorated function."""
    return getattr(func, '_task_config', None)


def update_progress(percentage: int, message: str = "", task_context: Optional[Dict] = None):
    """
    Update task progress (to be called from within task functions).
    
    Args:
        percentage: Progress percentage (0-100)
        message: Progress message
        task_context: Task context (usually provided by framework)
    """
    if task_context and 'progress_callback' in task_context:
        try:
            callback = task_context['progress_callback']
            if asyncio.iscoroutinefunction(callback):
                # Can't await here, so we'll schedule it
                asyncio.create_task(callback(percentage, message))
            else:
                callback(percentage, message)
                
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")


def get_task_context() -> Dict[str, Any]:
    """
    Get current task execution context.
    
    This is a placeholder that would be properly implemented
    by the task engine when executing tasks.
    """
    # In a real implementation, this would access thread-local
    # or async context storage
    return {}


# Context manager for task execution


class TaskExecutionContext:
    """Context manager for task execution with progress tracking."""
    
    def __init__(
        self,
        task_name: str,
        progress_callback: Optional[Callable] = None,
        metadata: Dict[str, Any] = None
    ):
        self.task_name = task_name
        self.progress_callback = progress_callback
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.current_progress = 0
    
    async def __aenter__(self):
        self.start_time = time.time()
        logger.info(f"Starting task execution: {self.task_name}")
        
        if self.progress_callback:
            await self._safe_progress_update(0, "Task started")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - (self.start_time or time.time())
        
        if exc_type is None:
            logger.info(f"Task completed: {self.task_name} ({execution_time:.2f}s)")
            if self.progress_callback:
                await self._safe_progress_update(100, "Task completed")
        else:
            logger.error(f"Task failed: {self.task_name} - {exc_val}")
            if self.progress_callback:
                await self._safe_progress_update(self.current_progress, f"Task failed: {exc_val}")
    
    async def update_progress(self, percentage: int, message: str = ""):
        """Update task progress."""
        self.current_progress = percentage
        if self.progress_callback:
            await self._safe_progress_update(percentage, message)
    
    async def _safe_progress_update(self, percentage: int, message: str):
        """Safely update progress with error handling."""
        try:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(percentage, message)
            else:
                self.progress_callback(percentage, message)
        except Exception as e:
            logger.warning(f"Progress callback failed: {e}")


# Batch task processing utilities


async def execute_task_batch(
    tasks: List[Task],
    max_concurrent: int = 10,
    fail_fast: bool = False
) -> List[Dict[str, Any]]:
    """
    Execute multiple tasks concurrently with controlled concurrency.
    
    Args:
        tasks: List of Task instances to execute
        max_concurrent: Maximum concurrent executions
        fail_fast: Stop on first failure if True
        
    Returns:
        List of execution results
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []
    
    async def execute_single_task(task: Task) -> Dict[str, Any]:
        async with semaphore:
            try:
                # This would use the actual task engine in practice
                start_time = time.time()
                
                # Simulate task execution
                await asyncio.sleep(0.1)  # Placeholder
                
                execution_time = time.time() - start_time
                
                return {
                    'task_id': task.task_id,
                    'status': 'completed',
                    'execution_time': execution_time,
                    'result': 'success'
                }
                
            except Exception as e:
                return {
                    'task_id': task.task_id,
                    'status': 'failed',
                    'error': str(e)
                }
    
    # Execute tasks concurrently
    task_coroutines = [execute_single_task(task) for task in tasks]
    
    if fail_fast:
        # Stop on first failure
        for coro in asyncio.as_completed(task_coroutines):
            result = await coro
            results.append(result)
            
            if result['status'] == 'failed':
                # Cancel remaining tasks
                for remaining_coro in task_coroutines:
                    if hasattr(remaining_coro, 'cancel'):
                        remaining_coro.cancel()
                break
    else:
        # Execute all tasks regardless of failures
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # Process exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'task_id': tasks[i].task_id,
                    'status': 'failed',
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        results = processed_results
    
    return results


# Task dependency utilities


class TaskDependencyGraph:
    """Utility class for managing task dependencies."""
    
    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}
    
    def add_dependency(self, task_id: str, depends_on: str):
        """Add a dependency relationship."""
        if task_id not in self.dependencies:
            self.dependencies[task_id] = set()
        if depends_on not in self.dependents:
            self.dependents[depends_on] = set()
        
        self.dependencies[task_id].add(depends_on)
        self.dependents[depends_on].add(task_id)
    
    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[str]:
        """Get tasks that are ready to execute."""
        ready_tasks = []
        
        for task_id, deps in self.dependencies.items():
            if task_id not in completed_tasks and deps.issubset(completed_tasks):
                ready_tasks.append(task_id)
        
        return ready_tasks
    
    def validate_no_cycles(self) -> bool:
        """Check for circular dependencies."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for dep in self.dependencies.get(node, set()):
                if has_cycle(dep):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in self.dependencies:
            if has_cycle(task_id):
                return False
        
        return True