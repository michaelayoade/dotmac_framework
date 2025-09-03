"""
Tenant Identity and Context Management

MIGRATION NOTICE: This module provides backward compatibility during migration
to the new dotmac-tenant package. See MIGRATION_GUIDE.md for details.

All imports from this module continue to work but will show deprecation warnings
when the new package is available. New code should import from dotmac.tenant.
"""

# Import legacy shims for backward compatibility
from ._legacy_shims import (
    LegacyTenantContext as TenantContext,
    LegacyTenantMiddleware as TenantMiddleware,
    LegacyTenantIdentityResolver as TenantIdentityResolver,
    LegacyTenantResolutionStrategy as TenantResolutionStrategy,
    legacy_tenant_resolver as tenant_resolver,
    legacy_tenant_registry as TenantRegistry,  # Class reference for legacy compatibility
    legacy_tenant_registry as tenant_registry,  # Instance reference
    legacy_get_current_tenant as get_current_tenant,
    legacy_require_tenant as require_tenant,
    legacy_tenant_required as tenant_required,
    legacy_resolve_tenant_from_host as resolve_tenant_from_host,
)

__all__ = [
    "TenantContext",
    "TenantIdentityResolver",
    "TenantRegistry", 
    "TenantResolutionStrategy",
    "tenant_resolver",
    "tenant_registry",
    "resolve_tenant_from_host",
    "TenantMiddleware",
    "get_current_tenant",
    "require_tenant", 
    "tenant_required",
]