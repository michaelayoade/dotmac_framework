"""
Tests for OpenTelemetry bootstrap functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from dotmac.observability.config import create_default_config, Environment, ExporterType
from dotmac.observability.bootstrap import initialize_otel, shutdown_otel


def test_create_default_config():
    """Test default configuration creation."""
    config = create_default_config(
        service_name="test-service",
        environment=Environment.DEVELOPMENT,
        service_version="1.0.0",
    )
    
    assert config.service_name == "test-service"
    assert config.environment == Environment.DEVELOPMENT
    assert config.service_version == "1.0.0"
    assert config.enable_tracing is True
    assert config.enable_metrics is True
    assert config.trace_sampler_ratio == 1.0  # Development should be 1.0
    
    # Check default exporters for development
    assert len(config.tracing_exporters) == 1
    assert config.tracing_exporters[0].type == ExporterType.CONSOLE


def test_create_production_config():
    """Test production configuration."""
    config = create_default_config(
        service_name="prod-service",
        environment=Environment.PRODUCTION,
        service_version="2.0.0",
    )
    
    assert config.service_name == "prod-service"
    assert config.environment == Environment.PRODUCTION
    assert config.trace_sampler_ratio == 0.1  # Production should be lower
    
    # Production should have OTLP exporters
    assert len(config.tracing_exporters) == 1
    assert config.tracing_exporters[0].type == ExporterType.OTLP_HTTP


def test_config_resource_attributes():
    """Test resource attributes generation."""
    config = create_default_config(
        service_name="test-service",
        environment="development",
        custom_resource_attributes={"team": "platform", "region": "us-east-1"},
    )
    
    attributes = config.get_resource_attributes()
    
    assert attributes["service.name"] == "test-service"
    assert attributes["service.version"] == "1.0.0"
    assert attributes["deployment.environment"] == "development"
    assert attributes["team"] == "platform"
    assert attributes["region"] == "us-east-1"


@pytest.mark.otel
def test_initialize_otel_with_mocking():
    """Test OpenTelemetry initialization with mocked dependencies."""
    config = create_default_config("test-service", Environment.DEVELOPMENT)
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', True), \
         patch('dotmac.observability.bootstrap.TracerProvider') as mock_tracer_provider, \
         patch('dotmac.observability.bootstrap.MeterProvider') as mock_meter_provider, \
         patch('dotmac.observability.bootstrap.trace') as mock_trace, \
         patch('dotmac.observability.bootstrap.metrics') as mock_metrics:
        
        # Setup mocks
        mock_tracer_provider_instance = MagicMock()
        mock_tracer_provider.return_value = mock_tracer_provider_instance
        
        mock_meter_provider_instance = MagicMock()
        mock_meter_provider.return_value = mock_meter_provider_instance
        
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        
        mock_meter = MagicMock()
        mock_metrics.get_meter.return_value = mock_meter
        
        # Initialize OpenTelemetry
        bootstrap = initialize_otel(config)
        
        # Verify bootstrap result
        assert bootstrap.is_initialized
        assert bootstrap.tracer_provider == mock_tracer_provider_instance
        assert bootstrap.meter_provider == mock_meter_provider_instance
        assert bootstrap.tracer == mock_tracer
        assert bootstrap.meter == mock_meter
        assert bootstrap.config == config
        
        # Verify providers were set up
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
        mock_metrics.set_meter_provider.assert_called_once_with(mock_meter_provider_instance)


def test_initialize_otel_without_extras():
    """Test OpenTelemetry initialization without OTEL extras installed."""
    config = create_default_config("test-service", Environment.DEVELOPMENT)
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', False):
        bootstrap = initialize_otel(config)
        
        # Should return bootstrap with None values
        assert not bootstrap.is_initialized
        assert bootstrap.tracer_provider is None
        assert bootstrap.meter_provider is None
        assert bootstrap.tracer is None
        assert bootstrap.meter is None
        assert bootstrap.config == config


def test_shutdown_otel():
    """Test OpenTelemetry shutdown."""
    config = create_default_config("test-service", Environment.DEVELOPMENT)
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', True):
        # Create mock bootstrap
        mock_tracer_provider = MagicMock()
        mock_meter_provider = MagicMock()
        
        bootstrap = MagicMock()
        bootstrap.is_initialized = True
        bootstrap.tracer_provider = mock_tracer_provider
        bootstrap.meter_provider = mock_meter_provider
        
        # Test shutdown
        shutdown_otel(bootstrap)
        
        # Verify shutdown was called
        mock_tracer_provider.shutdown.assert_called_once()
        mock_meter_provider.shutdown.assert_called_once()


def test_shutdown_otel_without_initialization():
    """Test shutdown with uninitialized bootstrap."""
    bootstrap = MagicMock()
    bootstrap.is_initialized = False
    
    # Should not raise exception
    shutdown_otel(bootstrap)


@pytest.mark.otel
def test_get_current_span_context():
    """Test getting current span context."""
    from dotmac.observability.bootstrap import get_current_span_context
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', True), \
         patch('dotmac.observability.bootstrap.trace') as mock_trace:
        
        # Mock span with context
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        
        mock_span_context = MagicMock()
        mock_span_context.trace_id = 12345678901234567890123456789012
        mock_span_context.span_id = 1234567890123456
        mock_span_context.trace_flags = 1
        
        mock_span.get_span_context.return_value = mock_span_context
        mock_trace.get_current_span.return_value = mock_span
        
        context = get_current_span_context()
        
        assert context is not None
        assert "trace_id" in context
        assert "span_id" in context
        assert "trace_flags" in context


def test_get_current_span_context_without_otel():
    """Test getting span context without OTEL available."""
    from dotmac.observability.bootstrap import get_current_span_context
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', False):
        context = get_current_span_context()
        assert context is None


@pytest.mark.otel
def test_create_child_span():
    """Test creating child span."""
    from dotmac.observability.bootstrap import create_child_span
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', True), \
         patch('dotmac.observability.bootstrap.trace') as mock_trace:
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_trace.get_tracer.return_value = mock_tracer
        
        attributes = {"operation": "test"}
        span = create_child_span("test-span", attributes)
        
        assert span == mock_span
        mock_tracer.start_span.assert_called_once_with("test-span", attributes=attributes)


def test_create_child_span_without_otel():
    """Test creating span without OTEL available."""
    from dotmac.observability.bootstrap import create_child_span
    
    with patch('dotmac.observability.bootstrap.OTEL_AVAILABLE', False):
        span = create_child_span("test-span")
        assert span is None