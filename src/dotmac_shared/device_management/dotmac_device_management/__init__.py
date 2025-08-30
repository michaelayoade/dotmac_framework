"""
DotMac Device Management Framework

Comprehensive device management system providing:
- Device inventory and asset tracking
- SNMP monitoring and telemetry collection
- Network topology discovery and management
- Hardware lifecycle management
- MAC address registry and tracking
- Configuration management and templates
- Device health monitoring and alerting

This framework standardizes device management across all DotMac modules.
"""

from .adapters.platform_adapter import (
    BaseDeviceAdapter,
    ISPDeviceAdapter,
    ManagementDeviceAdapter,
)
from .core.device_inventory import DeviceInventoryManager, DeviceInventoryService
from .core.device_monitoring import DeviceMonitoringManager, DeviceMonitoringService
from .core.mac_registry import MacRegistryManager, MacRegistryService
from .core.models import (
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
from .core.network_topology import NetworkTopologyManager, NetworkTopologyService
from .core.schemas import (
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
from .services.device_service import DeviceService
from .utils.snmp_client import SNMPClient, SNMPCollector
from .utils.topology_analyzer import TopologyAnalyzer
from .workflows.lifecycle_manager import DeviceLifecycleManager

__version__ = "1.0.0"

__all__ = [
    # Core managers
    "DeviceInventoryManager",
    "DeviceInventoryService",
    "DeviceMonitoringManager",
    "DeviceMonitoringService",
    "MacRegistryManager",
    "MacRegistryService",
    "NetworkTopologyManager",
    "NetworkTopologyService",
    # Models
    "Device",
    "DeviceModule",
    "DeviceInterface",
    "NetworkNode",
    "NetworkLink",
    "MacAddress",
    "MonitoringRecord",
    "ConfigTemplate",
    "ConfigIntent",
    # Schemas
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
    # Services
    "DeviceService",
    # Adapters
    "BaseDeviceAdapter",
    "ISPDeviceAdapter",
    "ManagementDeviceAdapter",
    # Utilities
    "SNMPClient",
    "SNMPCollector",
    "TopologyAnalyzer",
    # Workflows
    "DeviceLifecycleManager",
    # Version
    "__version__",
]
