"""
Tests for integration adapters and fallback behavior.
"""

from unittest.mock import MagicMock, patch, AsyncMock
import logging

from dotmac.ticketing.integrations.adapters import (
    get_communication_service,
    get_monitoring_service,
    get_benchmark_manager,
    NoopCommunicationService,
    NoopMonitoringService,
)


class TestIntegrationAdapters:
    """Test integration adapter functionality."""

    async def test_noop_communication_service(self, caplog):
        """Test NoopCommunicationService logs notifications."""
        service = NoopCommunicationService()
        
        with caplog.at_level(logging.INFO):
            result = await service.send_notification(
                recipient="test@example.com",
                subject="Test Subject",
                template="test_template.html",
                context={"ticket_number": "TKT-123"},
                channel="email"
            )
        
        assert result is True
        assert "NOTIFICATION: email to test@example.com - Test Subject" in caplog.text
        assert "ticket: TKT-123" in caplog.text

    def test_noop_monitoring_service(self, caplog):
        """Test NoopMonitoringService logs events."""
        service = NoopMonitoringService()
        
        with caplog.at_level(logging.INFO):
            service.record_event(
                event_type="ticket_created",
                service="dotmac-ticketing",
                details={"ticket_number": "TKT-123", "priority": "high"}
            )
        
        assert "EVENT: ticket_created in dotmac-ticketing" in caplog.text
        assert "ticket: TKT-123" in caplog.text

    def test_get_communication_service_with_platform_available(self):
        """Test get_communication_service returns platform service when available."""
        from dotmac.ticketing.integrations.adapters import get_communication_service
        
        # Mock the import inside the function
        mock_platform_service = MagicMock()
        
        with patch('builtins.__import__') as mock_import:
            mock_module = MagicMock()
            mock_module.CommunicationService = MagicMock(return_value=mock_platform_service)
            mock_import.return_value = mock_module
            
            result = get_communication_service()
            assert result is mock_platform_service

    @patch('dotmac.ticketing.integrations.adapters.logger')
    def test_get_communication_service_fallback(self, mock_logger):
        """Test get_communication_service falls back to noop when platform unavailable."""
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            result = get_communication_service()
            
            assert isinstance(result, NoopCommunicationService)
            mock_logger.debug.assert_called_once_with(
                "Platform communication service not available, using noop"
            )

    @patch('dotmac.ticketing.integrations.adapters.logger')
    def test_get_monitoring_service_with_platform_available(self, mock_logger):
        """Test get_monitoring_service returns platform service when available."""
        mock_platform_service = MagicMock()
        
        with patch.dict('sys.modules', {
            'dotmac.platform.integrations.monitoring': MagicMock()
        }):
            with patch('dotmac.platform.integrations.monitoring.IntegratedMonitoringService', 
                      return_value=mock_platform_service):
                result = get_monitoring_service()
                assert result is mock_platform_service
                mock_logger.debug.assert_not_called()

    @patch('dotmac.ticketing.integrations.adapters.logger')
    def test_get_monitoring_service_fallback(self, mock_logger):
        """Test get_monitoring_service falls back to noop when platform unavailable."""
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            result = get_monitoring_service()
            
            assert isinstance(result, NoopMonitoringService)
            mock_logger.debug.assert_called_once_with(
                "Platform monitoring service not available, using noop"
            )

    @patch('dotmac.ticketing.integrations.adapters.logger')
    def test_get_benchmark_manager_with_platform_available(self, mock_logger):
        """Test get_benchmark_manager returns platform manager when available."""
        mock_benchmark_manager = MagicMock()
        
        with patch.dict('sys.modules', {
            'dotmac.platform.integrations.benchmarking': MagicMock()
        }):
            with patch('dotmac.platform.integrations.benchmarking.BenchmarkManager', 
                      return_value=mock_benchmark_manager):
                result = get_benchmark_manager()
                assert result is mock_benchmark_manager
                mock_logger.debug.assert_not_called()

    @patch('dotmac.ticketing.integrations.adapters.logger')
    def test_get_benchmark_manager_fallback(self, mock_logger):
        """Test get_benchmark_manager returns None when platform unavailable."""
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            result = get_benchmark_manager()
            
            assert result is None
            mock_logger.debug.assert_called_once_with(
                "Platform benchmark manager not available"
            )


class TestCommunicationServiceProtocol:
    """Test communication service protocol compliance."""

    async def test_noop_communication_service_protocol_compliance(self):
        """Test NoopCommunicationService implements protocol correctly."""
        service = NoopCommunicationService()
        
        # Should have required method with correct signature
        assert hasattr(service, 'send_notification')
        assert callable(service.send_notification)
        
        # Should handle async call
        result = await service.send_notification(
            recipient="test@example.com",
            subject="Test",
            template="test.html",
            context={},
            channel="email"
        )
        assert isinstance(result, bool)

    async def test_communication_service_context_handling(self):
        """Test communication service handles different context types."""
        service = NoopCommunicationService()
        
        # Test with various context types
        contexts = [
            {"ticket_number": "TKT-123", "priority": "high"},
            {"ticket_number": None, "user": "test"},
            {},
            {"complex": {"nested": "data"}}
        ]
        
        for context in contexts:
            result = await service.send_notification(
                recipient="test@example.com",
                subject="Test",
                template="test.html",
                context=context
            )
            assert result is True


class TestMonitoringServiceProtocol:
    """Test monitoring service protocol compliance."""

    def test_noop_monitoring_service_protocol_compliance(self):
        """Test NoopMonitoringService implements protocol correctly."""
        service = NoopMonitoringService()
        
        # Should have required method with correct signature
        assert hasattr(service, 'record_event')
        assert callable(service.record_event)
        
        # Should handle call without returning value
        result = service.record_event(
            event_type="test_event",
            service="test_service",
            details={}
        )
        assert result is None

    def test_monitoring_service_details_handling(self):
        """Test monitoring service handles different details types."""
        service = NoopMonitoringService()
        
        # Test with various detail types
        detail_sets = [
            {"ticket_number": "TKT-123", "action": "created"},
            {"ticket_number": None, "error": "validation failed"},
            {},
            {"metrics": {"response_time": 0.5, "success": True}}
        ]
        
        for details in detail_sets:
            service.record_event(
                event_type="test_event",
                service="test_service",
                details=details
            )


class TestAdapterIntegrationWithServices:
    """Test adapters integrate correctly with ticketing services."""

    def test_adapter_integration_with_ticket_manager(self):
        """Test adapters can be injected into TicketManager."""
        from dotmac.ticketing.core.manager import TicketManager
        
        communication_service = NoopCommunicationService()
        monitoring_service = NoopMonitoringService()
        
        # Create manager with adapters
        manager = TicketManager(
            communication_service=communication_service,
            monitoring_service=monitoring_service
        )
        
        assert manager.communication_service is communication_service
        assert manager.monitoring_service is monitoring_service

    async def test_adapter_usage_in_ticket_workflows(self):
        """Test adapters are used in ticket workflow events."""
        from dotmac.ticketing.core.manager import TicketManager
        from dotmac.ticketing.core.models import Ticket, TicketStatus, TicketPriority
        
        # Create mock adapters
        mock_communication = AsyncMock()
        mock_monitoring = MagicMock()
        
        manager = TicketManager(
            communication_service=mock_communication,
            monitoring_service=mock_monitoring
        )
        
        # Create a test ticket
        ticket = Ticket(
            id="test-123",
            ticket_number="TKT-123",
            tenant_id="test-tenant",
            title="Test Ticket",
            description="Test",
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            customer_email="test@example.com"
        )
        
        # Trigger event that should use adapters
        await manager._trigger_ticket_created_events(ticket)
        
        # Verify monitoring service was called
        mock_monitoring.record_event.assert_called_once()
        event_call = mock_monitoring.record_event.call_args
        assert event_call[1]["event_type"] == "ticket_created"
        assert event_call[1]["service"] == "dotmac-ticketing"

    def test_adapter_graceful_degradation(self):
        """Test system works when adapters are not available."""
        from dotmac.ticketing.core.manager import TicketManager
        
        # Create manager without adapters (should use defaults)
        manager = TicketManager()
        
        # Should have fallback services
        assert manager.communication_service is not None
        assert manager.monitoring_service is not None
        assert isinstance(manager.communication_service, NoopCommunicationService)
        assert isinstance(manager.monitoring_service, NoopMonitoringService)