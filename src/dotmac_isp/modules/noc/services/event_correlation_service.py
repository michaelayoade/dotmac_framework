"""
Event Correlation Service.

Provides intelligent event correlation, root cause analysis, and automated
incident grouping for network operations center.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from dotmac_shared.services.base import BaseTenantService
from sqlalchemy import and_
from sqlalchemy.orm import Session

from dotmac.application import standard_exception_handler

from ..models.events import EventRule, EventSeverity, EventType, NetworkEvent

logger = logging.getLogger(__name__)


class EventCorrelationService(BaseTenantService):
    """Service for correlating network events and identifying patterns."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=NetworkEvent,
            create_schema=None,
            update_schema=None,
            response_schema=None,
            tenant_id=tenant_id,
        )

    @standard_exception_handler
    async def process_incoming_event(
        self, event_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Process incoming network event with correlation analysis."""
        event_id = event_data.get("event_id") or str(uuid4())

        # Create base event
        event = NetworkEvent(
            event_id=event_id,
            tenant_id=self.tenant_id,
            event_type=event_data["event_type"],
            severity=event_data["severity"],
            category=event_data.get("category", "general"),
            source_system=event_data.get("source_system", "unknown"),
            device_id=event_data.get("device_id"),
            interface_id=event_data.get("interface_id"),
            service_id=event_data.get("service_id"),
            customer_id=event_data.get("customer_id"),
            title=event_data["title"],
            description=event_data.get("description"),
            raw_data=event_data.get("raw_data", {}),
            previous_state=event_data.get("previous_state"),
            current_state=event_data.get("current_state"),
            tags=event_data.get("tags", []),
            custom_fields=event_data.get("custom_fields", {}),
            event_timestamp=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )

        # Perform correlation analysis
        correlation_results = await self._perform_event_correlation(event)

        if correlation_results["correlation_id"]:
            event.correlation_id = correlation_results["correlation_id"]
        if correlation_results["parent_event_id"]:
            event.parent_event_id = correlation_results["parent_event_id"]
        if correlation_results["root_cause_event_id"]:
            event.root_cause_event_id = correlation_results["root_cause_event_id"]

        # Apply event rules
        rule_actions = await self._apply_event_rules(event)

        # Save event
        self.db.add(event)
        self.db.commit()

        logger.info(f"Processed event {event_id}: {event.title}")

        return {
            "event_id": event.event_id,
            "correlation_results": correlation_results,
            "rule_actions": rule_actions,
            "event_data": event.to_dict(),
        }

    @standard_exception_handler
    async def analyze_event_patterns(
        self, time_window_hours: int = 24, min_event_count: int = 5
    ) -> dict[str, Any]:
        """Analyze recent events for patterns and anomalies."""
        since = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

        # Get events within time window
        events = (
            self.db.query(NetworkEvent)
            .filter(
                and_(
                    NetworkEvent.tenant_id == self.tenant_id,
                    NetworkEvent.event_timestamp >= since,
                )
            )
            .all()
        )

        if len(events) < min_event_count:
            return {
                "total_events": len(events),
                "analysis": "Insufficient events for pattern analysis",
                "patterns": [],
                "anomalies": [],
            }

        # Analyze patterns
        patterns = await self._identify_event_patterns(events)
        anomalies = await self._detect_event_anomalies(events)
        correlations = await self._analyze_event_correlations(events)

        return {
            "total_events": len(events),
            "time_window_hours": time_window_hours,
            "patterns": patterns,
            "anomalies": anomalies,
            "correlations": correlations,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def get_correlated_events(
        self, correlation_id: str, include_children: bool = True
    ) -> dict[str, Any]:
        """Get all events in a correlation group."""
        query = self.db.query(NetworkEvent).filter(
            and_(
                NetworkEvent.tenant_id == self.tenant_id,
                NetworkEvent.correlation_id == correlation_id,
            )
        )

        events = query.order_by(NetworkEvent.event_timestamp).all()

        # Get child events if requested
        child_events = []
        if include_children:
            for event in events:
                children = (
                    self.db.query(NetworkEvent)
                    .filter(
                        and_(
                            NetworkEvent.tenant_id == self.tenant_id,
                            NetworkEvent.parent_event_id == event.event_id,
                        )
                    )
                    .all()
                )
                child_events.extend(children)

        # Build event hierarchy
        event_tree = await self._build_event_hierarchy(events + child_events)

        return {
            "correlation_id": correlation_id,
            "total_events": len(events),
            "child_events": len(child_events),
            "events": [event.to_dict() for event in events],
            "child_events_data": [event.to_dict() for event in child_events],
            "event_hierarchy": event_tree,
        }

    @standard_exception_handler
    async def create_incident_from_correlation(
        self,
        correlation_id: str,
        incident_title: str,
        incident_description: str,
        assigned_to: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create incident from correlated events (integration point)."""
        # Get correlated events
        correlation_data = await self.get_correlated_events(correlation_id)

        # This would integrate with incident management system
        # For now, we'll create a high-level alarm representing the incident
        {
            "alarm_type": "incident",
            "severity": "major",
            "title": incident_title,
            "description": incident_description,
            "source_system": "event_correlation",
            "correlation_id": correlation_id,
            "context_data": {
                "incident_type": "correlated_events",
                "related_events_count": correlation_data["total_events"],
                "assigned_to": assigned_to,
                "created_from_correlation": True,
            },
            "tags": ["incident", "auto_created", f"correlation:{correlation_id}"],
        }

        # This would call the alarm management service
        # from .alarm_management_service import AlarmManagementService
        # alarm_service = AlarmManagementService(self.db, self.tenant_id)
        # incident_alarm = await alarm_service.create_alarm(incident_data)

        logger.info(
            f"Created incident for correlation {correlation_id}: {incident_title}"
        )

        return {
            "incident_id": f"INC-{correlation_id[:8]}",
            "correlation_id": correlation_id,
            "title": incident_title,
            "related_events": correlation_data["total_events"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Private helper methods

    async def _perform_event_correlation(self, event: NetworkEvent) -> dict[str, Any]:
        """Perform correlation analysis for an event."""
        correlation_window = timedelta(minutes=30)
        since = datetime.now(timezone.utc) - correlation_window

        # Find related events
        related_events = await self._find_related_events(event, since)

        correlation_results = {
            "correlation_id": None,
            "parent_event_id": None,
            "root_cause_event_id": None,
            "related_events_count": len(related_events),
            "correlation_strength": 0.0,
        }

        if not related_events:
            return correlation_results

        # Check if any related events already have a correlation ID
        existing_correlation = None
        for related_event in related_events:
            if related_event.correlation_id:
                existing_correlation = related_event.correlation_id
                break

        if existing_correlation:
            correlation_results["correlation_id"] = existing_correlation
        else:
            # Create new correlation ID
            correlation_results["correlation_id"] = f"CORR-{uuid4().hex[:8]}"

        # Determine parent-child relationships
        correlation_results["parent_event_id"] = await self._determine_parent_event(
            event, related_events
        )

        # Identify potential root cause
        correlation_results["root_cause_event_id"] = await self._identify_root_cause(
            event, related_events
        )

        # Calculate correlation strength
        correlation_results[
            "correlation_strength"
        ] = await self._calculate_correlation_strength(event, related_events)

        return correlation_results

    async def _find_related_events(
        self, event: NetworkEvent, since: datetime
    ) -> list[NetworkEvent]:
        """Find events related to the given event."""
        related_events = []

        # Find events from same device
        if event.device_id:
            device_events = (
                self.db.query(NetworkEvent)
                .filter(
                    and_(
                        NetworkEvent.tenant_id == self.tenant_id,
                        NetworkEvent.device_id == event.device_id,
                        NetworkEvent.event_timestamp >= since,
                        NetworkEvent.event_id != event.event_id,
                    )
                )
                .all()
            )
            related_events.extend(device_events)

        # Find events from same service
        if event.service_id:
            service_events = (
                self.db.query(NetworkEvent)
                .filter(
                    and_(
                        NetworkEvent.tenant_id == self.tenant_id,
                        NetworkEvent.service_id == event.service_id,
                        NetworkEvent.event_timestamp >= since,
                        NetworkEvent.event_id != event.event_id,
                    )
                )
                .all()
            )
            related_events.extend(service_events)

        # Find events of same type from different sources
        type_events = (
            self.db.query(NetworkEvent)
            .filter(
                and_(
                    NetworkEvent.tenant_id == self.tenant_id,
                    NetworkEvent.event_type == event.event_type,
                    NetworkEvent.event_timestamp >= since,
                    NetworkEvent.event_id != event.event_id,
                )
            )
            .limit(10)
            .all()
        )
        related_events.extend(type_events)

        # Remove duplicates
        seen_ids = set()
        unique_events = []
        for evt in related_events:
            if evt.event_id not in seen_ids:
                seen_ids.add(evt.event_id)
                unique_events.append(evt)

        return unique_events

    async def _determine_parent_event(
        self, event: NetworkEvent, related_events: list[NetworkEvent]
    ) -> Optional[str]:
        """Determine if this event should be a child of another event."""
        # Look for earlier events that could be parents
        for related_event in related_events:
            if related_event.event_timestamp < event.event_timestamp:
                # Check if it's a likely parent based on event types
                if await self._is_likely_parent_child(related_event, event):
                    return related_event.event_id
        return None

    async def _identify_root_cause(
        self, event: NetworkEvent, related_events: list[NetworkEvent]
    ) -> Optional[str]:
        """Identify potential root cause event."""
        # Find the earliest device-down or critical event
        root_cause_events = [
            evt
            for evt in related_events
            if evt.event_type
            in [EventType.DEVICE_STATE_CHANGE, EventType.INTERFACE_STATE_CHANGE]
            and evt.severity in [EventSeverity.CRITICAL, EventSeverity.HIGH]
        ]

        if root_cause_events:
            # Return earliest critical event
            earliest = min(root_cause_events, key=lambda x: x.event_timestamp)
            return earliest.event_id

        return None

    async def _calculate_correlation_strength(
        self, event: NetworkEvent, related_events: list[NetworkEvent]
    ) -> float:
        """Calculate correlation strength (0.0 - 1.0)."""
        if not related_events:
            return 0.0

        strength = 0.0
        max_strength = 1.0

        # Same device increases correlation
        same_device_count = sum(
            1 for evt in related_events if evt.device_id == event.device_id
        )
        if same_device_count > 0:
            strength += 0.3

        # Same service increases correlation
        same_service_count = sum(
            1 for evt in related_events if evt.service_id == event.service_id
        )
        if same_service_count > 0:
            strength += 0.2

        # Same customer increases correlation
        same_customer_count = sum(
            1 for evt in related_events if evt.customer_id == event.customer_id
        )
        if same_customer_count > 0:
            strength += 0.2

        # Time proximity increases correlation
        time_proximity = min(len(related_events) * 0.1, 0.3)
        strength += time_proximity

        return min(strength, max_strength)

    async def _is_likely_parent_child(
        self, potential_parent: NetworkEvent, potential_child: NetworkEvent
    ) -> bool:
        """Determine if two events have a parent-child relationship."""
        # Device down -> Interface down
        if (
            potential_parent.event_type == EventType.DEVICE_STATE_CHANGE
            and potential_parent.current_state == "down"
            and potential_child.event_type == EventType.INTERFACE_STATE_CHANGE
            and potential_child.device_id == potential_parent.device_id
        ):
            return True

        # Interface down -> Service down
        if (
            potential_parent.event_type == EventType.INTERFACE_STATE_CHANGE
            and potential_parent.current_state == "down"
            and potential_child.event_type == EventType.SERVICE_STATE_CHANGE
        ):
            return True

        return False

    async def _apply_event_rules(self, event: NetworkEvent) -> list[dict[str, Any]]:
        """Apply event processing rules."""
        rules = (
            self.db.query(EventRule)
            .filter(
                and_(
                    EventRule.tenant_id == self.tenant_id,
                    EventRule.is_enabled == "true",
                )
            )
            .all()
        )

        applied_actions = []

        for rule in rules:
            try:
                if await self._event_matches_rule(event, rule):
                    action_result = await self._execute_rule_action(event, rule)
                    applied_actions.append(action_result)
            except Exception as e:
                logger.error(f"Error applying rule {rule.rule_id}: {str(e)}")

        return applied_actions

    async def _event_matches_rule(self, event: NetworkEvent, rule: EventRule) -> bool:
        """Check if event matches rule criteria."""
        # Simple pattern matching - can be enhanced
        if rule.event_type_pattern and rule.event_type_pattern != event.event_type:
            return False

        if rule.severity_filter and event.severity not in rule.severity_filter:
            return False

        # Device filter matching
        if rule.device_filter:
            device_criteria = rule.device_filter
            if "device_type" in device_criteria and event.raw_data:
                event_device_type = event.raw_data.get("device_type")
                if event_device_type != device_criteria["device_type"]:
                    return False

        return True

    async def _execute_rule_action(
        self, event: NetworkEvent, rule: EventRule
    ) -> dict[str, Any]:
        """Execute rule action."""
        action_result = {
            "rule_id": rule.rule_id,
            "rule_name": rule.name,
            "action_type": rule.action_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "success": True,
            "details": {},
        }

        try:
            if rule.action_type == "suppress":
                # Suppress similar events
                action_result["details"]["suppressed_similar_events"] = True

            elif rule.action_type == "escalate":
                # Escalate event severity
                original_severity = event.severity
                event.severity = rule.action_config.get("target_severity", "high")
                action_result["details"]["escalated_from"] = original_severity
                action_result["details"]["escalated_to"] = event.severity

            elif rule.action_type == "correlate":
                # Force correlation with specific pattern
                action_result["details"]["forced_correlation"] = True

            elif rule.action_type == "notify":
                # Send notification (placeholder)
                action_result["details"]["notification_sent"] = True
                action_result["details"]["notification_type"] = rule.action_config.get(
                    "notification_type", "email"
                )

        except Exception as e:
            action_result["success"] = False
            action_result["error"] = str(e)

        return action_result

    async def _identify_event_patterns(
        self, events: list[NetworkEvent]
    ) -> list[dict[str, Any]]:
        """Identify patterns in event data."""
        patterns = []

        # Pattern: Repeated events from same device
        device_counts = {}
        for event in events:
            if event.device_id:
                device_counts[event.device_id] = (
                    device_counts.get(event.device_id, 0) + 1
                )

        for device_id, count in device_counts.items():
            if count >= 10:  # Threshold for pattern detection
                patterns.append(
                    {
                        "pattern_type": "repeated_device_events",
                        "device_id": device_id,
                        "event_count": count,
                        "severity": "high" if count >= 20 else "medium",
                    }
                )

        # Pattern: Event type frequency
        type_counts = {}
        for event in events:
            type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1

        for event_type, count in type_counts.items():
            if count >= 15:
                patterns.append(
                    {
                        "pattern_type": "high_frequency_event_type",
                        "event_type": event_type,
                        "event_count": count,
                        "severity": "medium",
                    }
                )

        return patterns

    async def _detect_event_anomalies(
        self, events: list[NetworkEvent]
    ) -> list[dict[str, Any]]:
        """Detect anomalies in event patterns."""
        anomalies = []

        # Anomaly: Sudden spike in events
        hourly_counts = {}
        for event in events:
            hour_key = event.event_timestamp.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1

        if hourly_counts:
            avg_per_hour = sum(hourly_counts.values()) / len(hourly_counts)
            for hour, count in hourly_counts.items():
                if count > avg_per_hour * 3:  # 3x average is anomaly
                    anomalies.append(
                        {
                            "anomaly_type": "event_spike",
                            "time_period": hour,
                            "event_count": count,
                            "average_count": round(avg_per_hour, 2),
                            "severity": "high",
                        }
                    )

        return anomalies

    async def _analyze_event_correlations(
        self, events: list[NetworkEvent]
    ) -> dict[str, Any]:
        """Analyze correlation statistics."""
        correlations = {
            "total_correlated_events": 0,
            "unique_correlations": set(),
            "correlation_groups": {},
        }

        for event in events:
            if event.correlation_id:
                correlations["total_correlated_events"] += 1
                correlations["unique_correlations"].add(event.correlation_id)

                if event.correlation_id not in correlations["correlation_groups"]:
                    correlations["correlation_groups"][event.correlation_id] = []
                correlations["correlation_groups"][event.correlation_id].append(
                    event.event_id
                )

        correlations["unique_correlations"] = len(correlations["unique_correlations"])
        correlations["uncorrelated_events"] = (
            len(events) - correlations["total_correlated_events"]
        )

        return correlations

    async def _build_event_hierarchy(
        self, events: list[NetworkEvent]
    ) -> dict[str, Any]:
        """Build hierarchical representation of events."""
        hierarchy = {
            "root_events": [],
            "parent_child_relationships": {},
            "orphaned_events": [],
        }

        event_dict = {event.event_id: event for event in events}

        for event in events:
            if event.parent_event_id and event.parent_event_id in event_dict:
                # This is a child event
                parent_id = event.parent_event_id
                if parent_id not in hierarchy["parent_child_relationships"]:
                    hierarchy["parent_child_relationships"][parent_id] = []
                hierarchy["parent_child_relationships"][parent_id].append(
                    event.event_id
                )
            elif not event.parent_event_id:
                # This is a root event
                hierarchy["root_events"].append(event.event_id)
            else:
                # Parent not found - orphaned
                hierarchy["orphaned_events"].append(event.event_id)

        return hierarchy
