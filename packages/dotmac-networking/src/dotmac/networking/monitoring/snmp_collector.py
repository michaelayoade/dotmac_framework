"""
SNMP Collector - Network device data collection via SNMP
"""

from dataclasses import dataclass
from typing import Any, Optional

from dotmac.core import get_logger, retry_on_failure, standard_exception_handler

logger = get_logger(__name__)


@dataclass
class SNMPConfig:
    """SNMP configuration"""

    community: str = "public"
    version: str = "2c"
    timeout: int = 10
    retries: int = 3


class SNMPCollector:
    """
    SNMP data collector for network devices

    Provides comprehensive SNMP monitoring with vendor-specific OID support
    for ISP network infrastructure monitoring.
    """

    def __init__(self, default_config: Optional[SNMPConfig] = None):
        self.default_config = default_config or SNMPConfig()

        # Comprehensive SNMP OID library for major network vendors
        self.oids = {
            # RFC 1213 - MIB-II Standard OIDs
            "system_name": "1.3.6.1.2.1.1.5.0",
            "system_uptime": "1.3.6.1.2.1.1.3.0",
            "system_description": "1.3.6.1.2.1.1.1.0",
            "system_contact": "1.3.6.1.2.1.1.4.0",
            "system_location": "1.3.6.1.2.1.1.6.0",
            # Interface Statistics (RFC 1213)
            "if_table": "1.3.6.1.2.1.2.2.1",
            "if_name": "1.3.6.1.2.1.2.2.1.2",
            "if_type": "1.3.6.1.2.1.2.2.1.3",
            "if_speed": "1.3.6.1.2.1.2.2.1.5",
            "if_admin_status": "1.3.6.1.2.1.2.2.1.7",
            "if_oper_status": "1.3.6.1.2.1.2.2.1.8",
            "if_in_octets": "1.3.6.1.2.1.2.2.1.10",
            "if_out_octets": "1.3.6.1.2.1.2.2.1.16",
            "if_in_errors": "1.3.6.1.2.1.2.2.1.14",
            "if_out_errors": "1.3.6.1.2.1.2.2.1.20",
            "if_in_discards": "1.3.6.1.2.1.2.2.1.13",
            "if_out_discards": "1.3.6.1.2.1.2.2.1.19",
            # Cisco-specific OIDs
            "cisco_cpu_5sec": "1.3.6.1.4.1.9.2.1.56.0",
            "cisco_cpu_1min": "1.3.6.1.4.1.9.2.1.57.0",
            "cisco_cpu_5min": "1.3.6.1.4.1.9.2.1.58.0",
            "cisco_memory_used": "1.3.6.1.4.1.9.2.1.8.0",
            "cisco_memory_free": "1.3.6.1.4.1.9.2.1.9.0",
            "cisco_temperature": "1.3.6.1.4.1.9.2.1.8.0",
            # Juniper-specific OIDs
            "juniper_cpu_util": "1.3.6.1.4.1.2636.3.1.13.1.8",
            "juniper_memory_util": "1.3.6.1.4.1.2636.3.1.13.1.11",
            "juniper_temperature": "1.3.6.1.4.1.2636.3.1.13.1.7",
            # Mikrotik-specific OIDs
            "mikrotik_cpu_load": "1.3.6.1.2.1.25.3.3.1.2",
            "mikrotik_memory_total": "1.3.6.1.2.1.25.2.2.0",
            "mikrotik_disk_total": "1.3.6.1.4.1.14988.1.1.1.1.0",
            # Generic Host Resources MIB
            "hr_cpu_load": "1.3.6.1.2.1.25.3.3.1.2",
            "hr_memory_size": "1.3.6.1.2.1.25.2.2.0",
            "hr_storage_table": "1.3.6.1.2.1.25.2.3.1",
        }

        # Vendor-specific OID mappings
        self.vendor_oids = {
            "cisco": {
                "cpu_utilization": "cisco_cpu_5sec",
                "memory_used": "cisco_memory_used",
                "memory_free": "cisco_memory_free",
            },
            "juniper": {
                "cpu_utilization": "juniper_cpu_util",
                "memory_utilization": "juniper_memory_util",
                "temperature": "juniper_temperature",
            },
            "mikrotik": {
                "cpu_utilization": "mikrotik_cpu_load",
                "memory_total": "mikrotik_memory_total",
            },
            "generic": {
                "cpu_utilization": "hr_cpu_load",
                "memory_total": "hr_memory_size",
            },
        }

    @standard_exception_handler
    @retry_on_failure(max_attempts=3, delay=1.0)
    async def get_system_info(self, host: str, community: Optional[str] = None) -> dict[str, Any]:
        """
        Get basic system information via SNMP

        Returns system name, description, uptime, contact, location
        """
        community = community or self.default_config.community

        # Mock implementation - in production, use pysnmp
        logger.info(f"Collecting system info from {host} with community '{community}'")

        # Simulate SNMP data collection
        return {
            "name": f"router-{host.split('.')[-1]}",
            "description": "Cisco IOS Router",
            "uptime": 864000,  # 10 days in seconds
            "contact": "network-admin@isp.com",
            "location": "Data Center Rack 42",
        }

    @standard_exception_handler
    @retry_on_failure(max_attempts=3, delay=1.0)
    async def get_cpu_utilization(
        self, host: str, community: Optional[str] = None, vendor: str = "generic"
    ) -> Optional[float]:
        """
        Get CPU utilization percentage for specified vendor
        """
        community = community or self.default_config.community
        vendor_mapping = self.vendor_oids.get(vendor, self.vendor_oids["generic"])
        cpu_oid = self.oids.get(vendor_mapping["cpu_utilization"])

        logger.debug(f"Getting CPU utilization from {host} using OID {cpu_oid}")

        # Mock CPU utilization - in production, use SNMP
        import random

        return random.uniform(15.0, 85.0)

    @standard_exception_handler
    @retry_on_failure(max_attempts=3, delay=1.0)
    async def get_memory_utilization(
        self, host: str, community: Optional[str] = None, vendor: str = "generic"
    ) -> Optional[float]:
        """
        Get memory utilization percentage for specified vendor
        """
        community = community or self.default_config.community

        logger.debug(f"Getting memory utilization from {host}")

        # Mock memory utilization - in production, calculate from SNMP data
        import random

        return random.uniform(30.0, 90.0)

    @standard_exception_handler
    @retry_on_failure(max_attempts=3, delay=1.0)
    async def get_interface_statistics(
        self, host: str, community: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Get comprehensive interface statistics for all interfaces
        """
        community = community or self.default_config.community

        logger.debug(f"Getting interface statistics from {host}")

        # Mock interface data - in production, walk interface table
        interfaces = [
            {
                "index": 1,
                "name": "GigabitEthernet0/0",
                "type": "ethernetCsmacd",
                "speed": 1000000000,  # 1 Gbps
                "admin_status": "up",
                "oper_status": "up",
                "in_octets": 1234567890,
                "out_octets": 987654321,
                "in_errors": 0,
                "out_errors": 0,
                "utilization": 45.2,  # Calculated utilization %
            },
            {
                "index": 2,
                "name": "GigabitEthernet0/1",
                "type": "ethernetCsmacd",
                "speed": 1000000000,
                "admin_status": "up",
                "oper_status": "down",
                "in_octets": 0,
                "out_octets": 0,
                "in_errors": 0,
                "out_errors": 0,
                "utilization": 0.0,
            },
        ]

        return interfaces

    async def get_device_inventory(
        self, host: str, community: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get comprehensive device inventory information
        """
        community = community or self.default_config.community

        # Collect all device information
        system_info = await self.get_system_info(host, community)
        interfaces = await self.get_interface_statistics(host, community)

        return {
            "host": host,
            "system": system_info,
            "interface_count": len(interfaces),
            "interfaces": interfaces,
            "collected_at": "2024-01-01T12:00:00Z",
        }

    def get_supported_vendors(self) -> list[str]:
        """Get list of supported vendor-specific OID mappings"""
        return list(self.vendor_oids.keys())

    def get_vendor_oids(self, vendor: str) -> Optional[dict[str, str]]:
        """Get OID mappings for specific vendor"""
        return self.vendor_oids.get(vendor)
