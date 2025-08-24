"""Comprehensive audit trail system for compliance and security tracking.

This module provides detailed audit logging for all data changes, user actions,
and system events to meet compliance requirements (GDPR, SOX, HIPAA, etc.).
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
import hashlib
import hmac

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from fastapi import Request

from dotmac_isp.shared.database.base import Base, TenantModel
from dotmac_isp.core.database import engine, get_db
from dotmac_isp.shared.cache import get_cache_manager

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_FAILED_LOGIN = "user_failed_login"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_VIEW = "data_view"
    DATA_EXPORT = "data_export"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"
    API_ACCESS = "api_access"
    BULK_OPERATION = "bulk_operation"


class AuditSeverity(Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Compliance frameworks for audit requirements."""

    GDPR = "gdpr"
    SOX = "sox"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    SOC2 = "soc2"


@dataclass
class AuditContext:
    """Context information for audit events."""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    source_system: Optional[str] = None
    correlation_id: Optional[str] = None


class AuditLog(TenantModel):
    """Main audit log table for tracking all system events."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_tenant_id", "tenant_id"),
        Index("idx_audit_logs_severity", "severity"),
        Index("idx_audit_logs_table_name", "table_name"),
        Index("idx_audit_logs_compliance", "compliance_frameworks"),
        {"extend_existing": True},
    )

    # Event identification
    event_type = Column(String(50), nullable=False)
    event_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="medium")

    # User and session context
    user_id = Column(UUID(as_uuid=False), nullable=True)
    username = Column(String(100), nullable=True)
    user_role = Column(String(50), nullable=True)
    session_id = Column(String(200), nullable=True)

    # Request context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_url = Column(Text, nullable=True)

    # Data context
    table_name = Column(String(100), nullable=True)
    record_id = Column(UUID(as_uuid=False), nullable=True)
    entity_type = Column(String(100), nullable=True)

    # Change tracking
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    changed_fields = Column(JSONB, nullable=True)  # Array of field names

    # System context
    source_system = Column(String(100), nullable=True, default="dotmac_isp")
    correlation_id = Column(String(100), nullable=True)
    parent_audit_id = Column(UUID(as_uuid=False), nullable=True)

    # Compliance and retention
    compliance_frameworks = Column(JSONB, nullable=True)  # Array of frameworks
    retention_period_days = Column(
        Integer, nullable=False, default=2555
    )  # 7 years default
    is_immutable = Column(Boolean, nullable=False, default=True)

    # Integrity and verification
    event_hash = Column(String(64), nullable=True)  # SHA-256 hash
    signature = Column(String(512), nullable=True)  # HMAC signature

    # Timestamp (inherited from TenantModel)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DataChangeLog(TenantModel):
    """Detailed data change tracking for specific table operations."""

    __tablename__ = "data_change_logs"
    __table_args__ = (
        Index("idx_data_change_logs_table_record", "table_name", "record_id"),
        Index("idx_data_change_logs_created_at", "created_at"),
        Index("idx_data_change_logs_operation", "operation"),
        {"extend_existing": True},
    )

    # Reference to main audit log
    audit_log_id = Column(UUID(as_uuid=False), nullable=False)

    # Table and record information
    table_name = Column(String(100), nullable=False)
    record_id = Column(UUID(as_uuid=False), nullable=False)
    operation = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE

    # Detailed change information
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    data_type = Column(String(50), nullable=True)

    # Sensitive data handling
    is_sensitive = Column(Boolean, nullable=False, default=False)
    is_encrypted = Column(Boolean, nullable=False, default=False)
    encryption_key_id = Column(String(100), nullable=True)


class ComplianceAuditReport(TenantModel):
    """Pre-generated compliance audit reports for faster retrieval."""

    __tablename__ = "compliance_audit_reports"
    __table_args__ = (
        Index("idx_compliance_reports_framework", "framework"),
        Index(
            "idx_compliance_reports_period", "report_period_start", "report_period_end"
        ),
        {"extend_existing": True},
    )

    # Report identification
    report_name = Column(String(200), nullable=False)
    framework = Column(String(50), nullable=False)
    report_type = Column(String(100), nullable=False)

    # Time period
    report_period_start = Column(DateTime(timezone=True), nullable=False)
    report_period_end = Column(DateTime(timezone=True), nullable=False)

    # Report data
    total_events = Column(Integer, nullable=False, default=0)
    critical_events = Column(Integer, nullable=False, default=0)
    violations_found = Column(Integer, nullable=False, default=0)

    # Report content
    summary = Column(JSONB, nullable=True)
    findings = Column(JSONB, nullable=True)
    recommendations = Column(JSONB, nullable=True)

    # Generation metadata
    generated_by = Column(UUID(as_uuid=False), nullable=False)
    generation_time_seconds = Column(Integer, nullable=True)
    report_hash = Column(String(64), nullable=True)


class AuditTrailManager:
    """Central manager for audit trail operations."""

    def __init__(self):
        """  Init   operation."""
        self.cache_manager = get_cache_manager()
        self.current_context: Optional[AuditContext] = None
        self.sensitive_fields = {
            "password",
            "password_hash",
            "ssn",
            "credit_card",
            "bank_account",
            "api_key",
            "secret",
            "token",
            "private_key",
        }

    def set_context(self, context: AuditContext):
        """Set audit context for current operation."""
        self.current_context = context

    def log_event(
        self,
        event_type: AuditEventType,
        event_name: str,
        description: str = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        table_name: str = None,
        record_id: str = None,
        old_values: Dict[str, Any] = None,
        new_values: Dict[str, Any] = None,
        compliance_frameworks: List[ComplianceFramework] = None,
        additional_data: Dict[str, Any] = None,
    ) -> str:
        """Log an audit event."""

        try:
            # Prepare audit log entry
            audit_entry = self._prepare_audit_entry(
                event_type=event_type,
                event_name=event_name,
                description=description,
                severity=severity,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                compliance_frameworks=compliance_frameworks,
                additional_data=additional_data,
            )

            # Save to database
            with next(get_db()) as db:
                db.add(audit_entry)
                db.commit()
                audit_id = audit_entry.id

            # Log detailed changes if applicable
            if old_values or new_values:
                self._log_detailed_changes(
                    audit_id, table_name, record_id, old_values, new_values
                )

            # Cache recent events for quick access
            self._cache_recent_event(audit_entry)

            logger.info(f"📋 Audit event logged: {event_type.value} - {event_name}")
            return audit_id

        except Exception as e:
            logger.error(f"❌ Failed to log audit event: {e}")
            # Don't raise exception to avoid breaking main application flow
            return None

    def _prepare_audit_entry(self, **kwargs) -> AuditLog:
        """Prepare audit log entry with all context information."""
        context = self.current_context or AuditContext()

        # Sanitize sensitive data
        old_values = self._sanitize_sensitive_data(kwargs.get("old_values", {}))
        new_values = self._sanitize_sensitive_data(kwargs.get("new_values", {}))

        # Calculate changed fields
        changed_fields = []
        if old_values and new_values:
            changed_fields = [
                k
                for k in new_values.keys()
                if k in old_values and old_values[k] != new_values[k]
            ]

        # Prepare entry data
        entry_data = {
            "event_type": kwargs["event_type"].value,
            "event_name": kwargs["event_name"],
            "description": kwargs.get("description"),
            "severity": kwargs["severity"].value,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "ip_address": context.ip_address,
            "user_agent": context.user_agent,
            "request_id": context.request_id,
            "table_name": kwargs.get("table_name"),
            "record_id": kwargs.get("record_id"),
            "old_values": old_values,
            "new_values": new_values,
            "changed_fields": changed_fields,
            "source_system": context.source_system or "dotmac_isp",
            "correlation_id": context.correlation_id,
            "tenant_id": context.tenant_id,
            "timestamp": datetime.utcnow(),
        }

        # Add compliance frameworks
        if kwargs.get("compliance_frameworks"):
            entry_data["compliance_frameworks"] = [
                f.value for f in kwargs["compliance_frameworks"]
            ]

        # Create audit entry
        audit_entry = AuditLog(**entry_data)

        # Generate integrity hash
        audit_entry.event_hash = self._generate_event_hash(audit_entry)

        return audit_entry

    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive data from audit logs."""
        if not data:
            return data

        sanitized = data.copy()

        for field in self.sensitive_fields:
            if field in sanitized:
                if sanitized[field]:
                    # Mask sensitive data
                    sanitized[field] = "***REDACTED***"

        # Check for credit card patterns
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) >= 13:
                # Simple credit card pattern detection
                if value.replace("-", "").replace(" ", "").isdigit():
                    sanitized[key] = f"****-****-****-{value[-4:]}"

        return sanitized

    def _generate_event_hash(self, audit_entry: AuditLog) -> str:
        """Generate SHA-256 hash for audit entry integrity."""
        # Create deterministic string from audit entry
        hash_data = f"{audit_entry.event_type}|{audit_entry.event_name}|{audit_entry.timestamp}|{audit_entry.user_id}|{audit_entry.record_id}"
        return hashlib.sha256(hash_data.encode()).hexdigest()

    def _log_detailed_changes(
        self,
        audit_id: str,
        table_name: str,
        record_id: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
    ):
        """Log detailed field-level changes."""
        if not old_values and not new_values:
            return

        try:
            with next(get_db()) as db:
                # Log each changed field
                all_fields = set((old_values or {}).keys()) | set(
                    (new_values or {}).keys()
                )

                for field in all_fields:
                    old_val = (old_values or {}).get(field)
                    new_val = (new_values or {}).get(field)

                    # Only log if values are different
                    if old_val != new_val:
                        change_log = DataChangeLog(
                            audit_log_id=audit_id,
                            table_name=table_name,
                            record_id=record_id,
                            operation=(
                                "UPDATE"
                                if old_values and new_values
                                else ("INSERT" if new_values else "DELETE")
                            ),
                            field_name=field,
                            old_value=str(old_val) if old_val is not None else None,
                            new_value=str(new_val) if new_val is not None else None,
                            is_sensitive=field.lower() in self.sensitive_fields,
                            tenant_id=(
                                self.current_context.tenant_id
                                if self.current_context
                                else None
                            ),
                        )
                        db.add(change_log)

                db.commit()

        except Exception as e:
            logger.error(f"Failed to log detailed changes: {e}")

    def _cache_recent_event(self, audit_entry: AuditLog):
        """Cache recent audit event for quick access."""
        try:
            cache_key = f"recent_audit_events:{audit_entry.tenant_id}"
            recent_events = self.cache_manager.get(cache_key, "audit") or []

            # Add new event (keep last 100)
            event_data = {
                "id": audit_entry.id,
                "event_type": audit_entry.event_type,
                "event_name": audit_entry.event_name,
                "timestamp": audit_entry.timestamp.isoformat(),
                "severity": audit_entry.severity,
                "user_id": audit_entry.user_id,
            }

            recent_events.insert(0, event_data)
            recent_events = recent_events[:100]  # Keep last 100

            # Cache for 1 hour
            self.cache_manager.set(cache_key, recent_events, 3600, "audit")

        except Exception as e:
            logger.error(f"Failed to cache recent audit event: {e}")

    def get_audit_trail(
        self,
        entity_type: str = None,
        record_id: str = None,
        user_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        event_types: List[AuditEventType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit trail with filtering options."""

        try:
            with next(get_db()) as db:
                query = db.query(AuditLog)

                # Apply filters
                if self.current_context and self.current_context.tenant_id:
                    query = query.filter(
                        AuditLog.tenant_id == self.current_context.tenant_id
                    )

                if entity_type:
                    query = query.filter(AuditLog.table_name == entity_type)

                if record_id:
                    query = query.filter(AuditLog.record_id == record_id)

                if user_id:
                    query = query.filter(AuditLog.user_id == user_id)

                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)

                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)

                if event_types:
                    type_values = [et.value for et in event_types]
                    query = query.filter(AuditLog.event_type.in_(type_values))

                # Order by timestamp descending and limit
                audit_logs = (
                    query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
                )

                # Convert to dictionaries
                return [self._audit_log_to_dict(log) for log in audit_logs]

        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []

    def _audit_log_to_dict(self, audit_log: AuditLog) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            "id": audit_log.id,
            "event_type": audit_log.event_type,
            "event_name": audit_log.event_name,
            "description": audit_log.description,
            "severity": audit_log.severity,
            "timestamp": audit_log.timestamp.isoformat(),
            "user_id": audit_log.user_id,
            "username": audit_log.username,
            "table_name": audit_log.table_name,
            "record_id": audit_log.record_id,
            "changed_fields": audit_log.changed_fields,
            "ip_address": str(audit_log.ip_address) if audit_log.ip_address else None,
            "request_id": audit_log.request_id,
        }

    def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        start_date: datetime,
        end_date: datetime,
        tenant_id: str = None,
    ) -> Dict[str, Any]:
        """Generate compliance audit report."""

        try:
            with next(get_db()) as db:
                query = db.query(AuditLog).filter(
                    AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date
                )

                if tenant_id:
                    query = query.filter(AuditLog.tenant_id == tenant_id)

                # Filter by compliance framework
                query = query.filter(
                    AuditLog.compliance_frameworks.contains([framework.value])
                )

                audit_logs = query.all()

                # Generate report
                report = {
                    "framework": framework.value,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "total_events": len(audit_logs),
                    "critical_events": len(
                        [log for log in audit_logs if log.severity == "critical"]
                    ),
                    "event_breakdown": {},
                    "user_activity": {},
                    "security_events": [],
                    "compliance_violations": [],
                }

                # Event breakdown by type
                for log in audit_logs:
                    event_type = log.event_type
                    if event_type not in report["event_breakdown"]:
                        report["event_breakdown"][event_type] = 0
                    report["event_breakdown"][event_type] += 1

                # User activity summary
                for log in audit_logs:
                    if log.user_id:
                        if log.user_id not in report["user_activity"]:
                            report["user_activity"][log.user_id] = 0
                        report["user_activity"][log.user_id] += 1

                # Identify security events
                security_event_types = [
                    "user_failed_login",
                    "security_event",
                    "permission_grant",
                    "permission_revoke",
                ]
                report["security_events"] = [
                    self._audit_log_to_dict(log)
                    for log in audit_logs
                    if log.event_type in security_event_types
                ]

                return report

        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {}

    def cleanup_old_audit_logs(self, days_to_keep: int = 2555) -> int:
        """Clean up old audit logs based on retention policy."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        try:
            with next(get_db()) as db:
                # Delete old audit logs
                deleted_count = (
                    db.query(AuditLog)
                    .filter(
                        AuditLog.timestamp < cutoff_date,
                        AuditLog.is_immutable
                        == False,  # Only delete non-immutable records
                    )
                    .delete()
                )

                # Delete related change logs
                db.query(DataChangeLog).filter(
                    DataChangeLog.created_at < cutoff_date
                ).delete()

                db.commit()

                logger.info(f"🧹 Cleaned up {deleted_count} old audit log entries")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            return 0


# Context manager for audit operations
@contextmanager
def audit_context(
    user_id: str = None,
    tenant_id: str = None,
    session_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
    request_id: str = None,
):
    """Context manager for setting audit context."""
    context = AuditContext(
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    audit_manager.set_context(context)
    try:
        yield audit_manager
    finally:
        audit_manager.set_context(None)


def create_audit_tables():
    """Create audit trail tables in the database."""
    try:
        # Create tables
        Base.metadata.create_all(
            bind=engine,
            tables=[
                AuditLog.__table__,
                DataChangeLog.__table__,
                ComplianceAuditReport.__table__,
            ],
        )

        logger.info("📋 Audit trail tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create audit tables: {e}")
        raise


# Global audit trail manager
audit_manager = AuditTrailManager()


# Convenience functions
def log_user_action(action: str, description: str = None, **kwargs):
    """Log a user action."""
    return audit_manager.log_event(
        event_type=AuditEventType.API_ACCESS,
        event_name=action,
        description=description,
        **kwargs,
    )


def log_data_change(
    table_name: str,
    record_id: str,
    operation: str,
    old_values: Dict = None,
    new_values: Dict = None,
    **kwargs,
):
    """Log a data change."""
    event_type_map = {
        "INSERT": AuditEventType.DATA_CREATE,
        "UPDATE": AuditEventType.DATA_UPDATE,
        "DELETE": AuditEventType.DATA_DELETE,
    }

    return audit_manager.log_event(
        event_type=event_type_map.get(operation, AuditEventType.DATA_UPDATE),
        event_name=f"{operation} {table_name}",
        table_name=table_name,
        record_id=record_id,
        old_values=old_values,
        new_values=new_values,
        **kwargs,
    )


def log_security_event(
    event_name: str, severity: AuditSeverity = AuditSeverity.HIGH, **kwargs
):
    """Log a security event."""
    return audit_manager.log_event(
        event_type=AuditEventType.SECURITY_EVENT,
        event_name=event_name,
        severity=severity,
        compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
        **kwargs,
    )
