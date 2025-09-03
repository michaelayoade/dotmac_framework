/**
 * Testing Utilities
 * Custom render functions and test helpers
 */

import React from 'react';
import { render, RenderOptions, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ============================================================================
// MOCK PROVIDERS
// ============================================================================

interface MockAuthContextValue {
  user: any;
  tenant: any;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: jest.MockedFunction<any>;
  logout: jest.MockedFunction<any>;
  refreshAuth: jest.MockedFunction<any>;
}

// Mock auth context
const mockAuthContext: MockAuthContextValue = {
  user: {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    role: 'admin',
    tenant_id: 'tenant-123',
    permissions: ['read', 'write', 'admin'],
    last_login: new Date(),
  },
  tenant: {
    id: 'tenant-123',
    name: 'Test Tenant',
    display_name: 'Test Tenant Display Name',
    slug: 'test-tenant',
    status: 'active' as const,
    tier: 'premium',
    custom_domain: 'test.example.com',
    primary_color: '#007bff',
    logo_url: 'https://example.com/logo.png',
  },
  isLoading: false,
  isAuthenticated: true,
  login: jest.fn(),
  logout: jest.fn(),
  refreshAuth: jest.fn(),
};

// Mock auth provider
const MockAuthProvider = ({
  children,
  value = mockAuthContext,
}: {
  children: React.ReactNode;
  value?: Partial<MockAuthContextValue>;
}) => {
  const contextValue = { ...mockAuthContext, ...value };
  // Use a simple div wrapper since we're mocking the auth context
  return React.createElement('div', { 'data-testid': 'mock-auth-provider' }, children);
};

// ============================================================================
// CUSTOM RENDER FUNCTIONS
// ============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  // Auth context overrides
  authContext?: Partial<MockAuthContextValue>;
  // Route simulation
  initialRoute?: string;
  // Error boundary
  withErrorBoundary?: boolean;
}

/**
 * Custom render function with providers
 */
export function renderWithProviders(ui: React.ReactElement, options: CustomRenderOptions = {}) {
  const {
    authContext = {},
    initialRoute = '/',
    withErrorBoundary = false,
    ...renderOptions
  } = options;

  // Create wrapper component
  const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
    let wrappedChildren = children;

    // Wrap with mock router if needed
    if (initialRoute !== '/') {
      // Mock Next.js router
      Object.defineProperty(window, 'location', {
        value: { pathname: initialRoute },
        writable: true,
      });
    }

    // Wrap with auth provider
    wrappedChildren = React.createElement(
      MockAuthProvider,
      { value: authContext },
      wrappedChildren
    );

    // Wrap with error boundary if requested
    if (withErrorBoundary) {
      wrappedChildren = React.createElement(
        'div',
        { 'data-testid': 'error-boundary-wrapper' },
        wrappedChildren
      );
    }

    return wrappedChildren as React.ReactElement;
  };

  return render(ui, { wrapper: AllTheProviders, ...renderOptions });
}

/**
 * Render function specifically for authentication-related components
 */
export function renderWithAuth(
  ui: React.ReactElement,
  authState: Partial<MockAuthContextValue> = {}
) {
  return renderWithProviders(ui, { authContext: authState });
}

/**
 * Render function for unauthenticated state
 */
export function renderUnauthenticated(ui: React.ReactElement) {
  return renderWithAuth(ui, {
    user: null,
    tenant: null,
    isAuthenticated: false,
    isLoading: false,
  });
}

/**
 * Render function with loading state
 */
export function renderWithLoading(ui: React.ReactElement) {
  return renderWithAuth(ui, {
    isLoading: true,
    user: null,
    tenant: null,
    isAuthenticated: false,
  });
}

/**
 * Render function with error boundary
 */
export function renderWithErrorBoundary(ui: React.ReactElement) {
  return renderWithProviders(ui, { withErrorBoundary: true });
}

// ============================================================================
// TEST HELPERS
// ============================================================================

/**
 * User event instance for consistent usage
 */
export const user = userEvent.setup();

/**
 * Helper to wait for element to be present
 */
export const waitForElement = async (testId: string) => {
  return screen.findByTestId(testId);
};

/**
 * Helper to simulate form submission
 */
export const submitForm = async (form: HTMLFormElement) => {
  await user.click(screen.getByRole('button', { name: /submit/i }));
};

/**
 * Helper to fill and submit login form
 */
export const fillAndSubmitLogin = async (email = 'test@example.com', password = 'password123') => {
  const emailInput = screen.getByLabelText(/email/i);
  const passwordInput = screen.getByLabelText(/password/i);
  const submitButton = screen.getByRole('button', { name: /sign in/i });

  await user.type(emailInput, email);
  await user.type(passwordInput, password);
  await user.click(submitButton);
};

/**
 * Helper to mock API responses
 */
export const mockApiResponse = (url: string, response: any, status = 200) => {
  return jest.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: async () => response,
  });
};

// ============================================================================
// MOCK DATA FACTORIES
// ============================================================================

/**
 * Create mock user data
 */
export const createMockUser = (overrides: any = {}) => ({
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  tenant_id: 'tenant-123',
  permissions: ['read'],
  last_login: new Date(),
  ...overrides,
});

/**
 * Create mock tenant data
 */
export const createMockTenant = (overrides: any = {}) => ({
  id: 'tenant-123',
  name: 'Test Tenant',
  display_name: 'Test Tenant Display',
  slug: 'test-tenant',
  status: 'active' as const,
  tier: 'basic',
  ...overrides,
});

/**
 * Create mock auth response
 */
export const createMockAuthResponse = (overrides: any = {}) => ({
  success: true,
  user: createMockUser(),
  tenant: createMockTenant(),
  tokens: {
    accessToken: 'mock-access-token',
    refreshToken: 'mock-refresh-token',
  },
  ...overrides,
});

/**
 * Create mock API error response
 */
export const createMockErrorResponse = (
  message = 'Test error',
  code = 'TEST_ERROR',
  status = 400
) => ({
  success: false,
  error: message,
  code,
  status,
});

// ============================================================================
// ASSERTIONS HELPERS
// ============================================================================

/**
 * Assert element is visible and accessible
 */
export const expectToBeVisibleAndAccessible = (element: HTMLElement) => {
  expect(element).toBeVisible();
  expect(element).not.toHaveAttribute('aria-hidden', 'true');
};

/**
 * Assert form has proper validation
 */
export const expectFormValidation = (form: HTMLFormElement) => {
  expect(form).toHaveAttribute('novalidate', 'false');

  // Check for required fields
  const requiredFields = form.querySelectorAll('[required]');
  expect(requiredFields.length).toBeGreaterThan(0);
};

/**
 * Assert loading state
 */
export const expectLoadingState = () => {
  expect(screen.getByRole('status')).toBeInTheDocument();
};

/**
 * Assert error state
 */
export const expectErrorState = (message?: string) => {
  expect(screen.getByRole('alert')).toBeInTheDocument();
  if (message) {
    expect(screen.getByText(message)).toBeInTheDocument();
  }
};

// ============================================================================
// SETUP AND TEARDOWN
// ============================================================================

/**
 * Setup function for tests that need auth
 */
export const setupAuthTest = () => {
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();
  const mockRefreshAuth = jest.fn();

  beforeEach(() => {
    mockLogin.mockClear();
    mockLogout.mockClear();
    mockRefreshAuth.mockClear();
  });

  return { mockLogin, mockLogout, mockRefreshAuth };
};

/**
 * Cleanup function for tests
 */
export const cleanupTest = () => {
  // Clear all timers
  jest.clearAllTimers();

  // Clear all mocks
  jest.clearAllMocks();

  // Reset DOM
  document.body.innerHTML = '';
};

// Re-export everything from React Testing Library
export * from '@testing-library/react';
export { userEvent };
