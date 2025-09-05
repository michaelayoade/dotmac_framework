"""
Guest network management for captive portal systems.

Provides comprehensive guest network configuration, access control,
VLAN management, and network isolation capabilities.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from netaddr import IPAddress, IPNetwork
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Constants
MAX_VLAN_ID = 4094


@dataclass
class NetworkRange:
    """Network range configuration."""

    network: str  # CIDR notation: 192.168.1.0/24
    gateway: str
    dns_servers: list[str]
    dhcp_start: str
    dhcp_end: str
    lease_time: int = 3600  # seconds


@dataclass
class VLANConfig:
    """VLAN configuration for guest network isolation."""

    vlan_id: int
    name: str
    description: str
    isolation_enabled: bool = True
    inter_vlan_routing: bool = False
    bandwidth_limit_mbps: int | None = None


@dataclass
class AccessPointConfig:
    """Access point configuration."""

    mac_address: str
    name: str
    location: str
    ssid: str
    security_type: str  # open, wep, wpa, wpa2, wpa3
    password: str | None = None
    hidden_ssid: bool = False
    max_clients: int = 50
    channel: int | None = None
    transmit_power: int = 100  # percentage


class GuestNetwork:
    """Represents a guest network configuration."""

    def __init__(
        self,
        network_id: str,
        name: str,
        network_range: NetworkRange,
        vlan_config: VLANConfig | None = None,
        **kwargs,
    ):
        self.network_id = network_id
        self.name = name
        self.network_range = network_range
        self.vlan_config = vlan_config

        # Network policies
        self.internet_access = kwargs.get("internet_access", True)
        self.lan_access = kwargs.get("lan_access", False)
        self.guest_to_guest = kwargs.get("guest_to_guest", False)

        # Bandwidth controls
        self.bandwidth_limit_down = kwargs.get("bandwidth_limit_down", 0)  # 0 = unlimited
        self.bandwidth_limit_up = kwargs.get("bandwidth_limit_up", 0)
        self.per_user_bandwidth = kwargs.get("per_user_bandwidth", True)

        # Access controls
        self.allowed_protocols = kwargs.get("allowed_protocols", ["http", "https", "dns"])
        self.blocked_ports = kwargs.get("blocked_ports", [22, 23, 135, 139, 445])
        self.content_filtering = kwargs.get("content_filtering", False)

        # Time-based access
        self.access_schedule = kwargs.get("access_schedule", {})  # Day/time restrictions

        # Security settings
        self.captive_portal_bypass = kwargs.get("captive_portal_bypass", [])  # MAC addresses
        self.device_isolation = kwargs.get("device_isolation", True)

        # Monitoring
        self.logging_enabled = kwargs.get("logging_enabled", True)
        self.traffic_analysis = kwargs.get("traffic_analysis", True)

        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def is_ip_in_range(self, ip_address: str) -> bool:
        """Check if IP address is in the network range."""
        try:
            network = IPNetwork(self.network_range.network)
            ip = IPAddress(ip_address)
            return ip in network
        except (ValueError, TypeError, AttributeError) as e:
            logger.exception("Error checking IP range", error=str(e), ip=ip_address)
            return False

    def get_available_ips(self, exclude_ips: list[str] | None = None) -> list[str]:
        """Get list of available IP addresses in the network range."""
        exclude_ips = exclude_ips or []
        try:
            network = IPNetwork(self.network_range.network)
            dhcp_start = IPAddress(self.network_range.dhcp_start)
            dhcp_end = IPAddress(self.network_range.dhcp_end)

            available_ips = []
            for ip in network:
                if dhcp_start <= ip <= dhcp_end and str(ip) not in exclude_ips:
                    available_ips.append(str(ip))

            return available_ips
        except (ValueError, TypeError, AttributeError) as e:
            logger.exception("Error getting available IPs", error=str(e))
            return []

    def validate_configuration(self) -> dict[str, Any]:
        """Validate network configuration."""
        issues = []
        warnings = []

        try:
            issues.extend(self._validate_network_range())
            issues.extend(self._validate_dns_servers())
            issues.extend(self._validate_vlan_config())
            warnings.extend(self._get_security_warnings())

        except (ValueError, TypeError, AttributeError) as e:
            issues.append(f"Configuration validation error: {e!s}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def _validate_network_range(self) -> list[str]:
        """Validate network range configuration."""
        issues = []

        network = IPNetwork(self.network_range.network)
        gateway = IPAddress(self.network_range.gateway)
        dhcp_start = IPAddress(self.network_range.dhcp_start)
        dhcp_end = IPAddress(self.network_range.dhcp_end)

        # Check if gateway is in network
        if gateway not in network:
            issues.append("Gateway IP is not in network range")

        # Check DHCP range
        if dhcp_start not in network or dhcp_end not in network:
            issues.append("DHCP range is not within network range")

        if dhcp_start >= dhcp_end:
            issues.append("DHCP start IP must be less than end IP")

        return issues

    def _validate_dns_servers(self) -> list[str]:
        """Validate DNS server configuration."""
        issues = []

        for dns in self.network_range.dns_servers:
            try:
                IPAddress(dns)
            except (ValueError, TypeError):
                issues.append(f"Invalid DNS server IP: {dns}")

        return issues

    def _validate_vlan_config(self) -> list[str]:
        """Validate VLAN configuration."""
        issues = []

        if self.vlan_config and (self.vlan_config.vlan_id < 1 or self.vlan_config.vlan_id > MAX_VLAN_ID):
            issues.append("VLAN ID must be between 1 and 4094")

        return issues

    def _get_security_warnings(self) -> list[str]:
        """Get security-related warnings."""
        warnings = []

        if self.lan_access:
            warnings.append("LAN access is enabled - may pose security risk")

        if self.guest_to_guest:
            warnings.append("Guest-to-guest communication is enabled")

        if not self.content_filtering:
            warnings.append("Content filtering is disabled")

        return warnings

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "network_id": self.network_id,
            "name": self.name,
            "network_range": {
                "network": self.network_range.network,
                "gateway": self.network_range.gateway,
                "dns_servers": self.network_range.dns_servers,
                "dhcp_start": self.network_range.dhcp_start,
                "dhcp_end": self.network_range.dhcp_end,
                "lease_time": self.network_range.lease_time,
            },
            "vlan_config": (
                {
                    "vlan_id": self.vlan_config.vlan_id,
                    "name": self.vlan_config.name,
                    "description": self.vlan_config.description,
                    "isolation_enabled": self.vlan_config.isolation_enabled,
                    "inter_vlan_routing": self.vlan_config.inter_vlan_routing,
                    "bandwidth_limit_mbps": self.vlan_config.bandwidth_limit_mbps,
                }
                if self.vlan_config
                else None
            ),
            "policies": {
                "internet_access": self.internet_access,
                "lan_access": self.lan_access,
                "guest_to_guest": self.guest_to_guest,
                "device_isolation": self.device_isolation,
            },
            "bandwidth": {
                "limit_down": self.bandwidth_limit_down,
                "limit_up": self.bandwidth_limit_up,
                "per_user": self.per_user_bandwidth,
            },
            "security": {
                "allowed_protocols": self.allowed_protocols,
                "blocked_ports": self.blocked_ports,
                "content_filtering": self.content_filtering,
                "captive_portal_bypass": self.captive_portal_bypass,
            },
            "monitoring": {
                "logging_enabled": self.logging_enabled,
                "traffic_analysis": self.traffic_analysis,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class NetworkDeviceManager:
    """Manages network devices and their access control."""

    def __init__(self):
        self._devices: dict[str, dict[str, Any]] = {}  # MAC -> device info
        self._device_sessions: dict[str, str] = {}  # MAC -> session_id
        self._bandwidth_usage: dict[str, dict[str, int]] = {}  # MAC -> usage stats

    def register_device(
        self,
        mac_address: str,
        ip_address: str,
        device_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new device on the network."""
        device = {
            "mac_address": mac_address.lower(),
            "ip_address": ip_address,
            "hostname": (device_info.get("hostname", "unknown") if device_info else "unknown"),
            "vendor": (device_info.get("vendor", "unknown") if device_info else "unknown"),
            "device_type": (device_info.get("device_type", "unknown") if device_info else "unknown"),
            "first_seen": datetime.now(UTC),
            "last_seen": datetime.now(UTC),
            "status": "online",
            "bytes_downloaded": 0,
            "bytes_uploaded": 0,
            "session_count": 0,
        }

        self._devices[mac_address.lower()] = device

        logger.info(
            "Device registered",
            mac_address=mac_address,
            ip_address=ip_address,
            hostname=device.get("hostname"),
        )

        return device

    def update_device_activity(self, mac_address: str, bytes_down: int = 0, bytes_up: int = 0):
        """Update device network activity."""
        mac_lower = mac_address.lower()
        if mac_lower in self._devices:
            device = self._devices[mac_lower]
            device["last_seen"] = datetime.now(UTC)
            device["bytes_downloaded"] += bytes_down
            device["bytes_uploaded"] += bytes_up

            # Track bandwidth usage
            if mac_lower not in self._bandwidth_usage:
                self._bandwidth_usage[mac_lower] = {"downloads": [], "uploads": []}

            now = datetime.now(UTC)
            self._bandwidth_usage[mac_lower]["downloads"].append((now, bytes_down))
            self._bandwidth_usage[mac_lower]["uploads"].append((now, bytes_up))

    def get_device_info(self, mac_address: str) -> dict[str, Any] | None:
        """Get device information by MAC address."""
        return self._devices.get(mac_address.lower())

    def get_device_bandwidth_usage(
        self,
        mac_address: str,
        time_window_minutes: int = 60,
    ) -> dict[str, float]:
        """Get device bandwidth usage in specified time window."""
        mac_lower = mac_address.lower()
        if mac_lower not in self._bandwidth_usage:
            return {"download_mbps": 0.0, "upload_mbps": 0.0}

        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_window_minutes)
        usage = self._bandwidth_usage[mac_lower]

        # Calculate usage in time window
        download_bytes = sum(bytes_count for timestamp, bytes_count in usage["downloads"] if timestamp >= cutoff_time)
        upload_bytes = sum(bytes_count for timestamp, bytes_count in usage["uploads"] if timestamp >= cutoff_time)

        # Convert to Mbps
        time_window_seconds = time_window_minutes * 60
        download_mbps = (download_bytes * 8) / (time_window_seconds * 1_000_000)
        upload_mbps = (upload_bytes * 8) / (time_window_seconds * 1_000_000)

        return {
            "download_mbps": download_mbps,
            "upload_mbps": upload_mbps,
            "total_bytes": download_bytes + upload_bytes,
        }

    def list_online_devices(self, inactive_threshold_minutes: int = 5) -> list[dict[str, Any]]:
        """List devices that are currently online."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=inactive_threshold_minutes)

        online_devices = []
        for device in self._devices.values():
            if device["last_seen"] >= cutoff_time:
                device["status"] = "online"
                online_devices.append(device)
            else:
                device["status"] = "offline"

        return online_devices

    def associate_device_session(self, mac_address: str, session_id: str):
        """Associate device with a captive portal session."""
        self._device_sessions[mac_address.lower()] = session_id

        if mac_address.lower() in self._devices:
            self._devices[mac_address.lower()]["session_count"] += 1

    def get_device_session(self, mac_address: str) -> str | None:
        """Get associated session ID for a device."""
        return self._device_sessions.get(mac_address.lower())


class GuestNetworkManager:
    """Manages guest networks and their configurations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._networks: dict[str, GuestNetwork] = {}
        self._device_manager = NetworkDeviceManager()
        self._access_points: dict[str, AccessPointConfig] = {}

    async def create_guest_network(
        self,
        tenant_id: str,
        name: str,
        network_cidr: str,
        gateway_ip: str,
        dns_servers: list[str] | None = None,
        vlan_id: int | None = None,
        **kwargs,
    ) -> GuestNetwork:
        """Create a new guest network configuration."""
        network_id = str(uuid.uuid4())

        # Set up network range
        network_range = NetworkRange(
            network=network_cidr,
            gateway=gateway_ip,
            dns_servers=dns_servers or ["8.8.8.8", "8.8.4.4"],
            dhcp_start=kwargs.get("dhcp_start", self._calculate_dhcp_start(network_cidr)),
            dhcp_end=kwargs.get("dhcp_end", self._calculate_dhcp_end(network_cidr)),
            lease_time=kwargs.get("lease_time", 3600),
        )

        # Set up VLAN if specified
        vlan_config = None
        if vlan_id:
            vlan_config = VLANConfig(
                vlan_id=vlan_id,
                name=kwargs.get("vlan_name", f"guest_vlan_{vlan_id}"),
                description=kwargs.get("vlan_description", f"Guest network VLAN {vlan_id}"),
                isolation_enabled=kwargs.get("vlan_isolation", True),
                inter_vlan_routing=kwargs.get("inter_vlan_routing", False),
                bandwidth_limit_mbps=kwargs.get("vlan_bandwidth_limit"),
            )

        # Create guest network
        guest_network = GuestNetwork(
            network_id=network_id,
            name=name,
            network_range=network_range,
            vlan_config=vlan_config,
            **kwargs,
        )

        # Validate configuration
        validation = guest_network.validate_configuration()
        if not validation["valid"]:
            msg = f"Invalid network configuration: {validation['issues']}"
            raise ValueError(msg)

        # Store network
        self._networks[network_id] = guest_network

        logger.info(
            "Guest network created",
            network_id=network_id,
            name=name,
            network_cidr=network_cidr,
            vlan_id=vlan_id,
            tenant_id=tenant_id,
        )

        return guest_network

    def get_guest_network(self, network_id: str) -> GuestNetwork | None:
        """Get guest network by ID."""
        return self._networks.get(network_id)

    def list_guest_networks(self) -> list[GuestNetwork]:
        """List all configured guest networks."""
        return list(self._networks.values())

    async def update_guest_network(
        self,
        network_id: str,
        **updates,
    ) -> GuestNetwork | None:
        """Update guest network configuration."""
        if network_id not in self._networks:
            return None

        network = self._networks[network_id]

        # Update network range if provided
        if any(key in updates for key in ["network_cidr", "gateway_ip", "dns_servers"]):
            if "network_cidr" in updates:
                network.network_range.network = updates["network_cidr"]
            if "gateway_ip" in updates:
                network.network_range.gateway = updates["gateway_ip"]
            if "dns_servers" in updates:
                network.network_range.dns_servers = updates["dns_servers"]

        # Update VLAN configuration
        if network.vlan_config and "vlan_id" in updates:
            network.vlan_config.vlan_id = updates["vlan_id"]

        # Update other properties
        for key, value in updates.items():
            if hasattr(network, key):
                setattr(network, key, value)

        network.updated_at = datetime.now(UTC)

        # Validate updated configuration
        validation = network.validate_configuration()
        if not validation["valid"]:
            msg = f"Invalid updated configuration: {validation['issues']}"
            raise ValueError(msg)

        logger.info("Guest network updated", network_id=network_id, updates=list(updates.keys()))

        return network

    def delete_guest_network(self, network_id: str) -> bool:
        """Delete guest network configuration."""
        if network_id not in self._networks:
            return False

        del self._networks[network_id]

        logger.info("Guest network deleted", network_id=network_id)
        return True

    async def assign_ip_address(
        self,
        network_id: str,
        mac_address: str,
        preferred_ip: str | None = None,
    ) -> str | None:
        """Assign IP address to device on guest network."""
        network = self.get_guest_network(network_id)
        if not network:
            return None

        # Get currently assigned IPs
        assigned_ips = await self._get_assigned_ips(network_id)

        # Try preferred IP first
        if preferred_ip and preferred_ip not in assigned_ips:
            if network.is_ip_in_range(preferred_ip):
                self._device_manager.register_device(mac_address, preferred_ip)
                return preferred_ip

        # Get first available IP
        available_ips = network.get_available_ips(exclude_ips=assigned_ips)
        if available_ips:
            assigned_ip = available_ips[0]
            self._device_manager.register_device(mac_address, assigned_ip)
            return assigned_ip

        logger.warning("No available IP addresses", network_id=network_id, mac_address=mac_address)
        return None

    async def apply_bandwidth_policies(
        self,
        network_id: str,
        device_mac: str,
        download_limit_kbps: int | None = None,
        upload_limit_kbps: int | None = None,
    ) -> bool:
        """Apply bandwidth policies to device."""
        network = self.get_guest_network(network_id)
        if not network:
            return False

        # Use network defaults if not specified
        if download_limit_kbps is None:
            download_limit_kbps = network.bandwidth_limit_down
        if upload_limit_kbps is None:
            upload_limit_kbps = network.bandwidth_limit_up

        # In a real implementation, this would configure network equipment
        # For now, we log the policy application
        logger.info(
            "Bandwidth policy applied",
            network_id=network_id,
            device_mac=device_mac,
            download_limit=download_limit_kbps,
            upload_limit=upload_limit_kbps,
        )

        return True

    async def apply_firewall_rules(
        self,
        network_id: str,
        device_mac: str | None = None,
    ) -> bool:
        """Apply firewall rules for network or specific device."""
        network = self.get_guest_network(network_id)
        if not network:
            return False

        # Build firewall rules based on network policy
        rules = []

        # Internet access
        if network.internet_access:
            rules.append("ALLOW internet access")
        else:
            rules.append("DENY internet access")

        # LAN access
        if not network.lan_access:
            rules.append("DENY LAN access")

        # Guest-to-guest communication
        if not network.guest_to_guest:
            rules.append("DENY guest-to-guest communication")

        # Block specific ports
        for port in network.blocked_ports:
            rules.append(f"DENY port {port}")

        # Device isolation
        if network.device_isolation:
            rules.append("ENABLE device isolation")

        # In a real implementation, configure network equipment
        logger.info(
            "Firewall rules applied",
            network_id=network_id,
            device_mac=device_mac,
            rules=rules,
        )

        return True

    def configure_access_point(
        self,
        ap_mac: str,
        ap_config: AccessPointConfig,
    ) -> bool:
        """Configure access point for guest network."""
        self._access_points[ap_mac.lower()] = ap_config

        logger.info(
            "Access point configured",
            ap_mac=ap_mac,
            ap_name=ap_config.name,
            ssid=ap_config.ssid,
            max_clients=ap_config.max_clients,
        )

        return True

    def get_network_statistics(self, network_id: str) -> dict[str, Any]:
        """Get comprehensive network statistics."""
        network = self.get_guest_network(network_id)
        if not network:
            return {}

        online_devices = self._device_manager.list_online_devices()
        network_devices = [device for device in online_devices if network.is_ip_in_range(device["ip_address"])]

        total_bandwidth_down = sum(
            self._device_manager.get_device_bandwidth_usage(
                device["mac_address"],
            )["download_mbps"]
            for device in network_devices
        )

        total_bandwidth_up = sum(
            self._device_manager.get_device_bandwidth_usage(
                device["mac_address"],
            )["upload_mbps"]
            for device in network_devices
        )

        return {
            "network_id": network_id,
            "network_name": network.name,
            "total_devices": len(network_devices),
            "online_devices": len(network_devices),
            "bandwidth_usage": {
                "download_mbps": total_bandwidth_down,
                "upload_mbps": total_bandwidth_up,
            },
            "ip_utilization": {
                "available_ips": len(network.get_available_ips()),
                "assigned_ips": len(network_devices),
            },
            "vlan_id": network.vlan_config.vlan_id if network.vlan_config else None,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def _calculate_dhcp_start(self, network_cidr: str) -> str:
        """Calculate DHCP start IP from network CIDR."""
        try:
            network = IPNetwork(network_cidr)
            # Start from the 10th IP in the range
            return str(network[10])
        except (ValueError, IndexError, TypeError):
            return "192.168.1.10"

    def _calculate_dhcp_end(self, network_cidr: str) -> str:
        """Calculate DHCP end IP from network CIDR."""
        try:
            network = IPNetwork(network_cidr)
            # End at the 250th IP or network end - 5, whichever is smaller
            end_index = min(250, len(network) - 5)
            return str(network[end_index])
        except (ValueError, IndexError, TypeError):
            return "192.168.1.250"

    async def _get_assigned_ips(self, network_id: str) -> list[str]:
        """Get list of currently assigned IP addresses."""
        # In a real implementation, query the database or DHCP server
        online_devices = self._device_manager.list_online_devices()
        return [device["ip_address"] for device in online_devices]
