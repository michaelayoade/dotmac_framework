"""
Device Management Framework Exceptions.
"""


class DeviceManagementError(Exception):
    """Base exception for device management operations."""

    pass


class DeviceInventoryError(DeviceManagementError):
    """Exception for device inventory operations."""

    pass


class DeviceMonitoringError(DeviceManagementError):
    """Exception for device monitoring operations."""

    pass


class MacRegistryError(DeviceManagementError):
    """Exception for MAC address registry operations."""

    pass


class NetworkTopologyError(DeviceManagementError):
    """Exception for network topology operations."""

    pass


class DeviceConfigError(DeviceManagementError):
    """Exception for device configuration operations."""

    pass


class DeviceLifecycleError(DeviceManagementError):
    """Exception for device lifecycle operations."""

    pass


class SNMPError(DeviceManagementError):
    """Exception for SNMP operations."""

    pass


class TopologyAnalysisError(DeviceManagementError):
    """Exception for topology analysis operations."""

    pass
