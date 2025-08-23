"""Network Integration Module for DotMac ISP Framework.

This module provides comprehensive network infrastructure integration including:
- Network device management and monitoring
- SNMP-based device monitoring
- Network topology discovery and visualization
- Device location tracking and GIS integration
- Performance metrics and alerting
"""

from .models import (
    NetworkDevice,
    NetworkInterface,
    NetworkLocation,
    NetworkMetric,
    NetworkTopology,
    DeviceConfiguration,
    NetworkAlert,
    DeviceGroup,
    NetworkService,
    MaintenanceWindow,
)
from .schemas import (
    NetworkDeviceCreate,
    NetworkDeviceUpdate,
    NetworkDeviceResponse,
    NetworkLocationCreate,
    NetworkLocationUpdate,
    NetworkLocationResponse,
    NetworkMetricResponse,
    NetworkTopologyResponse,
    DeviceConfigurationCreate,
    DeviceConfigurationResponse,
    NetworkAlertResponse,
    DeviceGroupCreate,
    DeviceGroupResponse,
    NetworkServiceCreate,
    NetworkServiceResponse,
    MaintenanceWindowCreate,
    MaintenanceWindowResponse,
)

__all__ = [
    # Models
    "NetworkDevice",
    "NetworkInterface",
    "NetworkLocation",
    "NetworkMetric",
    "NetworkTopology",
    "DeviceConfiguration",
    "NetworkAlert",
    "DeviceGroup",
    "NetworkService",
    "MaintenanceWindow",
    # Schemas
    "NetworkDeviceCreate",
    "NetworkDeviceUpdate",
    "NetworkDeviceResponse",
    "NetworkLocationCreate",
    "NetworkLocationUpdate",
    "NetworkLocationResponse",
    "NetworkMetricResponse",
    "NetworkTopologyResponse",
    "DeviceConfigurationCreate",
    "DeviceConfigurationResponse",
    "NetworkAlertResponse",
    "DeviceGroupCreate",
    "DeviceGroupResponse",
    "NetworkServiceCreate",
    "NetworkServiceResponse",
    "MaintenanceWindowCreate",
    "MaintenanceWindowResponse",
]
