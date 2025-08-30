"""
Audit API implementation for DotMac monitoring system.

This module provides comprehensive audit trail functionality including:
- Event tracking and storage
- User action auditing
- System event logging
- Compliance reporting
- Real-time audit streaming
"""

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .utils import ValidationError, get_current_timestamp, get_logger, sanitize_dict

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events that can be tracked."""

    # Authentication events
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_TOKEN_REFRESH = "auth.token_refresh"
    AUTH_PASSWORD_CHANGE = "auth.password_change"
    AUTH_MFA_ENABLED = "auth.mfa_enabled"
    AUTH_MFA_DISABLED = "auth.mfa_disabled"

    # Authorization events
    AUTHZ_PERMISSION_GRANTED = "authz.permission_granted"
    AUTHZ_PERMISSION_DENIED = "authz.permission_denied"
    AUTHZ_ROLE_ASSIGNED = "authz.role_assigned"
    AUTHZ_ROLE_REMOVED = "authz.role_removed"

    # Data access events
    DATA_CREATE = "data.create"
    DATA_READ = "data.read"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"

    # System events
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_CONFIG_CHANGE = "system.config_change"
    SYSTEM_BACKUP = "system.backup"
    SYSTEM_RESTORE = "system.restore"

    # Business events
    BUSINESS_CUSTOMER_CREATED = "business.customer_created"
    BUSINESS_INVOICE_GENERATED = "business.invoice_generated"
    BUSINESS_PAYMENT_PROCESSED = "business.payment_processed"
    BUSINESS_SERVICE_ACTIVATED = "business.service_activated"
    BUSINESS_SERVICE_SUSPENDED = "business.service_suspended"

    # Security events
    SECURITY_INTRUSION_DETECTED = "security.intrusion_detected"
    SECURITY_VULNERABILITY_FOUND = "security.vulnerability_found"
    SECURITY_POLICY_VIOLATION = "security.policy_violation"
    SECURITY_CERTIFICATE_RENEWED = "security.certificate_renewed"


class AuditSeverity(Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditOutcome(Enum):
    """Outcome of audited operations."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class AuditContext:
    """Context information for audit events."""

    # Request context
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    # Network context
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    forwarded_for: Optional[str] = None

    # Application context
    service_name: Optional[str] = None
    service_version: Optional[str] = None
    environment: Optional[str] = None

    # Geographic context
    country: Optional[str] = None
    city: Optional[str] = None
    timezone: Optional[str] = None


@dataclass
class AuditActor:
    """Actor (user, system, or service) performing the audited action."""

    # Identity information
    actor_id: str
    actor_type: str  # user, system, service, api_key
    actor_name: Optional[str] = None

    # User-specific information
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)

    # Session information
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # System/service information
    service_account: Optional[str] = None
    api_key_id: Optional[str] = None


@dataclass
class AuditResource:
    """Resource being accessed or modified in the audit event."""

    # Resource identification
    resource_id: Optional[str] = None
    resource_type: str = "unknown"
    resource_name: Optional[str] = None

    # Resource metadata
    parent_resource_id: Optional[str] = None
    resource_attributes: Dict[str, Any] = field(default_factory=dict)

    # Data sensitivity
    classification: Optional[str] = None  # public, internal, confidential, restricted
    contains_pii: bool = False


@dataclass
class AuditEvent:
    """Complete audit event record."""

    # Event identification
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.DATA_READ
    event_name: Optional[str] = None

    # Timing
    timestamp: float = field(default_factory=get_current_timestamp)
    duration_ms: Optional[float] = None

    # Event details
    severity: AuditSeverity = AuditSeverity.LOW
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    message: str = ""
    description: Optional[str] = None

    # Event participants
    actor: Optional[AuditActor] = None
    resource: Optional[AuditResource] = None
    context: Optional[AuditContext] = None

    # Event data
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    changes: Optional[Dict[str, Any]] = None

    # Additional metadata
    tags: Dict[str, str] = field(default_factory=dict)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    # Risk and compliance
    risk_score: Optional[int] = None  # 0-100
    compliance_frameworks: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization processing."""
        if not self.event_name:
            self.event_name = self.event_type.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for storage/transmission."""

        def serialize_dataclass(obj):
            if hasattr(obj, "__dataclass_fields__"):
                return {
                    k: serialize_dataclass(v)
                    for k, v in obj.__dict__.items()
                    if v is not None
                }
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, list):
                return [serialize_dataclass(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: serialize_dataclass(v) for k, v in obj.items()}
            else:
                return obj

        return serialize_dataclass(self)

    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str, separators=(",", ":"))


class AuditStore:
    """Abstract base class for audit event storage backends."""

    def store_event(self, event: AuditEvent) -> bool:
        """Store a single audit event."""
        raise NotImplementedError

    def store_events(self, events: List[AuditEvent]) -> int:
        """Store multiple audit events. Returns number of events successfully stored."""
        raise NotImplementedError

    def query_events(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_types: Optional[List[AuditEventType]] = None,
        actor_ids: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """Query stored audit events."""
        raise NotImplementedError


class InMemoryAuditStore(AuditStore):
    """In-memory audit store for testing and development."""

    def __init__(self, max_events: int = 10000):
        self.events: List[AuditEvent] = []
        self.max_events = max_events

    def store_event(self, event: AuditEvent) -> bool:
        """Store audit event in memory."""
        try:
            self.events.append(event)
            # Maintain maximum events limit
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events :]
            return True
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
            return False

    def store_events(self, events: List[AuditEvent]) -> int:
        """Store multiple audit events in memory."""
        stored = 0
        for event in events:
            if self.store_event(event):
                stored += 1
        return stored

    def query_events(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_types: Optional[List[AuditEventType]] = None,
        actor_ids: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """Query audit events from memory."""
        filtered_events = self.events

        # Apply filters
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        if event_types:
            filtered_events = [
                e for e in filtered_events if e.event_type in event_types
            ]
        if actor_ids and any(e.actor for e in filtered_events):
            filtered_events = [
                e for e in filtered_events if e.actor and e.actor.actor_id in actor_ids
            ]
        if resource_types and any(e.resource for e in filtered_events):
            filtered_events = [
                e
                for e in filtered_events
                if e.resource and e.resource.resource_type in resource_types
            ]
        if tenant_id and any(e.actor for e in filtered_events):
            filtered_events = [
                e for e in filtered_events if e.actor and e.actor.tenant_id == tenant_id
            ]

        # Sort by timestamp (newest first)
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        return filtered_events[offset : offset + limit]


class AuditLogger:
    """Main audit logging service."""

    def __init__(
        self,
        store: Optional[AuditStore] = None,
        service_name: str = "dotmac-service",
        tenant_id: Optional[str] = None,
    ):
        self.store = store or InMemoryAuditStore()
        self.service_name = service_name
        self.tenant_id = tenant_id
        self._default_context = AuditContext(
            service_name=service_name,
            environment="development",  # Should be configurable
        )

    def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        actor: Optional[AuditActor] = None,
        resource: Optional[AuditResource] = None,
        context: Optional[AuditContext] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        **kwargs,
    ) -> AuditEvent:
        """Log an audit event."""

        # Merge context with defaults
        effective_context = self._merge_context(context)

        # Create audit event
        event = AuditEvent(
            event_type=event_type,
            message=message,
            actor=actor,
            resource=resource,
            context=effective_context,
            severity=severity,
            outcome=outcome,
            **kwargs,
        )

        # Store the event
        try:
            self.store.store_event(event)
            logger.debug(f"Audit event logged: {event.event_id}")
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")

        return event

    def log_auth_event(
        self,
        event_type: AuditEventType,
        actor_id: str,
        outcome: AuditOutcome,
        message: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs,
    ) -> AuditEvent:
        """Log authentication-related audit event."""

        actor = AuditActor(
            actor_id=actor_id, actor_type="user", tenant_id=self.tenant_id
        )

        context = AuditContext(
            client_ip=client_ip, user_agent=user_agent, service_name=self.service_name
        )

        severity = (
            AuditSeverity.HIGH
            if outcome == AuditOutcome.FAILURE
            else AuditSeverity.MEDIUM
        )

        return self.log_event(
            event_type=event_type,
            message=message,
            actor=actor,
            context=context,
            severity=severity,
            outcome=outcome,
            **kwargs,
        )

    def log_data_access(
        self,
        operation: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None,
        **kwargs,
    ) -> AuditEvent:
        """Log data access audit event."""

        # Map operation to event type
        event_type_map = {
            "create": AuditEventType.DATA_CREATE,
            "read": AuditEventType.DATA_READ,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
        }
        event_type = event_type_map.get(operation.lower(), AuditEventType.DATA_READ)

        actor = AuditActor(
            actor_id=actor_id, actor_type="user", tenant_id=self.tenant_id
        )

        resource = AuditResource(resource_id=resource_id, resource_type=resource_type)

        message = f"{operation.title()} {resource_type} {resource_id}"
        severity = (
            AuditSeverity.HIGH
            if operation.lower() == "delete"
            else AuditSeverity.MEDIUM
        )

        return self.log_event(
            event_type=event_type,
            message=message,
            actor=actor,
            resource=resource,
            severity=severity,
            outcome=outcome,
            before_state=before_state,
            after_state=after_state,
            **kwargs,
        )

    def log_system_event(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        **kwargs,
    ) -> AuditEvent:
        """Log system-level audit event."""

        actor = AuditActor(
            actor_id="system",
            actor_type="system",
            service_account=self.service_name,
            tenant_id=self.tenant_id,
        )

        return self.log_event(
            event_type=event_type,
            message=message,
            actor=actor,
            severity=severity,
            **kwargs,
        )

    def query_events(self, **kwargs) -> List[AuditEvent]:
        """Query audit events from the store."""
        return self.store.query_events(**kwargs)

    def get_event_stats(
        self, start_time: Optional[float] = None, end_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get audit event statistics."""
        events = self.query_events(
            start_time=start_time, end_time=end_time, limit=10000
        )

        stats = {
            "total_events": len(events),
            "events_by_type": {},
            "events_by_severity": {},
            "events_by_outcome": {},
            "unique_actors": set(),
            "unique_resources": set(),
        }

        for event in events:
            # Count by type
            event_type = event.event_type.value
            stats["events_by_type"][event_type] = (
                stats["events_by_type"].get(event_type, 0) + 1
            )

            # Count by severity
            severity = event.severity.value
            stats["events_by_severity"][severity] = (
                stats["events_by_severity"].get(severity, 0) + 1
            )

            # Count by outcome
            outcome = event.outcome.value
            stats["events_by_outcome"][outcome] = (
                stats["events_by_outcome"].get(outcome, 0) + 1
            )

            # Track unique actors and resources
            if event.actor:
                stats["unique_actors"].add(event.actor.actor_id)
            if event.resource:
                stats["unique_resources"].add(
                    f"{event.resource.resource_type}:{event.resource.resource_id}"
                )

        # Convert sets to counts
        stats["unique_actors"] = len(stats["unique_actors"])
        stats["unique_resources"] = len(stats["unique_resources"])

        return stats

    def _merge_context(self, context: Optional[AuditContext]) -> AuditContext:
        """Merge provided context with default context."""
        if not context:
            return self._default_context

        # Create merged context
        merged = AuditContext(**self._default_context.__dict__)
        for key, value in context.__dict__.items():
            if value is not None:
                setattr(merged, key, value)

        return merged


# Factory functions
def create_audit_logger(
    service_name: str,
    tenant_id: Optional[str] = None,
    store: Optional[AuditStore] = None,
) -> AuditLogger:
    """Create an audit logger instance."""
    return AuditLogger(store=store, service_name=service_name, tenant_id=tenant_id)


def create_audit_event(
    event_type: AuditEventType,
    message: str,
    actor_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    **kwargs,
) -> AuditEvent:
    """Factory function to create audit events."""

    actor = None
    if actor_id:
        actor = AuditActor(actor_id=actor_id, actor_type="user")

    resource = None
    if resource_type:
        resource = AuditResource(resource_type=resource_type, resource_id=resource_id)

    return AuditEvent(
        event_type=event_type, message=message, actor=actor, resource=resource, **kwargs
    )


# Global audit logger instance
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> Optional[AuditLogger]:
    """Get the global audit logger instance."""
    return _global_audit_logger


def init_audit_logger(
    service_name: str,
    tenant_id: Optional[str] = None,
    store: Optional[AuditStore] = None,
) -> AuditLogger:
    """Initialize the global audit logger."""
    global _global_audit_logger
    _global_audit_logger = create_audit_logger(service_name, tenant_id, store)
    return _global_audit_logger


__all__ = [
    # Core classes
    "AuditEvent",
    "AuditActor",
    "AuditResource",
    "AuditContext",
    "AuditLogger",
    "AuditStore",
    # Enums
    "AuditEventType",
    "AuditSeverity",
    "AuditOutcome",
    # Implementations
    "InMemoryAuditStore",
    # Factory functions
    "create_audit_logger",
    "create_audit_event",
    "get_audit_logger",
    "init_audit_logger",
]
