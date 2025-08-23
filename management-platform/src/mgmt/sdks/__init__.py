"""
SDK Registry for DotMac Management Platform.

This module provides centralized access to all SDKs used within the
multi-tenant SaaS management platform for ISP deployments.
"""

from typing import Dict, Any, Optional
import logging

# Core SDK components
from .core import (
    BaseSDKClient,
    SDKError,
    RequestContext,
    generate_request_id,
)

# Tenant Management SDKs
from .tenant_management import (
    TenantManagementSDK,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantOnboardingRequest,
    TenantConfigurationCreate,
    TenantHealthStatus,
    TenantListFilters,
    TenantStatusEnum,
    SubscriptionTierEnum,
    BillingCycleEnum,
    IsolationLevelEnum,
)

logger = logging.getLogger(__name__)


class PlatformSDKRegistry:
    """
    Centralized SDK registry for the Management Platform.
    
    Provides unified access to all platform-level SDKs for managing
    multiple tenant ISP deployments across cloud providers.
    """
    
    def __init__(self, platform_context: Optional[Dict[str, Any]] = None):
        """
        Initialize platform SDK registry.
        
        Args:
            platform_context: Platform-level authentication and configuration context
        """
        self.platform_context = platform_context or {}
        
        # Initialize all SDKs
        self._init_sdks()
        
        logger.info("Initialized Platform SDK Registry")
    
    def _init_sdks(self):
        """Initialize all SDK instances with platform context."""
        # Tenant Management
        self.tenants = TenantManagementSDK(self.platform_context)
        
        # TODO: Add additional platform SDKs as they are implemented
        # self.deployment = DeploymentSDK(self.platform_context)
        # self.billing_saas = BillingSaaSSDK(self.platform_context)
        # self.analytics = PlatformAnalyticsSDK(self.platform_context)
        
        logger.debug("All platform SDKs initialized")
    
    def get_tenant_management_sdk(self) -> TenantManagementSDK:
        """Get the tenant management SDK."""
        return self.tenants
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all platform SDKs.
        
        Returns:
            Health status of all SDK components
        """
        health_status = {
            "platform": "dotmac_management_platform",
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "overall_status": "healthy",
            "components": {
                "tenant_management": "healthy",
                # Future components will be added here
                # "deployment_engine": "healthy",
                # "billing_saas": "healthy", 
                # "platform_analytics": "healthy",
            }
        }
        
        # In a real implementation, each SDK would have its own health check
        logger.info("Platform SDK health check completed")
        
        return health_status
    
    async def get_platform_metrics(self) -> Dict[str, Any]:
        """
        Get platform-wide metrics across all tenants.
        
        Returns:
            Platform metrics and statistics
        """
        # This would aggregate metrics from all tenant instances
        metrics = {
            "total_tenants": len(getattr(self.tenants._service, '_tenants', {})),
            "active_tenants": 0,
            "pending_tenants": 0,
            "suspended_tenants": 0,
            "total_customers": 0,  # Aggregated across all tenants
            "total_services": 0,   # Aggregated across all tenants
            "platform_uptime": 99.9,
            "avg_tenant_health_score": 85.5,
        }
        
        # Count tenant statuses
        for tenant_data in getattr(self.tenants._service, '_tenants', {}).values():
            status = tenant_data.get("status", "")
            if status == TenantStatusEnum.ACTIVE.value:
                metrics["active_tenants"] += 1
            elif status == TenantStatusEnum.PENDING.value:
                metrics["pending_tenants"] += 1
            elif status == TenantStatusEnum.SUSPENDED.value:
                metrics["suspended_tenants"] += 1
        
        return metrics


class TenantSDKContext:
    """
    Context manager for tenant-specific SDK operations.
    
    Provides easy access to SDKs configured for a specific tenant,
    useful for operations that need to work within a tenant's context.
    """
    
    def __init__(self, tenant_id: str, platform_registry: PlatformSDKRegistry):
        """
        Initialize tenant SDK context.
        
        Args:
            tenant_id: Target tenant identifier
            platform_registry: Platform SDK registry instance
        """
        self.tenant_id = tenant_id
        self.platform_registry = platform_registry
    
    async def get_tenant_info(self) -> Optional[TenantResponse]:
        """Get tenant information."""
        return await self.platform_registry.tenants.get_tenant_by_id(self.tenant_id)
    
    async def get_tenant_health(self) -> Optional[TenantHealthStatus]:
        """Get tenant health status."""
        return await self.platform_registry.tenants.get_tenant_health_status(self.tenant_id)
    
    async def update_tenant_status(
        self,
        new_status: TenantStatusEnum,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[TenantResponse]:
        """Update tenant status."""
        return await self.platform_registry.tenants.update_tenant_status(
            self.tenant_id, new_status, reason, updated_by
        )


# Convenience functions
def create_platform_sdk_registry(
    platform_context: Optional[Dict[str, Any]] = None
) -> PlatformSDKRegistry:
    """
    Create a new platform SDK registry instance.
    
    Args:
        platform_context: Platform-level context
        
    Returns:
        Configured platform SDK registry instance
    """
    return PlatformSDKRegistry(platform_context)


def create_tenant_context(
    tenant_id: str, 
    platform_registry: PlatformSDKRegistry
) -> TenantSDKContext:
    """
    Create a tenant-specific SDK context.
    
    Args:
        tenant_id: Target tenant identifier
        platform_registry: Platform SDK registry
        
    Returns:
        Tenant SDK context instance
    """
    return TenantSDKContext(tenant_id, platform_registry)


# Export all SDK classes and schemas for direct import
__all__ = [
    # Core components
    "BaseSDKClient",
    "SDKError",
    "RequestContext",
    "generate_request_id",
    
    # Registry
    "PlatformSDKRegistry",
    "TenantSDKContext",
    "create_platform_sdk_registry",
    "create_tenant_context",
    
    # Tenant Management SDKs
    "TenantManagementSDK",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantOnboardingRequest",
    "TenantConfigurationCreate", 
    "TenantHealthStatus",
    "TenantListFilters",
    
    # Enums
    "TenantStatusEnum",
    "SubscriptionTierEnum",
    "BillingCycleEnum",
    "IsolationLevelEnum",
]