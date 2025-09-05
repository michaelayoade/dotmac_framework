"""
Test suite for plugin observability functionality.

Tests observability hooks, metrics collection, logging integration,
and event monitoring.
"""

import logging
from unittest.mock import Mock, patch

import pytest
from dotmac.plugins import (
    LoggingObservabilityCollector,
    MetricsCollector,
    ObservabilityCollector,
    PluginLifecycleManager,
    PluginObservabilityHooks,
    PluginRegistry,
)

from conftest import AsyncTestPlugin, FailingPlugin, TestPlugin


class TestPluginObservabilityHooks:
    """Test basic observability hooks functionality."""
    
    def test_observability_hooks_creation(self):
        """Test observability hooks initialization."""
        hooks = PluginObservabilityHooks()
        
        assert hooks.enable_logging is True
        assert hooks.enable_metrics is True
        assert isinstance(hooks.collectors, list)
        
    def test_observability_hooks_with_config(self):
        """Test observability hooks with configuration."""
        hooks = PluginObservabilityHooks(
            enable_logging=False,
            enable_metrics=False
        )
        
        assert hooks.enable_logging is False
        assert hooks.enable_metrics is False
        
    def test_add_collector(self):
        """Test adding collectors to observability hooks."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        
        hooks.add_collector(collector)
        
        assert collector in hooks.collectors
        
    def test_remove_collector(self):
        """Test removing collectors from observability hooks."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        
        hooks.add_collector(collector)
        assert collector in hooks.collectors
        
        hooks.remove_collector(collector)
        assert collector not in hooks.collectors
        
    def test_on_register_event(self, test_plugin):
        """Test plugin registration event hook."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        hooks.on_register(test_plugin)
        
        collector.on_plugin_registered.assert_called_once_with(test_plugin)
        
    def test_on_init_event(self, test_plugin):
        """Test plugin initialization event hook."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        hooks.on_init(test_plugin)
        
        collector.on_plugin_initialized.assert_called_once_with(test_plugin)
        
    def test_on_start_event(self, test_plugin):
        """Test plugin start event hook."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        hooks.on_start(test_plugin)
        
        collector.on_plugin_started.assert_called_once_with(test_plugin)
        
    def test_on_stop_event(self, test_plugin):
        """Test plugin stop event hook."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        hooks.on_stop(test_plugin)
        
        collector.on_plugin_stopped.assert_called_once_with(test_plugin)
        
    def test_on_error_event(self, test_plugin):
        """Test plugin error event hook."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        error = RuntimeError("Test error")
        hooks.on_error(test_plugin, error)
        
        collector.on_plugin_error.assert_called_once_with(test_plugin, error)
        
    def test_multiple_collectors(self, test_plugin):
        """Test multiple collectors receive events."""
        hooks = PluginObservabilityHooks()
        collector1 = Mock(spec=ObservabilityCollector)
        collector2 = Mock(spec=ObservabilityCollector)
        
        hooks.add_collector(collector1)
        hooks.add_collector(collector2)
        
        hooks.on_register(test_plugin)
        
        collector1.on_plugin_registered.assert_called_once_with(test_plugin)
        collector2.on_plugin_registered.assert_called_once_with(test_plugin)


class TestLoggingObservabilityCollector:
    """Test logging-based observability collector."""
    
    def test_logging_collector_creation(self):
        """Test logging collector initialization."""
        collector = LoggingObservabilityCollector()
        
        assert collector.logger.name == "dotmac.plugins.observability"
        assert collector.log_level == logging.INFO
        
    def test_logging_collector_with_custom_logger(self):
        """Test logging collector with custom logger."""
        custom_logger = logging.getLogger("custom")
        collector = LoggingObservabilityCollector(logger=custom_logger)
        
        assert collector.logger is custom_logger
        
    def test_logging_collector_with_log_level(self):
        """Test logging collector with custom log level."""
        collector = LoggingObservabilityCollector(log_level=logging.DEBUG)
        
        assert collector.log_level == logging.DEBUG
        
    def test_log_plugin_registered(self, test_plugin, caplog):
        """Test logging plugin registration."""
        collector = LoggingObservabilityCollector()
        
        with caplog.at_level(logging.INFO):
            collector.on_plugin_registered(test_plugin)
            
        assert "Plugin registered" in caplog.text
        assert test_plugin.name in caplog.text
        
    def test_log_plugin_initialized(self, test_plugin, caplog):
        """Test logging plugin initialization."""
        collector = LoggingObservabilityCollector()
        
        with caplog.at_level(logging.INFO):
            collector.on_plugin_initialized(test_plugin)
            
        assert "Plugin initialized" in caplog.text
        assert test_plugin.name in caplog.text
        
    def test_log_plugin_started(self, test_plugin, caplog):
        """Test logging plugin start."""
        collector = LoggingObservabilityCollector()
        
        with caplog.at_level(logging.INFO):
            collector.on_plugin_started(test_plugin)
            
        assert "Plugin started" in caplog.text
        assert test_plugin.name in caplog.text
        
    def test_log_plugin_stopped(self, test_plugin, caplog):
        """Test logging plugin stop."""
        collector = LoggingObservabilityCollector()
        
        with caplog.at_level(logging.INFO):
            collector.on_plugin_stopped(test_plugin)
            
        assert "Plugin stopped" in caplog.text
        assert test_plugin.name in caplog.text
        
    def test_log_plugin_error(self, test_plugin, caplog):
        """Test logging plugin error."""
        collector = LoggingObservabilityCollector()
        error = RuntimeError("Test error")
        
        with caplog.at_level(logging.ERROR):
            collector.on_plugin_error(test_plugin, error)
            
        assert "Plugin error" in caplog.text
        assert test_plugin.name in caplog.text
        assert "Test error" in caplog.text


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    def test_metrics_collector_creation(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        
        assert isinstance(collector.metrics, dict)
        assert collector.metrics == {}
        
    def test_increment_counter(self):
        """Test counter increment functionality."""
        collector = MetricsCollector()
        
        collector.increment_counter("plugin.registered")
        collector.increment_counter("plugin.registered")
        collector.increment_counter("plugin.started")
        
        assert collector.metrics["plugin.registered"] == 2
        assert collector.metrics["plugin.started"] == 1
        
    def test_set_gauge(self):
        """Test gauge value setting."""
        collector = MetricsCollector()
        
        collector.set_gauge("plugins.active", 5)
        collector.set_gauge("plugins.active", 8)  # Update value
        collector.set_gauge("plugins.initialized", 3)
        
        assert collector.metrics["plugins.active"] == 8
        assert collector.metrics["plugins.initialized"] == 3
        
    def test_record_timing(self):
        """Test timing recording."""
        collector = MetricsCollector()
        
        collector.record_timing("plugin.init_duration", 0.5)
        collector.record_timing("plugin.init_duration", 0.3)
        
        # Should store list of timings
        assert "plugin.init_duration" in collector.metrics
        timings = collector.metrics["plugin.init_duration"]
        assert isinstance(timings, list)
        assert 0.5 in timings
        assert 0.3 in timings
        
    def test_get_metrics(self):
        """Test metrics retrieval."""
        collector = MetricsCollector()
        
        collector.increment_counter("test.counter")
        collector.set_gauge("test.gauge", 42)
        collector.record_timing("test.timing", 1.23)
        
        metrics = collector.get_metrics()
        
        assert metrics["test.counter"] == 1
        assert metrics["test.gauge"] == 42
        assert metrics["test.timing"] == [1.23]
        
    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        collector = MetricsCollector()
        
        collector.increment_counter("test.counter")
        collector.set_gauge("test.gauge", 42)
        
        assert len(collector.metrics) > 0
        
        collector.reset_metrics()
        
        assert len(collector.metrics) == 0
        
    def test_plugin_lifecycle_metrics(self, test_plugin):
        """Test metrics collection for plugin lifecycle events."""
        collector = MetricsCollector()
        
        collector.on_plugin_registered(test_plugin)
        collector.on_plugin_initialized(test_plugin)
        collector.on_plugin_started(test_plugin)
        collector.on_plugin_stopped(test_plugin)
        
        metrics = collector.get_metrics()
        
        assert metrics["plugins.registered"] == 1
        assert metrics["plugins.initialized"] == 1
        assert metrics["plugins.started"] == 1
        assert metrics["plugins.stopped"] == 1
        
    def test_plugin_error_metrics(self, test_plugin):
        """Test metrics collection for plugin errors."""
        collector = MetricsCollector()
        error = RuntimeError("Test error")
        
        collector.on_plugin_error(test_plugin, error)
        collector.on_plugin_error(test_plugin, error)  # Second error
        
        metrics = collector.get_metrics()
        
        assert metrics["plugins.errors"] == 2


class TestObservabilityIntegration:
    """Test observability integration with plugin system."""
    
    @pytest.mark.asyncio
    async def test_registry_with_observability(self, plugin_context):
        """Test registry operations trigger observability events."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        registry = PluginRegistry(observability_hooks=hooks)
        plugin = TestPlugin("observed")
        
        # Register plugin
        registry.register(plugin)
        collector.on_plugin_registered.assert_called_once_with(plugin)
        
        # Initialize plugin
        await registry.init_plugin(plugin.name, plugin_context)
        collector.on_plugin_initialized.assert_called_once_with(plugin)
        
        # Start plugin
        await registry.start_plugin(plugin.name)
        collector.on_plugin_started.assert_called_once_with(plugin)
        
        # Stop plugin
        await registry.stop_plugin(plugin.name)
        collector.on_plugin_stopped.assert_called_once_with(plugin)
        
    @pytest.mark.asyncio
    async def test_lifecycle_manager_with_observability(self, plugin_context):
        """Test lifecycle manager operations trigger observability events."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        registry = PluginRegistry(observability_hooks=hooks)
        lifecycle = PluginLifecycleManager(registry=registry)
        
        plugin1 = TestPlugin("plugin1")
        plugin2 = TestPlugin("plugin2")
        
        registry.register(plugin1)
        registry.register(plugin2)
        
        # Should trigger registered events
        assert collector.on_plugin_registered.call_count == 2
        
        # Initialize all
        await lifecycle.initialize_all(plugin_context)
        assert collector.on_plugin_initialized.call_count == 2
        
        # Start all
        await lifecycle.start_all()
        assert collector.on_plugin_started.call_count == 2
        
        # Stop all
        await lifecycle.stop_all()
        assert collector.on_plugin_stopped.call_count == 2
        
    @pytest.mark.asyncio
    async def test_error_observability(self, plugin_context):
        """Test error events are properly observed."""
        hooks = PluginObservabilityHooks()
        collector = Mock(spec=ObservabilityCollector)
        hooks.add_collector(collector)
        
        registry = PluginRegistry(observability_hooks=hooks)
        failing_plugin = FailingPlugin("failing", fail_on="init")
        
        registry.register(failing_plugin)
        
        # This should trigger error event
        with pytest.raises(RuntimeError):
            await registry.init_plugin(failing_plugin.name, plugin_context)
            
        collector.on_plugin_error.assert_called_once()
        args = collector.on_plugin_error.call_args[0]
        assert args[0] is failing_plugin
        assert isinstance(args[1], RuntimeError)


class TestOpenTelemetryIntegration:
    """Test OpenTelemetry integration when available."""
    
    def test_otel_integration_available(self):
        """Test OpenTelemetry integration when library is available."""
        try:
            from opentelemetry import trace
            # If import succeeds, test basic integration
            hooks = PluginObservabilityHooks()
            assert hooks.enable_metrics is True
        except ImportError:
            pytest.skip("OpenTelemetry not available")
            
    def test_otel_integration_unavailable(self):
        """Test graceful handling when OpenTelemetry is unavailable."""
        # Mock import error for opentelemetry
        with patch.dict('sys.modules', {'opentelemetry': None}):
            # Should still create hooks without error
            hooks = PluginObservabilityHooks()
            assert hooks.enable_metrics is True


class TestPerformanceMetrics:
    """Test performance monitoring and timing metrics."""
    
    @pytest.mark.asyncio
    async def test_timing_metrics_collection(self, plugin_context):
        """Test collection of timing metrics for plugin operations."""
        collector = MetricsCollector()
        hooks = PluginObservabilityHooks()
        hooks.add_collector(collector)
        
        registry = PluginRegistry(observability_hooks=hooks)
        
        # Use AsyncTestPlugin to simulate some timing
        async_plugin = AsyncTestPlugin("timed")
        registry.register(async_plugin)
        
        import time
        start_time = time.time()
        await registry.init_plugin(async_plugin.name, plugin_context)
        end_time = time.time()
        
        # Manually record timing (in real implementation, this would be automatic)
        collector.record_timing("plugin.init_duration", end_time - start_time)
        
        metrics = collector.get_metrics()
        assert "plugin.init_duration" in metrics
        assert len(metrics["plugin.init_duration"]) == 1
        assert metrics["plugin.init_duration"][0] > 0
        
    @pytest.mark.asyncio
    async def test_batch_operation_metrics(self, plugin_context):
        """Test metrics for batch plugin operations."""
        collector = MetricsCollector()
        
        # Simulate batch initialization
        plugins = [TestPlugin(f"plugin_{i}") for i in range(5)]
        
        for plugin in plugins:
            collector.on_plugin_registered(plugin)
            collector.on_plugin_initialized(plugin)
            collector.on_plugin_started(plugin)
            
        metrics = collector.get_metrics()
        
        assert metrics["plugins.registered"] == 5
        assert metrics["plugins.initialized"] == 5
        assert metrics["plugins.started"] == 5


class TestObservabilityConfiguration:
    """Test observability configuration options."""
    
    def test_disable_logging(self, test_plugin):
        """Test disabling logging observability."""
        hooks = PluginObservabilityHooks(enable_logging=False)
        
        # Add logging collector - should still work but hooks won't use it
        logging_collector = LoggingObservabilityCollector()
        hooks.add_collector(logging_collector)
        
        # This should not generate logs
        with patch.object(logging_collector, 'on_plugin_registered') as mock_log:
            hooks.on_register(test_plugin)
            mock_log.assert_called_once()  # Collector still gets called
            
    def test_disable_metrics(self, test_plugin):
        """Test disabling metrics observability."""
        hooks = PluginObservabilityHooks(enable_metrics=False)
        
        metrics_collector = MetricsCollector()
        hooks.add_collector(metrics_collector)
        
        # Should still call collectors even with metrics disabled
        with patch.object(metrics_collector, 'on_plugin_registered') as mock_metrics:
            hooks.on_register(test_plugin)
            mock_metrics.assert_called_once()
            
    def test_custom_collector_integration(self, test_plugin):
        """Test integration with custom observability collector."""
        class CustomCollector(ObservabilityCollector):
            def __init__(self):
                self.events = []
                
            def on_plugin_registered(self, plugin):
                self.events.append(f"registered:{plugin.name}")
                
            def on_plugin_started(self, plugin):
                self.events.append(f"started:{plugin.name}")
                
        hooks = PluginObservabilityHooks()
        custom_collector = CustomCollector()
        hooks.add_collector(custom_collector)
        
        hooks.on_register(test_plugin)
        hooks.on_start(test_plugin)
        
        assert "registered:test_plugin" in custom_collector.events
        assert "started:test_plugin" in custom_collector.events


class TestObservabilityErrorHandling:
    """Test error handling in observability system."""
    
    def test_collector_error_isolation(self, test_plugin):
        """Test that errors in one collector don't affect others."""
        failing_collector = Mock(spec=ObservabilityCollector)
        failing_collector.on_plugin_registered.side_effect = RuntimeError("Collector error")
        
        working_collector = Mock(spec=ObservabilityCollector)
        
        hooks = PluginObservabilityHooks()
        hooks.add_collector(failing_collector)
        hooks.add_collector(working_collector)
        
        # Should not raise error, working collector should still be called
        hooks.on_register(test_plugin)
        
        failing_collector.on_plugin_registered.assert_called_once_with(test_plugin)
        working_collector.on_plugin_registered.assert_called_once_with(test_plugin)
        
    def test_observability_without_collectors(self, test_plugin):
        """Test observability hooks work without any collectors."""
        hooks = PluginObservabilityHooks()
        
        # Should not raise errors
        hooks.on_register(test_plugin)
        hooks.on_init(test_plugin)
        hooks.on_start(test_plugin)
        hooks.on_stop(test_plugin)
        hooks.on_error(test_plugin, RuntimeError("test"))
        
    def test_none_collector_handling(self, test_plugin):
        """Test handling of None collectors."""
        hooks = PluginObservabilityHooks()
        
        # Try to add None collector
        hooks.add_collector(None)
        
        # Should handle gracefully
        hooks.on_register(test_plugin)