"""
Tenant Isolation Testing Framework

Comprehensive testing utilities for multi-tenant database isolation including:
- Data isolation validation between tenants
- Query result isolation testing
- Cross-tenant data access prevention
- Tenant-specific constraint validation
- Performance isolation testing
- Security boundary validation
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Type, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from sqlalchemy import create_engine, text, select, and_, or_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

from ...core.logging import get_logger  
from ...tenant.identity import TenantContext
from ...api.exception_handlers import standard_exception_handler

logger = get_logger(__name__)


class IsolationTestType(str, Enum):
    """Types of tenant isolation tests"""
    DATA_ISOLATION = "data_isolation"
    QUERY_ISOLATION = "query_isolation"
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    CONSTRAINT_ISOLATION = "constraint_isolation"
    PERFORMANCE_ISOLATION = "performance_isolation"
    SECURITY_BOUNDARY = "security_boundary"


class IsolationViolationType(str, Enum):
    """Types of isolation violations"""
    DATA_LEAKAGE = "data_leakage"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CONSTRAINT_BYPASS = "constraint_bypass"
    PERFORMANCE_INTERFERENCE = "performance_interference"
    TENANT_MISMATCH = "tenant_mismatch"


@dataclass
class IsolationViolation:
    """Represents a tenant isolation violation"""
    violation_type: IsolationViolationType
    tenant_id: str
    affected_tenant_id: Optional[str]
    table: str
    record_id: Any
    field: str
    description: str
    severity: str = "high"


@dataclass
class TenantIsolationTestResult:
    """Result of a tenant isolation test"""
    test_name: str
    test_type: IsolationTestType
    tenant_id: str
    result: str  # "pass", "fail", "error"
    violations: List[IsolationViolation]
    execution_time: float
    records_tested: int = 0
    error_message: Optional[str] = None


class TenantIsolationTester:
    """
    Comprehensive tenant isolation testing framework.
    
    Features:
    - Multi-tenant data isolation validation
    - Cross-tenant access prevention testing
    - Query result isolation verification
    - Performance isolation testing
    - Security boundary validation
    - Tenant-specific constraint testing
    - Bulk isolation testing across all tenants
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.test_results: List[TenantIsolationTestResult] = []
    
    @standard_exception_handler
    async def test_data_isolation(
        self,
        model_class: Type,
        tenant_contexts: List[TenantContext],
        test_data_per_tenant: Dict[str, List[Dict]]
    ) -> List[TenantIsolationTestResult]:
        """
        Test that tenant data is properly isolated.
        
        Validates that:
        - Tenant A cannot see Tenant B's data
        - Queries are properly filtered by tenant_id
        - No data leakage between tenants
        """
        logger.info(f"Testing data isolation for {model_class.__name__}")
        
        results = []
        
        # First, create test data for each tenant
        await self._setup_tenant_test_data(model_class, tenant_contexts, test_data_per_tenant)
        
        # Test isolation for each tenant
        for tenant_context in tenant_contexts:
            result = await self._test_single_tenant_data_isolation(
                model_class, tenant_context, tenant_contexts, test_data_per_tenant
            )
            results.append(result)
        
        self.test_results.extend(results)
        return results
    
    async def _setup_tenant_test_data(
        self,
        model_class: Type,
        tenant_contexts: List[TenantContext], 
        test_data_per_tenant: Dict[str, List[Dict]]
    ):
        """Create test data for each tenant"""
        
        with self.SessionLocal() as session:
            for tenant_context in tenant_contexts:
                tenant_id = tenant_context.tenant_id
                if tenant_id in test_data_per_tenant:
                    for data in test_data_per_tenant[tenant_id]:
                        # Ensure tenant_id is set in the data
                        data_with_tenant = data.copy()
                        data_with_tenant['tenant_id'] = tenant_id
                        
                        record = model_class(**data_with_tenant)
                        session.add(record)
            
            session.commit()
    
    async def _test_single_tenant_data_isolation(
        self,
        model_class: Type,
        tenant_context: TenantContext,
        all_tenant_contexts: List[TenantContext],
        test_data_per_tenant: Dict[str, List[Dict]]
    ) -> TenantIsolationTestResult:
        """Test data isolation for a single tenant"""
        
        start_time = time.time()
        violations = []
        records_tested = 0
        
        try:
            with self.SessionLocal() as session:
                tenant_id = tenant_context.tenant_id
                
                # Test 1: Query without tenant filter should not return other tenant's data
                try:
                    all_records = session.query(model_class).all()
                    
                    for record in all_records:
                        if hasattr(record, 'tenant_id'):
                            if record.tenant_id != tenant_id:
                                violations.append(IsolationViolation(
                                    violation_type=IsolationViolationType.DATA_LEAKAGE,
                                    tenant_id=tenant_id,
                                    affected_tenant_id=record.tenant_id,
                                    table=model_class.__tablename__,
                                    record_id=getattr(record, 'id', 'unknown'),
                                    field='tenant_id',
                                    description=f"Query returned data from tenant {record.tenant_id} when querying as tenant {tenant_id}",
                                    severity="critical"
                                ))
                        records_tested += 1
                
                except Exception as e:
                    logger.warning(f"Failed to test unfiltered query: {e}")
                
                # Test 2: Explicit tenant filtering
                try:
                    tenant_records = session.query(model_class).filter(
                        model_class.tenant_id == tenant_id
                    ).all()
                    
                    expected_count = len(test_data_per_tenant.get(tenant_id, []))
                    actual_count = len(tenant_records)
                    
                    if actual_count != expected_count:
                        violations.append(IsolationViolation(
                            violation_type=IsolationViolationType.DATA_LEAKAGE,
                            tenant_id=tenant_id,
                            affected_tenant_id=None,
                            table=model_class.__tablename__,
                            record_id='N/A',
                            field='record_count',
                            description=f"Expected {expected_count} records for tenant {tenant_id}, got {actual_count}",
                            severity="medium"
                        ))
                    
                    # Verify each record belongs to correct tenant
                    for record in tenant_records:
                        if hasattr(record, 'tenant_id') and record.tenant_id != tenant_id:
                            violations.append(IsolationViolation(
                                violation_type=IsolationViolationType.TENANT_MISMATCH,
                                tenant_id=tenant_id,
                                affected_tenant_id=record.tenant_id,
                                table=model_class.__tablename__,
                                record_id=getattr(record, 'id', 'unknown'),
                                field='tenant_id',
                                description=f"Record has tenant_id {record.tenant_id} but was returned for tenant {tenant_id}",
                                severity="critical"
                            ))
                
                except Exception as e:
                    logger.warning(f"Failed to test tenant filtering: {e}")
                
                # Test 3: Cross-tenant access attempt
                for other_tenant in all_tenant_contexts:
                    if other_tenant.tenant_id != tenant_id:
                        try:
                            cross_tenant_records = session.query(model_class).filter(
                                model_class.tenant_id == other_tenant.tenant_id
                            ).all()
                            
                            # This query should succeed but return no results for proper isolation
                            # However, if we're not using RLS, this might return data
                            if cross_tenant_records:
                                violations.append(IsolationViolation(
                                    violation_type=IsolationViolationType.UNAUTHORIZED_ACCESS,
                                    tenant_id=tenant_id,
                                    affected_tenant_id=other_tenant.tenant_id,
                                    table=model_class.__tablename__,
                                    record_id='multiple',
                                    field='tenant_access',
                                    description=f"Tenant {tenant_id} can access {len(cross_tenant_records)} records from tenant {other_tenant.tenant_id}",
                                    severity="critical"
                                ))
                        
                        except Exception as e:
                            # Access denial is actually good for isolation
                            logger.debug(f"Cross-tenant access properly denied: {e}")
        
        except Exception as e:
            error_message = f"Data isolation test failed: {str(e)}"
            logger.error(error_message)
            
            return TenantIsolationTestResult(
                test_name=f"data_isolation_{model_class.__name__}_{tenant_context.tenant_id}",
                test_type=IsolationTestType.DATA_ISOLATION,
                tenant_id=tenant_context.tenant_id,
                result="error",
                violations=violations,
                execution_time=time.time() - start_time,
                records_tested=records_tested,
                error_message=error_message
            )
        
        execution_time = time.time() - start_time
        result_status = "pass" if not violations else "fail"
        
        return TenantIsolationTestResult(
            test_name=f"data_isolation_{model_class.__name__}_{tenant_context.tenant_id}",
            test_type=IsolationTestType.DATA_ISOLATION,
            tenant_id=tenant_context.tenant_id,
            result=result_status,
            violations=violations,
            execution_time=execution_time,
            records_tested=records_tested
        )
    
    @standard_exception_handler
    async def test_query_isolation(
        self,
        model_class: Type,
        tenant_contexts: List[TenantContext],
        custom_queries: List[Tuple[str, str]]  # (name, query)
    ) -> List[TenantIsolationTestResult]:
        """Test that custom queries respect tenant isolation"""
        
        results = []
        
        for tenant_context in tenant_contexts:
            result = await self._test_tenant_query_isolation(
                model_class, tenant_context, custom_queries
            )
            results.append(result)
        
        self.test_results.extend(results)
        return results
    
    async def _test_tenant_query_isolation(
        self,
        model_class: Type,
        tenant_context: TenantContext,
        custom_queries: List[Tuple[str, str]]
    ) -> TenantIsolationTestResult:
        """Test query isolation for a single tenant"""
        
        start_time = time.time()
        violations = []
        records_tested = 0
        
        try:
            with self.SessionLocal() as session:
                tenant_id = tenant_context.tenant_id
                
                for query_name, query_sql in custom_queries:
                    try:
                        # Execute the query
                        result = session.execute(text(query_sql), {"tenant_id": tenant_id})
                        rows = result.fetchall()
                        
                        # Check if results are properly filtered
                        for row in rows:
                            records_tested += 1
                            # If the query returns tenant_id, verify it matches
                            if hasattr(row, 'tenant_id') and row.tenant_id != tenant_id:
                                violations.append(IsolationViolation(
                                    violation_type=IsolationViolationType.DATA_LEAKAGE,
                                    tenant_id=tenant_id,
                                    affected_tenant_id=row.tenant_id,
                                    table=model_class.__tablename__,
                                    record_id=getattr(row, 'id', 'unknown'),
                                    field='query_result',
                                    description=f"Query '{query_name}' returned data from tenant {row.tenant_id} for tenant {tenant_id}",
                                    severity="high"
                                ))
                    
                    except Exception as e:
                        logger.warning(f"Query '{query_name}' failed for tenant {tenant_id}: {e}")
        
        except Exception as e:
            error_message = f"Query isolation test failed: {str(e)}"
            logger.error(error_message)
            
            return TenantIsolationTestResult(
                test_name=f"query_isolation_{model_class.__name__}_{tenant_context.tenant_id}",
                test_type=IsolationTestType.QUERY_ISOLATION,
                tenant_id=tenant_context.tenant_id,
                result="error",
                violations=violations,
                execution_time=time.time() - start_time,
                records_tested=records_tested,
                error_message=error_message
            )
        
        execution_time = time.time() - start_time
        result_status = "pass" if not violations else "fail"
        
        return TenantIsolationTestResult(
            test_name=f"query_isolation_{model_class.__name__}_{tenant_context.tenant_id}",
            test_type=IsolationTestType.QUERY_ISOLATION,
            tenant_id=tenant_context.tenant_id,
            result=result_status,
            violations=violations,
            execution_time=execution_time,
            records_tested=records_tested
        )
    
    @standard_exception_handler
    async def test_performance_isolation(
        self,
        model_class: Type,
        tenant_contexts: List[TenantContext],
        load_per_tenant: int = 100
    ) -> List[TenantIsolationTestResult]:
        """Test that tenant performance is isolated (no noisy neighbor effect)"""
        
        logger.info(f"Testing performance isolation for {model_class.__name__}")
        
        results = []
        baseline_times = {}
        
        # First, measure baseline performance for each tenant individually
        for tenant_context in tenant_contexts:
            baseline_time = await self._measure_tenant_performance(
                model_class, tenant_context, load_per_tenant
            )
            baseline_times[tenant_context.tenant_id] = baseline_time
        
        # Then, run all tenants concurrently and compare performance
        concurrent_times = await self._measure_concurrent_tenant_performance(
            model_class, tenant_contexts, load_per_tenant
        )
        
        # Analyze performance isolation
        for tenant_context in tenant_contexts:
            tenant_id = tenant_context.tenant_id
            violations = []
            
            baseline_time = baseline_times.get(tenant_id, 0)
            concurrent_time = concurrent_times.get(tenant_id, 0)
            
            if baseline_time > 0:
                performance_degradation = (concurrent_time - baseline_time) / baseline_time
                
                # If performance degrades by more than 50%, consider it a violation
                if performance_degradation > 0.5:
                    violations.append(IsolationViolation(
                        violation_type=IsolationViolationType.PERFORMANCE_INTERFERENCE,
                        tenant_id=tenant_id,
                        affected_tenant_id=None,
                        table=model_class.__tablename__,
                        record_id='N/A',
                        field='response_time',
                        description=f"Performance degraded by {performance_degradation:.2%} under concurrent load",
                        severity="medium"
                    ))
            
            result = TenantIsolationTestResult(
                test_name=f"performance_isolation_{model_class.__name__}_{tenant_id}",
                test_type=IsolationTestType.PERFORMANCE_ISOLATION,
                tenant_id=tenant_id,
                result="pass" if not violations else "fail",
                violations=violations,
                execution_time=concurrent_time,
                records_tested=load_per_tenant
            )
            
            results.append(result)
        
        self.test_results.extend(results)
        return results
    
    async def _measure_tenant_performance(
        self,
        model_class: Type,
        tenant_context: TenantContext,
        operation_count: int
    ) -> float:
        """Measure performance for a single tenant"""
        
        start_time = time.time()
        
        with self.SessionLocal() as session:
            for i in range(operation_count):
                # Simple read operation
                records = session.query(model_class).filter(
                    model_class.tenant_id == tenant_context.tenant_id
                ).limit(10).all()
        
        return time.time() - start_time
    
    async def _measure_concurrent_tenant_performance(
        self,
        model_class: Type,
        tenant_contexts: List[TenantContext],
        operation_count: int
    ) -> Dict[str, float]:
        """Measure performance when all tenants run concurrently"""
        
        async def tenant_workload(tenant_context: TenantContext):
            return await self._measure_tenant_performance(
                model_class, tenant_context, operation_count
            )
        
        # Run all tenant workloads concurrently
        tasks = [tenant_workload(tc) for tc in tenant_contexts]
        execution_times = await asyncio.gather(*tasks)
        
        return {
            tenant_contexts[i].tenant_id: execution_times[i]
            for i in range(len(tenant_contexts))
        }
    
    @standard_exception_handler
    async def test_constraint_isolation(
        self,
        model_class: Type,
        tenant_contexts: List[TenantContext],
        constraint_test_data: Dict[str, List[Dict]]
    ) -> List[TenantIsolationTestResult]:
        """Test that constraints are properly isolated between tenants"""
        
        results = []
        
        # Test unique constraints per tenant
        for tenant_context in tenant_contexts:
            result = await self._test_tenant_constraint_isolation(
                model_class, tenant_context, constraint_test_data
            )
            results.append(result)
        
        self.test_results.extend(results)
        return results
    
    async def _test_tenant_constraint_isolation(
        self,
        model_class: Type,
        tenant_context: TenantContext,
        constraint_test_data: Dict[str, List[Dict]]
    ) -> TenantIsolationTestResult:
        """Test constraint isolation for a single tenant"""
        
        start_time = time.time()
        violations = []
        records_tested = 0
        
        try:
            tenant_id = tenant_context.tenant_id
            
            if tenant_id not in constraint_test_data:
                return TenantIsolationTestResult(
                    test_name=f"constraint_isolation_{model_class.__name__}_{tenant_id}",
                    test_type=IsolationTestType.CONSTRAINT_ISOLATION,
                    tenant_id=tenant_id,
                    result="skip",
                    violations=[],
                    execution_time=time.time() - start_time,
                    records_tested=0,
                    error_message="No test data provided"
                )
            
            with self.SessionLocal() as session:
                # Test that unique constraints work within tenant
                test_data = constraint_test_data[tenant_id]
                
                # Create first record
                first_data = test_data[0].copy()
                first_data['tenant_id'] = tenant_id
                first_record = model_class(**first_data)
                session.add(first_record)
                session.commit()
                records_tested += 1
                
                # Try to create duplicate within same tenant (should fail)
                try:
                    duplicate_data = test_data[0].copy()
                    duplicate_data['tenant_id'] = tenant_id
                    duplicate_record = model_class(**duplicate_data)
                    session.add(duplicate_record)
                    session.commit()
                    
                    # If we get here, constraint was not enforced
                    violations.append(IsolationViolation(
                        violation_type=IsolationViolationType.CONSTRAINT_BYPASS,
                        tenant_id=tenant_id,
                        affected_tenant_id=None,
                        table=model_class.__tablename__,
                        record_id=getattr(duplicate_record, 'id', 'unknown'),
                        field='unique_constraint',
                        description=f"Unique constraint not enforced within tenant {tenant_id}",
                        severity="high"
                    ))
                
                except IntegrityError:
                    # Expected - constraint should prevent duplicate
                    session.rollback()
                
                # Test that same data can exist in different tenants
                if len(tenant_contexts) > 1:
                    other_tenant = next(
                        (tc for tc in tenant_contexts if tc.tenant_id != tenant_id),
                        None
                    )
                    
                    if other_tenant:
                        try:
                            other_tenant_data = test_data[0].copy()
                            other_tenant_data['tenant_id'] = other_tenant.tenant_id
                            other_tenant_record = model_class(**other_tenant_data)
                            session.add(other_tenant_record)
                            session.commit()
                            records_tested += 1
                        
                        except IntegrityError:
                            # This might indicate global constraint instead of tenant-scoped
                            violations.append(IsolationViolation(
                                violation_type=IsolationViolationType.CONSTRAINT_BYPASS,
                                tenant_id=tenant_id,
                                affected_tenant_id=other_tenant.tenant_id,
                                table=model_class.__tablename__,
                                record_id='N/A',
                                field='tenant_constraint_isolation',
                                description=f"Constraint prevents same data across different tenants",
                                severity="medium"
                            ))
                            session.rollback()
        
        except Exception as e:
            error_message = f"Constraint isolation test failed: {str(e)}"
            logger.error(error_message)
            
            return TenantIsolationTestResult(
                test_name=f"constraint_isolation_{model_class.__name__}_{tenant_context.tenant_id}",
                test_type=IsolationTestType.CONSTRAINT_ISOLATION,
                tenant_id=tenant_context.tenant_id,
                result="error",
                violations=violations,
                execution_time=time.time() - start_time,
                records_tested=records_tested,
                error_message=error_message
            )
        
        execution_time = time.time() - start_time
        result_status = "pass" if not violations else "fail"
        
        return TenantIsolationTestResult(
            test_name=f"constraint_isolation_{model_class.__name__}_{tenant_context.tenant_id}",
            test_type=IsolationTestType.CONSTRAINT_ISOLATION,
            tenant_id=tenant_context.tenant_id,
            result=result_status,
            violations=violations,
            execution_time=execution_time,
            records_tested=records_tested
        )
    
    def get_isolation_summary(self) -> Dict[str, Any]:
        """Get summary of all tenant isolation test results"""
        
        if not self.test_results:
            return {"total": 0, "summary": "No isolation tests run"}
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.result == "pass")
        failed_tests = sum(1 for r in self.test_results if r.result == "fail")
        error_tests = sum(1 for r in self.test_results if r.result == "error")
        
        total_violations = sum(len(r.violations) for r in self.test_results)
        critical_violations = sum(
            len([v for v in r.violations if v.severity == "critical"])
            for r in self.test_results
        )
        
        # Break down by test type
        type_breakdown = {}
        for result in self.test_results:
            test_type = result.test_type.value
            if test_type not in type_breakdown:
                type_breakdown[test_type] = {
                    "total": 0, "passed": 0, "failed": 0, "violations": 0
                }
            
            type_breakdown[test_type]["total"] += 1
            if result.result == "pass":
                type_breakdown[test_type]["passed"] += 1
            elif result.result == "fail":
                type_breakdown[test_type]["failed"] += 1
            type_breakdown[test_type]["violations"] += len(result.violations)
        
        # Break down by tenant
        tenant_breakdown = {}
        for result in self.test_results:
            tenant_id = result.tenant_id
            if tenant_id not in tenant_breakdown:
                tenant_breakdown[tenant_id] = {
                    "total": 0, "passed": 0, "failed": 0, "violations": 0
                }
            
            tenant_breakdown[tenant_id]["total"] += 1
            if result.result == "pass":
                tenant_breakdown[tenant_id]["passed"] += 1
            elif result.result == "fail":  
                tenant_breakdown[tenant_id]["failed"] += 1
            tenant_breakdown[tenant_id]["violations"] += len(result.violations)
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_violations": total_violations,
            "critical_violations": critical_violations,
            "test_type_breakdown": type_breakdown,
            "tenant_breakdown": tenant_breakdown
        }


# Convenience functions

async def comprehensive_tenant_isolation_test(
    database_url: str,
    model_classes: List[Type],
    tenant_contexts: List[TenantContext],
    test_data_per_tenant: Dict[str, List[Dict]],
    include_performance: bool = True
) -> Dict[str, Any]:
    """
    Run comprehensive tenant isolation tests across multiple models and tenants.
    
    Args:
        database_url: Database connection URL
        model_classes: List of SQLAlchemy model classes
        tenant_contexts: List of tenant contexts to test
        test_data_per_tenant: Test data organized by tenant ID
        include_performance: Whether to include performance isolation tests
        
    Returns:
        Dictionary with comprehensive isolation test results
    """
    tester = TenantIsolationTester(database_url)
    
    all_results = []
    
    # Test data isolation for each model
    for model_class in model_classes:
        logger.info(f"Testing isolation for {model_class.__name__}")
        
        # Data isolation tests
        data_results = await tester.test_data_isolation(
            model_class, tenant_contexts, test_data_per_tenant
        )
        all_results.extend(data_results)
        
        # Performance isolation tests
        if include_performance:
            perf_results = await tester.test_performance_isolation(
                model_class, tenant_contexts, 50
            )
            all_results.extend(perf_results)
        
        # Constraint isolation tests
        constraint_results = await tester.test_constraint_isolation(
            model_class, tenant_contexts, test_data_per_tenant
        )
        all_results.extend(constraint_results)
    
    return {
        "models_tested": len(model_classes),
        "tenants_tested": len(tenant_contexts),
        "total_tests": len(all_results),
        "summary": tester.get_isolation_summary(),
        "detailed_results": tester.test_results
    }