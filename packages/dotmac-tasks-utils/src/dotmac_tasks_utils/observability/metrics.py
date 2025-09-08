"""Metrics collection for task execution."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from dotmac_tasks_utils.types import TaskStatus


@dataclass
class TaskMetric:
    """Individual task execution metric."""
    task_id: str
    task_type: str
    status: TaskStatus
    duration_ms: float
    attempt: int
    timestamp: float = field(default_factory=time.time)
    queue_name: str = "default"
    error_type: str | None = None


class TaskMetrics:
    """In-memory metrics collector for task execution."""

    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self._lock = Lock()
        self._metrics: list[TaskMetric] = []
        self._active_tasks: set[str] = set()

        # Aggregate counters
        self._counters: dict[str, int] = defaultdict(int)
        self._durations: dict[str, list[float]] = defaultdict(list)

    def record_task_start(self, task_id: str, task_type: str, queue_name: str = "default") -> None:
        """Record task execution start."""
        with self._lock:
            self._active_tasks.add(task_id)
            self._counters[f"{queue_name}.{task_type}.started"] += 1
            self._counters["total.started"] += 1

    def record_task_completion(
        self,
        task_id: str,
        task_type: str,
        duration_ms: float,
        status: TaskStatus,
        attempt: int = 1,
        queue_name: str = "default",
        error_type: str | None = None
    ) -> None:
        """Record task completion."""
        with self._lock:
            self._active_tasks.discard(task_id)

            # Create metric record
            metric = TaskMetric(
                task_id=task_id,
                task_type=task_type,
                status=status,
                duration_ms=duration_ms,
                attempt=attempt,
                queue_name=queue_name,
                error_type=error_type
            )

            # Add to metrics list (with rotation)
            self._metrics.append(metric)
            if len(self._metrics) > self.max_metrics:
                # Remove oldest metrics
                self._metrics = self._metrics[-self.max_metrics:]

            # Update counters
            status_key = f"{queue_name}.{task_type}.{status.value}"
            self._counters[status_key] += 1
            self._counters[f"total.{status.value}"] += 1

            # Track durations for successful tasks
            if status == TaskStatus.SUCCESS:
                duration_key = f"{queue_name}.{task_type}.duration"
                self._durations[duration_key].append(duration_ms)

                # Keep only recent durations for percentile calculations
                if len(self._durations[duration_key]) > 1000:
                    self._durations[duration_key] = self._durations[duration_key][-1000:]

    def get_active_task_count(self) -> int:
        """Get number of currently active tasks."""
        with self._lock:
            return len(self._active_tasks)

    def get_counter(self, key: str) -> int:
        """Get counter value."""
        with self._lock:
            return self._counters.get(key, 0)

    def get_task_stats(
        self, queue_name: str | None = None, task_type: str | None = None
    ) -> dict[str, any]:
        """Get comprehensive task statistics."""
        with self._lock:
            stats = {
                "active_tasks": len(self._active_tasks),
                "total_metrics": len(self._metrics),
                "counters": dict(self._counters),
            }

            # Filter metrics if criteria provided
            filtered_metrics = self._metrics
            if queue_name or task_type:
                filtered_metrics = [
                    m for m in self._metrics
                    if (not queue_name or m.queue_name == queue_name) and
                       (not task_type or m.task_type == task_type)
                ]

            if filtered_metrics:
                # Calculate success rate
                successful = sum(1 for m in filtered_metrics if m.status == TaskStatus.SUCCESS)
                total = len(filtered_metrics)
                stats["success_rate"] = successful / total if total > 0 else 0

                # Calculate average duration for successful tasks
                successful_durations = [
                    m.duration_ms for m in filtered_metrics
                    if m.status == TaskStatus.SUCCESS
                ]

                if successful_durations:
                    stats["avg_duration_ms"] = sum(successful_durations) / len(successful_durations)
                    stats["min_duration_ms"] = min(successful_durations)
                    stats["max_duration_ms"] = max(successful_durations)

                    # Calculate percentiles
                    sorted_durations = sorted(successful_durations)
                    stats["p50_duration_ms"] = self._percentile(sorted_durations, 50)
                    stats["p95_duration_ms"] = self._percentile(sorted_durations, 95)
                    stats["p99_duration_ms"] = self._percentile(sorted_durations, 99)

                # Error breakdown
                error_counts = defaultdict(int)
                for m in filtered_metrics:
                    if m.status == TaskStatus.FAILED and m.error_type:
                        error_counts[m.error_type] += 1

                if error_counts:
                    stats["error_breakdown"] = dict(error_counts)

            return stats

    def get_queue_stats(self) -> dict[str, dict[str, any]]:
        """Get statistics grouped by queue."""
        with self._lock:
            queues = {m.queue_name for m in self._metrics}
            return {
                queue: self.get_task_stats(queue_name=queue)
                for queue in queues
            }

    def get_task_type_stats(self) -> dict[str, dict[str, any]]:
        """Get statistics grouped by task type."""
        with self._lock:
            task_types = {m.task_type for m in self._metrics}
            return {
                task_type: self.get_task_stats(task_type=task_type)
                for task_type in task_types
            }

    def get_recent_failures(self, limit: int = 50) -> list[TaskMetric]:
        """Get recent failed tasks."""
        with self._lock:
            failures = [
                m for m in self._metrics
                if m.status == TaskStatus.FAILED
            ]
            return sorted(failures, key=lambda m: m.timestamp, reverse=True)[:limit]

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        with self._lock:
            self._metrics.clear()
            self._active_tasks.clear()
            self._counters.clear()
            self._durations.clear()

    @staticmethod
    def _percentile(sorted_data: list[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0

        index = (percentile / 100.0) * (len(sorted_data) - 1)

        if index.is_integer():
            return sorted_data[int(index)]

        # Interpolate between two values
        lower_index = int(index)
        upper_index = lower_index + 1

        if upper_index >= len(sorted_data):
            return sorted_data[-1]

        weight = index - lower_index
        return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight


# Global metrics instance
_global_metrics: TaskMetrics | None = None


def get_global_metrics() -> TaskMetrics:
    """Get the global metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = TaskMetrics()
    return _global_metrics


def set_global_metrics(metrics: TaskMetrics) -> None:
    """Set the global metrics instance."""
    global _global_metrics
    _global_metrics = metrics
