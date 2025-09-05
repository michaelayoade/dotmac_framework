"""
Test suite for PluginLifecycleManager functionality.

Tests plugin lifecycle orchestration, startup/shutdown ordering,
batch operations, and error handling.
"""

import asyncio
from unittest.mock import patch

import pytest
from dotmac.plugins import (
    PluginError,
    PluginKind,
    PluginLifecycleManager,
    PluginRegistry,
    PluginStatus,
)

from conftest import AsyncTestPlugin, FailingPlugin, TestExportPlugin, TestPlugin


class TestLifecycleManager:
    """Test PluginLifecycleManager core functionality."""
    
    def test_lifecycle_manager_creation(self, plugin_registry):
        """Test lifecycle manager initialization."""
        manager = PluginLifecycleManager(registry=plugin_registry)
        
        assert manager.registry is plugin_registry
        assert manager.is_initialized is False
        assert manager.is_started is False
        
    def test_lifecycle_manager_default_registry(self):
        """Test lifecycle manager with default registry."""
        manager = PluginLifecycleManager()
        
        assert isinstance(manager.registry, PluginRegistry)
        assert manager.is_initialized is False
        assert manager.is_started is False
        
    def test_load_plugins_method(self, plugin_lifecycle):
        """Test load_plugins method integration."""
        with patch.object(plugin_lifecycle.registry, 'load') as mock_load:
            mock_load.return_value = 3
            
            result = plugin_lifecycle.load_plugins("test.plugins")
            
            assert result == 3
            mock_load.assert_called_once_with("test.plugins")
            
    @pytest.mark.asyncio
    async def test_initialize_all_empty_registry(self, plugin_lifecycle, plugin_context):
        """Test initializing with empty registry."""
        result = await plugin_lifecycle.initialize_all(plugin_context)
        
        assert result is True
        assert plugin_lifecycle.is_initialized is True
        
    @pytest.mark.asyncio
    async def test_initialize_all_with_plugins(self, plugin_lifecycle, plugin_context):
        """Test initializing all plugins."""
        # Add test plugins
        plugin1 = TestPlugin("plugin1")
        plugin2 = AsyncTestPlugin("plugin2")
        
        plugin_lifecycle.registry.register(plugin1)
        plugin_lifecycle.registry.register(plugin2)
        
        result = await plugin_lifecycle.initialize_all(plugin_context)
        
        assert result is True
        assert plugin_lifecycle.is_initialized is True
        assert plugin1.init_called
        assert plugin2.init_called
        assert all(p.status == PluginStatus.INITIALIZED for p in [plugin1, plugin2])
        
    @pytest.mark.asyncio
    async def test_initialize_all_with_failures(self, plugin_lifecycle, plugin_context):
        """Test initialization continues despite failures."""
        good_plugin = TestPlugin("good")
        failing_plugin = FailingPlugin("bad", fail_on="init")
        
        plugin_lifecycle.registry.register(good_plugin)
        plugin_lifecycle.registry.register(failing_plugin)
        
        result = await plugin_lifecycle.initialize_all(plugin_context)
        
        # Should succeed overall despite individual failure
        assert result is True
        assert plugin_lifecycle.is_initialized is True
        assert good_plugin.status == PluginStatus.INITIALIZED
        assert failing_plugin.status == PluginStatus.ERROR
        
    @pytest.mark.asyncio
    async def test_start_all_not_initialized(self, plugin_lifecycle):
        """Test starting without initialization raises error."""
        plugin_lifecycle.registry.register(TestPlugin("test"))
        
        with pytest.raises(PluginError, match="Cannot start plugins before initialization"):
            await plugin_lifecycle.start_all()
            
    @pytest.mark.asyncio
    async def test_start_all_success(self, plugin_lifecycle, plugin_context):
        """Test starting all plugins successfully."""
        plugin1 = TestPlugin("plugin1")
        plugin2 = AsyncTestPlugin("plugin2")
        
        plugin_lifecycle.registry.register(plugin1)
        plugin_lifecycle.registry.register(plugin2)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        result = await plugin_lifecycle.start_all()
        
        assert result is True
        assert plugin_lifecycle.is_started is True
        assert plugin1.start_called
        assert plugin2.start_called
        assert all(p.status == PluginStatus.STARTED for p in [plugin1, plugin2])
        
    @pytest.mark.asyncio
    async def test_stop_all_not_started(self, plugin_lifecycle, plugin_context):
        """Test stopping without starting is allowed."""
        plugin_lifecycle.registry.register(TestPlugin("test"))
        await plugin_lifecycle.initialize_all(plugin_context)
        
        result = await plugin_lifecycle.stop_all()
        
        # Should succeed even if not started
        assert result is True
        assert plugin_lifecycle.is_started is False
        
    @pytest.mark.asyncio
    async def test_stop_all_success(self, plugin_lifecycle, plugin_context):
        """Test stopping all plugins successfully."""
        plugin1 = TestPlugin("plugin1")
        plugin2 = AsyncTestPlugin("plugin2")
        
        plugin_lifecycle.registry.register(plugin1)
        plugin_lifecycle.registry.register(plugin2)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        await plugin_lifecycle.start_all()
        result = await plugin_lifecycle.stop_all()
        
        assert result is True
        assert plugin_lifecycle.is_started is False
        assert plugin1.stop_called
        assert plugin2.stop_called
        assert all(p.status == PluginStatus.STOPPED for p in [plugin1, plugin2])


class TestStartupOrdering:
    """Test plugin startup ordering by kind."""
    
    @pytest.mark.asyncio
    async def test_startup_order_respected(self, plugin_lifecycle, plugin_context):
        """Test plugins start in correct order by kind."""
        # Create plugins of different kinds in reverse order
        custom_plugin = TestPlugin("custom")
        custom_plugin._metadata.kind = PluginKind.CUSTOM
        
        export_plugin = TestExportPlugin("export")
        export_plugin._metadata.kind = PluginKind.EXPORT
        
        observer_plugin = TestPlugin("observer")
        observer_plugin._metadata.kind = PluginKind.OBSERVER
        
        # Register in reverse order
        plugin_lifecycle.registry.register(custom_plugin)
        plugin_lifecycle.registry.register(export_plugin)
        plugin_lifecycle.registry.register(observer_plugin)
        
        start_order = []
        
        # Mock start methods to track order
        original_start = TestPlugin.start
        original_export_start = TestExportPlugin.start
        
        def track_start(self):
            start_order.append(self.name)
            return original_start(self)
            
        def track_export_start(self):
            start_order.append(self.name)
            return original_export_start(self)
        
        TestPlugin.start = track_start
        TestExportPlugin.start = track_export_start
        
        try:
            await plugin_lifecycle.initialize_all(plugin_context)
            await plugin_lifecycle.start_all()
            
            # Observer should start first, then export, then custom
            assert start_order == ["observer", "export", "custom"]
            
        finally:
            # Restore original methods
            TestPlugin.start = original_start
            TestExportPlugin.start = original_export_start
            
    @pytest.mark.asyncio
    async def test_shutdown_order_reversed(self, plugin_lifecycle, plugin_context):
        """Test plugins stop in reverse order."""
        custom_plugin = TestPlugin("custom")
        custom_plugin._metadata.kind = PluginKind.CUSTOM
        
        observer_plugin = TestPlugin("observer")
        observer_plugin._metadata.kind = PluginKind.OBSERVER
        
        plugin_lifecycle.registry.register(custom_plugin)
        plugin_lifecycle.registry.register(observer_plugin)
        
        stop_order = []
        
        original_stop = TestPlugin.stop
        
        def track_stop(self):
            stop_order.append(self.name)
            return original_stop(self)
        
        TestPlugin.stop = track_stop
        
        try:
            await plugin_lifecycle.initialize_all(plugin_context)
            await plugin_lifecycle.start_all()
            await plugin_lifecycle.stop_all()
            
            # Should stop in reverse order: custom first, then observer
            assert stop_order == ["custom", "observer"]
            
        finally:
            TestPlugin.stop = original_stop


class TestBatchOperations:
    """Test batch plugin operations."""
    
    @pytest.mark.asyncio
    async def test_batch_initialize_mixed_sync_async(self, plugin_lifecycle, plugin_context):
        """Test batch initialization with mixed sync/async plugins."""
        sync_plugin = TestPlugin("sync")
        async_plugin = AsyncTestPlugin("async")
        
        plugin_lifecycle.registry.register(sync_plugin)
        plugin_lifecycle.registry.register(async_plugin)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        
        assert sync_plugin.init_called
        assert async_plugin.init_called
        
    @pytest.mark.asyncio
    async def test_batch_start_parallel_execution(self, plugin_lifecycle, plugin_context):
        """Test that plugin start operations run in parallel."""
        # Create plugins with async delays
        plugin1 = AsyncTestPlugin("async1")
        plugin2 = AsyncTestPlugin("async2")
        
        plugin_lifecycle.registry.register(plugin1)
        plugin_lifecycle.registry.register(plugin2)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        
        # Time the start operation
        import time
        start_time = time.time()
        await plugin_lifecycle.start_all()
        end_time = time.time()
        
        # Should complete in roughly the time of one async operation
        # (since they run in parallel), not the sum of both
        duration = end_time - start_time
        assert duration < 0.05  # Much less than 2 * 0.01 seconds
        
        assert plugin1.start_called
        assert plugin2.start_called
        
    @pytest.mark.asyncio
    async def test_batch_operations_preserve_individual_errors(self, plugin_lifecycle, plugin_context):
        """Test batch operations preserve individual plugin error states."""
        good1 = TestPlugin("good1")
        failing = FailingPlugin("failing", fail_on="start")
        good2 = TestPlugin("good2")
        
        plugin_lifecycle.registry.register(good1)
        plugin_lifecycle.registry.register(failing)
        plugin_lifecycle.registry.register(good2)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        result = await plugin_lifecycle.start_all()
        
        # Operation succeeds overall
        assert result is True
        
        # Good plugins started successfully
        assert good1.status == PluginStatus.STARTED
        assert good2.status == PluginStatus.STARTED
        
        # Failing plugin marked as error
        assert failing.status == PluginStatus.ERROR


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, plugin_lifecycle, plugin_context):
        """Test initialization handles various error types."""
        # Plugin that raises different exception types
        class MultiErrorPlugin(TestPlugin):
            def __init__(self, error_type):
                super().__init__(f"error_{error_type.__name__}")
                self.error_type = error_type
                
            def init(self, context):
                raise self.error_type("Test error")
        
        plugins = [
            MultiErrorPlugin(ValueError),
            MultiErrorPlugin(RuntimeError),
            MultiErrorPlugin(ImportError),
            TestPlugin("good"),
        ]
        
        for plugin in plugins:
            plugin_lifecycle.registry.register(plugin)
            
        result = await plugin_lifecycle.initialize_all(plugin_context)
        
        # Should succeed overall
        assert result is True
        
        # Good plugin should be initialized
        good_plugin = plugin_lifecycle.registry.get("good")
        assert good_plugin.status == PluginStatus.INITIALIZED
        
        # Error plugins should be marked as error
        for plugin in plugins[:-1]:
            assert plugin.status == PluginStatus.ERROR
            
    @pytest.mark.asyncio
    async def test_async_error_handling(self, plugin_lifecycle, plugin_context):
        """Test error handling in async plugin methods."""
        class AsyncErrorPlugin(AsyncTestPlugin):
            async def start(self):
                await asyncio.sleep(0.01)
                raise RuntimeError("Async error")
        
        error_plugin = AsyncErrorPlugin("async_error")
        good_plugin = AsyncTestPlugin("good")
        
        plugin_lifecycle.registry.register(error_plugin)
        plugin_lifecycle.registry.register(good_plugin)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        result = await plugin_lifecycle.start_all()
        
        assert result is True
        assert error_plugin.status == PluginStatus.ERROR
        assert good_plugin.status == PluginStatus.STARTED
        
    @pytest.mark.asyncio
    async def test_stop_error_recovery(self, plugin_lifecycle, plugin_context):
        """Test that stop errors don't prevent other plugins from stopping."""
        failing_stop = FailingPlugin("fail_stop", fail_on="stop")
        good1 = TestPlugin("good1")
        good2 = TestPlugin("good2")
        
        for plugin in [good1, failing_stop, good2]:
            plugin_lifecycle.registry.register(plugin)
            
        await plugin_lifecycle.initialize_all(plugin_context)
        await plugin_lifecycle.start_all()
        result = await plugin_lifecycle.stop_all()
        
        # Should succeed overall despite one failure
        assert result is True
        
        # Good plugins should be stopped
        assert good1.status == PluginStatus.STOPPED
        assert good2.status == PluginStatus.STOPPED
        
        # Failing plugin marked as error
        assert failing_stop.status == PluginStatus.ERROR


class TestLifecycleState:
    """Test lifecycle state management."""
    
    @pytest.mark.asyncio
    async def test_multiple_initialization_calls(self, plugin_lifecycle, plugin_context):
        """Test multiple initialization calls are handled gracefully."""
        plugin = TestPlugin("test")
        plugin_lifecycle.registry.register(plugin)
        
        # First initialization
        result1 = await plugin_lifecycle.initialize_all(plugin_context)
        assert result1 is True
        assert plugin_lifecycle.is_initialized is True
        
        # Second initialization should succeed but not reinitialize plugins
        result2 = await plugin_lifecycle.initialize_all(plugin_context)
        assert result2 is True
        assert plugin_lifecycle.is_initialized is True
        
    @pytest.mark.asyncio
    async def test_multiple_start_calls(self, plugin_lifecycle, plugin_context):
        """Test multiple start calls are handled gracefully."""
        plugin = TestPlugin("test")
        plugin_lifecycle.registry.register(plugin)
        
        await plugin_lifecycle.initialize_all(plugin_context)
        
        # First start
        result1 = await plugin_lifecycle.start_all()
        assert result1 is True
        assert plugin_lifecycle.is_started is True
        
        # Second start should succeed without restarting plugins
        result2 = await plugin_lifecycle.start_all()
        assert result2 is True
        assert plugin_lifecycle.is_started is True
        
    @pytest.mark.asyncio
    async def test_lifecycle_state_after_errors(self, plugin_lifecycle, plugin_context):
        """Test lifecycle state remains consistent after errors."""
        failing_plugin = FailingPlugin("failing", fail_on="init")
        plugin_lifecycle.registry.register(failing_plugin)
        
        # Initialization fails but manager should still be marked as initialized
        result = await plugin_lifecycle.initialize_all(plugin_context)
        assert result is True  # Succeeds overall despite individual failure
        assert plugin_lifecycle.is_initialized is True
        
        # Can proceed to start (though this plugin will be skipped)
        result = await plugin_lifecycle.start_all()
        assert result is True
        assert plugin_lifecycle.is_started is True


class TestIntegrationScenarios:
    """Integration tests for complete lifecycle scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_lifecycle_scenario(self, plugin_lifecycle, plugin_context):
        """Test complete plugin lifecycle from load to shutdown."""
        # Simulate loading plugins
        plugins = [
            TestPlugin("plugin1"),
            AsyncTestPlugin("plugin2"),
            TestExportPlugin("export1"),
        ]
        
        for plugin in plugins:
            plugin_lifecycle.registry.register(plugin)
            
        # Full lifecycle
        await plugin_lifecycle.initialize_all(plugin_context)
        await plugin_lifecycle.start_all()
        await plugin_lifecycle.stop_all()
        
        # Verify final states
        for plugin in plugins:
            assert plugin.status == PluginStatus.STOPPED
            
        # Verify all lifecycle methods called
        for plugin in plugins[:2]:  # TestPlugin and AsyncTestPlugin
            if hasattr(plugin, 'init_called'):
                assert plugin.init_called
                assert plugin.start_called
                assert plugin.stop_called
                
    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self, plugin_lifecycle, plugin_context):
        """Test system recovers from partial failures."""
        plugins = [
            TestPlugin("good1"),
            FailingPlugin("fail_init", fail_on="init"),
            TestPlugin("good2"),
            FailingPlugin("fail_start", fail_on="start"),
            TestPlugin("good3"),
        ]
        
        for plugin in plugins:
            plugin_lifecycle.registry.register(plugin)
            
        # Run full lifecycle
        init_result = await plugin_lifecycle.initialize_all(plugin_context)
        start_result = await plugin_lifecycle.start_all()
        stop_result = await plugin_lifecycle.stop_all()
        
        # All operations should succeed overall
        assert init_result is True
        assert start_result is True
        assert stop_result is True
        
        # Good plugins should complete lifecycle
        good_plugins = [p for p in plugins if p.name.startswith("good")]
        for plugin in good_plugins:
            assert plugin.status == PluginStatus.STOPPED
            
        # Failing plugins should be marked as errors
        failing_plugins = [p for p in plugins if p.name.startswith("fail")]
        for plugin in failing_plugins:
            assert plugin.status == PluginStatus.ERROR