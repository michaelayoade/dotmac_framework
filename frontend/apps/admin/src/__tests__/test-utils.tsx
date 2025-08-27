/**
 * Testing Utilities - Comprehensive testing setup for React components
 * Provides custom render functions with providers and testing helpers
 */

import React, { type ReactElement, type ReactNode } from 'react';
import { render as rtlRender, type RenderOptions, type RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BillingErrorBoundary } from '../components/error/ErrorBoundary';
import { GlobalErrorProvider } from '../components/error/GlobalErrorProvider';

// Custom render options
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  withErrorBoundary?: boolean;
  withQueryClient?: boolean;
  queryClient?: QueryClient;
  initialState?: any;
}

// Test providers wrapper
function TestProvidersWrapper({ 
  children, 
  withErrorBoundary = false,
  withQueryClient = false,
  queryClient
}: {
  children: ReactNode;
  withErrorBoundary?: boolean;
  withQueryClient?: boolean;
  queryClient?: QueryClient;
}) {
  // Create default query client for testing
  const defaultQueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0, // Updated from cacheTime in React Query v5
      },
    },
  });

  const testQueryClient = queryClient || defaultQueryClient;

  let wrapper = children;

  // Add Query Client Provider if requested
  if (withQueryClient) {
    wrapper = (
      <QueryClientProvider client={testQueryClient}>
        {wrapper}
      </QueryClientProvider>
    );
  }

  // Add Error Boundary if requested
  if (withErrorBoundary) {
    wrapper = (
      <GlobalErrorProvider>
        <BillingErrorBoundary>
          {wrapper}
        </BillingErrorBoundary>
      </GlobalErrorProvider>
    );
  }

  return <>{wrapper}</>;
}

// Custom render function
export function render(
  ui: ReactElement,
  options: CustomRenderOptions = {}
): RenderResult {
  const {
    withErrorBoundary = false,
    withQueryClient = false,
    queryClient,
    ...renderOptions
  } = options;

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <TestProvidersWrapper
      withErrorBoundary={withErrorBoundary}
      withQueryClient={withQueryClient}
      queryClient={queryClient}
    >
      {children}
    </TestProvidersWrapper>
  );

  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
}

// Render with all providers (convenience function)
export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  return render(ui, {
    withErrorBoundary: true,
    withQueryClient: true,
    ...options,
  });
}

// Mock API responses
export const mockApiResponses = {
  invoices: {
    success: true,
    data: [
      {
        id: 'inv-001',
        customerName: 'Test Customer',
        customerEmail: 'test@example.com',
        total: 100.00,
        status: 'pending',
        dueDate: '2025-01-15',
        lastReminderSent: null,
      },
    ],
  },
  
  payments: {
    success: true,
    data: [
      {
        id: 'pay-001',
        invoiceId: 'inv-001',
        amount: 100.00,
        status: 'completed',
        paymentDate: '2025-01-10',
        method: 'credit_card',
      },
    ],
  },

  metrics: {
    success: true,
    data: {
      totalRevenue: 10000,
      collectionsRate: 95.5,
      averageInvoiceValue: 250.00,
      paymentFailureRate: 2.1,
      chartData: {
        revenue: [
          { month: 'Jan', amount: 5000 },
          { month: 'Feb', amount: 5000 },
        ],
        paymentMethods: [
          { method: 'Credit Card', percentage: 65, amount: 6500 },
          { method: 'Bank Transfer', percentage: 30, amount: 3000 },
          { method: 'Cash', percentage: 5, amount: 500 },
        ],
      },
    },
  },

  error: {
    success: false,
    error: 'Test error message',
    code: 'TEST_ERROR',
    statusCode: 400,
  },
};

// Mock fetch function
export function mockFetch(responses: Record<string, any> = {}) {
  const defaultResponses = {
    '/api/billing/invoices': mockApiResponses.invoices,
    '/api/billing/payments': mockApiResponses.payments,
    '/api/billing/metrics': mockApiResponses.metrics,
    '/api/billing/reports': { success: true, data: [] },
  };

  const allResponses = { ...defaultResponses, ...responses };

  global.fetch = jest.fn().mockImplementation((url: string) => {
    const endpoint = url.replace(/^.*\/api/, '/api');
    const response = allResponses[endpoint] || mockApiResponses.error;
    
    return Promise.resolve({
      ok: response.success,
      status: response.success ? 200 : (response.statusCode || 400),
      json: () => Promise.resolve(response),
      blob: () => Promise.resolve(new Blob(['test file'])),
    });
  });

  return global.fetch as jest.MockedFunction<typeof fetch>;
}

// Clear all mocks
export function clearAllMocks() {
  jest.clearAllMocks();
  if (global.fetch && 'mockClear' in global.fetch) {
    (global.fetch as jest.MockedFunction<typeof fetch>).mockClear();
  }
}

// Wait for async operations
export async function waitForLoadingToFinish() {
  const { waitFor } = await import('@testing-library/react');
  return waitFor(() => {
    expect(document.querySelector('[data-testid="loading"]')).not.toBeInTheDocument();
  }, { timeout: 5000 });
}

// Custom matchers for better testing
export const customMatchers = {
  toBeLoading: (received: HTMLElement) => {
    const isLoading = received.hasAttribute('data-loading') || 
                     received.classList.contains('loading') ||
                     received.querySelector('[data-testid="loading-spinner"]') !== null;
    
    return {
      message: () => `expected element ${isLoading ? 'not ' : ''}to be loading`,
      pass: isLoading,
    };
  },

  toHaveErrorMessage: (received: HTMLElement, expectedMessage?: string) => {
    const errorElement = received.querySelector('[role="alert"], .error-message, [data-testid="error"]');
    const hasError = errorElement !== null;
    
    if (expectedMessage && hasError) {
      const actualMessage = errorElement?.textContent || '';
      const messageMatches = actualMessage.includes(expectedMessage);
      
      return {
        message: () => `expected error message "${actualMessage}" to contain "${expectedMessage}"`,
        pass: messageMatches,
      };
    }
    
    return {
      message: () => `expected element ${hasError ? 'not ' : ''}to have an error message`,
      pass: hasError,
    };
  },
};

// Re-export everything from testing-library
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';