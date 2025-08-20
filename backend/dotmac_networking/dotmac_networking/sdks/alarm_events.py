"""
Alarm Events SDK - normalize traps/syslog to events, alarm management
"""

import re
from datetime import datetime
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import AlarmError, AlarmStormDetectedError


class AlarmEventsService:
    """In-memory service for alarm and event operations."""

    def __init__(self):
        self._alarms: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []
        self._alarm_rules: Dict[str, Dict[str, Any]] = {}
        self._suppressions: Dict[str, Dict[str, Any]] = {}
        self._device_alarms: Dict[str, List[str]] = {}

    async def create_alarm_rule(self, **kwargs) -> Dict[str, Any]:
        """Create alarm rule for event processing."""
        rule_id = kwargs.get("rule_id") or str(uuid4())

        rule = {
            "rule_id": rule_id,
            "rule_name": kwargs["rule_name"],
            "event_type": kwargs.get("event_type", "snmp_trap"),
            "match_criteria": kwargs.get("match_criteria", {}),
            "severity": kwargs.get("severity", "warning"),
            "alarm_type": kwargs.get("alarm_type", "equipment"),
            "auto_clear": kwargs.get("auto_clear", False),
            "clear_conditions": kwargs.get("clear_conditions", {}),
            "description_template": kwargs.get("description_template", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._alarm_rules[rule_id] = rule
        return rule

    async def process_snmp_trap(self, **kwargs) -> Dict[str, Any]:
        """Process SNMP trap and generate alarm if needed."""
        event_id = str(uuid4())

        event = {
            "event_id": event_id,
            "event_type": "snmp_trap",
            "source_device": kwargs.get("source_device", ""),
            "source_ip": kwargs.get("source_ip", ""),
            "trap_oid": kwargs.get("trap_oid", ""),
            "varbinds": kwargs.get("varbinds", {}),
            "timestamp": utc_now().isoformat(),
            "raw_data": kwargs.get("raw_data", ""),
        }

        self._events.append(event)

        # Check alarm rules
        matching_rules = self._find_matching_rules(event)

        alarms_created = []
        for rule in matching_rules:
            alarm = await self._create_alarm_from_event(event, rule)
            if alarm:
                alarms_created.append(alarm)

        return {
            "event_id": event_id,
            "processed_at": utc_now().isoformat(),
            "alarms_created": len(alarms_created),
            "alarm_ids": [alarm["alarm_id"] for alarm in alarms_created],
        }

    async def process_syslog_message(self, **kwargs) -> Dict[str, Any]:
        """Process syslog message and generate alarm if needed."""
        event_id = str(uuid4())

        event = {
            "event_id": event_id,
            "event_type": "syslog",
            "source_device": kwargs.get("source_device", ""),
            "source_ip": kwargs.get("source_ip", ""),
            "facility": kwargs.get("facility", 16),
            "severity": kwargs.get("severity", 6),
            "message": kwargs.get("message", ""),
            "timestamp": utc_now().isoformat(),
            "raw_data": kwargs.get("raw_data", ""),
        }

        self._events.append(event)

        # Check alarm rules
        matching_rules = self._find_matching_rules(event)

        alarms_created = []
        for rule in matching_rules:
            alarm = await self._create_alarm_from_event(event, rule)
            if alarm:
                alarms_created.append(alarm)

        return {
            "event_id": event_id,
            "processed_at": utc_now().isoformat(),
            "alarms_created": len(alarms_created),
            "alarm_ids": [alarm["alarm_id"] for alarm in alarms_created],
        }

    def _find_matching_rules(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find alarm rules that match the event."""
        matching_rules = []

        for rule in self._alarm_rules.values():
            if rule["status"] != "active":
                continue

            if rule["event_type"] != event["event_type"]:
                continue

            # Check match criteria
            match_criteria = rule["match_criteria"]
            matches = True

            for key, pattern in match_criteria.items():
                if key not in event:
                    matches = False
                    break

                if isinstance(pattern, str) and not re.search(pattern, str(event[key])) or not isinstance(pattern, str) and event[key] != pattern:
                    matches = False
                    break

            if matches:
                matching_rules.append(rule)

        return matching_rules

    async def _create_alarm_from_event(self, event: Dict[str, Any], rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create alarm from event using rule."""
        device_id = event.get("source_device", "")

        # Check for alarm storm
        if device_id:
            recent_alarms = self._get_recent_alarms_for_device(device_id, minutes=5)
            if len(recent_alarms) > 10:
                raise AlarmStormDetectedError(device_id, len(recent_alarms), 300)

        # Check if alarm is suppressed
        if self._is_alarm_suppressed(device_id, rule["alarm_type"]):
            return None

        alarm_id = str(uuid4())

        # Generate description from template
        description = rule["description_template"]
        for key, value in event.items():
            description = description.replace(f"{{{key}}}", str(value))

        alarm = {
            "alarm_id": alarm_id,
            "device_id": device_id,
            "alarm_type": rule["alarm_type"],
            "severity": rule["severity"],
            "title": rule["rule_name"],
            "description": description,
            "source_event_id": event["event_id"],
            "status": "active",
            "acknowledged": False,
            "auto_clear": rule["auto_clear"],
            "clear_conditions": rule["clear_conditions"],
            "raised_at": utc_now().isoformat(),
            "acknowledged_at": None,
            "cleared_at": None,
            "acknowledged_by": None,
        }

        self._alarms[alarm_id] = alarm

        # Index by device
        if device_id not in self._device_alarms:
            self._device_alarms[device_id] = []
        self._device_alarms[device_id].append(alarm_id)

        return alarm

    def _get_recent_alarms_for_device(self, device_id: str, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get recent alarms for device."""
        cutoff_time = utc_now().timestamp() - (minutes * 60)

        device_alarm_ids = self._device_alarms.get(device_id, [])
        recent_alarms = []

        for alarm_id in device_alarm_ids:
            alarm = self._alarms.get(alarm_id)
            if alarm:
                alarm_time = datetime.fromisoformat(alarm["raised_at"]).timestamp()
                if alarm_time >= cutoff_time:
                    recent_alarms.append(alarm)

        return recent_alarms

    def _is_alarm_suppressed(self, device_id: str, alarm_type: str) -> bool:
        """Check if alarm is suppressed."""
        for suppression in self._suppressions.values():
            if suppression["status"] != "active":
                continue

            if suppression.get("device_id") == device_id or suppression.get("device_id") == "*":
                if suppression.get("alarm_type") == alarm_type or suppression.get("alarm_type") == "*":
                    # Check if suppression is still valid
                    if suppression.get("expires_at"):
                        expires_at = datetime.fromisoformat(suppression["expires_at"])
                        if utc_now() > expires_at:
                            suppression["status"] = "expired"
                            continue

                    return True

        return False


class AlarmEventsSDK:
    """Minimal, reusable SDK for alarm and event management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = AlarmEventsService()

    async def create_snmp_alarm_rule(
        self,
        rule_name: str,
        trap_oid: str,
        severity: str = "warning",
        alarm_type: str = "equipment",
        description_template: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create SNMP trap alarm rule."""
        match_criteria = {
            "trap_oid": trap_oid,
        }

        rule = await self._service.create_alarm_rule(
            rule_name=rule_name,
            event_type="snmp_trap",
            match_criteria=match_criteria,
            severity=severity,
            alarm_type=alarm_type,
            description_template=description_template or f"SNMP alarm: {rule_name}",
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "event_type": rule["event_type"],
            "match_criteria": rule["match_criteria"],
            "severity": rule["severity"],
            "alarm_type": rule["alarm_type"],
            "auto_clear": rule["auto_clear"],
            "status": rule["status"],
            "created_at": rule["created_at"],
        }

    async def create_syslog_alarm_rule(
        self,
        rule_name: str,
        message_pattern: str,
        severity: str = "warning",
        alarm_type: str = "system",
        description_template: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create syslog message alarm rule."""
        match_criteria = {
            "message": message_pattern,
        }

        rule = await self._service.create_alarm_rule(
            rule_name=rule_name,
            event_type="syslog",
            match_criteria=match_criteria,
            severity=severity,
            alarm_type=alarm_type,
            description_template=description_template or f"Syslog alarm: {rule_name}",
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "event_type": rule["event_type"],
            "match_criteria": rule["match_criteria"],
            "severity": rule["severity"],
            "alarm_type": rule["alarm_type"],
            "status": rule["status"],
            "created_at": rule["created_at"],
        }

    async def process_snmp_trap(
        self,
        source_device: str,
        source_ip: str,
        trap_oid: str,
        varbinds: Dict[str, Any],
        raw_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process incoming SNMP trap."""
        result = await self._service.process_snmp_trap(
            source_device=source_device,
            source_ip=source_ip,
            trap_oid=trap_oid,
            varbinds=varbinds,
            raw_data=raw_data
        )

        return {
            "event_id": result["event_id"],
            "processed_at": result["processed_at"],
            "alarms_created": result["alarms_created"],
            "alarm_ids": result["alarm_ids"],
        }

    async def process_syslog_message(
        self,
        source_device: str,
        source_ip: str,
        message: str,
        facility: int = 16,
        severity: int = 6,
        raw_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process incoming syslog message."""
        result = await self._service.process_syslog_message(
            source_device=source_device,
            source_ip=source_ip,
            facility=facility,
            severity=severity,
            message=message,
            raw_data=raw_data
        )

        return {
            "event_id": result["event_id"],
            "processed_at": result["processed_at"],
            "alarms_created": result["alarms_created"],
            "alarm_ids": result["alarm_ids"],
        }

    async def acknowledge_alarm(self, alarm_id: str, acknowledged_by: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Acknowledge alarm."""
        if alarm_id not in self._service._alarms:
            raise AlarmError(f"Alarm not found: {alarm_id}")

        alarm = self._service._alarms[alarm_id]

        if alarm["acknowledged"]:
            raise AlarmError(f"Alarm already acknowledged: {alarm_id}")

        alarm["acknowledged"] = True
        alarm["acknowledged_by"] = acknowledged_by
        alarm["acknowledged_at"] = utc_now().isoformat()
        alarm["ack_comments"] = comments

        return {
            "alarm_id": alarm_id,
            "acknowledged": True,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": alarm["acknowledged_at"],
            "comments": comments,
        }

    async def clear_alarm(self, alarm_id: str, cleared_by: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Clear alarm."""
        if alarm_id not in self._service._alarms:
            raise AlarmError(f"Alarm not found: {alarm_id}")

        alarm = self._service._alarms[alarm_id]

        if alarm["status"] == "cleared":
            raise AlarmError(f"Alarm already cleared: {alarm_id}")

        alarm["status"] = "cleared"
        alarm["cleared_by"] = cleared_by
        alarm["cleared_at"] = utc_now().isoformat()
        alarm["clear_comments"] = comments

        return {
            "alarm_id": alarm_id,
            "status": "cleared",
            "cleared_by": cleared_by,
            "cleared_at": alarm["cleared_at"],
            "comments": comments,
        }

    async def suppress_alarms(
        self,
        device_id: str,
        alarm_type: str = "*",
        duration_minutes: int = 60,
        reason: Optional[str] = None,
        suppressed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suppress alarms for device/type."""
        suppression_id = str(uuid4())

        expires_at = utc_now() + timedelta(minutes=duration_minutes)

        suppression = {
            "suppression_id": suppression_id,
            "device_id": device_id,
            "alarm_type": alarm_type,
            "reason": reason,
            "suppressed_by": suppressed_by,
            "duration_minutes": duration_minutes,
            "expires_at": expires_at.isoformat(),
            "status": "active",
            "created_at": utc_now().isoformat(),
        }

        self._service._suppressions[suppression_id] = suppression

        return {
            "suppression_id": suppression_id,
            "device_id": device_id,
            "alarm_type": alarm_type,
            "duration_minutes": duration_minutes,
            "expires_at": suppression["expires_at"],
            "status": "active",
            "created_at": suppression["created_at"],
        }

    async def get_active_alarms(self, device_id: Optional[str] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active alarms."""
        alarms = [
            alarm for alarm in self._service._alarms.values()
            if alarm["status"] == "active"
        ]

        if device_id:
            alarms = [alarm for alarm in alarms if alarm["device_id"] == device_id]

        if severity:
            alarms = [alarm for alarm in alarms if alarm["severity"] == severity]

        return [
            {
                "alarm_id": alarm["alarm_id"],
                "device_id": alarm["device_id"],
                "alarm_type": alarm["alarm_type"],
                "severity": alarm["severity"],
                "title": alarm["title"],
                "description": alarm["description"],
                "acknowledged": alarm["acknowledged"],
                "raised_at": alarm["raised_at"],
                "acknowledged_at": alarm["acknowledged_at"],
                "acknowledged_by": alarm["acknowledged_by"],
            }
            for alarm in sorted(alarms, key=lambda a: a["raised_at"], reverse=True)
        ]

    async def get_alarm_statistics(self, device_id: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get alarm statistics."""
        cutoff_time = utc_now() - timedelta(hours=hours)

        alarms = list(self._service._alarms.values())

        if device_id:
            alarms = [alarm for alarm in alarms if alarm["device_id"] == device_id]

        # Filter by time period
        recent_alarms = [
            alarm for alarm in alarms
            if datetime.fromisoformat(alarm["raised_at"]) >= cutoff_time
        ]

        # Count by severity
        severity_counts = {}
        for alarm in recent_alarms:
            severity = alarm["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count by type
        type_counts = {}
        for alarm in recent_alarms:
            alarm_type = alarm["alarm_type"]
            type_counts[alarm_type] = type_counts.get(alarm_type, 0) + 1

        active_alarms = [alarm for alarm in alarms if alarm["status"] == "active"]
        acknowledged_alarms = [alarm for alarm in active_alarms if alarm["acknowledged"]]

        return {
            "total_alarms": len(recent_alarms),
            "active_alarms": len(active_alarms),
            "acknowledged_alarms": len(acknowledged_alarms),
            "unacknowledged_alarms": len(active_alarms) - len(acknowledged_alarms),
            "severity_distribution": severity_counts,
            "type_distribution": type_counts,
            "time_period_hours": hours,
            "generated_at": utc_now().isoformat(),
        }
