"""Tests for plugin registry."""

import pytest
import weakref
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

from dotmac_isp.plugins.core.base import (
    BasePlugin, PluginInfo, PluginConfig, PluginAPI, 
    PluginStatus, PluginCategory
)
from dotmac_isp.plugins.core.registry import PluginRegistry, plugin_registry
from dotmac_isp.plugins.core.exceptions import (
    PluginRegistrationError, PluginDependencyError
)


class TestPlugin1(BasePlugin):
    """Test plugin 1 for testing."""
    
    @property
    def plugin_info(self):
        return PluginInfo(
            id="test_plugin_1",
            name="Test Plugin 1",
            version="1.0.0",
            description="Test plugin 1",
            author="Test",
            category=PluginCategory.CUSTOM
        )
    
    async def initialize(self): pass
    async def activate(self): pass
    async def deactivate(self): pass
    async def cleanup(self): pass


class TestPlugin2(BasePlugin):
    """Test plugin 2 for testing."""
    
    @property
    def plugin_info(self):
        return PluginInfo(
            id="test_plugin_2",
            name="Test Plugin 2",
            version="2.0.0",
            description="Test plugin 2",
            author="Test",
            category=PluginCategory.NETWORK_AUTOMATION,
            dependencies=["test_plugin_1"]
        )
    
    async def initialize(self): pass
    async def activate(self): pass
    async def deactivate(self): pass
    async def cleanup(self): pass


class TestPlugin3(BasePlugin):
    """Test plugin 3 for testing."""
    
    @property
    def plugin_info(self):
        return PluginInfo(
            id="test_plugin_3",
            name="Test Plugin 3",
            version="1.5.0",
            description="Test plugin 3",
            author="Test",
            category=PluginCategory.BILLING_INTEGRATION,
            dependencies=["test_plugin_1", "test_plugin_2"]
        )
    
    async def initialize(self): pass
    async def activate(self): pass
    async def deactivate(self): pass
    async def cleanup(self): pass


class TestPluginRegistry:
    """Test PluginRegistry class."""
    
    def setup_method(self):
        """Set up fresh registry for each test."""
        self.registry = PluginRegistry()
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = PluginRegistry()
        
        assert registry._plugins == {}
        assert registry._plugin_info == {}
        assert registry._plugin_instances == {}
        assert registry._plugin_configs == {}
        assert registry._plugin_dependencies == {}
        assert registry._plugin_dependents == {}
        assert registry._load_order == []
        assert len(registry._category_plugins) == len(PluginCategory)
        assert registry._event_listeners == {}
        
        # Check category mappings are initialized
        for category in PluginCategory:
            assert category in registry._category_plugins
            assert registry._category_plugins[category] == set()
    
    def test_register_plugin_basic(self):
        """Test basic plugin registration."""
        self.registry.register_plugin(TestPlugin1)
        
        # Check plugin is registered
        assert "test_plugin_1" in self.registry._plugins
        assert self.registry._plugins["test_plugin_1"] == TestPlugin1
        
        # Check plugin info is stored
        assert "test_plugin_1" in self.registry._plugin_info
        info = self.registry._plugin_info["test_plugin_1"]
        assert info.id == "test_plugin_1"
        assert info.name == "Test Plugin 1"
        
        # Check category mapping
        assert "test_plugin_1" in self.registry._category_plugins[PluginCategory.CUSTOM]
        
        # Check dependencies
        assert self.registry._plugin_dependencies["test_plugin_1"] == set()
        
        # Check load order
        assert self.registry._load_order == ["test_plugin_1"]
    
    def test_register_plugin_with_dependencies(self):
        """Test plugin registration with dependencies."""
        # Register dependency first
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)
        
        # Check dependencies are stored
        assert self.registry._plugin_dependencies["test_plugin_2"] == {"test_plugin_1"}
        assert self.registry._plugin_dependents["test_plugin_1"] == {"test_plugin_2"}
        
        # Check load order respects dependencies
        assert self.registry._load_order.index("test_plugin_1") < self.registry._load_order.index("test_plugin_2")
    
    def test_register_plugin_with_explicit_info(self):
        """Test plugin registration with explicit plugin info."""
        custom_info = PluginInfo(
            id="custom_plugin",
            name="Custom Plugin",
            version="3.0.0",
            description="Custom plugin",
            author="Custom Author",
            category=PluginCategory.MONITORING
        )
        
        self.registry.register_plugin(TestPlugin1, custom_info)
        
        # Should use the provided info instead of plugin's info
        assert "custom_plugin" in self.registry._plugins
        stored_info = self.registry._plugin_info["custom_plugin"]
        assert stored_info.id == "custom_plugin"
        assert stored_info.name == "Custom Plugin"
        assert stored_info.version == "3.0.0"
    
    def test_register_plugin_duplicate_id_error(self):
        """Test registering plugin with duplicate ID raises error."""
        self.registry.register_plugin(TestPlugin1)
        
        with pytest.raises(PluginRegistrationError) as exc_info:
            self.registry.register_plugin(TestPlugin1)
        
        assert "already registered" in str(exc_info.value)
        assert "test_plugin_1" in str(exc_info.value)
    
    def test_unregister_plugin_basic(self):
        """Test basic plugin unregistration."""
        # Register and then unregister
        self.registry.register_plugin(TestPlugin1)
        assert "test_plugin_1" in self.registry._plugins
        
        self.registry.unregister_plugin("test_plugin_1")
        
        # Check plugin is removed
        assert "test_plugin_1" not in self.registry._plugins
        assert "test_plugin_1" not in self.registry._plugin_info
        assert "test_plugin_1" not in self.registry._plugin_dependencies
        assert "test_plugin_1" not in self.registry._category_plugins[PluginCategory.CUSTOM]
    
    def test_unregister_plugin_with_dependents_error(self):
        """Test unregistering plugin with loaded dependents raises error."""
        # Register plugins with dependency
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)
        
        # Add mock instance for dependent
        mock_instance = MagicMock()
        self.registry._plugin_instances["test_plugin_2"] = mock_instance
        
        # Should raise error when trying to unregister plugin with loaded dependents
        with pytest.raises(PluginDependencyError) as exc_info:
            self.registry.unregister_plugin("test_plugin_1")
        
        assert "loaded dependents" in str(exc_info.value)
    
    def test_unregister_nonexistent_plugin(self):
        """Test unregistering non-existent plugin does nothing."""
        # Should not raise error
        self.registry.unregister_plugin("nonexistent_plugin")
    
    def test_get_plugin_class(self):
        """Test getting plugin class."""
        self.registry.register_plugin(TestPlugin1)
        
        plugin_class = self.registry.get_plugin_class("test_plugin_1")
        assert plugin_class == TestPlugin1
        
        assert self.registry.get_plugin_class("nonexistent") is None
    
    def test_get_plugin_info(self):
        """Test getting plugin info."""
        self.registry.register_plugin(TestPlugin1)
        
        info = self.registry.get_plugin_info("test_plugin_1")
        assert info.id == "test_plugin_1"
        assert info.name == "Test Plugin 1"
        
        assert self.registry.get_plugin_info("nonexistent") is None
    
    def test_plugin_instance_operations(self):
        """Test plugin instance operations."""
        mock_instance = MagicMock()
        
        # Initially no instance
        assert self.registry.get_plugin_instance("test_plugin") is None
        
        # Set instance
        self.registry.set_plugin_instance("test_plugin", mock_instance)
        assert self.registry.get_plugin_instance("test_plugin") == mock_instance
        
        # Remove instance
        self.registry.remove_plugin_instance("test_plugin")
        assert self.registry.get_plugin_instance("test_plugin") is None
    
    def test_plugin_config_operations(self):
        """Test plugin config operations."""
        config = PluginConfig(enabled=False)
        
        # Initially no config
        assert self.registry.get_plugin_config("test_plugin") is None
        
        # Set config
        self.registry.set_plugin_config("test_plugin", config)
        assert self.registry.get_plugin_config("test_plugin") == config
    
    def test_list_plugins_no_filters(self):
        """Test listing plugins without filters."""
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)
        
        plugins = self.registry.list_plugins()
        
        assert set(plugins) == {"test_plugin_1", "test_plugin_2"}
    
    def test_list_plugins_with_category_filter(self):
        """Test listing plugins with category filter."""
        self.registry.register_plugin(TestPlugin1)  # CUSTOM
        self.registry.register_plugin(TestPlugin2)  # NETWORK_AUTOMATION
        
        custom_plugins = self.registry.list_plugins(category=PluginCategory.CUSTOM)
        assert custom_plugins == ["test_plugin_1"]
        
        network_plugins = self.registry.list_plugins(category=PluginCategory.NETWORK_AUTOMATION)
        assert network_plugins == ["test_plugin_2"]
    
    def test_list_plugins_with_status_filter(self):
        """Test listing plugins with status filter."""
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)
        
        # Add mock instances with different statuses
        mock_instance1 = MagicMock()
        mock_instance1.status = PluginStatus.ACTIVE
        mock_instance2 = MagicMock()
        mock_instance2.status = PluginStatus.INACTIVE
        
        self.registry.set_plugin_instance("test_plugin_1", mock_instance1)
        self.registry.set_plugin_instance("test_plugin_2", mock_instance2)
        
        active_plugins = self.registry.list_plugins(status=PluginStatus.ACTIVE)
        assert active_plugins == ["test_plugin_1"]
        
        inactive_plugins = self.registry.list_plugins(status=PluginStatus.INACTIVE)
        assert inactive_plugins == ["test_plugin_2"]
    
    def test_get_plugins_by_category(self):
        """Test getting plugins by category."""
        self.registry.register_plugin(TestPlugin1)  # CUSTOM
        self.registry.register_plugin(TestPlugin2)  # NETWORK_AUTOMATION
        
        custom_plugins = self.registry.get_plugins_by_category(PluginCategory.CUSTOM)
        
        assert len(custom_plugins) == 1
        assert "test_plugin_1" in custom_plugins
        assert custom_plugins["test_plugin_1"].name == "Test Plugin 1"
    
    def test_dependency_operations(self):
        """Test dependency-related operations."""
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)  # depends on test_plugin_1
        
        # Test get dependencies
        deps = self.registry.get_plugin_dependencies("test_plugin_2")
        assert deps == {"test_plugin_1"}
        
        # Test get dependents
        dependents = self.registry.get_plugin_dependents("test_plugin_1")
        assert dependents == {"test_plugin_2"}
    
    def test_validate_dependencies(self):
        """Test dependency validation."""
        self.registry.register_plugin(TestPlugin1)
        
        # Valid dependencies (plugin 1 has no deps)
        missing = self.registry.validate_dependencies("test_plugin_1")
        assert missing == []
        
        # Register plugin with missing dependency
        self.registry.register_plugin(TestPlugin2)  # depends on test_plugin_1 (exists)
        missing = self.registry.validate_dependencies("test_plugin_2")
        assert missing == []
        
        # Create plugin with missing dependency
        class BadPlugin(BasePlugin):
            @property
            def plugin_info(self):
                return PluginInfo(
                    id="bad_plugin",
                    name="Bad Plugin",
                    version="1.0.0",
                    description="Bad plugin",
                    author="Test",
                    category=PluginCategory.CUSTOM,
                    dependencies=["missing_dependency"]
                )
            async def initialize(self): pass
            async def activate(self): pass
            async def deactivate(self): pass
            async def cleanup(self): pass
        
        self.registry.register_plugin(BadPlugin)
        missing = self.registry.validate_dependencies("bad_plugin")
        assert missing == ["missing_dependency"]
    
    def test_can_load_plugin(self):
        """Test can_load_plugin check."""
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)
        
        # Plugin 1 has no dependencies, can load
        assert self.registry.can_load_plugin("test_plugin_1") is True
        
        # Plugin 2 depends on plugin 1, can load since plugin 1 is registered
        assert self.registry.can_load_plugin("test_plugin_2") is True
    
    def test_calculate_load_order_simple(self):
        """Test load order calculation with simple dependencies."""
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)  # depends on 1
        self.registry.register_plugin(TestPlugin3)  # depends on 1, 2
        
        load_order = self.registry.get_load_order()
        
        # Check that dependencies come before dependents
        idx1 = load_order.index("test_plugin_1")
        idx2 = load_order.index("test_plugin_2")
        idx3 = load_order.index("test_plugin_3")
        
        assert idx1 < idx2  # 1 before 2
        assert idx1 < idx3  # 1 before 3
        assert idx2 < idx3  # 2 before 3
    
    def test_calculate_load_order_circular_dependency(self):
        """Test load order calculation handles circular dependencies."""
        class CircularPlugin1(BasePlugin):
            @property
            def plugin_info(self):
                return PluginInfo(
                    id="circular_1", name="Circular 1", version="1.0.0",
                    description="", author="", category=PluginCategory.CUSTOM,
                    dependencies=["circular_2"]
                )
            async def initialize(self): pass
            async def activate(self): pass
            async def deactivate(self): pass
            async def cleanup(self): pass
        
        class CircularPlugin2(BasePlugin):
            @property
            def plugin_info(self):
                return PluginInfo(
                    id="circular_2", name="Circular 2", version="1.0.0",
                    description="", author="", category=PluginCategory.CUSTOM,
                    dependencies=["circular_1"]
                )
            async def initialize(self): pass
            async def activate(self): pass
            async def deactivate(self): pass
            async def cleanup(self): pass
        
        # Should not crash with circular dependency
        self.registry.register_plugin(CircularPlugin1)
        self.registry.register_plugin(CircularPlugin2)
        
        load_order = self.registry.get_load_order()
        
        # Both plugins should be in the order (circular dependencies handled)
        assert "circular_1" in load_order
        assert "circular_2" in load_order
        assert len(load_order) == 2
    
    def test_event_listener_operations(self):
        """Test event listener operations."""
        callback_calls = []
        
        def test_callback(event_type, event_data):
            callback_calls.append((event_type, event_data))
        
        # Add listener
        self.registry.add_event_listener("test_event", test_callback)
        
        # Trigger event
        self.registry._notify_listeners("test_event", {"data": "test"})
        
        # Check callback was called
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test_event", {"data": "test"})
        
        # Remove listener
        self.registry.remove_event_listener("test_event", test_callback)
        
        # Trigger event again
        self.registry._notify_listeners("test_event", {"data": "test2"})
        
        # Should not be called again
        assert len(callback_calls) == 1
    
    def test_event_listener_weak_references(self):
        """Test event listeners use weak references."""
        callback_calls = []
        
        class TestCallback:
            def __call__(self, event_type, event_data):
                callback_calls.append((event_type, event_data))
        
        callback = TestCallback()
        self.registry.add_event_listener("test_event", callback)
        
        # Trigger event
        self.registry._notify_listeners("test_event", {"data": "test"})
        assert len(callback_calls) == 1
        
        # Delete callback and trigger garbage collection
        del callback
        import gc
        gc.collect()
        
        # Trigger event again - should clean up dead reference
        self.registry._notify_listeners("test_event", {"data": "test2"})
        
        # Should still be 1 (dead reference cleaned up)
        assert len(callback_calls) == 1
    
    async def test_async_event_listener(self):
        """Test async event listeners."""
        callback_calls = []
        
        async def async_callback(event_type, event_data):
            callback_calls.append((event_type, event_data))
        
        self.registry.add_event_listener("test_event", async_callback)
        
        # Trigger event
        self.registry._notify_listeners("test_event", {"data": "test"})
        
        # Give a moment for async task to complete
        await asyncio.sleep(0.1)
        
        assert len(callback_calls) == 1
    
    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        # Register plugins
        self.registry.register_plugin(TestPlugin1)
        self.registry.register_plugin(TestPlugin2)
        
        # Add instance
        mock_instance = MagicMock()
        mock_instance.status = PluginStatus.ACTIVE
        self.registry.set_plugin_instance("test_plugin_1", mock_instance)
        
        stats = self.registry.get_registry_stats()
        
        assert stats["total_registered"] == 2
        assert stats["total_loaded"] == 1
        assert stats["categories"][PluginCategory.CUSTOM.value] == 1
        assert stats["categories"][PluginCategory.NETWORK_AUTOMATION.value] == 1
        assert stats["status_distribution"]["active"] == 1
        assert stats["load_order_length"] == 2


class TestGlobalPluginRegistry:
    """Test global plugin registry instance."""
    
    def test_global_registry_exists(self):
        """Test that global plugin registry exists."""
        assert plugin_registry is not None
        assert isinstance(plugin_registry, PluginRegistry)
    
    def test_global_registry_singleton_behavior(self):
        """Test global registry behaves like singleton."""
        from dotmac_isp.plugins.core.registry import plugin_registry as registry2
        
        assert plugin_registry is registry2