"""
Plugin context and environment management.

Provides runtime context for plugins including tenant information, services,
configuration, and permission management for secure plugin execution.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set, Union, Callable, Awaitable

from .types import PluginPermissionError, PluginConfig


@dataclass
class PluginContext:
    """
    Runtime context provided to plugins during initialization.
    
    Contains all the services, configuration, and permissions that a plugin
    needs to operate within the host application environment.
    """
    
    # Tenant and environment information
    tenant_id: Optional[str] = None
    environment: str = "production"
    
    # Core services
    services: Dict[str, Any] = field(default_factory=dict)
    
    # Plugin configuration
    config: PluginConfig = field(default_factory=dict)
    
    # Security and permissions
    permissions: Set[str] = field(default_factory=set)
    
    # Additional context data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Initialize default services if not provided."""
        # Ensure logger is available
        if 'logger' not in self.services:
            self.services['logger'] = logging.getLogger(f"dotmac.plugins.context")
        
        # Ensure permissions is a set
        if isinstance(self.permissions, (list, tuple)):
            self.permissions = set(self.permissions)
    
    # Service access methods
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Get logger instance for plugin use.
        
        Args:
            name: Optional logger name (defaults to plugin context logger)
            
        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(name)
        
        return self.services.get('logger', logging.getLogger("dotmac.plugins"))
    
    def get_secrets_manager(self) -> Optional[Any]:
        """
        Get secrets manager service.
        
        Returns:
            Secrets manager instance or None if not available
        """
        return self.services.get('secrets')
    
    def get_database_factory(self) -> Optional[Callable]:
        """
        Get database session factory.
        
        Returns:
            Database session factory or None if not available
        """
        return self.services.get('db_factory')
    
    def get_metrics_collector(self) -> Optional[Any]:
        """
        Get metrics collector service.
        
        Returns:
            Metrics collector instance or None if not available
        """
        return self.services.get('metrics')
    
    def get_event_bus(self) -> Optional[Any]:
        """
        Get event bus service for publishing events.
        
        Returns:
            Event bus instance or None if not available
        """
        return self.services.get('event_bus')
    
    def get_cache(self) -> Optional[Any]:
        """
        Get cache service (Redis, etc.).
        
        Returns:
            Cache instance or None if not available
        """
        return self.services.get('cache')
    
    # Configuration access methods
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Supports nested key access using dot notation (e.g., "database.host").
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if '.' not in key:
            return self.config.get(key, default)
        
        # Handle nested keys
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set configuration value by key.
        
        Supports nested key creation using dot notation.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        if '.' not in key:
            self.config[key] = value
            return
        
        # Handle nested keys
        keys = key.split('.')
        current = self.config
        
        # Create nested structure
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_required_config(self, key: str) -> Any:
        """
        Get required configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value
            
        Raises:
            KeyError: If required configuration is missing
        """
        value = self.get_config_value(key)
        if value is None:
            raise KeyError(f"Required configuration '{key}' not found")
        return value
    
    # Permission management methods
    def has_permission(self, permission: str) -> bool:
        """
        Check if context has specific permission.
        
        Args:
            permission: Permission string to check
            
        Returns:
            True if permission is granted
        """
        if not permission:
            return True
        
        # Check exact match
        if permission in self.permissions:
            return True
        
        # Check wildcard permissions (e.g., "export:*" matches "export:csv")
        for perm in self.permissions:
            if self._permission_matches(perm, permission):
                return True
        
        return False
    
    def require_permission(self, permission: str) -> None:
        """
        Require specific permission, raising exception if not granted.
        
        Args:
            permission: Permission string to require
            
        Raises:
            PluginPermissionError: If permission is not granted
        """
        if not self.has_permission(permission):
            raise PluginPermissionError(
                f"Permission '{permission}' required but not granted. "
                f"Available permissions: {', '.join(sorted(self.permissions))}"
            )
    
    def _permission_matches(self, granted_permission: str, required_permission: str) -> bool:
        """
        Check if granted permission matches required permission.
        
        Supports wildcard matching (e.g., "export:*" matches "export:csv").
        
        Args:
            granted_permission: Permission that was granted
            required_permission: Permission that is required
            
        Returns:
            True if permissions match
        """
        # Exact match
        if granted_permission == required_permission:
            return True
        
        # Wildcard match
        if granted_permission.endswith(':*'):
            prefix = granted_permission[:-2]  # Remove ':*'
            return required_permission.startswith(prefix + ':')
        
        return False
    
    def add_permission(self, permission: str) -> None:
        """
        Add permission to context.
        
        Args:
            permission: Permission to add
        """
        self.permissions.add(permission)
    
    def remove_permission(self, permission: str) -> None:
        """
        Remove permission from context.
        
        Args:
            permission: Permission to remove
        """
        self.permissions.discard(permission)
    
    # Service registration methods (for host applications)
    def register_service(self, name: str, service: Any) -> None:
        """
        Register service in context.
        
        Args:
            name: Service name
            service: Service instance
        """
        self.services[name] = service
    
    def unregister_service(self, name: str) -> None:
        """
        Unregister service from context.
        
        Args:
            name: Service name to remove
        """
        self.services.pop(name, None)
    
    def has_service(self, name: str) -> bool:
        """
        Check if service is available.
        
        Args:
            name: Service name to check
            
        Returns:
            True if service is registered
        """
        return name in self.services
    
    def get_service(self, name: str, default: Any = None) -> Any:
        """
        Get service by name.
        
        Args:
            name: Service name
            default: Default value if service not found
            
        Returns:
            Service instance or default
        """
        return self.services.get(name, default)
    
    def require_service(self, name: str) -> Any:
        """
        Get required service, raising exception if not available.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not available
        """
        if name not in self.services:
            raise KeyError(f"Required service '{name}' not available")
        return self.services[name]
    
    # Environment and tenant methods
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ('development', 'dev', 'local')
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ('production', 'prod')
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment.lower() in ('staging', 'stage')
    
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.environment.lower() in ('test', 'testing')
    
    def has_tenant(self) -> bool:
        """Check if tenant context is available."""
        return self.tenant_id is not None
    
    def require_tenant(self) -> str:
        """
        Get tenant ID, raising exception if not available.
        
        Returns:
            Tenant ID
            
        Raises:
            ValueError: If no tenant context is available
        """
        if self.tenant_id is None:
            raise ValueError("Tenant context required but not available")
        return self.tenant_id
    
    # Metadata methods
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def has_metadata(self, key: str) -> bool:
        """Check if metadata key exists."""
        return key in self.metadata
    
    # Context validation
    def validate(self) -> list[str]:
        """
        Validate context completeness.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required services
        required_services = ['logger']
        for service in required_services:
            if not self.has_service(service):
                errors.append(f"Required service '{service}' not available")
        
        # Check environment
        if not self.environment:
            errors.append("Environment not specified")
        
        return errors
    
    def clone(self, **overrides: Any) -> "PluginContext":
        """
        Create a copy of this context with optional overrides.
        
        Args:
            **overrides: Fields to override in the clone
            
        Returns:
            New PluginContext instance
        """
        clone_data = {
            'tenant_id': self.tenant_id,
            'environment': self.environment,
            'services': self.services.copy(),
            'config': self.config.copy(),
            'permissions': self.permissions.copy(),
            'metadata': self.metadata.copy(),
        }
        
        clone_data.update(overrides)
        return PluginContext(**clone_data)
    
    def __repr__(self) -> str:
        """String representation of context."""
        return (
            f"PluginContext("
            f"tenant_id={self.tenant_id!r}, "
            f"environment={self.environment!r}, "
            f"services={list(self.services.keys())}, "
            f"permissions={len(self.permissions)} perms, "
            f"config_keys={list(self.config.keys())}"
            f")"
        )