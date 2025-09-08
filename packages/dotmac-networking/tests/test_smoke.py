"""
Smoke tests for dotmac-networking package - basic functionality verification.
"""

import sys
from pathlib import Path

import pytest

# Add local source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSmokeTests:
    """Basic smoke tests to verify core functionality."""

    def test_basic_imports_work(self):
        """Test that basic imports work without errors."""
        from dotmac.networking import (
            NetworkingService,
            create_networking_service,
        )
        from dotmac.networking.ipam.core.exceptions import IPAMError
        from dotmac.networking.ipam.core.models import AllocationStatus, NetworkType

        # Should be able to create instances
        service = NetworkingService()
        assert service is not None

        factory_service = create_networking_service()
        assert isinstance(factory_service, NetworkingService)

        # Enums should work
        assert NetworkType.CUSTOMER == "customer"
        assert AllocationStatus.ALLOCATED == "allocated"

        # Exceptions should work
        error = IPAMError("test")
        assert str(error) == "test"

    def test_ipam_service_creation(self):
        """Test IPAM service can be created and used."""
        from dotmac.networking.ipam.services.ipam_service import IPAMService

        # Should be able to create service
        service = IPAMService()
        assert service is not None

        # Check configuration defaults
        assert service.default_lease_time == 86400
        assert service.conflict_detection is True

        # Check private attributes exist
        assert hasattr(service, "_in_memory_networks")
        assert hasattr(service, "_in_memory_allocations")

    def test_networking_service_properties(self):
        """Test NetworkingService lazy loading properties."""
        from dotmac.networking import NetworkingService

        service = NetworkingService()

        # Properties should be None initially (lazy loading)
        assert service._ipam is None
        assert service._automation is None
        assert service._monitoring is None
        assert service._radius is None

        # Should have config
        assert isinstance(service.config, dict)
        assert "ipam" in service.config

    def test_configuration_management(self):
        """Test configuration management works correctly."""
        from dotmac.networking import get_default_config

        # Should return copies
        config1 = get_default_config()
        config2 = get_default_config()

        assert config1 == config2
        assert config1 is not config2

        # Should have expected structure
        assert "ipam" in config1
        assert "automation" in config1
        assert "monitoring" in config1
        assert "radius" in config1

        # Values should match defaults
        assert config1["ipam"]["default_subnet_size"] == 24
        assert config1["automation"]["ssh_timeout"] == 30
        assert config1["monitoring"]["snmp_timeout"] == 10
        assert config1["radius"]["auth_port"] == 1812

    @pytest.mark.asyncio
    async def test_async_ipam_methods_exist(self):
        """Test that async IPAM methods exist and are callable."""
        import inspect

        from dotmac.networking.ipam.services.ipam_service import IPAMService

        service = IPAMService()

        # These should be async methods
        assert inspect.iscoroutinefunction(service.create_network)
        assert inspect.iscoroutinefunction(service.allocate_ip)
        assert inspect.iscoroutinefunction(service.reserve_ip)
        assert inspect.iscoroutinefunction(service.release_allocation)

        # Should be able to call helper methods
        assert callable(service._use_database)
        assert callable(service._utc_now)

    def test_model_enums_comprehensive(self):
        """Test all model enums have expected values."""
        from dotmac.networking.ipam.core.models import (
            AllocationStatus,
            NetworkType,
            ReservationStatus,
        )

        # NetworkType should have ISP-relevant values
        expected_network_types = {
            "CUSTOMER", "INFRASTRUCTURE", "MANAGEMENT",
            "SERVICE", "TRANSIT", "LOOPBACK", "POINT_TO_POINT"
        }
        actual_network_types = {attr for attr in dir(NetworkType)
                               if not attr.startswith("_") and attr.isupper()}
        assert expected_network_types.issubset(actual_network_types)

        # AllocationStatus should have lifecycle values
        expected_alloc_statuses = {"ALLOCATED", "RELEASED", "EXPIRED", "RESERVED"}
        actual_alloc_statuses = {attr for attr in dir(AllocationStatus)
                                if not attr.startswith("_") and attr.isupper()}
        assert expected_alloc_statuses.issubset(actual_alloc_statuses)

        # ReservationStatus should have reservation lifecycle values
        expected_res_statuses = {"RESERVED", "ALLOCATED", "EXPIRED", "CANCELLED"}
        actual_res_statuses = {attr for attr in dir(ReservationStatus)
                              if not attr.startswith("_") and attr.isupper()}
        assert expected_res_statuses.issubset(actual_res_statuses)

    def test_exception_hierarchy_complete(self):
        """Test exception hierarchy is properly structured."""
        from dotmac.networking.ipam.core.exceptions import (
            AllocationNotFoundError,
            InsufficientAddressSpaceError,
            IPAddressConflictError,
            IPAMError,
            NetworkNotFoundError,
            NetworkOverlapError,
        )

        # All should inherit from IPAMError
        exceptions = [
            NetworkNotFoundError,
            NetworkOverlapError,
            IPAddressConflictError,
            InsufficientAddressSpaceError,
            AllocationNotFoundError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, IPAMError)

            # Should be able to instantiate with appropriate args
            if exc_class == NetworkOverlapError:
                exc = exc_class("192.168.1.0/24", "192.168.0.0/16")
                assert "192.168.1.0/24" in str(exc)
            else:
                exc = exc_class("test message")
                assert "test message" in str(exc)

    def test_snmp_config_dataclass(self):
        """Test SNMP configuration dataclass works."""
        try:
            from dotmac.networking.monitoring.snmp_collector import SNMPConfig

            # Should work with defaults
            config = SNMPConfig()
            assert config.community == "public"
            assert config.version == "2c"
            assert config.timeout == 10
            assert config.retries == 3

            # Should work with custom values
            custom_config = SNMPConfig(
                community="private",
                version="3",
                timeout=30,
                retries=5
            )
            assert custom_config.community == "private"
            assert custom_config.timeout == 30
        except ImportError:
            pytest.skip("SNMP collector not available due to missing dependencies")

    def test_package_metadata(self):
        """Test package has proper metadata."""
        import dotmac.networking as networking_pkg

        # Should have version info
        assert hasattr(networking_pkg, "__version__") or "version" in dir(networking_pkg)

        # Should have proper docstring
        assert networking_pkg.__doc__ is not None
        assert len(networking_pkg.__doc__.strip()) > 100  # Should be comprehensive

        # Should have __all__ defined
        assert hasattr(networking_pkg, "__all__")
        assert isinstance(networking_pkg.__all__, list)
        assert len(networking_pkg.__all__) > 10  # Should export many symbols


@pytest.mark.integration
class TestIntegrationSmoke:
    """Integration smoke tests."""

    @pytest.mark.asyncio
    async def test_end_to_end_ipam_workflow(self):
        """Test basic IPAM workflow without database."""
        from dotmac.networking.ipam.services.ipam_service import IPAMService

        service = IPAMService()  # No database session = in-memory mode

        # Should be able to create a network
        network = await service.create_network(
            tenant_id="test-tenant",
            network_id="test-network",
            cidr="192.168.1.0/24",
            network_name="Test Network"
        )

        assert network["network_id"] == "test-network"
        assert network["cidr"] == "192.168.1.0/24"
        assert network["is_active"] is True

        # Should be able to allocate an IP
        allocation = await service.allocate_ip(
            tenant_id="test-tenant",
            network_id="test-network",
            assigned_to="test-device"
        )

        assert "allocation_id" in allocation
        assert allocation["network_id"] == "test-network"
        assert allocation["allocation_status"] == "allocated"

        # Should be able to get utilization
        utilization = await service.get_network_utilization(
            tenant_id="test-tenant",
            network_id="test-network"
        )

        assert utilization["total_addresses"] == 256
        assert utilization["allocated_addresses"] == 1
        assert utilization["utilization_percent"] > 0

    def test_networking_service_integration(self):
        """Test NetworkingService integrates components properly."""
        from dotmac.networking import NetworkingService

        custom_config = {
            "ipam": {"default_subnet_size": 16},
            "automation": {"ssh_timeout": 60},
            "monitoring": {"snmp_timeout": 20},
            "radius": {"auth_port": 1645},
        }

        service = NetworkingService(config=custom_config)

        # Should use custom config
        assert service.config["ipam"]["default_subnet_size"] == 16
        assert service.config["automation"]["ssh_timeout"] == 60

        # Service properties should be lazy-loaded
        assert service._ipam is None
        assert service._automation is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
