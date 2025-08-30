# Portal Development Standards

## DotMac Framework - Frontend Portal Guidelines

### Version: 1.0.0

### Last Updated: 2025-01-29

### Status: Production Standard

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [Portal Naming Conventions](#portal-naming-conventions)
3. [Required Pages by Portal Type](#required-pages-by-portal-type)
4. [Navigation Patterns](#navigation-patterns)
5. [Page Layout Templates](#page-layout-templates)
6. [Authentication & Authorization](#authentication--authorization)
7. [Mobile Responsiveness](#mobile-responsiveness)
8. [Production Readiness Checklist](#production-readiness-checklist)
9. [Code Standards](#code-standards)
10. [Testing Requirements](#testing-requirements)
11. [Performance Standards](#performance-standards)
12. [Security Standards](#security-standards)

---

## 🎯 **Overview**

This document establishes comprehensive standards for all DotMac Framework frontend portals to ensure consistency, maintainability, and production readiness across the platform.

### **Portal Architecture Philosophy**

- **Consistency First**: All portals follow identical patterns
- **Mobile-First**: Responsive design for all screen sizes
- **Security-First**: Authentication and authorization built-in
- **Performance-First**: Optimized for production deployment
- **Accessibility-First**: WCAG 2.1 AA compliance

---

## 🏷️ **Portal Naming Conventions**

### **Directory Structure**

```
frontend/apps/
├── admin/                    # ISP Administrator Portal
├── customer/                 # Customer Self-Service Portal
├── management-admin/         # Master Platform Administrator
├── management-reseller/      # Reseller Network Management
├── reseller/                 # Individual Reseller Portal
├── technician/              # Mobile Technician Portal
└── tenant-portal/           # Tenant Self-Service Portal
```

### **Naming Standards**

| Portal Type | Directory Name | Package Name | Port | Description |
|-------------|----------------|--------------|------|-------------|
| **Master Admin** | `management-admin` | `@dotmac/management-admin` | 3001 | Platform-wide administration |
| **Technician Mobile** | `technician` | `@dotmac/technician` | 3002 | Field service mobile app |
| **Tenant Self-Service** | `tenant-portal` | `@dotmac/tenant-portal` | 3003 | Multi-tenant self-service |
| **Reseller Network** | `management-reseller` | `@dotmac/management-reseller` | 3004 | Reseller network management |
| **ISP Administrator** | `admin` | `@dotmac/admin` | 3005 | ISP business administration |
| **Individual Reseller** | `reseller` | `@dotmac/reseller` | 3006 | Single reseller operations |
| **Customer Portal** | `customer` | `@dotmac/customer` | 3000 | End-customer self-service |

### **URL Conventions**

- Production: `https://{portal-type}.dotmac.app`
- Development: `http://localhost:{port}`
- Staging: `https://{portal-type}-staging.dotmac.app`

---

## 📄 **Required Pages by Portal Type**

### 🏢 **Management Admin Portal** (Master Platform)

**Audience**: Platform administrators managing multiple ISP tenants

#### **Core Pages** ✅ Required

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'Platform overview with tenant metrics',
  '/tenants': 'Tenant management and provisioning',
  '/tenants/new': 'Create new ISP tenant',
  '/tenants/[id]': 'Tenant details and management',
  '/tenants/[id]/edit': 'Modify tenant configuration',
  '/billing': 'Platform billing and subscription management',
  '/users': 'Cross-tenant user management',
  '/security': 'Security monitoring and audit dashboard',
  '/plugins': 'Plugin marketplace and installation',
  '/infrastructure': 'Infrastructure monitoring and scaling',
  '/analytics': 'Platform-wide analytics and insights',
  '/monitoring': 'System health and performance monitoring',
  '/audit-logs': 'Comprehensive audit trail',
  '/api-keys': 'API key management and monitoring',
  '/settings': 'Platform configuration settings',
  '/login': 'Multi-factor authentication'
}
```

#### **Advanced Features** ⭐ Recommended

- `/backup-restore`: Data management and disaster recovery
- `/integrations`: Third-party platform integrations
- `/reports`: Executive reporting and business intelligence
- `/notifications`: System-wide alert management

---

### 👤 **Customer Portal** (End Customer)

**Audience**: ISP end customers managing their services

#### **Core Pages** ✅ Required

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'Service overview and account status',
  '/account': 'Profile and account settings',
  '/billing': 'Billing overview and payment center',
  '/billing/invoices': 'Invoice history and downloads',
  '/billing/payments': 'Payment methods and history',
  '/services': 'Service plans and add-ons management',
  '/usage': 'Usage analytics and data consumption',
  '/support': 'Support center and ticket system',
  '/support/tickets': 'Support ticket management',
  '/support/knowledge-base': 'Self-help resources',
  '/documents': 'Bills, contracts, and important documents',
  '/settings': 'Preferences and notification settings',
  '/login': 'Customer authentication'
}
```

#### **Family Features** 👨‍👩‍👧‍👦 Recommended

- `/family`: Family member management
- `/family/parental-controls`: Content filtering and restrictions
- `/devices`: Connected device management

---

### 🏪 **Reseller Portal** (Individual Reseller)

**Audience**: Individual resellers managing their customer base

#### **Core Pages** ✅ Required

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'Sales metrics and customer overview',
  '/customers': 'Customer relationship management',
  '/customers/new': 'Customer onboarding workflow',
  '/customers/[id]': 'Individual customer management',
  '/commissions': 'Commission tracking and payments',
  '/territories': 'Territory and coverage management',
  '/sales': 'Sales pipeline and opportunity tracking',
  '/billing': 'Reseller billing and payout management',
  '/reports': 'Sales performance and analytics',
  '/marketing': 'Marketing tools and campaign management',
  '/training': 'Training materials and certification',
  '/settings': 'Reseller account configuration',
  '/login': 'Reseller authentication'
}
```

---

### 👨‍🔧 **Technician Mobile Portal** (Field Service)

**Audience**: Field technicians with mobile-first workflow

#### **Core Pages** ✅ Required (Mobile-Optimized)

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'Daily schedule and work order overview',
  '/work-orders': 'Active and pending work orders',
  '/work-orders/[id]': 'Work order details and completion',
  '/customers/[id]': 'Customer information and service history',
  '/inventory': 'Equipment inventory and requisitions',
  '/schedule': 'Calendar view and appointment management',
  '/navigation': 'GPS navigation and route optimization',
  '/reports': 'Field reports and photo documentation',
  '/offline-sync': 'Offline data synchronization status',
  '/profile': 'Technician profile and preferences',
  '/login': 'Mobile-optimized authentication'
}
```

#### **PWA Features** 📱 Required

- Offline functionality with local database
- GPS tracking and geolocation
- Camera integration for photo reports
- Push notifications for new work orders

---

### 🏢 **Admin Portal** (ISP Administrator)

**Audience**: ISP administrators managing their business operations

#### **Core Pages** ✅ Required

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'ISP business metrics and KPIs',
  '/customers': 'Customer lifecycle management',
  '/customers/[id]': 'Customer account details',
  '/services': 'Service catalog and plan management',
  '/billing': 'Revenue management and invoicing',
  '/network': 'Network infrastructure monitoring',
  '/devices': 'Network device management and provisioning',
  '/analytics': 'Business intelligence and reporting',
  '/users': 'Staff and role management',
  '/security': 'Network security monitoring',
  '/reports': 'Financial and operational reports',
  '/settings': 'ISP configuration and preferences',
  '/login': 'Administrator authentication'
}
```

---

### 🤝 **Management Reseller Portal** (Reseller Network)

**Audience**: Platform administrators managing reseller networks

#### **Core Pages** ✅ Required (✅ Currently Complete)

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'Reseller network overview and metrics',
  '/partners': 'Reseller partner management',
  '/partners/onboarding': 'New partner onboarding workflow',
  '/partners/applications': 'Partnership applications processing',
  '/territories': 'Territory allocation and management',
  '/commissions': 'Commission structure and payments',
  '/commissions/calculations': 'Commission calculation engine',
  '/commissions/disputes': 'Dispute resolution system',
  '/training': 'Partner training program management',
  '/analytics': 'Network performance analytics',
  '/incentives': 'Incentive program management',
  '/settings': 'Network configuration settings',
  '/login': 'Management authentication'
}
```

---

### 🏢 **Tenant Portal** (Multi-Tenant Self-Service)

**Audience**: Tenant administrators managing their organization

#### **Core Pages** ✅ Required (🚨 Currently Missing)

```typescript
const REQUIRED_PAGES = {
  '/dashboard': 'Tenant overview and resource usage',
  '/users': 'User management within tenant',
  '/billing': 'Tenant billing and subscription management',
  '/services': 'Service configuration and provisioning',
  '/analytics': 'Tenant-specific analytics and reports',
  '/integrations': 'Third-party service integrations',
  '/api-keys': 'API access management',
  '/audit': 'Tenant audit logs and compliance',
  '/support': 'Support requests and documentation',
  '/settings': 'Tenant configuration and preferences',
  '/login': 'Tenant-scoped authentication'
}
```

---

## 🧭 **Navigation Patterns**

### **Sidebar Navigation Standard**

All desktop portals must implement consistent sidebar navigation:

```typescript
// Standard Navigation Interface
interface NavigationItem {
  name: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  badge?: string | number;
  permission?: string;
  children?: NavigationItem[];
}

// Implementation Example
export const navigationConfig: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard
  },
  {
    name: 'Management',
    href: '/management',
    icon: Users,
    children: [
      { name: 'Users', href: '/users', icon: User },
      { name: 'Roles', href: '/roles', icon: Shield }
    ]
  }
  // ... additional items
];
```

### **Mobile Navigation Standard**

Mobile portals (Technician) must implement bottom tab navigation:

```typescript
// Mobile Tab Navigation
const mobileNavigation = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Orders', href: '/orders', icon: ClipboardList },
  { name: 'Schedule', href: '/schedule', icon: Calendar },
  { name: 'Profile', href: '/profile', icon: User }
];
```

### **Navigation Requirements**

- **Active State Indication**: Clear visual feedback for current page
- **Permission-Based Filtering**: Hide unauthorized sections
- **Badge Notifications**: Show counts for pending items
- **Responsive Collapse**: Mobile-friendly hamburger menu
- **Breadcrumb Navigation**: For deep hierarchies

---

## 🎨 **Page Layout Templates**

### **Standard Layout Components**

#### **1. Desktop Layout Template**

```typescript
interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumb?: BreadcrumbItem[];
}

export function StandardLayout({
  children,
  title,
  subtitle,
  actions,
  breadcrumb
}: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <div className="md:pl-64">
        <Header />
        {breadcrumb && <Breadcrumb items={breadcrumb} />}
        <main className="py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {(title || actions) && (
              <div className="md:flex md:items-center md:justify-between mb-6">
                <div className="flex-1 min-w-0">
                  {title && (
                    <h1 className="text-2xl font-bold text-gray-900">
                      {title}
                    </h1>
                  )}
                  {subtitle && (
                    <p className="mt-1 text-sm text-gray-500">
                      {subtitle}
                    </p>
                  )}
                </div>
                {actions && <div className="mt-4 md:mt-0">{actions}</div>}
              </div>
            )}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
```

#### **2. Mobile Layout Template**

```typescript
export function MobileLayout({ children, title }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <MobileHeader title={title} />
      <main className="pb-16">
        <div className="px-4 py-6">
          {children}
        </div>
      </main>
      <MobileBottomNavigation />
    </div>
  );
}
```

#### **3. Card-Based Content Template**

```typescript
export function CardLayout({ children, className }: CardLayoutProps) {
  return (
    <div className={`bg-white shadow rounded-lg ${className}`}>
      <div className="px-4 py-5 sm:p-6">
        {children}
      </div>
    </div>
  );
}
```

### **Required Layout Elements**

1. **Header**: Logo, user menu, notifications, search
2. **Sidebar**: Primary navigation with collapsible sections
3. **Main Content**: Consistent padding and max-width
4. **Footer**: Version info, support links
5. **Loading States**: Skeleton screens and spinners
6. **Error Boundaries**: Graceful error handling
7. **Breadcrumb**: Deep navigation context

---

## 🔐 **Authentication & Authorization**

### **Authentication Standards**

#### **Multi-Factor Authentication (MFA)**

All portals MUST implement MFA for production:

```typescript
interface AuthConfig {
  mfaRequired: boolean;
  sessionTimeout: number; // minutes
  passwordComplexity: {
    minLength: number;
    requireUppercase: boolean;
    requireLowercase: boolean;
    requireNumbers: boolean;
    requireSymbols: boolean;
  };
  accountLockout: {
    maxAttempts: number;
    lockoutDuration: number; // minutes
  };
}

// Production Configuration
const authConfig: AuthConfig = {
  mfaRequired: true,
  sessionTimeout: 480, // 8 hours
  passwordComplexity: {
    minLength: 12,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSymbols: true
  },
  accountLockout: {
    maxAttempts: 5,
    lockoutDuration: 30
  }
};
```

#### **Session Management**

```typescript
interface SessionConfig {
  tokenRefreshThreshold: number; // seconds before expiry
  inactivityWarning: number; // minutes
  sessionExtensionGracePeriod: number; // minutes
  simultaneousSessionLimit: number;
}
```

### **Authorization Patterns**

#### **Permission-Based Access Control**

```typescript
enum Permission {
  // Customer Management
  CUSTOMERS_VIEW = 'customers.view',
  CUSTOMERS_EDIT = 'customers.edit',
  CUSTOMERS_DELETE = 'customers.delete',

  // Billing Management
  BILLING_VIEW = 'billing.view',
  BILLING_PROCESS = 'billing.process',
  BILLING_REFUND = 'billing.refund',

  // System Administration
  SYSTEM_ADMIN = 'system.admin',
  TENANT_MANAGE = 'tenant.manage',
  USER_MANAGE = 'user.manage'
}

// Page-Level Protection
<ProtectedRoute requiredPermissions={[Permission.CUSTOMERS_VIEW]}>
  <CustomerList />
</ProtectedRoute>

// Component-Level Protection
<PermissionGate permission={Permission.BILLING_REFUND}>
  <RefundButton />
</PermissionGate>
```

#### **Role-Based Access Control**

```typescript
enum Role {
  SUPER_ADMIN = 'super_admin',
  PLATFORM_ADMIN = 'platform_admin',
  ISP_ADMIN = 'isp_admin',
  RESELLER_ADMIN = 'reseller_admin',
  TECHNICIAN = 'technician',
  CUSTOMER = 'customer'
}
```

### **Security Headers**

All portals must implement these security headers:

```typescript
// next.config.js security headers
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin'
  }
];
```

---

## 📱 **Mobile Responsiveness Standards**

### **Breakpoint System**

```scss
// Standardized Breakpoints
$breakpoints: (
  xs: 0px,      // Extra small devices (phones)
  sm: 640px,    // Small devices (large phones)
  md: 768px,    // Medium devices (tablets)
  lg: 1024px,   // Large devices (laptops)
  xl: 1280px,   // Extra large devices (desktops)
  2xl: 1536px   // 2X Extra large devices (large desktops)
);
```

### **Responsive Design Requirements**

#### **Mobile-First Approach**

- Design starts with mobile layout
- Progressive enhancement for larger screens
- Touch-friendly interface elements (44px minimum)
- Thumb-zone optimization for mobile navigation

#### **Responsive Navigation**

```typescript
// Desktop: Sidebar navigation
// Tablet: Collapsible sidebar
// Mobile: Bottom tab navigation or hamburger menu

const useResponsiveNavigation = () => {
  const [screenSize, setScreenSize] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');

  useEffect(() => {
    const updateScreenSize = () => {
      if (window.innerWidth < 768) setScreenSize('mobile');
      else if (window.innerWidth < 1024) setScreenSize('tablet');
      else setScreenSize('desktop');
    };

    updateScreenSize();
    window.addEventListener('resize', updateScreenSize);
    return () => window.removeEventListener('resize', updateScreenSize);
  }, []);

  return screenSize;
};
```

#### **Content Adaptation**

- **Tables**: Horizontal scroll or stack on mobile
- **Forms**: Single-column layout on mobile
- **Cards**: Responsive grid with proper spacing
- **Images**: Responsive with proper aspect ratios
- **Typography**: Fluid typography scaling

### **Touch Interaction Standards**

- **Minimum Touch Target**: 44x44px
- **Gesture Support**: Swipe, pinch, tap, long press
- **Visual Feedback**: Immediate response to touch
- **Accessibility**: Screen reader compatible

---

## ✅ **Production Readiness Checklist**

### **🔒 Security Requirements**

- [ ] Multi-factor authentication implemented
- [ ] HTTPS/TLS encryption enforced
- [ ] Security headers configured
- [ ] Input validation and sanitization
- [ ] CSRF protection enabled
- [ ] XSS prevention measures
- [ ] SQL injection protection
- [ ] Rate limiting implemented
- [ ] Audit logging enabled
- [ ] Sensitive data encryption

### **⚡ Performance Requirements**

- [ ] First Contentful Paint < 1.5s
- [ ] Largest Contentful Paint < 2.5s
- [ ] Cumulative Layout Shift < 0.1
- [ ] Time to Interactive < 3.5s
- [ ] Bundle size optimized (< 200KB gzipped)
- [ ] Image optimization implemented
- [ ] Lazy loading for non-critical resources
- [ ] Service Worker for caching
- [ ] CDN integration configured

### **🧪 Testing Requirements**

- [ ] Unit tests (>80% coverage)
- [ ] Integration tests for critical paths
- [ ] E2E tests for user workflows
- [ ] Accessibility testing (WCAG 2.1 AA)
- [ ] Cross-browser compatibility testing
- [ ] Mobile device testing
- [ ] Performance testing
- [ ] Security penetration testing
- [ ] Load testing for expected traffic

### **📱 Progressive Web App (PWA)**

- [ ] Web App Manifest configured
- [ ] Service Worker implemented
- [ ] Offline functionality
- [ ] App-like experience
- [ ] Install prompt implementation
- [ ] Push notification support
- [ ] Background sync capability

### **♿ Accessibility Requirements**

- [ ] WCAG 2.1 AA compliance
- [ ] Screen reader compatibility
- [ ] Keyboard navigation support
- [ ] Focus management
- [ ] Alt text for images
- [ ] Proper heading hierarchy
- [ ] Color contrast ratios met
- [ ] Form labels and descriptions

### **📊 Monitoring & Observability**

- [ ] Error tracking (Sentry/similar)
- [ ] Performance monitoring (Core Web Vitals)
- [ ] User analytics (privacy-compliant)
- [ ] Uptime monitoring
- [ ] Real User Monitoring (RUM)
- [ ] Business metrics tracking
- [ ] Security event monitoring

---

## 💻 **Code Standards**

### **Technology Stack**

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + CSS Modules
- **State Management**: Zustand (preferred) or React Query
- **Testing**: Jest + React Testing Library + Playwright
- **Linting**: ESLint + Prettier
- **Build**: Turbo (monorepo optimization)

### **File Organization**

```
src/
├── app/                     # Next.js App Router
│   ├── (protected)/        # Route groups
│   ├── globals.css         # Global styles
│   ├── layout.tsx          # Root layout
│   └── page.tsx            # Home page
├── components/             # React components
│   ├── ui/                # Reusable UI components
│   ├── forms/             # Form components
│   ├── layout/            # Layout components
│   └── features/          # Feature-specific components
├── hooks/                 # Custom React hooks
├── lib/                   # Utility functions
├── stores/                # State management
├── types/                 # TypeScript definitions
└── utils/                 # Helper functions
```

### **Component Standards**

```typescript
// Component Template
interface ComponentProps {
  // Props with proper typing
}

export function ComponentName({
  prop1,
  prop2
}: ComponentProps) {
  // Component implementation

  return (
    <div className="component-styles">
      {/* JSX content */}
    </div>
  );
}

// Export with proper naming
export default ComponentName;
```

### **TypeScript Standards**

```typescript
// Strict TypeScript configuration required
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitAny": true
  }
}
```

---

## 🧪 **Testing Requirements**

### **Test Coverage Standards**

- **Unit Tests**: Minimum 80% code coverage
- **Integration Tests**: Critical user workflows
- **E2E Tests**: Complete user journeys
- **Accessibility Tests**: Automated a11y checks
- **Performance Tests**: Core Web Vitals monitoring

### **Testing Framework Configuration**

```typescript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx}'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  }
};
```

### **E2E Testing Standards**

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] }
    }
  ]
});
```

---

## ⚡ **Performance Standards**

### **Core Web Vitals Targets**

- **Largest Contentful Paint (LCP)**: < 2.5 seconds
- **First Input Delay (FID)**: < 100 milliseconds
- **Cumulative Layout Shift (CLS)**: < 0.1
- **First Contentful Paint (FCP)**: < 1.8 seconds
- **Time to Interactive (TTI)**: < 3.5 seconds

### **Bundle Size Optimization**

```typescript
// next.config.js optimization
const nextConfig = {
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production'
  },
  experimental: {
    optimizeCss: true,
    swcMinify: true
  },
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 31536000 // 1 year
  },
  webpack: (config) => {
    config.optimization.splitChunks = {
      chunks: 'all',
      cacheGroups: {
        default: false,
        vendors: false,
        vendor: {
          name: 'vendor',
          chunks: 'all',
          test: /node_modules/
        }
      }
    };
    return config;
  }
};
```

### **Performance Monitoring**

```typescript
// Performance monitoring implementation
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics(metric: any) {
  // Send metrics to monitoring service
  analytics.track('Web Vital', {
    name: metric.name,
    value: metric.value,
    id: metric.id
  });
}

// Track all Core Web Vitals
getCLS(sendToAnalytics);
getFID(sendToAnalytics);
getFCP(sendToAnalytics);
getLCP(sendToAnalytics);
getTTFB(sendToAnalytics);
```

---

## 🔐 **Security Standards**

### **Content Security Policy (CSP)**

```typescript
// Strict CSP configuration
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline' https://trusted-cdn.com;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  img-src 'self' blob: data: https://trusted-images.com;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://api.dotmac.app;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
`;
```

### **Input Validation Standards**

```typescript
// Zod schema validation example
import { z } from 'zod';

const customerSchema = z.object({
  name: z.string().min(2).max(100).regex(/^[a-zA-Z\s]+$/),
  email: z.string().email(),
  phone: z.string().regex(/^\+?[1-9]\d{1,14}$/),
  address: z.string().min(10).max(200)
});

// Form validation with sanitization
const validateAndSanitize = (input: unknown) => {
  const result = customerSchema.safeParse(input);
  if (!result.success) {
    throw new ValidationError(result.error.issues);
  }
  return result.data;
};
```

### **Authentication Flow Security**

```typescript
// Secure authentication implementation
interface AuthFlowConfig {
  maxLoginAttempts: 5;
  lockoutDuration: 30; // minutes
  sessionTimeout: 480; // minutes
  tokenRotationInterval: 15; // minutes
  mfaRequired: true;
  passwordHistoryCount: 5;
  sessionConcurrencyLimit: 3;
}
```

---

## 📋 **Implementation Checklist**

### **Phase 1: Critical Fixes** (Week 1)

- [ ] **Customer Portal**: Replace alert() with toast notifications
- [ ] **Customer Portal**: Implement missing essential pages
- [ ] **Admin Portal**: Add proper navigation structure
- [ ] **Tenant Portal**: Implement basic dashboard functionality
- [ ] **Reseller Portal**: Add commission tracking pages

### **Phase 2: Production Readiness** (Week 2-3)

- [ ] **All Portals**: Implement comprehensive error boundaries
- [ ] **All Portals**: Add loading states and skeleton screens
- [ ] **All Portals**: Enhance mobile responsiveness
- [ ] **All Portals**: Implement MFA authentication
- [ ] **All Portals**: Add comprehensive test coverage

### **Phase 3: Enhancement** (Week 4-6)

- [ ] **All Portals**: PWA capabilities and offline support
- [ ] **All Portals**: Performance optimization to meet Core Web Vitals
- [ ] **All Portals**: Accessibility compliance (WCAG 2.1 AA)
- [ ] **All Portals**: Advanced security features
- [ ] **All Portals**: Analytics and monitoring integration

### **Phase 4: Standardization** (Week 7-8)

- [ ] **Design System**: Create unified component library
- [ ] **Documentation**: Complete API documentation for all portals
- [ ] **Testing**: Achieve 80%+ test coverage across all portals
- [ ] **Deployment**: Production-ready CI/CD pipelines
- [ ] **Monitoring**: Comprehensive observability stack

---

## 📚 **References and Resources**

### **Internal Documentation**

- [Architecture Documentation](./ARCHITECTURE.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Testing Strategy](./AI_FIRST_TESTING_STRATEGY.md)

### **External Standards**

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Core Web Vitals](https://web.dev/vitals/)
- [Next.js Best Practices](https://nextjs.org/docs/basic-features/pages)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)

### **Security References**

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Security Headers](https://securityheaders.com/)

---

## 📅 **Maintenance and Updates**

This document should be reviewed and updated:

- **Monthly**: Review implementation status and update checklists
- **Quarterly**: Update technology stack recommendations
- **Annually**: Comprehensive review of all standards

### **Change Management Process**

1. **Proposal**: Submit changes via pull request
2. **Review**: Architecture team review and approval
3. **Implementation**: Gradual rollout across portals
4. **Documentation**: Update this document with approved changes

---

**Document Owner**: Platform Architecture Team
**Next Review Date**: 2025-02-29
**Distribution**: All frontend developers, QA engineers, product managers

---

*This document serves as the definitive guide for all DotMac Framework frontend portal development. Adherence to these standards ensures consistent, secure, and maintainable applications across the platform.*
