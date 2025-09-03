"""
Legacy shims for backward compatibility during tenant system migration.

This module provides compatibility imports from the new dotmac-tenant package
while maintaining the existing API surface of dotmac_shared.tenant.
"""

import warnings
from typing import Optional, Dict, Any, List

# Import from new package with fallback to original implementation
try:
    from dotmac.tenant import (
        TenantContext as _NewTenantContext,
        TenantMiddleware as _NewTenantMiddleware,
        TenantIdentityResolver as _NewTenantIdentityResolver,
        TenantResolutionStrategy as _NewTenantResolutionStrategy,
        get_current_tenant as _new_get_current_tenant,
        require_tenant as _new_require_tenant,
        tenant_required as _new_tenant_required,
        TenantConfig,
    )
    
    NEW_PACKAGE_AVAILABLE = True
    
except ImportError:
    NEW_PACKAGE_AVAILABLE = False
    # Fallback to original implementation would be here
    from .identity import (
        TenantContext as _OriginalTenantContext,
        TenantIdentityResolver as _OriginalTenantIdentityResolver,
        TenantResolutionStrategy as _OriginalTenantResolutionStrategy,
        tenant_resolver,
        tenant_registry,
    )
    from .middleware import (
        TenantMiddleware as _OriginalTenantMiddleware,
        get_current_tenant as _original_get_current_tenant,
        require_tenant as _original_require_tenant,
        tenant_required as _original_tenant_required,
    )


def _show_migration_warning(item_name: str):
    """Show migration warning for legacy usage."""
    if NEW_PACKAGE_AVAILABLE:
        warnings.warn(
            f"Using {item_name} from dotmac_shared.tenant is deprecated. "
            f"Please migrate to 'from dotmac.tenant import {item_name}' "
            f"for enhanced features and future compatibility.",
            DeprecationWarning,
            stacklevel=3
        )


class LegacyTenantContext:
    """Legacy wrapper for TenantContext with backward compatibility."""
    
    def __new__(cls, *args, **kwargs):
        _show_migration_warning("TenantContext")
        
        if NEW_PACKAGE_AVAILABLE:
            # Map legacy parameters to new format
            if len(args) >= 1:
                # Convert positional arguments
                tenant_id = args[0]
                subdomain = kwargs.get('subdomain')
                host = kwargs.get('host') 
                resolution_strategy = kwargs.get('resolution_strategy')
                is_management = kwargs.get('is_management', False)
                is_verified = kwargs.get('is_verified', False)
                metadata = kwargs.get('metadata', {})
                
                # Create new context with mapped fields
                return _NewTenantContext(
                    tenant_id=tenant_id,
                    display_name=None,  # New field
                    resolution_method=str(resolution_strategy) if resolution_strategy else "legacy",
                    resolved_from=host or subdomain or "legacy",
                    context_data=metadata,
                    # Legacy compatibility fields in context_data
                    context_data_legacy={
                        'subdomain': subdomain,
                        'host': host,
                        'is_management': is_management,
                        'is_verified': is_verified,
                        'metadata': metadata,
                    }
                )
            else:
                return _NewTenantContext(**kwargs)
        else:
            # Fallback to original implementation
            return _OriginalTenantContext(*args, **kwargs)


class LegacyTenantMiddleware:
    """Legacy wrapper for TenantMiddleware with backward compatibility."""
    
    def __new__(cls, app, *args, **kwargs):
        _show_migration_warning("TenantMiddleware")
        
        if NEW_PACKAGE_AVAILABLE:
            # Map legacy parameters to new configuration
            require_tenant = kwargs.get('require_tenant', True)
            skip_paths = kwargs.get('skip_paths', ["/health", "/metrics", "/docs", "/openapi.json"])
            
            # Create new-style config from legacy parameters
            config = TenantConfig(
                # Map legacy settings to new config
                resolution_strategy="host",  # Default legacy behavior
                fallback_tenant_id=None if require_tenant else "default",
                # Add skip paths logic would need to be handled in application
            )
            
            return _NewTenantMiddleware(app, config=config, **kwargs)
        else:
            # Fallback to original implementation 
            return _OriginalTenantMiddleware(app, *args, **kwargs)


class LegacyTenantIdentityResolver:
    """Legacy wrapper for TenantIdentityResolver with backward compatibility."""
    
    def __new__(cls, *args, **kwargs):
        _show_migration_warning("TenantIdentityResolver")
        
        if NEW_PACKAGE_AVAILABLE:
            # Map legacy constructor parameters
            base_domains = kwargs.get('base_domains', args[0] if args else None)
            management_domains = kwargs.get('management_domains', args[1] if len(args) > 1 else None)
            
            # Create new config from legacy parameters
            config = TenantConfig(
                # Map legacy domains to new host mappings
                host_tenant_mapping={},  # Would need domain-specific mapping
            )
            
            return _NewTenantIdentityResolver(config)
        else:
            # Fallback to original implementation
            return _OriginalTenantIdentityResolver(*args, **kwargs)


class LegacyTenantResolutionStrategy:
    """Legacy enum wrapper for backward compatibility."""
    
    def __new__(cls):
        _show_migration_warning("TenantResolutionStrategy")
        
        if NEW_PACKAGE_AVAILABLE:
            return _NewTenantResolutionStrategy
        else:
            return _OriginalTenantResolutionStrategy


def legacy_get_current_tenant() -> Optional[object]:
    """Legacy wrapper for get_current_tenant."""
    _show_migration_warning("get_current_tenant")
    
    if NEW_PACKAGE_AVAILABLE:
        return _new_get_current_tenant()
    else:
        return _original_get_current_tenant()


def legacy_require_tenant() -> object:
    """Legacy wrapper for require_tenant."""
    _show_migration_warning("require_tenant")
    
    if NEW_PACKAGE_AVAILABLE:
        return _new_require_tenant()
    else:
        return _original_require_tenant()


def legacy_tenant_required(func):
    """Legacy wrapper for tenant_required decorator."""
    _show_migration_warning("tenant_required")
    
    if NEW_PACKAGE_AVAILABLE:
        return _new_tenant_required(func)
    else:
        return _original_tenant_required(func)


# Legacy registry and resolver singletons
if NEW_PACKAGE_AVAILABLE:
    # Create legacy-compatible instances using new system
    _legacy_config = TenantConfig()
    legacy_tenant_resolver = _NewTenantIdentityResolver(_legacy_config)
    
    # Mock registry for compatibility
    class LegacyTenantRegistry:
        """Legacy registry wrapper."""
        
        async def get_tenant_info(self, tenant_id: str) -> Optional[Dict[str, Any]]:
            # Return legacy-compatible format
            return {
                "tenant_id": tenant_id,
                "status": "active",
                "plan": "professional", 
                "features": ["billing", "monitoring"],
                "region": "us-east-1"
            }
        
        async def validate_tenant_access(self, tenant_id: str, resource: str, action: str) -> bool:
            return True
    
    legacy_tenant_registry = LegacyTenantRegistry()
    
else:
    # Use original implementations
    legacy_tenant_resolver = tenant_resolver
    legacy_tenant_registry = tenant_registry


# Legacy convenience function
async def legacy_resolve_tenant_from_host(host: str) -> Optional[object]:
    """Legacy wrapper for resolve_tenant_from_host."""
    _show_migration_warning("resolve_tenant_from_host")
    
    if NEW_PACKAGE_AVAILABLE:
        return await legacy_tenant_resolver.resolve_tenant(
            # Create mock request object for new API
            type('MockRequest', (), {'headers': {'host': host}})()
        )
    else:
        from .identity import resolve_tenant_from_host
        return await resolve_tenant_from_host(host)