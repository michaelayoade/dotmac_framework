"""
Core tenant management for DotMac Framework.

Consolidates tenant identity resolution, context management, and middleware
from dotmac-tenant package with production-ready error handling.
"""

import re
import uuid
from contextvars import ContextVar
from typing import Any, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field
from structlog import get_logger

from dotmac.core.exceptions import (
    TenantNotFoundError,
)

# Structured logging
log = get_logger(__name__)

# Context variable to store current tenant information
_tenant_context: ContextVar[Optional["TenantContext"]] = ContextVar("tenant_context", default=None)


class TenantMetadata(BaseModel):
    """Tenant metadata configuration."""

    model_config = ConfigDict(extra="allow")

    # Database settings
    database_url: str | None = None
    database_schema: str | None = None
    database_isolation_level: str = "read_committed"

    # Feature flags
    features: dict[str, bool] = Field(default_factory=dict)

    # Security settings
    allowed_domains: list[str] = Field(default_factory=list)
    rate_limits: dict[str, int] = Field(default_factory=dict)

    # Custom settings
    settings: dict[str, Any] = Field(default_factory=dict)


class TenantContext(BaseModel):
    """Container for current tenant context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core identification
    tenant_id: uuid.UUID
    tenant_slug: str
    display_name: str

    # Metadata
    metadata: TenantMetadata | None = None

    # Resolution information
    resolution_method: str
    resolved_from: str

    # Request context
    request_id: str | None = None
    user_id: uuid.UUID | None = None

    # Security context
    security_level: str = "standard"
    permissions: list[str] = Field(default_factory=list)

    # Feature flags
    features: dict[str, bool] = Field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.security_level != "suspended"

    def has_feature(self, feature_name: str) -> bool:
        """Check if tenant has specific feature enabled."""
        return self.features.get(feature_name, False)

    def has_permission(self, permission: str) -> bool:
        """Check if current context has specific permission."""
        return permission in self.permissions


class TenantResolver(Protocol):
    """Protocol for tenant resolution strategies."""

    async def resolve_tenant(self, request_data: dict[str, Any]) -> TenantContext | None:
        """Resolve tenant from request data."""
        ...


class SubdomainTenantResolver:
    """Resolve tenant from subdomain."""

    def __init__(self, domain_pattern: str = r"^([a-zA-Z0-9\-]+)\."):
        self.domain_pattern = re.compile(domain_pattern)

    async def resolve_tenant(self, request_data: dict[str, Any]) -> TenantContext | None:
        """Resolve tenant from subdomain."""
        host = request_data.get("host")
        if not host:
            return None

        match = self.domain_pattern.match(host)
        if not match:
            return None

        subdomain = match.group(1)

        # In production, this would query the database
        tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, subdomain)

        return TenantContext(
            tenant_id=tenant_id,
            tenant_slug=subdomain,
            display_name=subdomain.replace("-", " ").title(),
            resolution_method="subdomain",
            resolved_from=subdomain,
        )


class HeaderTenantResolver:
    """Resolve tenant from HTTP header."""

    def __init__(self, header_name: str = "X-Tenant-ID"):
        self.header_name = header_name.lower()

    async def resolve_tenant(self, request_data: dict[str, Any]) -> TenantContext | None:
        """Resolve tenant from header."""
        headers = request_data.get("headers", {})
        tenant_value = headers.get(self.header_name)

        if not tenant_value:
            return None

        try:
            tenant_id = uuid.UUID(tenant_value)
        except ValueError:
            # Treat as slug if not valid UUID
            tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, tenant_value)
            tenant_slug = tenant_value
        else:
            tenant_slug = str(tenant_id)

        return TenantContext(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            display_name=tenant_slug.title(),
            resolution_method="header",
            resolved_from=tenant_value,
        )


class TenantManager:
    """Central manager for tenant operations."""

    def __init__(self):
        self.resolvers: list[TenantResolver] = [
            SubdomainTenantResolver(),
            HeaderTenantResolver(),
        ]
        self._tenant_cache: dict[str, TenantContext] = {}

    async def resolve_tenant(self, request_data: dict[str, Any]) -> TenantContext | None:
        """Resolve tenant using configured resolvers."""
        for resolver in self.resolvers:
            try:
                tenant_context = await resolver.resolve_tenant(request_data)
                if tenant_context:
                    log.info(
                        "Tenant resolved",
                        tenant_id=str(tenant_context.tenant_id),
                        method=tenant_context.resolution_method,
                        resolved_from=tenant_context.resolved_from,
                    )
                    return tenant_context
            except Exception as e:
                log.warning(
                    "Tenant resolution failed", resolver=resolver.__class__.__name__, error=str(e)
                )
                continue

        log.warning("No tenant could be resolved", request_data=request_data)
        return None

    def set_tenant_context(self, tenant_context: TenantContext | None) -> None:
        """Set current tenant context."""
        _tenant_context.set(tenant_context)

        if tenant_context:
            log.info(
                "Tenant context set",
                tenant_id=str(tenant_context.tenant_id),
                tenant_slug=tenant_context.tenant_slug,
            )

    def get_tenant_context(self) -> TenantContext | None:
        """Get current tenant context."""
        return _tenant_context.get()

    def require_tenant_context(self) -> TenantContext:
        """Get current tenant context, raising error if not set."""
        context = _tenant_context.get()
        if context is None:
            msg = "No tenant context available"
            raise TenantNotFoundError(msg, error_code="TENANT_CONTEXT_REQUIRED")
        return context

    def clear_tenant_context(self) -> None:
        """Clear current tenant context."""
        _tenant_context.set(None)
        log.debug("Tenant context cleared")


# Global tenant manager instance
tenant_manager = TenantManager()


# Convenience functions
def get_current_tenant() -> TenantContext | None:
    """Get current tenant context."""
    return tenant_manager.get_tenant_context()


def require_current_tenant() -> TenantContext:
    """Get current tenant context, raising error if not available."""
    return tenant_manager.require_tenant_context()


def set_current_tenant(tenant_context: TenantContext | None) -> None:
    """Set current tenant context."""
    tenant_manager.set_tenant_context(tenant_context)


def clear_current_tenant() -> None:
    """Clear current tenant context."""
    tenant_manager.clear_tenant_context()
