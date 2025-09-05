"""
Project Workflow Management

Automated workflows for project lifecycle management, notifications,
and cross-system integrations.
"""

import asyncio
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (
    Project,
    ProjectMilestone,
    ProjectPhase,
    ProjectPriority,
    ProjectStatus,
    ProjectType,
)
from ..core.project_manager import ProjectManager
from ..services.project_service import ProjectService

logger = logging.getLogger(__name__)


class WorkflowTrigger(str, Enum):
    """Workflow trigger events."""

    PROJECT_CREATED = "project_created"
    PROJECT_STARTED = "project_started"
    PROJECT_COMPLETED = "project_completed"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    MILESTONE_REACHED = "milestone_reached"
    PROJECT_OVERDUE = "project_overdue"
    PHASE_OVERDUE = "phase_overdue"
    MILESTONE_OVERDUE = "milestone_overdue"
    STATUS_CHANGED = "status_changed"
    PRIORITY_ESCALATED = "priority_escalated"


class WorkflowAction(str, Enum):
    """Available workflow actions."""

    SEND_NOTIFICATION = "send_notification"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    ASSIGN_TEAM = "assign_team"
    UPDATE_STATUS = "update_status"
    CREATE_MILESTONE = "create_milestone"
    ESCALATE_PRIORITY = "escalate_priority"
    CREATE_FOLLOWUP_TASK = "create_followup_task"
    SEND_CLIENT_UPDATE = "send_client_update"


class WorkflowRule:
    """A workflow rule that defines trigger conditions and actions."""

    def __init__(
        self,
        name: str,
        trigger: WorkflowTrigger,
        conditions: Optional[dict[str, Any]] = None,
        actions: Optional[list[dict[str, Any]]] = None,
        enabled: bool = True,
    ):
        self.name = name
        self.trigger = trigger
        self.conditions = conditions or {}
        self.actions = actions or []
        self.enabled = enabled

    def matches(self, context: dict[str, Any]) -> bool:
        """Check if this rule matches the given context."""
        if not self.enabled:
            return False

        for condition_key, condition_value in self.conditions.items():
            context_value = context.get(condition_key)

            if isinstance(condition_value, list):
                if context_value not in condition_value:
                    return False
            elif condition_value != context_value:
                return False

        return True


class ProjectWorkflowManager:
    """Manages automated project workflows and business rules."""

    def __init__(
        self, project_manager: ProjectManager, project_service: ProjectService
    ):
        self.project_manager = project_manager
        self.project_service = project_service
        self.workflow_rules: list[WorkflowRule] = []
        self.action_handlers: dict[WorkflowAction, Callable] = {}

        # Register default action handlers
        self._register_default_handlers()

        # Load default workflow rules
        self._load_default_rules()

    def add_workflow_rule(self, rule: WorkflowRule):
        """Add a custom workflow rule."""
        self.workflow_rules.append(rule)
        logger.info(f"Added workflow rule: {rule.name}")

    def register_action_handler(self, action: WorkflowAction, handler: Callable):
        """Register a custom action handler."""
        self.action_handlers[action] = handler

    async def trigger_workflow(self, trigger: WorkflowTrigger, context: dict[str, Any]):
        """Trigger workflows based on an event."""
        try:
            # Find matching rules
            matching_rules = [
                rule
                for rule in self.workflow_rules
                if rule.trigger == trigger and rule.matches(context)
            ]

            if not matching_rules:
                return

            logger.info(
                f"Triggering {len(matching_rules)} workflow rules for {trigger}"
            )

            # Execute actions for matching rules
            for rule in matching_rules:
                await self._execute_rule_actions(rule, context)

        except Exception as e:
            logger.error(f"Error triggering workflow for {trigger}: {e}")

    async def process_project_created(self, db: AsyncSession, project: Project):
        """Process project creation workflows."""
        context = {
            "project_id": str(project.id),
            "project_type": project.project_type,
            "priority": project.priority,
            "customer_id": project.customer_id,
            "tenant_id": project.tenant_id,
            "project": project,
        }

        await self.trigger_workflow(WorkflowTrigger.PROJECT_CREATED, context)

    async def process_project_status_change(
        self, db: AsyncSession, project: Project, old_status: ProjectStatus
    ):
        """Process project status change workflows."""
        context = {
            "project_id": str(project.id),
            "project_type": project.project_type,
            "old_status": old_status,
            "new_status": project.project_status,
            "tenant_id": project.tenant_id,
            "project": project,
        }

        await self.trigger_workflow(WorkflowTrigger.STATUS_CHANGED, context)

        # Specific status triggers
        if project.project_status == ProjectStatus.IN_PROGRESS:
            await self.trigger_workflow(WorkflowTrigger.PROJECT_STARTED, context)
        elif project.project_status == ProjectStatus.COMPLETED:
            await self.trigger_workflow(WorkflowTrigger.PROJECT_COMPLETED, context)

    async def process_phase_completion(
        self, db: AsyncSession, project: Project, phase: ProjectPhase
    ):
        """Process phase completion workflows."""
        context = {
            "project_id": str(project.id),
            "phase_id": str(phase.id),
            "project_type": project.project_type,
            "phase_name": phase.phase_name,
            "phase_order": phase.phase_order,
            "is_critical": phase.is_critical_path,
            "tenant_id": project.tenant_id,
            "project": project,
            "phase": phase,
        }

        await self.trigger_workflow(WorkflowTrigger.PHASE_COMPLETED, context)

    async def process_milestone_reached(
        self, db: AsyncSession, project: Project, milestone: ProjectMilestone
    ):
        """Process milestone reached workflows."""
        context = {
            "project_id": str(project.id),
            "milestone_id": str(milestone.id),
            "project_type": project.project_type,
            "milestone_type": milestone.milestone_type,
            "is_critical": milestone.is_critical,
            "tenant_id": project.tenant_id,
            "project": project,
            "milestone": milestone,
        }

        await self.trigger_workflow(WorkflowTrigger.MILESTONE_REACHED, context)

    async def check_overdue_items(self, db: AsyncSession, tenant_id: str):
        """Check for overdue projects, phases, and milestones."""
        try:
            # Get active projects
            filters = {
                "project_status": [ProjectStatus.IN_PROGRESS, ProjectStatus.SCHEDULED]
            }
            projects, _ = await self.project_manager.list_projects(
                db, tenant_id, filters
            )

            for project in projects:
                # Check overdue project
                if project.is_overdue:
                    context = {
                        "project_id": str(project.id),
                        "project_type": project.project_type,
                        "days_overdue": (
                            abs(project.days_remaining) if project.days_remaining else 0
                        ),
                        "tenant_id": tenant_id,
                        "project": project,
                    }
                    await self.trigger_workflow(
                        WorkflowTrigger.PROJECT_OVERDUE, context
                    )

                # Check overdue phases
                for phase in project.phases:
                    if phase.is_overdue:
                        context = {
                            "project_id": str(project.id),
                            "phase_id": str(phase.id),
                            "project_type": project.project_type,
                            "phase_name": phase.phase_name,
                            "is_critical": phase.is_critical_path,
                            "tenant_id": tenant_id,
                            "project": project,
                            "phase": phase,
                        }
                        await self.trigger_workflow(
                            WorkflowTrigger.PHASE_OVERDUE, context
                        )

                # Check overdue milestones
                for milestone in project.milestones:
                    if milestone.is_overdue:
                        context = {
                            "project_id": str(project.id),
                            "milestone_id": str(milestone.id),
                            "project_type": project.project_type,
                            "milestone_type": milestone.milestone_type,
                            "is_critical": milestone.is_critical,
                            "tenant_id": tenant_id,
                            "project": project,
                            "milestone": milestone,
                        }
                        await self.trigger_workflow(
                            WorkflowTrigger.MILESTONE_OVERDUE, context
                        )

        except Exception as e:
            logger.error(f"Error checking overdue items for tenant {tenant_id}: {e}")

    def _register_default_handlers(self):
        """Register default action handlers."""
        self.action_handlers = {
            WorkflowAction.SEND_NOTIFICATION: self._handle_send_notification,
            WorkflowAction.CREATE_CALENDAR_EVENT: self._handle_create_calendar_event,
            WorkflowAction.ASSIGN_TEAM: self._handle_assign_team,
            WorkflowAction.UPDATE_STATUS: self._handle_update_status,
            WorkflowAction.ESCALATE_PRIORITY: self._handle_escalate_priority,
            WorkflowAction.SEND_CLIENT_UPDATE: self._handle_send_client_update,
        }

    def _load_default_rules(self):
        """Load default workflow rules."""

        # Installation project rules
        self.workflow_rules.extend(
            [
                # Notify customer when installation project is created
                WorkflowRule(
                    name="Installation Project Created Notification",
                    trigger=WorkflowTrigger.PROJECT_CREATED,
                    conditions={"project_type": ProjectType.NEW_INSTALLATION},
                    actions=[
                        {
                            "action": WorkflowAction.SEND_NOTIFICATION,
                            "recipient_type": "customer",
                            "template": "installation_project_created",
                            "delay_hours": 0,
                        }
                    ],
                ),
                # Create calendar event when installation project starts
                WorkflowRule(
                    name="Installation Project Started Calendar Event",
                    trigger=WorkflowTrigger.PROJECT_STARTED,
                    conditions={"project_type": ProjectType.NEW_INSTALLATION},
                    actions=[
                        {
                            "action": WorkflowAction.CREATE_CALENDAR_EVENT,
                            "event_type": "installation_start",
                            "duration_days": 1,
                        }
                    ],
                ),
                # Escalate overdue critical installations
                WorkflowRule(
                    name="Critical Installation Overdue Escalation",
                    trigger=WorkflowTrigger.PROJECT_OVERDUE,
                    conditions={
                        "project_type": ProjectType.NEW_INSTALLATION,
                        "days_overdue": 1,  # >= 1 day overdue
                    },
                    actions=[
                        {
                            "action": WorkflowAction.ESCALATE_PRIORITY,
                            "new_priority": ProjectPriority.URGENT,
                        },
                        {
                            "action": WorkflowAction.SEND_NOTIFICATION,
                            "recipient_type": "project_manager",
                            "template": "installation_overdue",
                        },
                    ],
                ),
            ]
        )

        # Deployment project rules
        self.workflow_rules.extend(
            [
                # Notify on deployment completion
                WorkflowRule(
                    name="Deployment Completed Notification",
                    trigger=WorkflowTrigger.PROJECT_COMPLETED,
                    conditions={"project_type": ProjectType.DEPLOYMENT},
                    actions=[
                        {
                            "action": WorkflowAction.SEND_NOTIFICATION,
                            "recipient_type": "customer",
                            "template": "deployment_completed",
                        },
                        {
                            "action": WorkflowAction.SEND_CLIENT_UPDATE,
                            "update_type": "completion_summary",
                        },
                    ],
                ),
            ]
        )

        # General rules
        self.workflow_rules.extend(
            [
                # Weekly status updates for long-running projects
                WorkflowRule(
                    name="Weekly Status Update",
                    trigger=WorkflowTrigger.PROJECT_STARTED,
                    conditions={},
                    actions=[
                        {
                            "action": WorkflowAction.SEND_CLIENT_UPDATE,
                            "update_type": "weekly_status",
                            "recurring": True,
                            "interval_days": 7,
                        }
                    ],
                ),
                # Milestone completion celebrations
                WorkflowRule(
                    name="Critical Milestone Reached",
                    trigger=WorkflowTrigger.MILESTONE_REACHED,
                    conditions={"is_critical": True},
                    actions=[
                        {
                            "action": WorkflowAction.SEND_NOTIFICATION,
                            "recipient_type": "customer",
                            "template": "milestone_completed",
                        },
                        {
                            "action": WorkflowAction.SEND_NOTIFICATION,
                            "recipient_type": "project_manager",
                            "template": "milestone_celebration",
                        },
                    ],
                ),
            ]
        )

    async def _execute_rule_actions(self, rule: WorkflowRule, context: dict[str, Any]):
        """Execute all actions for a workflow rule."""
        for action_config in rule.actions:
            try:
                action_type = WorkflowAction(action_config["action"])
                handler = self.action_handlers.get(action_type)

                if handler:
                    await handler(action_config, context)
                else:
                    logger.warning(f"No handler found for action: {action_type}")

            except Exception as e:
                logger.error(
                    f"Error executing action {action_config} for rule {rule.name}: {e}"
                )

    async def _handle_send_notification(
        self, action_config: dict[str, Any], context: dict[str, Any]
    ):
        """Handle send notification action."""
        recipient_type = action_config.get("recipient_type", "customer")
        template = action_config.get("template", "generic_notification")
        delay_hours = action_config.get("delay_hours", 0)

        if delay_hours > 0:
            # Schedule for later (would use task queue in production)
            logger.info(f"Scheduling notification for {delay_hours} hours: {template}")
        else:
            logger.info(f"Sending {template} notification to {recipient_type}")
            # Would integrate with notification system

    async def _handle_create_calendar_event(
        self, action_config: dict[str, Any], context: dict[str, Any]
    ):
        """Handle create calendar event action."""
        event_type = action_config.get("event_type", "project_event")
        duration_days = action_config.get("duration_days", 1)

        logger.info(f"Creating calendar event: {event_type} for {duration_days} days")
        # Would integrate with calendar system

    async def _handle_assign_team(
        self, action_config: dict[str, Any], context: dict[str, Any]
    ):
        """Handle assign team action."""
        team_name = action_config.get("team_name")
        project_id = context.get("project_id")

        if team_name and project_id:
            logger.info(f"Assigning team {team_name} to project {project_id}")
            # Would call project service to assign team

    async def _handle_update_status(
        self, action_config: dict[str, Any], context: dict[str, Any]
    ):
        """Handle update status action."""
        new_status = action_config.get("new_status")
        project_id = context.get("project_id")

        if new_status and project_id:
            logger.info(f"Updating project {project_id} status to {new_status}")
            # Would call project service to update status

    async def _handle_escalate_priority(
        self, action_config: dict[str, Any], context: dict[str, Any]
    ):
        """Handle escalate priority action."""
        new_priority = action_config.get("new_priority")
        project_id = context.get("project_id")

        if new_priority and project_id:
            logger.info(f"Escalating project {project_id} to {new_priority} priority")
            # Would call project service to escalate

    async def _handle_send_client_update(
        self, action_config: dict[str, Any], context: dict[str, Any]
    ):
        """Handle send client update action."""
        update_type = action_config.get("update_type", "progress_update")
        project_id = context.get("project_id")

        logger.info(f"Sending {update_type} client update for project {project_id}")
        # Would integrate with client communication system


# Utility functions for workflow management
async def setup_project_workflows(
    project_manager: ProjectManager,
    project_service: ProjectService,
    custom_rules: Optional[list[WorkflowRule]] = None,
) -> ProjectWorkflowManager:
    """Setup and configure project workflow manager."""

    workflow_manager = ProjectWorkflowManager(project_manager, project_service)

    # Add custom rules if provided
    if custom_rules:
        for rule in custom_rules:
            workflow_manager.add_workflow_rule(rule)

    return workflow_manager


async def run_workflow_scheduler(
    workflow_manager: ProjectWorkflowManager,
    db_session_factory,
    tenant_ids: list[str],
    check_interval_minutes: int = 60,
):
    """Run periodic workflow scheduler for overdue checks."""

    while True:
        try:
            async with db_session_factory() as db:
                for tenant_id in tenant_ids:
                    await workflow_manager.check_overdue_items(db, tenant_id)

            # Wait for next check
            await asyncio.sleep(check_interval_minutes * 60)

        except Exception as e:
            logger.error(f"Error in workflow scheduler: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error
