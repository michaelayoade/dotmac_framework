"""
Tenancy SDK for Platform using contract-first design with Pydantic v2.

Provides multi-tenant functionality with comprehensive tenant management,
context switching, quota enforcement, and isolation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from dotmac_isp.sdks.contracts.tenancy import (
    ResourceQuota,
    Tenant,
    TenantContextRequest,
    TenantContextResponse,
    TenantCreateRequest,
    TenantListRequest,
    TenantListResponse,
    TenantPlan,
    TenantSettings,
    TenantStatsResponse,
    TenantStatus,
    TenantUpdateRequest,
    TenantUsageRequest,
    TenantUsageResponse,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class TenancyError(Exception):
    """Base tenancy error."""

    pass


class TenantNotFoundError(TenancyError):
    """Tenant not found error."""

    pass


class TenantQuotaExceededError(TenancyError):
    """Tenant quota exceeded error."""

    pass


class TenantInactiveError(TenancyError):
    """Tenant inactive error."""

    pass


class TenantSlugExistsError(TenancyError):
    """Tenant slug already exists error."""

    pass


class TenancySDKConfig:
    """Tenancy SDK configuration."""

    def __init__(
        self,
        cache_ttl: int = 300,  # 5 minutes
        enable_caching: bool = True,
        enable_audit_logging: bool = True,
        default_quotas: dict[str, int] | None = None,
        quota_warning_threshold: int = 80,  # percentage
        trial_duration_days: int = 30,
        enforce_quotas: bool = True,
    ):
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching
        self.enable_audit_logging = enable_audit_logging
        self.default_quotas = default_quotas or {
            "users": 100,
            "storage_mb": 1000,
            "api_calls_per_month": 10000,
            "projects": 10,
        }
        self.quota_warning_threshold = quota_warning_threshold
        self.trial_duration_days = trial_duration_days
        self.enforce_quotas = enforce_quotas


class TenancySDK:
    """
    Contract-first Tenancy SDK with comprehensive multi-tenant functionality.

    Features:
    - Multi-tenant data isolation
    - Tenant context management
    - Resource quota enforcement
    - Usage tracking and analytics
    - Trial and subscription management
    - Custom domain support
    - Tenant settings and preferences
    - Audit logging for compliance
    """

    def __init__(
        self,
        config: TenancySDKConfig | None = None,
        cache_sdk: Any | None = None,
        database_sdk: Any | None = None,
    ):
        """Initialize Tenancy SDK."""
        self.config = config or TenancySDKConfig()
        self.cache_sdk = cache_sdk
        self.database_sdk = database_sdk

        # In-memory stores for testing/fallback
        self._tenants: dict[str, Tenant] = {}
        self._tenant_slugs: dict[str, str] = {}  # slug -> tenant_id
        self._tenant_domains: dict[str, str] = {}  # domain -> tenant_id
        self._usage_data: dict[str, dict[str, Any]] = {}  # tenant_id -> usage data

        # Performance tracking
        self._stats = {
            "tenant_creations": 0,
            "context_switches": 0,
            "quota_checks": 0,
            "quota_violations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Initialize default tenant
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default system tenant."""
        system_tenant = Tenant(
            id="system",
            name="System Tenant",
            slug="system",
            description="Default system tenant for administrative operations",
            status=TenantStatus.ACTIVE,
            plan=TenantPlan.ENTERPRISE,
            owner_id="system",
            settings=TenantSettings(
                features={
                    "system_admin": True,
                    "unlimited_quotas": True,
                    "advanced_analytics": True,
                }
            ),
            quotas=[
                ResourceQuota(
                    resource_type="users",
                    limit=999999,
                    warning_threshold=None,
                ),
                ResourceQuota(
                    resource_type="storage_mb",
                    limit=999999,
                    warning_threshold=None,
                ),
            ],
        )

        self._tenants[system_tenant.id] = system_tenant
        self._tenant_slugs[system_tenant.slug] = system_tenant.id

    async def _get_cache_key(self, key_type: str, identifier: str) -> str:
        """Generate cache key."""
        return f"tenancy:{key_type}:{identifier}"

    async def _cache_get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return None

        try:
            result = await self.cache_sdk.get(key)
            if result is not None:
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1
            return result
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            self._stats["cache_misses"] += 1
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.set(key, value, ttl or self.config.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")

    async def _cache_delete(self, key: str) -> None:
        """Delete value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")

    def _create_default_quotas(self, plan: TenantPlan) -> list[ResourceQuota]:
        """Create default quotas based on tenant plan."""
        plan_multipliers = {
            TenantPlan.FREE: 1,
            TenantPlan.BASIC: 5,
            TenantPlan.PROFESSIONAL: 20,
            TenantPlan.ENTERPRISE: 100,
            TenantPlan.CUSTOM: 50,
        }

        multiplier = plan_multipliers.get(plan, 1)
        quotas = []

        for resource_type, base_limit in self.config.default_quotas.items():
            quotas.append(
                ResourceQuota(
                    resource_type=resource_type,
                    limit=base_limit * multiplier,
                    warning_threshold=self.config.quota_warning_threshold,
                )
            )

        return quotas

    async def create_tenant(
        self,
        request: TenantCreateRequest,
        context: RequestContext | None = None,
    ) -> Tenant:
        """Create a new tenant."""
        try:
            # Check if slug already exists
            if request.slug in self._tenant_slugs:
                raise TenantSlugExistsError(
                    f"Tenant slug '{request.slug}' already exists"
                )

            # Check if domain already exists
            if request.domain and request.domain in self._tenant_domains:
                raise TenancyError(
                    f"Domain '{request.domain}' already assigned to another tenant"
                )

            # Generate tenant ID
            tenant_id = f"tenant-{len(self._tenants) + 1}"

            # Create default quotas if not provided
            quotas = self._create_default_quotas(request.plan)

            # Set trial expiration for free plans
            expires_at = None
            if request.plan == TenantPlan.FREE:
                expires_at = datetime.now(UTC) + timedelta(
                    days=self.config.trial_duration_days
                )

            # Create tenant
            tenant = Tenant(
                id=tenant_id,
                name=request.name,
                slug=request.slug,
                description=request.description,
                status=TenantStatus.ACTIVE,
                plan=request.plan,
                domain=request.domain,
                owner_id=request.owner_id,
                settings=request.settings or TenantSettings(),
                quotas=quotas,
                metadata=request.metadata,
                expires_at=expires_at,
            )

            # Store tenant
            self._tenants[tenant_id] = tenant
            self._tenant_slugs[request.slug] = tenant_id

            if request.domain:
                self._tenant_domains[request.domain] = tenant_id

            # Initialize usage data
            self._usage_data[tenant_id] = {
                "created_at": datetime.now(UTC),
                "last_activity": datetime.now(UTC),
                "resource_usage": {quota.resource_type: 0 for quota in quotas},
                "usage_history": {},
            }

            self._stats["tenant_creations"] += 1

            # Clear cache
            cache_key = await self._get_cache_key("all_tenants", "list")
            await self._cache_delete(cache_key)

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Tenant created: id={tenant_id}, name={request.name}, "
                    f"slug={request.slug}, plan={request.plan}, "
                    f"created_by={context.headers.x_user_id if context and context.headers.x_user_id else 'system'}"
                )

            return tenant

        except Exception as e:
            logger.error(f"Tenant creation failed: {e}")
            raise TenancyError(f"Failed to create tenant: {str(e)}")

    async def get_tenant(
        self,
        tenant_id: str,
        context: RequestContext | None = None,
    ) -> Tenant | None:
        """Get tenant by ID."""
        # Try cache first
        cache_key = await self._get_cache_key("tenant", tenant_id)
        cached_tenant = await self._cache_get(cache_key)

        if cached_tenant:
            return cached_tenant

        # Get from storage
        tenant = self._tenants.get(tenant_id)

        if tenant:
            # Cache the result
            await self._cache_set(cache_key, tenant)

        return tenant

    async def get_tenant_by_slug(
        self,
        slug: str,
        context: RequestContext | None = None,
    ) -> Tenant | None:
        """Get tenant by slug."""
        tenant_id = self._tenant_slugs.get(slug)
        if not tenant_id:
            return None

        return await self.get_tenant(tenant_id, context)

    async def get_tenant_by_domain(
        self,
        domain: str,
        context: RequestContext | None = None,
    ) -> Tenant | None:
        """Get tenant by domain."""
        tenant_id = self._tenant_domains.get(domain)
        if not tenant_id:
            return None

        return await self.get_tenant(tenant_id, context)

    async def update_tenant(  # noqa: C901
        self,
        tenant_id: str,
        request: TenantUpdateRequest,
        context: RequestContext | None = None,
    ) -> Tenant:
        """Update tenant."""
        try:
            tenant = await self.get_tenant(tenant_id, context)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # Update fields
            if request.name is not None:
                tenant.name = request.name

            if request.description is not None:
                tenant.description = request.description

            if request.status is not None:
                tenant.status = request.status

            if request.plan is not None:
                # Update quotas if plan changed
                if tenant.plan != request.plan:
                    tenant.quotas = self._create_default_quotas(request.plan)
                tenant.plan = request.plan

            if request.domain is not None:
                # Remove old domain mapping
                if tenant.domain:
                    self._tenant_domains.pop(tenant.domain, None)

                # Add new domain mapping
                if request.domain:
                    if request.domain in self._tenant_domains:
                        raise TenancyError(
                            f"Domain '{request.domain}' already assigned"
                        )
                    self._tenant_domains[request.domain] = tenant_id

                tenant.domain = request.domain

            if request.settings is not None:
                tenant.settings = request.settings

            if request.metadata is not None:
                tenant.metadata = request.metadata

            if request.expires_at is not None:
                tenant.expires_at = request.expires_at

            tenant.updated_at = datetime.now(UTC)

            # Store updated tenant
            self._tenants[tenant_id] = tenant

            # Clear cache
            cache_key = await self._get_cache_key("tenant", tenant_id)
            await self._cache_delete(cache_key)

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Tenant updated: id={tenant_id}, "
                    f"updated_by={context.headers.x_user_id if context and context.headers.x_user_id else 'system'}"
                )

            return tenant

        except Exception as e:
            logger.error(f"Tenant update failed: {e}")
            raise TenancyError(f"Failed to update tenant: {str(e)}")

    async def list_tenants(
        self,
        request: TenantListRequest,
        context: RequestContext | None = None,
    ) -> TenantListResponse:
        """List tenants with filtering."""
        tenants = list(self._tenants.values())

        # Apply filters
        if request.status is not None:
            tenants = [t for t in tenants if t.status == request.status]

        if request.plan is not None:
            tenants = [t for t in tenants if t.plan == request.plan]

        if request.owner_id is not None:
            tenants = [t for t in tenants if t.owner_id == request.owner_id]

        if request.search:
            search_lower = request.search.lower()
            tenants = [
                t
                for t in tenants
                if search_lower in t.name.lower()
                or (t.description and search_lower in t.description.lower())
                or search_lower in t.slug.lower()
            ]

        if request.expired_only:
            tenants = [t for t in tenants if t.is_expired]

        if request.trial_only:
            tenants = [t for t in tenants if t.is_trial]

        # Apply pagination
        total = len(tenants)
        start_idx = (request.page - 1) * request.per_page
        end_idx = start_idx + request.per_page
        paginated_tenants = tenants[start_idx:end_idx]

        # Calculate pagination manually to avoid recursion
        import math

        total_pages = math.ceil(total / request.per_page) if total > 0 else 0

        # Create response directly without validation to avoid recursion
        response = TenantListResponse.model_construct(
            tenants=paginated_tenants,
            page=request.page,
            per_page=request.per_page,
            total_items=total,
            total_pages=total_pages,
            has_next=end_idx < total,
            has_prev=request.page > 1,
        )

        return response

    async def resolve_tenant_context(
        self,
        request: TenantContextRequest,
        context: RequestContext | None = None,
    ) -> TenantContextResponse:
        """Resolve tenant context from various identifiers."""
        try:
            tenant = None

            # Try to resolve by tenant_id first
            if request.tenant_id:
                tenant = await self.get_tenant(request.tenant_id, context)

            # Try to resolve by slug
            if not tenant and request.tenant_slug:
                tenant = await self.get_tenant_by_slug(request.tenant_slug, context)

            # Try to resolve by domain
            if not tenant and request.domain:
                tenant = await self.get_tenant_by_domain(request.domain, context)

            if not tenant:
                raise TenantNotFoundError("Tenant not found with provided identifiers")

            # Check tenant status
            if tenant.status != TenantStatus.ACTIVE:
                raise TenantInactiveError(f"Tenant {tenant.id} is not active")

            # Check if tenant is expired
            if tenant.is_expired:
                raise TenantInactiveError(f"Tenant {tenant.id} has expired")

            # Get user permissions (placeholder - would integrate with RBAC SDK)
            permissions = ["users.read", "profile.write"]  # Default permissions

            # Get quota status
            quotas_status = {}
            for quota in tenant.quotas:
                quotas_status[quota.resource_type] = {
                    "limit": quota.limit,
                    "current": quota.current_usage,
                    "percentage": quota.usage_percentage,
                    "warning": quota.is_warning_level,
                    "over_limit": quota.is_over_limit,
                }

            # Get available features
            features = tenant.settings.features.copy()

            self._stats["context_switches"] += 1

            # Update last activity
            if tenant.id in self._usage_data:
                self._usage_data[tenant.id]["last_activity"] = datetime.now(UTC)

            return TenantContextResponse(
                tenant=tenant,
                permissions=permissions,
                quotas_status=quotas_status,
                features=features,
            )

        except Exception as e:
            logger.error(f"Tenant context resolution failed: {e}")
            raise

    async def check_quota(
        self,
        tenant_id: str,
        resource_type: str,
        requested_amount: int = 1,
        context: RequestContext | None = None,
    ) -> tuple[bool, str | None]:
        """Check if tenant has quota available for resource."""
        self._stats["quota_checks"] += 1

        try:
            tenant = await self.get_tenant(tenant_id, context)
            if not tenant:
                return False, "Tenant not found"

            # Skip quota checks for system tenant or if quotas disabled
            if tenant.id == "system" or not self.config.enforce_quotas:
                return True, None

            # Find quota for resource type
            quota = None
            for q in tenant.quotas:
                if q.resource_type == resource_type:
                    quota = q
                    break

            if not quota:
                # No quota defined means unlimited
                return True, None

            # Check if request would exceed quota
            if quota.current_usage + requested_amount > quota.limit:
                self._stats["quota_violations"] += 1
                return (
                    False,
                    f"Quota exceeded for {resource_type}: {quota.current_usage + requested_amount}/{quota.limit}",
                )

            return True, None

        except Exception as e:
            logger.error(f"Quota check failed: {e}")
            return False, f"Quota check error: {str(e)}"

    async def update_usage(
        self,
        tenant_id: str,
        resource_type: str,
        amount: int,
        context: RequestContext | None = None,
    ) -> bool:
        """Update resource usage for tenant."""
        try:
            tenant = await self.get_tenant(tenant_id, context)
            if not tenant:
                return False

            # Update quota usage
            for quota in tenant.quotas:
                if quota.resource_type == resource_type:
                    quota.current_usage = max(0, quota.current_usage + amount)
                    break

            # Update usage data
            if tenant_id in self._usage_data:
                usage_data = self._usage_data[tenant_id]
                if resource_type not in usage_data["resource_usage"]:
                    usage_data["resource_usage"][resource_type] = 0
                usage_data["resource_usage"][resource_type] = max(
                    0, usage_data["resource_usage"][resource_type] + amount
                )
                usage_data["last_activity"] = datetime.now(UTC)

            # Store updated tenant
            self._tenants[tenant_id] = tenant

            # Clear cache
            cache_key = await self._get_cache_key("tenant", tenant_id)
            await self._cache_delete(cache_key)

            return True

        except Exception as e:
            logger.error(f"Usage update failed: {e}")
            return False

    async def get_tenant_usage(
        self,
        request: TenantUsageRequest,
        context: RequestContext | None = None,
    ) -> TenantUsageResponse:
        """Get tenant usage statistics."""
        tenant = await self.get_tenant(request.tenant_id, context)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {request.tenant_id} not found")

        # Get usage data
        usage_data = self._usage_data.get(request.tenant_id, {})

        # Determine period
        period_start = request.start_date or usage_data.get(
            "created_at", datetime.now(UTC)
        )
        period_end = request.end_date or datetime.now(UTC)

        # Filter quotas by resource types if specified
        quotas = tenant.quotas
        if request.resource_types:
            quotas = [q for q in quotas if q.resource_type in request.resource_types]

        # Generate usage history (placeholder - would come from time-series data)
        usage_history = {}
        for quota in quotas:
            usage_history[quota.resource_type] = [
                {"date": period_start.date().isoformat(), "count": quota.current_usage}
            ]

        # Generate warnings
        warnings = []
        for quota in quotas:
            if quota.is_over_limit:
                warnings.append(
                    f"{quota.resource_type} usage exceeds limit: {quota.current_usage}/{quota.limit}"
                )
            elif quota.is_warning_level:
                warnings.append(
                    f"{quota.resource_type} usage is at {quota.usage_percentage:.1f}% of limit"
                )

        return TenantUsageResponse(
            tenant_id=request.tenant_id,
            period_start=period_start,
            period_end=period_end,
            quotas=quotas,
            usage_history=usage_history,
            warnings=warnings,
        )

    async def get_stats(self) -> TenantStatsResponse:
        """Get tenant statistics."""
        tenants = list(self._tenants.values())

        # Count by status
        tenants_by_status = {}
        for status in TenantStatus:
            tenants_by_status[status.value] = len(
                [t for t in tenants if t.status == status]
            )

        # Count by plan
        tenants_by_plan = {}
        for plan in TenantPlan:
            tenants_by_plan[plan.value] = len([t for t in tenants if t.plan == plan])

        # Count active, trial, and expired
        active_tenants = len([t for t in tenants if t.status == TenantStatus.ACTIVE])
        trial_tenants = len([t for t in tenants if t.is_trial])
        expired_tenants = len([t for t in tenants if t.is_expired])

        # Calculate average users per tenant (placeholder)
        total_users = sum(
            quota.current_usage
            for tenant in tenants
            for quota in tenant.quotas
            if quota.resource_type == "users"
        )
        avg_users_per_tenant = total_users / len(tenants) if tenants else 0

        return TenantStatsResponse(
            total_tenants=len(tenants),
            active_tenants=active_tenants,
            tenants_by_status=tenants_by_status,
            tenants_by_plan=tenants_by_plan,
            trial_tenants=trial_tenants,
            expired_tenants=expired_tenants,
            avg_users_per_tenant=avg_users_per_tenant,
        )

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        try:
            # Test basic functionality
            test_request = TenantContextRequest(tenant_id="system")

            start_time = datetime.now(UTC)
            await self.resolve_tenant_context(test_request)
            end_time = datetime.now(UTC)

            response_time = (end_time - start_time).total_seconds() * 1000

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "tenants_count": len(self._tenants),
                "active_tenants_count": len(
                    [
                        t
                        for t in self._tenants.values()
                        if t.status == TenantStatus.ACTIVE
                    ]
                ),
                "cache_enabled": self.config.enable_caching,
                "quota_enforcement": self.config.enforce_quotas,
            }

        except Exception as e:
            logger.error(f"Tenancy health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "tenants_count": len(self._tenants),
            }


__all__ = [
    "TenancySDKConfig",
    "TenancySDK",
    "TenancyError",
    "TenantNotFoundError",
    "TenantQuotaExceededError",
    "TenantInactiveError",
    "TenantSlugExistsError",
]
