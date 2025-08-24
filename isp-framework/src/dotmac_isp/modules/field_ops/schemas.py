"""Field Operations Pydantic schemas for API request/response validation."""

from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from .models import (
    WorkOrderType,
    WorkOrderStatus,
    WorkOrderPriority,
    TechnicianStatus,
    AppointmentStatus,
    EquipmentCondition,
)


# Work Order Schemas
class WorkOrderBase(BaseModel):
    """Class for WorkOrderBase operations."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    work_order_type: WorkOrderType
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL
    customer_id: Optional[str] = None
    service_id: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    """Class for WorkOrderCreate operations."""
    pass


class WorkOrderUpdate(BaseModel):
    """Class for WorkOrderUpdate operations."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    work_order_type: Optional[WorkOrderType] = None
    priority: Optional[WorkOrderPriority] = None
    work_order_status: Optional[WorkOrderStatus] = None
    completion_notes: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)


class WorkOrder(WorkOrderBase):
    """Class for WorkOrder operations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    work_order_number: str
    work_order_status: WorkOrderStatus
    assigned_technician_id: Optional[str] = None
    scheduled_date: Optional[date] = None
    scheduled_time_start: Optional[time] = None
    scheduled_time_end: Optional[time] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    progress_percentage: int = 0
    completion_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Technician Schemas
class TechnicianBase(BaseModel):
    """Class for TechnicianBase operations."""
    employee_id: str = Field(..., min_length=1, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    hire_date: date
    skill_level: Optional[str] = Field(None, max_length=50)
    certifications: Optional[List[str]] = None


class TechnicianCreate(TechnicianBase):
    """Class for TechnicianCreate operations."""
    pass


class TechnicianUpdate(BaseModel):
    """Class for TechnicianUpdate operations."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    employee_status: Optional[TechnicianStatus] = None
    skill_level: Optional[str] = Field(None, max_length=50)
    certifications: Optional[List[str]] = None


class Technician(TechnicianBase):
    """Class for Technician operations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    employee_status: TechnicianStatus = TechnicianStatus.ACTIVE
    location: Optional[str] = None
    current_workload: int = 0
    max_concurrent_orders: int = 5
    created_at: datetime
    updated_at: Optional[datetime] = None


# Appointment Schemas
class AppointmentBase(BaseModel):
    """Class for AppointmentBase operations."""
    work_order_id: str
    technician_id: str
    customer_id: Optional[str] = None
    appointment_date: date
    time_slot_start: time
    time_slot_end: time
    estimated_duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Class for AppointmentCreate operations."""
    pass


class AppointmentUpdate(BaseModel):
    """Class for AppointmentUpdate operations."""
    appointment_date: Optional[date] = None
    time_slot_start: Optional[time] = None
    time_slot_end: Optional[time] = None
    appointment_status: Optional[AppointmentStatus] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    actual_duration_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None


class Appointment(AppointmentBase):
    """Class for Appointment operations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    appointment_id: str
    appointment_status: AppointmentStatus = AppointmentStatus.SCHEDULED
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Time Log Schemas
class TimeLogBase(BaseModel):
    """Class for TimeLogBase operations."""
    technician_id: str
    work_order_id: Optional[str] = None
    log_date: date
    start_time: datetime
    activity_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TimeLogCreate(TimeLogBase):
    """Class for TimeLogCreate operations."""
    pass


class TimeLogUpdate(BaseModel):
    """Class for TimeLogUpdate operations."""
    end_time: Optional[datetime] = None
    break_duration_minutes: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None


class TimeLog(TimeLogBase):
    """Class for TimeLog operations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    end_time: Optional[datetime] = None
    total_hours: Optional[float] = None
    break_duration_minutes: int = 0
    billable: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


# Field Equipment Schemas
class FieldEquipmentBase(BaseModel):
    """Class for FieldEquipmentBase operations."""
    equipment_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    condition: EquipmentCondition = EquipmentCondition.GOOD
    assigned_to_technician: Optional[str] = None


class FieldEquipmentCreate(FieldEquipmentBase):
    """Class for FieldEquipmentCreate operations."""
    pass


class FieldEquipmentUpdate(BaseModel):
    """Class for FieldEquipmentUpdate operations."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    condition: Optional[EquipmentCondition] = None
    assigned_to_technician: Optional[str] = None
    location: Optional[str] = None


class FieldEquipment(FieldEquipmentBase):
    """Class for FieldEquipment operations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    last_maintenance: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Service Route Schemas
class ServiceRouteBase(BaseModel):
    """Class for ServiceRouteBase operations."""
    route_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    technician_id: str
    service_area: Optional[str] = Field(None, max_length=255)
    estimated_travel_time_minutes: Optional[int] = Field(None, ge=0)


class ServiceRouteCreate(ServiceRouteBase):
    """Class for ServiceRouteCreate operations."""
    pass


class ServiceRouteUpdate(BaseModel):
    """Class for ServiceRouteUpdate operations."""
    route_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    technician_id: Optional[str] = None
    service_area: Optional[str] = Field(None, max_length=255)
    estimated_travel_time_minutes: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ServiceRoute(ServiceRouteBase):
    """Class for ServiceRoute operations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


# Dashboard Response Schemas
class WorkOrderDashboard(BaseModel):
    """Class for WorkOrderDashboard operations."""
    summary: Dict[str, Any]
    status_breakdown: List[Dict[str, Any]]
    recent_work_orders: List[Dict[str, Any]]


class TechnicianPerformanceReport(BaseModel):
    """Class for TechnicianPerformanceReport operations."""
    report_period: Dict[str, date]
    technician_id: Optional[str]
    metrics: Dict[str, Any]
    work_orders: List[Dict[str, Any]]
