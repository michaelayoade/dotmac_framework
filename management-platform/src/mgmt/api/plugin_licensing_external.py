"""External API endpoints for plugin licensing - used by ISP Framework instances."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from mgmt.shared.database import get_async_session
from mgmt.services.plugin_licensing.service import PluginLicensingService
from mgmt.services.plugin_licensing.models import PluginTier, LicenseStatus
from mgmt.services.plugin_licensing.exceptions import PluginNotFoundError, LicenseExpiredError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/plugin-licensing", tags=["Plugin Licensing External"])


class LicenseValidationResponse(BaseModel):
    """Response model for license validation."""
    plugin_id: str
    tenant_id: str
    is_valid: bool
    license_status: str
    tier: str
    features: List[str] = Field(default_factory=list)
    usage_limits: Dict[str, int] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    reason: Optional[str] = None


class UsageMetricRequest(BaseModel):
    """Usage metric report request."""
    plugin_id: str
    metric_name: str
    usage_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsageReportRequest(BaseModel):
    """Usage report request."""
    tenant_id: str
    plugin_id: str
    metrics: List[UsageMetricRequest]


class HealthStatusReport(BaseModel):
    """Health status report from ISP Framework."""
    tenant_id: str
    component: str
    status: str  # healthy, unhealthy, warning
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[str] = None


def get_tenant_id_from_header(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant ID from header."""
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required"
        )
    return x_tenant_id


@router.get("/validate/{tenant_id}", response_model=LicenseValidationResponse)
async def validate_plugin_license(
    tenant_id: str,
    plugin_id: str,
    feature: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """Validate plugin license for ISP Framework instance.
    
    This endpoint is called by ISP Framework instances to validate
    plugin licenses before allowing plugin activation or feature access.
    """
    try:
        logger.info(f"Validating license for plugin {plugin_id}, tenant {tenant_id}")
        
        licensing_service = PluginLicensingService(session)
        
        # Get plugin subscription
        subscription = await licensing_service.get_active_plugin_subscription(tenant_id, plugin_id)
        
        if not subscription:
            return LicenseValidationResponse(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                is_valid=False,
                license_status="not_found",
                tier="free",
                reason="No active subscription found"
            )
        
        # Check if license is expired
        if subscription.expires_at and subscription.expires_at < datetime.utcnow():
            return LicenseValidationResponse(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                is_valid=False,
                license_status="expired",
                tier=subscription.tier.value,
                expires_at=subscription.expires_at,
                reason="License expired"
            )
        
        # Check trial status
        if subscription.is_trial and subscription.trial_ends_at and subscription.trial_ends_at < datetime.utcnow():
            return LicenseValidationResponse(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                is_valid=False,
                license_status="trial_expired",
                tier=subscription.tier.value,
                trial_ends_at=subscription.trial_ends_at,
                reason="Trial period expired"
            )
        
        # Get available features for this tier
        features = []
        if subscription.feature_entitlements:
            features = [ent.feature_name for ent in subscription.feature_entitlements if ent.is_enabled]
        
        # Check specific feature access if requested
        if feature and feature not in features:
            return LicenseValidationResponse(
                plugin_id=plugin_id,
                tenant_id=tenant_id,
                is_valid=False,
                license_status="feature_not_available",
                tier=subscription.tier.value,
                features=features,
                reason=f"Feature '{feature}' not available in {subscription.tier.value} tier"
            )
        
        # Build usage limits
        usage_limits = {}
        if subscription.usage_limits:
            if isinstance(subscription.usage_limits, dict):
                tier_limits = subscription.usage_limits.get(subscription.tier.value, subscription.usage_limits.get("default", {}))
                if isinstance(tier_limits, dict):
                    usage_limits = tier_limits
        
        return LicenseValidationResponse(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            is_valid=True,
            license_status=subscription.status.value,
            tier=subscription.tier.value,
            features=features,
            usage_limits=usage_limits,
            expires_at=subscription.expires_at,
            trial_ends_at=subscription.trial_ends_at
        )
        
    except Exception as e:
        logger.error(f"Error validating license for {plugin_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during license validation"
        )


@router.post("/usage", status_code=status.HTTP_201_CREATED)
async def report_plugin_usage(
    request: UsageReportRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Report plugin usage metrics from ISP Framework instance.
    
    This endpoint receives usage metrics from ISP Framework instances
    for billing and compliance tracking.
    """
    try:
        logger.info(f"Received {len(request.metrics)} usage metrics for plugin {request.plugin_id}")
        
        licensing_service = PluginLicensingService(session)
        
        # Verify plugin subscription exists
        subscription = await licensing_service.get_active_plugin_subscription(
            request.tenant_id, 
            request.plugin_id
        )
        
        if not subscription:
            logger.warning(f"No subscription found for plugin {request.plugin_id}, tenant {request.tenant_id}")
            # Don't fail - just log the attempt
            return {"status": "recorded", "message": "Usage recorded (no active subscription)"}
        
        # Record each metric
        recorded_count = 0
        for metric in request.metrics:
            try:
                await licensing_service.record_plugin_usage(
                    tenant_id=request.tenant_id,
                    plugin_id=request.plugin_id,
                    metric_name=metric.metric_name,
                    usage_count=metric.usage_count,
                    timestamp=metric.timestamp,
                    metadata=metric.metadata
                )
                recorded_count += 1
                
            except Exception as e:
                logger.error(f"Failed to record metric {metric.metric_name}: {str(e)}")
                continue
        
        logger.info(f"Successfully recorded {recorded_count}/{len(request.metrics)} metrics")
        
        return {
            "status": "recorded",
            "recorded_count": recorded_count,
            "total_metrics": len(request.metrics)
        }
        
    except Exception as e:
        logger.error(f"Error recording plugin usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while recording usage"
        )


@router.post("/health-status", status_code=status.HTTP_201_CREATED)
async def report_health_status(
    request: HealthStatusReport,
    session: AsyncSession = Depends(get_async_session)
):
    """Report health status from ISP Framework instance.
    
    This endpoint receives health status reports from ISP Framework instances
    for monitoring and SLA compliance.
    """
    try:
        logger.debug(f"Health status report from tenant {request.tenant_id}: {request.component} = {request.status}")
        
        # Import here to avoid circular imports
        from mgmt.services.saas_monitoring.service import SaaSMonitoringService
        
        monitoring_service = SaaSMonitoringService(session)
        
        # Record health status
        await monitoring_service.record_external_health_report(
            tenant_id=request.tenant_id,
            component=request.component,
            status=request.status,
            metrics=request.metrics,
            details=request.details,
            timestamp=request.timestamp
        )
        
        return {"status": "recorded", "timestamp": request.timestamp.isoformat()}
        
    except Exception as e:
        logger.error(f"Error recording health status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while recording health status"
        )


@router.get("/tenant/{tenant_id}/subscriptions")
async def get_tenant_plugin_subscriptions(
    tenant_id: str,
    active_only: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """Get plugin subscriptions for tenant (used by ISP Framework for initialization)."""
    try:
        licensing_service = PluginLicensingService(session)
        
        subscriptions = await licensing_service.get_tenant_plugin_subscriptions(
            tenant_id=tenant_id,
            active_only=active_only
        )
        
        return {
            "tenant_id": tenant_id,
            "subscription_count": len(subscriptions),
            "subscriptions": [
                {
                    "plugin_id": sub.plugin_id,
                    "tier": sub.tier.value,
                    "status": sub.status.value,
                    "is_trial": sub.is_trial,
                    "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                    "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                    "license_key": sub.license_key,
                    "features": [ent.feature_name for ent in sub.feature_entitlements if ent.is_enabled] if sub.feature_entitlements else []
                }
                for sub in subscriptions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting tenant subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting subscriptions"
        )


@router.get("/usage-summary/{tenant_id}/{plugin_id}")
async def get_plugin_usage_summary(
    tenant_id: str,
    plugin_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """Get usage summary for plugin (used for billing validation)."""
    try:
        licensing_service = PluginLicensingService(session)
        
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        usage_summary = await licensing_service.get_plugin_usage_summary(
            tenant_id=tenant_id,
            plugin_id=plugin_id,
            start_date=start_dt.date() if start_dt else None,
            end_date=end_dt.date() if end_dt else None
        )
        
        return usage_summary
        
    except Exception as e:
        logger.error(f"Error getting usage summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting usage summary"
        )