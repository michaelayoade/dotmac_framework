"""Field operations service layer for work order and technician management."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date, time, timedelta
import secrets
import string

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dotmac_isp.shared.base_service import BaseTenantService
from .models import (
    WorkOrder,
    Technician,
    Appointment,
    TimeLog,
    FieldEquipment,
    WorkOrderStatus,
    WorkOrderPriority,
    WorkOrderType,
    TechnicianStatus,
    AppointmentStatus,
    EquipmentCondition,
)
from . import schemas
from dotmac_isp.shared.exceptions import (
    ServiceError,
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)


def generate_work_order_number() -> str:
    """Generate a unique work order number."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"WO-{timestamp}-{random_chars}"


def generate_appointment_id() -> str:
    """Generate a unique appointment ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp()
    return f"APT-{timestamp}"


class WorkOrderService:
    """Service layer for work order management."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize work order service with database session."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.work_order_repo = WorkOrderRepository(db, self.tenant_id)
        self.technician_repo = TechnicianRepository(db, self.tenant_id)

    async def create_work_order(
        self, work_order_data: schemas.WorkOrderCreate, created_by: str
    ) -> schemas.WorkOrder:
        """Create a new work order."""
        try:
            # Generate work order number
            work_order_number = generate_work_order_number()

            # Calculate estimated completion based on type and priority
            estimated_hours = self._estimate_work_hours(
                work_order_data.work_order_type, work_order_data.priority
            )

            create_data = {
                "work_order_number": work_order_number,
                "title": work_order_data.title,
                "description": work_order_data.description,
                "work_order_type": work_order_data.work_order_type,
                "priority": work_order_data.priority,
                "customer_id": work_order_data.customer_id,
                "service_id": work_order_data.service_id,
                "work_order_status": WorkOrderStatus.PENDING,
                "estimated_hours": estimated_hours,
                "created_by": created_by,
                "location_address": work_order_data.location_address,
                "location_notes": work_order_data.location_notes,
                "required_skills": work_order_data.required_skills,
                "estimated_cost": work_order_data.estimated_cost,
            }

            work_order = self.work_order_repo.create(create_data)
            return schemas.WorkOrder.from_orm(work_order)

        except Exception as e:
            raise ServiceError(f"Failed to create work order: {str(e)}")

    async def get_work_order(self, work_order_id: str) -> Optional[schemas.WorkOrder]:
        """Get work order by ID."""
        try:
            work_order = self.work_order_repo.get_by_id(work_order_id)
            if not work_order:
                raise NotFoundError(f"Work order {work_order_id} not found")

            return schemas.WorkOrder.from_orm(work_order)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get work order: {str(e)}")

    async def list_work_orders(
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
    ) -> List[schemas.WorkOrder]:
        """List work orders with filtering."""
        try:
            work_orders = self.work_order_repo.list_work_orders(
                skip=skip,
                limit=limit,
                status=status,
                priority=priority,
                work_order_type=work_order_type,
                assigned_technician_id=assigned_technician_id,
                customer_id=customer_id,
                scheduled_date=scheduled_date,
                overdue_only=overdue_only,
            )

            return [schemas.WorkOrder.from_orm(wo) for wo in work_orders]

        except Exception as e:
            raise ServiceError(f"Failed to list work orders: {str(e)}")

    async def assign_work_order(
        self,
        work_order_id: str,
        technician_id: str,
        scheduled_date: Optional[date] = None,
        scheduled_time_start: Optional[time] = None,
        assigned_by: str = None,
    ) -> schemas.WorkOrder:
        """Assign work order to technician."""
        try:
            # Verify work order exists
            work_order = self.work_order_repo.get_by_id(work_order_id)
            if not work_order:
                raise NotFoundError(f"Work order {work_order_id} not found")

            # Verify technician exists and is active
            technician = self.technician_repo.get_by_id(technician_id)
            if not technician:
                raise NotFoundError(f"Technician {technician_id} not found")

            if technician.employee_status != TechnicianStatus.ACTIVE:
                raise ValidationError(f"Technician {technician_id} is not active")

            # Check technician availability if date/time specified
            if scheduled_date and scheduled_time_start:
                is_available = await self._check_technician_availability(
                    technician_id, scheduled_date, scheduled_time_start
                )
                if not is_available:
                    raise ValidationError(
                        f"Technician is not available at requested time"
                    )

            # Update work order
            update_data = {
                "assigned_technician_id": technician_id,
                "work_order_status": WorkOrderStatus.ASSIGNED,
                "scheduled_date": scheduled_date,
                "scheduled_time_start": scheduled_time_start,
                "updated_by": assigned_by,
            }

            updated_work_order = self.work_order_repo.update(work_order_id, update_data)
            return schemas.WorkOrder.from_orm(updated_work_order)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to assign work order: {str(e)}")

    async def update_work_order_status(
        self,
        work_order_id: str,
        status: WorkOrderStatus,
        completion_notes: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> schemas.WorkOrder:
        """Update work order status."""
        try:
            work_order = self.work_order_repo.get_by_id(work_order_id)
            if not work_order:
                raise NotFoundError(f"Work order {work_order_id} not found")

            update_data = {"work_order_status": status, "updated_by": updated_by}

            # Handle status-specific updates
            if (
                status == WorkOrderStatus.IN_PROGRESS
                and not work_order.actual_start_time
            ):
                update_data["actual_start_time"] = datetime.now(timezone.utc)
            elif status == WorkOrderStatus.COMPLETED:
                update_data["actual_end_time"] = datetime.now(timezone.utc)
                update_data["progress_percentage"] = 100
                if completion_notes:
                    update_data["completion_notes"] = completion_notes
            elif status == WorkOrderStatus.CANCELLED:
                update_data["cancelled_at"] = datetime.now(timezone.utc)

            updated_work_order = self.work_order_repo.update(work_order_id, update_data)
            return schemas.WorkOrder.from_orm(updated_work_order)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to update work order status: {str(e)}")

    async def get_overdue_work_orders(self) -> List[schemas.WorkOrder]:
        """Get overdue work orders."""
        try:
            work_orders = self.work_order_repo.get_overdue_work_orders()
            return [schemas.WorkOrder.from_orm(wo) for wo in work_orders]

        except Exception as e:
            raise ServiceError(f"Failed to get overdue work orders: {str(e)}")

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get field operations dashboard statistics."""
        try:
            status_counts = self.work_order_repo.count_by_status()
            overdue_count = len(self.work_order_repo.get_overdue_work_orders()

            # Get active technicians count
            active_technicians = len(
                self.technician_repo.list_technicians(
                    status=TechnicianStatus.ACTIVE, limit=1000
                )
            )

            # Calculate totals
            total_work_orders = sum(item["count"] for item in status_counts)
            open_work_orders = sum(
                item["count"]
                for item in status_counts
                if item["status"]
                in [
                    WorkOrderStatus.PENDING,
                    WorkOrderStatus.SCHEDULED,
                    WorkOrderStatus.ASSIGNED,
                    WorkOrderStatus.IN_PROGRESS,
                ]
            )

            return {
                "total_work_orders": total_work_orders,
                "open_work_orders": open_work_orders,
                "overdue_work_orders": overdue_count,
                "active_technicians": active_technicians,
                "status_breakdown": status_counts,
            }

        except Exception as e:
            raise ServiceError(f"Failed to get dashboard stats: {str(e)}")

    def _estimate_work_hours(
        self, work_type: WorkOrderType, priority: WorkOrderPriority
    ) -> float:
        """Estimate work hours based on type and priority."""
        base_hours = {
            WorkOrderType.INSTALLATION: 4.0,
            WorkOrderType.REPAIR: 2.0,
            WorkOrderType.MAINTENANCE: 1.5,
            WorkOrderType.UPGRADE: 3.0,
            WorkOrderType.EMERGENCY: 1.0,
            WorkOrderType.INSPECTION: 1.0,
        }.get(work_type, 2.0)

        # Adjust for priority
        if priority == WorkOrderPriority.CRITICAL:
            return base_hours * 0.8  # Rush jobs might be faster
        elif priority == WorkOrderPriority.LOW:
            return base_hours * 1.2  # More thorough work

        return base_hours

    async def _check_technician_availability(
        self, technician_id: str, check_date: date, check_time: time
    ) -> bool:
        """Check if technician is available at specified date/time."""
        # This would check against scheduled work orders and appointments
        # For now, return True (simplified implementation)
        return True


class TechnicianService:
    """Service layer for technician management."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize technician service."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.technician_repo = TechnicianRepository(db, self.tenant_id)
        self.work_order_repo = WorkOrderRepository(db, self.tenant_id)

    async def create_technician(
        self, technician_data: schemas.TechnicianCreate, created_by: str
    ) -> schemas.Technician:
        """Create a new technician."""
        try:
            create_data = {
                "employee_id": technician_data.employee_id,
                "first_name": technician_data.first_name,
                "last_name": technician_data.last_name,
                "email": technician_data.email,
                "phone": technician_data.phone,
                "hire_date": technician_data.hire_date,
                "skill_level": technician_data.skill_level,
                "specializations": technician_data.specializations,
                "created_by": created_by,
            }

            technician = self.technician_repo.create(create_data)
            return schemas.Technician.from_orm(technician)

        except ConflictError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create technician: {str(e)}")

    async def get_technician(self, technician_id: str) -> Optional[schemas.Technician]:
        """Get technician by ID."""
        try:
            technician = self.technician_repo.get_by_id(technician_id)
            if not technician:
                raise NotFoundError(f"Technician {technician_id} not found")

            return schemas.Technician.from_orm(technician)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get technician: {str(e)}")

    async def list_technicians(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TechnicianStatus] = None,
        skill_level: Optional[str] = None,
        available_only: bool = False,
    ) -> List[schemas.Technician]:
        """List technicians with filtering."""
        try:
            technicians = self.technician_repo.list_technicians(
                skip=skip,
                limit=limit,
                status=status,
                skill_level=skill_level,
                available_only=available_only,
            )

            return [schemas.Technician.from_orm(tech) for tech in technicians]

        except Exception as e:
            raise ServiceError(f"Failed to list technicians: {str(e)}")

    async def get_technician_workload(
        self, technician_id: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Get technician workload for date range."""
        try:
            # Verify technician exists
            technician = self.technician_repo.get_by_id(technician_id)
            if not technician:
                raise NotFoundError(f"Technician {technician_id} not found")

            # Get work orders
            work_orders = self.work_order_repo.get_technician_workload(
                technician_id, start_date, end_date
            )

            # Calculate workload statistics
            total_hours = sum(wo.estimated_hours or 0 for wo in work_orders)
            completed_orders = [
                wo
                for wo in work_orders
                if wo.work_order_status == WorkOrderStatus.COMPLETED
            ]
            pending_orders = [
                wo
                for wo in work_orders
                if wo.work_order_status
                in [
                    WorkOrderStatus.PENDING,
                    WorkOrderStatus.SCHEDULED,
                    WorkOrderStatus.ASSIGNED,
                ]
            ]

            return {
                "technician_id": technician_id,
                "period": {"start_date": start_date, "end_date": end_date},
                "workload_summary": {
                    "total_work_orders": len(work_orders),
                    "completed_work_orders": len(completed_orders),
                    "pending_work_orders": len(pending_orders),
                    "total_estimated_hours": total_hours,
                    "completion_rate": (
                        (len(completed_orders) / len(work_orders) * 100)
                        if work_orders
                        else 0
                    ),
                },
                "work_orders": [schemas.WorkOrder.from_orm(wo) for wo in work_orders],
            }

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get technician workload: {str(e)}")


class AppointmentService:
    """Service layer for appointment management."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize appointment service."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.appointment_repo = AppointmentRepository(db, self.tenant_id)
        self.technician_repo = TechnicianRepository(db, self.tenant_id)

    async def create_appointment(
        self, appointment_data: schemas.AppointmentCreate, created_by: str
    ) -> schemas.Appointment:
        """Create a new appointment."""
        try:
            # Check availability
            is_available = self.appointment_repo.check_availability(
                appointment_data.technician_id,
                appointment_data.appointment_date,
                appointment_data.time_slot_start,
                appointment_data.time_slot_end,
            )

            if not is_available:
                raise ValidationError(
                    f"Technician is not available for the requested time slot"
                )

            # Generate appointment ID
            appointment_id = generate_appointment_id()

            create_data = {
                "appointment_id": appointment_id,
                "work_order_id": appointment_data.work_order_id,
                "technician_id": appointment_data.technician_id,
                "customer_id": appointment_data.customer_id,
                "appointment_date": appointment_data.appointment_date,
                "time_slot_start": appointment_data.time_slot_start,
                "time_slot_end": appointment_data.time_slot_end,
                "appointment_type": appointment_data.appointment_type,
                "appointment_status": AppointmentStatus.SCHEDULED,
                "created_by": created_by,
                "notes": appointment_data.notes,
            }

            appointment = self.appointment_repo.create(create_data)
            return schemas.Appointment.from_orm(appointment)

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create appointment: {str(e)}")

    async def get_technician_schedule(
        self, technician_id: str, start_date: date, end_date: date
    ) -> List[schemas.Appointment]:
        """Get technician's schedule for date range."""
        try:
            # Verify technician exists
            technician = self.technician_repo.get_by_id(technician_id)
            if not technician:
                raise NotFoundError(f"Technician {technician_id} not found")

            appointments = self.appointment_repo.get_technician_schedule(
                technician_id, start_date, end_date
            )

            return [schemas.Appointment.from_orm(apt) for apt in appointments]

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get technician schedule: {str(e)}")


class FieldEquipmentService:
    """Service layer for field equipment management."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize field equipment service."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.equipment_repo = FieldEquipmentRepository(db, self.tenant_id)
        self.technician_repo = TechnicianRepository(db, self.tenant_id)

    async def create_equipment(
        self, equipment_data: schemas.FieldEquipmentCreate, created_by: str
    ) -> schemas.FieldEquipment:
        """Create a new equipment item."""
        try:
            create_data = {
                "equipment_id": equipment_data.equipment_id,
                "name": equipment_data.name,
                "category": equipment_data.category,
                "condition": equipment_data.condition,
                "serial_number": equipment_data.serial_number,
                "purchase_date": equipment_data.purchase_date,
                "warranty_expires": equipment_data.warranty_expires,
                "created_by": created_by,
            }

            equipment = self.equipment_repo.create(create_data)
            return schemas.FieldEquipment.from_orm(equipment)

        except ConflictError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create equipment: {str(e)}")

    async def assign_equipment(
        self, equipment_id: str, technician_id: str, assigned_by: str
    ) -> schemas.FieldEquipment:
        """Assign equipment to technician."""
        try:
            # Verify equipment exists
            equipment = self.equipment_repo.get_by_id(equipment_id)
            if not equipment:
                raise NotFoundError(f"Equipment {equipment_id} not found")

            # Verify technician exists
            technician = self.technician_repo.get_by_id(technician_id)
            if not technician:
                raise NotFoundError(f"Technician {technician_id} not found")

            success = self.equipment_repo.assign_equipment(equipment_id, technician_id)
            if not success:
                raise ServiceError("Failed to assign equipment")

            # Get updated equipment
            updated_equipment = self.equipment_repo.get_by_id(equipment_id)
            return schemas.FieldEquipment.from_orm(updated_equipment)

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to assign equipment: {str(e)}")

    async def get_technician_equipment(
        self, technician_id: str
    ) -> List[schemas.FieldEquipment]:
        """Get equipment assigned to technician."""
        try:
            # Verify technician exists
            technician = self.technician_repo.get_by_id(technician_id)
            if not technician:
                raise NotFoundError(f"Technician {technician_id} not found")

            equipment_list = self.equipment_repo.get_technician_equipment(technician_id)
            return [schemas.FieldEquipment.from_orm(eq) for eq in equipment_list]

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get technician equipment: {str(e)}")
