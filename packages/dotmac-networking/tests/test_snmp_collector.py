"""
Tests for SNMP Collector - Network device data collection via SNMP.
"""

from unittest.mock import patch

import pytest

from dotmac.networking.monitoring.snmp_collector import SNMPCollector, SNMPConfig


class TestSNMPConfig:
    """Test SNMP configuration dataclass."""

    def test_default_values(self):
        """Test default SNMP configuration values."""
        config = SNMPConfig()

        assert config.community == "public"
        assert config.version == "2c"
        assert config.timeout == 10
        assert config.retries == 3

    def test_custom_values(self):
        """Test SNMP configuration with custom values."""
        config = SNMPConfig(
            community="private",
            version="3",
            timeout=30,
            retries=5
        )

        assert config.community == "private"
        assert config.version == "3"
        assert config.timeout == 30
        assert config.retries == 5


class TestSNMPCollectorInitialization:
    """Test SNMP collector initialization and configuration."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        collector = SNMPCollector()

        assert collector.default_config.community == "public"
        assert collector.default_config.version == "2c"
        assert collector.default_config.timeout == 10
        assert collector.default_config.retries == 3

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        custom_config = SNMPConfig(
            community="monitoring",
            version="2c",
            timeout=15,
            retries=2
        )

        collector = SNMPCollector(default_config=custom_config)

        assert collector.default_config.community == "monitoring"
        assert collector.default_config.timeout == 15
        assert collector.default_config.retries == 2

    def test_oid_library_structure(self):
        """Test SNMP OID library structure and key OIDs."""
        collector = SNMPCollector()

        # Test standard MIB-II OIDs
        assert "system_name" in collector.oids
        assert "system_uptime" in collector.oids
        assert "if_table" in collector.oids
        assert "if_in_octets" in collector.oids
        assert "if_out_octets" in collector.oids

        # Test vendor-specific OIDs
        assert "cisco_cpu_5sec" in collector.oids
        assert "juniper_cpu_util" in collector.oids
        assert "mikrotik_cpu_load" in collector.oids

        # Verify OID format (should be dotted decimal)
        assert collector.oids["system_name"] == "1.3.6.1.2.1.1.5.0"
        assert collector.oids["if_in_octets"] == "1.3.6.1.2.1.2.2.1.10"

    def test_vendor_oid_mappings(self):
        """Test vendor-specific OID mappings."""
        collector = SNMPCollector()

        # Test Cisco mappings
        cisco_oids = collector.vendor_oids["cisco"]
        assert "cpu_utilization" in cisco_oids
        assert cisco_oids["cpu_utilization"] == "cisco_cpu_5sec"

        # Test Juniper mappings
        juniper_oids = collector.vendor_oids["juniper"]
        assert "cpu_utilization" in juniper_oids
        assert juniper_oids["cpu_utilization"] == "juniper_cpu_util"

        # Test generic mappings
        generic_oids = collector.vendor_oids["generic"]
        assert "cpu_utilization" in generic_oids
        assert generic_oids["cpu_utilization"] == "hr_cpu_load"


class TestSNMPCollectorSystemInfo:
    """Test system information collection."""

    @pytest.mark.asyncio
    async def test_get_system_info_success(self):
        """Test successful system information collection."""
        collector = SNMPCollector()

        result = await collector.get_system_info("192.168.1.1")

        assert isinstance(result, dict)
        assert "name" in result
        assert "description" in result
        assert "uptime" in result
        assert "contact" in result
        assert "location" in result

        # Verify expected format
        assert isinstance(result["uptime"], int)
        assert result["uptime"] > 0

    @pytest.mark.asyncio
    async def test_get_system_info_custom_community(self):
        """Test system info collection with custom community."""
        collector = SNMPCollector()

        with patch('dotmac.networking.monitoring.snmp_collector.logger') as mock_logger:
            result = await collector.get_system_info("192.168.1.1", community="private")

            # Should log with custom community
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "private" in call_args

        assert isinstance(result, dict)
        assert "name" in result

    @pytest.mark.asyncio
    async def test_get_system_info_uses_default_community(self):
        """Test system info uses default community when none specified."""
        custom_config = SNMPConfig(community="monitoring")
        collector = SNMPCollector(default_config=custom_config)

        with patch('dotmac.networking.monitoring.snmp_collector.logger') as mock_logger:
            await collector.get_system_info("192.168.1.1")

            # Should use default community
            call_args = mock_logger.info.call_args[0][0]
            assert "monitoring" in call_args


class TestSNMPCollectorCPUUtilization:
    """Test CPU utilization collection."""

    @pytest.mark.asyncio
    async def test_get_cpu_utilization_generic(self):
        """Test CPU utilization collection for generic devices."""
        collector = SNMPCollector()

        result = await collector.get_cpu_utilization("192.168.1.1")

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    @pytest.mark.asyncio
    async def test_get_cpu_utilization_cisco(self):
        """Test CPU utilization collection for Cisco devices."""
        collector = SNMPCollector()

        result = await collector.get_cpu_utilization("192.168.1.1", vendor="cisco")

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    @pytest.mark.asyncio
    async def test_get_cpu_utilization_juniper(self):
        """Test CPU utilization collection for Juniper devices."""
        collector = SNMPCollector()

        result = await collector.get_cpu_utilization("192.168.1.1", vendor="juniper")

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    @pytest.mark.asyncio
    async def test_get_cpu_utilization_unknown_vendor(self):
        """Test CPU utilization collection for unknown vendor (falls back to generic)."""
        collector = SNMPCollector()

        result = await collector.get_cpu_utilization("192.168.1.1", vendor="unknown")

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    @pytest.mark.asyncio
    async def test_get_cpu_utilization_custom_community(self):
        """Test CPU utilization with custom community string."""
        collector = SNMPCollector()

        result = await collector.get_cpu_utilization(
            "192.168.1.1",
            community="private",
            vendor="cisco"
        )

        assert isinstance(result, float)


class TestSNMPCollectorMemoryUtilization:
    """Test memory utilization collection."""

    @pytest.mark.asyncio
    async def test_get_memory_utilization_success(self):
        """Test successful memory utilization collection."""
        collector = SNMPCollector()

        result = await collector.get_memory_utilization("192.168.1.1")

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    @pytest.mark.asyncio
    async def test_get_memory_utilization_vendor_specific(self):
        """Test memory utilization with vendor-specific settings."""
        collector = SNMPCollector()

        result = await collector.get_memory_utilization(
            "192.168.1.1",
            vendor="cisco",
            community="private"
        )

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0


class TestSNMPCollectorInterfaceStatistics:
    """Test interface statistics collection."""

    @pytest.mark.asyncio
    async def test_get_interface_statistics_success(self):
        """Test successful interface statistics collection."""
        collector = SNMPCollector()

        result = await collector.get_interface_statistics("192.168.1.1")

        assert isinstance(result, list)
        assert len(result) > 0

        # Test first interface structure
        interface = result[0]
        assert "index" in interface
        assert "name" in interface
        assert "type" in interface
        assert "speed" in interface
        assert "admin_status" in interface
        assert "oper_status" in interface
        assert "in_octets" in interface
        assert "out_octets" in interface
        assert "in_errors" in interface
        assert "out_errors" in interface
        assert "utilization" in interface

        # Verify data types
        assert isinstance(interface["index"], int)
        assert isinstance(interface["speed"], int)
        assert isinstance(interface["in_octets"], int)
        assert isinstance(interface["out_octets"], int)
        assert isinstance(interface["utilization"], float)

    @pytest.mark.asyncio
    async def test_get_interface_statistics_multiple_interfaces(self):
        """Test interface statistics returns multiple interfaces."""
        collector = SNMPCollector()

        result = await collector.get_interface_statistics("192.168.1.1")

        # Should have at least 2 interfaces in mock data
        assert len(result) >= 2

        # Test that interfaces have different indices
        indices = [iface["index"] for iface in result]
        assert len(set(indices)) == len(indices)  # All unique

    @pytest.mark.asyncio
    async def test_get_interface_statistics_custom_community(self):
        """Test interface statistics with custom community."""
        collector = SNMPCollector()

        result = await collector.get_interface_statistics("192.168.1.1", community="private")

        assert isinstance(result, list)
        assert len(result) > 0


class TestSNMPCollectorDeviceInventory:
    """Test comprehensive device inventory collection."""

    @pytest.mark.asyncio
    async def test_get_device_inventory_success(self):
        """Test successful device inventory collection."""
        collector = SNMPCollector()

        result = await collector.get_device_inventory("192.168.1.1")

        assert isinstance(result, dict)
        assert "host" in result
        assert "system" in result
        assert "interface_count" in result
        assert "interfaces" in result
        assert "collected_at" in result

        assert result["host"] == "192.168.1.1"
        assert isinstance(result["system"], dict)
        assert isinstance(result["interface_count"], int)
        assert isinstance(result["interfaces"], list)

        # System info should have expected fields
        system = result["system"]
        assert "name" in system
        assert "description" in system
        assert "uptime" in system

    @pytest.mark.asyncio
    async def test_get_device_inventory_integrates_data(self):
        """Test device inventory integrates system and interface data."""
        collector = SNMPCollector()

        result = await collector.get_device_inventory("192.168.1.1")

        # Interface count should match actual interfaces
        assert result["interface_count"] == len(result["interfaces"])

        # Should have both system and interface data
        assert len(result["system"]) > 0
        assert len(result["interfaces"]) > 0

    @pytest.mark.asyncio
    async def test_get_device_inventory_custom_community(self):
        """Test device inventory with custom community."""
        collector = SNMPCollector()

        result = await collector.get_device_inventory("192.168.1.1", community="monitoring")

        assert isinstance(result, dict)
        assert result["host"] == "192.168.1.1"


class TestSNMPCollectorVendorSupport:
    """Test vendor support and OID mapping functionality."""

    def test_get_supported_vendors(self):
        """Test getting list of supported vendors."""
        collector = SNMPCollector()

        vendors = collector.get_supported_vendors()

        assert isinstance(vendors, list)
        assert "cisco" in vendors
        assert "juniper" in vendors
        assert "mikrotik" in vendors
        assert "generic" in vendors
        assert len(vendors) >= 4

    def test_get_vendor_oids_cisco(self):
        """Test getting Cisco-specific OID mappings."""
        collector = SNMPCollector()

        cisco_oids = collector.get_vendor_oids("cisco")

        assert isinstance(cisco_oids, dict)
        assert "cpu_utilization" in cisco_oids
        assert "memory_used" in cisco_oids
        assert cisco_oids["cpu_utilization"] == "cisco_cpu_5sec"

    def test_get_vendor_oids_juniper(self):
        """Test getting Juniper-specific OID mappings."""
        collector = SNMPCollector()

        juniper_oids = collector.get_vendor_oids("juniper")

        assert isinstance(juniper_oids, dict)
        assert "cpu_utilization" in juniper_oids
        assert "memory_utilization" in juniper_oids
        assert "temperature" in juniper_oids

    def test_get_vendor_oids_unknown(self):
        """Test getting OID mappings for unknown vendor."""
        collector = SNMPCollector()

        unknown_oids = collector.get_vendor_oids("unknown_vendor")

        assert unknown_oids is None

    def test_get_vendor_oids_generic(self):
        """Test getting generic OID mappings."""
        collector = SNMPCollector()

        generic_oids = collector.get_vendor_oids("generic")

        assert isinstance(generic_oids, dict)
        assert "cpu_utilization" in generic_oids
        assert "memory_total" in generic_oids


class TestSNMPCollectorErrorHandling:
    """Test error handling and resilience."""

    @pytest.mark.asyncio
    async def test_retry_decorator_applied(self):
        """Test that retry decorator is properly applied to methods."""
        collector = SNMPCollector()

        # Check that methods have the retry decorator attributes
        # This indirectly tests the decorator is applied
        assert hasattr(collector.get_system_info, '__wrapped__')
        assert hasattr(collector.get_cpu_utilization, '__wrapped__')
        assert hasattr(collector.get_memory_utilization, '__wrapped__')
        assert hasattr(collector.get_interface_statistics, '__wrapped__')

    @pytest.mark.asyncio
    async def test_exception_handler_decorator_applied(self):
        """Test that standard exception handler decorator is applied."""
        collector = SNMPCollector()

        # Methods should have the exception handler decorator
        # This is implicit in the function signature but we can test the behavior
        # by ensuring methods don't raise unhandled exceptions
        try:
            await collector.get_system_info("invalid_host")
            # Should not raise unhandled exceptions due to decorator
        except Exception as e:
            # Any exceptions should be handled appropriately
            pytest.fail(f"Unhandled exception: {e}")


class TestSNMPCollectorLogging:
    """Test logging functionality."""

    @pytest.mark.asyncio
    async def test_system_info_logging(self):
        """Test system info collection includes proper logging."""
        collector = SNMPCollector()

        with patch('dotmac.networking.monitoring.snmp_collector.logger') as mock_logger:
            await collector.get_system_info("192.168.1.1")

            # Should log the collection activity
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "Collecting system info" in call_args
            assert "192.168.1.1" in call_args

    @pytest.mark.asyncio
    async def test_cpu_utilization_logging(self):
        """Test CPU utilization collection includes debug logging."""
        collector = SNMPCollector()

        with patch('dotmac.networking.monitoring.snmp_collector.logger') as mock_logger:
            await collector.get_cpu_utilization("192.168.1.1", vendor="cisco")

            # Should log the OID being used
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "Getting CPU utilization" in call_args
            assert "192.168.1.1" in call_args
