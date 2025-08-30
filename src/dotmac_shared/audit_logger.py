#!/usr/bin/env python3
"""
Audit Logging System for DotMac Framework
Provides comprehensive audit trail functionality
"""

import datetime
import inspect
import json
import logging
import uuid
from datetime import timezone
from functools import wraps
from typing import Any, Dict, Optional


class AuditLogger:
    """AuditLogger implementation."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("audit")

    def log_event(
        self,
        event_type: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        action: str = None,
        details: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
    ):
        """Log an audit event"""

        audit_record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "status": status,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }

        try:
            self.logger.info(json.dumps(audit_record))
        except (TypeError, ValueError) as e:
            # Handle JSON serialization errors gracefully
            safe_record = {k: str(v) for k, v in audit_record.items()}
            self.logger.info(json.dumps(safe_record))

    def log_authentication(
        self,
        user_id: str,
        action: str,
        status: str,
        ip_address: str = None,
        details: Dict[str, Any] = None,
    ):
        """Log authentication events"""
        self.log_event(
            event_type="authentication",
            user_id=user_id,
            action=action,
            status=status,
            ip_address=ip_address,
            details=details,
        )

    def log_authorization(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        status: str,
        details: Dict[str, Any] = None,
    ):
        """Log authorization events"""
        self.log_event(
            event_type="authorization",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            details=details,
        )

    def log_data_access(
        self,
        user_id: str,
        table_name: str,
        operation: str,
        record_count: int = None,
        details: Dict[str, Any] = None,
    ):
        """Log data access events"""
        access_details = {"record_count": record_count, **(details or {})}
        self.log_event(
            event_type="data_access",
            user_id=user_id,
            resource_type="database",
            resource_id=table_name,
            action=operation,
            details=access_details,
        )

    def log_system_event(
        self,
        event_type: str,
        service_name: str,
        status: str,
        details: Dict[str, Any] = None,
    ):
        """Log system events"""
        self.log_event(
            event_type=event_type,
            user_id="system",
            resource_type="system",
            resource_id=service_name,
            action=event_type,
            status=status,
            details=details,
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: str = None,
        ip_address: str = None,
        details: Dict[str, Any] = None,
    ):
        """Log security events"""
        security_details = {
            "severity": severity,
            "description": description,
            **(details or {}),
        }

        self.log_event(
            event_type=f"security_{event_type}",
            user_id=user_id,
            action=event_type,
            status="alert" if severity in ["high", "critical"] else "warning",
            ip_address=ip_address,
            details=security_details,
        )


# Decorators for automatic audit logging
def audit_api_call(resource_type: str = None, action: str = None):
    """Decorator to automatically audit API calls"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            audit = AuditLogger()

            # Extract user info from request context (FastAPI)
            user_id = None
            ip_address = None

            try:
                # Attempt to get user info from FastAPI request
                for arg in args:
                    if hasattr(arg, "state") and hasattr(arg.state, "user"):
                        user_id = getattr(arg.state.user, "id", None)
                    if hasattr(arg, "client") and hasattr(arg.client, "host"):
                        ip_address = arg.client.host
                        break

                # Execute the function
                result = func(*args, **kwargs)

                # Log successful API call
                audit.log_event(
                    event_type="api_call",
                    user_id=user_id,
                    resource_type=resource_type or func.__name__,
                    action=action or func.__name__,
                    status="success",
                    ip_address=ip_address,
                    details={"function": func.__name__, "module": func.__module__},
                )

                return result

            except Exception as e:
                # Log failed API call
                audit.log_event(
                    event_type="api_call",
                    user_id=user_id,
                    resource_type=resource_type or func.__name__,
                    action=action or func.__name__,
                    status="error",
                    ip_address=ip_address,
                    details={
                        "function": func.__name__,
                        "module": func.__module__,
                        "error": str(e),
                    },
                )
                raise

        return wrapper

    return decorator


def audit_database_operation(operation_type: str):
    """Decorator to audit database operations"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            audit = AuditLogger()

            try:
                result = func(*args, **kwargs)

                audit.log_event(
                    event_type="database_operation",
                    action=operation_type,
                    status="success",
                    details={"function": func.__name__, "operation": operation_type},
                )

                return result

            except Exception as e:
                audit.log_event(
                    event_type="database_operation",
                    action=operation_type,
                    status="error",
                    details={
                        "function": func.__name__,
                        "operation": operation_type,
                        "error": str(e),
                    },
                )
                raise

        return wrapper

    return decorator


# Global audit logger instance
audit_logger = AuditLogger()
