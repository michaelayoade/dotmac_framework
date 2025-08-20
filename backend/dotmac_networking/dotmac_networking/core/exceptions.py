"""
Custom exceptions for DotMac Networking operations.
"""


class NetworkingError(Exception):
    """Base exception for networking operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "NETWORKING_ERROR"
        self.details = details or {}


class DeviceError(NetworkingError):
    """Exception for device-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "DEVICE_ERROR", details)


class IPAMError(NetworkingError):
    """Exception for IPAM-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "IPAM_ERROR", details)


class VLANError(NetworkingError):
    """Exception for VLAN-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "VLAN_ERROR", details)


class TopologyError(NetworkingError):
    """Exception for topology-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "TOPOLOGY_ERROR", details)


class RADIUSError(NetworkingError):
    """Exception for RADIUS-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "RADIUS_ERROR", details)


class ConfigError(NetworkingError):
    """Exception for configuration-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "CONFIG_ERROR", details)


class AutomationError(NetworkingError):
    """Exception for automation-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "AUTOMATION_ERROR", details)


class MonitoringError(NetworkingError):
    """Exception for monitoring-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "MONITORING_ERROR", details)


class AlarmError(NetworkingError):
    """Exception for alarm-related operations."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message, error_code or "ALARM_ERROR", details)


# Specific error types
class DeviceNotFoundError(DeviceError):
    """Device not found."""

    def __init__(self, device_id: str):
        super().__init__(f"Device not found: {device_id}", "DEVICE_NOT_FOUND", {"device_id": device_id})


class IPAddressConflictError(IPAMError):
    """IP address conflict."""

    def __init__(self, ip_address: str):
        super().__init__(f"IP address conflict: {ip_address}", "IP_CONFLICT", {"ip_address": ip_address})


class VLANConflictError(VLANError):
    """VLAN conflict."""

    def __init__(self, vlan_id: int):
        super().__init__(f"VLAN conflict: {vlan_id}", "VLAN_CONFLICT", {"vlan_id": vlan_id})


class ConfigDriftDetectedError(ConfigError):
    """Configuration drift detected."""

    def __init__(self, device_id: str, drift_details: dict):
        super().__init__(f"Configuration drift detected on device: {device_id}", "CONFIG_DRIFT",
                        {"device_id": device_id, "drift": drift_details})


class AutomationTimeoutError(AutomationError):
    """Automation operation timed out."""

    def __init__(self, operation: str, timeout: int):
        super().__init__(f"Automation operation timed out: {operation} after {timeout}s",
                        "AUTOMATION_TIMEOUT", {"operation": operation, "timeout": timeout})


class RADIUSAuthenticationError(RADIUSError):
    """RADIUS authentication failed."""

    def __init__(self, username: str):
        super().__init__(f"RADIUS authentication failed for user: {username}",
                        "RADIUS_AUTH_FAILED", {"username": username})


class CoAFailedError(RADIUSError):
    """Change of Authorization failed."""

    def __init__(self, session_id: str, reason: str):
        super().__init__(f"CoA failed for session {session_id}: {reason}",
                        "COA_FAILED", {"session_id": session_id, "reason": reason})


class MonitoringDataUnavailableError(MonitoringError):
    """Monitoring data unavailable."""

    def __init__(self, device_id: str, metric: str):
        super().__init__(f"Monitoring data unavailable for {metric} on device: {device_id}",
                        "MONITORING_DATA_UNAVAILABLE", {"device_id": device_id, "metric": metric})


class AlarmStormDetectedError(AlarmError):
    """Alarm storm detected."""

    def __init__(self, device_id: str, alarm_count: int, time_window: int):
        super().__init__(f"Alarm storm detected on device {device_id}: {alarm_count} alarms in {time_window}s",
                        "ALARM_STORM", {"device_id": device_id, "alarm_count": alarm_count, "time_window": time_window})
