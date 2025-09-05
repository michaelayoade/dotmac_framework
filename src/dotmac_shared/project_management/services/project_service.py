"""
High-level Project Management Service

Business logic layer that orchestrates project operations, workflows,
and cross-platform integrations.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (
    MilestoneCreate,
    MilestoneType,
    PhaseResponse,
    PhaseStatus,
    PhaseUpdate,
    Project,
    ProjectCreate,
    ProjectPriority,
    ProjectResponse,
    ProjectStatus,
    ProjectType,
)
from ..core.models import ProjectUpdate as ProjectUpdateSchema
from ..core.models import UpdateCreate
from ..core.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class ProjectService:
    """High-level project management service with business logic."""

    def __init__(self, project_manager: ProjectManager):
        """Initialize service."""
        self.project_manager = project_manager

    async def create_customer_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        project_name: str,
        project_type: ProjectType,
        description: Optional[str] = None,
        priority: ProjectPriority = ProjectPriority.NORMAL,
        project_manager: Optional[str] = None,
        planned_start_date: Optional[date] = None,
        planned_end_date: Optional[date] = None,
        estimated_cost: Optional[Decimal] = None,
        requirements: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ProjectResponse:
        """Create a project for a customer with business logic."""

        # Prepare project data
        project_data = ProjectCreate(
            project_name=project_name,
            description=description,
            project_type=project_type,
            priority=priority,
            customer_id=customer_id,
            project_manager=project_manager,
            planned_start_date=planned_start_date,
            planned_end_date=planned_end_date,
            estimated_cost=estimated_cost,
            requirements=requirements,
            platform_data=metadata or {},
        )

        # Create project
        project = await self.project_manager.create_project(db, tenant_id, project_data)

        # Apply business rules
        await self._apply_project_creation_rules(db, project)

        # Convert to response
        return ProjectResponse.model_validate(project)

    async def assign_project_manager(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        manager_id: str,
        manager_name: str,
    ) -> Optional[ProjectResponse]:
        """Assign project manager with notification."""

        update_data = ProjectUpdateSchema(project_manager=manager_name)
        project = await self.project_manager.update_project(
            db, tenant_id, project_id, update_data
        )

        if project:
            # Add assignment update
            await self.project_manager.add_project_update(
                db,
                tenant_id,
                project_id,
                UpdateCreate(
                    update_title="Project Manager Assigned",
                    update_content=f"Project assigned to {manager_name}",
                    update_type="assignment",
                    priority=ProjectPriority.NORMAL,
                    author_name="System",
                    author_role="system",
                ),
            )

            return ProjectResponse.model_validate(project)
        return None

    async def start_project(
        self, db: AsyncSession, tenant_id: str, project_id: str, started_by: str
    ) -> Optional[ProjectResponse]:
        """Start a project and trigger first phase."""

        # Update project status
        update_data = ProjectUpdateSchema(
            project_status=ProjectStatus.IN_PROGRESS, actual_start_date=date.today()
        )

        project = await self.project_manager.update_project(
            db, tenant_id, project_id, update_data, started_by
        )

        if project:
            # Start first phase if exists
            if project.phases:
                first_phase = min(project.phases, key=lambda p: p.phase_order)
                await self.start_project_phase(
                    db, tenant_id, project_id, str(first_phase.id), started_by
                )

            # Add start notification
            await self.project_manager.add_project_update(
                db,
                tenant_id,
                project_id,
                UpdateCreate(
                    update_title="Project Started",
                    update_content=f"Project has been officially started by {started_by}",
                    update_type="milestone",
                    priority=ProjectPriority.HIGH,
                    author_name=started_by,
                    author_role="project_manager",
                ),
            )

            return ProjectResponse.model_validate(project)
        return None

    async def complete_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        completion_notes: str,
        completed_by: str,
        client_satisfaction: Optional[int] = None,
    ) -> Optional[ProjectResponse]:
        """Complete a project with final updates."""

        # Update project status
        update_data = ProjectUpdateSchema(
            project_status=ProjectStatus.COMPLETED,
            actual_end_date=date.today(),
            completion_percentage=100,
            completion_notes=completion_notes,
            client_satisfaction_score=client_satisfaction,
        )

        project = await self.project_manager.update_project(
            db, tenant_id, project_id, update_data, completed_by
        )

        if project:
            # Complete all remaining phases
            for phase in project.phases:
                if phase.phase_status not in [
                    PhaseStatus.COMPLETED,
                    PhaseStatus.SKIPPED,
                ]:
                    await self.complete_project_phase(
                        db,
                        tenant_id,
                        project_id,
                        str(phase.id),
                        "Auto-completed with project",
                        completed_by,
                    )

            # Add completion update
            await self.project_manager.add_project_update(
                db,
                tenant_id,
                project_id,
                UpdateCreate(
                    update_title="Project Completed",
                    update_content=f"Project successfully completed. {completion_notes}",
                    update_type="completion",
                    priority=ProjectPriority.HIGH,
                    author_name=completed_by,
                    author_role="project_manager",
                    progress_percentage=100,
                ),
            )

            return ProjectResponse.model_validate(project)
        return None

    async def start_project_phase(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        phase_id: str,
        started_by: str,
    ) -> Optional[PhaseResponse]:
        """Start a project phase."""

        update_data = PhaseUpdate(
            phase_status=PhaseStatus.IN_PROGRESS, actual_start_date=date.today()
        )

        phase = await self.project_manager.update_project_phase(
            db, tenant_id, project_id, phase_id, update_data
        )

        if phase:
            # Add phase start update
            await self.project_manager.add_project_update(
                db,
                tenant_id,
                project_id,
                UpdateCreate(
                    update_title=f"Phase Started: {phase.phase_name}",
                    update_content=f"Phase '{phase.phase_name}' has been started",
                    update_type="phase_start",
                    priority=ProjectPriority.NORMAL,
                    author_name=started_by,
                    phase_completed=phase.phase_name,
                ),
            )

            return PhaseResponse.model_validate(phase)
        return None

    async def complete_project_phase(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        phase_id: str,
        completion_notes: str,
        completed_by: str,
    ) -> Optional[PhaseResponse]:
        """Complete a project phase."""

        update_data = PhaseUpdate(
            phase_status=PhaseStatus.COMPLETED,
            completion_percentage=100,
            actual_end_date=date.today(),
            completion_notes=completion_notes,
        )

        phase = await self.project_manager.update_project_phase(
            db, tenant_id, project_id, phase_id, update_data
        )

        if phase:
            # Add phase completion update
            await self.project_manager.add_project_update(
                db,
                tenant_id,
                project_id,
                UpdateCreate(
                    update_title=f"Phase Completed: {phase.phase_name}",
                    update_content=f"Phase '{phase.phase_name}' has been completed. {completion_notes}",
                    update_type="phase_complete",
                    priority=ProjectPriority.NORMAL,
                    author_name=completed_by,
                    phase_completed=phase.phase_name,
                ),
            )

            # Check if we should start next phase
            await self._check_next_phase_start(
                db, tenant_id, project_id, phase.phase_order
            )

            return PhaseResponse.model_validate(phase)
        return None

    async def escalate_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        escalation_reason: str,
        escalated_by: str,
        new_priority: ProjectPriority = None,
    ) -> Optional[ProjectResponse]:
        """Escalate a project due to issues or delays."""

        # Get current project
        project = await self.project_manager.get_project(db, tenant_id, project_id)
        if not project:
            return None

        # Determine new priority
        if not new_priority:
            priority_escalation = {
                ProjectPriority.LOW: ProjectPriority.NORMAL,
                ProjectPriority.NORMAL: ProjectPriority.HIGH,
                ProjectPriority.HIGH: ProjectPriority.URGENT,
                ProjectPriority.URGENT: ProjectPriority.CRITICAL,
                ProjectPriority.CRITICAL: ProjectPriority.CRITICAL,
            }
            new_priority = priority_escalation.get(
                project.priority, ProjectPriority.HIGH
            )

        # Update project
        update_data = ProjectUpdateSchema(priority=new_priority)
        updated_project = await self.project_manager.update_project(
            db, tenant_id, project_id, update_data, escalated_by
        )

        if updated_project:
            # Add escalation update
            await self.project_manager.add_project_update(
                db,
                tenant_id,
                project_id,
                UpdateCreate(
                    update_title="Project Escalated",
                    update_content=f"Project escalated to {new_priority.value} priority. Reason: {escalation_reason}",
                    update_type="escalation",
                    priority=ProjectPriority.URGENT,
                    author_name=escalated_by,
                    author_role="project_manager",
                ),
            )

            return ProjectResponse.model_validate(updated_project)
        return None

    async def get_customer_projects(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        status_filter: Optional[list[ProjectStatus]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProjectResponse], int]:
        """Get all projects for a customer."""

        filters = {"customer_id": customer_id}
        if status_filter:
            filters["project_status"] = status_filter

        projects, total = await self.project_manager.list_projects(
            db, tenant_id, filters, page, page_size
        )

        project_responses = [
            ProjectResponse.model_validate(project) for project in projects
        ]
        return project_responses, total

    async def get_team_projects(
        self,
        db: AsyncSession,
        tenant_id: str,
        team_name: str,
        status_filter: Optional[list[ProjectStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ProjectResponse], int]:
        """Get all projects assigned to a team."""

        filters = {"assigned_team": team_name}
        if status_filter:
            filters["project_status"] = status_filter

        projects, total = await self.project_manager.list_projects(
            db, tenant_id, filters, page, page_size
        )

        project_responses = [
            ProjectResponse.model_validate(project) for project in projects
        ]
        return project_responses, total

    async def get_overdue_projects(
        self, db: AsyncSession, tenant_id: str
    ) -> list[ProjectResponse]:
        """Get all overdue projects."""

        filters = {"overdue_only": True}
        projects, _ = await self.project_manager.list_projects(db, tenant_id, filters)

        return [ProjectResponse.model_validate(project) for project in projects]

    async def get_project_dashboard(
        self,
        db: AsyncSession,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get project dashboard metrics."""

        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)
        elif start_date:
            date_range = (start_date, datetime.now(timezone.utc))
        elif end_date:
            date_range = (datetime.now(timezone.utc) - timedelta(days=30), end_date)

        filters = {}
        if date_range:
            filters["date_range"] = date_range

        analytics = await self.project_manager.get_project_analytics(
            db, tenant_id, filters
        )

        # Add additional dashboard metrics
        overdue_projects = await self.get_overdue_projects(db, tenant_id)
        analytics["overdue_projects"] = len(overdue_projects)

        # Get active projects
        active_filters = {
            "project_status": [ProjectStatus.IN_PROGRESS, ProjectStatus.SCHEDULED]
        }
        active_projects, _ = await self.project_manager.list_projects(
            db, tenant_id, active_filters
        )
        analytics["active_projects"] = len(active_projects)

        return analytics

    async def _apply_project_creation_rules(self, db: AsyncSession, project: Project):
        """Apply business rules after project creation."""

        # Auto-create milestones for certain project types
        if project.project_type == ProjectType.NEW_INSTALLATION:
            await self._create_installation_milestones(db, project)
        elif project.project_type == ProjectType.DEPLOYMENT:
            await self._create_deployment_milestones(db, project)

    async def _create_installation_milestones(self, db: AsyncSession, project: Project):
        """Create standard milestones for installation projects."""

        milestones = [
            {
                "name": "Site Survey Completed",
                "type": MilestoneType.PHASE_COMPLETE,
                "days_offset": 3,
                "critical": True,
            },
            {
                "name": "Equipment Delivered",
                "type": MilestoneType.CUSTOM_CHECKPOINT,
                "days_offset": 7,
                "critical": True,
            },
            {
                "name": "Installation Complete",
                "type": MilestoneType.DELIVERY_READY,
                "days_offset": 14,
                "critical": True,
            },
        ]

        for milestone_data in milestones:
            planned_date = (project.planned_start_date or date.today()) + timedelta(
                days=milestone_data["days_offset"]
            )

            milestone_create = MilestoneCreate(
                milestone_name=milestone_data["name"],
                milestone_type=milestone_data["type"],
                planned_date=planned_date,
                is_critical=milestone_data["critical"],
            )

            await self.project_manager.create_project_milestone(
                db, project.tenant_id, str(project.id), milestone_create
            )

    async def _create_deployment_milestones(self, db: AsyncSession, project: Project):
        """Create standard milestones for deployment projects."""

        milestones = [
            {
                "name": "Planning Complete",
                "type": MilestoneType.PLANNING_COMPLETE,
                "days_offset": 5,
                "critical": True,
            },
            {
                "name": "Environment Ready",
                "type": MilestoneType.PHASE_COMPLETE,
                "days_offset": 10,
                "critical": True,
            },
            {
                "name": "Deployment Complete",
                "type": MilestoneType.PROJECT_COMPLETE,
                "days_offset": 21,
                "critical": True,
            },
        ]

        for milestone_data in milestones:
            planned_date = (project.planned_start_date or date.today()) + timedelta(
                days=milestone_data["days_offset"]
            )

            milestone_create = MilestoneCreate(
                milestone_name=milestone_data["name"],
                milestone_type=milestone_data["type"],
                planned_date=planned_date,
                is_critical=milestone_data["critical"],
            )

            await self.project_manager.create_project_milestone(
                db, project.tenant_id, str(project.id), milestone_create
            )

    async def _check_next_phase_start(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        completed_phase_order: int,
    ):
        """Check if next phase should automatically start."""

        project = await self.project_manager.get_project(db, tenant_id, project_id)
        if not project:
            return

        # Find next phase in sequence
        next_phase = None
        for phase in project.phases:
            if (
                phase.phase_order == completed_phase_order + 1
                and phase.phase_status == PhaseStatus.PENDING
            ):
                next_phase = phase
                break

        if next_phase:
            # Auto-start if no dependencies or all dependencies met
            can_start = True
            if next_phase.depends_on_phases:
                for dep_id in next_phase.depends_on_phases:
                    dep_phase = next(
                        (p for p in project.phases if str(p.id) == dep_id), None
                    )
                    if dep_phase and dep_phase.phase_status != PhaseStatus.COMPLETED:
                        can_start = False
                        break

            if can_start:
                await self.start_project_phase(
                    db, tenant_id, project_id, str(next_phase.id), "System Auto-Start"
                )
