"""Row Level Security (RLS) implementation for PostgreSQL multi-tenant isolation.

This module provides comprehensive RLS policies for ensuring tenant data isolation
at the database level, preventing unauthorized cross-tenant data access.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from sqlalchemy import text, event
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from contextlib import contextmanager

from dotmac_isp.core.database import engine, async_engine
from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)


class RLSPolicyManager:
    """Manages Row Level Security policies for multi-tenant isolation."""

    def __init__(self):
        """  Init   operation."""
        self.settings = get_settings()
        self.policies_created = set()

    def create_tenant_isolation_policies(self) -> None:
        """Create RLS policies for all tenant-aware tables."""

        # Define tables that need tenant isolation
        tenant_tables = [
            "users",
            "customers",
            "roles",
            "auth_tokens",
            "login_attempts",
            "services",
            "invoices",
            "tickets",
            "network_devices",
            "service_instances",
            "billing_accounts",
            "support_tickets",
            "analytics_events",
            "inventory_items",
            "field_operations",
            "compliance_records",
            "notifications",
            "projects",
        ]

        with engine.connect() as conn:
            with conn.begin():
                # Enable RLS for each tenant table
                for table in tenant_tables:
                    try:
                        self._create_table_rls_policy(conn, table)
                        logger.info(f"✅ RLS policy created for table: {table}")
                    except Exception as e:
                        logger.warning(
                            f"⚠️  Failed to create RLS policy for {table}: {e}"
                        )
                        # Continue with other tables

                # Create security functions
                self._create_security_functions(conn)

                # Create audit trigger functions
                self._create_audit_functions(conn)

        logger.info("🔒 RLS policies initialization complete")

    def _create_table_rls_policy(self, conn, table_name: str) -> None:
        """Create RLS policy for a specific table."""

        # Enable RLS on the table
        conn.execute(
            text(
                f"""
            ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
        """
            )
        )

        # Drop existing policies if they exist
        policy_name = f"{table_name}_tenant_policy"
        try:
            conn.execute(
                text(
                    f"""
                DROP POLICY IF EXISTS {policy_name} ON {table_name};
            """
                )
            )
        except:
            pass  # Policy might not exist

        # Create tenant isolation policy
        conn.execute(
            text(
                f"""
            CREATE POLICY {policy_name} ON {table_name}
                FOR ALL
                TO PUBLIC
                USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
                WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
        """
            )
        )

        # Create super admin bypass policy
        superadmin_policy = f"{table_name}_superadmin_policy"
        try:
            conn.execute(
                text(
                    f"""
                DROP POLICY IF EXISTS {superadmin_policy} ON {table_name};
            """
                )
            )
        except:
            pass

        conn.execute(
            text(
                f"""
            CREATE POLICY {superadmin_policy} ON {table_name}
                FOR ALL
                TO PUBLIC
                USING (
                    current_setting('app.user_role', true) = 'super_admin' OR
                    current_setting('app.bypass_rls', true)::boolean = true
                );
        """
            )
        )

        self.policies_created.add(table_name)

    def _create_security_functions(self, conn) -> None:
        """Create security helper functions."""

        # Function to set current tenant
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION set_current_tenant(tenant_uuid uuid)
            RETURNS void AS $$
            BEGIN
                PERFORM set_config('app.current_tenant_id', tenant_uuid::text, false);
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
            )
        )

        # Function to set current user role
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION set_current_user_role(role_name text)
            RETURNS void AS $$
            BEGIN
                PERFORM set_config('app.user_role', role_name, false);
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
            )
        )

        # Function to bypass RLS (for admin operations)
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION set_rls_bypass(bypass_enabled boolean)
            RETURNS void AS $$
            BEGIN
                PERFORM set_config('app.bypass_rls', bypass_enabled::text, false);
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
            )
        )

        # Function to get current tenant context
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION get_current_tenant()
            RETURNS uuid AS $$
            BEGIN
                RETURN current_setting('app.current_tenant_id', true)::uuid;
            EXCEPTION
                WHEN OTHERS THEN
                    RETURN NULL;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
            )
        )

        # Tenant validation function
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION validate_tenant_access(target_tenant_id uuid)
            RETURNS boolean AS $$
            DECLARE
                current_tenant uuid;
                user_role text;
            BEGIN
                current_tenant := current_setting('app.current_tenant_id', true)::uuid;
                user_role := current_setting('app.user_role', true);
                
                -- Super admins can access any tenant
                IF user_role = 'super_admin' THEN
                    RETURN true;
                END IF;
                
                -- Check if current tenant matches target tenant
                RETURN current_tenant = target_tenant_id;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
            )
        )

        logger.info("🔒 Security functions created")

    def _create_audit_functions(self, conn) -> None:
        """Create audit trail trigger functions."""

        # Create audit log table
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS audit_log (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                table_name text NOT NULL,
                record_id uuid NOT NULL,
                tenant_id uuid NOT NULL,
                operation text NOT NULL, -- INSERT, UPDATE, DELETE
                old_values jsonb,
                new_values jsonb,
                changed_fields text[],
                user_id uuid,
                user_role text,
                session_id text,
                ip_address inet,
                user_agent text,
                timestamp timestamptz DEFAULT NOW(),
                CONSTRAINT audit_log_operation_check CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')
            );
        """
            )
        )

        # Create indexes for audit log
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
            CREATE INDEX IF NOT EXISTS idx_audit_log_record_id ON audit_log(record_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_id ON audit_log(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
        """
            )
        )

        # Generic audit trigger function
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION audit_trigger_function()
            RETURNS trigger AS $$
            DECLARE
                old_values jsonb;
                new_values jsonb;
                changed_fields text[] := ARRAY[]::text[];
                current_user_id uuid;
                current_user_role text;
                current_session_id text;
                current_ip inet;
                current_user_agent text;
            BEGIN
                -- Get current session context
                BEGIN
                    current_user_id := current_setting('app.current_user_id', true)::uuid;
                    current_user_role := current_setting('app.user_role', true);
                    current_session_id := current_setting('app.session_id', true);
                    current_ip := current_setting('app.client_ip', true)::inet;
                    current_user_agent := current_setting('app.user_agent', true);
                EXCEPTION
                    WHEN OTHERS THEN
                        -- Handle missing session context gracefully
                        current_user_id := NULL;
                        current_user_role := 'system';
                        current_session_id := NULL;
                        current_ip := NULL;
                        current_user_agent := NULL;
                END;
                
                -- Handle different operations
                IF TG_OP = 'DELETE' THEN
                    old_values := to_jsonb(OLD);
                    new_values := NULL;
                    
                    INSERT INTO audit_log (
                        table_name, record_id, tenant_id, operation, 
                        old_values, new_values, changed_fields,
                        user_id, user_role, session_id, ip_address, user_agent
                    ) VALUES (
                        TG_TABLE_NAME, OLD.id, OLD.tenant_id, TG_OP,
                        old_values, new_values, changed_fields,
                        current_user_id, current_user_role, current_session_id, 
                        current_ip, current_user_agent
                    );
                    
                    RETURN OLD;
                    
                ELSIF TG_OP = 'UPDATE' THEN
                    old_values := to_jsonb(OLD);
                    new_values := to_jsonb(NEW);
                    
                    -- Detect changed fields
                    SELECT array_agg(key) INTO changed_fields
                    FROM jsonb_each(old_values) old_val
                    WHERE old_val.value IS DISTINCT FROM (new_values->old_val.key);
                    
                    -- Only log if there are actual changes
                    IF array_length(changed_fields, 1) > 0 THEN
                        INSERT INTO audit_log (
                            table_name, record_id, tenant_id, operation,
                            old_values, new_values, changed_fields,
                            user_id, user_role, session_id, ip_address, user_agent
                        ) VALUES (
                            TG_TABLE_NAME, NEW.id, NEW.tenant_id, TG_OP,
                            old_values, new_values, changed_fields,
                            current_user_id, current_user_role, current_session_id,
                            current_ip, current_user_agent
                        );
                    END IF;
                    
                    RETURN NEW;
                    
                ELSIF TG_OP = 'INSERT' THEN
                    old_values := NULL;
                    new_values := to_jsonb(NEW);
                    
                    INSERT INTO audit_log (
                        table_name, record_id, tenant_id, operation,
                        old_values, new_values, changed_fields,
                        user_id, user_role, session_id, ip_address, user_agent
                    ) VALUES (
                        TG_TABLE_NAME, NEW.id, NEW.tenant_id, TG_OP,
                        old_values, new_values, changed_fields,
                        current_user_id, current_user_role, current_session_id,
                        current_ip, current_user_agent
                    );
                    
                    RETURN NEW;
                END IF;
                
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
            )
        )

        logger.info("🔒 Audit functions created")

    def enable_audit_for_table(self, table_name: str) -> None:
        """Enable audit trail for a specific table."""
        with engine.connect() as conn:
            with conn.begin():
                # Drop existing trigger if it exists
                trigger_name = f"audit_trigger_{table_name}"
                try:
                    conn.execute(
                        text(
                            f"""
                        DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};
                    """
                        )
                    )
                except:
                    pass

                # Create audit trigger
                conn.execute(
                    text(
                        f"""
                    CREATE TRIGGER {trigger_name}
                        AFTER INSERT OR UPDATE OR DELETE ON {table_name}
                        FOR EACH ROW
                        EXECUTE FUNCTION audit_trigger_function();
                """
                    )
                )

                logger.info(f"✅ Audit trigger enabled for table: {table_name}")

    def disable_rls_for_maintenance(self) -> None:
        """Temporarily disable RLS for maintenance operations."""
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SELECT set_rls_bypass(true);"))
        logger.warning("⚠️  RLS bypassed for maintenance - ensure to re-enable!")

    def enable_rls_after_maintenance(self) -> None:
        """Re-enable RLS after maintenance operations."""
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SELECT set_rls_bypass(false);"))
        logger.info("🔒 RLS re-enabled after maintenance")


class TenantContext:
    """Context manager for setting tenant isolation in database sessions."""

    def __init__(
        self,
        tenant_id: str,
        user_id: str = None,
        user_role: str = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.user_role = user_role or "user"
        self.session_id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent

    def __enter__(self):
        """Set tenant context in database session."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear tenant context."""
        pass

    def apply_to_session(self, session: Session) -> None:
        """Apply tenant context to a SQLAlchemy session."""
        # Set tenant context
        session.execute(
            text("SELECT set_current_tenant(:tenant_id)"), {"tenant_id": self.tenant_id}
        )

        if self.user_role:
            session.execute(
                text("SELECT set_current_user_role(:role)"), {"role": self.user_role}
            )

        # Set audit context
        if self.user_id:
            session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, false)"),
                {"user_id": self.user_id},
            )

        if self.session_id:
            session.execute(
                text("SELECT set_config('app.session_id', :session_id, false)"),
                {"session_id": self.session_id},
            )

        if self.ip_address:
            session.execute(
                text("SELECT set_config('app.client_ip', :ip, false)"),
                {"ip": self.ip_address},
            )

        if self.user_agent:
            session.execute(
                text("SELECT set_config('app.user_agent', :ua, false)"),
                {"ua": self.user_agent},
            )


@contextmanager
def tenant_context(
    tenant_id: str,
    user_id: str = None,
    user_role: str = None,
    session_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
):
    """Context manager for tenant-aware database operations."""
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    with context:
        yield context


def setup_session_rls(
    session: Session,
    tenant_id: str,
    user_id: str = None,
    user_role: str = None,
    **audit_context,
) -> None:
    """Helper function to setup RLS context for a session."""
    context = TenantContext(
        tenant_id=tenant_id, user_id=user_id, user_role=user_role, **audit_context
    )
    context.apply_to_session(session)


# Global RLS manager instance
rls_manager = RLSPolicyManager()


# Event listeners for automatic RLS setup
@event.listens_for(Engine, "connect")
def set_postgresql_settings(dbapi_connection, connection_record):
    """Set PostgreSQL session settings on connection."""
    try:
        with dbapi_connection.cursor() as cursor:
            # Set default tenant context (will be overridden per request)
            cursor.execute("SET app.current_tenant_id = ''")
            cursor.execute("SET app.user_role = 'user'")
            cursor.execute("SET app.bypass_rls = false")

            # Performance settings
            cursor.execute("SET work_mem = '64MB'")
            cursor.execute("SET random_page_cost = 1.1")
            cursor.execute("SET effective_cache_size = '1GB'")

        dbapi_connection.commit()
    except Exception as e:
        logger.warning(f"Failed to set PostgreSQL session settings: {e}")


def initialize_rls() -> None:
    """Initialize RLS policies for the application."""
    try:
        rls_manager.create_tenant_isolation_policies()

        # Enable audit for critical tables
        critical_tables = [
            "users",
            "customers",
            "auth_tokens",
            "billing_accounts",
            "invoices",
            "services",
            "compliance_records",
        ]

        for table in critical_tables:
            try:
                rls_manager.enable_audit_for_table(table)
            except Exception as e:
                logger.warning(f"Failed to enable audit for {table}: {e}")

        logger.info("🔒 RLS initialization complete")

    except Exception as e:
        logger.error(f"❌ RLS initialization failed: {e}")
        raise


def cleanup_audit_logs(days_to_keep: int = 90) -> int:
    """Clean up old audit logs for compliance retention."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            DELETE FROM audit_log 
            WHERE timestamp < NOW() - INTERVAL '%s days'
            RETURNING id
        """
            ),
            (days_to_keep,),
        )

        deleted_count = len(result.fetchall())
        conn.commit()

        logger.info(
            f"🧹 Cleaned up {deleted_count} audit log entries older than {days_to_keep} days"
        )
        return deleted_count
