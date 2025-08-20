"""
Background task management for dotmac_core_events.

Provides background task coordination for:
- Outbox event dispatch
- System cleanup tasks
- Health monitoring
- Metrics collection
"""

import asyncio
from typing import Optional

import structlog

from ..sdks import EventBusSDK, OutboxSDK, SchemaRegistrySDK
from .config import RuntimeConfig

logger = structlog.get_logger(__name__)


class BackgroundTaskManager:
    """Manager for background tasks."""

    def __init__(self):
        """Initialize task manager."""
        self._tasks = {}
        self._running = False

    async def start_task(self, name: str, coro) -> None:
        """
        Start a background task.

        Args:
            name: Task name
            coro: Coroutine to run
        """
        if name in self._tasks:
            logger.warning("Task already running", task_name=name)
            return

        task = asyncio.create_task(coro)
        self._tasks[name] = task

        logger.info("Started background task", task_name=name)

    async def stop_task(self, name: str) -> None:
        """
        Stop a background task.

        Args:
            name: Task name
        """
        if name not in self._tasks:
            return

        task = self._tasks[name]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        del self._tasks[name]
        logger.info("Stopped background task", task_name=name)

    async def stop_all(self) -> None:
        """Stop all background tasks."""
        self._running = False

        for name in list(self._tasks.keys()):
            await self.stop_task(name)

        logger.info("Stopped all background tasks")

    def is_running(self, name: str) -> bool:
        """Check if a task is running."""
        return name in self._tasks and not self._tasks[name].done()


async def outbox_dispatch_task(
    outbox: OutboxSDK,
    interval: int = 5
) -> None:
    """
    Background task for dispatching outbox events.

    Args:
        outbox: Outbox SDK instance
        interval: Dispatch interval in seconds
    """
    logger.info("Starting outbox dispatch task", interval=interval)

    try:
        while True:
            try:
                # Dispatch pending events
                result = await outbox.dispatch_pending_events()

                if result.get("dispatched_count", 0) > 0:
                    logger.debug(
                        "Dispatched outbox events",
                        dispatched=result["dispatched_count"],
                        failed=result.get("failed_count", 0)
                    )

            except Exception as e:
                logger.error("Error in outbox dispatch task", error=str(e))

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("Outbox dispatch task cancelled")
        raise


async def cleanup_task(
    event_bus: EventBusSDK,
    schema_registry: SchemaRegistrySDK,
    outbox: Optional[OutboxSDK],
    interval: int = 3600
) -> None:
    """
    Background task for system cleanup.

    Args:
        event_bus: Event bus SDK instance
        schema_registry: Schema registry SDK instance
        outbox: Optional outbox SDK instance
        interval: Cleanup interval in seconds
    """
    logger.info("Starting cleanup task", interval=interval)

    try:
        while True:
            try:
                cleanup_results = {}

                # Clean up schema registry cache
                try:
                    await schema_registry.cache.clear()
                    cleanup_results["schema_cache"] = "cleared"
                except Exception as e:
                    logger.warning("Failed to clear schema cache", error=str(e))

                # Clean up outbox if available
                if outbox:
                    try:
                        result = await outbox.cleanup_expired_events()
                        cleanup_results["outbox_cleanup"] = result
                    except Exception as e:
                        logger.warning("Failed to cleanup outbox", error=str(e))

                # Clean up event bus metrics
                try:
                    # This would depend on the adapter implementation
                    pass
                except Exception as e:
                    logger.warning("Failed to cleanup event bus", error=str(e))

                if cleanup_results:
                    logger.info("Completed cleanup tasks", results=cleanup_results)

            except Exception as e:
                logger.error("Error in cleanup task", error=str(e))

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")
        raise


async def health_monitoring_task(
    event_bus: EventBusSDK,
    schema_registry: SchemaRegistrySDK,
    outbox: Optional[OutboxSDK],
    interval: int = 60
) -> None:
    """
    Background task for health monitoring.

    Args:
        event_bus: Event bus SDK instance
        schema_registry: Schema registry SDK instance
        outbox: Optional outbox SDK instance
        interval: Health check interval in seconds
    """
    logger.info("Starting health monitoring task", interval=interval)

    try:
        while True:
            try:
                health_status = {}

                # Check event bus health
                try:
                    if hasattr(event_bus, "adapter"):
                        adapter_health = await event_bus.adapter.health_check()
                        health_status["event_bus"] = adapter_health
                except Exception as e:
                    health_status["event_bus"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }

                # Check schema registry health
                try:
                    # Simple health check - try to access cache
                    await schema_registry.cache.get("__health_check__")
                    health_status["schema_registry"] = {"status": "healthy"}
                except Exception as e:
                    health_status["schema_registry"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }

                # Check outbox health if available
                if outbox:
                    try:
                        # This would check database connectivity
                        health_status["outbox"] = {"status": "healthy"}
                    except Exception as e:
                        health_status["outbox"] = {
                            "status": "unhealthy",
                            "error": str(e)
                        }

                # Log health status
                unhealthy_components = [
                    name for name, status in health_status.items()
                    if status.get("status") != "healthy"
                ]

                if unhealthy_components:
                    logger.warning(
                        "Unhealthy components detected",
                        unhealthy=unhealthy_components,
                        health_status=health_status
                    )
                else:
                    logger.debug("All components healthy", health_status=health_status)

            except Exception as e:
                logger.error("Error in health monitoring task", error=str(e))

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("Health monitoring task cancelled")
        raise


async def metrics_collection_task(  # noqa: C901
    event_bus: EventBusSDK,
    schema_registry: SchemaRegistrySDK,
    outbox: Optional[OutboxSDK],
    interval: int = 30
) -> None:
    """
    Background task for metrics collection.

    Args:
        event_bus: Event bus SDK instance
        schema_registry: Schema registry SDK instance
        outbox: Optional outbox SDK instance
        interval: Metrics collection interval in seconds
    """
    logger.info("Starting metrics collection task", interval=interval)

    try:
        while True:
            try:
                metrics = {}

                # Collect event bus metrics
                try:
                    if hasattr(event_bus, "get_metrics"):
                        bus_metrics = await event_bus.get_metrics()
                        metrics["event_bus"] = bus_metrics
                except Exception as e:
                    logger.warning("Failed to collect event bus metrics", error=str(e))

                # Collect schema registry metrics
                try:
                    if hasattr(schema_registry, "get_metrics"):
                        registry_metrics = await schema_registry.get_metrics()
                        metrics["schema_registry"] = registry_metrics
                except Exception as e:
                    logger.warning("Failed to collect schema registry metrics", error=str(e))

                # Collect outbox metrics if available
                if outbox:
                    try:
                        if hasattr(outbox, "get_metrics"):
                            outbox_metrics = await outbox.get_metrics()
                            metrics["outbox"] = outbox_metrics
                    except Exception as e:
                        logger.warning("Failed to collect outbox metrics", error=str(e))

                if metrics:
                    logger.debug("Collected metrics", metrics=metrics)

            except Exception as e:
                logger.error("Error in metrics collection task", error=str(e))

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("Metrics collection task cancelled")
        raise


async def start_background_tasks(
    task_manager: BackgroundTaskManager,
    event_bus: EventBusSDK,
    schema_registry: SchemaRegistrySDK,
    outbox: Optional[OutboxSDK],
    config: RuntimeConfig
) -> None:
    """
    Start all configured background tasks.

    Args:
        task_manager: Task manager instance
        event_bus: Event bus SDK instance
        schema_registry: Schema registry SDK instance
        outbox: Optional outbox SDK instance
        config: Runtime configuration
    """
    logger.info("Starting background tasks")

    # Start outbox dispatch task if outbox is available
    if outbox:
        await task_manager.start_task(
            "outbox_dispatch",
            outbox_dispatch_task(outbox, config.outbox_dispatch_interval)
        )

    # Start cleanup task
    await task_manager.start_task(
        "cleanup",
        cleanup_task(
            event_bus,
            schema_registry,
            outbox,
            config.cleanup_interval
        )
    )

    # Start health monitoring if enabled
    if config.observability.enable_metrics:
        await task_manager.start_task(
            "health_monitoring",
            health_monitoring_task(event_bus, schema_registry, outbox)
        )

    # Start metrics collection if enabled
    if config.observability.enable_metrics:
        await task_manager.start_task(
            "metrics_collection",
            metrics_collection_task(event_bus, schema_registry, outbox)
        )

    logger.info("All background tasks started")
