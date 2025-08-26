"""
Tenant Admin Portal API endpoints for ISP customer self-service management.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...src.mgmt.shared.database.connections import get_db
from ...src.mgmt.shared.auth.permissions import require_tenant_admin, get_current_tenant
from ...src.mgmt.services.tenant_management import TenantManagementService
from .schemas import ()
    TenantInstanceOverview,
    InstanceConfigurationUpdate,
    InstanceConfigurationCategory,
    ScalingConfiguration,
    BackupConfiguration,
    UsageMetricsResponse,
    BillingPortalResponse,
    SupportTicketCreate,
    SupportTicketResponse,
    CustomBrandingSettings,
    IntegrationConfiguration,
    UserManagementUser,
    UserManagementCreateUser,
    AnalyticsReport,
    MaintenanceWindow,
    FeatureToggle,
, timezone)

logger = logging.getLogger(__name__)

# Create the Tenant Admin Portal router
tenant_admin_router = APIRouter()
    prefix="/api/v1/tenant-admin",
    tags=["Tenant Admin Portal"],
    dependencies=[Depends(require_tenant_admin)],
)


# Dashboard and Instance Overview
@tenant_admin_router.get("/dashboard/overview", response_model=TenantInstanceOverview)
async def get_instance_overview():
    db: AsyncSession = Depends(get_db),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> TenantInstanceOverview:
    """
    Get comprehensive overview of tenant's DotMac instance.
    
    This endpoint provides:
    - Instance status and health metrics
    - Current usage and resource utilization
    - Subscription and billing information
    - Recent activity summary
    """
    tenant_service = TenantManagementService(db)
    tenant_id = current_tenant["tenant_id"]
    
    try:
        # Get tenant details
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        
        # Get health status
        health_status = await tenant_service.get_tenant_health_status(tenant_id)
        if not health_status:
            raise HTTPException()
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to retrieve instance health",
            )
        
        # Get usage summary
        usage_summary = await tenant_service.get_tenant_usage_summary(tenant_id)
        
        # Mock health metrics (would integrate with monitoring service)
        health_metrics = {
            "uptime_percentage": health_status.uptime_percentage or 99.5,
            "avg_response_time_ms": health_status.response_time_ms or 185,
            "requests_per_minute": 1250,
            "error_rate_percentage": (health_status.error_rate or 0.001) * 100,
            "cpu_usage_percentage": 45.2,
            "memory_usage_percentage": 68.7,
            "storage_usage_percentage": usage_summary.get("utilization", {}).get("storage_percent", 0),
            "database_status": "healthy",
            "cache_status": "healthy", 
            "queue_status": "healthy",
            "last_updated": datetime.now(timezone.utc),
        }
        
        return TenantInstanceOverview()
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.display_name,
            instance_url=f"https://{tenant.custom_domain or f'{tenant.tenant_id}.dotmac.cloud'}",
            custom_domain=tenant.custom_domain,
            status=tenant.status,
            health_score=health_status.health_score,
            last_health_check=health_status.last_health_check,
            subscription_tier=tenant.subscription_tier,
            billing_cycle=tenant.billing_cycle,
            next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
            current_customers=usage_summary.get("current_usage", {}).get("active_customers", 0),
            current_services=usage_summary.get("current_usage", {}).get("active_services", 0),
            storage_used_gb=usage_summary.get("current_usage", {}).get("storage_used_gb", 0),
            storage_limit_gb=tenant.max_storage_gb,
            health_metrics=health_metrics,
            recent_logins=156,
            recent_api_calls=12450,
            recent_tickets=2,
            active_alerts=health_status.active_alerts,
            pending_updates=1,
            scheduled_maintenance=None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get instance overview for tenant {tenant_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve instance overview",
        )


# Instance Management
@tenant_admin_router.get("/instance/configuration", response_model=List[InstanceConfigurationCategory])
async def get_instance_configuration():
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> List[InstanceConfigurationCategory]:
    """Get current instance configuration settings organized by category."""
    # Mock configuration categories (would integrate with configuration service)
    return [
        InstanceConfigurationCategory()
            category="general",
            display_name="General Settings",
            description="Basic instance configuration settings",
            settings={
                "instance_name": "My ISP Platform",
                "timezone": "UTC",
                "default_language": "en",
                "date_format": "YYYY-MM-DD",
                "currency": "USD",
            },
            editable_by_tenant=True,
            requires_restart=False,
        ),
        InstanceConfigurationCategory()
            category="branding",
            display_name="Branding & Appearance",
            description="Customize the look and feel of your platform",
            settings={
                "primary_color": "#1f2937",
                "logo_url": "https://example.com/logo.png",
                "favicon_url": "https://example.com/favicon.ico",
                "company_name": "My ISP Company",
            },
            editable_by_tenant=True,
            requires_restart=False,
        ),
        InstanceConfigurationCategory()
            category="features",
            display_name="Feature Settings",
            description="Enable or disable platform features",
            settings={
                "customer_self_service": True,
                "api_access": True,
                "advanced_analytics": False,
                "white_labeling": True,
            },
            editable_by_tenant=True,
            requires_restart=True,
        ),
        InstanceConfigurationCategory()
            category="security",
            display_name="Security Settings",
            description="Security and authentication settings",
            settings={
                "session_timeout_minutes": 60,
                "password_complexity": "medium",
                "two_factor_auth": True,
                "ip_whitelist_enabled": False,
            },
            editable_by_tenant=False,  # Managed by platform admin
            requires_restart=True,
        ),
    ]


@tenant_admin_router.put("/instance/configuration")
async def update_instance_configuration():
    config_update: InstanceConfigurationUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
):
    """Update instance configuration settings."""
    tenant_service = TenantManagementService(db)
    tenant_id = current_tenant["tenant_id"]
    
    try:
        # Validate tenant exists
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        
        # Create configuration record
        from ...src.mgmt.services.tenant_management.schemas import TenantConfigurationCreate
        config_data = TenantConfigurationCreate()
            category=config_update.category,
            configuration_key="tenant_settings",
            configuration_value=config_update.settings,
        )
        
        await tenant_service.create_tenant_configuration()
            tenant.id,
            config_data,
            current_user.get("user_id"),
        )
        
        # Schedule maintenance if required
        if not config_update.apply_immediately and config_update.schedule_maintenance:
            # background_tasks.add_task(schedule_configuration_update, tenant_id, config_update)
            return {"message": "Configuration update scheduled", "maintenance_window": config_update.schedule_maintenance}
        
        # Apply immediately (would integrate with instance management service)
        # background_tasks.add_task(apply_configuration_update, tenant_id, config_update)
        
        return {"message": "Configuration updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update configuration for tenant {tenant_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update instance configuration",
        )


@tenant_admin_router.get("/instance/scaling", response_model=ScalingConfiguration)
async def get_scaling_configuration():
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> ScalingConfiguration:
    """Get current instance scaling configuration and options."""
    # Mock scaling configuration (would integrate with infrastructure service)
    return ScalingConfiguration()
        current_cpu_cores=4,
        current_memory_gb=16,
        current_storage_gb=100,
        target_cpu_cores=4,
        target_memory_gb=16,
        target_storage_gb=100,
        auto_scaling_enabled=False,
        min_instances=1,
        max_instances=3,
        scale_up_threshold=80,
        scale_down_threshold=30,
        estimated_hourly_cost=12.50,
        estimated_monthly_cost=9000.00,
    )


@tenant_admin_router.put("/instance/scaling")
async def update_scaling_configuration():
    scaling_config: ScalingConfiguration,
    background_tasks: BackgroundTasks,
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
):
    """Update instance scaling configuration."""
    tenant_id = current_tenant["tenant_id"]
    
    try:
        # Validate scaling request (would include cost calculations)
        if scaling_config.target_cpu_cores > 32:
            raise HTTPException()
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPU cores cannot exceed 32 for this subscription tier",
            )
        
        # Start scaling operation
        # background_tasks.add_task(scale_instance, tenant_id, scaling_config)
        
        scaling_id = f"scale_{tenant_id}_{int(datetime.now(timezone.utc).timestamp()}"
        
        return {
            "message": "Instance scaling initiated",
            "scaling_id": scaling_id,
            "estimated_completion_minutes": 15,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to scale instance for tenant {tenant_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate instance scaling",
        )


@tenant_admin_router.get("/instance/backups", response_model=BackupConfiguration)
async def get_backup_configuration():
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> BackupConfiguration:
    """Get backup configuration and recent backup status."""
    # Mock backup configuration (would integrate with backup service)
    return BackupConfiguration()
        backup_enabled=True,
        backup_frequency="daily",
        backup_retention_days=30,
        backup_time="02:00",
        backup_storage_used_gb=25.7,
        backup_storage_limit_gb=500,
        last_backup=datetime.now(timezone.utc) - timedelta(hours=8),
        last_backup_status="success",
        available_restore_points=30,
    )


@tenant_admin_router.post("/instance/backups/create")
async def create_manual_backup():
    background_tasks: BackgroundTasks,
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
):
    """Create manual backup of the instance."""
    tenant_id = current_tenant["tenant_id"]
    
    # Start manual backup
    # background_tasks.add_task(create_instance_backup, tenant_id, "manual")
    
    backup_id = f"backup_{tenant_id}_{int(datetime.now(timezone.utc).timestamp()}"
    
    return {
        "message": "Manual backup initiated",
        "backup_id": backup_id,
        "estimated_completion_minutes": 30,
    }


# Usage and Analytics
@tenant_admin_router.get("/usage/metrics", response_model=UsageMetricsResponse)
async def get_usage_metrics():
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    db: AsyncSession = Depends(get_db),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> UsageMetricsResponse:
    """Get detailed usage metrics for the specified period."""
    tenant_service = TenantManagementService(db)
    tenant_id = current_tenant["tenant_id"]
    
    try:
        usage_summary = await tenant_service.get_tenant_usage_summary(tenant_id, period_days)
        
        if not usage_summary or "current_usage" not in usage_summary:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usage data not available",
            )
        
        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)
        period_end = datetime.now(timezone.utc)
        
        current_usage = usage_summary["current_usage"]
        performance = usage_summary.get("performance", {})
        
        return UsageMetricsResponse()
            period_start=period_start,
            period_end=period_end,
            customers_active=current_usage.get("active_customers", 0),
            customers_new=25,  # Mock data
            customers_churned=3,  # Mock data
            services_active=current_usage.get("active_services", 0),
            services_provisioned=127,  # Mock data
            services_deprovisioned=8,   # Mock data
            storage_used_gb=current_usage.get("storage_used_gb", 0),
            bandwidth_used_gb=current_usage.get("bandwidth_used_gb", 0),
            api_requests_total=performance.get("total_api_requests", 0),
            avg_response_time_ms=performance.get("avg_response_time_ms", 0),
            uptime_percentage=performance.get("avg_uptime_percent", 99.5),
            error_count=45,  # Mock data
            customers_growth_rate=8.5,
            services_growth_rate=12.3,
            storage_growth_rate=5.2,
            api_usage_growth_rate=15.7,
            storage_utilization_percentage=usage_summary.get("utilization", {}).get("storage_percent", 0),
            bandwidth_utilization_percentage=45.2,  # Mock data
            infrastructure_cost=2850.00,
            feature_costs={"advanced_analytics": 150.00, "white_labeling": 300.00},
            total_cost=3300.00,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage metrics for tenant {tenant_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage metrics",
        )


# Billing Portal
@tenant_admin_router.get("/billing/portal", response_model=BillingPortalResponse)
async def get_billing_portal():
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> BillingPortalResponse:
    """Get billing portal information including subscription and payment details."""
    tenant_id = current_tenant["tenant_id"]
    
    # Mock billing data (would integrate with billing service)
    return BillingPortalResponse()
        subscription_id=f"sub_{tenant_id}",
        subscription_tier="standard",
        billing_cycle="monthly",
        current_period_start=datetime.now(timezone.utc) - timedelta(days=15),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=15),
        next_billing_date=datetime.now(timezone.utc) + timedelta(days=15),
        current_amount=2500.00,
        next_amount=2650.00,
        usage_charges={"api_requests": 150.00, "storage_overage": 75.00},
        overage_charges={"bandwidth": 25.00},
        payment_methods=[
            {
                "payment_method_id": "pm_123",
                "type": "card",
                "card_brand": "visa",
                "card_last_four": "4242",
                "card_exp_month": 12,
                "card_exp_year": 2025,
                "is_default": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            }
        ],
        default_payment_method="pm_123",
        recent_invoices=[
            {
                "invoice_id": "inv_456",
                "invoice_date": datetime.now(timezone.utc) - timedelta(days=30),
                "due_date": datetime.now(timezone.utc) - timedelta(days=23),
                "period_start": datetime.now(timezone.utc) - timedelta(days=45),
                "period_end": datetime.now(timezone.utc) - timedelta(days=15),
                "subtotal": 2500.00,
                "tax_amount": 225.00,
                "total_amount": 2725.00,
                "amount_paid": 2725.00,
                "amount_due": 0.00,
                "status": "paid",
                "payment_date": datetime.now(timezone.utc) - timedelta(days=22),
                "line_items": [
                    {"description": "Standard Plan", "amount": 2500.00, "quantity": 1},
                    {"description": "API Overages", "amount": 150.00, "quantity": 1},
                ],
                "payment_method": "Visa ending in 4242",
                "download_url": f"https://billing.dotmac.cloud/invoices/inv_456.pdf",
            }
        ],
        account_status="active",
        days_overdue=0,
        usage_alerts=[],
        payment_alerts=[],
    )


# Support Portal
@tenant_admin_router.post("/support/tickets", response_model=SupportTicketResponse)
async def create_support_ticket():
    ticket_data: SupportTicketCreate,
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> SupportTicketResponse:
    """Create a new support ticket."""
    tenant_id = current_tenant["tenant_id"]
    
    # Generate ticket ID
    ticket_id = f"TKT-{tenant_id.upper()}-{int(datetime.now(timezone.utc).timestamp()}"
    
    # Determine SLA based on priority
    sla_hours = {"low": 72, "normal": 24, "high": 8, "urgent": 2}
    response_sla = sla_hours.get(ticket_data.priority, 24)
    resolution_sla = response_sla * 4
    
    # Mock ticket creation (would integrate with support system)
    return SupportTicketResponse()
        ticket_id=ticket_id,
        subject=ticket_data.subject,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority,
        status="new",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        response_sla_hours=response_sla,
        resolution_sla_hours=resolution_sla,
    )


@tenant_admin_router.get("/support/tickets", response_model=List[SupportTicketResponse])
async def list_support_tickets():
    status: Optional[str] = Query(None, description="Filter by ticket status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> List[SupportTicketResponse]:
    """List support tickets for the tenant."""
    # Mock ticket list (would integrate with support system)
    return [
        SupportTicketResponse()
            ticket_id="TKT-TENANT123-1234567890",
            subject="API rate limiting issue",
            description="Experiencing rate limiting on customer API endpoints",
            category="technical",
            priority="high",
            status="in_progress",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=6),
            assigned_to="support@dotmac.com",
            assigned_at=datetime.now(timezone.utc) - timedelta(days=1),
            response_sla_hours=8,
            resolution_sla_hours=32,
            time_to_first_response=4,
        ),
    ]


# Branding and Customization
@tenant_admin_router.get("/branding", response_model=CustomBrandingSettings)
async def get_branding_settings():
    db: AsyncSession = Depends(get_db),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
) -> CustomBrandingSettings:
    """Get current branding and customization settings."""
    tenant_service = TenantManagementService(db)
    tenant_id = current_tenant["tenant_id"]
    
    # Get branding configurations
    branding_configs = await tenant_service.get_tenant_configurations()
        tenant_id, category="branding"
    )
    
    # Extract branding settings or use defaults
    default_settings = CustomBrandingSettings()
        company_name=current_tenant.get("tenant_name", "My ISP Company"),
        support_email=current_tenant.get("primary_contact_email", "support@example.com"),
    )
    
    # Merge with stored configurations
    for config in branding_configs:
        if config.configuration_key == "branding_settings" and config.configuration_value:
            # Update default settings with stored values
            for key, value in config.configuration_value.items():
                if hasattr(default_settings, key):
                    setattr(default_settings, key, value)
    
    return default_settings


@tenant_admin_router.put("/branding")
async def update_branding_settings():
    branding_settings: CustomBrandingSettings,
    db: AsyncSession = Depends(get_db),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
):
    """Update branding and customization settings."""
    tenant_service = TenantManagementService(db)
    tenant_id = current_tenant["tenant_id"]
    
    try:
        tenant = await tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        
        # Create or update branding configuration
        from ...src.mgmt.services.tenant_management.schemas import TenantConfigurationCreate
        config_data = TenantConfigurationCreate()
            category="branding",
            configuration_key="branding_settings",
            configuration_value=branding_settings.model_dump(),
        )
        
        await tenant_service.create_tenant_configuration()
            tenant.id,
            config_data,
            current_user.get("user_id"),
        )
        
        return {"message": "Branding settings updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update branding settings for tenant {tenant_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update branding settings",
        )


# Health and Status
@tenant_admin_router.get("/health/instance")
async def get_instance_health():
    db: AsyncSession = Depends(get_db),
    current_tenant: dict = Depends(get_current_tenant),
    current_user: dict = Depends(require_tenant_admin),
):
    """Get detailed instance health status."""
    tenant_service = TenantManagementService(db)
    tenant_id = current_tenant["tenant_id"]
    
    try:
        health_status = await tenant_service.get_tenant_health_status(tenant_id)
        if not health_status:
            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Health status not available",
            )
        
        # Add additional health details
        return {
            **health_status.model_dump(),
            "detailed_metrics": {
                "database_connections": {"active": 8, "idle": 12, "total": 20},
                "cache_hit_rate": 0.89,
                "queue_sizes": {"background_jobs": 5, "email": 2, "webhooks": 0},
                "disk_usage_gb": 67.5,
                "network_io_mbps": {"inbound": 12.5, "outbound": 8.3},
            },
            "recent_events": [
                {"timestamp": datetime.now(timezone.utc) - timedelta(hours=2), "event": "Backup completed successfully"},
                {"timestamp": datetime.now(timezone.utc) - timedelta(hours=8), "event": "Scheduled maintenance completed"},
            ],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get instance health for tenant {tenant_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve instance health",
        )