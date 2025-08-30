"""
Platform adapters.

This module contains adapters for integrating the authentication service
with different platforms in the DotMac framework:
- ISP Framework integration
- Management Platform integration
"""

from .isp_adapter import ISPAuthAdapter
from .management_adapter import ManagementAuthAdapter

__all__ = [
    "ISPAuthAdapter",
    "ManagementAuthAdapter",
]
