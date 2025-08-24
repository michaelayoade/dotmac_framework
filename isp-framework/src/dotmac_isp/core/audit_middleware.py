"""Audit middleware for automatic change tracking and compliance logging.

This middleware automatically captures user actions, API calls, and data changes
for audit trail purposes without requiring explicit logging in business logic.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, InstanceState

from dotmac_isp.core.audit_trail import (
    audit_manager,
    audit_context,
    AuditEventType,
    AuditSeverity,
    ComplianceFramework,
    log_user_action,
    log_data_change,
    log_security_event,
)
from dotmac_isp.core.tracing import trace_context
from dotmac_isp.shared.cache import get_cache_manager

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive audit logging of HTTP requests."""

    def __init__(
        """  Init   operation."""
        self, app, exclude_paths: list = None, sensitive_endpoints: list = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]
        self.sensitive_endpoints = sensitive_endpoints or [
            "/auth/",
            "/login",
            "/logout",
            "/password",
            "/api-key",
            "/token",
        ]
        self.cache_manager = get_cache_manager()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with audit logging."""
        start_time = time.time()

        # Skip audit for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Extract user context
        user_context = await self._extract_user_context(request)

        # Set audit context
        with audit_context(
            user_id=user_context.get("user_id"),
            tenant_id=user_context.get("tenant_id"),
            session_id=user_context.get("session_id"),
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=request_id,
        ) as audit_mgr:

            # Log request start
            self._log_request_start(request, user_context, request_id)

            try:
                # Process request
                response = await call_next(request)

                # Calculate duration
                duration = time.time() - start_time

                # Log successful request
                await self._log_request_completion(
                    request, response, user_context, request_id, duration
                )

                # Add audit headers to response
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Audit-Logged"] = "true"

                return response

            except Exception as e:
                # Calculate duration for failed request
                duration = time.time() - start_time

                # Log request failure
                await self._log_request_failure(
                    request, e, user_context, request_id, duration
                )

                # Re-raise the exception
                raise

    async def _extract_user_context(self, request: Request) -> Dict[str, Any]:
        """Extract user context from request."""
        context = {
            "user_id": None,
            "tenant_id": None,
            "session_id": None,
            "user_role": None,
        }

        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            context["user_id"] = request.state.user_id

        if hasattr(request.state, "tenant_id"):
            context["tenant_id"] = request.state.tenant_id

        if hasattr(request.state, "session_id"):
            context["session_id"] = request.state.session_id

        if hasattr(request.state, "user_role"):
            context["user_role"] = request.state.user_role

        # Try to get from headers
        context["tenant_id"] = context["tenant_id"] or request.headers.get(
            "X-Tenant-ID"
        )
        context["session_id"] = context["session_id"] or request.headers.get(
            "X-Session-ID"
        )

        # Try to get from trace context
        if not context["tenant_id"]:
            context["tenant_id"] = trace_context.get_tenant_id()

        if not context["user_id"]:
            context["user_id"] = trace_context.get_user_id()

        return context

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        forwarded = request.headers.get("X-Forwarded")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        if request.client:
            return request.client.host

        return "unknown"

    def _log_request_start(
        self, request: Request, user_context: Dict[str, Any], request_id: str
    ):
        """Log request start event."""
        try:
            # Determine if this is a sensitive endpoint
            is_sensitive = any(
                endpoint in str(request.url.path)
                for endpoint in self.sensitive_endpoints
            )

            event_name = f"{request.method} {request.url.path}"
            description = f"API request started: {request.method} {request.url.path}"

            # Log with appropriate severity
            severity = AuditSeverity.HIGH if is_sensitive else AuditSeverity.LOW

            log_user_action(
                action=event_name,
                description=description,
                severity=severity,
                compliance_frameworks=(
                    [ComplianceFramework.SOC2] if is_sensitive else None
                ),
                additional_data={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": (
                        str(request.query_params) if request.query_params else None
                    ),
                    "is_sensitive": is_sensitive,
                },
            )

        except Exception as e:
            logger.error(f"Failed to log request start: {e}")

    async def _log_request_completion(
        self,
        request: Request,
        response: Response,
        user_context: Dict[str, Any],
        request_id: str,
        duration: float,
    ):
        """Log successful request completion."""
        try:
            is_sensitive = any(
                endpoint in str(request.url.path)
                for endpoint in self.sensitive_endpoints
            )

            event_name = f"{request.method} {request.url.path} - {response.status_code}"
            description = f"API request completed: {request.method} {request.url.path} ({response.status_code}) in {duration:.3f}s"

            # Determine severity based on status code
            if response.status_code >= 400:
                severity = AuditSeverity.MEDIUM
            elif is_sensitive:
                severity = AuditSeverity.HIGH
            else:
                severity = AuditSeverity.LOW

            log_user_action(
                action=event_name,
                description=description,
                severity=severity,
                compliance_frameworks=(
                    [ComplianceFramework.SOC2] if is_sensitive else None
                ),
                additional_data={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "duration_seconds": duration,
                    "response_size": (
                        len(response.body) if hasattr(response, "body") else None
                    ),
                },
            )

            # Log data export events
            if request.method == "GET" and any(
                keyword in str(request.url.path).lower()
                for keyword in ["export", "download", "report"]
            ):
                audit_manager.log_event(
                    event_type=AuditEventType.DATA_EXPORT,
                    event_name=f"Data export: {request.url.path}",
                    description=f"User exported data from {request.url.path}",
                    severity=AuditSeverity.MEDIUM,
                    compliance_frameworks=[
                        ComplianceFramework.GDPR,
                        ComplianceFramework.SOC2,
                    ],
                )

        except Exception as e:
            logger.error(f"Failed to log request completion: {e}")

    async def _log_request_failure(
        self,
        request: Request,
        exception: Exception,
        user_context: Dict[str, Any],
        request_id: str,
        duration: float,
    ):
        """Log failed request."""
        try:
            is_sensitive = any(
                endpoint in str(request.url.path)
                for endpoint in self.sensitive_endpoints
            )

            event_name = f"{request.method} {request.url.path} - FAILED"
            description = f"API request failed: {request.method} {request.url.path} - {str(exception)}"

            # Failed requests are always at least medium severity
            severity = AuditSeverity.HIGH if is_sensitive else AuditSeverity.MEDIUM

            log_user_action(
                action=event_name,
                description=description,
                severity=severity,
                compliance_frameworks=[ComplianceFramework.SOC2],
                additional_data={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "error_type": type(exception).__name__,
                    "error_message": str(exception),
                    "duration_seconds": duration,
                },
            )

            # Log security events for auth failures
            if isinstance(exception, HTTPException) and exception.status_code == 401:
                log_security_event(
                    event_name="Authentication failure",
                    description=f"Authentication failed for {request.url.path}",
                    severity=AuditSeverity.HIGH,
                    additional_data={
                        "path": str(request.url.path),
                        "ip_address": self._get_client_ip(request),
                    },
                )

        except Exception as e:
            logger.error(f"Failed to log request failure: {e}")


class DatabaseAuditListener:
    """SQLAlchemy event listener for automatic database change auditing."""

    def __init__(self):
        """  Init   operation."""
        self.tracked_tables = {
            "users",
            "customers",
            "roles",
            "auth_tokens",
            "services",
            "invoices",
            "billing_accounts",
            "tickets",
            "inventory_items",
            "compliance_records",
            "network_devices",
        }
        self.session_states = {}

    def setup_listeners(self):
        """Setup SQLAlchemy event listeners for audit tracking."""

        # Listen for individual record changes (the main events we need)
        event.listen(Session, "before_flush", self.before_flush)
        event.listen(Session, "after_flush", self.after_flush)

        # Note: Bulk operation auditing would require mapper-level events
        # For now, we'll focus on individual record changes which cover most use cases

        logger.info("📋 Database audit listeners configured")

    def before_flush(self, session, flush_context, instances):
        """Capture state before flush to compare changes."""
        session_id = id(session)
        self.session_states[session_id] = {"new": [], "dirty": [], "deleted": []}

        # Capture new instances
        for instance in session.new:
            if (
                hasattr(instance, "__tablename__")
                and instance.__tablename__ in self.tracked_tables
            ):
                self.session_states[session_id]["new"].append(
                    {
                        "instance": instance,
                        "table": instance.__tablename__,
                        "values": self._get_instance_values(instance),
                    }
                )

        # Capture dirty instances (with old values)
        for instance in session.dirty:
            if (
                hasattr(instance, "__tablename__")
                and instance.__tablename__ in self.tracked_tables
            ):
                old_values = {}
                state = instance.__dict__.get("_sa_instance_state")
                if state and hasattr(state, "committed_state"):
                    old_values = dict(state.committed_state)

                self.session_states[session_id]["dirty"].append(
                    {
                        "instance": instance,
                        "table": instance.__tablename__,
                        "old_values": old_values,
                        "new_values": self._get_instance_values(instance),
                    }
                )

        # Capture deleted instances
        for instance in session.deleted:
            if (
                hasattr(instance, "__tablename__")
                and instance.__tablename__ in self.tracked_tables
            ):
                self.session_states[session_id]["deleted"].append(
                    {
                        "instance": instance,
                        "table": instance.__tablename__,
                        "values": self._get_instance_values(instance),
                    }
                )

    def after_flush(self, session, flush_context):
        """Log changes after successful flush."""
        session_id = id(session)

        if session_id not in self.session_states:
            return

        try:
            states = self.session_states[session_id]

            # Log new records
            for item in states["new"]:
                log_data_change(
                    table_name=item["table"],
                    record_id=str(getattr(item["instance"], "id", "unknown")),
                    operation="INSERT",
                    new_values=item["values"],
                )

            # Log updated records
            for item in states["dirty"]:
                log_data_change(
                    table_name=item["table"],
                    record_id=str(getattr(item["instance"], "id", "unknown")),
                    operation="UPDATE",
                    old_values=item["old_values"],
                    new_values=item["new_values"],
                )

            # Log deleted records
            for item in states["deleted"]:
                log_data_change(
                    table_name=item["table"],
                    record_id=str(getattr(item["instance"], "id", "unknown")),
                    operation="DELETE",
                    old_values=item["values"],
                )

        except Exception as e:
            logger.error(f"Failed to log database changes: {e}")

        finally:
            # Clean up session state
            del self.session_states[session_id]

    def _get_instance_values(self, instance) -> Dict[str, Any]:
        """Get values from SQLAlchemy instance."""
        values = {}

        try:
            # Get all columns
            if hasattr(instance, "__table__"):
                for column in instance.__table__.columns:
                    value = getattr(instance, column.name, None)
                    if value is not None:
                        # Convert non-serializable types
                        if hasattr(value, "isoformat"):  # datetime
                            values[column.name] = value.isoformat()
                        elif hasattr(value, "__dict__"):  # complex objects
                            values[column.name] = str(value)
                        else:
                            values[column.name] = value

        except Exception as e:
            logger.warning(f"Failed to extract instance values: {e}")

        return values


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for security event auditing."""

    def __init__(self, app):
        """  Init   operation."""
        super().__init__(app)
        self.failed_login_cache = {}
        self.rate_limit_cache = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor for security events."""

        # Monitor authentication endpoints
        if "/auth/" in str(request.url.path) or "/login" in str(request.url.path):
            return await self._monitor_auth_request(request, call_next)

        # Monitor admin endpoints
        if "/admin/" in str(request.url.path):
            return await self._monitor_admin_request(request, call_next)

        # Regular processing
        return await call_next(request)

    async def _monitor_auth_request(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Monitor authentication requests for security events."""
        client_ip = self._get_client_ip(request)

        try:
            response = await call_next(request)

            # Check for successful login
            if response.status_code == 200 and request.method == "POST":
                log_security_event(
                    event_name="User login successful",
                    severity=AuditSeverity.MEDIUM,
                    description=f"Successful login from {client_ip}",
                    additional_data={
                        "ip_address": client_ip,
                        "endpoint": str(request.url.path),
                    },
                )

                # Clear failed login attempts for this IP
                self.failed_login_cache.pop(client_ip, None)

            return response

        except HTTPException as e:
            if e.status_code == 401:
                # Track failed login attempts
                self.failed_login_cache[client_ip] = (
                    self.failed_login_cache.get(client_ip, 0) + 1
                )

                log_security_event(
                    event_name="User login failed",
                    severity=AuditSeverity.HIGH,
                    description=f"Failed login attempt from {client_ip} (attempt #{self.failed_login_cache[client_ip]})",
                    additional_data={
                        "ip_address": client_ip,
                        "attempt_number": self.failed_login_cache[client_ip],
                        "endpoint": str(request.url.path),
                    },
                )

                # Alert on multiple failed attempts
                if self.failed_login_cache[client_ip] >= 5:
                    log_security_event(
                        event_name="Multiple failed login attempts",
                        severity=AuditSeverity.CRITICAL,
                        description=f"Multiple failed login attempts from {client_ip} - possible brute force attack",
                        additional_data={
                            "ip_address": client_ip,
                            "total_attempts": self.failed_login_cache[client_ip],
                        },
                    )

            raise

    async def _monitor_admin_request(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Monitor administrative function access."""

        # Log all admin access
        log_security_event(
            event_name="Admin endpoint access",
            severity=AuditSeverity.HIGH,
            description=f"Access to admin endpoint: {request.url.path}",
            additional_data={
                "endpoint": str(request.url.path),
                "method": request.method,
                "ip_address": self._get_client_ip(request),
            },
        )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        if request.client:
            return request.client.host
        return "unknown"


# Global database audit listener
db_audit_listener = DatabaseAuditListener()


def setup_audit_middleware(app):
    """Setup all audit middleware components."""

    # Add HTTP audit middleware
    app.add_middleware(AuditMiddleware)

    # Add security audit middleware
    app.add_middleware(SecurityAuditMiddleware)

    # Setup database audit listeners
    db_audit_listener.setup_listeners()

    logger.info("📋 Audit middleware configured successfully")


def initialize_audit_system():
    """Initialize the complete audit system."""
    try:
        # Create audit tables
        from dotmac_isp.core.audit_trail import create_audit_tables

        create_audit_tables()

        # Setup database listeners
        db_audit_listener.setup_listeners()

        logger.info("📋 Audit system initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize audit system: {e}")
        raise
