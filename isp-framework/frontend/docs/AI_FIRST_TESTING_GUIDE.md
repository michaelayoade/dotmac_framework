# AI-First Testing Guide for Frontend

## Overview

This guide explains how to implement and maintain the AI-first testing strategy in the DotMac ISP Framework frontend. Unlike traditional testing that focuses on code coverage, our approach prioritizes business outcomes, mathematical correctness, and revenue protection.

## Philosophy

### Traditional Testing vs. AI-First Testing

| Aspect | Traditional Testing | AI-First Testing |
|--------|-------------------|------------------|
| **Focus** | Code Coverage (85%) | Business Outcomes |
| **Test Data** | Hardcoded fixtures | AI-generated scenarios |
| **Edge Cases** | Manually identified | Automatically discovered |
| **Validation** | Mock assertions | Mathematical properties |
| **Revenue Safety** | Hope for the best | Mathematical guarantees |

### AI-First Principles

1. **Property-Based Testing**: Define mathematical properties that must always hold
2. **AI-Generated Scenarios**: Use fast-check to generate thousands of test cases
3. **Business Rule Enforcement**: Test ISP-specific constraints, not just code paths
4. **Revenue Protection**: Ensure payment calculations are mathematically correct
5. **Security Invariants**: Validate input sanitization and injection prevention

## Test Architecture

### Project Structure

```
frontend/
├── packages/headless/src/
│   ├── __tests__/
│   │   ├── property-based/          # Property-based tests
│   │   │   └── *.property.test.ts
│   │   ├── ai-scenarios/            # AI-generated component scenarios
│   │   │   └── *.scenario.test.tsx
│   │   └── traditional/             # Traditional unit tests (legacy)
│   │       └── *.test.ts
│   └── hooks/
│       └── payment/
├── scripts/
│   └── ai-safety-frontend-pipeline.js  # AI safety validation pipeline
└── jest.config.js                      # Multi-project Jest configuration
```

### Test Types

#### 1. Property-Based Tests (`*.property.test.ts`)

Test mathematical properties that must always hold, regardless of input:

```typescript
import fc from 'fast-check';

describe('Payment Calculation Properties', () => {
  test('Tax calculation is always mathematically correct', () => {
    fc.assert(
      fc.property(
        fc.record({
          amount: fc.double({ min: 9.99, max: 999.99 }),
          taxRate: fc.double({ min: 0.0, max: 0.30 }),
        }),
        (payment) => {
          const result = calculateTax(payment.amount, payment.taxRate);
          
          // Property: Tax amount equals amount * tax rate
          const expected = payment.amount * payment.taxRate;
          expect(Math.abs(result - expected)).toBeLessThan(0.01);
          
          // Property: Tax is never negative
          expect(result).toBeGreaterThanOrEqual(0);
        }
      ),
      { numRuns: 1000 } // Generate 1000 test cases
    );
  });
});
```

#### 2. AI-Generated Component Scenarios (`*.scenario.test.tsx`)

Test React components with AI-generated user interactions:

```typescript
import fc from 'fast-check';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('Billing Component AI Scenarios', () => {
  test('Component handles any valid billing data', () => {
    fc.assert(
      fc.property(billingDataArb, (billingData) => {
        render(<BillingComponent data={billingData} />);
        
        // Property: All form fields should be present
        expect(screen.getByTestId('customer-id')).toBeInTheDocument();
        expect(screen.getByDisplayValue(billingData.customerId)).toBeInTheDocument();
      }),
      { numRuns: 100 }
    );
  });
});
```

#### 3. AI Safety Tests (Automated Pipeline)

The AI safety pipeline automatically scans for:
- Revenue-critical code without validation
- Unvalidated user input
- Potential injection vulnerabilities
- Payment data exposure risks

## Implementation Guide

### Step 1: Install Dependencies

```bash
# Add fast-check for property-based testing
pnpm add -D fast-check@^3.15.1

# Ensure testing libraries are installed
pnpm add -D @testing-library/react @testing-library/user-event
```

### Step 2: Create Custom Arbitraries

Define domain-specific test data generators:

```typescript
// arbitraries/billing.ts
import fc from 'fast-check';

export const customerIdArb = fc.record({
  prefix: fc.constantFrom('CUS', 'CUST', 'C'),
  number: fc.integer({ min: 1, max: 999999 })
}).map(({ prefix, number }) => `${prefix}-${number.toString().padStart(6, '0')}`);

export const serviceAmountArb = fc.double({ 
  min: 9.99, 
  max: 999.99, 
  noNaN: true 
});

export const billingDataArb = fc.record({
  customerId: customerIdArb,
  amount: serviceAmountArb,
  currency: fc.constantFrom('USD', 'EUR', 'GBP'),
  taxRate: fc.double({ min: 0.0, max: 0.30 }),
  paymentMethod: fc.constantFrom('credit_card', 'bank_transfer', 'paypal')
});
```

### Step 3: Write Property-Based Tests

Focus on business rules and mathematical invariants:

```typescript
// __tests__/property-based/billing-properties.property.test.ts
import fc from 'fast-check';
import { billingDataArb } from '../../arbitraries/billing';
import { calculateInvoiceTotal } from '../../utils/billing';

describe('Billing Calculation Properties', () => {
  test('Invoice totals are always mathematically correct', () => {
    fc.assert(
      fc.property(billingDataArb, (billing) => {
        const invoice = calculateInvoiceTotal(billing);
        
        // Property 1: Total includes tax
        const expectedTax = billing.amount * billing.taxRate;
        expect(Math.abs(invoice.taxAmount - expectedTax)).toBeLessThan(0.01);
        
        // Property 2: Total is amount + tax
        const expectedTotal = billing.amount + expectedTax;
        expect(Math.abs(invoice.total - expectedTotal)).toBeLessThan(0.01);
        
        // Property 3: No negative values
        expect(invoice.total).toBeGreaterThan(0);
        expect(invoice.taxAmount).toBeGreaterThanOrEqual(0);
      }),
      { 
        numRuns: 500,
        verbose: true // Show generated values on failure
      }
    );
  });
});
```

### Step 4: Create AI-Generated Component Tests

Test components with dynamic scenarios:

```typescript
// __tests__/ai-scenarios/payment-form.scenario.test.tsx
import fc from 'fast-check';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PaymentForm } from '../../components/PaymentForm';

describe('Payment Form AI Scenarios', () => {
  test('Form validation works for any user input', async () => {
    const userInputScenarios = fc.record({
      amount: fc.oneof(
        fc.constant(''), // Empty
        fc.constant('abc'), // Non-numeric
        fc.double().map(n => n.toString()) // Valid number
      ),
      email: fc.oneof(
        fc.emailAddress(), // Valid email
        fc.string(), // Invalid format
        fc.constant('') // Empty
      )
    });

    await fc.assert(
      fc.asyncProperty(userInputScenarios, async (inputs) => {
        const user = userEvent.setup();
        render(<PaymentForm />);
        
        // Simulate user input
        await user.type(screen.getByTestId('amount'), inputs.amount);
        await user.type(screen.getByTestId('email'), inputs.email);
        await user.click(screen.getByTestId('submit'));
        
        // Property: Form should either submit or show validation errors
        const errorMessages = screen.queryAllByRole('alert');
        const successMessage = screen.queryByText(/success/i);
        
        expect(errorMessages.length > 0 || successMessage).toBeTruthy();
      }),
      { numRuns: 75 }
    );
  });
});
```

### Step 5: Configure Jest for AI-First Tests

Update `jest.config.js` to include property-based test project:

```javascript
module.exports = {
  projects: [
    // ... existing projects
    
    // Property-Based Tests (AI-First Testing)
    {
      displayName: 'Property-Based Tests',
      testMatch: [
        '<rootDir>/**/__tests__/**/*property*.test.[jt]s?(x)',
        '<rootDir>/**/__tests__/**/*scenario*.test.[jt]s?(x)'
      ],
      testTimeout: 30000, // Property tests can take longer
      // ... other configuration
    }
  ]
};
```

## Running Tests

### Basic Commands

```bash
# Run all traditional unit tests
pnpm test:unit

# Run property-based tests only
pnpm test:property

# Run AI safety validation
pnpm test:ai-safety

# Run all tests
pnpm test:all
```

### Advanced Commands

```bash
# Run property tests with verbose output
pnpm test:property -- --verbose

# Run specific property test file
pnpm test -- payment-calculations.property.test.ts

# Run with coverage (business outcome focused)
pnpm test:coverage

# Run AI safety pipeline in CI mode
NODE_ENV=ci pnpm test:ai-safety
```

## AI Safety Pipeline

### Automated Validation

The AI safety pipeline (`scripts/ai-safety-frontend-pipeline.js`) automatically:

1. **Scans Components** for revenue-critical patterns without validation
2. **Validates Payment Security** to prevent client-side calculation manipulation
3. **Checks Input Sanitization** for injection vulnerabilities
4. **Runs Property Tests** to ensure mathematical correctness
5. **Generates Safety Report** with actionable recommendations

### Running the Pipeline

```bash
# Run complete AI safety validation
pnpm test:ai-safety

# Run in CI/CD pipeline
NODE_ENV=production pnpm test:ai-safety
```

### Pipeline Output

```
🤖 Starting Frontend AI Safety Validation Pipeline
============================================================
🔍 Scanning React components for AI safety violations...
   Found 0 components with safety concerns
💳 Validating payment processing security...
   Found 0 files with payment security issues
🧹 Checking input sanitization patterns...
   Found 0 components with input sanitization issues
🎲 Running property-based tests...
   ✅ Property-based tests passed

📋 AI Safety Summary:
   🔍 Components scanned: 0
   🚨 Critical issues: 0
   ⚠️  High priority: 0
   📝 Medium priority: 0
   💳 Payment security issues: 0
   🧹 Input validation issues: 0

✅ AI Safety Pipeline PASSED - No critical issues found
```

## Best Practices

### 1. Property Definition

Always start by defining the business properties that must hold:

```typescript
// Good: Tests business rule
expect(result.finalTotal).toBeGreaterThanOrEqual(result.subtotal);

// Bad: Tests implementation detail  
expect(mockCalculate).toHaveBeenCalledWith(expectedParams);
```

### 2. Revenue-Critical Code

All payment calculations must have property-based tests:

```typescript
// Required for any function that calculates money
describe('calculateServiceTotal', () => {
  test('Service total properties always hold', () => {
    fc.assert(fc.property(serviceArb, (service) => {
      const total = calculateServiceTotal(service);
      
      // Property: Total is never negative
      expect(total).toBeGreaterThanOrEqual(0);
      
      // Property: Total includes all service fees
      const expectedMin = service.basePrice;
      expect(total).toBeGreaterThanOrEqual(expectedMin);
    }));
  });
});
```

### 3. Input Validation

Test all user input with edge cases:

```typescript
const dangerousInputs = fc.oneof(
  fc.constant(''), // Empty
  fc.constant('<script>alert("xss")</script>'), // XSS
  fc.constant("'; DROP TABLE users; --"), // SQL injection
  fc.constant('null'), // Null string
  fc.constant('undefined'), // Undefined string
);
```

### 4. Error Handling

Property tests should verify error handling:

```typescript
fc.assert(fc.property(invalidDataArb, (invalidData) => {
  expect(() => {
    processPayment(invalidData);
  }).toThrow(); // Should throw for invalid data
}));
```

## Migration from Traditional Tests

### Phase 1: Identify Revenue-Critical Code

1. Find all payment, billing, and financial calculation functions
2. Add property-based tests for mathematical invariants
3. Keep existing unit tests for now

### Phase 2: Add AI-Generated Component Tests

1. Replace static test data with fast-check arbitraries  
2. Add scenario tests for user interactions
3. Focus on business outcomes, not implementation

### Phase 3: Implement AI Safety Pipeline

1. Run AI safety validation in CI/CD
2. Fix any issues found by the pipeline
3. Enforce AI safety checks for all new code

### Phase 4: Deprecate Traditional Tests

1. Remove redundant unit tests that don't add business value
2. Keep accessibility and integration tests
3. Focus coverage metrics on business outcomes

## Troubleshooting

### Common Issues

#### Property Test Failures

When a property test fails, fast-check shows the failing input:

```
Property failed after 1 test(s) with seed 42:
{ amount: 10.5, taxRate: 0.08500000000000001 }
```

This reveals edge cases like floating-point precision errors.

#### Slow Test Execution

Reduce `numRuns` for faster feedback during development:

```typescript
// Development
{ numRuns: 50 }

// CI/CD
{ numRuns: 1000 }
```

#### Memory Issues

For large datasets, use streaming arbitraries:

```typescript
fc.memo(fc.integer()).map(id => generateLargeCustomerData(id))
```

### Debugging Tips

1. **Use `verbose: true`** to see generated values
2. **Add `fc.pre()` conditions** to filter invalid combinations
3. **Use `fc.example()`** to test specific edge cases
4. **Add `note()` calls** to track test execution

## Conclusion

AI-first testing transforms frontend testing from a code coverage exercise into a business outcome validation system. By focusing on mathematical properties and AI-generated scenarios, we catch bugs that traditional testing misses while ensuring revenue-critical code is mathematically correct.

The key is thinking about what properties must ALWAYS hold, regardless of the specific inputs or user interactions. This approach provides stronger guarantees about system behavior while finding edge cases that could cost money or compromise security.