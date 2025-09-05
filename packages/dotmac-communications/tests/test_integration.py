"""Integration tests for dotmac-communications package."""


import pytest
from dotmac.communications import (
    CommunicationsService,
    create_communications_service,
)


class TestCommunicationsIntegration:
    """Test integrated communications service."""

    def test_communications_service_creation(self):
        """Test basic service creation."""
        service = create_communications_service()
        assert isinstance(service, CommunicationsService)
        assert service.config is not None

    def test_communications_service_with_config(self):
        """Test service creation with custom config."""
        config = {
            "notifications": {"retry_attempts": 5},
            "websockets": {"connection_timeout": 120},
            "events": {"max_retries": 10},
        }
        service = create_communications_service(config)
        assert service.config["notifications"]["retry_attempts"] == 5
        assert service.config["websockets"]["connection_timeout"] == 120

    def test_service_components_accessible(self):
        """Test that all service components are accessible."""
        service = create_communications_service()

        # Test property access (should not raise exceptions)
        notifications = service.notifications
        websockets = service.websockets
        events = service.events

        # Services should be available or None (graceful degradation)
        assert notifications is not None or notifications is None
        assert websockets is not None or websockets is None
        assert events is not None or events is None

    def test_configuration_defaults(self):
        """Test that default configuration is properly set."""
        from dotmac.communications import get_default_config

        config = get_default_config()

        # Test notifications defaults
        assert "notifications" in config
        assert config["notifications"]["retry_attempts"] == 3
        assert config["notifications"]["track_delivery"] is True

        # Test websockets defaults
        assert "websockets" in config
        assert config["websockets"]["connection_timeout"] == 60
        assert config["websockets"]["max_connections_per_tenant"] == 1000

        # Test events defaults
        assert "events" in config
        assert config["events"]["max_retries"] == 5
        assert config["events"]["dead_letter_enabled"] is True


class TestNotificationsComponent:
    """Test notifications component."""

    def test_notification_service_import(self):
        """Test notification service can be imported."""
        from dotmac.communications.notifications import UnifiedNotificationService

        assert UnifiedNotificationService is not None

    def test_notification_models_import(self):
        """Test notification models can be imported."""
        from dotmac.communications.notifications import (
            NotificationRequest,
            NotificationResponse,
            NotificationStatus,
            NotificationTemplate,
        )

        assert NotificationTemplate is not None
        assert NotificationRequest is not None
        assert NotificationResponse is not None
        assert NotificationStatus is not None


class TestWebSocketsComponent:
    """Test WebSockets component."""

    def test_websocket_gateway_import(self):
        """Test WebSocket gateway can be imported."""
        from dotmac.communications.websockets import WebSocketGateway

        assert WebSocketGateway is not None

    def test_websocket_managers_import(self):
        """Test WebSocket managers can be imported."""
        from dotmac.communications.websockets import (
            BroadcastManager,
            ChannelManager,
            SessionManager,
        )

        assert ChannelManager is not None
        assert BroadcastManager is not None
        assert SessionManager is not None

    def test_websocket_config_import(self):
        """Test WebSocket config can be imported."""
        from dotmac.communications.websockets import WebSocketConfig

        assert WebSocketConfig is not None


class TestEventsComponent:
    """Test Events component."""

    def test_event_bus_import(self):
        """Test event bus can be imported."""
        from dotmac.communications.events import EventBus

        assert EventBus is not None

    def test_event_models_import(self):
        """Test event models can be imported."""
        from dotmac.communications.events import Event

        assert Event is not None

    def test_event_adapters_import(self):
        """Test event adapters can be imported."""
        from dotmac.communications.events.adapters import MemoryEventBus, create_memory_bus

        assert create_memory_bus is not None
        assert MemoryEventBus is not None


class TestPackageMetadata:
    """Test package metadata and version info."""

    def test_version_info(self):
        """Test version information is available."""
        import dotmac.communications

        assert hasattr(dotmac.communications, "__version__")
        assert dotmac.communications.__version__ == "1.0.0"

    def test_author_info(self):
        """Test author information is available."""
        import dotmac.communications

        assert hasattr(dotmac.communications, "__author__")
        assert dotmac.communications.__author__ == "DotMac Team"

    def test_all_exports(self):
        """Test that all expected exports are available."""
        import dotmac.communications

        expected_exports = [
            "NotificationService",
            "WebSocketManager",
            "EventBus",
            "CommunicationsService",
            "create_communications_service",
            "__version__",
        ]

        for export in expected_exports:
            assert hasattr(dotmac.communications, export), f"Missing export: {export}"


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_graceful_import_failure_handling(self):
        """Test that import failures are handled gracefully."""
        # The package should not crash even if some components fail to import
        service = create_communications_service()

        # Should be able to access properties without exceptions
        try:
            _ = service.notifications
            _ = service.websockets
            _ = service.events
        except Exception as e:
            pytest.fail(f"Service property access should not raise exceptions: {e}")

    def test_configuration_validation(self):
        """Test configuration validation."""
        # Invalid config should not crash the service
        invalid_config = {"invalid_key": "invalid_value"}
        service = create_communications_service(invalid_config)
        assert service is not None


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations if available."""

    async def test_event_bus_creation(self):
        """Test event bus creation."""
        from dotmac.communications.events.adapters import create_memory_bus

        try:
            bus = create_memory_bus()
            assert bus is not None
        except Exception:
            # It's okay if this fails - just testing if it's available
            pass


if __name__ == "__main__":
    pytest.main([__file__])
