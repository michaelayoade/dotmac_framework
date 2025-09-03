"""
Test configuration and fixtures for dotmac-plugins package.
"""

import asyncio
import logging
from typing import AsyncIterator
import pytest

from dotmac.plugins import (
    PluginRegistry,
    PluginLifecycleManager,
    PluginContext,
    PluginMetadata,
    PluginKind,
    PluginStatus,
    IPlugin,
    IExportPlugin,
    Author,
    Version,
)
from dotmac.plugins.observability import PluginObservabilityHooks


# Test plugin implementations for testing

class TestPlugin(IPlugin):
    """Simple test plugin implementation."""
    
    def __init__(self, name: str = "test_plugin", version: str = "1.0.0"):
        self._name = name
        self._version = version
        self._metadata = PluginMetadata(
            name=name,
            version=version,
            kind=PluginKind.CUSTOM,
            author=Author(name="Test Author"),
            description="Test plugin for unit tests"
        )
        self._status = PluginStatus.UNKNOWN
        self._init_called = False
        self._start_called = False
        self._stop_called = False
        self._context = None
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def kind(self) -> PluginKind:
        return PluginKind.CUSTOM
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @status.setter
    def status(self, value: PluginStatus) -> None:
        self._status = value
    
    def init(self, context: PluginContext) -> bool:
        self._init_called = True
        self._context = context
        return True
    
    def start(self) -> bool:
        self._start_called = True
        return True
    
    def stop(self) -> bool:
        self._stop_called = True
        return True
    
    # Test helper properties
    @property
    def init_called(self) -> bool:
        return self._init_called
    
    @property
    def start_called(self) -> bool:
        return self._start_called
    
    @property
    def stop_called(self) -> bool:
        return self._stop_called
    
    @property
    def context(self) -> PluginContext:
        return self._context


class AsyncTestPlugin(IPlugin):
    """Test plugin with async methods."""
    
    def __init__(self, name: str = "async_test_plugin"):
        self._name = name
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            kind=PluginKind.CUSTOM,
            author=Author(name="Test Author"),
            description="Async test plugin"
        )
        self._status = PluginStatus.UNKNOWN
        self._init_called = False
        self._start_called = False
        self._stop_called = False
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def kind(self) -> PluginKind:
        return PluginKind.CUSTOM
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @status.setter
    def status(self, value: PluginStatus) -> None:
        self._status = value
    
    async def init(self, context: PluginContext) -> bool:
        # Simulate async initialization
        await asyncio.sleep(0.01)
        self._init_called = True
        return True
    
    async def start(self) -> bool:
        # Simulate async startup
        await asyncio.sleep(0.01)
        self._start_called = True
        return True
    
    async def stop(self) -> bool:
        # Simulate async shutdown
        await asyncio.sleep(0.01)
        self._stop_called = True
        return True
    
    # Test helper properties
    @property
    def init_called(self) -> bool:
        return self._init_called
    
    @property
    def start_called(self) -> bool:
        return self._start_called
    
    @property
    def stop_called(self) -> bool:
        return self._stop_called


class TestExportPlugin(IExportPlugin):
    """Test export plugin implementation."""
    
    def __init__(self, name: str = "test_export"):
        self._name = name
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            kind=PluginKind.EXPORT,
            author=Author(name="Test Author"),
            description="Test export plugin"
        )
        self._status = PluginStatus.UNKNOWN
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @status.setter
    def status(self, value: PluginStatus) -> None:
        self._status = value
    
    def init(self, context: PluginContext) -> bool:
        return True
    
    def start(self) -> bool:
        return True
    
    def stop(self) -> bool:
        return True
    
    async def export(self, task: dict) -> dict:
        return {
            "success": True,
            "file_url": f"/exports/{task.get('format', 'csv')}_export.csv",
            "file_name": f"test_export.{task.get('format', 'csv')}",
            "metadata": {"rows": 100}
        }
    
    def get_supported_formats(self) -> list[str]:
        return ["csv", "xlsx"]


class FailingPlugin(IPlugin):
    """Plugin that fails operations for testing error handling."""
    
    def __init__(self, name: str = "failing_plugin", fail_on: str = "init"):
        self._name = name
        self._fail_on = fail_on
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            kind=PluginKind.CUSTOM,
            author=Author(name="Test Author"),
            description="Plugin that fails for testing"
        )
        self._status = PluginStatus.UNKNOWN
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def kind(self) -> PluginKind:
        return PluginKind.CUSTOM
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    @property
    def status(self) -> PluginStatus:
        return self._status
    
    @status.setter
    def status(self, value: PluginStatus) -> None:
        self._status = value
    
    def init(self, context: PluginContext) -> bool:
        if self._fail_on == "init":
            raise RuntimeError("Intentional failure in init")
        return True
    
    def start(self) -> bool:
        if self._fail_on == "start":
            raise RuntimeError("Intentional failure in start")
        return True
    
    def stop(self) -> bool:
        if self._fail_on == "stop":
            raise RuntimeError("Intentional failure in stop")
        return True


# Fixtures

@pytest.fixture
def test_plugin():
    """Create a test plugin."""
    return TestPlugin()


@pytest.fixture
def async_test_plugin():
    """Create an async test plugin."""
    return AsyncTestPlugin()


@pytest.fixture
def test_export_plugin():
    """Create a test export plugin."""
    return TestExportPlugin()


@pytest.fixture
def failing_plugin():
    """Create a plugin that fails during init."""
    return FailingPlugin()


@pytest.fixture
def plugin_context():
    """Create a basic plugin context."""
    return PluginContext(
        tenant_id="test_tenant",
        environment="test",
        permissions={"export", "test:permission"},
        config={"test_key": "test_value"}
    )


@pytest.fixture
def plugin_registry():
    """Create a clean plugin registry."""
    return PluginRegistry()


@pytest.fixture
def plugin_lifecycle(plugin_registry):
    """Create a plugin lifecycle manager."""
    return PluginLifecycleManager(registry=plugin_registry)


@pytest.fixture
def observability_hooks():
    """Create observability hooks for testing."""
    return PluginObservabilityHooks(enable_logging=False)


@pytest.fixture
def populated_registry(plugin_registry, test_plugin, test_export_plugin):
    """Create a registry with some test plugins registered."""
    plugin_registry.register(test_plugin)
    plugin_registry.register(test_export_plugin)
    return plugin_registry


# Mock logger to capture log messages during testing
@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    import logging
    from unittest.mock import Mock
    
    logger = Mock(spec=logging.Logger)
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    
    return logger


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Helper functions for tests

def create_test_plugin(name: str = None, kind: PluginKind = PluginKind.CUSTOM) -> TestPlugin:
    """Create a test plugin with optional name and kind."""
    plugin = TestPlugin(name=name or "test_plugin")
    plugin._metadata = PluginMetadata(
        name=plugin.name,
        version="1.0.0",
        kind=kind,
        author=Author(name="Test Author"),
        description="Test plugin"
    )
    return plugin


def assert_plugin_status(plugin: IPlugin, expected_status: PluginStatus) -> None:
    """Assert that plugin has expected status."""
    assert plugin.status == expected_status, f"Expected {expected_status}, got {plugin.status}"


def assert_lifecycle_methods_called(plugin: TestPlugin) -> None:
    """Assert that all lifecycle methods were called on test plugin."""
    assert plugin.init_called, "init() was not called"
    assert plugin.start_called, "start() was not called"