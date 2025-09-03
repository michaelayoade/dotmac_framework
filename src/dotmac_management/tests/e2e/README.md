# DotMac Management Backend E2E Tests

Comprehensive end-to-end test suite for container provisioning, lifecycle management, and multi-tenant isolation validation.

## Overview

This E2E test suite validates the complete tenant provisioning and container lifecycle management workflows for the DotMac ISP Framework. It ensures:

- ✅ **Complete tenant provisioning workflows** - From tenant creation to first admin login
- ✅ **Container lifecycle management** - Scaling, updates, backups, and deprovisioning  
- ✅ **Multi-tenant data isolation** - Zero cross-tenant data access or contamination
- ✅ **Resource isolation** - CPU, memory, storage, and network segregation
- ✅ **Security boundaries** - Authentication, authorization, and audit log isolation

## Test Categories

### 1. Tenant Provisioning Tests (`tenant_provisioning.spec.py`)

**Scope**: End-to-end tenant provisioning workflows

**Test Scenarios**:
- Management admin creates new tenant via UI
- Container provisioning triggers (Kubernetes/Docker deployment)
- Database schema creation and isolation
- Initial app deployment (ISP Framework)
- Health check validation
- Tenant admin first login

**Key Test Cases**:
- `test_successful_tenant_provisioning_end_to_end` - Complete workflow validation
- `test_tenant_provisioning_with_validation_failures` - Error handling
- `test_tenant_provisioning_container_deployment_failure` - Rollback scenarios
- `test_concurrent_tenant_provisioning` - Parallel provisioning
- `test_tenant_provisioning_monitoring_and_events` - Event logging

### 2. Container Lifecycle Tests (`container_lifecycle.spec.py`)

**Scope**: Container scaling, updates, backups, and deprovisioning

**Test Scenarios**:
- Horizontal and vertical container scaling
- Zero-downtime updates and rollbacks
- Database migrations during updates
- Automated backup and restore procedures
- Graceful and forced deprovisioning
- Resource cleanup and archival

**Key Test Classes**:
- `TestContainerScaling` - Auto-scaling and manual scaling operations
- `TestContainerUpdatesAndMigrations` - Application updates with data integrity
- `TestContainerBackupAndRestore` - Data protection and recovery
- `TestContainerDeprovisioning` - Clean resource removal
- `TestContainerMonitoringAndAlerts` - Health monitoring and failure recovery

### 3. Multi-Tenant Isolation Tests (`tenant_isolation.spec.py`)

**Scope**: Complete tenant isolation validation

**Test Scenarios**:
- Database schema isolation between tenants
- API endpoint access restrictions
- User authentication boundaries
- Resource usage isolation (CPU, memory, storage)
- Security policy isolation

**Key Test Classes**:
- `TestDatabaseIsolation` - Database-level tenant separation
- `TestAPIIsolation` - API endpoint and JWT token isolation
- `TestUIIsolation` - Frontend session and branding isolation
- `TestResourceIsolation` - Infrastructure resource limits
- `TestSecurityIsolation` - Audit logs and security policy separation

## Test Infrastructure

### Core Components

- **`conftest.py`** - Test fixtures and configuration
- **`factories.py`** - Test data generation using factory pattern
- **`utils.py`** - Shared utilities for database, API, and UI testing
- **`cleanup.py`** - Comprehensive cleanup and isolation validation
- **`run_tests.py`** - Automated test runner with environment setup

### Test Utilities

#### Database Testing
```python
from .utils import DatabaseTestUtils

# Wait for database readiness
await DatabaseTestUtils.wait_for_database_ready(db_url)

# Verify tenant data isolation
isolation_result = DatabaseTestUtils.verify_tenant_data_isolation(
    tenant_a_session, tenant_b_session, "customers", 
    tenant_a_id, tenant_b_id
)
```

#### Container Testing  
```python
from .utils import ContainerTestUtils

# Wait for container health
healthy = await ContainerTestUtils.wait_for_container_health(container_url)

# Monitor resource usage
metrics = await ContainerTestUtils.monitor_container_resources(container_id)
```

#### API Testing
```python
from .utils import ApiTestUtils

# Test API isolation between tenants
isolation_result = await ApiTestUtils.verify_tenant_api_isolation(
    tenant_a_url, tenant_b_url, tenant_a_token, tenant_b_token
)
```

## Test Data Management

### Factories

The test suite uses factory-based data generation for consistent, reproducible test scenarios:

```python
from .factories import TenantFactory

# Create tenant for provisioning tests
tenant_data = TenantFactory.create_provisioning_workflow_tenant(
    company_name="E2E Test ISP",
    subdomain="e2etest",
    plan="professional"
)

# Create multiple tenants for isolation testing
tenants = TenantFactory.create_isolation_test_tenants(count=2)
```

### Cleanup and Isolation

Automated cleanup ensures complete test isolation:

```python
from .cleanup import isolated_test_environment

async with isolated_test_environment("test_name") as cleaner:
    # Test execution
    cleaner.register_tenant(tenant_id)
    cleaner.register_container(container_id)
    # Automatic cleanup on exit
```

## Running Tests

### Prerequisites

1. **Python Dependencies**:
   ```bash
   poetry install --with dev
   ```

2. **Test Databases**:
   ```bash
   # Management database
   postgresql://test_user:test_pass@localhost:5433/test_management
   
   # Tenant databases  
   postgresql://test_user:test_pass@localhost:5434/test_tenant_a
   postgresql://test_user:test_pass@localhost:5435/test_tenant_b
   ```

3. **Container Orchestration** (mocked in tests):
   - Docker or Kubernetes cluster
   - Coolify API access (mocked)

### Test Execution

#### Run All E2E Tests
```bash
cd src/dotmac_management/tests/e2e
python run_tests.py
```

#### Run Specific Test Categories
```bash
# Tenant provisioning only
python run_tests.py --provisioning

# Container lifecycle only  
python run_tests.py --lifecycle

# Multi-tenant isolation only
python run_tests.py --isolation
```

#### Debug Mode
```bash
python run_tests.py --debug
```

#### Parallel Execution
```bash
python run_tests.py --parallel 4
```

#### With Coverage Reporting
```bash
python run_tests.py --coverage
```

### Using pytest Directly

```bash
# All E2E tests
pytest -m e2e -v

# Specific category
pytest -m tenant_provisioning -v
pytest -m container_lifecycle -v  
pytest -m tenant_isolation -v

# Debug mode
pytest -m e2e -v -s --log-cli-level=DEBUG

# Parallel execution
pytest -m e2e -n 4
```

## Test Environment Configuration

### Environment Variables

```bash
# Test environment
export ENVIRONMENT=e2e_testing
export LOG_LEVEL=INFO
export DISABLE_REAL_DEPLOYMENTS=true

# Database URLs
export TEST_MANAGEMENT_DB="postgresql://test_user:test_pass@localhost:5433/test_management"
export TEST_TENANT_A_DB="postgresql://test_user:test_pass@localhost:5434/test_tenant_a" 
export TEST_TENANT_B_DB="postgresql://test_user:test_pass@localhost:5435/test_tenant_b"

# API Configuration
export TEST_BASE_URL="https://test.dotmac.local"

# Test behavior
export TEST_CLEANUP_ENABLED=true
export TEST_DATA_ISOLATION=strict
```

### Mock Services

Tests use comprehensive mocking for external services:

- **Coolify API** - Container orchestration
- **Database Services** - PostgreSQL and Redis provisioning
- **DNS/Domain Management** - Subdomain allocation
- **Email Services** - Welcome notifications
- **Monitoring APIs** - Health checks and metrics

## Success Criteria

### Tenant Provisioning
- ✅ Complete provisioning workflow (16 steps) validated
- ✅ Zero provisioning failures under normal conditions
- ✅ Proper error handling and rollback on failures
- ✅ Event logging and monitoring throughout process

### Container Lifecycle  
- ✅ Scaling operations maintain service availability
- ✅ Zero-downtime updates and rollbacks
- ✅ Data integrity preserved during operations
- ✅ Complete resource cleanup after deprovisioning

### Multi-Tenant Isolation
- ✅ **ZERO** cross-tenant data access possible
- ✅ Complete API endpoint isolation
- ✅ Resource usage limits enforced per tenant
- ✅ Security boundaries maintained at all levels

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   ```bash
   # Check database containers
   docker ps | grep postgres
   
   # Verify connection
   psql postgresql://test_user:test_pass@localhost:5433/test_management
   ```

2. **Test Data Contamination**
   ```bash
   # Force cleanup
   python run_tests.py --cleanup-only
   
   # Reset test databases
   dropdb test_management && createdb test_management
   ```

3. **Container Service Unavailable**
   ```bash
   # Check Docker daemon
   docker info
   
   # Verify Coolify service (if using real deployment)
   curl -f http://coolify-api:8080/health
   ```

### Debug Mode

Enable comprehensive debugging:

```bash
python run_tests.py --debug --skip-cleanup
```

This provides:
- Detailed log output
- No parallel execution
- Test artifacts preserved
- Browser screenshots on failures

### Isolation Validation

Verify test isolation after failures:

```bash
# Validate database isolation
python -c "
from src.dotmac_management.tests.e2e.cleanup import TestIsolationValidator
# Run isolation checks
"

# Manual cleanup
python -c "
from src.dotmac_management.tests.e2e.cleanup import E2ETestCleaner
import asyncio
cleaner = E2ETestCleaner()
asyncio.run(cleaner.cleanup_all())
"
```

## Continuous Integration

### GitHub Actions Integration

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install --with dev
    
    - name: Setup test databases
      run: |
        # Create test databases
        createdb -h localhost -U postgres test_management
        createdb -h localhost -U postgres test_tenant_a
        createdb -h localhost -U postgres test_tenant_b
    
    - name: Run E2E tests
      run: |
        cd src/dotmac_management/tests/e2e
        python run_tests.py --junit-xml=results.xml --coverage
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: e2e-test-results
        path: |
          results.xml
          htmlcov/
```

## Performance Benchmarks

### Expected Performance

- **Tenant Provisioning**: < 5 minutes end-to-end
- **Container Scaling**: < 30 seconds per operation  
- **Database Operations**: < 2 seconds per query
- **Test Suite Execution**: < 45 minutes complete suite

### Monitoring

Tests include performance monitoring:

```python
from .utils import performance_monitor

async with performance_monitor("tenant_provisioning"):
    # Test execution with timing
    pass
```

## Contributing

### Adding New Tests

1. **Create test file**: Follow naming convention `*.spec.py`
2. **Add test markers**: Use appropriate `pytest.mark` decorators
3. **Include cleanup**: Register all resources with cleaner
4. **Document scenarios**: Add comprehensive docstrings
5. **Validate isolation**: Ensure no cross-test contamination

### Test Categories

Mark tests with appropriate categories:

```python
@pytest.mark.tenant_provisioning
@pytest.mark.slow
class TestNewFeature:
    async def test_feature_workflow(self, ...):
        # Test implementation
```

### Isolation Requirements

All tests MUST:
- Use unique tenant IDs and subdomains
- Clean up all created resources
- Verify no cross-tenant data access
- Include isolation validation assertions

## Security Considerations

### Test Data Security

- All test data uses synthetic/mock values
- No real credentials or sensitive information
- Test databases isolated from production
- Automatic cleanup prevents data persistence

### Access Controls

- Tests validate authentication boundaries
- JWT token isolation verified
- API endpoint access restrictions tested
- Session management isolation confirmed

### Audit Requirements

- All test actions logged and tracked
- Isolation validation results recorded
- Cleanup verification documented
- Security boundary testing mandatory

---

**Status**: ✅ **PRODUCTION READY**

This E2E test suite provides comprehensive validation of the DotMac ISP Framework's multi-tenant architecture with zero tolerance for isolation failures or data contamination.