"""
Cache Provider Interface
Abstract interface for cache providers (Redis, Memcached, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CacheConfig:
    """Cache service configuration"""

    name: str
    password: Optional[str] = None
    max_memory: str = "256mb"
    persistence: bool = True
    version: str = "latest"
    port: int = 6379
    configuration: dict[str, Any] = None

    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}


@dataclass
class CacheConnectionInfo:
    """Cache connection information"""

    host: str
    port: int
    password: Optional[str] = None
    connection_url: str = ""
    ssl: bool = False


class ICacheProvider(ABC):
    """
    Abstract interface for cache providers.
    Handles cache service provisioning and management.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the cache provider"""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health"""
        pass

    @abstractmethod
    async def create_cache_service(self, config: CacheConfig) -> dict[str, Any]:
        """Create a new cache service"""
        pass

    @abstractmethod
    async def get_connection_info(self, service_name: str) -> CacheConnectionInfo:
        """Get cache connection information"""
        pass

    @abstractmethod
    async def get_cache_status(self, service_name: str) -> dict[str, Any]:
        """Get cache service status"""
        pass

    @abstractmethod
    async def get_cache_metrics(self, service_name: str) -> dict[str, Any]:
        """Get cache performance metrics"""
        pass

    @abstractmethod
    async def flush_cache(self, service_name: str) -> bool:
        """Flush all cache data"""
        pass

    @abstractmethod
    async def backup_cache(self, service_name: str) -> dict[str, Any]:
        """Create cache backup"""
        pass

    @abstractmethod
    async def restore_cache(self, service_name: str, backup_id: str) -> bool:
        """Restore cache from backup"""
        pass

    @abstractmethod
    async def scale_cache(self, service_name: str, memory_limit: str) -> bool:
        """Scale cache memory allocation"""
        pass

    @abstractmethod
    async def remove_cache_service(self, service_name: str) -> bool:
        """Remove cache service"""
        pass

    @abstractmethod
    def get_supported_cache_types(self) -> list[str]:
        """Get supported cache types (redis, memcached, etc.)"""
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """Cleanup provider resources"""
        pass
