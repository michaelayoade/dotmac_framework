"""
DotMac Tenant - Multi-tenant identity resolution and isolation

This package provides comprehensive multi-tenancy capabilities including:
- Tenant identification and resolution
- Request context management
- Security enforcement and isolation
- Database helpers for RLS and schema-per-tenant
"""

from .identity import (
    TenantContext,
    TenantIdentityResolver,
    TenantResolutionStrategy,
    get_current_tenant,
    require_tenant,
)
from .middleware import TenantMiddleware
from .config import TenantConfig
from .exceptions import (
    TenantError,
    TenantNotFoundError,
    TenantResolutionError,
    TenantSecurityError,
)

__version__ = "0.1.0"

__all__ = [
    # Core identity resolution
    "TenantContext",
    "TenantIdentityResolver", 
    "TenantResolutionStrategy",
    "get_current_tenant",
    "require_tenant",
    
    # Middleware
    "TenantMiddleware",
    
    # Configuration
    "TenantConfig",
    
    # Exceptions
    "TenantError",
    "TenantNotFoundError", 
    "TenantResolutionError",
    "TenantSecurityError",
    
    # Version
    "__version__",
]