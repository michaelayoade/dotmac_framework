"""Tests for edge cases and error conditions."""


import pytest

from dotmac_observability import HealthMonitor, MetricsCollector
from dotmac_observability.types import HealthStatus


class TestMetricsEdgeCases:
    """Test edge cases for metrics collection."""

    def test_empty_tags(self):
        """Test handling of empty tags."""
        collector = MetricsCollector()

        # Empty dict should be treated as None
        collector.counter("test", tags={})
        collector.counter("test", tags=None)

        summary = collector.get_summary()

        # Should have single counter (both resolve to same key)
        assert len(summary["counters"]) == 1
        assert summary["counters"]["test"] == 2.0

    def test_none_values(self):
        """Test handling of None and zero values."""
        collector = MetricsCollector()

        # Zero values should be allowed
        collector.counter("zero_counter", 0.0)
        collector.gauge("zero_gauge", 0.0)
        collector.histogram("zero_hist", 0.0)

        summary = collector.get_summary()

        assert summary["counters"]["zero_counter"] == 0.0
        assert summary["gauges"]["zero_gauge"] == 0.0
        assert summary["histograms"]["zero_hist"]["sum"] == 0.0

    def test_large_values(self):
        """Test handling of large values."""
        collector = MetricsCollector()

        large_value = 1e15
        collector.counter("large_counter", large_value)
        collector.gauge("large_gauge", large_value)
        collector.histogram("large_hist", large_value)

        summary = collector.get_summary()

        assert summary["counters"]["large_counter"] == large_value
        assert summary["gauges"]["large_gauge"] == large_value
        assert summary["histograms"]["large_hist"]["sum"] == large_value

    def test_negative_values(self):
        """Test handling of negative values."""
        collector = MetricsCollector()

        # Negative values should be allowed for gauges and histograms
        collector.gauge("temp", -10.0)
        collector.histogram("delta", -5.0)

        summary = collector.get_summary()

        assert summary["gauges"]["temp"] == -10.0
        assert summary["histograms"]["delta"]["min"] == -5.0

    def test_special_characters_in_names(self):
        """Test handling of special characters in metric names."""
        collector = MetricsCollector()

        special_names = [
            "metric.with.dots",
            "metric_with_underscores",
            "metric-with-dashes",
            "metric:with:colons",
            "metric/with/slashes",
        ]

        for name in special_names:
            collector.counter(name, 1.0)

        summary = collector.get_summary()

        # All should be recorded
        assert len(summary["counters"]) == len(special_names)

    def test_special_characters_in_tags(self):
        """Test handling of special characters in tag values."""
        collector = MetricsCollector()

        special_tags = {
            "path": "/api/v1/users",
            "error": "Connection failed: timeout",
            "version": "1.2.3-beta",
            "host": "server-01.example.com:8080",
        }

        collector.counter("requests", tags=special_tags)

        summary = collector.get_summary()

        # Should have one counter with encoded tags
        assert len(summary["counters"]) == 1

    def test_histogram_percentiles_edge_cases(self):
        """Test histogram percentile calculations with edge cases."""
        collector = MetricsCollector()

        # Single value
        collector.histogram("single", 42.0)

        summary = collector.get_summary()
        hist = summary["histograms"]["single"]

        assert hist["p50"] == 42.0
        assert hist["p95"] == 42.0
        assert hist["p99"] == 42.0

    def test_histogram_empty(self):
        """Test histogram with no values."""
        collector = MetricsCollector()

        # Add counter first to ensure histograms dict exists
        collector.counter("test", 1.0)

        summary = collector.get_summary()

        # Empty histograms should not appear in summary
        assert len(summary["histograms"]) == 0

    def test_get_metric_entries_empty(self):
        """Test get_metric_entries with no metrics."""
        collector = MetricsCollector()

        entries = collector.get_metric_entries()
        assert len(entries) == 0

        entries = collector.get_metric_entries("nonexistent")
        assert len(entries) == 0

    def test_metric_key_generation(self):
        """Test metric key generation edge cases."""
        collector = MetricsCollector()

        # Test tag ordering consistency
        tags1 = {"b": "2", "a": "1", "c": "3"}
        tags2 = {"c": "3", "a": "1", "b": "2"}

        collector.counter("test", 1.0, tags=tags1)
        collector.counter("test", 1.0, tags=tags2)

        summary = collector.get_summary()

        # Should be same counter (tags sorted consistently)
        assert len(summary["counters"]) == 1
        assert summary["counters"]["test#a=1,b=2,c=3"] == 2.0

    def test_timer_exception_handling(self):
        """Test timer context manager with exceptions."""
        collector = MetricsCollector()

        with pytest.raises(ValueError), collector.timer("failed_operation"):
            raise ValueError("Test error")

        summary = collector.get_summary()

        # Timer should still record the duration
        assert "failed_operation" in summary["histograms"]
        assert summary["histograms"]["failed_operation"]["count"] == 1


class TestHealthMonitorEdgeCases:
    """Test edge cases for health monitoring."""

    @pytest.mark.asyncio
    async def test_empty_health_monitor(self):
        """Test health monitor with no checks."""
        monitor = HealthMonitor()

        result = await monitor.run_checks()

        assert result["status"] == HealthStatus.UNKNOWN.value
        assert result["summary"]["total"] == 0
        assert len(result["checks"]) == 0

    @pytest.mark.asyncio
    async def test_health_check_timeout_edge_case(self):
        """Test health check with very small timeout."""
        monitor = HealthMonitor()

        async def slow_check():
            import asyncio

            await asyncio.sleep(0.1)
            return True

        monitor.add_check("slow", slow_check, timeout=0.01)  # 10ms timeout

        result = await monitor.run_checks()

        assert result["checks"]["slow"]["status"] == HealthStatus.TIMEOUT.value

    @pytest.mark.asyncio
    async def test_health_check_sync_function(self):
        """Test health monitor with synchronous check function."""
        monitor = HealthMonitor()

        def sync_check():
            return True

        monitor.add_check("sync", sync_check)

        result = await monitor.run_checks()

        assert result["checks"]["sync"]["status"] == HealthStatus.HEALTHY.value

    @pytest.mark.asyncio
    async def test_health_check_return_values(self):
        """Test different return values from health checks."""
        monitor = HealthMonitor()

        async def returns_false():
            return False

        async def returns_none():
            return None

        async def returns_string():
            return "healthy"

        monitor.add_check("false", returns_false)
        monitor.add_check("none", returns_none)
        monitor.add_check("string", returns_string)

        result = await monitor.run_checks()

        # Only True should be considered healthy
        assert result["checks"]["false"]["status"] == HealthStatus.UNHEALTHY.value
        assert result["checks"]["none"]["status"] == HealthStatus.UNHEALTHY.value
        assert result["checks"]["string"]["status"] == HealthStatus.UNHEALTHY.value

    def test_health_check_remove_nonexistent(self):
        """Test removing non-existent health check."""
        monitor = HealthMonitor()

        removed = monitor.remove_check("nonexistent")
        assert removed is False

    def test_health_check_list_checks_empty(self):
        """Test listing checks when none are configured."""
        monitor = HealthMonitor()

        checks = monitor.list_checks()
        assert len(checks) == 0

    @pytest.mark.asyncio
    async def test_health_check_complex_exception(self):
        """Test health check with complex exception."""
        monitor = HealthMonitor()

        async def complex_error():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e

        monitor.add_check("complex", complex_error)

        result = await monitor.run_checks()

        assert result["checks"]["complex"]["status"] == HealthStatus.UNHEALTHY.value
        assert "Outer error" in result["checks"]["complex"]["error"]

    def test_last_results_none(self):
        """Test get_last_results when no checks have been run."""
        monitor = HealthMonitor()

        result = monitor.get_last_results()
        assert result is None


class TestThreadSafety:
    """Test thread safety of metrics collector."""

    def test_concurrent_counter_updates(self):
        """Test concurrent counter updates."""
        import threading

        collector = MetricsCollector()

        def increment_counter():
            for _ in range(100):
                collector.counter("concurrent_test", 1.0)

        # Start 10 threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        summary = collector.get_summary()

        # Should have exactly 1000 total increments
        assert summary["counters"]["concurrent_test"] == 1000.0

    def test_concurrent_different_operations(self):
        """Test concurrent different metric operations."""
        import threading

        collector = MetricsCollector()

        def counter_ops():
            for i in range(50):
                collector.counter(f"counter_{i % 5}", 1.0)

        def gauge_ops():
            for i in range(50):
                collector.gauge(f"gauge_{i % 5}", float(i))

        def histogram_ops():
            for i in range(50):
                collector.histogram(f"hist_{i % 5}", float(i))

        threads = [
            threading.Thread(target=counter_ops),
            threading.Thread(target=gauge_ops),
            threading.Thread(target=histogram_ops),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        summary = collector.get_summary()

        # Should have metrics from all operations
        assert len(summary["counters"]) > 0
        assert len(summary["gauges"]) > 0
        assert len(summary["histograms"]) > 0
