"""
DotMac Plugins - Comprehensive plugin system with typed interfaces and lifecycle management.

Provides a complete plugin system for the DotMac Framework including:
- Typed plugin interfaces for different plugin kinds
- Registry-based plugin management with lifecycle orchestration  
- Discovery system for entry points and namespace packages
- Security features including signing/verification and sandboxing
- Observability hooks for monitoring and metrics
- Tenant-aware plugin context with permission management

Key Components:
- Plugin interfaces: IPlugin, IExportPlugin, IDeploymentProvider, IDNSProvider, IObserver, IRouterPlugin
- Registry and lifecycle: PluginRegistry, PluginLifecycleManager  
- Discovery: Entry point and namespace package discovery
- Context: PluginContext with services, config, and permissions
- Security: Signature verification and sandboxing policies
- Observability: Event hooks and metrics collection

Example Usage:
    from dotmac.plugins import (
        PluginRegistry, PluginLifecycleManager, PluginContext,
        IExportPlugin, PluginKind, discover_plugins
    )
    
    # Create lifecycle manager
    lifecycle = PluginLifecycleManager()
    
    # Load plugins from entry points
    lifecycle.load_plugins()
    
    # Create context
    context = PluginContext(
        tenant_id="acme",
        environment="production",
        permissions={"export", "dns:validate"}
    )
    
    # Initialize and start plugins
    await lifecycle.initialize_all(context)
    await lifecycle.start_all()
    
    # Use plugins
    export_plugins = lifecycle.registry.list(kind=PluginKind.EXPORT)
    if export_plugins:
        result = await export_plugins[0].export({"format": "csv", "type": "commissions"})
"""

# Core registry and lifecycle management
from .registry import PluginRegistry
from .lifecycle import PluginLifecycleManager

# Plugin interfaces
from .interfaces import (
    IPlugin,
    IExportPlugin,
    IDeploymentProvider, 
    IDNSProvider,
    IObserver,
    IRouterPlugin,
)

# Types and enums
from .types import (
    PluginKind,
    PluginStatus,
    PluginError,
    PluginNotFoundError,
    PluginRegistrationError,
    PluginInitError,
    PluginStartError,
    PluginStopError,
    PluginPermissionError,
    PluginVersionError,
    PluginConfigError,
    PluginDependencyError,
    PluginSecurityError,
    PluginDiscoveryError,
    ExportResult,
    DeploymentResult,
    ValidationResult,
    PluginConfig,
    PluginCapabilities,
)

# Metadata and context
from .metadata import PluginMetadata, Version, Author
from .context import PluginContext

# Discovery functions
from .discovery import (
    discover_plugins,
    discover_entry_points_only,
    discover_namespace_only,
    validate_plugin_requirements,
    create_plugin_factory,
)

# Observability
from .observability import (
    PluginObservabilityHooks,
    ObservabilityCollector,
    LoggingObservabilityCollector,
    MetricsCollector,
)

# Core exports - always available
__all__ = [
    # Core management
    "PluginRegistry",
    "PluginLifecycleManager",
    
    # Interfaces
    "IPlugin",
    "IExportPlugin", 
    "IDeploymentProvider",
    "IDNSProvider",
    "IObserver",
    
    # Types and enums
    "PluginKind",
    "PluginStatus",
    "ExportResult",
    "DeploymentResult", 
    "ValidationResult",
    "PluginConfig",
    "PluginCapabilities",
    
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginRegistrationError",
    "PluginInitError",
    "PluginStartError",
    "PluginStopError",
    "PluginPermissionError",
    "PluginVersionError", 
    "PluginConfigError",
    "PluginDependencyError",
    "PluginSecurityError",
    "PluginDiscoveryError",
    
    # Metadata and context
    "PluginMetadata",
    "Version",
    "Author", 
    "PluginContext",
    
    # Discovery
    "discover_plugins",
    "discover_entry_points_only",
    "discover_namespace_only",
    "validate_plugin_requirements",
    "create_plugin_factory",
    
    # Observability
    "PluginObservabilityHooks",
    "ObservabilityCollector",
    "LoggingObservabilityCollector",
    "MetricsCollector",
]

# Optional FastAPI router plugin interface (only if fastapi available)
try:
    from .interfaces import IRouterPlugin as _IRouterPlugin
    __all__.append("IRouterPlugin")
except ImportError:
    pass

# Optional signing and security (only if cryptography available)
try:
    from .signing import (
        PluginSignatureVerifier,
        PluginSigner,
        generate_key_pair,
        create_self_signed_certificate,
    )
    __all__.extend([
        "PluginSignatureVerifier",
        "PluginSigner", 
        "generate_key_pair",
        "create_self_signed_certificate",
    ])
except ImportError:
    pass

# Optional sandboxing (policy declaration)
try:
    from .sandbox import (
        PluginSandbox,
        SecurityPolicy,
        SecurityLevel,
        ResourceLimits,
        ExecutionContext,
        UNRESTRICTED_POLICY,
        STRICT_POLICY,
    )
    __all__.extend([
        "PluginSandbox",
        "SecurityPolicy",
        "SecurityLevel", 
        "ResourceLimits",
        "ExecutionContext",
        "UNRESTRICTED_POLICY",
        "STRICT_POLICY",
    ])
except ImportError:
    pass


# Convenience functions for common patterns

def create_registry_with_discovery(
    entry_point_group: str = "dotmac.plugins",
    namespace: str = "dotmac_plugins",
    enable_observability: bool = True,
) -> PluginRegistry:
    """
    Create registry and load plugins from discovery.
    
    Args:
        entry_point_group: Entry point group to discover
        namespace: Namespace to discover
        enable_observability: Whether to enable observability hooks
        
    Returns:
        Configured PluginRegistry with discovered plugins
    """
    hooks = PluginObservabilityHooks() if enable_observability else None
    registry = PluginRegistry(observability_hooks=hooks)
    
    # Load plugins
    try:
        count = registry.load(entry_point_group)
        if count == 0:
            # Try namespace discovery as fallback
            from .discovery import PluginDiscovery
            discovery = PluginDiscovery()
            try:
                plugins = discovery.discover_namespace_packages(namespace)
                for plugin in plugins:
                    registry.register(plugin)
            except Exception:
                pass  # Fallback discovery failed, continue with empty registry
    except Exception:
        pass  # Discovery failed, continue with empty registry
    
    return registry


def create_lifecycle_manager(
    entry_point_group: str = "dotmac.plugins", 
    namespace: str = "dotmac_plugins",
    enable_observability: bool = True,
) -> PluginLifecycleManager:
    """
    Create lifecycle manager and load plugins from discovery.
    
    Args:
        entry_point_group: Entry point group to discover
        namespace: Namespace to discover  
        enable_observability: Whether to enable observability hooks
        
    Returns:
        Configured PluginLifecycleManager with discovered plugins
    """
    registry = create_registry_with_discovery(
        entry_point_group, namespace, enable_observability
    )
    return PluginLifecycleManager(registry=registry)


def create_plugin_context(
    tenant_id: str = None,
    environment: str = "production",
    permissions: list = None,
    services: dict = None,
    config: dict = None,
) -> PluginContext:
    """
    Create plugin context with common defaults.
    
    Args:
        tenant_id: Optional tenant identifier
        environment: Environment name
        permissions: List of permissions to grant
        services: Dictionary of services to register
        config: Plugin configuration dictionary
        
    Returns:
        Configured PluginContext
    """
    import logging
    
    # Default services
    default_services = {
        "logger": logging.getLogger("dotmac.plugins.context"),
    }
    
    if services:
        default_services.update(services)
    
    return PluginContext(
        tenant_id=tenant_id,
        environment=environment,
        services=default_services,
        config=config or {},
        permissions=set(permissions or []),
    )