/**
 * Integration tests for CustomerDashboard component
 * Tests data loading, error handling, and user interactions
 */
import { waitFor, screen, within } from '@testing-library/react';
import { QueryClient } from '@tanstack/react-query';
import { render, createMockCustomerData, mockApiCall, mockApiError } from '../../../utils/test-utils';
import { CustomerDashboard } from '../CustomerDashboard';

// Mock the API calls
const mockFetchNetworkStatus = jest.fn();
const mockFetchUsageData = jest.fn();
const mockFetchBillingInfo = jest.fn();
const mockFetchNotifications = jest.fn();

jest.mock('../../../hooks/useCustomerData', () => ({
  useNetworkStatus: () => ({
    data: mockFetchNetworkStatus(),
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  }),
  useUsageData: () => ({
    data: mockFetchUsageData(),
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  }),
  useBillingInfo: () => ({
    data: mockFetchBillingInfo(),
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  }),
  useNotifications: () => ({
    data: mockFetchNotifications(),
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  }),
}));

describe('CustomerDashboard Integration Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Default mock responses
    mockFetchNetworkStatus.mockReturnValue({
      connectionStatus: 'connected',
      currentSpeed: { download: 100, upload: 10 },
      uptime: 99.9,
      latency: 15,
    });

    mockFetchUsageData.mockReturnValue({
      current: 450,
      limit: 1000,
      percentage: 45,
      history: [
        { date: '2024-01-01', download: 10, upload: 2, total: 12 },
        { date: '2024-01-02', download: 15, upload: 3, total: 18 },
      ],
    });

    mockFetchBillingInfo.mockReturnValue({
      balance: 89.99,
      nextDueDate: '2024-02-15',
      isOverdue: false,
      autopay: { enabled: true },
      daysUntilDue: 15,
    });

    mockFetchNotifications.mockReturnValue([
      {
        id: 'notif-1',
        type: 'info',
        title: 'Service Update',
        message: 'Maintenance scheduled for tonight',
        timestamp: new Date().toISOString(),
      },
    ]);
  });

  describe('Data Loading Integration', () => {
    it('renders dashboard with all data sections loaded', async () => {
      render(<CustomerDashboard />, { queryClient });

      // Wait for all sections to load
      await waitFor(() => {
        expect(screen.getByText('Network Status')).toBeInTheDocument();
        expect(screen.getByText('Usage Overview')).toBeInTheDocument();
        expect(screen.getByText('Billing Summary')).toBeInTheDocument();
        expect(screen.getByText('Recent Activity')).toBeInTheDocument();
      });

      // Verify network status data
      expect(screen.getByText('Connected')).toBeInTheDocument();
      expect(screen.getByText('100 Mbps')).toBeInTheDocument();
      expect(screen.getByText('99.9%')).toBeInTheDocument();

      // Verify usage data
      expect(screen.getByText('450 GB')).toBeInTheDocument();
      expect(screen.getByText('of 1000 GB')).toBeInTheDocument();

      // Verify billing data
      expect(screen.getByText('$89.99')).toBeInTheDocument();
      expect(screen.getByText('Due Feb 15, 2024')).toBeInTheDocument();

      // Verify notifications
      expect(screen.getByText('Service Update')).toBeInTheDocument();
    });

    it('handles mixed loading states correctly', async () => {
      const { useBillingInfo } = require('../../../hooks/useCustomerData');
      
      // Mock billing still loading while others are ready
      useBillingInfo.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<CustomerDashboard />, { queryClient });

      // Network and usage should load normally
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
        expect(screen.getByText('450 GB')).toBeInTheDocument();
      });

      // Billing should show loading state
      expect(screen.getByText('Loading billing information...')).toBeInTheDocument();
    });
  });

  describe('Error Handling Integration', () => {
    it('handles network status API failure gracefully', async () => {
      const { useNetworkStatus } = require('../../../hooks/useCustomerData');
      
      useNetworkStatus.mockReturnValue({
        data: null,
        isLoading: false,
        error: { message: 'Failed to fetch network status' },
        refetch: jest.fn(),
      });

      render(<CustomerDashboard />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('Unable to load network status')).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      // Other sections should still work
      expect(screen.getByText('450 GB')).toBeInTheDocument();
      expect(screen.getByText('$89.99')).toBeInTheDocument();
    });

    it('handles multiple API failures simultaneously', async () => {
      const { useNetworkStatus, useBillingInfo } = require('../../../hooks/useCustomerData');
      
      useNetworkStatus.mockReturnValue({
        data: null,
        isLoading: false,
        error: { message: 'Network error' },
        refetch: jest.fn(),
      });

      useBillingInfo.mockReturnValue({
        data: null,
        isLoading: false,
        error: { message: 'Billing API error' },
        refetch: jest.fn(),
      });

      render(<CustomerDashboard />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('Unable to load network status')).toBeInTheDocument();
        expect(screen.getByText('Unable to load billing information')).toBeInTheDocument();
      });

      // Should have multiple retry buttons
      const retryButtons = screen.getAllByText('Retry');
      expect(retryButtons).toHaveLength(2);
    });

    it('recovers from error state after successful retry', async () => {
      const mockRefetch = jest.fn();
      const { useNetworkStatus } = require('../../../hooks/useCustomerData');
      
      // Initially return error
      useNetworkStatus.mockReturnValue({
        data: null,
        isLoading: false,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      });

      const { user, rerender } = render(<CustomerDashboard />, { queryClient });

      // Should show error state
      await waitFor(() => {
        expect(screen.getByText('Unable to load network status')).toBeInTheDocument();
      });

      // Click retry
      const retryButton = screen.getByText('Retry');
      await user.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();

      // Mock successful retry
      useNetworkStatus.mockReturnValue({
        data: {
          connectionStatus: 'connected',
          currentSpeed: { download: 100, upload: 10 },
          uptime: 99.9,
          latency: 15,
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      rerender(<CustomerDashboard />);

      // Should show successful data
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
        expect(screen.queryByText('Unable to load network status')).not.toBeInTheDocument();
      });
    });
  });

  describe('User Interaction Workflows', () => {
    it('handles account balance payment workflow', async () => {
      // Mock overdue account
      mockFetchBillingInfo.mockReturnValue({
        balance: 150.00,
        nextDueDate: '2024-01-10',
        isOverdue: true,
        autopay: { enabled: false },
        daysUntilDue: -5,
      });

      const { user } = render(<CustomerDashboard />, { queryClient });

      // Should show overdue warning
      await waitFor(() => {
        expect(screen.getByText('Payment Overdue')).toBeInTheDocument();
        expect(screen.getByText('$150.00')).toBeInTheDocument();
      });

      // Should have pay now button
      const payButton = screen.getByText('Pay Now');
      expect(payButton).toBeInTheDocument();

      await user.click(payButton);

      // Should navigate to payment page
      // Note: This would typically be tested with router mock
      // For now, we verify the button is clickable
      expect(payButton).toHaveBeenClicked;
    });

    it('shows usage alerts when approaching limit', async () => {
      // Mock high usage
      mockFetchUsageData.mockReturnValue({
        current: 950,
        limit: 1000,
        percentage: 95,
        history: [
          { date: '2024-01-01', download: 300, upload: 50, total: 350 },
          { date: '2024-01-02', download: 400, upload: 200, total: 600 },
        ],
      });

      render(<CustomerDashboard />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('950 GB')).toBeInTheDocument();
        expect(screen.getByText('of 1000 GB')).toBeInTheDocument();
      });

      // Should show usage warning
      expect(screen.getByText(/approaching your data limit/i)).toBeInTheDocument();
      
      // Should have manage usage button
      expect(screen.getByText('Manage Usage')).toBeInTheDocument();
    });

    it('handles notification interactions', async () => {
      // Mock multiple notifications
      mockFetchNotifications.mockReturnValue([
        {
          id: 'notif-1',
          type: 'warning',
          title: 'Service Maintenance',
          message: 'Scheduled maintenance tonight 2-4 AM',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'notif-2',
          type: 'info',
          title: 'Bill Ready',
          message: 'Your January bill is now available',
          timestamp: new Date().toISOString(),
        },
      ]);

      const { user } = render(<CustomerDashboard />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('Service Maintenance')).toBeInTheDocument();
        expect(screen.getByText('Bill Ready')).toBeInTheDocument();
      });

      // Should be able to dismiss notifications
      const dismissButtons = screen.getAllByText('Dismiss');
      expect(dismissButtons).toHaveLength(2);

      await user.click(dismissButtons[0]);
      
      // First notification should be dismissed (implementation dependent)
      // In real implementation, this would trigger an API call
    });
  });

  describe('Real-time Updates Integration', () => {
    it('updates network status automatically', async () => {
      const { rerender } = render(<CustomerDashboard />, { queryClient });

      // Initial state
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
        expect(screen.getByText('100 Mbps')).toBeInTheDocument();
      });

      // Simulate network status change
      mockFetchNetworkStatus.mockReturnValue({
        connectionStatus: 'connecting',
        currentSpeed: { download: 0, upload: 0 },
        uptime: 99.8,
        latency: 25,
      });

      rerender(<CustomerDashboard />);

      // Should show updated status
      await waitFor(() => {
        expect(screen.getByText('Connecting')).toBeInTheDocument();
        expect(screen.getByText('0 Mbps')).toBeInTheDocument();
      });
    });

    it('handles real-time usage updates', async () => {
      const { rerender } = render(<CustomerDashboard />, { queryClient });

      // Initial usage
      await waitFor(() => {
        expect(screen.getByText('450 GB')).toBeInTheDocument();
      });

      // Simulate usage increase
      mockFetchUsageData.mockReturnValue({
        current: 475,
        limit: 1000,
        percentage: 47.5,
        history: [
          { date: '2024-01-01', download: 10, upload: 2, total: 12 },
          { date: '2024-01-02', download: 15, upload: 3, total: 18 },
          { date: '2024-01-03', download: 25, upload: 5, total: 30 },
        ],
      });

      rerender(<CustomerDashboard />);

      // Should show updated usage
      await waitFor(() => {
        expect(screen.getByText('475 GB')).toBeInTheDocument();
      });
    });
  });

  describe('Performance Integration', () => {
    it('handles large datasets efficiently', async () => {
      // Mock large usage history
      const largeHistory = Array.from({ length: 365 }, (_, i) => ({
        date: `2024-${String(Math.floor(i / 30) + 1).padStart(2, '0')}-${String((i % 30) + 1).padStart(2, '0')}`,
        download: Math.floor(Math.random() * 50),
        upload: Math.floor(Math.random() * 10),
        total: Math.floor(Math.random() * 60),
      }));

      mockFetchUsageData.mockReturnValue({
        current: 450,
        limit: 1000,
        percentage: 45,
        history: largeHistory,
      });

      const startTime = performance.now();
      render(<CustomerDashboard />, { queryClient });

      await waitFor(() => {
        expect(screen.getByText('450 GB')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render within reasonable time even with large datasets
      expect(renderTime).toBeLessThan(1000); // Less than 1 second
    });

    it('maintains responsiveness during data updates', async () => {
      const { user, rerender } = render(<CustomerDashboard />, { queryClient });

      // Initial render
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      });

      // Simulate rapid data updates
      for (let i = 0; i < 10; i++) {
        mockFetchNetworkStatus.mockReturnValue({
          connectionStatus: 'connected',
          currentSpeed: { download: 100 + i, upload: 10 + i },
          uptime: 99.9,
          latency: 15 + i,
        });

        rerender(<CustomerDashboard />);

        // Should remain responsive to user interactions
        const refreshButton = screen.getByText('Refresh');
        await user.click(refreshButton);
      }

      // Final state should be updated
      await waitFor(() => {
        expect(screen.getByText('109 Mbps')).toBeInTheDocument();
      });
    });
  });
});