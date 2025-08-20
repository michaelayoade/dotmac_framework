"""
Security monitoring and alerting for suspicious activities.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class SecurityEventType(str, Enum):
    """Types of security events."""

    # Authentication events
    AUTH_FAILURE = "auth_failure"
    JWT_INVALID = "jwt_invalid"
    JWT_EXPIRED = "jwt_expired"

    # Authorization events
    ACCESS_DENIED = "access_denied"
    TENANT_VIOLATION = "tenant_violation"
    PERMISSION_DENIED = "permission_denied"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Input validation events
    VALIDATION_ERROR = "validation_error"
    INJECTION_ATTEMPT = "injection_attempt"

    # Suspicious behavior
    UNUSUAL_PATTERN = "unusual_pattern"
    BRUTE_FORCE = "brute_force"
    ENUMERATION_ATTEMPT = "enumeration_attempt"


@dataclass
class SecurityEvent:
    """Security event data."""

    event_type: SecurityEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    request_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical


class SecurityMonitor:
    """Monitor and track security events."""

    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: deque[SecurityEvent] = deque(maxlen=max_events)
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.client_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.alert_handlers: List[Callable[[SecurityEvent], None]] = []
        self._lock = asyncio.Lock()

    async def record_event(self, event: SecurityEvent):
        """Record a security event."""
        async with self._lock:
            self.events.append(event)
            self.event_counts[event.event_type] += 1

            if event.client_ip:
                self.client_events[event.client_ip].append(event)

            # Check for patterns that warrant alerts
            await self._check_for_alerts(event)

            # Log the event
            logger.warning(
                "Security event recorded",
                event_type=event.event_type,
                severity=event.severity,
                client_ip=event.client_ip,
                tenant_id=event.tenant_id,
                endpoint=event.endpoint,
                details=event.details
            )

    async def _check_for_alerts(self, event: SecurityEvent):
        """Check if event should trigger alerts."""
        client_ip = event.client_ip
        if not client_ip:
            return

        client_events = list(self.client_events[client_ip])
        now = datetime.now(timezone.utc)

        # Check for brute force attacks (multiple auth failures)
        if event.event_type in [SecurityEventType.AUTH_FAILURE, SecurityEventType.JWT_INVALID]:
            recent_failures = [
                e for e in client_events[-20:]  # Last 20 events
                if e.event_type in [SecurityEventType.AUTH_FAILURE, SecurityEventType.JWT_INVALID]
                and (now - e.timestamp).total_seconds() < 300  # Within 5 minutes
            ]

            if len(recent_failures) >= 5:
                brute_force_event = SecurityEvent(
                    event_type=SecurityEventType.BRUTE_FORCE,
                    client_ip=client_ip,
                    details={
                        "failure_count": len(recent_failures),
                        "time_window": 300,
                        "original_event": event.event_type
                    },
                    severity="high"
                )
                await self._trigger_alerts(brute_force_event)

        # Check for enumeration attempts (many different endpoints)
        recent_events = [
            e for e in client_events[-50:]  # Last 50 events
            if (now - e.timestamp).total_seconds() < 3600  # Within 1 hour
        ]

        unique_endpoints = set(e.endpoint for e in recent_events if e.endpoint)
        if len(unique_endpoints) > 20:
            enum_event = SecurityEvent(
                event_type=SecurityEventType.ENUMERATION_ATTEMPT,
                client_ip=client_ip,
                details={
                    "unique_endpoints": len(unique_endpoints),
                    "total_requests": len(recent_events),
                    "time_window": 3600
                },
                severity="medium"
            )
            await self._trigger_alerts(enum_event)

        # Check for unusual patterns (rapid requests to sensitive endpoints)
        sensitive_endpoints = [
            "/api/v1/admin/",
            "/api/v1/events/publish",
            "/api/v1/schemas/"
        ]

        sensitive_requests = [
            e for e in recent_events
            if e.endpoint and any(sensitive in e.endpoint for sensitive in sensitive_endpoints)
            and (now - e.timestamp).total_seconds() < 60  # Within 1 minute
        ]

        if len(sensitive_requests) > 10:
            unusual_event = SecurityEvent(
                event_type=SecurityEventType.UNUSUAL_PATTERN,
                client_ip=client_ip,
                details={
                    "sensitive_requests": len(sensitive_requests),
                    "endpoints": list(set(e.endpoint for e in sensitive_requests)),
                    "time_window": 60
                },
                severity="high"
            )
            await self._trigger_alerts(unusual_event)

    async def _trigger_alerts(self, event: SecurityEvent):
        """Trigger alerts for security events."""
        # Record the alert event
        await self.record_event(event)

        # Call alert handlers
        for handler in self.alert_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Alert handler error", error=str(e))

    def add_alert_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add an alert handler."""
        self.alert_handlers.append(handler)

    async def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[SecurityEventType] = None,
        client_ip: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[SecurityEvent]:
        """Get recent security events."""
        async with self._lock:
            events = list(self.events)

            # Filter events
            if event_type:
                events = [e for e in events if e.event_type == event_type]

            if client_ip:
                events = [e for e in events if e.client_ip == client_ip]

            if severity:
                events = [e for e in events if e.severity == severity]

            # Sort by timestamp (newest first)
            events.sort(key=lambda e: e.timestamp, reverse=True)

            return events[:limit]

    async def get_statistics(self) -> Dict[str, Any]:
        """Get security monitoring statistics."""
        async with self._lock:
            now = datetime.now(timezone.utc)

            # Count events by type
            event_type_counts = dict(self.event_counts)

            # Count recent events (last hour)
            recent_events = [
                e for e in self.events
                if (now - e.timestamp).total_seconds() < 3600
            ]

            recent_by_type = defaultdict(int)
            recent_by_severity = defaultdict(int)

            for event in recent_events:
                recent_by_type[event.event_type] += 1
                recent_by_severity[event.severity] += 1

            # Top clients by event count
            client_counts = {}
            for client_ip, events in self.client_events.items():
                client_counts[client_ip] = len(events)

            top_clients = sorted(
                client_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            return {
                "total_events": len(self.events),
                "event_types": dict(event_type_counts),
                "recent_events_1h": len(recent_events),
                "recent_by_type": dict(recent_by_type),
                "recent_by_severity": dict(recent_by_severity),
                "top_clients": dict(top_clients),
                "monitored_clients": len(self.client_events)
            }


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for security monitoring."""

    def __init__(self, app, monitor: SecurityMonitor):
        super().__init__(app)
        self.monitor = monitor

    async def dispatch(self, request: Request, call_next):
        """Monitor requests for security events."""
        start_time = time.time()

        # Extract request information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        endpoint = f"{request.method}:{request.url.path}"
        request_id = getattr(request.state, "request_id", None)
        tenant_id = request.headers.get("X-Tenant-ID")

        try:
            response = await call_next(request)

            # Monitor for suspicious patterns
            await self._check_request_patterns(
                request, response, client_ip, user_agent, endpoint, request_id, tenant_id
            )

            return response

        except Exception as e:
            # Record application errors that might indicate attacks
            if "validation" in str(e).lower():
                await self.monitor.record_event(SecurityEvent(
                    event_type=SecurityEventType.VALIDATION_ERROR,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    details={"error": str(e)},
                    severity="medium"
                ))

            raise

    async def _check_request_patterns(
        self,
        request: Request,
        response,
        client_ip: str,
        user_agent: str,
        endpoint: str,
        request_id: str,
        tenant_id: str
    ):
        """Check request patterns for security issues."""

        # Monitor authentication failures
        if hasattr(response, "status_code"):
            if response.status_code == 401:
                await self.monitor.record_event(SecurityEvent(
                    event_type=SecurityEventType.AUTH_FAILURE,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    details={"status_code": response.status_code},
                    severity="medium"
                ))

            elif response.status_code == 403:
                await self.monitor.record_event(SecurityEvent(
                    event_type=SecurityEventType.ACCESS_DENIED,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    details={"status_code": response.status_code},
                    severity="medium"
                ))

            elif response.status_code == 429:
                await self.monitor.record_event(SecurityEvent(
                    event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    details={"status_code": response.status_code},
                    severity="low"
                ))

        # Check for potential injection attempts in query parameters
        if request.query_params:
            query_string = str(request.query_params)
            suspicious_patterns = [
                "script",
                "javascript:",
                "vbscript:",
                "onload=",
                "onerror=",
                "union select",
                "1=1",
                "or 1=1",
                "drop table",
                "../",
                "..\\",
                "%2e%2e",
                "etc/passwd",
                "cmd.exe",
                "powershell"
            ]

            for pattern in suspicious_patterns:
                if pattern in query_string.lower():
                    await self.monitor.record_event(SecurityEvent(
                        event_type=SecurityEventType.INJECTION_ATTEMPT,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        endpoint=endpoint,
                        request_id=request_id,
                        tenant_id=tenant_id,
                        details={
                            "pattern": pattern,
                            "query_params": dict(request.query_params)
                        },
                        severity="high"
                    ))
                    break

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"


def create_default_security_monitor() -> SecurityMonitor:
    """Create default security monitor with alert handlers."""
    monitor = SecurityMonitor()

    # Add default alert handler
    def default_alert_handler(event: SecurityEvent):
        if event.severity in ["high", "critical"]:
            logger.error(
                "SECURITY ALERT",
                event_type=event.event_type,
                severity=event.severity,
                client_ip=event.client_ip,
                details=event.details
            )
        else:
            logger.warning(
                "Security event",
                event_type=event.event_type,
                severity=event.severity,
                client_ip=event.client_ip
            )

    monitor.add_alert_handler(default_alert_handler)

    return monitor


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """Get global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = create_default_security_monitor()
    return _security_monitor
