"""Installation Project Management Models."""

from datetime import datetime, date
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
    Integer,
    Float,
    Numeric,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin
from dotmac_isp.shared.models import ContactMixin, AddressMixin
from dotmac_isp.shared.database.relationship_registry import register_cross_module_relationship


class ProjectType(str, Enum):
    """Installation project types."""

    NEW_INSTALLATION = "new_installation"
    SERVICE_UPGRADE = "service_upgrade"
    RELOCATION = "relocation"
    EQUIPMENT_REPLACEMENT = "equipment_replacement"
    NETWORK_EXPANSION = "network_expansion"
    REPAIR = "repair"
    MAINTENANCE = "maintenance"


class ProjectStatus(str, Enum):
    """Project status."""

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
    """Project phase status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class MilestoneType(str, Enum):
    """Milestone types."""

    SITE_SURVEY = "site_survey"
    PERMITS_APPROVED = "permits_approved"
    EQUIPMENT_ORDERED = "equipment_ordered"
    EQUIPMENT_DELIVERED = "equipment_delivered"
    INSTALLATION_STARTED = "installation_started"
    EQUIPMENT_INSTALLED = "equipment_installed"
    TESTING_COMPLETED = "testing_completed"
    SERVICE_ACTIVATED = "service_activated"
    CUSTOMER_TRAINING = "customer_training"
    PROJECT_COMPLETED = "project_completed"


class InstallationProject(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Installation project model for tracking customer installations."""

    __tablename__ = "installation_projects"

    # Project identification
    project_number = Column(String(100), nullable=False, unique=True, index=True)
    project_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Project classification
    project_type = Column(SQLEnum(ProjectType), nullable=False, index=True)
    project_status = Column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True,
    )
    priority = Column(
        String(20), default="normal", nullable=False
    )  # low, normal, high, urgent

    # Customer and sales information
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    opportunity_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to sales opportunity
    service_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to service being installed

    # Project timeline
    requested_date = Column(Date, nullable=True)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # Project management
    project_manager = Column(String(200), nullable=True)
    sales_owner = Column(String(200), nullable=True)
    lead_technician = Column(String(200), nullable=True)

    # Progress tracking
    completion_percentage = Column(Integer, default=0, nullable=False)
    phases_completed = Column(Integer, default=0, nullable=False)
    total_phases = Column(Integer, default=0, nullable=False)

    # Cost tracking
    estimated_cost = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), nullable=True)
    budget_variance = Column(Numeric(12, 2), nullable=True)

    # Requirements and specifications
    service_requirements = Column(JSON, nullable=True)
    technical_specifications = Column(JSON, nullable=True)
    equipment_list = Column(JSON, nullable=True)
    special_requirements = Column(Text, nullable=True)

    # Customer communication
    customer_contact_name = Column(String(200), nullable=True)
    customer_contact_phone = Column(String(20), nullable=True)
    customer_contact_email = Column(String(255), nullable=True)
    preferred_contact_method = Column(String(50), default="phone", nullable=False)

    # Installation site details
    installation_address_same_as_service = Column(Boolean, default=True, nullable=False)
    site_access_instructions = Column(Text, nullable=True)
    site_conditions = Column(JSON, nullable=True)
    permits_required = Column(JSON, nullable=True)

    # Quality and completion
    quality_check_passed = Column(Boolean, nullable=True)
    customer_satisfaction_score = Column(Integer, nullable=True)  # 1-10 scale
    customer_feedback = Column(Text, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Documentation
    project_documents = Column(JSON, nullable=True)  # List of document URLs/paths
    installation_photos = Column(JSON, nullable=True)  # List of photo URLs/paths

    # Risk and issues
    risk_factors = Column(JSON, nullable=True)
    issues_encountered = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    # Relationships
    phases = relationship(
        "ProjectPhase", back_populates="project", cascade="all, delete-orphan"
    )
    milestones = relationship(
        "ProjectMilestone", back_populates="project", cascade="all, delete-orphan"
    )
    updates = relationship(
        "ProjectUpdate", back_populates="project", cascade="all, delete-orphan"
    )
    # Work orders relationship - connects to field_ops module - temporarily commented out
    # work_orders = relationship(
    #     "WorkOrder",
    #     foreign_keys="[WorkOrder.project_id]",
    #     back_populates="project",
    #     cascade="all, delete-orphan"
    # )

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
        """Calculate days remaining until planned end date."""
        if self.planned_end_date:
            delta = self.planned_end_date - date.today()
            return delta.days
        return None

    def calculate_completion_percentage(self):
        """Calculate completion percentage based on completed phases."""
        if self.total_phases > 0:
            self.completion_percentage = int(
                (self.phases_completed / self.total_phases) * 100
            )
        else:
            self.completion_percentage = 0


class ProjectPhase(TenantModel, StatusMixin, AuditMixin):
    """Project phases for tracking installation progress."""

    __tablename__ = "project_phases"

    # Phase identification
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("installation_projects.id"),
        nullable=False,
        index=True,
    )
    phase_name = Column(String(200), nullable=False)
    phase_description = Column(Text, nullable=True)
    phase_order = Column(Integer, nullable=False)

    # Phase classification
    phase_type = Column(
        String(100), nullable=True
    )  # survey, permits, installation, testing, etc.
    is_critical_path = Column(Boolean, default=False, nullable=False)
    is_customer_facing = Column(
        Boolean, default=True, nullable=False
    )  # Show to customer in portal

    # Status and progress
    phase_status = Column(
        SQLEnum(PhaseStatus), default=PhaseStatus.PENDING, nullable=False, index=True
    )
    completion_percentage = Column(Integer, default=0, nullable=False)

    # Timeline
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    estimated_duration_hours = Column(Float, nullable=True)
    actual_duration_hours = Column(Float, nullable=True)

    # Dependencies
    depends_on_phases = Column(
        JSON, nullable=True
    )  # List of phase IDs this phase depends on
    blocks_phases = Column(JSON, nullable=True)  # List of phase IDs this phase blocks

    # Assignment and resources
    assigned_technician = Column(String(200), nullable=True)
    assigned_team = Column(String(100), nullable=True)
    required_skills = Column(JSON, nullable=True)
    required_equipment = Column(JSON, nullable=True)

    # Work details
    work_instructions = Column(Text, nullable=True)
    deliverables = Column(JSON, nullable=True)
    quality_criteria = Column(JSON, nullable=True)

    # Cost tracking
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    actual_cost = Column(Numeric(10, 2), nullable=True)

    # Completion details
    completion_notes = Column(Text, nullable=True)
    issues_encountered = Column(Text, nullable=True)
    photos_taken = Column(JSON, nullable=True)
    documents_generated = Column(JSON, nullable=True)

    # Customer notification
    notify_customer_on_start = Column(Boolean, default=True, nullable=False)
    notify_customer_on_completion = Column(Boolean, default=True, nullable=False)
    customer_notification_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("InstallationProject", back_populates="phases")

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if phase is overdue."""
        if self.planned_end_date and self.phase_status not in [
            PhaseStatus.COMPLETED,
            PhaseStatus.SKIPPED,
        ]:
            return date.today() > self.planned_end_date
        return False


class ProjectMilestone(TenantModel, StatusMixin, AuditMixin):
    """Project milestones for key checkpoint tracking."""

    __tablename__ = "project_milestones"

    # Milestone identification
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("installation_projects.id"),
        nullable=False,
        index=True,
    )
    milestone_name = Column(String(200), nullable=False)
    milestone_description = Column(Text, nullable=True)
    milestone_type = Column(SQLEnum(MilestoneType), nullable=False, index=True)

    # Timeline
    planned_date = Column(Date, nullable=False)
    actual_date = Column(Date, nullable=True)

    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    is_critical = Column(Boolean, default=False, nullable=False)

    # Details
    success_criteria = Column(JSON, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Customer facing
    is_customer_visible = Column(Boolean, default=True, nullable=False)
    customer_notification_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("InstallationProject", back_populates="milestones")

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if milestone is overdue."""
        if not self.is_completed and self.planned_date:
            return date.today() > self.planned_date
        return False


class ProjectUpdate(TenantModel, AuditMixin):
    """Project updates and communication log."""

    __tablename__ = "project_updates"

    # Update identification
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("installation_projects.id"),
        nullable=False,
        index=True,
    )
    update_title = Column(String(300), nullable=False)
    update_content = Column(Text, nullable=False)

    # Update classification
    update_type = Column(
        String(100), nullable=False
    )  # progress, issue, milestone, completion, etc.
    priority = Column(String(20), default="normal", nullable=False)

    # Visibility and notification
    is_customer_visible = Column(Boolean, default=True, nullable=False)
    customer_notified = Column(Boolean, default=False, nullable=False)
    notification_sent_at = Column(DateTime, nullable=True)

    # Author and context
    author_name = Column(String(200), nullable=False)
    author_role = Column(
        String(100), nullable=True
    )  # technician, project_manager, sales

    # Attachments
    photos = Column(JSON, nullable=True)
    documents = Column(JSON, nullable=True)

    # Progress information
    progress_percentage = Column(Integer, nullable=True)
    phase_completed = Column(String(200), nullable=True)
    next_steps = Column(Text, nullable=True)
    estimated_completion = Column(Date, nullable=True)

    # Relationships
    project = relationship("InstallationProject", back_populates="updates")


# Add indexes for performance
Index(
    "idx_installation_projects_customer_status",
    InstallationProject.customer_id,
    InstallationProject.project_status,
)
Index(
    "idx_project_phases_project_order",
    ProjectPhase.project_id,
    ProjectPhase.phase_order,
)
Index(
    "idx_project_milestones_project_date",
    ProjectMilestone.project_id,
    ProjectMilestone.planned_date,
)
Index(
    "idx_project_updates_project_date",
    ProjectUpdate.project_id,
    ProjectUpdate.created_at,
)


# Register cross-module relationships that will be configured after all models are loaded
@register_cross_module_relationship(InstallationProject, 'work_orders')
def create_installation_project_work_orders_relationship():
    return relationship(
        "WorkOrder",
        foreign_keys="[WorkOrder.project_id]",
        back_populates="project",
        cascade="all, delete-orphan"
    )
