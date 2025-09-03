# Enhanced Database Testing Framework

Comprehensive testing utilities for database operations, addressing the current gaps in database-specific tests with transaction testing, constraint validation, and data integrity checks.

## Overview

This framework provides five core testing modules:

1. **Transaction Testing** - ACID properties, rollbacks, isolation levels
2. **Constraint Validation** - Primary keys, foreign keys, unique constraints
3. **Data Integrity** - Concurrent operations, referential integrity, business rules
4. **Performance Testing** - Load testing, stress testing, query benchmarking
5. **Tenant Isolation** - Multi-tenant data isolation and security boundaries

## Quick Start

```python
from dotmac_shared.testing.database import run_full_database_test_suite

# Run comprehensive tests
results = await run_full_database_test_suite(
    database_url="postgresql://user:pass@localhost/db",
    model_classes=[User, Order, Product],
    test_data={
        User: [{"username": "test1", "email": "test@example.com"}],
        Order: [{"user_id": 1, "amount": 1000}]
    },
    tenant_contexts=[tenant1, tenant2]
)

print(f"Pass rate: {results['summary']['pass_rate']:.1f}%")
```

## Core Modules

### 1. Transaction Testing (`transaction_testing.py`)

Tests database transaction behavior including:

- **ACID Properties**: Atomicity, Consistency, Isolation, Durability
- **Rollback Scenarios**: Explicit rollbacks, constraint violations, savepoints
- **Isolation Levels**: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE
- **Concurrent Access**: Deadlock detection, transaction conflicts

```python
from dotmac_shared.testing.database import DatabaseTransactionTester

tester = DatabaseTransactionTester("postgresql://localhost/db")

# Test rollback scenarios
rollback_results = await tester.test_rollback_scenarios(User, test_data)

# Test isolation levels  
isolation_results = await tester.test_isolation_levels(User, test_data[0])

# Test concurrent access
concurrent_results = await tester.test_concurrent_access(User, test_data)
```

### 2. Constraint Validation (`constraint_validation.py`)

Validates database constraints and their enforcement:

- **Primary Key Constraints**: Duplicate detection, null prevention
- **Foreign Key Constraints**: Invalid references, cascading rules
- **Unique Constraints**: Duplicate value prevention
- **Not Null Constraints**: Required field validation
- **Check Constraints**: Custom validation rules
- **Custom Validators**: Business logic constraints

```python
from dotmac_shared.testing.database import DatabaseConstraintValidator

validator = DatabaseConstraintValidator(session)

# Validate all model constraints
results = await validator.validate_model_constraints(User, test_data_sets)

# Test custom business rules
custom_results = await validator.validate_custom_constraints(
    User, 
    [lambda user: len(user.username) >= 3],
    test_data_sets
)
```

### 3. Data Integrity (`data_integrity.py`)

Comprehensive data integrity testing:

- **ACID Properties**: Full ACID compliance testing
- **Referential Integrity**: Parent-child relationship consistency
- **Concurrent Data Access**: Multi-session integrity validation
- **Business Rules**: Custom integrity constraints
- **Cross-Table Validation**: Relationship consistency

```python
from dotmac_shared.testing.database import DataIntegrityTester

tester = DataIntegrityTester("postgresql://localhost/db")

# Test ACID properties
acid_results = await tester.test_acid_properties([User, Order], test_data)

# Test referential integrity
ref_results = await tester.test_referential_integrity(
    User, Order, parent_data, child_data, "user_id"
)

# Test concurrent integrity
concurrent_results = await tester.test_concurrent_data_integrity(
    User, test_data, concurrent_sessions=10
)
```

### 4. Performance Testing (`performance_testing.py`)

Database performance and load testing:

- **Load Testing**: Gradual ramp-up with concurrent users
- **Stress Testing**: Breaking point identification
- **Query Benchmarking**: Individual query performance
- **Connection Pool Testing**: Pool size optimization
- **Resource Monitoring**: CPU, memory, connection usage

```python
from dotmac_shared.testing.database import DatabasePerformanceTester, LoadTestConfig

tester = DatabasePerformanceTester("postgresql://localhost/db")

# Load testing
config = LoadTestConfig(
    concurrent_users=50,
    duration_seconds=60,
    operations_per_user=100
)
load_results = await tester.run_load_test(User, test_data, config)

# Query benchmarking
queries = [
    ("user_lookup", "SELECT * FROM users WHERE username = :username"),
    ("order_summary", "SELECT COUNT(*) FROM orders WHERE user_id = :user_id")
]
benchmark_results = await tester.benchmark_queries(queries, iterations=1000)

# Stress testing
stress_results = await tester.run_stress_test(User, test_data, max_users=200)
```

### 5. Tenant Isolation (`tenant_isolation.py`)

Multi-tenant data isolation validation:

- **Data Isolation**: Tenant data segregation
- **Query Isolation**: Tenant-filtered query results
- **Cross-Tenant Access Prevention**: Unauthorized data access
- **Performance Isolation**: No noisy neighbor effects
- **Security Boundaries**: Tenant security validation

```python
from dotmac_shared.testing.database import TenantIsolationTester

tester = TenantIsolationTester("postgresql://localhost/db")

# Test data isolation
isolation_results = await tester.test_data_isolation(
    User, tenant_contexts, test_data_per_tenant
)

# Test performance isolation
perf_isolation = await tester.test_performance_isolation(
    User, tenant_contexts, load_per_tenant=100
)

# Test constraint isolation
constraint_isolation = await tester.test_constraint_isolation(
    User, tenant_contexts, constraint_test_data
)
```

## Comprehensive Testing Suite

The `ComprehensiveDatabaseTester` coordinates all test modules:

```python
from dotmac_shared.testing.database import DatabaseTestConfig, ComprehensiveDatabaseTester

config = DatabaseTestConfig(
    database_url="postgresql://localhost/db",
    test_suites=["comprehensive"],
    concurrent_operations=10,
    load_test_users=20,
    load_test_duration=30
)

tester = ComprehensiveDatabaseTester(config)
results = await tester.run_comprehensive_tests(
    model_classes=[User, Order],
    test_data={User: user_data, Order: order_data},
    tenant_contexts=[tenant1, tenant2]
)

# Analyze results
print(f"Total tests: {results['summary']['total_tests']}")
print(f"Pass rate: {results['summary']['pass_rate']:.1f}%")

for recommendation in results['recommendations']:
    print(f"• {recommendation}")
```

## Configuration Options

### DatabaseTestConfig

```python
config = DatabaseTestConfig(
    database_url="postgresql://localhost/db",
    
    # Test suite selection
    test_suites=["transactions", "constraints", "integrity", "performance", "tenant_isolation"],
    
    # Transaction testing
    include_rollback_tests=True,
    include_isolation_tests=True,
    include_concurrent_tests=True,
    
    # Constraint testing
    include_custom_validators=True,
    custom_validators=[validation_functions],
    
    # Integrity testing
    concurrent_operations=5,
    include_acid_tests=True,
    
    # Performance testing
    load_test_users=10,
    load_test_duration=30,
    include_stress_tests=False,
    include_query_benchmarks=True,
    
    # Tenant isolation
    include_performance_isolation=True
)
```

## Example Results

```python
{
    "summary": {
        "total_execution_time": 45.67,
        "total_tests": 156,
        "passed_tests": 142,
        "failed_tests": 8,
        "error_tests": 6,
        "pass_rate": 91.0,
        "suites_run": 5
    },
    "suite_summaries": {
        "transactions": {"status": "completed", "success_rate": 95.2},
        "constraints": {"status": "completed", "success_rate": 88.7},
        "integrity": {"status": "completed", "success_rate": 92.1},
        "performance": {"status": "completed", "avg_ops_per_second": 847.3},
        "tenant_isolation": {"status": "completed", "critical_violations": 0}
    },
    "recommendations": [
        "Consider adding database indexes for better performance",
        "Review 3 constraint validation failures in Order model",
        "All tenant isolation tests passed - security boundaries are properly configured"
    ]
}
```

## Best Practices

### Test Data Preparation

```python
# Create realistic test data with variations
test_data = {
    User: [
        {"username": "user1", "email": "user1@example.com", "tenant_id": "tenant_1"},
        {"username": "user2", "email": "user2@example.com", "tenant_id": "tenant_1"},
        {"username": "user3", "email": "user3@example.com", "tenant_id": "tenant_2"}
    ],
    Order: [
        {"user_id": 1, "amount": 1000, "status": "pending", "tenant_id": "tenant_1"},
        {"user_id": 1, "amount": 2000, "status": "completed", "tenant_id": "tenant_1"}
    ]
}
```

### Tenant Context Setup

```python
tenant_contexts = [
    TenantContext(
        tenant_id="tenant_1",
        subdomain="company1",
        host="company1.example.com",
        is_management=False,
        is_verified=True,
        metadata={"plan": "premium"}
    )
]
```

### Custom Validation Rules

```python
def validate_email_format(user):
    return "@" in user.email and "." in user.email

def validate_order_amount(order):
    return order.amount > 0 and order.amount <= 1000000

custom_validators = [validate_email_format, validate_order_amount]
```

## Integration with CI/CD

```yaml
# .github/workflows/database-tests.yml
- name: Run Database Tests
  run: |
    python -m pytest tests/database/ -v
    python examples/database_testing_example.py
```

## Performance Considerations

- **Parallel Execution**: Tests can run concurrently where safe
- **Resource Monitoring**: Tracks CPU, memory, and connection usage
- **Cleanup**: Automatic cleanup of test data
- **Connection Pooling**: Optimized connection management

## Troubleshooting

### Common Issues

1. **Connection Pool Exhaustion**
   ```python
   # Increase pool size or reduce concurrent operations
   config.concurrent_operations = 5
   ```

2. **Transaction Deadlocks**
   ```python
   # Enable deadlock detection
   config.include_isolation_tests = True
   ```

3. **Tenant Data Leakage**
   ```python
   # Enable comprehensive isolation testing
   config.test_suites.append("tenant_isolation")
   ```

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use smaller test sets for debugging
test_data = {User: test_data[User][:2]}  # Limit data
```

## Advanced Usage

### Custom Test Cases

```python
from dotmac_shared.testing.database import TransactionTestCase, TransactionTestResult

custom_test = TransactionTestCase(
    name="custom_business_logic_test",
    operations=[
        lambda s: create_user(s, "test_user"),
        lambda s: validate_user_state(s, "test_user"),
        lambda s: process_user_workflow(s, "test_user")
    ],
    expected_result=TransactionTestResult.SUCCESS
)

result = await tester.run_transaction_test(custom_test)
```

### Performance Profiling

```python
# Profile specific queries
queries_to_profile = [
    ("slow_query", "SELECT * FROM orders o JOIN users u ON o.user_id = u.id WHERE u.created_at > :date"),
    ("fast_query", "SELECT id, username FROM users WHERE id = :user_id")
]

benchmark_results = await tester.benchmark_queries(queries_to_profile, iterations=5000)

for query_name, metrics in benchmark_results.items():
    print(f"{query_name}: {metrics.average_response_time:.3f}s avg")
```

This comprehensive database testing framework addresses the current gaps in database testing by providing thorough validation of transactions, constraints, data integrity, performance, and tenant isolation - ensuring robust and reliable database operations in production.