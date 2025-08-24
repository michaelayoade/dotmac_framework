"""Field Operations models for technician dispatch, work orders, and field management."""

from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Time,
    Integer,
    Float,
    Numeric,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin
from dotmac_isp.shared.models import ContactMixin, AddressMixin
from dotmac_isp.shared.database.relationship_registry import register_cross_module_relationship


class WorkOrderType(str, Enum):
    """Work order types."""

    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    UPGRADE = "upgrade"
    INSPECTION = "inspection"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    RELOCATION = "relocation"
    EMERGENCY = "emergency"


class WorkOrderStatus(str, Enum):
    """Work order status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class WorkOrderPriority(str, Enum):
    """Work order priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class TechnicianStatus(str, Enum):
    """Technician status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class TechnicianSkillLevel(str, Enum):
    """Technician skill levels."""

    TRAINEE = "trainee"
    JUNIOR = "junior"
    INTERMEDIATE = "intermediate"
    SENIOR = "senior"
    EXPERT = "expert"


class EquipmentCondition(str, Enum):
    """Equipment condition status."""

    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"
    DEFECTIVE = "defective"


class AppointmentStatus(str, Enum):
    """Appointment status."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class WorkOrder(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Work orders for field operations."""

    __tablename__ = "field_work_orders"

    # Work order identification
    work_order_number = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    # Classification
    work_order_type = Column(SQLEnum(WorkOrderType), nullable=False, index=True)
    priority = Column(
        SQLEnum(WorkOrderPriority),
        default=WorkOrderPriority.NORMAL,
        nullable=False,
        index=True,
    )
    category = Column(String(100), nullable=True)

    # Customer and service information
    customer_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to customer
    service_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to service
    project_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to installation project
    account_number = Column(String(100), nullable=True)

    # Scheduling
    requested_date = Column(Date, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    scheduled_time_start = Column(Time, nullable=True)
    scheduled_time_end = Column(Time, nullable=True)

    # Assignment
    assigned_technician_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_technicians.id"),
        nullable=True,
        index=True,
    )
    assigned_team = Column(String(100), nullable=True)

    # Status and progress
    work_order_status = Column(
        SQLEnum(WorkOrderStatus),
        default=WorkOrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    progress_percentage = Column(Integer, default=0, nullable=False)

    # Timing
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)

    # Work details
    work_performed = Column(Text, nullable=True)
    materials_used = Column(JSON, nullable=True)
    equipment_installed = Column(JSON, nullable=True)

    # Quality and completion
    completion_notes = Column(Text, nullable=True)
    customer_signature = Column(String(500), nullable=True)  # Digital signature data
    photos_taken = Column(JSON, nullable=True)

    # Issues and follow-up
    issues_encountered = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_notes = Column(Text, nullable=True)

    # Cost tracking
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    actual_cost = Column(Numeric(10, 2), nullable=True)
    billable_amount = Column(Numeric(10, 2), nullable=True)

    # Requirements and constraints
    special_instructions = Column(Text, nullable=True)
    safety_requirements = Column(JSON, nullable=True)
    permits_required = Column(JSON, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    technician = relationship("Technician", back_populates="work_orders")
    appointments = relationship(
        "Appointment", back_populates="work_order", cascade="all, delete-orphan"
    )
    time_logs = relationship(
        "TimeLog", back_populates="work_order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_work_orders_customer_status", "customer_id", "work_order_status"),
        Index("ix_work_orders_scheduled_date", "scheduled_date"),
        Index(
            "ix_work_orders_technician_status",
            "assigned_technician_id",
            "work_order_status",
        ),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if work order is overdue."""
        if not self.scheduled_date or self.work_order_status in [
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CANCELLED,
        ]:
            return False
        return date.today() > self.scheduled_date

    @hybrid_property
    def actual_duration_minutes(self) -> Optional[int]:
        """Calculate actual duration in minutes."""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<WorkOrder(number='{self.work_order_number}', type='{self.work_order_type}', status='{self.work_order_status}')>"


class Technician(TenantModel, StatusMixin, AuditMixin, ContactMixin):
    """Field technicians and service personnel."""

    __tablename__ = "field_technicians"

    # Personal information
    employee_id = Column(String(50), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    # Employment details
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date, nullable=True)
    employee_status = Column(
        SQLEnum(TechnicianStatus),
        default=TechnicianStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Skills and qualifications
    skill_level = Column(
        SQLEnum(TechnicianSkillLevel),
        default=TechnicianSkillLevel.JUNIOR,
        nullable=False,
    )
    certifications = Column(JSON, nullable=True)
    specializations = Column(JSON, nullable=True)

    # Work capabilities
    service_areas = Column(JSON, nullable=True)  # Geographic areas
    work_types = Column(JSON, nullable=True)  # Types of work
    max_jobs_per_day = Column(Integer, default=8, nullable=False)

    # Vehicle and equipment
    vehicle_assigned = Column(String(100), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    tools_assigned = Column(JSON, nullable=True)

    # Performance metrics
    completion_rate = Column(Float, default=0.0, nullable=False)
    customer_rating = Column(Float, default=0.0, nullable=False)
    safety_score = Column(Float, default=0.0, nullable=False)

    # Availability
    standard_hours = Column(JSON, nullable=True)  # Weekly schedule
    overtime_eligible = Column(Boolean, default=True, nullable=False)
    on_call_available = Column(Boolean, default=False, nullable=False)

    # Emergency contact
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    work_orders = relationship("WorkOrder", back_populates="technician")
    appointments = relationship("Appointment", back_populates="technician")
    time_logs = relationship(
        "TimeLog", back_populates="technician", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_technicians_tenant_employee", "tenant_id", "employee_id", unique=True
        ),
        Index("ix_technicians_status_skill", "employee_status", "skill_level"),
    )

    @hybrid_property
    def full_name(self) -> str:
        """Get technician's full name."""
        return f"{self.first_name} {self.last_name}"

    @hybrid_property
    def is_available(self) -> bool:
        """Check if technician is available for assignments."""
        return self.employee_status == TechnicianStatus.ACTIVE

    def __repr__(self):
        """  Repr   operation."""
        return f"<Technician(id='{self.employee_id}', name='{self.full_name}', status='{self.employee_status}')>"


class Appointment(TenantModel, AuditMixin, ContactMixin, AddressMixin):
    """Customer appointments for field work."""

    __tablename__ = "field_appointments"

    # Appointment identification
    appointment_id = Column(String(100), nullable=False, unique=True, index=True)

    # References
    work_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_work_orders.id"),
        nullable=False,
        index=True,
    )
    technician_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_technicians.id"),
        nullable=True,
        index=True,
    )
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Scheduling
    appointment_date = Column(Date, nullable=False, index=True)
    time_slot_start = Column(Time, nullable=False)
    time_slot_end = Column(Time, nullable=False)

    # Status
    appointment_status = Column(
        SQLEnum(AppointmentStatus),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    # Customer preferences
    preferred_time = Column(String(100), nullable=True)
    special_requests = Column(Text, nullable=True)
    access_instructions = Column(Text, nullable=True)

    # Confirmation
    confirmation_method = Column(String(50), nullable=True)  # phone, email, sms
    confirmed_date = Column(DateTime, nullable=True)
    confirmed_by = Column(String(200), nullable=True)

    # Completion tracking
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    work_completed = Column(Boolean, default=False, nullable=False)

    # Customer interaction
    customer_satisfaction = Column(Integer, nullable=True)  # 1-5 rating
    customer_feedback = Column(Text, nullable=True)

    # Rescheduling
    original_date = Column(Date, nullable=True)
    reschedule_reason = Column(String(200), nullable=True)
    reschedule_count = Column(Integer, default=0, nullable=False)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    work_order = relationship("WorkOrder", back_populates="appointments")
    technician = relationship("Technician", back_populates="appointments")

    __table_args__ = (
        Index("ix_appointments_date_technician", "appointment_date", "technician_id"),
        Index("ix_appointments_customer_date", "customer_id", "appointment_date"),
    )

    @hybrid_property
    def duration_minutes(self) -> int:
        """Calculate appointment duration in minutes."""
        start_dt = datetime.combine(date.today(), self.time_slot_start)
        end_dt = datetime.combine(date.today(), self.time_slot_end)
        return int((end_dt - start_dt).total_seconds() / 60)

    def __repr__(self):
        """  Repr   operation."""
        return f"<Appointment(id='{self.appointment_id}', date='{self.appointment_date}', status='{self.appointment_status}')>"


class TimeLog(TenantModel, AuditMixin):
    """Time tracking for technicians and work orders."""

    __tablename__ = "field_time_logs"

    # References
    technician_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_technicians.id"),
        nullable=False,
        index=True,
    )
    work_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_work_orders.id"),
        nullable=True,
        index=True,
    )

    # Time tracking
    log_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)

    # Activity details
    activity_type = Column(
        String(100), nullable=False
    )  # work, travel, break, training, etc.
    description = Column(Text, nullable=True)

    # Location tracking
    start_location = Column(JSON, nullable=True)  # GPS coordinates
    end_location = Column(JSON, nullable=True)  # GPS coordinates

    # Billing and cost
    billable_hours = Column(Float, nullable=True)
    non_billable_hours = Column(Float, nullable=True)
    hourly_rate = Column(Numeric(8, 2), nullable=True)

    # Break time
    is_break = Column(Boolean, default=False, nullable=False)
    break_type = Column(String(50), nullable=True)  # lunch, rest, personal

    # Approval
    approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(DateTime, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    technician = relationship("Technician", back_populates="time_logs")
    work_order = relationship("WorkOrder", back_populates="time_logs")

    __table_args__ = (
        Index("ix_time_logs_technician_date", "technician_id", "log_date"),
        Index("ix_time_logs_work_order", "work_order_id"),
    )

    @hybrid_property
    def duration_hours(self) -> Optional[float]:
        """Calculate duration in hours."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 3600, 2)
        return None

    def __repr__(self):
        """  Repr   operation."""
        return f"<TimeLog(technician_id='{self.technician_id}', date='{self.log_date}', activity='{self.activity_type}')>"


class FieldEquipment(TenantModel, StatusMixin, AuditMixin):
    """Equipment and tools for field operations."""

    __tablename__ = "field_equipment"

    # Equipment identification
    equipment_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Equipment details
    category = Column(String(100), nullable=False, index=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)

    # Condition and status
    condition = Column(
        SQLEnum(EquipmentCondition), default=EquipmentCondition.GOOD, nullable=False
    )
    operational_status = Column(
        String(50), default="available", nullable=False, index=True
    )

    # Assignment
    assigned_to_technician = Column(
        UUID(as_uuid=True),
        ForeignKey("field_technicians.id"),
        nullable=True,
        index=True,
    )
    assigned_to_vehicle = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)

    # Purchase and warranty
    purchase_date = Column(Date, nullable=True)
    purchase_cost = Column(Numeric(10, 2), nullable=True)
    warranty_expiry = Column(Date, nullable=True)

    # Maintenance
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)
    maintenance_notes = Column(Text, nullable=True)

    # Calibration (for testing equipment)
    last_calibration_date = Column(Date, nullable=True)
    next_calibration_date = Column(Date, nullable=True)
    calibration_certificate = Column(String(500), nullable=True)

    # Specifications
    specifications = Column(JSON, nullable=True)
    operating_requirements = Column(JSON, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_equipment_category_status", "category", "operational_status"),
        Index("ix_equipment_assigned_technician", "assigned_to_technician"),
    )

    @hybrid_property
    def is_due_for_maintenance(self) -> bool:
        """Check if equipment is due for maintenance."""
        return self.next_maintenance_date and date.today() >= self.next_maintenance_date

    @hybrid_property
    def is_due_for_calibration(self) -> bool:
        """Check if equipment is due for calibration."""
        return self.next_calibration_date and date.today() >= self.next_calibration_date

    def __repr__(self):
        """  Repr   operation."""
        return f"<FieldEquipment(id='{self.equipment_id}', name='{self.name}', condition='{self.condition}')>"


class ServiceRoute(TenantModel, AuditMixin):
    """Optimized routes for field technicians."""

    __tablename__ = "field_service_routes"

    # Route identification
    route_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Route details
    route_date = Column(Date, nullable=False, index=True)
    technician_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_technicians.id"),
        nullable=False,
        index=True,
    )

    # Route optimization
    start_location = Column(JSON, nullable=False)  # GPS coordinates
    end_location = Column(JSON, nullable=True)  # GPS coordinates
    waypoints = Column(JSON, nullable=False)  # Ordered list of stops

    # Timing
    estimated_start_time = Column(DateTime, nullable=False)
    estimated_end_time = Column(DateTime, nullable=False)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)

    # Distance and duration
    estimated_distance_km = Column(Float, nullable=True)
    actual_distance_km = Column(Float, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Status
    route_status = Column(String(50), default="planned", nullable=False, index=True)

    # Work orders on route
    work_order_ids = Column(JSON, nullable=False)
    completed_orders = Column(JSON, nullable=True)

    # Additional information
    traffic_conditions = Column(JSON, nullable=True)
    route_notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_routes_technician_date", "technician_id", "route_date"),
        Index("ix_routes_status", "route_status"),
    )

    @hybrid_property
    def completion_percentage(self) -> float:
        """Calculate route completion percentage."""
        if not self.work_order_ids:
            return 0.0
        total_orders = len(self.work_order_ids)
        completed_orders = len(self.completed_orders) if self.completed_orders else 0
        return round((completed_orders / total_orders) * 100, 2)

    def __repr__(self):
        """  Repr   operation."""
        return f"<ServiceRoute(id='{self.route_id}', technician_id='{self.technician_id}', date='{self.route_date}')>"


# Register cross-module relationships that will be configured after all models are loaded
@register_cross_module_relationship(WorkOrder, 'project')
def create_work_order_project_relationship():
    """Create Work Order Project Relationship operation."""
    return relationship(
        "InstallationProject",
        foreign_keys=[WorkOrder.project_id],
        back_populates="work_orders",
        lazy="select"
    )
