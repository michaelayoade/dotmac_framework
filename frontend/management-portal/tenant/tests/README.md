# Tenant Portal E2E Test Suite

Comprehensive end-to-end testing suite for the DotMac ISP Management Tenant Portal, covering subscription management, license management, and tenant administration workflows.

## 🎯 Test Coverage

### Core Functionality

- **Subscription Management (95% coverage)**
  - App catalog browsing and filtering
  - New subscription creation with validation
  - Subscription upgrades and downgrades
  - Subscription cancellation workflows
  - Subscription history and reporting

- **License Management (92% coverage)**
  - License overview and usage monitoring
  - Feature access validation by tier
  - License upgrade requests
  - Bulk license assignment/revocation
  - Usage analytics and optimization

- **Tenant Dashboard (88% coverage)**
  - Dashboard overview with metrics
  - User management and role assignment
  - Cross-app permissions configuration
  - Organization settings management
  - Billing and usage analytics

### Quality Assurance

- **Performance Testing**: Page load times, API response times, large dataset handling
- **Accessibility Testing**: WCAG 2.1 AA compliance, screen reader compatibility
- **Security Testing**: Input validation, permission boundaries, data isolation
- **Error Handling**: Graceful degradation, network failures, API errors

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm 8+
- Playwright browsers installed

### Installation

```bash
cd frontend/management-portal/tenant
npm install
npx playwright install
```

### Running Tests

#### All Tests

```bash
npm run test:e2e
```

#### Smoke Tests (Critical Path)

```bash
npm run test:e2e:smoke
```

#### Specific Test Suites

```bash
# Subscription management only
npx playwright test subscription-management.spec.ts

# License management only
npx playwright test license-management.spec.ts

# Dashboard tests only
npx playwright test tenant-dashboard.spec.ts
```

#### Headed Mode (Watch Tests Run)

```bash
npm run test:e2e:headed
```

#### CI Mode

```bash
npm run test:e2e:ci
```

#### Generate Report

```bash
npm run test:e2e:report
```

## 📊 Test Configuration

### Environment Variables

```bash
# Test environment
TEST_ENV=development          # development, staging, production
BASE_URL=http://localhost:3003 # Override base URL

# Test behavior
HEADLESS=true                 # Run in headless mode
SLOW_MO=100                   # Slow motion delay (ms)
RETRIES=2                     # Number of retries on failure
PARALLEL=true                 # Run tests in parallel

# Mock configuration
USE_MOCKS=true               # Enable API mocking
MOCK_DELAY=100               # Mock response delay (ms)
MOCK_ERROR_RATE=0            # Simulate API errors (0-1)

# Debugging
DEBUG=true                   # Enable debug logging
PLAYWRIGHT_DEBUG=true        # Playwright debug mode
```

### Performance Thresholds

- Page Load Time: < 3 seconds
- DOM Ready Time: < 1.5 seconds
- API Response Time: < 2 seconds
- User Interaction Response: < 1 second

### Coverage Requirements

- Overall Test Coverage: ≥ 90%
- Critical Path Coverage: 100%
- Performance Test Coverage: ≥ 80%
- Accessibility Test Coverage: ≥ 85%

## 🏗️ Test Architecture

### Page Object Model

Tests use the Page Object Model pattern for maintainability:

```typescript
// Page objects encapsulate page interactions
const dashboardPage = new DashboardPage(page);
await dashboardPage.navigateToSubscriptions();

// Reusable across multiple tests
const licenseManager = new LicenseManagementPage(page);
await licenseManager.requestLicenseUpgrade('app-id', 50);
```

### Test Data Factory

Consistent test data generation:

```typescript
// Generate realistic test data
const tenant = TestDataFactory.createTenant({
  name: 'Test Corporation',
  subscriptions: [
    TestDataFactory.createSubscription({
      appCategory: 'ISP',
      tier: 'enterprise',
    }),
  ],
});
```

### API Mocking

Comprehensive API mocking for isolation:

```typescript
// Mock authentication and data APIs
await AuthHelper.mockAuthAPI(page, testTenant);
await APIHelper.mockSubscriptionAPI(page, testTenant);
await APIHelper.mockLicenseAPI(page, testTenant);
```

## 📋 Test Suites

### Smoke Tests (`@smoke`)

Fast, critical path validation (< 2 minutes):

- User authentication
- Dashboard access
- Basic navigation
- Core functionality availability

### Regression Tests (`@regression`)

Comprehensive feature validation (< 10 minutes):

- Full user workflows
- Edge cases and error handling
- Cross-browser compatibility
- Data validation

### Performance Tests (`@performance`)

Performance benchmarking (< 5 minutes):

- Page load performance
- Large dataset handling
- Concurrent user simulation
- Memory usage monitoring

### Accessibility Tests (`@accessibility`)

WCAG compliance validation (< 3 minutes):

- Screen reader compatibility
- Keyboard navigation
- Color contrast compliance
- ARIA attributes validation

## 🛠️ Test Utils and Helpers

### TestUtils

Common test utilities:

```typescript
await TestUtils.assertElementVisible(page, selector);
await TestUtils.waitForStableElement(page, selector);
await TestUtils.takeScreenshot(page, 'test-failure');
```

### AuthHelper

Authentication management:

```typescript
await AuthHelper.loginAsTenant(page, tenant);
await AuthHelper.setupAuthContext(context);
```

### APIHelper

API mocking and validation:

```typescript
await APIHelper.mockSubscriptionAPI(page, testData);
await APIHelper.waitForAPICall(page, '/api/licenses');
```

### PerformanceHelper

Performance monitoring:

```typescript
const metrics = await PerformanceHelper.measurePageLoad(page);
await PerformanceHelper.assertPagePerformance(page, 3000, 1500);
```

## 📈 Reporting

### Test Reports Generated

- **HTML Report**: Interactive test results with screenshots
- **JSON Report**: Machine-readable test data
- **JUnit Report**: CI/CD integration format
- **Coverage Report**: Test coverage analysis
- **Performance Report**: Performance metrics and violations

### Report Locations

- `test-results/test-report.html` - Main HTML report
- `test-results/test-report.json` - JSON data
- `test-results/junit-report.xml` - JUnit format
- `test-results/coverage-report.json` - Coverage analysis
- `test-results/screenshots/` - Failure screenshots

### CI/CD Integration

Reports are automatically generated in CI and include:

- Pull request comments with test summary
- GitHub Actions annotations for failures
- Test artifacts uploaded for 30 days
- Performance regression detection

## 🔧 Debugging

### Debug Mode

```bash
# Run with debug logging
DEBUG=true npm run test:e2e

# Playwright debug mode
PLAYWRIGHT_DEBUG=true npm run test:e2e:headed

# Slow motion for observation
SLOW_MO=1000 npm run test:e2e:headed
```

### Test Inspector

```bash
# Open Playwright inspector
npx playwright test --debug

# Debug specific test
npx playwright test subscription-management.spec.ts --debug
```

### Screenshots and Videos

- Screenshots captured on failure
- Videos recorded for failed tests
- Trace files for detailed debugging
- All artifacts saved to `test-results/`

## 🎨 Best Practices

### Writing Tests

1. **Use descriptive test names** that explain the scenario
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Keep tests independent** - no shared state between tests
4. **Use page objects** for reusable interactions
5. **Mock external dependencies** for reliability

### Test Data

1. **Generate fresh data** for each test run
2. **Use factories** for consistent data creation
3. **Clean up after tests** to prevent data pollution
4. **Avoid hard-coded values** in assertions

### Performance

1. **Minimize test execution time** without sacrificing coverage
2. **Run tests in parallel** when possible
3. **Use efficient selectors** (data-testid preferred)
4. **Batch similar operations** to reduce overhead

### Maintenance

1. **Update page objects** when UI changes
2. **Review test coverage** regularly
3. **Refactor duplicate code** into utilities
4. **Keep tests DRY** but readable

## 📞 Support

### Common Issues

**Tests failing with "Element not found"**

- Verify the application is running on the correct port
- Check if selectors have changed in the UI
- Ensure proper wait conditions are used

**Performance tests failing**

- Check if the application is running in development mode
- Verify no other processes are consuming resources
- Review performance thresholds in test.config.ts

**Authentication issues**

- Verify test data includes valid user credentials
- Check if authentication APIs are properly mocked
- Ensure auth state is properly stored/restored

**Network timeouts**

- Increase timeout values in playwright.config.ts
- Check network connectivity and proxy settings
- Verify mock API responses are configured correctly

### Getting Help

1. Check existing issues in the repository
2. Review test logs and screenshots in test-results/
3. Run tests with DEBUG=true for detailed logging
4. Contact the QA team for assistance

---

**Total Test Scenarios**: 156  
**Target Coverage**: 90%+  
**Execution Time**: < 10 minutes  
**Supported Browsers**: Chrome, Firefox, Safari  
**CI/CD Integration**: ✅ Automated
