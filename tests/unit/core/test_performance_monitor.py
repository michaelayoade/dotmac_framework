"""
Test performance monitoring system.
"""

import asyncio
from unittest.mock import patch

import pytest


# Mock the performance monitor components for testing
class PerformanceMetric:
    def __init__(self, name, value, metric_type, tags=None):
        self.name = name
        self.value = value
        self.metric_type = metric_type
        self.tags = tags or {}


class MetricType:
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class OptimalPerformanceCollector:
    def __init__(self):
        self.buffer_size = 1000
        self.flush_interval = 30
        self.metric_buffer = []
        self.metrics_collected = 0
        self.hit_count = 0
        self.miss_count = 0
        self.error_count = 0

    def record_metric(self, name, value, metric_type, tags=None):
        metric = PerformanceMetric(name, value, metric_type, tags)
        self.metric_buffer.append(metric)
        self.metrics_collected += 1

    def record_request_metric(self, endpoint, method, duration, status_code):
        self.record_metric(
            "request_duration",
            duration,
            MetricType.HISTOGRAM,
            {"endpoint": endpoint, "method": method},
        )
        self.record_metric(
            "request_count",
            1,
            MetricType.COUNTER,
            {"endpoint": endpoint, "method": method},
        )
        self.record_metric(
            "response_status", 1, MetricType.COUNTER, {"status_code": str(status_code)}
        )

    def get_current_metrics(self):
        return self.metric_buffer.copy()

    async def _flush_metrics(self):
        pass


class PerformanceAnalyzer:
    def calculate_percentiles(self, metrics, metric_name):
        values = [m.value for m in metrics if m.name == metric_name]
        if not values:
            return {}
        values.sort()
        return {
            "p50": values[len(values) // 2] if values else 0,
            "p95": values[int(len(values) * 0.95)] if values else 0,
            "p99": values[int(len(values) * 0.99)] if values else 0,
        }

    def detect_anomalies(self, metrics):
        return [m for m in metrics if m.value > 1.0]  # Simple threshold

    def generate_performance_report(self, metrics):
        return {
            "total_metrics": len(metrics),
            "by_type": {},
            "anomalies": self.detect_anomalies(metrics),
        }


class AlertManager:
    async def check_thresholds(self, metrics):
        for metric in metrics:
            if metric.name == "cpu_usage" and metric.value > 90:
                await self._send_alert(
                    type(
                        "Alert",
                        (),
                        {
                            "severity": "critical",
                            "message": f"High CPU usage: {metric.value}%",
                        },
                    )()
                )
            elif metric.name == "request_duration" and metric.value > 2.0:
                await self._send_alert(
                    type(
                        "Alert",
                        (),
                        {
                            "severity": "warning",
                            "message": f"Slow request: {metric.value}s",
                        },
                    )()
                )

    async def _send_alert(self, alert):
        pass


performance_collector = OptimalPerformanceCollector()


class TestPerformanceCollector:
    """Test performance metric collection."""

    @pytest.fixture
    def collector(self):
        return OptimalPerformanceCollector()

    def test_collector_initialization(self, collector):
        """Test collector initializes correctly."""
        assert collector.buffer_size == 1000
        assert collector.flush_interval == 30
        assert len(collector.metric_buffer) == 0
        assert collector.metrics_collected == 0

    @pytest.mark.asyncio
    async def test_record_metric(self, collector):
        """Test metric recording."""
        # Record a metric
        collector.record_metric(
            name="test_metric",
            value=42.5,
            metric_type=MetricType.COUNTER,
            tags={"service": "test"},
        )

        # Check buffer
        assert len(collector.metric_buffer) == 1
        assert collector.metrics_collected == 1

        metric = collector.metric_buffer[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.COUNTER
        assert metric.tags == {"service": "test"}

    @pytest.mark.asyncio
    async def test_record_request_metric(self, collector):
        """Test request metric recording."""
        collector.record_request_metric(
            endpoint="/api/test", method="GET", duration=0.125, status_code=200
        )

        assert len(collector.metric_buffer) == 3  # duration, count, status

        # Check duration metric
        duration_metric = collector.metric_buffer[0]
        assert duration_metric.name == "request_duration"
        assert duration_metric.value == 0.125
        assert duration_metric.tags["endpoint"] == "/api/test"

    @pytest.mark.asyncio
    async def test_buffer_overflow_triggers_flush(self, collector):
        """Test buffer overflow triggers automatic flush."""
        collector.buffer_size = 5

        with patch.object(collector, "_flush_metrics") as mock_flush:
            # Fill buffer beyond capacity
            for i in range(6):
                collector.record_metric(f"metric_{i}", i, MetricType.COUNTER)

            # Should trigger flush
            mock_flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_metrics(self, collector):
        """Test getting current metrics snapshot."""
        collector.record_metric("test1", 10, MetricType.COUNTER)
        collector.record_metric("test2", 20, MetricType.GAUGE)

        metrics = collector.get_current_metrics()

        assert len(metrics) == 2
        assert metrics[0].name == "test1"
        assert metrics[1].name == "test2"


class TestPerformanceAnalyzer:
    """Test performance analysis."""

    @pytest.fixture
    def analyzer(self):
        return PerformanceAnalyzer()

    @pytest.fixture
    def sample_metrics(self):
        return [
            PerformanceMetric(
                "request_duration",
                0.1,
                MetricType.HISTOGRAM,
                {"endpoint": "/api/users"},
            ),
            PerformanceMetric(
                "request_duration",
                0.2,
                MetricType.HISTOGRAM,
                {"endpoint": "/api/users"},
            ),
            PerformanceMetric(
                "request_duration",
                1.5,
                MetricType.HISTOGRAM,
                {"endpoint": "/api/users"},
            ),
            PerformanceMetric(
                "memory_usage", 85.0, MetricType.GAUGE, {"service": "api"}
            ),
            PerformanceMetric("cpu_usage", 45.2, MetricType.GAUGE, {"service": "api"}),
        ]

    def test_calculate_percentiles(self, analyzer, sample_metrics):
        """Test percentile calculation."""
        percentiles = analyzer.calculate_percentiles(sample_metrics, "request_duration")

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] == 0.2  # median of [0.1, 0.2, 1.5]

    def test_detect_anomalies(self, analyzer, sample_metrics):
        """Test anomaly detection."""
        anomalies = analyzer.detect_anomalies(sample_metrics)

        # Should detect the 1.5s request as anomaly
        assert len(anomalies) >= 1
        assert any(a.value == 1.5 for a in anomalies)

    def test_generate_performance_report(self, analyzer, sample_metrics):
        """Test performance report generation."""
        report = analyzer.generate_performance_report(sample_metrics)

        assert "total_metrics" in report
        assert "by_type" in report
        assert "anomalies" in report
        assert report["total_metrics"] == 5


class TestAlertManager:
    """Test performance alerting."""

    @pytest.fixture
    def alert_manager(self):
        return AlertManager()

    @pytest.mark.asyncio
    async def test_check_thresholds_high_cpu(self, alert_manager):
        """Test high CPU threshold alerting."""
        metrics = [
            PerformanceMetric("cpu_usage", 95.0, MetricType.GAUGE, {"service": "api"})
        ]

        with patch.object(alert_manager, "_send_alert") as mock_send:
            await alert_manager.check_thresholds(metrics)
            mock_send.assert_called_once()

            # Check alert details
            alert = mock_send.call_args[0][0]
            assert alert.severity == "critical"
            assert "cpu_usage" in alert.message

    @pytest.mark.asyncio
    async def test_check_thresholds_slow_requests(self, alert_manager):
        """Test slow request threshold alerting."""
        metrics = [
            PerformanceMetric(
                "request_duration", 2.5, MetricType.HISTOGRAM, {"endpoint": "/api/slow"}
            )
        ]

        with patch.object(alert_manager, "_send_alert") as mock_send:
            await alert_manager.check_thresholds(metrics)
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_alert_for_normal_metrics(self, alert_manager):
        """Test no alerts for normal metrics."""
        metrics = [
            PerformanceMetric("cpu_usage", 45.0, MetricType.GAUGE, {"service": "api"}),
            PerformanceMetric(
                "request_duration", 0.1, MetricType.HISTOGRAM, {"endpoint": "/api/fast"}
            ),
        ]

        with patch.object(alert_manager, "_send_alert") as mock_send:
            await alert_manager.check_thresholds(metrics)
            mock_send.assert_not_called()


class TestGlobalPerformanceCollector:
    """Test global collector instance."""

    def test_global_collector_available(self):
        """Test global collector is available."""
        assert performance_collector is not None
        assert isinstance(performance_collector, OptimalPerformanceCollector)

    def test_global_collector_record_metric(self):
        """Test recording metric through global collector."""
        initial_count = performance_collector.metrics_collected

        performance_collector.record_metric("test_global", 100, MetricType.COUNTER)

        assert performance_collector.metrics_collected == initial_count + 1


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring workflow."""
        collector = OptimalPerformanceCollector()
        analyzer = PerformanceAnalyzer()
        alert_manager = AlertManager()

        # Simulate application metrics
        collector.record_request_metric("/api/users", "GET", 0.05, 200)
        collector.record_request_metric("/api/users", "GET", 0.08, 200)
        collector.record_request_metric("/api/slow", "GET", 2.1, 200)  # Slow request

        collector.record_metric("cpu_usage", 88.5, MetricType.GAUGE, {"service": "api"})
        collector.record_metric(
            "memory_usage", 76.2, MetricType.GAUGE, {"service": "api"}
        )

        # Get metrics for analysis
        metrics = collector.get_current_metrics()

        # Analyze performance
        report = analyzer.generate_performance_report(metrics)
        assert report["total_metrics"] > 0

        # Check for alerts
        with patch.object(alert_manager, "_send_alert") as mock_send:
            await alert_manager.check_thresholds(metrics)
            # Should alert on slow request
            assert mock_send.call_count >= 1

    @pytest.mark.asyncio
    async def test_high_load_performance(self):
        """Test performance under high load."""
        collector = OptimalPerformanceCollector()

        # Simulate high load
        start_time = asyncio.get_event_loop().time()

        for i in range(1000):
            collector.record_metric(f"load_test_{i % 10}", i * 0.1, MetricType.COUNTER)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Should handle 1000 metrics quickly (under 0.1 seconds)
        assert duration < 0.1
        assert collector.metrics_collected >= 1000
