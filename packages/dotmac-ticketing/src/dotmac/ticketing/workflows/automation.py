"""
Ticket automation engine and rules system.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import Ticket, TicketPriority, TicketStatus
from .base import TicketWorkflow
from .implementations import (
    BillingIssueWorkflow,
    CustomerSupportWorkflow,
    TechnicalSupportWorkflow,
)

logger = logging.getLogger(__name__)


@dataclass
class AutoAssignmentRule:
    """Rule for automatically assigning tickets."""

    name: str
    conditions: dict[str, Any]
    assigned_team: str
    assigned_user_id: str | None = None
    priority: int = 0  # Higher number = higher priority
    active: bool = True


@dataclass
class EscalationRule:
    """Rule for automatic ticket escalation."""

    name: str
    conditions: dict[str, Any]
    escalation_time_hours: int
    escalate_to_team: str
    escalate_to_user_id: str | None = None
    priority_increase: bool = True
    active: bool = True


class SLAMonitor:
    """Service Level Agreement monitoring and enforcement."""

    def __init__(self, db_session_factory: Callable):
        self.db_session_factory = db_session_factory
        self.sla_config = {
            TicketPriority.CRITICAL: {"response": 0.25, "resolution": 4},  # 15min, 4hr
            TicketPriority.URGENT: {"response": 1, "resolution": 8},  # 1hr, 8hr
            TicketPriority.HIGH: {"response": 4, "resolution": 24},  # 4hr, 24hr
            TicketPriority.NORMAL: {"response": 24, "resolution": 72},  # 24hr, 3days
            TicketPriority.LOW: {"response": 48, "resolution": 168},  # 2days, 7days
        }

    async def check_sla_breaches(self, tenant_id: str) -> list[Ticket]:
        """Check for tickets that have breached SLA."""
        async with self.db_session_factory() as db:
            now = datetime.now(timezone.utc)

            # Find tickets that may have breached SLA
            query = select(Ticket).where(
                Ticket.tenant_id == tenant_id,
                Ticket.status.in_(
                    [
                        TicketStatus.OPEN,
                        TicketStatus.IN_PROGRESS,
                        TicketStatus.WAITING_FOR_CUSTOMER,
                        TicketStatus.ESCALATED,
                    ]
                ),
                Ticket.sla_breach_time <= now,
            )

            result = await db.execute(query)
            breached_tickets = result.scalars().all()

            return list(breached_tickets)

    async def calculate_sla_breach_time(
        self, ticket: Ticket, sla_type: str = "resolution"
    ) -> datetime:
        """Calculate when a ticket will breach SLA."""
        sla_config = self.sla_config.get(
            ticket.priority, self.sla_config[TicketPriority.NORMAL]
        )

        hours_to_breach = sla_config.get(sla_type, sla_config["resolution"])
        breach_time = ticket.created_at + timedelta(hours=hours_to_breach)

        return breach_time

    async def update_ticket_sla(self, ticket: Ticket, db: AsyncSession):
        """Update ticket SLA breach time."""
        breach_time = await self.calculate_sla_breach_time(ticket)
        ticket.sla_breach_time = breach_time
        await db.commit()


class TicketAutomationEngine:
    """Engine for executing ticket automation rules and workflows."""

    def __init__(self, db_session_factory: Callable):
        self.db_session_factory = db_session_factory
        self.assignment_rules: list[AutoAssignmentRule] = []
        self.escalation_rules: list[EscalationRule] = []
        self.workflows: dict[str, TicketWorkflow] = {}
        self.sla_monitor = SLAMonitor(db_session_factory)

        # Register default workflows
        self._register_default_workflows()

    def _register_default_workflows(self):
        """Register default workflow implementations."""
        self.workflows = {
            "customer_support": CustomerSupportWorkflow(),
            "technical_support": TechnicalSupportWorkflow(),
            "billing_issue": BillingIssueWorkflow(),
        }

    def add_assignment_rule(self, rule: AutoAssignmentRule):
        """Add an auto-assignment rule."""
        self.assignment_rules.append(rule)
        # Sort by priority (descending)
        self.assignment_rules.sort(key=lambda r: r.priority, reverse=True)

    def add_escalation_rule(self, rule: EscalationRule):
        """Add an escalation rule."""
        self.escalation_rules.append(rule)

    def register_workflow(self, name: str, workflow: TicketWorkflow):
        """Register a custom workflow."""
        self.workflows[name] = workflow

    async def process_new_ticket(
        self, ticket: Ticket, tenant_id: str, db: AsyncSession
    ):
        """Process a newly created ticket through automation."""
        try:
            # Apply auto-assignment rules
            await self._apply_assignment_rules(ticket, tenant_id, db)

            # Update SLA information
            await self.sla_monitor.update_ticket_sla(ticket, db)

            # Trigger appropriate workflows
            await self._trigger_workflows(ticket, tenant_id, db)

        except Exception as e:
            logger.error(f"Error processing ticket {ticket.id}: {str(e)}")
            raise

    async def _apply_assignment_rules(
        self, ticket: Ticket, tenant_id: str, db: AsyncSession
    ):
        """Apply auto-assignment rules to a ticket."""
        for rule in self.assignment_rules:
            if not rule.active:
                continue

            if await self._rule_matches_ticket(rule.conditions, ticket):
                # Apply assignment
                ticket.assigned_team = rule.assigned_team
                if rule.assigned_user_id:
                    ticket.assigned_to_id = rule.assigned_user_id

                ticket.status = TicketStatus.IN_PROGRESS

                logger.info(
                    f"Auto-assigned ticket {ticket.id} to {rule.assigned_team} "
                    f"using rule '{rule.name}'"
                )
                break  # Apply first matching rule only

    async def _trigger_workflows(
        self, ticket: Ticket, tenant_id: str, db: AsyncSession
    ):
        """Trigger appropriate workflows for a ticket."""
        for workflow_name, workflow in self.workflows.items():
            if await workflow.should_trigger(ticket):
                # Set ticket context and execute workflow
                workflow.set_ticket_context(ticket, tenant_id, db)

                # Execute workflow in background
                asyncio.create_task(self._execute_workflow_safe(workflow))

                logger.info(
                    f"Triggered workflow '{workflow_name}' for ticket {ticket.id}"
                )

    async def _execute_workflow_safe(self, workflow: TicketWorkflow):
        """Safely execute a workflow with error handling."""
        try:
            results = await workflow.execute()
            logger.info(
                f"Workflow {workflow.workflow_type} completed with "
                f"{len([r for r in results if r.success])} successful steps"
            )
        except Exception as e:
            logger.error(f"Workflow {workflow.workflow_type} failed: {str(e)}")

    async def _rule_matches_ticket(
        self, conditions: dict[str, Any], ticket: Ticket
    ) -> bool:
        """Check if rule conditions match a ticket."""
        for field, expected_value in conditions.items():
            ticket_value = getattr(ticket, field, None)

            if isinstance(expected_value, list):
                if ticket_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # Handle more complex conditions
                operator = expected_value.get("operator", "eq")
                value = expected_value.get("value")

                if operator == "eq" and ticket_value != value:
                    return False
                elif operator == "in" and ticket_value not in value:
                    return False
                elif operator == "contains" and value not in str(ticket_value).lower():
                    return False
            else:
                if ticket_value != expected_value:
                    return False

        return True

    async def check_escalations(self, tenant_id: str):
        """Check and process ticket escalations."""
        async with self.db_session_factory() as db:
            now = datetime.now(timezone.utc)

            # Find tickets that may need escalation
            query = select(Ticket).where(
                Ticket.tenant_id == tenant_id,
                Ticket.status.in_(
                    [
                        TicketStatus.OPEN,
                        TicketStatus.IN_PROGRESS,
                        TicketStatus.WAITING_FOR_CUSTOMER,
                    ]
                ),
            )

            result = await db.execute(query)
            tickets = result.scalars().all()

            for ticket in tickets:
                await self._check_ticket_escalation(ticket, now, db)

    async def _check_ticket_escalation(
        self, ticket: Ticket, current_time: datetime, db: AsyncSession
    ):
        """Check if a specific ticket needs escalation."""
        for rule in self.escalation_rules:
            if not rule.active:
                continue

            # Check if rule matches ticket
            if not await self._rule_matches_ticket(rule.conditions, ticket):
                continue

            # Check if escalation time has passed
            escalation_time = ticket.created_at + timedelta(
                hours=rule.escalation_time_hours
            )

            if current_time >= escalation_time:
                # Escalate ticket
                await self._escalate_ticket(ticket, rule, db)
                break  # Apply first matching escalation rule

    async def _escalate_ticket(
        self, ticket: Ticket, rule: EscalationRule, db: AsyncSession
    ):
        """Escalate a ticket according to a rule."""
        # Update ticket
        ticket.status = TicketStatus.ESCALATED
        ticket.assigned_team = rule.escalate_to_team

        if rule.escalate_to_user_id:
            ticket.assigned_to_id = rule.escalate_to_user_id

        # Increase priority if requested
        if rule.priority_increase and ticket.priority != TicketPriority.CRITICAL:
            priority_order = [
                TicketPriority.LOW,
                TicketPriority.NORMAL,
                TicketPriority.HIGH,
                TicketPriority.URGENT,
                TicketPriority.CRITICAL,
            ]

            current_index = priority_order.index(ticket.priority)
            if current_index < len(priority_order) - 1:
                ticket.priority = priority_order[current_index + 1]

        await db.commit()

        logger.info(
            f"Escalated ticket {ticket.id} to {rule.escalate_to_team} "
            f"using rule '{rule.name}'"
        )
