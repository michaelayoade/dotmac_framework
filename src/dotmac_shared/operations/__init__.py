"""
DotMac Operations Module

Comprehensive operations automation following strict DRY patterns.
All operations scripts MUST use shared patterns and exception handlers.
"""

from .automation import (
    InfrastructureAutomation,
    MaintenanceScheduler,
    OperationsOrchestrator,
)
from .health_monitoring import NetworkHealthMonitor, ServiceHealthChecker
from .lifecycle_management import (
    CustomerLifecycleManager,
    ServiceProvisioningAutomation,
)

__all__ = [
    # Health Monitoring
    "NetworkHealthMonitor",
    "ServiceHealthChecker",
    # Lifecycle Management
    "CustomerLifecycleManager",
    "ServiceProvisioningAutomation",
    # Infrastructure Automation
    "InfrastructureAutomation",
    "MaintenanceScheduler",
    "OperationsOrchestrator",
]
