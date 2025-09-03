# @dotmac/auth-system

Universal Authentication System for all DotMac portals. Provides secure, type-safe, and portal-aware authentication functionality with comprehensive security features.

## Features

- **Universal Portal Support**: Works with all 7 DotMac portals (management-admin, customer, admin, reseller, technician, management-reseller, tenant-portal)
- **Multiple Authentication Methods**: Email, Portal ID, Account Number, Partner Code
- **Security-First Design**: Rate limiting, threat detection, audit trails, MFA support
- **Token Management**: Auto-refresh, secure storage, cross-tab synchronization
- **Session Management**: Timeout handling, activity tracking, cross-tab sync
- **Real-time Security**: Suspicious activity detection, anomaly analysis
- **Type-Safe**: Full TypeScript support with comprehensive type definitions
- **Portal-Aware**: Custom styling, validation rules, and behavior per portal

## Installation

```bash
pnpm add @dotmac/auth-system
```

## Dependencies

The package requires these peer dependencies:

```json
{
  "@tanstack/react-query": "^5.0.0",
  "react": "^18.0.0",
  "react-dom": "^18.0.0",
  "zod": "^3.22.0"
}
```

## Quick Start

### 1. Wrap your app with AuthProvider

```tsx
import { AuthProvider } from '@dotmac/auth-system';

function App() {
  return (
    <AuthProvider portalVariant='customer'>
      <YourAppComponents />
    </AuthProvider>
  );
}
```

### 2. Use authentication in components

```tsx
import { useAuthContext } from '@dotmac/auth-system';

function LoginPage() {
  const { login, isLoading, error } = useAuthContext();

  const handleLogin = async (credentials) => {
    try {
      await login(credentials);
      // Redirect to dashboard
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <UniversalLoginForm
      portalVariant='customer'
      onSubmit={handleLogin}
      isLoading={isLoading}
      error={error}
    />
  );
}
```

### 3. Protect routes

```tsx
import { ProtectedRoute } from '@dotmac/auth-system';

function Dashboard() {
  return (
    <ProtectedRoute requiredPermissions={['dashboard.read']}>
      <DashboardContent />
    </ProtectedRoute>
  );
}
```

## Portal Configuration

Each portal has its own configuration with custom styling, validation rules, and features:

```tsx
import { getPortalConfig } from '@dotmac/auth-system';

const config = getPortalConfig('customer');
console.log(config);
// {
//   name: 'Customer Portal',
//   loginMethods: ['portalId', 'accountNumber', 'email'],
//   features: {
//     mfaRequired: false,
//     passwordStrength: 'medium',
//     sessionTimeout: 480
//   },
//   // ... more config
// }
```

## Authentication Methods

### Email + Password (Standard)

```tsx
const credentials = {
  email: 'user@example.com',
  password: 'securepassword',
  portalType: 'customer',
};
```

### Portal ID (Customer Portal)

```tsx
const credentials = {
  portalId: 'CUST123456',
  password: 'securepassword',
  portalType: 'customer',
};
```

### Account Number (Customer Portal)

```tsx
const credentials = {
  accountNumber: 'ACC789012',
  password: 'securepassword',
  portalType: 'customer',
};
```

### Partner Code (Reseller Portal)

```tsx
const credentials = {
  partnerCode: 'PARTNER001',
  password: 'securepassword',
  portalType: 'reseller',
};
```

## Advanced Usage

### Custom Authentication Hook

```tsx
import { useAuth } from '@dotmac/auth-system';

function useCustomAuth() {
  const auth = useAuth('management-admin');

  return {
    ...auth,
    isAdmin: auth.hasRole(['admin', 'super_admin']),
    canManageUsers: auth.hasPermission('users.manage'),
  };
}
```

### Session Management

```tsx
import { sessionManager } from '@dotmac/auth-system';

// Get current session info
const sessionInfo = await sessionManager.getSessionInfo();

// Extend session
await sessionManager.extendSession(60); // 60 minutes

// Setup session timeout warnings
const cleanup = sessionManager.setupSessionTimeout(
  session,
  () => alert('Session expiring in 5 minutes!'),
  () => (window.location.href = '/login')
);
```

### Security Monitoring

```tsx
import { securityService } from '@dotmac/auth-system';

// Analyze user security
const analysis = await securityService.analyzeUserSecurity(userId);
console.log('Risk score:', analysis.riskScore);
console.log('Threats:', analysis.threats);

// Report suspicious activity
await securityService.recordEvent({
  type: 'suspicious_activity',
  userId: user.id,
  portalType: 'customer',
  ipAddress: '192.168.1.1',
  userAgent: navigator.userAgent,
  metadata: { reason: 'unusual_location' },
  success: false,
  timestamp: new Date(),
});
```

### Rate Limiting

```tsx
import { rateLimiter } from '@dotmac/auth-system';

// Check if login attempt is allowed
const status = await rateLimiter.checkLimit('login');
if (!status.allowed) {
  console.log(`Rate limited. Try again in ${status.retryAfter} seconds`);
  return;
}

// Record login attempt
await rateLimiter.recordAttempt('login', success);
```

## Components

### UniversalLoginForm

Intelligent login form that adapts to each portal's requirements:

```tsx
<UniversalLoginForm
  portalVariant='customer'
  onSubmit={handleLogin}
  isLoading={isLoading}
  error={error}
  showRememberMe={true}
  showForgotPassword={true}
  customStyles={{
    primaryColor: '#your-brand-color',
  }}
/>
```

### ProtectedRoute

Protect routes based on authentication and permissions:

```tsx
<ProtectedRoute
  requiredPermissions={['billing.read', 'billing.write']}
  requiredRole='admin'
  fallback={<AccessDenied />}
  redirectTo='/login'
>
  <AdminBillingPage />
</ProtectedRoute>
```

### AuthGuard

Conditional rendering based on auth state:

```tsx
<AuthGuard
  requireAuth={true}
  requiredPermissions={['users.manage']}
  fallback={<div>Access Denied</div>}
>
  <UserManagementTools />
</AuthGuard>
```

### PortalSwitcher

Allow users to switch between accessible portals:

```tsx
<PortalSwitcher
  availablePortals={['admin', 'reseller', 'customer']}
  onPortalSwitch={(portal) => {
    window.location.href = `/${portal}`;
  }}
/>
```

## API Reference

### AuthContextValue

```tsx
interface AuthContextValue {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: LoginError | null;
  session: Session | null;
  portal: PortalConfig | null;
  permissions: string[];
  role: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (updates: Partial<User>) => Promise<User>;
  changePassword: (request: PasswordChangeRequest) => Promise<void>;
  resetPassword: (request: PasswordResetRequest) => Promise<void>;
  setupMfa: (type: 'totp' | 'sms' | 'email') => Promise<MfaSetup>;
  verifyMfa: (verification: MfaVerification) => Promise<boolean>;

  // Session management
  getSessions: () => Promise<Session[]>;
  terminateSession: (sessionId: string) => Promise<void>;
  terminateAllSessions: () => Promise<void>;

  // Permission helpers
  hasPermission: (permission: string) => boolean;
  hasRole: (roleOrRoles: string | string[]) => boolean;
  hasAnyRole: (roles: string[]) => boolean;

  // Portal helpers
  getPortalConfig: () => PortalConfig | null;
  getLoginMethods: () => string[];
  isMfaRequired: () => boolean;
  canAccessPortal: (portalType: PortalVariant) => boolean;

  // Validation helpers
  validateCredentials: (credentials: LoginCredentials) => ValidationResult;
  validatePassword: (password: string) => ValidationResult;

  // Security
  getRateLimitStatus: () => Promise<RateLimitStatus | null>;
  getSecurityEvents: () => Promise<AuthEvent[]>;
  reportSuspiciousActivity: (details: Record<string, any>) => Promise<void>;
}
```

## Security Features

### Built-in Security Measures

- **Rate Limiting**: Prevents brute force attacks with progressive delays
- **Threat Detection**: Identifies suspicious patterns and user agents
- **Audit Trail**: Comprehensive logging of all security events
- **Session Security**: Secure token storage with cross-tab synchronization
- **CSRF Protection**: Automatic CSRF token handling
- **IP Monitoring**: Tracks and blocks suspicious IP addresses
- **Anomaly Detection**: Identifies unusual login patterns

### Security Best Practices

1. **Always use HTTPS** in production
2. **Enable MFA** for sensitive portals
3. **Monitor security events** regularly
4. **Set appropriate session timeouts**
5. **Review rate limiting configurations**
6. **Implement proper error handling**

## Portal Variants

| Portal                | Description           | Login Methods               | Features                      |
| --------------------- | --------------------- | --------------------------- | ----------------------------- |
| `management-admin`    | Master admin portal   | Email                       | MFA required, strict security |
| `admin`               | Tenant admin portal   | Email                       | MFA optional, admin features  |
| `customer`            | Customer self-service | Portal ID, Account #, Email | User-friendly, self-service   |
| `reseller`            | Partner portal        | Partner Code, Email         | Territory management          |
| `technician`          | Field technician app  | Email                       | Mobile-optimized              |
| `management-reseller` | Reseller management   | Email                       | Reseller oversight            |
| `tenant-portal`       | Multi-tenant access   | Email                       | Tenant switching              |

## Migration Guide

### From Existing Auth Systems

1. **Install the package**:

   ```bash
   pnpm add @dotmac/auth-system
   ```

2. **Replace auth providers**:

   ```tsx
   // Before
   <OldAuthProvider>

   // After
   <AuthProvider portalVariant="your-portal">
   ```

3. **Update auth hooks**:

   ```tsx
   // Before
   const { user, login } = useOldAuth();

   // After
   const { user, login } = useAuthContext();
   ```

4. **Update login forms**:

   ```tsx
   // Before
   <CustomLoginForm />

   // After
   <UniversalLoginForm portalVariant="your-portal" />
   ```

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure TypeScript types are accurate

## License

Private - DotMac Framework

---

For more examples and advanced usage, see the [DotMac Framework Documentation](../../../docs/).
