"""
Basic import tests for dotmac-networking package.
"""

import os
import sys
from unittest.mock import patch

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))


class TestBasicImports:
    """Test basic imports work correctly."""

    def test_import_networking_package(self):
        """Test basic networking package import."""
        # Mock the problematic imports first
        with patch.dict('sys.modules', {
            'dotmac.core.get_logger': None,
            'dotmac.core.retry_on_failure': None,
            'dotmac.core.standard_exception_handler': None,
        }):
            # Should be able to import the package structure
            import dotmac.networking
            assert dotmac.networking is not None

    def test_import_networking_enums(self):
        """Test importing networking enums."""
        from dotmac.networking.ipam.core.models import (
            AllocationStatus,
            NetworkType,
            ReservationStatus,
        )

        assert NetworkType.CUSTOMER == "customer"
        assert AllocationStatus.ALLOCATED == "allocated"
        assert ReservationStatus.RESERVED == "reserved"

    def test_import_snmp_config(self):
        """Test importing SNMP config with mocked dependencies."""
        # Mock the core imports that are causing issues
        with patch.dict('sys.modules', {
            'dotmac.core': patch.MagicMock(),
        }):
            from dotmac.networking.monitoring.snmp_collector import SNMPConfig

            config = SNMPConfig()
            assert config.community == "public"
            assert config.version == "2c"
            assert config.timeout == 10
            assert config.retries == 3


class TestMockedSNMPCollector:
    """Test SNMP collector with mocked dependencies."""

    def test_snmp_config_creation(self):
        """Test SNMP config can be created."""
        # Mock the dotmac.core module completely
        mock_core = patch.MagicMock()
        mock_core.get_logger.return_value = patch.MagicMock()
        mock_core.retry_on_failure = lambda *args, **kwargs: lambda f: f
        mock_core.standard_exception_handler = lambda f: f

        with patch.dict('sys.modules', {'dotmac.core': mock_core}):
            from dotmac.networking.monitoring.snmp_collector import (
                SNMPCollector,
                SNMPConfig,
            )

            # Test SNMPConfig
            config = SNMPConfig()
            assert config.community == "public"
            assert config.version == "2c"

            # Test SNMPCollector creation
            collector = SNMPCollector()
            assert collector is not None
            assert hasattr(collector, 'oids')
            assert isinstance(collector.oids, dict)

            # Test some OID mappings exist
            assert 'system_name' in collector.oids
            assert 'if_in_octets' in collector.oids
            assert 'cisco_cpu_5sec' in collector.oids


class TestIPAMModels:
    """Test IPAM models without SQLAlchemy dependency."""

    def test_enum_values(self):
        """Test enum values are correct."""
        from dotmac.networking.ipam.core.models import AllocationStatus, NetworkType

        # Test NetworkType enum
        assert NetworkType.CUSTOMER.value == "customer"
        assert NetworkType.INFRASTRUCTURE.value == "infrastructure"
        assert NetworkType.MANAGEMENT.value == "management"

        # Test AllocationStatus enum
        assert AllocationStatus.ALLOCATED.value == "allocated"
        assert AllocationStatus.RELEASED.value == "released"
        assert AllocationStatus.EXPIRED.value == "expired"

    def test_sqlalchemy_availability_flag(self):
        """Test SQLAlchemy availability flag."""
        from dotmac.networking.ipam.core.models import SQLALCHEMY_AVAILABLE

        # Should be a boolean
        assert isinstance(SQLALCHEMY_AVAILABLE, bool)

    @patch('dotmac.networking.ipam.core.models.SQLALCHEMY_AVAILABLE', False)
    def test_model_stubs_when_sqlalchemy_unavailable(self):
        """Test model stubs exist when SQLAlchemy is unavailable."""
        from dotmac.networking.ipam.core.models import (
            IPAllocation,
            IPNetwork,
            IPReservation,
        )

        # Should be able to instantiate stub classes
        network = IPNetwork()
        allocation = IPAllocation()
        reservation = IPReservation()

        assert network is not None
        assert allocation is not None
        assert reservation is not None


class TestIPAMExceptions:
    """Test IPAM exceptions can be imported."""

    def test_import_ipam_exceptions(self):
        """Test importing IPAM exceptions."""
        from dotmac.networking.ipam.core.exceptions import (
            AllocationNotFoundError,
            InsufficientAddressSpaceError,
            IPAddressConflictError,
            IPAMError,
            NetworkNotFoundError,
            NetworkOverlapError,
        )

        # Test base exception
        error = IPAMError("test message")
        assert str(error) == "test message"

        # Test specific exceptions
        network_error = NetworkNotFoundError("net-123")
        assert "net-123" in str(network_error)

        overlap_error = NetworkOverlapError("192.168.1.0/24", "192.168.0.0/16")
        assert "192.168.1.0/24" in str(overlap_error)
        assert "192.168.0.0/16" in str(overlap_error)

        conflict_error = IPAddressConflictError("192.168.1.1")
        assert "192.168.1.1" in str(conflict_error)

        space_error = InsufficientAddressSpaceError("net-123")
        assert "net-123" in str(space_error)

        alloc_error = AllocationNotFoundError("alloc-123")
        assert "alloc-123" in str(alloc_error)


class TestNetworkingServiceBasics:
    """Test basic NetworkingService functionality."""

    def test_default_config_structure(self):
        """Test default config has expected structure."""
        # Import directly to avoid dependency issues
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        from dotmac.networking import DEFAULT_CONFIG, get_default_config

        assert isinstance(DEFAULT_CONFIG, dict)
        assert "ipam" in DEFAULT_CONFIG
        assert "automation" in DEFAULT_CONFIG
        assert "monitoring" in DEFAULT_CONFIG
        assert "radius" in DEFAULT_CONFIG

        # Test get_default_config returns a copy
        config1 = get_default_config()
        config2 = get_default_config()

        assert config1 == config2
        assert config1 is not config2  # Different objects

    def test_default_config_values(self):
        """Test default configuration values."""
        from dotmac.networking import DEFAULT_CONFIG

        # Test IPAM defaults
        ipam_config = DEFAULT_CONFIG["ipam"]
        assert ipam_config["default_subnet_size"] == 24
        assert ipam_config["dhcp_lease_time"] == 86400
        assert ipam_config["conflict_detection"] is True

        # Test automation defaults
        automation_config = DEFAULT_CONFIG["automation"]
        assert automation_config["ssh_timeout"] == 30
        assert automation_config["retry_attempts"] == 3

        # Test monitoring defaults
        monitoring_config = DEFAULT_CONFIG["monitoring"]
        assert monitoring_config["snmp_timeout"] == 10
        assert monitoring_config["community"] == "public"

        # Test RADIUS defaults
        radius_config = DEFAULT_CONFIG["radius"]
        assert radius_config["auth_port"] == 1812
        assert radius_config["acct_port"] == 1813
