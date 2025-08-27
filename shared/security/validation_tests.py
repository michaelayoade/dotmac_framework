"""
Comprehensive Multi-Tenant Security Validation Tests
Validates all aspects of tenant isolation and security controls

SECURITY: These tests verify that tenant isolation is working correctly
and no cross-tenant data access is possible
"""

import logging
import asyncio
import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from .row_level_security import RLSPolicyManager
from .database_audit import DatabaseAuditLogger, AuditEventType, AuditSeverity
from .connection_pool import TenantAwareConnectionPool

logger = logging.getLogger(__name__)

class MultiTenantSecurityValidator:
    """
    Comprehensive security validator for multi-tenant systems
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize security components
        self.rls_manager = RLSPolicyManager(self.engine)
        self.audit_logger = DatabaseAuditLogger(self.engine)
        self.connection_pool = TenantAwareConnectionPool(
            database_url=database_url,
            audit_logger=self.audit_logger
        )
        
        self.test_results = []
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run all security validation tests
        """
        print("🔒 COMPREHENSIVE MULTI-TENANT SECURITY VALIDATION")
        print("=" * 60)
        
        results = {
            'validation_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'test_categories': {},
            'overall_status': 'UNKNOWN',
            'recommendations': []
        }
        
        # Test categories
        test_categories = [
            ('Database Schema Validation', self.validate_database_schema),
            ('Row Level Security Tests', self.validate_rls_policies),
            ('Tenant Context Tests', self.validate_tenant_context),
            ('Cross-Tenant Access Tests', self.validate_cross_tenant_prevention),
            ('Audit Logging Tests', self.validate_audit_logging),
            ('Connection Pool Tests', self.validate_connection_pool),
            ('Security Middleware Tests', self.validate_security_middleware)
        ]
        
        for category_name, test_func in test_categories:
            print(f"\n🧪 {category_name}")
            print("-" * 50)
            
            try:
                category_results = await test_func()
                results['test_categories'][category_name] = category_results
                
                # Update counters
                results['total_tests'] += category_results.get('total_tests', 0)
                results['passed_tests'] += category_results.get('passed_tests', 0)
                results['failed_tests'] += category_results.get('failed_tests', 0)
                results['critical_failures'] += category_results.get('critical_failures', 0)
                
                # Print results
                status = "✅ PASS" if category_results.get('all_passed', False) else "❌ FAIL"
                print(f"{status} - {category_results.get('passed_tests', 0)}/{category_results.get('total_tests', 0)} tests passed")
                
            except Exception as e:
                logger.error(f"Test category {category_name} failed: {e}")
                results['test_categories'][category_name] = {
                    'error': str(e),
                    'total_tests': 1,
                    'passed_tests': 0,
                    'failed_tests': 1,
                    'critical_failures': 1
                }
                results['total_tests'] += 1
                results['failed_tests'] += 1
                results['critical_failures'] += 1
        
        # Determine overall status
        if results['critical_failures'] > 0:
            results['overall_status'] = 'CRITICAL_FAILURE'
            results['recommendations'].append("URGENT: Critical security vulnerabilities detected")
        elif results['failed_tests'] > 0:
            results['overall_status'] = 'PARTIAL_FAILURE'
            results['recommendations'].append("Some security tests failed - review and fix")
        else:
            results['overall_status'] = 'SECURE'
            results['recommendations'].append("All security validations passed")
        
        return results
    
    async def validate_database_schema(self) -> Dict[str, Any]:
        """Validate database schema for multi-tenant security"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            with self.engine.begin() as conn:
                # Test 1: Check for tenant_id columns
                tenant_tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.columns 
                    WHERE column_name = 'tenant_id' 
                    AND table_schema = 'public'
                """)).fetchall()
                
                results['total_tests'] += 1
                if len(tenant_tables) > 0:
                    results['passed_tests'] += 1
                    results['tests'].append({
                        'test': 'tenant_id_columns_exist',
                        'status': 'PASS',
                        'details': f'Found {len(tenant_tables)} tables with tenant_id'
                    })
                    print(f"✅ Found {len(tenant_tables)} tables with tenant_id columns")
                else:
                    results['failed_tests'] += 1
                    results['critical_failures'] += 1
                    results['tests'].append({
                        'test': 'tenant_id_columns_exist',
                        'status': 'CRITICAL_FAIL',
                        'details': 'No tables with tenant_id found'
                    })
                    print("❌ No tables with tenant_id columns found")
                
                # Test 2: Check for audit log table
                audit_table_exists = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'database_audit_log'
                    );
                """)).scalar()
                
                results['total_tests'] += 1
                if audit_table_exists:
                    results['passed_tests'] += 1
                    results['tests'].append({
                        'test': 'audit_table_exists',
                        'status': 'PASS',
                        'details': 'Audit log table found'
                    })
                    print("✅ Database audit log table exists")
                else:
                    results['failed_tests'] += 1
                    results['tests'].append({
                        'test': 'audit_table_exists',
                        'status': 'FAIL',
                        'details': 'Audit log table missing'
                    })
                    print("⚠️  Database audit log table missing")
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['critical_failures'] += 1
            results['tests'].append({
                'test': 'schema_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results
    
    async def validate_rls_policies(self) -> Dict[str, Any]:
        """Validate Row Level Security policies"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            session = self.SessionLocal()
            
            # Test RLS status
            rls_status = await self.rls_manager.get_rls_status(session)
            
            results['total_tests'] += 1
            if rls_status.get('rls_enabled_tables', 0) > 0:
                results['passed_tests'] += 1
                results['tests'].append({
                    'test': 'rls_policies_active',
                    'status': 'PASS',
                    'details': f"RLS enabled on {rls_status.get('rls_enabled_tables')} tables"
                })
                print(f"✅ RLS enabled on {rls_status.get('rls_enabled_tables')} tables")
            else:
                results['failed_tests'] += 1
                results['critical_failures'] += 1
                results['tests'].append({
                    'test': 'rls_policies_active',
                    'status': 'CRITICAL_FAIL',
                    'details': 'No RLS policies active'
                })
                print("❌ No RLS policies are active")
            
            session.close()
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['tests'].append({
                'test': 'rls_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results
    
    async def validate_tenant_context(self) -> Dict[str, Any]:
        """Validate tenant context management"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            test_tenant = "test-tenant-validation-001"
            
            # Test connection pool tenant context
            async with self.connection_pool.get_tenant_session(test_tenant) as session:
                # Check if tenant context is set
                current_tenant = session.execute(text(
                    "SELECT current_setting('app.current_tenant_id', true)"
                )).scalar()
                
                results['total_tests'] += 1
                if current_tenant == test_tenant:
                    results['passed_tests'] += 1
                    results['tests'].append({
                        'test': 'tenant_context_setting',
                        'status': 'PASS',
                        'details': f'Tenant context correctly set to {test_tenant}'
                    })
                    print(f"✅ Tenant context correctly set: {test_tenant}")
                else:
                    results['failed_tests'] += 1
                    results['critical_failures'] += 1
                    results['tests'].append({
                        'test': 'tenant_context_setting',
                        'status': 'CRITICAL_FAIL',
                        'details': f'Expected {test_tenant}, got {current_tenant}'
                    })
                    print(f"❌ Tenant context mismatch: expected {test_tenant}, got {current_tenant}")
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['tests'].append({
                'test': 'tenant_context_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results
    
    async def validate_cross_tenant_prevention(self) -> Dict[str, Any]:
        """Validate cross-tenant access prevention"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            tenant_1 = "validation-tenant-001"
            tenant_2 = "validation-tenant-002"
            
            # Test cross-tenant prevention
            isolation_results = await self.connection_pool.validate_tenant_isolation(tenant_1, tenant_2)
            
            results['total_tests'] += 1
            if isolation_results.get('isolation_test_passed', False):
                results['passed_tests'] += 1
                results['tests'].append({
                    'test': 'cross_tenant_prevention',
                    'status': 'PASS',
                    'details': 'Cross-tenant access properly blocked'
                })
                print("✅ Cross-tenant access prevention working")
            else:
                results['failed_tests'] += 1
                results['critical_failures'] += 1
                results['tests'].append({
                    'test': 'cross_tenant_prevention',
                    'status': 'CRITICAL_FAIL',
                    'details': 'Cross-tenant access not blocked'
                })
                print("❌ CRITICAL: Cross-tenant access not blocked")
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['tests'].append({
                'test': 'cross_tenant_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results
    
    async def validate_audit_logging(self) -> Dict[str, Any]:
        """Validate audit logging functionality"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            # Test audit logging
            test_logged = await self.audit_logger.log_event(
                event_type=AuditEventType.SECURITY_EVENT,
                severity=AuditSeverity.INFO,
                tenant_id="test-audit-tenant",
                event_title="Security validation test",
                event_description="Testing audit logging functionality"
            )
            
            results['total_tests'] += 1
            if test_logged:
                results['passed_tests'] += 1
                results['tests'].append({
                    'test': 'audit_logging',
                    'status': 'PASS',
                    'details': 'Audit event successfully logged'
                })
                print("✅ Audit logging working correctly")
            else:
                results['failed_tests'] += 1
                results['tests'].append({
                    'test': 'audit_logging',
                    'status': 'FAIL',
                    'details': 'Audit event logging failed'
                })
                print("❌ Audit logging failed")
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['tests'].append({
                'test': 'audit_logging_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results
    
    async def validate_connection_pool(self) -> Dict[str, Any]:
        """Validate connection pool security"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            # Test connection pool stats
            stats = await self.connection_pool.get_connection_stats()
            
            results['total_tests'] += 1
            if stats.get('pool_size', 0) > 0:
                results['passed_tests'] += 1
                results['tests'].append({
                    'test': 'connection_pool_active',
                    'status': 'PASS',
                    'details': f"Pool size: {stats.get('pool_size')}"
                })
                print(f"✅ Connection pool active - size: {stats.get('pool_size')}")
            else:
                results['failed_tests'] += 1
                results['tests'].append({
                    'test': 'connection_pool_active',
                    'status': 'FAIL',
                    'details': 'Connection pool not properly configured'
                })
                print("❌ Connection pool not properly configured")
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['tests'].append({
                'test': 'connection_pool_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results
    
    async def validate_security_middleware(self) -> Dict[str, Any]:
        """Validate security middleware components"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'critical_failures': 0,
            'tests': []
        }
        
        try:
            # Test middleware imports
            from .tenant_middleware import TenantIsolationMiddleware
            from .csrf_protection import CSRFProtection
            from .input_sanitizer import SecuritySanitizer
            
            results['total_tests'] += 1
            results['passed_tests'] += 1
            results['tests'].append({
                'test': 'security_middleware_available',
                'status': 'PASS',
                'details': 'All security middleware components available'
            })
            print("✅ Security middleware components available")
            
            # Test input sanitization
            dangerous_input = "<script>alert('xss')</script>"
            sanitized = SecuritySanitizer.sanitize_string(dangerous_input)
            
            results['total_tests'] += 1
            if dangerous_input != sanitized and not SecuritySanitizer.is_safe_input(dangerous_input):
                results['passed_tests'] += 1
                results['tests'].append({
                    'test': 'input_sanitization',
                    'status': 'PASS',
                    'details': 'Input sanitization working correctly'
                })
                print("✅ Input sanitization working correctly")
            else:
                results['failed_tests'] += 1
                results['critical_failures'] += 1
                results['tests'].append({
                    'test': 'input_sanitization',
                    'status': 'CRITICAL_FAIL',
                    'details': 'Input sanitization not working'
                })
                print("❌ CRITICAL: Input sanitization not working")
        
        except Exception as e:
            results['total_tests'] += 1
            results['failed_tests'] += 1
            results['tests'].append({
                'test': 'middleware_validation',
                'status': 'ERROR',
                'details': str(e)
            })
        
        results['all_passed'] = results['failed_tests'] == 0
        return results

async def run_validation_suite(database_url: str = "sqlite:///security_validation.db") -> Dict[str, Any]:
    """
    Run the complete multi-tenant security validation suite
    """
    validator = MultiTenantSecurityValidator(database_url)
    results = await validator.run_comprehensive_validation()
    
    print("\n" + "=" * 60)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Overall Status: {results['overall_status']}")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Critical Failures: {results['critical_failures']}")
    
    if results['recommendations']:
        print("\n🔍 Recommendations:")
        for rec in results['recommendations']:
            print(f"  • {rec}")
    
    return results

# Standalone test runner
if __name__ == "__main__":
    import asyncio
    
    async def main():
        results = await run_validation_suite()
        
        # Exit with appropriate code
        if results['overall_status'] == 'SECURE':
            exit(0)
        elif results['overall_status'] == 'PARTIAL_FAILURE':
            exit(1)
        else:  # CRITICAL_FAILURE
            exit(2)
    
    asyncio.run(main())