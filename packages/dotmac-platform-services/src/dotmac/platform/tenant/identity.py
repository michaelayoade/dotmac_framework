"""
Tenant identity utilities for multi-tenant apps.

Provides a resolver that extracts tenant context from common sources.
"""

from __future__ import annotations

from fastapi import Request


class TenantIdentityResolver:
    """Resolve tenant identity from request.

    Order of resolution:
    - Header: X-Tenant-ID
    - Query param: tenant_id
    - Path state: request.state.tenant_id (if set by upstream middleware)
    """

    header_name: str = "X-Tenant-ID"
    query_param: str = "tenant_id"

    async def resolve(self, request: Request) -> str | None:
        # Header
        tenant_id = request.headers.get(self.header_name)
        if tenant_id:
            return tenant_id

        # Query param
        tenant_id = request.query_params.get(self.query_param)
        if tenant_id:
            return tenant_id

        # Request state (set by upstream or router)
        return getattr(request.state, "tenant_id", None)

