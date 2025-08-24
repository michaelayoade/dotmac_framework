"""Installation Project Management Repository."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from .models import (
    InstallationProject,
    ProjectPhase,
    ProjectMilestone,
    ProjectUpdate,
    ProjectType,
    ProjectStatus,
    PhaseStatus,
    MilestoneType,
)


class InstallationProjectRepository:
    """Repository for installation project data operations."""

    def __init__(self, db: Session):
        """  Init   operation."""
        self.db = db

    def create(self, project_data: Dict[str, Any]) -> InstallationProject:
        """Create a new installation project."""
        project = InstallationProject(**project_data)
        self.db.add(project)
        self.db.flush()
        return project

    def get_by_id(
        self, project_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[InstallationProject]:
        """Get project by ID."""
        query = self.db.query(InstallationProject).filter(
            InstallationProject.id == project_id
        )
        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)
        return query.first()

    def get_by_number(
        self, project_number: str, tenant_id: Optional[UUID] = None
    ) -> Optional[InstallationProject]:
        """Get project by project number."""
        query = self.db.query(InstallationProject).filter(
            InstallationProject.project_number == project_number
        )
        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)
        return query.first()

    def list_by_customer(
        self,
        customer_id: UUID,
        tenant_id: Optional[UUID] = None,
        status_filter: Optional[ProjectStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[InstallationProject]:
        """List projects for a customer."""
        query = self.db.query(InstallationProject).filter(
            InstallationProject.customer_id == customer_id
        )

        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)

        if status_filter:
            query = query.filter(InstallationProject.project_status == status_filter)

        return (
            query.order_by(desc(InstallationProject.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_by_status(
        self,
        status: ProjectStatus,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InstallationProject]:
        """List projects by status."""
        query = self.db.query(InstallationProject).filter(
            InstallationProject.project_status == status
        )

        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)

        return (
            query.order_by(desc(InstallationProject.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_overdue(
        self, tenant_id: Optional[UUID] = None
    ) -> List[InstallationProject]:
        """List overdue projects."""
        query = self.db.query(InstallationProject).filter(
            and_(
                InstallationProject.planned_end_date < date.today(),
                InstallationProject.project_status.in_(
                    [
                        ProjectStatus.IN_PROGRESS,
                        ProjectStatus.SCHEDULED,
                        ProjectStatus.TESTING,
                    ]
                ),
            )
        )

        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)

        return query.order_by(asc(InstallationProject.planned_end_date)).all()

    def list_by_technician(
        self,
        technician: str,
        tenant_id: Optional[UUID] = None,
        active_only: bool = True,
    ) -> List[InstallationProject]:
        """List projects assigned to a technician."""
        query = self.db.query(InstallationProject).filter(
            InstallationProject.lead_technician == technician
        )

        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)

        if active_only:
            query = query.filter(
                InstallationProject.project_status.in_(
                    [
                        ProjectStatus.SCHEDULED,
                        ProjectStatus.IN_PROGRESS,
                        ProjectStatus.TESTING,
                    ]
                )
            )

        return query.order_by(asc(InstallationProject.planned_start_date)).all()

    def get_project_statistics(
        self, tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get project statistics."""
        query = self.db.query(InstallationProject)
        if tenant_id:
            query = query.filter(InstallationProject.tenant_id == tenant_id)

        # Total projects
        total = query.count()

        # Projects by status
        status_counts = (
            query.with_entities(
                InstallationProject.project_status, func.count(InstallationProject.id)
            )
            .group_by(InstallationProject.project_status)
            .all()
        )

        # Projects by type
        type_counts = (
            query.with_entities(
                InstallationProject.project_type, func.count(InstallationProject.id)
            )
            .group_by(InstallationProject.project_type)
            .all()
        )

        # Overdue count
        overdue_count = query.filter(
            and_(
                InstallationProject.planned_end_date < date.today(),
                InstallationProject.project_status.in_(
                    [
                        ProjectStatus.IN_PROGRESS,
                        ProjectStatus.SCHEDULED,
                        ProjectStatus.TESTING,
                    ]
                ),
            )
        ).count()

        # Average completion percentage
        avg_completion = (
            query.with_entities(
                func.avg(InstallationProject.completion_percentage)
            ).scalar()
            or 0
        )

        return {
            "total_projects": total,
            "overdue_projects": overdue_count,
            "average_completion": float(avg_completion),
            "projects_by_status": {
                status.value: count for status, count in status_counts
            },
            "projects_by_type": {ptype.value: count for ptype, count in type_counts},
        }

    def update(
        self, project: InstallationProject, update_data: Dict[str, Any]
    ) -> InstallationProject:
        """Update project."""
        for field, value in update_data.items():
            if hasattr(project, field):
                setattr(project, field, value)

        project.updated_at = datetime.utcnow()
        self.db.flush()
        return project

    def delete(self, project: InstallationProject):
        """Soft delete project."""
        project.is_deleted = True
        project.deleted_at = datetime.utcnow()
        self.db.flush()


class ProjectPhaseRepository:
    """Repository for project phase data operations."""

    def __init__(self, db: Session):
        """  Init   operation."""
        self.db = db

    def create(self, phase_data: Dict[str, Any]) -> ProjectPhase:
        """Create a new project phase."""
        phase = ProjectPhase(**phase_data)
        self.db.add(phase)
        self.db.flush()
        return phase

    def get_by_id(
        self, phase_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[ProjectPhase]:
        """Get phase by ID."""
        query = self.db.query(ProjectPhase).filter(ProjectPhase.id == phase_id)
        if tenant_id:
            query = query.filter(ProjectPhase.tenant_id == tenant_id)
        return query.first()

    def list_by_project(
        self,
        project_id: UUID,
        tenant_id: Optional[UUID] = None,
        customer_facing_only: bool = False,
    ) -> List[ProjectPhase]:
        """List phases for a project."""
        query = self.db.query(ProjectPhase).filter(
            ProjectPhase.project_id == project_id
        )

        if tenant_id:
            query = query.filter(ProjectPhase.tenant_id == tenant_id)

        if customer_facing_only:
            query = query.filter(ProjectPhase.is_customer_facing == True)

        return query.order_by(ProjectPhase.phase_order).all()

    def list_by_status(
        self,
        status: PhaseStatus,
        tenant_id: Optional[UUID] = None,
        assigned_technician: Optional[str] = None,
    ) -> List[ProjectPhase]:
        """List phases by status."""
        query = self.db.query(ProjectPhase).filter(ProjectPhase.phase_status == status)

        if tenant_id:
            query = query.filter(ProjectPhase.tenant_id == tenant_id)

        if assigned_technician:
            query = query.filter(
                ProjectPhase.assigned_technician == assigned_technician
            )

        return query.order_by(ProjectPhase.planned_start_date).all()

    def list_overdue(self, tenant_id: Optional[UUID] = None) -> List[ProjectPhase]:
        """List overdue phases."""
        query = self.db.query(ProjectPhase).filter(
            and_(
                ProjectPhase.planned_end_date < date.today(),
                ProjectPhase.phase_status.in_(
                    [PhaseStatus.SCHEDULED, PhaseStatus.IN_PROGRESS]
                ),
            )
        )

        if tenant_id:
            query = query.filter(ProjectPhase.tenant_id == tenant_id)

        return query.order_by(asc(ProjectPhase.planned_end_date)).all()

    def get_completed_count_for_project(self, project_id: UUID) -> int:
        """Get count of completed phases for a project."""
        return (
            self.db.query(ProjectPhase)
            .filter(
                and_(
                    ProjectPhase.project_id == project_id,
                    ProjectPhase.phase_status == PhaseStatus.COMPLETED,
                )
            )
            .count()
        )

    def update(self, phase: ProjectPhase, update_data: Dict[str, Any]) -> ProjectPhase:
        """Update phase."""
        for field, value in update_data.items():
            if hasattr(phase, field):
                setattr(phase, field, value)

        phase.updated_at = datetime.utcnow()
        self.db.flush()
        return phase


class ProjectMilestoneRepository:
    """Repository for project milestone data operations."""

    def __init__(self, db: Session):
        """  Init   operation."""
        self.db = db

    def create(self, milestone_data: Dict[str, Any]) -> ProjectMilestone:
        """Create a new project milestone."""
        milestone = ProjectMilestone(**milestone_data)
        self.db.add(milestone)
        self.db.flush()
        return milestone

    def get_by_id(
        self, milestone_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[ProjectMilestone]:
        """Get milestone by ID."""
        query = self.db.query(ProjectMilestone).filter(
            ProjectMilestone.id == milestone_id
        )
        if tenant_id:
            query = query.filter(ProjectMilestone.tenant_id == tenant_id)
        return query.first()

    def list_by_project(
        self,
        project_id: UUID,
        tenant_id: Optional[UUID] = None,
        customer_visible_only: bool = False,
    ) -> List[ProjectMilestone]:
        """List milestones for a project."""
        query = self.db.query(ProjectMilestone).filter(
            ProjectMilestone.project_id == project_id
        )

        if tenant_id:
            query = query.filter(ProjectMilestone.tenant_id == tenant_id)

        if customer_visible_only:
            query = query.filter(ProjectMilestone.is_customer_visible == True)

        return query.order_by(ProjectMilestone.planned_date).all()

    def list_upcoming(
        self,
        tenant_id: Optional[UUID] = None,
        days_ahead: int = 7,
        customer_id: Optional[UUID] = None,
    ) -> List[ProjectMilestone]:
        """List upcoming milestones."""
        end_date = date.today() + timedelta(days=days_ahead)

        query = self.db.query(ProjectMilestone).filter(
            and_(
                ProjectMilestone.planned_date >= date.today(),
                ProjectMilestone.planned_date <= end_date,
                ProjectMilestone.is_completed == False,
            )
        )

        if tenant_id:
            query = query.filter(ProjectMilestone.tenant_id == tenant_id)

        if customer_id:
            query = query.join(InstallationProject).filter(
                InstallationProject.customer_id == customer_id
            )

        return query.order_by(ProjectMilestone.planned_date).all()

    def list_overdue(self, tenant_id: Optional[UUID] = None) -> List[ProjectMilestone]:
        """List overdue milestones."""
        query = self.db.query(ProjectMilestone).filter(
            and_(
                ProjectMilestone.planned_date < date.today(),
                ProjectMilestone.is_completed == False,
            )
        )

        if tenant_id:
            query = query.filter(ProjectMilestone.tenant_id == tenant_id)

        return query.order_by(asc(ProjectMilestone.planned_date)).all()

    def get_next_milestone_for_project(
        self, project_id: UUID
    ) -> Optional[ProjectMilestone]:
        """Get next incomplete milestone for a project."""
        return (
            self.db.query(ProjectMilestone)
            .filter(
                and_(
                    ProjectMilestone.project_id == project_id,
                    ProjectMilestone.is_completed == False,
                    ProjectMilestone.planned_date >= date.today(),
                )
            )
            .order_by(ProjectMilestone.planned_date)
            .first()
        )

    def mark_completed(
        self, milestone: ProjectMilestone, completion_notes: Optional[str] = None
    ):
        """Mark milestone as completed."""
        milestone.is_completed = True
        milestone.actual_date = date.today()
        if completion_notes:
            milestone.completion_notes = completion_notes
        milestone.updated_at = datetime.utcnow()
        self.db.flush()


class ProjectUpdateRepository:
    """Repository for project update data operations."""

    def __init__(self, db: Session):
        """  Init   operation."""
        self.db = db

    def create(self, update_data: Dict[str, Any]) -> ProjectUpdate:
        """Create a new project update."""
        update = ProjectUpdate(**update_data)
        self.db.add(update)
        self.db.flush()
        return update

    def get_by_id(
        self, update_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[ProjectUpdate]:
        """Get update by ID."""
        query = self.db.query(ProjectUpdate).filter(ProjectUpdate.id == update_id)
        if tenant_id:
            query = query.filter(ProjectUpdate.tenant_id == tenant_id)
        return query.first()

    def list_by_project(
        self,
        project_id: UUID,
        tenant_id: Optional[UUID] = None,
        customer_visible_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ProjectUpdate]:
        """List updates for a project."""
        query = self.db.query(ProjectUpdate).filter(
            ProjectUpdate.project_id == project_id
        )

        if tenant_id:
            query = query.filter(ProjectUpdate.tenant_id == tenant_id)

        if customer_visible_only:
            query = query.filter(ProjectUpdate.is_customer_visible == True)

        return (
            query.order_by(desc(ProjectUpdate.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_latest_for_project(
        self, project_id: UUID, customer_visible_only: bool = False
    ) -> Optional[ProjectUpdate]:
        """Get latest update for a project."""
        query = self.db.query(ProjectUpdate).filter(
            ProjectUpdate.project_id == project_id
        )

        if customer_visible_only:
            query = query.filter(ProjectUpdate.is_customer_visible == True)

        return query.order_by(desc(ProjectUpdate.created_at)).first()

    def list_recent(
        self,
        tenant_id: Optional[UUID] = None,
        customer_id: Optional[UUID] = None,
        days: int = 7,
        limit: int = 50,
    ) -> List[ProjectUpdate]:
        """List recent updates."""
        since_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(ProjectUpdate).filter(
            ProjectUpdate.created_at >= since_date
        )

        if tenant_id:
            query = query.filter(ProjectUpdate.tenant_id == tenant_id)

        if customer_id:
            query = query.join(InstallationProject).filter(
                InstallationProject.customer_id == customer_id
            )

        return query.order_by(desc(ProjectUpdate.created_at)).limit(limit).all()

    def mark_customer_notified(self, update: ProjectUpdate):
        """Mark update as customer notified."""
        update.customer_notified = True
        update.notification_sent_at = datetime.utcnow()
        self.db.flush()
