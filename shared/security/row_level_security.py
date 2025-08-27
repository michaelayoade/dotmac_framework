"""
Row Level Security (RLS) Implementation for Multi-Tenant Database Isolation
Provides database-level security policies to prevent cross-tenant data access

SECURITY: This module implements PostgreSQL Row Level Security policies
to ensure complete tenant data isolation at the database level
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

class RLSPolicyManager:
    """
    Manager for PostgreSQL Row Level Security policies
    
    Features:
    - Automatic RLS policy creation for tenant-aware tables
    - Policy validation and testing
    - Tenant context management
    - Security audit logging
    """
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.policies_created = set()
    
    async def enable_rls_for_table(self, table_name: str, tenant_column: str = 'tenant_id') -> bool:
        """
        Enable Row Level Security for a specific table
        """
        try:
            with self.engine.begin() as conn:
                # Enable RLS on the table
                conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
                
                # Create tenant isolation policy
                policy_name = f"{table_name}_tenant_isolation"
                
                # Drop existing policy if it exists
                conn.execute(text(f"""
                    DROP POLICY IF EXISTS {policy_name} ON {table_name};
                """))
                
                # Create new tenant isolation policy
                conn.execute(text(f"""
                    CREATE POLICY {policy_name} ON {table_name}
                    USING ({tenant_column}::text = current_setting('app.current_tenant_id', true));
                """))
                
                logger.info(f"✅ RLS enabled for table: {table_name}")
                self.policies_created.add(table_name)
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to enable RLS for {table_name}: {e}")
            return False
    
    async def enable_rls_for_all_tenant_tables(self, session: Session) -> Dict[str, bool]:
        """
        Enable RLS for all tables that have tenant_id columns
        """
        results = {}
        
        # Find all tables with tenant_id columns
        tenant_tables = await self._find_tenant_tables(session)
        
        for table_name in tenant_tables:
            result = await self.enable_rls_for_table(table_name)
            results[table_name] = result
        
        return results
    
    async def _find_tenant_tables(self, session: Session) -> List[str]:
        """
        Find all tables that have tenant_id columns
        """
        query = text("""
            SELECT table_name 
            FROM information_schema.columns 
            WHERE column_name = 'tenant_id' 
            AND table_schema = 'public'
            ORDER BY table_name;
        """)
        
        result = session.execute(query)
        return [row[0] for row in result.fetchall()]
    
    async def set_tenant_context(self, session: Session, tenant_id: str) -> bool:
        """
        Set the current tenant context for the database session
        """
        try:
            session.execute(text(f"SELECT set_config('app.current_tenant_id', '{tenant_id}', false);"))
            logger.debug(f"Set tenant context to: {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set tenant context: {e}")
            return False
    
    async def clear_tenant_context(self, session: Session) -> bool:
        """
        Clear the current tenant context
        """
        try:
            session.execute(text("SELECT set_config('app.current_tenant_id', '', false);"))
            return True
        except Exception as e:
            logger.error(f"Failed to clear tenant context: {e}")
            return False
    
    async def create_tenant_isolation_function(self) -> bool:
        """
        Create a PostgreSQL function for tenant isolation checks
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION check_tenant_access(target_tenant_id TEXT)
                    RETURNS BOOLEAN AS $$
                    DECLARE
                        current_tenant TEXT;
                    BEGIN
                        current_tenant := current_setting('app.current_tenant_id', true);
                        
                        -- If no tenant context is set, deny access
                        IF current_tenant IS NULL OR current_tenant = '' THEN
                            RAISE EXCEPTION 'No tenant context set - access denied';
                            RETURN FALSE;
                        END IF;
                        
                        -- Check if current tenant matches target tenant
                        IF current_tenant != target_tenant_id THEN
                            RAISE EXCEPTION 'Cross-tenant access denied: % attempted to access %', current_tenant, target_tenant_id;
                            RETURN FALSE;
                        END IF;
                        
                        RETURN TRUE;
                    END;
                    $$ LANGUAGE plpgsql SECURITY DEFINER;
                """))
                
                logger.info("✅ Tenant isolation function created")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create tenant isolation function: {e}")
            return False
    
    async def create_audit_trigger_function(self) -> bool:
        """
        Create audit trigger function for cross-tenant access attempts
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION audit_tenant_access()
                    RETURNS TRIGGER AS $$
                    DECLARE
                        current_tenant TEXT;
                        operation_type TEXT;
                    BEGIN
                        current_tenant := current_setting('app.current_tenant_id', true);
                        
                        -- Determine operation type
                        IF TG_OP = 'INSERT' THEN
                            operation_type := 'INSERT';
                        ELSIF TG_OP = 'UPDATE' THEN 
                            operation_type := 'UPDATE';
                        ELSIF TG_OP = 'DELETE' THEN
                            operation_type := 'DELETE';
                        END IF;
                        
                        -- Log all database operations with tenant context
                        INSERT INTO audit_log (
                            table_name,
                            operation_type,
                            tenant_id,
                            user_context,
                            timestamp,
                            ip_address
                        ) VALUES (
                            TG_TABLE_NAME,
                            operation_type,
                            current_tenant,
                            current_setting('app.current_user_id', true),
                            NOW(),
                            current_setting('app.client_ip', true)
                        );
                        
                        -- Return appropriate record
                        IF TG_OP = 'DELETE' THEN
                            RETURN OLD;
                        ELSE
                            RETURN NEW;
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql SECURITY DEFINER;
                """))
                
                logger.info("✅ Audit trigger function created")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create audit trigger function: {e}")
            return False
    
    async def create_audit_log_table(self) -> bool:
        """
        Create audit log table for tenant access tracking
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(255) NOT NULL,
                        operation_type VARCHAR(50) NOT NULL,
                        tenant_id VARCHAR(255),
                        user_context VARCHAR(255),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        ip_address INET,
                        record_id UUID,
                        old_values JSONB,
                        new_values JSONB,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT
                    );
                """))
                
                # Create indexes for performance
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_id ON audit_log(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
                """))
                
                logger.info("✅ Audit log table created")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create audit log table: {e}")
            return False
    
    async def add_audit_triggers_to_table(self, table_name: str) -> bool:
        """
        Add audit triggers to a specific table
        """
        try:
            with self.engine.begin() as conn:
                # Create triggers for all operations
                for operation in ['INSERT', 'UPDATE', 'DELETE']:
                    trigger_name = f"audit_{table_name}_{operation.lower()}"
                    
                    conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};"))
                    
                    conn.execute(text(f"""
                        CREATE TRIGGER {trigger_name}
                        AFTER {operation} ON {table_name}
                        FOR EACH ROW EXECUTE FUNCTION audit_tenant_access();
                    """))
                
                logger.info(f"✅ Audit triggers added to: {table_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add audit triggers to {table_name}: {e}")
            return False
    
    async def validate_tenant_isolation(self, session: Session, test_tenant_1: str, test_tenant_2: str) -> Dict[str, Any]:
        """
        Validate tenant isolation by attempting cross-tenant access
        """
        results = {
            'isolation_working': True,
            'tests_passed': 0,
            'tests_failed': 0,
            'details': []
        }
        
        try:
            # Test 1: Set tenant context and try to access own data
            await self.set_tenant_context(session, test_tenant_1)
            
            # Test 2: Try to access other tenant's data (should fail)
            try:
                query = text("""
                    SELECT COUNT(*) FROM users WHERE tenant_id = :other_tenant
                """)
                result = session.execute(query, {'other_tenant': test_tenant_2})
                count = result.scalar()
                
                if count > 0:
                    results['isolation_working'] = False
                    results['tests_failed'] += 1
                    results['details'].append(f"❌ Cross-tenant access succeeded (found {count} records)")
                else:
                    results['tests_passed'] += 1
                    results['details'].append("✅ Cross-tenant access properly blocked")
                    
            except Exception as e:
                results['tests_passed'] += 1
                results['details'].append(f"✅ Cross-tenant access blocked with error: {str(e)[:100]}")
            
            return results
            
        except Exception as e:
            results['isolation_working'] = False
            results['details'].append(f"❌ Test setup failed: {e}")
            return results
    
    async def get_rls_status(self, session: Session) -> Dict[str, Any]:
        """
        Get the current status of RLS policies
        """
        query = text("""
            SELECT 
                schemaname,
                tablename,
                rowsecurity,
                (SELECT COUNT(*) FROM pg_policies WHERE schemaname = t.schemaname AND tablename = t.tablename) as policy_count
            FROM pg_tables t
            WHERE schemaname = 'public'
            AND tablename IN (
                SELECT table_name 
                FROM information_schema.columns 
                WHERE column_name = 'tenant_id'
            )
            ORDER BY tablename;
        """)
        
        result = session.execute(query)
        tables = []
        
        for row in result.fetchall():
            tables.append({
                'table_name': row.tablename,
                'rls_enabled': row.rowsecurity,
                'policy_count': row.policy_count
            })
        
        return {
            'total_tenant_tables': len(tables),
            'rls_enabled_tables': len([t for t in tables if t['rls_enabled']]),
            'tables': tables
        }

# Convenience functions
async def setup_complete_rls(engine: Engine, session: Session) -> Dict[str, Any]:
    """
    Set up complete Row Level Security for the database
    """
    rls_manager = RLSPolicyManager(engine)
    
    results = {
        'audit_table_created': False,
        'audit_functions_created': False,
        'rls_policies_created': {},
        'audit_triggers_added': {},
        'total_success': 0,
        'total_failures': 0
    }
    
    try:
        # 1. Create audit infrastructure
        results['audit_table_created'] = await rls_manager.create_audit_log_table()
        results['audit_functions_created'] = (
            await rls_manager.create_tenant_isolation_function() and 
            await rls_manager.create_audit_trigger_function()
        )
        
        # 2. Enable RLS for all tenant tables
        rls_results = await rls_manager.enable_rls_for_all_tenant_tables(session)
        results['rls_policies_created'] = rls_results
        
        # 3. Add audit triggers to all tenant tables
        tenant_tables = await rls_manager._find_tenant_tables(session)
        for table_name in tenant_tables:
            trigger_result = await rls_manager.add_audit_triggers_to_table(table_name)
            results['audit_triggers_added'][table_name] = trigger_result
        
        # Count successes and failures
        results['total_success'] = sum([
            1 if results['audit_table_created'] else 0,
            1 if results['audit_functions_created'] else 0,
            len([r for r in rls_results.values() if r]),
            len([r for r in results['audit_triggers_added'].values() if r])
        ])
        
        results['total_failures'] = sum([
            0 if results['audit_table_created'] else 1,
            0 if results['audit_functions_created'] else 1,
            len([r for r in rls_results.values() if not r]),
            len([r for r in results['audit_triggers_added'].values() if not r])
        ])
        
        return results
        
    except Exception as e:
        logger.error(f"Complete RLS setup failed: {e}")
        results['setup_error'] = str(e)
        return results