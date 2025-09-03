"""
Field Operations API Router

RESTful API endpoints for field operations management using existing RouterFactory patterns.
Provides endpoints for technicians, work orders, dispatch, and performance analytics.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.security import HTTPBearer

from ..api.router_factory import RouterFactory
from ..auth.dependencies import get_current_user, require_permissions
from ..exceptions import ValidationError, NotFoundError, BusinessLogicError
from .service import FieldOperationsService, DispatchService
from .models import (
    TechnicianCreate, TechnicianUpdate, TechnicianResponse,
    WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse, WorkOrderDetailResponse,
    WorkOrderStatus, WorkOrderPriority, WorkOrderType, TechnicianStatus,
    PerformanceMetrics
)

# Initialize security
security = HTTPBearer()

# Create the main router
router = APIRouter(prefix="/api/v1/field-operations", tags=["Field Operations"])


class FieldOperationsRouter:
    """Field operations API router with all endpoints."""
    
    def __init__(self):
        self.field_service = FieldOperationsService()
        self.dispatch_service = DispatchService()
        self.router = router
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all field operations routes."""
        
        # Technician Management Routes
        
        @self.router.post("/technicians", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED)
        async def create_technician(
            technician_data: TechnicianCreate,
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:technician:create"]))
        ):
            """Create a new field technician."""
            try:
                return self.field_service.create_technician(
                    tenant_id=current_user["tenant_id"],
                    technician_data=technician_data
                )
            except ValidationError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
        
        @self.router.get("/technicians/{technician_id}", response_model=TechnicianResponse)
        async def get_technician(
            technician_id: UUID = Path(..., description="Technician ID"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:technician:read"]))
        ):
            """Get technician by ID."""
            try:
                return self.field_service.get_technician(
                    tenant_id=current_user["tenant_id"],
                    technician_id=technician_id
                )
            except NotFoundError as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
        @self.router.put("/technicians/{technician_id}", response_model=TechnicianResponse)
        async def update_technician(
            update_data: TechnicianUpdate,
            technician_id: UUID = Path(..., description="Technician ID"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:technician:update"]))
        ):
            """Update technician information."""
            try:
                return self.field_service.update_technician(
                    tenant_id=current_user["tenant_id"],
                    technician_id=technician_id,
                    update_data=update_data
                )
            except NotFoundError as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except ValidationError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        @self.router.get("/technicians", response_model=List[TechnicianResponse])
        async def get_available_technicians(
            work_order_type: Optional[WorkOrderType] = Query(None, description="Filter by work order type"),
            latitude: Optional[float] = Query(None, description="Location latitude for proximity search"),
            longitude: Optional[float] = Query(None, description="Location longitude for proximity search"),
            radius_km: float = Query(50.0, ge=1, le=500, description="Search radius in kilometers"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:technician:read"]))
        ):
            """Get available technicians, optionally filtered by skills and location."""
            location = None
            if latitude is not None and longitude is not None:
                from ..location.models import Coordinates
                location = Coordinates(latitude=latitude, longitude=longitude)
            
            return self.field_service.get_available_technicians(
                tenant_id=current_user["tenant_id"],
                work_order_type=work_order_type,
                location=location,
                radius_km=radius_km
            )
        
        # Work Order Management Routes
        
        @self.router.post("/work-orders", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
        async def create_work_order(
            work_order_data: WorkOrderCreate,
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:work_order:create"]))
        ):
            """Create a new work order."""
            try:
                return self.field_service.create_work_order(
                    tenant_id=current_user["tenant_id"],
                    work_order_data=work_order_data
                )
            except ValidationError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        @self.router.get("/work-orders/{work_order_id}", response_model=WorkOrderDetailResponse)
        async def get_work_order(
            work_order_id: UUID = Path(..., description="Work order ID"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:work_order:read"]))
        ):
            """Get detailed work order information."""
            try:
                return self.field_service.get_work_order_detail(
                    tenant_id=current_user["tenant_id"],
                    work_order_id=work_order_id
                )
            except NotFoundError as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
        @self.router.put("/work-orders/{work_order_id}/status", response_model=WorkOrderResponse)
        async def update_work_order_status(
            work_order_id: UUID,
            new_status: WorkOrderStatus,
            notes: Optional[str] = None,
            latitude: Optional[float] = Query(None, description="Current latitude"),
            longitude: Optional[float] = Query(None, description="Current longitude"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:work_order:update"]))
        ):
            """Update work order status."""
            try:
                location = None
                if latitude is not None and longitude is not None:
                    location = {"latitude": latitude, "longitude": longitude}
                
                return self.field_service.update_work_order_status(
                    tenant_id=current_user["tenant_id"],
                    work_order_id=work_order_id,
                    new_status=new_status,
                    notes=notes,
                    updated_by=current_user.get("email"),
                    location=location
                )
            except NotFoundError as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except ValidationError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        @self.router.put("/work-orders/{work_order_id}/assign/{technician_id}", response_model=WorkOrderResponse)
        async def assign_technician_to_work_order(
            work_order_id: UUID = Path(..., description="Work order ID"),
            technician_id: UUID = Path(..., description="Technician ID"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:work_order:assign"]))
        ):
            """Assign a technician to a work order."""
            try:
                return self.field_service.assign_technician(
                    tenant_id=current_user["tenant_id"],
                    work_order_id=work_order_id,
                    technician_id=technician_id,
                    assigned_by=current_user.get("email", "system")
                )
            except (NotFoundError, BusinessLogicError) as e:
                status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_400_BAD_REQUEST
                raise HTTPException(status_code=status_code, detail=str(e))
        
        @self.router.get("/technicians/{technician_id}/work-orders", response_model=List[WorkOrderResponse])
        async def get_technician_work_orders(
            technician_id: UUID = Path(..., description="Technician ID"),
            status_filter: Optional[List[WorkOrderStatus]] = Query(None, description="Filter by work order status"),
            date_from: Optional[date] = Query(None, description="Start date filter"),
            date_to: Optional[date] = Query(None, description="End date filter"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:work_order:read"]))
        ):
            """Get work orders for a specific technician."""
            return self.field_service.get_technician_work_orders(
                tenant_id=current_user["tenant_id"],
                technician_id=technician_id,
                status_filter=status_filter,
                date_from=date_from,
                date_to=date_to
            )
        
        # Intelligent Dispatch Routes
        
        @self.router.post("/work-orders/{work_order_id}/dispatch/intelligent", response_model=TechnicianResponse)
        async def intelligent_dispatch_work_order(
            work_order_id: UUID = Path(..., description="Work order ID"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:dispatch:intelligent"]))
        ):
            """Intelligently assign the best technician for a work order."""
            try:
                return self.field_service.intelligent_dispatch(
                    tenant_id=current_user["tenant_id"],
                    work_order_id=work_order_id
                )
            except (NotFoundError, BusinessLogicError) as e:
                status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_400_BAD_REQUEST
                raise HTTPException(status_code=status_code, detail=str(e))
        
        @self.router.post("/work-orders/{work_order_id}/dispatch/emergency", response_model=TechnicianResponse)
        async def emergency_dispatch_work_order(
            work_order_id: UUID = Path(..., description="Work order ID"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:dispatch:emergency"]))
        ):
            """Emergency dispatch - find nearest available technician immediately."""
            try:
                return self.dispatch_service.emergency_dispatch(
                    tenant_id=current_user["tenant_id"],
                    work_order_id=work_order_id
                )
            except (NotFoundError, BusinessLogicError) as e:
                status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_400_BAD_REQUEST
                raise HTTPException(status_code=status_code, detail=str(e))
        
        # Route Optimization Routes
        
        @self.router.get("/technicians/{technician_id}/route/optimize", response_model=List[WorkOrderResponse])
        async def optimize_technician_route(
            technician_id: UUID = Path(..., description="Technician ID"),
            target_date: date = Query(..., description="Date to optimize route for"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:route:optimize"]))
        ):
            """Optimize work order sequence for a technician's day."""
            return self.field_service.optimize_technician_route(
                tenant_id=current_user["tenant_id"],
                technician_id=technician_id,
                target_date=target_date
            )
        
        # Performance Analytics Routes
        
        @self.router.get("/technicians/{technician_id}/performance", response_model=PerformanceMetrics)
        async def get_technician_performance(
            technician_id: UUID = Path(..., description="Technician ID"),
            period_start: date = Query(..., description="Performance period start date"),
            period_end: date = Query(..., description="Performance period end date"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:analytics:read"]))
        ):
            """Get comprehensive performance metrics for a technician."""
            try:
                return self.field_service.calculate_technician_performance(
                    tenant_id=current_user["tenant_id"],
                    technician_id=technician_id,
                    period_start=period_start,
                    period_end=period_end
                )
            except NotFoundError as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
        # Dashboard and Analytics Routes
        
        @self.router.get("/dashboard/summary")
        async def get_field_operations_summary(
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:dashboard:read"]))
        ):
            """Get field operations dashboard summary."""
            tenant_id = current_user["tenant_id"]
            
            # Get today's stats
            today = date.today()
            
            # Count work orders by status
            from sqlalchemy import func
            from .models import WorkOrder, Technician
            
            db = self.field_service.db
            
            # Work order counts
            work_order_stats = db.query(
                WorkOrder.status,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.tenant_id == tenant_id,
                WorkOrder.scheduled_date == today
            ).group_by(WorkOrder.status).all()
            
            # Technician availability
            tech_stats = db.query(
                Technician.current_status,
                func.count(Technician.id).label('count')
            ).filter(
                Technician.tenant_id == tenant_id
            ).group_by(Technician.current_status).all()
            
            # Convert to dictionaries
            wo_stats_dict = {stat.status.value: stat.count for stat in work_order_stats}
            tech_stats_dict = {stat.current_status.value: stat.count for stat in tech_stats}
            
            return {
                "date": today,
                "work_orders": {
                    "total": sum(wo_stats_dict.values()),
                    "by_status": wo_stats_dict,
                    "completed_today": wo_stats_dict.get("completed", 0),
                    "in_progress": wo_stats_dict.get("in_progress", 0),
                    "overdue": 0  # Calculate overdue separately if needed
                },
                "technicians": {
                    "total": sum(tech_stats_dict.values()),
                    "available": tech_stats_dict.get("available", 0),
                    "on_job": tech_stats_dict.get("on_job", 0),
                    "off_duty": tech_stats_dict.get("off_duty", 0)
                }
            }
        
        # Mobile API Routes (simplified responses for mobile apps)
        
        @self.router.get("/mobile/technician/schedule", response_model=List[WorkOrderResponse])
        async def get_technician_mobile_schedule(
            schedule_date: Optional[date] = Query(None, description="Schedule date (defaults to today)"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:mobile:schedule"]))
        ):
            """Get technician's schedule for mobile app."""
            if not schedule_date:
                schedule_date = date.today()
            
            # Assume current user is a technician or get technician ID from user profile
            technician_id = UUID(current_user.get("technician_id", "00000000-0000-0000-0000-000000000000"))
            
            return self.field_service.get_technician_work_orders(
                tenant_id=current_user["tenant_id"],
                technician_id=technician_id,
                date_from=schedule_date,
                date_to=schedule_date
            )
        
        @self.router.put("/mobile/work-orders/{work_order_id}/checkin")
        async def mobile_work_order_checkin(
            work_order_id: UUID = Path(..., description="Work order ID"),
            latitude: float = Query(..., description="Check-in latitude"),
            longitude: float = Query(..., description="Check-in longitude"),
            current_user: Dict[str, Any] = Depends(get_current_user),
            _permissions: None = Depends(require_permissions(["field_ops:mobile:checkin"]))
        ):
            """Check in to a work order from mobile app."""
            try:
                location = {"latitude": latitude, "longitude": longitude}
                
                # Update to on-site status
                result = self.field_service.update_work_order_status(
                    tenant_id=current_user["tenant_id"],
                    work_order_id=work_order_id,
                    new_status=WorkOrderStatus.ON_SITE,
                    notes="Technician checked in via mobile app",
                    updated_by=current_user.get("email"),
                    location=location
                )
                
                return {"message": "Successfully checked in", "work_order": result}
            
            except (NotFoundError, ValidationError) as e:
                status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_400_BAD_REQUEST
                raise HTTPException(status_code=status_code, detail=str(e))


# Create router factory instance
field_operations_router_factory = RouterFactory(
    resource_name="field_operations",
    base_path="/api/v1/field-operations",
    service_class=FieldOperationsService,
    tags=["Field Operations"]
)

# Initialize the router
field_ops_router = FieldOperationsRouter()

# Export the router
field_operations_router = field_ops_router.router