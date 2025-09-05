"""
SaaS Operations Automation API Endpoints

Self-service container provisioning and management API for resellers.
Leverages existing services with DRY principles for complete automation.
"""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.application import standard_exception_handler
from dotmac.database.base import get_db_session
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


# Pydantic models for API contracts
class TenantProvisioningRequest(BaseModel):
    """Request model for tenant container provisioning."""

    company_name: str = Field(..., min_length=2, max_length=100)
    subdomain: str = Field(..., min_length=3, max_length=63, regex=r"^[a-z0-9-]+$")
    contact_email: str = Field(..., regex=r"^[^@]+@[^@]+\.[^@]+$")
    plan: str = Field(default="standard", regex=r"^(standard|premium|enterprise)$")
    enabled_features: list[str] = Field(
        default_factory=lambda: [
            "customer_portal",
            "technician_portal",
            "billing",
            "notifications",
        ]
    )
    custom_domain: Optional[str] = Field(None, max_length=253)
    backup_enabled: bool = Field(default=True)


class ProvisioningResponse(BaseModel):
    """Response model for provisioning operations."""

    success: bool
    workflow_id: Optional[str] = None
    tenant_id: Optional[str] = None
    estimated_completion_time: Optional[str] = None
    tracking_url: Optional[str] = None
    error: Optional[str] = None


class ProvisioningStatusResponse(BaseModel):
    """Response model for provisioning status."""

    workflow_id: str
    status: str
    progress_percentage: float
    current_phase: str
    deployment_time: Optional[float] = None
    target_met: Optional[bool] = None
    estimated_completion: Optional[str] = None
    steps_completed: int
    total_steps: int
    errors: list[str] = Field(default_factory=list)


class UsageMetricRequest(BaseModel):
    """Request model for usage tracking."""

    tenant_id: str
    metric_type: str = Field(
        ...,
        regex=r"^(bandwidth_gb|storage_gb|api_calls_1000|active_users|email_sends_1000|sms_sends)$",
    )
    value: float = Field(..., gt=0)
    metadata: Optional[dict[str, Any]] = None


class UsageTrackingResponse(BaseModel):
    """Response model for usage tracking."""

    tenant_id: str
    metric_type: str
    value: float
    cost: float
    tracked_at: str
    processed: bool


class DecommissionRequest(BaseModel):
    """Request model for tenant decommissioning."""

    tenant_id: str
    reason: str = Field(default="Customer requested decommissioning")
    backup_data: bool = Field(default=True)
    force: bool = Field(
        default=False, description="Force decommission even if tenant is active"
    )


# API Router
router = APIRouter(prefix="/api/v1/saas-automation", tags=["SaaS Automation"])


@router.post("/provision", response_model=ProvisioningResponse)
@standard_exception_handler
async def provision_tenant_container(
    request: TenantProvisioningRequest,
    reseller_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Self-service tenant container provisioning for resellers.

    Leverages fast deployment optimizer for 4-minute target deployment.
    """
    try:
        # Import services (lazy loading for DRY)
        from dotmac_isp.modules.resellers.portal_interface import ResellerPortalService

        portal_service = ResellerPortalService(db)

        # Convert request to internal format
        customer_data = {
            "tenant_id": f"tenant_{request.subdomain}",
            "subdomain": request.subdomain,
            "company_name": request.company_name,
            "contact_email": request.contact_email,
            "plan": request.plan,
            "enabled_features": request.enabled_features,
            "custom_domain": request.custom_domain,
            "backup_enabled": request.backup_enabled,
        }

        # Start provisioning using integrated portal service
        result = await portal_service.provision_tenant_container(
            reseller_id=reseller_id, customer_data=customer_data
        )

        if result["success"]:
            # Add background task for progress monitoring
            background_tasks.add_task(
                _monitor_provisioning_progress, result["workflow_id"], reseller_id
            )

            return ProvisioningResponse(
                success=True,
                workflow_id=result["workflow_id"],
                tenant_id=result["tenant_id"],
                estimated_completion_time=result["estimated_completion_time"],
                tracking_url=result["tracking_url"],
            )
        else:
            return ProvisioningResponse(success=False, error=result["error"])

    except Exception as e:
        logger.error(f"Provisioning API error for reseller {reseller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/provision/status/{workflow_id}", response_model=ProvisioningStatusResponse
)
@standard_exception_handler
async def get_provisioning_status(
    workflow_id: str, db: AsyncSession = Depends(get_db_session)
):
    """
    Get real-time provisioning status and progress.

    Leverages enhanced provisioning service monitoring.
    """
    try:
        from dotmac_isp.modules.resellers.portal_interface import ResellerPortalService

        portal_service = ResellerPortalService(db)
        status = await portal_service.get_provisioning_status(workflow_id)

        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])

        return ProvisioningStatusResponse(
            workflow_id=status["workflow_id"],
            status=status["status"],
            progress_percentage=status["progress_percentage"],
            current_phase=status["current_phase"],
            deployment_time=status.get("deployment_time"),
            target_met=status.get("target_met"),
            estimated_completion=status.get("estimated_completion"),
            steps_completed=status["steps_completed"],
            total_steps=status["total_steps"],
            errors=status["errors"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status API error for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/containers")
@standard_exception_handler
async def list_tenant_containers(
    reseller_id: str, db: AsyncSession = Depends(get_db_session)
):
    """
    List all tenant containers for a reseller.

    Integrates with existing customer service for DRY data access.
    """
    try:
        from dotmac_isp.modules.resellers.portal_interface import ResellerPortalService

        portal_service = ResellerPortalService(db)
        containers = await portal_service.list_tenant_containers(reseller_id)

        if "error" in containers:
            raise HTTPException(status_code=500, detail=containers["error"])

        return {
            "reseller_id": reseller_id,
            "containers": containers["containers"],
            "summary": {
                "total_count": containers["total_count"],
                "active_count": containers["active_count"],
                "total_mrr": containers["total_mrr"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Container list API error for reseller {reseller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/dashboard/{reseller_id}")
@standard_exception_handler
async def get_saas_dashboard(
    reseller_id: str, db: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive SaaS automation dashboard data.

    Combines existing services with new automation capabilities.
    """
    try:
        from dotmac_isp.modules.resellers.portal_interface import ResellerPortalService

        portal_service = ResellerPortalService(db)
        dashboard_data = await portal_service.get_container_management_data(reseller_id)

        return {"reseller_id": reseller_id, "dashboard_data": dashboard_data}

    except Exception as e:
        logger.error(f"Dashboard API error for reseller {reseller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/usage/track", response_model=UsageTrackingResponse)
@standard_exception_handler
async def track_usage_metric(
    request: UsageMetricRequest, db: AsyncSession = Depends(get_db_session)
):
    """
    Track real-time usage metric for billing.

    Integrates with real-time usage billing system.
    """
    try:
        from dotmac_isp.modules.resellers.realtime_usage_billing import (
            get_usage_billing_service,
        )

        usage_service = await get_usage_billing_service(db)

        # Route to appropriate tracking method based on metric type
        if request.metric_type == "api_calls_1000":
            result = await usage_service.track_api_usage(
                request.tenant_id,
                request.metadata.get("endpoint", "unknown")
                if request.metadata
                else "unknown",
                int(request.value * 1000),
            )
        elif request.metric_type == "bandwidth_gb":
            bytes_transferred = int(request.value * (1024**3))
            result = await usage_service.track_bandwidth_usage(
                request.tenant_id, bytes_transferred
            )
        elif request.metric_type == "storage_gb":
            bytes_stored = int(request.value * (1024**3))
            result = await usage_service.track_storage_usage(
                request.tenant_id, bytes_stored
            )
        elif request.metric_type == "active_users":
            result = await usage_service.track_user_activity(
                request.tenant_id, int(request.value)
            )
        else:
            # Use generic tracking for other metric types
            usage_engine = usage_service.usage_engine
            result = await usage_engine.track_usage(
                request.tenant_id, request.metric_type, request.value, request.metadata
            )

        return UsageTrackingResponse(
            tenant_id=result["tenant_id"],
            metric_type=result["metric_type"],
            value=result["value"],
            cost=result["cost"],
            tracked_at=result["tracked_at"],
            processed=result["processed"],
        )

    except Exception as e:
        logger.error(f"Usage tracking API error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/usage/summary/{tenant_id}")
@standard_exception_handler
async def get_usage_summary(tenant_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Get real-time usage summary for tenant.

    Shows current unbilled usage and costs.
    """
    try:
        from dotmac_isp.modules.resellers.realtime_usage_billing import (
            get_usage_billing_service,
        )

        usage_service = await get_usage_billing_service(db)
        summary = await usage_service.get_realtime_usage_summary(tenant_id)

        return summary

    except Exception as e:
        logger.error(f"Usage summary API error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/billing/run")
@standard_exception_handler
async def create_usage_billing_run(
    reseller_ids: Optional[list[str]] = None,
    period_hours: int = 24,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create usage-based billing run.

    Leverages existing commission automation workflow.
    """
    try:
        from dotmac_isp.modules.resellers.realtime_usage_billing import (
            get_usage_billing_service,
        )

        usage_service = await get_usage_billing_service(db)
        usage_engine = usage_service.usage_engine

        # Start billing run
        billing_run = await usage_engine.create_usage_based_billing_run(
            reseller_ids=reseller_ids, period_hours=period_hours
        )

        return {
            "billing_run_id": billing_run["execution_id"],
            "workflow_id": billing_run["workflow_id"],
            "period_hours": period_hours,
            "reseller_count": len(reseller_ids) if reseller_ids else "all",
            "status": billing_run["status"],
        }

    except Exception as e:
        logger.error(f"Billing run API error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/decommission", response_model=ProvisioningResponse)
@standard_exception_handler
async def decommission_tenant(
    request: DecommissionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Decommission tenant container with automated cleanup.

    Leverages enhanced provisioning service decommissioning workflow.
    """
    try:
        from dotmac_management.services.enhanced_tenant_provisioning import (
            EnhancedTenantProvisioningService,
        )

        # Get tenant database ID from tenant_id
        with get_db_session() as session:
            from dotmac_management.models.tenant import CustomerTenant

            tenant = (
                session.query(CustomerTenant)
                .filter_by(tenant_id=request.tenant_id)
                .first()
            )
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")

            if not request.force and tenant.status != "active":
                raise HTTPException(
                    status_code=400,
                    detail="Tenant is not active. Use force=true to override.",
                )

        # Initialize provisioning service
        provisioning_service = EnhancedTenantProvisioningService()
        await provisioning_service.initialize()

        # Start decommissioning workflow
        workflow_id = await provisioning_service.decommission_tenant(
            tenant_db_id=tenant.id,
            reason=request.reason,
            backup_data=request.backup_data,
        )

        # Add background monitoring
        background_tasks.add_task(
            _monitor_decommissioning_progress, workflow_id, request.tenant_id
        )

        return ProvisioningResponse(
            success=True,
            workflow_id=workflow_id,
            tenant_id=request.tenant_id,
            estimated_completion_time="30 minutes",
            tracking_url=f"/api/v1/saas-automation/provision/status/{workflow_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Decommission API error for tenant {request.tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/analytics/{reseller_id}")
@standard_exception_handler
async def get_usage_analytics(
    reseller_id: str, days: int = 30, db: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive usage billing analytics.

    Leverages existing commission reporting with usage data.
    """
    try:
        from dotmac_isp.modules.resellers.realtime_usage_billing import (
            get_usage_billing_service,
        )

        usage_service = await get_usage_billing_service(db)
        usage_engine = usage_service.usage_engine

        analytics = await usage_engine.get_usage_billing_analytics(reseller_id, days)

        return {"reseller_id": reseller_id, "period_days": days, "analytics": analytics}

    except Exception as e:
        logger.error(f"Analytics API error for reseller {reseller_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Background task functions
async def _monitor_provisioning_progress(workflow_id: str, reseller_id: str):
    """Background task to monitor provisioning progress."""
    try:
        logger.info(
            f"Started monitoring provisioning {workflow_id} for reseller {reseller_id}"
        )
        # Implementation would send periodic status updates via webhooks or notifications
    except Exception as e:
        logger.error(f"Error monitoring provisioning {workflow_id}: {e}")


async def _monitor_decommissioning_progress(workflow_id: str, tenant_id: str):
    """Background task to monitor decommissioning progress."""
    try:
        logger.info(
            f"Started monitoring decommissioning {workflow_id} for tenant {tenant_id}"
        )
        # Implementation would send periodic status updates
    except Exception as e:
        logger.error(f"Error monitoring decommissioning {workflow_id}: {e}")


# Health check endpoint
@router.get("/health")
async def saas_automation_health():
    """Health check for SaaS automation API."""
    return {
        "status": "healthy",
        "service": "saas-automation-api",
        "features": [
            "4-minute container provisioning",
            "real-time usage billing",
            "automated decommissioning",
            "self-service portal integration",
        ],
    }
