"""Cross-platform event streaming for unified audit trails."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from pydantic import BaseModel, Field

from dotmac_isp.core.management_platform_client import get_management_client


logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of cross-platform events."""

    # Configuration events
    CONFIG_UPDATE = "config_update"
    CONFIG_APPLIED = "config_applied"
    CONFIG_VALIDATION = "config_validation"
    CONFIG_ROLLBACK = "config_rollback"

    # Plugin events
    PLUGIN_ACTIVATED = "plugin_activated"
    PLUGIN_DEACTIVATED = "plugin_deactivated"
    PLUGIN_LICENSE_VALIDATED = "plugin_license_validated"
    PLUGIN_USAGE_RECORDED = "plugin_usage_recorded"
    PLUGIN_ERROR = "plugin_error"

    # Health events
    HEALTH_CHECK_PERFORMED = "health_check_performed"
    HEALTH_STATUS_CHANGED = "health_status_changed"
    HEALTH_ALERT_TRIGGERED = "health_alert_triggered"

    # Security events
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_DENIED = "authorization_denied"
    SECURITY_VIOLATION = "security_violation"

    # System events
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    DEPLOYMENT_EVENT = "deployment_event"
    ERROR_OCCURRED = "error_occurred"

    # Audit events
    USER_ACTION = "user_action"
    DATA_ACCESS = "data_access"
    ADMIN_ACTION = "admin_action"
    COMPLIANCE_EVENT = "compliance_event"


class EventSeverity(str, Enum):
    """Event severity levels."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventSource(str, Enum):
    """Source platforms for events."""

    MANAGEMENT_PLATFORM = "management_platform"
    ISP_FRAMEWORK = "isp_framework"
    KUBERNETES = "kubernetes"
    EXTERNAL_SYSTEM = "external_system"


class CrossPlatformEvent(BaseModel):
    """Cross-platform event model."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None  # Links related events
    event_type: EventType
    severity: EventSeverity = EventSeverity.INFO

    # Source information
    source: EventSource
    source_component: str  # Specific component that generated event
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None

    # Temporal information
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_version: str = "1.0"

    # Event content
    title: str
    description: Optional[str] = None
    event_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Cross-platform tracking
    target_platform: Optional[EventSource] = None
    related_events: List[str] = Field(default_factory=list)

    # Audit fields
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None

    # Performance tracking
    processing_time_ms: Optional[float] = None
    response_code: Optional[int] = None

    class Config:
        """Class for Config operations."""
        use_enum_values = True


class EventEmitter:
    """Cross-platform event emitter."""

    def __init__(self):
        """  Init   operation."""
        self.tenant_id = os.getenv("ISP_TENANT_ID")
        self.source = EventSource.ISP_FRAMEWORK
        self.component_name = os.getenv("SERVICE_NAME", "isp-framework")
        self.event_listeners: Dict[EventType, List[Callable]] = {}
        self.event_buffer: List[CrossPlatformEvent] = []
        self.buffer_size = 100
        self.auto_flush_interval = 30  # seconds
        self._flush_task = None

    async def start(self):
        """Start the event emitter."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._auto_flush_loop())
            logger.info("Cross-platform event emitter started")

    async def stop(self):
        """Stop the event emitter."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        # Flush remaining events
        await self.flush_events()
        logger.info("Cross-platform event emitter stopped")

    async def emit(self, event: CrossPlatformEvent) -> str:
        """Emit a cross-platform event."""
        # Set source information
        if not event.tenant_id:
            event.tenant_id = self.tenant_id
        event.source = self.source
        if not event.source_component:
            event.source_component = self.component_name

        # Add to buffer
        self.event_buffer.append(event)

        # Trigger local listeners
        await self._notify_local_listeners(event)

        # Auto-flush if buffer is full
        if len(self.event_buffer) >= self.buffer_size:
            await self.flush_events()

        logger.debug(f"Emitted event: {event.event_type} [{event.event_id}]")
        return event.event_id

    async def emit_simple(
        self,
        event_type: EventType,
        title: str,
        description: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        severity: EventSeverity = EventSeverity.INFO,
        correlation_id: Optional[str] = None,
        target_platform: Optional[EventSource] = None,
    ) -> str:
        """Emit a simple event with minimal parameters."""
        event = CrossPlatformEvent(
            event_type=event_type,
            title=title,
            description=description,
            event_data=event_data or {},
            severity=severity,
            correlation_id=correlation_id,
            target_platform=target_platform,
        )
        return await self.emit(event)

    async def emit_config_event(
        self,
        action: str,
        config_version: str,
        success: bool,
        changes: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
    ) -> str:
        """Emit configuration-related event."""
        event_type = (
            EventType.CONFIG_APPLIED if action == "applied" else EventType.CONFIG_UPDATE
        )
        severity = EventSeverity.INFO if success else EventSeverity.ERROR

        event_data = {
            "action": action,
            "config_version": config_version,
            "success": success,
            "changes": changes or {},
            "errors": errors or [],
        }

        return await self.emit_simple(
            event_type=event_type,
            title=f"Configuration {action}",
            description=f"Configuration {action} {'succeeded' if success else 'failed'}: {config_version}",
            event_data=event_data,
            severity=severity,
            target_platform=EventSource.MANAGEMENT_PLATFORM,
        )

    async def emit_plugin_event(
        self,
        plugin_id: str,
        action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Emit plugin-related event."""
        event_type_map = {
            "activated": EventType.PLUGIN_ACTIVATED,
            "deactivated": EventType.PLUGIN_DEACTIVATED,
            "license_validated": EventType.PLUGIN_LICENSE_VALIDATED,
            "usage_recorded": EventType.PLUGIN_USAGE_RECORDED,
            "error": EventType.PLUGIN_ERROR,
        }

        event_type = event_type_map.get(action, EventType.PLUGIN_ERROR)
        severity = EventSeverity.INFO if success else EventSeverity.ERROR

        event_data = {
            "plugin_id": plugin_id,
            "action": action,
            "success": success,
            "details": details or {},
        }

        return await self.emit_simple(
            event_type=event_type,
            title=f"Plugin {action}",
            description=f"Plugin {plugin_id} {action} {'succeeded' if success else 'failed'}",
            event_data=event_data,
            severity=severity,
            target_platform=EventSource.MANAGEMENT_PLATFORM,
        )

    async def emit_health_event(
        self,
        component: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
        previous_status: Optional[str] = None,
    ) -> str:
        """Emit health-related event."""
        event_type = (
            EventType.HEALTH_STATUS_CHANGED
            if previous_status
            else EventType.HEALTH_CHECK_PERFORMED
        )

        severity_map = {
            "healthy": EventSeverity.INFO,
            "warning": EventSeverity.WARNING,
            "unhealthy": EventSeverity.ERROR,
            "unknown": EventSeverity.WARNING,
        }
        severity = severity_map.get(status, EventSeverity.INFO)

        event_data = {
            "component": component,
            "status": status,
            "previous_status": previous_status,
            "metrics": metrics or {},
        }

        return await self.emit_simple(
            event_type=event_type,
            title=f"Health check: {component}",
            description=f"Component {component} status: {status}",
            event_data=event_data,
            severity=severity,
            target_platform=EventSource.MANAGEMENT_PLATFORM,
        )

    async def emit_security_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Emit security-related event."""
        event_type_map = {
            "authentication": (
                EventType.AUTHENTICATION_SUCCESS
                if success
                else EventType.AUTHENTICATION_FAILURE
            ),
            "authorization": (
                EventType.AUTHORIZATION_DENIED if not success else EventType.USER_ACTION
            ),
            "security_violation": EventType.SECURITY_VIOLATION,
        }

        event_type = event_type_map.get(action, EventType.USER_ACTION)
        severity = EventSeverity.WARNING if not success else EventSeverity.INFO

        event_data = {
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "success": success,
            "details": details or {},
        }

        event = CrossPlatformEvent(
            event_type=event_type,
            title=f"Security event: {action}",
            description=f"Security action {action} {'succeeded' if success else 'failed'}",
            event_data=event_data,
            severity=severity,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            target_platform=EventSource.MANAGEMENT_PLATFORM,
        )

        return await self.emit(event)

    async def emit_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Emit audit trail event."""
        event_data = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "changes": changes or {},
            "details": details or {},
        }

        event = CrossPlatformEvent(
            event_type=EventType.USER_ACTION,
            title=f"Audit: {action}",
            description=f"User action: {action} on {resource_type}/{resource_id}",
            event_data=event_data,
            severity=EventSeverity.INFO,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            target_platform=EventSource.MANAGEMENT_PLATFORM,
        )

        return await self.emit(event)

    def add_listener(
        self, event_type: EventType, callback: Callable[[CrossPlatformEvent], None]
    ):
        """Add local event listener."""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)

    def remove_listener(
        self, event_type: EventType, callback: Callable[[CrossPlatformEvent], None]
    ):
        """Remove local event listener."""
        if event_type in self.event_listeners:
            try:
                self.event_listeners[event_type].remove(callback)
            except ValueError:
                pass

    async def _notify_local_listeners(self, event: CrossPlatformEvent):
        """Notify local event listeners."""
        listeners = self.event_listeners.get(event.event_type, [])
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    async def flush_events(self):
        """Flush buffered events to Management Platform."""
        if not self.event_buffer:
            return

        try:
            events_to_send = self.event_buffer.copy()
            self.event_buffer.clear()

            # Send events to Management Platform
            await self._send_events_to_management_platform(events_to_send)

            logger.debug(f"Flushed {len(events_to_send)} events to Management Platform")

        except Exception as e:
            logger.error(f"Error flushing events: {e}")
            # Re-add events to buffer on failure
            self.event_buffer.extend(events_to_send)

    async def _send_events_to_management_platform(
        self, events: List[CrossPlatformEvent]
    ):
        """Send events to Management Platform."""
        try:
            management_client = await get_management_client()

            # Convert events to dict format
            events_data = [event.dict() for event in events]

            # This would be a new endpoint in the Management Platform
            # For now, we'll log the events and potentially use the health status endpoint
            logger.info(
                f"Sending {len(events)} cross-platform events to Management Platform"
            )

            # Group events by type and send appropriately
            for event in events:
                if event.event_type in [
                    EventType.HEALTH_CHECK_PERFORMED,
                    EventType.HEALTH_STATUS_CHANGED,
                ]:
                    # Send as health status
                    if event.event_data.get("component") and event.event_data.get(
                        "status"
                    ):
                        await management_client.report_health_status(
                            component=event.event_data["component"],
                            status=event.event_data["status"],
                            metrics=event.event_data.get("metrics", {}),
                            details=event.description,
                        )

        except Exception as e:
            logger.error(f"Error sending events to Management Platform: {e}")
            raise

    async def _auto_flush_loop(self):
        """Auto-flush events periodically."""
        while True:
            try:
                await asyncio.sleep(self.auto_flush_interval)
                await self.flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-flush loop: {e}")


# Global event emitter instance
_event_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    """Get global event emitter instance."""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = EventEmitter()
    return _event_emitter


async def start_event_streaming():
    """Start global event streaming."""
    emitter = get_event_emitter()
    await emitter.start()


async def stop_event_streaming():
    """Stop global event streaming."""
    emitter = get_event_emitter()
    await emitter.stop()


# Convenience functions for common events
async def emit_config_event(
    action: str,
    config_version: str,
    success: bool,
    changes: Optional[Dict[str, Any]] = None,
    errors: Optional[List[str]] = None,
) -> str:
    """Emit configuration event."""
    emitter = get_event_emitter()
    return await emitter.emit_config_event(
        action, config_version, success, changes, errors
    )


async def emit_plugin_event(
    plugin_id: str, action: str, success: bool, details: Optional[Dict[str, Any]] = None
) -> str:
    """Emit plugin event."""
    emitter = get_event_emitter()
    return await emitter.emit_plugin_event(plugin_id, action, success, details)


async def emit_health_event(
    component: str,
    status: str,
    metrics: Optional[Dict[str, Any]] = None,
    previous_status: Optional[str] = None,
) -> str:
    """Emit health event."""
    emitter = get_event_emitter()
    return await emitter.emit_health_event(component, status, metrics, previous_status)


async def emit_security_event(
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """Emit security event."""
    emitter = get_event_emitter()
    return await emitter.emit_security_event(
        action, user_id, resource_type, resource_id, success, details
    )


async def emit_audit_event(
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """Emit audit trail event."""
    emitter = get_event_emitter()
    return await emitter.emit_audit_event(
        action, resource_type, resource_id, user_id, changes, details
    )
