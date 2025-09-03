"""
Test suite for plugin interfaces and typed implementations.

Tests plugin interface contracts, method signatures, and
specialized plugin types (export, deployment, DNS, observer, router).
"""

import pytest
import asyncio
from abc import ABC
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock

from dotmac.plugins import (
    IPlugin,
    IExportPlugin,
    IDeploymentProvider,
    IDNSProvider,
    IObserver,
    PluginKind,
    PluginStatus,
    PluginContext,
    PluginMetadata,
    Version,
    Author,
    ExportResult,
    DeploymentResult,
    ValidationResult,
)
from conftest import TestPlugin, TestExportPlugin


# Test implementations for interface testing

class ConcreteExportPlugin(IExportPlugin):
    """Concrete implementation for testing IExportPlugin."""
    
    def __init__(self, name: str = "concrete_export"):
        self._name = name
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            kind=PluginKind.EXPORT,
            author=Author(name="Test Author"),
            description="Concrete export plugin for testing"
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
        return PluginKind.EXPORT
        
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
        
    async def export(self, task: Dict[str, Any]) -> ExportResult:
        return ExportResult(
            success=True,
            file_url=f"/exports/test_{task.get('format', 'csv')}.csv",
            file_name=f"export.{task.get('format', 'csv')}",
            metadata={"rows": 100, "format": task.get('format', 'csv')}
        )
        
    def get_supported_formats(self) -> List[str]:
        return ["csv", "xlsx", "json"]


class ConcreteDeploymentProvider(IDeploymentProvider):
    """Concrete implementation for testing IDeploymentProvider."""
    
    def __init__(self, name: str = "concrete_deployment"):
        self._name = name
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0", 
            kind=PluginKind.DEPLOYMENT,
            author=Author(name="Test Author"),
            description="Concrete deployment provider for testing"
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
        return PluginKind.DEPLOYMENT
        
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
        
    async def deploy(self, config: Dict[str, Any]) -> DeploymentResult:
        return DeploymentResult(
            success=True,
            deployment_id=f"deploy_{config.get('service', 'unknown')}",
            status="deployed",
            metadata={"timestamp": "2024-01-01T00:00:00Z"}
        )
        
    async def undeploy(self, deployment_id: str) -> DeploymentResult:
        return DeploymentResult(
            success=True,
            deployment_id=deployment_id,
            status="undeployed",
            metadata={"timestamp": "2024-01-01T00:05:00Z"}
        )
        
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        return {
            "deployment_id": deployment_id,
            "status": "running",
            "health": "healthy"
        }


class ConcreteDNSProvider(IDNSProvider):
    """Concrete implementation for testing IDNSProvider."""
    
    def __init__(self, name: str = "concrete_dns"):
        self._name = name
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            kind=PluginKind.DNS,
            author=Author(name="Test Author"),
            description="Concrete DNS provider for testing"
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
        return PluginKind.DNS
        
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
        
    async def validate_domain(self, domain: str) -> ValidationResult:
        return ValidationResult(
            success=True,
            message="Domain validation successful",
            details={"domain": domain, "valid": True}
        )
        
    async def create_dns_record(self, domain: str, record_type: str, value: str) -> Dict[str, Any]:
        return {
            "record_id": f"{domain}_{record_type}",
            "domain": domain,
            "type": record_type,
            "value": value,
            "status": "created"
        }
        
    async def delete_dns_record(self, record_id: str) -> bool:
        return True


class ConcreteObserver(IObserver):
    """Concrete implementation for testing IObserver."""
    
    def __init__(self, name: str = "concrete_observer"):
        self._name = name
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            kind=PluginKind.OBSERVER,
            author=Author(name="Test Author"),
            description="Concrete observer for testing"
        )
        self._status = PluginStatus.UNKNOWN
        self.observed_events = []
        
    @property
    def name(self) -> str:
        return self._name
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def kind(self) -> PluginKind:
        return PluginKind.OBSERVER
        
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
        
    async def on_event(self, event_type: str, data: Dict[str, Any]) -> None:
        self.observed_events.append({"type": event_type, "data": data})
        
    def get_subscribed_events(self) -> List[str]:
        return ["plugin.registered", "plugin.started", "plugin.stopped"]


class TestIPluginInterface:
    """Test the base IPlugin interface."""
    
    def test_iplugin_is_abstract(self):
        """Test IPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IPlugin()
            
    def test_iplugin_subclass_implementation(self):
        """Test concrete IPlugin subclass can be instantiated."""
        plugin = TestPlugin("test_concrete")
        
        assert isinstance(plugin, IPlugin)
        assert plugin.name == "test_concrete"
        assert plugin.version == "1.0.0"
        assert plugin.kind == PluginKind.CUSTOM
        assert isinstance(plugin.metadata, PluginMetadata)
        assert plugin.status == PluginStatus.UNKNOWN
        
    def test_iplugin_required_properties(self, test_plugin):
        """Test IPlugin has all required properties."""
        assert hasattr(test_plugin, 'name')
        assert hasattr(test_plugin, 'version')
        assert hasattr(test_plugin, 'kind')
        assert hasattr(test_plugin, 'metadata')
        assert hasattr(test_plugin, 'status')
        
        # Properties should be typed correctly
        assert isinstance(test_plugin.name, str)
        assert isinstance(test_plugin.version, str)
        assert isinstance(test_plugin.kind, PluginKind)
        assert isinstance(test_plugin.metadata, PluginMetadata)
        assert isinstance(test_plugin.status, PluginStatus)
        
    def test_iplugin_required_methods(self, test_plugin, plugin_context):
        """Test IPlugin has all required methods with correct signatures."""
        # Test method existence and callable
        assert hasattr(test_plugin, 'init')
        assert hasattr(test_plugin, 'start') 
        assert hasattr(test_plugin, 'stop')
        
        assert callable(test_plugin.init)
        assert callable(test_plugin.start)
        assert callable(test_plugin.stop)
        
        # Test methods can be called
        result = test_plugin.init(plugin_context)
        assert isinstance(result, bool)
        
        result = test_plugin.start()
        assert isinstance(result, bool)
        
        result = test_plugin.stop()
        assert isinstance(result, bool)
        
    def test_iplugin_status_setter(self, test_plugin):
        """Test plugin status can be set."""
        test_plugin.status = PluginStatus.INITIALIZED
        assert test_plugin.status == PluginStatus.INITIALIZED
        
        test_plugin.status = PluginStatus.STARTED
        assert test_plugin.status == PluginStatus.STARTED


class TestIExportPluginInterface:
    """Test IExportPlugin specialized interface."""
    
    def test_iexportplugin_inheritance(self):
        """Test IExportPlugin inherits from IPlugin."""
        assert issubclass(IExportPlugin, IPlugin)
        
    def test_iexportplugin_implementation(self):
        """Test concrete IExportPlugin implementation."""
        plugin = ConcreteExportPlugin("test_export")
        
        assert isinstance(plugin, IExportPlugin)
        assert isinstance(plugin, IPlugin)
        assert plugin.kind == PluginKind.EXPORT
        
    @pytest.mark.asyncio
    async def test_export_method(self):
        """Test export method functionality."""
        plugin = ConcreteExportPlugin()
        
        task = {"format": "csv", "type": "users"}
        result = await plugin.export(task)
        
        assert isinstance(result, ExportResult)
        assert result.success is True
        assert "csv" in result.file_url
        assert result.metadata["format"] == "csv"
        
    def test_supported_formats_method(self):
        """Test get_supported_formats method."""
        plugin = ConcreteExportPlugin()
        
        formats = plugin.get_supported_formats()
        
        assert isinstance(formats, list)
        assert "csv" in formats
        assert "xlsx" in formats
        assert "json" in formats
        
    @pytest.mark.asyncio
    async def test_export_with_different_formats(self):
        """Test export method with different formats."""
        plugin = ConcreteExportPlugin()
        
        for fmt in ["csv", "xlsx", "json"]:
            task = {"format": fmt}
            result = await plugin.export(task)
            
            assert result.success is True
            assert fmt in result.file_url


class TestIDeploymentProviderInterface:
    """Test IDeploymentProvider specialized interface."""
    
    def test_ideploymentprovider_inheritance(self):
        """Test IDeploymentProvider inherits from IPlugin."""
        assert issubclass(IDeploymentProvider, IPlugin)
        
    def test_ideploymentprovider_implementation(self):
        """Test concrete IDeploymentProvider implementation."""
        plugin = ConcreteDeploymentProvider("test_deployment")
        
        assert isinstance(plugin, IDeploymentProvider)
        assert isinstance(plugin, IPlugin)
        assert plugin.kind == PluginKind.DEPLOYMENT
        
    @pytest.mark.asyncio
    async def test_deploy_method(self):
        """Test deploy method functionality."""
        plugin = ConcreteDeploymentProvider()
        
        config = {"service": "web-app", "version": "1.0.0"}
        result = await plugin.deploy(config)
        
        assert isinstance(result, DeploymentResult)
        assert result.success is True
        assert "deploy_web-app" in result.deployment_id
        assert result.status == "deployed"
        
    @pytest.mark.asyncio
    async def test_undeploy_method(self):
        """Test undeploy method functionality."""
        plugin = ConcreteDeploymentProvider()
        
        deployment_id = "deploy_test_123"
        result = await plugin.undeploy(deployment_id)
        
        assert isinstance(result, DeploymentResult)
        assert result.success is True
        assert result.deployment_id == deployment_id
        assert result.status == "undeployed"
        
    @pytest.mark.asyncio
    async def test_get_deployment_status_method(self):
        """Test get_deployment_status method functionality."""
        plugin = ConcreteDeploymentProvider()
        
        deployment_id = "deploy_test_123"
        status = await plugin.get_deployment_status(deployment_id)
        
        assert isinstance(status, dict)
        assert status["deployment_id"] == deployment_id
        assert "status" in status
        assert "health" in status


class TestIDNSProviderInterface:
    """Test IDNSProvider specialized interface."""
    
    def test_idnsprovider_inheritance(self):
        """Test IDNSProvider inherits from IPlugin."""
        assert issubclass(IDNSProvider, IPlugin)
        
    def test_idnsprovider_implementation(self):
        """Test concrete IDNSProvider implementation."""
        plugin = ConcreteDNSProvider("test_dns")
        
        assert isinstance(plugin, IDNSProvider)
        assert isinstance(plugin, IPlugin)
        assert plugin.kind == PluginKind.DNS
        
    @pytest.mark.asyncio
    async def test_validate_domain_method(self):
        """Test validate_domain method functionality."""
        plugin = ConcreteDNSProvider()
        
        domain = "example.com"
        result = await plugin.validate_domain(domain)
        
        assert isinstance(result, ValidationResult)
        assert result.success is True
        assert domain in result.details["domain"]
        
    @pytest.mark.asyncio
    async def test_create_dns_record_method(self):
        """Test create_dns_record method functionality."""
        plugin = ConcreteDNSProvider()
        
        domain = "example.com"
        record_type = "A"
        value = "192.168.1.1"
        
        result = await plugin.create_dns_record(domain, record_type, value)
        
        assert isinstance(result, dict)
        assert result["domain"] == domain
        assert result["type"] == record_type
        assert result["value"] == value
        assert result["status"] == "created"
        
    @pytest.mark.asyncio
    async def test_delete_dns_record_method(self):
        """Test delete_dns_record method functionality."""
        plugin = ConcreteDNSProvider()
        
        record_id = "example.com_A"
        result = await plugin.delete_dns_record(record_id)
        
        assert isinstance(result, bool)
        assert result is True


class TestIObserverInterface:
    """Test IObserver specialized interface."""
    
    def test_iobserver_inheritance(self):
        """Test IObserver inherits from IPlugin."""
        assert issubclass(IObserver, IPlugin)
        
    def test_iobserver_implementation(self):
        """Test concrete IObserver implementation."""
        plugin = ConcreteObserver("test_observer")
        
        assert isinstance(plugin, IObserver)
        assert isinstance(plugin, IPlugin)
        assert plugin.kind == PluginKind.OBSERVER
        
    @pytest.mark.asyncio
    async def test_on_event_method(self):
        """Test on_event method functionality."""
        plugin = ConcreteObserver()
        
        event_type = "test.event"
        data = {"message": "test data"}
        
        await plugin.on_event(event_type, data)
        
        assert len(plugin.observed_events) == 1
        assert plugin.observed_events[0]["type"] == event_type
        assert plugin.observed_events[0]["data"] == data
        
    def test_get_subscribed_events_method(self):
        """Test get_subscribed_events method functionality."""
        plugin = ConcreteObserver()
        
        events = plugin.get_subscribed_events()
        
        assert isinstance(events, list)
        assert "plugin.registered" in events
        assert "plugin.started" in events
        assert "plugin.stopped" in events
        
    @pytest.mark.asyncio
    async def test_multiple_events(self):
        """Test observer can handle multiple events."""
        plugin = ConcreteObserver()
        
        events = [
            ("event1", {"data": "first"}),
            ("event2", {"data": "second"}),
            ("event3", {"data": "third"}),
        ]
        
        for event_type, data in events:
            await plugin.on_event(event_type, data)
            
        assert len(plugin.observed_events) == 3
        assert plugin.observed_events[0]["data"]["data"] == "first"
        assert plugin.observed_events[1]["data"]["data"] == "second"
        assert plugin.observed_events[2]["data"]["data"] == "third"


class TestOptionalInterfaces:
    """Test optional interfaces (require extra dependencies)."""
    
    def test_router_plugin_interface_optional(self):
        """Test IRouterPlugin interface is optionally available."""
        try:
            from dotmac.plugins import IRouterPlugin
            assert issubclass(IRouterPlugin, IPlugin)
        except ImportError:
            # FastAPI not available, interface should not be importable
            pytest.skip("FastAPI not available, IRouterPlugin interface not accessible")


class TestInterfaceContract:
    """Test interface contracts and method signatures."""
    
    def test_sync_and_async_method_support(self):
        """Test interfaces support both sync and async implementations."""
        # Test sync implementation
        sync_plugin = TestPlugin("sync")
        assert not asyncio.iscoroutinefunction(sync_plugin.init)
        assert not asyncio.iscoroutinefunction(sync_plugin.start)
        assert not asyncio.iscoroutinefunction(sync_plugin.stop)
        
        # Test async implementation (from conftest.py)
        from conftest import AsyncTestPlugin
        async_plugin = AsyncTestPlugin("async")
        assert asyncio.iscoroutinefunction(async_plugin.init)
        assert asyncio.iscoroutinefunction(async_plugin.start)
        assert asyncio.iscoroutinefunction(async_plugin.stop)
        
    def test_method_return_types(self, test_plugin, plugin_context):
        """Test methods return expected types."""
        # Lifecycle methods should return bool
        assert isinstance(test_plugin.init(plugin_context), bool)
        assert isinstance(test_plugin.start(), bool)
        assert isinstance(test_plugin.stop(), bool)
        
    @pytest.mark.asyncio
    async def test_specialized_method_return_types(self):
        """Test specialized interfaces return correct types."""
        # Export plugin
        export_plugin = ConcreteExportPlugin()
        export_result = await export_plugin.export({"format": "csv"})
        assert isinstance(export_result, ExportResult)
        
        formats = export_plugin.get_supported_formats()
        assert isinstance(formats, list)
        assert all(isinstance(fmt, str) for fmt in formats)
        
        # Deployment provider
        deploy_plugin = ConcreteDeploymentProvider()
        deploy_result = await deploy_plugin.deploy({"service": "test"})
        assert isinstance(deploy_result, DeploymentResult)
        
        status = await deploy_plugin.get_deployment_status("test")
        assert isinstance(status, dict)
        
        # DNS provider
        dns_plugin = ConcreteDNSProvider()
        validation_result = await dns_plugin.validate_domain("example.com")
        assert isinstance(validation_result, ValidationResult)
        
        record_result = await dns_plugin.create_dns_record("example.com", "A", "1.1.1.1")
        assert isinstance(record_result, dict)
        
        delete_result = await dns_plugin.delete_dns_record("test")
        assert isinstance(delete_result, bool)
        
        # Observer
        observer = ConcreteObserver()
        events = observer.get_subscribed_events()
        assert isinstance(events, list)
        
        # on_event should return None
        result = await observer.on_event("test", {})
        assert result is None