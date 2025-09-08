"""Tests for metrics module."""

import time

from dotmac_observability import MetricsCollector, get_collector, reset_collector
from dotmac_observability.types import MetricType


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_counter(self):
        """Test counter metrics."""
        collector = MetricsCollector()

        collector.counter("test_counter")
        collector.counter("test_counter", 2.0)
        collector.counter("test_counter", tags={"env": "test"})

        summary = collector.get_summary()

        # Should have two different counters (with and without tags)
        assert len(summary["counters"]) == 2
        assert "test_counter" in summary["counters"]
        assert "test_counter#env=test" in summary["counters"]

        # Check values
        assert summary["counters"]["test_counter"] == 3.0  # 1.0 + 2.0
        assert summary["counters"]["test_counter#env=test"] == 1.0

    def test_gauge(self):
        """Test gauge metrics."""
        collector = MetricsCollector()

        collector.gauge("memory_usage", 100.5)
        collector.gauge("memory_usage", 150.0)  # Should overwrite
        collector.gauge("cpu_usage", 75.0, tags={"core": "0"})

        summary = collector.get_summary()

        assert summary["gauges"]["memory_usage"] == 150.0
        assert summary["gauges"]["cpu_usage#core=0"] == 75.0

    def test_histogram(self):
        """Test histogram metrics."""
        collector = MetricsCollector()

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            collector.histogram("response_time", value)

        summary = collector.get_summary()

        assert "response_time" in summary["histograms"]
        hist = summary["histograms"]["response_time"]

        assert hist["count"] == 5
        assert hist["sum"] == 15.0
        assert hist["min"] == 1.0
        assert hist["max"] == 5.0
        assert hist["mean"] == 3.0

    def test_timer(self):
        """Test timer context manager."""
        collector = MetricsCollector()

        with collector.timer("operation_duration"):
            time.sleep(0.01)  # 10ms

        summary = collector.get_summary()

        assert "operation_duration" in summary["histograms"]
        hist = summary["histograms"]["operation_duration"]

        assert hist["count"] == 1
        assert hist["min"] > 0.005  # At least 5ms (some margin for timing)

    def test_tags(self):
        """Test metric tags."""
        collector = MetricsCollector()

        tags = {"service": "api", "version": "1.0"}
        collector.counter("requests", tags=tags)

        summary = collector.get_summary()

        # Tags should be sorted in key
        expected_key = "requests#service=api,version=1.0"
        assert expected_key in summary["counters"]

    def test_get_metric_entries(self):
        """Test getting raw metric entries."""
        collector = MetricsCollector()

        collector.counter("test_metric", 1.0)
        collector.counter("other_metric", 2.0)

        # Get all entries
        all_entries = collector.get_metric_entries()
        assert len(all_entries) == 2

        # Get specific metric entries
        test_entries = collector.get_metric_entries("test_metric")
        assert len(test_entries) == 1
        assert test_entries[0].name == "test_metric"
        assert test_entries[0].type == MetricType.COUNTER

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()

        collector.counter("test_counter")
        collector.gauge("test_gauge", 100.0)

        assert len(collector.get_summary()["counters"]) == 1
        assert len(collector.get_summary()["gauges"]) == 1

        collector.reset()

        summary = collector.get_summary()
        assert len(summary["counters"]) == 0
        assert len(summary["gauges"]) == 0
        assert len(summary["histograms"]) == 0


class TestGlobalCollector:
    """Test the global collector functionality."""

    def test_get_collector_singleton(self):
        """Test that get_collector returns the same instance."""
        reset_collector()  # Start fresh

        collector1 = get_collector()
        collector2 = get_collector()

        assert collector1 is collector2

    def test_reset_collector(self):
        """Test resetting the global collector."""
        collector1 = get_collector()
        collector1.counter("test_counter")

        reset_collector()

        collector2 = get_collector()

        # Should be a new instance
        assert collector1 is not collector2

        # Should be empty
        summary = collector2.get_summary()
        assert len(summary["counters"]) == 0

    def teardown_method(self):
        """Clean up after each test."""
        reset_collector()
