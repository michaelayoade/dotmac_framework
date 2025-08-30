/**
 * Example DRY component test for AdminDashboard
 * Demonstrates shared testing patterns and utilities
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, testUtils, createMockData, mockUtils } from '@test/utils';
import AdminDashboard from '@/components/dashboard/AdminDashboard';

// DRY test data using our factories
const mockTenant = createMockData.tenant({ name: 'Test ISP Company' });
const mockUser = createMockData.admin({ tenantId: mockTenant.id });
const mockCustomers = createMockData.customers(10);
const mockTickets = createMockData.tickets(5);

describe('AdminDashboard', () => {
  beforeEach(() => {
    // DRY authentication setup
    testUtils.portal.mockPortalAuth('admin', mockUser);
  });

  afterEach(() => {
    mockUtils.resetHandlers();
  });

  describe('Rendering', () => {
    test('renders dashboard with all sections', async () => {
      renderWithProviders(<AdminDashboard />);

      // Use DRY test utilities for consistent checking
      await testUtils.api.waitForLoadingToFinish();

      expect(screen.getByText('Dashboard Overview')).toBeInTheDocument();
      expect(screen.getByText('System Status')).toBeInTheDocument();
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });

    test('displays tenant information', async () => {
      renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      expect(screen.getByText(mockTenant.name)).toBeInTheDocument();
      expect(screen.getByText('Enterprise Plan')).toBeInTheDocument();
    });

    // DRY responsive testing
    testUtils.component.testResponsive(AdminDashboard);
  });

  describe('Data Loading', () => {
    test('shows loading state initially', () => {
      // Mock slow API response
      mockUtils.mockSlowResponse('/analytics/dashboard', 1000);

      renderWithProviders(<AdminDashboard />);

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    test('loads dashboard metrics successfully', async () => {
      renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      // Check for metrics cards
      expect(screen.getByText('Total Customers')).toBeInTheDocument();
      expect(screen.getByText('Open Tickets')).toBeInTheDocument();
      expect(screen.getByText('Monthly Revenue')).toBeInTheDocument();
      expect(screen.getByText('System Uptime')).toBeInTheDocument();
    });

    test('handles API error gracefully', async () => {
      // DRY error mocking
      mockUtils.mockApiError('/analytics/dashboard', 500, 'Server Error');

      renderWithProviders(<AdminDashboard />);

      await waitFor(() => {
        testUtils.api.expectErrorMessage('Failed to load dashboard data');
      });
    });
  });

  describe('Interactions', () => {
    test('navigates to customers page when clicking customer count', async () => {
      const { user } = renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      const customerCard = screen.getByTestId('customer-count-card');
      await user.click(customerCard);

      await testUtils.navigation.clickLinkAndVerify('View All Customers', '/customers');
    });

    test('refreshes data when refresh button is clicked', async () => {
      const { user } = renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      await user.click(refreshButton);

      // Should trigger new API call
      await testUtils.api.waitForApiCall(2); // Initial + refresh
    });
  });

  describe('Real-time Updates', () => {
    test('updates metrics when websocket data received', async () => {
      renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      // Simulate real-time update
      const initialCustomerCount = screen.getByTestId('customer-count').textContent;

      // Mock websocket message (this would be integrated with your websocket system)
      const mockWebSocketUpdate = {
        type: 'CUSTOMER_CREATED',
        data: { totalCustomers: parseInt(initialCustomerCount || '0') + 1 }
      };

      // Trigger update (implementation depends on your websocket integration)
      window.dispatchEvent(new CustomEvent('websocket-update', {
        detail: mockWebSocketUpdate
      }));

      await waitFor(() => {
        expect(screen.getByTestId('customer-count')).not.toHaveTextContent(initialCustomerCount || '');
      });
    });
  });

  describe('Accessibility', () => {
    test('meets accessibility standards', async () => {
      const { container } = renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      // DRY accessibility testing
      await testUtils.a11y.expectNoA11yViolations(container);
    });

    test('supports keyboard navigation', async () => {
      renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      const interactiveElements = [
        screen.getByRole('button', { name: /refresh/i }),
        screen.getByTestId('customer-count-card'),
        screen.getByTestId('tickets-count-card')
      ];

      await testUtils.a11y.testKeyboardNavigation(interactiveElements);
    });
  });

  describe('Error Boundaries', () => {
    test('catches and displays component errors', async () => {
      // Force component to throw error
      const ThrowError = () => {
        throw new Error('Test error');
      };

      // Mock a component that throws
      jest.doMock('@/components/dashboard/DashboardMetrics', () => ThrowError);

      renderWithProviders(<AdminDashboard />);

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });
  });

  describe('Multi-tenant Behavior', () => {
    const tenantVariations = [
      { id: 'tenant-1', name: 'ISP Alpha', plan: 'starter' },
      { id: 'tenant-2', name: 'ISP Beta', plan: 'professional' },
      { id: 'tenant-3', name: 'ISP Gamma', plan: 'enterprise' }
    ];

    // DRY multi-tenant testing
    testUtils.portal.testMultiTenant(AdminDashboard, tenantVariations);
  });

  describe('Performance', () => {
    test('renders within performance budget', async () => {
      const startTime = performance.now();

      renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render within 1 second
      expect(renderTime).toBeLessThan(1000);
    });

    test('handles large datasets efficiently', async () => {
      // Mock large dataset
      const largeMockData = {
        customers: createMockData.customers(1000),
        tickets: createMockData.tickets(100)
      };

      mockUtils.useHandler(
        http.get('/api/v1/analytics/dashboard', () => {
          return HttpResponse.json(
            factories.ApiResponse.success(largeMockData)
          );
        })
      );

      renderWithProviders(<AdminDashboard />);

      await testUtils.api.waitForLoadingToFinish();

      // Should still render efficiently
      expect(screen.getByText('Total Customers')).toBeInTheDocument();
    });
  });
});
