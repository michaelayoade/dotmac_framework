"""
Simple Management Platform startup without complex shared dependencies.
"""

import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_simple_app() -> FastAPI:
    """Create a simple management platform app."""
    
    app = FastAPI(
        title="DotMac Management Platform",
        description="Master control plane for all ISP tenants",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {
            "service": "DotMac Management Platform",
            "status": "running",
            "role": "Master Control Plane",
            "manages": [
                "Tenant Provisioning",
                "License Administration", 
                "Partner Management",
                "Global Billing",
                "Resource Orchestration",
                "Cross-tenant Monitoring"
            ]
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "management-platform"}
    
    @app.get("/tenants")
    async def list_tenants():
        """List all managed ISP tenants."""
        return {
            "tenants": [
                {
                    "id": "tenant-001",
                    "name": "Mountain View ISP",
                    "plan": "professional",
                    "status": "active",
                    "features": ["crm", "tickets", "projects"],
                    "container_status": "running"
                },
                {
                    "id": "tenant-002", 
                    "name": "Valley Networks",
                    "plan": "enterprise",
                    "status": "active",
                    "features": ["crm", "tickets", "projects", "fieldops", "analytics"],
                    "container_status": "running"
                }
            ]
        }
    
    @app.post("/tenants/{tenant_id}/license/upgrade")
    async def upgrade_tenant_license(tenant_id: str, new_plan: str):
        """Upgrade a tenant's license plan."""
        return {
            "tenant_id": tenant_id,
            "old_plan": "starter",
            "new_plan": new_plan,
            "status": "upgraded",
            "activated_features": ["crm", "projects"] if new_plan == "professional" else ["crm", "projects", "fieldops", "analytics"]
        }
    
    @app.get("/partners")
    async def list_partners():
        """List all reseller partners."""
        return {
            "partners": [
                {
                    "id": "partner-001",
                    "name": "TechSolutions Inc",
                    "type": "reseller",
                    "tenants_managed": 15,
                    "commission_rate": 0.15
                }
            ]
        }
    
    @app.get("/monitoring/overview")
    async def monitoring_overview():
        """Global monitoring overview."""
        return {
            "total_tenants": 2,
            "active_tenants": 2,
            "total_containers": 2,
            "healthy_containers": 2,
            "total_partners": 1,
            "resource_utilization": {
                "cpu": "45%",
                "memory": "62%",
                "storage": "38%"
            }
        }
    
    return app

# Create the app
app = create_simple_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    
    logger.info(f"Starting DotMac Management Platform on {host}:{port}")
    
    uvicorn.run(
        "main_simple:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
