"""
SNMP Client and Collector utilities for device monitoring.

Provides SNMP query capabilities and metric collection functionality.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..exceptions import SNMPError


@dataclass
class SNMPConfig:
    """SNMP configuration parameters."""

    host: str
    port: int = 161
    community: str = "public"
    version: str = "2c"  # 1, 2c, or 3
    timeout: int = 5
    retries: int = 3

    # SNMPv3 specific
    username: Optional[str] = None
    auth_protocol: Optional[str] = None
    auth_password: Optional[str] = None
    priv_protocol: Optional[str] = None
    priv_password: Optional[str] = None


class SNMPClient:
    """SNMP client for querying network devices."""

    # Common SNMP OIDs
    SYSTEM_OID_MAP = {
        "sysDescr": "1.3.6.1.2.1.1.1.0",
        "sysObjectID": "1.3.6.1.2.1.1.2.0",
        "sysUpTime": "1.3.6.1.2.1.1.3.0",
        "sysContact": "1.3.6.1.2.1.1.4.0",
        "sysName": "1.3.6.1.2.1.1.5.0",
        "sysLocation": "1.3.6.1.2.1.1.6.0",
        "sysServices": "1.3.6.1.2.1.1.7.0",
    }

    INTERFACE_OID_MAP = {
        "ifIndex": "1.3.6.1.2.1.2.2.1.1",
        "ifDescr": "1.3.6.1.2.1.2.2.1.2",
        "ifType": "1.3.6.1.2.1.2.2.1.3",
        "ifMtu": "1.3.6.1.2.1.2.2.1.4",
        "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
        "ifPhysAddress": "1.3.6.1.2.1.2.2.1.6",
        "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",
        "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
        "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
        "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
        "ifInErrors": "1.3.6.1.2.1.2.2.1.14",
        "ifOutErrors": "1.3.6.1.2.1.2.2.1.20",
    }

    CPU_MEMORY_OID_MAP = {
        # Cisco specific
        "cpmCPUTotalPhysicalIndex": "1.3.6.1.4.1.9.9.109.1.1.1.1.2",
        "cpmCPUTotal5minRev": "1.3.6.1.4.1.9.9.109.1.1.1.1.8",
        "ciscoMemoryPoolUsed": "1.3.6.1.4.1.9.9.48.1.1.1.5",
        "ciscoMemoryPoolFree": "1.3.6.1.4.1.9.9.48.1.1.1.6",
        # Generic host resources
        "hrProcessorLoad": "1.3.6.1.2.1.25.3.3.1.2",
        "hrMemorySize": "1.3.6.1.2.1.25.2.2.0",
        "hrStorageUsed": "1.3.6.1.2.1.25.2.3.1.6",
        "hrStorageSize": "1.3.6.1.2.1.25.2.3.1.5",
    }

    def __init__(self, config: SNMPConfig):
        """Initialize SNMP client with configuration."""
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """Validate SNMP configuration."""
        if not self.config.host:
            raise SNMPError("Host is required")

        if self.config.version not in ["1", "2c", "3"]:
            raise SNMPError("Invalid SNMP version")

        if self.config.version == "3" and not self.config.username:
            raise SNMPError("Username required for SNMPv3")

    async def get(self, oid: str) -> Optional[Any]:
        """Perform SNMP GET operation."""
        try:
            # Simulate SNMP GET operation
            # In a real implementation, this would use pysnmp or similar library
            await asyncio.sleep(0.1)  # Simulate network delay

            # Mock response based on OID patterns
            return self._mock_snmp_response(oid)

        except Exception as e:
            raise SNMPError(f"SNMP GET failed for OID {oid}: {str(e)}")

    async def walk(self, oid: str) -> List[Tuple[str, Any]]:
        """Perform SNMP WALK operation."""
        try:
            # Simulate SNMP WALK operation
            await asyncio.sleep(0.2)  # Simulate network delay

            # Mock walk response based on OID patterns
            return self._mock_snmp_walk(oid)

        except Exception as e:
            raise SNMPError(f"SNMP WALK failed for OID {oid}: {str(e)}")

    async def get_bulk(self, oids: List[str]) -> Dict[str, Any]:
        """Perform bulk SNMP GET operations."""
        results = {}
        for oid in oids:
            try:
                results[oid] = await self.get(oid)
            except SNMPError:
                results[oid] = None
        return results

    def _mock_snmp_response(self, oid: str) -> Any:
        """Mock SNMP response for testing/development."""
        # System information
        if oid == self.SYSTEM_OID_MAP.get("sysDescr"):
            return f"Mock Router {self.config.host}"
        elif oid == self.SYSTEM_OID_MAP.get("sysName"):
            return f"router-{self.config.host.replace('.', '-')}"
        elif oid == self.SYSTEM_OID_MAP.get("sysUpTime"):
            return 123456789  # Timeticks
        elif oid == self.SYSTEM_OID_MAP.get("sysLocation"):
            return "Data Center"

        # Interface specific
        elif "1.3.6.1.2.1.2.2.1" in oid:
            # Extract interface index from OID
            parts = oid.split(".")
            if len(parts) > 10:
                if_index = parts[-1]
                if "1.3.6.1.2.1.2.2.1.2" in oid:  # ifDescr
                    return f"GigabitEthernet0/{if_index}"
                elif "1.3.6.1.2.1.2.2.1.5" in oid:  # ifSpeed
                    return 1000000000  # 1 Gbps
                elif "1.3.6.1.2.1.2.2.1.7" in oid:  # ifAdminStatus
                    return 1  # up
                elif "1.3.6.1.2.1.2.2.1.8" in oid:  # ifOperStatus
                    return 1  # up

        # CPU/Memory
        elif "1.3.6.1.4.1.9.9.109.1.1.1.1.8" in oid:  # Cisco CPU
            return 25  # 25% CPU utilization
        elif "1.3.6.1.2.1.25.3.3.1.2" in oid:  # Generic CPU
            return 30  # 30% CPU utilization

        return None

    def _mock_snmp_walk(self, base_oid: str) -> List[Tuple[str, Any]]:
        """Mock SNMP walk response."""
        results = []

        # Interface table walk
        if base_oid.startswith("1.3.6.1.2.1.2.2.1"):
            for i in range(1, 5):  # Mock 4 interfaces
                oid = f"{base_oid}.{i}"
                value = self._mock_snmp_response(oid)
                if value is not None:
                    results.append((oid, value))

        return results

    async def test_connectivity(self) -> bool:
        """Test SNMP connectivity to device."""
        try:
            result = await self.get(self.SYSTEM_OID_MAP["sysName"])
            return result is not None
        except SNMPError:
            return False


class SNMPCollector:
    """High-level SNMP metrics collector."""

    def __init__(self, client: SNMPClient):
        """Initialize collector with SNMP client."""
        self.client = client

    async def collect_system_info(self) -> Dict[str, Any]:
        """Collect basic system information."""
        system_oids = [
            ("system_description", self.client.SYSTEM_OID_MAP["sysDescr"]),
            ("system_name", self.client.SYSTEM_OID_MAP["sysName"]),
            ("system_uptime", self.client.SYSTEM_OID_MAP["sysUpTime"]),
            ("system_location", self.client.SYSTEM_OID_MAP["sysLocation"]),
            ("system_contact", self.client.SYSTEM_OID_MAP["sysContact"]),
        ]

        system_info = {}
        for name, oid in system_oids:
            try:
                value = await self.client.get(oid)
                system_info[name] = value
            except SNMPError as e:
                system_info[name] = f"Error: {str(e)}"

        return system_info

    async def collect_interface_stats(self) -> Dict[str, Any]:
        """Collect interface statistics."""
        interface_stats = {
            "interfaces": {},
            "total_interfaces": 0,
            "interfaces_up": 0,
            "interfaces_down": 0,
        }

        try:
            # Walk interface description table
            if_descr_results = await self.client.walk(
                self.client.INTERFACE_OID_MAP["ifDescr"]
            )

            for oid, description in if_descr_results:
                # Extract interface index
                if_index = oid.split(".")[-1]

                # Collect stats for this interface
                interface_data = {"description": description, "index": if_index}

                # Get additional interface data
                try:
                    admin_status = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifAdminStatus']}.{if_index}"
                    )
                    oper_status = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifOperStatus']}.{if_index}"
                    )
                    speed = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifSpeed']}.{if_index}"
                    )
                    in_octets = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifInOctets']}.{if_index}"
                    )
                    out_octets = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifOutOctets']}.{if_index}"
                    )
                    in_errors = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifInErrors']}.{if_index}"
                    )
                    out_errors = await self.client.get(
                        f"{self.client.INTERFACE_OID_MAP['ifOutErrors']}.{if_index}"
                    )

                    interface_data.update(
                        {
                            "admin_status": "up" if admin_status == 1 else "down",
                            "oper_status": "up" if oper_status == 1 else "down",
                            "speed": speed,
                            "in_octets": in_octets,
                            "out_octets": out_octets,
                            "in_errors": in_errors,
                            "out_errors": out_errors,
                        }
                    )

                    # Count interface status
                    interface_stats["total_interfaces"] += 1
                    if oper_status == 1:
                        interface_stats["interfaces_up"] += 1
                    else:
                        interface_stats["interfaces_down"] += 1

                except SNMPError:
                    interface_data["error"] = "Failed to collect interface details"

                interface_stats["interfaces"][if_index] = interface_data

        except SNMPError as e:
            interface_stats["error"] = f"Failed to collect interface stats: {str(e)}"

        return interface_stats

    async def collect_cpu_memory_stats(self) -> Dict[str, Any]:
        """Collect CPU and memory utilization."""
        cpu_memory_stats = {}

        # Try Cisco-specific OIDs first
        try:
            cpu_usage = await self.client.get(
                self.client.CPU_MEMORY_OID_MAP["cpmCPUTotal5minRev"]
            )
            if cpu_usage is not None:
                cpu_memory_stats["cpu_usage"] = cpu_usage
                cpu_memory_stats["cpu_source"] = "cisco"
        except SNMPError:
            # Try generic host resources
            try:
                cpu_usage = await self.client.get(
                    self.client.CPU_MEMORY_OID_MAP["hrProcessorLoad"]
                )
                if cpu_usage is not None:
                    cpu_memory_stats["cpu_usage"] = cpu_usage
                    cpu_memory_stats["cpu_source"] = "host_resources"
            except SNMPError:
                cpu_memory_stats["cpu_usage"] = None
                cpu_memory_stats["cpu_error"] = "Unable to retrieve CPU usage"

        # Try to collect memory stats
        try:
            # Cisco memory
            memory_used = await self.client.get(
                self.client.CPU_MEMORY_OID_MAP["ciscoMemoryPoolUsed"]
            )
            memory_free = await self.client.get(
                self.client.CPU_MEMORY_OID_MAP["ciscoMemoryPoolFree"]
            )

            if memory_used is not None and memory_free is not None:
                total_memory = memory_used + memory_free
                memory_utilization = (
                    (memory_used / total_memory) * 100 if total_memory > 0 else 0
                )
                cpu_memory_stats["memory_usage"] = memory_utilization
                cpu_memory_stats["memory_total"] = total_memory
                cpu_memory_stats["memory_used"] = memory_used
                cpu_memory_stats["memory_source"] = "cisco"

        except SNMPError:
            try:
                # Generic host resources
                memory_size = await self.client.get(
                    self.client.CPU_MEMORY_OID_MAP["hrMemorySize"]
                )
                if memory_size is not None:
                    cpu_memory_stats["memory_total"] = memory_size
                    cpu_memory_stats["memory_source"] = "host_resources"
            except SNMPError:
                cpu_memory_stats["memory_error"] = "Unable to retrieve memory stats"

        return cpu_memory_stats

    async def collect_comprehensive_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive device metrics."""
        start_time = time.time()

        # Collect all metrics concurrently
        try:
            system_task = asyncio.create_task(self.collect_system_info())
            interface_task = asyncio.create_task(self.collect_interface_stats())
            cpu_memory_task = asyncio.create_task(self.collect_cpu_memory_stats())

            system_info, interface_stats, cpu_memory_stats = await asyncio.gather(
                system_task, interface_task, cpu_memory_task, return_exceptions=True
            )

            collection_duration = (
                time.time() - start_time
            ) * 1000  # Convert to milliseconds

            metrics = {
                "collection_timestamp": datetime.utcnow(),
                "collection_duration_ms": collection_duration,
                "collection_status": "success",
                "device_host": self.client.config.host,
            }

            # Add collected metrics
            if not isinstance(system_info, Exception):
                metrics.update(system_info)
            else:
                metrics["system_error"] = str(system_info)

            if not isinstance(interface_stats, Exception):
                metrics.update(interface_stats)
            else:
                metrics["interface_error"] = str(interface_stats)

            if not isinstance(cpu_memory_stats, Exception):
                metrics.update(cpu_memory_stats)
            else:
                metrics["cpu_memory_error"] = str(cpu_memory_stats)

            return metrics

        except Exception as e:
            return {
                "collection_timestamp": datetime.utcnow(),
                "collection_duration_ms": (time.time() - start_time) * 1000,
                "collection_status": "error",
                "error_message": str(e),
                "device_host": self.client.config.host,
            }

    async def test_device_reachability(self) -> Dict[str, Any]:
        """Test device reachability and basic SNMP functionality."""
        test_results = {
            "host": self.client.config.host,
            "port": self.client.config.port,
            "community": self.client.config.community,
            "version": self.client.config.version,
            "test_timestamp": datetime.utcnow(),
            "tests": {},
        }

        # Test basic connectivity
        try:
            connectivity_test = await self.client.test_connectivity()
            test_results["tests"]["connectivity"] = {
                "status": "pass" if connectivity_test else "fail",
                "message": (
                    "SNMP connectivity successful"
                    if connectivity_test
                    else "SNMP connectivity failed"
                ),
            }
        except Exception as e:
            test_results["tests"]["connectivity"] = {
                "status": "error",
                "message": f"Connectivity test error: {str(e)}",
            }

        # Test system info retrieval
        try:
            system_name = await self.client.get(self.client.SYSTEM_OID_MAP["sysName"])
            test_results["tests"]["system_info"] = {
                "status": "pass" if system_name else "fail",
                "message": (
                    f"System name: {system_name}"
                    if system_name
                    else "Failed to retrieve system name"
                ),
                "system_name": system_name,
            }
        except Exception as e:
            test_results["tests"]["system_info"] = {
                "status": "error",
                "message": f"System info test error: {str(e)}",
            }

        # Test interface walk
        try:
            interface_results = await self.client.walk(
                self.client.INTERFACE_OID_MAP["ifDescr"]
            )
            interface_count = len(interface_results)
            test_results["tests"]["interface_discovery"] = {
                "status": "pass" if interface_count > 0 else "fail",
                "message": f"Discovered {interface_count} interfaces",
                "interface_count": interface_count,
            }
        except Exception as e:
            test_results["tests"]["interface_discovery"] = {
                "status": "error",
                "message": f"Interface discovery error: {str(e)}",
            }

        # Overall test result
        all_tests_passed = all(
            test["status"] == "pass" for test in test_results["tests"].values()
        )
        test_results["overall_status"] = "pass" if all_tests_passed else "fail"

        return test_results
