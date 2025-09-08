"""
Basic test coverage for cache base service module.
"""

from dotmac.core.cache.base_service import BaseService, ConfigurableService, ServiceStatus, ServiceHealth


class TestConcreteService(BaseService):
    """Concrete implementation of BaseService for testing."""
    
    async def initialize(self) -> bool:
        self.status = ServiceStatus.RUNNING
        return True
    
    async def shutdown(self) -> bool:
        self.status = ServiceStatus.STOPPED
        return True
    
    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(
            healthy=self.status == ServiceStatus.RUNNING,
            service_name=self.service_name
        )


class TestBaseService:
    """Test BaseService functionality."""

    def test_base_service_initialization(self):
        """Test base service initialization."""
        service = TestConcreteService("test_service")
        
        assert service.service_name == "test_service"
        assert service.service_type == "generic"
        assert service.dependencies == []
        assert service.status == ServiceStatus.UNINITIALIZED

    def test_base_service_with_dependencies(self):
        """Test base service with dependencies."""
        deps = ["db", "cache"]
        service = TestConcreteService("test_service", "custom", deps)
        
        assert service.service_name == "test_service"
        assert service.service_type == "custom"
        assert service.dependencies == deps

    async def test_base_service_lifecycle(self):
        """Test service lifecycle methods."""
        service = TestConcreteService("test_service")
        
        # Initial state
        assert service.status == ServiceStatus.UNINITIALIZED
        
        # Initialize
        result = await service.initialize()
        assert result is True
        assert service.status == ServiceStatus.RUNNING
        
        # Shutdown
        result = await service.shutdown()
        assert result is True
        assert service.status == ServiceStatus.STOPPED

    async def test_base_service_health_check(self):
        """Test health check functionality."""
        service = TestConcreteService("test_service")
        
        # Health check before initialization
        health = await service.health_check()
        assert health.healthy is False
        assert health.service_name == "test_service"
        
        # Health check after initialization
        await service.initialize()
        health = await service.health_check()
        assert health.healthy is True

    async def test_get_service_info(self):
        """Test service info retrieval."""
        service = TestConcreteService("test_service", "test_type", ["dep1"])
        
        info = await service.get_service_info()
        
        assert info["service_name"] == "test_service"
        assert info["service_type"] == "test_type"
        assert info["status"] == ServiceStatus.UNINITIALIZED.value
        assert info["dependencies"] == ["dep1"]
        assert "timestamp" in info


class TestConcreteConfigurableService(ConfigurableService):
    """Concrete implementation of ConfigurableService for testing."""
    
    async def initialize(self) -> bool:
        self.status = ServiceStatus.RUNNING
        return True
    
    async def shutdown(self) -> bool:
        self.status = ServiceStatus.STOPPED
        return True
    
    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(
            healthy=self.status == ServiceStatus.RUNNING,
            service_name=self.service_name
        )


class TestConfigurableService:
    """Test ConfigurableService functionality."""
    
    def test_configurable_service_initialization(self):
        """Test configurable service initialization."""
        config = {"key1": "value1", "key2": 42}
        service = TestConcreteConfigurableService("config_service", config=config)
        
        assert service.service_name == "config_service"
        assert service.service_type == "configurable"
        assert service.config == config

    def test_get_config_value(self):
        """Test configuration value retrieval."""
        config = {"timeout": 30, "enabled": True}
        service = TestConcreteConfigurableService("config_service", config=config)
        
        assert service.get_config_value("timeout") == 30
        assert service.get_config_value("enabled") is True
        assert service.get_config_value("missing", "default") == "default"
        assert service.get_config_value("missing") is None

    def test_update_config(self):
        """Test configuration updates."""
        service = TestConcreteConfigurableService("config_service", config={"old": "value"})
        
        service.update_config({"new": "value", "old": "updated"})
        
        assert service.config["new"] == "value"
        assert service.config["old"] == "updated"


class TestServiceStatus:
    """Test ServiceStatus enum."""
    
    def test_service_status_values(self):
        """Test service status enum values."""
        assert ServiceStatus.UNINITIALIZED == "uninitialized"
        assert ServiceStatus.INITIALIZING == "initializing" 
        assert ServiceStatus.RUNNING == "running"
        assert ServiceStatus.DEGRADED == "degraded"
        assert ServiceStatus.ERROR == "error"
        assert ServiceStatus.STOPPED == "stopped"


class TestServiceHealth:
    """Test ServiceHealth dataclass."""
    
    def test_service_health_creation(self):
        """Test ServiceHealth creation."""
        health = ServiceHealth(healthy=True, service_name="test")
        
        assert health.healthy is True
        assert health.service_name == "test"
        assert health.details == {}
        assert health.timestamp is not None

    def test_service_health_with_details(self):
        """Test ServiceHealth with custom details."""
        details = {"cpu_usage": 45.2, "memory_usage": 1024}
        health = ServiceHealth(
            healthy=False, 
            service_name="test",
            status=ServiceStatus.DEGRADED,
            details=details
        )
        
        assert health.healthy is False
        assert health.status == ServiceStatus.DEGRADED
        assert health.details == details
