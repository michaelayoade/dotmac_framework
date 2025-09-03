"""
Test suite for plugin discovery functionality.

Tests entry point discovery, namespace package discovery,
plugin validation, and factory creation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from types import ModuleType
import sys

from dotmac.plugins import (
    PluginDiscovery,
    discover_plugins,
    discover_entry_points_only,
    discover_namespace_only,
    validate_plugin_requirements,
    create_plugin_factory,
    PluginDiscoveryError,
    PluginKind,
    IPlugin,
)
from conftest import TestPlugin, TestExportPlugin


class TestPluginDiscovery:
    """Test PluginDiscovery class functionality."""
    
    def test_discovery_initialization(self):
        """Test PluginDiscovery initialization."""
        discovery = PluginDiscovery()
        assert discovery is not None
        
    @patch('importlib.metadata.entry_points')
    def test_discover_entry_points_empty(self, mock_entry_points):
        """Test entry point discovery with no plugins."""
        mock_entry_points.return_value = []
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_entry_points("dotmac.plugins")
        
        assert plugins == []
        mock_entry_points.assert_called_once()
        
    @patch('importlib.metadata.entry_points')
    def test_discover_entry_points_with_plugins(self, mock_entry_points):
        """Test entry point discovery with mock plugins."""
        # Create mock entry point
        mock_ep = Mock()
        mock_ep.name = "test_plugin"
        mock_ep.load.return_value = TestPlugin
        mock_entry_points.return_value = [mock_ep]
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_entry_points("dotmac.plugins")
        
        assert len(plugins) == 1
        assert isinstance(plugins[0], TestPlugin)
        mock_ep.load.assert_called_once()
        
    @patch('importlib.metadata.entry_points')
    def test_discover_entry_points_load_failure(self, mock_entry_points):
        """Test entry point discovery handles load failures."""
        mock_ep = Mock()
        mock_ep.name = "failing_plugin"
        mock_ep.load.side_effect = ImportError("Module not found")
        mock_entry_points.return_value = [mock_ep]
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_entry_points("dotmac.plugins")
        
        # Should skip failed plugins and continue
        assert plugins == []
        
    @patch('importlib.metadata.entry_points')
    def test_discover_entry_points_invalid_plugin(self, mock_entry_points):
        """Test entry point discovery handles invalid plugin classes."""
        mock_ep = Mock()
        mock_ep.name = "invalid_plugin"
        mock_ep.load.return_value = str  # Not a plugin class
        mock_entry_points.return_value = [mock_ep]
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_entry_points("dotmac.plugins")
        
        # Should skip invalid plugins
        assert plugins == []
        
    @patch('pkgutil.iter_modules')
    def test_discover_namespace_packages_empty(self, mock_iter_modules):
        """Test namespace discovery with no packages."""
        mock_iter_modules.return_value = []
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_namespace_packages("dotmac_plugins")
        
        assert plugins == []
        
    @patch('pkgutil.iter_modules')
    @patch('importlib.import_module')
    def test_discover_namespace_packages_with_plugin(self, mock_import_module, mock_iter_modules):
        """Test namespace discovery with mock plugin module."""
        # Mock module info
        mock_module_info = Mock()
        mock_module_info.name = "test_plugin"
        mock_iter_modules.return_value = [mock_module_info]
        
        # Mock module with PLUGIN attribute
        mock_module = Mock(spec=ModuleType)
        mock_module.PLUGIN = TestPlugin
        mock_import_module.return_value = mock_module
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_namespace_packages("dotmac_plugins")
        
        assert len(plugins) == 1
        assert isinstance(plugins[0], TestPlugin)
        
    @patch('pkgutil.iter_modules')
    @patch('importlib.import_module')
    def test_discover_namespace_packages_with_factory(self, mock_import_module, mock_iter_modules):
        """Test namespace discovery with plugin factory."""
        mock_module_info = Mock()
        mock_module_info.name = "factory_plugin"
        mock_iter_modules.return_value = [mock_module_info]
        
        # Mock module with PLUGIN_FACTORY attribute
        mock_module = Mock(spec=ModuleType)
        mock_module.PLUGIN_FACTORY = lambda: TestPlugin("factory_created")
        mock_import_module.return_value = mock_module
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_namespace_packages("dotmac_plugins")
        
        assert len(plugins) == 1
        assert isinstance(plugins[0], TestPlugin)
        assert plugins[0].name == "factory_created"
        
    @patch('pkgutil.iter_modules')
    @patch('importlib.import_module')
    def test_discover_namespace_packages_import_failure(self, mock_import_module, mock_iter_modules):
        """Test namespace discovery handles import failures."""
        mock_module_info = Mock()
        mock_module_info.name = "broken_plugin"
        mock_iter_modules.return_value = [mock_module_info]
        
        mock_import_module.side_effect = ImportError("Broken module")
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_namespace_packages("dotmac_plugins")
        
        # Should skip broken modules
        assert plugins == []
        
    @patch('pkgutil.iter_modules')
    @patch('importlib.import_module')
    def test_discover_namespace_packages_no_plugin_attribute(self, mock_import_module, mock_iter_modules):
        """Test namespace discovery skips modules without plugin attributes."""
        mock_module_info = Mock()
        mock_module_info.name = "no_plugin"
        mock_iter_modules.return_value = [mock_module_info]
        
        # Mock module without PLUGIN or PLUGIN_FACTORY
        mock_module = Mock(spec=ModuleType)
        del mock_module.PLUGIN  # Ensure attribute doesn't exist
        del mock_module.PLUGIN_FACTORY
        mock_import_module.return_value = mock_module
        
        discovery = PluginDiscovery()
        plugins = discovery.discover_namespace_packages("dotmac_plugins")
        
        assert plugins == []


class TestDiscoveryFunctions:
    """Test module-level discovery functions."""
    
    @patch('dotmac.plugins.discovery.PluginDiscovery')
    def test_discover_plugins(self, mock_discovery_class):
        """Test discover_plugins convenience function."""
        mock_discovery = Mock()
        mock_discovery.discover_entry_points.return_value = [TestPlugin("ep1")]
        mock_discovery.discover_namespace_packages.return_value = [TestPlugin("ns1")]
        mock_discovery_class.return_value = mock_discovery
        
        plugins = discover_plugins()
        
        assert len(plugins) == 2
        assert plugins[0].name == "ep1"
        assert plugins[1].name == "ns1"
        
        mock_discovery.discover_entry_points.assert_called_once_with("dotmac.plugins")
        mock_discovery.discover_namespace_packages.assert_called_once_with("dotmac_plugins")
        
    @patch('dotmac.plugins.discovery.PluginDiscovery')
    def test_discover_entry_points_only(self, mock_discovery_class):
        """Test discover_entry_points_only function."""
        mock_discovery = Mock()
        mock_discovery.discover_entry_points.return_value = [TestPlugin("ep1")]
        mock_discovery_class.return_value = mock_discovery
        
        plugins = discover_entry_points_only("custom.plugins")
        
        assert len(plugins) == 1
        assert plugins[0].name == "ep1"
        mock_discovery.discover_entry_points.assert_called_once_with("custom.plugins")
        
    @patch('dotmac.plugins.discovery.PluginDiscovery')
    def test_discover_namespace_only(self, mock_discovery_class):
        """Test discover_namespace_only function."""
        mock_discovery = Mock()
        mock_discovery.discover_namespace_packages.return_value = [TestPlugin("ns1")]
        mock_discovery_class.return_value = mock_discovery
        
        plugins = discover_namespace_only("custom_plugins")
        
        assert len(plugins) == 1
        assert plugins[0].name == "ns1"
        mock_discovery.discover_namespace_packages.assert_called_once_with("custom_plugins")


class TestPluginValidation:
    """Test plugin validation functionality."""
    
    def test_validate_plugin_requirements_valid(self):
        """Test validation of valid plugin."""
        plugin = TestPlugin("valid")
        
        result = validate_plugin_requirements(plugin)
        
        assert result is True
        
    def test_validate_plugin_requirements_invalid_interface(self):
        """Test validation rejects non-plugin objects."""
        invalid_plugin = "not a plugin"
        
        result = validate_plugin_requirements(invalid_plugin)
        
        assert result is False
        
    def test_validate_plugin_requirements_missing_methods(self):
        """Test validation of plugin missing required methods."""
        class IncompletePlugin:
            def __init__(self):
                self.name = "incomplete"
                
        plugin = IncompletePlugin()
        
        result = validate_plugin_requirements(plugin)
        
        assert result is False
        
    def test_validate_plugin_requirements_with_dependencies(self):
        """Test validation with plugin dependencies."""
        plugin = TestPlugin("with_deps")
        plugin._metadata.dependencies = ["required_plugin>=1.0.0"]
        
        # Without checking dependencies (default behavior)
        result = validate_plugin_requirements(plugin, check_dependencies=False)
        assert result is True
        
        # With dependency checking - would need mock registry
        result = validate_plugin_requirements(plugin, check_dependencies=True)
        # Since we don't have required_plugin available, validation should fail
        assert result is False


class TestPluginFactory:
    """Test plugin factory creation."""
    
    def test_create_plugin_factory_class(self):
        """Test factory creation from plugin class."""
        factory = create_plugin_factory(TestPlugin)
        
        assert callable(factory)
        
        plugin = factory()
        assert isinstance(plugin, TestPlugin)
        
    def test_create_plugin_factory_instance(self):
        """Test factory creation from plugin instance."""
        plugin_instance = TestPlugin("instance")
        factory = create_plugin_factory(plugin_instance)
        
        assert callable(factory)
        
        # Should return the same instance
        result = factory()
        assert result is plugin_instance
        
    def test_create_plugin_factory_callable(self):
        """Test factory creation from existing callable."""
        def existing_factory():
            return TestPlugin("from_callable")
            
        factory = create_plugin_factory(existing_factory)
        
        # Should return the same callable
        assert factory is existing_factory
        
        plugin = factory()
        assert isinstance(plugin, TestPlugin)
        assert plugin.name == "from_callable"
        
    def test_create_plugin_factory_invalid(self):
        """Test factory creation with invalid input."""
        with pytest.raises(PluginDiscoveryError, match="Invalid plugin type"):
            create_plugin_factory("not a plugin")
            
    def test_create_plugin_factory_with_args(self):
        """Test factory creation with arguments."""
        factory = create_plugin_factory(TestPlugin, name="custom_name", version="2.0.0")
        
        plugin = factory()
        assert isinstance(plugin, TestPlugin)
        assert plugin.name == "custom_name"
        assert plugin.version == "2.0.0"


class TestDiscoveryIntegration:
    """Integration tests for discovery system."""
    
    def test_full_discovery_pipeline(self):
        """Test complete discovery pipeline with mocked plugins."""
        with patch('importlib.metadata.entry_points') as mock_ep, \
             patch('pkgutil.iter_modules') as mock_iter, \
             patch('importlib.import_module') as mock_import:
            
            # Mock entry point
            ep_mock = Mock()
            ep_mock.name = "ep_plugin"
            ep_mock.load.return_value = TestPlugin
            mock_ep.return_value = [ep_mock]
            
            # Mock namespace module
            module_info = Mock()
            module_info.name = "ns_plugin"
            mock_iter.return_value = [module_info]
            
            ns_module = Mock(spec=ModuleType)
            ns_module.PLUGIN = TestExportPlugin
            mock_import.return_value = ns_module
            
            # Run discovery
            plugins = discover_plugins()
            
            # Should find both plugins
            assert len(plugins) == 2
            
            # Verify plugin types
            plugin_names = [p.name for p in plugins]
            assert "test_plugin" in plugin_names  # Default TestPlugin name
            assert "test_export" in plugin_names  # Default TestExportPlugin name
            
    def test_discovery_deduplication(self):
        """Test that discovery handles duplicate plugins gracefully."""
        with patch('importlib.metadata.entry_points') as mock_ep, \
             patch('pkgutil.iter_modules') as mock_iter, \
             patch('importlib.import_module') as mock_import:
            
            # Mock same plugin from both sources
            ep_mock = Mock()
            ep_mock.name = "duplicate_plugin"
            ep_mock.load.return_value = lambda: TestPlugin("duplicate")
            mock_ep.return_value = [ep_mock]
            
            module_info = Mock()
            module_info.name = "duplicate_plugin"
            mock_iter.return_value = [module_info]
            
            ns_module = Mock(spec=ModuleType)
            ns_module.PLUGIN_FACTORY = lambda: TestPlugin("duplicate")
            mock_import.return_value = ns_module
            
            plugins = discover_plugins()
            
            # Should have both plugins (no automatic deduplication)
            assert len(plugins) == 2
            assert all(p.name == "duplicate" for p in plugins)
            
    def test_discovery_error_handling(self):
        """Test discovery continues despite individual failures."""
        with patch('importlib.metadata.entry_points') as mock_ep, \
             patch('pkgutil.iter_modules') as mock_iter, \
             patch('importlib.import_module') as mock_import:
            
            # Mix of working and failing entry points
            good_ep = Mock()
            good_ep.name = "good_plugin"
            good_ep.load.return_value = TestPlugin
            
            bad_ep = Mock()
            bad_ep.name = "bad_plugin"
            bad_ep.load.side_effect = ImportError("Broken")
            
            mock_ep.return_value = [good_ep, bad_ep]
            
            # Failing namespace module
            module_info = Mock()
            module_info.name = "broken_ns"
            mock_iter.return_value = [module_info]
            mock_import.side_effect = ImportError("Broken namespace")
            
            plugins = discover_plugins()
            
            # Should get only the working plugin
            assert len(plugins) == 1
            assert isinstance(plugins[0], TestPlugin)