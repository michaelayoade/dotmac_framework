"""
License Enforcement Middleware
Enforces license limits in ISP Framework instances based on Management Platform contracts
"""

import time
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from dotmac.application.api.response import APIResponse
from dotmac.database.base import get_db_session
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class LicenseCheck(BaseModel):
    """License check result"""

    model_config = ConfigDict()

    allowed: bool
    remaining: Optional[int] = None
    limit: Optional[int] = None
    feature: str
    message: Optional[str] = None
    retry_after: Optional[int] = None


class LicenseEnforcementMiddleware:
    """FastAPI middleware for license enforcement in ISP instances"""

    def __init__(self, app):
        self.app = app
        self.license_cache = {}
        self.usage_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_sync = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip enforcement for system endpoints
        if self._is_system_endpoint(request.url.path):
            await self.app(scope, receive, send)
            return

        # Check license before processing request
        license_check = await self._check_license_for_request(request)

        if not license_check.allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=APIResponse(
                    success=False,
                    message=license_check.message or "License limit exceeded",
                    data={
                        "feature": license_check.feature,
                        "limit": license_check.limit,
                        "remaining": license_check.remaining,
                        "retry_after": license_check.retry_after,
                    },
                ).model_dump(),
            )
            await response(scope, receive, send)
            return

        # Process request normally
        await self.app(scope, receive, send)

        # Update usage after successful request
        await self._update_usage_tracking(request, license_check.feature)

    async def _check_license_for_request(self, request: Request) -> LicenseCheck:
        """Check if request is allowed based on license limits"""

        try:
            # Get tenant ID from request context
            tenant_id = await self._get_tenant_id(request)
            if not tenant_id:
                return LicenseCheck(allowed=True, feature="unknown")

            # Get current license
            license_contract = await self._get_license_contract(tenant_id)
            if not license_contract:
                # No license found - allow with warning
                logger.warning(f"No license found for tenant {tenant_id}")
                return LicenseCheck(allowed=True, feature="unknown")

            # Check if license is active and not expired
            if not self._is_license_active(license_contract):
                return LicenseCheck(
                    allowed=False,
                    feature="license_validity",
                    message="License has expired or is inactive",
                )

            # Determine what feature/limit to check based on endpoint
            feature_check = self._determine_feature_check(request.url.path, request.method)

            if not feature_check:
                return LicenseCheck(allowed=True, feature="unknown")

            # Check specific limit
            return await self._check_feature_limit(
                tenant_id,
                license_contract,
                feature_check["feature"],
                feature_check.get("increment", 1),
            )

        except Exception as e:
            logger.error(f"License check error: {e}")
            # Fail open - allow request but log error
            return LicenseCheck(allowed=True, feature="error")

    async def _get_license_contract(self, tenant_id: str) -> Optional[dict[str, Any]]:
        """Get license contract from cache or Management Platform"""

        cache_key = f"license:{tenant_id}"
        now = time.time()

        # Check cache
        if cache_key in self.license_cache:
            cached_data, cached_time = self.license_cache[cache_key]
            if now - cached_time < self.cache_ttl:
                return cached_data

        # Fetch from Management Platform
        try:
            management_url = self._get_management_platform_url()

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{management_url}/api/v1/licensing/contracts/by-tenant/{tenant_id}",
                    headers={
                        "Authorization": f"Bearer {await self._get_service_token()}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    contract_data = response.json()["data"]
                    self.license_cache[cache_key] = (contract_data, now)
                    return contract_data
                elif response.status_code == 404:
                    # No license found
                    self.license_cache[cache_key] = (None, now)
                    return None
                else:
                    logger.error(f"Failed to fetch license contract: {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching license contract: {e}")
            return None

    async def _check_feature_limit(
        self,
        tenant_id: str,
        license_contract: dict[str, Any],
        feature: str,
        increment: int = 1,
    ) -> LicenseCheck:
        """Check if feature usage is within limits"""

        try:
            # Get feature limit from license
            limit = self._get_feature_limit(license_contract, feature)
            if limit is None or limit == -1:  # -1 means unlimited
                return LicenseCheck(allowed=True, feature=feature, limit=limit)

            # Get current usage
            current_usage = await self._get_current_usage(tenant_id, feature)

            # Check if we would exceed limit
            new_usage = current_usage + increment
            if new_usage > limit:
                return LicenseCheck(
                    allowed=False,
                    feature=feature,
                    limit=limit,
                    remaining=0,
                    message=f"License limit exceeded for {feature}. Limit: {limit}, Current: {current_usage}",
                )

            return LicenseCheck(allowed=True, feature=feature, limit=limit, remaining=limit - new_usage)

        except Exception as e:
            logger.error(f"Error checking feature limit {feature}: {e}")
            # Fail open
            return LicenseCheck(allowed=True, feature=feature)

    def _determine_feature_check(self, path: str, method: str) -> Optional[dict[str, Any]]:
        """Map API endpoint to license feature check"""

        # Customer management endpoints
        if "/api/v1/customers" in path and method == "POST":
            return {"feature": "max_customers", "increment": 1}

        # Concurrent user check (for login endpoints)
        if "/api/v1/auth/login" in path:
            return {"feature": "max_concurrent_users", "increment": 1}

        # API rate limiting
        if path.startswith("/api/"):
            return {"feature": "api_calls_per_hour", "increment": 1}

        # Service plan creation
        if "/api/v1/service-plans" in path and method == "POST":
            return {"feature": "service_plans", "increment": 1}

        # Network device management
        if "/api/v1/network/devices" in path and method == "POST":
            return {"feature": "max_network_devices", "increment": 1}

        # Feature-specific endpoints
        if "/api/v1/analytics" in path:
            return {"feature": "advanced_analytics", "increment": 0}

        if "/api/v1/resellers" in path:
            return {"feature": "reseller_management", "increment": 0}

        if "/api/v1/webhooks" in path:
            return {"feature": "webhook_integrations", "increment": 0}

        # No specific check needed
        return None

    def _get_feature_limit(self, license_contract: dict[str, Any], feature: str) -> Optional[int]:
        """Get limit for specific feature from license contract"""

        # Direct limit fields
        limit_mapping = {
            "max_customers": "max_customers",
            "max_concurrent_users": "max_concurrent_users",
            "max_network_devices": "max_network_devices",
            "api_calls_per_hour": "max_api_calls_per_hour",
        }

        if feature in limit_mapping:
            return license_contract.get(limit_mapping[feature])

        # Feature limits from feature_limits JSON
        feature_limits = license_contract.get("feature_limits", {})
        if feature in feature_limits:
            return feature_limits[feature]

        # Feature enabled/disabled check
        enabled_features = license_contract.get("enabled_features", [])
        disabled_features = license_contract.get("disabled_features", [])

        if feature in disabled_features:
            return 0  # Feature disabled

        if feature in enabled_features:
            return -1  # Feature enabled, unlimited

        # Default - no limit specified
        return None

    async def _get_current_usage(self, tenant_id: str, feature: str) -> int:
        """Get current usage for feature from local tracking or database"""

        cache_key = f"usage:{tenant_id}:{feature}"

        # For per-hour limits, check time-based cache
        if feature == "api_calls_per_hour":
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            hour_key = f"{cache_key}:{current_hour.isoformat()}"

            if hour_key in self.usage_cache:
                return self.usage_cache[hour_key]
            else:
                self.usage_cache[hour_key] = 0
                return 0

        # For persistent counts (customers, devices, etc.), query database
        if feature in ["max_customers", "max_network_devices", "service_plans"]:
            return await self._query_database_count(tenant_id, feature)

        # For concurrent users, check active sessions
        if feature == "max_concurrent_users":
            return await self._get_active_session_count(tenant_id)

        # Default cache-based tracking
        return self.usage_cache.get(cache_key, 0)

    async def _update_usage_tracking(self, request: Request, feature: str):
        """Update usage tracking after successful request"""

        try:
            tenant_id = await self._get_tenant_id(request)
            if not tenant_id:
                return

            # Update API call tracking
            if feature == "api_calls_per_hour":
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                cache_key = f"usage:{tenant_id}:{feature}:{current_hour.isoformat()}"

                self.usage_cache[cache_key] = self.usage_cache.get(cache_key, 0) + 1

                # Clean up old hour entries
                self._cleanup_hourly_cache(tenant_id, feature)

            # Sync usage to Management Platform periodically
            await self._sync_usage_to_management(tenant_id)

        except Exception as e:
            logger.error(f"Error updating usage tracking: {e}")

    def _is_system_endpoint(self, path: str) -> bool:
        """Check if endpoint should skip license enforcement"""

        system_paths = [
            "/health",
            "/metrics",
            "/api/v1/system/license",  # License management endpoint
            "/api/v1/auth/logout",
            "/docs",
            "/openapi.json",
        ]

        return any(path.startswith(sys_path) for sys_path in system_paths)

    def _is_license_active(self, license_contract: dict[str, Any]) -> bool:
        """Check if license is currently active and valid"""

        status = license_contract.get("status", "").lower()
        if status != "active":
            return False

        # Check expiry
        valid_until = license_contract.get("valid_until")
        if valid_until:
            if isinstance(valid_until, str):
                valid_until = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))

            if datetime.now(valid_until.tzinfo) > valid_until:
                return False

        return True

    async def _get_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request context"""

        # Check if set by auth middleware
        if hasattr(request.state, "tenant_id"):
            return request.state.tenant_id

        # Extract from JWT token if available
        if hasattr(request.state, "user") and hasattr(request.state.user, "tenant_id"):
            return request.state.user.tenant_id

        # Extract from subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            return f"tenant-{subdomain}"

        return None

    async def _get_service_token(self) -> str:
        """Get service token for Management Platform communication"""

        from dotmac.platform.auth.core.jwt_service import JWTService

        jwt_service = JWTService()
        payload = {
            "service": "isp_instance",
            "scope": "license_check",
            "token_type": "service",
        }

        return await jwt_service.create_access_token(data=payload, expires_delta=timedelta(hours=1))

    def _get_management_platform_url(self) -> str:
        """Get Management Platform URL from environment"""
        import os

        return os.getenv("MANAGEMENT_PLATFORM_URL", "https://admin.yourdomain.com")

    async def _query_database_count(self, tenant_id: str, feature: str) -> int:
        """Query database for current count of feature usage"""

        # This would query the ISP instance database
        # Implementation depends on specific models
        try:
            with get_db_session() as db:
                if feature == "max_customers":
                    from dotmac_isp.modules.identity.models import Customer

                    return db.query(Customer).filter_by(tenant_id=tenant_id, is_active=True).count()

                elif feature == "service_plans":
                    from dotmac_isp.modules.services.models import ServicePlan

                    return db.query(ServicePlan).filter_by(tenant_id=tenant_id, is_active=True).count()

                # Add other feature counts as needed

        except Exception as e:
            logger.error(f"Error querying database count for {feature}: {e}")
            return 0

        return 0

    async def _get_active_session_count(self, tenant_id: str) -> int:
        """Get count of active user sessions"""

        # This would query active sessions from database or cache
        return 0

    def _cleanup_hourly_cache(self, tenant_id: str, feature: str):
        """Clean up old hourly usage entries"""

        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        cutoff = current_hour - timedelta(hours=2)

        keys_to_remove = []
        for key in self.usage_cache.keys():
            if key.startswith(f"usage:{tenant_id}:{feature}:"):
                try:
                    key_time_str = key.split(":")[-1]
                    key_time = datetime.fromisoformat(key_time_str)
                    if key_time < cutoff:
                        keys_to_remove.append(key)
                except (ValueError, TypeError, AttributeError) as e:
                    # Skip malformed cache keys - they'll be cleaned up naturally
                    logger.warning(f"Skipping malformed cache key {key}: {e}")
                    continue

        for key in keys_to_remove:
            del self.usage_cache[key]

    async def _sync_usage_to_management(self, tenant_id: str):
        """Sync usage data to Management Platform periodically"""

        now = time.time()
        last_sync_key = f"last_sync:{tenant_id}"

        # Only sync every 5 minutes
        if last_sync_key in self.last_sync and now - self.last_sync[last_sync_key] < 300:
            return

        try:
            # Collect current usage data

            # Would collect all relevant usage metrics
            # and send to Management Platform for tracking

            self.last_sync[last_sync_key] = now

        except Exception as e:
            logger.error(f"Error syncing usage to management platform: {e}")
