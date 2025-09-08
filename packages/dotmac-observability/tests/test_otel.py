"""
Test OpenTelemetry integration.
"""

from unittest.mock import MagicMock, patch

import pytest

from dotmac_observability import OTEL_AVAILABLE, MetricsCollector


class TestOtelAvailability:
    """Test OpenTelemetry availability detection."""

    def test_otel_imports(self):
        """Test OpenTelemetry imports when available."""
        # Since OTEL is available in our test environment
        from dotmac_observability import enable_otel_bridge

        assert enable_otel_bridge is not None

    def test_otel_available_flag(self):
        """Test OTEL_AVAILABLE flag reflects actual availability."""
        assert isinstance(OTEL_AVAILABLE, bool)
        # In our test environment, OTEL is available
        assert OTEL_AVAILABLE is True


# Test OpenTelemetry integration since it's available
if OTEL_AVAILABLE:
    from dotmac_observability.otel import OTelBridge, enable_otel_bridge

    class TestOtelBridge:
        """Test OpenTelemetry bridge functionality."""

        @patch("dotmac_observability.otel.otel_metrics.get_meter")
        def test_otel_bridge_initialization(self, mock_get_meter):
            """Test OTelBridge initialization."""
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter

            collector = MetricsCollector()
            bridge = OTelBridge(collector, "test-service")

            assert bridge.collector is collector
            assert bridge.service_name == "test-service"

        @patch("dotmac_observability.otel.otel_metrics.get_meter")
        @patch("dotmac_observability.otel.set_meter_provider")
        def test_otel_bridge_setup_meter(self, mock_set_provider, mock_get_meter):
            """Test OTelBridge setup_meter method."""
            mock_meter = MagicMock()
            mock_get_meter.return_value = mock_meter

            collector = MetricsCollector()
            bridge = OTelBridge(collector, "test-service")
            
            bridge.setup_meter()
            
            # Verify meter was set up
            mock_set_provider.assert_called_once()
            mock_get_meter.assert_called_once()

        @patch("dotmac_observability.otel.otel_metrics.get_meter")
        def test_otel_bridge_sync_metrics(self, mock_get_meter):
            """Test OTelBridge sync_metrics method."""
            mock_meter = MagicMock()
            mock_counter = MagicMock()
            mock_meter.create_counter.return_value = mock_counter
            mock_get_meter.return_value = mock_meter

            collector = MetricsCollector()
            collector.counter("test_counter", 5.0)

            bridge = OTelBridge(collector, "test-service")
            bridge._meter = mock_meter
            
            bridge.sync_metrics()
            
            # Should have created a counter
            mock_meter.create_counter.assert_called()

        def test_enable_otel_bridge(self):
            """Test enable_otel_bridge function."""
            collector = MetricsCollector()

            # Should not raise an exception since OTEL is available
            bridge = enable_otel_bridge(
                collector,
                service_name="test-app",
                auto_sync=False  # Disable auto_sync to avoid background operations
            )

            assert bridge is not None
            assert isinstance(bridge, OTelBridge)
            assert bridge.service_name == "test-app"

        def test_otel_bridge_error_handling(self):
            """Test OTelBridge error handling when meter not set up."""
            collector = MetricsCollector()
            bridge = OTelBridge(collector, "test-service")
            
            # Should raise error if meter not set up
            with pytest.raises(RuntimeError, match="Meter not set up"):
                bridge.sync_metrics()

else:
    # Test behavior when OpenTelemetry is unavailable
    class TestOtelUnavailable:
        """Test behavior when OpenTelemetry is unavailable."""

        def test_otel_unavailable(self):
            """Test that OTEL gracefully handles unavailability."""
            assert OTEL_AVAILABLE is False

        def test_enable_otel_bridge_unavailable(self):
            """Test enable_otel_bridge when unavailable."""
            from dotmac_observability import enable_otel_bridge
            
            collector = MetricsCollector()
            
            with pytest.raises(ImportError, match="OpenTelemetry extras not installed"):
                enable_otel_bridge(collector, service_name="test")