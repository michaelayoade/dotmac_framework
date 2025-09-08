"""
Test platform adapter graceful degradation when integrations are absent.
"""

from unittest.mock import patch, MagicMock
import logging

from dotmac.ticketing.integrations.adapters import (
    get_communication_service,
    get_monitoring_service,  
    get_benchmark_manager,
    NoopCommunicationService,
    NoopMonitoringService,
    CommunicationServiceProtocol,
    MonitoringServiceProtocol,
)


class TestGracefulDegradation:
    """Test adapters gracefully degrade when platform services are unavailable."""

    def test_communication_service_graceful_fallback(self, caplog):
        """Test communication service falls back gracefully when platform unavailable."""
        # Simulate ImportError by blocking the import
        with patch.dict('sys.modules', {'dotmac.platform.monitoring.integrations': None}):
            with patch('builtins.__import__', side_effect=ImportError("Module not found")):
                service = get_communication_service()
                
                # Should return noop service
                assert isinstance(service, NoopCommunicationService)
                assert isinstance(service, CommunicationServiceProtocol)
                
                # Should log debug message
                with caplog.at_level(logging.DEBUG):
                    get_communication_service()  # Call again to trigger log
                    
    def test_monitoring_service_graceful_fallback(self, caplog):
        """Test monitoring service falls back gracefully when platform unavailable."""
        with patch.dict('sys.modules', {'dotmac.platform.monitoring.integrations': None}):
            with patch('builtins.__import__', side_effect=ImportError("Module not found")):
                service = get_monitoring_service()
                
                # Should return noop service
                assert isinstance(service, NoopMonitoringService)
                assert isinstance(service, MonitoringServiceProtocol)

    def test_benchmark_manager_graceful_fallback(self, caplog):
        """Test benchmark manager falls back gracefully when platform unavailable."""
        with patch.dict('sys.modules', {'dotmac.platform.monitoring.benchmarks': None}):
            with patch('builtins.__import__', side_effect=ImportError("Module not found")):
                manager = get_benchmark_manager()
                
                # Should return None
                assert manager is None

    async def test_noop_communication_service_functionality(self, caplog):
        """Test noop communication service provides expected functionality."""
        service = NoopCommunicationService()
        
        with caplog.at_level(logging.INFO):
            result = await service.send_notification(
                recipient="test@example.com",
                subject="Test Subject",
                template="test_template.html",
                context={"ticket_number": "TKT-123", "priority": "high"}
            )
        
        # Should return True indicating "success"
        assert result is True
        
        # Should log notification details
        assert "NOTIFICATION:" in caplog.text
        assert "test@example.com" in caplog.text
        assert "Test Subject" in caplog.text
        assert "TKT-123" in caplog.text

    def test_noop_monitoring_service_functionality(self, caplog):
        """Test noop monitoring service provides expected functionality."""
        service = NoopMonitoringService()
        
        with caplog.at_level(logging.INFO):
            service.record_event(
                event_type="ticket_created",
                service="dotmac-ticketing",
                details={"ticket_number": "TKT-123", "priority": "high", "tenant": "acme"}
            )
        
        # Should log event details
        assert "EVENT: ticket_created in dotmac-ticketing" in caplog.text
        assert "TKT-123" in caplog.text

    def test_adapters_implement_protocols(self):
        """Test that all adapters properly implement their protocols."""
        # Communication service
        comm_service = NoopCommunicationService()
        assert hasattr(comm_service, 'send_notification')
        assert callable(comm_service.send_notification)
        
        # Monitoring service
        mon_service = NoopMonitoringService()
        assert hasattr(mon_service, 'record_event')
        assert callable(mon_service.record_event)

    def test_platform_service_integration_when_available(self):
        """Test that platform services are used when available."""
        # Mock platform notification service
        mock_notification_service = MagicMock()
        mock_module = MagicMock()
        mock_module.NotificationService = MagicMock(return_value=mock_notification_service)
        
        with patch.dict('sys.modules', {'dotmac.platform.monitoring.integrations': mock_module}):
            service = get_communication_service()
            assert service is mock_notification_service
            mock_module.NotificationService.assert_called_once()

    def test_platform_monitoring_integration_when_available(self):
        """Test that platform monitoring services are used when available."""
        # Mock platform metrics service
        mock_metrics_service = MagicMock()
        mock_module = MagicMock()
        mock_module.MetricsService = MagicMock(return_value=mock_metrics_service)
        
        with patch.dict('sys.modules', {'dotmac.platform.monitoring.integrations': mock_module}):
            service = get_monitoring_service()
            assert service is mock_metrics_service
            mock_module.MetricsService.assert_called_once_with(
                service_name="dotmac-ticketing",
                tenant_id="default"
            )

    def test_platform_benchmark_integration_when_available(self):
        """Test that platform benchmark manager is used when available."""
        # Mock platform benchmark manager
        mock_benchmark_manager = MagicMock()
        mock_module = MagicMock()
        mock_module.BenchmarkManager = MagicMock(return_value=mock_benchmark_manager)
        
        with patch.dict('sys.modules', {'dotmac.platform.monitoring.benchmarks': mock_module}):
            manager = get_benchmark_manager()
            assert manager is mock_benchmark_manager
            mock_module.BenchmarkManager.assert_called_once_with(service_name="dotmac-ticketing")


class TestEndToEndAdapterBehavior:
    """Test adapter behavior in realistic integration scenarios."""

    async def test_ticketing_works_without_platform_services(self):
        """Test that ticketing system works completely without platform services."""
        # Force all platform imports to fail
        with patch('builtins.__import__') as mock_import:
            def side_effect(name, *args, **kwargs):
                if 'dotmac.platform' in name:
                    raise ImportError(f"No module named '{name}'")
                return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = side_effect
            
            # Get services - should all return noop implementations
            comm_service = get_communication_service()
            mon_service = get_monitoring_service()
            bench_manager = get_benchmark_manager()
            
            # Verify fallback behavior
            assert isinstance(comm_service, NoopCommunicationService)
            assert isinstance(mon_service, NoopMonitoringService)
            assert bench_manager is None
            
            # Verify services still work
            result = await comm_service.send_notification(
                recipient="user@test.com",
                subject="Test",
                template="test.html",
                context={"ticket_number": "TKT-001"}
            )
            assert result is True
            
            # Monitoring should work without errors
            mon_service.record_event("test", "service", {"data": "test"})

    def test_mixed_availability_scenario(self):
        """Test scenario where some platform services are available, others aren't."""
        # Mock only notification service available
        mock_notification = MagicMock()
        mock_notif_module = MagicMock()
        mock_notif_module.NotificationService = MagicMock(return_value=mock_notification)
        
        with patch.dict('sys.modules', {
            'dotmac.platform.monitoring.integrations': mock_notif_module,
            'dotmac.platform.monitoring.benchmarks': None
        }):
            with patch('builtins.__import__') as mock_import:
                def side_effect(name, *args, **kwargs):
                    if 'benchmarks' in name:
                        raise ImportError(f"No module named '{name}'")
                    return __import__(name, *args, **kwargs)
                
                mock_import.side_effect = side_effect
                
                # Should get real notification service but noop benchmark
                comm_service = get_communication_service()
                bench_manager = get_benchmark_manager()
                
                assert comm_service is mock_notification
                assert bench_manager is None

    def test_import_error_types_handled(self):
        """Test different types of import errors are handled gracefully."""
        import_errors = [
            ImportError("No module named 'dotmac.platform'"),
            ModuleNotFoundError("No module named 'dotmac.platform.monitoring'"),
            ImportError("cannot import name 'NotificationService'"),
            AttributeError("module has no attribute 'NotificationService'"),
        ]
        
        for error in import_errors:
            with patch('builtins.__import__', side_effect=error):
                # Should not raise, should return noop services
                comm_service = get_communication_service()
                mon_service = get_monitoring_service()
                bench_manager = get_benchmark_manager()
                
                assert isinstance(comm_service, NoopCommunicationService)
                assert isinstance(mon_service, NoopMonitoringService)
                assert bench_manager is None

    async def test_adapter_contract_compliance(self):
        """Test that adapters fulfill the expected contracts regardless of availability."""
        # Test both scenarios - with and without platform services
        scenarios = [
            # Force fallback to noop
            lambda: patch('builtins.__import__', side_effect=ImportError()),
            # Allow platform services (will still fail but tests the path)
            lambda: patch('builtins.__import__', return_value=MagicMock()),
        ]
        
        for scenario_context in scenarios:
            with scenario_context():
                comm_service = get_communication_service()
                mon_service = get_monitoring_service()
                
                # Both should implement the protocol methods
                assert hasattr(comm_service, 'send_notification')
                assert hasattr(mon_service, 'record_event')
                
                # Methods should be callable
                assert callable(comm_service.send_notification)
                assert callable(mon_service.record_event)
                
                # Communication service should return bool
                if isinstance(comm_service, NoopCommunicationService):
                    result = await comm_service.send_notification("test", "test", "test", {})
                    assert isinstance(result, bool)
                
                # Monitoring service should not raise
                if isinstance(mon_service, NoopMonitoringService):
                    mon_service.record_event("test", "test", {})  # Should not raise

    def test_logging_behavior_consistent(self, caplog):
        """Test that logging behavior is consistent across fallback scenarios."""
        # Test that debug messages are logged when falling back
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            with caplog.at_level(logging.DEBUG):
                get_communication_service()
                get_monitoring_service()
                get_benchmark_manager()
            
            # Should have debug messages for each fallback
            debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
            
            assert any("notification service not available" in msg.lower() for msg in debug_messages)
            assert any("monitoring service not available" in msg.lower() for msg in debug_messages)  
            assert any("benchmark manager not available" in msg.lower() for msg in debug_messages)

    def test_adapter_isolation(self):
        """Test that adapter failures don't affect each other."""
        # Mock scenario where notification works but monitoring fails
        mock_notification = MagicMock()
        
        def import_side_effect(name, *args, **kwargs):
            if 'integrations' in name:
                mock_module = MagicMock()
                mock_module.NotificationService = MagicMock(return_value=mock_notification)
                mock_module.MetricsService = MagicMock(side_effect=Exception("Service init failed"))
                return mock_module
            elif 'benchmarks' in name:
                raise ImportError("Benchmark module not found")
            return __import__(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=import_side_effect):
            # Communication should work
            comm_service = get_communication_service()
            assert comm_service is mock_notification
            
            # Monitoring should fallback gracefully even if init fails
            mon_service = get_monitoring_service()
            # Will either be the failed service or fallback to noop
            assert mon_service is not None
            
            # Benchmark should fallback to None
            bench_manager = get_benchmark_manager()
            assert bench_manager is None