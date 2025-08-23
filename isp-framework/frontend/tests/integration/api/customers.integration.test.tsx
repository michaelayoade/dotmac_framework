/**
 * Integration tests for customer API interactions
 * Following backend integration test patterns
 */

import { CustomerManagement } from '@dotmac/reseller-app/src/components/customers/CustomerManagement';
import { QueryClient } from '@tanstack/react-query';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';

import { server } from '../../../__mocks__/server';
import { factories, mockResponses, renderWithProviders, testUtils } from '../../../test-utils';

describe('Customer API Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, staleTime: 0 },
        mutations: { retry: false },
      },
    });
  });

  describe('Customer List API Integration', () => {
    it('fetches and displays customers from API', async () => {
      const customers = [
        factories.customer({ name: 'API Customer 1' }),
        factories.customer({ name: 'API Customer 2' }),
      ];

      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.success(customers));
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('API Customer 1')).toBeInTheDocument();
        expect(screen.getByText('API Customer 2')).toBeInTheDocument();
      });
    });

    it('handles paginated responses', async () => {
      const allCustomers = Array.from({ length: 25 }, (_, i) =>
        factories.customer({ name: `Customer ${i + 1}` })
      );

      server.use(
        http.get('/api/v1/customers', ({ request }) => {
          const url = new URL(request.url);
          const page = parseInt(url.searchParams.get('page') || '1', 10);
          const perPage = parseInt(url.searchParams.get('per_page') || '10', 10);

          return HttpResponse.json(mockResponses.paginated(allCustomers, page, perPage));
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      // Should load first page
      await waitFor(() => {
        expect(screen.getByText('Customer 1')).toBeInTheDocument();
        expect(screen.getByText('Customer 10')).toBeInTheDocument();
        expect(screen.queryByText('Customer 11')).not.toBeInTheDocument();
      });

      // Navigate to next page
      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText('Customer 11')).toBeInTheDocument();
        expect(screen.getByText('Customer 20')).toBeInTheDocument();
        expect(screen.queryByText('Customer 1')).not.toBeInTheDocument();
      });
    });

    it('handles search query parameters', async () => {
      const searchResults = [factories.customer({ name: 'Searchable Customer' })];

      server.use(
        http.get('/api/v1/customers', ({ request }) => {
          const url = new URL(request.url);
          const search = url.searchParams.get('search');

          if (search === 'Searchable') {
            return HttpResponse.json(mockResponses.success(searchResults));
          }

          return HttpResponse.json(mockResponses.success([]));
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      const searchInput = screen.getByPlaceholderText('Search customers...');
      fireEvent.change(searchInput, { target: { value: 'Searchable' } });

      await waitFor(() => {
        expect(screen.getByText('Searchable Customer')).toBeInTheDocument();
      });
    });

    it('handles filter query parameters', async () => {
      const activeCustomers = [factories.customer({ name: 'Active Customer', status: 'active' })];

      server.use(
        http.get('/api/v1/customers', ({ request }) => {
          const url = new URL(request.url);
          const status = url.searchParams.get('status');

          if (status === 'active') {
            return HttpResponse.json(mockResponses.success(activeCustomers));
          }

          return HttpResponse.json(mockResponses.success([]));
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      const statusFilter = screen.getByDisplayValue('All Status');
      fireEvent.change(statusFilter, { target: { value: 'active' } });

      await waitFor(() => {
        expect(screen.getByText('Active Customer')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling Integration', () => {
    it('handles 500 server errors', async () => {
      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.error('Internal Server Error'), {
            status: 500,
          });
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
      });
    });

    it('handles 401 unauthorized errors', async () => {
      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.error('Unauthorized'), {
            status: 401,
          });
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText(/unauthorized/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
      });
    });

    it('handles 403 forbidden errors', async () => {
      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.error('Forbidden'), { status: 403 });
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText(/access denied/i)).toBeInTheDocument();
      });
    });

    it('handles network connectivity issues', async () => {
      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.error();
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    it('implements retry mechanism', async () => {
      let attemptCount = 0;

      server.use(
        http.get('/api/v1/customers', () => {
          attemptCount++;
          if (attemptCount < 3) {
            return HttpResponse.error();
          }
          return HttpResponse.json(
            mockResponses.success([factories.customer({ name: 'Retry Success Customer' })])
          );
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      // Should eventually succeed after retries
      await waitFor(
        () => {
          expect(screen.getByText('Retry Success Customer')).toBeInTheDocument();
        },
        { timeout: 10000 }
      );

      expect(attemptCount).toBe(3);
    });
  });

  describe('Loading States Integration', () => {
    it('shows loading states during API calls', async () => {
      server.use(
        http.get(
          '/api/v1/customers',
          testUtils.withDelay(() => {
            return HttpResponse.json(
              mockResponses.success([factories.customer({ name: 'Delayed Customer' })])
            );
          }, 1000)
        )
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      // Should show loading state initially
      expect(screen.getByTestId('customers-loading')).toBeInTheDocument();

      // Should show data after loading
      await waitFor(
        () => {
          expect(screen.getByText('Delayed Customer')).toBeInTheDocument();
        },
        { timeout: 2000 }
      );

      expect(screen.queryByTestId('customers-loading')).not.toBeInTheDocument();
    });

    it('shows skeleton loading for individual items', async () => {
      renderWithProviders(<CustomerManagement />, { queryClient });

      // Should show skeleton loaders
      expect(screen.getAllByTestId('customer-skeleton')).toHaveLength(3);
    });
  });

  describe('Real-time Updates Integration', () => {
    it('handles real-time customer status updates', async () => {
      const customer = factories.customer({
        name: 'Status Change Customer',
        status: 'active',
      });

      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.success([customer]));
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument();
      });

      // Simulate real-time status update
      customer.status = 'suspended';

      // Trigger refetch (simulating WebSocket update)
      queryClient.invalidateQueries({ queryKey: ['customers'] });

      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.success([customer]));
        })
      );

      await waitFor(() => {
        expect(screen.getByText('Suspended')).toBeInTheDocument();
        expect(screen.queryByText('Active')).not.toBeInTheDocument();
      });
    });
  });

  describe('Performance Integration', () => {
    it('implements proper caching behavior', async () => {
      let requestCount = 0;

      server.use(
        http.get('/api/v1/customers', () => {
          requestCount++;
          return HttpResponse.json(
            mockResponses.success([factories.customer({ name: 'Cached Customer' })])
          );
        })
      );

      const { rerender } = renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('Cached Customer')).toBeInTheDocument();
      });

      // Re-render component - should use cache
      rerender(<CustomerManagement />);

      await testUtils.delay(100);

      // Should only make one API call due to caching
      expect(requestCount).toBe(1);
    });

    it('implements stale-while-revalidate pattern', async () => {
      const staleData = [factories.customer({ name: 'Stale Customer' })];
      const freshData = [factories.customer({ name: 'Fresh Customer' })];

      // Configure query client for stale-while-revalidate
      const staleQueryClient = new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 0,
            gcTime: 10000,
          },
        },
      });

      let responseData = staleData;

      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.success(responseData));
        })
      );

      // First render - load stale data
      renderWithProviders(<CustomerManagement />, { queryClient: staleQueryClient });

      await waitFor(() => {
        expect(screen.getByText('Stale Customer')).toBeInTheDocument();
      });

      // Update server data
      responseData = freshData;

      // Trigger revalidation
      staleQueryClient.invalidateQueries({ queryKey: ['customers'] });

      // Should show fresh data
      await waitFor(() => {
        expect(screen.getByText('Fresh Customer')).toBeInTheDocument();
      });
    });
  });

  describe('Authentication Integration', () => {
    it('includes authentication headers in requests', async () => {
      let capturedHeaders: Record<string, string> = {
        // Implementation pending
      };

      server.use(
        http.get('/api/v1/customers', ({ request }) => {
          capturedHeaders = Object.fromEntries(request.headers.entries());
          return HttpResponse.json(mockResponses.success([]));
        })
      );

      // Setup authenticated user
      testUtils.setupAuthenticatedUser();

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(capturedHeaders.authorization).toBe('Bearer mock-jwt-token');
      });
    });

    it('handles token expiration', async () => {
      server.use(
        http.get('/api/v1/customers', () => {
          return HttpResponse.json(mockResponses.error('Token expired'), {
            status: 401,
          });
        })
      );

      renderWithProviders(<CustomerManagement />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText(/session expired/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /sign in again/i })).toBeInTheDocument();
      });
    });
  });
});
