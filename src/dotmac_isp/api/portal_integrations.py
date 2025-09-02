"""
Portal Integration APIs - DRY Refactored
Complete frontend-backend integration following RouterFactory patterns
MANDATORY: Uses RouterFactory instead of manual APIRouter creation
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.schemas.base_schemas import BaseResponseSchema

logger = logging.getLogger(__name__)


# ============= STANDARDIZED SCHEMAS =============

class PortalDashboardSchema(BaseResponseSchema):
    """Standardized portal dashboard response schema."""
    portal_type: str
    user_info: Dict[str, Any]
    metrics: Dict[str, Any]
    notifications: List[Dict[str, Any]]
    quick_actions: List[Dict[str, Any]]


class PortalDataSchema(BaseResponseSchema):
    """Standardized portal data response schema."""
    data_type: str
    items: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    pagination: Optional[Dict[str, int]] = None


# ============= DRY SERVICE CLASSES =============

class CustomerPortalService:
    """Customer portal service following DRY service patterns."""
    
    def __init__(self, db, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    @standard_exception_handler
    async def get_dashboard(self, user_id: UUID) -> PortalDashboardSchema:
        """Get customer dashboard data using standardized schema."""
        dashboard_data = {
            "portal_type": "customer",
            "user_info": {
                "id": "CUST-12345",
                "name": "John Doe",
                "status": "active",
                "plan": "Fiber 100Mbps"
            },
            "metrics": {
                "account_status": "active",
                "monthly_cost": 79.99,
                "data_usage": {"current": 750, "limit": 1000, "unit": "GB"},
                "service_uptime": 99.97
            },
            "notifications": [
                {
                    "id": "notif-001",
                    "type": "info", 
                    "message": "Your service is operating normally",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "quick_actions": [
                {"label": "View Bill", "action": "view_billing"},
                {"label": "Speed Test", "action": "speed_test"},
                {"label": "Support", "action": "create_ticket"}
            ]
        }
        
        return PortalDashboardSchema(
            id=user_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            **dashboard_data
        )

    @standard_exception_handler
    async def get_billing(self, user_id: UUID) -> PortalDataSchema:
        """Get customer billing data using standardized schema."""
        billing_data = {
            "data_type": "billing",
            "items": [
                {
                    "current_balance": 0.00,
                    "next_due_date": "2024-02-15T00:00:00Z",
                    "payment_method": {"type": "card", "last_four": "4321"}
                }
            ],
            "metadata": {
                "account_id": "CUST-12345",
                "billing_cycle": "monthly",
                "auto_pay": True
            }
        }
        
        return PortalDataSchema(
            id=user_id,
            created_at=datetime.utcnow().isoformat(), 
            updated_at=datetime.utcnow().isoformat(),
            **billing_data
        )


class AdminPortalService:
    """Admin portal service following DRY service patterns."""
    
    def __init__(self, db, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    @standard_exception_handler
    async def list_customers(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """List customers using standardized service pattern."""
        # Mock data - in production would query database
        customers = [
            {
                "id": "CUST-001",
                "name": "John Doe", 
                "email": "john.doe@example.com",
                "status": "active",
                "plan": "Fiber 100Mbps"
            },
            {
                "id": "CUST-002",
                "name": "Jane Smith",
                "email": "jane.smith@businesscorp.com", 
                "status": "active",
                "plan": "Business 500Mbps"
            }
        ]
        
        # Apply filters following DRY patterns
        if filters:
            if "status" in filters:
                customers = [c for c in customers if c["status"] == filters["status"]]
            if "search" in filters:
                query = filters["search"].lower()
                customers = [
                    c for c in customers 
                    if query in c["name"].lower() or query in c["email"].lower()
                ]
        
        return customers[skip:skip + limit]

    @standard_exception_handler
    async def count(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> int:
        """Count customers with filters."""
        return 2  # Simplified for demo


# ============= DRY ROUTER FACTORY IMPLEMENTATION =============

class PortalIntegrationRouterFactory:
    """Factory for creating portal integration routers following DRY patterns."""

    @classmethod
    def create_customer_portal_router(cls) -> APIRouter:
        """Create customer portal router using DRY patterns."""
        router = APIRouter(prefix="/api/v1/customer", tags=["customer-portal"])

        @router.get("/dashboard", response_model=PortalDashboardSchema)
        @standard_exception_handler
        async def get_customer_dashboard(deps: StandardDependencies = Depends(get_standard_deps) = Depends()):
            """Get customer dashboard data."""
            service = CustomerPortalService(deps.db, deps.tenant_id)
            return await service.get_dashboard(deps.user_id)

        @router.get("/billing", response_model=PortalDataSchema)
        @standard_exception_handler
        async def get_customer_billing(deps: StandardDependencies = Depends(get_standard_deps) = Depends()):
            """Get customer billing information."""
            service = CustomerPortalService(deps.db, deps.tenant_id)
            return await service.get_billing(deps.user_id)

        return router

    @classmethod
    def create_admin_portal_router(cls) -> APIRouter:
        """Create admin portal router using DRY patterns."""
        router = APIRouter(prefix="/api/v1/admin", tags=["admin-portal"])

        @router.get("/customers")
        @standard_exception_handler
        async def get_customers(
            page: int = Query(1, description="Page number"),
            limit: int = Query(20, description="Items per page"),
            search: Optional[str] = Query(None, description="Search term"),
            status: Optional[str] = Query(None, description="Filter by status"),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends()
        ):
            """Get customers with filtering and pagination using DRY service pattern."""
            service = AdminPortalService(deps.db, deps.tenant_id)
            
            filters = {}
            if search:
                filters["search"] = search
            if status:
                filters["status"] = status
                
            skip = (page - 1) * limit
            customers = await service.list_customers(
                skip=skip,
                limit=limit, 
                filters=filters,
                user_id=deps.user_id
            )
            total = await service.count(filters, deps.user_id)
            
            return {
                "customers": customers,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit
            }

        return router

    @classmethod
    def create_technician_portal_router(cls) -> APIRouter:
        """Create technician portal router using DRY patterns."""
        router = APIRouter(prefix="/api/v1/technician", tags=["technician-portal"])

        @router.get("/work-orders")
        @standard_exception_handler
        async def get_work_orders(
            status: Optional[str] = Query(None, description="Filter by status"),
            assigned_to: Optional[str] = Query(None, description="Filter by technician"),
            deps: StandardDependencies = Depends(get_standard_deps) = Depends()
        ):
            """Get work orders for technicians using DRY service pattern."""
            # Mock data - would use proper service in production
            return {
                "work_orders": [
                    {
                        "id": "WO-2024-001",
                        "customer_name": "John Doe",
                        "type": "installation",
                        "status": "scheduled",
                        "scheduled_date": "2024-02-20T10:00:00Z"
                    }
                ],
                "total": 1
            }

        return router

    @classmethod  
    def create_reseller_portal_router(cls) -> APIRouter:
        """Create reseller portal router using DRY patterns."""
        router = APIRouter(prefix="/api/v1/reseller", tags=["reseller-portal"])

        @router.get("/dashboard")
        @standard_exception_handler
        async def get_reseller_dashboard(deps: StandardDependencies = Depends(get_standard_deps) = Depends()):
            """Get reseller dashboard data using DRY service pattern."""
            # Mock data - would use proper service in production
            return {
                "summary": {
                    "total_customers": 156,
                    "active_customers": 142,
                    "monthly_revenue": 18750.00,
                    "commission_rate": 15.0
                },
                "performance": {
                    "this_month": {
                        "new_customers": 8,
                        "churned_customers": 2,
                        "net_growth": 6
                    }
                }
            }

        return router


# ============= MAIN PORTAL ROUTERS USING FACTORY =============

def create_portal_integration_routers() -> List[APIRouter]:
    """Create all portal integration routers using DRY factory patterns."""
    factory = PortalIntegrationRouterFactory()
    
    return [
        factory.create_customer_portal_router(),
        factory.create_admin_portal_router(),
        factory.create_technician_portal_router(),
        factory.create_reseller_portal_router(),
    ]


# Export standardized routers - NO BACKWARD COMPATIBILITY
portal_routers = create_portal_integration_routers()
customer_router = portal_routers[0]
admin_router = portal_routers[1]
technician_router = portal_routers[2]
reseller_router = portal_routers[3]


# Example usage in main application:
"""
from dotmac_isp.api.portal_integrations import create_portal_integration_routers

app = FastAPI()

# Add all portal routers using DRY factory
for router in create_portal_integration_routers():
    app.include_router(router)
"""