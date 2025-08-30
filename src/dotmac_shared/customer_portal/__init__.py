"""
Shared Customer Portal Service

Unified customer portal functionality shared between ISP Framework and Management Platform.
Implements DRY principles by consolidating common portal operations.
"""

from .adapters.isp_adapter import ISPPortalAdapter
from .adapters.management_adapter import ManagementPortalAdapter
from .core.auth import PortalAuthenticationManager
from .core.schemas import (
    BillingSummary,
    CustomerDashboardData,
    CustomerPortalConfig,
    CustomerProfileUpdate,
    PortalSessionData,
    ServiceUsageData,
)
from .core.service import CustomerPortalService

__all__ = [
    # Core service
    "CustomerPortalService",
    # Schemas
    "CustomerDashboardData",
    "CustomerPortalConfig",
    "PortalSessionData",
    "CustomerProfileUpdate",
    "ServiceUsageData",
    "BillingSummary",
    # Authentication
    "PortalAuthenticationManager",
    # Platform adapters
    "ISPPortalAdapter",
    "ManagementPortalAdapter",
]
