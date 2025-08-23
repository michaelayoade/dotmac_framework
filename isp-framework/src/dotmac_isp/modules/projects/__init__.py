"""Installation Project Management Module."""

from .models import (
    InstallationProject,
    ProjectPhase,
    ProjectMilestone,
    ProjectUpdate,
    ProjectStatus,
    PhaseStatus,
    ProjectType,
    MilestoneType,
)

from .schemas import (
    InstallationProjectCreate,
    InstallationProjectUpdate,
    InstallationProjectResponse,
    ProjectPhaseCreate,
    ProjectPhaseResponse,
    ProjectMilestoneResponse,
    ProjectUpdateCreate,
    ProjectUpdateResponse,
    CustomerProjectSummary,
    ProjectTimelineResponse,
)

from .service import InstallationProjectService, ProjectWorkflowService

from .repository import InstallationProjectRepository, ProjectPhaseRepository

__all__ = [
    # Models
    "InstallationProject",
    "ProjectPhase",
    "ProjectMilestone",
    "ProjectUpdate",
    "ProjectStatus",
    "PhaseStatus",
    "ProjectType",
    "MilestoneType",
    # Schemas
    "InstallationProjectCreate",
    "InstallationProjectUpdate",
    "InstallationProjectResponse",
    "ProjectPhaseCreate",
    "ProjectPhaseResponse",
    "ProjectMilestoneResponse",
    "ProjectUpdateCreate",
    "ProjectUpdateResponse",
    "CustomerProjectSummary",
    "ProjectTimelineResponse",
    # Services
    "InstallationProjectService",
    "ProjectWorkflowService",
    # Repositories
    "InstallationProjectRepository",
    "ProjectPhaseRepository",
]
