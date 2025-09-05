"""
Enhanced Database Testing Framework

Comprehensive testing utilities for database operations including:
- Transaction testing and rollback scenarios
- Constraint validation and enforcement
- Data integrity with concurrent operations
- Performance and load testing
- Tenant isolation validation
"""

from .constraint_validation import (
    ConstraintTestCase,
    ConstraintType,
    ConstraintValidationResult,
    DatabaseConstraintValidator,
    create_constraint_test_data,
    validate_model_constraints,
)
from .data_integrity import (
    DataIntegrityTester,
    IntegrityTestResult,
    IntegrityTestType,
    IntegrityViolation,
    comprehensive_integrity_test,
)
from .performance_testing import (
    DatabasePerformanceTester,
    LoadTestConfig,
    PerformanceMetrics,
    PerformanceTestType,
    quick_performance_test,
)
from .tenant_isolation import (
    IsolationTestType,
    IsolationViolation,
    TenantIsolationTester,
    TenantIsolationTestResult,
    comprehensive_tenant_isolation_test,
)
from .transaction_testing import (
    DatabaseTransactionTester,
    TransactionTestCase,
    TransactionTestResult,
    test_model_transactions,
    validate_transaction_integrity,
)

__all__ = [
    # Transaction Testing
    "DatabaseTransactionTester",
    "TransactionTestCase",
    "TransactionTestResult",
    "test_model_transactions",
    "validate_transaction_integrity",
    # Constraint Validation
    "DatabaseConstraintValidator",
    "ConstraintType",
    "ConstraintTestCase",
    "ConstraintValidationResult",
    "validate_model_constraints",
    "create_constraint_test_data",
    # Data Integrity
    "DataIntegrityTester",
    "IntegrityTestType",
    "IntegrityViolation",
    "IntegrityTestResult",
    "comprehensive_integrity_test",
    # Performance Testing
    "DatabasePerformanceTester",
    "PerformanceTestType",
    "PerformanceMetrics",
    "LoadTestConfig",
    "quick_performance_test",
    # Tenant Isolation
    "TenantIsolationTester",
    "IsolationTestType",
    "IsolationViolation",
    "TenantIsolationTestResult",
    "comprehensive_tenant_isolation_test",
]
