"""
Universal Project Management Models

Platform-agnostic models for project lifecycle management, suitable for:
- ISP customer installations
- Infrastructure deployments
- Software projects
- Service implementations
- General project tracking
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ProjectType(str, Enum):
    """Universal project types."""

    # ISP/Telecom specific
    NEW_INSTALLATION = "new_installation"
    SERVICE_UPGRADE = "service_upgrade"
    NETWORK_EXPANSION = "network_expansion"
    EQUIPMENT_REPLACEMENT = "equipment_replacement"

    # Infrastructure
    DEPLOYMENT = "deployment"
    MIGRATION = "migration"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"

    # Software/IT
    SOFTWARE_DEVELOPMENT = "software_development"
    SYSTEM_INTEGRATION = "system_integration"
    DATA_MIGRATION = "data_migration"

    # General
    CONSULTING = "consulting"
    TRAINING = "training"
    AUDIT = "audit"
    CUSTOM = "custom"


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    PLANNING = "planning"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    TESTING = "testing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PhaseStatus(str, Enum):
    """Individual phase status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class MilestoneType(str, Enum):
    """Standard milestone types."""

    # Planning milestones
    PLANNING_COMPLETE = "planning_complete"
    APPROVAL_RECEIVED = "approval_received"
    RESOURCES_ALLOCATED = "resources_allocated"

    # Execution milestones
    PROJECT_STARTED = "project_started"
    PHASE_COMPLETE = "phase_complete"
    TESTING_COMPLETE = "testing_complete"

    # Delivery milestones
    DELIVERY_READY = "delivery_ready"
    CLIENT_ACCEPTANCE = "client_acceptance"
    PROJECT_COMPLETE = "project_complete"

    # Custom milestones
    CUSTOM_CHECKPOINT = "custom_checkpoint"


class ProjectPriority(str, Enum):
    """Project priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class ResourceType(str, Enum):
    """Resource types for project tracking."""

    HUMAN = "human"
    EQUIPMENT = "equipment"
    SOFTWARE = "software"
    BUDGET = "budget"
    FACILITY = "facility"
    VENDOR = "vendor"


# SQLAlchemy Models
class Project(Base):
    """Universal project model for any type of project management."""

    __tablename__ = "projects"

    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    project_number = Column(String(100), nullable=False, unique=True, index=True)
    project_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    project_type = Column(SQLEnum(ProjectType), nullable=False, index=True)
    project_status = Column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True,
    )
    priority = Column(
        SQLEnum(ProjectPriority),
        default=ProjectPriority.NORMAL,
        nullable=False,
        index=True,
    )

    # Stakeholders (flexible for different platforms)
    customer_id = Column(String(255), nullable=True, index=True)
    client_name = Column(String(200), nullable=True)
    client_email = Column(String(255), nullable=True)
    client_phone = Column(String(20), nullable=True)

    # Project management
    project_manager = Column(String(200), nullable=True)
    lead_technician = Column(String(200), nullable=True)
    assigned_team = Column(String(200), nullable=True)

    # Timeline
    requested_date = Column(Date, nullable=True)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # Progress tracking
    completion_percentage = Column(Integer, default=0, nullable=False)
    phases_completed = Column(Integer, default=0, nullable=False)
    total_phases = Column(Integer, default=0, nullable=False)

    # Cost management
    estimated_cost = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), nullable=True)
    budget_variance = Column(Numeric(12, 2), nullable=True)
    approved_budget = Column(Numeric(12, 2), nullable=True)

    # Requirements and deliverables
    requirements = Column(JSON, nullable=True)
    deliverables = Column(JSON, nullable=True)
    success_criteria = Column(JSON, nullable=True)

    # Location and logistics (flexible)
    project_location = Column(JSON, nullable=True)
    site_access_info = Column(Text, nullable=True)
    special_requirements = Column(Text, nullable=True)

    # Quality and completion
    quality_score = Column(Integer, nullable=True)
    client_satisfaction_score = Column(Integer, nullable=True)
    completion_notes = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    # Documentation and assets
    documents = Column(JSON, nullable=True)
    photos = Column(JSON, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(200), nullable=True)
    updated_by = Column(String(200), nullable=True)

    # Platform-specific metadata
    platform_data = Column(JSON, nullable=True)

    # Relationships
    phases = relationship("ProjectPhase", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    updates = relationship("ProjectUpdate", back_populates="project", cascade="all, delete-orphan")
    resources = relationship("ProjectResource", back_populates="project", cascade="all, delete-orphan")

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if project is overdue."""
        if self.planned_end_date and self.project_status not in [
            ProjectStatus.COMPLETED,
            ProjectStatus.CANCELLED,
        ]:
            return date.today() > self.planned_end_date
        return False

    @hybrid_property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining until deadline."""
        if self.planned_end_date:
            delta = self.planned_end_date - date.today()
            return delta.days
        return None

    def calculate_completion_percentage(self):
        """Calculate completion based on completed phases."""
        if self.total_phases > 0:
            self.completion_percentage = int((self.phases_completed / self.total_phases) * 100)
        else:
            self.completion_percentage = 0


class ProjectPhase(Base):
    """Project phases for detailed progress tracking."""

    __tablename__ = "project_phases"

    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Phase definition
    phase_name = Column(String(200), nullable=False)
    phase_description = Column(Text, nullable=True)
    phase_order = Column(Integer, nullable=False)
    phase_type = Column(String(100), nullable=True)

    # Phase properties
    is_critical_path = Column(Boolean, default=False, nullable=False)
    is_client_visible = Column(Boolean, default=True, nullable=False)
    is_milestone = Column(Boolean, default=False, nullable=False)

    # Status and progress
    phase_status = Column(SQLEnum(PhaseStatus), default=PhaseStatus.PENDING, nullable=False, index=True)
    completion_percentage = Column(Integer, default=0, nullable=False)

    # Timeline
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    estimated_duration_hours = Column(Float, nullable=True)
    actual_duration_hours = Column(Float, nullable=True)

    # Dependencies
    depends_on_phases = Column(JSON, nullable=True)
    blocks_phases = Column(JSON, nullable=True)

    # Assignment
    assigned_to = Column(String(200), nullable=True)
    assigned_team = Column(String(100), nullable=True)
    required_skills = Column(JSON, nullable=True)

    # Work details
    work_instructions = Column(Text, nullable=True)
    deliverables = Column(JSON, nullable=True)
    quality_criteria = Column(JSON, nullable=True)

    # Cost tracking
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    actual_cost = Column(Numeric(10, 2), nullable=True)

    # Completion
    completion_notes = Column(Text, nullable=True)
    issues_encountered = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    project = relationship("Project", back_populates="phases")

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if phase is overdue."""
        if self.planned_end_date and self.phase_status not in [
            PhaseStatus.COMPLETED,
            PhaseStatus.SKIPPED,
        ]:
            return date.today() > self.planned_end_date
        return False


class ProjectMilestone(Base):
    """Project milestones for key checkpoint tracking."""

    __tablename__ = "project_milestones"

    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Milestone definition
    milestone_name = Column(String(200), nullable=False)
    milestone_description = Column(Text, nullable=True)
    milestone_type = Column(SQLEnum(MilestoneType), nullable=False, index=True)

    # Timeline
    planned_date = Column(Date, nullable=False)
    actual_date = Column(Date, nullable=True)

    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    is_critical = Column(Boolean, default=False, nullable=False)
    is_client_visible = Column(Boolean, default=True, nullable=False)

    # Details
    success_criteria = Column(JSON, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    project = relationship("Project", back_populates="milestones")

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if milestone is overdue."""
        if not self.is_completed and self.planned_date:
            return date.today() > self.planned_date
        return False


class ProjectUpdate(Base):
    """Project updates and communication log."""

    __tablename__ = "project_updates"

    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Update content
    update_title = Column(String(300), nullable=False)
    update_content = Column(Text, nullable=False)
    update_type = Column(String(100), nullable=False)

    # Classification
    priority = Column(SQLEnum(ProjectPriority), default=ProjectPriority.NORMAL, nullable=False)
    is_client_visible = Column(Boolean, default=True, nullable=False)

    # Author
    author_name = Column(String(200), nullable=False)
    author_role = Column(String(100), nullable=True)

    # Progress information
    progress_percentage = Column(Integer, nullable=True)
    phase_completed = Column(String(200), nullable=True)
    next_steps = Column(Text, nullable=True)
    estimated_completion = Column(Date, nullable=True)

    # Attachments
    photos = Column(JSON, nullable=True)
    documents = Column(JSON, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    project = relationship("Project", back_populates="updates")


class ProjectResource(Base):
    """Project resource allocation and tracking."""

    __tablename__ = "project_resources"

    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Resource details
    resource_name = Column(String(200), nullable=False)
    resource_type = Column(SQLEnum(ResourceType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Allocation
    quantity_required = Column(Float, nullable=True)
    quantity_allocated = Column(Float, nullable=True)
    unit_cost = Column(Numeric(10, 2), nullable=True)
    total_cost = Column(Numeric(12, 2), nullable=True)

    # Schedule
    required_from = Column(Date, nullable=True)
    required_until = Column(Date, nullable=True)

    # Status
    is_allocated = Column(Boolean, default=False, nullable=False)
    allocation_notes = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    project = relationship("Project", back_populates="resources")


class ProjectDocument(Base):
    """Project document management."""

    __tablename__ = "project_documents"

    # Core identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Document details
    document_name = Column(String(300), nullable=False)
    document_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Classification
    is_client_visible = Column(Boolean, default=True, nullable=False)
    version = Column(String(50), nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by = Column(String(200), nullable=True)


# Database indexes for performance
Index("idx_projects_tenant_status", Project.tenant_id, Project.project_status)
Index("idx_projects_customer_type", Project.customer_id, Project.project_type)
Index("idx_phases_project_order", ProjectPhase.project_id, ProjectPhase.phase_order)
Index(
    "idx_milestones_project_date",
    ProjectMilestone.project_id,
    ProjectMilestone.planned_date,
)
Index("idx_updates_project_created", ProjectUpdate.project_id, ProjectUpdate.created_at)


# Pydantic Schemas for API
class ProjectCreate(BaseModel):
    """Schema for creating projects."""

    project_name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    project_type: ProjectType
    priority: ProjectPriority = ProjectPriority.NORMAL

    # Stakeholders
    customer_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    client_phone: Optional[str] = None

    # Timeline
    requested_date: Optional[date] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None

    # Management
    project_manager: Optional[str] = None
    assigned_team: Optional[str] = None

    # Budget
    estimated_cost: Optional[Decimal] = Field(None, ge=0)
    approved_budget: Optional[Decimal] = Field(None, ge=0)

    # Requirements
    requirements: Optional[dict[str, Any]] = None
    deliverables: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = None

    # Location
    project_location: Optional[dict[str, Any]] = None
    special_requirements: Optional[str] = None

    # Platform-specific data
    platform_data: Optional[dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    """Schema for updating projects."""

    project_name: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    project_status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None

    # Timeline updates
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None

    # Cost updates
    actual_cost: Optional[Decimal] = Field(None, ge=0)

    # Completion
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    completion_notes: Optional[str] = None
    quality_score: Optional[int] = Field(None, ge=1, le=10)
    client_satisfaction_score: Optional[int] = Field(None, ge=1, le=10)


class ProjectResponse(BaseModel):
    """Schema for project responses."""

    id: UUID
    tenant_id: str
    project_number: str
    project_name: str
    description: Optional[str]
    project_type: ProjectType
    project_status: ProjectStatus
    priority: ProjectPriority

    # Stakeholders
    customer_id: Optional[str]
    client_name: Optional[str]
    project_manager: Optional[str]

    # Timeline
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]

    # Progress
    completion_percentage: int
    phases_completed: int
    total_phases: int

    # Costs
    estimated_cost: Optional[Decimal]
    actual_cost: Optional[Decimal]

    # Status indicators
    is_overdue: bool
    days_remaining: Optional[int]

    # Audit
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Phase schemas
class PhaseCreate(BaseModel):
    """Schema for creating project phases."""

    phase_name: str = Field(..., min_length=1, max_length=200)
    phase_description: Optional[str] = None
    phase_order: int = Field(..., ge=1)
    phase_type: Optional[str] = None

    is_critical_path: bool = False
    is_client_visible: bool = True

    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    estimated_duration_hours: Optional[float] = Field(None, gt=0)

    assigned_to: Optional[str] = None
    work_instructions: Optional[str] = None
    estimated_cost: Optional[Decimal] = Field(None, ge=0)


class PhaseUpdate(BaseModel):
    """Schema for updating project phases."""

    phase_status: Optional[PhaseStatus] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    assigned_to: Optional[str] = None
    completion_notes: Optional[str] = None
    issues_encountered: Optional[str] = None
    actual_cost: Optional[Decimal] = Field(None, ge=0)


class PhaseResponse(BaseModel):
    """Schema for project phase responses."""

    id: UUID
    project_id: UUID
    phase_name: str
    phase_description: Optional[str]
    phase_order: int
    phase_status: PhaseStatus
    completion_percentage: int

    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]

    assigned_to: Optional[str]
    is_overdue: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Milestone schemas
class MilestoneCreate(BaseModel):
    """Schema for creating milestones."""

    milestone_name: str = Field(..., min_length=1, max_length=200)
    milestone_description: Optional[str] = None
    milestone_type: MilestoneType
    planned_date: date
    is_critical: bool = False
    is_client_visible: bool = True
    success_criteria: Optional[list[str]] = None


class MilestoneResponse(BaseModel):
    """Schema for milestone responses."""

    id: UUID
    project_id: UUID
    milestone_name: str
    milestone_type: MilestoneType
    planned_date: date
    actual_date: Optional[date]
    is_completed: bool
    is_critical: bool
    is_overdue: bool

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Update schemas
class UpdateCreate(BaseModel):
    """Schema for creating project updates."""

    update_title: str = Field(..., min_length=1, max_length=300)
    update_content: str = Field(..., min_length=1)
    update_type: str = Field(..., min_length=1, max_length=100)
    priority: ProjectPriority = ProjectPriority.NORMAL
    is_client_visible: bool = True

    author_name: str = Field(..., min_length=1, max_length=200)
    author_role: Optional[str] = None

    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    next_steps: Optional[str] = None
    estimated_completion: Optional[date] = None


class UpdateResponse(BaseModel):
    """Schema for update responses."""

    id: UUID
    project_id: UUID
    update_title: str
    update_content: str
    update_type: str
    priority: ProjectPriority

    author_name: str
    author_role: Optional[str]
    progress_percentage: Optional[int]

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
