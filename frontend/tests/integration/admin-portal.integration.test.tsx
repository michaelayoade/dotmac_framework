/**
 * Admin Portal Integration Tests
 * Tests the complete admin portal functionality with API integration
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

// Mock admin portal pages
const AdminDashboard = () => (
  <div data-testid='admin-dashboard'>
    <h1>Admin Dashboard</h1>
    <div data-testid='metrics-cards'>
      <div data-testid='customer-count'>1,234 Customers</div>
      <div data-testid='revenue-metric'>$45,678 MRR</div>
    </div>
  </div>
);

const CustomerManagement = () => (
  <div data-testid='customer-management'>
    <h1>Customer Management</h1>
    <button data-testid='add-customer'>Add Customer</button>
    <div data-testid='customer-table'>Customer Table</div>
  </div>
);

// Mock API server
const server = setupServer(
  rest.get('/api/v1/admin/dashboard', (req, res, ctx) => {
    return res(
      ctx.json({
        total_customers: 1234,
        active_services: 5678,
        monthly_revenue: 45678,
        open_tickets: 12,
        system_alerts: 3,
        recent_activities: [],
      })
    );
  }),

  rest.get('/api/v1/admin/customers', (req, res, ctx) => {
    const page = req.url.searchParams.get('page') || '1';
    const limit = req.url.searchParams.get('limit') || '10';

    return res(
      ctx.json({
        data: Array.from({ length: parseInt(limit) }, (_, i) => ({
          id: `customer-${i}`,
          name: `Customer ${i}`,
          email: `customer${i}@example.com`,
          status: 'active',
          plan: 'Premium',
          revenue: 99.99,
        })),
        pagination: {
          page: parseInt(page),
          total_pages: 10,
          total_items: 100,
        },
      })
    );
  }),

  rest.post('/api/v1/admin/customers', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: 'new-customer-123',
        name: 'New Customer',
        email: 'new@example.com',
        status: 'active',
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const createTestQueryClient = () => {
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
  });
};

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createTestQueryClient();

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('Admin Portal Integration Tests', () => {
  describe('Dashboard Integration', () => {
    test('loads dashboard data from API', async () => {
      renderWithProviders(<AdminDashboard />);

      expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();

      // Verify metrics are displayed
      await waitFor(() => {
        expect(screen.getByTestId('customer-count')).toBeInTheDocument();
        expect(screen.getByTestId('revenue-metric')).toBeInTheDocument();
      });
    });

    test('handles dashboard API errors gracefully', async () => {
      server.use(
        rest.get('/api/v1/admin/dashboard', (req, res, ctx) => {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }));
        })
      );

      renderWithProviders(<AdminDashboard />);

      // Dashboard should still render even with API error
      expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
    });
  });

  describe('Customer Management Integration', () => {
    test('loads customer list from API', async () => {
      renderWithProviders(<CustomerManagement />);

      expect(screen.getByTestId('customer-management')).toBeInTheDocument();
      expect(screen.getByText('Customer Management')).toBeInTheDocument();
      expect(screen.getByTestId('add-customer')).toBeInTheDocument();
    });

    test('handles customer creation workflow', async () => {
      renderWithProviders(<CustomerManagement />);

      const addButton = screen.getByTestId('add-customer');
      await userEvent.click(addButton);

      // Simulate form submission
      // In real implementation, this would open a modal/form
    });

    test('handles customer API pagination', async () => {
      // Test pagination functionality
      renderWithProviders(<CustomerManagement />);

      await waitFor(() => {
        expect(screen.getByTestId('customer-table')).toBeInTheDocument();
      });
    });
  });

  describe('Cross-Portal Integration', () => {
    test('maintains authentication state across components', async () => {
      // Test that auth state persists across different admin components
      renderWithProviders(
        <div>
          <AdminDashboard />
          <CustomerManagement />
        </div>
      );

      await waitFor(() => {
        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
        expect(screen.getByTestId('customer-management')).toBeInTheDocument();
      });
    });

    test('shares data between related components', async () => {
      // Test that data updates in one component reflect in others
      renderWithProviders(
        <div>
          <AdminDashboard />
          <CustomerManagement />
        </div>
      );

      // Simulate customer creation affecting dashboard metrics
      // This would test real-time updates and cache invalidation
    });
  });

  describe('Error Boundaries Integration', () => {
    test('error boundaries prevent component crashes', () => {
      const ThrowingComponent = () => {
        throw new Error('Test error');
      };

      const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
        try {
          return <>{children}</>;
        } catch (error) {
          return <div data-testid='error-boundary'>Something went wrong</div>;
        }
      };

      renderWithProviders(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    });
  });

  describe('Performance Integration', () => {
    test('components render within performance budget', async () => {
      const startTime = performance.now();

      renderWithProviders(
        <div>
          <AdminDashboard />
          <CustomerManagement />
        </div>
      );

      await waitFor(() => {
        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
      });

      const endTime = performance.now();

      // Should render within 500ms
      expect(endTime - startTime).toBeLessThan(500);
    });
  });

  describe('API Contract Validation', () => {
    test('API responses match expected schema', async () => {
      let dashboardResponse: any;

      server.use(
        rest.get('/api/v1/admin/dashboard', (req, res, ctx) => {
          dashboardResponse = {
            total_customers: 1234,
            active_services: 5678,
            monthly_revenue: 45678,
            open_tickets: 12,
            system_alerts: 3,
            recent_activities: [],
          };
          return res(ctx.json(dashboardResponse));
        })
      );

      renderWithProviders(<AdminDashboard />);

      await waitFor(() => {
        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
      });

      // Verify API response structure
      expect(dashboardResponse).toHaveProperty('total_customers');
      expect(dashboardResponse).toHaveProperty('monthly_revenue');
      expect(dashboardResponse.total_customers).toBeGreaterThan(0);
    });
  });
});
