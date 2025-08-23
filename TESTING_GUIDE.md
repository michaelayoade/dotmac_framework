# DotMac Framework - Comprehensive Testing Guide

## 🎯 Overview

This testing guide provides everything you need to know about testing in the DotMac Framework. We've implemented enterprise-grade testing infrastructure with comprehensive CI/CD pipelines, quality gates, and monitoring.

## 🏗️ Testing Infrastructure

### Test Architecture

```
Testing Stack:
├── Unit Tests (70%)        # Fast, isolated tests
├── Integration Tests (20%) # Component interaction tests  
├── End-to-End Tests (10%)  # Full workflow tests
├── Contract Tests          # API schema validation
├── Performance Tests       # Load and benchmark tests
└── Security Tests          # Vulnerability and penetration tests
```

### Test Environment

- **Local Testing**: pytest with async support
- **Docker Testing**: Isolated containers with PostgreSQL, Redis, TimescaleDB
- **CI/CD Testing**: GitHub Actions with multiple environments
- **Quality Gates**: Automated quality thresholds and reporting

## 🚀 Quick Start

### Prerequisites

1. **Set up development environment**:
   ```bash
   python scripts/dev-setup.py
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Start test services**:
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

### Running Tests

#### Basic Commands

```bash
# Run all tests with coverage
make test

# Run only unit tests (fast)
make test-unit

# Run integration tests
make test-integration

# Run tests in Docker (recommended)
make test-docker

# Run all quality checks
make check
```

#### Test Categories

```bash
# By test type
pytest -m "unit"           # Unit tests only
pytest -m "integration"    # Integration tests only
pytest -m "e2e"           # End-to-end tests only
pytest -m "contract"      # Contract tests only
pytest -m "performance"   # Performance tests only
pytest -m "security"      # Security tests only

# By speed
pytest -m "fast"          # Quick tests
pytest -m "slow"          # Slower tests  
pytest -m "not slow"      # Exclude slow tests

# By service
pytest -m "identity"      # Identity service tests
pytest -m "billing"       # Billing service tests
pytest -m "api_gateway"   # API Gateway tests
```

#### Advanced Options

```bash
# Parallel execution
pytest -n auto

# With coverage
pytest --cov --cov-report=html

# Stop on first failure
pytest -x

# Verbose output
pytest -v

# Debug mode
pytest --pdb

# Specific file or test
pytest tests/test_example.py::TestClass::test_method
```

## 📋 Test Types and Examples

### 1. Unit Tests

**Purpose**: Test individual functions/methods in isolation

**Location**: `tests/examples/unit/`

**Example**:
```python
import pytest
from decimal import Decimal
from pydantic import BaseModel, ValidationError

@pytest.mark.unit
@pytest.mark.fast
class TestCustomerModel:
    def test_customer_creation(self, valid_customer_data):
        customer = Customer(**valid_customer_data)
        
        assert customer.email == valid_customer_data['email']
        assert customer.status == CustomerStatus.ACTIVE
        assert isinstance(customer.created_at, datetime)
    
    def test_invalid_email_validation(self, valid_customer_data):
        valid_customer_data['email'] = 'invalid-email'
        
        with pytest.raises(ValidationError) as exc_info:
            Customer(**valid_customer_data)
        
        errors = exc_info.value.errors()
        assert 'email' in str(errors[0]['field'])
```

**Key Patterns**:
- Use `@pytest.mark.unit` and `@pytest.mark.fast`
- Mock external dependencies
- Test both success and failure cases
- Use fixtures for test data
- Focus on single unit of functionality

### 2. Integration Tests

**Purpose**: Test component interactions, databases, external services

**Location**: `tests/examples/integration/`

**Example**:
```python
import pytest
import pytest_asyncio

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
class TestCustomerRepository:
    async def test_create_and_retrieve_customer(self, repository, sample_customer_data):
        # Create customer
        created_customer = await repository.create(sample_customer_data)
        assert created_customer['id'] is not None
        
        # Retrieve customer
        retrieved_customer = await repository.get_by_id(
            created_customer['id'], 
            sample_customer_data['tenant_id']
        )
        
        assert retrieved_customer['email'] == sample_customer_data['email']
    
    async def test_tenant_isolation(self, repository, sample_customer_data):
        # Create customer in tenant 1
        customer = await repository.create(sample_customer_data)
        
        # Try to access from different tenant (should fail)
        result = await repository.get_by_id(customer['id'], 'different-tenant')
        assert result is None
```

**Key Patterns**:
- Use `@pytest.mark.integration`
- Test with real databases/services
- Use async/await for database operations
- Test cross-component interactions
- Verify data persistence and retrieval

### 3. End-to-End Tests

**Purpose**: Test complete user workflows through the API

**Location**: `tests/examples/e2e/`

**Example**:
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
class TestCustomerWorkflow:
    async def test_complete_customer_lifecycle(self, authenticated_client):
        # Create customer
        customer_data = {
            "email": "e2e_test@example.com",
            "first_name": "E2E",
            "last_name": "Test"
        }
        
        response = await authenticated_client.post("/api/v1/customers", json=customer_data)
        assert response.status_code == 201
        customer_id = response.json()['id']
        
        # Retrieve customer
        response = await authenticated_client.get(f"/api/v1/customers/{customer_id}")
        assert response.status_code == 200
        
        # Update customer
        update_data = {"first_name": "Updated"}
        response = await authenticated_client.put(
            f"/api/v1/customers/{customer_id}", 
            json=update_data
        )
        assert response.status_code == 200
        assert response.json()['first_name'] == "Updated"
        
        # Delete customer
        response = await authenticated_client.delete(f"/api/v1/customers/{customer_id}")
        assert response.status_code == 204
```

**Key Patterns**:
- Use `@pytest.mark.e2e`
- Test complete workflows
- Use real HTTP clients
- Test authentication/authorization
- Verify end-user scenarios

### 4. Contract Tests

**Purpose**: Validate API schemas and contracts

**Location**: `tests/examples/contract/`

**Example**:
```python
import pytest
from jsonschema import validate, ValidationError

@pytest.mark.contract
@pytest.mark.asyncio
class TestAPIContracts:
    async def test_customer_response_schema(self, api_client, customer_schema):
        response = await api_client.get("/api/v1/customers/test-id")
        
        if response.status_code == 200:
            # Validate response against schema
            validate(instance=response.json(), schema=customer_schema)
        elif response.status_code in [401, 403, 404]:
            # Validate error response format
            error_data = response.json()
            assert "detail" in error_data or "message" in error_data
```

**Key Patterns**:
- Use `@pytest.mark.contract`
- Validate request/response schemas
- Test API versioning
- Verify error response formats
- Check HTTP headers and status codes

### 5. Performance Tests

**Purpose**: Test system performance and scalability

**Location**: `tests/examples/performance/`

**Example with pytest-benchmark**:
```python
import pytest

@pytest.mark.performance
@pytest.mark.benchmark
class TestPerformance:
    def test_customer_creation_benchmark(self, benchmark, sample_customer_data):
        def create_customer():
            return Customer(**sample_customer_data)
        
        result = benchmark(create_customer)
        assert isinstance(result, Customer)
        
        # Performance assertion
        assert benchmark.stats.mean < 0.001  # Under 1ms
```

**Example with Locust**:
```python
# locustfile.py
from locust import HttpUser, task, between

class CustomerUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def list_customers(self):
        self.client.get("/api/v1/customers")
    
    @task(1)
    def create_customer(self):
        self.client.post("/api/v1/customers", json={
            "email": "load_test@example.com",
            "first_name": "Load",
            "last_name": "Test"
        })
```

**Key Patterns**:
- Use `@pytest.mark.performance`
- Benchmark critical operations
- Test concurrent users with Locust
- Measure response times and throughput
- Set performance thresholds

### 6. Security Tests

**Purpose**: Test security vulnerabilities and compliance

**Location**: `tests/examples/security/`

**Example**:
```python
import pytest

@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityMeasures:
    async def test_sql_injection_prevention(self, api_client, auth_headers):
        # SQL injection payload
        malicious_payload = "'; DROP TABLE customers; --"
        
        response = await api_client.get(
            "/api/v1/customers",
            params={"search": malicious_payload},
            headers=auth_headers
        )
        
        # Should not cause server error
        assert response.status_code != 500
        
        # Payload should not be executed
        response_text = response.text
        assert "DROP TABLE" not in response_text
    
    async def test_authentication_required(self, api_client):
        response = await api_client.get("/api/v1/customers")
        assert response.status_code == 401
```

**Key Patterns**:
- Use `@pytest.mark.security`
- Test authentication/authorization
- Try injection attacks (SQL, XSS, etc.)
- Test rate limiting
- Verify input sanitization

## 🔧 Test Configuration

### pytest Configuration

Located in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov-fail-under=80",
    "--numprocesses=auto",
    "--dist=loadgroup"
]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests - fast, isolated",
    "integration: Integration tests - component interactions",
    "e2e: End-to-end tests - full workflows",
    "contract: API contract tests",
    "performance: Performance and load testing",
    "security: Security testing",
    "fast: Tests that complete in under 1 second",
    "slow: Tests that take more than 5 seconds",
]
```

### Test Fixtures

Global fixtures in `conftest.py`:

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture
async def api_client():
    async with AsyncClient(base_url="http://localhost:8000") as client:
        yield client

@pytest.fixture
def valid_customer_data():
    return {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "tenant_id": "test-tenant"
    }

@pytest_asyncio.fixture
async def db_connection():
    # Set up test database connection
    conn = await create_test_connection()
    yield conn
    await conn.close()
```

## 🐳 Docker Testing Environment

### Starting Test Environment

```bash
# Start full test environment
docker-compose -f docker-compose.test.yml up -d

# Start only databases
docker-compose -f docker-compose.test.yml up -d postgres-test redis-test

# Run tests in Docker
make test-docker
```

### Test Services

The Docker test environment includes:

- **PostgreSQL 16**: Main database with test data
- **Redis 7**: Caching and message queues
- **TimescaleDB**: Analytics database
- **MinIO**: S3-compatible storage
- **Test Runner**: Python environment with all dependencies

### Environment Variables

```bash
# Database URLs
DATABASE_URL=postgresql://dotmac_test:test_password_123@postgres-test:5432/dotmac_test
REDIS_URL=redis://:test_redis_password@redis-test:6379/0

# Test configuration
TESTING=true
ENVIRONMENT=test
LOG_LEVEL=DEBUG
```

## 📊 Quality Gates and Thresholds

### Coverage Requirements

- **Overall Coverage**: ≥80%
- **Unit Test Coverage**: ≥85%
- **Integration Coverage**: ≥75%
- **Branch Coverage**: ≥70%

### Code Quality Gates

- **Linting**: 0 violations (Ruff)
- **Complexity**: Max 10 (McCabe)
- **Security**: 0 vulnerabilities (Bandit)
- **Type Checking**: Gradual adoption (MyPy)

### Performance Thresholds

- **API Response Time**: <2000ms (95th percentile)
- **Database Queries**: <1000ms
- **Error Rate**: <5%
- **Throughput**: >100 RPS

### Quality Gate Check

```bash
# Check all quality gates
python scripts/quality-gate-check.py

# Check for specific environment
python scripts/quality-gate-check.py --environment production
```

## 📈 CI/CD Integration

### GitHub Actions Workflows

1. **Code Quality Pipeline** (`.github/workflows/ci-code-quality.yml`)
   - Linting, formatting, type checking
   - Security scanning
   - Complexity analysis

2. **Test Pipeline** (`.github/workflows/ci-tests.yml`)
   - Unit, integration, E2E tests
   - Coverage reporting
   - Cross-platform testing

3. **Security Pipeline** (`.github/workflows/ci-security.yml`)
   - Vulnerability scanning
   - Dependency checks
   - Security tests

4. **Performance Pipeline** (`.github/workflows/ci-performance.yml`)
   - Load testing with Locust
   - Benchmark comparisons
   - Performance regression detection

5. **Docker Pipeline** (`.github/workflows/ci-docker.yml`)
   - Container builds and testing
   - Security scanning
   - Integration testing

### Workflow Triggers

- **Push to main/develop**: Full test suite
- **Pull requests**: Code quality + unit tests + integration tests
- **Scheduled (daily)**: Performance + security tests
- **Manual**: All tests with custom options

### Quality Gate Enforcement

Tests must pass these gates before deployment:

**Blocking (Must Pass)**:
- All unit tests
- Integration tests
- Code quality checks
- Security scans

**Warning (Can Proceed)**:
- Documentation coverage
- Performance benchmarks
- Dependency freshness

## 📋 Test Reports and Monitoring

### Automated Reporting

```bash
# Generate comprehensive test report
python scripts/generate-test-report.py

# Generate quality gate report  
python scripts/quality-gate-check.py
```

### Report Formats

- **HTML Reports**: Interactive dashboards with charts
- **JSON Reports**: Machine-readable results
- **JUnit XML**: CI/CD integration
- **Coverage Reports**: HTML and XML formats

### Monitoring Dashboard

The test report includes:
- ✅ **Test Results**: Pass/fail rates by category
- 📊 **Coverage Metrics**: Line and branch coverage
- ⚡ **Performance Data**: Response times and throughput
- 🔒 **Security Status**: Vulnerability counts
- 📈 **Trend Analysis**: Historical comparisons

## 🛠️ Development Workflow

### Daily Development

1. **Start development**:
   ```bash
   git pull origin main
   make install-dev
   ```

2. **Before committing**:
   ```bash
   make check  # Run all quality checks
   ```

3. **Before pushing**:
   ```bash
   make ci-test  # Run CI-like tests locally
   ```

### Creating New Tests

1. **Choose appropriate test type**:
   - Unit: Testing isolated functions
   - Integration: Testing with database/services
   - E2E: Testing user workflows
   - Contract: Testing API schemas
   - Performance: Testing speed/load
   - Security: Testing vulnerabilities

2. **Use appropriate markers**:
   ```python
   @pytest.mark.unit
   @pytest.mark.fast
   def test_my_function():
       pass
   ```

3. **Follow naming conventions**:
   - Files: `test_*.py`
   - Classes: `Test*`
   - Functions: `test_*`

4. **Use fixtures for setup**:
   ```python
   @pytest.fixture
   def sample_data():
       return {"key": "value"}
   ```

5. **Write descriptive test names**:
   ```python
   def test_customer_creation_with_valid_data_should_succeed():
       pass
   ```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check if databases are running
docker-compose -f docker-compose.test.yml ps

# Restart databases
docker-compose -f docker-compose.test.yml restart postgres-test redis-test

# Check logs
docker-compose -f docker-compose.test.yml logs postgres-test
```

#### Import Errors
```bash
# Install in development mode
pip install -e .

# Check PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH
```

#### Test Failures
```bash
# Run specific failing test
pytest tests/test_example.py::test_specific -v

# Debug with pdb
pytest --pdb tests/test_example.py::test_specific

# Check test isolation
pytest tests/test_example.py::test_specific --forked
```

#### Async Test Issues
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Use proper async markers
@pytest.mark.asyncio
async def test_async_function():
    pass
```

#### Performance Test Issues
```bash
# Install performance dependencies
pip install pytest-benchmark locust

# Check system resources
htop  # or top on macOS
```

### Getting Help

1. **Check documentation**: `docs/development/`
2. **Run setup script**: `python scripts/dev-setup.py`
3. **Check GitHub Actions**: View CI logs for examples
4. **Use debug mode**: `pytest --pdb -x`
5. **Ask team members**: Create GitHub issue or discussion

## 📚 Additional Resources

### External Documentation

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Locust Documentation](https://locust.io/)
- [Docker Compose](https://docs.docker.com/compose/)
- [GitHub Actions](https://docs.github.com/en/actions)

### Project-Specific

- [`CLAUDE.md`](./CLAUDE.md) - Project overview and commands
- [`Makefile`](./Makefile) - Available make commands
- [`.quality-gates.yml`](./.quality-gates.yml) - Quality gate configuration
- [Test Examples](./tests/examples/) - Comprehensive test examples

---

## 🎉 Conclusion

This testing infrastructure provides enterprise-grade quality assurance with:

- ✅ **Comprehensive Coverage**: All test types covered
- 🔄 **Automated CI/CD**: Continuous quality checking
- 📊 **Quality Gates**: Automated quality enforcement
- 🐳 **Docker Integration**: Consistent test environments
- 📈 **Monitoring**: Detailed reporting and trends
- 🛡️ **Security**: Built-in security testing
- ⚡ **Performance**: Load and benchmark testing

The framework ensures high code quality, reliability, and maintainability while providing excellent developer experience.

**Happy Testing!** 🧪✨