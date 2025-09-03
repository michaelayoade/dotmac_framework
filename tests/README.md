# License Enforcement E2E Tests

Comprehensive end-to-end testing suite for license enforcement and feature flag management across the DotMac multi-app platform.

## Overview

This test suite validates license-based feature access and cross-app coordination for the DotMac platform, ensuring proper enforcement of subscription plans and feature flags across all tenant applications.

## Test Coverage

### 🚀 Feature Flag Enforcement (`feature-flags.spec.ts`)

Tests license-based feature access and multi-app coordination:

- **Basic Plan Restrictions**: Validates that basic plan tenants cannot access premium features
- **License Upgrades**: Ensures immediate feature enablement after license upgrades  
- **Cross-App Propagation**: Verifies feature flags propagate across all tenant apps
- **Grace Period Handling**: Tests feature access during subscription downgrades
- **Audit Logging**: Validates feature access attempts are properly logged

### 🔐 Cross-App Permissions (`cross-app-permissions.spec.ts`)

Tests user permissions and access control across multiple apps:

- **Access Restrictions**: Users with ISP access but not CRM are properly restricted
- **Permission Grants**: Admin-granted permissions enable immediate app access
- **Role Propagation**: Role changes reflect across all subscribed apps
- **Single Sign-On**: SSO functionality works seamlessly across tenant apps
- **Permission Inheritance**: Complex role hierarchies resolve correctly

### 📦 App Subscription Lifecycle (`app-subscription-lifecycle.spec.ts`)

Tests the complete app subscription management workflow:

- **Subscription Process**: New app subscriptions and activation
- **App Configuration**: Initial setup wizards and customization
- **Data Migration**: Version upgrades with data preservation
- **Unsubscription**: Graceful data archival and access removal
- **Billing Integration**: Usage tracking and prorated billing

## Architecture

### Test Structure

```
tests/
├── e2e/                           # E2E test specifications
│   ├── feature-flags.spec.ts
│   ├── cross-app-permissions.spec.ts
│   └── app-subscription-lifecycle.spec.ts
├── setup/                         # Global setup and teardown
│   ├── global.setup.ts
│   └── global.teardown.ts
├── reporters/                     # Custom test reporters
│   └── license-compliance-reporter.ts
├── playwright.config.ts           # Playwright configuration
└── package.json                   # Test dependencies
```

### Shared Utilities

```
src/dotmac_shared/tests/e2e/licensing/
├── __init__.py                    # Public API exports
├── factories.py                   # Test data factories
├── fixtures.py                    # Test fixtures and cleanup
├── helpers.py                     # Test helper functions
└── assertions.py                  # Custom assertions
```

## Quick Start

### Prerequisites

- Node.js 18+ 
- Python 3.9+ with Poetry
- All DotMac platform services running

### Installation

```bash
cd tests
npm install
playwright install
```

### Running Tests

```bash
# Run all license enforcement tests
npm run test

# Run specific test suites
npm run test:feature-flags
npm run test:cross-app  
npm run test:subscription

# Run by license plan
npm run test:basic-plan
npm run test:premium-plan
npm run test:enterprise-plan

# Generate compliance report
npm run test:compliance

# Debug mode
npm run test:debug
```

## Test Configuration

### Multi-App Setup

The test suite automatically starts and coordinates multiple applications:

- **Management Platform** (Port 8000): License server and admin
- **ISP Admin** (Port 3000): Primary admin interface
- **Customer Portal** (Port 3001): Customer self-service
- **Field Operations** (Port 3002): Technician tools
- **Reseller Portal** (Port 3003): Partner management
- **CRM System** (Port 3004): Sales and leads

### Environment Variables

```bash
# Test environment
NODE_ENV=test
ENVIRONMENT=test

# Database
DATABASE_URL=sqlite:///test_license.db

# License enforcement
ENABLE_LICENSE_ENFORCEMENT=true
ENABLE_LICENSE_MIDDLEWARE=true
MANAGEMENT_PLATFORM_URL=http://localhost:8000

# Debugging
LOG_LEVEL=INFO
```

## Test Data Management

### Factories

Test data is generated using factories for consistent, realistic scenarios:

```typescript
// Create tenant with specific license plan
const [tenant, license] = await fixtures.create_tenant_with_license('premium');

// Create user with specific role
const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');

// Create feature flag
const flag = await fixtures.create_feature_flag(tenant.tenant_id, 'advanced_analytics');
```

### Fixtures

Automated setup and cleanup of test resources:

```typescript
await license_fixtures(async (fixtures) => {
  // Test implementation - fixtures handle cleanup automatically
});
```

## Compliance Reporting

### Custom Reporter

The `LicenseComplianceReporter` generates specialized compliance reports:

- **Compliance Score**: Overall platform compliance percentage
- **Violation Tracking**: Critical license violations and warnings
- **Feature Coverage**: Which features are tested across which license tiers
- **Cross-App Consistency**: Consistency scores across apps

### Report Outputs

- `test-results/license-compliance-report.json`: Detailed JSON report
- `test-results/license-compliance-summary.md`: Human-readable summary
- `test-results/license-enforcement-report/`: HTML report with screenshots

## Debugging

### Test Debugging

```bash
# Run tests in headed mode (browser visible)
npm run test:headed

# Debug specific test
npm run test:debug -- --grep "should deny access"

# Open test UI for interactive debugging
npm run test:ui
```

### Common Issues

1. **Service Startup Timeouts**: Ensure all platform services are healthy
2. **Port Conflicts**: Check that required ports (3000-3004, 8000) are available
3. **Database Locks**: Tests cleanup databases automatically, but manual cleanup may be needed
4. **License Cache**: Clear license cache between test runs if needed

## Development

### Adding New Tests

1. Create test specification in appropriate suite file
2. Use shared utilities from `src/dotmac_shared/tests/e2e/licensing/`
3. Follow existing patterns for test data and cleanup
4. Ensure proper test isolation and cleanup

### Extending Utilities

The shared utilities can be extended for new test scenarios:

- **Factories**: Add new data generators in `factories.py`
- **Helpers**: Add UI interaction helpers in `helpers.py`
- **Assertions**: Add custom validation logic in `assertions.py`
- **Fixtures**: Add resource management in `fixtures.py`

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run License Enforcement Tests
  run: |
    cd tests
    npm install
    npm run test:ci

- name: Upload Test Reports
  uses: actions/upload-artifact@v3
  with:
    name: license-test-reports
    path: tests/test-results/
```

### Quality Gates

Tests enforce quality gates for:

- **95%+ Compliance Score**: All license restrictions properly enforced
- **Zero Critical Violations**: No unauthorized feature access
- **Cross-App Consistency**: Feature state consistent across all apps

## Success Criteria

The test suite validates the following success criteria:

✅ **License Tier Enforcement**
- Basic plans cannot access premium/enterprise features
- Premium plans cannot access enterprise-only features
- Enterprise plans have full feature access

✅ **Cross-App Coordination**
- Feature flags propagate to all tenant apps within 30 seconds
- Permission changes reflect across apps in real-time
- SSO works seamlessly across all subscribed apps

✅ **Subscription Lifecycle**
- App subscriptions activate immediately upon payment
- Data migrations preserve all user data during upgrades
- Unsubscriptions archive data with 30-day grace period
- Billing accurately tracks usage and handles proration

✅ **Security and Compliance**
- All license enforcement actions are logged
- No unauthorized feature access is possible
- User permissions are properly isolated between tenants

## Support

For issues with the E2E test suite:

1. Check test logs in `test-results/` directory
2. Review compliance reports for specific violations
3. Consult the debugging section above
4. Contact the DotMac Framework team

---

**Last Updated**: December 2024  
**Test Framework**: Playwright v1.40+  
**Coverage**: 100% of license enforcement scenarios