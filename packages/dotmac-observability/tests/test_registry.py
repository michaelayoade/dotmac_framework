"""
Tests for metrics registry functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from dotmac.observability.metrics.registry import (
    MetricsRegistry,
    MetricDefinition,
    MetricType,
    initialize_metrics_registry,
)


def test_metric_definition():
    """Test metric definition creation and validation."""
    definition = MetricDefinition(
        name="test_counter",
        type=MetricType.COUNTER,
        description="A test counter",
        labels=["service", "endpoint"],
    )
    
    assert definition.name == "test_counter"
    assert definition.type == MetricType.COUNTER
    assert definition.description == "A test counter"
    assert definition.labels == ["service", "endpoint"]


def test_metric_definition_histogram_defaults():
    """Test histogram metric definition gets default buckets."""
    definition = MetricDefinition(
        name="test_histogram",
        type=MetricType.HISTOGRAM,
        description="A test histogram",
    )
    
    assert definition.buckets is not None
    assert len(definition.buckets) > 0
    assert definition.labels == []


def test_metrics_registry_initialization():
    """Test metrics registry initialization."""
    registry = MetricsRegistry(
        service_name="test-service",
        enable_prometheus=True,
    )
    
    assert registry.service_name == "test-service"
    assert registry.enable_prometheus is True
    assert len(registry.list_metrics()) == 0


def test_metrics_registry_register_metric():
    """Test registering a metric."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    definition = MetricDefinition(
        name="test_counter",
        type=MetricType.COUNTER,
        description="Test counter",
    )
    
    success = registry.register_metric(definition)
    assert success is True
    
    # Check metric is registered
    metric = registry.get_metric("test_counter")
    assert metric is not None
    assert metric.definition.name == "test_counter"
    
    # Check it appears in list
    assert "test_counter" in registry.list_metrics()


def test_metrics_registry_duplicate_registration():
    """Test registering duplicate metric."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    definition = MetricDefinition(
        name="test_counter",
        type=MetricType.COUNTER,
        description="Test counter",
    )
    
    # First registration should succeed
    success1 = registry.register_metric(definition)
    assert success1 is True
    
    # Second registration should fail
    success2 = registry.register_metric(definition)
    assert success2 is False


def test_metrics_registry_record_metric():
    """Test recording metric values."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    # Register metric
    definition = MetricDefinition(
        name="test_counter",
        type=MetricType.COUNTER,
        description="Test counter",
    )
    registry.register_metric(definition)
    
    # Record value - should not raise exception
    registry.record_metric("test_counter", 1)
    registry.increment_counter("test_counter", 5)


def test_metrics_registry_record_unknown_metric():
    """Test recording value for unknown metric."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    # Should not raise exception, but log warning
    registry.record_metric("unknown_metric", 1)


def test_metrics_registry_get_metrics_info():
    """Test getting metrics information."""
    registry = MetricsRegistry("test-service", enable_prometheus=False)
    
    # Register a few metrics
    counter_def = MetricDefinition(
        name="test_counter",
        type=MetricType.COUNTER,
        description="Test counter",
        labels=["service"],
    )
    registry.register_metric(counter_def)
    
    gauge_def = MetricDefinition(
        name="test_gauge",
        type=MetricType.GAUGE,
        description="Test gauge",
        unit="bytes",
    )
    registry.register_metric(gauge_def)
    
    info = registry.get_metrics_info()
    
    assert len(info) == 2
    assert "test_counter" in info
    assert "test_gauge" in info
    
    counter_info = info["test_counter"]
    assert counter_info["type"] == "counter"
    assert counter_info["description"] == "Test counter"
    assert counter_info["labels"] == ["service"]
    
    gauge_info = info["test_gauge"]
    assert gauge_info["type"] == "gauge"
    assert gauge_info["unit"] == "bytes"


@pytest.mark.prometheus
def test_metrics_registry_with_prometheus():
    """Test metrics registry with Prometheus support."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', True), \
         patch('dotmac.observability.metrics.registry.CollectorRegistry') as mock_registry_class, \
         patch('dotmac.observability.metrics.registry.PrometheusCounter') as mock_counter_class:
        
        mock_prometheus_registry = MagicMock()
        mock_registry_class.return_value = mock_prometheus_registry
        
        mock_prometheus_counter = MagicMock()
        mock_counter_class.return_value = mock_prometheus_counter
        
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        # Register counter metric
        definition = MetricDefinition(
            name="test_counter",
            type=MetricType.COUNTER,
            description="Test counter",
        )
        
        success = registry.register_metric(definition)
        assert success is True
        
        # Verify Prometheus counter was created
        mock_counter_class.assert_called_once()
        
        # Test getting Prometheus registry
        prom_registry = registry.get_prometheus_registry()
        assert prom_registry == mock_prometheus_registry


def test_metrics_registry_without_prometheus():
    """Test metrics registry without Prometheus."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        registry = MetricsRegistry("test-service", enable_prometheus=True)
        
        # Should disable Prometheus internally
        assert registry.enable_prometheus is False
        assert registry.get_prometheus_registry() is None
        assert registry.get_prometheus_metrics() == ""


def test_initialize_metrics_registry():
    """Test initialize_metrics_registry function."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        registry = initialize_metrics_registry("test-service", enable_prometheus=False)
        
        assert isinstance(registry, MetricsRegistry)
        assert registry.service_name == "test-service"
        
        # Should have default metrics registered
        metrics = registry.list_metrics()
        assert len(metrics) > 0
        assert "http_requests_total" in metrics
        assert "http_request_duration_seconds" in metrics


def test_initialize_metrics_registry_with_prometheus_warning():
    """Test initialize function shows warning when Prometheus not available."""
    with patch('dotmac.observability.metrics.registry.PROMETHEUS_AVAILABLE', False):
        with pytest.warns(UserWarning, match="prometheus-client not installed"):
            registry = initialize_metrics_registry("test-service", enable_prometheus=True)
            assert registry.enable_prometheus is False


@pytest.mark.otel
def test_metrics_registry_set_otel_meter():
    """Test setting OpenTelemetry meter."""
    with patch('dotmac.observability.metrics.registry.OTEL_AVAILABLE', True):
        registry = MetricsRegistry("test-service", enable_prometheus=False)
        
        # Register a metric first
        definition = MetricDefinition(
            name="test_counter",
            type=MetricType.COUNTER,
            description="Test counter",
        )
        registry.register_metric(definition)
        
        # Mock OTEL meter
        mock_meter = MagicMock()
        mock_otel_counter = MagicMock()
        mock_meter.create_counter.return_value = mock_otel_counter
        
        # Set meter
        registry.set_otel_meter(mock_meter)
        
        # Verify OTEL instrument was created
        mock_meter.create_counter.assert_called_once()
        
        # Verify metric instrument has OTEL instrument
        metric = registry.get_metric("test_counter")
        assert metric.otel_instrument == mock_otel_counter


def test_metric_instrument_record():
    """Test metric instrument recording."""
    definition = MetricDefinition(
        name="test_counter",
        type=MetricType.COUNTER,
        description="Test counter",
        labels=["service"],
    )
    
    # Create mock instruments
    mock_otel_instrument = MagicMock()
    mock_prometheus_instrument = MagicMock()
    
    from dotmac.observability.metrics.registry import MetricInstrument
    
    instrument = MetricInstrument(
        definition=definition,
        otel_instrument=mock_otel_instrument,
        prometheus_instrument=mock_prometheus_instrument,
    )
    
    # Record value
    labels = {"service": "test-service"}
    instrument.record(5, labels)
    
    # Verify OTEL instrument was called
    mock_otel_instrument.add.assert_called_once_with(5, labels)
    
    # Verify Prometheus instrument was called
    mock_prometheus_instrument.labels.assert_called_once_with("test-service")
    mock_prometheus_instrument.labels.return_value.inc.assert_called_once_with(5)