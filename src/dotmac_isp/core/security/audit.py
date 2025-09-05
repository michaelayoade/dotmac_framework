"""Audit logging for security events."""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class AuditEventType(Enum):
    """Audit event types."""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PASSWORD_CHANGE = "password_change"  # noqa: S105 - label string, not a secret
    ACCOUNT_LOCKED = "account_locked"


class AuditLogger:
    """Audit logger for security events."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Init   operation."""
        self.db_session = db_session
        self.logger = logging.getLogger("security_audit")

        # Configure audit logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                ".format(asctime)s - AUDIT - .format(levelname)s - .format(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
    ):
        """Log an audit event."""
        audit_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "details": details or {},
        }

        # Log to standard logger
        log_message = (
            f"AUDIT: {event_type.value} - User: {user_id} - Success: {success}"
        )
        if details:
            log_message += f" - Details: {json.dumps(details)}"

        if success:
            self.logger.info(log_message)
        else:
            self.logger.warning(log_message)

        # Store to database if session available
        if self.db_session:
            await self._store_to_database(audit_data)

    async def _store_to_database(self, audit_data: dict[str, Any]):
        """Store audit event to database."""
        # This would typically store to an audit_logs table
        # For now, just log that we would store it
        self.logger.debug(f"Would store audit event to database: {audit_data}")

    async def log_login(self, user_id: str, ip_address: str, success: bool = True):
        """Log user login event."""
        await self.log_event(
            AuditEventType.USER_LOGIN,
            user_id=user_id,
            ip_address=ip_address,
            success=success,
        )

    async def log_logout(self, user_id: str, ip_address: str):
        """Log user logout event."""
        await self.log_event(
            AuditEventType.USER_LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
            success=True,
        )

    async def log_permission_denied(self, user_id: str, resource_id: str, action: str):
        """Log permission denied event."""
        await self.log_event(
            AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            resource_id=resource_id,
            details={"action": action},
            success=False,
        )

    async def log_security_violation(
        self,
        user_id: Optional[str],
        violation_type: str,
        details: dict[str, Any],
        ip_address: Optional[str] = None,
    ):
        """Log security violation."""
        await self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            ip_address=ip_address,
            details={"violation_type": violation_type, **details},
            success=False,
        )

    async def log_data_access(self, user_id: str, resource_type: str, resource_id: str):
        """Log data access event."""
        await self.log_event(
            AuditEventType.DATA_ACCESS,
            user_id=user_id,
            resource_id=resource_id,
            details={"resource_type": resource_type},
            success=True,
        )
