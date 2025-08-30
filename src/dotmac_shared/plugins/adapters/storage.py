"""
Storage domain adapter for the plugin system.

Provides specialized interfaces and utilities for storage plugins
like file storage, databases, caching, and cloud storage.
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, BinaryIO, Dict, List, Optional, Union

from ..core.exceptions import PluginError, PluginExecutionError
from ..core.plugin_base import BasePlugin, PluginMetadata


class StorageType(Enum):
    """Storage types."""

    FILE = "file"
    DATABASE = "database"
    CACHE = "cache"
    OBJECT = "object"
    BLOCK = "block"


class AccessMode(Enum):
    """File access modes."""

    READ = "read"
    WRITE = "write"
    APPEND = "append"
    READ_WRITE = "read_write"


@dataclass
class StorageObject:
    """Universal storage object representation."""

    key: str
    content: Union[bytes, str]
    content_type: Optional[str] = None
    metadata: Dict[str, Any] = None
    size: Optional[int] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    checksum: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

        # Calculate size if not provided
        if self.size is None:
            if isinstance(self.content, (bytes, str)):
                self.size = len(self.content)

        # Calculate checksum if not provided
        if self.checksum is None and isinstance(self.content, bytes):
            self.checksum = hashlib.sha256(self.content).hexdigest()


@dataclass
class StorageInfo:
    """Storage information and metadata."""

    key: str
    size: int
    content_type: Optional[str] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = None
    exists: bool = True

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StorageResult:
    """Storage operation result."""

    success: bool
    key: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ListResult:
    """Storage listing result."""

    objects: List[StorageInfo]
    has_more: bool = False
    next_token: Optional[str] = None
    total_count: Optional[int] = None


class StoragePlugin(BasePlugin):
    """
    Base class for storage plugins.

    Provides common interface for all storage backends.
    """

    @abstractmethod
    async def put(
        self, key: str, content: Union[bytes, str], **kwargs
    ) -> StorageResult:
        """
        Store content at the specified key.

        Args:
            key: Storage key/path
            content: Content to store
            **kwargs: Additional storage options

        Returns:
            Storage result
        """
        pass

    @abstractmethod
    async def get(self, key: str, **kwargs) -> Optional[StorageObject]:
        """
        Retrieve content from the specified key.

        Args:
            key: Storage key/path
            **kwargs: Additional retrieval options

        Returns:
            Storage object or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, key: str, **kwargs) -> StorageResult:
        """
        Delete content at the specified key.

        Args:
            key: Storage key/path
            **kwargs: Additional deletion options

        Returns:
            Storage result
        """
        pass

    @abstractmethod
    async def exists(self, key: str, **kwargs) -> bool:
        """
        Check if content exists at the specified key.

        Args:
            key: Storage key/path
            **kwargs: Additional check options

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    async def list(self, prefix: str = "", **kwargs) -> ListResult:
        """
        List objects with optional prefix filter.

        Args:
            prefix: Key prefix to filter by
            **kwargs: Additional listing options

        Returns:
            List result
        """
        pass

    async def get_info(self, key: str, **kwargs) -> Optional[StorageInfo]:
        """
        Get information about stored object.

        Args:
            key: Storage key/path
            **kwargs: Additional info options

        Returns:
            Storage info or None if not found
        """
        # Default implementation tries to get the object
        obj = await self.get(key, **kwargs)
        if obj is None:
            return None

        return StorageInfo(
            key=obj.key,
            size=obj.size or 0,
            content_type=obj.content_type,
            created_at=obj.created_at,
            modified_at=obj.modified_at,
            checksum=obj.checksum,
            metadata=obj.metadata,
        )

    async def copy(self, source_key: str, dest_key: str, **kwargs) -> StorageResult:
        """
        Copy object from source to destination.

        Args:
            source_key: Source key/path
            dest_key: Destination key/path
            **kwargs: Additional copy options

        Returns:
            Storage result
        """
        # Default implementation gets and puts
        obj = await self.get(source_key)
        if obj is None:
            return StorageResult(
                success=False, error_message=f"Source object not found: {source_key}"
            )

        return await self.put(dest_key, obj.content, **kwargs)

    async def move(self, source_key: str, dest_key: str, **kwargs) -> StorageResult:
        """
        Move object from source to destination.

        Args:
            source_key: Source key/path
            dest_key: Destination key/path
            **kwargs: Additional move options

        Returns:
            Storage result
        """
        # Default implementation copies and deletes
        copy_result = await self.copy(source_key, dest_key, **kwargs)
        if not copy_result.success:
            return copy_result

        delete_result = await self.delete(source_key, **kwargs)
        if not delete_result.success:
            # Try to clean up the copy
            await self.delete(dest_key, **kwargs)
            return delete_result

        return copy_result

    def get_storage_type(self) -> StorageType:
        """Get the storage type supported by this plugin."""
        return StorageType.FILE  # Override in subclasses

    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations."""
        return ["put", "get", "delete", "exists", "list"]  # Override to specify

    def get_storage_limits(self) -> Dict[str, Any]:
        """Get storage limits and constraints."""
        return {}  # Override to specify limits


class StorageAdapter:
    """
    Domain adapter for storage plugins.

    Provides high-level interface for managing storage plugins
    and routing operations to appropriate backends.
    """

    def __init__(self):
        self._plugins: Dict[str, StoragePlugin] = {}
        self._default_backend: Optional[str] = None
        self._routing_rules: List[Dict[str, Any]] = []
        self._logger = logging.getLogger("plugins.storage_adapter")

    def register_plugin(self, plugin_name: str, plugin: StoragePlugin) -> None:
        """Register a storage plugin."""
        if not isinstance(plugin, StoragePlugin):
            raise PluginError(f"Plugin {plugin_name} is not a StoragePlugin")

        self._plugins[plugin_name] = plugin

        # Set as default if none set
        if self._default_backend is None:
            self._default_backend = plugin_name

        self._logger.info(f"Registered storage plugin: {plugin_name}")

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a storage plugin."""
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]

            # Update default backend if necessary
            if self._default_backend == plugin_name:
                self._default_backend = next(iter(self._plugins.keys()), None)

            self._logger.info(f"Unregistered storage plugin: {plugin_name}")

    def set_default_backend(self, plugin_name: str) -> None:
        """Set the default storage backend."""
        if plugin_name not in self._plugins:
            raise PluginError(f"Plugin {plugin_name} is not registered")

        self._default_backend = plugin_name
        self._logger.info(f"Set default storage backend: {plugin_name}")

    def add_routing_rule(self, rule: Dict[str, Any], priority: int = 100) -> None:
        """
        Add routing rule for storage operations.

        Args:
            rule: Routing rule configuration
            priority: Rule priority (lower = higher priority)
        """
        rule["priority"] = priority
        self._routing_rules.append(rule)
        self._routing_rules.sort(key=lambda r: r["priority"])

        self._logger.info(f"Added storage routing rule: {rule}")

    def _select_backend(self, key: str, operation: str) -> str:
        """Select appropriate backend based on routing rules."""

        # Apply routing rules in priority order
        for rule in self._routing_rules:
            if self._matches_rule(key, operation, rule):
                backend = rule.get("backend")
                if backend and backend in self._plugins:
                    return backend

        # Use default backend
        if self._default_backend and self._default_backend in self._plugins:
            return self._default_backend

        # Use any available backend
        if self._plugins:
            return next(iter(self._plugins.keys()))

        raise PluginError("No storage backends available")

    def _matches_rule(self, key: str, operation: str, rule: Dict[str, Any]) -> bool:
        """Check if key and operation match routing rule."""

        # Check key pattern
        if "key_pattern" in rule:
            import re

            if not re.match(rule["key_pattern"], key):
                return False

        # Check key prefix
        if "key_prefix" in rule:
            if not key.startswith(rule["key_prefix"]):
                return False

        # Check operation
        if "operations" in rule:
            if operation not in rule["operations"]:
                return False

        # Check file size (for put operations)
        if "max_size" in rule and operation == "put":
            # Would need to check content size, but not available here
            pass

        return True

    async def put(
        self,
        key: str,
        content: Union[bytes, str],
        backend: Optional[str] = None,
        **kwargs,
    ) -> StorageResult:
        """
        Store content at the specified key.

        Args:
            key: Storage key/path
            content: Content to store
            backend: Specific backend to use
            **kwargs: Additional storage options

        Returns:
            Storage result
        """
        if backend is None:
            backend = self._select_backend(key, "put")

        if backend not in self._plugins:
            raise PluginError(f"Storage backend {backend} not found")

        plugin = self._plugins[backend]

        try:
            result = await plugin.put(key, content, **kwargs)
            self._logger.debug(
                f"Stored {len(content) if hasattr(content, '__len__') else '?'} bytes at {key} using {backend}"
            )
            return result
        except Exception as e:
            self._logger.error(f"Error storing {key} with backend {backend}: {e}")
            raise PluginExecutionError(
                plugin.name,
                "put",
                original_error=e,
                execution_context={"key": key, "backend": backend},
            ) from e

    async def get(
        self, key: str, backend: Optional[str] = None, **kwargs
    ) -> Optional[StorageObject]:
        """
        Retrieve content from the specified key.

        Args:
            key: Storage key/path
            backend: Specific backend to use
            **kwargs: Additional retrieval options

        Returns:
            Storage object or None if not found
        """
        if backend is None:
            backend = self._select_backend(key, "get")

        if backend not in self._plugins:
            raise PluginError(f"Storage backend {backend} not found")

        plugin = self._plugins[backend]

        try:
            obj = await plugin.get(key, **kwargs)
            if obj:
                self._logger.debug(
                    f"Retrieved {obj.size or '?'} bytes from {key} using {backend}"
                )
            return obj
        except Exception as e:
            self._logger.error(f"Error retrieving {key} with backend {backend}: {e}")
            raise PluginExecutionError(
                plugin.name,
                "get",
                original_error=e,
                execution_context={"key": key, "backend": backend},
            ) from e

    async def delete(
        self, key: str, backend: Optional[str] = None, **kwargs
    ) -> StorageResult:
        """
        Delete content at the specified key.

        Args:
            key: Storage key/path
            backend: Specific backend to use
            **kwargs: Additional deletion options

        Returns:
            Storage result
        """
        if backend is None:
            backend = self._select_backend(key, "delete")

        if backend not in self._plugins:
            raise PluginError(f"Storage backend {backend} not found")

        plugin = self._plugins[backend]

        try:
            result = await plugin.delete(key, **kwargs)
            self._logger.debug(f"Deleted {key} using {backend}")
            return result
        except Exception as e:
            self._logger.error(f"Error deleting {key} with backend {backend}: {e}")
            raise PluginExecutionError(
                plugin.name,
                "delete",
                original_error=e,
                execution_context={"key": key, "backend": backend},
            ) from e

    async def exists(self, key: str, backend: Optional[str] = None, **kwargs) -> bool:
        """
        Check if content exists at the specified key.

        Args:
            key: Storage key/path
            backend: Specific backend to use
            **kwargs: Additional check options

        Returns:
            True if exists
        """
        if backend is None:
            backend = self._select_backend(key, "exists")

        if backend not in self._plugins:
            raise PluginError(f"Storage backend {backend} not found")

        plugin = self._plugins[backend]

        try:
            exists = await plugin.exists(key, **kwargs)
            return exists
        except Exception as e:
            self._logger.error(
                f"Error checking existence of {key} with backend {backend}: {e}"
            )
            raise PluginExecutionError(
                plugin.name,
                "exists",
                original_error=e,
                execution_context={"key": key, "backend": backend},
            ) from e

    async def list(
        self, prefix: str = "", backend: Optional[str] = None, **kwargs
    ) -> ListResult:
        """
        List objects with optional prefix filter.

        Args:
            prefix: Key prefix to filter by
            backend: Specific backend to use
            **kwargs: Additional listing options

        Returns:
            List result
        """
        if backend is None:
            backend = self._select_backend(prefix, "list")

        if backend not in self._plugins:
            raise PluginError(f"Storage backend {backend} not found")

        plugin = self._plugins[backend]

        try:
            result = await plugin.list(prefix, **kwargs)
            self._logger.debug(
                f"Listed {len(result.objects)} objects with prefix '{prefix}' using {backend}"
            )
            return result
        except Exception as e:
            self._logger.error(
                f"Error listing with prefix '{prefix}' using backend {backend}: {e}"
            )
            raise PluginExecutionError(
                plugin.name,
                "list",
                original_error=e,
                execution_context={"prefix": prefix, "backend": backend},
            ) from e

    async def get_info(
        self, key: str, backend: Optional[str] = None, **kwargs
    ) -> Optional[StorageInfo]:
        """Get information about stored object."""
        if backend is None:
            backend = self._select_backend(key, "get_info")

        if backend not in self._plugins:
            raise PluginError(f"Storage backend {backend} not found")

        plugin = self._plugins[backend]

        try:
            return await plugin.get_info(key, **kwargs)
        except Exception as e:
            self._logger.error(
                f"Error getting info for {key} with backend {backend}: {e}"
            )
            raise PluginExecutionError(
                plugin.name,
                "get_info",
                original_error=e,
                execution_context={"key": key, "backend": backend},
            ) from e

    async def copy(
        self,
        source_key: str,
        dest_key: str,
        source_backend: Optional[str] = None,
        dest_backend: Optional[str] = None,
        **kwargs,
    ) -> StorageResult:
        """Copy object between keys and optionally between backends."""
        if source_backend is None:
            source_backend = self._select_backend(source_key, "get")

        if dest_backend is None:
            dest_backend = self._select_backend(dest_key, "put")

        # Same backend copy
        if source_backend == dest_backend:
            plugin = self._plugins[source_backend]
            return await plugin.copy(source_key, dest_key, **kwargs)

        # Cross-backend copy
        obj = await self.get(source_key, source_backend)
        if obj is None:
            return StorageResult(
                success=False, error_message=f"Source object not found: {source_key}"
            )

        return await self.put(dest_key, obj.content, dest_backend, **kwargs)

    async def move(
        self,
        source_key: str,
        dest_key: str,
        source_backend: Optional[str] = None,
        dest_backend: Optional[str] = None,
        **kwargs,
    ) -> StorageResult:
        """Move object between keys and optionally between backends."""
        copy_result = await self.copy(
            source_key, dest_key, source_backend, dest_backend, **kwargs
        )
        if not copy_result.success:
            return copy_result

        delete_backend = source_backend or self._select_backend(source_key, "delete")
        delete_result = await self.delete(source_key, delete_backend, **kwargs)

        if not delete_result.success:
            # Try to clean up the copy
            dest_backend = dest_backend or self._select_backend(dest_key, "delete")
            await self.delete(dest_key, dest_backend, **kwargs)
            return delete_result

        return copy_result

    def get_available_backends(self) -> List[str]:
        """Get list of available storage backends."""
        return list(self._plugins.keys())

    def get_backend_info(self, backend_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a storage backend."""
        if backend_name not in self._plugins:
            return None

        plugin = self._plugins[backend_name]

        return {
            "name": backend_name,
            "domain": plugin.domain,
            "version": plugin.version,
            "status": plugin.status.value,
            "storage_type": plugin.get_storage_type().value,
            "supported_operations": plugin.get_supported_operations(),
            "storage_limits": plugin.get_storage_limits(),
            "is_active": plugin.is_active,
            "is_healthy": plugin.is_healthy,
        }

    def get_routing_config(self) -> Dict[str, Any]:
        """Get current storage routing configuration."""
        return {
            "default_backend": self._default_backend,
            "routing_rules": self._routing_rules,
            "available_backends": list(self._plugins.keys()),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all storage backends."""
        health_results = {}

        for backend_name, plugin in self._plugins.items():
            try:
                health_data = await plugin.health_check()
                health_results[backend_name] = health_data
            except Exception as e:
                health_results[backend_name] = {"healthy": False, "error": str(e)}

        total_backends = len(self._plugins)
        healthy_backends = sum(
            1 for result in health_results.values() if result.get("healthy", False)
        )

        return {
            "total_backends": total_backends,
            "healthy_backends": healthy_backends,
            "health_percentage": (healthy_backends / max(1, total_backends)) * 100,
            "backend_health": health_results,
        }

    @staticmethod
    def create_file_routing_rule(
        file_pattern: str, backend: str, priority: int = 100
    ) -> Dict[str, Any]:
        """Create a routing rule for file patterns."""
        return {
            "key_pattern": file_pattern,
            "backend": backend,
            "priority": priority,
            "operations": ["put", "get", "delete", "exists"],
        }

    @staticmethod
    def create_size_routing_rule(
        max_size: int, backend: str, priority: int = 100
    ) -> Dict[str, Any]:
        """Create a routing rule based on file size."""
        return {
            "max_size": max_size,
            "backend": backend,
            "priority": priority,
            "operations": ["put"],
        }

    @staticmethod
    def create_prefix_routing_rule(
        prefix: str, backend: str, priority: int = 100
    ) -> Dict[str, Any]:
        """Create a routing rule for key prefixes."""
        return {
            "key_prefix": prefix,
            "backend": backend,
            "priority": priority,
            "operations": ["put", "get", "delete", "exists", "list"],
        }
