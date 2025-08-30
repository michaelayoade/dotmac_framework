"""
Audit Logging Middleware

Implements comprehensive authentication audit logging:
- Authentication event logging
- Security event tracking
- Failed login attempt monitoring
- Suspicious activity detection
- Structured logging with metadata
- Configurable log levels and filters
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"

    # MFA events
    MFA_SETUP = "mfa_setup"
    MFA_SUCCESS = "mfa_success"
    MFA_FAILURE = "mfa_failure"
    MFA_DISABLED = "mfa_disabled"
    MFA_BACKUP_CODE_USED = "mfa_backup_code_used"

    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_TERMINATED = "session_terminated"
    SESSION_HIJACK_DETECTED = "session_hijack_detected"

    # Permission events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"

    # System events
    CONFIG_CHANGED = "config_changed"
    SECURITY_ALERT = "security_alert"


class AuditSeverity(Enum):
    """Audit event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure."""

    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    severity: AuditSeverity
    user_id: Optional[str]
    tenant_id: Optional[str]
    ip_address: str
    user_agent: Optional[str]
    endpoint: Optional[str]
    http_method: Optional[str]
    success: bool
    message: str
    details: Dict[str, Any]
    session_id: Optional[str] = None
    device_fingerprint: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger(ABC):
    """Abstract audit logger interface."""

    @abstractmethod
    async def log_event(self, event: AuditEvent) -> bool:
        """Log audit event."""
        pass

    @abstractmethod
    async def query_events(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events."""
        pass


class FileAuditLogger(AuditLogger):
    """File-based audit logger."""

    def __init__(self, log_file_path: str, rotate_size_mb: int = 100):
        """
        Initialize file audit logger.

        Args:
            log_file_path: Path to audit log file
            rotate_size_mb: File size in MB before rotation
        """
        self.log_file_path = log_file_path
        self.rotate_size_mb = rotate_size_mb

        # Set up file logger
        self.file_logger = logging.getLogger("audit")
        self.file_logger.setLevel(logging.INFO)

        # Add file handler if not already present
        if not self.file_logger.handlers:
            handler = logging.FileHandler(log_file_path)
            formatter = logging.Formatter(
                ".format(asctime)s - AUDIT - .format(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.file_logger.addHandler(handler)

    async def log_event(self, event: AuditEvent) -> bool:
        """Log audit event to file."""
        try:
            self.file_logger.info(event.to_json())
            return True
        except Exception as e:
            logger.error(f"Failed to log audit event to file: {e}")
            return False

    async def query_events(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events from file (basic implementation)."""
        # Note: This is a basic implementation. In production,
        # use a proper log aggregation system like ELK stack
        events = []
        try:
            with open(self.log_file_path, "r") as f:
                for line in f:
                    if "AUDIT" in line and len(events) < limit:
                        # Parse JSON from log line
                        try:
                            json_start = line.find("{")
                            if json_start != -1:
                                event_data = json.loads(line[json_start:])
                                event = AuditEvent(
                                    event_id=event_data["event_id"],
                                    event_type=AuditEventType(event_data["event_type"]),
                                    timestamp=datetime.fromisoformat(
                                        event_data["timestamp"]
                                    ),
                                    severity=AuditSeverity(event_data["severity"]),
                                    user_id=event_data.get("user_id"),
                                    tenant_id=event_data.get("tenant_id"),
                                    ip_address=event_data["ip_address"],
                                    user_agent=event_data.get("user_agent"),
                                    endpoint=event_data.get("endpoint"),
                                    http_method=event_data.get("http_method"),
                                    success=event_data["success"],
                                    message=event_data["message"],
                                    details=event_data.get("details", {}),
                                    session_id=event_data.get("session_id"),
                                    device_fingerprint=event_data.get(
                                        "device_fingerprint"
                                    ),
                                    location=event_data.get("location"),
                                )

                                # Apply filters
                                if user_id and event.user_id != user_id:
                                    continue
                                if tenant_id and event.tenant_id != tenant_id:
                                    continue
                                if event_types and event.event_type not in event_types:
                                    continue
                                if start_time and event.timestamp < start_time:
                                    continue
                                if end_time and event.timestamp > end_time:
                                    continue

                                events.append(event)
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")

        return events[:limit]


class DatabaseAuditLogger(AuditLogger):
    """Database-based audit logger (interface)."""

    def __init__(self, db_connection: Any):
        """
        Initialize database audit logger.

        Args:
            db_connection: Database connection
        """
        self.db = db_connection

    async def log_event(self, event: AuditEvent) -> bool:
        """Log audit event to database."""
        # Implementation would depend on specific database
        # This is a placeholder for the interface
        try:
            # Insert event into audit_events table
            query = """
                INSERT INTO audit_events (
                    event_id, event_type, timestamp, severity, user_id, tenant_id,
                    ip_address, user_agent, endpoint, http_method, success,
                    message, details, session_id, device_fingerprint, location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            await self.db.execute(
                query,
                (
                    event.event_id,
                    event.event_type.value,
                    event.timestamp,
                    event.severity.value,
                    event.user_id,
                    event.tenant_id,
                    event.ip_address,
                    event.user_agent,
                    event.endpoint,
                    event.http_method,
                    event.success,
                    event.message,
                    json.dumps(event.details),
                    event.session_id,
                    event.device_fingerprint,
                    json.dumps(event.location),
                ),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to log audit event to database: {e}")
            return False

    async def query_events(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events from database."""
        # Implementation would depend on specific database
        return []


class AuditManager:
    """
    Audit management system.

    Features:
    - Multiple audit loggers
    - Event filtering and routing
    - Suspicious activity detection
    - Alert generation for security events
    - Metrics and reporting
    """

    def __init__(
        self,
        audit_loggers: List[AuditLogger],
        enable_suspicious_activity_detection: bool = True,
        suspicious_threshold: int = 10,
        alert_on_severity: AuditSeverity = AuditSeverity.HIGH,
    ):
        """
        Initialize audit manager.

        Args:
            audit_loggers: List of audit logger instances
            enable_suspicious_activity_detection: Enable suspicious activity detection
            suspicious_threshold: Threshold for suspicious activity alerts
            alert_on_severity: Minimum severity level for alerts
        """
        self.audit_loggers = audit_loggers
        self.enable_suspicious_activity_detection = enable_suspicious_activity_detection
        self.suspicious_threshold = suspicious_threshold
        self.alert_on_severity = alert_on_severity

        # Activity tracking for suspicious behavior detection
        self._ip_activity: Dict[str, List[datetime]] = {}
        self._user_activity: Dict[str, List[datetime]] = {}
        self._failed_attempts: Dict[str, int] = {}

        logger.info(f"Audit Manager initialized with {len(audit_loggers)} loggers")

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        tenant_id: Optional[str],
        ip_address: str,
        success: bool,
        message: str,
        severity: AuditSeverity = AuditSeverity.LOW,
        details: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """
        Log audit event.

        Args:
            event_type: Type of audit event
            user_id: User identifier
            tenant_id: Tenant identifier
            ip_address: Client IP address
            success: Whether the action was successful
            message: Human-readable message
            severity: Event severity level
            details: Additional event details
            user_agent: User agent string
            endpoint: API endpoint
            http_method: HTTP method
            session_id: Session identifier

        Returns:
            True if event was logged successfully
        """
        try:
            # Create audit event
            event = AuditEvent(
                event_id=self._generate_event_id(),
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                severity=severity,
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                http_method=http_method,
                success=success,
                message=message,
                details=details or {},
                session_id=session_id,
            )

            # Enhanced details
            event.details.update(
                {
                    "ip_hash": self._hash_ip(ip_address),
                    "timestamp_unix": event.timestamp.timestamp(),
                    "severity_level": severity.value,
                }
            )

            # Suspicious activity detection
            if self.enable_suspicious_activity_detection:
                await self._check_suspicious_activity(event)

            # Log to all configured loggers
            success_count = 0
            for audit_logger in self.audit_loggers:
                if await audit_logger.log_event(event):
                    success_count += 1

            # Generate alerts for high-severity events
            if event.severity.value in [
                AuditSeverity.HIGH.value,
                AuditSeverity.CRITICAL.value,
            ]:
                await self._generate_alert(event)

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    async def log_authentication_event(
        self,
        success: bool,
        user_id: Optional[str],
        tenant_id: Optional[str],
        ip_address: str,
        user_agent: Optional[str] = None,
        method: str = "password",
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """Log authentication event."""
        event_type = (
            AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
        )
        severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM

        message = f"Authentication {'succeeded' if success else 'failed'} for user {user_id or 'unknown'}"
        if not success and failure_reason:
            message += f" - {failure_reason}"

        details = {
            "method": method,
            "failure_reason": failure_reason,
            "attempt_number": self._get_attempt_number(ip_address, user_id),
        }

        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            success=success,
            message=message,
            severity=severity,
            details=details,
            user_agent=user_agent,
            session_id=session_id,
        )

    async def log_mfa_event(
        self,
        success: bool,
        user_id: str,
        tenant_id: str,
        ip_address: str,
        mfa_method: str,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> bool:
        """Log MFA event."""
        event_type = (
            AuditEventType.MFA_SUCCESS if success else AuditEventType.MFA_FAILURE
        )
        severity = AuditSeverity.LOW if success else AuditSeverity.HIGH

        message = f"MFA {'succeeded' if success else 'failed'} for user {user_id} using {mfa_method}"

        details = {"mfa_method": mfa_method, "failure_reason": failure_reason}

        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            success=success,
            message=message,
            severity=severity,
            details=details,
            user_agent=user_agent,
        )

    async def log_permission_event(
        self,
        granted: bool,
        user_id: str,
        tenant_id: str,
        permission: str,
        resource: Optional[str] = None,
        ip_address: str = "",
        user_agent: Optional[str] = None,
    ) -> bool:
        """Log permission check event."""
        event_type = (
            AuditEventType.PERMISSION_GRANTED
            if granted
            else AuditEventType.PERMISSION_DENIED
        )
        severity = AuditSeverity.LOW if granted else AuditSeverity.MEDIUM

        message = f"Permission '{permission}' {'granted' if granted else 'denied'} for user {user_id}"
        if resource:
            message += f" on resource '{resource}'"

        details = {"permission": permission, "resource": resource, "granted": granted}

        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            success=granted,
            message=message,
            severity=severity,
            details=details,
            user_agent=user_agent,
        )

    async def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        tenant_id: Optional[str],
        ip_address: str,
        message: str,
        severity: AuditSeverity = AuditSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log security event."""
        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            success=False,  # Security events are typically failures
            message=message,
            severity=severity,
            details=details,
        )

    async def query_events(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events from all loggers."""
        all_events = []

        for audit_logger in self.audit_loggers:
            try:
                events = await audit_logger.query_events(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    event_types=event_types,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                )
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Failed to query events from logger: {e}")

        # Sort by timestamp and return limited results
        all_events.sort(key=lambda x: x.timestamp, reverse=True)
        return all_events[:limit]

    async def get_security_summary(
        self, tenant_id: Optional[str] = None, hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get security summary for the specified time period."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        # Query security-related events
        security_events = await self.query_events(
            tenant_id=tenant_id,
            event_types=[
                AuditEventType.LOGIN_FAILURE,
                AuditEventType.MFA_FAILURE,
                AuditEventType.SUSPICIOUS_ACTIVITY,
                AuditEventType.ACCOUNT_LOCKED,
                AuditEventType.RATE_LIMIT_EXCEEDED,
                AuditEventType.SESSION_HIJACK_DETECTED,
            ],
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        # Analyze events
        summary = {
            "time_period": f"{hours_back} hours",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_security_events": len(security_events),
            "events_by_type": {},
            "events_by_severity": {},
            "top_source_ips": {},
            "affected_users": set(),
            "alerts_generated": 0,
        }

        for event in security_events:
            # Count by type
            event_type = event.event_type.value
            summary["events_by_type"][event_type] = (
                summary["events_by_type"].get(event_type, 0) + 1
            )

            # Count by severity
            severity = event.severity.value
            summary["events_by_severity"][severity] = (
                summary["events_by_severity"].get(severity, 0) + 1
            )

            # Track source IPs
            ip_hash = self._hash_ip(event.ip_address)
            summary["top_source_ips"][ip_hash] = (
                summary["top_source_ips"].get(ip_hash, 0) + 1
            )

            # Track affected users
            if event.user_id:
                summary["affected_users"].add(event.user_id)

            # Count high-severity events as alerts
            if event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                summary["alerts_generated"] += 1

        # Convert set to count
        summary["affected_users"] = len(summary["affected_users"])

        # Sort top IPs
        summary["top_source_ips"] = dict(
            sorted(summary["top_source_ips"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        )

        return summary

    async def _check_suspicious_activity(self, event: AuditEvent):
        """Check for suspicious activity patterns."""
        try:
            now = datetime.now(timezone.utc)
            ip_hash = self._hash_ip(event.ip_address)

            # Track IP activity
            if ip_hash not in self._ip_activity:
                self._ip_activity[ip_hash] = []

            self._ip_activity[ip_hash].append(now)

            # Clean old entries (last hour)
            cutoff = now - timedelta(hours=1)
            self._ip_activity[ip_hash] = [
                timestamp
                for timestamp in self._ip_activity[ip_hash]
                if timestamp > cutoff
            ]

            # Check for suspicious patterns
            ip_count = len(self._ip_activity[ip_hash])

            if ip_count > self.suspicious_threshold:
                await self.log_security_event(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    user_id=event.user_id,
                    tenant_id=event.tenant_id,
                    ip_address=event.ip_address,
                    message=f"Suspicious activity detected: {ip_count} requests from IP in last hour",
                    severity=AuditSeverity.HIGH,
                    details={
                        "request_count": ip_count,
                        "time_window": "1 hour",
                        "threshold": self.suspicious_threshold,
                    },
                )

        except Exception as e:
            logger.error(f"Failed to check suspicious activity: {e}")

    async def _generate_alert(self, event: AuditEvent):
        """Generate alert for high-severity events."""
        try:
            alert_message = f"SECURITY ALERT: {event.message}"

            # Log alert (this could be extended to send notifications)
            logger.warning(f"Security Alert Generated: {alert_message}")

            # Could implement additional alerting mechanisms here:
            # - Email notifications
            # - Slack/Teams notifications
            # - SIEM integration
            # - SMS alerts for critical events

        except Exception as e:
            logger.error(f"Failed to generate alert: {e}")

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid

        return str(uuid.uuid4())

    def _hash_ip(self, ip_address: str) -> str:
        """Hash IP address for privacy."""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

    def _get_attempt_number(self, ip_address: str, user_id: Optional[str]) -> int:
        """Get attempt number for IP/user combination."""
        key = f"{self._hash_ip(ip_address)}:{user_id or 'anonymous'}"
        self._failed_attempts[key] = self._failed_attempts.get(key, 0) + 1
        return self._failed_attempts[key]


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware for audit logging.

    Automatically logs authentication-related requests and responses.
    """

    def __init__(
        self,
        app,
        audit_manager: AuditManager,
        log_all_requests: bool = False,
        auth_endpoints: Optional[Set[str]] = None,
        sensitive_endpoints: Optional[Set[str]] = None,
    ):
        """
        Initialize audit logging middleware.

        Args:
            app: ASGI application
            audit_manager: Audit manager instance
            log_all_requests: Log all requests (not just auth)
            auth_endpoints: Set of authentication endpoints to always log
            sensitive_endpoints: Set of sensitive endpoints to always log
        """
        super().__init__(app)
        self.audit_manager = audit_manager
        self.log_all_requests = log_all_requests

        self.auth_endpoints = auth_endpoints or {
            "/api/auth/login",
            "/api/auth/logout",
            "/api/auth/refresh",
            "/api/auth/mfa/setup",
            "/api/auth/mfa/validate",
            "/auth/login",
            "/auth/logout",
        }

        self.sensitive_endpoints = sensitive_endpoints or {
            "/api/admin/users",
            "/api/admin/tenants",
            "/api/billing/invoices",
            "/api/customers/payment",
        }

        logger.info("Audit Logging Middleware initialized")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log relevant events."""
        start_time = datetime.now(timezone.utc)

        # Extract request info
        ip_address = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        tenant_id = self._get_tenant_id(request)
        user_agent = request.headers.get("user-agent")
        path = request.url.path
        method = request.method

        # Determine if we should log this request
        should_log = (
            self.log_all_requests
            or path in self.auth_endpoints
            or path in self.sensitive_endpoints
            or any(endpoint in path for endpoint in self.auth_endpoints)
        )

        # Process request
        response = await call_next(request)

        # Log if appropriate
        if should_log:
            await self._log_request_response(
                request,
                response,
                start_time,
                ip_address,
                user_id,
                tenant_id,
                user_agent,
            )

        return response

    async def _log_request_response(
        self,
        request: Request,
        response: Response,
        start_time: datetime,
        ip_address: str,
        user_id: Optional[str],
        tenant_id: Optional[str],
        user_agent: Optional[str],
    ):
        """Log request/response pair."""
        try:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            success = 200 <= response.status_code < 400

            # Determine event type based on endpoint
            event_type = self._determine_event_type(request.url.path, success)

            # Determine severity
            severity = AuditSeverity.LOW
            if not success:
                if response.status_code == 401:
                    severity = AuditSeverity.MEDIUM
                elif response.status_code in [403, 429]:
                    severity = AuditSeverity.HIGH
                elif response.status_code >= 500:
                    severity = AuditSeverity.HIGH

            # Create message
            message = f"{request.method} {request.url.path} - {response.status_code}"

            # Collect details
            details = {
                "status_code": response.status_code,
                "duration_seconds": duration,
                "request_size": request.headers.get("content-length", 0),
                "response_size": response.headers.get("content-length", 0),
                "referer": request.headers.get("referer"),
                "user_agent_hash": (
                    hashlib.sha256(user_agent.encode()).hexdigest()[:16]
                    if user_agent
                    else None
                ),
            }

            # Log event
            await self.audit_manager.log_event(
                event_type=event_type,
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=ip_address,
                success=success,
                message=message,
                severity=severity,
                details=details,
                user_agent=user_agent,
                endpoint=request.url.path,
                http_method=request.method,
            )

        except Exception as e:
            logger.error(f"Failed to log request/response: {e}")

    def _determine_event_type(self, path: str, success: bool) -> AuditEventType:
        """Determine audit event type based on endpoint."""
        if "/login" in path:
            return (
                AuditEventType.LOGIN_SUCCESS
                if success
                else AuditEventType.LOGIN_FAILURE
            )
        elif "/logout" in path:
            return AuditEventType.LOGOUT
        elif "/mfa" in path:
            return AuditEventType.MFA_SUCCESS if success else AuditEventType.MFA_FAILURE
        elif "/refresh" in path:
            return AuditEventType.TOKEN_REFRESH
        else:
            return (
                AuditEventType.PERMISSION_GRANTED
                if success
                else AuditEventType.PERMISSION_DENIED
            )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "127.0.0.1"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request state."""
        if hasattr(request.state, "user") and request.state.user:
            if isinstance(request.state.user, dict):
                return request.state.user.get("user_id")
            else:
                return getattr(request.state.user, "user_id", None)
        return None

    def _get_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request state."""
        if hasattr(request.state, "user") and request.state.user:
            if isinstance(request.state.user, dict):
                return request.state.user.get("tenant_id")
            else:
                return getattr(request.state.user, "tenant_id", None)
        return None
