"""
Minimal, reusable SDKs for DotMac Networking.
"""

# Resource & topology SDKs
from .alarm_events import AlarmEventsSDK

# Config & execution SDKs
from .device_config import DeviceConfigSDK
from .device_inventory import DeviceInventorySDK

# Monitoring & assurance SDKs
from .device_monitoring import DeviceMonitoringSDK
from .device_provisioning import DeviceProvisioningSDK
from .flow_analytics import FlowAnalyticsSDK
from .ipam import IPAMSDK
from .mac_registry import MacRegistrySDK
from .nas import NASSDK
from .network_automation import NetworkAutomationSDK
from .network_topology import NetworkTopologySDK
from .olt_onu import OltOnuSDK
from .radius import RADIUSSDK

# Identity & access SDKs
from .radius_server_mgmt import RADIUSServerMgmtSDK
from .service_assurance import ServiceAssuranceSDK
from .site_pop import SitePopSDK
from .tr069_cwmp import TR069CWMPSDK
from .vlan import VLANSDK

__all__ = [
    # Resource & topology
    "DeviceInventorySDK",
    "SitePopSDK",
    "IPAMSDK",
    "VLANSDK",
    "MacRegistrySDK",
    "NetworkTopologySDK",
    # Identity & access
    "RADIUSServerMgmtSDK",
    "RADIUSSDK",
    "NASSDK",
    "OltOnuSDK",
    "TR069CWMPSDK",
    # Config & execution
    "DeviceConfigSDK",
    "NetworkAutomationSDK",
    "DeviceProvisioningSDK",
    # Monitoring & assurance
    "DeviceMonitoringSDK",
    "AlarmEventsSDK",
    "ServiceAssuranceSDK",
    "FlowAnalyticsSDK",
]
