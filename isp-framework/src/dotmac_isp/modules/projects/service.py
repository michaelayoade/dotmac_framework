import logging

logger = logging.getLogger(__name__)

"""Installation Project Management Services."""

import secrets
import string
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from fastapi import HTTPException
from ..notifications.models import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel
, timezone)

from dotmac_isp.core.database import get_db
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
from .schemas import (
    InstallationProjectCreate,
    InstallationProjectUpdate,
    InstallationProjectResponse,
    ProjectPhaseCreate,
    ProjectPhaseUpdate,
    ProjectUpdateCreate,
    CustomerProjectSummary,
    ProjectTimelineResponse,
)


class InstallationProjectService:
    """Service for managing installation projects."""

    def __init__(self, db: Session):
        self.db = db

    def generate_project_number(self) -> str:
        """Generate unique project number."""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_chars = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
        )
        return f"PROJ-{timestamp}-{random_chars}"

    async def create_project_from_opportunity(
        self,
        opportunity_id: UUID,
        customer_id: UUID,
        project_data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> InstallationProject:
        """Create installation project from completed sales opportunity."""

        # Generate project number
        project_number = self.generate_project_number()

        # Create project
        project = InstallationProject(
            id=uuid4(),
            tenant_id=project_data.get("tenant_id"),
            project_number=project_number,
            project_name=project_data.get(
                "project_name", f"Installation for Customer {customer_id}"
            ),
            description=project_data.get("description"),
            project_type=ProjectType(
                project_data.get("project_type", ProjectType.NEW_INSTALLATION)
            ),
            customer_id=customer_id,
            opportunity_id=opportunity_id,
            service_id=project_data.get("service_id"),
            sales_owner=project_data.get("sales_owner"),
            project_manager=project_data.get("project_manager"),
            priority=project_data.get("priority", "normal"),
            requested_date=project_data.get("requested_date"),
            planned_start_date=project_data.get("planned_start_date"),
            planned_end_date=project_data.get("planned_end_date"),
            estimated_cost=project_data.get("estimated_cost"),
            service_requirements=project_data.get("service_requirements"),
            technical_specifications=project_data.get("technical_specifications"),
            equipment_list=project_data.get("equipment_list"),
            customer_contact_name=project_data.get("customer_contact_name"),
            customer_contact_phone=project_data.get("customer_contact_phone"),
            customer_contact_email=project_data.get("customer_contact_email"),
            preferred_contact_method=project_data.get(
                "preferred_contact_method", "phone"
            ),
            street_address=project_data.get("street_address"),
            city=project_data.get("city"),
            state_province=project_data.get("state_province"),
            postal_code=project_data.get("postal_code"),
            country_code=project_data.get("country_code", "US"),
            site_access_instructions=project_data.get("site_access_instructions"),
            permits_required=project_data.get("permits_required"),
            created_by=created_by,
        )

        self.db.add(project)
        self.db.flush()  # Get the ID

        # Create default project phases
        await self._create_default_phases(project.id, project.project_type)

        # Create default milestones
        await self._create_default_milestones(project.id, project.project_type)

        # Create initial project update
        initial_update = ProjectUpdate(
            id=uuid4(),
            tenant_id=project.tenant_id,
            project_id=project.id,
            update_title="Project Created",
            update_content=f"Installation project {project.project_number} has been created and is ready for scheduling.",
            update_type="project_created",
            author_name=created_by or "System",
            author_role="system",
            is_customer_visible=True,
            progress_percentage=0,
        )

        self.db.add(initial_update)
        self.db.commit()
        self.db.refresh(project)

        return project

    async def _create_default_phases(self, project_id: UUID, project_type: ProjectType):
        """Create default phases based on project type."""

        phase_templates = {
            ProjectType.NEW_INSTALLATION: [
                {
                    "phase_name": "Site Survey",
                    "phase_description": "Initial site assessment and requirements gathering",
                    "phase_order": 1,
                    "phase_type": "survey",
                    "is_critical_path": True,
                    "estimated_duration_hours": 2.0,
                    "notify_customer_on_start": True,
                    "notify_customer_on_completion": True,
                },
                {
                    "phase_name": "Permits and Approvals",
                    "phase_description": "Obtain necessary permits and regulatory approvals",
                    "phase_order": 2,
                    "phase_type": "permits",
                    "is_critical_path": True,
                    "estimated_duration_hours": 8.0,
                    "is_customer_facing": False,
                },
                {
                    "phase_name": "Equipment Procurement",
                    "phase_description": "Order and receive required equipment and materials",
                    "phase_order": 3,
                    "phase_type": "procurement",
                    "is_critical_path": True,
                    "estimated_duration_hours": 4.0,
                    "is_customer_facing": False,
                },
                {
                    "phase_name": "Installation Preparation",
                    "phase_description": "Prepare installation site and stage equipment",
                    "phase_order": 4,
                    "phase_type": "preparation",
                    "is_critical_path": True,
                    "estimated_duration_hours": 4.0,
                    "notify_customer_on_start": True,
                },
                {
                    "phase_name": "Equipment Installation",
                    "phase_description": "Install and configure customer equipment",
                    "phase_order": 5,
                    "phase_type": "installation",
                    "is_critical_path": True,
                    "estimated_duration_hours": 6.0,
                    "notify_customer_on_start": True,
                    "notify_customer_on_completion": True,
                },
                {
                    "phase_name": "Service Testing",
                    "phase_description": "Test service functionality and performance",
                    "phase_order": 6,
                    "phase_type": "testing",
                    "is_critical_path": True,
                    "estimated_duration_hours": 2.0,
                    "notify_customer_on_completion": True,
                },
                {
                    "phase_name": "Customer Training",
                    "phase_description": "Train customer on service usage and features",
                    "phase_order": 7,
                    "phase_type": "training",
                    "is_critical_path": False,
                    "estimated_duration_hours": 1.0,
                    "notify_customer_on_start": True,
                },
                {
                    "phase_name": "Service Activation",
                    "phase_description": "Activate service and complete installation",
                    "phase_order": 8,
                    "phase_type": "activation",
                    "is_critical_path": True,
                    "estimated_duration_hours": 1.0,
                    "notify_customer_on_completion": True,
                },
            ],
            ProjectType.SERVICE_UPGRADE: [
                {
                    "phase_name": "Service Assessment",
                    "phase_description": "Assess current service and upgrade requirements",
                    "phase_order": 1,
                    "phase_type": "assessment",
                    "is_critical_path": True,
                    "estimated_duration_hours": 1.0,
                },
                {
                    "phase_name": "Equipment Upgrade",
                    "phase_description": "Upgrade customer equipment",
                    "phase_order": 2,
                    "phase_type": "installation",
                    "is_critical_path": True,
                    "estimated_duration_hours": 3.0,
                    "notify_customer_on_start": True,
                },
                {
                    "phase_name": "Service Testing",
                    "phase_description": "Test upgraded service functionality",
                    "phase_order": 3,
                    "phase_type": "testing",
                    "is_critical_path": True,
                    "estimated_duration_hours": 1.0,
                },
                {
                    "phase_name": "Service Activation",
                    "phase_description": "Activate upgraded service",
                    "phase_order": 4,
                    "phase_type": "activation",
                    "is_critical_path": True,
                    "estimated_duration_hours": 0.5,
                    "notify_customer_on_completion": True,
                },
            ],
        }

        phases_to_create = phase_templates.get(
            project_type, phase_templates[ProjectType.NEW_INSTALLATION]
        )

        for phase_data in phases_to_create:
            phase = ProjectPhase(
                id=uuid4(),
                tenant_id=await self._get_project_tenant_id(project_id),
                project_id=project_id,
                **phase_data,
            )
            self.db.add(phase)

        # Update project total phases count
        project = (
            self.db.query(InstallationProject)
            .filter(InstallationProject.id == project_id)
            .first()
        )
        if project:
            project.total_phases = len(phases_to_create)

    async def _create_default_milestones(
        self, project_id: UUID, project_type: ProjectType
    ):
        """Create default milestones based on project type."""

        milestone_templates = {
            ProjectType.NEW_INSTALLATION: [
                {
                    "milestone_name": "Site Survey Complete",
                    "milestone_type": MilestoneType.SITE_SURVEY,
                    "days_offset": 1,
                    "is_critical": True,
                },
                {
                    "milestone_name": "Equipment Delivered",
                    "milestone_type": MilestoneType.EQUIPMENT_DELIVERED,
                    "days_offset": 7,
                    "is_critical": True,
                },
                {
                    "milestone_name": "Installation Started",
                    "milestone_type": MilestoneType.INSTALLATION_STARTED,
                    "days_offset": 10,
                    "is_critical": True,
                },
                {
                    "milestone_name": "Service Activated",
                    "milestone_type": MilestoneType.SERVICE_ACTIVATED,
                    "days_offset": 14,
                    "is_critical": True,
                },
                {
                    "milestone_name": "Project Completed",
                    "milestone_type": MilestoneType.PROJECT_COMPLETED,
                    "days_offset": 15,
                    "is_critical": True,
                },
            ]
        }

        milestones_to_create = milestone_templates.get(
            project_type, milestone_templates[ProjectType.NEW_INSTALLATION]
        )
        base_date = date.today()

        for milestone_data in milestones_to_create:
            planned_date = base_date + timedelta(days=milestone_data["days_offset"])

            milestone = ProjectMilestone(
                id=uuid4(),
                tenant_id=await self._get_project_tenant_id(project_id),
                project_id=project_id,
                milestone_name=milestone_data["milestone_name"],
                milestone_type=milestone_data["milestone_type"],
                planned_date=planned_date,
                is_critical=milestone_data["is_critical"],
                is_customer_visible=True,
            )
            self.db.add(milestone)

    async def _get_project_tenant_id(self, project_id: UUID) -> UUID:
        """Get tenant ID for a project."""
        project = (
            self.db.query(InstallationProject)
            .filter(InstallationProject.id == project_id)
            .first()
        )
        return project.tenant_id if project else None

    async def update_project_progress(
        self, project_id: UUID, phase_id: Optional[UUID] = None
    ):
        """Update project completion percentage based on completed phases."""
        project = (
            self.db.query(InstallationProject)
            .filter(InstallationProject.id == project_id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Count completed phases
        completed_phases = (
            self.db.query(ProjectPhase)
            .filter(
                and_(
                    ProjectPhase.project_id == project_id,
                    ProjectPhase.phase_status == PhaseStatus.COMPLETED,
                )
            )
            .count()
        )

        project.phases_completed = completed_phases
        project.calculate_completion_percentage()

        # Update project status based on progress
        if project.completion_percentage == 100:
            project.project_status = ProjectStatus.COMPLETED
            project.actual_end_date = date.today()
        elif (
            project.completion_percentage > 0
            and project.project_status == ProjectStatus.PLANNING
        ):
            project.project_status = ProjectStatus.IN_PROGRESS
            if not project.actual_start_date:
                project.actual_start_date = date.today()

        self.db.commit()
        return project

    async def get_customer_projects(
        self,
        customer_id: UUID,
        status_filter: Optional[ProjectStatus] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> List[CustomerProjectSummary]:
        """Get projects for customer portal display."""

        query = self.db.query(InstallationProject).filter(
            InstallationProject.customer_id == customer_id
        )

        if status_filter:
            query = query.filter(InstallationProject.project_status == status_filter)

        projects = (
            query.order_by(desc(InstallationProject.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

        project_summaries = []
        for project in projects:
            # Get next milestone
            next_milestone = (
                self.db.query(ProjectMilestone)
                .filter(
                    and_(
                        ProjectMilestone.project_id == project.id,
                        ProjectMilestone.is_completed == False,
                        ProjectMilestone.is_customer_visible == True,
                    )
                )
                .order_by(ProjectMilestone.planned_date)
                .first()
            )

            # Get last update
            last_update = (
                self.db.query(ProjectUpdate)
                .filter(
                    and_(
                        ProjectUpdate.project_id == project.id,
                        ProjectUpdate.is_customer_visible == True,
                    )
                )
                .order_by(desc(ProjectUpdate.created_at)
                .first()
            )

            # Estimate completion date
            estimated_completion = None
            if project.planned_end_date:
                estimated_completion = project.planned_end_date
            elif next_milestone:
                estimated_completion = next_milestone.planned_date

            summary = CustomerProjectSummary(
                id=project.id,
                project_number=project.project_number,
                project_name=project.project_name,
                project_type=project.project_type,
                project_status=project.project_status,
                priority=project.priority,
                completion_percentage=project.completion_percentage,
                planned_start_date=project.planned_start_date,
                planned_end_date=project.planned_end_date,
                actual_start_date=project.actual_start_date,
                estimated_completion=estimated_completion,
                lead_technician=project.lead_technician,
                is_overdue=project.is_overdue,
                days_remaining=project.days_remaining,
                next_milestone=(
                    next_milestone.milestone_name if next_milestone else None
                ),
                last_update=last_update.update_title if last_update else None,
                can_reschedule=project.project_status
                in [ProjectStatus.PLANNING, ProjectStatus.SCHEDULED],
            )

            project_summaries.append(summary)

        return project_summaries

    async def get_project_timeline(
        self, project_id: UUID, customer_id: Optional[UUID] = None
    ) -> ProjectTimelineResponse:
        """Get detailed project timeline for customer or internal view."""

        project = (
            self.db.query(InstallationProject)
            .filter(InstallationProject.id == project_id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify customer access
        if customer_id and project.customer_id != customer_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get phases (filter to customer-facing if customer view)
        phases_query = self.db.query(ProjectPhase).filter(
            ProjectPhase.project_id == project_id
        )
        if customer_id:
            phases_query = phases_query.filter(ProjectPhase.is_customer_facing == True)
        phases = phases_query.order_by(ProjectPhase.phase_order).all()

        # Get milestones (filter to customer-visible if customer view)
        milestones_query = self.db.query(ProjectMilestone).filter(
            ProjectMilestone.project_id == project_id
        )
        if customer_id:
            milestones_query = milestones_query.filter(
                ProjectMilestone.is_customer_visible == True
            )
        milestones = milestones_query.order_by(ProjectMilestone.planned_date).all()

        # Get recent updates (filter to customer-visible if customer view)
        updates_query = self.db.query(ProjectUpdate).filter(
            ProjectUpdate.project_id == project_id
        )
        if customer_id:
            updates_query = updates_query.filter(
                ProjectUpdate.is_customer_visible == True
            )
        updates = updates_query.order_by(desc(ProjectUpdate.created_at).limit(10).all()

        return ProjectTimelineResponse(
            project=InstallationProjectResponse.from_orm(project),
            phases=[ProjectPhaseResponse.from_orm(phase) for phase in phases],
            milestones=[
                ProjectMilestoneResponse.from_orm(milestone) for milestone in milestones
            ],
            recent_updates=[
                ProjectUpdateResponse.from_orm(update) for update in updates
            ],
            upcoming_appointments=[],  # Field ops integration - would connect to field_ops module
        )


class ProjectWorkflowService:
    """Service for managing project workflow and integrations."""

    def __init__(self, db: Session):
        self.db = db
        self.project_service = InstallationProjectService(db)

    async def convert_opportunity_to_project(
        self,
        opportunity_id: UUID,
        customer_id: UUID,
        project_data: Dict[str, Any],
        sales_owner: str,
    ) -> InstallationProject:
        """Convert completed sales opportunity to installation project."""

        # Update project data with sales context
        project_data.update({"sales_owner": sales_owner, "created_by": sales_owner})

        # Create the project
        project = await self.project_service.create_project_from_opportunity(
            opportunity_id=opportunity_id,
            customer_id=customer_id,
            project_data=project_data,
            created_by=sales_owner,
        )

        # Trigger notifications for project creation
        await self._notify_project_created(project)

        # Update sales opportunity status
        await self._update_opportunity_status(opportunity_id, "converted_to_project")

        return project

    async def _notify_project_created(self, project: InstallationProject):
        """Send notifications when project is created."""
        try:
            # Create notification for project creation
            notification = Notification(
                id=uuid4(),
                tenant_id=project.tenant_id,
                notification_type=NotificationType.PROJECT_UPDATE,
                channel=NotificationChannel.EMAIL,
                priority=NotificationPriority.HIGH,
                recipient_type="user",
                recipient_identifier=project.project_manager or "project_team",
                subject=f"New Project Created: {project.project_name}",
                content=f"Project {project.project_number} has been created and is ready for execution",
                template_data={
                    "project_id": str(project.id),
                    "project_number": project.project_number,
                    "project_name": project.project_name,
                    "customer_id": str(project.customer_id)
                },
                status=NotificationStatus.PENDING,
                scheduled_for=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(notification)
            self.db.commit()
        except Exception as e:
logger.info(f"Failed to create project notification: {e}")

    async def _update_opportunity_status(self, opportunity_id: UUID, status: str):
        """Update sales opportunity status."""
        try:
            # Import here to avoid circular imports
            from ..sales.models import Opportunity, OpportunityStatus
            
            # Update the opportunity status
            opportunity = self.db.query(Opportunity).filter(
                Opportunity.id == opportunity_id
            ).first()
            
            if opportunity:
                if status == "converted_to_project":
                    opportunity.opportunity_status = OpportunityStatus.WON
                    opportunity.updated_at = datetime.now(timezone.utc)
                    self.db.commit()
logger.info(f"Updated opportunity {opportunity_id} status to WON")
        except ImportError:
logger.info(f"Sales module not available for opportunity update: {opportunity_id}")
        except Exception as e:
logger.info(f"Failed to update opportunity status: {e}")
