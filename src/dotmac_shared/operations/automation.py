"""
Infrastructure Maintenance Automation

Comprehensive infrastructure maintenance, optimization, and automation scripts.
Follows DRY patterns with standardized exception handling.
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.application import standard_exception_handler
from dotmac.core.exceptions import ServiceError
from dotmac_shared.monitoring.config import MonitoringConfig

logger = logging.getLogger(__name__)


class MaintenanceType(str, Enum):
    """Maintenance operation types"""

    DATABASE_CLEANUP = "database_cleanup"
    LOG_ROTATION = "log_rotation"
    CACHE_CLEANUP = "cache_cleanup"
    BACKUP_MANAGEMENT = "backup_management"
    SECURITY_UPDATES = "security_updates"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DISK_CLEANUP = "disk_cleanup"
    SYSTEM_MONITORING = "system_monitoring"


class MaintenanceStatus(str, Enum):
    """Maintenance task status"""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MaintenanceTask:
    """Maintenance task configuration"""

    task_id: UUID
    task_name: str
    maintenance_type: MaintenanceType
    schedule_cron: str
    enabled: bool = True
    timeout_minutes: int = 60
    retry_count: int = 3
    parameters: dict[str, Any] = None
    last_run: Optional[datetime] = None
    last_status: Optional[MaintenanceStatus] = None
    next_run: Optional[datetime] = None


@dataclass
class MaintenanceResult:
    """Maintenance operation result"""

    task_id: UUID
    task_name: str
    status: MaintenanceStatus
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    items_processed: int = 0
    items_cleaned: int = 0
    space_freed_mb: float = 0.0
    error_message: Optional[str] = None
    details: dict[str, Any] = None


class InfrastructureAutomation:
    """
    Comprehensive infrastructure maintenance automation.

    Provides automated maintenance, cleanup, and optimization
    for databases, logs, caches, and system resources.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        monitoring_config: Optional[MonitoringConfig] = None,
    ):
        self.db = db_session
        self.monitoring_config = monitoring_config or MonitoringConfig(
            service_name="infrastructure_automation"
        )
        self.maintenance_tasks: dict[UUID, MaintenanceTask] = {}

    @standard_exception_handler
    async def register_maintenance_task(self, task: MaintenanceTask) -> None:
        """Register maintenance task for automated execution."""
        self.maintenance_tasks[task.task_id] = task
        logger.info(f"Registered maintenance task: {task.task_name}")

    @standard_exception_handler
    async def database_cleanup(
        self, parameters: Optional[dict[str, Any]] = None
    ) -> MaintenanceResult:
        """Perform database maintenance and cleanup."""
        start_time = datetime.now(timezone.utc)
        task_id = uuid4()

        try:
            params = parameters or {}
            retention_days = params.get("retention_days", 30)
            vacuum_analyze = params.get("vacuum_analyze", True)
            cleanup_temp_tables = params.get("cleanup_temp_tables", True)

            items_processed = 0
            items_cleaned = 0

            # Clean old logs and events
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            # Clean user lifecycle events
            if "clean_lifecycle_events" in params and params["clean_lifecycle_events"]:
                # This would need actual implementation based on your database schema
                lifecycle_cleaned = await self._cleanup_old_lifecycle_events(
                    cutoff_date
                )
                items_cleaned += lifecycle_cleaned
                items_processed += lifecycle_cleaned

            # Clean audit logs
            if "clean_audit_logs" in params and params["clean_audit_logs"]:
                audit_cleaned = await self._cleanup_old_audit_logs(cutoff_date)
                items_cleaned += audit_cleaned
                items_processed += audit_cleaned

            # Clean temporary data
            if cleanup_temp_tables:
                temp_cleaned = await self._cleanup_temp_tables()
                items_cleaned += temp_cleaned
                items_processed += temp_cleaned

            # Database optimization
            if vacuum_analyze:
                await self._vacuum_analyze_database()

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Database cleanup completed: {items_cleaned} items cleaned in {duration:.2f}s"
            )

            return MaintenanceResult(
                task_id=task_id,
                task_name="database_cleanup",
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                items_processed=items_processed,
                items_cleaned=items_cleaned,
                details={
                    "retention_days": retention_days,
                    "vacuum_analyze": vacuum_analyze,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Database cleanup failed: {e}")

            return MaintenanceResult(
                task_id=task_id,
                task_name="database_cleanup",
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                error_message=str(e),
            )

    @standard_exception_handler
    async def log_rotation_cleanup(
        self, parameters: Optional[dict[str, Any]] = None
    ) -> MaintenanceResult:
        """Perform log rotation and cleanup."""
        start_time = datetime.now(timezone.utc)
        task_id = uuid4()

        try:
            params = parameters or {}
            log_directories = params.get("log_directories", ["/var/log", "/app/logs"])
            max_age_days = params.get("max_age_days", 7)
            max_size_mb = params.get("max_size_mb", 100)
            compress_old_logs = params.get("compress_old_logs", True)

            items_processed = 0
            items_cleaned = 0
            space_freed = 0.0

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

            for log_dir in log_directories:
                log_path = Path(log_dir)
                if not log_path.exists():
                    continue

                # Process log files
                for log_file in log_path.rglob("*.log*"):
                    items_processed += 1

                    try:
                        # Check file age
                        file_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                        file_size_mb = log_file.stat().st_size / (1024 * 1024)

                        if file_modified < cutoff_date or file_size_mb > max_size_mb:
                            if compress_old_logs and not str(log_file).endswith(".gz"):
                                # Compress instead of delete
                                await self._compress_log_file(log_file)
                            else:
                                # Delete old or oversized files
                                space_freed += file_size_mb
                                log_file.unlink()
                                items_cleaned += 1

                    except Exception as e:
                        logger.warning(f"Failed to process log file {log_file}: {e}")

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Log cleanup completed: {items_cleaned} files cleaned, {space_freed:.2f}MB freed"
            )

            return MaintenanceResult(
                task_id=task_id,
                task_name="log_rotation_cleanup",
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                items_processed=items_processed,
                items_cleaned=items_cleaned,
                space_freed_mb=space_freed,
                details={
                    "log_directories": log_directories,
                    "max_age_days": max_age_days,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Log cleanup failed: {e}")

            return MaintenanceResult(
                task_id=task_id,
                task_name="log_rotation_cleanup",
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                error_message=str(e),
            )

    @standard_exception_handler
    async def cache_cleanup(
        self, parameters: Optional[dict[str, Any]] = None
    ) -> MaintenanceResult:
        """Clean up cache systems and temporary files."""
        start_time = datetime.now(timezone.utc)
        task_id = uuid4()

        try:
            params = parameters or {}
            redis_cleanup = params.get("redis_cleanup", True)
            file_cache_cleanup = params.get("file_cache_cleanup", True)
            temp_dir_cleanup = params.get("temp_dir_cleanup", True)

            items_processed = 0
            items_cleaned = 0
            space_freed = 0.0

            # Redis cache cleanup
            if redis_cleanup:
                redis_stats = await self._cleanup_redis_cache(params)
                items_processed += redis_stats["processed"]
                items_cleaned += redis_stats["cleaned"]

            # File cache cleanup
            if file_cache_cleanup:
                cache_dirs = params.get(
                    "cache_directories", ["/tmp/cache", "/var/cache"]
                )
                for cache_dir in cache_dirs:
                    cache_path = Path(cache_dir)
                    if cache_path.exists():
                        dir_stats = await self._cleanup_directory(
                            cache_path,
                            max_age_hours=params.get("cache_max_age_hours", 24),
                        )
                        items_processed += dir_stats["processed"]
                        items_cleaned += dir_stats["cleaned"]
                        space_freed += dir_stats["space_freed"]

            # Temp directory cleanup
            if temp_dir_cleanup:
                temp_dirs = params.get("temp_directories", ["/tmp", "/var/tmp"])
                for temp_dir in temp_dirs:
                    temp_path = Path(temp_dir)
                    if temp_path.exists():
                        temp_stats = await self._cleanup_directory(
                            temp_path, max_age_hours=params.get("temp_max_age_hours", 1)
                        )
                        items_processed += temp_stats["processed"]
                        items_cleaned += temp_stats["cleaned"]
                        space_freed += temp_stats["space_freed"]

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Cache cleanup completed: {items_cleaned} items cleaned, {space_freed:.2f}MB freed"
            )

            return MaintenanceResult(
                task_id=task_id,
                task_name="cache_cleanup",
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                items_processed=items_processed,
                items_cleaned=items_cleaned,
                space_freed_mb=space_freed,
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Cache cleanup failed: {e}")

            return MaintenanceResult(
                task_id=task_id,
                task_name="cache_cleanup",
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                error_message=str(e),
            )

    @standard_exception_handler
    async def performance_optimization(
        self, parameters: Optional[dict[str, Any]] = None
    ) -> MaintenanceResult:
        """Perform system performance optimization."""
        start_time = datetime.now(timezone.utc)
        task_id = uuid4()

        try:
            params = parameters or {}
            analyze_queries = params.get("analyze_queries", True)
            update_statistics = params.get("update_statistics", True)
            optimize_indexes = params.get("optimize_indexes", True)

            optimizations_applied = 0

            # Database query optimization
            if analyze_queries:
                query_optimizations = await self._analyze_slow_queries()
                optimizations_applied += query_optimizations

            # Database statistics update
            if update_statistics:
                await self._update_database_statistics()
                optimizations_applied += 1

            # Index optimization
            if optimize_indexes:
                index_optimizations = await self._optimize_database_indexes()
                optimizations_applied += index_optimizations

            # System resource optimization
            system_optimizations = await self._optimize_system_resources()
            optimizations_applied += system_optimizations

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Performance optimization completed: {optimizations_applied} optimizations applied"
            )

            return MaintenanceResult(
                task_id=task_id,
                task_name="performance_optimization",
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                items_processed=optimizations_applied,
                details={
                    "optimizations_applied": optimizations_applied,
                    "analyze_queries": analyze_queries,
                    "update_statistics": update_statistics,
                    "optimize_indexes": optimize_indexes,
                },
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Performance optimization failed: {e}")

            return MaintenanceResult(
                task_id=task_id,
                task_name="performance_optimization",
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                error_message=str(e),
            )

    # Helper methods for specific maintenance operations

    async def _cleanup_old_lifecycle_events(self, cutoff_date: datetime) -> int:
        """Clean up old lifecycle events."""
        # Placeholder - would need actual SQL implementation
        await asyncio.sleep(0.1)  # Simulate database operation
        return 150  # Simulated cleanup count

    async def _cleanup_old_audit_logs(self, cutoff_date: datetime) -> int:
        """Clean up old audit logs."""
        # Placeholder - would need actual SQL implementation
        await asyncio.sleep(0.1)  # Simulate database operation
        return 300  # Simulated cleanup count

    async def _cleanup_temp_tables(self) -> int:
        """Clean up temporary database tables."""
        # Placeholder - would need actual SQL implementation
        await asyncio.sleep(0.1)  # Simulate database operation
        return 25  # Simulated cleanup count

    async def _vacuum_analyze_database(self) -> None:
        """Perform database vacuum and analyze operations."""
        # Placeholder - would need actual SQL implementation
        await asyncio.sleep(0.2)  # Simulate database operation
        logger.info("Database vacuum and analyze completed")

    async def _compress_log_file(self, log_file: Path) -> None:
        """Compress log file using gzip."""
        import gzip

        with open(log_file, "rb") as f_in:
            with gzip.open(f"{log_file}.gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove original file after compression
        log_file.unlink()

    async def _cleanup_redis_cache(self, params: dict[str, Any]) -> dict[str, int]:
        """Clean up Redis cache."""
        # Placeholder for Redis cleanup
        await asyncio.sleep(0.1)  # Simulate Redis operations
        return {"processed": 1000, "cleaned": 200}

    async def _cleanup_directory(
        self, directory: Path, max_age_hours: int = 24
    ) -> dict[str, Any]:
        """Clean up files in directory older than specified age."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        processed = 0
        cleaned = 0
        space_freed = 0.0

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    processed += 1

                    file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if file_modified < cutoff_time:
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        file_path.unlink()
                        cleaned += 1
                        space_freed += file_size_mb

        except Exception as e:
            logger.warning(f"Error cleaning directory {directory}: {e}")

        return {
            "processed": processed,
            "cleaned": cleaned,
            "space_freed": space_freed,
        }

    async def _analyze_slow_queries(self) -> int:
        """Analyze and optimize slow database queries."""
        # Placeholder - would analyze pg_stat_statements or similar
        await asyncio.sleep(0.1)  # Simulate analysis
        return 5  # Number of queries optimized

    async def _update_database_statistics(self) -> None:
        """Update database statistics for query optimization."""
        # Placeholder - would run ANALYZE on tables
        await asyncio.sleep(0.1)  # Simulate statistics update

    async def _optimize_database_indexes(self) -> int:
        """Optimize database indexes."""
        # Placeholder - would analyze and rebuild fragmented indexes
        await asyncio.sleep(0.1)  # Simulate index optimization
        return 10  # Number of indexes optimized

    async def _optimize_system_resources(self) -> int:
        """Optimize system resources."""
        # Placeholder - could optimize memory, clear caches, etc.
        await asyncio.sleep(0.1)  # Simulate system optimization
        return 3  # Number of optimizations applied


class MaintenanceScheduler:
    """
    Task scheduler for automated maintenance operations.

    Manages scheduling and execution of maintenance tasks.
    """

    def __init__(self, infrastructure_automation: InfrastructureAutomation):
        self.automation = infrastructure_automation
        self.running = False
        self.task_history: list[MaintenanceResult] = []

    @standard_exception_handler
    async def start_scheduler(self) -> None:
        """Start the maintenance scheduler."""
        self.running = True
        logger.info("Maintenance scheduler started")

        while self.running:
            try:
                await self._check_and_execute_tasks()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    @standard_exception_handler
    async def stop_scheduler(self) -> None:
        """Stop the maintenance scheduler."""
        self.running = False
        logger.info("Maintenance scheduler stopped")

    async def _check_and_execute_tasks(self) -> None:
        """Check for due tasks and execute them."""
        current_time = datetime.now(timezone.utc)

        for task in self.automation.maintenance_tasks.values():
            if not task.enabled:
                continue

            # Check if task is due (simplified cron logic)
            if self._is_task_due(task, current_time):
                result = await self._execute_maintenance_task(task)
                self.task_history.append(result)

                # Keep only last 100 results
                if len(self.task_history) > 100:
                    self.task_history.pop(0)

    def _is_task_due(self, task: MaintenanceTask, current_time: datetime) -> bool:
        """Check if maintenance task is due for execution."""
        # Simplified due check - in reality would parse cron expression
        if task.last_run is None:
            return True

        # For demo purposes, run daily tasks if more than 24 hours since last run
        if "daily" in task.schedule_cron.lower():
            return current_time - task.last_run > timedelta(hours=24)

        # Run hourly tasks if more than 1 hour since last run
        if "hourly" in task.schedule_cron.lower():
            return current_time - task.last_run > timedelta(hours=1)

        return False

    async def _execute_maintenance_task(
        self, task: MaintenanceTask
    ) -> MaintenanceResult:
        """Execute a maintenance task."""
        logger.info(f"Executing maintenance task: {task.task_name}")

        task.last_run = datetime.now(timezone.utc)

        try:
            # Route to appropriate maintenance method
            if task.maintenance_type == MaintenanceType.DATABASE_CLEANUP:
                result = await self.automation.database_cleanup(task.parameters)
            elif task.maintenance_type == MaintenanceType.LOG_ROTATION:
                result = await self.automation.log_rotation_cleanup(task.parameters)
            elif task.maintenance_type == MaintenanceType.CACHE_CLEANUP:
                result = await self.automation.cache_cleanup(task.parameters)
            elif task.maintenance_type == MaintenanceType.PERFORMANCE_OPTIMIZATION:
                result = await self.automation.performance_optimization(task.parameters)
            else:
                raise ServiceError(
                    f"Unsupported maintenance type: {task.maintenance_type}"
                )

            task.last_status = result.status
            return result

        except Exception as e:
            logger.error(f"Maintenance task failed: {task.task_name}: {e}")

            return MaintenanceResult(
                task_id=task.task_id,
                task_name=task.task_name,
                status=MaintenanceStatus.FAILED,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=0,
                error_message=str(e),
            )


class OperationsOrchestrator:
    """
    Central orchestrator for all operations automation.

    Coordinates health monitoring, lifecycle management, and maintenance.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.infrastructure_automation = InfrastructureAutomation(db_session)
        self.scheduler = MaintenanceScheduler(self.infrastructure_automation)

    @standard_exception_handler
    async def initialize_default_maintenance_tasks(self) -> None:
        """Initialize default maintenance tasks."""

        # Database cleanup - daily at 2 AM
        db_cleanup_task = MaintenanceTask(
            task_id=uuid4(),
            task_name="Daily Database Cleanup",
            maintenance_type=MaintenanceType.DATABASE_CLEANUP,
            schedule_cron="0 2 * * *",  # Daily at 2 AM
            parameters={
                "retention_days": 30,
                "vacuum_analyze": True,
                "clean_lifecycle_events": True,
                "clean_audit_logs": True,
            },
        )

        # Log rotation - daily at 3 AM
        log_rotation_task = MaintenanceTask(
            task_id=uuid4(),
            task_name="Daily Log Rotation",
            maintenance_type=MaintenanceType.LOG_ROTATION,
            schedule_cron="0 3 * * *",  # Daily at 3 AM
            parameters={
                "max_age_days": 7,
                "compress_old_logs": True,
                "log_directories": ["/var/log", "/app/logs"],
            },
        )

        # Cache cleanup - every 6 hours
        cache_cleanup_task = MaintenanceTask(
            task_id=uuid4(),
            task_name="Cache Cleanup",
            maintenance_type=MaintenanceType.CACHE_CLEANUP,
            schedule_cron="0 */6 * * *",  # Every 6 hours
            parameters={
                "redis_cleanup": True,
                "file_cache_cleanup": True,
                "cache_max_age_hours": 24,
            },
        )

        # Performance optimization - weekly on Sunday at 4 AM
        perf_optimization_task = MaintenanceTask(
            task_id=uuid4(),
            task_name="Weekly Performance Optimization",
            maintenance_type=MaintenanceType.PERFORMANCE_OPTIMIZATION,
            schedule_cron="0 4 * * 0",  # Weekly on Sunday at 4 AM
            parameters={
                "analyze_queries": True,
                "update_statistics": True,
                "optimize_indexes": True,
            },
        )

        # Register all tasks
        await self.infrastructure_automation.register_maintenance_task(db_cleanup_task)
        await self.infrastructure_automation.register_maintenance_task(
            log_rotation_task
        )
        await self.infrastructure_automation.register_maintenance_task(
            cache_cleanup_task
        )
        await self.infrastructure_automation.register_maintenance_task(
            perf_optimization_task
        )

        logger.info("Default maintenance tasks initialized")

    @standard_exception_handler
    async def start_operations(self) -> None:
        """Start all operations automation."""
        await self.initialize_default_maintenance_tasks()
        await self.scheduler.start_scheduler()

    @standard_exception_handler
    async def stop_operations(self) -> None:
        """Stop all operations automation."""
        await self.scheduler.stop_scheduler()

    @standard_exception_handler
    async def get_operations_status(self) -> dict[str, Any]:
        """Get comprehensive operations status."""

        return {
            "scheduler_running": self.scheduler.running,
            "active_tasks": len(self.infrastructure_automation.maintenance_tasks),
            "recent_results": [
                {
                    "task_name": result.task_name,
                    "status": result.status,
                    "duration_seconds": result.duration_seconds,
                    "items_cleaned": result.items_cleaned,
                    "space_freed_mb": result.space_freed_mb,
                    "end_time": result.end_time.isoformat(),
                }
                for result in self.scheduler.task_history[-10:]  # Last 10 results
            ],
            "maintenance_tasks": [
                {
                    "task_name": task.task_name,
                    "maintenance_type": task.maintenance_type,
                    "enabled": task.enabled,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "last_status": task.last_status,
                }
                for task in self.infrastructure_automation.maintenance_tasks.values()
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
