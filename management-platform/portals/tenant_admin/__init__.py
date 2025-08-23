"""
Tenant Admin Portal for DotMac Management Platform.

This portal provides self-service interface for ISP customers including:
- Instance configuration and customization tools
- Subscription management with usage tracking  
- Platform support and documentation access
- Tenant-specific analytics and reporting
- Instance scaling and backup management
"""

from .api import tenant_admin_router
from .schemas import (
    TenantInstanceOverview,
    InstanceConfigurationUpdate,
    UsageMetricsResponse,
    BillingPortalResponse,
    SupportTicketCreate,
)

__all__ = [
    "tenant_admin_router",
    "TenantInstanceOverview",
    "InstanceConfigurationUpdate", 
    "UsageMetricsResponse",
    "BillingPortalResponse",
    "SupportTicketCreate",
]