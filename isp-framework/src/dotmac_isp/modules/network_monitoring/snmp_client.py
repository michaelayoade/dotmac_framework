"""SNMP client for network device monitoring."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from ipaddress import IPv4Address, IPv6Address

try:
    from pysnmp.hlapi import (
        getCmd,
        setCmd,
        nextCmd,
        bulkCmd,
        CommunityData,
        UdpTransportTarget,
        ContextData,
        ObjectType,
        ObjectIdentity,
        UsmUserData,
        usmHMACMD5AuthProtocol,
        usmHMACSHAAuthProtocol,
        usmDESPrivProtocol,
        usmAesCfb128Protocol,
        SnmpEngine,
        Udp6TransportTarget,
    , timezone)
    from pysnmp.proto.rfc1902 import Counter32, Counter64, Gauge32, Integer, OctetString
    from pysnmp.error import PySnmpError

    PYSNMP_AVAILABLE = True
except ImportError:
    PYSNMP_AVAILABLE = False


logger = logging.getLogger(__name__)


class SnmpError(Exception):
    """Base exception for SNMP operations."""

    def __init__(self, message: str, error_code: str = None, device_ip: str = None):
        """  Init   operation."""
        super().__init__(message)
        self.error_code = error_code
        self.device_ip = device_ip


class SnmpTimeoutError(SnmpError):
    """Exception raised when SNMP operation times out."""

    pass


class SnmpAuthError(SnmpError):
    """Exception raised when SNMP authentication fails."""

    pass


class SnmpClient:
    """Asynchronous SNMP client for network device monitoring."""

    def __init__(self, timeout: int = 5, retries: int = 3, max_concurrent: int = 50):
        """Initialize SNMP client.

        Args:
            timeout: SNMP request timeout in seconds
            retries: Number of retry attempts
            max_concurrent: Maximum concurrent SNMP requests
        """
        if not PYSNMP_AVAILABLE:
            raise ImportError("pysnmp library is required for SNMP monitoring")

        self.timeout = timeout
        self.retries = retries
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.snmp_engine = SnmpEngine()

        # Common OIDs for monitoring
        self.common_oids = {
            # System information
            "sysDescr": "1.3.6.1.2.1.1.1.0",
            "sysObjectID": "1.3.6.1.2.1.1.2.0",
            "sysUpTime": "1.3.6.1.2.1.1.3.0",
            "sysContact": "1.3.6.1.2.1.1.4.0",
            "sysName": "1.3.6.1.2.1.1.5.0",
            "sysLocation": "1.3.6.1.2.1.1.6.0",
            # Interface information
            "ifNumber": "1.3.6.1.2.1.2.1.0",
            "ifIndex": "1.3.6.1.2.1.2.2.1.1",
            "ifDescr": "1.3.6.1.2.1.2.2.1.2",
            "ifType": "1.3.6.1.2.1.2.2.1.3",
            "ifMtu": "1.3.6.1.2.1.2.2.1.4",
            "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
            "ifPhysAddress": "1.3.6.1.2.1.2.2.1.6",
            "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",
            "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
            "ifLastChange": "1.3.6.1.2.1.2.2.1.9",
            "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
            "ifInUcastPkts": "1.3.6.1.2.1.2.2.1.11",
            "ifInNUcastPkts": "1.3.6.1.2.1.2.2.1.12",
            "ifInDiscards": "1.3.6.1.2.1.2.2.1.13",
            "ifInErrors": "1.3.6.1.2.1.2.2.1.14",
            "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
            "ifOutUcastPkts": "1.3.6.1.2.1.2.2.1.17",
            "ifOutNUcastPkts": "1.3.6.1.2.1.2.2.1.18",
            "ifOutDiscards": "1.3.6.1.2.1.2.2.1.19",
            "ifOutErrors": "1.3.6.1.2.1.2.2.1.20",
            # High-capacity interface counters (64-bit)
            "ifHCInOctets": "1.3.6.1.2.1.31.1.1.1.6",
            "ifHCOutOctets": "1.3.6.1.2.1.31.1.1.1.10",
            "ifHighSpeed": "1.3.6.1.2.1.31.1.1.1.15",
            # Host resources (if supported)
            "hrSystemUptime": "1.3.6.1.2.1.25.1.1.0",
            "hrSystemUsers": "1.3.6.1.2.1.25.1.5.0",
            "hrSystemProcesses": "1.3.6.1.2.1.25.1.6.0",
            "hrMemorySize": "1.3.6.1.2.1.25.2.2.0",
            # CPU and memory utilization (vendor-specific, these are Cisco examples)
            "cpmCPUTotal5min": "1.3.6.1.4.1.9.9.109.1.1.1.1.8",
            "ciscoMemoryPoolUsed": "1.3.6.1.4.1.9.9.48.1.1.1.5",
            "ciscoMemoryPoolFree": "1.3.6.1.4.1.9.9.48.1.1.1.6",
        }

    async def get(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        oids: Union[str, List[str]],
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform SNMP GET request.

        Args:
            target: Target device IP address
            oids: Single OID string or list of OID strings
            community: SNMP community string (for v1/v2c)
            version: SNMP version ("v1", "v2c", "v3")
            port: SNMP port number
            auth_data: SNMPv3 authentication data

        Returns:
            Dictionary mapping OIDs to their values
        """
        async with self._semaphore:
            return await self._perform_get_request(
                target, oids, community, version, port, auth_data
            )

    async def walk(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        oid: str,
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform SNMP WALK request.

        Args:
            target: Target device IP address
            oid: Root OID to walk
            community: SNMP community string (for v1/v2c)
            version: SNMP version ("v1", "v2c", "v3")
            port: SNMP port number
            auth_data: SNMPv3 authentication data

        Returns:
            Dictionary mapping OIDs to their values
        """
        async with self._semaphore:
            return await self._perform_walk_request(
                target, oid, community, version, port, auth_data
            )

    async def bulk_get(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        oids: List[str],
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        non_repeaters: int = 0,
        max_repetitions: int = 25,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform SNMP GETBULK request (v2c/v3 only).

        Args:
            target: Target device IP address
            oids: List of OID strings
            community: SNMP community string (for v2c)
            version: SNMP version ("v2c", "v3")
            port: SNMP port number
            non_repeaters: Number of non-repeater variables
            max_repetitions: Maximum repetitions
            auth_data: SNMPv3 authentication data

        Returns:
            Dictionary mapping OIDs to their values
        """
        if version == "v1":
            raise SnmpError("GETBULK is not supported in SNMPv1")

        async with self._semaphore:
            return await self._perform_bulk_request(
                target,
                oids,
                community,
                version,
                port,
                non_repeaters,
                max_repetitions,
                auth_data,
            )

    async def get_system_info(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get basic system information from device.

        Args:
            target: Target device IP address
            community: SNMP community string
            version: SNMP version
            port: SNMP port number
            auth_data: SNMPv3 authentication data

        Returns:
            Dictionary with system information
        """
        system_oids = [
            self.common_oids["sysDescr"],
            self.common_oids["sysObjectID"],
            self.common_oids["sysUpTime"],
            self.common_oids["sysContact"],
            self.common_oids["sysName"],
            self.common_oids["sysLocation"],
        ]

        result = await self.get(
            target, system_oids, community, version, port, auth_data
        )

        return {
            "description": result.get(self.common_oids["sysDescr"]),
            "object_id": result.get(self.common_oids["sysObjectID"]),
            "uptime": result.get(self.common_oids["sysUpTime"]),
            "contact": result.get(self.common_oids["sysContact"]),
            "name": result.get(self.common_oids["sysName"]),
            "location": result.get(self.common_oids["sysLocation"]),
        }

    async def get_interface_list(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of interfaces from device.

        Args:
            target: Target device IP address
            community: SNMP community string
            version: SNMP version
            port: SNMP port number
            auth_data: SNMPv3 authentication data

        Returns:
            List of interface information dictionaries
        """
        # First get the number of interfaces
        if_number_result = await self.get(
            target, self.common_oids["ifNumber"], community, version, port, auth_data
        )

        if_count = if_number_result.get(self.common_oids["ifNumber"], 0)

        if if_count == 0:
            return []

        # Walk interface table for basic information
        interface_oids = [
            self.common_oids["ifIndex"],
            self.common_oids["ifDescr"],
            self.common_oids["ifType"],
            self.common_oids["ifSpeed"],
            self.common_oids["ifPhysAddress"],
            self.common_oids["ifAdminStatus"],
            self.common_oids["ifOperStatus"],
        ]

        interfaces = []

        for oid in interface_oids:
            base_oid = oid.rsplit(".", 1)[0]  # Remove the trailing index
            walk_result = await self.walk(
                target, base_oid, community, version, port, auth_data
            )

            # Process results by interface index
            for full_oid, value in walk_result.items():
                if_index = int(full_oid.split(".")[-1])

                # Find or create interface entry
                interface = next(
                    (i for i in interfaces if i["index"] == if_index), None
                )
                if not interface:
                    interface = {"index": if_index}
                    interfaces.append(interface)

                # Map OID to field name
                if base_oid in oid:
                    if "ifDescr" in oid:
                        interface["description"] = value
                    elif "ifType" in oid:
                        interface["type"] = value
                    elif "ifSpeed" in oid:
                        interface["speed"] = value
                    elif "ifPhysAddress" in oid:
                        interface["mac_address"] = value
                    elif "ifAdminStatus" in oid:
                        interface["admin_status"] = value
                    elif "ifOperStatus" in oid:
                        interface["operational_status"] = value

        return sorted(interfaces, key=lambda x: x["index"])

    async def get_interface_stats(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        interface_index: int,
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get interface statistics for specific interface.

        Args:
            target: Target device IP address
            interface_index: Interface index number
            community: SNMP community string
            version: SNMP version
            port: SNMP port number
            auth_data: SNMPv3 authentication data

        Returns:
            Dictionary with interface statistics
        """
        stats_oids = [
            f"{self.common_oids['ifInOctets']}.{interface_index}",
            f"{self.common_oids['ifInUcastPkts']}.{interface_index}",
            f"{self.common_oids['ifInDiscards']}.{interface_index}",
            f"{self.common_oids['ifInErrors']}.{interface_index}",
            f"{self.common_oids['ifOutOctets']}.{interface_index}",
            f"{self.common_oids['ifOutUcastPkts']}.{interface_index}",
            f"{self.common_oids['ifOutDiscards']}.{interface_index}",
            f"{self.common_oids['ifOutErrors']}.{interface_index}",
            # Try to get 64-bit counters if available
            f"{self.common_oids['ifHCInOctets']}.{interface_index}",
            f"{self.common_oids['ifHCOutOctets']}.{interface_index}",
            f"{self.common_oids['ifHighSpeed']}.{interface_index}",
        ]

        result = await self.get(target, stats_oids, community, version, port, auth_data)

        return {
            "interface_index": interface_index,
            "in_octets": result.get(
                f"{self.common_oids['ifInOctets']}.{interface_index}"
            ),
            "in_packets": result.get(
                f"{self.common_oids['ifInUcastPkts']}.{interface_index}"
            ),
            "in_discards": result.get(
                f"{self.common_oids['ifInDiscards']}.{interface_index}"
            ),
            "in_errors": result.get(
                f"{self.common_oids['ifInErrors']}.{interface_index}"
            ),
            "out_octets": result.get(
                f"{self.common_oids['ifOutOctets']}.{interface_index}"
            ),
            "out_packets": result.get(
                f"{self.common_oids['ifOutUcastPkts']}.{interface_index}"
            ),
            "out_discards": result.get(
                f"{self.common_oids['ifOutDiscards']}.{interface_index}"
            ),
            "out_errors": result.get(
                f"{self.common_oids['ifOutErrors']}.{interface_index}"
            ),
            "hc_in_octets": result.get(
                f"{self.common_oids['ifHCInOctets']}.{interface_index}"
            ),
            "hc_out_octets": result.get(
                f"{self.common_oids['ifHCOutOctets']}.{interface_index}"
            ),
            "high_speed": result.get(
                f"{self.common_oids['ifHighSpeed']}.{interface_index}"
            ),
            "timestamp": datetime.now(timezone.utc),
        }

    async def ping_device(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Test device availability via SNMP.

        Args:
            target: Target device IP address
            community: SNMP community string
            version: SNMP version
            port: SNMP port number
            auth_data: SNMPv3 authentication data

        Returns:
            True if device responds to SNMP, False otherwise
        """
        try:
            result = await self.get(
                target,
                self.common_oids["sysUpTime"],
                community,
                version,
                port,
                auth_data,
            )
            return self.common_oids["sysUpTime"] in result
        except SnmpError:
            return False

    # Private helper methods

    async def _perform_get_request(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        oids: Union[str, List[str]],
        community: str,
        version: str,
        port: int,
        auth_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Perform the actual SNMP GET request."""
        if isinstance(oids, str):
            oids = [oids]

        target_str = str(target)

        # Create authentication data
        if version in ["v1", "v2c"]:
            auth_data_obj = CommunityData(community)
        elif version == "v3":
            if not auth_data:
                raise SnmpError("Authentication data required for SNMPv3")
            auth_data_obj = self._create_v3_auth_data(auth_data)
        else:
            raise SnmpError(f"Unsupported SNMP version: {version}")

        # Create transport target
        if ":" in target_str and not target_str.startswith("["):
            # IPv6 address
            transport_target = Udp6TransportTarget((target_str, port))
        else:
            # IPv4 address
            transport_target = UdpTransportTarget((target_str, port))

        # Create object types for all OIDs
        object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]

        try:
            # Perform SNMP GET
            loop = asyncio.get_event_loop()
            error_indication, error_status, error_index, var_binds = (
                await loop.run_in_executor(
                    None,
                    lambda: next(
                        getCmd(
                            self.snmp_engine,
                            auth_data_obj,
                            transport_target,
                            ContextData(),
                            *object_types,
                            lexicographicMode=False,
                            ignoreNonIncreasingOid=False,
                            maxRows=1,
                        )
                    ),
                )
            )

            if error_indication:
                raise SnmpError(f"SNMP error: {error_indication}", device_ip=target_str)

            if error_status:
                raise SnmpError(
                    f"SNMP error: {error_status.prettyPrint()} at {error_index}",
                    device_ip=target_str,
                )

            # Parse results
            result = {}
            for var_bind in var_binds:
                oid, value = var_bind
                result[str(oid)] = self._convert_snmp_value(value)

            return result

        except PySnmpError as e:
            logger.error(f"SNMP error for {target_str}: {e}")
            raise SnmpError(f"SNMP operation failed: {e}", device_ip=target_str)
        except Exception as e:
            logger.error(f"Unexpected error for {target_str}: {e}")
            raise SnmpError(f"Unexpected error: {e}", device_ip=target_str)

    async def _perform_walk_request(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        oid: str,
        community: str,
        version: str,
        port: int,
        auth_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Perform the actual SNMP WALK request."""
        target_str = str(target)

        # Create authentication data
        if version in ["v1", "v2c"]:
            auth_data_obj = CommunityData(community)
        elif version == "v3":
            if not auth_data:
                raise SnmpError("Authentication data required for SNMPv3")
            auth_data_obj = self._create_v3_auth_data(auth_data)
        else:
            raise SnmpError(f"Unsupported SNMP version: {version}")

        # Create transport target
        if ":" in target_str and not target_str.startswith("["):
            transport_target = Udp6TransportTarget((target_str, port)
        else:
            transport_target = UdpTransportTarget((target_str, port)

        try:
            # Perform SNMP WALK
            result = {}
            loop = asyncio.get_event_loop()

            for (
                error_indication,
                error_status,
                error_index,
                var_binds,
            ) in await loop.run_in_executor(
                None,
                lambda: nextCmd(
                    self.snmp_engine,
                    auth_data_obj,
                    transport_target,
                    ContextData(),
                    ObjectType(ObjectIdentity(oid),
                    lexicographicMode=False,
                    ignoreNonIncreasingOid=False,
                    maxRows=1000,  # Limit to prevent runaway walks
                ),
            ):
                if error_indication:
                    break

                if error_status:
                    break

                for var_bind in var_binds:
                    oid_obj, value = var_bind
                    result[str(oid_obj)] = self._convert_snmp_value(value)

            return result

        except PySnmpError as e:
            logger.error(f"SNMP walk error for {target_str}: {e}")
            raise SnmpError(f"SNMP walk failed: {e}", device_ip=target_str)
        except Exception as e:
            logger.error(f"Unexpected error during SNMP walk for {target_str}: {e}")
            raise SnmpError(f"Unexpected error: {e}", device_ip=target_str)

    async def _perform_bulk_request(
        self,
        target: Union[str, IPv4Address, IPv6Address],
        oids: List[str],
        community: str,
        version: str,
        port: int,
        non_repeaters: int,
        max_repetitions: int,
        auth_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Perform the actual SNMP GETBULK request."""
        target_str = str(target)

        # Create authentication data
        if version == "v2c":
            auth_data_obj = CommunityData(community)
        elif version == "v3":
            if not auth_data:
                raise SnmpError("Authentication data required for SNMPv3")
            auth_data_obj = self._create_v3_auth_data(auth_data)
        else:
            raise SnmpError(f"GETBULK not supported for SNMP version: {version}")

        # Create transport target
        if ":" in target_str and not target_str.startswith("["):
            transport_target = Udp6TransportTarget((target_str, port)
        else:
            transport_target = UdpTransportTarget((target_str, port)

        # Create object types
        object_types = [ObjectType(ObjectIdentity(oid) for oid in oids]

        try:
            # Perform SNMP GETBULK
            result = {}
            loop = asyncio.get_event_loop()

            error_indication, error_status, error_index, var_binds = (
                await loop.run_in_executor(
                    None,
                    lambda: next(
                        bulkCmd(
                            self.snmp_engine,
                            auth_data_obj,
                            transport_target,
                            ContextData(),
                            non_repeaters,
                            max_repetitions,
                            *object_types,
                            lexicographicMode=False,
                            ignoreNonIncreasingOid=False,
                        )
                    ),
                )
            )

            if error_indication:
                raise SnmpError(f"SNMP error: {error_indication}", device_ip=target_str)

            if error_status:
                raise SnmpError(
                    f"SNMP error: {error_status.prettyPrint()} at {error_index}",
                    device_ip=target_str,
                )

            # Parse results
            for var_bind in var_binds:
                oid_obj, value = var_bind
                result[str(oid_obj)] = self._convert_snmp_value(value)

            return result

        except PySnmpError as e:
            logger.error(f"SNMP bulk error for {target_str}: {e}")
            raise SnmpError(f"SNMP bulk operation failed: {e}", device_ip=target_str)
        except Exception as e:
            logger.error(f"Unexpected error during SNMP bulk for {target_str}: {e}")
            raise SnmpError(f"Unexpected error: {e}", device_ip=target_str)

    def _create_v3_auth_data(self, auth_data: Dict[str, Any]) -> UsmUserData:
        """Create SNMPv3 authentication data."""
        username = auth_data.get("username")
        if not username:
            raise SnmpError("Username required for SNMPv3")

        auth_key = auth_data.get("auth_key")
        priv_key = auth_data.get("priv_key")
        auth_protocol = auth_data.get("auth_protocol", "MD5")
        priv_protocol = auth_data.get("priv_protocol", "DES")

        # Map protocol strings to protocol objects
        auth_protocol_map = {
            "MD5": usmHMACMD5AuthProtocol,
            "SHA": usmHMACSHAAuthProtocol,
        }

        priv_protocol_map = {
            "DES": usmDESPrivProtocol,
            "AES": usmAesCfb128Protocol,
            "AES128": usmAesCfb128Protocol,
        }

        auth_proto = auth_protocol_map.get(auth_protocol.upper() if auth_key else None
        priv_proto = priv_protocol_map.get(priv_protocol.upper() if priv_key else None

        return UsmUserData(
            userName=username,
            authKey=auth_key,
            privKey=priv_key,
            authProtocol=auth_proto,
            privProtocol=priv_proto,
        )

    def _convert_snmp_value(self, value: Any) -> Any:
        """Convert SNMP value to Python type."""
        if isinstance(value, (Counter32, Counter64, Gauge32, Integer):
            return int(value)
        elif isinstance(value, OctetString):
            # Try to decode as string, fall back to bytes representation
            try:
                return str(value)
            except UnicodeDecodeError:
                return bytes(value).hex()
        else:
            return str(value)
