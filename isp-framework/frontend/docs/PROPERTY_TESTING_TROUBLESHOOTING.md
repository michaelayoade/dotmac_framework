# Property-Based Testing Troubleshooting Guide

## UserEvent Issues in Property-Based Tests

### Problem Description

When running property-based tests with React components that simulate user interactions, you may encounter errors like:

```
TypeError: Cannot redefine property: clipboard
    at Function.defineProperty (<anonymous>)
    at Object.attachClipboardStubToView
```

Or:

```
TestingLibraryElementError: Found multiple elements by: [data-testid="customer-id"]
```

### Root Causes

1. **Clipboard Redefinition**: `userEvent.setup()` tries to redefine the `navigator.clipboard` property multiple times within the same test suite
2. **DOM Pollution**: Components from multiple property test runs accumulate in the DOM without proper cleanup
3. **Async/Await Complexity**: Property-based tests run many iterations, and async userEvent operations can interfere with each other

### Solutions Implemented

#### 1. Replace userEvent with fireEvent for Property Tests

**Problem**: userEvent's async nature and clipboard management don't work well with fast-check's multiple test runs.

**Solution**: Use synchronous `fireEvent` for property-based tests:

```typescript
// ❌ Problematic approach
const user = userEvent.setup();
await user.click(submitButton);

// ✅ Working approach  
const submitButton = container.querySelector('[data-testid="submit-payment"]');
fireEvent.click(submitButton);
```

#### 2. Implement Proper DOM Isolation

**Problem**: Multiple component instances accumulate in the DOM across property test runs.

**Solution**: Create isolated containers for each property test run:

```typescript
test('Component handles any valid data', () => {
  fc.assert(
    fc.property(dataArb, (data) => {
      // Create isolated container for each property test run
      const testContainer = document.createElement('div');
      document.body.appendChild(testContainer);
      
      const { container, unmount } = render(
        <Component data={data} />,
        { container: testContainer }
      );
      
      try {
        // Run assertions using container queries instead of screen
        expect(container.querySelector('[data-testid="form"]')).toBeInTheDocument();
      } finally {
        // Clean up this specific test run
        unmount();
        document.body.removeChild(testContainer);
      }
    }),
    { numRuns: 10 }
  );
});
```

#### 3. Use Container Queries Instead of Screen Queries

**Problem**: `screen.getByTestId()` finds elements across all rendered components in the DOM.

**Solution**: Use container-specific queries:

```typescript
// ❌ Finds elements across all components
expect(screen.getByTestId('customer-id')).toBeInTheDocument();

// ✅ Finds elements only in this specific component  
expect(container.querySelector('[data-testid="customer-id"]')).toBeInTheDocument();
```

#### 4. Enhanced Cleanup Strategy

**Solution**: Implement comprehensive cleanup between tests:

```typescript
afterEach(() => {
  // Clean up after each test to prevent interference
  cleanup();
  jest.clearAllMocks();
  
  // Clear DOM to prevent component state bleeding between property test runs
  document.body.innerHTML = '';
});
```

#### 5. Configure Jest for Property-Based Tests

Create dedicated Jest project configuration:

```javascript
// jest.config.js
{
  displayName: 'Property-Based Tests',
  testMatch: [
    '<rootDir>/**/__tests__/**/*property*.test.[jt]s?(x)',
    '<rootDir>/**/*scenario*.test.[jt]s?(x)'
  ],
  setupFilesAfterEnv: ['<rootDir>/jest-setup.js', '<rootDir>/jest-property-setup.js'],
  testTimeout: 30000, // Property tests can take longer
}
```

### Best Practices for Property-Based Component Tests

#### 1. Reduce Test Runs for Development

```typescript
// Development - faster feedback
{ numRuns: 10 }

// CI/CD - comprehensive testing  
{ numRuns: 100 }
```

#### 2. Use Synchronous Operations When Possible

```typescript
// ✅ Fast and reliable
fireEvent.change(input, { target: { value: 'test' } });
fireEvent.click(button);

// ❌ Slow and can cause issues in property tests
await user.type(input, 'test');
await user.click(button);
```

#### 3. Implement Custom Property Test Utilities

```typescript
// Utility for safe component rendering in property tests
const renderInIsolation = (component: ReactElement) => {
  const testContainer = document.createElement('div');
  document.body.appendChild(testContainer);
  
  const result = render(component, { container: testContainer });
  
  return {
    ...result,
    cleanup: () => {
      result.unmount();
      document.body.removeChild(testContainer);
    }
  };
};

// Usage
const { container, cleanup } = renderInIsolation(<MyComponent />);
try {
  // Run tests
} finally {
  cleanup();
}
```

#### 4. Filter Out NaN Values in Arbitraries

```typescript
// ✅ Prevents NaN-related errors
const amountArb = fc.double({ 
  min: 0.01, 
  max: 999.99, 
  noNaN: true 
});
```

### Running Property-Based Tests

```bash
# Run only property-based tests
pnpm test -- --selectProjects="Property-Based Tests"

# Run with single worker to prevent interference
pnpm test -- --testPathPattern="property" --maxWorkers=1

# Run specific property test file  
pnpm test -- payment-calculations.property.test.ts
```

### Debugging Property Test Failures

1. **Enable Verbose Mode**: See the exact values that cause failures
   ```typescript
   fc.assert(fc.property(arb, test), { 
     verbose: true,
     numRuns: 10 
   });
   ```

2. **Add Notes**: Track test execution
   ```typescript
   fc.property(arb, (data) => {
     fc.pre(data.amount > 0); // Add preconditions
     note(`Testing with: ${JSON.stringify(data)}`);
     // ... test logic
   });
   ```

3. **Use Smaller Test Sets**: For development debugging
   ```typescript
   { numRuns: 5 } // Minimal runs for debugging
   ```

### When to Use Each Approach

| Test Type | Use fireEvent | Use userEvent | Notes |
|-----------|---------------|---------------|-------|
| Property-Based | ✅ | ❌ | Fast-check + userEvent = problems |
| Unit Tests | Either | ✅ | userEvent provides better simulation |
| Integration | Either | ✅ | More realistic user interactions |
| E2E | N/A | N/A | Use Playwright instead |

### Summary

The key to successful property-based component testing is:

1. **Use fireEvent instead of userEvent** for property-based tests
2. **Isolate each test run** with dedicated DOM containers
3. **Clean up aggressively** between tests
4. **Use container queries** instead of screen queries
5. **Reduce test runs** during development for faster feedback

These solutions resolve the clipboard redefinition errors and DOM pollution issues that commonly occur when running property-based tests with React components.