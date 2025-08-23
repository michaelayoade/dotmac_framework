"""
Master Admin Portal for DotMac Management Platform.

This portal provides platform operations interface for DotMac staff including:
- Tenant management with ISP customer onboarding workflows
- Infrastructure monitoring and deployment management  
- Cross-tenant analytics and business intelligence
- Platform health monitoring and performance dashboards
- SaaS billing and subscription management
"""

from .api import master_admin_router
from .schemas import (
    PlatformOverviewResponse,
    TenantOnboardingWorkflow,
    InfrastructureDeploymentRequest,
    CrossTenantAnalytics,
)

__all__ = [
    "master_admin_router",
    "PlatformOverviewResponse",
    "TenantOnboardingWorkflow", 
    "InfrastructureDeploymentRequest",
    "CrossTenantAnalytics",
]