"""Caching middleware for automatic response caching and cache warming."""

import hashlib
import json
import logging
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from dotmac_isp.shared.cache import get_cache_manager, cache_get, cache_set

logger = logging.getLogger(__name__)


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic HTTP response caching."""

    def __init__(
        self,
        app,
        default_ttl: int = 300,  # 5 minutes
        cache_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        cache_private: bool = False,
    ):
        super().__init__(app)
        self.default_ttl = default_ttl
        self.cache_patterns = cache_patterns or ["/api/v1/"]
        self.exclude_patterns = exclude_patterns or [
            "/auth/",
            "/logout",
            "/upload",
            "/payment",
        ]
        self.cache_private = cache_private
        self.cache_manager = get_cache_manager()

    def _should_cache_request(self, request: Request) -> bool:
        """Determine if request should be cached."""
        # Only cache GET requests
        if request.method != "GET":
            return False

        path = str(request.url.path)

        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if pattern in path:
                return False

        # Check if path matches cache patterns
        for pattern in self.cache_patterns:
            if pattern in path:
                return True

        return False

    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        # Include path, query params, and tenant info
        path = str(request.url.path)
        query = str(request.url.query) if request.url.query else ""

        # Include tenant_id from headers or auth context
        tenant_id = request.headers.get("X-Tenant-ID", "default")

        # Create hash of the request components
        key_data = f"{path}:{query}:{tenant_id}"
        cache_key = hashlib.sha256(key_data.encode()).hexdigest()

        return f"response:{cache_key}"

    def _get_cache_ttl(self, request: Request) -> int:
        """Get TTL based on request path."""
        path = str(request.url.path)

        # Different TTLs for different types of data
        ttl_map = {
            "/api/v1/customers": 180,  # 3 minutes - customer data changes often
            "/api/v1/services": 300,  # 5 minutes - service plans don't change often
            "/api/v1/billing": 120,  # 2 minutes - billing data is sensitive
            "/api/v1/analytics": 600,  # 10 minutes - analytics can be cached longer
            "/api/v1/portal": 60,  # 1 minute - portal data should be fresh
            "/api/v1/inventory": 300,  # 5 minutes - inventory changes moderately
        }

        for pattern, ttl in ttl_map.items():
            if pattern in path:
                return ttl

        return self.default_ttl

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching logic."""

        # Check if we should cache this request
        if not self._should_cache_request(request):
            return await call_next(request)

        # Generate cache key
        cache_key = self._generate_cache_key(request)

        # Try to get from cache
        cached_response = self.cache_manager.get(cache_key, namespace="responses")

        if cached_response:
            logger.debug(f"Cache HIT for {request.url.path}")
            # Return cached response
            return JSONResponse(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={
                    **cached_response.get("headers", {}),
                    "X-Cache": "HIT",
                    "X-Cache-Key": cache_key[:16],  # Truncated for security
                },
            )

        # Cache miss - process request
        logger.debug(f"Cache MISS for {request.url.path}")
        response = await call_next(request)

        # Only cache successful responses
        if response.status_code == 200:
            # Get response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            try:
                # Parse JSON response
                content = json.loads(response_body.decode())

                # Prepare cache data
                cache_data = {
                    "content": content,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "cached_at": datetime.utcnow().isoformat(),
                }

                # Cache the response
                ttl = self._get_cache_ttl(request)
                self.cache_manager.set(
                    cache_key, cache_data, ttl, namespace="responses"
                )

                # Create new response with cache headers
                return JSONResponse(
                    content=content,
                    status_code=response.status_code,
                    headers={
                        **dict(response.headers),
                        "X-Cache": "MISS",
                        "X-Cache-TTL": str(ttl),
                    },
                )

            except (json.JSONDecodeError, UnicodeDecodeError):
                # If not JSON, return original response
                pass

        return response


class CacheWarmupService:
    """Service for warming up critical caches."""

    def __init__(self):
        """  Init   operation."""
        self.cache_manager = get_cache_manager()

    async def warm_customer_data(self, tenant_id: str):
        """Warm up frequently accessed customer data."""
        try:
            # Import here to avoid circular imports
            from dotmac_isp.modules.identity.service import CustomerService
            from dotmac_isp.core.database import get_async_db

            async for db in get_async_db():
                service = CustomerService(db, tenant_id)

                # Cache customer count
                customer_count = await service.get_customer_count()
                cache_set(f"customer_count:{tenant_id}", customer_count, 300, "stats")

                # Cache recent customers
                recent_customers = await service.get_recent_customers(limit=50)
                cache_set(
                    f"recent_customers:{tenant_id}", recent_customers, 180, "customers"
                )

                logger.info(f"Warmed customer cache for tenant {tenant_id}")
                break

        except Exception as e:
            logger.error(f"Failed to warm customer cache for {tenant_id}: {e}")

    async def warm_service_catalog(self, tenant_id: str):
        """Warm up service catalog data."""
        try:
            from dotmac_isp.modules.services.service import ServiceCatalogService
            from dotmac_isp.core.database import get_async_db

            async for db in get_async_db():
                service = ServiceCatalogService(db, tenant_id)

                # Cache active service plans
                active_plans = await service.get_active_service_plans()
                cache_set(f"active_plans:{tenant_id}", active_plans, 600, "services")

                # Cache service categories
                categories = await service.get_service_categories()
                cache_set(
                    f"service_categories:{tenant_id}", categories, 1200, "services"
                )

                logger.info(f"Warmed service catalog cache for tenant {tenant_id}")
                break

        except Exception as e:
            logger.error(f"Failed to warm service catalog cache for {tenant_id}: {e}")

    async def warm_analytics_data(self, tenant_id: str):
        """Warm up analytics dashboards."""
        try:
            from dotmac_isp.modules.analytics.service import AnalyticsService
            from dotmac_isp.core.database import get_async_db

            async for db in get_async_db():
                service = AnalyticsService(db, tenant_id)

                # Cache dashboard overview
                overview = await service.get_dashboard_overview()
                cache_set(f"dashboard_overview:{tenant_id}", overview, 300, "analytics")

                # Cache key metrics
                metrics = await service.get_key_metrics()
                cache_set(f"key_metrics:{tenant_id}", metrics, 600, "analytics")

                logger.info(f"Warmed analytics cache for tenant {tenant_id}")
                break

        except Exception as e:
            logger.error(f"Failed to warm analytics cache for {tenant_id}: {e}")


# Cache invalidation helpers
class CacheInvalidator:
    """Helper class for intelligent cache invalidation."""

    def __init__(self):
        """  Init   operation."""
        self.cache_manager = get_cache_manager()

    def invalidate_customer_caches(self, tenant_id: str, customer_id: str = None):
        """Invalidate customer-related caches."""
        tags = [f"customer:{tenant_id}"]
        if customer_id:
            tags.append(f"customer:{tenant_id}:{customer_id}")

        for tag in tags:
            count = self.cache_manager.invalidate_by_tag(tag, "customers")
            logger.info(f"Invalidated {count} cache entries for tag {tag}")

    def invalidate_service_caches(self, tenant_id: str):
        """Invalidate service-related caches."""
        count = self.cache_manager.invalidate_by_tag(
            f"services:{tenant_id}", "services"
        )
        logger.info(f"Invalidated {count} service cache entries for tenant {tenant_id}")

    def invalidate_billing_caches(self, tenant_id: str, customer_id: str = None):
        """Invalidate billing-related caches."""
        tags = [f"billing:{tenant_id}"]
        if customer_id:
            tags.append(f"billing:{tenant_id}:{customer_id}")

        for tag in tags:
            count = self.cache_manager.invalidate_by_tag(tag, "billing")
            logger.info(f"Invalidated {count} billing cache entries for tag {tag}")


# Global instances
cache_warmup_service = CacheWarmupService()
cache_invalidator = CacheInvalidator()
