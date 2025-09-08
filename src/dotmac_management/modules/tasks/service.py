"""
Task Management Service Layer

Provides business logic and orchestration for task management operations.
Acts as the interface between the API layer and the underlying task system
components, implementing business rules and validation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dotmac.tasks import (
    TaskEngine,
    TaskMonitor,
    TaskPriority,
    TaskStatus,
    WorkflowOrchestrator,
)
from dotmac.tasks.decorators import standard_exception_handler

from .schemas import SystemHealthResponse, TaskQueryRequest, TaskStatusResponse

logger = logging.getLogger(__name__)


class TaskManagementService:
    """
    Service class for task management operations.

    Provides a high-level interface for task management functionality,
    implementing business logic, validation, and orchestration between
    different task system components.
    """

    def __init__(
        self,
        task_engine: TaskEngine,
        task_monitor: TaskMonitor,
        workflow_orchestrator: WorkflowOrchestrator,
    ):
        self.task_engine = task_engine
        self.task_monitor = task_monitor
        self.workflow_orchestrator = workflow_orchestrator

    @standard_exception_handler
    async def get_task_details(
        self, task_id: str, tenant_id: str, include_logs: bool = False
    ) -> Optional[TaskStatusResponse]:
        """
        Get comprehensive task details with optional logs.

        Args:
            task_id: Task identifier
            tenant_id: Tenant identifier for authorization
            include_logs: Whether to include task execution logs

        Returns:
            Task details or None if not found
        """
        task_data = await self.task_engine.get_task_status(task_id, tenant_id)

        if not task_data:
            return None

        # Enrich with additional monitoring data
        if include_logs:
            logs = await self.task_monitor.get_task_logs(task_id, tenant_id)
            task_data["logs"] = logs

        # Get performance metrics for this task
        metrics = await self.task_monitor.get_task_metrics(task_id)
        if metrics:
            task_data.update(
                {
                    "execution_time": metrics.get("execution_time"),
                    "memory_usage": metrics.get("peak_memory"),
                    "cpu_usage": metrics.get("cpu_time"),
                }
            )

        return TaskStatusResponse(**task_data)

    @standard_exception_handler
    async def query_tasks_advanced(self, query: TaskQueryRequest, tenant_id: str) -> dict[str, Any]:
        """
        Advanced task querying with business logic validation.

        Args:
            query: Query parameters and filters
            tenant_id: Tenant identifier for authorization

        Returns:
            Query results with metadata
        """
        # Validate query parameters
        if query.created_after and query.created_before:
            if query.created_after >= query.created_before:
                raise ValueError("created_after must be before created_before")

        # Apply tenant-specific limits
        max_limit = await self._get_tenant_query_limit(tenant_id)
        if query.limit > max_limit:
            query.limit = max_limit

        # Build filters with tenant context
        filters = self._build_query_filters(query, tenant_id)

        # Execute query
        result = await self.task_engine.query_tasks(
            tenant_id=tenant_id,
            filters=filters,
            limit=query.limit,
            offset=query.offset,
            order_by=query.order_by,
            order_direction=query.order_direction,
        )

        # Enrich results with additional metadata
        for task in result["tasks"]:
            await self._enrich_task_data(task)

        return {
            "tasks": result["tasks"],
            "total_count": result["total_count"],
            "query_metadata": {
                "executed_at": datetime.now(timezone.utc),
                "tenant_id": tenant_id,
                "filters_applied": filters,
                "performance": result.get("query_performance", {}),
            },
        }

    @standard_exception_handler
    async def cancel_task_with_validation(
        self,
        task_id: str,
        tenant_id: str,
        reason: Optional[str] = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Cancel a task with business rule validation.

        Args:
            task_id: Task identifier
            tenant_id: Tenant identifier
            reason: Cancellation reason
            force: Whether to force cancellation

        Returns:
            Cancellation result with metadata
        """
        # Get current task status
        task_data = await self.task_engine.get_task_status(task_id, tenant_id)

        if not task_data:
            raise ValueError("Task not found")

        # Validate cancellation is allowed
        if not self._can_cancel_task(task_data, force):
            raise ValueError("Task cannot be cancelled in its current state")

        # Check for dependent tasks
        dependents = await self.task_engine.get_dependent_tasks(task_id)
        if dependents and not force:
            raise ValueError(f"Task has {len(dependents)} dependent tasks. Use force=True to cancel anyway.")

        # Perform cancellation
        success = await self.task_engine.cancel_task(task_id=task_id, tenant_id=tenant_id, reason=reason, force=force)

        if not success:
            raise RuntimeError("Failed to cancel task")

        # Log cancellation for audit
        await self._log_task_operation(
            task_id=task_id,
            tenant_id=tenant_id,
            operation="cancel",
            metadata={"reason": reason, "force": force},
        )

        return {
            "success": True,
            "cancelled_at": datetime.now(timezone.utc),
            "dependent_tasks_affected": len(dependents),
            "reason": reason,
        }

    @standard_exception_handler
    async def retry_task_with_strategy(
        self,
        task_id: str,
        tenant_id: str,
        reset_retry_count: bool = False,
        priority: Optional[TaskPriority] = None,
        delay_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Retry a failed task with intelligent retry strategy.

        Args:
            task_id: Task identifier
            tenant_id: Tenant identifier
            reset_retry_count: Whether to reset retry counter
            priority: New priority for retry
            delay_seconds: Delay before retry

        Returns:
            Retry result with new task ID
        """
        # Get current task status
        task_data = await self.task_engine.get_task_status(task_id, tenant_id)

        if not task_data:
            raise ValueError("Task not found")

        # Validate retry is allowed
        if not self._can_retry_task(task_data):
            raise ValueError("Task cannot be retried in its current state")

        # Analyze failure patterns to suggest retry strategy
        failure_analysis = await self._analyze_task_failure(task_id)

        # Apply intelligent retry parameters
        retry_params = self._calculate_retry_parameters(failure_analysis, delay_seconds, priority)

        # Execute retry
        new_task_id = await self.task_engine.retry_task(
            task_id=task_id,
            tenant_id=tenant_id,
            reset_retry_count=reset_retry_count,
            priority=retry_params["priority"],
            delay_seconds=retry_params["delay"],
        )

        if not new_task_id:
            raise RuntimeError("Failed to retry task")

        # Log retry for audit
        await self._log_task_operation(
            task_id=task_id,
            tenant_id=tenant_id,
            operation="retry",
            metadata={
                "new_task_id": new_task_id,
                "failure_analysis": failure_analysis,
                "retry_params": retry_params,
            },
        )

        return {
            "success": True,
            "original_task_id": task_id,
            "new_task_id": new_task_id,
            "retry_strategy": retry_params,
            "failure_analysis": failure_analysis,
            "retried_at": datetime.now(timezone.utc),
        }

    @standard_exception_handler
    async def get_comprehensive_system_health(self) -> SystemHealthResponse:
        """
        Get comprehensive system health with intelligent analysis.

        Returns:
            Detailed system health information
        """
        # Get basic health data
        health_data = await self.task_monitor.get_system_health()

        # Perform additional health checks
        extended_checks = await self._perform_extended_health_checks()

        # Analyze trends and generate recommendations
        health_trends = await self._analyze_health_trends()
        recommendations = await self._generate_health_recommendations(health_data, extended_checks, health_trends)

        # Combine all health information
        comprehensive_health = {
            **health_data,
            "extended_checks": extended_checks,
            "trends": health_trends,
            "recommendations": recommendations,
            "last_analysis": datetime.now(timezone.utc),
        }

        return SystemHealthResponse(**comprehensive_health)

    # Private helper methods

    async def _get_tenant_query_limit(self, tenant_id: str) -> int:
        """Get query limit for tenant based on their plan."""
        # This would typically check tenant plan/limits from database
        # For now, return a default
        return 1000

    def _build_query_filters(self, query: TaskQueryRequest, tenant_id: str) -> dict[str, Any]:
        """Build query filters with tenant context."""
        filters = {}

        if query.status:
            filters["status"] = query.status
        if query.priority:
            filters["priority"] = query.priority
        if query.task_type:
            filters["task_type"] = query.task_type
        if query.user_id:
            filters["user_id"] = query.user_id
        if query.created_after:
            filters["created_after"] = query.created_after
        if query.created_before:
            filters["created_before"] = query.created_before

        # Always filter by tenant
        filters["tenant_id"] = tenant_id

        return filters

    async def _enrich_task_data(self, task: dict[str, Any]) -> None:
        """Enrich task data with additional metadata."""
        # Add performance metrics if available
        metrics = await self.task_monitor.get_task_metrics(task["task_id"])
        if metrics:
            task.update(
                {
                    "performance_metrics": metrics,
                    "cost_estimate": self._calculate_task_cost(metrics),
                }
            )

    def _can_cancel_task(self, task_data: dict[str, Any], force: bool) -> bool:
        """Check if task can be cancelled."""
        status = task_data["status"]

        if force:
            return status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]

        return status in [TaskStatus.PENDING, TaskStatus.RUNNING]

    def _can_retry_task(self, task_data: dict[str, Any]) -> bool:
        """Check if task can be retried."""
        status = task_data["status"]
        retry_count = task_data.get("retry_count", 0)
        max_retries = task_data.get("max_retries", 3)

        return status == TaskStatus.FAILED and retry_count < max_retries

    async def _analyze_task_failure(self, task_id: str) -> dict[str, Any]:
        """Analyze task failure patterns to suggest retry strategy."""
        # Get task failure history
        failure_history = await self.task_monitor.get_task_failure_history(task_id)

        # Analyze failure patterns
        analysis = {
            "failure_type": "unknown",
            "is_transient": False,
            "recommended_delay": 60,
            "success_probability": 0.5,
        }

        if failure_history:
            # Analyze error patterns
            errors = [f.get("error") for f in failure_history if f.get("error")]

            # Simple heuristics for failure analysis
            if any("timeout" in str(e).lower() for e in errors):
                analysis.update(
                    {
                        "failure_type": "timeout",
                        "is_transient": True,
                        "recommended_delay": 120,
                        "success_probability": 0.7,
                    }
                )
            elif any("connection" in str(e).lower() for e in errors):
                analysis.update(
                    {
                        "failure_type": "connection",
                        "is_transient": True,
                        "recommended_delay": 30,
                        "success_probability": 0.8,
                    }
                )
            elif any("memory" in str(e).lower() for e in errors):
                analysis.update(
                    {
                        "failure_type": "resource",
                        "is_transient": False,
                        "recommended_delay": 300,
                        "success_probability": 0.3,
                    }
                )

        return analysis

    def _calculate_retry_parameters(
        self,
        failure_analysis: dict[str, Any],
        delay_seconds: Optional[int],
        priority: Optional[TaskPriority],
    ) -> dict[str, Any]:
        """Calculate optimal retry parameters based on failure analysis."""
        params = {
            "delay": delay_seconds or failure_analysis.get("recommended_delay", 60),
            "priority": priority,
        }

        # Adjust priority based on failure analysis
        if not priority:
            if failure_analysis.get("is_transient"):
                params["priority"] = TaskPriority.HIGH  # Retry transient failures quickly
            else:
                params["priority"] = TaskPriority.LOW  # Lower priority for non-transient failures

        return params

    async def _perform_extended_health_checks(self) -> dict[str, Any]:
        """Perform additional health checks beyond basic monitoring."""
        checks = {}

        # Check queue latency
        try:
            latency = await self.task_monitor.measure_queue_latency()
            checks["queue_latency"] = {
                "status": "healthy" if latency < 1.0 else "degraded",
                "value": latency,
                "unit": "seconds",
            }
        except Exception as e:
            checks["queue_latency"] = {"status": "unhealthy", "error": str(e)}

        # Check worker responsiveness
        try:
            worker_health = await self.task_monitor.check_worker_responsiveness()
            checks["worker_responsiveness"] = worker_health
        except Exception as e:
            checks["worker_responsiveness"] = {"status": "unhealthy", "error": str(e)}

        return checks

    async def _analyze_health_trends(self) -> dict[str, Any]:
        """Analyze system health trends over time."""
        # Get historical health data
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)

        trends = await self.task_monitor.get_health_trends(start_time, end_time)

        return {
            "error_rate_trend": trends.get("error_rate_trend", "stable"),
            "throughput_trend": trends.get("throughput_trend", "stable"),
            "latency_trend": trends.get("latency_trend", "stable"),
            "resource_usage_trend": trends.get("resource_usage_trend", "stable"),
        }

    async def _generate_health_recommendations(
        self,
        health_data: dict[str, Any],
        extended_checks: dict[str, Any],
        trends: dict[str, Any],
    ) -> list[str]:
        """Generate actionable health recommendations."""
        recommendations = []

        # Check error rate
        error_rate = health_data.get("error_rate", 0)
        if error_rate > 0.1:  # 10% error rate
            recommendations.append(
                f"High error rate detected ({error_rate:.1%}). " "Consider reviewing failed tasks and system resources."
            )

        # Check queue depth
        queue_health = health_data.get("queue_health", {})
        if queue_health.get("depth", 0) > 1000:
            recommendations.append(
                "Large queue depth detected. Consider scaling up workers or " "reviewing task processing efficiency."
            )

        # Check worker utilization
        worker_health = health_data.get("worker_health", {})
        utilization = worker_health.get("utilization", 0)
        if utilization > 0.9:  # 90% utilization
            recommendations.append(
                "High worker utilization detected. Consider adding more workers " "to handle increased load."
            )
        elif utilization < 0.3:  # 30% utilization
            recommendations.append(
                "Low worker utilization detected. Consider reducing worker count " "to optimize resource usage."
            )

        # Check trends
        if trends.get("error_rate_trend") == "increasing":
            recommendations.append("Error rate is trending upward. Investigate recent changes " "and system stability.")

        if trends.get("latency_trend") == "increasing":
            recommendations.append(
                "Response latency is increasing. Check system resources and " "consider performance optimization."
            )

        return recommendations

    def _calculate_task_cost(self, metrics: dict[str, Any]) -> float:
        """Calculate estimated cost for task execution."""
        # Simple cost calculation based on execution time and resource usage
        execution_time = metrics.get("execution_time", 0)  # seconds
        memory_usage = metrics.get("peak_memory", 0)  # bytes

        # Cost factors (adjust based on actual infrastructure costs)
        compute_cost_per_second = 0.001  # $0.001 per second
        memory_cost_per_gb_second = 0.0001  # $0.0001 per GB-second

        compute_cost = execution_time * compute_cost_per_second
        memory_cost = (memory_usage / (1024**3)) * execution_time * memory_cost_per_gb_second

        return compute_cost + memory_cost

    async def _log_task_operation(self, task_id: str, tenant_id: str, operation: str, metadata: dict[str, Any]) -> None:
        """Log task operations for audit purposes."""
        log_entry = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata,
        }

        logger.info(f"Task operation: {operation}", extra=log_entry)

        # Store in audit log if available
        try:
            await self.task_monitor.store_audit_log(log_entry)
        except Exception as e:
            logger.warning(f"Failed to store audit log: {e}")
