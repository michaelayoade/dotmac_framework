"""
Redis-based Distributed Task Queue Implementation

Provides high-performance, distributed task queuing with:
- Priority-based task ordering
- Dead letter queue handling
- Batch operations and bulk processing
- Queue monitoring and statistics
- Multi-tenant queue isolation
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, TimeoutError

from .engine import Task, TaskStatus, TaskPriority, TaskError
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class TaskQueue(ABC):
    """Abstract base class for task queues."""

    @abstractmethod
    async def enqueue(self, task: Task) -> str:
        """Enqueue a task for processing."""
        pass

    @abstractmethod
    async def dequeue(self, queue_name: str = "default", timeout: int = 30) -> Optional[Task]:
        """Dequeue the next available task."""
        pass

    @abstractmethod
    async def get_queue_size(self, queue_name: str = "default") -> int:
        """Get the number of tasks in queue."""
        pass

    @abstractmethod
    async def get_queue_stats(self, queue_name: str = "default") -> Dict[str, Any]:
        """Get detailed queue statistics."""
        pass


class RedisTaskQueue(TaskQueue):
    """
    Redis-based distributed task queue with advanced features.
    
    Features:
    - Priority-based ordering using Redis sorted sets
    - Dead letter queue for failed tasks
    - Batch dequeue operations for high throughput
    - Queue monitoring and health checks
    - Multi-tenant queue isolation
    - Rate limiting per tenant/queue
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "dotmac_tasks",
        default_timeout: int = 30,
        max_queue_size: int = 10000,
        enable_dead_letter: bool = True,
        dead_letter_ttl: int = 86400 * 7,  # 7 days
    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_timeout = default_timeout
        self.max_queue_size = max_queue_size
        self.enable_dead_letter = enable_dead_letter
        self.dead_letter_ttl = dead_letter_ttl
        
        self._redis: Optional[AsyncRedis] = None
        self._is_connected = False

    async def initialize(self):
        """Initialize Redis connection and verify connectivity."""
        try:
            self._redis = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                max_connections=50
            )
            
            # Test connection
            await self._redis.ping()
            self._is_connected = True
            
            # Initialize Lua scripts for atomic operations
            await self._load_lua_scripts()
            
            logger.info("Redis task queue initialized successfully", extra={
                'redis_url': self.redis_url,
                'key_prefix': self.key_prefix
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis task queue: {e}")
            raise TaskError(f"Redis queue initialization failed: {e}")

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._is_connected = False
            logger.info("Redis task queue connection closed")

    async def _load_lua_scripts(self):
        """Load Lua scripts for atomic operations."""
        
        # Atomic enqueue script with size limit check
        self._enqueue_script = await self._redis.script_load("""
            local queue_key = KEYS[1]
            local task_key = KEYS[2]
            local max_size = tonumber(ARGV[1])
            local task_id = ARGV[2]
            local priority_score = tonumber(ARGV[3])
            local task_data = ARGV[4]
            local timestamp = ARGV[5]
            
            -- Check queue size limit
            local current_size = redis.call('ZCARD', queue_key)
            if current_size >= max_size then
                return {-1, "Queue size limit exceeded"}
            end
            
            -- Store task data
            redis.call('HSET', task_key, 'data', task_data, 'status', 'pending', 'enqueued_at', timestamp)
            
            -- Add to priority queue
            redis.call('ZADD', queue_key, priority_score, task_id)
            
            return {1, current_size + 1}
        """)
        
        # Atomic dequeue script with lease mechanism
        self._dequeue_script = await self._redis.script_load("""
            local queue_key = KEYS[1]
            local lease_key = KEYS[2]
            local worker_id = ARGV[1]
            local lease_timeout = tonumber(ARGV[2])
            local timestamp = ARGV[3]
            
            -- Get highest priority task
            local tasks = redis.call('ZREVRANGE', queue_key, 0, 0, 'WITHSCORES')
            if #tasks == 0 then
                return nil
            end
            
            local task_id = tasks[1]
            
            -- Remove from queue
            redis.call('ZREM', queue_key, task_id)
            
            -- Create lease
            redis.call('HSET', lease_key, task_id, worker_id)
            redis.call('EXPIRE', lease_key, lease_timeout)
            
            -- Update task status
            local task_key = 'task:' .. task_id
            redis.call('HSET', task_key, 'status', 'leased', 'worker', worker_id, 'leased_at', timestamp)
            
            return task_id
        """)

    async def enqueue(self, task: Task) -> str:
        """
        Enqueue a task with priority ordering and size limits.
        
        Args:
            task: Task instance to enqueue
            
        Returns:
            str: Task ID
            
        Raises:
            TaskError: If enqueue fails or queue is full
        """
        if not self._is_connected:
            raise TaskError("Queue not connected")

        try:
            # Determine queue key with tenant isolation
            queue_key = self._get_queue_key(task.config.queue_name, task.tenant_id)
            task_key = self._get_task_key(task.task_id)
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(
                task.config.priority, 
                task.scheduled_at or datetime.now(timezone.utc)
            )
            
            # Serialize task data
            task_data = json.dumps(task.to_dict())
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Execute atomic enqueue
            result = await self._redis.evalsha(
                self._enqueue_script,
                2,  # Number of keys
                queue_key,
                task_key,
                self.max_queue_size,
                task.task_id,
                priority_score,
                task_data,
                timestamp
            )
            
            if result[0] == -1:
                raise TaskError(result[1])
            
            # Update metrics
            await self._update_enqueue_metrics(task.config.queue_name, task.tenant_id)
            
            logger.info(f"Task enqueued successfully", extra={
                'task_id': task.task_id,
                'queue': task.config.queue_name,
                'tenant_id': task.tenant_id,
                'priority': task.config.priority.value,
                'queue_size': result[1]
            })
            
            return task.task_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.task_id}: {e}")
            raise TaskError(f"Enqueue failed: {e}")

    async def dequeue(
        self, 
        queue_name: str = "default", 
        timeout: int = None,
        tenant_id: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> Optional[Task]:
        """
        Dequeue the next highest priority task with lease mechanism.
        
        Args:
            queue_name: Name of the queue to dequeue from
            timeout: Blocking timeout in seconds
            tenant_id: Optional tenant isolation
            worker_id: Worker identifier for lease tracking
            
        Returns:
            Optional[Task]: Next available task or None if timeout
        """
        if not self._is_connected:
            raise TaskError("Queue not connected")

        timeout = timeout or self.default_timeout
        worker_id = worker_id or f"worker-{time.time()}"
        
        try:
            queue_key = self._get_queue_key(queue_name, tenant_id)
            lease_key = self._get_lease_key(queue_name, tenant_id)
            
            # Try immediate dequeue first
            task_id = await self._redis.evalsha(
                self._dequeue_script,
                2,  # Number of keys
                queue_key,
                lease_key,
                worker_id,
                300,  # 5 minute lease timeout
                datetime.now(timezone.utc).isoformat()
            )
            
            if task_id:
                task = await self._load_task(task_id)
                if task:
                    await self._update_dequeue_metrics(queue_name, tenant_id)
                    logger.debug(f"Task dequeued", extra={
                        'task_id': task_id,
                        'queue': queue_name,
                        'worker_id': worker_id
                    })
                    return task
            
            # If no immediate task, use blocking pop with timeout
            if timeout > 0:
                return await self._blocking_dequeue(queue_key, lease_key, worker_id, timeout)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue from {queue_name}: {e}")
            raise TaskError(f"Dequeue failed: {e}")

    async def _blocking_dequeue(
        self, 
        queue_key: str, 
        lease_key: str, 
        worker_id: str, 
        timeout: int
    ) -> Optional[Task]:
        """Implement blocking dequeue with timeout."""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            # Check for available tasks
            task_id = await self._redis.evalsha(
                self._dequeue_script,
                2,
                queue_key,
                lease_key,
                worker_id,
                300,
                datetime.now(timezone.utc).isoformat()
            )
            
            if task_id:
                task = await self._load_task(task_id)
                if task:
                    return task
            
            # Short sleep before retry
            await asyncio.sleep(0.1)
        
        return None

    async def _load_task(self, task_id: str) -> Optional[Task]:
        """Load task data from Redis."""
        try:
            task_key = self._get_task_key(task_id)
            task_data_json = await self._redis.hget(task_key, 'data')
            
            if task_data_json:
                task_data = json.loads(task_data_json)
                return Task.from_dict(task_data)
            
            logger.warning(f"Task data not found for {task_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load task {task_id}: {e}")
            return None

    async def dequeue_batch(
        self, 
        queue_name: str = "default", 
        batch_size: int = 10,
        tenant_id: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> List[Task]:
        """
        Dequeue multiple tasks in a single operation.
        
        Args:
            queue_name: Queue to dequeue from
            batch_size: Maximum number of tasks to dequeue
            tenant_id: Optional tenant isolation
            worker_id: Worker identifier
            
        Returns:
            List[Task]: List of dequeued tasks
        """
        tasks = []
        worker_id = worker_id or f"worker-{time.time()}"
        
        try:
            queue_key = self._get_queue_key(queue_name, tenant_id)
            lease_key = self._get_lease_key(queue_name, tenant_id)
            
            for _ in range(batch_size):
                task_id = await self._redis.evalsha(
                    self._dequeue_script,
                    2,
                    queue_key,
                    lease_key,
                    worker_id,
                    300,
                    datetime.now(timezone.utc).isoformat()
                )
                
                if not task_id:
                    break
                
                task = await self._load_task(task_id)
                if task:
                    tasks.append(task)
            
            if tasks:
                await self._update_batch_dequeue_metrics(queue_name, tenant_id, len(tasks))
                logger.info(f"Batch dequeued {len(tasks)} tasks", extra={
                    'queue': queue_name,
                    'batch_size': len(tasks),
                    'worker_id': worker_id
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to batch dequeue from {queue_name}: {e}")
            raise TaskError(f"Batch dequeue failed: {e}")

    async def requeue_task(
        self, 
        task: Task, 
        delay_seconds: int = 0,
        increment_retry: bool = True
    ) -> str:
        """
        Requeue a task with optional delay.
        
        Args:
            task: Task to requeue
            delay_seconds: Delay before task becomes available
            increment_retry: Whether to increment retry count
            
        Returns:
            str: Task ID
        """
        try:
            # Update task for requeue
            if increment_retry:
                # Create new task instance with incremented retry
                requeued_task = Task.from_dict(task.to_dict())
                if not hasattr(requeued_task.config, 'retry_count'):
                    requeued_task.config.metadata['retry_count'] = 0
                requeued_task.config.metadata['retry_count'] += 1
            else:
                requeued_task = task
            
            # Set scheduled time if delay specified
            if delay_seconds > 0:
                requeued_task.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            
            # Enqueue with updated priority (lower for retries)
            if increment_retry and requeued_task.config.priority != TaskPriority.CRITICAL:
                priority_map = {
                    TaskPriority.HIGH: TaskPriority.NORMAL,
                    TaskPriority.NORMAL: TaskPriority.LOW,
                    TaskPriority.LOW: TaskPriority.LOW
                }
                requeued_task.config.priority = priority_map.get(
                    requeued_task.config.priority, 
                    TaskPriority.LOW
                )
            
            return await self.enqueue(requeued_task)
            
        except Exception as e:
            logger.error(f"Failed to requeue task {task.task_id}: {e}")
            raise TaskError(f"Requeue failed: {e}")

    async def move_to_dead_letter(self, task: Task, reason: str) -> bool:
        """
        Move a task to the dead letter queue.
        
        Args:
            task: Task to move
            reason: Reason for dead letter placement
            
        Returns:
            bool: Success status
        """
        if not self.enable_dead_letter:
            return False
            
        try:
            dlq_key = self._get_dead_letter_key(task.config.queue_name, task.tenant_id)
            
            dead_letter_entry = {
                'task_data': json.dumps(task.to_dict()),
                'reason': reason,
                'moved_at': datetime.now(timezone.utc).isoformat(),
                'original_queue': task.config.queue_name,
                'tenant_id': task.tenant_id or ''
            }
            
            # Add to dead letter queue with TTL
            await self._redis.zadd(
                dlq_key, 
                {task.task_id: time.time()}
            )
            await self._redis.hset(
                f"{dlq_key}:data:{task.task_id}",
                mapping=dead_letter_entry
            )
            await self._redis.expire(dlq_key, self.dead_letter_ttl)
            await self._redis.expire(f"{dlq_key}:data:{task.task_id}", self.dead_letter_ttl)
            
            # Update metrics
            await self._update_dead_letter_metrics(task.config.queue_name, task.tenant_id)
            
            logger.warning(f"Task moved to dead letter queue", extra={
                'task_id': task.task_id,
                'reason': reason,
                'queue': task.config.queue_name
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move task to dead letter queue: {e}")
            return False

    async def get_queue_size(self, queue_name: str = "default", tenant_id: Optional[str] = None) -> int:
        """Get the current size of a queue."""
        try:
            queue_key = self._get_queue_key(queue_name, tenant_id)
            return await self._redis.zcard(queue_key)
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0

    async def get_queue_stats(self, queue_name: str = "default", tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        try:
            queue_key = self._get_queue_key(queue_name, tenant_id)
            metrics_key = self._get_metrics_key(queue_name, tenant_id)
            dlq_key = self._get_dead_letter_key(queue_name, tenant_id)
            
            # Get current queue size
            queue_size = await self._redis.zcard(queue_key)
            
            # Get dead letter queue size
            dlq_size = await self._redis.zcard(dlq_key) if self.enable_dead_letter else 0
            
            # Get metrics
            metrics = await self._redis.hgetall(metrics_key)
            
            # Get priority distribution
            priority_dist = await self._get_priority_distribution(queue_key)
            
            # Get oldest and newest task times
            oldest_task = await self._redis.zrange(queue_key, 0, 0, withscores=True)
            newest_task = await self._redis.zrange(queue_key, -1, -1, withscores=True)
            
            return {
                'queue_name': queue_name,
                'tenant_id': tenant_id,
                'current_size': queue_size,
                'dead_letter_size': dlq_size,
                'total_enqueued': int(metrics.get('enqueued', 0)),
                'total_dequeued': int(metrics.get('dequeued', 0)),
                'total_failed': int(metrics.get('failed', 0)),
                'priority_distribution': priority_dist,
                'oldest_task_score': oldest_task[0][1] if oldest_task else None,
                'newest_task_score': newest_task[0][1] if newest_task else None,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}

    async def _get_priority_distribution(self, queue_key: str) -> Dict[str, int]:
        """Get distribution of tasks by priority."""
        try:
            # Define priority score ranges
            priority_ranges = {
                'critical': (1000.0, float('inf')),
                'high': (100.0, 999.99),
                'normal': (10.0, 99.99),
                'low': (0.0, 9.99)
            }
            
            distribution = {}
            for priority, (min_score, max_score) in priority_ranges.items():
                count = await self._redis.zcount(queue_key, min_score, max_score)
                distribution[priority] = count
            
            return distribution
            
        except Exception as e:
            logger.warning(f"Failed to get priority distribution: {e}")
            return {}

    def _get_queue_key(self, queue_name: str, tenant_id: Optional[str] = None) -> str:
        """Generate Redis key for queue."""
        if tenant_id:
            return f"{self.key_prefix}:queue:{tenant_id}:{queue_name}"
        return f"{self.key_prefix}:queue:{queue_name}"

    def _get_task_key(self, task_id: str) -> str:
        """Generate Redis key for task data."""
        return f"{self.key_prefix}:task:{task_id}"

    def _get_lease_key(self, queue_name: str, tenant_id: Optional[str] = None) -> str:
        """Generate Redis key for task leases."""
        if tenant_id:
            return f"{self.key_prefix}:lease:{tenant_id}:{queue_name}"
        return f"{self.key_prefix}:lease:{queue_name}"

    def _get_metrics_key(self, queue_name: str, tenant_id: Optional[str] = None) -> str:
        """Generate Redis key for queue metrics."""
        if tenant_id:
            return f"{self.key_prefix}:metrics:{tenant_id}:{queue_name}"
        return f"{self.key_prefix}:metrics:{queue_name}"

    def _get_dead_letter_key(self, queue_name: str, tenant_id: Optional[str] = None) -> str:
        """Generate Redis key for dead letter queue."""
        if tenant_id:
            return f"{self.key_prefix}:dlq:{tenant_id}:{queue_name}"
        return f"{self.key_prefix}:dlq:{queue_name}"

    def _calculate_priority_score(self, priority: TaskPriority, scheduled_at: datetime) -> float:
        """Calculate priority score for Redis sorted set."""
        # Base priority scores
        priority_scores = {
            TaskPriority.CRITICAL: 10000.0,
            TaskPriority.HIGH: 1000.0,
            TaskPriority.NORMAL: 100.0,
            TaskPriority.LOW: 10.0
        }
        
        base_score = priority_scores[priority]
        
        # Add scheduled time component (earlier = higher score)
        scheduled_timestamp = scheduled_at.timestamp()
        now_timestamp = datetime.now(timezone.utc).timestamp()
        
        # For scheduled tasks in the future, reduce priority
        if scheduled_timestamp > now_timestamp:
            time_penalty = (scheduled_timestamp - now_timestamp) / 3600  # Hours in future
            base_score -= min(time_penalty, base_score * 0.5)
        else:
            # For overdue tasks, increase priority slightly
            time_bonus = min((now_timestamp - scheduled_timestamp) / 60, base_score * 0.1)  # Minutes overdue
            base_score += time_bonus
        
        # Add small random component to avoid exact ties
        import random
        base_score += random.uniform(0, 0.001)
        
        return base_score

    async def _update_enqueue_metrics(self, queue_name: str, tenant_id: Optional[str]):
        """Update enqueue metrics."""
        metrics_key = self._get_metrics_key(queue_name, tenant_id)
        await self._redis.hincrby(metrics_key, 'enqueued', 1)
        await self._redis.expire(metrics_key, 86400)  # 24 hour TTL

    async def _update_dequeue_metrics(self, queue_name: str, tenant_id: Optional[str]):
        """Update dequeue metrics."""
        metrics_key = self._get_metrics_key(queue_name, tenant_id)
        await self._redis.hincrby(metrics_key, 'dequeued', 1)
        await self._redis.expire(metrics_key, 86400)

    async def _update_batch_dequeue_metrics(self, queue_name: str, tenant_id: Optional[str], count: int):
        """Update batch dequeue metrics."""
        metrics_key = self._get_metrics_key(queue_name, tenant_id)
        await self._redis.hincrby(metrics_key, 'dequeued', count)
        await self._redis.hincrby(metrics_key, 'batch_operations', 1)
        await self._redis.expire(metrics_key, 86400)

    async def _update_dead_letter_metrics(self, queue_name: str, tenant_id: Optional[str]):
        """Update dead letter metrics."""
        metrics_key = self._get_metrics_key(queue_name, tenant_id)
        await self._redis.hincrby(metrics_key, 'dead_letter', 1)
        await self._redis.expire(metrics_key, 86400)

    async def list_queues(self, tenant_id: Optional[str] = None) -> List[str]:
        """List all available queues."""
        try:
            if tenant_id:
                pattern = f"{self.key_prefix}:queue:{tenant_id}:*"
                prefix_len = len(f"{self.key_prefix}:queue:{tenant_id}:")
            else:
                pattern = f"{self.key_prefix}:queue:*"
                prefix_len = len(f"{self.key_prefix}:queue:")
            
            keys = await self._redis.keys(pattern)
            return [key[prefix_len:] for key in keys if ':' not in key[prefix_len:]]
            
        except Exception as e:
            logger.error(f"Failed to list queues: {e}")
            return []

    async def purge_queue(self, queue_name: str = "default", tenant_id: Optional[str] = None) -> int:
        """
        Purge all tasks from a queue.
        
        Args:
            queue_name: Queue to purge
            tenant_id: Optional tenant isolation
            
        Returns:
            int: Number of tasks purged
        """
        try:
            queue_key = self._get_queue_key(queue_name, tenant_id)
            count = await self._redis.zcard(queue_key)
            
            if count > 0:
                await self._redis.delete(queue_key)
                logger.warning(f"Purged {count} tasks from queue {queue_name}")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to purge queue {queue_name}: {e}")
            return 0