"""Repository pattern for field operations database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, asc

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
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class WorkOrderRepository:
    """Repository for work order database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, work_order_data: Dict[str, Any]) -> WorkOrder:
        """Create a new work order."""
        try:
            work_order = WorkOrder(
                id=str(uuid4()), tenant_id=str(self.tenant_id), **work_order_data
            )

            self.db.add(work_order)
            self.db.commit()
            self.db.refresh(work_order)
            return work_order

        except IntegrityError as e:
            self.db.rollback()
            if "work_order_number" in str(e):
                raise ConflictError(
                    f"Work order number {work_order_data.get('work_order_number')} already exists"
                )
            raise ConflictError("Work order creation failed due to data conflict")

    def get_by_id(self, work_order_id: str) -> Optional[WorkOrder]:
        """Get work order by ID."""
        return (
            self.db.query(WorkOrder)
            .filter(
                and_(
                    WorkOrder.id == work_order_id,
                    WorkOrder.tenant_id == str(self.tenant_id),
                    WorkOrder.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_work_order_number(self, work_order_number: str) -> Optional[WorkOrder]:
        """Get work order by work order number."""
        return (
            self.db.query(WorkOrder)
            .filter(
                and_(
                    WorkOrder.work_order_number == work_order_number,
                    WorkOrder.tenant_id == str(self.tenant_id),
                    WorkOrder.is_deleted == False,
                )
            )
            .first()
        )

    def list_work_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[WorkOrderStatus] = None,
        priority: Optional[WorkOrderPriority] = None,
        work_order_type: Optional[WorkOrderType] = None,
        assigned_technician_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        scheduled_date: Optional[date] = None,
        overdue_only: bool = False,
    ) -> List[WorkOrder]:
        """List work orders with filtering."""
        query = self.db.query(WorkOrder).filter(
            and_(
                WorkOrder.tenant_id == str(self.tenant_id),
                WorkOrder.is_deleted == False,
            )
        )

        if status:
            query = query.filter(WorkOrder.work_order_status == status)
        if priority:
            query = query.filter(WorkOrder.priority == priority)
        if work_order_type:
            query = query.filter(WorkOrder.work_order_type == work_order_type)
        if assigned_technician_id:
            query = query.filter(
                WorkOrder.assigned_technician_id == assigned_technician_id
            )
        if customer_id:
            query = query.filter(WorkOrder.customer_id == customer_id)
        if scheduled_date:
            query = query.filter(WorkOrder.scheduled_date == scheduled_date)

        if overdue_only:
            query = query.filter(
                and_(
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

        return (
            query.order_by(desc(WorkOrder.created_at)).offset(skip).limit(limit).all()
        )

    def update(
        self, work_order_id: str, update_data: Dict[str, Any]
    ) -> Optional[WorkOrder]:
        """Update work order."""
        work_order = self.get_by_id(work_order_id)
        if not work_order:
            return None

        for key, value in update_data.items():
            if hasattr(work_order, key):
                setattr(work_order, key, value)

        work_order.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(work_order)
        return work_order

    def delete(self, work_order_id: str) -> bool:
        """Soft delete work order."""
        work_order = self.get_by_id(work_order_id)
        if not work_order:
            return False

        work_order.soft_delete()
        self.db.commit()
        return True

    def get_overdue_work_orders(self) -> List[WorkOrder]:
        """Get overdue work orders."""
        return (
            self.db.query(WorkOrder)
            .filter(
                and_(
                    WorkOrder.tenant_id == str(self.tenant_id),
                    WorkOrder.is_deleted == False,
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
            .all()
        )

    def count_by_status(self) -> List[Dict[str, Any]]:
        """Count work orders by status."""
        result = (
            self.db.query(
                WorkOrder.work_order_status, func.count(WorkOrder.id).label("count")
            )
            .filter(
                and_(
                    WorkOrder.tenant_id == str(self.tenant_id),
                    WorkOrder.is_deleted == False,
                )
            )
            .group_by(WorkOrder.work_order_status)
            .all()
        )

        return [{"status": row.work_order_status, "count": row.count} for row in result]

    def get_technician_workload(
        self, technician_id: str, start_date: date, end_date: date
    ) -> List[WorkOrder]:
        """Get work orders assigned to a technician in date range."""
        return (
            self.db.query(WorkOrder)
            .filter(
                and_(
                    WorkOrder.tenant_id == str(self.tenant_id),
                    WorkOrder.is_deleted == False,
                    WorkOrder.assigned_technician_id == technician_id,
                    WorkOrder.scheduled_date >= start_date,
                    WorkOrder.scheduled_date <= end_date,
                )
            )
            .order_by(WorkOrder.scheduled_date, WorkOrder.scheduled_time_start)
            .all()
        )


class TechnicianRepository:
    """Repository for technician database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, technician_data: Dict[str, Any]) -> Technician:
        """Create a new technician."""
        try:
            technician = Technician(
                id=str(uuid4()), tenant_id=str(self.tenant_id), **technician_data
            )

            self.db.add(technician)
            self.db.commit()
            self.db.refresh(technician)
            return technician

        except IntegrityError as e:
            self.db.rollback()
            if "employee_id" in str(e):
                raise ConflictError(
                    f"Employee ID {technician_data.get('employee_id')} already exists"
                )
            raise ConflictError("Technician creation failed due to data conflict")

    def get_by_id(self, technician_id: str) -> Optional[Technician]:
        """Get technician by ID."""
        return (
            self.db.query(Technician)
            .filter(
                and_(
                    Technician.id == technician_id,
                    Technician.tenant_id == str(self.tenant_id),
                    Technician.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_employee_id(self, employee_id: str) -> Optional[Technician]:
        """Get technician by employee ID."""
        return (
            self.db.query(Technician)
            .filter(
                and_(
                    Technician.employee_id == employee_id,
                    Technician.tenant_id == str(self.tenant_id),
                    Technician.is_deleted == False,
                )
            )
            .first()
        )

    def list_technicians(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TechnicianStatus] = None,
        skill_level: Optional[str] = None,
        available_only: bool = False,
    ) -> List[Technician]:
        """List technicians with filtering."""
        query = self.db.query(Technician).filter(
            and_(
                Technician.tenant_id == str(self.tenant_id),
                Technician.is_deleted == False,
            )
        )

        if status:
            query = query.filter(Technician.employee_status == status)
        if skill_level:
            query = query.filter(Technician.skill_level == skill_level)
        if available_only:
            query = query.filter(Technician.current_availability == True)

        return (
            query.order_by(Technician.last_name, Technician.first_name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(
        self, technician_id: str, update_data: Dict[str, Any]
    ) -> Optional[Technician]:
        """Update technician."""
        technician = self.get_by_id(technician_id)
        if not technician:
            return None

        for key, value in update_data.items():
            if hasattr(technician, key):
                setattr(technician, key, value)

        technician.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(technician)
        return technician

    def get_available_technicians(
        self, date_time: datetime, skill_requirements: Optional[List[str]] = None
    ) -> List[Technician]:
        """Get technicians available at specific date/time."""
        query = self.db.query(Technician).filter(
            and_(
                Technician.tenant_id == str(self.tenant_id),
                Technician.is_deleted == False,
                Technician.employee_status == TechnicianStatus.ACTIVE,
                Technician.current_availability == True,
            )
        )

        # Additional logic would check against scheduled appointments and work orders
        # For now, return all active technicians
        return query.all()


class AppointmentRepository:
    """Repository for appointment database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, appointment_data: Dict[str, Any]) -> Appointment:
        """Create a new appointment."""
        appointment = Appointment(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **appointment_data
        )

        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        """Get appointment by ID."""
        return (
            self.db.query(Appointment)
            .filter(
                and_(
                    Appointment.id == appointment_id,
                    Appointment.tenant_id == str(self.tenant_id),
                    Appointment.is_deleted == False,
                )
            )
            .first()
        )

    def list_appointments(
        self,
        skip: int = 0,
        limit: int = 100,
        technician_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        appointment_date: Optional[date] = None,
        status: Optional[AppointmentStatus] = None,
    ) -> List[Appointment]:
        """List appointments with filtering."""
        query = self.db.query(Appointment).filter(
            and_(
                Appointment.tenant_id == str(self.tenant_id),
                Appointment.is_deleted == False,
            )
        )

        if technician_id:
            query = query.filter(Appointment.technician_id == technician_id)
        if customer_id:
            query = query.filter(Appointment.customer_id == customer_id)
        if appointment_date:
            query = query.filter(Appointment.appointment_date == appointment_date)
        if status:
            query = query.filter(Appointment.appointment_status == status)

        return (
            query.order_by(Appointment.appointment_date, Appointment.time_slot_start)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_technician_schedule(
        self, technician_id: str, start_date: date, end_date: date
    ) -> List[Appointment]:
        """Get technician's schedule for date range."""
        return (
            self.db.query(Appointment)
            .filter(
                and_(
                    Appointment.tenant_id == str(self.tenant_id),
                    Appointment.is_deleted == False,
                    Appointment.technician_id == technician_id,
                    Appointment.appointment_date >= start_date,
                    Appointment.appointment_date <= end_date,
                )
            )
            .order_by(Appointment.appointment_date, Appointment.time_slot_start)
            .all()
        )

    def check_availability(
        self,
        technician_id: str,
        appointment_date: date,
        time_start: time,
        time_end: time,
    ) -> bool:
        """Check if technician is available for time slot."""
        existing = (
            self.db.query(Appointment)
            .filter(
                and_(
                    Appointment.tenant_id == str(self.tenant_id),
                    Appointment.is_deleted == False,
                    Appointment.technician_id == technician_id,
                    Appointment.appointment_date == appointment_date,
                    Appointment.appointment_status.in_(
                        [
                            AppointmentStatus.SCHEDULED,
                            AppointmentStatus.CONFIRMED,
                            AppointmentStatus.IN_PROGRESS,
                        ]
                    ),
                    or_(
                        and_(
                            Appointment.time_slot_start <= time_start,
                            Appointment.time_slot_end > time_start,
                        ),
                        and_(
                            Appointment.time_slot_start < time_end,
                            Appointment.time_slot_end >= time_end,
                        ),
                        and_(
                            Appointment.time_slot_start >= time_start,
                            Appointment.time_slot_end <= time_end,
                        ),
                    ),
                )
            )
            .first()
        )

        return existing is None


class TimeLogRepository:
    """Repository for time log database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, time_log_data: Dict[str, Any]) -> TimeLog:
        """Create a new time log entry."""
        time_log = TimeLog(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **time_log_data
        )

        self.db.add(time_log)
        self.db.commit()
        self.db.refresh(time_log)
        return time_log

    def get_by_id(self, time_log_id: str) -> Optional[TimeLog]:
        """Get time log by ID."""
        return (
            self.db.query(TimeLog)
            .filter(
                and_(
                    TimeLog.id == time_log_id,
                    TimeLog.tenant_id == str(self.tenant_id),
                    TimeLog.is_deleted == False,
                )
            )
            .first()
        )

    def get_technician_time_logs(
        self, technician_id: str, start_date: date, end_date: date
    ) -> List[TimeLog]:
        """Get time logs for technician in date range."""
        return (
            self.db.query(TimeLog)
            .filter(
                and_(
                    TimeLog.tenant_id == str(self.tenant_id),
                    TimeLog.is_deleted == False,
                    TimeLog.technician_id == technician_id,
                    TimeLog.log_date >= start_date,
                    TimeLog.log_date <= end_date,
                )
            )
            .order_by(TimeLog.log_date, TimeLog.start_time)
            .all()
        )

    def get_active_time_log(self, technician_id: str) -> Optional[TimeLog]:
        """Get active (not ended) time log for technician."""
        return (
            self.db.query(TimeLog)
            .filter(
                and_(
                    TimeLog.tenant_id == str(self.tenant_id),
                    TimeLog.is_deleted == False,
                    TimeLog.technician_id == technician_id,
                    TimeLog.end_time.is_(None),
                )
            )
            .first()
        )

    def update(
        self, time_log_id: str, update_data: Dict[str, Any]
    ) -> Optional[TimeLog]:
        """Update time log entry."""
        time_log = self.get_by_id(time_log_id)
        if not time_log:
            return None

        for key, value in update_data.items():
            if hasattr(time_log, key):
                setattr(time_log, key, value)

        time_log.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(time_log)
        return time_log


class FieldEquipmentRepository:
    """Repository for field equipment database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, equipment_data: Dict[str, Any]) -> FieldEquipment:
        """Create a new equipment item."""
        try:
            equipment = FieldEquipment(
                id=str(uuid4()), tenant_id=str(self.tenant_id), **equipment_data
            )

            self.db.add(equipment)
            self.db.commit()
            self.db.refresh(equipment)
            return equipment

        except IntegrityError as e:
            self.db.rollback()
            if "equipment_id" in str(e):
                raise ConflictError(
                    f"Equipment ID {equipment_data.get('equipment_id')} already exists"
                )
            raise ConflictError("Equipment creation failed due to data conflict")

    def get_by_id(self, equipment_id: str) -> Optional[FieldEquipment]:
        """Get equipment by ID."""
        return (
            self.db.query(FieldEquipment)
            .filter(
                and_(
                    FieldEquipment.id == equipment_id,
                    FieldEquipment.tenant_id == str(self.tenant_id),
                    FieldEquipment.is_deleted == False,
                )
            )
            .first()
        )

    def list_equipment(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        condition: Optional[EquipmentCondition] = None,
        assigned_to: Optional[str] = None,
        available_only: bool = False,
    ) -> List[FieldEquipment]:
        """List equipment with filtering."""
        query = self.db.query(FieldEquipment).filter(
            and_(
                FieldEquipment.tenant_id == str(self.tenant_id),
                FieldEquipment.is_deleted == False,
            )
        )

        if category:
            query = query.filter(FieldEquipment.category == category)
        if condition:
            query = query.filter(FieldEquipment.condition == condition)
        if assigned_to:
            query = query.filter(FieldEquipment.assigned_to_technician == assigned_to)
        if available_only:
            query = query.filter(FieldEquipment.assigned_to_technician.is_(None))

        return query.order_by(FieldEquipment.name).offset(skip).limit(limit).all()

    def get_technician_equipment(self, technician_id: str) -> List[FieldEquipment]:
        """Get equipment assigned to technician."""
        return (
            self.db.query(FieldEquipment)
            .filter(
                and_(
                    FieldEquipment.tenant_id == str(self.tenant_id),
                    FieldEquipment.is_deleted == False,
                    FieldEquipment.assigned_to_technician == technician_id,
                )
            )
            .order_by(FieldEquipment.name)
            .all()
        )

    def assign_equipment(self, equipment_id: str, technician_id: str) -> bool:
        """Assign equipment to technician."""
        equipment = self.get_by_id(equipment_id)
        if not equipment:
            return False

        equipment.assigned_to_technician = technician_id
        equipment.assignment_date = datetime.utcnow()
        equipment.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def unassign_equipment(self, equipment_id: str) -> bool:
        """Unassign equipment from technician."""
        equipment = self.get_by_id(equipment_id)
        if not equipment:
            return False

        equipment.assigned_to_technician = None
        equipment.assignment_date = None
        equipment.updated_at = datetime.utcnow()

        self.db.commit()
        return True
