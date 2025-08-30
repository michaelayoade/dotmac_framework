# Frontend Audit Integration Guide

## Overview

The DotMac Framework now includes comprehensive audit logging integration across all frontend applications using DRY (Don't Repeat Yourself) principles. This integration provides automatic tracking of user interactions, API calls, and business events with minimal setup.

## 🚀 Quick Integration

### 1. Basic Setup (3 lines of code)

```tsx
// Import the preset for your app type
import { CustomerPortalAudit } from '@dotmac/headless';

// Wrap your app
export default function RootLayout({ children }) {
  return (
    <CustomerPortalAudit>
      {children}
    </CustomerPortalAudit>
  );
}
```

### 2. Available Presets

Each preset is optimized for specific app types:

```tsx
import {
  CustomerPortalAudit,    // For customer self-service portals
  AdminPortalAudit,       // For admin management interfaces
  TechnicianAppAudit,     // For mobile/offline technician apps
  ResellerPortalAudit,    // For partner/reseller portals
  ManagementPortalAudit   // For management dashboards
} from '@dotmac/headless';
```

## 📋 What Gets Audited Automatically

### User Interactions

- ✅ **Page Views** - Navigation and route changes
- ✅ **Button Clicks** - All clickable elements with context
- ✅ **Form Submissions** - Forms with field validation (PII protected)
- ✅ **Feature Usage** - Component interactions and workflows

### API Communications

- ✅ **HTTP Requests** - All fetch calls with timing and outcomes
- ✅ **Authentication** - Login/logout events and token refresh
- ✅ **Data Access** - CRUD operations with before/after states
- ✅ **Error Handling** - Failed requests and system errors

### Security Events

- ✅ **Authentication Failures** - Failed login attempts
- ✅ **Permission Denials** - Unauthorized access attempts
- ✅ **Suspicious Activity** - XSS attempts and console manipulation
- ✅ **Session Management** - Session start/end tracking

## 🛠 Advanced Configuration

### Custom Setup

```tsx
import { AuditIntegrationWrapper } from '@dotmac/headless';

function MyApp({ children }) {
  return (
    <AuditIntegrationWrapper
      serviceName="my-custom-app"
      batchSize={20}
      batchTimeout={3000}
      interceptFetch={true}
      interceptClicks={true}
      interceptForms={true}
      excludeUrls={[/\/private\//, /\/internal\//]}
      excludeElements={['.sensitive-data', '[data-private]']}
    >
      {children}
    </AuditIntegrationWrapper>
  );
}
```

### Programmatic Logging

```tsx
import { useAudit } from '@dotmac/headless';

function BusinessComponent() {
  const { logBusinessEvent, logDataAccess, logUIEvent } = useAudit();

  const handleImportantAction = async () => {
    // Log business process
    await logBusinessEvent(
      AuditEventType.BUSINESS_WORKFLOW_START,
      'invoice_generation',
      AuditOutcome.SUCCESS,
      { invoice_count: 150 }
    );

    // Log data access
    await logDataAccess(
      'create',
      'invoice',
      'invoice_12345',
      AuditOutcome.SUCCESS,
      { amount: 299.99 }
    );
  };
}
```

## 🔐 Security & Privacy

### PII Protection

- Sensitive form fields are automatically redacted
- Passwords, tokens, and keys are never logged
- Custom sensitive field detection via configuration

### Data Sanitization

```tsx
// Exclude sensitive elements
<input
  type="password"
  className="no-audit"           // CSS class exclusion
  data-no-audit="true"          // Data attribute exclusion
/>
```

### URL Exclusions

```tsx
excludeUrls: [
  /\/api\/auth\/token/,         // Authentication endpoints
  /\/payment\/process/,         // Payment processing
  /\/admin\/sensitive/          // Sensitive admin areas
]
```

## 📊 Monitoring & Analytics

### Real-time Event Streaming

```tsx
import { AuditApiClient } from '@dotmac/headless';

const auditClient = new AuditApiClient('/api');

// Stream events in real-time
const eventStream = await auditClient.streamEvents({
  event_types: ['auth.login', 'data.create'],
  severity: ['high', 'critical']
});

eventStream.onmessage = (event) => {
  const auditEvent = JSON.parse(event.data);
  console.log('New audit event:', auditEvent);
};
```

### Export & Reporting

```tsx
// Export audit data
const csvData = await auditClient.exportEvents('csv', {
  start_time: Date.now() - 86400000, // Last 24 hours
  event_types: ['business.transaction']
});

// Generate compliance report
const complianceReport = await auditClient.getComplianceReport('GDPR');
```

## 🎯 App-Specific Examples

### Customer Portal Integration

```tsx
// apps/customer/src/app/layout.tsx
import { CustomerPortalAudit } from '@dotmac/headless';

export default function CustomerLayout({ children }) {
  return (
    <CustomerPortalAudit>
      {children}
    </CustomerPortalAudit>
  );
}
```

**Automatically Tracks:**

- Bill payments and payment failures
- Service requests and support tickets
- Account updates and profile changes
- Usage monitoring and plan changes

### Admin Portal Integration

```tsx
// apps/admin/src/app/layout.tsx
import { AdminPortalAudit } from '@dotmac/headless';

export default function AdminLayout({ children }) {
  return (
    <AdminPortalAudit>
      {children}
    </AdminPortalAudit>
  );
}
```

**Automatically Tracks:**

- User management and permission changes
- System configuration updates
- Data exports and imports
- Critical administrative actions

## 🔧 Configuration Options

| Option | Description | Default | Customer | Admin | Technician |
|--------|-------------|---------|----------|-------|------------|
| `batchSize` | Events per batch | 10 | 15 | 5 | 20 |
| `batchTimeout` | Batch timeout (ms) | 5000 | 3000 | 2000 | 10000 |
| `interceptClicks` | Track all clicks | true | ✅ | ✅ | ✅ |
| `interceptForms` | Track form submissions | true | ✅ | ✅ | ✅ |
| `interceptNavigation` | Track page navigation | true | ✅ | ✅ | ✅ |
| `enableLocalStorage` | Offline event storage | true | ✅ | ❌ | ✅ |

## 🚨 Troubleshooting

### Common Issues

**Q: Audit events not appearing in backend?**
A: Check network connectivity and authentication tokens. Events are batched locally until connection is restored.

**Q: Too many events being logged?**
A: Use `excludeElements` and `excludeUrls` to filter out noisy components.

**Q: Performance impact?**
A: Audit logging is optimized with batching and background processing. Typical overhead is <1% of request time.

### Debug Mode

```tsx
// Enable verbose logging in development
<AuditIntegrationWrapper
  enableConsoleLogging={true}
  serviceName="debug-app"
>
```

## 📈 Benefits Summary

✅ **Zero-Code Setup** - 3-line integration for most use cases
✅ **Comprehensive Coverage** - All user interactions and API calls tracked
✅ **Security-First** - PII protection and sensitive data handling
✅ **Performance Optimized** - Batching, background processing, offline support
✅ **Compliance Ready** - GDPR, SOC2, CCPA reporting built-in
✅ **Developer Friendly** - TypeScript support, React hooks, minimal config

## 🔄 Migration from Legacy Systems

If you have existing audit code, the new system provides compatibility:

```tsx
// Old way (multiple setup files, complex configuration)
import { SecurityLogger } from './old-security';
import { EventTracker } from './old-tracking';
// ... 50+ lines of setup code

// New way (single line)
import { CustomerPortalAudit } from '@dotmac/headless';
```

The DRY approach eliminates code duplication across all 7 frontend applications while providing enhanced functionality and better performance.
