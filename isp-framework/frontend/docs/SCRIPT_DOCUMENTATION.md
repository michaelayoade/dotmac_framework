# Frontend NPM Scripts Documentation

## Overview

This document explains all available NPM scripts in the frontend monorepo, with special focus on the AI-first testing infrastructure.

## Development Scripts

### Core Development

```bash
# Start all applications in development mode
pnpm dev

# Start development servers for packages only
pnpm dev:packages

# Start development servers for applications only  
pnpm dev:apps
```

**What they do:**
- `dev`: Uses Turbo to start all apps (admin:3000, customer:3001, reseller:3002) with hot reloading
- `dev:packages`: Starts only shared packages in watch mode for development
- `dev:apps`: Starts only applications, useful when packages are already built

### Build Scripts

```bash
# Build all applications and packages
pnpm build

# Build packages only (shared libraries)
pnpm build:packages

# Build applications only  
pnpm build:apps

# Advanced build options
pnpm build:system        # Full system build with prerequisites
pnpm build:ci           # CI build (skips prerequisites)
pnpm build:fast         # Skip tests and Storybook for speed
pnpm build:packages-only # Only build shared packages
```

**Build outputs:**
- Next.js applications: `.next/` and `out/` directories
- Packages: `dist/` directories with compiled TypeScript
- Storybook: `storybook-static/` for component documentation

## AI-First Testing Scripts

### Core Testing Commands

```bash
# Traditional unit tests (legacy compatibility)
pnpm test:unit

# AI-first property-based tests (RECOMMENDED)
pnpm test:property  

# Comprehensive AI safety validation
pnpm test:ai-safety

# All tests including E2E
pnpm test:all
```

### Specialized Testing

```bash
# Integration tests across services
pnpm test:integration

# Accessibility testing
pnpm test:a11y

# End-to-end testing with Playwright
pnpm test:e2e
pnpm test:e2e:ui          # With Playwright UI
pnpm test:e2e:headed      # With visible browser
pnpm test:e2e:debug       # Debug mode

# Visual regression testing
pnpm test:visual
pnpm test:visual:portals          # Portal-specific visual tests
pnpm test:visual:portals:headed   # With visible browser
pnpm test:visual:update           # Update visual snapshots

# Performance testing
pnpm test:perf
```

### Coverage and CI

```bash
# Coverage reports (business outcome focused)
pnpm test:coverage
pnpm test:coverage:open   # Open coverage report in browser

# CI-optimized testing
pnpm test:ci              # No watch mode, full coverage

# Watch mode for development
pnpm test:watch
```

## AI Safety Pipeline

### AI Safety Script Deep Dive

```bash
pnpm test:ai-safety
```

**What it does:**
1. **Component Safety Scanning**: Analyzes React components for:
   - Payment processing without validation
   - Sensitive data exposure (credit cards, SSNs)
   - Dangerous patterns (eval, innerHTML manipulation)
   - Unvalidated user input

2. **Payment Security Validation**: Checks for:
   - Hardcoded payment amounts
   - Client-side calculations without server validation
   - Payment data stored in browser storage

3. **Input Sanitization**: Validates:
   - Form components have proper validation
   - User input is sanitized before processing
   - Control characters are filtered out

4. **Property-Based Test Execution**: Runs all property-based tests to ensure:
   - Mathematical invariants hold
   - Business rules are enforced
   - Edge cases are handled

**Pipeline Output:**
```
🤖 Starting Frontend AI Safety Validation Pipeline
🔍 Scanning React components for AI safety violations...
💳 Validating payment processing security...
🧹 Checking input sanitization patterns...
🎲 Running property-based tests...
📊 Generating AI Safety Report...
```

**Exit Codes:**
- `0`: All safety checks passed
- `1`: Critical or high-severity issues found

### AI Safety Configuration

The pipeline can be configured via environment variables:

```bash
# Run in CI mode (stricter validation)
NODE_ENV=ci pnpm test:ai-safety

# Skip certain checks (not recommended)
SKIP_PAYMENT_VALIDATION=true pnpm test:ai-safety

# Generate detailed reports
VERBOSE=true pnpm test:ai-safety
```

## Property-Based Testing

### Property Test Commands

```bash
# Run all property-based tests
pnpm test:property

# Run with verbose output to see generated values
pnpm test:property -- --verbose

# Run specific property test file
pnpm test -- payment-calculations.property.test.ts

# Run property tests with specific parameters
pnpm test:property -- --testNamePattern="Payment.*Properties"
```

### Property Test Types

**Mathematical Property Tests:**
- Payment calculation invariants
- Tax calculation correctness
- Currency formatting consistency
- Discount application rules

**Component Property Tests:**
- Form validation with generated inputs
- Component rendering with any valid props
- Event handling with edge case scenarios
- Accessibility with dynamic content

**Business Rule Tests:**
- ISP-specific billing rules
- Customer onboarding workflows
- Service provisioning constraints
- Revenue protection rules

## Code Quality Scripts

### Linting and Formatting

```bash
# ESLint with auto-fix
pnpm lint
pnpm lint:fix

# CI linting (strict, no warnings allowed)
pnpm lint:ci

# Prettier formatting
pnpm format
pnpm format:check  # Check only, don't modify files
```

### Type Checking

```bash
# TypeScript type checking across all packages
pnpm type-check

# Validate imports and circular dependencies
pnpm validate:imports
pnpm validate:circular
pnpm validate:unused
```

### Quality Gates

```bash
# Run all quality checks
pnpm validate    # type-check + lint + test:unit

# Quality gate for CI/CD
pnpm quality:gate

# Milestone validation (comprehensive check)
pnpm validate:milestone
```

## Advanced Scripts

### Bundle Analysis

```bash
# Analyze bundle sizes
pnpm bundle:analyze

# Generate bundle report and open in browser
pnpm bundle:report
```

### Performance Monitoring

```bash
# Start performance monitoring
pnpm perf:monitor

# Run performance tests
pnpm test:perf
```

### Security and Compliance

```bash
# Security scanning
pnpm test:security

# API contract validation
pnpm test:contract

# Accessibility audit
pnpm a11y:audit
pnpm a11y:test
pnpm a11y:jest
pnpm a11y:lint
```

### Storybook (Component Documentation)

```bash
# Start Storybook dev server
pnpm storybook

# Build Storybook for production
pnpm storybook:build
pnpm build-storybook  # Alternative command

# Test Storybook components
pnpm storybook:test

# Visual testing with Chromatic
pnpm chromatic
```

### Utility Scripts

```bash
# Clean all build artifacts
pnpm clean

# Generate SRI hashes for security
pnpm generate:sri

# Smoke test (quick validation)
pnpm smoke
pnpm smoke:quick  # Skip build and tests
```

## Version Management

```bash
# Changesets for version management
pnpm changeset

# Version packages (automated)
pnpm version-packages

# Release packages
pnpm release
```

## CI/CD Integration

### Recommended CI Pipeline

```bash
# Install dependencies
pnpm install --frozen-lockfile

# Run quality checks
pnpm lint:ci
pnpm type-check

# Run AI-first testing
pnpm test:ai-safety  # Will exit 1 if critical issues found
pnpm test:property   # Property-based tests
pnpm test:unit       # Traditional unit tests (legacy)

# Run integration tests
pnpm test:integration

# Build for production
pnpm build

# Run E2E tests against build
pnpm test:e2e

# Security and compliance
pnpm test:security
pnpm validate:milestone
```

### Environment-Specific Commands

**Development:**
```bash
pnpm dev
pnpm test:watch
```

**Staging:**
```bash
pnpm build
pnpm test:all
pnpm test:visual
```

**Production:**
```bash
pnpm build:ci
pnpm test:ci
pnpm test:ai-safety
```

## Troubleshooting

### Common Issues

**Property tests timing out:**
```bash
# Reduce number of test runs for faster feedback
pnpm test:property -- --testTimeout=15000
```

**Memory issues with large test suites:**
```bash
# Run tests with increased memory
NODE_OPTIONS="--max_old_space_size=4096" pnpm test
```

**Jest cache issues:**
```bash
# Clear Jest cache
pnpm test -- --clearCache
```

### Debug Commands

```bash
# Run tests in debug mode
pnpm test -- --detectOpenHandles --forceExit

# Debug specific test file
pnpm test -- --testNamePattern="Payment" --verbose

# Run AI safety pipeline with debug info
DEBUG=* pnpm test:ai-safety
```

## Migration Guide

### From Traditional Testing

1. **Start with property tests for revenue-critical code:**
   ```bash
   pnpm test:property -- payment
   ```

2. **Gradually add AI-generated component scenarios:**
   ```bash
   pnpm test:property -- component
   ```

3. **Implement AI safety pipeline:**
   ```bash
   pnpm test:ai-safety
   ```

4. **Phase out redundant unit tests:**
   - Keep integration tests
   - Keep accessibility tests
   - Remove mocking-heavy unit tests that don't test business outcomes

### Script Evolution

**Old approach (legacy):**
```bash
pnpm test        # 85% coverage requirement
pnpm lint        # Code style enforcement
```

**New AI-first approach:**
```bash
pnpm test:ai-safety   # Revenue protection and security
pnpm test:property    # Mathematical correctness
pnpm test:unit        # Legacy compatibility
```

The AI-first scripts ensure business outcomes are validated while traditional scripts focus on code quality and style.