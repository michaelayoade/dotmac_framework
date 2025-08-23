# Frontend Testing Suite

This directory contains comprehensive tests for the DotMac Framework frontend,
following the same patterns as the backend testing architecture.

## Test Structure

```
tests/
├── unit/                    # Fast unit tests
│   ├── components/          # Component unit tests
│   ├── hooks/              # Custom hooks tests
│   ├── utils/              # Utility function tests
│   └── config/             # Configuration tests
├── integration/            # Integration tests with APIs/external services
│   ├── api/                # API integration tests
│   ├── auth/               # Authentication flow tests
│   └── portal/             # Portal-specific integration tests
├── e2e/                    # End-to-end tests
│   ├── customer/           # Customer portal E2E tests
│   ├── admin/              # Admin portal E2E tests
│   └── reseller/           # Reseller portal E2E tests
├── performance/            # Performance and load tests
├── visual/                 # Visual regression tests
├── accessibility/          # Comprehensive accessibility tests
├── contracts/              # API contract tests
└── fixtures/               # Test data and fixtures
```

## Test Types

### Unit Tests

- Component rendering and behavior
- Custom hooks functionality
- Utility functions
- Configuration systems
- Business logic

### Integration Tests

- API interactions
- Authentication flows
- State management
- Error handling
- Loading states

### E2E Tests

- Complete user workflows
- Cross-browser compatibility
- Portal-specific features
- Multi-tenant scenarios

### Performance Tests

- Bundle size limits
- Core Web Vitals
- Render performance
- Memory leaks

### Visual Regression Tests

- Component visual consistency
- Theme variations
- Responsive design
- Portal branding

### Accessibility Tests

- WCAG compliance
- Keyboard navigation
- Screen reader compatibility
- Color contrast

## Running Tests

```bash
# All tests
pnpm test

# Unit tests only
pnpm test:unit

# Integration tests
pnpm test:integration

# E2E tests
pnpm test:e2e

# Accessibility tests
pnpm test:a11y

# Visual regression tests
pnpm test:visual

# Performance tests
pnpm test:perf

# With coverage
pnpm test:coverage

# Watch mode
pnpm test:watch
```

## Test Configuration

### Coverage Thresholds

- Statements: 80%
- Branches: 75%
- Functions: 80%
- Lines: 80%

### Test Markers

- `@unit` - Fast unit tests
- `@integration` - Tests requiring external services
- `@e2e` - End-to-end tests
- `@slow` - Tests that take >5 seconds
- `@visual` - Visual regression tests
- `@a11y` - Accessibility tests

## Best Practices

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Factories**: Consistent test data creation
3. **Mock External Services**: Keep tests isolated
4. **Test Behavior**: Focus on what users see/do
5. **Descriptive Names**: Clear test descriptions
6. **Parallel Execution**: Fast test runs
7. **Clean State**: Each test runs independently

## Test Utilities

### Render Helpers

```js
import { renderWithProviders } from '@/test-utils';

renderWithProviders(<Component />, {
  user: testUtils.createMockUser(),
  config: testUtils.createMockConfig(),
});
```

### Factory Helpers

```js
const customer = testUtils.factories.customer({
  plan: 'enterprise',
  status: 'active',
});
```

### API Mocking

```js
import { server } from '@/__mocks__/server';
import { http, HttpResponse } from 'msw';

// Custom endpoint for test
server.use(
  http.get('/api/customers', () => {
    return HttpResponse.json({ data: [customer] });
  })
);
```

## Continuous Integration

Tests run automatically on:

- Pull requests
- Pushes to main/develop
- Nightly schedules (E2E and visual tests)

### Test Reports

- Coverage reports uploaded to Codecov
- Test results in GitHub Actions
- Visual diff reports for UI changes
- Performance metrics tracking
