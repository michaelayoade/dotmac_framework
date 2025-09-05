"""
SNMP Monitoring and Network Telemetry

Comprehensive network device monitoring with SNMP support for:
- Real-time performance metrics (CPU, memory, interfaces)
- Multi-vendor device support (Cisco, Juniper, Mikrotik, generic)
- Automated alerting and threshold management
- Historical data collection and trending
"""

from .network_monitor import DeviceMetrics, MonitoringTarget, NetworkMonitor
from .snmp_collector import SNMPCollector, SNMPConfig

InterfaceMonitor = NetworkMonitor  # Alias for now
DeviceHealthMonitor = NetworkMonitor  # Alias for now
MetricsCollector = SNMPCollector  # Alias for now

__all__ = [
    "SNMPCollector",
    "SNMPConfig",
    "NetworkMonitor",
    "MonitoringTarget",
    "DeviceMetrics",
    "InterfaceMonitor",
    "DeviceHealthMonitor",
    "MetricsCollector",
]
