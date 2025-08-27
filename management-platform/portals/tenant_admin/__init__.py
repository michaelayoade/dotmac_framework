"""
Tenant Admin Portal for DotMac Management Platform.

This portal provides self-service interface for ISP customers including:
- Instance configuration and customization tools
- Subscription management with usage tracking  
- Platform support and documentation access
- Tenant-specific analytics and reporting
- Instance scaling and backup management
"""

from .router import tenant_admin_api_router as tenant_admin_router

__all__ = [
    "tenant_admin_router",
]