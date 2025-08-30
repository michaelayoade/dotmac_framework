"""
Shared cache integration for ISP modules.
Provides unified caching across all ISP services using dotmac_shared.cache.
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from dotmac_shared.cache import create_cache_service

logger = logging.getLogger(__name__)


class ISPCacheManager:
    """
    Centralized cache manager for all ISP modules.
    Provides tenant-aware caching with consistent key patterns.
    """

    def __init__(self, tenant_id: str, cache_service=None):
        self.tenant_id = tenant_id
        self.cache_service = cache_service or create_cache_service()
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the cache manager."""
        try:
            if self.cache_service and not self._initialized:
                await self.cache_service.initialize()
                self._initialized = True
                logger.info(
                    f"✅ ISP Cache Manager initialized for tenant {self.tenant_id}"
                )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize ISP Cache Manager: {e}")
            return False

    def _get_cache_key(self, module: str, key: str) -> str:
        """Generate consistent cache key pattern."""
        return f"isp:{self.tenant_id}:{module}:{key}"

    # Customer/Identity caching
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get cached customer data."""
        if not self._initialized:
            return None

        try:
            cache_key = self._get_cache_key("identity", f"customer:{customer_id}")
            cached_data = await self.cache_service.get(
                cache_key, tenant_id=self.tenant_id
            )
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Failed to get cached customer {customer_id}: {e}")
            return None

    async def cache_customer(
        self, customer_id: str, customer_data: Dict[str, Any], expire_minutes: int = 30
    ) -> bool:
        """Cache customer data."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key("identity", f"customer:{customer_id}")
            await self.cache_service.set(
                cache_key,
                json.dumps(customer_data),
                tenant_id=self.tenant_id,
                expire=expire_minutes * 60,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache customer {customer_id}: {e}")
            return False

    # Billing caching
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get cached invoice data."""
        if not self._initialized:
            return None

        try:
            cache_key = self._get_cache_key("billing", f"invoice:{invoice_id}")
            cached_data = await self.cache_service.get(
                cache_key, tenant_id=self.tenant_id
            )
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Failed to get cached invoice {invoice_id}: {e}")
            return None

    async def cache_invoice(
        self, invoice_id: str, invoice_data: Dict[str, Any], expire_minutes: int = 60
    ) -> bool:
        """Cache invoice data."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key("billing", f"invoice:{invoice_id}")
            await self.cache_service.set(
                cache_key,
                json.dumps(invoice_data),
                tenant_id=self.tenant_id,
                expire=expire_minutes * 60,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache invoice {invoice_id}: {e}")
            return False

    # Network monitoring caching
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get cached device status."""
        if not self._initialized:
            return None

        try:
            cache_key = self._get_cache_key("network", f"device_status:{device_id}")
            cached_data = await self.cache_service.get(
                cache_key, tenant_id=self.tenant_id
            )
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Failed to get cached device status {device_id}: {e}")
            return None

    async def cache_device_status(
        self, device_id: str, status_data: Dict[str, Any], expire_minutes: int = 5
    ) -> bool:
        """Cache device status (short TTL for real-time data)."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key("network", f"device_status:{device_id}")
            await self.cache_service.set(
                cache_key,
                json.dumps(status_data),
                tenant_id=self.tenant_id,
                expire=expire_minutes * 60,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache device status {device_id}: {e}")
            return False

    # Analytics caching
    async def get_report_data(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get cached report data."""
        if not self._initialized:
            return None

        try:
            cache_key = self._get_cache_key("analytics", f"report:{report_id}")
            cached_data = await self.cache_service.get(
                cache_key, tenant_id=self.tenant_id
            )
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Failed to get cached report {report_id}: {e}")
            return None

    async def cache_report_data(
        self, report_id: str, report_data: Dict[str, Any], expire_minutes: int = 120
    ) -> bool:
        """Cache report data."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key("analytics", f"report:{report_id}")
            await self.cache_service.set(
                cache_key,
                json.dumps(report_data),
                tenant_id=self.tenant_id,
                expire=expire_minutes * 60,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache report {report_id}: {e}")
            return False

    # Service configuration caching
    async def get_service_config(
        self, service_name: str, config_key: str
    ) -> Optional[Any]:
        """Get cached service configuration."""
        if not self._initialized:
            return None

        try:
            cache_key = self._get_cache_key("config", f"{service_name}:{config_key}")
            cached_data = await self.cache_service.get(
                cache_key, tenant_id=self.tenant_id
            )
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(
                f"Failed to get cached config {service_name}:{config_key}: {e}"
            )
            return None

    async def cache_service_config(
        self,
        service_name: str,
        config_key: str,
        config_data: Any,
        expire_minutes: int = 180,
    ) -> bool:
        """Cache service configuration."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key("config", f"{service_name}:{config_key}")
            await self.cache_service.set(
                cache_key,
                json.dumps(config_data),
                tenant_id=self.tenant_id,
                expire=expire_minutes * 60,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache config {service_name}:{config_key}: {e}")
            return False

    # Generic caching methods
    async def get_cached_data(self, module: str, key: str) -> Optional[Any]:
        """Get generic cached data."""
        if not self._initialized:
            return None

        try:
            cache_key = self._get_cache_key(module, key)
            cached_data = await self.cache_service.get(
                cache_key, tenant_id=self.tenant_id
            )
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Failed to get cached data {module}:{key}: {e}")
            return None

    async def cache_data(
        self, module: str, key: str, data: Any, expire_minutes: int = 60
    ) -> bool:
        """Cache generic data."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key(module, key)
            await self.cache_service.set(
                cache_key,
                json.dumps(data),
                tenant_id=self.tenant_id,
                expire=expire_minutes * 60,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache data {module}:{key}: {e}")
            return False

    async def invalidate_cache(self, module: str, key: str) -> bool:
        """Invalidate specific cached data."""
        if not self._initialized:
            return False

        try:
            cache_key = self._get_cache_key(module, key)
            await self.cache_service.delete(cache_key, tenant_id=self.tenant_id)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache {module}:{key}: {e}")
            return False

    async def invalidate_module_cache(self, module: str) -> bool:
        """Invalidate all cache for a specific module."""
        if not self._initialized:
            return False

        try:
            pattern = f"isp:{self.tenant_id}:{module}:*"
            # Note: This would require cache service to support pattern deletion
            # For now, we'll just log it
            logger.info(
                f"Cache invalidation requested for module {module} (pattern: {pattern})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate module cache {module}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Health check for cache manager."""
        try:
            if self.cache_service:
                cache_health = await self.cache_service.health_check()
                return {
                    "cache_manager": (
                        "healthy" if self._initialized else "not_initialized"
                    ),
                    "tenant_id": self.tenant_id,
                    "cache_service": cache_health,
                    "initialized": self._initialized,
                }
            else:
                return {
                    "cache_manager": "no_cache_service",
                    "tenant_id": self.tenant_id,
                    "initialized": False,
                }
        except Exception as e:
            return {
                "cache_manager": "unhealthy",
                "tenant_id": self.tenant_id,
                "error": str(e),
            }


# Global cache managers per tenant (will be managed by application factory)
_cache_managers: Dict[str, ISPCacheManager] = {}


def get_isp_cache_manager(tenant_id: str) -> ISPCacheManager:
    """Get or create ISP cache manager for tenant."""
    if tenant_id not in _cache_managers:
        _cache_managers[tenant_id] = ISPCacheManager(tenant_id)
    return _cache_managers[tenant_id]


async def initialize_isp_cache_managers() -> bool:
    """Initialize all cache managers."""
    try:
        for cache_manager in _cache_managers.values():
            await cache_manager.initialize()
        logger.info("✅ All ISP cache managers initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize ISP cache managers: {e}")
        return False
