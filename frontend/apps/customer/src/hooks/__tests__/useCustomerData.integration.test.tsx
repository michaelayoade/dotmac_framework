/**
 * Integration tests for customer data hooks
 * Tests API integration, caching, error handling, and data transformations
 */
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { 
  useNetworkStatus, 
  useUsageData, 
  useBillingInfo, 
  useNotifications,
  useCustomerProfile 
} from '../useCustomerData';

// Mock the API client
const mockApiCall = jest.fn();
jest.mock('../../api/customerClient', () => ({
  customerApi: {
    getNetworkStatus: () => mockApiCall('network-status'),
    getUsageData: () => mockApiCall('usage-data'),
    getBillingInfo: () => mockApiCall('billing-info'),
    getNotifications: () => mockApiCall('notifications'),
    getProfile: () => mockApiCall('profile'),
  },
}));

// Mock auth context
jest.mock('../../components/auth/SecureAuthProvider', () => ({
  useSecureAuth: () => ({
    user: { id: 'user-123', accountNumber: 'ACC123456' },
    isAuthenticated: true,
  }),
}));

describe('Customer Data Hooks Integration Tests', () => {
  let queryClient: QueryClient;
  let wrapper: React.FC<{ children: React.ReactNode }>;

  beforeEach(() => {
    jest.clearAllMocks();
    
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { 
          retry: false,
          staleTime: 0,
          cacheTime: 0,
        },
      },
    });

    wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('useNetworkStatus Hook', () => {
    it('fetches and transforms network status data correctly', async () => {
      const mockNetworkData = {
        connection_status: 'connected',
        current_speed: { download_mbps: 100, upload_mbps: 10 },
        uptime_percentage: 99.9,
        latency_ms: 15,
        last_updated: '2024-01-15T10:30:00Z',
      };

      mockApiCall.mockResolvedValueOnce(mockNetworkData);

      const { result } = renderHook(() => useNetworkStatus(), { wrapper });

      // Initially loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual({
        connectionStatus: 'connected',
        currentSpeed: { download: 100, upload: 10 },
        uptime: 99.9,
        latency: 15,
        lastUpdated: '2024-01-15T10:30:00Z',
      });

      expect(mockApiCall).toHaveBeenCalledWith('network-status');
    });

    it('handles network status API errors gracefully', async () => {
      const apiError = new Error('Network unavailable');
      mockApiCall.mockRejectedValueOnce(apiError);

      const { result } = renderHook(() => useNetworkStatus(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('refetches data when refetch is called', async () => {
      mockApiCall
        .mockResolvedValueOnce({ connection_status: 'connected' })
        .mockResolvedValueOnce({ connection_status: 'disconnected' });

      const { result } = renderHook(() => useNetworkStatus(), { wrapper });

      await waitFor(() => {
        expect(result.current.data?.connectionStatus).toBe('connected');
      });

      // Refetch data
      await result.current.refetch();

      await waitFor(() => {
        expect(result.current.data?.connectionStatus).toBe('disconnected');
      });

      expect(mockApiCall).toHaveBeenCalledTimes(2);
    });
  });

  describe('useUsageData Hook', () => {
    it('fetches usage data with date range filtering', async () => {
      const mockUsageData = {
        current_month: {
          usage_gb: 450,
          limit_gb: 1000,
          percentage_used: 45,
        },
        history: [
          { date: '2024-01-01', download_gb: 10, upload_gb: 2, total_gb: 12 },
          { date: '2024-01-02', download_gb: 15, upload_gb: 3, total_gb: 18 },
        ],
        overage_charges: 0,
        next_cycle_date: '2024-02-01',
      };

      mockApiCall.mockResolvedValueOnce(mockUsageData);

      const dateRange = { start: '2024-01-01', end: '2024-01-31' };
      const { result } = renderHook(() => useUsageData(dateRange), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual({
        current: 450,
        limit: 1000,
        percentage: 45,
        history: [
          { date: '2024-01-01', download: 10, upload: 2, total: 12 },
          { date: '2024-01-02', download: 15, upload: 3, total: 18 },
        ],
        overageCharges: 0,
        nextCycleDate: '2024-02-01',
      });

      expect(mockApiCall).toHaveBeenCalledWith('usage-data');
    });

    it('calculates usage trends and projections', async () => {
      const mockUsageData = {
        current_month: { usage_gb: 600, limit_gb: 1000, percentage_used: 60 },
        history: Array.from({ length: 15 }, (_, i) => ({
          date: `2024-01-${String(i + 1).padStart(2, '0')}`,
          download_gb: 20 + i,
          upload_gb: 5 + i,
          total_gb: 25 + i,
        })),
        projected_usage: 950,
        days_remaining_in_cycle: 16,
      };

      mockApiCall.mockResolvedValueOnce(mockUsageData);

      const { result } = renderHook(() => useUsageData(), { wrapper });

      await waitFor(() => {
        expect(result.current.data?.projectedUsage).toBe(950);
        expect(result.current.data?.daysRemaining).toBe(16);
      });

      // Should indicate approaching limit
      expect(result.current.data?.isApproachingLimit).toBe(true);
    });

    it('handles usage data for unlimited plans', async () => {
      const mockUnlimitedData = {
        current_month: { usage_gb: 2500, limit_gb: null, percentage_used: null },
        history: [
          { date: '2024-01-01', download_gb: 100, upload_gb: 20, total_gb: 120 },
        ],
        plan_type: 'unlimited',
        throttling_threshold: 1000,
      };

      mockApiCall.mockResolvedValueOnce(mockUnlimitedData);

      const { result } = renderHook(() => useUsageData(), { wrapper });

      await waitFor(() => {
        expect(result.current.data?.current).toBe(2500);
        expect(result.current.data?.limit).toBe(null);
        expect(result.current.data?.planType).toBe('unlimited');
        expect(result.current.data?.throttlingThreshold).toBe(1000);
      });
    });
  });

  describe('useBillingInfo Hook', () => {
    it('fetches and processes billing information', async () => {
      const mockBillingData = {
        current_balance: 89.99,
        next_due_date: '2024-02-15',
        is_overdue: false,
        autopay: { enabled: true, method: 'credit_card' },
        recent_payments: [
          { date: '2024-01-15', amount: 89.99, status: 'completed' },
        ],
        billing_cycle: { start: '2024-01-15', end: '2024-02-14' },
      };

      mockApiCall.mockResolvedValueOnce(mockBillingData);

      const { result } = renderHook(() => useBillingInfo(), { wrapper });

      await waitFor(() => {
        expect(result.current.data).toEqual({
          balance: 89.99,
          nextDueDate: '2024-02-15',
          isOverdue: false,
          autopay: { enabled: true, method: 'credit_card' },
          recentPayments: [
            { date: '2024-01-15', amount: 89.99, status: 'completed' },
          ],
          billingCycle: { start: '2024-01-15', end: '2024-02-14' },
          daysUntilDue: expect.any(Number),
        });
      });
    });

    it('calculates overdue status and days correctly', async () => {
      const mockOverdueData = {
        current_balance: 150.00,
        next_due_date: '2024-01-10', // Past date
        is_overdue: true,
        autopay: { enabled: false },
        late_fees: 15.00,
      };

      mockApiCall.mockResolvedValueOnce(mockOverdueData);

      const { result } = renderHook(() => useBillingInfo(), { wrapper });

      await waitFor(() => {
        expect(result.current.data?.isOverdue).toBe(true);
        expect(result.current.data?.lateFees).toBe(15.00);
        expect(result.current.data?.daysUntilDue).toBeLessThan(0); // Negative for overdue
      });
    });

    it('handles billing API timeout gracefully', async () => {
      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'TimeoutError';
      mockApiCall.mockRejectedValueOnce(timeoutError);

      const { result } = renderHook(() => useBillingInfo(), { wrapper });

      await waitFor(() => {
        expect(result.current.error?.name).toBe('TimeoutError');
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe('useNotifications Hook', () => {
    it('fetches and categorizes notifications', async () => {
      const mockNotifications = [
        {
          id: 'notif-1',
          type: 'service_alert',
          title: 'Planned Maintenance',
          message: 'Service maintenance tonight 2-4 AM',
          priority: 'high',
          created_at: '2024-01-15T08:00:00Z',
          is_read: false,
        },
        {
          id: 'notif-2',
          type: 'billing',
          title: 'Bill Available',
          message: 'Your January bill is ready',
          priority: 'normal',
          created_at: '2024-01-14T10:00:00Z',
          is_read: true,
        },
      ];

      mockApiCall.mockResolvedValueOnce(mockNotifications);

      const { result } = renderHook(() => useNotifications(), { wrapper });

      await waitFor(() => {
        expect(result.current.data).toEqual([
          {
            id: 'notif-1',
            type: 'service_alert',
            title: 'Planned Maintenance',
            message: 'Service maintenance tonight 2-4 AM',
            priority: 'high',
            timestamp: '2024-01-15T08:00:00Z',
            isRead: false,
          },
          {
            id: 'notif-2',
            type: 'billing',
            title: 'Bill Available',
            message: 'Your January bill is ready',
            priority: 'normal',
            timestamp: '2024-01-14T10:00:00Z',
            isRead: true,
          },
        ]);
      });
    });

    it('filters notifications by type and status', async () => {
      const mockNotifications = [
        { id: '1', type: 'billing', is_read: false },
        { id: '2', type: 'service_alert', is_read: false },
        { id: '3', type: 'billing', is_read: true },
        { id: '4', type: 'general', is_read: false },
      ];

      mockApiCall.mockResolvedValueOnce(mockNotifications);

      const filters = { type: 'billing', unreadOnly: true };
      const { result } = renderHook(() => useNotifications(filters), { wrapper });

      await waitFor(() => {
        expect(result.current.data).toHaveLength(1);
        expect(result.current.data?.[0].id).toBe('1');
      });
    });

    it('provides unread count and summary', async () => {
      const mockNotifications = [
        { id: '1', type: 'billing', is_read: false },
        { id: '2', type: 'service_alert', is_read: false },
        { id: '3', type: 'billing', is_read: true },
      ];

      mockApiCall.mockResolvedValueOnce(mockNotifications);

      const { result } = renderHook(() => useNotifications(), { wrapper });

      await waitFor(() => {
        expect(result.current.unreadCount).toBe(2);
        expect(result.current.summary).toEqual({
          total: 3,
          unread: 2,
          byType: {
            billing: 2,
            service_alert: 1,
          },
        });
      });
    });
  });

  describe('Data Caching and Invalidation', () => {
    it('caches network status data for configured duration', async () => {
      const mockData = { connection_status: 'connected' };
      mockApiCall.mockResolvedValue(mockData);

      // Configure longer cache time for this test
      queryClient.setQueryDefaults(['network-status'], { 
        staleTime: 30000,
        cacheTime: 60000,
      });

      const { result: result1 } = renderHook(() => useNetworkStatus(), { wrapper });
      await waitFor(() => expect(result1.current.data).toBeTruthy());

      // Second hook instance should use cached data
      const { result: result2 } = renderHook(() => useNetworkStatus(), { wrapper });
      expect(result2.current.data).toBeTruthy();
      expect(result2.current.isLoading).toBe(false);

      // API should only be called once due to caching
      expect(mockApiCall).toHaveBeenCalledTimes(1);
    });

    it('invalidates cache when user context changes', async () => {
      mockApiCall.mockResolvedValue({ usage_gb: 450 });

      const { result, rerender } = renderHook(
        ({ userId }) => useUsageData(),
        { 
          wrapper,
          initialProps: { userId: 'user-123' }
        }
      );

      await waitFor(() => expect(result.current.data).toBeTruthy());

      // Simulate user change (would trigger cache invalidation in real app)
      rerender({ userId: 'user-456' });

      // Should trigger new API call for different user
      await waitFor(() => {
        expect(mockApiCall).toHaveBeenCalledTimes(2);
      });
    });

    it('handles concurrent requests to same endpoint', async () => {
      mockApiCall.mockImplementation(() => 
        new Promise(resolve => 
          setTimeout(() => resolve({ connection_status: 'connected' }), 100)
        )
      );

      // Start multiple hooks simultaneously
      const { result: result1 } = renderHook(() => useNetworkStatus(), { wrapper });
      const { result: result2 } = renderHook(() => useNetworkStatus(), { wrapper });
      const { result: result3 } = renderHook(() => useNetworkStatus(), { wrapper });

      await waitFor(() => {
        expect(result1.current.data).toBeTruthy();
        expect(result2.current.data).toBeTruthy();
        expect(result3.current.data).toBeTruthy();
      });

      // Should dedupe requests - only one API call
      expect(mockApiCall).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Recovery and Retry Logic', () => {
    it('retries failed requests with exponential backoff', async () => {
      // Configure retry for this test
      queryClient.setQueryDefaults(['network-status'], { 
        retry: 3,
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      });

      mockApiCall
        .mockRejectedValueOnce(new Error('Server error'))
        .mockRejectedValueOnce(new Error('Server error'))
        .mockResolvedValueOnce({ connection_status: 'connected' });

      const { result } = renderHook(() => useNetworkStatus(), { wrapper });

      // Should eventually succeed after retries
      await waitFor(() => {
        expect(result.current.data).toBeTruthy();
      }, { timeout: 10000 });

      expect(mockApiCall).toHaveBeenCalledTimes(3);
    });

    it('provides error recovery actions', async () => {
      const apiError = new Error('Network error');
      mockApiCall.mockRejectedValue(apiError);

      const { result } = renderHook(() => useNetworkStatus(), { wrapper });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      // Reset mock to return success
      mockApiCall.mockResolvedValue({ connection_status: 'connected' });

      // Manual refetch should recover
      await result.current.refetch();

      await waitFor(() => {
        expect(result.current.data).toBeTruthy();
        expect(result.current.error).toBe(null);
      });
    });

    it('handles partial data loading gracefully', async () => {
      // Mock scenario where some APIs fail
      mockApiCall
        .mockImplementation((endpoint) => {
          if (endpoint === 'network-status') {
            return Promise.resolve({ connection_status: 'connected' });
          }
          if (endpoint === 'billing-info') {
            return Promise.reject(new Error('Billing service unavailable'));
          }
          return Promise.resolve({});
        });

      const networkHook = renderHook(() => useNetworkStatus(), { wrapper });
      const billingHook = renderHook(() => useBillingInfo(), { wrapper });

      // Network should succeed
      await waitFor(() => {
        expect(networkHook.result.current.data).toBeTruthy();
        expect(networkHook.result.current.error).toBe(null);
      });

      // Billing should fail gracefully
      await waitFor(() => {
        expect(billingHook.result.current.error).toBeTruthy();
        expect(billingHook.result.current.data).toBeFalsy();
      });
    });
  });
});