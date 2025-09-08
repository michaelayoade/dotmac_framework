"""
Unified Device Service.

High-level service that orchestrates all device management operations.
"""

from typing import Any, Optional

from sqlalchemy.orm import Session

from ..core.device_inventory import DeviceInventoryService
from ..core.device_monitoring import DeviceMonitoringService
from ..core.mac_registry import MacRegistryService
from ..core.network_topology import NetworkTopologyService
from ..exceptions import DeviceManagementError
from ..utils.snmp_client import SNMPClient, SNMPCollector, SNMPConfig
from ..utils.topology_analyzer import TopologyAnalyzer
from ..workflows.lifecycle_manager import DeviceLifecycleManager


class DeviceService:
    """Unified service for all device management operations."""

    def __init__(self, session: Session, tenant_id: str):
        """Initialize device service with all managers."""
        self.session = session
        self.tenant_id = tenant_id

        # Initialize core services
        self.inventory = DeviceInventoryService(session, tenant_id)
        self.monitoring = DeviceMonitoringService(session, tenant_id)
        self.mac_registry = MacRegistryService(session, tenant_id)
        self.topology = NetworkTopologyService(session, tenant_id)
        self.lifecycle = DeviceLifecycleManager(session, tenant_id)

        # Initialize utilities
        self.topology_analyzer = TopologyAnalyzer()

    # Device Inventory Operations
    async def create_device(self, **kwargs) -> dict[str, Any]:
        """Create new device."""
        device = await self.inventory.manager.create_device(**kwargs)
        return {
            "device_id": device.device_id,
            "hostname": device.hostname,
            "status": device.status,
            "created_at": device.created_at.isoformat(),
        }

    async def get_device(self, device_id: str) -> Optional[dict[str, Any]]:
        """Get device information."""
        device = await self.inventory.manager.get_device(device_id)
        if not device:
            return None

        return {
            "device_id": device.device_id,
            "hostname": device.hostname,
            "device_type": device.device_type,
            "vendor": device.vendor,
            "model": device.model,
            "status": device.status,
            "site_id": device.site_id,
            "management_ip": device.management_ip,
            "created_at": device.created_at.isoformat(),
            "updated_at": device.updated_at.isoformat(),
        }

    async def update_device(self, device_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Update device information."""
        device = await self.inventory.manager.update_device(device_id, updates)
        if not device:
            return None

        return {
            "device_id": device.device_id,
            "hostname": device.hostname,
            "status": device.status,
            "updated_at": device.updated_at.isoformat(),
        }

    async def delete_device(self, device_id: str) -> bool:
        """Delete device."""
        return await self.inventory.manager.delete_device(device_id)

    async def list_devices(self, **filters) -> list[dict[str, Any]]:
        """List devices with filtering."""
        devices = await self.inventory.manager.list_devices(**filters)
        return [
            {
                "device_id": device.device_id,
                "hostname": device.hostname,
                "device_type": device.device_type,
                "status": device.status,
                "site_id": device.site_id,
                "created_at": device.created_at.isoformat(),
            }
            for device in devices
        ]

    # Device Monitoring Operations
    async def setup_device_monitoring(self, device_id: str, monitor_type: str = "snmp", **config) -> dict[str, Any]:
        """Set up monitoring for device."""
        if monitor_type == "snmp":
            result = await self.monitoring.create_snmp_monitor(
                device_id=device_id,
                metrics=config.get("metrics", ["system", "interfaces"]),
                collection_interval=config.get("interval", 60),
                snmp_community=config.get("community", "public"),
            )
        else:
            result = await self.monitoring.create_health_check(device_id=device_id, check_type=monitor_type)

        return result

    async def get_device_health(self, device_id: str) -> dict[str, Any]:
        """Get device health status."""
        health = await self.monitoring.manager.get_device_health_status(device_id)
        overview = await self.monitoring.get_device_monitoring_overview(device_id)

        return {
            "device_id": device_id,
            "health_status": health.get("health_status", "unknown"),
            "health_score": health.get("health_score", 0),
            "last_check": health.get("last_check"),
            "active_monitors": len(overview.get("active_monitors", [])),
            "issues": health.get("issues", []),
        }

    async def collect_device_metrics(
        self, device_id: str, snmp_config: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Collect metrics from device via SNMP."""
        device = await self.inventory.manager.get_device(device_id)
        if not device or not device.management_ip:
            raise DeviceManagementError("Device not found or missing management IP")

        # Create SNMP client
        config = SNMPConfig(
            host=device.management_ip,
            community=(snmp_config.get("community", "public") if snmp_config else "public"),
            version=snmp_config.get("version", "2c") if snmp_config else "2c",
        )

        client = SNMPClient(config)
        collector = SNMPCollector(client)

        # Collect comprehensive metrics
        metrics = await collector.collect_comprehensive_metrics()

        # Store metrics in monitoring record
        monitor_id = f"snmp_{device_id}"
        record = await self.monitoring.collect_snmp_metrics(
            device_id=device_id, monitor_id=monitor_id, metrics_data=metrics
        )

        return {
            "device_id": device_id,
            "collection_status": record["collection_status"],
            "metrics_count": record["metrics_count"],
            "collected_at": record["collected_at"],
            "metrics": metrics,
        }

    # MAC Address Registry Operations
    async def register_device_macs(self, device_id: str, interface_macs: dict[str, str]) -> dict[str, Any]:
        """Register MAC addresses for device interfaces."""
        return await self.mac_registry.discover_device_macs(device_id, interface_macs)

    async def lookup_mac_address(self, mac_address: str) -> Optional[dict[str, Any]]:
        """Look up MAC address information."""
        return await self.mac_registry.get_mac_address_details(mac_address)

    # Network Topology Operations
    async def add_device_to_topology(self, device_id: str, **node_config) -> dict[str, Any]:
        """Add device to network topology."""
        node = await self.topology.manager.create_node(
            node_id=device_id, node_type="device", device_id=device_id, **node_config
        )

        return {
            "node_id": node.node_id,
            "device_id": node.device_id,
            "name": node.name,
            "site_id": node.site_id,
            "created_at": node.created_at.isoformat(),
        }

    async def create_device_connection(self, source_device: str, target_device: str, **link_config) -> dict[str, Any]:
        """Create connection between devices."""
        link = await self.topology.manager.create_link(
            link_id=f"{source_device}_{target_device}",
            source_node_id=source_device,
            target_node_id=target_device,
            **link_config,
        )

        return {
            "link_id": link.link_id,
            "source_device": link.source_node_id,
            "target_device": link.target_node_id,
            "link_type": link.link_type,
            "bandwidth": link.bandwidth,
            "created_at": link.created_at.isoformat(),
        }

    async def find_device_path(self, source_device: str, target_device: str) -> dict[str, Any]:
        """Find network path between devices."""
        return await self.topology.discover_network_paths(source_device, target_device)

    async def analyze_network_topology(self, site_id: Optional[str] = None) -> dict[str, Any]:
        """Analyze network topology."""
        # Get topology data
        if site_id:
            topo_data = await self.topology.manager.get_site_topology(site_id)
            nodes = topo_data["nodes"]
            links = topo_data["links"]
        else:
            nodes = await self.topology.manager.list_nodes()
            links = await self.topology.manager.list_links()

        # Convert to dict format for analyzer
        nodes_data = [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "site_id": node.site_id,
                "status": node.status,
                "properties": node.properties,
            }
            for node in nodes
        ]

        links_data = [
            {
                "link_id": link.link_id,
                "source_node_id": link.source_node_id,
                "target_node_id": link.target_node_id,
                "link_type": link.link_type,
                "bandwidth": link.bandwidth,
                "latency_ms": link.latency_ms,
                "cost": link.cost,
                "status": link.status,
            }
            for link in links
        ]

        # Build graph and analyze
        self.topology_analyzer.build_graph(nodes_data, links_data)
        return self.topology_analyzer.generate_topology_report()

    # Lifecycle Management Operations
    async def provision_device(self, device_id: str, **config) -> dict[str, Any]:
        """Provision new device through lifecycle workflow."""
        return await self.lifecycle.execute_lifecycle_action(device_id=device_id, action="provision", parameters=config)

    async def deploy_device(self, device_id: str, **config) -> dict[str, Any]:
        """Deploy device through lifecycle workflow."""
        return await self.lifecycle.execute_lifecycle_action(device_id=device_id, action="deploy", parameters=config)

    async def decommission_device(self, device_id: str, **config) -> dict[str, Any]:
        """Decommission device through lifecycle workflow."""
        return await self.lifecycle.execute_lifecycle_action(
            device_id=device_id, action="decommission", parameters=config
        )

    # Comprehensive Operations
    async def get_device_overview(self, device_id: str) -> dict[str, Any]:
        """Get comprehensive device overview."""
        # Get basic device info
        device_info = await self.get_device(device_id)
        if not device_info:
            return {"error": "Device not found"}

        # Get health status
        health_info = await self.get_device_health(device_id)

        # Get topology connectivity
        connectivity = await self.topology.get_device_connectivity(device_id)

        # Get MAC addresses
        device_macs = await self.mac_registry.manager.get_device_mac_addresses(device_id)

        # Get interfaces and modules
        interfaces = await self.inventory.manager.get_device_interfaces(device_id)
        modules = await self.inventory.manager.get_device_modules(device_id)

        return {
            "device_info": device_info,
            "health_status": health_info,
            "connectivity": connectivity,
            "mac_addresses": [
                {
                    "mac_address": mac.mac_address,
                    "vendor": mac.vendor,
                    "interface": mac.interface_name,
                    "status": mac.status,
                }
                for mac in device_macs
            ],
            "interfaces": [
                {
                    "interface_id": iface.interface_id,
                    "name": iface.interface_name,
                    "type": iface.interface_type,
                    "status": iface.oper_status,
                    "speed": iface.speed,
                }
                for iface in interfaces
            ],
            "modules": [
                {
                    "module_id": module.module_id,
                    "slot": module.slot,
                    "type": module.module_type,
                    "status": module.status,
                }
                for module in modules
            ],
        }

    async def bulk_device_operation(self, device_ids: list[str], operation: str, **parameters) -> dict[str, Any]:
        """Perform bulk operation on multiple devices."""
        results = {
            "operation": operation,
            "total_devices": len(device_ids),
            "successful": [],
            "failed": [],
            "results": {},
        }

        for device_id in device_ids:
            if operation == "health_check":
                result = await self.get_device_health(device_id)
            elif operation == "collect_metrics":
                result = await self.collect_device_metrics(device_id, parameters.get("snmp_config"))
            elif operation == "update_status":
                result = await self.update_device(device_id, {"status": parameters["status"]})
            else:
                raise DeviceManagementError(f"Unknown operation: {operation}")

            results["successful"].append(device_id)
            results["results"][device_id] = result

        return results
