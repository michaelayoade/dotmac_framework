"""Performance monitoring for task execution."""

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any

from dotmac_tasks_utils.types import TaskStatus


@dataclass
class PerformanceSnapshot:
    """Point-in-time performance metrics."""

    timestamp: float
    task_type: str
    queue_name: str
    total_executions: int
    success_count: int
    failure_count: int
    avg_duration_ms: float
    p95_duration_ms: float
    success_rate: float


class TaskPerformanceMonitor:
    """Performance monitoring with time-based aggregation."""

    def __init__(self, window_size_seconds: int = 300):  # 5 minute windows
        self.window_size = window_size_seconds
        self._lock = Lock()

        # Raw execution data
        self._executions: list[dict] = []

        # Time-based aggregations
        self._snapshots: list[PerformanceSnapshot] = []

        # Current window stats
        self._current_window_start = self._get_current_window_start()
        self._current_stats: dict[str, dict] = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "durations": [],
            "task_type": "",
            "queue_name": ""
        })

    def record_execution(
        self,
        task_type: str,
        queue_name: str,
        duration_ms: float,
        status: TaskStatus
    ) -> None:
        """Record a task execution."""
        with self._lock:
            current_time = time.time()

            # Check if we need to rotate the window
            if current_time >= self._current_window_start + self.window_size:
                self._rotate_window()

            # Record execution
            execution = {
                "timestamp": current_time,
                "task_type": task_type,
                "queue_name": queue_name,
                "duration_ms": duration_ms,
                "status": status,
            }

            self._executions.append(execution)

            # Update current window stats
            key = f"{queue_name}:{task_type}"
            stats = self._current_stats[key]
            stats["task_type"] = task_type
            stats["queue_name"] = queue_name
            stats["total"] += 1

            if status == TaskStatus.SUCCESS:
                stats["success"] += 1
                stats["durations"].append(duration_ms)
            else:
                stats["failure"] += 1

            # Cleanup old executions (keep last hour)
            cutoff_time = current_time - 3600
            self._executions = [e for e in self._executions if e["timestamp"] > cutoff_time]

    def get_current_performance(self) -> dict[str, PerformanceSnapshot]:
        """Get performance metrics for the current window."""
        with self._lock:
            snapshots = {}

            for key, stats in self._current_stats.items():
                if stats["total"] == 0:
                    continue

                durations = stats["durations"]
                avg_duration = sum(durations) / len(durations) if durations else 0
                p95_duration = self._percentile(sorted(durations), 95) if durations else 0
                success_rate = stats["success"] / stats["total"]

                snapshot = PerformanceSnapshot(
                    timestamp=time.time(),
                    task_type=stats["task_type"],
                    queue_name=stats["queue_name"],
                    total_executions=stats["total"],
                    success_count=stats["success"],
                    failure_count=stats["failure"],
                    avg_duration_ms=avg_duration,
                    p95_duration_ms=p95_duration,
                    success_rate=success_rate
                )

                snapshots[key] = snapshot

            return snapshots

    def get_historical_snapshots(self, hours: int = 24) -> list[PerformanceSnapshot]:
        """Get historical performance snapshots."""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            return [
                snapshot for snapshot in self._snapshots
                if snapshot.timestamp > cutoff_time
            ]

    def get_performance_trends(
        self,
        task_type: str,
        queue_name: str,
        hours: int = 24
    ) -> dict[str, list[float]]:
        """Get performance trends for a specific task type."""
        snapshots = [
            s for s in self.get_historical_snapshots(hours)
            if s.task_type == task_type and s.queue_name == queue_name
        ]

        if not snapshots:
            return {}

        # Sort by timestamp
        snapshots.sort(key=lambda s: s.timestamp)

        return {
            "timestamps": [s.timestamp for s in snapshots],
            "success_rates": [s.success_rate for s in snapshots],
            "avg_durations": [s.avg_duration_ms for s in snapshots],
            "p95_durations": [s.p95_duration_ms for s in snapshots],
            "execution_counts": [s.total_executions for s in snapshots],
        }

    def get_failure_analysis(self, hours: int = 24) -> dict[str, Any]:
        """Get failure analysis for recent executions."""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            recent_executions = [
                e for e in self._executions
                if e["timestamp"] > cutoff_time
            ]

            # Group by task type and status
            task_stats = defaultdict(lambda: {"total": 0, "failed": 0, "errors": []})

            for execution in recent_executions:
                key = f"{execution['queue_name']}:{execution['task_type']}"
                task_stats[key]["total"] += 1

                if execution["status"] != TaskStatus.SUCCESS:
                    task_stats[key]["failed"] += 1

            # Calculate failure rates
            failure_analysis = {}
            for key, stats in task_stats.items():
                if stats["total"] > 0:
                    queue_name, task_type = key.split(":", 1)
                    failure_rate = stats["failed"] / stats["total"]

                    failure_analysis[key] = {
                        "queue_name": queue_name,
                        "task_type": task_type,
                        "total_executions": stats["total"],
                        "failed_executions": stats["failed"],
                        "failure_rate": failure_rate,
                        "success_rate": 1 - failure_rate,
                    }

            return failure_analysis

    def get_slowest_tasks(
        self,
        limit: int = 10,
        hours: int = 24
    ) -> list[dict[str, Any]]:
        """Get slowest task executions."""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            successful_executions = [
                e for e in self._executions
                if e["timestamp"] > cutoff_time and e["status"] == TaskStatus.SUCCESS
            ]

            # Sort by duration
            successful_executions.sort(key=lambda e: e["duration_ms"], reverse=True)

            return successful_executions[:limit]

    def _rotate_window(self) -> None:
        """Rotate to a new time window."""
        # Create snapshots from current window
        for stats in self._current_stats.values():
            if stats["total"] == 0:
                continue

            durations = stats["durations"]
            avg_duration = sum(durations) / len(durations) if durations else 0
            p95_duration = self._percentile(sorted(durations), 95) if durations else 0
            success_rate = stats["success"] / stats["total"]

            snapshot = PerformanceSnapshot(
                timestamp=self._current_window_start,
                task_type=stats["task_type"],
                queue_name=stats["queue_name"],
                total_executions=stats["total"],
                success_count=stats["success"],
                failure_count=stats["failure"],
                avg_duration_ms=avg_duration,
                p95_duration_ms=p95_duration,
                success_rate=success_rate
            )

            self._snapshots.append(snapshot)

        # Reset current window
        self._current_window_start = self._get_current_window_start()
        self._current_stats.clear()

        # Cleanup old snapshots (keep 7 days)
        cutoff_time = time.time() - (7 * 24 * 3600)
        self._snapshots = [s for s in self._snapshots if s.timestamp > cutoff_time]

    def _get_current_window_start(self) -> float:
        """Get the start time of the current window."""
        current_time = time.time()
        return (current_time // self.window_size) * self.window_size

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
