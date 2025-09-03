"""
Field Operations Management Models

Complete backend models for field operations, technician management,
work orders, and dispatch operations using Pydantic v2 and SQLAlchemy 2.0.

Built on existing project management and location services.
"""

from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, validator
from sqlalchemy import (
    JSON, Boolean, Column, Date, DateTime, Enum as SQLEnum,
    Float, ForeignKey, Index, Integer, Numeric, String, Text, Time
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TechnicianStatus(str, Enum):
    """Technician availability status."""
    AVAILABLE = "available"
    ON_JOB = "on_job"
    BREAK = "break"
    LUNCH = "lunch"
    TRAVELING = "traveling"
    SICK = "sick"
    VACATION = "vacation"
    OFF_DUTY = "off_duty"
    EMERGENCY = "emergency"


class WorkOrderStatus(str, Enum):
    """Work order lifecycle status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled" 
    DISPATCHED = "dispatched"
    ACCEPTED = "accepted"
    EN_ROUTE = "en_route"
    ON_SITE = "on_site"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    WAITING_CUSTOMER = "waiting_customer"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REQUIRES_FOLLOWUP = "requires_followup"
    ESCALATED = "escalated"


class WorkOrderPriority(str, Enum):
    """Work order priority levels."""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class WorkOrderType(str, Enum):
    """Work order types."""
    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    UPGRADE = "upgrade"
    INSPECTION = "inspection"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    TROUBLESHOOTING = "troubleshooting"
    EMERGENCY_REPAIR = "emergency_repair"


class SkillLevel(str, Enum):
    """Technician skill levels."""
    TRAINEE = "trainee"
    JUNIOR = "junior"
    INTERMEDIATE = "intermediate"
    SENIOR = "senior"
    EXPERT = "expert"
    SPECIALIST = "specialist"


class EquipmentStatus(str, Enum):
    """Equipment status tracking."""
    REQUIRED = "required"
    ASSIGNED = "assigned"
    INSTALLED = "installed"
    TESTED = "tested" 
    RETURNED = "returned"
    MISSING = "missing"
    DAMAGED = "damaged"


class NotificationType(str, Enum):
    """Field operations notification types."""
    WORK_ORDER_ASSIGNED = "work_order_assigned"
    SCHEDULE_CHANGED = "schedule_changed"
    CUSTOMER_CONTACTED = "customer_contacted"
    PARTS_ARRIVED = "parts_arrived"
    ESCALATION_REQUIRED = "escalation_required"
    JOB_COMPLETED = "job_completed"
    EMERGENCY_ALERT = "emergency_alert"


# SQLAlchemy Models

class Technician(Base):
    """Technician profiles and management."""
    
    __tablename__ = "field_technicians"
    
    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    employee_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Link to auth system
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), nullable=False)
    mobile_phone = Column(String(20), nullable=True)
    
    # Employment details
    hire_date = Column(Date, nullable=False)
    employment_status = Column(String(50), default="active", nullable=False)
    job_title = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    supervisor_id = Column(PGUUID(as_uuid=True), ForeignKey("field_technicians.id"), nullable=True)
    
    # Skills and certifications
    skill_level = Column(SQLEnum(SkillLevel), default=SkillLevel.JUNIOR, nullable=False)
    skills = Column(ARRAY(String), nullable=True)  # ["fiber_splicing", "copper_installation"]
    certifications = Column(JSON, nullable=True)  # Certification details with expiry dates
    specializations = Column(ARRAY(String), nullable=True)  # ["commercial", "residential"]
    
    # Work capacity and scheduling
    max_jobs_per_day = Column(Integer, default=8, nullable=False)
    work_hours_start = Column(Time, nullable=True)
    work_hours_end = Column(Time, nullable=True)
    overtime_approved = Column(Boolean, default=False, nullable=False)
    weekend_availability = Column(Boolean, default=False, nullable=False)
    
    # Current status and location
    current_status = Column(SQLEnum(TechnicianStatus), default=TechnicianStatus.OFF_DUTY, nullable=False)
    current_location = Column(JSON, nullable=True)  # Latest GPS coordinates
    last_location_update = Column(DateTime, nullable=True)
    
    # Performance metrics
    jobs_completed_today = Column(Integer, default=0, nullable=False)
    jobs_completed_week = Column(Integer, default=0, nullable=False) 
    jobs_completed_month = Column(Integer, default=0, nullable=False)
    average_job_rating = Column(Float, nullable=True)
    completion_rate = Column(Float, default=0.0, nullable=False)  # Percentage
    
    # Equipment and vehicle
    assigned_vehicle = Column(String(100), nullable=True)
    vehicle_location = Column(JSON, nullable=True)
    equipment_assigned = Column(JSON, nullable=True)  # Current equipment inventory
    
    # Preferences and settings
    preferred_work_types = Column(ARRAY(String), nullable=True)
    notification_preferences = Column(JSON, nullable=True)
    language_preference = Column(String(10), default="en", nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, nullable=True)
    
    # Relationships
    work_orders = relationship("WorkOrder", back_populates="technician")
    time_entries = relationship("TechnicianTimeEntry", back_populates="technician")
    performance_reviews = relationship("TechnicianPerformance", back_populates="technician")
    
    @hybrid_property
    def full_name(self) -> str:
        """Get technician's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @hybrid_property
    def is_available(self) -> bool:
        """Check if technician is available for work."""
        return self.current_status in [TechnicianStatus.AVAILABLE, TechnicianStatus.TRAVELING]
    
    @hybrid_property
    def current_workload(self) -> int:
        """Calculate current daily workload percentage."""
        if self.max_jobs_per_day > 0:
            return int((self.jobs_completed_today / self.max_jobs_per_day) * 100)
        return 0


class WorkOrder(Base):
    """Enhanced work order model building on existing project management."""
    
    __tablename__ = "field_work_orders"
    
    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    work_order_number = Column(String(100), nullable=False, unique=True, index=True)
    
    # Link to existing project management
    project_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    project_phase_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    
    # Work order details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    work_order_type = Column(SQLEnum(WorkOrderType), nullable=False, index=True)
    priority = Column(SQLEnum(WorkOrderPriority), default=WorkOrderPriority.NORMAL, nullable=False, index=True)
    
    # Customer and location
    customer_id = Column(String(255), nullable=True, index=True)
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(255), nullable=True)
    
    # Service location details
    service_address = Column(Text, nullable=False)
    service_coordinates = Column(JSON, nullable=True)  # {lat, lng, accuracy}
    access_instructions = Column(Text, nullable=True)
    site_contact = Column(String(200), nullable=True)
    site_contact_phone = Column(String(20), nullable=True)
    
    # Scheduling
    requested_date = Column(Date, nullable=True)
    scheduled_date = Column(Date, nullable=True, index=True)
    scheduled_time_start = Column(Time, nullable=True)
    scheduled_time_end = Column(Time, nullable=True)
    estimated_duration = Column(Integer, nullable=True)  # minutes
    
    # Assignment
    technician_id = Column(PGUUID(as_uuid=True), ForeignKey("field_technicians.id"), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    assigned_by = Column(String(200), nullable=True)
    backup_technician_id = Column(PGUUID(as_uuid=True), ForeignKey("field_technicians.id"), nullable=True)
    
    # Status and progress
    status = Column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.DRAFT, nullable=False, index=True)
    progress_percentage = Column(Integer, default=0, nullable=False)
    
    # Work tracking
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    on_site_arrival_time = Column(DateTime, nullable=True)
    customer_signature_time = Column(DateTime, nullable=True)
    
    # Equipment and materials
    required_equipment = Column(JSON, nullable=True)  # List of required equipment with quantities
    required_materials = Column(JSON, nullable=True)  # Materials needed
    equipment_used = Column(JSON, nullable=True)  # Equipment actually used
    materials_used = Column(JSON, nullable=True)  # Materials consumed
    
    # Work details
    work_performed = Column(Text, nullable=True)
    checklist_items = Column(JSON, nullable=True)  # Dynamic checklist based on work type
    photos = Column(JSON, nullable=True)  # Photo metadata and URLs
    documents = Column(JSON, nullable=True)  # Document attachments
    customer_signature = Column(Text, nullable=True)  # Base64 signature data
    
    # Quality and completion
    quality_check_passed = Column(Boolean, nullable=True)
    customer_satisfaction_rating = Column(Integer, nullable=True)  # 1-5 scale
    completion_notes = Column(Text, nullable=True)
    followup_required = Column(Boolean, default=False, nullable=False)
    followup_reason = Column(String(500), nullable=True)
    
    # Cost tracking
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    actual_cost = Column(Numeric(10, 2), nullable=True)
    billable_hours = Column(Float, nullable=True)
    overtime_hours = Column(Float, nullable=True)
    
    # Notifications and communication
    customer_notified = Column(Boolean, default=False, nullable=False)
    last_customer_contact = Column(DateTime, nullable=True)
    automated_updates_sent = Column(JSON, nullable=True)  # Track automated notifications
    
    # SLA and performance
    sla_target_completion = Column(DateTime, nullable=True)
    sla_met = Column(Boolean, nullable=True)
    response_time_minutes = Column(Integer, nullable=True)
    resolution_time_minutes = Column(Integer, nullable=True)
    
    # Sync and mobile
    last_sync = Column(DateTime, nullable=True)
    offline_changes = Column(JSON, nullable=True)  # Track offline modifications
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(200), nullable=True)
    updated_by = Column(String(200), nullable=True)
    
    # Relationships
    technician = relationship("Technician", back_populates="work_orders", foreign_keys=[technician_id])
    backup_technician = relationship("Technician", foreign_keys=[backup_technician_id])
    status_history = relationship("WorkOrderStatusHistory", back_populates="work_order", cascade="all, delete-orphan")
    equipment_tracking = relationship("WorkOrderEquipment", back_populates="work_order", cascade="all, delete-orphan")
    time_entries = relationship("WorkOrderTimeEntry", back_populates="work_order", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if work order is overdue."""
        if self.scheduled_date and self.status not in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]:
            return date.today() > self.scheduled_date
        return False
    
    @hybrid_property
    def total_duration(self) -> Optional[int]:
        """Calculate total work duration in minutes."""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return int(delta.total_seconds() / 60)
        return None


class WorkOrderStatusHistory(Base):
    """Track work order status changes."""
    
    __tablename__ = "work_order_status_history"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    work_order_id = Column(PGUUID(as_uuid=True), ForeignKey("field_work_orders.id"), nullable=False, index=True)
    
    # Status change details
    from_status = Column(SQLEnum(WorkOrderStatus), nullable=True)
    to_status = Column(SQLEnum(WorkOrderStatus), nullable=False)
    change_reason = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Change tracking
    changed_by = Column(String(200), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    location = Column(JSON, nullable=True)  # GPS location when status changed
    
    # Relationship
    work_order = relationship("WorkOrder", back_populates="status_history")


class WorkOrderEquipment(Base):
    """Track equipment associated with work orders."""
    
    __tablename__ = "work_order_equipment"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    work_order_id = Column(PGUUID(as_uuid=True), ForeignKey("field_work_orders.id"), nullable=False, index=True)
    
    # Equipment details
    equipment_type = Column(String(100), nullable=False)
    equipment_model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, index=True)
    barcode = Column(String(100), nullable=True, index=True)
    
    # Status tracking
    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.REQUIRED, nullable=False)
    quantity_required = Column(Integer, default=1, nullable=False)
    quantity_used = Column(Integer, default=0, nullable=False)
    
    # Installation details
    installation_location = Column(String(200), nullable=True)
    installation_notes = Column(Text, nullable=True)
    test_results = Column(JSON, nullable=True)
    
    # Tracking
    assigned_at = Column(DateTime, nullable=True)
    installed_at = Column(DateTime, nullable=True)
    tested_at = Column(DateTime, nullable=True)
    returned_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    work_order = relationship("WorkOrder", back_populates="equipment_tracking")


class TechnicianTimeEntry(Base):
    """Track technician time and activities."""
    
    __tablename__ = "technician_time_entries"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    technician_id = Column(PGUUID(as_uuid=True), ForeignKey("field_technicians.id"), nullable=False, index=True)
    work_order_id = Column(PGUUID(as_uuid=True), ForeignKey("field_work_orders.id"), nullable=True, index=True)
    
    # Time tracking
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Activity details
    activity_type = Column(String(100), nullable=False)  # "travel", "work", "break", "admin"
    description = Column(Text, nullable=True)
    location_start = Column(JSON, nullable=True)
    location_end = Column(JSON, nullable=True)
    
    # Business tracking
    billable = Column(Boolean, default=True, nullable=False)
    overtime = Column(Boolean, default=False, nullable=False)
    break_time = Column(Boolean, default=False, nullable=False)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    technician = relationship("Technician", back_populates="time_entries")
    work_order = relationship("WorkOrder")


class WorkOrderTimeEntry(Base):
    """Track time spent on specific work orders."""
    
    __tablename__ = "work_order_time_entries"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    work_order_id = Column(PGUUID(as_uuid=True), ForeignKey("field_work_orders.id"), nullable=False, index=True)
    technician_id = Column(PGUUID(as_uuid=True), ForeignKey("field_technicians.id"), nullable=False, index=True)
    
    # Time details
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Work details
    activity_type = Column(String(100), nullable=False)  # "setup", "installation", "testing", "cleanup"
    description = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="time_entries")


class TechnicianPerformance(Base):
    """Track technician performance metrics."""
    
    __tablename__ = "technician_performance"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    technician_id = Column(PGUUID(as_uuid=True), ForeignKey("field_technicians.id"), nullable=False, index=True)
    
    # Performance period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # "daily", "weekly", "monthly", "quarterly"
    
    # Job metrics
    jobs_assigned = Column(Integer, default=0, nullable=False)
    jobs_completed = Column(Integer, default=0, nullable=False)
    jobs_cancelled = Column(Integer, default=0, nullable=False)
    completion_rate = Column(Float, default=0.0, nullable=False)
    
    # Time metrics
    total_work_hours = Column(Float, default=0.0, nullable=False)
    billable_hours = Column(Float, default=0.0, nullable=False)
    overtime_hours = Column(Float, default=0.0, nullable=False)
    average_job_duration = Column(Float, nullable=True)
    
    # Quality metrics
    average_customer_rating = Column(Float, nullable=True)
    quality_checks_passed = Column(Integer, default=0, nullable=False)
    quality_checks_failed = Column(Integer, default=0, nullable=False)
    callbacks = Column(Integer, default=0, nullable=False)  # Return visits required
    
    # SLA metrics
    sla_met_count = Column(Integer, default=0, nullable=False)
    sla_missed_count = Column(Integer, default=0, nullable=False)
    average_response_time = Column(Integer, nullable=True)  # minutes
    average_resolution_time = Column(Integer, nullable=True)  # minutes
    
    # Revenue metrics
    revenue_generated = Column(Numeric(12, 2), nullable=True)
    cost_of_materials = Column(Numeric(12, 2), nullable=True)
    profit_margin = Column(Float, nullable=True)
    
    # Additional metrics
    miles_traveled = Column(Float, nullable=True)
    fuel_costs = Column(Numeric(8, 2), nullable=True)
    safety_incidents = Column(Integer, default=0, nullable=False)
    
    # Calculated scores (0-100 scale)
    productivity_score = Column(Integer, nullable=True)
    quality_score = Column(Integer, nullable=True)
    customer_service_score = Column(Integer, nullable=True)
    overall_performance_score = Column(Integer, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    technician = relationship("Technician", back_populates="performance_reviews")


class DispatchZone(Base):
    """Define dispatch zones for efficient technician assignment."""
    
    __tablename__ = "dispatch_zones"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Zone definition
    zone_name = Column(String(200), nullable=False)
    zone_code = Column(String(20), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Geographic boundaries
    boundary_coordinates = Column(JSON, nullable=False)  # Polygon coordinates
    center_coordinates = Column(JSON, nullable=False)  # Zone center point
    coverage_radius = Column(Float, nullable=True)  # km
    
    # Zone properties
    service_types = Column(ARRAY(String), nullable=True)  # Supported service types
    priority_level = Column(Integer, default=1, nullable=False)  # 1=highest priority
    max_concurrent_jobs = Column(Integer, default=10, nullable=False)
    
    # Technician assignment
    primary_technicians = Column(ARRAY(String), nullable=True)  # Technician IDs
    backup_technicians = Column(ARRAY(String), nullable=True)
    
    # Schedule settings
    operating_hours_start = Column(Time, nullable=True)
    operating_hours_end = Column(Time, nullable=True)
    weekend_coverage = Column(Boolean, default=False, nullable=False)
    
    # Performance tracking
    average_response_time = Column(Integer, nullable=True)  # minutes
    jobs_completed_month = Column(Integer, default=0, nullable=False)
    customer_satisfaction_avg = Column(Float, nullable=True)
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Database indexes for performance
Index("idx_technicians_status_location", Technician.current_status, Technician.tenant_id)
Index("idx_technicians_skills", Technician.tenant_id, Technician.skill_level)
Index("idx_workorders_status_date", WorkOrder.status, WorkOrder.scheduled_date)
Index("idx_workorders_technician_status", WorkOrder.technician_id, WorkOrder.status)
Index("idx_workorders_customer_priority", WorkOrder.customer_id, WorkOrder.priority)
Index("idx_performance_technician_period", TechnicianPerformance.technician_id, TechnicianPerformance.period_start)
Index("idx_time_entries_technician_date", TechnicianTimeEntry.technician_id, TechnicianTimeEntry.start_time)


# Pydantic v2 Schemas

class TechnicianCreate(BaseModel):
    """Schema for creating technicians."""
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
    
    employee_id: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    phone: str = Field(..., min_length=10, max_length=20)
    mobile_phone: Optional[str] = Field(None, max_length=20)
    
    hire_date: date
    job_title: Optional[str] = Field(None, max_length=100)
    skill_level: SkillLevel = SkillLevel.JUNIOR
    skills: Optional[List[str]] = None
    specializations: Optional[List[str]] = None
    
    max_jobs_per_day: int = Field(8, ge=1, le=20)
    work_hours_start: Optional[time] = None
    work_hours_end: Optional[time] = None
    weekend_availability: bool = False


class TechnicianUpdate(BaseModel):
    """Schema for updating technicians."""
    model_config = ConfigDict(from_attributes=True)
    
    current_status: Optional[TechnicianStatus] = None
    current_location: Optional[Dict[str, Any]] = None
    skill_level: Optional[SkillLevel] = None
    skills: Optional[List[str]] = None
    max_jobs_per_day: Optional[int] = Field(None, ge=1, le=20)
    overtime_approved: Optional[bool] = None
    weekend_availability: Optional[bool] = None


class TechnicianResponse(BaseModel):
    """Schema for technician responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: str
    employee_id: str
    full_name: str
    email: str
    phone: str
    
    skill_level: SkillLevel
    skills: Optional[List[str]]
    current_status: TechnicianStatus
    is_available: bool
    current_workload: int
    
    jobs_completed_today: int
    average_job_rating: Optional[float]
    completion_rate: float
    
    created_at: datetime
    last_active: Optional[datetime]


class WorkOrderCreate(BaseModel):
    """Schema for creating work orders."""
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
    
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)
    work_order_type: WorkOrderType
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL
    
    # Customer details
    customer_id: Optional[str] = None
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    
    # Location
    service_address: str = Field(..., min_length=1)
    service_coordinates: Optional[Dict[str, float]] = None
    access_instructions: Optional[str] = None
    
    # Scheduling
    requested_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    scheduled_time_start: Optional[time] = None
    estimated_duration: Optional[int] = Field(None, ge=15, le=1440)  # 15min - 24hrs
    
    # Requirements
    required_equipment: Optional[List[Dict[str, Any]]] = None
    required_materials: Optional[List[Dict[str, Any]]] = None
    checklist_items: Optional[List[Dict[str, Any]]] = None


class WorkOrderUpdate(BaseModel):
    """Schema for updating work orders."""
    model_config = ConfigDict(from_attributes=True)
    
    status: Optional[WorkOrderStatus] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    technician_id: Optional[UUID] = None
    
    # Time tracking
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    on_site_arrival_time: Optional[datetime] = None
    
    # Work completion
    work_performed: Optional[str] = None
    quality_check_passed: Optional[bool] = None
    customer_satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    completion_notes: Optional[str] = None
    followup_required: Optional[bool] = None
    
    # Cost tracking
    actual_cost: Optional[Decimal] = Field(None, ge=0)
    billable_hours: Optional[float] = Field(None, ge=0)


class WorkOrderResponse(BaseModel):
    """Schema for work order responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: str
    work_order_number: str
    title: str
    work_order_type: WorkOrderType
    status: WorkOrderStatus
    priority: WorkOrderPriority
    
    customer_name: Optional[str]
    service_address: str
    scheduled_date: Optional[date]
    
    technician: Optional[TechnicianResponse]
    progress_percentage: int
    is_overdue: bool
    
    estimated_duration: Optional[int]
    total_duration: Optional[int]
    
    created_at: datetime
    updated_at: datetime


class WorkOrderDetailResponse(WorkOrderResponse):
    """Detailed work order response with all fields."""
    model_config = ConfigDict(from_attributes=True)
    
    description: str
    customer_phone: Optional[str]
    customer_email: Optional[str]
    access_instructions: Optional[str]
    
    scheduled_time_start: Optional[time]
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    
    required_equipment: Optional[List[Dict[str, Any]]]
    equipment_used: Optional[List[Dict[str, Any]]]
    work_performed: Optional[str]
    completion_notes: Optional[str]
    
    quality_check_passed: Optional[bool]
    customer_satisfaction_rating: Optional[int]
    
    estimated_cost: Optional[Decimal]
    actual_cost: Optional[Decimal]


class PerformanceMetrics(BaseModel):
    """Performance metrics response."""
    model_config = ConfigDict(from_attributes=True)
    
    technician_id: UUID
    period_start: date
    period_end: date
    
    jobs_completed: int
    completion_rate: float
    average_customer_rating: Optional[float]
    
    total_work_hours: float
    billable_hours: float
    average_job_duration: Optional[float]
    
    sla_met_count: int
    sla_missed_count: int
    average_response_time: Optional[int]
    
    overall_performance_score: Optional[int]