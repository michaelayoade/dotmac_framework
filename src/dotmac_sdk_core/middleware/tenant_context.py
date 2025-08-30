"""Tenant context middleware."""

from typing import Any, Dict

from .base import RequestMiddleware


class TenantContextMiddleware(RequestMiddleware):
    """Middleware for handling tenant context."""

    def __init__(self, tenant_id: str, tenant_header: str = "X-Tenant-ID"):
        self.tenant_id = tenant_id
        self.tenant_header = tenant_header

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add tenant context to request headers."""
        if "headers" not in request_data:
            request_data["headers"] = {}

        request_data["headers"][self.tenant_header] = self.tenant_id
        return request_data
