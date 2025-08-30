"""
Comprehensive Database Audit Logging for Multi-Tenant Security
Provides detailed audit trails for all database operations with tenant context

SECURITY: This module ensures complete audit trail for compliance and security monitoring
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events"""

    DATABASE_CONNECTION = "db_connection"
    QUERY_EXECUTION = "query_execution"
    TENANT_CONTEXT_SET = "tenant_context_set"
    TENANT_CONTEXT_CLEAR = "tenant_context_clear"
    CROSS_TENANT_ATTEMPT = "cross_tenant_attempt"
    RLS_POLICY_VIOLATION = "rls_policy_violation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DatabaseAuditLogger:
    """
    Comprehensive database audit logging system
    """

    def __init__(self, engine: Engine):
        self.engine = engine
        self.session_local = None
        self._setup_audit_table()
        self._setup_event_listeners()

    def _setup_audit_table(self):
        """Ensure audit table exists with proper structure"""
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS database_audit_log (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        event_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) DEFAULT 'info',

                        -- Tenant and user context
                        tenant_id VARCHAR(255),
                        user_id VARCHAR(255),
                        session_id VARCHAR(255),

                        -- Request context
                        ip_address INET,
                        user_agent TEXT,
                        request_id VARCHAR(255),

                        -- Database context
                        database_name VARCHAR(255),
                        table_name VARCHAR(255),
                        operation_type VARCHAR(50),
                        query_hash VARCHAR(64),

                        -- Event details
                        event_title VARCHAR(500),
                        event_description TEXT,
                        event_data JSONB,

                        -- Results and performance
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        execution_time_ms INTEGER,
                        rows_affected INTEGER,

                        -- Compliance and tags
                        compliance_tags TEXT[],
                        risk_level VARCHAR(20) DEFAULT 'low',

                        -- Indexing for performance
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """
                    )
                )

                # Create performance indexes
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_db_audit_timestamp ON database_audit_log(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_db_audit_tenant_id ON database_audit_log(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_db_audit_event_type ON database_audit_log(event_type);
                    CREATE INDEX IF NOT EXISTS idx_db_audit_severity ON database_audit_log(severity);
                    CREATE INDEX IF NOT EXISTS idx_db_audit_success ON database_audit_log(success);
                    CREATE INDEX IF NOT EXISTS idx_db_audit_user_id ON database_audit_log(user_id);
                    CREATE INDEX IF NOT EXISTS idx_db_audit_ip ON database_audit_log(ip_address);
                """
                    )
                )

                logger.info("✅ Database audit table and indexes created")

        except Exception as e:
            logger.error(f"Failed to setup audit table: {e}")

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for automatic audit logging"""

        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            """Log before query execution"""
            context._query_start_time = datetime.now(timezone.utc)

            # Get tenant context if available
            try:
                tenant_id = conn.execute(
                    "SELECT current_setting('app.current_tenant_id', true)"
                ).scalar()
                user_id = conn.execute(
                    "SELECT current_setting('app.current_user_id', true)"
                ).scalar()
            except Exception:
                tenant_id = None
                user_id = None

            context._audit_data = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "statement": statement[:1000],  # Truncate long statements
                "parameters": str(parameters)[:500] if parameters else None,
            }

        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            """Log after query execution"""
            if hasattr(context, "_query_start_time"):
                execution_time = (
                    datetime.now(timezone.utc) - context._query_start_time
                ).total_seconds() * 1000

                audit_data = getattr(context, "_audit_data", {})

                # Determine operation type
                operation_type = "SELECT"
                if statement.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                    operation_type = statement.strip().split()[0].upper()

                # Log the query execution
                asyncio.create_task(
                    self.log_event(
                        event_type=AuditEventType.QUERY_EXECUTION,
                        severity=AuditSeverity.INFO,
                        tenant_id=audit_data.get("tenant_id"),
                        user_id=audit_data.get("user_id"),
                        operation_type=operation_type,
                        event_title=f"Query executed: {operation_type}",
                        event_description=f"Executed query in {execution_time:.2f}ms",
                        event_data={
                            "statement_preview": audit_data.get("statement"),
                            "execution_time_ms": execution_time,
                            "parameters": audit_data.get("parameters"),
                        },
                        execution_time_ms=int(execution_time),
                        rows_affected=(
                            cursor.rowcount if hasattr(cursor, "rowcount") else None
                        ),
                    )
                )

    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        event_title: Optional[str] = None,
        event_description: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        rows_affected: Optional[int] = None,
        compliance_tags: Optional[List[str]] = None,
        risk_level: str = "low",
    ) -> bool:
        """Log an audit event to the database"""
        try:
            with self.engine.begin() as conn:
                # Generate query hash for deduplication
                query_hash = None
                if event_data and "statement_preview" in event_data:
                    import hashlib

                    query_hash = hashlib.md5(
                        event_data["statement_preview"].encode()
                    ).hexdigest()[:32]

                conn.execute(
                    text(
                        """
                    INSERT INTO database_audit_log (
                        event_type, severity, tenant_id, user_id, session_id,
                        ip_address, user_agent, request_id, database_name, table_name,
                        operation_type, query_hash, event_title, event_description, event_data,
                        success, error_message, execution_time_ms, rows_affected,
                        compliance_tags, risk_level
                    ) VALUES (
                        :event_type, :severity, :tenant_id, :user_id, :session_id,
                        :ip_address, :user_agent, :request_id, :database_name, :table_name,
                        :operation_type, :query_hash, :event_title, :event_description, :event_data,
                        :success, :error_message, :execution_time_ms, :rows_affected,
                        :compliance_tags, :risk_level
                    )
                """
                    ),
                    {
                        "event_type": event_type.value,
                        "severity": severity.value,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "request_id": request_id,
                        "database_name": database_name,
                        "table_name": table_name,
                        "operation_type": operation_type,
                        "query_hash": query_hash,
                        "event_title": event_title,
                        "event_description": event_description,
                        "event_data": json.dumps(event_data) if event_data else None,
                        "success": success,
                        "error_message": error_message,
                        "execution_time_ms": execution_time_ms,
                        "rows_affected": rows_affected,
                        "compliance_tags": compliance_tags,
                        "risk_level": risk_level,
                    },
                )

            return True

        except Exception as e:
            # Fallback to file logging if database logging fails
            logger.error(f"Database audit logging failed: {e}")
            logger.info(
                f"AUDIT: {event_type.value} - {event_title} - Tenant: {tenant_id}"
            )
            return False

    async def log_tenant_context_change(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        action: str = "set",
        ip_address: Optional[str] = None,
    ) -> bool:
        """Log tenant context changes for security monitoring"""
        return await self.log_event(
            event_type=(
                AuditEventType.TENANT_CONTEXT_SET
                if action == "set"
                else AuditEventType.TENANT_CONTEXT_CLEAR
            ),
            severity=AuditSeverity.INFO,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip_address,
            event_title=f"Tenant context {action}",
            event_description=f"Database tenant context {action} to {tenant_id}",
            event_data={"action": action, "tenant_id": tenant_id},
            compliance_tags=["tenant_security", "context_management"],
        )

    async def log_cross_tenant_attempt(
        self,
        attempting_tenant: str,
        target_tenant: str,
        user_id: Optional[str] = None,
        table_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Log cross-tenant access attempts (security incidents)"""
        return await self.log_event(
            event_type=AuditEventType.CROSS_TENANT_ATTEMPT,
            severity=AuditSeverity.CRITICAL,
            tenant_id=attempting_tenant,
            user_id=user_id,
            table_name=table_name,
            operation_type=operation_type,
            ip_address=ip_address,
            event_title="Cross-tenant access attempt detected",
            event_description=f"Tenant {attempting_tenant} attempted to access data from tenant {target_tenant}",
            event_data={
                "attempting_tenant": attempting_tenant,
                "target_tenant": target_tenant,
                "blocked": True,
            },
            success=False,
            compliance_tags=[
                "security_incident",
                "tenant_isolation",
                "access_violation",
            ],
            risk_level="critical",
        )

    async def get_audit_summary(
        self, tenant_id: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """Get audit summary for the last N hours"""
        try:
            with self.engine.begin() as conn:
                where_clause = ""
                params = {"hours": hours}

                if tenant_id:
                    where_clause = "AND tenant_id = :tenant_id"
                    params["tenant_id"] = tenant_id

                result = conn.execute(
                    text(
                        f"""
                    SELECT
                        event_type,
                        severity,
                        COUNT(*) as count,
                        COUNT(CASE WHEN success = false THEN 1 END) as failures
                    FROM database_audit_log
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                    {where_clause}
                    GROUP BY event_type, severity
                    ORDER BY count DESC
                """
                    ),
                    params,
                )

                summary = []
                for row in result.fetchall():
                    summary.append(
                        {
                            "event_type": row.event_type,
                            "severity": row.severity,
                            "count": row.count,
                            "failures": row.failures,
                        }
                    )

                return {
                    "period_hours": hours,
                    "tenant_id": tenant_id,
                    "summary": summary,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to generate audit summary: {e}")
            return {"error": str(e)}


# Global audit logger instance
audit_logger: Optional[DatabaseAuditLogger] = None


def init_database_audit_logging(engine: Engine) -> DatabaseAuditLogger:
    """Initialize database audit logging"""
    global audit_logger
    audit_logger = DatabaseAuditLogger(engine)
    logger.info("✅ Database audit logging initialized")
    return audit_logger


def get_audit_logger() -> Optional[DatabaseAuditLogger]:
    """Get the global audit logger instance"""
    return audit_logger
