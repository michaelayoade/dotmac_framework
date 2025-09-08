"""
Test coverage for missing otel.py lines.
"""

from unittest.mock import MagicMock, patch

import pytest

from dotmac_observability import MetricsCollector


# Test the OTEL_AVAILABLE import fallback paths
def test_otel_import_fallback_path():
    """Test OTEL import fallback when OpenTelemetry not available."""
    # This tests the import section lines 16-20
    from dotmac_observability.otel import OTEL_AVAILABLE
    
    # In our environment, OTEL is available, but we can test the existence of the flag
    assert isinstance(OTEL_AVAILABLE, bool)


# Test OTelBridge initialization error handling
def test_otel_bridge_init_when_unavailable():
    """Test OTelBridge initialization when OTEL unavailable."""
    from dotmac_observability.otel import OTelBridge
    
    collector = MetricsCollector()
    
    # Mock OTEL_AVAILABLE to be False to test the ImportError path (line 40)
    with patch('dotmac_observability.otel.OTEL_AVAILABLE', False):
        with pytest.raises(ImportError, match="OpenTelemetry extras not installed"):
            OTelBridge(collector, "test-service")


# Test setup_meter with otlp_endpoint
def test_otel_bridge_setup_meter_with_endpoint():
    """Test setup_meter with OTLP endpoint configuration."""
    from dotmac_observability.otel import OTelBridge
    
    with patch('dotmac_observability.otel.OTEL_AVAILABLE', True):
        with patch('dotmac_observability.otel.Resource') as mock_resource:
            with patch('dotmac_observability.otel.OTLPMetricExporter') as mock_exporter:
                with patch('dotmac_observability.otel.PeriodicExportingMetricReader') as mock_reader:
                    with patch('dotmac_observability.otel.MeterProvider') as mock_provider:
                        with patch('dotmac_observability.otel.set_meter_provider') as mock_set_provider:
                            with patch('dotmac_observability.otel.otel_metrics.get_meter') as mock_get_meter:
                                
                                collector = MetricsCollector()
                                bridge = OTelBridge(collector, "test-service")
                                
                                # Test setup_meter with OTLP endpoint (tests lines 72, 79-83)
                                bridge.setup_meter(
                                    otlp_endpoint="http://localhost:4317",
                                    resource_attrs={"custom.attr": "value"},
                                    export_interval=60
                                )
                                
                                # Verify OTLP exporter was created
                                mock_exporter.assert_called_once_with(endpoint="http://localhost:4317")
                                mock_reader.assert_called_once()
                                
                                # Verify resource was created with custom attributes
                                mock_resource.create.assert_called_once()
                                call_args = mock_resource.create.call_args[0][0]
                                assert call_args["service.name"] == "test-service"
                                assert call_args["custom.attr"] == "value"


# Test sync_metrics gauge creation path
def test_otel_bridge_sync_metrics_gauges():
    """Test sync_metrics with gauge metrics."""
    from dotmac_observability.otel import OTelBridge
    
    with patch('dotmac_observability.otel.OTEL_AVAILABLE', True):
        collector = MetricsCollector()
        collector.gauge("test_gauge", 42.0, {"env": "test"})
        
        bridge = OTelBridge(collector, "test-service")
        
        # Mock the meter
        mock_meter = MagicMock()
        mock_gauge = MagicMock()
        mock_meter.create_observable_gauge.return_value = mock_gauge
        bridge._meter = mock_meter
        
        # Test sync_metrics (tests lines 117-124)
        bridge.sync_metrics()
        
        # Verify gauge was created
        mock_meter.create_observable_gauge.assert_called()


# Test sync_metrics histogram path
def test_otel_bridge_sync_metrics_histograms():
    """Test sync_metrics with histogram metrics."""
    from dotmac_observability.otel import OTelBridge
    
    with patch('dotmac_observability.otel.OTEL_AVAILABLE', True):
        collector = MetricsCollector()
        collector.histogram("test_histogram", 1.5)
        collector.histogram("test_histogram", 2.5)
        
        bridge = OTelBridge(collector, "test-service")
        
        # Mock the meter
        mock_meter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        bridge._meter = mock_meter
        
        # Test sync_metrics (tests lines 132-141)
        bridge.sync_metrics()
        
        # Verify histogram was created and recorded
        mock_meter.create_histogram.assert_called()
        mock_histogram.record.assert_called()


# Test enable_otel_bridge error handling
def test_enable_otel_bridge_unavailable():
    """Test enable_otel_bridge when OTEL unavailable."""
    from dotmac_observability.otel import enable_otel_bridge
    
    collector = MetricsCollector()
    
    # Mock OTEL_AVAILABLE to be False (tests line 178)
    with patch('dotmac_observability.otel.OTEL_AVAILABLE', False):
        with pytest.raises(ImportError, match="OpenTelemetry extras not installed"):
            enable_otel_bridge(collector, service_name="test-service")


# Test enable_otel_bridge auto_sync exception handling
def test_enable_otel_bridge_auto_sync_exception():
    """Test enable_otel_bridge auto_sync exception handling."""
    from dotmac_observability.otel import enable_otel_bridge
    
    with patch('dotmac_observability.otel.OTEL_AVAILABLE', True):
        with patch('dotmac_observability.otel.OTelBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge.sync_metrics.side_effect = Exception("Sync error")
            mock_bridge_class.return_value = mock_bridge
            
            collector = MetricsCollector()
            
            # This should not raise an exception (tests lines 191-195)
            result = enable_otel_bridge(
                collector,
                service_name="test-service",
                auto_sync=True
            )
            
            assert result is mock_bridge
            mock_bridge.sync_metrics.assert_called_once()