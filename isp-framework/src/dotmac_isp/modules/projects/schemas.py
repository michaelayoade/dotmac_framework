"""Installation Project Management Schemas."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from .models import ProjectType, ProjectStatus, PhaseStatus, MilestoneType


class ProjectPhaseBase(BaseModel):
    """Base project phase schema."""

    phase_name: str = Field(..., min_length=1, max_length=200)
    phase_description: Optional[str] = None
    phase_order: int = Field(..., ge=1)
    phase_type: Optional[str] = None
    is_critical_path: bool = False
    is_customer_facing: bool = True
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    estimated_duration_hours: Optional[float] = Field(None, gt=0)
    assigned_technician: Optional[str] = None
    work_instructions: Optional[str] = None
    notify_customer_on_start: bool = True
    notify_customer_on_completion: bool = True


class ProjectPhaseCreate(ProjectPhaseBase):
    """Schema for creating project phases."""

    pass


class ProjectPhaseUpdate(BaseModel):
    """Schema for updating project phases."""

    phase_status: Optional[PhaseStatus] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    assigned_technician: Optional[str] = None
    completion_notes: Optional[str] = None
    issues_encountered: Optional[str] = None


class ProjectPhaseResponse(ProjectPhaseBase):
    """Schema for project phase responses."""

    id: UUID
    project_id: UUID
    phase_status: PhaseStatus
    completion_percentage: int
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    actual_duration_hours: Optional[float]
    completion_notes: Optional[str]
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


class ProjectMilestoneResponse(BaseModel):
    """Schema for project milestone responses."""

    id: UUID
    project_id: UUID
    milestone_name: str
    milestone_description: Optional[str]
    milestone_type: MilestoneType
    planned_date: date
    actual_date: Optional[date]
    is_completed: bool
    is_critical: bool
    is_customer_visible: bool
    is_overdue: bool
    completion_notes: Optional[str]
    created_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


class ProjectUpdateCreate(BaseModel):
    """Schema for creating project updates."""

    update_title: str = Field(..., min_length=1, max_length=300)
    update_content: str = Field(..., min_length=1)
    update_type: str = Field(..., min_length=1, max_length=100)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    is_customer_visible: bool = True
    author_name: str = Field(..., min_length=1, max_length=200)
    author_role: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    phase_completed: Optional[str] = None
    next_steps: Optional[str] = None
    estimated_completion: Optional[date] = None
    photos: Optional[List[str]] = None
    documents: Optional[List[str]] = None


class ProjectUpdateResponse(ProjectUpdateCreate):
    """Schema for project update responses."""

    id: UUID
    project_id: UUID
    customer_notified: bool
    notification_sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


class InstallationProjectBase(BaseModel):
    """Base installation project schema."""

    project_name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    project_type: ProjectType
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    requested_date: Optional[date] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    project_manager: Optional[str] = None
    lead_technician: Optional[str] = None
    estimated_cost: Optional[Decimal] = Field(None, gt=0)
    service_requirements: Optional[Dict[str, Any]] = None
    technical_specifications: Optional[Dict[str, Any]] = None
    equipment_list: Optional[List[Dict[str, Any]]] = None
    special_requirements: Optional[str] = None
    customer_contact_name: Optional[str] = None
    customer_contact_phone: Optional[str] = None
    customer_contact_email: Optional[str] = None
    preferred_contact_method: str = Field(
        default="phone", pattern="^(phone|email|sms)$"
    )
    site_access_instructions: Optional[str] = None
    permits_required: Optional[List[str]] = None


class InstallationProjectCreate(InstallationProjectBase):
    """Schema for creating installation projects."""

    customer_id: UUID
    opportunity_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    sales_owner: Optional[str] = None

    # Address fields
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: str = Field(default="US", max_length=2)
    installation_address_same_as_service: bool = True


class InstallationProjectUpdate(BaseModel):
    """Schema for updating installation projects."""

    project_name: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    project_status: Optional[ProjectStatus] = None
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    project_manager: Optional[str] = None
    lead_technician: Optional[str] = None
    estimated_cost: Optional[Decimal] = Field(None, gt=0)
    actual_cost: Optional[Decimal] = Field(None, gt=0)
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    quality_check_passed: Optional[bool] = None
    customer_satisfaction_score: Optional[int] = Field(None, ge=1, le=10)
    customer_feedback: Optional[str] = None
    completion_notes: Optional[str] = None
    issues_encountered: Optional[str] = None


class InstallationProjectResponse(InstallationProjectBase):
    """Schema for installation project responses."""

    id: UUID
    tenant_id: UUID
    project_number: str
    customer_id: UUID
    opportunity_id: Optional[UUID]
    service_id: Optional[UUID]
    project_status: ProjectStatus
    sales_owner: Optional[str]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    completion_percentage: int
    phases_completed: int
    total_phases: int
    actual_cost: Optional[Decimal]
    budget_variance: Optional[Decimal]
    quality_check_passed: Optional[bool]
    customer_satisfaction_score: Optional[int]
    is_overdue: bool
    days_remaining: Optional[int]

    # Address fields
    street_address: Optional[str]
    city: Optional[str]
    state_province: Optional[str]
    postal_code: Optional[str]
    country_code: str

    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


class CustomerProjectSummary(BaseModel):
    """Summary schema for customer portal project display."""

    id: UUID
    project_number: str
    project_name: str
    project_type: ProjectType
    project_status: ProjectStatus
    priority: str
    completion_percentage: int
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    estimated_completion: Optional[date]
    lead_technician: Optional[str]
    is_overdue: bool
    days_remaining: Optional[int]
    next_milestone: Optional[str]
    last_update: Optional[str]
    can_reschedule: bool = False

    class Config:
        """Class for Config operations."""
        from_attributes = True


class ProjectTimelineResponse(BaseModel):
    """Schema for project timeline with phases and milestones."""

    project: InstallationProjectResponse
    phases: List[ProjectPhaseResponse]
    milestones: List[ProjectMilestoneResponse]
    recent_updates: List[ProjectUpdateResponse]
    upcoming_appointments: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        """Class for Config operations."""
        from_attributes = True


class ProjectDashboardResponse(BaseModel):
    """Schema for project dashboard analytics."""

    total_projects: int
    active_projects: int
    completed_projects: int
    overdue_projects: int
    projects_by_status: Dict[str, int]
    projects_by_type: Dict[str, int]
    average_completion_time: Optional[float]
    customer_satisfaction_average: Optional[float]
    upcoming_milestones: List[ProjectMilestoneResponse]

    class Config:
        """Class for Config operations."""
        from_attributes = True


class ProjectNotificationRequest(BaseModel):
    """Schema for triggering project notifications."""

    project_id: UUID
    notification_type: str
    recipients: List[str] = Field(default_factory=list)  # customer, technician, manager
    message: Optional[str] = None
    include_project_details: bool = True
    include_timeline: bool = True
