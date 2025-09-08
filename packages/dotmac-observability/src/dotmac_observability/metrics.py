"""Metrics collection for dotmac-observability."""

import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from threading import Lock
from typing import Any, Optional

from .types import MetricEntry, MetricType, Tags


class MetricsCollector:
    """
    Thread-safe in-memory metrics collector.

    Provides counters, gauges, histograms, and timers with optional tags.
    """

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._metrics: dict[str, list[MetricEntry]] = defaultdict(list)
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def counter(self, name: str, value: float = 1.0, tags: Tags = None) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Value to add (default: 1.0)
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._metric_key(name, tags)
            self._counters[key] += value

            entry = MetricEntry(
                name=name,
                type=MetricType.COUNTER,
                value=self._counters[key],
                tags=tags,
                timestamp=datetime.utcnow(),
            )
            self._metrics[key].append(entry)

    def gauge(self, name: str, value: float, tags: Tags = None) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Gauge name
            value: Current value
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._metric_key(name, tags)
            self._gauges[key] = value

            entry = MetricEntry(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                tags=tags,
                timestamp=datetime.utcnow(),
            )
            self._metrics[key].append(entry)

    def histogram(self, name: str, value: float, tags: Tags = None) -> None:
        """
        Record a histogram value.

        Args:
            name: Histogram name
            value: Value to record
            tags: Optional tags for the metric
        """
        with self._lock:
            key = self._metric_key(name, tags)
            self._histograms[key].append(value)

            entry = MetricEntry(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                tags=tags,
                timestamp=datetime.utcnow(),
            )
            self._metrics[key].append(entry)

    @contextmanager
    def timer(self, name: str, tags: Tags = None) -> Iterator[None]:
        """
        Context manager for timing operations.

        Args:
            name: Timer name
            tags: Optional tags for the metric

        Example:
            with collector.timer("api_request"):
                # Your code here
                pass
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.histogram(name, duration, tags)

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of all collected metrics.

        Returns:
            Dictionary containing metric summaries
        """
        with self._lock:
            summary = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Calculate histogram statistics
            for key, values in self._histograms.items():
                if values:
                    sorted_values = sorted(values)
                    count = len(sorted_values)

                    summary["histograms"][key] = {
                        "count": count,
                        "sum": sum(sorted_values),
                        "min": sorted_values[0],
                        "max": sorted_values[-1],
                        "mean": sum(sorted_values) / count,
                        "p50": sorted_values[int(count * 0.5)],
                        "p95": sorted_values[int(count * 0.95)],
                        "p99": sorted_values[int(count * 0.99)],
                    }

        return summary

    def get_metric_entries(self, name: Optional[str] = None) -> list[MetricEntry]:
        """
        Get raw metric entries.

        Args:
            name: Optional metric name to filter by

        Returns:
            List of metric entries
        """
        with self._lock:
            if name is None:
                # Return all entries
                entries = []
                for metric_entries in self._metrics.values():
                    entries.extend(metric_entries)
                return entries
            else:
                # Return entries for specific metric
                entries = []
                for _key, metric_entries in self._metrics.items():
                    if any(entry.name == name for entry in metric_entries):
                        entries.extend([entry for entry in metric_entries if entry.name == name])
                return entries

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def _metric_key(self, name: str, tags: Tags) -> str:
        """Generate a unique key for a metric with tags."""
        if not tags:
            return name

        # Sort tags for consistent key generation
        tag_items = sorted(tags.items())
        tag_str = ",".join(f"{k}={v}" for k, v in tag_items)
        return f"{name}#{tag_str}"


# Global collector instance
_global_collector: Optional[MetricsCollector] = None
_collector_lock = Lock()


def get_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _global_collector

    if _global_collector is None:
        with _collector_lock:
            if _global_collector is None:
                _global_collector = MetricsCollector()

    return _global_collector


def reset_collector() -> None:
    """Reset the global collector (primarily for testing)."""
    global _global_collector

    with _collector_lock:
        _global_collector = None
