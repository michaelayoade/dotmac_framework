"""
Core Project Management System

Universal project manager providing CRUD operations, lifecycle management,
and business logic for any type of project.
"""

import logging
import secrets
import string
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    MilestoneCreate,
    PhaseCreate,
    PhaseStatus,
    PhaseUpdate,
    Project,
    ProjectCreate,
    ProjectMilestone,
    ProjectPhase,
    ProjectStatus,
    ProjectType,
)
from .models import ProjectUpdate
from .models import ProjectUpdate as ProjectUpdateSchema
from .models import UpdateCreate

logger = logging.getLogger(__name__)


class ProjectManager:
    """Core project management system."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize project manager."""
        self.config = config or {}
        self._project_counter = 1000

        # Default phase templates for different project types
        self.default_phases = {
            ProjectType.NEW_INSTALLATION: [
                {"name": "Site Survey", "order": 1, "critical": True},
                {"name": "Equipment Procurement", "order": 2, "critical": True},
                {"name": "Installation", "order": 3, "critical": True},
                {"name": "Testing & Commissioning", "order": 4, "critical": True},
                {"name": "Customer Training", "order": 5, "critical": False},
            ],
            ProjectType.DEPLOYMENT: [
                {"name": "Planning & Design", "order": 1, "critical": True},
                {"name": "Environment Preparation", "order": 2, "critical": True},
                {"name": "System Deployment", "order": 3, "critical": True},
                {"name": "Testing & Validation", "order": 4, "critical": True},
                {"name": "Go-Live & Support", "order": 5, "critical": False},
            ],
            ProjectType.SOFTWARE_DEVELOPMENT: [
                {"name": "Requirements Analysis", "order": 1, "critical": True},
                {"name": "Design & Architecture", "order": 2, "critical": True},
                {"name": "Development", "order": 3, "critical": True},
                {"name": "Testing", "order": 4, "critical": True},
                {"name": "Deployment", "order": 5, "critical": True},
            ],
        }

    def generate_project_number(
        self, tenant_id: str, project_type: ProjectType = None
    ) -> str:
        """Generate unique project number."""
        timestamp = int(datetime.now(timezone.utc).timestamp())

        # Use project type prefix if available
        if project_type:
            type_prefix = {
                ProjectType.NEW_INSTALLATION: "INST",
                ProjectType.DEPLOYMENT: "DEPL",
                ProjectType.SOFTWARE_DEVELOPMENT: "DEV",
                ProjectType.MAINTENANCE: "MAINT",
                ProjectType.REPAIR: "REP",
            }.get(project_type, "PROJ")
        else:
            type_prefix = "PROJ"

        # Add tenant prefix
        tenant_prefix = tenant_id[:3].upper() if tenant_id else "GEN"

        random_chars = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
        )

        return f"{tenant_prefix}-{type_prefix}-{timestamp}-{random_chars}"

    async def create_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_data: ProjectCreate,
        created_by: Optional[str] = None,
    ) -> Project:
        """Create a new project with optional default phases."""
        try:
            # Generate project number
            project_number = self.generate_project_number(
                tenant_id, project_data.project_type
            )

            # Create project
            project = Project(
                id=uuid4(),
                tenant_id=tenant_id,
                project_number=project_number,
                project_name=project_data.project_name,
                description=project_data.description,
                project_type=project_data.project_type,
                priority=project_data.priority,
                customer_id=project_data.customer_id,
                client_name=project_data.client_name,
                client_email=project_data.client_email,
                client_phone=project_data.client_phone,
                project_manager=project_data.project_manager,
                assigned_team=project_data.assigned_team,
                requested_date=project_data.requested_date,
                planned_start_date=project_data.planned_start_date,
                planned_end_date=project_data.planned_end_date,
                estimated_cost=project_data.estimated_cost,
                approved_budget=project_data.approved_budget,
                requirements=project_data.requirements,
                deliverables=project_data.deliverables,
                success_criteria=project_data.success_criteria,
                project_location=project_data.project_location,
                special_requirements=project_data.special_requirements,
                platform_data=project_data.platform_data,
                created_by=created_by,
                updated_by=created_by,
            )

            db.add(project)

            # Create default phases if available for this project type
            if project_data.project_type in self.default_phases:
                await self._create_default_phases(
                    db, project, project_data.project_type
                )

            await db.commit()
            await db.refresh(project)

            logger.info(
                f"Created project {project.project_number} for tenant {tenant_id}"
            )

            # Trigger project creation events
            await self._trigger_project_created_events(project)

            return project

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating project: {str(e)}")
            raise

    async def get_project(
        self, db: AsyncSession, tenant_id: str, project_id: str
    ) -> Optional[Project]:
        """Get project by ID with related data."""
        query = (
            select(Project)
            .where(and_(Project.id == project_id, Project.tenant_id == tenant_id))
            .options(
                selectinload(Project.phases),
                selectinload(Project.milestones),
                selectinload(Project.updates),
                selectinload(Project.resources),
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_project_by_number(
        self, db: AsyncSession, tenant_id: str, project_number: str
    ) -> Optional[Project]:
        """Get project by project number."""
        query = (
            select(Project)
            .where(
                and_(
                    Project.project_number == project_number,
                    Project.tenant_id == tenant_id,
                )
            )
            .options(
                selectinload(Project.phases),
                selectinload(Project.milestones),
                selectinload(Project.updates),
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        update_data: ProjectUpdateSchema,
        updated_by: Optional[str] = None,
    ) -> Optional[Project]:
        """Update project."""
        try:
            # Get existing project
            project = await self.get_project(db, tenant_id, project_id)
            if not project:
                return None

            # Track status changes
            old_status = project.project_status

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(project, field, value)

            project.updated_at = datetime.now(timezone.utc)
            project.updated_by = updated_by

            # Handle status changes
            if update_data.project_status and update_data.project_status != old_status:
                await self._handle_status_change(
                    project, old_status, update_data.project_status
                )

            # Recalculate completion if needed
            if (
                hasattr(update_data, "completion_percentage")
                and update_data.completion_percentage is not None
            ):
                project.calculate_completion_percentage()

            await db.commit()
            await db.refresh(project)

            logger.info(f"Updated project {project.project_number}")

            # Trigger events
            await self._trigger_project_updated_events(project, old_status)

            return project

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating project {project_id}: {str(e)}")
            raise

    async def list_projects(
        self,
        db: AsyncSession,
        tenant_id: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Project], int]:
        """List projects with filtering, pagination, and sorting."""
        try:
            # Build base query
            query = select(Project).where(Project.tenant_id == tenant_id)

            # Apply filters
            if filters:
                if "project_status" in filters:
                    if isinstance(filters["project_status"], list):
                        query = query.where(
                            Project.project_status.in_(filters["project_status"])
                        )
                    else:
                        query = query.where(
                            Project.project_status == filters["project_status"]
                        )

                if "project_type" in filters:
                    if isinstance(filters["project_type"], list):
                        query = query.where(
                            Project.project_type.in_(filters["project_type"])
                        )
                    else:
                        query = query.where(
                            Project.project_type == filters["project_type"]
                        )

                if "priority" in filters:
                    if isinstance(filters["priority"], list):
                        query = query.where(Project.priority.in_(filters["priority"]))
                    else:
                        query = query.where(Project.priority == filters["priority"])

                if "project_manager" in filters:
                    query = query.where(
                        Project.project_manager == filters["project_manager"]
                    )

                if "customer_id" in filters:
                    query = query.where(Project.customer_id == filters["customer_id"])

                if "assigned_team" in filters:
                    query = query.where(
                        Project.assigned_team == filters["assigned_team"]
                    )

                if "search" in filters and filters["search"]:
                    search_term = f"%{filters['search']}%"
                    query = query.where(
                        or_(
                            Project.project_name.ilike(search_term),
                            Project.description.ilike(search_term),
                            Project.project_number.ilike(search_term),
                        )
                    )

                if "overdue_only" in filters and filters["overdue_only"]:
                    query = query.where(
                        and_(
                            Project.planned_end_date < date.today(),
                            Project.project_status.notin_(
                                [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]
                            ),
                        )
                    )

                if "created_after" in filters:
                    query = query.where(Project.created_at >= filters["created_after"])

                if "created_before" in filters:
                    query = query.where(Project.created_at <= filters["created_before"])

            # Get total count
            count_query = select(func.count(Project.id)).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()

            # Apply sorting
            sort_column = getattr(Project, sort_by, Project.created_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            # Execute query
            result = await db.execute(query)
            projects = result.scalars().all()

            return list(projects), total_count

        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            raise

    async def create_project_phase(
        self, db: AsyncSession, tenant_id: str, project_id: str, phase_data: PhaseCreate
    ) -> Optional[ProjectPhase]:
        """Create a new project phase."""
        try:
            # Verify project exists
            project = await self.get_project(db, tenant_id, project_id)
            if not project:
                return None

            phase = ProjectPhase(
                id=uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                phase_name=phase_data.phase_name,
                phase_description=phase_data.phase_description,
                phase_order=phase_data.phase_order,
                phase_type=phase_data.phase_type,
                is_critical_path=phase_data.is_critical_path,
                is_client_visible=phase_data.is_client_visible,
                planned_start_date=phase_data.planned_start_date,
                planned_end_date=phase_data.planned_end_date,
                estimated_duration_hours=phase_data.estimated_duration_hours,
                assigned_to=phase_data.assigned_to,
                work_instructions=phase_data.work_instructions,
                estimated_cost=phase_data.estimated_cost,
            )

            db.add(phase)

            # Update project phase counts
            project.total_phases += 1
            project.calculate_completion_percentage()

            await db.commit()
            await db.refresh(phase)

            logger.info(
                f"Created phase {phase.phase_name} for project {project.project_number}"
            )

            return phase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating project phase: {str(e)}")
            raise

    async def update_project_phase(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        phase_id: str,
        update_data: PhaseUpdate,
    ) -> Optional[ProjectPhase]:
        """Update project phase."""
        try:
            # Get phase
            query = select(ProjectPhase).where(
                and_(
                    ProjectPhase.id == phase_id,
                    ProjectPhase.project_id == project_id,
                    ProjectPhase.tenant_id == tenant_id,
                )
            )
            result = await db.execute(query)
            phase = result.scalar_one_or_none()

            if not phase:
                return None

            # Track status changes
            old_status = phase.phase_status

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(phase, field, value)

            phase.updated_at = datetime.now(timezone.utc)

            # Handle completion
            if (
                update_data.phase_status == PhaseStatus.COMPLETED
                and old_status != PhaseStatus.COMPLETED
            ):
                phase.actual_end_date = date.today()

                # Update project phases completed count
                project = await self.get_project(db, tenant_id, project_id)
                if project:
                    project.phases_completed += 1
                    project.calculate_completion_percentage()

            await db.commit()
            await db.refresh(phase)

            logger.info(f"Updated phase {phase.phase_name}")

            return phase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating phase {phase_id}: {str(e)}")
            raise

    async def create_project_milestone(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        milestone_data: MilestoneCreate,
    ) -> Optional[ProjectMilestone]:
        """Create a project milestone."""
        try:
            # Verify project exists
            project = await self.get_project(db, tenant_id, project_id)
            if not project:
                return None

            milestone = ProjectMilestone(
                id=uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                milestone_name=milestone_data.milestone_name,
                milestone_description=milestone_data.milestone_description,
                milestone_type=milestone_data.milestone_type,
                planned_date=milestone_data.planned_date,
                is_critical=milestone_data.is_critical,
                is_client_visible=milestone_data.is_client_visible,
                success_criteria=milestone_data.success_criteria,
            )

            db.add(milestone)
            await db.commit()
            await db.refresh(milestone)

            logger.info(
                f"Created milestone {milestone.milestone_name} for project {project.project_number}"
            )

            return milestone

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating milestone: {str(e)}")
            raise

    async def add_project_update(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
        update_data: UpdateCreate,
    ) -> Optional[ProjectUpdate]:
        """Add a project update/communication."""
        try:
            # Verify project exists
            project = await self.get_project(db, tenant_id, project_id)
            if not project:
                return None

            update = ProjectUpdate(
                id=uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                update_title=update_data.update_title,
                update_content=update_data.update_content,
                update_type=update_data.update_type,
                priority=update_data.priority,
                is_client_visible=update_data.is_client_visible,
                author_name=update_data.author_name,
                author_role=update_data.author_role,
                progress_percentage=update_data.progress_percentage,
                next_steps=update_data.next_steps,
                estimated_completion=update_data.estimated_completion,
            )

            db.add(update)

            # Update project if progress percentage is provided
            if update_data.progress_percentage is not None:
                project.completion_percentage = update_data.progress_percentage

            await db.commit()
            await db.refresh(update)

            logger.info(f"Added update to project {project.project_number}")

            # Trigger notification events
            await self._trigger_update_events(project, update)

            return update

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding project update: {str(e)}")
            raise

    async def get_project_analytics(
        self, db: AsyncSession, tenant_id: str, filters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Get project analytics and metrics."""
        try:
            base_query = select(Project).where(Project.tenant_id == tenant_id)

            if filters:
                if "date_range" in filters:
                    start_date, end_date = filters["date_range"]
                    base_query = base_query.where(
                        and_(
                            Project.created_at >= start_date,
                            Project.created_at <= end_date,
                        )
                    )

            # Total projects
            total_result = await db.execute(
                select(func.count()).select_from(base_query.subquery())
            )
            total_projects = total_result.scalar()

            # Status breakdown
            status_query = (
                select(Project.project_status, func.count(Project.id).label("count"))
                .where(Project.tenant_id == tenant_id)
                .group_by(Project.project_status)
            )

            if filters and "date_range" in filters:
                start_date, end_date = filters["date_range"]
                status_query = status_query.where(
                    and_(
                        Project.created_at >= start_date, Project.created_at <= end_date
                    )
                )

            status_result = await db.execute(status_query)
            status_breakdown = {row.project_status: row.count for row in status_result}

            # Type breakdown
            type_query = (
                select(Project.project_type, func.count(Project.id).label("count"))
                .where(Project.tenant_id == tenant_id)
                .group_by(Project.project_type)
            )

            if filters and "date_range" in filters:
                start_date, end_date = filters["date_range"]
                type_query = type_query.where(
                    and_(
                        Project.created_at >= start_date, Project.created_at <= end_date
                    )
                )

            type_result = await db.execute(type_query)
            type_breakdown = {row.project_type: row.count for row in type_result}

            # Average completion time
            completion_query = select(
                func.avg(
                    func.extract(
                        "epoch", Project.actual_end_date - Project.actual_start_date
                    )
                    / 86400
                ).label("avg_days")
            ).where(
                and_(
                    Project.tenant_id == tenant_id,
                    Project.actual_end_date.isnot(None),
                    Project.actual_start_date.isnot(None),
                )
            )

            completion_result = await db.execute(completion_query)
            avg_completion_days = completion_result.scalar() or 0

            # Overdue projects
            overdue_query = select(func.count(Project.id)).where(
                and_(
                    Project.tenant_id == tenant_id,
                    Project.planned_end_date < date.today(),
                    Project.project_status.notin_(
                        [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]
                    ),
                )
            )
            overdue_result = await db.execute(overdue_query)
            overdue_count = overdue_result.scalar()

            return {
                "total_projects": total_projects,
                "status_breakdown": status_breakdown,
                "type_breakdown": type_breakdown,
                "avg_completion_days": round(avg_completion_days, 2),
                "overdue_count": overdue_count,
                "date_range": (
                    {
                        "start": filters.get("date_range", [None, None])[0],
                        "end": filters.get("date_range", [None, None])[1],
                    }
                    if filters
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error getting project analytics: {str(e)}")
            raise

    async def _create_default_phases(
        self, db: AsyncSession, project: Project, project_type: ProjectType
    ):
        """Create default phases for a project type."""
        phase_templates = self.default_phases.get(project_type, [])

        for template in phase_templates:
            phase = ProjectPhase(
                id=uuid4(),
                tenant_id=project.tenant_id,
                project_id=project.id,
                phase_name=template["name"],
                phase_order=template["order"],
                is_critical_path=template["critical"],
                is_client_visible=True,
            )
            db.add(phase)

        # Update total phases
        project.total_phases = len(phase_templates)

    async def _handle_status_change(
        self, project: Project, old_status: ProjectStatus, new_status: ProjectStatus
    ):
        """Handle project status changes."""
        if (
            new_status == ProjectStatus.IN_PROGRESS
            and old_status != ProjectStatus.IN_PROGRESS
        ):
            if not project.actual_start_date:
                project.actual_start_date = date.today()

        elif (
            new_status == ProjectStatus.COMPLETED
            and old_status != ProjectStatus.COMPLETED
        ):
            if not project.actual_end_date:
                project.actual_end_date = date.today()
            project.completion_percentage = 100

        elif new_status == ProjectStatus.CANCELLED:
            # Mark as cancelled but preserve progress
            pass

    async def _trigger_project_created_events(self, project: Project):
        """Trigger events when project is created."""
        logger.info(f"Project created events triggered for {project.project_number}")
        # This would integrate with event system, notifications, etc.

    async def _trigger_project_updated_events(
        self, project: Project, old_status: ProjectStatus
    ):
        """Trigger events when project is updated."""
        logger.info(f"Project updated events triggered for {project.project_number}")

    async def _trigger_update_events(self, project: Project, update: ProjectUpdate):
        """Trigger events when update is added."""
        logger.info(f"Project update events triggered for {project.project_number}")


class GlobalProjectManager:
    """Global singleton project manager."""

    def __init__(self):
        self._instance: Optional[ProjectManager] = None
        self._initialized = False

    def initialize(self, config: dict[str, Any]) -> ProjectManager:
        """Initialize the global project manager."""
        if not self._initialized:
            self._instance = ProjectManager(config=config)
            self._initialized = True
        return self._instance

    def get_instance(self) -> Optional[ProjectManager]:
        """Get the global instance."""
        return self._instance
