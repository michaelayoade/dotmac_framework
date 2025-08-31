"""
DotMac Framework Python SDK - Modern DRY Implementation

Official Python SDK for the DotMac Platform API.
NO BACKWARD COMPATIBILITY - Pure DRY patterns only.
"""

__version__ = "2.0.0"  # Breaking change - no backward compatibility
__author__ = "DotMac Team"
__email__ = "support@dotmac.com"

# Main client exports - Modern DRY patterns only
from .client import DotMacClient
from .exceptions import DotMacAPIError, DotMacAuthError, DotMacConfigError

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "DotMacClient",
    "DotMacAPIError", 
    "DotMacAuthError",
    "DotMacConfigError",
]

# NO LEGACY COMPATIBILITY - All clients must use modern DotMacClient
# For migration: Replace _LegacyDotMacClient with DotMacClient
# Breaking change: Service interfaces updated to use DRY patterns