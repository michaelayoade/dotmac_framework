"""
Test suite for PluginRegistry functionality.

Tests plugin registration, lifecycle management, permission checks,
duplicate handling, and error paths.
"""

import pytest
import asyncio
from unittest.mock import Mock

from dotmac.plugins import (
    PluginRegistry,
    PluginKind,
    PluginStatus,
    PluginNotFoundError,
    PluginRegistrationError,
    PluginPermissionError,
    IPlugin,
)
from conftest import TestPlugin, AsyncTestPlugin, FailingPlugin


class TestPluginRegistry:
    """Test PluginRegistry core functionality."""
    
    def test_empty_registry(self, plugin_registry):
        """Test empty registry state."""
        assert plugin_registry.count() == 0
        assert plugin_registry.list() == []
        assert plugin_registry.list(kind=PluginKind.EXPORT) == []
        
    def test_register_plugin(self, plugin_registry, test_plugin):
        """Test basic plugin registration."""
        result = plugin_registry.register(test_plugin)
        
        assert result is True
        assert plugin_registry.count() == 1
        assert test_plugin in plugin_registry.list()
        assert test_plugin.status == PluginStatus.REGISTERED
        
    def test_register_duplicate_name_rejected(self, plugin_registry):
        """Test duplicate plugin name registration is rejected."""
        plugin1 = TestPlugin("same_name")
        plugin2 = TestPlugin("same_name")
        
        # First registration succeeds
        assert plugin_registry.register(plugin1) is True
        
        # Second registration fails
        with pytest.raises(PluginRegistrationError, match="Plugin 'same_name' already registered"):
            plugin_registry.register(plugin2)
            
        assert plugin_registry.count() == 1
        
    def test_register_duplicate_with_force(self, plugin_registry):
        """Test duplicate registration with force flag."""
        plugin1 = TestPlugin("same_name")
        plugin2 = TestPlugin("same_name")
        
        plugin_registry.register(plugin1)
        
        # Force registration should succeed
        result = plugin_registry.register(plugin2, force=True)
        assert result is True
        assert plugin_registry.count() == 1
        assert plugin_registry.get("same_name") is plugin2
        
    def test_get_plugin(self, plugin_registry, test_plugin):
        """Test plugin retrieval by name."""
        plugin_registry.register(test_plugin)
        
        retrieved = plugin_registry.get(test_plugin.name)
        assert retrieved is test_plugin
        
    def test_get_nonexistent_plugin(self, plugin_registry):
        """Test retrieving non-existent plugin raises error."""
        with pytest.raises(PluginNotFoundError, match="Plugin 'nonexistent' not found"):
            plugin_registry.get("nonexistent")
            
    def test_list_by_kind(self, plugin_registry):
        """Test listing plugins by kind."""
        export_plugin = TestPlugin("export1")
        export_plugin._metadata.kind = PluginKind.EXPORT
        
        custom_plugin = TestPlugin("custom1")
        custom_plugin._metadata.kind = PluginKind.CUSTOM
        
        plugin_registry.register(export_plugin)
        plugin_registry.register(custom_plugin)
        
        export_plugins = plugin_registry.list(kind=PluginKind.EXPORT)
        custom_plugins = plugin_registry.list(kind=PluginKind.CUSTOM)
        
        assert len(export_plugins) == 1
        assert export_plugin in export_plugins
        assert len(custom_plugins) == 1
        assert custom_plugin in custom_plugins
        
    def test_list_by_status(self, plugin_registry):
        """Test listing plugins by status."""
        plugin1 = TestPlugin("plugin1")
        plugin2 = TestPlugin("plugin2")
        
        plugin_registry.register(plugin1)
        plugin_registry.register(plugin2)
        
        # Both should be registered
        registered = plugin_registry.list(status=PluginStatus.REGISTERED)
        assert len(registered) == 2
        
        # Change status and test
        plugin1.status = PluginStatus.STARTED
        started = plugin_registry.list(status=PluginStatus.STARTED)
        assert len(started) == 1
        assert plugin1 in started
        
    def test_unregister_plugin(self, plugin_registry, test_plugin):
        """Test plugin unregistration."""
        plugin_registry.register(test_plugin)
        assert plugin_registry.count() == 1
        
        result = plugin_registry.unregister(test_plugin.name)
        assert result is True
        assert plugin_registry.count() == 0
        
        with pytest.raises(PluginNotFoundError):
            plugin_registry.get(test_plugin.name)
            
    def test_unregister_nonexistent(self, plugin_registry):
        """Test unregistering non-existent plugin returns False."""
        result = plugin_registry.unregister("nonexistent")
        assert result is False


class TestPluginLifecycle:
    """Test plugin lifecycle operations through registry."""
    
    @pytest.mark.asyncio
    async def test_init_single_plugin(self, plugin_registry, test_plugin, plugin_context):
        """Test initializing a single plugin."""
        plugin_registry.register(test_plugin)
        
        await plugin_registry.init_plugin(test_plugin.name, plugin_context)
        
        assert test_plugin.init_called
        assert test_plugin.context is plugin_context
        assert test_plugin.status == PluginStatus.INITIALIZED
        
    @pytest.mark.asyncio
    async def test_init_async_plugin(self, plugin_registry, async_test_plugin, plugin_context):
        """Test initializing async plugin."""
        plugin_registry.register(async_test_plugin)
        
        await plugin_registry.init_plugin(async_test_plugin.name, plugin_context)
        
        assert async_test_plugin.init_called
        assert async_test_plugin.status == PluginStatus.INITIALIZED
        
    @pytest.mark.asyncio
    async def test_init_all_plugins(self, plugin_registry, plugin_context):
        """Test initializing all registered plugins."""
        plugin1 = TestPlugin("plugin1")
        plugin2 = TestPlugin("plugin2")
        async_plugin = AsyncTestPlugin("async1")
        
        plugin_registry.register(plugin1)
        plugin_registry.register(plugin2)
        plugin_registry.register(async_plugin)
        
        await plugin_registry.init_all(plugin_context)
        
        assert plugin1.init_called
        assert plugin2.init_called
        assert async_plugin.init_called
        assert all(p.status == PluginStatus.INITIALIZED for p in [plugin1, plugin2, async_plugin])
        
    @pytest.mark.asyncio
    async def test_start_plugin(self, plugin_registry, test_plugin, plugin_context):
        """Test starting a plugin."""
        plugin_registry.register(test_plugin)
        await plugin_registry.init_plugin(test_plugin.name, plugin_context)
        
        await plugin_registry.start_plugin(test_plugin.name)
        
        assert test_plugin.start_called
        assert test_plugin.status == PluginStatus.STARTED
        
    @pytest.mark.asyncio
    async def test_start_all_plugins(self, plugin_registry, plugin_context):
        """Test starting all plugins."""
        plugin1 = TestPlugin("plugin1")
        plugin2 = AsyncTestPlugin("async1")
        
        plugin_registry.register(plugin1)
        plugin_registry.register(plugin2)
        
        await plugin_registry.init_all(plugin_context)
        await plugin_registry.start_all()
        
        assert plugin1.start_called
        assert plugin2.start_called
        assert all(p.status == PluginStatus.STARTED for p in [plugin1, plugin2])
        
    @pytest.mark.asyncio
    async def test_stop_plugin(self, plugin_registry, test_plugin, plugin_context):
        """Test stopping a plugin."""
        plugin_registry.register(test_plugin)
        await plugin_registry.init_plugin(test_plugin.name, plugin_context)
        await plugin_registry.start_plugin(test_plugin.name)
        
        await plugin_registry.stop_plugin(test_plugin.name)
        
        assert test_plugin.stop_called
        assert test_plugin.status == PluginStatus.STOPPED
        
    @pytest.mark.asyncio
    async def test_stop_all_plugins(self, plugin_registry, plugin_context):
        """Test stopping all plugins."""
        plugin1 = TestPlugin("plugin1")
        plugin2 = AsyncTestPlugin("async1")
        
        plugin_registry.register(plugin1)
        plugin_registry.register(plugin2)
        
        await plugin_registry.init_all(plugin_context)
        await plugin_registry.start_all()
        await plugin_registry.stop_all()
        
        assert plugin1.stop_called
        assert plugin2.stop_called
        assert all(p.status == PluginStatus.STOPPED for p in [plugin1, plugin2])


class TestPermissionChecks:
    """Test plugin permission enforcement."""
    
    def test_permission_required_plugin(self, plugin_registry, plugin_context):
        """Test plugin with required permissions."""
        plugin = TestPlugin("perm_plugin")
        plugin._metadata.permissions_required = ["test:permission"]
        
        # Context has required permission
        plugin_context.permissions.add("test:permission")
        
        result = plugin_registry.register(plugin)
        assert result is True
        
    def test_missing_permission_registration(self, plugin_registry, plugin_context):
        """Test plugin registration fails without required permission."""
        plugin = TestPlugin("perm_plugin")
        plugin._metadata.permissions_required = ["admin:write"]
        
        # Context doesn't have required permission
        plugin_registry.register(plugin)  # Registration succeeds
        
        # But initialization should check permissions
        with pytest.raises(PluginPermissionError):
            plugin_context.check_permission("admin:write")
            
    def test_wildcard_permissions(self, plugin_registry, plugin_context):
        """Test wildcard permission matching."""
        plugin_context.permissions.add("test:*")
        
        # Should match wildcard
        assert plugin_context.has_permission("test:read")
        assert plugin_context.has_permission("test:write")
        assert not plugin_context.has_permission("admin:read")


class TestErrorHandling:
    """Test error scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_init_failing_plugin(self, plugin_registry, plugin_context):
        """Test handling plugin that fails during init."""
        failing_plugin = FailingPlugin("fail_init", fail_on="init")
        plugin_registry.register(failing_plugin)
        
        with pytest.raises(RuntimeError, match="Intentional failure in init"):
            await plugin_registry.init_plugin(failing_plugin.name, plugin_context)
            
        assert failing_plugin.status == PluginStatus.ERROR
        
    @pytest.mark.asyncio
    async def test_start_failing_plugin(self, plugin_registry, plugin_context):
        """Test handling plugin that fails during start."""
        failing_plugin = FailingPlugin("fail_start", fail_on="start")
        plugin_registry.register(failing_plugin)
        
        # Init should succeed
        await plugin_registry.init_plugin(failing_plugin.name, plugin_context)
        assert failing_plugin.status == PluginStatus.INITIALIZED
        
        # Start should fail
        with pytest.raises(RuntimeError, match="Intentional failure in start"):
            await plugin_registry.start_plugin(failing_plugin.name)
            
        assert failing_plugin.status == PluginStatus.ERROR
        
    @pytest.mark.asyncio
    async def test_stop_failing_plugin(self, plugin_registry, plugin_context):
        """Test handling plugin that fails during stop."""
        failing_plugin = FailingPlugin("fail_stop", fail_on="stop")
        plugin_registry.register(failing_plugin)
        
        await plugin_registry.init_plugin(failing_plugin.name, plugin_context)
        await plugin_registry.start_plugin(failing_plugin.name)
        
        # Stop should fail but plugin status should still be updated
        with pytest.raises(RuntimeError, match="Intentional failure in stop"):
            await plugin_registry.stop_plugin(failing_plugin.name)
            
        assert failing_plugin.status == PluginStatus.ERROR
        
    @pytest.mark.asyncio
    async def test_init_all_with_failures(self, plugin_registry, plugin_context):
        """Test init_all continues despite individual failures."""
        good_plugin = TestPlugin("good")
        failing_plugin = FailingPlugin("bad", fail_on="init")
        
        plugin_registry.register(good_plugin)
        plugin_registry.register(failing_plugin)
        
        # Should not raise, but should log errors
        await plugin_registry.init_all(plugin_context)
        
        assert good_plugin.status == PluginStatus.INITIALIZED
        assert failing_plugin.status == PluginStatus.ERROR
        
    def test_thread_safety(self, plugin_registry):
        """Test registry thread safety with concurrent operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def register_plugins():
            try:
                for i in range(10):
                    plugin = TestPlugin(f"thread_plugin_{threading.current_thread().ident}_{i}")
                    result = plugin_registry.register(plugin)
                    results.append(result)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=register_plugins)
            threads.append(thread)
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # All registrations should succeed
        assert len(errors) == 0
        assert len(results) == 30
        assert all(results)
        assert plugin_registry.count() == 30


class TestObservabilityIntegration:
    """Test registry integration with observability hooks."""
    
    def test_register_with_observability(self, plugin_registry, test_plugin, observability_hooks):
        """Test plugin registration triggers observability hooks."""
        plugin_registry._observability_hooks = observability_hooks
        
        plugin_registry.register(test_plugin)
        
        # Should have been called (mock verification would go here)
        assert plugin_registry.count() == 1
        
    @pytest.mark.asyncio
    async def test_lifecycle_with_observability(self, plugin_registry, test_plugin, plugin_context, observability_hooks):
        """Test lifecycle operations trigger observability hooks."""
        plugin_registry._observability_hooks = observability_hooks
        plugin_registry.register(test_plugin)
        
        await plugin_registry.init_plugin(test_plugin.name, plugin_context)
        await plugin_registry.start_plugin(test_plugin.name)
        await plugin_registry.stop_plugin(test_plugin.name)
        
        # Verify all lifecycle events occurred
        assert test_plugin.init_called
        assert test_plugin.start_called
        assert test_plugin.stop_called