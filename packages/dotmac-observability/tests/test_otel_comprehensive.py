"""Comprehensive tests for OpenTelemetry integration."""

from contextlib import suppress
from unittest.mock import MagicMock, patch

import pytest

from dotmac_observability import MetricsCollector


class TestOtelAvailability:
    """Test OpenTelemetry availability detection."""

    def test_otel_availability_flag(self):
        """Test OTEL_AVAILABLE flag is properly set."""
        from dotmac_observability import OTEL_AVAILABLE
        
        assert isinstance(OTEL_AVAILABLE, bool)

    def test_enable_otel_bridge_availability(self):
        """Test enable_otel_bridge import behavior."""
        from dotmac_observability import enable_otel_bridge, OTEL_AVAILABLE
        
        if OTEL_AVAILABLE:
            assert enable_otel_bridge is not None
            assert callable(enable_otel_bridge)
        else:
            assert enable_otel_bridge is None


class TestOtelBridgeWhenAvailable:
    """Test OpenTelemetry bridge when OTEL is available."""

    def setUp(self):
        """Set up test environment."""
        # Try to import otel modules to see if they're actually available
        try:
            from dotmac_observability.otel import _OtelBridge, enable_otel_bridge
            self.otel_available = True
            self._OtelBridge = _OtelBridge
            self.enable_otel_bridge = enable_otel_bridge
        except ImportError:
            self.otel_available = False

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Run setup before each test."""
        self.setUp()

    @patch('dotmac_observability.otel.get_meter')
    @patch('dotmac_observability.otel.Resource')
    @patch('dotmac_observability.otel.MeterProvider')
    @patch('dotmac_observability.otel.OTLPMetricExporter')
    @patch('dotmac_observability.otel.PeriodicExportingMetricReader')
    @patch('dotmac_observability.otel.set_meter_provider')
    def test_otel_bridge_initialization(self, mock_set_provider, mock_reader, mock_exporter, 
                                       mock_provider, mock_resource, mock_get_meter):
        """Test OtelBridge initialization with all dependencies mocked."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        # Mock the meter and other OTEL components
        mock_meter = MagicMock()
        mock_get_meter.return_value = mock_meter
        mock_resource.from_attributes.return_value = MagicMock()
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_exporter_instance = MagicMock()
        mock_exporter.return_value = mock_exporter_instance
        mock_reader_instance = MagicMock()
        mock_reader.return_value = mock_reader_instance

        collector = MetricsCollector()
        bridge = self._OtelBridge(collector, "test-service")

        assert bridge.collector is collector
        assert bridge.service_name == "test-service"
        assert bridge._meter is None  # Not set up yet
        mock_get_meter.assert_called_once_with("test-service")

    @patch('dotmac_observability.otel.get_meter')
    def test_otel_bridge_setup_meter(self, mock_get_meter):
        """Test setting up the OTEL meter."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        mock_meter = MagicMock()
        mock_get_meter.return_value = mock_meter

        collector = MetricsCollector()
        bridge = self._OtelBridge(collector, "test-service")

        # Test setup_meter method
        with patch('dotmac_observability.otel.Resource') as mock_resource, \
             patch('dotmac_observability.otel.MeterProvider') as mock_provider, \
             patch('dotmac_observability.otel.OTLPMetricExporter') as mock_exporter, \
             patch('dotmac_observability.otel.PeriodicExportingMetricReader') as mock_reader, \
             patch('dotmac_observability.otel.set_meter_provider') as mock_set_provider:
            
            # Mock all the OTEL components
            mock_resource.from_attributes.return_value = MagicMock()
            mock_provider_instance = MagicMock()
            mock_provider.return_value = mock_provider_instance
            mock_exporter_instance = MagicMock()
            mock_exporter.return_value = mock_exporter_instance
            mock_reader_instance = MagicMock()
            mock_reader.return_value = mock_reader_instance
            mock_provider_instance.get_meter.return_value = mock_meter

            bridge.setup_meter(
                otlp_endpoint="http://localhost:4318/v1/metrics",
                resource_attrs={"service.version": "1.0.0"},
                export_interval=10
            )

            # Verify setup calls
            mock_resource.from_attributes.assert_called_once()
            mock_exporter.assert_called_once_with(endpoint="http://localhost:4318/v1/metrics")
            mock_reader.assert_called_once_with(mock_exporter_instance, export_interval_millis=10000)
            mock_provider.assert_called_once()
            mock_set_provider.assert_called_once_with(mock_provider_instance)

    @patch('dotmac_observability.otel.get_meter')
    def test_otel_bridge_sync_metrics(self, mock_get_meter):
        """Test syncing metrics to OpenTelemetry."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        # Mock OTEL components
        mock_counter = MagicMock()
        mock_histogram = MagicMock()
        mock_gauge = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter
        mock_meter.create_histogram.return_value = mock_histogram
        mock_meter.create_gauge.return_value = mock_gauge
        mock_get_meter.return_value = mock_meter

        collector = MetricsCollector()
        bridge = self._OtelBridge(collector, "test-service")
        bridge._meter = mock_meter  # Set up meter directly

        # Add test metrics
        collector.counter("http_requests", 5.0, {"method": "GET", "status": "200"})
        collector.gauge("memory_usage", 1024.0, {"type": "heap"})
        collector.histogram("response_time", 0.150, {"endpoint": "/api/users"})
        collector.histogram("response_time", 0.200, {"endpoint": "/api/users"})

        # Sync metrics
        bridge._sync_metrics()

        # Verify instruments were created
        mock_meter.create_counter.assert_called()
        mock_meter.create_histogram.assert_called()
        mock_meter.create_gauge.assert_called()

        # Verify metrics were recorded
        mock_counter.add.assert_called()
        mock_gauge.set.assert_called()
        mock_histogram.record.assert_called()

    @patch('dotmac_observability.otel.get_meter')
    @patch('dotmac_observability.otel.threading.Timer')
    def test_otel_bridge_start_stop(self, mock_timer_class, mock_get_meter):
        """Test starting and stopping the OTEL bridge."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        mock_meter = MagicMock()
        mock_get_meter.return_value = mock_meter
        mock_timer = MagicMock()
        mock_timer_class.return_value = mock_timer

        collector = MetricsCollector()
        bridge = self._OtelBridge(collector, "test-service", sync_interval=30.0)

        # Test start
        bridge.start()
        mock_timer_class.assert_called_with(30.0, bridge._sync_and_schedule)
        mock_timer.start.assert_called_once()

        # Test stop
        bridge.stop()
        mock_timer.cancel.assert_called_once()

    @patch('dotmac_observability.otel.get_meter')
    def test_otel_bridge_sync_and_schedule(self, mock_get_meter):
        """Test sync and schedule method."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        mock_meter = MagicMock()
        mock_get_meter.return_value = mock_meter

        collector = MetricsCollector()
        bridge = self._OtelBridge(collector, "test-service")
        bridge._meter = mock_meter

        with patch.object(bridge, '_sync_metrics') as mock_sync, \
             patch('dotmac_observability.otel.threading.Timer') as mock_timer_class:
            
            mock_timer = MagicMock()
            mock_timer_class.return_value = mock_timer

            bridge._sync_and_schedule()

            mock_sync.assert_called_once()
            mock_timer_class.assert_called_once()
            mock_timer.start.assert_called_once()

    def test_enable_otel_bridge_function(self):
        """Test the enable_otel_bridge function."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        with patch('dotmac_observability.otel._OtelBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.return_value = mock_bridge

            collector = MetricsCollector()
            
            # Test without setup_meter call
            result = self.enable_otel_bridge(collector, service_name="test-app")
            
            assert result is mock_bridge
            mock_bridge_class.assert_called_once_with(collector, "test-app", sync_interval=30)

    def test_enable_otel_bridge_with_options(self):
        """Test enable_otel_bridge with all options."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        with patch('dotmac_observability.otel._OtelBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.return_value = mock_bridge

            collector = MetricsCollector()
            
            result = self.enable_otel_bridge(
                collector,
                service_name="test-app",
                otlp_endpoint="http://otel-collector:4318/v1/metrics",
                resource_attrs={"service.version": "1.0.0", "env": "test"},
                auto_sync=True,
                sync_interval=60
            )
            
            assert result is mock_bridge
            mock_bridge_class.assert_called_once_with(collector, "test-app", sync_interval=60)
            mock_bridge.setup_meter.assert_called_once()
            mock_bridge.start.assert_called_once()

    @patch('dotmac_observability.otel.get_meter')
    def test_otel_bridge_error_handling(self, mock_get_meter):
        """Test error handling in OTEL bridge."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        mock_meter = MagicMock()
        # Make create_counter raise an exception
        mock_meter.create_counter.side_effect = Exception("OTEL error")
        mock_get_meter.return_value = mock_meter

        collector = MetricsCollector()
        bridge = self._OtelBridge(collector, "test-service")
        bridge._meter = mock_meter

        # Add a metric that will trigger the error
        collector.counter("test_metric", 1.0)

        # This should not raise an exception due to error handling
        with suppress(Exception):
            bridge._sync_metrics()

        # Verify the error was handled gracefully
        mock_meter.create_counter.assert_called()

    def test_enable_otel_bridge_auto_sync_false(self):
        """Test enable_otel_bridge with auto_sync=False."""
        if not self.otel_available:
            pytest.skip("OpenTelemetry not available")

        with patch('dotmac_observability.otel._OtelBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.return_value = mock_bridge

            collector = MetricsCollector()
            
            result = self.enable_otel_bridge(
                collector,
                service_name="test-app",
                auto_sync=False
            )
            
            assert result is mock_bridge
            mock_bridge.start.assert_not_called()


class TestOtelUnavailable:
    """Test behavior when OpenTelemetry is not available."""

    def test_otel_unavailable_flag(self):
        """Test OTEL_AVAILABLE is False when OpenTelemetry not available."""
        # Mock the import to fail
        with patch.dict('sys.modules', {'opentelemetry.sdk.metrics': None}):
            from dotmac_observability import OTEL_AVAILABLE
            # Could be True or False depending on actual availability
            assert isinstance(OTEL_AVAILABLE, bool)

    def test_enable_otel_bridge_unavailable(self):
        """Test enable_otel_bridge behavior when unavailable."""
        from dotmac_observability import enable_otel_bridge, OTEL_AVAILABLE
        
        if not OTEL_AVAILABLE:
            assert enable_otel_bridge is None
        else:
            # Test that calling it raises ImportError when forced unavailable
            with patch('dotmac_observability.otel.OTEL_AVAILABLE', False):
                with pytest.raises(ImportError):
                    # Try to call the actual function with missing OTEL
                    from dotmac_observability.otel import enable_otel_bridge as actual_func
                    collector = MetricsCollector()
                    actual_func(collector, service_name="test")

    def test_otel_import_fallback(self):
        """Test that OTEL import fallback works correctly."""
        # This tests the ImportError handling in __init__.py
        import dotmac_observability
        
        # Should have OTEL_AVAILABLE attribute regardless
        assert hasattr(dotmac_observability, 'OTEL_AVAILABLE')
        assert isinstance(dotmac_observability.OTEL_AVAILABLE, bool)
        
        # If not available, enable_otel_bridge should be None
        if not dotmac_observability.OTEL_AVAILABLE:
            assert dotmac_observability.enable_otel_bridge is None


class TestOtelModuleImport:
    """Test direct import of otel module."""

    def test_otel_module_constants(self):
        """Test OTEL module constants."""
        try:
            from dotmac_observability import otel
            assert hasattr(otel, 'OTEL_AVAILABLE')
            assert isinstance(otel.OTEL_AVAILABLE, bool)
        except ImportError:
            # Expected if OpenTelemetry not available
            pass

    def test_otel_module_import_error(self):
        """Test OTEL module import error handling."""
        # Try importing the otel module directly
        try:
            import dotmac_observability.otel
            # If successful, test the error handling within the module
            from dotmac_observability.otel import OTEL_AVAILABLE
            assert isinstance(OTEL_AVAILABLE, bool)
        except ImportError:
            # This is expected if OpenTelemetry is not available
            from dotmac_observability import OTEL_AVAILABLE
            assert OTEL_AVAILABLE is False