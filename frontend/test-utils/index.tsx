/**
 * Test utilities and providers
 * Centralized testing helpers following backend patterns
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type RenderOptions, render } from '@testing-library/react';
import type React from 'react';
import type { ReactElement } from 'react';

import { ConfigProvider, ThemeProvider } from '@dotmac/headless';

// Test configuration
const testConfig = {
  locale: {
    primary: 'en-US',
    supported: ['en-US'],
    fallback: 'en-US',
    dateFormat: {
      short: { month: 'numeric', day: 'numeric', year: 'numeric' },
      medium: { month: 'long', day: 'numeric', year: 'numeric' },
      long: { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' },
      time: { hour: 'numeric', minute: '2-digit' },
    },
  },
  currency: {
    primary: 'USD',
    symbol: '$',
    position: 'before',
    precision: 2,
    thousandsSeparator: ',',
    decimalSeparator: '.',
  },
  business: {
    planTypes: {
      basic: {
        label: 'Basic Plan',
        category: 'residential',
        features: ['25 Mbps', 'WiFi Router'],
      },
      business_pro: {
        label: 'Business Pro',
        category: 'business',
        features: ['100 Mbps', 'Static IP', 'Priority Support'],
      },
      enterprise: {
        label: 'Enterprise',
        category: 'enterprise',
        features: ['Dedicated Line', 'SLA', 'Account Manager'],
      },
    },
    statusTypes: {
      active: {
        label: 'Active',
        color: 'success',
        description: 'Service is active',
      },
      pending: {
        label: 'Pending',
        color: 'warning',
        description: 'Setup in progress',
      },
      suspended: {
        label: 'Suspended',
        color: 'danger',
        description: 'Service suspended',
      },
    },
    partnerTiers: {
      bronze: {
        label: 'Bronze Partner',
        color: 'secondary',
        benefits: ['5% Commission'],
        requirements: { customers: 10, revenue: 5000 },
      },
      silver: {
        label: 'Silver Partner',
        color: 'primary',
        benefits: ['10% Commission', 'Priority Support'],
        requirements: { customers: 25, revenue: 15000 },
      },
    },
    units: {
      bandwidth: 'mbps',
      data: 'gb',
      currency: 'USD',
    },
  },
  branding: {
    company: {
      name: 'Test ISP',
      logo: '/test-logo.svg',
      favicon: '/test-favicon.ico',
      colors: {
        primary: '#3b82f6',
        secondary: '#64748b',
        accent: '#10b981',
      },
    },
    portal: {
      admin: { name: 'Admin Portal', theme: 'professional' },
      customer: { name: 'Customer Portal', theme: 'friendly' },
      reseller: { name: 'Partner Portal', theme: 'business' },
    },
  },
  features: {
    multiTenancy: true,
    advancedAnalytics: false,
    automatedBilling: true,
    apiAccess: false,
    whiteLabel: false,
    customDomains: false,
    ssoIntegration: false,
    mobileApp: false,
  },
  api: {
    baseUrl: '/api',
    version: 'v1',
    timeout: 10000,
    retries: 2,
  },
  monitoring: {
    analytics: false,
    errorReporting: false,
    performanceMonitoring: false,
  },
};

// Create test providers wrapper
interface TestProvidersProps {
  children: React.ReactNode;
  config?: Partial<typeof testConfig>;
  portalType?: 'admin' | 'customer' | 'reseller';
  queryClient?: QueryClient;
}

function TestProviders({
  children,
  config = {
    // Implementation pending
  },
  portalType = 'customer',
  queryClient,
}: TestProvidersProps) {
  const client =
    queryClient ||
    new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          staleTime: 0,
          gcTime: 0,
        },
        mutations: {
          retry: false,
        },
      },
    });

  const finalConfig = { ...testConfig, ...config };

  return (
    <QueryClientProvider client={client}>
      <ConfigProvider initialConfig={finalConfig}>
        <ThemeProvider portalType={portalType}>{children}</ThemeProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

// Custom render function with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  config?: Partial<typeof testConfig>;
  portalType?: 'admin' | 'customer' | 'reseller';
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {
    // Implementation pending
  }
) {
  const { config, portalType, queryClient, ...renderOptions } = options;

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <TestProviders config={config} portalType={portalType} queryClient={queryClient}>
        {children}
      </TestProviders>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

// Test data factories (following backend pattern)
export const factories = {
  user: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    id: `user-${Date.now()}`,
    name: 'Test User',
    email: 'test@user.com',
    role: 'customer',
    tenant: 'tenant-123',
    created_at: new Date().toISOString(),
    ...overrides,
  }),

  customer: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    id: `cust-${Date.now()}`,
    name: 'Test Customer',
    email: 'customer@test.com',
    phone: '+1 (555) 123-4567',
    address: '123 Test St, Test City, TC 12345',
    plan: 'business_pro',
    mrr: 79.99,
    status: 'active',
    join_date: '2024-01-15',
    last_payment: '2024-03-01',
    connection_status: 'online',
    usage: 65.5,
    tenant: 'tenant-123',
    ...overrides,
  }),

  service: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    id: `service-${Date.now()}`,
    name: 'Internet Service',
    type: 'internet',
    status: 'active',
    speed_down: 100,
    speed_up: 20,
    monthly_price: 79.99,
    features: ['WiFi Router', 'Static IP'],
    ...overrides,
  }),

  invoice: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    id: `inv-${Date.now()}`,
    number: `INV-${Date.now()}`,
    amount: 79.99,
    status: 'paid',
    due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    items: [
      {
        description: 'Internet Service',
        amount: 79.99,
        quantity: 1,
      },
    ],
    ...overrides,
  }),

  usageData: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    period: '30d',
    total_download: 850.5,
    total_upload: 120.3,
    average_speed: 95.2,
    peak_usage: new Date().toISOString(),
    daily_data: Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      download: Math.random() * 50 + 20,
      upload: Math.random() * 15 + 5,
    })),
    ...overrides,
  }),

  commission: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    id: `comm-${Date.now()}`,
    month: new Date().toISOString().slice(0, 7),
    amount: 150.75,
    status: 'pending',
    customers_count: 12,
    revenue: 1507.5,
    tier: 'silver',
    ...overrides,
  }),
};

// Mock API response helpers
export const mockResponses = {
  success: (data: unknown) => ({
    data,
    meta: {
      total: Array.isArray(data) ? data.length : 1,
      page: 1,
      per_page: 10,
    },
  }),

  error: (message: string, status = 400) => ({
    error: {
      message,
      status,
      timestamp: new Date().toISOString(),
    },
  }),

  paginated: (data: unknown[], page = 1, perPage = 10) => ({
    data: data.slice((page - 1) * perPage, page * perPage),
    meta: {
      total: data.length,
      page,
      per_page: perPage,
      total_pages: Math.ceil(data.length / perPage),
    },
  }),
};

// Utility functions
export const testUtils = {
  // Wait for async operations
  waitFor: (condition: () => boolean, timeout = 5000) => {
    return new Promise((resolve, _reject) => {
      const start = Date.now();
      const check = () => {
        if (condition()) {
          resolve(true);
        } else if (Date.now() - start > timeout) {
          reject(new Error('Timeout waiting for condition'));
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  },

  // Delay helper
  delay: (ms: number) => new Promise((resolve) => setTimeout(resolve, ms)),

  // Mock localStorage
  mockLocalStorage: () => {
    const store: Record<string, string> = {
      // Implementation pending
    };
    return {
      getItem: jest.fn((key: string) => store[key] || null),
      setItem: jest.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: jest.fn((key: string) => {
        delete store[key];
      }),
      clear: jest.fn(() => {
        Object.keys(store).forEach((key) => delete store[key]);
      }),
    };
  },

  // Create mock router
  mockRouter: (
    overrides = {
      // Implementation pending
    }
  ) => ({
    push: jest.fn(),
    replace: jest.fn(),
    reload: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    prefetch: jest.fn(),
    route: '/',
    pathname: '/',
    query: {
      // Implementation pending
    },
    asPath: '/',
    events: {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn(),
    },
    ...overrides,
  }),
};

export * from '@testing-library/jest-dom';
// Re-export testing library utilities
export * from '@testing-library/react';

// Export custom render as default render
export { renderWithProviders as render };
