import logging

logger = logging.getLogger(__name__)

"""Installation Project Management API endpoints."""

from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant, get_current_user_from_token
from ..notifications.models import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel
)

from uuid import uuid4
from .models import (
    InstallationProject,
    ProjectPhase,
    ProjectMilestone,
    ProjectUpdate,
    ProjectType,
    ProjectStatus,
    PhaseStatus,
)
from .schemas import (
    InstallationProjectCreate,
    InstallationProjectUpdate,
    InstallationProjectResponse,
    ProjectPhaseCreate,
    ProjectPhaseUpdate,
    ProjectPhaseResponse,
    ProjectUpdateCreate,
    ProjectUpdateResponse,
    CustomerProjectSummary,
    ProjectTimelineResponse,
    ProjectDashboardResponse,
    ProjectNotificationRequest,
)
from .service import InstallationProjectService, ProjectWorkflowService

router = APIRouter(prefix="/projects", tags=["installation-projects"])


async def get_project_service(
    db: Session = Depends(get_db),
) -> InstallationProjectService:
    """Get project service instance."""
    return InstallationProjectService(db)


async def get_workflow_service(db: Session = Depends(get_db)) -> ProjectWorkflowService:
    """Get workflow service instance."""
    return ProjectWorkflowService(db)


# Project Management Endpoints


@router.post("/", response_model=InstallationProjectResponse)
async def create_project(
    project_data: InstallationProjectCreate,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Create a new installation project."""

    project_dict = project_data.model_dump()
    project_dict["tenant_id"] = tenant_id

    project = await service.create_project_from_opportunity(
        opportunity_id=project_data.opportunity_id,
        customer_id=project_data.customer_id,
        project_data=project_dict,
        created_by=current_user.username,
    )

    return InstallationProjectResponse.from_orm(project)


@router.get("/", response_model=List[InstallationProjectResponse])
async def list_projects(
    status: Optional[ProjectStatus] = None,
    project_type: Optional[ProjectType] = None,
    customer_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """List installation projects with filtering."""

    query = service.db.query(InstallationProject).filter(
        InstallationProject.tenant_id == tenant_id
    )

    if status:
        query = query.filter(InstallationProject.project_status == status)

    if project_type:
        query = query.filter(InstallationProject.project_type == project_type)

    if customer_id:
        query = query.filter(InstallationProject.customer_id == customer_id)

    projects = (
        query.order_by(desc(InstallationProject.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [InstallationProjectResponse.from_orm(project) for project in projects]


@router.get("/{project_id}", response_model=InstallationProjectResponse)
async def get_project(
    project_id: UUID,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get installation project by ID."""

    project = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.id == project_id,
                InstallationProject.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return InstallationProjectResponse.from_orm(project)


@router.put("/{project_id}", response_model=InstallationProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: InstallationProjectUpdate,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update installation project."""

    project = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.id == project_id,
                InstallationProject.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(project, field):
            setattr(project, field, value)

    project.updated_at = datetime.now(timezone.utc)
    service.db.commit()
    service.db.refresh(project)

    # Update progress if completion percentage changed
    if "completion_percentage" in update_data:
        await service.update_project_progress(project_id)

    return InstallationProjectResponse.from_orm(project)


@router.get("/{project_id}/timeline", response_model=ProjectTimelineResponse)
async def get_project_timeline(
    project_id: UUID,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get detailed project timeline with phases and milestones."""

    return await service.get_project_timeline(project_id)


# Project Phases


@router.get("/{project_id}/phases", response_model=List[ProjectPhaseResponse])
async def list_project_phases(
    project_id: UUID,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """List project phases."""

    phases = (
        service.db.query(ProjectPhase)
        .filter(
            and_(
                ProjectPhase.project_id == project_id,
                ProjectPhase.tenant_id == tenant_id,
            )
        )
        .order_by(ProjectPhase.phase_order)
        .all()
    )

    return [ProjectPhaseResponse.from_orm(phase) for phase in phases]


@router.put("/{project_id}/phases/{phase_id}", response_model=ProjectPhaseResponse)
async def update_project_phase(
    project_id: UUID,
    phase_id: UUID,
    phase_update: ProjectPhaseUpdate,
    background_tasks: BackgroundTasks,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update project phase status and details."""

    phase = (
        service.db.query(ProjectPhase)
        .filter(
            and_(
                ProjectPhase.id == phase_id,
                ProjectPhase.project_id == project_id,
                ProjectPhase.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not phase:
        raise HTTPException(status_code=404, detail="Project phase not found")

    # Track status changes for notifications
    old_status = phase.phase_status

    # Update fields
    update_data = phase_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(phase, field):
            setattr(phase, field, value)

    # Set completion timestamp
    if (
        phase_update.phase_status == PhaseStatus.COMPLETED
        and old_status != PhaseStatus.COMPLETED
    ):
        phase.actual_end_date = date.today()
        phase.completion_percentage = 100
    elif (
        phase_update.phase_status == PhaseStatus.IN_PROGRESS
        and old_status != PhaseStatus.IN_PROGRESS
    ):
        phase.actual_start_date = date.today()

    service.db.commit()
    service.db.refresh(phase)

    # Update project progress
    await service.update_project_progress(project_id, phase_id)

    # Schedule notifications
    if old_status != phase.phase_status:
        background_tasks.add_task(
            notify_phase_status_change,
            project_id=project_id,
            phase_id=phase_id,
            old_status=old_status,
            new_status=phase.phase_status,
        )

    return ProjectPhaseResponse.from_orm(phase)


# Project Updates


@router.get("/{project_id}/updates", response_model=List[ProjectUpdateResponse])
async def list_project_updates(
    project_id: UUID,
    customer_visible_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """List project updates."""

    query = service.db.query(ProjectUpdate).filter(
        and_(
            ProjectUpdate.project_id == project_id, ProjectUpdate.tenant_id == tenant_id
        )
    )

    if customer_visible_only:
        query = query.filter(ProjectUpdate.is_customer_visible == True)

    updates = (
        query.order_by(desc(ProjectUpdate.created_at)).offset(skip).limit(limit).all()
    )

    return [ProjectUpdateResponse.from_orm(update) for update in updates]


@router.post("/{project_id}/updates", response_model=ProjectUpdateResponse)
async def create_project_update(
    project_id: UUID,
    update_data: ProjectUpdateCreate,
    background_tasks: BackgroundTasks,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Create a new project update."""

    # Verify project exists
    project = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.id == project_id,
                InstallationProject.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create update
    update = ProjectUpdate(
        id=UUID(),
        tenant_id=tenant_id,
        project_id=project_id,
        **update_data.model_dump(),
        created_by=current_user.username,
    )

    service.db.add(update)
    service.db.commit()
    service.db.refresh(update)

    # Schedule customer notification if visible
    if update.is_customer_visible:
        background_tasks.add_task(
            notify_customer_project_update, project_id=project_id, update_id=update.id
        )

    return ProjectUpdateResponse.from_orm(update)


# Sales Integration


@router.post("/from-opportunity", response_model=InstallationProjectResponse)
async def create_project_from_opportunity(
    opportunity_id: UUID,
    customer_id: UUID,
    project_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    workflow_service: ProjectWorkflowService = Depends(get_workflow_service),
    tenant_id: str = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Create installation project from completed sales opportunity."""

    project_data["tenant_id"] = tenant_id

    project = await workflow_service.convert_opportunity_to_project(
        opportunity_id=opportunity_id,
        customer_id=customer_id,
        project_data=project_data,
        sales_owner=current_user.username,
    )

    # Schedule project creation notifications
    background_tasks.add_task(
        notify_project_created,
        project_id=project.id,
        recipients=["customer", "project_manager", "sales_owner"],
    )

    return InstallationProjectResponse.from_orm(project)


# Customer Portal Endpoints


@router.get("/customer/{customer_id}", response_model=List[CustomerProjectSummary])
async def get_customer_projects(
    customer_id: UUID,
    status: Optional[ProjectStatus] = None,
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get projects for customer portal display."""

    return await service.get_customer_projects(
        customer_id=customer_id, status_filter=status, limit=limit, skip=skip
    )


@router.get(
    "/customer/{customer_id}/{project_id}/timeline",
    response_model=ProjectTimelineResponse,
)
async def get_customer_project_timeline(
    customer_id: UUID,
    project_id: UUID,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get project timeline for customer portal."""

    return await service.get_project_timeline(project_id, customer_id)


# Dashboard and Analytics


@router.get("/dashboard/stats", response_model=ProjectDashboardResponse)
async def get_project_dashboard(
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get project dashboard statistics."""

    # Total projects
    total_projects = (
        service.db.query(InstallationProject)
        .filter(InstallationProject.tenant_id == tenant_id)
        .count()
    )

    # Active projects
    active_projects = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.tenant_id == tenant_id,
                InstallationProject.project_status.in_(
                    [
                        ProjectStatus.IN_PROGRESS,
                        ProjectStatus.SCHEDULED,
                        ProjectStatus.TESTING,
                    ]
                ),
            )
        )
        .count()
    )

    # Completed projects
    completed_projects = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.tenant_id == tenant_id,
                InstallationProject.project_status == ProjectStatus.COMPLETED,
            )
        )
        .count()
    )

    # Overdue projects
    overdue_projects = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.tenant_id == tenant_id,
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
        .count()
    )

    # Projects by status
    status_counts = (
        service.db.query(
            InstallationProject.project_status, func.count(InstallationProject.id)
        )
        .filter(InstallationProject.tenant_id == tenant_id)
        .group_by(InstallationProject.project_status)
        .all()
    )

    projects_by_status = {status.value: count for status, count in status_counts}

    # Projects by type
    type_counts = (
        service.db.query(
            InstallationProject.project_type, func.count(InstallationProject.id)
        )
        .filter(InstallationProject.tenant_id == tenant_id)
        .group_by(InstallationProject.project_type)
        .all()
    )

    projects_by_type = {ptype.value: count for ptype, count in type_counts}

    # Calculate basic average completion time for completed projects
    completed_project_query = (service.db.query(InstallationProject)
        .filter(and_(
            InstallationProject.tenant_id == tenant_id,
            InstallationProject.project_status == ProjectStatus.COMPLETED
        )))
    completed_projects_list = completed_project_query.all()
    
    avg_completion_days = None
    if completed_projects_list:
        completion_times = []
        for project in completed_projects_list:
            if project.actual_end_date and project.actual_start_date:
                days = (project.actual_end_date - project.actual_start_date).days
                completion_times.append(days)
        
        if completion_times:
            avg_completion_days = sum(completion_times) / len(completion_times)
    
    # Basic customer satisfaction placeholder - would integrate with feedback system
    customer_satisfaction = 4.2  # Placeholder value

    return ProjectDashboardResponse(
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        overdue_projects=overdue_projects,
        projects_by_status=projects_by_status,
        projects_by_type=projects_by_type,
        average_completion_time=avg_completion_days,
        customer_satisfaction_average=customer_satisfaction,
        upcoming_milestones=[],
    )


# Notification Endpoints


@router.post("/{project_id}/notify", status_code=202)
async def send_project_notification(
    project_id: UUID,
    notification_request: ProjectNotificationRequest,
    background_tasks: BackgroundTasks,
    service: InstallationProjectService = Depends(get_project_service),
    tenant_id: str = Depends(get_current_tenant),
):
    """Send project notification to specified recipients."""

    # Verify project exists
    project = (
        service.db.query(InstallationProject)
        .filter(
            and_(
                InstallationProject.id == project_id,
                InstallationProject.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Schedule notification
    background_tasks.add_task(
        send_custom_project_notification,
        project_id=project_id,
        notification_type=notification_request.notification_type,
        recipients=notification_request.recipients,
        message=notification_request.message,
        include_details=notification_request.include_project_details,
    )

    return {"message": "Notification scheduled"}


# Background Task Functions


async def notify_phase_status_change(
    project_id: UUID, phase_id: UUID, old_status: PhaseStatus, new_status: PhaseStatus
):
    """Background task to notify phase status changes."""
    try:
        # Create notification for phase status change
        db = next(get_db())
        notification = Notification(
            id=uuid4(),
            tenant_id="default",  # Would get from context
            notification_type=NotificationType.PROJECT_UPDATE,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.MEDIUM,
            recipient_type="user",
            recipient_identifier="project_manager",
            subject=f"Project Phase Status Changed",
            content=f"Phase {phase_id} status changed from {old_status.value} to {new_status.value}",
            template_data={"project_id": str(project_id), "phase_id": str(phase_id)},
            status=NotificationStatus.PENDING,
            scheduled_for=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db.add(notification)
        db.commit()
    except Exception as e:
        logger.info(f"Failed to create phase change notification: {e}")


async def notify_customer_project_update(project_id: UUID, update_id: UUID):
    """Background task to notify customer of project updates."""
    try:
        # Create notification for customer project update
        db = next(get_db())
        notification = Notification(
            id=uuid4(),
            tenant_id="default",  # Would get from context
            notification_type=NotificationType.CUSTOMER_UPDATE,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.HIGH,
            recipient_type="customer",
            recipient_identifier="customer",
            subject=f"Project Update Notification",
            content=f"Your project {project_id} has been updated",
            template_data={"project_id": str(project_id), "update_id": str(update_id)},
            status=NotificationStatus.PENDING,
            scheduled_for=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db.add(notification)
        db.commit()
    except Exception as e:
        logger.info(f"Failed to create customer update notification: {e}")


async def notify_project_created(project_id: UUID, recipients: List[str]):
    """Background task to notify project creation."""
    try:
        # Create notifications for project creation
        db = next(get_db())
        for recipient in recipients:
            notification = Notification(
                id=uuid4(),
                tenant_id="default",  # Would get from context
                notification_type=NotificationType.PROJECT_UPDATE,
                channel=NotificationChannel.EMAIL,
                priority=NotificationPriority.HIGH,
                recipient_type="user",
                recipient_identifier=recipient,
                subject=f"New Project Created",
                content=f"Project {project_id} has been created and assigned",
                template_data={"project_id": str(project_id)},
                status=NotificationStatus.PENDING,
                scheduled_for=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            db.add(notification)
        db.commit()
    except Exception as e:
        logger.info(f"Failed to create project creation notifications: {e}")


async def send_custom_project_notification(
    project_id: UUID,
    notification_type: str,
    recipients: List[str],
    message: Optional[str] = None,
    include_details: bool = True,
):
    """Background task to send custom project notifications."""
    try:
        # Create custom project notifications
        db = next(get_db())
        for recipient in recipients:
            notification = Notification(
                id=uuid4(),
                tenant_id="default",  # Would get from context
                notification_type=NotificationType.PROJECT_UPDATE,
                channel=NotificationChannel.EMAIL,
                priority=NotificationPriority.MEDIUM,
                recipient_type="user",
                recipient_identifier=recipient,
                subject=f"Project Notification: {notification_type}",
                content=message or f"Custom notification for project {project_id}",
                template_data={
                    "project_id": str(project_id),
                    "include_details": include_details,
                    "notification_type": notification_type
                },
                status=NotificationStatus.PENDING,
                scheduled_for=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            db.add(notification)
        db.commit()
    except Exception as e:
        logger.info(f"Failed to create custom project notifications: {e}")
