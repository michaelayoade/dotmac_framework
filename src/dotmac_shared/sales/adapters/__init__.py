"""
Sales platform adapters.
"""
try:
    from .isp_adapter import ISPSalesAdapter
except ImportError:
    ISPSalesAdapter = None

try:
    from .management_adapter import ManagementPlatformSalesAdapter
except ImportError:
    ManagementPlatformSalesAdapter = None

__all__ = ["ISPSalesAdapter", "ManagementPlatformSalesAdapter"]
