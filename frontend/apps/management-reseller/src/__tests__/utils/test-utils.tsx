import { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ErrorBoundary } from '@/components/error/ErrorBoundary'

// Mock providers for testing
interface TestProvidersProps {
  children: ReactNode
}

// Create a test query client
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: () => {},
      warn: () => {},
      error: () => {},
    },
  })
}

function TestProviders({ children }: TestProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

// Custom render function with providers
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: TestProviders, ...options })
}

// Mock auth context
export const mockAuthContext = {
  user: {
    id: 'test-user-1',
    email: 'test@example.com',
    name: 'Test User',
    role: 'CHANNEL_MANAGER' as const,
    permissions: ['MANAGE_RESELLERS', 'VIEW_ANALYTICS'],
    departments: ['Channel Operations'],
    last_login: new Date(),
  },
  isLoading: false,
  isAuthenticated: true,
  login: jest.fn(),
  logout: jest.fn(),
  refreshAuth: jest.fn(),
  hasPermission: jest.fn(() => true),
  canManageResellers: jest.fn(() => true),
  canApproveCommissions: jest.fn(() => true),
  canViewAnalytics: jest.fn(() => true),
}

// Mock API responses
export const mockApiResponses = {
  partners: {
    list: {
      data: [
        {
          id: 'partner-1',
          company_name: 'Test Partner 1',
          contact_name: 'John Doe',
          contact_email: 'john@testpartner1.com',
          contact_phone: '+1234567890',
          partner_type: 'AGENT',
          tier: 'GOLD',
          status: 'ACTIVE',
          territory: {
            id: 'territory-1',
            type: 'GEOGRAPHIC',
            value: 'California',
            description: 'California Region',
          },
          commission_rate: 0.15,
          expected_revenue: 100000,
          performance_score: 85,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-15T00:00:00Z',
          total_sales: 75000,
          total_commission: 11250,
          onboarding_status: {
            stage: 'APPROVED',
            completion_percentage: 100,
            required_documents: {
              business_license: true,
              tax_document: true,
              bank_info: true,
              references: true,
              insurance: true,
            },
          },
        },
      ],
      pagination: {
        page: 1,
        limit: 10,
        total: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    },
    detail: {
      data: {
        id: 'partner-1',
        company_name: 'Test Partner 1',
        contact_name: 'John Doe',
        contact_email: 'john@testpartner1.com',
        contact_phone: '+1234567890',
        partner_type: 'AGENT',
        tier: 'GOLD',
        status: 'ACTIVE',
        territory: {
          id: 'territory-1',
          type: 'GEOGRAPHIC',
          value: 'California',
          description: 'California Region',
        },
        commission_rate: 0.15,
        expected_revenue: 100000,
        performance_score: 85,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
        total_sales: 75000,
        total_commission: 11250,
        onboarding_status: {
          stage: 'APPROVED',
          completion_percentage: 100,
          required_documents: {
            business_license: true,
            tax_document: true,
            bank_info: true,
            references: true,
            insurance: true,
          },
        },
      },
    },
  },
  commissions: {
    list: {
      data: [
        {
          id: 'commission-1',
          payment_number: 'PAY-2024-001',
          partner_id: 'partner-1',
          partner_name: 'Test Partner 1',
          partner_tier: 'GOLD',
          period_start: '2024-01-01',
          period_end: '2024-01-31',
          gross_amount: 12000,
          deductions: [
            {
              id: 'deduction-1',
              type: 'TAX',
              description: 'Federal Tax',
              amount: 1200,
              percentage: 10,
              applied_at: '2024-02-01T00:00:00Z',
            },
          ],
          net_amount: 10800,
          payment_method: 'ACH',
          status: 'APPROVED',
          created_at: '2024-02-01T00:00:00Z',
          updated_at: '2024-02-01T00:00:00Z',
          sales_count: 15,
          approved_by: 'admin-1',
          approved_at: '2024-02-01T00:00:00Z',
        },
      ],
      pagination: {
        page: 1,
        limit: 10,
        total: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    },
  },
  analytics: {
    channelMetrics: {
      data: {
        total_partners: 50,
        active_partners: 42,
        pending_approvals: 5,
        total_revenue: 2500000,
        commission_payout: 375000,
        avg_deal_size: 15000,
        conversion_rate: 0.65,
        partner_satisfaction: 4.2,
        territory_coverage: 85,
        top_performers: [],
        revenue_by_tier: {
          PLATINUM: 1000000,
          GOLD: 800000,
          SILVER: 500000,
          BRONZE: 200000,
        },
        commission_by_month: [],
        partner_growth: [],
      },
    },
  },
}

// Utility functions
export const testUtils = {
  // Wait for loading states
  waitForLoadingToFinish: () => new Promise(resolve => setTimeout(resolve, 100)),
  
  // Mock fetch with different responses
  mockFetch: (response: any, status = 200) => {
    const mockResponse = {
      ok: status < 400,
      status,
      json: async () => response,
      text: async () => JSON.stringify(response),
    }
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse)
  },
  
  // Mock fetch error
  mockFetchError: (error: Error) => {
    ;(global.fetch as jest.Mock).mockRejectedValueOnce(error)
  },
  
  // Create mock user with specific permissions
  createMockUser: (overrides = {}) => ({
    ...mockAuthContext.user,
    ...overrides,
  }),
  
  // Create form data for testing
  createFormData: (data: Record<string, any>) => {
    const formData = new FormData()
    Object.entries(data).forEach(([key, value]) => {
      formData.append(key, value.toString())
    })
    return formData
  },
  
  // Mock date for consistent testing
  mockDate: (date: string) => {
    const mockDate = new Date(date)
    jest.spyOn(global, 'Date').mockImplementation(() => mockDate)
    return mockDate
  },
  
  // Restore date mock
  restoreDate: () => {
    jest.restoreAllMocks()
  },
}

// Custom matchers for common assertions
expect.extend({
  toHaveLoadingState(received) {
    const hasLoader = received.querySelector('[data-testid="loading"]') !== null
    const hasSpinner = received.querySelector('.animate-spin') !== null
    const hasLoadingText = received.textContent?.includes('Loading') || false
    
    const pass = hasLoader || hasSpinner || hasLoadingText
    
    if (pass) {
      return {
        message: () => `expected element not to have loading state`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected element to have loading state`,
        pass: false,
      }
    }
  },
  
  toHaveErrorState(received) {
    const hasErrorText = received.textContent?.includes('Error') || false
    const hasErrorClass = received.classList.contains('error') || received.querySelector('.text-red-500, .text-red-600, .text-red-700')
    
    const pass = hasErrorText || hasErrorClass
    
    if (pass) {
      return {
        message: () => `expected element not to have error state`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected element to have error state`,
        pass: false,
      }
    }
  },
})

// Export everything
export * from '@testing-library/react'
export { renderWithProviders as render }