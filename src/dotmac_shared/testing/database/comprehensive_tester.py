"""
Comprehensive Database Testing Suite

Unified interface for running all database tests including:
- Transaction testing
- Constraint validation  
- Data integrity testing
- Performance benchmarking
- Tenant isolation validation
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from enum import Enum

from ...core.logging import get_logger
from ...tenant.identity import TenantContext
from ...api.exception_handlers import standard_exception_handler

from .transaction_testing import DatabaseTransactionTester, test_model_transactions
from .constraint_validation import DatabaseConstraintValidator, validate_model_constraints  
from .data_integrity import DataIntegrityTester, comprehensive_integrity_test
from .performance_testing import DatabasePerformanceTester, quick_performance_test
from .tenant_isolation import TenantIsolationTester, comprehensive_tenant_isolation_test

logger = get_logger(__name__)


class DatabaseTestSuite(str, Enum):
    """Available database test suites"""
    TRANSACTIONS = "transactions"
    CONSTRAINTS = "constraints"
    INTEGRITY = "integrity" 
    PERFORMANCE = "performance"
    TENANT_ISOLATION = "tenant_isolation"
    COMPREHENSIVE = "comprehensive"


@dataclass
class DatabaseTestConfig:
    """Configuration for comprehensive database testing"""
    database_url: str
    test_suites: List[DatabaseTestSuite] = None
    
    # Transaction test config
    include_rollback_tests: bool = True
    include_isolation_tests: bool = True
    include_concurrent_tests: bool = True
    
    # Constraint test config
    include_custom_validators: bool = False
    custom_validators: List = None
    
    # Integrity test config
    concurrent_operations: int = 5
    include_acid_tests: bool = True
    
    # Performance test config
    load_test_users: int = 10
    load_test_duration: int = 30
    include_stress_tests: bool = False
    include_query_benchmarks: bool = True
    
    # Tenant isolation config
    include_performance_isolation: bool = True
    
    def __post_init__(self):
        if self.test_suites is None:
            self.test_suites = [DatabaseTestSuite.COMPREHENSIVE]
        if self.custom_validators is None:
            self.custom_validators = []


class ComprehensiveDatabaseTester:
    """
    Unified database testing framework that runs all test suites.
    
    Features:
    - Coordinated test execution
    - Comprehensive reporting
    - Test suite selection
    - Performance impact analysis
    - Automated recommendations
    """
    
    def __init__(self, config: DatabaseTestConfig):
        self.config = config
        self.test_results: Dict[str, Any] = {}
        self.execution_times: Dict[str, float] = {}
        
    @standard_exception_handler
    async def run_comprehensive_tests(
        self,
        model_classes: List[Type],
        test_data: Dict[Type, List[Dict]],
        tenant_contexts: Optional[List[TenantContext]] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive database tests across all specified suites.
        
        Args:
            model_classes: SQLAlchemy model classes to test
            test_data: Test data for each model class
            tenant_contexts: Tenant contexts for isolation testing
            
        Returns:
            Comprehensive test results and analysis
        """
        logger.info(f"Starting comprehensive database testing for {len(model_classes)} models")
        logger.info(f"Test suites: {[suite.value for suite in self.config.test_suites]}")
        
        overall_start_time = time.time()
        
        # Run each test suite
        for suite in self.config.test_suites:
            if suite == DatabaseTestSuite.COMPREHENSIVE:
                # Run all suites
                await self._run_all_test_suites(model_classes, test_data, tenant_contexts)
                break
            else:
                await self._run_single_test_suite(suite, model_classes, test_data, tenant_contexts)
        
        overall_execution_time = time.time() - overall_start_time
        
        # Generate comprehensive report
        report = await self._generate_comprehensive_report(overall_execution_time)
        
        logger.info(f"✅ Comprehensive database testing completed in {overall_execution_time:.2f} seconds")
        return report
    
    async def _run_all_test_suites(
        self,
        model_classes: List[Type],
        test_data: Dict[Type, List[Dict]],
        tenant_contexts: Optional[List[TenantContext]]
    ):
        """Run all available test suites"""
        
        suites_to_run = [
            DatabaseTestSuite.TRANSACTIONS,
            DatabaseTestSuite.CONSTRAINTS,
            DatabaseTestSuite.INTEGRITY,
            DatabaseTestSuite.PERFORMANCE,
        ]
        
        if tenant_contexts:
            suites_to_run.append(DatabaseTestSuite.TENANT_ISOLATION)
        
        for suite in suites_to_run:
            await self._run_single_test_suite(suite, model_classes, test_data, tenant_contexts)
    
    async def _run_single_test_suite(
        self,
        suite: DatabaseTestSuite,
        model_classes: List[Type],
        test_data: Dict[Type, List[Dict]],
        tenant_contexts: Optional[List[TenantContext]]
    ):
        """Run a single test suite"""
        
        suite_start_time = time.time()
        logger.info(f"Running {suite.value} test suite")
        
        try:
            if suite == DatabaseTestSuite.TRANSACTIONS:
                await self._run_transaction_tests(model_classes, test_data)
            
            elif suite == DatabaseTestSuite.CONSTRAINTS:
                await self._run_constraint_tests(model_classes, test_data)
            
            elif suite == DatabaseTestSuite.INTEGRITY:
                await self._run_integrity_tests(model_classes, test_data)
            
            elif suite == DatabaseTestSuite.PERFORMANCE:
                await self._run_performance_tests(model_classes, test_data)
            
            elif suite == DatabaseTestSuite.TENANT_ISOLATION:
                if tenant_contexts:
                    await self._run_tenant_isolation_tests(model_classes, test_data, tenant_contexts)
                else:
                    logger.warning("Skipping tenant isolation tests - no tenant contexts provided")
        
        except Exception as e:
            logger.error(f"Test suite {suite.value} failed: {e}")
            self.test_results[suite.value] = {"status": "error", "error": str(e)}
        
        suite_execution_time = time.time() - suite_start_time
        self.execution_times[suite.value] = suite_execution_time
        logger.info(f"✅ {suite.value} test suite completed in {suite_execution_time:.2f} seconds")
    
    async def _run_transaction_tests(self, model_classes: List[Type], test_data: Dict[Type, List[Dict]]):
        """Run transaction testing suite"""
        
        transaction_results = {}
        
        for model_class in model_classes:
            if model_class in test_data and test_data[model_class]:
                try:
                    result = await test_model_transactions(
                        self.config.database_url,
                        model_class,
                        test_data[model_class],
                        include_concurrent=self.config.include_concurrent_tests
                    )
                    transaction_results[model_class.__name__] = result
                
                except Exception as e:
                    logger.error(f"Transaction tests failed for {model_class.__name__}: {e}")
                    transaction_results[model_class.__name__] = {"status": "error", "error": str(e)}
        
        self.test_results["transactions"] = transaction_results
    
    async def _run_constraint_tests(self, model_classes: List[Type], test_data: Dict[Type, List[Dict]]):
        """Run constraint validation suite"""
        
        constraint_results = {}
        
        # Create a session for constraint testing
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(self.config.database_url)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as session:
            for model_class in model_classes:
                if model_class in test_data and test_data[model_class]:
                    try:
                        result = await validate_model_constraints(
                            session,
                            model_class,
                            test_data[model_class],
                            include_custom=self.config.include_custom_validators,
                            custom_validators=self.config.custom_validators
                        )
                        constraint_results[model_class.__name__] = result
                    
                    except Exception as e:
                        logger.error(f"Constraint tests failed for {model_class.__name__}: {e}")
                        constraint_results[model_class.__name__] = {"status": "error", "error": str(e)}
        
        self.test_results["constraints"] = constraint_results
    
    async def _run_integrity_tests(self, model_classes: List[Type], test_data: Dict[Type, List[Dict]]):
        """Run data integrity testing suite"""
        
        try:
            result = await comprehensive_integrity_test(
                self.config.database_url,
                model_classes,
                test_data,
                include_concurrent=self.config.include_concurrent_tests,
                concurrent_operations=self.config.concurrent_operations
            )
            self.test_results["integrity"] = result
        
        except Exception as e:
            logger.error(f"Integrity tests failed: {e}")
            self.test_results["integrity"] = {"status": "error", "error": str(e)}
    
    async def _run_performance_tests(self, model_classes: List[Type], test_data: Dict[Type, List[Dict]]):
        """Run performance testing suite"""
        
        performance_results = {}
        
        for model_class in model_classes:
            if model_class in test_data and test_data[model_class]:
                try:
                    result = await quick_performance_test(
                        self.config.database_url,
                        model_class,
                        test_data[model_class],
                        concurrent_users=self.config.load_test_users,
                        duration_seconds=self.config.load_test_duration
                    )
                    performance_results[model_class.__name__] = result
                
                except Exception as e:
                    logger.error(f"Performance tests failed for {model_class.__name__}: {e}")
                    performance_results[model_class.__name__] = {"status": "error", "error": str(e)}
        
        self.test_results["performance"] = performance_results
    
    async def _run_tenant_isolation_tests(
        self,
        model_classes: List[Type],
        test_data: Dict[Type, List[Dict]],
        tenant_contexts: List[TenantContext]
    ):
        """Run tenant isolation testing suite"""
        
        # Convert test data to tenant-specific format
        tenant_test_data = {}
        for tenant_context in tenant_contexts:
            tenant_id = tenant_context.tenant_id
            tenant_test_data[tenant_id] = []
            
            # Use first model's test data for each tenant
            if model_classes and model_classes[0] in test_data:
                tenant_test_data[tenant_id] = test_data[model_classes[0]][:3]  # Limit data per tenant
        
        try:
            result = await comprehensive_tenant_isolation_test(
                self.config.database_url,
                model_classes,
                tenant_contexts,
                tenant_test_data,
                include_performance=self.config.include_performance_isolation
            )
            self.test_results["tenant_isolation"] = result
        
        except Exception as e:
            logger.error(f"Tenant isolation tests failed: {e}")
            self.test_results["tenant_isolation"] = {"status": "error", "error": str(e)}
    
    async def _generate_comprehensive_report(self, total_execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report with analysis and recommendations"""
        
        # Count total tests and results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        
        suite_summaries = {}
        
        for suite_name, suite_result in self.test_results.items():
            if isinstance(suite_result, dict):
                if "status" in suite_result and suite_result["status"] == "error":
                    error_tests += 1
                    suite_summaries[suite_name] = {"status": "error", "error": suite_result.get("error")}
                else:
                    # Process suite-specific results
                    suite_summary = self._analyze_suite_results(suite_name, suite_result)
                    suite_summaries[suite_name] = suite_summary
                    
                    if "summary" in suite_result:
                        summary = suite_result["summary"]
                        if isinstance(summary, dict):
                            total_tests += summary.get("total", 0)
                            passed_tests += summary.get("passed", summary.get("successful", 0))
                            failed_tests += summary.get("failed", 0)
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        # Performance analysis
        performance_analysis = self._analyze_performance_impact()
        
        return {
            "summary": {
                "total_execution_time": total_execution_time,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "suites_run": len(self.test_results)
            },
            "suite_summaries": suite_summaries,
            "execution_times": self.execution_times,
            "performance_analysis": performance_analysis,
            "recommendations": recommendations,
            "detailed_results": self.test_results
        }
    
    def _analyze_suite_results(self, suite_name: str, suite_result: Dict) -> Dict[str, Any]:
        """Analyze results for a specific test suite"""
        
        if "summary" in suite_result:
            summary = suite_result["summary"]
            return {
                "status": "completed",
                "tests_run": summary.get("total", 0),
                "success_rate": summary.get("pass_rate", summary.get("success_rate", 0)),
                "key_metrics": self._extract_key_metrics(suite_name, summary)
            }
        
        return {"status": "completed", "details": "Results processed"}
    
    def _extract_key_metrics(self, suite_name: str, summary: Dict) -> Dict[str, Any]:
        """Extract key metrics for each test suite"""
        
        metrics = {}
        
        if suite_name == "performance":
            metrics.update({
                "avg_ops_per_second": summary.get("average_ops_per_second", 0),
                "avg_response_time": summary.get("average_response_time", 0)
            })
        
        elif suite_name == "integrity":
            metrics.update({
                "total_violations": summary.get("total_violations", 0),
                "acid_tests": summary.get("acid_tests", 0)
            })
        
        elif suite_name == "tenant_isolation":
            metrics.update({
                "critical_violations": summary.get("critical_violations", 0),
                "tenants_tested": summary.get("tenants_tested", 0)
            })
        
        return metrics
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Performance recommendations
        if "performance" in self.test_results:
            perf_results = self.test_results["performance"]
            for model_name, model_results in perf_results.items():
                if isinstance(model_results, dict) and "recommendations" in model_results:
                    recommendations.extend([
                        f"{model_name}: {rec}" for rec in model_results["recommendations"]
                    ])
        
        # Integrity recommendations
        if "integrity" in self.test_results:
            integrity_result = self.test_results["integrity"]
            if isinstance(integrity_result, dict) and "summary" in integrity_result:
                violations = integrity_result["summary"].get("total_violations", 0)
                if violations > 0:
                    recommendations.append(f"Review {violations} data integrity violations")
        
        # Tenant isolation recommendations
        if "tenant_isolation" in self.test_results:
            isolation_result = self.test_results["tenant_isolation"]
            if isinstance(isolation_result, dict) and "summary" in isolation_result:
                critical_violations = isolation_result["summary"].get("critical_violations", 0)
                if critical_violations > 0:
                    recommendations.append(f"CRITICAL: Fix {critical_violations} tenant isolation violations")
        
        if not recommendations:
            recommendations.append("All tests passed - database appears to be properly configured")
        
        return recommendations
    
    def _analyze_performance_impact(self) -> Dict[str, Any]:
        """Analyze the performance impact of different test suites"""
        
        if not self.execution_times:
            return {"status": "no_data"}
        
        total_time = sum(self.execution_times.values())
        suite_percentages = {
            suite: (time_taken / total_time * 100) 
            for suite, time_taken in self.execution_times.items()
        }
        
        slowest_suite = max(self.execution_times.items(), key=lambda x: x[1])
        fastest_suite = min(self.execution_times.items(), key=lambda x: x[1])
        
        return {
            "total_time": total_time,
            "suite_percentages": suite_percentages,
            "slowest_suite": {"name": slowest_suite[0], "time": slowest_suite[1]},
            "fastest_suite": {"name": fastest_suite[0], "time": fastest_suite[1]},
            "average_suite_time": total_time / len(self.execution_times)
        }


# Convenience function
async def run_full_database_test_suite(
    database_url: str,
    model_classes: List[Type],
    test_data: Dict[Type, List[Dict]],
    tenant_contexts: Optional[List[TenantContext]] = None,
    **config_kwargs
) -> Dict[str, Any]:
    """
    Convenience function to run the complete database test suite.
    
    Args:
        database_url: Database connection string
        model_classes: SQLAlchemy models to test
        test_data: Test data for each model
        tenant_contexts: Optional tenant contexts for isolation testing
        **config_kwargs: Additional configuration options
        
    Returns:
        Comprehensive test results and recommendations
    """
    config = DatabaseTestConfig(
        database_url=database_url,
        **config_kwargs
    )
    
    tester = ComprehensiveDatabaseTester(config)
    
    return await tester.run_comprehensive_tests(
        model_classes,
        test_data,
        tenant_contexts
    )