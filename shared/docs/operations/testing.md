# Testing Guide - DotMac Frontend

## Overview

The DotMac Frontend uses a comprehensive testing strategy with multiple layers of testing to ensure reliability, accessibility, and performance.

## Testing Architecture

### Testing Pyramid
- **70% Unit Tests** - Fast, isolated component and utility tests
- **20% Integration Tests** - Cross-component and API integration tests  
- **10% E2E Tests** - Full user workflow testing across browsers

### Test Types

#### 1. Unit Tests
```bash
# Run all unit tests
pnpm test:unit

# Run unit tests with coverage
pnpm test:coverage

# Run unit tests in watch mode
pnpm test:watch
```

**What they test:**
- Individual React components
- Utility functions and hooks
- Business logic
- Component rendering and interactions

**Technologies:**
- Jest + React Testing Library
- MSW (Mock Service Worker) for API mocking
- jest-axe for basic accessibility testing

#### 2. Integration Tests
```bash
# Run integration tests
pnpm test:integration

# Run integration tests with services
pnpm test:integration --verbose
```

**What they test:**
- Component interactions
- API integration flows
- Cross-component state management
- Data flow between components

**Technologies:**
- Jest + React Testing Library
- MSW for API mocking
- Real API endpoints (when available)

#### 3. Accessibility Tests
```bash
# Run accessibility tests
pnpm test:a11y

# Run accessibility audit
pnpm a11y:audit
```

**What they test:**
- WCAG compliance
- Keyboard navigation
- Screen reader compatibility
- Color contrast
- Focus management

**Technologies:**
- jest-axe for automated accessibility testing
- @axe-core/playwright for E2E accessibility tests
- Manual testing guidelines

#### 4. E2E Tests
```bash
# Run E2E tests
pnpm test:e2e

# Run E2E tests with UI
pnpm test:e2e:ui

# Run E2E tests in headed mode
pnpm test:e2e:headed

# Debug E2E tests
pnpm test:e2e:debug
```

**What they test:**
- Complete user workflows
- Cross-browser compatibility
- Real user interactions
- Performance metrics

**Technologies:**
- Playwright
- Real browsers (Chromium, Firefox, WebKit)
- Visual regression testing
- Performance monitoring

#### 5. Visual Regression Tests
```bash
# Run visual tests
pnpm test:visual

# Update visual snapshots
pnpm test:visual --update-snapshots
```

**What they test:**
- UI consistency across themes
- Responsive design
- Component visual appearance
- Layout stability

#### 6. Performance Tests
```bash
# Run performance tests
pnpm test:perf

# Analyze bundle size
pnpm bundle:analyze
```

**What they test:**
- Bundle size optimization
- Core Web Vitals
- Loading performance
- Runtime performance

## CI/CD Integration

### Test Commands for CI
```bash
# CI-optimized test run (fails on snapshot changes)
pnpm test:ci

# All tests with coverage
pnpm test:all
```

### Snapshot Policy
- **Development**: Snapshots can be updated with `--update-snapshots`
- **CI**: Snapshot changes cause build failure
- **Review**: New snapshots must be reviewed before merge

## Coverage Requirements

### Current Thresholds
- **Statements**: 85%
- **Branches**: 80%
- **Functions**: 85%
- **Lines**: 85%

### Coverage Reports
- HTML report: `frontend/coverage/lcov-report/index.html`
- JSON summary: `frontend/coverage/coverage-summary.json`
- LCOV format: `frontend/coverage/lcov.info`

## Mock Service Worker (MSW)

### API Mocking
MSW provides consistent API mocking across all test types:

```javascript
// Example test with MSW
import { server } from '__mocks__/server';
import { http, HttpResponse } from 'msw';

test('handles API error gracefully', async () => {
  // Override default handler
  server.use(
    http.get('/api/v1/customers', () => {
      return HttpResponse.json(
        { error: 'Internal server error' },
        { status: 500 }
      );
    })
  );

  // Test component behavior with error state
});
```

### Available Mock Endpoints
- Authentication: `/api/v1/auth/*`
- Customers: `/api/v1/customers/*`
- Services: `/api/v1/services/*`
- Billing: `/api/v1/billing/*`
- Analytics: `/api/v1/analytics/*`
- Configuration: `/api/v1/config`

## Test Organization

### File Structure
```
frontend/
├── __tests__/                 # Global test utilities
├── __mocks__/                 # Mock files
│   ├── server.js             # MSW server setup
│   └── fileMock.js           # File/asset mocks
├── apps/*/                   # App-specific tests
│   └── src/**/__tests__/     # Component tests
├── packages/*/               # Package-specific tests
│   └── src/**/__tests__/     # Component/utility tests
├── tests/                    # Cross-cutting test suites
│   ├── e2e/                  # E2E test scenarios
│   ├── integration/          # Integration test suites
│   ├── visual/               # Visual regression tests
│   └── unit/                 # Shared unit test utilities
└── test-utils/              # Test helper utilities
```

### Naming Conventions
- **Unit tests**: `*.test.[jt]s?(x)`
- **Integration tests**: `*.integration.test.[jt]s?(x)`
- **E2E tests**: `*.e2e.test.[jt]s?(x)`
- **Accessibility tests**: `*.a11y.test.[jt]s?(x)`
- **Visual tests**: `*.visual.test.[jt]s?(x)`

## Test Configuration Files

### Jest Configuration
- `jest.config.js` - Main Jest configuration with projects
- `jest-setup.js` - Global test setup and mocks
- `jest-global-setup.js` - Global setup before all tests
- `jest-global-teardown.js` - Global cleanup after all tests
- `jest-integration-setup.js` - Integration test specific setup
- `jest-a11y-setup.js` - Accessibility test setup

### Playwright Configuration
- `playwright.config.ts` - Playwright configuration
- `tests/e2e/global-setup.ts` - E2E global setup
- `tests/e2e/global-teardown.ts` - E2E global teardown

## Writing Tests

### Unit Test Example
```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../Button';

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### Integration Test Example
```javascript
import { render, screen, waitFor } from '@testing-library/react';
import { server } from '__mocks__/server';
import { CustomerDashboard } from '../CustomerDashboard';

describe('Customer Dashboard Integration', () => {
  it('loads and displays customer data', async () => {
    render(<CustomerDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Test Customer')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Enterprise Plan')).toBeInTheDocument();
    expect(screen.getByText('$299.99/month')).toBeInTheDocument();
  });
});
```

### E2E Test Example
```javascript
import { test, expect } from '@playwright/test';

test('customer can view billing information', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', 'customer@test.com');
  await page.fill('[data-testid="password"]', 'password123');
  await page.click('[data-testid="login-button"]');

  await page.click('[data-testid="billing-nav"]');
  await expect(page).toHaveURL(/.*\/billing/);
  
  await expect(page.getByText('Current Balance')).toBeVisible();
  await expect(page.getByText('Next Bill Date')).toBeVisible();
});
```

### Accessibility Test Example
```javascript
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { LoginForm } from '../LoginForm';

expect.extend(toHaveNoViolations);

describe('LoginForm Accessibility', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(<LoginForm />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

## Debugging Tests

### Jest Debugging
```bash
# Debug specific test
node --inspect-brk node_modules/.bin/jest --runInBand your-test.test.js

# Debug with Chrome DevTools
pnpm test --inspect-brk --runInBand
```

### Playwright Debugging
```bash
# Debug mode with browser UI
pnpm test:e2e:debug

# Headed mode (see browser)
pnpm test:e2e:headed

# Trace viewer
pnpm playwright show-trace trace.zip
```

## Performance Considerations

### Test Performance
- Use `maxWorkers: '50%'` for optimal CI performance
- Avoid slow selectors in E2E tests
- Use `screen.getByRole()` over `container.querySelector()`
- Mock heavy dependencies in unit tests

### Bundle Impact
- Keep test utilities tree-shakeable
- Use dynamic imports for test-only code
- Monitor test bundle size with `bundle:analyze`

## Troubleshooting

### Common Issues

#### MSW Server Not Starting
```bash
# Check server setup in jest-setup.js
# Ensure server.listen() is called in beforeAll()
```

#### Async Test Timeouts
```javascript
// Increase timeout for slow operations
await waitFor(() => {
  expect(element).toBeInTheDocument();
}, { timeout: 10000 });
```

#### Visual Test Failures
```bash
# Update visual baselines
pnpm test:visual --update-snapshots

# Check for theme/viewport differences
```

#### Coverage Thresholds
```bash
# Check specific file coverage
pnpm test:coverage --collectCoverageFrom="**/Button.tsx"

# Exclude files from coverage
# Add to jest.config.js collectCoverageFrom
```

## Best Practices

### Testing Guidelines
1. **Write tests first** (TDD approach preferred)
2. **Test behavior, not implementation**
3. **Use data-testid for stable selectors**
4. **Mock external dependencies**
5. **Keep tests independent and isolated**
6. **Use descriptive test names**
7. **Test error states and edge cases**

### Accessibility Testing
1. **Include axe tests for all components**
2. **Test keyboard navigation manually**
3. **Verify screen reader announcements**
4. **Check color contrast in visual tests**
5. **Test with assistive technologies**

### E2E Testing
1. **Focus on critical user journeys**
2. **Use Page Object Model pattern**
3. **Test across different browsers**
4. **Include mobile viewports**
5. **Monitor Core Web Vitals**

### CI/CD Integration
1. **Use `--ci` flag in CI environments**
2. **Fail builds on snapshot changes**
3. **Upload test artifacts for debugging**
4. **Generate test reports for stakeholders**
5. **Monitor test execution time**

## Mutation Testing (Future)

The project roadmap includes mutation testing with Stryker:

```bash
# Future command (not yet implemented)
pnpm test:mutation

# Target mutation score: >60%
```

This will help identify gaps in test coverage by introducing code mutations and verifying that tests fail appropriately.

---

## Quick Reference

### Daily Commands
```bash
# Run tests during development
pnpm test:watch

# Run tests before commit
pnpm test:coverage

# Run full test suite
pnpm test:all

# Check accessibility
pnpm a11y:audit
```

### CI Commands
```bash
# CI test run
pnpm test:ci

# Lint and test
pnpm lint && pnpm test:ci

# Visual tests
pnpm test:visual
```

### Debugging
```bash
# Debug failing test
pnpm test:e2e:debug

# Trace analysis
pnpm playwright show-trace

# Coverage analysis
pnpm test:coverage:open
```

This comprehensive testing setup ensures the DotMac Frontend maintains high quality, performance, and accessibility standards while providing rapid feedback to developers and stakeholders.