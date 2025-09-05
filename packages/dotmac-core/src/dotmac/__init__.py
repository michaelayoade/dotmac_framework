from pydantic import BaseModel

"""
DotMac Core Package - Stub Implementation

This is a stub implementation to enable testing while the full framework
is being developed by the team. Replace with actual implementation when available.
"""

from .exceptions import AuthorizationError, ConfigurationError, DotMacError, ValidationError
from .models import BaseModel, TenantContext

__version__ = "0.1.0-stub"
__all__ = [
    "DotMacError",
    "ValidationError",
    "AuthorizationError",
    "ConfigurationError",
    "BaseModel",
    "TenantContext",
]
