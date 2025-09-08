"""
Alarm Management Service.

Provides alarm creation, acknowledgment, clearing, and escalation workflows
for network operations center alarm handling.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from dotmac.application import standard_exception_handler
from dotmac.core.exceptions import EntityNotFoundError, ValidationError
from dotmac_shared.services.base import BaseManagementService as BaseTenantService

from ..models.alarms import Alarm, AlarmRule, AlarmStatus
from ..models.events import EventSeverity, EventType, NetworkEvent

logger = logging.getLogger(__name__)


class AlarmManagementService(BaseTenantService):
    """Service for managing network alarms, rules, and escalations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=Alarm,
            create_schema=None,
            update_schema=None,
            response_schema=None,
            tenant_id=tenant_id,
        )

    @standard_exception_handler
    async def create_alarm(self, alarm_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new network alarm."""
        alarm_id = alarm_data.get("alarm_id") or str(uuid4())

        # Check if alarm already exists (for duplicate suppression)
        existing_alarm = self._find_existing_alarm(alarm_data)
        if existing_alarm:
            # Update occurrence count and last occurrence time
            existing_alarm.occurrence_count += 1
            existing_alarm.last_occurrence = datetime.now(timezone.utc)
            existing_alarm.updated_at = datetime.now(timezone.utc)

            self.db.commit()

            logger.info(
                f"Updated existing alarm {existing_alarm.alarm_id}, occurrence count: {existing_alarm.occurrence_count}"
            )

            return existing_alarm.to_dict()

        # Create new alarm
        alarm = Alarm(
            alarm_id=alarm_id,
            tenant_id=self.tenant_id,
            alarm_type=alarm_data["alarm_type"],
            severity=alarm_data["severity"],
            status=AlarmStatus.ACTIVE,
            device_id=alarm_data.get("device_id"),
            interface_id=alarm_data.get("interface_id"),
            service_id=alarm_data.get("service_id"),
            customer_id=alarm_data.get("customer_id"),
            title=alarm_data["title"],
            description=alarm_data.get("description"),
            raw_message=alarm_data.get("raw_message"),
            first_occurrence=datetime.now(timezone.utc),
            last_occurrence=datetime.now(timezone.utc),
            occurrence_count=1,
            source_system=alarm_data.get("source_system", "noc"),
            correlation_id=alarm_data.get("correlation_id"),
            context_data=alarm_data.get("context_data", {}),
            tags=alarm_data.get("tags", []),
        )

        self.db.add(alarm)
        self.db.commit()

        logger.info(f"Created new alarm {alarm_id}: {alarm.title}")

        # Create corresponding network event
        await self._create_alarm_event(alarm, "alarm_created")

        return alarm.to_dict()

    @standard_exception_handler
    async def acknowledge_alarm(
        self, alarm_id: str, acknowledged_by: str, notes: Optional[str] = None
    ) -> dict[str, Any]:
        """Acknowledge an active alarm."""
        alarm = self.db.query(Alarm).filter(and_(Alarm.alarm_id == alarm_id, Alarm.tenant_id == self.tenant_id)).first()

        if not alarm:
            raise EntityNotFoundError(f"Alarm not found: {alarm_id}")

        if alarm.status != AlarmStatus.ACTIVE:
            raise ValidationError(f"Cannot acknowledge alarm in status: {alarm.status}")

        # Update alarm status
        alarm.status = AlarmStatus.ACKNOWLEDGED
        alarm.acknowledged_at = datetime.now(timezone.utc)
        alarm.acknowledged_by = acknowledged_by
        alarm.updated_at = datetime.now(timezone.utc)

        # Add notes to context data
        if notes:
            if not alarm.context_data:
                alarm.context_data = {}
            alarm.context_data["acknowledgment_notes"] = notes

        self.db.commit()

        logger.info(f"Acknowledged alarm {alarm_id} by {acknowledged_by}")

        # Create event
        await self._create_alarm_event(
            alarm,
            "alarm_acknowledged",
            {"acknowledged_by": acknowledged_by, "notes": notes},
        )

        return alarm.to_dict()

    @standard_exception_handler
    async def clear_alarm(self, alarm_id: str, cleared_by: str, clear_reason: Optional[str] = None) -> dict[str, Any]:
        """Clear an alarm (mark as resolved)."""
        alarm = self.db.query(Alarm).filter(and_(Alarm.alarm_id == alarm_id, Alarm.tenant_id == self.tenant_id)).first()

        if not alarm:
            raise EntityNotFoundError(f"Alarm not found: {alarm_id}")

        if alarm.status == AlarmStatus.CLEARED:
            raise ValidationError("Alarm is already cleared")

        # Update alarm status
        previous_status = alarm.status
        alarm.status = AlarmStatus.CLEARED
        alarm.cleared_at = datetime.now(timezone.utc)
        alarm.cleared_by = cleared_by
        alarm.updated_at = datetime.now(timezone.utc)

        # Add clear reason to context data
        if clear_reason:
            if not alarm.context_data:
                alarm.context_data = {}
            alarm.context_data["clear_reason"] = clear_reason

        self.db.commit()

        logger.info(f"Cleared alarm {alarm_id} by {cleared_by}. Reason: {clear_reason}")

        # Create event
        await self._create_alarm_event(
            alarm,
            "alarm_cleared",
            {
                "cleared_by": cleared_by,
                "clear_reason": clear_reason,
                "previous_status": previous_status,
            },
        )

        return alarm.to_dict()

    @standard_exception_handler
    async def escalate_alarm(
        self,
        alarm_id: str,
        new_severity: str,
        escalated_by: str,
        escalation_reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Escalate alarm to higher severity."""
        alarm = self.db.query(Alarm).filter(and_(Alarm.alarm_id == alarm_id, Alarm.tenant_id == self.tenant_id)).first()

        if not alarm:
            raise EntityNotFoundError(f"Alarm not found: {alarm_id}")

        if alarm.status == AlarmStatus.CLEARED:
            raise ValidationError("Cannot escalate cleared alarm")

        # Validate severity escalation
        severity_levels = ["info", "warning", "minor", "major", "critical"]
        current_level = severity_levels.index(alarm.severity)
        new_level = severity_levels.index(new_severity)

        if new_level <= current_level:
            raise ValidationError("Can only escalate to higher severity")

        # Update alarm
        previous_severity = alarm.severity
        alarm.severity = new_severity
        alarm.updated_at = datetime.now(timezone.utc)

        # Track escalation in context data
        if not alarm.context_data:
            alarm.context_data = {}

        escalations = alarm.context_data.get("escalations", [])
        escalations.append(
            {
                "from_severity": previous_severity,
                "to_severity": new_severity,
                "escalated_by": escalated_by,
                "escalated_at": datetime.now(timezone.utc).isoformat(),
                "reason": escalation_reason,
            }
        )
        alarm.context_data["escalations"] = escalations

        self.db.commit()

        logger.info(f"Escalated alarm {alarm_id} from {previous_severity} to {new_severity} by {escalated_by}")

        # Create event
        await self._create_alarm_event(
            alarm,
            "alarm_escalated",
            {
                "escalated_by": escalated_by,
                "from_severity": previous_severity,
                "to_severity": new_severity,
                "escalation_reason": escalation_reason,
            },
        )

        return alarm.to_dict()

    @standard_exception_handler
    async def suppress_alarm(
        self,
        alarm_id: str,
        suppressed_by: str,
        suppression_duration_hours: Optional[int] = None,
        suppression_reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Temporarily suppress an alarm."""
        alarm = self.db.query(Alarm).filter(and_(Alarm.alarm_id == alarm_id, Alarm.tenant_id == self.tenant_id)).first()

        if not alarm:
            raise EntityNotFoundError(f"Alarm not found: {alarm_id}")

        # Update alarm status
        previous_status = alarm.status
        alarm.status = AlarmStatus.SUPPRESSED
        alarm.updated_at = datetime.now(timezone.utc)

        # Track suppression details
        if not alarm.context_data:
            alarm.context_data = {}

        suppression_data = {
            "suppressed_by": suppressed_by,
            "suppressed_at": datetime.now(timezone.utc).isoformat(),
            "reason": suppression_reason,
            "previous_status": previous_status,
        }

        if suppression_duration_hours:
            suppression_until = datetime.now(timezone.utc) + timedelta(hours=suppression_duration_hours)
            suppression_data["suppressed_until"] = suppression_until.isoformat()

        alarm.context_data["suppression"] = suppression_data

        self.db.commit()

        logger.info(
            f"Suppressed alarm {alarm_id} by {suppressed_by} for {suppression_duration_hours or 'indefinite'} hours"
        )

        return alarm.to_dict()

    @standard_exception_handler
    async def get_alarms_list(
        self,
        status_filter: Optional[list[str]] = None,
        severity_filter: Optional[list[str]] = None,
        device_filter: Optional[str] = None,
        customer_filter: Optional[str] = None,
        alarm_type_filter: Optional[str] = None,
        since_hours: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get filtered list of alarms."""
        query = self.db.query(Alarm).filter(Alarm.tenant_id == self.tenant_id)

        # Apply filters
        if status_filter:
            query = query.filter(Alarm.status.in_(status_filter))

        if severity_filter:
            query = query.filter(Alarm.severity.in_(severity_filter))

        if device_filter:
            query = query.filter(Alarm.device_id == device_filter)

        if customer_filter:
            query = query.filter(Alarm.customer_id == customer_filter)

        if alarm_type_filter:
            query = query.filter(Alarm.alarm_type == alarm_type_filter)

        if since_hours:
            since_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)
            query = query.filter(Alarm.first_occurrence >= since_time)

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination and ordering
        alarms = query.order_by(desc(Alarm.severity), desc(Alarm.last_occurrence)).offset(offset).limit(limit).all()

        return {
            "alarms": [alarm.to_dict() for alarm in alarms],
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_count,
        }

    @standard_exception_handler
    async def create_alarm_rule(self, rule_data: dict[str, Any]) -> dict[str, Any]:
        """Create alarm generation rule."""
        rule_id = rule_data.get("rule_id") or str(uuid4())

        rule = AlarmRule(
            rule_id=rule_id,
            tenant_id=self.tenant_id,
            name=rule_data["name"],
            description=rule_data.get("description"),
            is_enabled=rule_data.get("is_enabled", "true"),
            metric_name=rule_data.get("metric_name"),
            threshold_value=str(rule_data.get("threshold_value", "")),
            threshold_operator=rule_data.get("threshold_operator", ">"),
            evaluation_window_minutes=rule_data.get("evaluation_window_minutes", 5),
            device_type=rule_data.get("device_type"),
            device_tags=rule_data.get("device_tags", []),
            alarm_type=rule_data["alarm_type"],
            alarm_severity=rule_data["alarm_severity"],
            alarm_title_template=rule_data.get("alarm_title_template"),
            alarm_description_template=rule_data.get("alarm_description_template"),
            rule_definition=rule_data.get("rule_definition", {}),
            created_by=rule_data.get("created_by", "system"),
        )

        self.db.add(rule)
        self.db.commit()

        logger.info(f"Created alarm rule {rule_id}: {rule.name}")

        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "is_enabled": rule.is_enabled,
            "alarm_type": rule.alarm_type,
            "alarm_severity": rule.alarm_severity,
            "created_at": rule.created_at.isoformat(),
        }

    @standard_exception_handler
    async def evaluate_alarm_rules(self, device_metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate alarm rules against device metrics and generate alarms."""
        device_id = device_metrics.get("device_id")
        if not device_id:
            return []

        # Get active alarm rules
        rules = (
            self.db.query(AlarmRule)
            .filter(
                and_(
                    AlarmRule.tenant_id == self.tenant_id,
                    AlarmRule.is_enabled == "true",
                )
            )
            .all()
        )

        generated_alarms = []

        for rule in rules:
            try:
                alarm_data = await self._evaluate_rule_against_metrics(rule, device_metrics)
                if alarm_data:
                    created_alarm = await self.create_alarm(alarm_data)
                    generated_alarms.append(created_alarm)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {str(e)}")

        return generated_alarms

    # Private helper methods

    def _find_existing_alarm(self, alarm_data: dict[str, Any]) -> Optional[Alarm]:
        """Find existing active alarm for deduplication."""
        return (
            self.db.query(Alarm)
            .filter(
                and_(
                    Alarm.tenant_id == self.tenant_id,
                    Alarm.alarm_type == alarm_data["alarm_type"],
                    Alarm.device_id == alarm_data.get("device_id"),
                    Alarm.interface_id == alarm_data.get("interface_id"),
                    Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED]),
                    # Look for alarms within last hour to avoid duplicates
                    Alarm.last_occurrence >= datetime.now(timezone.utc) - timedelta(hours=1),
                )
            )
            .first()
        )

    async def _create_alarm_event(
        self,
        alarm: Alarm,
        event_type: str,
        additional_context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Create network event for alarm state change."""
        context_data = {
            "alarm_id": alarm.alarm_id,
            "alarm_type": alarm.alarm_type,
            "severity": alarm.severity,
            "status": alarm.status,
        }

        if additional_context:
            context_data.update(additional_context)

        event = NetworkEvent(
            event_id=str(uuid4()),
            tenant_id=self.tenant_id,
            event_type=EventType.SYSTEM_EVENT,
            severity=EventSeverity.MEDIUM if alarm.severity in ["minor", "warning"] else EventSeverity.HIGH,
            category="alarm_management",
            source_system="noc",
            device_id=alarm.device_id,
            customer_id=alarm.customer_id,
            title=f"Alarm {event_type.replace('_', ' ').title()}: {alarm.title}",
            description=f"Alarm {alarm.alarm_id} {event_type.replace('_', ' ')}",
            raw_data=context_data,
            event_timestamp=datetime.now(timezone.utc),
        )

        self.db.add(event)
        self.db.commit()

    async def _evaluate_rule_against_metrics(
        self, rule: AlarmRule, metrics: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Evaluate a single rule against device metrics."""
        if not rule.metric_name or rule.metric_name not in metrics:
            return None

        metric_value = metrics[rule.metric_name]
        threshold_value = float(rule.threshold_value)

        # Simple threshold evaluation
        triggered = False
        if rule.threshold_operator == ">":
            triggered = metric_value > threshold_value
        elif rule.threshold_operator == ">=":
            triggered = metric_value >= threshold_value
        elif rule.threshold_operator == "<":
            triggered = metric_value < threshold_value
        elif rule.threshold_operator == "<=":
            triggered = metric_value <= threshold_value
        elif rule.threshold_operator == "==":
            triggered = metric_value == threshold_value
        elif rule.threshold_operator == "!=":
            triggered = metric_value != threshold_value

        if not triggered:
            return None

        # Generate alarm data
        title = rule.alarm_title_template or f"{rule.metric_name} threshold exceeded"
        title = title.replace("{metric_name}", rule.metric_name)
        title = title.replace("{value}", str(metric_value))
        title = title.replace("{threshold}", str(threshold_value))

        description = (
            rule.alarm_description_template or f"{rule.metric_name} is {metric_value}, threshold: {threshold_value}"
        )
        description = description.replace("{metric_name}", rule.metric_name)
        description = description.replace("{value}", str(metric_value))
        description = description.replace("{threshold}", str(threshold_value))
        description = description.replace("{operator}", rule.threshold_operator)

        return {
            "alarm_type": rule.alarm_type,
            "severity": rule.alarm_severity,
            "device_id": metrics.get("device_id"),
            "title": title,
            "description": description,
            "source_system": "rule_engine",
            "correlation_id": rule.rule_id,
            "context_data": {
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "metric_name": rule.metric_name,
                "metric_value": metric_value,
                "threshold_value": threshold_value,
                "threshold_operator": rule.threshold_operator,
                "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "tags": ["auto_generated", f"rule:{rule.rule_id}"],
        }
