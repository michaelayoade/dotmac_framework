"""
DotMac Networking - Networking Plane SDKs for ISP Operations

A comprehensive networking management system providing minimal, reusable SDKs
for resource topology, identity & access, config & execution, and monitoring
& assurance in Internet Service Provider operations.
"""

from .core.config import NetworkingConfig
from .core.exceptions import (
    AlarmError,
    AutomationError,
    ConfigError,
    DeviceError,
    IPAMError,
    MonitoringError,
    NetworkingError,
    RADIUSError,
    TopologyError,
    VLANError,
)
from .sdks.alarm_events import AlarmEventsSDK

# Config & execution SDKs
from .sdks.device_config import DeviceConfigSDK
from .sdks.device_inventory import DeviceInventorySDK

# Monitoring & assurance SDKs
from .sdks.device_monitoring import DeviceMonitoringSDK
from .sdks.device_provisioning import DeviceProvisioningSDK
from .sdks.flow_analytics import FlowAnalyticsSDK
from .sdks.ipam import IPAMSDK
from .sdks.mac_registry import MacRegistrySDK
from .sdks.nas import NASSDK
from .sdks.network_automation import NetworkAutomationSDK
from .sdks.network_topology import NetworkTopologySDK
from .sdks.olt_onu import OltOnuSDK
from .sdks.radius import RADIUSSDK

# Identity & access SDKs
from .sdks.radius_server_mgmt import RADIUSServerMgmtSDK
from .sdks.service_assurance import ServiceAssuranceSDK

# Resource & topology SDKs
from .sdks.site_pop import SitePopSDK
from .sdks.tr069_cwmp import TR069CWMPSDK
from .sdks.vlan import VLANSDK

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "support@dotmac.com"

__all__ = [
    # Core
    "NetworkingConfig",
    # Exceptions
    "NetworkingError",
    "DeviceError",
    "IPAMError",
    "VLANError",
    "TopologyError",
    "RADIUSError",
    "ConfigError",
    "AutomationError",
    "MonitoringError",
    "AlarmError",
    # Resource & topology SDKs
    "SitePopSDK",
    "DeviceInventorySDK",
    "IPAMSDK",
    "VLANSDK",
    "MacRegistrySDK",
    "NetworkTopologySDK",
    # Identity & access SDKs
    "RADIUSServerMgmtSDK",
    "RADIUSSDK",
    "NASSDK",
    "OltOnuSDK",
    "TR069CWMPSDK",
    # Config & execution SDKs
    "DeviceConfigSDK",
    "NetworkAutomationSDK",
    "DeviceProvisioningSDK",
    # Monitoring & assurance SDKs
    "DeviceMonitoringSDK",
    "AlarmEventsSDK",
    "ServiceAssuranceSDK",
    "FlowAnalyticsSDK",
]
