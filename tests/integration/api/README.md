# DotMac Framework API Test Suite

This directory contains comprehensive integration tests for the DotMac ISP Framework API endpoints.

## Test Structure

### Core Test Files

- **`test_auth_flows.py`** - Authentication and authorization testing
  - JWT token creation, validation, and expiration
  - Login/logout workflows
  - Session management and security
  - Multi-tenant authentication
  - Token tampering prevention

- **`test_crud_operations.py`** - CRUD operations for all entities
  - Customer management (create, read, update, list)
  - Service plans (create, read, list with filters)
  - Service instances (activation, status updates, lifecycle)
  - Usage data recording and retrieval
  - Bulk operations

- **`test_error_handling.py`** - Comprehensive error scenario testing
  - HTTP status codes (400, 401, 403, 404, 422, 429, 500, 503)
  - Input validation errors
  - Database constraint violations
  - Business logic validation
  - Security error prevention
  - Exception handling middleware

- **`test_rate_limiting_security.py`** - Security and abuse prevention
  - Rate limiting enforcement
  - Authentication security measures
  - Input validation security (SQL injection, XSS prevention)
  - API abuse prevention (payload limits, concurrent requests)
  - Security headers validation

- **`test_complete_workflows.py`** - End-to-end business workflows
  - Complete customer onboarding
  - Service lifecycle management
  - Bulk operations workflows
  - Multi-tenant isolation
  - Error recovery and rollback

## Test Utilities

### `../utils/api_test_helpers.py`
Provides mock services, test data factories, and testing utilities:

- **MockAuthService** - Authentication service mock
- **MockCustomerService** - Customer service mock  
- **MockServicesService** - Services service mock
- **TestDataFactory** - Creates consistent test data
- **APITestClient** - Enhanced test client with auth helpers
- **DatabaseTestHelper** - Database testing utilities

### `../conftest_api.py`
Extended pytest configuration for API testing:

- Pre-configured FastAPI test application
- Mock dependency injection
- Authentication fixtures
- Test data fixtures
- Custom pytest markers

## Running the Tests

### All API Tests
```bash
# Run all API integration tests
pytest tests/integration/api/ -v

# Run with coverage
pytest tests/integration/api/ --cov=src/dotmac_isp --cov-report=html

# Run specific test categories
pytest tests/integration/api/ -m "auth" -v
pytest tests/integration/api/ -m "crud" -v  
pytest tests/integration/api/ -m "security" -v
```

### Individual Test Files
```bash
# Authentication tests
pytest tests/integration/api/test_auth_flows.py -v

# CRUD operation tests
pytest tests/integration/api/test_crud_operations.py -v

# Error handling tests  
pytest tests/integration/api/test_error_handling.py -v

# Security and rate limiting tests
pytest tests/integration/api/test_rate_limiting_security.py -v

# Complete workflow tests
pytest tests/integration/api/test_complete_workflows.py -v
```

### Performance Testing
```bash
# Run with performance benchmarks
pytest tests/integration/api/ --benchmark-only

# Slow tests (marked with @pytest.mark.slow)
pytest tests/integration/api/ -m "slow" -v
```

## Test Categories (Markers)

Tests are organized with pytest markers for easy filtering:

- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.crud` - CRUD operation tests  
- `@pytest.mark.error` - Error handling tests
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.rate_limit` - Rate limiting tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Long-running tests

## Test Coverage

The API test suite covers:

### Authentication & Authorization
- ✅ JWT token lifecycle (creation, validation, expiration)
- ✅ Login/logout workflows
- ✅ Session management and security
- ✅ Multi-tenant authentication isolation
- ✅ Token tampering and replay attack prevention
- ✅ Permission-based access control

### CRUD Operations  
- ✅ Customer management (all operations)
- ✅ Service plan management
- ✅ Service instance lifecycle
- ✅ Usage data recording and retrieval
- ✅ Bulk operations with partial failure handling

### Error Handling
- ✅ All HTTP status codes (400-500 range)
- ✅ Input validation and data type errors
- ✅ Database constraint violations
- ✅ Business logic validation errors
- ✅ Security error prevention
- ✅ Exception handling middleware

### Security & Rate Limiting
- ✅ Rate limiting enforcement per user/endpoint
- ✅ Authentication security measures
- ✅ SQL injection prevention
- ✅ XSS prevention in responses  
- ✅ API abuse prevention (payload limits, concurrent requests)
- ✅ Security headers validation
- ✅ Information disclosure prevention

### Business Workflows
- ✅ Complete customer onboarding
- ✅ Service lifecycle management (activation → active → suspended → cancelled)
- ✅ Bulk service operations
- ✅ Multi-tenant data isolation
- ✅ Error recovery and transaction rollback

## Configuration

### Test Environment Variables
```bash
export ENVIRONMENT=testing
export DATABASE_URL=sqlite:///test.db
export REDIS_URL=redis://localhost:6379/15
export JWT_SECRET_KEY=test-secret-key-for-testing-only-32-chars-min
```

### Test Database
Tests use mocked database services by default. For integration with real databases:

1. Set up test database
2. Update `DATABASE_URL` environment variable
3. Run migrations: `alembic upgrade head`

### Mock Services
All API tests use mock services by default for:
- Consistent test data
- Fast execution
- Isolation from external dependencies
- Predictable behavior

To test against real services, update the dependency injection in test fixtures.

## Best Practices

### Writing New API Tests
1. Use existing mock services and test data factories
2. Follow the existing test structure and naming conventions
3. Add appropriate pytest markers
4. Include both success and error scenarios
5. Test tenant isolation where applicable
6. Verify response structure and status codes

### Test Data Management
- Use `TestDataFactory` for consistent test data
- Avoid hardcoded UUIDs or dates
- Clean up test data after each test
- Use tenant-specific test data for isolation testing

### Error Testing
- Test all relevant HTTP status codes
- Verify error response format consistency
- Test edge cases and boundary conditions
- Ensure security errors don't leak sensitive information

### Performance Considerations
- Mark slow tests with `@pytest.mark.slow`
- Use mocks for external API calls
- Batch similar test operations
- Monitor test execution time

## Troubleshooting

### Common Issues
1. **Import errors** - Ensure PYTHONPATH includes src directory
2. **Authentication failures** - Check JWT_SECRET_KEY environment variable
3. **Database errors** - Verify test database connection and migrations
4. **Mock failures** - Update mock services when API changes

### Debug Mode
```bash
# Run with verbose output and no capture
pytest tests/integration/api/ -v -s

# Run single test with debugging
pytest tests/integration/api/test_auth_flows.py::TestAuthenticationFlows::test_login_success -v -s --pdb
```

### Test Data Inspection
Enable test data logging in conftest.py for debugging test failures.