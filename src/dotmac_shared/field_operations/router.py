"""
Field Operations API Router

Provides REST endpoints for field operations management leveraging existing service layer.
Uses simplified FastAPI patterns for compatibility while maintaining full functionality.
"""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.exceptions import BusinessLogicError, NotFoundError, ValidationError
from ..database import get_db_session
from .models import (
    PerformanceMetrics,
    TechnicianCreate,
    TechnicianResponse,
    TechnicianUpdate,
    WorkOrderCreate,
    WorkOrderDetailResponse,
    WorkOrderResponse,
    WorkOrderStatus,
    WorkOrderType,
)
from .service import DispatchService, FieldOperationsService

# Create router with proper prefix
router = APIRouter(prefix="/field-operations", tags=["Field Operations"])


# Dependency injection
def get_field_service(db: Session = Depends(get_db_session)) -> FieldOperationsService:
    return FieldOperationsService(db)


def get_dispatch_service(db: Session = Depends(get_db_session)) -> DispatchService:
    return DispatchService(db)


# Exception handler decorator for consistency
def handle_service_exceptions(func):
    """Decorator to handle service exceptions consistently."""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except BusinessLogicError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e

    return wrapper


# Health check
@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "field-operations"}


# Technician Management Endpoints
@router.post(
    "/technicians",
    response_model=TechnicianResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_service_exceptions
async def create_technician(
    technician_data: TechnicianCreate,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> TechnicianResponse:
    """Create a new technician."""
    return service.create_technician(tenant_id, technician_data)


@router.get("/technicians", response_model=list[TechnicianResponse])
@handle_service_exceptions
async def get_available_technicians(
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
    work_order_type: Optional[WorkOrderType] = Query(None, description="Filter by work order type"),
    latitude: Optional[float] = Query(None, description="Location latitude for radius search"),
    longitude: Optional[float] = Query(None, description="Location longitude for radius search"),
    radius_km: float = Query(50.0, ge=1.0, le=500.0, description="Search radius in kilometers"),
) -> list[TechnicianResponse]:
    """Get available technicians with optional filtering."""
    from ..location.models import Coordinates

    location = None
    if latitude is not None and longitude is not None:
        location = Coordinates(latitude=latitude, longitude=longitude)

    return service.get_available_technicians(
        tenant_id=tenant_id,
        work_order_type=work_order_type,
        location=location,
        radius_km=radius_km,
    )


@router.get("/technicians/{technician_id}", response_model=TechnicianResponse)
@handle_service_exceptions
async def get_technician(
    technician_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> TechnicianResponse:
    """Get technician details by ID."""
    return service.get_technician(tenant_id, technician_id)


@router.put("/technicians/{technician_id}", response_model=TechnicianResponse)
@handle_service_exceptions
async def update_technician(
    technician_id: UUID,
    update_data: TechnicianUpdate,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> TechnicianResponse:
    """Update technician information."""
    return service.update_technician(tenant_id, technician_id, update_data)


# Work Order Management Endpoints
@router.post(
    "/work-orders",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_service_exceptions
async def create_work_order(
    work_order_data: WorkOrderCreate,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> WorkOrderResponse:
    """Create a new work order."""
    return service.create_work_order(tenant_id, work_order_data)


@router.get("/work-orders", response_model=list[WorkOrderResponse])
@handle_service_exceptions
async def get_technician_work_orders(
    technician_id: UUID = Query(..., description="Technician ID"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
    status_filter: Optional[list[WorkOrderStatus]] = Query(None, description="Filter by status"),
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
) -> list[WorkOrderResponse]:
    """Get work orders for a specific technician."""
    return service.get_technician_work_orders(
        tenant_id=tenant_id,
        technician_id=technician_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/work-orders/{work_order_id}", response_model=WorkOrderDetailResponse)
@handle_service_exceptions
async def get_work_order_detail(
    work_order_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> WorkOrderDetailResponse:
    """Get detailed work order information."""
    return service.get_work_order_detail(tenant_id, work_order_id)


# Dispatch and Assignment Endpoints
@router.put("/work-orders/{work_order_id}/assign", response_model=WorkOrderResponse)
@handle_service_exceptions
async def assign_technician_to_work_order(
    work_order_id: UUID,
    technician_id: UUID = Query(..., description="Technician ID to assign"),
    assigned_by: str = Query(..., description="User performing the assignment"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> WorkOrderResponse:
    """Assign a technician to a work order."""
    return service.assign_technician(tenant_id, work_order_id, technician_id, assigned_by)


@router.post("/work-orders/{work_order_id}/dispatch", response_model=TechnicianResponse)
@handle_service_exceptions
async def intelligent_dispatch(
    work_order_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> TechnicianResponse:
    """Intelligently assign the best available technician to a work order."""
    return service.intelligent_dispatch(tenant_id, work_order_id)


@router.post("/work-orders/{work_order_id}/emergency-dispatch", response_model=TechnicianResponse)
@handle_service_exceptions
async def emergency_dispatch(
    work_order_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    dispatch_service: DispatchService = Depends(get_dispatch_service),
) -> TechnicianResponse:
    """Emergency dispatch - find nearest technician immediately."""
    return dispatch_service.emergency_dispatch(tenant_id, work_order_id)


# Status Management Endpoints
@router.put("/work-orders/{work_order_id}/status", response_model=WorkOrderResponse)
@handle_service_exceptions
async def update_work_order_status(
    work_order_id: UUID,
    new_status: WorkOrderStatus = Query(..., description="New status"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
    notes: Optional[str] = Query(None, description="Status change notes"),
    updated_by: Optional[str] = Query(None, description="User updating status"),
    latitude: Optional[float] = Query(None, description="Current latitude"),
    longitude: Optional[float] = Query(None, description="Current longitude"),
) -> WorkOrderResponse:
    """Update work order status with optional location tracking."""
    location = None
    if latitude is not None and longitude is not None:
        location = {"latitude": latitude, "longitude": longitude}

    return service.update_work_order_status(
        tenant_id=tenant_id,
        work_order_id=work_order_id,
        new_status=new_status,
        notes=notes,
        updated_by=updated_by or "SYSTEM",
        location=location,
    )


@router.put("/work-orders/{work_order_id}/complete", response_model=WorkOrderResponse)
@handle_service_exceptions
async def complete_work_order(
    work_order_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
    completion_notes: Optional[str] = Query(None, description="Completion notes"),
    customer_rating: Optional[int] = Query(None, ge=1, le=5, description="Customer satisfaction rating"),
    updated_by: Optional[str] = Query(None, description="User completing work order"),
) -> WorkOrderResponse:
    """Mark work order as completed with optional customer feedback."""
    notes = completion_notes or "Work completed"
    if customer_rating:
        notes += f" (Customer rating: {customer_rating}/5)"

    return service.update_work_order_status(
        tenant_id=tenant_id,
        work_order_id=work_order_id,
        new_status=WorkOrderStatus.COMPLETED,
        notes=notes,
        updated_by=updated_by or "SYSTEM",
    )


# Mobile and Tracking Endpoints
@router.post("/technicians/{technician_id}/location")
@handle_service_exceptions
async def update_technician_location(
    technician_id: UUID,
    latitude: float = Query(..., description="Current latitude"),
    longitude: float = Query(..., description="Current longitude"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> dict[str, str]:
    """Update technician's current location."""
    location_data = TechnicianUpdate(current_location={"latitude": latitude, "longitude": longitude})

    service.update_technician(tenant_id, technician_id, location_data)
    return {"message": "Location updated successfully"}


@router.get("/work-orders/{work_order_id}/tracking")
@handle_service_exceptions
async def get_work_order_tracking(
    work_order_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> dict[str, Any]:
    """Get real-time tracking information for a work order."""
    work_order = service.get_work_order_detail(tenant_id, work_order_id)

    return {
        "work_order_id": str(work_order_id),
        "status": work_order.status,
        "technician": {
            "id": str(work_order.technician_id) if work_order.technician_id else None,
            "name": work_order.technician.full_name if work_order.technician else None,
            "location": work_order.technician.current_location if work_order.technician else None,
        },
        "service_location": {
            "address": work_order.service_address,
            "coordinates": work_order.service_coordinates,
        },
        "schedule": {
            "start": work_order.scheduled_time_start,
            "end": work_order.scheduled_time_end,
        },
        "progress": {
            "percentage": work_order.progress_percentage,
            "estimated_completion": work_order.estimated_completion_time,
        },
        "last_update": work_order.updated_at,
    }


# Performance and Analytics Endpoints
@router.get("/technicians/{technician_id}/performance", response_model=PerformanceMetrics)
@handle_service_exceptions
async def get_technician_performance(
    technician_id: UUID,
    period_start: date = Query(..., description="Performance period start date"),
    period_end: date = Query(..., description="Performance period end date"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> PerformanceMetrics:
    """Calculate comprehensive performance metrics for a technician."""
    return service.calculate_technician_performance(tenant_id, technician_id, period_start, period_end)


@router.get(
    "/technicians/{technician_id}/route-optimization",
    response_model=list[WorkOrderResponse],
)
@handle_service_exceptions
async def optimize_technician_route(
    technician_id: UUID,
    target_date: date = Query(..., description="Date to optimize route for"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> list[WorkOrderResponse]:
    """Optimize work order sequence for a technician's day."""
    return service.optimize_technician_route(tenant_id, technician_id, target_date)


# Mobile App Integration Endpoints
@router.get("/mobile/technicians/{technician_id}/dashboard")
@handle_service_exceptions
async def get_mobile_dashboard(
    technician_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> dict[str, Any]:
    """Get mobile dashboard data for technician app."""
    technician = service.get_technician(tenant_id, technician_id)

    # Get today's work orders
    today_orders = service.get_technician_work_orders(
        tenant_id=tenant_id,
        technician_id=technician_id,
        date_from=date.today(),
        date_to=date.today(),
    )

    # Get optimized route for today
    optimized_route = service.optimize_technician_route(tenant_id, technician_id, date.today())

    return {
        "technician": technician,
        "today_summary": {
            "total_jobs": len(today_orders),
            "completed_jobs": len([wo for wo in today_orders if wo.status == WorkOrderStatus.COMPLETED]),
            "pending_jobs": len(
                [
                    wo
                    for wo in today_orders
                    if wo.status
                    in [
                        WorkOrderStatus.SCHEDULED,
                        WorkOrderStatus.DISPATCHED,
                        WorkOrderStatus.IN_PROGRESS,
                    ]
                ]
            ),
        },
        "next_job": optimized_route[0] if optimized_route else None,
        "optimized_route": optimized_route,
        "current_status": technician.current_status,
        "performance_summary": {
            "jobs_completed_today": technician.jobs_completed_today,
            "jobs_completed_week": technician.jobs_completed_week,
            "completion_rate": technician.completion_rate,
        },
    }


@router.post("/mobile/technicians/{technician_id}/checkin")
@handle_service_exceptions
async def mobile_checkin(
    technician_id: UUID,
    work_order_id: UUID = Query(..., description="Work order ID"),
    latitude: float = Query(..., description="Check-in latitude"),
    longitude: float = Query(..., description="Check-in longitude"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
) -> dict[str, str]:
    """Mobile app check-in at work order location."""
    # Update technician location
    location_update = TechnicianUpdate(current_location={"latitude": latitude, "longitude": longitude})
    service.update_technician(tenant_id, technician_id, location_update)

    # Update work order status to on-site
    service.update_work_order_status(
        tenant_id=tenant_id,
        work_order_id=work_order_id,
        new_status=WorkOrderStatus.ON_SITE,
        notes="Technician checked in on-site via mobile app",
        updated_by=f"MOBILE_APP_TECH_{technician_id}",
        location={"latitude": latitude, "longitude": longitude},
    )

    return {"message": "Check-in successful", "status": "on_site"}


@router.post("/mobile/technicians/{technician_id}/checkout")
@handle_service_exceptions
async def mobile_checkout(
    technician_id: UUID,
    work_order_id: UUID = Query(..., description="Work order ID"),
    tenant_id: str = Query(..., description="Tenant ID"),
    service: FieldOperationsService = Depends(get_field_service),
    completion_notes: Optional[str] = Query(None, description="Job completion notes"),
    customer_signature: Optional[str] = Query(None, description="Customer signature data"),
    customer_rating: Optional[int] = Query(None, ge=1, le=5, description="Customer satisfaction rating"),
) -> dict[str, str]:
    """Mobile app checkout after work order completion."""
    # Build completion notes with customer feedback
    notes = completion_notes or "Work completed via mobile app"

    if customer_rating:
        notes += f" | Customer rating: {customer_rating}/5 stars"

    if customer_signature:
        notes += " | Customer signature captured"

    # Update work order to completed
    service.update_work_order_status(
        tenant_id=tenant_id,
        work_order_id=work_order_id,
        new_status=WorkOrderStatus.COMPLETED,
        notes=notes,
        updated_by=f"MOBILE_APP_TECH_{technician_id}",
    )

    return {"message": "Work order completed successfully", "status": "completed"}
