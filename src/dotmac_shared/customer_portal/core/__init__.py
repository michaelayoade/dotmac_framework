"""
Core customer portal functionality.
"""

from .auth import PortalAuthenticationManager
from .schemas import (
    BillingSummary,
    CustomerDashboardData,
    CustomerPortalConfig,
    CustomerProfileUpdate,
    CustomerStatus,
    PortalSessionData,
    PortalType,
    ServiceStatus,
    ServiceUsageData,
)
from .service import CustomerPortalService, create_portal_service

__all__ = [
    # Service
    "CustomerPortalService",
    "create_portal_service",
    "PortalAuthenticationManager",
    # Schemas
    "CustomerDashboardData",
    "CustomerPortalConfig",
    "PortalSessionData",
    "CustomerProfileUpdate",
    "ServiceUsageData",
    "BillingSummary",
    "PortalType",
    "CustomerStatus",
    "ServiceStatus",
]
