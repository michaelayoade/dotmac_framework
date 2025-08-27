/**
 * Enhanced test utilities for React Testing Library with custom providers
 */
import { render, RenderOptions } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { ReactElement } from 'react';

// Mock authentication context
interface MockAuthContextValue {
  user: {
    id: string;
    name: string;
    email: string;
    accountNumber: string;
    portalType: 'customer';
  } | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: jest.MockedFunction<any>;
  logout: jest.MockedFunction<any>;
  refreshUser: jest.MockedFunction<any>;
}

const defaultAuthValue: MockAuthContextValue = {
  user: {
    id: 'test-user-1',
    name: 'Test User',
    email: 'test@example.com',
    accountNumber: 'ACC123456',
    portalType: 'customer'
  },
  isLoading: false,
  isAuthenticated: true,
  login: jest.fn(),
  logout: jest.fn(),
  refreshUser: jest.fn(),
};

const AuthContext = React.createContext<MockAuthContextValue>(defaultAuthValue);

export const MockAuthProvider = ({ 
  children, 
  value = defaultAuthValue 
}: { 
  children: React.ReactNode;
  value?: Partial<MockAuthContextValue>;
}) => {
  const authValue = { ...defaultAuthValue, ...value };
  return (
    <AuthContext.Provider value={authValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Mock the actual auth provider
jest.mock('../components/auth/SecureAuthProvider', () => ({
  useSecureAuth: () => React.useContext(AuthContext),
  SecureAuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuthActions: () => ({
    login: jest.fn(),
    logout: jest.fn(),
    refreshUser: jest.fn(),
  }),
  useAuthenticationStatus: () => ({
    isAuthenticated: true,
    isLoading: false,
    user: defaultAuthValue.user,
    hasValidSession: true,
  }),
}));

// Create a custom render function with all providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authValue?: Partial<MockAuthContextValue>;
  queryClient?: QueryClient;
  initialEntries?: string[];
}

function AllTheProviders({ 
  children, 
  authValue = {},
  queryClient 
}: { 
  children: React.ReactNode;
  authValue?: Partial<MockAuthContextValue>;
  queryClient?: QueryClient;
}) {
  const client = queryClient || new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return (
    <QueryClientProvider client={client}>
      <MockAuthProvider value={authValue}>
        {children}
      </MockAuthProvider>
    </QueryClientProvider>
  );
}

export function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { authValue, queryClient, ...renderOptions } = options;
  
  return {
    user: userEvent.setup(),
    ...render(ui, {
      wrapper: (props) => (
        <AllTheProviders 
          authValue={authValue}
          queryClient={queryClient}
          {...props} 
        />
      ),
      ...renderOptions,
    }),
  };
}

// Re-export everything
export * from '@testing-library/react';
export { customRender as render };

// Mock data generators
export const createMockNetworkStatus = (overrides = {}) => ({
  connectionStatus: 'connected',
  currentSpeed: {
    download: 100,
    upload: 10
  },
  uptime: 99.9,
  latency: 15,
  ...overrides
});

export const createMockUsageData = (overrides = {}) => ({
  current: 450,
  limit: 1000,
  history: [
    { date: '2024-01-01', download: 10, upload: 2, total: 12 },
    { date: '2024-01-02', download: 15, upload: 3, total: 18 },
    { date: '2024-01-03', download: 20, upload: 5, total: 25 },
  ],
  ...overrides
});

export const createMockCustomerData = (overrides = {}) => ({
  account: {
    id: 'acc-123',
    name: 'John Doe',
    number: 'ACC123456',
    type: 'residential'
  },
  networkStatus: createMockNetworkStatus(),
  services: [{
    id: 'svc-1',
    type: 'internet',
    status: 'active',
    usage: createMockUsageData()
  }],
  billing: {
    balance: 89.99,
    nextDueDate: '2024-02-15',
    isOverdue: false,
    autopay: { enabled: true },
    daysUntilDue: 15
  },
  ...overrides
});

export const createMockNotification = (overrides = {}) => ({
  id: `notif-${Date.now()}`,
  type: 'info' as const,
  title: 'Test Notification',
  message: 'This is a test notification',
  timestamp: new Date().toISOString(),
  ...overrides
});

// API mocking utilities
export const mockApiCall = <T,>(data: T, delay = 0): Promise<T> => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(data), delay);
  });
};

export const mockApiError = (message = 'API Error', status = 500) => {
  const error = new Error(message) as any;
  error.status = status;
  return Promise.reject(error);
};

// Performance testing utilities
export const measureRenderTime = async (renderFn: () => void) => {
  const start = performance.now();
  renderFn();
  await new Promise(resolve => setTimeout(resolve, 0)); // Wait for render
  const end = performance.now();
  return end - start;
};

export const waitForLoadingToFinish = async () => {
  // Wait for any loading spinners to disappear
  const { queryByRole } = await import('@testing-library/react');
  await new Promise(resolve => {
    const checkForLoading = () => {
      if (!document.querySelector('[data-testid="loading"]') && 
          !document.querySelector('.animate-spin')) {
        resolve(true);
      } else {
        setTimeout(checkForLoading, 50);
      }
    };
    checkForLoading();
  });
};

// Custom matchers
export const expectToBeLoading = (element: HTMLElement) => {
  expect(element).toHaveAttribute('data-testid', 'loading');
};

export const expectToHaveError = (container: HTMLElement, errorText?: string) => {
  const errorElement = container.querySelector('[role="alert"]') || 
                      container.querySelector('.text-red-600') ||
                      container.querySelector('[data-testid="error"]');
  
  expect(errorElement).toBeInTheDocument();
  
  if (errorText) {
    expect(errorElement).toHaveTextContent(errorText);
  }
};

// Mock intersection observer for lazy loading tests
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock ResizeObserver
window.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});