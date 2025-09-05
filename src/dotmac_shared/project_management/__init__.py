"""
DotMac Shared Project Management Package

Universal project management system for installation projects, service deployments,
infrastructure projects, and general project lifecycle management.

Key Features:
- Multi-phase project tracking with dependencies
- Milestone management and deadline tracking
- Resource allocation and team assignment
- Customer communication and visibility
- Cost tracking and budget management
- Document and photo management
- Real-time progress updates
- SLA compliance monitoring

Use Cases:
- ISP Framework: Customer installation projects, network expansions
- Management Platform: Infrastructure deployments, system upgrades
- General: Any multi-phase project with stakeholders and deadlines
"""
from typing import Any, Optional

__version__ = "1.0.0"

# Core project management components
from .core.models import (
    ProjectUpdate,  # Main entities; Enums and types; Pydantic schemas
)
from .core.models import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneType,
    PhaseCreate,
    PhaseResponse,
    PhaseStatus,
    PhaseUpdate,
    Project,
    ProjectCreate,
    ProjectDocument,
    ProjectMilestone,
    ProjectPhase,
    ProjectPriority,
    ProjectResource,
    ProjectResponse,
    ProjectStatus,
    ProjectType,
    ResourceType,
    UpdateCreate,
    UpdateResponse,
)
from .core.project_manager import ProjectManager
from .services.project_service import ProjectService
from .workflows.project_workflows import ProjectWorkflowManager

# Platform adapters
try:
    from .adapters.platform_adapter import (
        ISPProjectAdapter,
        ManagementProjectAdapter,
        ProjectPlatformAdapter,
    )

    _platform_adapters_available = True
except ImportError:
    _platform_adapters_available = False
    ISPProjectAdapter = ManagementProjectAdapter = ProjectPlatformAdapter = None


# Initialization functions
def initialize_project_management(config: Optional[dict] = None):
    """Initialize the project management system."""
    from .core.project_manager import ProjectManager

    manager = ProjectManager(config=config)
    return manager


def get_project_manager():
    """Get the global project manager instance."""
    # This would return a singleton instance in production
    return initialize_project_management()


# Export all public components
__all__ = [
    # Models
    "Project",
    "ProjectPhase",
    "ProjectMilestone",
    "ProjectUpdate",
    "ProjectDocument",
    "ProjectResource",
    # Enums
    "ProjectType",
    "ProjectStatus",
    "PhaseStatus",
    "MilestoneType",
    "ProjectPriority",
    "ResourceType",
    # Schemas
    "ProjectCreate",
    "ProjectUpdateSchema",
    "ProjectResponse",
    "PhaseCreate",
    "PhaseUpdate",
    "PhaseResponse",
    "MilestoneCreate",
    "MilestoneResponse",
    "UpdateCreate",
    "UpdateResponse",
    # Services
    "ProjectManager",
    "ProjectService",
    "ProjectWorkflowManager",
    # Platform adapters (if available)
    "ISPProjectAdapter",
    "ManagementProjectAdapter",
    "ProjectPlatformAdapter",
    # Initialization
    "initialize_project_management",
    "get_project_manager",
]
