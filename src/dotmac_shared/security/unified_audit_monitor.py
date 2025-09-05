"""
Unified audit and security monitoring system with DRY patterns.
Consolidates audit logging and security monitoring across all DotMac platforms.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.application import standard_exception_handler
from dotmac.communications.events import EventBus
from dotmac.core import create_cache_service
from dotmac.core.schemas.base_schemas import BaseSchema, TenantMixin
from dotmac.security.audit import (
    AuditEventType,
    AuditLogger,
    AuditOutcome,
    AuditSeverity,
    create_audit_logger,
)
from dotmac_shared.application.config import DeploymentContext
from dotmac_shared.services_framework.core.base import ServiceHealth, ServiceStatus, StatefulService
from pydantic import Field

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Types of security events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_TIMEOUT = "session_timeout"
    MFA_SUCCESS = "mfa_success"
    MFA_FAILURE = "mfa_failure"
    PASSWORD_CHANGE = "password_change"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ROLE_CHANGE = "role_change"

    # Data access events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"

    # System events
    SYSTEM_ACCESS = "system_access"
    CONFIG_CHANGE = "config_change"
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"

    # Security incidents
    INTRUSION_ATTEMPT = "intrusion_attempt"
    MALWARE_DETECTED = "malware_detected"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    POLICY_VIOLATION = "policy_violation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    BRUTE_FORCE_ATTACK = "brute_force_attack"


class SecurityThreatLevel(str, Enum):
    """Security threat levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(BaseSchema, TenantMixin):
    """Unified security event record."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: SecurityEventType = Field(..., description="Type of security event")
    threat_level: SecurityThreatLevel = Field(..., description="Threat level")

    # Actor information
    user_id: Optional[UUID] = Field(None, description="User identifier")
    username: Optional[str] = Field(None, description="Username")
    user_role: Optional[str] = Field(None, description="User role")
    session_id: Optional[str] = Field(None, description="Session identifier")

    # Network information
    source_ip: str = Field(..., description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    geo_location: Optional[dict[str, str]] = Field(None, description="Geographic location")

    # Resource information
    resource_id: Optional[str] = Field(None, description="Affected resource ID")
    resource_type: Optional[str] = Field(None, description="Type of affected resource")
    resource_owner: Optional[str] = Field(None, description="Resource owner")

    # Event details
    action: str = Field(..., description="Action performed")
    outcome: str = Field(..., description="Action outcome")
    description: str = Field(..., description="Event description")

    # Security context
    authentication_method: Optional[str] = Field(None, description="Authentication method used")
    authorization_context: dict[str, Any] = Field(default_factory=dict, description="Authorization context")
    security_context: dict[str, Any] = Field(default_factory=dict, description="Security context")

    # Metadata
    platform: str = Field(..., description="Platform (isp, management, etc.)")
    service: str = Field(..., description="Service generating event")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class SecurityAlert(BaseSchema, TenantMixin):
    """Security alert record."""

    alert_id: UUID = Field(default_factory=uuid4)
    alert_type: str = Field(..., description="Alert type")
    threat_level: SecurityThreatLevel = Field(..., description="Threat level")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")

    # Related events
    triggering_events: list[UUID] = Field(default_factory=list, description="Event IDs that triggered alert")
    event_count: int = Field(default=1, description="Number of related events")

    # Context
    affected_resources: list[str] = Field(default_factory=list, description="Affected resources")
    source_ips: list[str] = Field(default_factory=list, description="Source IP addresses")
    users_affected: list[str] = Field(default_factory=list, description="Affected users")

    # Alert lifecycle
    status: str = Field(default="open", description="Alert status")
    assigned_to: Optional[UUID] = Field(None, description="Assigned analyst")
    acknowledged_by: Optional[UUID] = Field(None, description="User who acknowledged")
    resolved_by: Optional[UUID] = Field(None, description="User who resolved")

    # Timestamps
    triggered_at: datetime = Field(default_factory=datetime.utcnow, description="Alert trigger time")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment time")
    resolved_at: Optional[datetime] = Field(None, description="Resolution time")

    # Response
    recommended_actions: list[str] = Field(default_factory=list, description="Recommended actions")
    mitigation_steps: list[str] = Field(default_factory=list, description="Mitigation steps taken")


@dataclass
class UnifiedAuditConfig:
    """Configuration for unified audit and security monitoring."""

    deployment_context: Optional[DeploymentContext] = None

    # Audit settings
    audit_enabled: bool = True
    security_monitoring_enabled: bool = True
    real_time_alerts: bool = True

    # Storage settings
    event_retention_days: int = 2555  # 7 years for compliance
    alert_retention_days: int = 365
    max_events_in_memory: int = 10000

    # Alert thresholds
    failed_login_threshold: int = 5  # Failed logins before alert
    failed_login_window_minutes: int = 15
    suspicious_ip_threshold: int = 10  # Events from IP before alert
    data_export_alert_threshold: int = 100  # MB exported before alert

    # Performance settings
    batch_size: int = 100
    flush_interval_seconds: int = 30
    cache_ttl_seconds: int = 1800  # 30 minutes

    # Integration settings
    compliance_integration: bool = True
    analytics_integration: bool = True
    notification_channels: list[str] = field(default_factory=lambda: ["email", "webhook"])


class UnifiedAuditMonitor(StatefulService):
    """
    Unified audit and security monitoring service with DRY patterns.
    Consolidates audit logging and security monitoring across all platforms.
    """

    def __init__(self, config: UnifiedAuditConfig):
        """Initialize unified audit monitor."""
        super().__init__(name="unified_audit_monitor", config=config.__dict__, required_config=["audit_enabled"])

        self.audit_config = config
        self.priority = 99  # Highest priority for security

        # Core components
        self.audit_logger: Optional[AuditLogger] = None

        # Service dependencies
        self.event_bus: Optional[EventBus] = None
        self.cache_service = None

        # Security monitoring storage
        self._security_events: list[SecurityEvent] = []
        self._security_alerts: list[SecurityAlert] = []
        self._ip_tracking: dict[str, list[datetime]] = {}
        self._user_tracking: dict[str, list[datetime]] = {}

        # Service statistics
        self._events_processed = 0
        self._alerts_generated = 0
        self._threats_blocked = 0

    async def _initialize_stateful_service(self) -> bool:
        """Initialize unified audit monitor."""
        try:
            # Initialize dependencies
            self.cache_service = create_cache_service()
            if self.cache_service:
                await self.cache_service.initialize()

            # Initialize audit logger
            service_name = "unified_audit_monitor"
            tenant_id = None
            if self.audit_config.deployment_context and hasattr(self.audit_config.deployment_context, "tenant_id"):
                tenant_id = self.audit_config.deployment_context.tenant_id

            self.audit_logger = create_audit_logger(service_name=service_name, tenant_id=tenant_id)

            # Initialize state
            self.set_state("events_processed", 0)
            self.set_state("alerts_generated", 0)
            self.set_state("threats_blocked", 0)
            self.set_state("last_flush", datetime.now(timezone.utc).isoformat())

            await self._set_status(
                ServiceStatus.READY,
                "Unified audit monitor ready",
                {
                    "audit_enabled": self.audit_config.audit_enabled,
                    "security_monitoring": self.audit_config.security_monitoring_enabled,
                    "real_time_alerts": self.audit_config.real_time_alerts,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Failed to initialize unified audit monitor: {e}")
            await self._set_status(ServiceStatus.ERROR, f"Initialization failed: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown unified audit monitor."""
        await self._set_status(ServiceStatus.SHUTTING_DOWN, "Shutting down audit monitor")

        # Flush remaining events
        if self._security_events:
            await self._flush_security_events()

        # Clear state
        self.clear_state()

        await self._set_status(ServiceStatus.SHUTDOWN, "Audit monitor shutdown complete")
        return True

    async def _health_check_stateful_service(self) -> ServiceHealth:
        """Perform health check on unified audit monitor."""
        try:
            details = {
                "events_in_buffer": len(self._security_events),
                "active_alerts": len([a for a in self._security_alerts if a.status == "open"]),
                "events_processed": self.get_state("events_processed", 0),
                "alerts_generated": self.get_state("alerts_generated", 0),
                "threats_blocked": self.get_state("threats_blocked", 0),
                "audit_logger": "available" if self.audit_logger else "unavailable",
                "cache_service": "available" if self.cache_service else "unavailable",
                "last_flush": self.get_state("last_flush"),
            }

            # Check buffer size
            if len(self._security_events) > self.audit_config.max_events_in_memory * 0.9:
                return ServiceHealth(
                    status=ServiceStatus.READY,
                    message=f"High event buffer: {len(self._security_events)} events",
                    details=details,
                )

            return ServiceHealth(status=ServiceStatus.READY, message="Unified audit monitor healthy", details=details)

        except Exception as e:
            return ServiceHealth(
                status=ServiceStatus.ERROR, message=f"Health check failed: {e}", details={"error": str(e)}
            )

    @standard_exception_handler
    async def log_security_event(
        self,
        event_type: SecurityEventType,
        threat_level: SecurityThreatLevel,
        action: str,
        outcome: str,
        description: str,
        source_ip: str,
        platform: str,
        service: str,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Log a security event."""
        if not self.is_ready():
            raise RuntimeError("Unified audit monitor not ready")

        # Get tenant context
        tenant_id = None
        if self.audit_config.deployment_context and hasattr(self.audit_config.deployment_context, "tenant_id"):
            tenant_id = self.audit_config.deployment_context.tenant_id

        # Create security event
        security_event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            user_id=user_id,
            username=username,
            user_role=user_role,
            session_id=session_id,
            source_ip=source_ip,
            user_agent=user_agent,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            outcome=outcome,
            description=description,
            platform=platform,
            service=service,
            metadata=metadata or {},
            tenant_id=tenant_id,
        )

        # Store security event
        self._security_events.append(security_event)

        # Track IP and user activity
        self._track_ip_activity(source_ip)
        if user_id:
            self._track_user_activity(str(user_id))

        # Create corresponding audit event
        if self.audit_logger and self.audit_config.audit_enabled:
            await self._create_audit_event(security_event)

        # Process real-time security monitoring
        if self.audit_config.security_monitoring_enabled:
            await self._process_security_monitoring(security_event)

        # Update statistics
        events_processed = self.get_state("events_processed", 0)
        self.set_state("events_processed", events_processed + 1)
        self._events_processed += 1

        # Flush events if we've reached the batch size
        if len(self._security_events) >= self.audit_config.batch_size:
            await self._flush_security_events()

        # Cache the event
        if self.cache_service:
            cache_key = f"security_event:{tenant_id}:{security_event.event_id}"
            await self.cache_service.set(
                cache_key,
                security_event.model_dump(),
                tenant_id=tenant_id,
                expire=self.audit_config.cache_ttl_seconds,
            )

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "security.event_logged",
                {
                    "event_id": str(security_event.event_id),
                    "event_type": security_event.event_type.value,
                    "threat_level": security_event.threat_level.value,
                    "source_ip": security_event.source_ip,
                    "platform": security_event.platform,
                    "tenant_id": tenant_id,
                },
            )

        return True

    @standard_exception_handler
    async def get_security_dashboard(
        self,
        period_hours: int = 24,
        tenant_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get security monitoring dashboard data."""
        if not self.is_ready():
            raise RuntimeError("Unified audit monitor not ready")

        period_start = datetime.now(timezone.utc) - timedelta(hours=period_hours)

        # Filter events for the period
        filtered_events = [
            event
            for event in self._security_events
            if (event.timestamp >= period_start and (not tenant_id or event.tenant_id == tenant_id))
        ]

        # Calculate dashboard metrics
        dashboard = {
            "period": {
                "start": period_start.isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
                "hours": period_hours,
            },
            "summary": {
                "total_events": len(filtered_events),
                "critical_events": len([e for e in filtered_events if e.threat_level == SecurityThreatLevel.CRITICAL]),
                "high_risk_events": len([e for e in filtered_events if e.threat_level == SecurityThreatLevel.HIGH]),
                "failed_logins": len([e for e in filtered_events if e.event_type == SecurityEventType.LOGIN_FAILURE]),
                "unauthorized_access": len(
                    [e for e in filtered_events if e.event_type == SecurityEventType.ACCESS_DENIED]
                ),
                "active_alerts": len([a for a in self._security_alerts if a.status == "open"]),
            },
            "by_threat_level": {},
            "by_event_type": {},
            "top_source_ips": [],
            "recent_alerts": [],
            "trends": [],
        }

        # Calculate threat level distribution
        for threat_level in SecurityThreatLevel:
            count = len([e for e in filtered_events if e.threat_level == threat_level])
            dashboard["by_threat_level"][threat_level.value] = count

        # Calculate event type distribution
        for event_type in SecurityEventType:
            count = len([e for e in filtered_events if e.event_type == event_type])
            if count > 0:  # Only include types with events
                dashboard["by_event_type"][event_type.value] = count

        # Top source IPs
        ip_counts = {}
        for event in filtered_events:
            ip = event.source_ip
            ip_counts[ip] = ip_counts.get(ip, 0) + 1

        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        dashboard["top_source_ips"] = [{"ip": ip, "count": count} for ip, count in top_ips]

        # Recent alerts
        recent_alerts = [alert for alert in self._security_alerts if alert.triggered_at >= period_start]
        recent_alerts.sort(key=lambda a: a.triggered_at, reverse=True)

        dashboard["recent_alerts"] = [
            {
                "alert_id": str(alert.alert_id),
                "threat_level": alert.threat_level.value,
                "title": alert.title,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat(),
            }
            for alert in recent_alerts[:10]
        ]

        return dashboard

    @standard_exception_handler
    async def get_active_alerts(
        self,
        threat_level: Optional[SecurityThreatLevel] = None,
        tenant_id: Optional[str] = None,
    ) -> list[SecurityAlert]:
        """Get active security alerts."""
        if not self.is_ready():
            raise RuntimeError("Unified audit monitor not ready")

        alerts = [
            alert
            for alert in self._security_alerts
            if (
                alert.status == "open"
                and (not threat_level or alert.threat_level == threat_level)
                and (not tenant_id or alert.tenant_id == tenant_id)
            )
        ]

        # Sort by threat level and timestamp
        threat_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        alerts.sort(key=lambda a: (threat_order.get(a.threat_level.value, 5), a.triggered_at), reverse=True)

        return alerts

    async def _create_audit_event(self, security_event: SecurityEvent):
        """Create corresponding audit event for security event."""

        # Map security event to audit event
        audit_event_type_map = {
            SecurityEventType.LOGIN_SUCCESS: AuditEventType.AUTH_LOGIN,
            SecurityEventType.LOGIN_FAILURE: AuditEventType.AUTH_FAILED,
            SecurityEventType.LOGOUT: AuditEventType.AUTH_LOGOUT,
            SecurityEventType.DATA_ACCESS: AuditEventType.DATA_READ,
            SecurityEventType.DATA_MODIFICATION: AuditEventType.DATA_UPDATE,
            SecurityEventType.DATA_DELETION: AuditEventType.DATA_DELETE,
            SecurityEventType.CONFIG_CHANGE: AuditEventType.SYSTEM_CONFIG_CHANGE,
        }

        audit_event_type = audit_event_type_map.get(
            security_event.event_type,
            AuditEventType.DATA_READ,  # Default
        )

        # Map threat level to audit severity
        severity_map = {
            SecurityThreatLevel.INFO: AuditSeverity.LOW,
            SecurityThreatLevel.LOW: AuditSeverity.LOW,
            SecurityThreatLevel.MEDIUM: AuditSeverity.MEDIUM,
            SecurityThreatLevel.HIGH: AuditSeverity.HIGH,
            SecurityThreatLevel.CRITICAL: AuditSeverity.CRITICAL,
        }

        severity = severity_map.get(security_event.threat_level, AuditSeverity.MEDIUM)
        outcome = AuditOutcome.SUCCESS if security_event.outcome == "success" else AuditOutcome.FAILURE

        # Create audit event
        self.audit_logger.log_event(
            event_type=audit_event_type,
            message=security_event.description,
            severity=severity,
            outcome=outcome,
            custom_attributes={
                "security_event_id": str(security_event.event_id),
                "threat_level": security_event.threat_level.value,
                "source_ip": security_event.source_ip,
                "platform": security_event.platform,
                "service": security_event.service,
            },
        )

    async def _process_security_monitoring(self, event: SecurityEvent):
        """Process security monitoring and generate alerts if needed."""

        # Check for failed login patterns
        if event.event_type == SecurityEventType.LOGIN_FAILURE:
            await self._check_failed_login_alert(event)

        # Check for suspicious IP activity
        await self._check_suspicious_ip_alert(event)

        # Check for data export alerts
        if event.event_type == SecurityEventType.DATA_EXPORT:
            await self._check_data_export_alert(event)

        # Check for privilege escalation
        if event.event_type == SecurityEventType.PRIVILEGE_ESCALATION:
            await self._generate_security_alert(
                "privilege_escalation",
                SecurityThreatLevel.HIGH,
                "Privilege Escalation Detected",
                f"User {event.username} escalated privileges",
                [event.event_id],
            )

    async def _check_failed_login_alert(self, event: SecurityEvent):
        """Check for failed login patterns and generate alerts."""

        # Count failed logins from this IP in the time window
        window_start = datetime.now(timezone.utc) - timedelta(minutes=self.audit_config.failed_login_window_minutes)

        failed_logins = [
            e
            for e in self._security_events
            if (
                e.event_type == SecurityEventType.LOGIN_FAILURE
                and e.source_ip == event.source_ip
                and e.timestamp >= window_start
            )
        ]

        if len(failed_logins) >= self.audit_config.failed_login_threshold:
            await self._generate_security_alert(
                "brute_force_attack",
                SecurityThreatLevel.HIGH,
                "Potential Brute Force Attack",
                f"Multiple failed login attempts from IP {event.source_ip}",
                [e.event_id for e in failed_logins],
            )

    async def _check_suspicious_ip_alert(self, event: SecurityEvent):
        """Check for suspicious IP activity patterns."""

        ip_events = [e for e in self._security_events if e.source_ip == event.source_ip]

        if len(ip_events) >= self.audit_config.suspicious_ip_threshold:
            # Check if IP has high-risk activities
            high_risk_events = [
                e for e in ip_events if e.threat_level in [SecurityThreatLevel.HIGH, SecurityThreatLevel.CRITICAL]
            ]

            if len(high_risk_events) > 0:
                await self._generate_security_alert(
                    "suspicious_ip",
                    SecurityThreatLevel.MEDIUM,
                    "Suspicious IP Activity",
                    f"IP {event.source_ip} showing suspicious patterns",
                    [e.event_id for e in high_risk_events[-5:]],  # Last 5 events
                )

    async def _check_data_export_alert(self, event: SecurityEvent):
        """Check for large data export activities."""

        export_size = event.metadata.get("export_size_mb", 0)

        if export_size >= self.audit_config.data_export_alert_threshold:
            await self._generate_security_alert(
                "large_data_export",
                SecurityThreatLevel.MEDIUM,
                "Large Data Export Detected",
                f"User {event.username} exported {export_size}MB of data",
                [event.event_id],
            )

    async def _generate_security_alert(
        self,
        alert_type: str,
        threat_level: SecurityThreatLevel,
        title: str,
        description: str,
        triggering_events: list[UUID],
    ):
        """Generate a security alert."""

        # Get tenant context
        tenant_id = None
        if self.audit_config.deployment_context and hasattr(self.audit_config.deployment_context, "tenant_id"):
            tenant_id = self.audit_config.deployment_context.tenant_id

        # Create security alert
        alert = SecurityAlert(
            alert_type=alert_type,
            threat_level=threat_level,
            title=title,
            description=description,
            triggering_events=triggering_events,
            event_count=len(triggering_events),
            tenant_id=tenant_id,
        )

        # Extract context from triggering events
        events = [e for e in self._security_events if e.event_id in triggering_events]

        alert.source_ips = list({e.source_ip for e in events})
        alert.users_affected = list({e.username for e in events if e.username})
        alert.affected_resources = list({e.resource_id for e in events if e.resource_id})

        # Add recommended actions based on alert type
        if alert_type == "brute_force_attack":
            alert.recommended_actions = [
                "Block source IP address",
                "Review user accounts for compromise",
                "Enable additional authentication factors",
            ]
        elif alert_type == "suspicious_ip":
            alert.recommended_actions = [
                "Investigate IP address reputation",
                "Review all activities from this IP",
                "Consider temporary IP blocking",
            ]
        elif alert_type == "large_data_export":
            alert.recommended_actions = [
                "Verify export authorization",
                "Review data classification",
                "Contact user for validation",
            ]

        # Store alert
        self._security_alerts.append(alert)

        # Update statistics
        alerts_generated = self.get_state("alerts_generated", 0)
        self.set_state("alerts_generated", alerts_generated + 1)
        self._alerts_generated += 1

        # Publish alert
        if self.event_bus:
            await self.event_bus.publish(
                "security.alert_generated",
                {
                    "alert_id": str(alert.alert_id),
                    "alert_type": alert.alert_type,
                    "threat_level": alert.threat_level.value,
                    "title": alert.title,
                    "event_count": alert.event_count,
                    "tenant_id": tenant_id,
                },
            )

        logger.warning(f"Security alert generated: {title} (Level: {threat_level.value})")

    def _track_ip_activity(self, ip_address: str):
        """Track IP address activity for pattern detection."""

        now = datetime.now(timezone.utc)

        if ip_address not in self._ip_tracking:
            self._ip_tracking[ip_address] = []

        # Add current timestamp
        self._ip_tracking[ip_address].append(now)

        # Clean old entries (keep last 24 hours)
        cutoff = now - timedelta(hours=24)
        self._ip_tracking[ip_address] = [ts for ts in self._ip_tracking[ip_address] if ts >= cutoff]

    def _track_user_activity(self, user_id: str):
        """Track user activity for pattern detection."""

        now = datetime.now(timezone.utc)

        if user_id not in self._user_tracking:
            self._user_tracking[user_id] = []

        # Add current timestamp
        self._user_tracking[user_id].append(now)

        # Clean old entries (keep last 24 hours)
        cutoff = now - timedelta(hours=24)
        self._user_tracking[user_id] = [ts for ts in self._user_tracking[user_id] if ts >= cutoff]

    async def _flush_security_events(self):
        """Flush security events to storage."""

        if not self._security_events:
            return

        # In production, this would write to database/long-term storage
        events_to_flush = self._security_events.copy()

        # Clear buffer
        self._security_events.clear()

        # Update flush timestamp
        self.set_state("last_flush", datetime.now(timezone.utc).isoformat())

        logger.info(f"Flushed {len(events_to_flush)} security events")


# Factory function
async def create_unified_audit_monitor(config: UnifiedAuditConfig) -> UnifiedAuditMonitor:
    """Create and initialize unified audit monitor."""
    service = UnifiedAuditMonitor(config)

    # Service will be initialized by the registry
    return service
