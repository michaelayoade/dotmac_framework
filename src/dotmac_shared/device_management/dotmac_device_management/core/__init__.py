"""
Core device management components.
"""

from .device_inventory import DeviceInventoryManager, DeviceInventoryService
from .device_monitoring import DeviceMonitoringManager, DeviceMonitoringService
from .mac_registry import MacRegistryManager, MacRegistryService
from .models import (
    ConfigIntent,
    ConfigTemplate,
    Device,
    DeviceInterface,
    DeviceModule,
    MacAddress,
    MonitoringRecord,
    NetworkLink,
    NetworkNode,
)
from .network_topology import NetworkTopologyManager, NetworkTopologyService
from .schemas import (
    ConfigIntentResponse,
    ConfigTemplateResponse,
    DeviceCreateRequest,
    DeviceInterfaceResponse,
    DeviceModuleResponse,
    DeviceResponse,
    MacAddressResponse,
    MonitoringRecordResponse,
    NetworkLinkResponse,
    NetworkNodeResponse,
    TopologyResponse,
)

__all__ = [
    "DeviceInventoryManager",
    "DeviceInventoryService",
    "DeviceMonitoringManager",
    "DeviceMonitoringService",
    "MacRegistryManager",
    "MacRegistryService",
    "NetworkTopologyManager",
    "NetworkTopologyService",
    "Device",
    "DeviceModule",
    "DeviceInterface",
    "NetworkNode",
    "NetworkLink",
    "MacAddress",
    "MonitoringRecord",
    "ConfigTemplate",
    "ConfigIntent",
    "DeviceResponse",
    "DeviceCreateRequest",
    "DeviceModuleResponse",
    "DeviceInterfaceResponse",
    "MonitoringRecordResponse",
    "MacAddressResponse",
    "NetworkNodeResponse",
    "NetworkLinkResponse",
    "TopologyResponse",
    "ConfigTemplateResponse",
    "ConfigIntentResponse",
]
