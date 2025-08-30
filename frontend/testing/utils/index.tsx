/**
 * DRY Test Utilities - Shared across all frontend applications.
 * Eliminates code duplication in test files.
 */

import React, { ReactElement, ReactNode, ComponentType } from 'react';
import { render, screen, waitFor, fireEvent, within, RenderOptions } from '@testing-library/react';
import userEvent, { UserEvent } from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, BrowserRouterProps } from 'react-router-dom';
import { ThemeProvider, DefaultTheme } from 'styled-components';

// Import shared theme and contexts
import { defaultTheme } from '@dotmac/styled-components';

// Types for our testing utilities
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
  routerProps?: BrowserRouterProps;
  queryClient?: QueryClient;
  theme?: DefaultTheme;
  wrapper?: ComponentType<{ children: ReactNode }>;
}

interface RenderResult extends ReturnType<typeof render> {
  queryClient: QueryClient;
  user: UserEvent;
}

interface FieldData {
  [key: string]: string;
}

interface FormUtils {
  fillField(labelText: string, value: string, options?: any): Promise<HTMLElement>;
  fillForm(fieldData: FieldData): Promise<Record<string, HTMLElement>>;
  submitForm(buttonText?: string): Promise<HTMLElement>;
  expectFieldError(fieldLabel: string, errorMessage?: string): void;
}

interface User {
  id: string;
  email: string;
  role: string;
  tenantId: string;
}

interface Tenant {
  id: string;
  name: string;
}

/**
 * Create a new QueryClient for testing
 */
export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        cacheTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

/**
 * DRY wrapper for rendering components with common providers
 */
export const renderWithProviders = (
  ui: ReactElement,
  {
    // Router options
    initialRoute = '/',
    routerProps = {},

    // Query client options
    queryClient = createTestQueryClient(),

    // Theme options
    theme = defaultTheme,

    // Additional providers
    wrapper: WrapperComponent,

    // Render options
    ...renderOptions
  }: CustomRenderOptions = {}
): RenderResult => {
  // Set initial route
  if (initialRoute !== '/') {
    window.history.pushState({}, 'Test page', initialRoute);
  }

  function AllTheProviders({ children }: { children: ReactNode }) {
    let content = (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter {...routerProps}>
          <ThemeProvider theme={theme}>
            {children}
          </ThemeProvider>
        </BrowserRouter>
      </QueryClientProvider>
    );

    if (WrapperComponent) {
      content = <WrapperComponent>{content}</WrapperComponent>;
    }

    return content;
  }

  const renderResult = render(ui, {
    wrapper: AllTheProviders,
    ...renderOptions,
  });

  return {
    ...renderResult,
    queryClient,
    user: userEvent.setup(), // Pre-configured user interactions
  };
};

/**
 * DRY form testing utilities
 */
export const formUtils = {
  // Fill form field by label
  async fillField(labelText: string, value: string, options: any = {}): Promise<HTMLElement> {
    const field = screen.getByLabelText(labelText, options);
    await userEvent.clear(field);
    await userEvent.type(field, value);
    return field;
  },

  // Fill multiple form fields
  async fillForm(fieldData: FieldData): Promise<Record<string, HTMLElement>> {
    const fields: Record<string, HTMLElement> = {};
    for (const [label, value] of Object.entries(fieldData)) {
      fields[label] = await this.fillField(label, value);
    }
    return fields;
  },

  // Submit form by button text or test ID
  async submitForm(buttonText: string = 'Submit'): Promise<HTMLElement> {
    const submitButton = screen.getByRole('button', { name: new RegExp(buttonText, 'i') });
    await userEvent.click(submitButton);
    return submitButton;
  },

  // Validate form errors
  expectFieldError(fieldLabel: string, errorMessage?: string): void {
    const field = screen.getByLabelText(fieldLabel);
    expect(field).toBeInvalid();
    if (errorMessage) {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    }
  }
};

/**
 * DRY API testing utilities
 */
export const apiUtils = {
  // Wait for loading states
  async waitForLoadingToFinish(): Promise<void> {
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  },

  // Wait for API calls
  async waitForApiCall(expectedCalls: number = 1): Promise<void> {
    await waitFor(() => {
      // This can be customized based on your API mocking setup
      expect(fetch).toHaveBeenCalledTimes(expectedCalls);
    });
  },

  // Assert error states
  expectErrorMessage(message: string): void {
    expect(screen.getByRole('alert')).toHaveTextContent(message);
  }
};

/**
 * DRY navigation testing utilities
 */
export const navigationUtils = {
  // Navigate and wait for route change
  async navigateToRoute(path: string): Promise<void> {
    window.history.pushState({}, 'Test page', path);
    await waitFor(() => {
      expect(window.location.pathname).toBe(path);
    });
  },

  // Click link and verify navigation
  async clickLinkAndVerify(linkText: string, expectedPath: string): Promise<void> {
    const link = screen.getByRole('link', { name: linkText });
    await userEvent.click(link);
    await waitFor(() => {
      expect(window.location.pathname).toBe(expectedPath);
    });
  }
};

/**
 * DRY accessibility testing utilities
 */
export const a11yUtils = {
  // Check for basic accessibility violations
  async expectNoA11yViolations(container: Element): Promise<void> {
    const { axe, toHaveNoViolations } = await import('jest-axe');
    expect.extend(toHaveNoViolations);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  },

  // Verify keyboard navigation
  async testKeyboardNavigation(elements: HTMLElement[]): Promise<void> {
    for (const element of elements) {
      element.focus();
      expect(element).toHaveFocus();
      await userEvent.keyboard('{Tab}');
    }
  }
};

/**
 * DRY component state testing
 */
export const componentUtils = {
  // Test component with different props
  testWithProps<P extends Record<string, any>>(
    Component: ComponentType<P>,
    propsVariations: P[],
    testFn: (container: Element, props: P) => void
  ): void {
    propsVariations.forEach((props, index) => {
      test(`renders correctly with props variation ${index + 1}`, () => {
        const { container } = renderWithProviders(<Component {...props} />);
        testFn(container, props);
      });
    });
  },

  // Test responsive behavior
  testResponsive<P extends Record<string, any>>(
    Component: ComponentType<P>,
    props: P = {} as P
  ): void {
    const breakpoints = [
      { width: 320, name: 'mobile' },
      { width: 768, name: 'tablet' },
      { width: 1024, name: 'desktop' }
    ];

    breakpoints.forEach(({ width, name }) => {
      test(`renders correctly on ${name} (${width}px)`, () => {
        Object.defineProperty(window, 'innerWidth', {
          writable: true,
          configurable: true,
          value: width,
        });

        window.dispatchEvent(new Event('resize'));

        const { container } = renderWithProviders(<Component {...props} />);
        expect(container).toBeInTheDocument();
      });
    });
  }
};

/**
 * DRY portal-specific testing utilities
 */
export const portalUtils = {
  // Mock portal authentication
  mockPortalAuth(portal: string = 'admin', user: Partial<User> = {}): User {
    const defaultUser: User = {
      id: 'test-user-id',
      email: 'test@example.com',
      role: portal === 'admin' ? 'admin' : 'user',
      tenantId: 'test-tenant',
      ...user
    };

    // Mock auth context
    jest.spyOn(require('@dotmac/headless'), 'useAuth').mockReturnValue({
      user: defaultUser,
      isAuthenticated: true,
      isLoading: false,
      login: jest.fn(),
      logout: jest.fn()
    });

    return defaultUser;
  },

  // Test multi-tenant features
  testMultiTenant<P extends Record<string, any>>(
    Component: ComponentType<P>,
    tenantVariations: Tenant[]
  ): void {
    tenantVariations.forEach((tenant) => {
      test(`renders correctly for tenant: ${tenant.name}`, () => {
        const user = this.mockPortalAuth('admin', { tenantId: tenant.id });
        const { container } = renderWithProviders(
          <Component />,
          { wrapper: ({ children }: { children: ReactNode }) => (
            // @ts-ignore - TenantProvider is a mock component for testing
            <TenantProvider tenant={tenant}>{children}</TenantProvider>
          )}
        );
        expect(container).toBeInTheDocument();
      });
    });
  }
};

// Re-export commonly used testing library functions for convenience
export {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
  userEvent
};

// Export grouped utilities
export const testUtils = {
  form: formUtils,
  api: apiUtils,
  navigation: navigationUtils,
  a11y: a11yUtils,
  component: componentUtils,
  portal: portalUtils
};
