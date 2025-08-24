"""Tests for plugin base classes."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from dotmac_isp.plugins.core.base import (
    PluginStatus,
    PluginCategory,
    PluginInfo,
    PluginConfig,
    PluginContext,
    PluginAPI,
    BasePlugin,
    NetworkAutomationPlugin,
    GISLocationPlugin,
    BillingIntegrationPlugin,
    CRMIntegrationPlugin,
    MonitoringPlugin,
    TicketingPlugin,
)


class TestPluginStatus:
    """Test PluginStatus enum."""
    
    def test_plugin_status_values(self):
        """Test PluginStatus enum values."""
        assert PluginStatus.UNLOADED.value == "unloaded"
        assert PluginStatus.LOADING.value == "loading"
        assert PluginStatus.LOADED.value == "loaded"
        assert PluginStatus.ACTIVE.value == "active"
        assert PluginStatus.INACTIVE.value == "inactive"
        assert PluginStatus.ERROR.value == "error"
        assert PluginStatus.DISABLED.value == "disabled"
    
    def test_plugin_status_count(self):
        """Test that we have the expected number of status values."""
        assert len(PluginStatus) == 7


class TestPluginCategory:
    """Test PluginCategory enum."""
    
    def test_plugin_category_values(self):
        """Test PluginCategory enum values."""
        assert PluginCategory.NETWORK_AUTOMATION.value == "network_automation"
        assert PluginCategory.GIS_LOCATION.value == "gis_location"
        assert PluginCategory.BILLING_INTEGRATION.value == "billing_integration"
        assert PluginCategory.CRM_INTEGRATION.value == "crm_integration"
        assert PluginCategory.MONITORING.value == "monitoring"
        assert PluginCategory.TICKETING.value == "ticketing"
        assert PluginCategory.COMMUNICATION.value == "communication"
        assert PluginCategory.REPORTING.value == "reporting"
        assert PluginCategory.SECURITY.value == "security"
        assert PluginCategory.CUSTOM.value == "custom"
    
    def test_plugin_category_count(self):
        """Test that we have the expected number of category values."""
        assert len(PluginCategory) == 10


class TestPluginInfo:
    """Test PluginInfo dataclass."""
    
    def test_plugin_info_creation(self):
        """Test basic PluginInfo creation."""
        info = PluginInfo(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            category=PluginCategory.CUSTOM
        )
        
        assert info.id == "test_plugin"
        assert info.name == "Test Plugin"
        assert info.version == "1.0.0"
        assert info.description == "A test plugin"
        assert info.author == "Test Author"
        assert info.category == PluginCategory.CUSTOM
        assert info.dependencies == []
        assert info.python_requires == ">=3.11"
        assert info.supports_multi_tenant is True
        assert info.supports_hot_reload is False
        assert info.requires_restart is False
        assert info.security_level == "standard"
        assert info.permissions_required == []
        assert isinstance(info.created_at, datetime)
        assert isinstance(info.updated_at, datetime)
    
    def test_plugin_info_with_dependencies(self):
        """Test PluginInfo with dependencies."""
        dependencies = ["dep1", "dep2"]
        info = PluginInfo(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            category=PluginCategory.NETWORK_AUTOMATION,
            dependencies=dependencies
        )
        
        assert info.dependencies == dependencies
    
    def test_plugin_info_post_init_none_values(self):
        """Test PluginInfo post_init with None values."""
        info = PluginInfo(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            category=PluginCategory.CUSTOM,
            dependencies=None,
            permissions_required=None,
            created_at=None,
            updated_at=None
        )
        
        assert info.dependencies == []
        assert info.permissions_required == []
        assert isinstance(info.created_at, datetime)
        assert isinstance(info.updated_at, datetime)
    
    @patch('dotmac_isp.plugins.core.base.datetime')
    def test_plugin_info_post_init_datetime_mocking(self, mock_datetime):
        """Test PluginInfo post_init with mocked datetime."""
        mock_now = datetime(2023, 12, 15, 10, 30, 45)
        mock_datetime.utcnow.return_value = mock_now
        
        info = PluginInfo(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            category=PluginCategory.CUSTOM
        )
        
        assert info.created_at == mock_now
        assert info.updated_at == mock_now


class TestPluginConfig:
    """Test PluginConfig Pydantic model."""
    
    def test_plugin_config_defaults(self):
        """Test PluginConfig default values."""
        config = PluginConfig()
        
        assert config.enabled is True
        assert config.tenant_id is None
        assert config.priority == 100
        assert config.config_data == {}
        assert config.sandbox_enabled is True
        assert config.resource_limits == {}
        assert config.metrics_enabled is True
        assert config.logging_enabled is True
    
    def test_plugin_config_custom_values(self):
        """Test PluginConfig with custom values."""
        tenant_id = uuid4()
        config_data = {"key1": "value1", "key2": 42}
        resource_limits = {"memory": "256MB", "cpu": "50%"}
        
        config = PluginConfig(
            enabled=False,
            tenant_id=tenant_id,
            priority=50,
            config_data=config_data,
            sandbox_enabled=False,
            resource_limits=resource_limits,
            metrics_enabled=False,
            logging_enabled=False
        )
        
        assert config.enabled is False
        assert config.tenant_id == tenant_id
        assert config.priority == 50
        assert config.config_data == config_data
        assert config.sandbox_enabled is False
        assert config.resource_limits == resource_limits
        assert config.metrics_enabled is False
        assert config.logging_enabled is False
    
    def test_plugin_config_priority_validation(self):
        """Test PluginConfig priority field validation."""
        # Valid priorities
        config = PluginConfig(priority=0)
        assert config.priority == 0
        
        config = PluginConfig(priority=1000)
        assert config.priority == 1000
        
        # Invalid priorities should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            PluginConfig(priority=-1)
        
        with pytest.raises(Exception):  # Pydantic validation error
            PluginConfig(priority=1001)


class TestPluginContext:
    """Test PluginContext class."""
    
    def test_plugin_context_creation(self):
        """Test basic PluginContext creation."""
        context = PluginContext()
        
        assert context.tenant_id is None
        assert context.user_id is None
        assert isinstance(context.request_id, str)
        assert len(context.request_id) == 36  # UUID4 string length
        assert context.metadata == {}
        assert isinstance(context.started_at, datetime)
    
    def test_plugin_context_with_params(self):
        """Test PluginContext with parameters."""
        tenant_id = uuid4()
        user_id = uuid4()
        request_id = "custom_request_id"
        
        context = PluginContext(
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id
        )
        
        assert context.tenant_id == tenant_id
        assert context.user_id == user_id
        assert context.request_id == request_id
    
    def test_plugin_context_metadata_operations(self):
        """Test PluginContext metadata operations."""
        context = PluginContext()
        
        # Test adding metadata
        context.add_metadata("key1", "value1")
        context.add_metadata("key2", {"nested": "data"})
        context.add_metadata("key3", 42)
        
        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"] == {"nested": "data"}
        assert context.metadata["key3"] == 42
        
        # Test getting metadata
        assert context.get_metadata("key1") == "value1"
        assert context.get_metadata("key2") == {"nested": "data"}
        assert context.get_metadata("key3") == 42
        assert context.get_metadata("nonexistent") is None
        assert context.get_metadata("nonexistent", "default") == "default"


class TestPluginAPI:
    """Test PluginAPI class."""
    
    def test_plugin_api_creation(self):
        """Test PluginAPI creation."""
        services = {
            "database": MagicMock(),
            "redis": MagicMock(),
            "event_bus": MagicMock(),
            "logger": MagicMock(),
            "config": MagicMock(),
        }
        
        api = PluginAPI(services)
        assert api._services == services
    
    def test_plugin_api_get_service(self):
        """Test getting services from PluginAPI."""
        mock_db = MagicMock()
        services = {"database": mock_db}
        
        api = PluginAPI(services)
        
        assert api.get_service("database") == mock_db
        assert api.get_service("nonexistent") is None
    
    def test_plugin_api_service_properties(self):
        """Test PluginAPI service properties."""
        mock_db = MagicMock()
        mock_redis = MagicMock()
        mock_event_bus = MagicMock()
        mock_logger = MagicMock()
        mock_config = MagicMock()
        
        services = {
            "database": mock_db,
            "redis": mock_redis,
            "event_bus": mock_event_bus,
            "logger": mock_logger,
            "config": mock_config,
        }
        
        api = PluginAPI(services)
        
        assert api.database == mock_db
        assert api.redis == mock_redis
        assert api.event_bus == mock_event_bus
        assert api.logger == mock_logger
        assert api.config == mock_config


class TestPluginImplementation(BasePlugin):
    """Test implementation of BasePlugin for testing."""
    
    @property
    def plugin_info(self):
        """Plugin Info operation."""
        return PluginInfo(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="Test plugin implementation",
            author="Test",
            category=PluginCategory.CUSTOM
        )
    
    async def initialize(self):
        """Test initialize implementation."""
        pass
    
    async def activate(self):
        """Test activate implementation."""
        pass
    
    async def deactivate(self):
        """Test deactivate implementation."""
        pass
    
    async def cleanup(self):
        """Test cleanup implementation."""
        pass


class TestBasePlugin:
    """Test BasePlugin class."""
    
    def test_base_plugin_creation(self):
        """Test BasePlugin creation."""
        config = PluginConfig()
        api = PluginAPI({})
        
        plugin = TestPluginImplementation(config, api)
        
        assert plugin.config == config
        assert plugin.api == api
        assert plugin.status == PluginStatus.UNLOADED
        assert plugin.info is None
        assert plugin._context is None
        assert isinstance(plugin._lock, asyncio.Lock)
    
    def test_base_plugin_plugin_info_property(self):
        """Test BasePlugin plugin_info property."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        
        info = plugin.plugin_info
        
        assert info.id == "test_plugin"
        assert info.name == "Test Plugin"
        assert info.version == "1.0.0"
        assert info.description == "Test plugin implementation"
        assert info.author == "Test"
        assert info.category == PluginCategory.CUSTOM
    
    async def test_validate_config_default(self):
        """Test default validate_config implementation."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        
        result = await plugin.validate_config(PluginConfig())
        assert result is True
    
    async def test_health_check_default(self):
        """Test default health_check implementation."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        plugin.status = PluginStatus.ACTIVE
        
        result = await plugin.health_check()
        
        assert result["status"] == "active"
        assert result["healthy"] is True
        assert "timestamp" in result
    
    async def test_health_check_unhealthy_status(self):
        """Test health_check with unhealthy status."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        plugin.status = PluginStatus.ERROR
        
        result = await plugin.health_check()
        
        assert result["status"] == "error"
        assert result["healthy"] is False
    
    async def test_get_metrics_default(self):
        """Test default get_metrics implementation."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        plugin.status = PluginStatus.ACTIVE
        
        result = await plugin.get_metrics()
        
        assert result["status"] == "active"
        assert result["uptime_seconds"] == 0  # No context set
    
    async def test_get_metrics_with_context(self):
        """Test get_metrics with context."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        plugin.status = PluginStatus.ACTIVE
        
        # Set context with started_at
        context = PluginContext()
        plugin.set_context(context)
        
        result = await plugin.get_metrics()
        
        assert result["status"] == "active"
        assert result["uptime_seconds"] >= 0
    
    def test_context_operations(self):
        """Test plugin context operations."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        
        # Initially no context
        assert plugin.get_context() is None
        
        # Set context
        context = PluginContext()
        plugin.set_context(context)
        
        assert plugin.get_context() == context
    
    async def test_safe_operation_success(self):
        """Test _safe_operation with successful operation."""
        mock_logger = MagicMock()
        api = PluginAPI({"logger": mock_logger})
        plugin = TestPluginImplementation(PluginConfig(), api)
        
        # Mock operation function
        operation_func = AsyncMock()
        
        # Execute safe operation
        await plugin._safe_operation("test_operation", operation_func)
        
        # Verify operation was called
        operation_func.assert_called_once()
        
        # Verify success log
        mock_logger.info.assert_called_once()
        assert "test_operation completed successfully" in mock_logger.info.call_args[0][0]
    
    async def test_safe_operation_failure(self):
        """Test _safe_operation with failing operation."""
        mock_logger = MagicMock()
        api = PluginAPI({"logger": mock_logger})
        plugin = TestPluginImplementation(PluginConfig(), api)
        
        # Mock failing operation
        test_error = Exception("Test error")
        operation_func = AsyncMock(side_effect=test_error)
        
        # Execute safe operation and expect exception
        with pytest.raises(Exception) as exc_info:
            await plugin._safe_operation("test_operation", operation_func)
        
        assert exc_info.value == test_error
        assert plugin.status == PluginStatus.ERROR
        
        # Verify error log
        mock_logger.error.assert_called_once()
        assert "test_operation failed: Test error" in mock_logger.error.call_args[0][0]
    
    def test_plugin_repr(self):
        """Test BasePlugin __repr__ method."""
        plugin = TestPluginImplementation(PluginConfig(), PluginAPI({}))
        plugin.status = PluginStatus.ACTIVE
        
        repr_str = repr(plugin)
        
        assert "TestPluginImplementation" in repr_str
        assert "name=Test Plugin" in repr_str
        assert "status=active" in repr_str


class TestNetworkAutomationPlugin:
    """Test NetworkAutomationPlugin abstract class."""
    
    def test_network_automation_plugin_inheritance(self):
        """Test NetworkAutomationPlugin inherits from BasePlugin."""
        assert issubclass(NetworkAutomationPlugin, BasePlugin)
    
    def test_network_automation_plugin_abstract_methods(self):
        """Test NetworkAutomationPlugin has required abstract methods."""
        abstract_methods = NetworkAutomationPlugin.__abstractmethods__
        
        expected_methods = {
            'discover_devices', 'configure_device', 'get_device_status',
            'plugin_info', 'initialize', 'activate', 'deactivate', 'cleanup'
        }
        
        assert abstract_methods == expected_methods


class TestSpecializedPluginClasses:
    """Test other specialized plugin classes."""
    
    def test_gis_location_plugin_inheritance(self):
        """Test GISLocationPlugin inherits from BasePlugin."""
        assert issubclass(GISLocationPlugin, BasePlugin)
    
    def test_billing_integration_plugin_inheritance(self):
        """Test BillingIntegrationPlugin inherits from BasePlugin."""
        assert issubclass(BillingIntegrationPlugin, BasePlugin)
    
    def test_crm_integration_plugin_inheritance(self):
        """Test CRMIntegrationPlugin inherits from BasePlugin."""
        assert issubclass(CRMIntegrationPlugin, BasePlugin)
    
    def test_monitoring_plugin_inheritance(self):
        """Test MonitoringPlugin inherits from BasePlugin."""
        assert issubclass(MonitoringPlugin, BasePlugin)
    
    def test_ticketing_plugin_inheritance(self):
        """Test TicketingPlugin inherits from BasePlugin."""
        assert issubclass(TicketingPlugin, BasePlugin)
    
    def test_all_specialized_plugins_have_abstract_methods(self):
        """Test that all specialized plugins define their abstract methods."""
        plugin_classes = [
            NetworkAutomationPlugin,
            GISLocationPlugin,
            BillingIntegrationPlugin,
            CRMIntegrationPlugin,
            MonitoringPlugin,
            TicketingPlugin,
        ]
        
        for plugin_class in plugin_classes:
            # Each should have abstract methods beyond the base plugin methods
            assert len(plugin_class.__abstractmethods__) > 4  # More than just base plugin methods