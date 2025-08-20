"""
Strict tenancy isolation with cross-tenant access prevention.
"""

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from contextlib import asynccontextmanager

import structlog
from pydantic import BaseModel, Field


logger = structlog.get_logger(__name__)


class TenantContext(BaseModel):
    """Tenant context for request isolation."""

    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Security attributes
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    api_key_id: Optional[str] = Field(None, description="API key identifier")

    # Resource access tracking
    accessed_resources: Set[str] = Field(default_factory=set, description="Accessed resource IDs")

    class Config:
        extra = "forbid"

    def add_accessed_resource(self, resource_id: str):
        """Track accessed resource."""
        self.accessed_resources.add(resource_id)

    def has_role(self, role: str) -> bool:
        """Check if tenant context has specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if tenant context has specific permission."""
        return permission in self.permissions

    def get_tenant_hash(self) -> str:
        """Get deterministic hash for tenant."""
        return hashlib.sha256(self.tenant_id.encode()).hexdigest()[:16]


class TenantIsolationError(Exception):
    """Exception raised when tenant isolation is violated."""
    pass


class CrossTenantAccessError(TenantIsolationError):
    """Exception raised when cross-tenant access is attempted."""
    pass


class TenantGuard:
    """Guard for enforcing tenant isolation."""

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.tenant_contexts: Dict[str, TenantContext] = {}
        self.resource_tenant_mapping: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def register_tenant_context(self, context: TenantContext):
        """Register tenant context for a request."""
        async with self._lock:
            self.tenant_contexts[context.request_id] = context

        logger.debug(
            "Tenant context registered",
            tenant_id=context.tenant_id,
            request_id=context.request_id,
            user_id=context.user_id
        )

    async def get_tenant_context(self, request_id: str) -> Optional[TenantContext]:
        """Get tenant context by request ID."""
        return self.tenant_contexts.get(request_id)

    async def cleanup_context(self, request_id: str):
        """Clean up tenant context after request completion."""
        async with self._lock:
            context = self.tenant_contexts.pop(request_id, None)
            if context:
                logger.debug(
                    "Tenant context cleaned up",
                    tenant_id=context.tenant_id,
                    request_id=request_id,
                    resources_accessed=len(context.accessed_resources)
                )

    async def register_resource(self, resource_id: str, tenant_id: str):
        """Register a resource as belonging to a specific tenant."""
        async with self._lock:
            existing_tenant = self.resource_tenant_mapping.get(resource_id)
            if existing_tenant and existing_tenant != tenant_id:
                raise TenantIsolationError(
                    f"Resource {resource_id} already belongs to tenant {existing_tenant}"
                )

            self.resource_tenant_mapping[resource_id] = tenant_id

    async def check_resource_access(
        self,
        resource_id: str,
        tenant_context: TenantContext,
        operation: str = "read"
    ):
        """Check if tenant can access a specific resource."""
        resource_tenant = self.resource_tenant_mapping.get(resource_id)

        if not resource_tenant:
            if self.strict_mode:
                raise TenantIsolationError(f"Resource {resource_id} not registered with any tenant")
            else:
                # In non-strict mode, register resource to current tenant
                await self.register_resource(resource_id, tenant_context.tenant_id)
                resource_tenant = tenant_context.tenant_id

        if resource_tenant != tenant_context.tenant_id:
            raise CrossTenantAccessError(
                f"Tenant {tenant_context.tenant_id} cannot access resource {resource_id} "
                f"belonging to tenant {resource_tenant}"
            )

        # Track resource access
        tenant_context.add_accessed_resource(resource_id)

        logger.debug(
            "Resource access granted",
            tenant_id=tenant_context.tenant_id,
            resource_id=resource_id,
            operation=operation
        )

    async def validate_tenant_data(self, data: Dict[str, Any], tenant_context: TenantContext):
        """Validate that data belongs to the correct tenant."""
        if "tenant_id" in data:
            data_tenant_id = data["tenant_id"]
            if data_tenant_id != tenant_context.tenant_id:
                raise CrossTenantAccessError(
                    f"Data tenant_id {data_tenant_id} does not match context tenant_id {tenant_context.tenant_id}"
                )

        # Ensure tenant_id is set in data
        data["tenant_id"] = tenant_context.tenant_id

    async def filter_tenant_data(
        self,
        data_list: List[Dict[str, Any]],
        tenant_context: TenantContext
    ) -> List[Dict[str, Any]]:
        """Filter data list to only include items belonging to the tenant."""
        filtered_data = []

        for item in data_list:
            item_tenant_id = item.get("tenant_id")
            if item_tenant_id == tenant_context.tenant_id:
                filtered_data.append(item)
            elif self.strict_mode:
                logger.warning(
                    "Cross-tenant data filtered out",
                    item_tenant_id=item_tenant_id,
                    context_tenant_id=tenant_context.tenant_id,
                    item_id=item.get("id", "unknown")
                )

        return filtered_data

    def get_tenant_stats(self) -> Dict[str, Any]:
        """Get tenant isolation statistics."""
        tenant_counts = {}
        resource_counts = {}

        for context in self.tenant_contexts.values():
            tenant_counts[context.tenant_id] = tenant_counts.get(context.tenant_id, 0) + 1

        for resource_id, tenant_id in self.resource_tenant_mapping.items():
            resource_counts[tenant_id] = resource_counts.get(tenant_id, 0) + 1

        return {
            "active_contexts": len(self.tenant_contexts),
            "registered_resources": len(self.resource_tenant_mapping),
            "tenants_with_contexts": len(tenant_counts),
            "tenants_with_resources": len(resource_counts),
            "strict_mode": self.strict_mode
        }


class TenantIsolatedStorage:
    """Storage adapter with built-in tenant isolation."""

    def __init__(self, base_storage_adapter, tenant_guard: TenantGuard):
        self.base_storage = base_storage_adapter
        self.tenant_guard = tenant_guard

    async def store_data(
        self,
        key: str,
        data: Dict[str, Any],
        tenant_context: TenantContext
    ):
        """Store data with tenant isolation."""
        # Validate tenant data
        await self.tenant_guard.validate_tenant_data(data, tenant_context)

        # Create tenant-prefixed key
        tenant_key = f"tenant:{tenant_context.tenant_id}:{key}"

        # Register resource
        await self.tenant_guard.register_resource(key, tenant_context.tenant_id)

        # Store data
        return await self.base_storage.store(tenant_key, data)

    async def get_data(
        self,
        key: str,
        tenant_context: TenantContext
    ) -> Optional[Dict[str, Any]]:
        """Get data with tenant isolation check."""
        # Check resource access
        await self.tenant_guard.check_resource_access(key, tenant_context, "read")

        # Create tenant-prefixed key
        tenant_key = f"tenant:{tenant_context.tenant_id}:{key}"

        # Get data
        data = await self.base_storage.get(tenant_key)

        if data:
            # Validate tenant data
            await self.tenant_guard.validate_tenant_data(data, tenant_context)

        return data

    async def list_data(
        self,
        prefix: str,
        tenant_context: TenantContext
    ) -> List[Dict[str, Any]]:
        """List data with tenant filtering."""
        # Create tenant-prefixed pattern
        tenant_prefix = f"tenant:{tenant_context.tenant_id}:{prefix}"

        # Get data from base storage
        all_data = await self.base_storage.list(tenant_prefix)

        # Filter and validate tenant data
        return await self.tenant_guard.filter_tenant_data(all_data, tenant_context)

    async def delete_data(
        self,
        key: str,
        tenant_context: TenantContext
    ) -> bool:
        """Delete data with tenant isolation check."""
        # Check resource access
        await self.tenant_guard.check_resource_access(key, tenant_context, "delete")

        # Create tenant-prefixed key
        tenant_key = f"tenant:{tenant_context.tenant_id}:{key}"

        # Delete data
        result = await self.base_storage.delete(tenant_key)

        # Clean up resource mapping
        if result:
            async with self.tenant_guard._lock:
                self.tenant_guard.resource_tenant_mapping.pop(key, None)

        return result


class TenantIsolationMiddleware:
    """Middleware for enforcing tenant isolation in requests."""

    def __init__(self, tenant_guard: TenantGuard):
        self.tenant_guard = tenant_guard

    @asynccontextmanager
    async def tenant_context(self, context: TenantContext):
        """Context manager for tenant isolation."""
        try:
            # Register tenant context
            await self.tenant_guard.register_tenant_context(context)

            logger.info(
                "Tenant context activated",
                tenant_id=context.tenant_id,
                request_id=context.request_id,
                user_id=context.user_id
            )

            yield context

        except Exception as e:
            logger.error(
                "Tenant context error",
                tenant_id=context.tenant_id,
                request_id=context.request_id,
                error=str(e)
            )
            raise

        finally:
            # Clean up tenant context
            await self.tenant_guard.cleanup_context(context.request_id)

    async def extract_tenant_context(self, request_data: Dict[str, Any]) -> TenantContext:
        """Extract tenant context from request data."""
        tenant_id = request_data.get("tenant_id")
        if not tenant_id:
            raise TenantIsolationError("Missing tenant_id in request")

        return TenantContext(
            tenant_id=tenant_id,
            user_id=request_data.get("user_id"),
            roles=request_data.get("roles", []),
            permissions=request_data.get("permissions", []),
            ip_address=request_data.get("ip_address"),
            user_agent=request_data.get("user_agent"),
            api_key_id=request_data.get("api_key_id")
        )


class TenantAwareWorkflowEngine:
    """Workflow engine with built-in tenant isolation."""

    def __init__(self, base_engine, tenant_guard: TenantGuard):
        self.base_engine = base_engine
        self.tenant_guard = tenant_guard

    async def create_workflow_run(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_context: TenantContext,
        business_key: Optional[str] = None
    ) -> str:
        """Create workflow run with tenant isolation."""
        # Validate tenant data
        await self.tenant_guard.validate_tenant_data(input_data, tenant_context)

        # Check workflow access
        await self.tenant_guard.check_resource_access(workflow_id, tenant_context, "execute")

        # Create execution ID with tenant prefix for additional isolation
        execution_id = f"{tenant_context.get_tenant_hash()}_{uuid.uuid4()}"

        # Register execution as resource
        await self.tenant_guard.register_resource(execution_id, tenant_context.tenant_id)

        # Create workflow run
        result = await self.base_engine.create_workflow_run(
            tenant_id=tenant_context.tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            business_key=business_key,
            input_data=input_data,
            context_data={"tenant_context": tenant_context.dict()}
        )

        logger.info(
            "Tenant-isolated workflow run created",
            tenant_id=tenant_context.tenant_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            user_id=tenant_context.user_id
        )

        return execution_id

    async def get_workflow_run(
        self,
        execution_id: str,
        tenant_context: TenantContext
    ) -> Optional[Dict[str, Any]]:
        """Get workflow run with tenant isolation check."""
        # Check execution access
        await self.tenant_guard.check_resource_access(execution_id, tenant_context, "read")

        # Get workflow run
        run_data = await self.base_engine.get_workflow_run(execution_id)

        if run_data:
            # Validate tenant data
            await self.tenant_guard.validate_tenant_data(run_data, tenant_context)

        return run_data

    async def list_workflow_runs(
        self,
        tenant_context: TenantContext,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List workflow runs with tenant filtering."""
        # Add tenant filter
        tenant_filters = {"tenant_id": tenant_context.tenant_id}
        if filters:
            tenant_filters.update(filters)

        # Get runs from base engine
        all_runs = await self.base_engine.list_workflow_runs(tenant_filters)

        # Filter tenant data (additional safety check)
        return await self.tenant_guard.filter_tenant_data(all_runs, tenant_context)

    async def cancel_workflow_run(
        self,
        execution_id: str,
        tenant_context: TenantContext,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel workflow run with tenant isolation check."""
        # Check execution access
        await self.tenant_guard.check_resource_access(execution_id, tenant_context, "cancel")

        # Cancel workflow run
        result = await self.base_engine.cancel_workflow_run(execution_id, reason)

        if result:
            logger.info(
                "Tenant-isolated workflow run cancelled",
                tenant_id=tenant_context.tenant_id,
                execution_id=execution_id,
                user_id=tenant_context.user_id,
                reason=reason
            )

        return result


class TenantMetrics:
    """Metrics collection with tenant isolation."""

    def __init__(self):
        self.tenant_metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def record_metric(
        self,
        tenant_id: str,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None
    ):
        """Record metric for a specific tenant."""
        async with self._lock:
            if tenant_id not in self.tenant_metrics:
                self.tenant_metrics[tenant_id] = {}

            if metric_name not in self.tenant_metrics[tenant_id]:
                self.tenant_metrics[tenant_id][metric_name] = {
                    "count": 0,
                    "sum": 0.0,
                    "min": float('inf'),
                    "max": float('-inf'),
                    "tags": tags or {}
                }

            metric = self.tenant_metrics[tenant_id][metric_name]
            metric["count"] += 1
            metric["sum"] += value
            metric["min"] = min(metric["min"], value)
            metric["max"] = max(metric["max"], value)

    async def get_tenant_metrics(
        self,
        tenant_id: str,
        tenant_context: TenantContext
    ) -> Dict[str, Any]:
        """Get metrics for a specific tenant with access control."""
        if tenant_context.tenant_id != tenant_id:
            raise CrossTenantAccessError(
                f"Tenant {tenant_context.tenant_id} cannot access metrics for tenant {tenant_id}"
            )

        return self.tenant_metrics.get(tenant_id, {})

    async def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across all tenants (admin only)."""
        # This should only be called by system administrators
        total_tenants = len(self.tenant_metrics)
        total_metrics = sum(len(metrics) for metrics in self.tenant_metrics.values())

        return {
            "total_tenants": total_tenants,
            "total_metrics": total_metrics,
            "tenants": list(self.tenant_metrics.keys())
        }
