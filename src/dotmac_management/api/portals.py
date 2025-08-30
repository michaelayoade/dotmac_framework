"""
Portal-specific API routes for different user interfaces.
"""

from fastapi import APIRouter

from dotmac_shared.api.router_factory import RouterFactory

# Create main portals router
portals_router = APIRouter()
portals_router = APIRouter()


@portals_router.get("/")
async def list_portals():
    """List available portals."""
    return {
        "portals": [
            {
                "name": "master_admin",
                "title": "Master Admin Portal",
                "description": "System administration and tenant management",
                "url": "/portals/master-admin",
            },
            {
                "name": "tenant_admin",
                "title": "Tenant Admin Portal",
                "description": "Tenant administration and configuration",
                "url": "/portals/tenant-admin",
            },
            {
                "name": "reseller",
                "title": "Reseller Portal",
                "description": "Reseller tenant management and billing",
                "url": "/portals/reseller",
            },
        ]
    }


@portals_router.get("/master-admin")
async def master_admin_portal():
    """Master admin portal metadata."""
    return {
        "name": "Master Admin Portal",
        "description": "System administration and tenant management",
        "features": [
            "Tenant Management",
            "User Management",
            "System Configuration",
            "Analytics & Reporting",
            "Plugin Management",
            "Infrastructure Monitoring",
        ],
    }


@portals_router.get("/tenant-admin")
async def tenant_admin_portal():
    """Tenant admin portal metadata."""
    return {
        "name": "Tenant Admin Portal",
        "description": "Tenant administration and configuration",
        "features": [
            "Tenant Configuration",
            "User Management",
            "Billing & Subscriptions",
            "Deployments",
            "Monitoring",
            "Plugin Management",
        ],
    }


@portals_router.get("/reseller")
async def reseller_portal():
    """Reseller portal metadata."""
    return {
        "name": "Reseller Portal",
        "description": "Reseller tenant management and billing",
        "features": [
            "Client Tenant Management",
            "Billing & Invoicing",
            "Subscription Management",
            "Analytics & Reports",
            "Support Tools",
        ],
    }
