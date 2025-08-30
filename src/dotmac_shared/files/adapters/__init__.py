"""
Platform adapters for integrating file service with different platforms.
"""

from .isp_adapter import ISPFileAdapter
from .management_adapter import ManagementPlatformAdapter

__all__ = [
    "ISPFileAdapter",
    "ManagementPlatformAdapter",
]
