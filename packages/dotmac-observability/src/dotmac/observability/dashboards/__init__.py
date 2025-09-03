"""Dashboard provisioning and management for DotMac observability."""

from .manager import (
    provision_platform_dashboards,
    DashboardProvisioningResult,
    DashboardConfig,
)

__all__ = [
    "provision_platform_dashboards",
    "DashboardProvisioningResult", 
    "DashboardConfig",
]