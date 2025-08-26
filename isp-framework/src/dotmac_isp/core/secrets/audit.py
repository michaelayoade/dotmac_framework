"""
Comprehensive Audit Trail System

Implements tamper-proof audit logging for all administrative operations
with support for compliance reporting and forensic analysis.
"""

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from ..utils.datetime_compat import utcnow
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from enum import Enum
from typing import Any

import structlog
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = structlog.get_logger(__name__)


class AuditEventType(Enum):
    """Types of auditable events"""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"

    # Authorization events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"

    # Administrative events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_REACTIVATED = "user_reactivated"

    # System events
    CONFIG_CHANGE = "config_change"
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"

    # Security events
    SECURITY_VIOLATION = "security_violation"
    INTRUSION_DETECTED = "intrusion_detected"
    KEY_ROTATION = "key_rotation"
    CERTIFICATE_RENEWAL = "certificate_renewal"

    # Compliance events
    GDPR_REQUEST = "gdpr_request"
    DATA_RETENTION_APPLIED = "data_retention_applied"
    AUDIT_LOG_ACCESS = "audit_log_access"


class AuditSeverity(Enum):
    """Audit event severity levels"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditStatus(Enum):
    """Audit event status"""

    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class AuditContext:
    """Context information for audit events"""

    user_id: str | None = None
    session_id: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    tenant_id: str | None = None
    organization_id: str | None = None
    location: str | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AuditMetadata:
    """Additional metadata for audit events"""

    resource_type: str | None = None
    resource_id: str | None = None
    operation: str | None = None
    affected_fields: list[str] | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    reason: str | None = None
    approval_id: str | None = None
    risk_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {}
        for k, v in asdict(self).items():
            if v is not None:
                if isinstance(v, list) and len(v) == 0:
                    continue
                if isinstance(v, dict) and len(v) == 0:
                    continue
                result[k] = v
        return result


class AuditEvent(BaseModel):
    """Immutable audit event record"""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    severity: AuditSeverity = Field(..., description="Event severity level")
    status: AuditStatus = Field(..., description="Event status")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    message: str = Field(..., description="Human-readable event description")
    context: dict[str, Any] = Field(default_factory=dict, description="Event context")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    hash_chain: str | None = Field(None, description="Hash chain for tamper detection")
    signature: str | None = Field(None, description="Digital signature")

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
    )

    @field_validator("event_id", mode="before")
    def generate_event_id(cls, v):
        """Generate unique event ID if not provided"""
        if not v:
            return str(uuid.uuid4())
        return v

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(sort_keys=True, separators=(",", ":"))

    def calculate_hash(self, previous_hash: str = "") -> str:
        """Calculate hash for tamper detection"""
        # Create canonical representation
        data = {
            "event_id": self.event_id,
            "event_type": (
                self.event_type.value
                if hasattr(self.event_type, "value")
                else str(self.event_type)
            ),
            "severity": (
                self.severity.value
                if hasattr(self.severity, "value")
                else str(self.severity)
            ),
            "status": (
                self.status.value if hasattr(self.status, "value") else str(self.status)
            ),
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "context": self.context,
            "metadata": self.metadata,
            "previous_hash": previous_hash,
        }

        # Convert to canonical JSON
        canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))

        # Calculate SHA-256 hash
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class AuditTrail:
    """Tamper-proof audit trail implementation"""

    def __init__(self, signing_key: bytes | None = None):
        """  Init   operation."""
        self.events: list[AuditEvent] = []
        self.event_index: dict[str, int] = {}
        self.hash_chain: list[str] = []
        self.signing_key = signing_key or self._generate_signing_key()
        self._lock = asyncio.Lock()

    def _generate_signing_key(self) -> bytes:
        """Generate RSA signing key"""
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    async def append_event(self, event: AuditEvent) -> str:
        """Append event to audit trail with hash chaining"""
        async with self._lock:
            # Get previous hash for chaining
            previous_hash = self.hash_chain[-1] if self.hash_chain else ""

            # Calculate hash chain
            event_hash = event.calculate_hash(previous_hash)
            event.hash_chain = event_hash

            # Sign the event
            if self.signing_key:
                event.signature = self._sign_event(event)

            # Add to trail
            self.events.append(event)
            self.event_index[event.event_id] = len(self.events) - 1
            self.hash_chain.append(event_hash)

            logger.info(
                "Audit event appended",
                event_id=event.event_id,
                event_type=(
                    event.event_type.value
                    if hasattr(event.event_type, "value")
                    else str(event.event_type)
                ),
                hash=event_hash[:16],
            )

            return event_hash

    def _sign_event(self, event: AuditEvent) -> str:
        """Digitally sign audit event"""
        try:
            private_key = serialization.load_pem_private_key(
                self.signing_key, password=None, backend=default_backend()
            )

            # Sign the hash
            signature = private_key.sign(
                event.hash_chain.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )

            return signature.hex()

        except Exception as e:
            logger.error("Event signing failed", error=str(e))
            return ""

    def verify_integrity(self) -> dict[str, Any]:
        """Verify audit trail integrity"""
        result = {
            "is_valid": True,
            "total_events": len(self.events),
            "verified_events": 0,
            "hash_chain_valid": True,
            "signature_valid": True,
            "errors": [],
        }

        previous_hash = ""
        for i, event in enumerate(self.events):
            try:
                # Verify hash chain
                expected_hash = event.calculate_hash(previous_hash)
                if event.hash_chain != expected_hash:
                    result["is_valid"] = False
                    result["hash_chain_valid"] = False
                    result["errors"].append(
                        f"Hash mismatch at event {i}: {event.event_id}"
                    )

                # Verify signature if present
                if event.signature and self.signing_key:
                    if not self._verify_signature(event):
                        result["is_valid"] = False
                        result["signature_valid"] = False
                        result["errors"].append(
                            f"Signature invalid at event {i}: {event.event_id}"
                        )

                result["verified_events"] += 1
                previous_hash = expected_hash

            except Exception as e:
                result["is_valid"] = False
                result["errors"].append(f"Verification error at event {i}: {str(e)}")

        return result

    def _verify_signature(self, event: AuditEvent) -> bool:
        """Verify event digital signature"""
        try:
            private_key = serialization.load_pem_private_key(
                self.signing_key, password=None, backend=default_backend()
            )
            public_key = private_key.public_key()

            signature_bytes = bytes.fromhex(event.signature)

            public_key.verify(
                signature_bytes,
                event.hash_chain.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )

            return True

        except Exception:
            return False

    def get_event(self, event_id: str) -> AuditEvent | None:
        """Get event by ID"""
        index = self.event_index.get(event_id)
        if index is not None:
            return self.events[index]
        return None

    def get_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_types: list[AuditEventType] | None = None,
        user_id: str | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        """Get filtered events"""
        filtered_events = []

        for event in self.events:
            # Time filter
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue

            # Event type filter
            if event_types and event.event_type not in event_types:
                continue

            # User filter
            if user_id and event.context.get("user_id") != user_id:
                continue

            filtered_events.append(event)

            # Limit results
            if limit and len(filtered_events) >= limit:
                break

        return filtered_events


class AuditLogger:
    """High-level audit logging service"""

    def __init__(self, audit_trail: AuditTrail | None = None):
        """  Init   operation."""
        self.audit_trail = audit_trail or AuditTrail()
        self.context_stack: list[AuditContext] = []
        self._performance_metrics: dict[str, list[float]] = {}

    @asynccontextmanager
    async def audit_context(self, context: AuditContext):
        """Context manager for audit context"""
        self.context_stack.append(context)
        try:
            yield context
        finally:
            if self.context_stack:
                self.context_stack.pop()

    def _get_current_context(self) -> dict[str, Any]:
        """Get current audit context"""
        if self.context_stack:
            return self.context_stack[-1].to_dict()
        return {}

    async def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        status: AuditStatus = AuditStatus.SUCCESS,
        context: AuditContext | None = None,
        metadata: AuditMetadata | None = None,
        **kwargs,
    ) -> str:
        """Log audit event"""
        start_time = time.time()

        try:
            # Combine contexts
            event_context = self._get_current_context()
            if context:
                event_context.update(context.to_dict())

            # Add any additional context from kwargs
            event_context.update(kwargs)

            # Create metadata
            event_metadata = {}
            if metadata:
                event_metadata.update(metadata.to_dict())

            # Create audit event
            event = AuditEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                severity=severity,
                status=status,
                timestamp=utcnow(),
                message=message,
                context=event_context,
                metadata=event_metadata,
            )

            # Append to audit trail
            event_hash = await self.audit_trail.append_event(event)

            # Track performance
            duration = time.time() - start_time
            event_type_key = event_type.value
            if event_type_key not in self._performance_metrics:
                self._performance_metrics[event_type_key] = []
            self._performance_metrics[event_type_key].append(duration)

            return event_hash

        except Exception as e:
            logger.error(
                "Audit logging failed", event_type=event_type.value, error=str(e)
            )
            raise

    async def log_authentication(
        self, user_id: str, success: bool, reason: str | None = None, **kwargs
    ) -> str:
        """Log authentication event"""
        event_type = (
            AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
        )
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        severity = AuditSeverity.INFO if success else AuditSeverity.MEDIUM

        message = (
            f"User {user_id} authentication {'succeeded' if success else 'failed'}"
        )
        if reason:
            message += f": {reason}"

        metadata = AuditMetadata(
            resource_type="user",
            resource_id=user_id,
            operation="authenticate",
            reason=reason,
        )

        return await self.log_event(
            event_type=event_type,
            message=message,
            severity=severity,
            status=status,
            metadata=metadata,
            user_id=user_id,
            **kwargs,
        )

    async def log_data_access(
        self,
        operation: str,
        resource_type: str,
        resource_id: str,
        success: bool = True,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        **kwargs,
    ) -> str:
        """Log data access event"""
        operation_map = {
            "read": AuditEventType.DATA_READ,
            "create": AuditEventType.DATA_CREATE,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
            "export": AuditEventType.DATA_EXPORT,
            "import": AuditEventType.DATA_IMPORT,
        }

        event_type = operation_map.get(operation.lower(), AuditEventType.DATA_READ)
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        severity = AuditSeverity.LOW if operation == "read" else AuditSeverity.MEDIUM

        message = f"Data {operation} on {resource_type} {resource_id}"
        if not success:
            message += " failed"

        # Detect affected fields
        affected_fields = []
        if old_values and new_values:
            for key in set(old_values.keys()) | set(new_values.keys()):
                if old_values.get(key) != new_values.get(key):
                    affected_fields.append(key)

        metadata = AuditMetadata(
            resource_type=resource_type,
            resource_id=resource_id,
            operation=operation,
            affected_fields=affected_fields if affected_fields else None,
            old_values=old_values,
            new_values=new_values,
        )

        return await self.log_event(
            event_type=event_type,
            message=message,
            severity=severity,
            status=status,
            metadata=metadata,
            **kwargs,
        )

    async def log_administrative_action(
        self,
        action: str,
        target_user_id: str,
        success: bool = True,
        reason: str | None = None,
        approval_id: str | None = None,
        **kwargs,
    ) -> str:
        """Log administrative action"""
        action_map = {
            "create_user": AuditEventType.USER_CREATED,
            "update_user": AuditEventType.USER_UPDATED,
            "delete_user": AuditEventType.USER_DELETED,
            "suspend_user": AuditEventType.USER_SUSPENDED,
            "reactivate_user": AuditEventType.USER_REACTIVATED,
            "assign_role": AuditEventType.ROLE_ASSIGNED,
            "revoke_role": AuditEventType.ROLE_REVOKED,
        }

        event_type = action_map.get(action, AuditEventType.CONFIG_CHANGE)
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        severity = AuditSeverity.HIGH  # Admin actions are high severity

        message = f"Administrative action '{action}' on user {target_user_id}"
        if not success:
            message += " failed"
        if reason:
            message += f": {reason}"

        metadata = AuditMetadata(
            resource_type="user",
            resource_id=target_user_id,
            operation=action,
            reason=reason,
            approval_id=approval_id,
        )

        return await self.log_event(
            event_type=event_type,
            message=message,
            severity=severity,
            status=status,
            metadata=metadata,
            target_user_id=target_user_id,
            **kwargs,
        )

    async def log_security_event(
        self,
        event_type: AuditEventType,
        message: str,
        risk_score: float | None = None,
        **kwargs,
    ) -> str:
        """Log security event"""
        severity = (
            AuditSeverity.CRITICAL
            if risk_score and risk_score > 0.8
            else AuditSeverity.HIGH
        )

        metadata = AuditMetadata(risk_score=risk_score)

        return await self.log_event(
            event_type=event_type,
            message=message,
            severity=severity,
            status=AuditStatus.WARNING,
            metadata=metadata,
            **kwargs,
        )

    def get_performance_metrics(self) -> dict[str, dict[str, float]]:
        """Get audit logging performance metrics"""
        metrics = {}

        for event_type, durations in self._performance_metrics.items():
            if durations:
                metrics[event_type] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }

        return metrics

    async def search_events(
        self,
        query: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Search audit events by text query"""
        events = self.audit_trail.get_events(
            start_time=start_time,
            end_time=end_time,
            limit=limit * 2,  # Get more to filter
        )

        # Simple text search
        query_lower = query.lower()
        matching_events = []

        for event in events:
            if (
                query_lower in event.message.lower()
                or query_lower in json.dumps(event.context).lower()
                or query_lower in json.dumps(event.metadata).lower()
            ):
                matching_events.append(event)

                if len(matching_events) >= limit:
                    break

        return matching_events

    async def export_audit_log(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        format: str = "json",
    ) -> str:
        """Export audit log for compliance reporting"""
        # Log the export action itself
        await self.log_event(
            event_type=AuditEventType.AUDIT_LOG_ACCESS,
            message=f"Audit log exported in {format} format",
            severity=AuditSeverity.HIGH,
            metadata=AuditMetadata(operation="export", reason="compliance_reporting"),
        )

        events = self.audit_trail.get_events(start_time=start_time, end_time=end_time)

        if format.lower() == "json":
            return json.dumps(
                [event.model_dump() for event in events], indent=2, default=str
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Audit decorators for automatic logging
def audit_operation(
    event_type: AuditEventType,
    message_template: str = "",
    severity: AuditSeverity = AuditSeverity.INFO,
    log_args: bool = False,
    log_result: bool = False,
):
    """Decorator to automatically audit function calls"""

    def decorator(func):
        """Decorator operation."""
        async def async_wrapper(*args, **kwargs):
            """Async Wrapper operation."""
            audit_logger = kwargs.pop("audit_logger", None)
            if not audit_logger:
                return await func(*args, **kwargs)

            start_time = time.time()
            success = True
            result = None
            error = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                # Create audit message
                message = message_template or f"Function {func.__name__} executed"
                if not success and error:
                    message += f" with error: {error}"

                # Create metadata
                metadata = AuditMetadata(
                    operation=func.__name__, reason="function_call"
                )

                if log_args:
                    metadata.old_values = {"args": args, "kwargs": kwargs}

                if log_result and result is not None:
                    metadata.new_values = {"result": str(result)[:1000]}  # Limit size

                await audit_logger.log_event(
                    event_type=event_type,
                    message=message,
                    severity=severity,
                    status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
                    metadata=metadata,
                    duration=time.time() - start_time,
                )

        def sync_wrapper(*args, **kwargs):
            """Sync Wrapper operation."""
            # For sync functions, create async wrapper
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
