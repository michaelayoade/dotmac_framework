"""Enhanced usage examples for dotmac-tasks-utils with observability."""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from dotmac_tasks_utils import (
    ConfigManager,
    DotmacTasksConfig,
    retry_async,
    with_idempotency,
)
from dotmac_tasks_utils.monitoring import HealthChecker
from dotmac_tasks_utils.observability import get_global_metrics
from dotmac_tasks_utils.queue import create_redis_queue
from dotmac_tasks_utils.runner import AsyncTaskRunner
from dotmac_tasks_utils.storage.memory import MemoryIdempotencyStore
from dotmac_tasks_utils.storage.persistent import JsonFilePersistentStore
from dotmac_tasks_utils.types import TaskOptions, TaskPriority


async def main():
    """Demonstrate enhanced features."""
    
    # 1. Configuration Management
    print("=== Configuration Management ===")
    
    # Load from environment or use defaults
    config = ConfigManager.get_config()
    print(f"Redis URL: {config.redis.url}")
    print(f"Max attempts: {config.retry.max_attempts}")
    print(f"Observability enabled: {config.observability.logging_enabled}")
    
    # Override configuration programmatically
    custom_config = DotmacTasksConfig(
        redis=config.redis,
        retry=config.retry,
        tasks=config.tasks,
        idempotency=config.idempotency,
        observability=config.observability
    )
    custom_config.retry.max_attempts = 5
    ConfigManager.set_config(custom_config)
    
    # 2. Enhanced Retry with Observability
    print("\\n=== Enhanced Retry Mechanisms ===")
    
    @retry_async(max_attempts=3, base_delay=0.1)
    async def flaky_api_call(success_rate: float = 0.3):
        """Simulate a flaky API call."""
        import random
        if random.random() > success_rate:
            raise ConnectionError("API temporarily unavailable")
        return {"status": "success", "data": "important_data"}
    
    try:
        result = await flaky_api_call()
        print(f"API call succeeded: {result}")
    except Exception as e:
        print(f"API call failed: {e}")
    
    # 3. Idempotency with Configuration
    print("\\n=== Enhanced Idempotency ===")
    
    store = MemoryIdempotencyStore()
    
    @with_idempotency(store, ttl=300)
    async def process_payment(user_id: str, amount: float):
        """Process payment - should only happen once."""
        # Simulate payment processing
        await asyncio.sleep(0.1)
        return {
            "transaction_id": f"txn_{user_id}_{int(amount)}",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
    
    # First call
    payment1 = await process_payment("user123", 99.99)
    print(f"First payment: {payment1}")
    
    # Second call (should return cached result)
    payment2 = await process_payment("user123", 99.99)
    print(f"Second payment (cached): {payment2}")
    
    # 4. Task Queue with Observability
    print("\\n=== Enhanced Task Queue ===")
    
    if os.getenv("REDIS_URL"):
        queue = create_redis_queue(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            queue_name="enhanced_demo"
        )
        
        # Submit tasks with different priorities
        task_id1 = await queue.enqueue(
            {"action": "send_email", "recipient": "user@example.com"},
            options=TaskOptions(priority=TaskPriority.HIGH, max_attempts=3)
        )
        
        task_id2 = await queue.enqueue(
            {"action": "generate_report", "report_type": "daily"},
            options=TaskOptions(priority=TaskPriority.NORMAL, max_attempts=2)
        )
        
        print(f"Submitted high priority task: {task_id1}")
        print(f"Submitted normal priority task: {task_id2}")
        
        # Check queue status
        queue_size = queue.get_queue_size()
        print(f"Current queue size: {queue_size}")
        
    else:
        print("Redis not available, skipping queue demonstration")
    
    # 5. Task Runner with Monitoring
    print("\\n=== Enhanced Task Runner ===")
    
    runner = AsyncTaskRunner(max_concurrent=3)
    
    async def cpu_intensive_task(task_id: str, duration: float):
        """Simulate CPU intensive work."""
        await asyncio.sleep(duration)
        return {"task_id": task_id, "duration": duration, "result": "completed"}
    
    # Submit multiple tasks
    task_ids = []
    for i in range(5):
        task_id = await runner.submit(
            cpu_intensive_task,
            f"task_{i}",
            0.1,  # 100ms duration
            options=TaskOptions(priority=TaskPriority.NORMAL, max_attempts=2)
        )
        task_ids.append(task_id)
    
    print(f"Submitted {len(task_ids)} tasks to runner")
    
    # Wait for completion
    for task_id in task_ids:
        result = await runner.get_result(task_id)
        print(f"Task {task_id} completed with status: {result.status}")
    
    # 6. Health Monitoring
    print("\\n=== Health Monitoring ===")
    
    health_checker = HealthChecker(
        task_runner=runner,
        thresholds={
            "utilization_warning": 0.7,
            "utilization_critical": 0.9
        }
    )
    
    health = await health_checker.get_overall_health()
    print(f"System health: {health['status']}")
    print(f"Health checks: {health['summary']}")
    
    # 7. Metrics Collection
    print("\\n=== Metrics Collection ===")
    
    metrics = get_global_metrics()
    stats = metrics.get_task_stats()
    
    print(f"Active tasks: {stats['active_tasks']}")
    print(f"Total metrics collected: {stats['total_metrics']}")
    if 'success_rate' in stats:
        print(f"Overall success rate: {stats['success_rate']:.2%}")
    
    # 8. Persistent Storage (File-based)
    print("\\n=== Persistent Storage ===")
    
    persistent_store = JsonFilePersistentStore("task_history.json")
    
    # Store some example task results
    from dotmac_tasks_utils.types import TaskResult, TaskStatus
    
    example_result = TaskResult(
        task_id="demo_task_001",
        status=TaskStatus.SUCCESS,
        result={"message": "Task completed successfully"},
        started_at=datetime.now() - timedelta(seconds=30),
        completed_at=datetime.now(),
        attempts=1,
        max_attempts=3
    )
    
    await persistent_store.store_task_result(example_result)
    print("Stored task result to persistent storage")
    
    # Query stored tasks
    recent_tasks = await persistent_store.query_tasks(
        start_time=datetime.now() - timedelta(hours=1),
        limit=10
    )
    print(f"Found {len(recent_tasks)} recent tasks in persistent storage")
    
    # 9. Cleanup and Monitoring
    print("\\n=== Cleanup and Monitoring ===")
    
    # Cleanup completed tasks
    cleaned_count = runner.cleanup_completed(max_age_seconds=300)
    print(f"Cleaned up {cleaned_count} completed tasks")
    
    # Final health check
    is_healthy = await health_checker.is_healthy()
    print(f"System is healthy: {is_healthy}")
    
    print("\\n=== Enhanced Demo Complete ===")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set environment variables for demo
    os.environ.setdefault("DOTMAC_LOGGING_ENABLED", "true")
    os.environ.setdefault("DOTMAC_METRICS_ENABLED", "true")
    os.environ.setdefault("DOTMAC_MAX_ATTEMPTS", "3")
    
    asyncio.run(main())