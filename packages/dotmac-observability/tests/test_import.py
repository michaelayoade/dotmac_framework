"""
Basic import and smoke tests.
"""


def test_basic_import():
    """Test that basic modules can be imported."""
    from dotmac_observability import (
        HealthMonitor,
        HealthStatus,
        MetricsCollector,
        MetricType,
        get_collector,
    )

    assert MetricsCollector is not None
    assert get_collector is not None
    assert HealthMonitor is not None
    assert MetricType is not None
    assert HealthStatus is not None


def test_optional_imports():
    """Test that optional imports fail gracefully."""
    from dotmac_observability import MIDDLEWARE_AVAILABLE, OTEL_AVAILABLE

    # These should be boolean values
    assert isinstance(MIDDLEWARE_AVAILABLE, bool)
    assert isinstance(OTEL_AVAILABLE, bool)


def test_version():
    """Test that version is available."""
    from dotmac_observability import __version__

    assert __version__ == "1.0.0"


def test_basic_functionality():
    """Basic smoke test of core functionality."""
    from dotmac_observability import HealthMonitor, get_collector

    # Test metrics
    collector = get_collector()
    collector.counter("smoke_test")

    summary = collector.get_summary()
    assert "smoke_test" in summary["counters"]

    # Test health monitor
    monitor = HealthMonitor()
    assert monitor.get_last_results() is None
