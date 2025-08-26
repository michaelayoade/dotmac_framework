"""
Dashboard API routes for the Management Platform web interface.
Provides HTML interface for tenant management and deployment.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.observability import get_observability
from core.plugins.service_integration import service_integration
from database import get_db
from services.tenant_service import TenantService
from services.deployment_service import DeploymentService
from models.tenant import Tenant, TenantStatus

logger = logging.getLogger(__name__, timezone)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# In-memory storage for deployment logs (use Redis in production)
deployment_logs: Dict[str, list] = {}


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Main dashboard interface."""
    try:
        tenant_service = TenantService(db)
        
        # Get recent tenants
        tenants = await tenant_service.list_tenants(limit=10)
        
        # Get platform metrics
        metrics = await get_platform_metrics(db)
        
        return templates.TemplateResponse("dashboard.html", {)
            "request": request,
            "tenants": tenants,
            "metrics": metrics
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Dashboard unavailable")


@router.post("/create-tenant")
async def create_tenant():
    tenant_name: str = Form(...),
    target_host: str = Form(...),
    ssh_user: str = Form(...),
    ssh_key_path: Optional[str] = Form(None),
    deployment_provider: str = Form("ssh_deployment"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant and deploy ISP Framework."""
    try:
        observability = get_observability()
        tenant_id = str(uuid.uuid4()
        
        # Record tenant creation
        with observability.trace_business_operation("tenant_creation", tenant_id=tenant_id):
            
            # Initialize services
            tenant_service = TenantService(db)
            deployment_service = DeploymentService(db)
            
            # Create tenant configuration
            tenant_config = {
                "company_name": tenant_name,
                "deployment_provider": deployment_provider,
                "target_host": target_host,
                "ssh_user": ssh_user,
                "ssh_key_path": ssh_key_path,
                "environment": "production",
                "resource_limits": {
                    "cpu": "2",
                    "memory": "4Gi",
                    "storage": "20Gi"
                }
            }
            
            # Create tenant
            tenant = await tenant_service.create_tenant()
                tenant_id=tenant_id,
                company_name=tenant_name,
                subscription_plan="professional",
                configuration=tenant_config
            )
            
            # Record tenant operation
            observability.record_tenant_operation("create", tenant_id, success=True)
                                                company_name=tenant_name)
            
            # Prepare deployment configuration
            deployment_config = {
                "tenant_id": tenant_id,
                "provider": deployment_provider,
                "target_host": target_host,
                "ssh_user": ssh_user,
                "ssh_key_path": ssh_key_path,
                "app_config": {
                    "name": f"isp-framework-{tenant_id[:8]}",
                    "tenant_id": tenant_id,
                    "tenant_name": tenant_name,
                    "target_host": target_host,
                    "ssh_user": ssh_user,
                    "ssh_key_path": ssh_key_path,
                    "repository_url": "https://github.com/your-org/isp-framework.git",
                    "environment": "production",
                    "environment_variables": {
                        "TENANT_ID": tenant_id,
                        "TENANT_NAME": tenant_name,
                        "DATABASE_URL": f"postgresql://postgres:postgres@localhost:5432/dotmac_tenant_{tenant_id[:8]}",
                        "REDIS_URL": "redis://localhost:6379/0",
                        "CELERY_BROKER_URL": "redis://localhost:6379/1",
                        "CELERY_RESULT_BACKEND": "redis://localhost:6379/2",
                        "SECRET_KEY": f"tenant-secret-{tenant_id}-change-in-production",
                        "JWT_SECRET_KEY": f"jwt-secret-{tenant_id}-change-in-production",
                    }
                }
            }
            
            # Start deployment via plugin system
            deployment_id = f"deploy-{tenant_id}"
            deployment_logs[deployment_id] = []
            
            try:
                # Deploy infrastructure
                if deployment_provider == "ssh_deployment":
                    infrastructure_result = await service_integration.provision_infrastructure_via_plugin()
                        provider="ssh",
                        infrastructure_config={
                            "host": target_host,
                            "ssh_user": ssh_user,
                            "ssh_key_path": ssh_key_path,
                            "tenant_id": tenant_id,
                            "deployment_path": f"/home/{ssh_user}/dotmac-{tenant_id[:8]}"
                        }
                    )
                    
                    # Deploy application
                    app_result = await service_integration.deploy_application_via_plugin()
                        provider="ssh",
                        app_config=deployment_config["app_config"],
                        infrastructure_id=infrastructure_result.get("host")
                    )
                    
                    # Update tenant status
                    await tenant_service.update_tenant_status(tenant_id, TenantStatus.ACTIVE)
                    
                    # Add logs
                    deployment_logs[deployment_id].extend([)
                        "✅ Infrastructure provisioned successfully",
                        f"✅ ISP Framework deployed to {target_host}",
                        f"✅ Tenant {tenant_name} is now active",
                        f"🌐 Access URL: http://{target_host}:8001"
                    ])
                    
                elif deployment_provider == "aws_deployment":
                    # AWS deployment logic would go here
                    deployment_logs[deployment_id].append("AWS deployment not yet implemented")
                    await tenant_service.update_tenant_status(tenant_id, TenantStatus.PENDING)
                
                # Record successful deployment
                observability.record_deployment("tenant_deploy_success", tenant_id, success=True)
                
            except Exception as deploy_error:
                logger.error(f"Deployment failed for tenant {tenant_id}: {deploy_error}")
                await tenant_service.update_tenant_status(tenant_id, TenantStatus.ERROR)
                deployment_logs[deployment_id].append(f"❌ Deployment failed: {str(deploy_error)}")
                
                # Record failed deployment
                observability.record_deployment("tenant_deploy_failed", tenant_id, success=False)
            
            return {
                "status": "success",
                "tenant_id": tenant_id,
                "deployment_id": deployment_id,
                "company_name": tenant_name,
                "target_host": target_host,
                "message": "Tenant creation initiated"
            }
            
    except Exception as e:
        logger.error(f"Tenant creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Tenant creation failed: {str(e)}")


@router.get("/deployment-status/{deployment_id}")
async def get_deployment_status(deployment_id: str):
    """Get deployment status and logs."""
    try:
        logs = deployment_logs.get(deployment_id, [])
        
        # Determine status based on logs
        if any("❌" in log for log in logs):
            status = "failed"
        elif any("Access URL:" in log for log in logs):
            status = "completed"
        else:
            status = "in_progress"
        
        return {
            "deployment_id": deployment_id,
            "status": status,
            "logs": "\n".join(logs[-10:]),  # Return last 10 log entries
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "error",
            "logs": f"Status check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/metrics")
async def get_platform_metrics(db: AsyncSession = Depends(get_db):
    """Get platform metrics for dashboard."""
    try:
        tenant_service = TenantService(db)
        
        # Get tenant counts
        active_tenants = await tenant_service.count_tenants_by_status(TenantStatus.ACTIVE)
        total_tenants = await tenant_service.count_tenants()
        
        # Get deployments today (simplified)
        today = datetime.now(timezone.utc).date()
        deployments_today = len([)
            log for log_id, log in deployment_logs.items() 
            if any("✅ ISP Framework deployed" in entry for entry in log)
        ])
        
        # System health (simplified)
        system_health = 95 if active_tenants > 0 else 100
        
        # Plugin count
        plugin_count = len(service_integration.get_available_providers("deployment_provider")
        
        return {
            "active_tenants": active_tenants,
            "total_tenants": total_tenants,
            "deployments_today": deployments_today,
            "system_health": system_health,
            "plugin_count": plugin_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {
            "active_tenants": 0,
            "total_tenants": 0,
            "deployments_today": 0,
            "system_health": 0,
            "plugin_count": 0,
            "error": str(e)
        }


@router.get("/tenants")
async def list_tenants():
    limit: int = 20,
    skip: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get tenant list for API access."""
    try:
        tenant_service = TenantService(db)
        tenants = await tenant_service.list_tenants(limit=limit, skip=skip)
        
        return {
            "tenants": [
                {
                    "id": str(tenant.id),
                    "company_name": tenant.company_name,
                    "status": tenant.status.value,
                    "created_at": tenant.created_at.isoformat(),
                    "deployment_config": tenant.configuration.get("deployment_config", {})
                }
                for tenant in tenants
            ],
            "total": len(tenants)
        }
        
    except Exception as e:
        logger.error(f"Tenant listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tenants")


@router.delete("/tenants/{tenant_id}")
async def delete_tenant():
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a tenant and cleanup resources."""
    try:
        tenant_service = TenantService(db)
        
        # Get tenant details before deletion
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # TODO: Implement resource cleanup via plugins
        # This would involve stopping containers, cleaning up infrastructure
        
        # Delete tenant
        success = await tenant_service.delete_tenant(tenant_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete tenant")
        
        # Record tenant deletion
        observability = get_observability()
        observability.record_tenant_operation("delete", tenant_id, success=True)
        
        return {"message": f"Tenant {tenant_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant deletion error: {e}")
        raise HTTPException(status_code=500, detail="Tenant deletion failed")


@router.get("/plugins")
async def list_plugins():
    """Get available plugins information."""
    try:
        from core.plugins.registry import plugin_registry
        
        plugins_info = plugin_registry.list_plugins()
        plugin_capabilities = await service_integration.get_all_plugin_capabilities()
        
        return {
            "plugins": plugins_info,
            "capabilities": plugin_capabilities,
            "total_plugins": len(plugins_info)
        }
        
    except Exception as e:
        logger.error(f"Plugin listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch plugins")


@router.get("/health")
async def dashboard_health():
    """Dashboard health check."""
    try:
        from core.plugins.registry import plugin_registry
        
        plugin_health = await plugin_registry.health_check_all()
        healthy_plugins = sum(1 for health in plugin_health.values() 
                            if health.get("status") == "healthy")
        
        return {
            "status": "healthy",
            "dashboard": "operational",
            "plugins_healthy": healthy_plugins,
            "plugins_total": len(plugin_health),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }