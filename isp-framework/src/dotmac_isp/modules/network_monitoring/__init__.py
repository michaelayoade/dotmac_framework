"""Network Monitoring Module for SNMP-based Device Monitoring.

This module provides comprehensive network monitoring capabilities including:
- SNMP-based device monitoring and data collection
- Real-time network performance metrics
- Network device health monitoring
- Alert generation and notification
- Historical data analysis and reporting
- Network topology discovery via SNMP
- Bandwidth utilization monitoring
- Device availability monitoring
"""

from .models import (
    MonitoringProfile,
    SnmpDevice,
    SnmpMetric,
    MonitoringAlert,
    AlertRule,
    MonitoringSchedule,
    DeviceAvailability,
    InterfaceMetric,
    SystemMetric,
)
from .schemas import (
    MonitoringProfileCreate,
    MonitoringProfileResponse,
    SnmpDeviceCreate,
    SnmpDeviceResponse,
    SnmpMetricResponse,
    MonitoringAlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    DeviceAvailabilityResponse,
)
from .service import (
    NetworkMonitoringService as SnmpMonitoringService,
    AlertManagementService as AlertingService,
    SnmpDeviceService as MetricsCollectionService,
    MonitoringProfileService as NetworkDiscoveryService,
    NetworkMonitoringMainService as PerformanceAnalyticsService,
)
from .snmp_client import SnmpClient, SnmpError
# Collectors not yet implemented - placeholder for future development
# from .collectors import (
#     SystemMetricsCollector,
#     InterfaceMetricsCollector, 
#     CustomMetricsCollector,
# )

__all__ = [
    # Models
    "MonitoringProfile",
    "SnmpDevice",
    "SnmpMetric",
    "MonitoringAlert",
    "AlertRule",
    "MonitoringSchedule",
    "DeviceAvailability",
    "InterfaceMetric",
    "SystemMetric",
    # Schemas
    "MonitoringProfileCreate",
    "MonitoringProfileResponse",
    "SnmpDeviceCreate",
    "SnmpDeviceResponse",
    "SnmpMetricResponse",
    "MonitoringAlertResponse",
    "AlertRuleCreate",
    "AlertRuleResponse",
    "DeviceAvailabilityResponse",
    # Services
    "SnmpMonitoringService",
    "AlertingService",
    "MetricsCollectionService",
    "NetworkDiscoveryService",
    "PerformanceAnalyticsService",
    # Core components
    "SnmpClient",
    "SnmpError",
    # Collectors - not yet implemented
    # "SystemMetricsCollector",
    # "InterfaceMetricsCollector",
    # "CustomMetricsCollector",
]
