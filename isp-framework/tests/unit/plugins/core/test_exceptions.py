"""Tests for plugin system exceptions."""

import pytest

from dotmac_isp.plugins.core.exceptions import (
    PluginError,
    PluginLoadError,
    PluginConfigError,
    PluginDependencyError,
    PluginSecurityError,
    PluginVersionError,
    PluginRegistrationError,
    PluginLifecycleError,
    PluginTimeoutError,
    PluginResourceError,
    PluginCommunicationError,
)


class TestPluginError:
    """Test base PluginError class."""
    
    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = PluginError("Test error")
        
        assert str(error) == "Test error"
        assert error.plugin_name is None
        assert error.plugin_version is None
    
    def test_error_with_plugin_name(self):
        """Test error with plugin name."""
        error = PluginError("Test error", plugin_name="test_plugin")
        
        assert "Test error (Plugin: test_plugin)" == str(error)
        assert error.plugin_name == "test_plugin"
        assert error.plugin_version is None
    
    def test_error_with_plugin_name_and_version(self):
        """Test error with plugin name and version."""
        error = PluginError("Test error", plugin_name="test_plugin", plugin_version="1.0.0")
        
        assert str(error) == "Test error (Plugin: test_plugin v1.0.0)"
        assert error.plugin_name == "test_plugin"
        assert error.plugin_version == "1.0.0"
    
    def test_error_with_version_only(self):
        """Test error with version but no name."""
        error = PluginError("Test error", plugin_version="1.0.0")
        
        assert str(error) == "Test error"
        assert error.plugin_name is None
        assert error.plugin_version == "1.0.0"


class TestPluginLoadError:
    """Test PluginLoadError class."""
    
    def test_plugin_load_error_creation(self):
        """Test PluginLoadError creation."""
        error = PluginLoadError("Failed to load plugin")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Failed to load plugin"
    
    def test_plugin_load_error_with_details(self):
        """Test PluginLoadError with plugin details."""
        error = PluginLoadError(
            "Failed to load plugin",
            plugin_name="network_plugin",
            plugin_version="2.1.0"
        )
        
        assert str(error) == "Failed to load plugin (Plugin: network_plugin v2.1.0)"


class TestPluginConfigError:
    """Test PluginConfigError class."""
    
    def test_plugin_config_error_creation(self):
        """Test PluginConfigError creation."""
        error = PluginConfigError("Invalid configuration")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Invalid configuration"


class TestPluginDependencyError:
    """Test PluginDependencyError class."""
    
    def test_plugin_dependency_error_basic(self):
        """Test basic PluginDependencyError creation."""
        error = PluginDependencyError("Missing dependencies")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Missing dependencies"
        assert error.missing_dependencies == []
    
    def test_plugin_dependency_error_with_missing_deps(self):
        """Test PluginDependencyError with missing dependencies list."""
        missing_deps = ["dep1", "dep2", "dep3"]
        error = PluginDependencyError(
            "Missing dependencies",
            plugin_name="dependent_plugin",
            missing_dependencies=missing_deps
        )
        
        assert str(error) == "Missing dependencies (Plugin: dependent_plugin)"
        assert error.missing_dependencies == missing_deps
    
    def test_plugin_dependency_error_none_missing_deps(self):
        """Test PluginDependencyError with None missing dependencies."""
        error = PluginDependencyError("Missing dependencies", missing_dependencies=None)
        
        assert error.missing_dependencies == []


class TestPluginSecurityError:
    """Test PluginSecurityError class."""
    
    def test_plugin_security_error_creation(self):
        """Test PluginSecurityError creation."""
        error = PluginSecurityError("Security validation failed")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Security validation failed"


class TestPluginVersionError:
    """Test PluginVersionError class."""
    
    def test_plugin_version_error_creation(self):
        """Test PluginVersionError creation."""
        error = PluginVersionError("Version requirements not met")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Version requirements not met"


class TestPluginRegistrationError:
    """Test PluginRegistrationError class."""
    
    def test_plugin_registration_error_creation(self):
        """Test PluginRegistrationError creation."""
        error = PluginRegistrationError("Registration failed")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Registration failed"


class TestPluginLifecycleError:
    """Test PluginLifecycleError class."""
    
    def test_plugin_lifecycle_error_creation(self):
        """Test PluginLifecycleError creation."""
        error = PluginLifecycleError("Lifecycle operation failed")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Lifecycle operation failed"


class TestPluginTimeoutError:
    """Test PluginTimeoutError class."""
    
    def test_plugin_timeout_error_creation(self):
        """Test PluginTimeoutError creation."""
        error = PluginTimeoutError("Operation timed out")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Operation timed out"


class TestPluginResourceError:
    """Test PluginResourceError class."""
    
    def test_plugin_resource_error_creation(self):
        """Test PluginResourceError creation."""
        error = PluginResourceError("Resource limit exceeded")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Resource limit exceeded"


class TestPluginCommunicationError:
    """Test PluginCommunicationError class."""
    
    def test_plugin_communication_error_creation(self):
        """Test PluginCommunicationError creation."""
        error = PluginCommunicationError("Communication failed")
        
        assert isinstance(error, PluginError)
        assert str(error) == "Communication failed"


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""
    
    def test_all_exceptions_inherit_from_plugin_error(self):
        """Test that all plugin exceptions inherit from PluginError."""
        exception_classes = [
            PluginLoadError,
            PluginConfigError,
            PluginDependencyError,
            PluginSecurityError,
            PluginVersionError,
            PluginRegistrationError,
            PluginLifecycleError,
            PluginTimeoutError,
            PluginResourceError,
            PluginCommunicationError,
        ]
        
        for exception_class in exception_classes:
            error = exception_class("Test message")
            assert isinstance(error, PluginError)
            assert isinstance(error, Exception)
    
    def test_plugin_error_inherits_from_exception(self):
        """Test that PluginError inherits from Exception."""
        error = PluginError("Test message")
        
        assert isinstance(error, Exception)


class TestExceptionStringRepresentation:
    """Test string representations of exceptions in various scenarios."""
    
    def test_complex_error_scenarios(self):
        """Test complex error message formatting scenarios."""
        # Test with special characters in plugin name
        error = PluginError("Error occurred", plugin_name="plugin-with-dashes_v2")
        assert "(Plugin: plugin-with-dashes_v2)" in str(error)
        
        # Test with empty plugin name (should be treated as None-ish)
        error = PluginError("Error occurred", plugin_name="")
        assert "(Plugin: )" in str(error)
        
        # Test with very long plugin name
        long_name = "a" * 100
        error = PluginError("Error occurred", plugin_name=long_name)
        assert f"(Plugin: {long_name})" in str(error)
        
        # Test with version containing special characters
        error = PluginError("Error occurred", plugin_name="test", plugin_version="1.0.0-beta+build.1")
        assert "(Plugin: test v1.0.0-beta+build.1)" in str(error)
    
    def test_multiline_error_messages(self):
        """Test error messages with multiple lines."""
        multiline_msg = "Error occurred:\n- Reason 1\n- Reason 2"
        error = PluginError(multiline_msg, plugin_name="test_plugin")
        
        result = str(error)
        assert "Error occurred:" in result
        assert "- Reason 1" in result
        assert "- Reason 2" in result
        assert "(Plugin: test_plugin)" in result