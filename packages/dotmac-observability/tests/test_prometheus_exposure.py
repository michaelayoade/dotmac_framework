"""
Tests for Prometheus metrics exposure.
"""

import pytest
from unittest.mock import patch, MagicMock

from dotmac.observability.metrics.registry import (
    MetricsRegistry,
    MetricDefinition,
    MetricType,
    initialize_metrics_registry,
)


@pytest.mark.prometheus
def test_prometheus_registry_creation():
    """Test Prometheus registry creation."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry') as mock_registry_class:
        
        mock_prometheus_registry = MagicMock()
        mock_registry_class.return_value = mock_prometheus_registry
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        assert registry.enable_prometheus is True
        assert registry.get_prometheus_registry() == mock_prometheus_registry
        mock_registry_class.assert_called_once()


@pytest.mark.prometheus
def test_prometheus_counter_registration():
    """Test registering Prometheus counter."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.PrometheusCounter') as mock_counter_class:
        
        mock_counter = MagicMock()
        mock_counter_class.return_value = mock_counter
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        definition = MetricDefinition(
            name="test_counter",
            type=MetricType.COUNTER,
            description="Test counter metric",
            labels=["service", "method"],
        )
        
        success = registry.register_metric(definition)
        assert success is True
        
        # Verify Prometheus counter was created with correct parameters
        mock_counter_class.assert_called_once_with(
            name="test_counter",
            documentation="Test counter metric",
            labelnames=["service", "method"],
            registry=registry._prometheus_registry,
        )


@pytest.mark.prometheus
def test_prometheus_gauge_registration():
    """Test registering Prometheus gauge."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.PrometheusGauge') as mock_gauge_class:
        
        mock_gauge = MagicMock()
        mock_gauge_class.return_value = mock_gauge
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        definition = MetricDefinition(
            name="test_gauge",
            type=MetricType.GAUGE,
            description="Test gauge metric",
        )
        
        success = registry.register_metric(definition)
        assert success is True
        
        mock_gauge_class.assert_called_once_with(
            name="test_gauge",
            documentation="Test gauge metric",
            labelnames=[],
            registry=registry._prometheus_registry,
        )


@pytest.mark.prometheus
def test_prometheus_histogram_registration():
    """Test registering Prometheus histogram."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.PrometheusHistogram') as mock_histogram_class:
        
        mock_histogram = MagicMock()
        mock_histogram_class.return_value = mock_histogram
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        definition = MetricDefinition(
            name="test_histogram",
            type=MetricType.HISTOGRAM,
            description="Test histogram metric",
            buckets=(0.1, 0.5, 1.0, 5.0),
        )
        
        success = registry.register_metric(definition)
        assert success is True
        
        mock_histogram_class.assert_called_once_with(
            name="test_histogram",
            documentation="Test histogram metric",
            labelnames=[],
            registry=registry._prometheus_registry,
            buckets=(0.1, 0.5, 1.0, 5.0),
        )


@pytest.mark.prometheus
def test_prometheus_up_down_counter_as_gauge():
    """Test that up-down counter becomes gauge in Prometheus."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.PrometheusGauge') as mock_gauge_class:
        
        mock_gauge = MagicMock()
        mock_gauge_class.return_value = mock_gauge
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        definition = MetricDefinition(
            name="test_up_down",
            type=MetricType.UP_DOWN_COUNTER,
            description="Test up-down counter",
        )
        
        success = registry.register_metric(definition)
        assert success is True
        
        # Should create Gauge instead of Counter for up-down counter
        mock_gauge_class.assert_called_once()


@pytest.mark.prometheus
def test_prometheus_metrics_generation():
    """Test generating Prometheus metrics text."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.generate_latest') as mock_generate:
        
        mock_generate.return_value = b"# HELP test_counter Test counter\n# TYPE test_counter counter\ntest_counter 5\n"
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        metrics_text = registry.get_prometheus_metrics()
        
        assert "test_counter" in metrics_text
        assert "counter" in metrics_text
        mock_generate.assert_called_once_with(registry._prometheus_registry)


@pytest.mark.prometheus
def test_prometheus_metrics_generation_error():
    """Test handling error during metrics generation."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.generate_latest') as mock_generate:
        
        mock_generate.side_effect = Exception("Prometheus error")
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        metrics_text = registry.get_prometheus_metrics()
        assert metrics_text == ""


@pytest.mark.prometheus
def test_prometheus_metric_recording():
    """Test recording values to Prometheus metrics."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.PrometheusCounter') as mock_counter_class:
        
        # Setup mock counter with labels
        mock_counter = MagicMock()
        mock_labeled_counter = MagicMock()
        mock_counter.labels.return_value = mock_labeled_counter
        mock_counter_class.return_value = mock_counter
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        # Register counter with labels
        definition = MetricDefinition(
            name="http_requests",
            type=MetricType.COUNTER,
            description="HTTP requests",
            labels=["method", "status"],
        )
        registry.register_metric(definition)
        
        # Record value with labels
        labels = {"method": "GET", "status": "200"}
        registry.record_metric("http_requests", 1, labels)
        
        # Verify Prometheus counter was called correctly
        mock_counter.labels.assert_called_once_with("GET", "200")
        mock_labeled_counter.inc.assert_called_once_with(1)


@pytest.mark.prometheus
def test_prometheus_metric_recording_no_labels():
    """Test recording values to Prometheus metrics without labels."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'), \
         patch('dotmac.observability.metrics.registry.PrometheusCounter') as mock_counter_class:
        
        mock_counter = MagicMock()
        mock_counter_class.return_value = mock_counter
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        # Register counter without labels
        definition = MetricDefinition(
            name="simple_counter",
            type=MetricType.COUNTER,
            description="Simple counter",
        )
        registry.register_metric(definition)
        
        # Record value
        registry.record_metric("simple_counter", 3)
        
        # Verify Prometheus counter increment was called
        mock_counter.inc.assert_called_once_with(3)


def test_prometheus_disabled_returns_empty():
    """Test that disabled Prometheus returns empty metrics."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    assert registry.get_prometheus_registry() is None
    assert registry.get_prometheus_metrics() == ""


@pytest.mark.prometheus  
def test_initialize_metrics_registry_with_prometheus():
    """Test initializing metrics registry with Prometheus enabled."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'):
        
        registry = initialize_metrics_registry(
            service_name="test-service",
            enable_prometheus=True,
        )
        
        assert registry.enable_prometheus is True
        assert registry.get_prometheus_registry() is not None
        
        # Should have default metrics that work with Prometheus
        metrics = registry.list_metrics()
        assert "http_requests_total" in metrics
        assert "http_request_duration_seconds" in metrics


@pytest.mark.prometheus
def test_business_metrics_prometheus_integration():
    """Test business metrics integration with Prometheus."""
    from dotmac.observability.metrics.business import (
        TenantMetrics,
        BusinessMetricSpec,
        BusinessMetricType,
        TenantContext,
    )
    
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry'):
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        tenant_metrics = TenantMetrics("test-service", registry)
        
        # Register business metric
        spec = BusinessMetricSpec(
            name="login_success_rate",
            metric_type=BusinessMetricType.SUCCESS_RATE,
            description="Login success rate",
            slo_target=0.99,
            alert_threshold=0.95,
        )
        
        success = tenant_metrics.register_business_metric(spec)
        assert success is True
        
        # Record business metric
        context = TenantContext(tenant_id="tenant-123", service="auth")
        tenant_metrics.record_business_metric("login_success_rate", 1, context)
        
        # Should be able to generate Prometheus metrics
        # (This would contain the underlying counter metrics)
        registry_metrics = registry.list_metrics()
        assert "login_success_rate_total" in registry_metrics
        assert "login_success_rate_success" in registry_metrics