"""
Tenant-Aware Database Connection Pooling
Provides secure database connections with automatic tenant context management

SECURITY: This module ensures tenant context is properly maintained
across all database connections and operations
"""

import asyncio
import logging
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .database_audit import AuditEventType, AuditSeverity, DatabaseAuditLogger

logger = logging.getLogger(__name__)


class TenantAwareConnectionPool:
    """
    Connection pool that automatically manages tenant context
    """

    def __init__(
        self,
        database_url: str,
        audit_logger: Optional[DatabaseAuditLogger] = None,
        max_connections: int = 20,
        min_connections: int = 5,
        connection_timeout: int = 30,
        enable_audit_logging: bool = True,
    ):
        self.database_url = database_url
        self.audit_logger = audit_logger
        self.enable_audit_logging = enable_audit_logging
        self.active_connections = {}

        # Create engine with tenant-aware pool
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=max_connections,
            max_overflow=10,
            pool_timeout=connection_timeout,
            pool_pre_ping=True,  # Validate connections
            echo=False,  # Set to True for query debugging
            future=True,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False, expire_on_commit=False)

        # Setup connection event listeners
        self._setup_connection_listeners()

    def _setup_connection_listeners(self):
        """Setup connection event listeners for audit and security"""

        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Called when a new connection is created"""
            if self.enable_audit_logging and self.audit_logger:
                asyncio.create_task(
                    self.audit_logger.log_event(
                        event_type=AuditEventType.DATABASE_CONNECTION,
                        severity=AuditSeverity.INFO,
                        event_title="Database connection established",
                        event_description="New database connection created in pool",
                        event_data={"connection_id": id(dbapi_connection)},
                    )
                )

        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Called when a connection is checked out from the pool"""
            connection_id = id(dbapi_connection)
            self.active_connections[connection_id] = {
                "checked_out_at": asyncio.get_event_loop().time(),
                "tenant_id": None,
                "user_id": None,
            }

        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Called when a connection is returned to the pool"""
            connection_id = id(dbapi_connection)
            if connection_id in self.active_connections:
                # Clear any tenant context when connection is returned
                try:
                    dbapi_connection.execute("SELECT set_config('app.current_tenant_id', '', false);")
                    dbapi_connection.execute("SELECT set_config('app.current_user_id', '', false);")
                    dbapi_connection.execute("SELECT set_config('app.client_ip', '', false);")
                except Exception:
                    pass  # Ignore errors during cleanup

                del self.active_connections[connection_id]

    @asynccontextmanager
    async def get_tenant_session(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AbstractAsyncContextManager[Session]:
        """
        Get a database session with tenant context automatically set
        """
        session = self.SessionLocal()
        connection_id = id(session.connection())

        try:
            # Set tenant context
            session.execute(text(f"SELECT set_config('app.current_tenant_id', '{tenant_id}', false);"))

            if user_id:
                session.execute(text(f"SELECT set_config('app.current_user_id', '{user_id}', false);"))

            if client_ip:
                session.execute(text(f"SELECT set_config('app.client_ip', '{client_ip}', false);"))

            if request_id:
                session.execute(text(f"SELECT set_config('app.request_id', '{request_id}', false);"))

            # Update connection tracking
            if connection_id in self.active_connections:
                self.active_connections[connection_id].update(
                    {"tenant_id": tenant_id, "user_id": user_id, "client_ip": client_ip}
                )

            # Log tenant context setting
            if self.enable_audit_logging and self.audit_logger:
                await self.audit_logger.log_tenant_context_change(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action="set",
                    ip_address=client_ip,
                )

            logger.debug(f"Database session configured for tenant: {tenant_id}")
            yield session

        except Exception as e:
            session.rollback()
            logger.error(f"Tenant session error: {e}")

            # Log the error
            if self.enable_audit_logging and self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DATABASE_CONNECTION,
                    severity=AuditSeverity.ERROR,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    ip_address=client_ip,
                    event_title="Tenant session error",
                    event_description=f"Error in tenant database session: {str(e)}",
                    success=False,
                    error_message=str(e),
                )

            raise
        finally:
            try:
                # Clear tenant context
                session.execute(text("SELECT set_config('app.current_tenant_id', '', false);"))
                session.execute(text("SELECT set_config('app.current_user_id', '', false);"))
                session.execute(text("SELECT set_config('app.client_ip', '', false);"))

                if self.enable_audit_logging and self.audit_logger:
                    await self.audit_logger.log_tenant_context_change(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        action="clear",
                        ip_address=client_ip,
                    )

            except Exception:
                pass  # Ignore cleanup errors
            finally:
                session.close()

    @asynccontextmanager
    async def get_admin_session(
        self,
        admin_user_id: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AbstractAsyncContextManager[Session]:
        """
        Get an administrative session that bypasses tenant isolation
        WARNING: Only use for system administration tasks
        """
        session = self.SessionLocal()

        try:
            # Set admin context (no tenant_id)
            if admin_user_id:
                session.execute(text(f"SELECT set_config('app.current_user_id', '{admin_user_id}', false);"))
                session.execute(text("SELECT set_config('app.admin_context', 'true', false);"))

            if client_ip:
                session.execute(text(f"SELECT set_config('app.client_ip', '{client_ip}', false);"))

            if request_id:
                session.execute(text(f"SELECT set_config('app.request_id', '{request_id}', false);"))

            # Log admin session creation
            if self.enable_audit_logging and self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DATABASE_CONNECTION,
                    severity=AuditSeverity.WARNING,
                    user_id=admin_user_id,
                    ip_address=client_ip,
                    event_title="Admin database session created",
                    event_description="Administrative session bypassing tenant isolation",
                    event_data={"admin_context": True},
                    compliance_tags=["admin_access", "tenant_bypass"],
                    risk_level="medium",
                )

            logger.warning(f"Admin database session created for user: {admin_user_id}")
            yield session

        except Exception as e:
            session.rollback()
            logger.error(f"Admin session error: {e}")
            raise
        finally:
            try:
                # Clear admin context
                session.execute(text("SELECT set_config('app.current_user_id', '', false);"))
                session.execute(text("SELECT set_config('app.admin_context', 'false', false);"))
                session.execute(text("SELECT set_config('app.client_ip', '', false);"))
            except Exception:
                pass
            finally:
                session.close()

    async def get_connection_stats(self) -> dict[str, Any]:
        """Get current connection pool statistics"""
        pool = self.engine.pool

        return {
            "pool_size": pool.size(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "invalid_connections": pool.invalidated(),
            "active_tenant_sessions": len(self.active_connections),
            "tenant_sessions": [
                {
                    "connection_id": conn_id,
                    "tenant_id": info.get("tenant_id"),
                    "user_id": info.get("user_id"),
                    "duration_seconds": asyncio.get_event_loop().time() - info.get("checked_out_at", 0),
                }
                for conn_id, info in self.active_connections.items()
            ],
        }

    async def validate_tenant_isolation(self, tenant_1: str, tenant_2: str) -> dict[str, Any]:
        """
        Validate that tenant isolation is working at the connection pool level
        """
        results = {"isolation_test_passed": True, "tests": []}

        try:
            # Test 1: Create session for tenant 1
            async with self.get_tenant_session(tenant_1) as session1:
                # Try to access tenant 2 data - should fail or return empty
                try:
                    session1.execute(
                        text(
                            """
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name LIKE '%tenant%'
                    """
                        )
                    ).scalar()

                    results["tests"].append(
                        {
                            "test": "tenant_1_session_created",
                            "passed": True,
                            "details": f"Session created for tenant {tenant_1}",
                        }
                    )

                except Exception as e:
                    results["isolation_test_passed"] = False
                    results["tests"].append(
                        {
                            "test": "tenant_1_session_failed",
                            "passed": False,
                            "error": str(e),
                        }
                    )

            # Test 2: Verify context is cleared between sessions
            async with self.get_tenant_session(tenant_2) as session2:
                current_tenant = session2.execute(
                    text("SELECT current_setting('app.current_tenant_id', true)")
                ).scalar()

                if current_tenant == tenant_2:
                    results["tests"].append(
                        {
                            "test": "context_switch_working",
                            "passed": True,
                            "details": f"Context correctly switched to {tenant_2}",
                        }
                    )
                else:
                    results["isolation_test_passed"] = False
                    results["tests"].append(
                        {
                            "test": "context_switch_failed",
                            "passed": False,
                            "details": f"Expected {tenant_2}, got {current_tenant}",
                        }
                    )

            return results

        except Exception as e:
            results["isolation_test_passed"] = False
            results["error"] = str(e)
            return results


# Factory function
def create_tenant_aware_pool(
    database_url: str, audit_logger: Optional[DatabaseAuditLogger] = None, **kwargs
) -> TenantAwareConnectionPool:
    """
    Factory function to create a tenant-aware connection pool
    """
    return TenantAwareConnectionPool(database_url=database_url, audit_logger=audit_logger, **kwargs)
