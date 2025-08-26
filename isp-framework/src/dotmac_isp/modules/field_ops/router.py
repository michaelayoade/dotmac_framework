"""Field Operations API endpoints."""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from .models import (
    WorkOrder,
    Technician,
    Appointment,
    TimeLog,
    FieldEquipment,
    ServiceRoute,
    WorkOrderType,
    WorkOrderStatus,
    WorkOrderPriority,
    TechnicianStatus,
    AppointmentStatus,
    EquipmentCondition,
)
from .service import (
    WorkOrderService,
    TechnicianService,
    AppointmentService,
    FieldEquipmentService,
)
from datetime import timezone
from dotmac_isp.shared.exceptions import NotFoundError, ValidationError, ServiceError

router = APIRouter(prefix="/field-ops", tags=["field-operations"])


def generate_work_order_number() -> str:
    """Generate a unique work order number."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"WO-{timestamp}-{random_chars}"


def generate_appointment_id() -> str:
    """Generate a unique appointment ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"APT-{timestamp}"


# Work Orders Management
@router.post("/work-orders")
async def create_work_order(
    title: str,
    description: str,
    work_order_type: WorkOrderType,
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL,
    customer_id: Optional[str] = None,
    service_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new work order."""
    try:
        service = WorkOrderService(db, tenant_id)
        work_order_data = {
            "title": title,
            "description": description,
            "work_order_type": work_order_type,
            "priority": priority,
            "customer_id": customer_id,
            "service_id": service_id,
        }
        work_order = await service.create_work_order(work_order_data)
        return work_order
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/work-orders")
async def list_work_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[WorkOrderStatus] = None,
    priority: Optional[WorkOrderPriority] = None,
    work_order_type: Optional[WorkOrderType] = None,
    technician_id: Optional[str] = None,
    overdue: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List work orders."""
    try:
        service = WorkOrderService(db, tenant_id)
        work_orders = await service.list_work_orders(
            skip=skip,
            limit=limit,
            status=status,
            priority=priority,
            work_order_type=work_order_type,
            technician_id=technician_id,
            overdue_only=overdue,
        )
        return work_orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/work-orders/{work_order_id}")
async def get_work_order(
    work_order_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific work order."""
    try:
        service = WorkOrderService(db, tenant_id)
        work_order = await service.get_work_order(work_order_id)
        return work_order
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Work order not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/work-orders/{work_order_id}/assign")
async def assign_work_order(
    work_order_id: str,
    technician_id: str,
    scheduled_date: Optional[date] = None,
    scheduled_time_start: Optional[time] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Assign a work order to a technician."""
    try:
        service = WorkOrderService(db, tenant_id)
        work_order = await service.assign_work_order(
            work_order_id=work_order_id,
            technician_id=technician_id,
            scheduled_date=scheduled_date,
            scheduled_time_start=scheduled_time_start,
        )
        return work_order
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/work-orders/{work_order_id}/status")
async def update_work_order_status(
    work_order_id: str,
    status: WorkOrderStatus,
    completion_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update work order status."""
    try:
        service = WorkOrderService(db, tenant_id)
        if status == WorkOrderStatus.COMPLETED:
            work_order = await service.complete_work_order(
                work_order_id, completion_notes
            )
        else:
            work_order = await service.update_work_order_status(work_order_id, status)
        return work_order
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Work order not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Technicians Management
@router.post("/technicians")
async def create_technician(
    employee_id: str,
    first_name: str,
    last_name: str,
    hire_date: date,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new technician."""
    try:
        service = TechnicianService(db, tenant_id)
        technician_data = {
            "employee_id": employee_id,
            "first_name": first_name,
            "last_name": last_name,
            "hire_date": hire_date,
            "email": email,
            "phone": phone,
        }
        technician = await service.create_technician(technician_data)
        return technician
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technicians")
async def list_technicians(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TechnicianStatus] = None,
    skill_level: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List technicians."""
    try:
        service = TechnicianService(db, tenant_id)
        technicians = await service.list_technicians(
            skip=skip, limit=limit, status=status, skill_level=skill_level
        )
        return technicians
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technicians/{technician_id}")
async def get_technician(
    technician_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get a specific technician."""
    try:
        service = TechnicianService(db, tenant_id)
        technician = await service.get_technician(technician_id)
        return technician
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Technician not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Appointments Management
@router.post("/appointments")
async def create_appointment(
    work_order_id: str,
    technician_id: str,
    appointment_date: date,
    time_slot_start: time,
    time_slot_end: time,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new appointment."""
    try:
        service = AppointmentService(db, tenant_id)
        appointment_data = {
            "work_order_id": work_order_id,
            "technician_id": technician_id,
            "customer_id": customer_id,
            "appointment_date": appointment_date,
            "time_slot_start": time_slot_start,
            "time_slot_end": time_slot_end,
        }
        appointment = await service.create_appointment(appointment_data)
        return appointment
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/appointments")
async def list_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    technician_id: Optional[str] = None,
    appointment_date: Optional[date] = None,
    status: Optional[AppointmentStatus] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List appointments."""
    try:
        service = AppointmentService(db, tenant_id)
        appointments = await service.list_appointments(
            skip=skip,
            limit=limit,
            technician_id=technician_id,
            appointment_date=appointment_date,
            status=status,
        )
        return appointments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Time Tracking
@router.post("/time-logs")
async def create_time_log(
    technician_id: str,
    activity_type: str,
    start_time: datetime,
    work_order_id: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new time log entry."""

    db_time_log = TimeLog(
        id=str(uuid4()),
        tenant_id=tenant_id,
        technician_id=technician_id,
        work_order_id=work_order_id,
        log_date=start_time.date(),
        start_time=start_time,
        activity_type=activity_type,
        description=description,
    )

    db.add(db_time_log)
    db.commit()
    db.refresh(db_time_log)

    return db_time_log


@router.put("/time-logs/{time_log_id}/end")
async def end_time_log(
    time_log_id: str,
    end_time: datetime,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """End a time log entry."""

    time_log = (
        db.query(TimeLog)
        .filter(and_(TimeLog.id == time_log_id, TimeLog.tenant_id == tenant_id))
        .first()
    )

    if not time_log:
        raise HTTPException(status_code=404, detail="Time log not found")

    time_log.end_time = end_time
    time_log.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(time_log)

    return time_log


# Equipment Management
@router.post("/equipment")
async def create_equipment(
    equipment_id: str,
    name: str,
    category: str,
    condition: EquipmentCondition = EquipmentCondition.GOOD,
    assigned_to_technician: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new equipment item."""
    try:
        service = FieldEquipmentService(db, tenant_id)
        equipment_data = {
            "equipment_id": equipment_id,
            "name": name,
            "category": category,
            "condition": condition,
            "assigned_to_technician": assigned_to_technician,
        }
        equipment = await service.create_equipment(equipment_data)
        return equipment
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment")
async def list_equipment(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    condition: Optional[EquipmentCondition] = None,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List equipment."""
    try:
        service = FieldEquipmentService(db, tenant_id)
        equipment = await service.list_equipment(
            skip=skip,
            limit=limit,
            category=category,
            condition=condition,
            assigned_to=assigned_to,
        )
        return equipment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Dashboard and Reports
@router.get("/dashboard")
async def get_field_ops_dashboard(
    db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant)
):
    """Get field operations dashboard data."""

    # Work order statistics
    total_work_orders = (
        db.query(WorkOrder).filter(WorkOrder.tenant_id == tenant_id).count()
    )

    open_work_orders = (
        db.query(WorkOrder)
        .filter(
            and_(
                WorkOrder.tenant_id == tenant_id,
                WorkOrder.work_order_status.in_(
                    [
                        WorkOrderStatus.PENDING,
                        WorkOrderStatus.SCHEDULED,
                        WorkOrderStatus.ASSIGNED,
                        WorkOrderStatus.IN_PROGRESS,
                    ]
                ),
            )
        )
        .count()
    )

    overdue_work_orders = (
        db.query(WorkOrder)
        .filter(
            and_(
                WorkOrder.tenant_id == tenant_id,
                WorkOrder.scheduled_date < date.today(),
                WorkOrder.work_order_status.in_(
                    [
                        WorkOrderStatus.PENDING,
                        WorkOrderStatus.SCHEDULED,
                        WorkOrderStatus.ASSIGNED,
                        WorkOrderStatus.IN_PROGRESS,
                    ]
                ),
            )
        )
        .count()
    )

    # Technician statistics
    active_technicians = (
        db.query(Technician)
        .filter(
            and_(
                Technician.tenant_id == tenant_id,
                Technician.employee_status == TechnicianStatus.ACTIVE,
            )
        )
        .count()
    )

    # Today's appointments
    today_appointments = (
        db.query(Appointment)
        .filter(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.appointment_date == date.today(),
            )
        )
        .count()
    )

    # Recent work orders
    recent_work_orders = (
        db.query(WorkOrder)
        .filter(WorkOrder.tenant_id == tenant_id)
        .order_by(desc(WorkOrder.created_at))
        .limit(10)
        .all()
    )

    # Work order status breakdown
    status_breakdown = (
        db.query(WorkOrder.work_order_status, func.count(WorkOrder.id))
        .filter(WorkOrder.tenant_id == tenant_id)
        .group_by(WorkOrder.work_order_status)
        .all()
    )

    return {
        "summary": {
            "total_work_orders": total_work_orders,
            "open_work_orders": open_work_orders,
            "overdue_work_orders": overdue_work_orders,
            "active_technicians": active_technicians,
            "today_appointments": today_appointments,
        },
        "status_breakdown": [
            {"status": status[0], "count": status[1]} for status in status_breakdown
        ],
        "recent_work_orders": [
            {
                "work_order_number": wo.work_order_number,
                "title": wo.title,
                "work_order_type": wo.work_order_type,
                "priority": wo.priority,
                "status": wo.work_order_status,
                "created_at": wo.created_at,
            }
            for wo in recent_work_orders
        ],
    }


@router.get("/reports/technician-performance")
async def get_technician_performance_report(
    start_date: date,
    end_date: date,
    technician_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get technician performance report."""

    query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.tenant_id == tenant_id,
            WorkOrder.scheduled_date >= start_date,
            WorkOrder.scheduled_date <= end_date,
        )
    )

    if technician_id:
        query = query.filter(WorkOrder.assigned_technician_id == technician_id)

    work_orders = query.all()

    # Calculate performance metrics
    total_orders = len(work_orders)
    completed_orders = len(
        [wo for wo in work_orders if wo.work_order_status == WorkOrderStatus.COMPLETED]
    )
    on_time_orders = len(
        [
            wo
            for wo in work_orders
            if wo.work_order_status == WorkOrderStatus.COMPLETED
            and wo.actual_end_time
            and wo.scheduled_date
            and wo.actual_end_time.date() <= wo.scheduled_date
        ]
    )

    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
    on_time_rate = (
        (on_time_orders / completed_orders * 100) if completed_orders > 0 else 0
    )

    return {
        "report_period": {"start_date": start_date, "end_date": end_date},
        "technician_id": technician_id,
        "metrics": {
            "total_work_orders": total_orders,
            "completed_work_orders": completed_orders,
            "on_time_completions": on_time_orders,
            "completion_rate": round(completion_rate, 2),
            "on_time_rate": round(on_time_rate, 2),
        },
        "work_orders": [
            {
                "work_order_number": wo.work_order_number,
                "title": wo.title,
                "scheduled_date": wo.scheduled_date,
                "actual_start_time": wo.actual_start_time,
                "actual_end_time": wo.actual_end_time,
                "status": wo.work_order_status,
            }
            for wo in work_orders
        ],
    }
