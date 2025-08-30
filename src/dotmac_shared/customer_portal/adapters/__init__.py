"""
Customer portal adapters.

Platform-specific adapters for integrating with ISP Framework and Management Platform.
"""

from .base import CustomerPortalAdapter
from .isp_adapter import ISPPortalAdapter
from .management_adapter import ManagementPortalAdapter

__all__ = [
    "CustomerPortalAdapter",
    "ISPPortalAdapter",
    "ManagementPortalAdapter",
]
