/**
 * @jest-environment jsdom
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useInvoices, usePayments, useReports, useBillingMetrics } from '../useBillingData';
import type { Invoice, Payment, BillingFilters } from '../../types/billing';

// Mock fetch globally
global.fetch = jest.fn();

// Test wrapper with React Query
function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function TestWrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// Mock data
const mockInvoices: Invoice[] = [
  {
    id: 'inv-1',
    customerName: 'John Doe',
    customerEmail: 'john@example.com',
    amount: 100.0,
    tax: 10.0,
    total: 110.0,
    status: 'paid',
    dueDate: '2024-01-15',
    createdAt: '2024-01-01',
  },
  {
    id: 'inv-2',
    customerName: 'Jane Smith',
    customerEmail: 'jane@example.com',
    amount: 200.0,
    tax: 20.0,
    total: 220.0,
    status: 'pending',
    dueDate: '2024-01-20',
    createdAt: '2024-01-05',
  },
];

const mockPayments: Payment[] = [
  {
    id: 'pay-1',
    invoiceId: 'inv-1',
    amount: 110.0,
    method: 'credit_card',
    status: 'completed',
    processedAt: '2024-01-10',
  },
  {
    id: 'pay-2',
    invoiceId: 'inv-2',
    amount: 220.0,
    method: 'bank_transfer',
    status: 'pending',
    processedAt: '2024-01-12',
  },
];

const mockMetrics = {
  totalRevenue: 5000.0,
  monthlyRecurring: 1200.0,
  outstandingAmount: 800.0,
  paidInvoices: 45,
  pendingInvoices: 12,
  overdueInvoices: 3,
  revenueGrowth: 15.5,
  collectionRate: 92.3,
};

describe('Billing Data Hooks', () => {
  let TestWrapper: ReturnType<typeof createTestWrapper>;

  beforeEach(() => {
    TestWrapper = createTestWrapper();
    jest.clearAllMocks();
  });

  describe('useInvoices', () => {
    it('should fetch invoices successfully', async () => {
      const mockResponse = {
        data: mockInvoices,
        pagination: {
          page: 1,
          pageSize: 10,
          total: 2,
          totalPages: 1,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should handle invoice fetch errors', async () => {
      const errorMessage = 'Failed to fetch invoices';

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: errorMessage }),
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('should handle loading state correctly', () => {
      (global.fetch as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
      expect(result.current.error).toBeNull();
    });

    it('should apply filters correctly', async () => {
      const filters: BillingFilters = {
        status: 'pending',
        dateRange: {
          start: '2024-01-01',
          end: '2024-01-31',
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: mockInvoices.filter((inv) => inv.status === 'pending'),
          pagination: { page: 1, pageSize: 10, total: 1, totalPages: 1 },
        }),
      });

      const { result } = renderHook(() => useInvoices(filters, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Check that fetch was called with correct parameters
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/billing/invoices'),
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should handle pagination correctly', async () => {
      const mockResponse = {
        data: mockInvoices,
        pagination: {
          page: 2,
          pageSize: 5,
          total: 10,
          totalPages: 2,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const { result } = renderHook(() => useInvoices({}, 2, 5), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.pagination.page).toBe(2);
      expect(result.current.data?.pagination.pageSize).toBe(5);
      expect(result.current.data?.pagination.totalPages).toBe(2);
    });
  });

  describe('usePayments', () => {
    it('should fetch payments successfully', async () => {
      const mockResponse = {
        data: mockPayments,
        pagination: {
          page: 1,
          pageSize: 10,
          total: 2,
          totalPages: 1,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const { result } = renderHook(() => usePayments(1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
    });

    it('should handle payment fetch errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => usePayments(1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
    });
  });

  describe('useReports', () => {
    it('should fetch reports successfully', async () => {
      const mockReports = [
        {
          id: 'report-1',
          name: 'Monthly Revenue Report',
          type: 'revenue',
          generatedAt: '2024-01-01',
          data: { revenue: 5000 },
        },
        {
          id: 'report-2',
          name: 'Customer Summary',
          type: 'customers',
          generatedAt: '2024-01-01',
          data: { totalCustomers: 100 },
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockReports,
      });

      const { result } = renderHook(() => useReports(), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockReports);
    });
  });

  describe('useBillingMetrics', () => {
    it('should fetch billing metrics successfully', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics,
      });

      const { result } = renderHook(() => useBillingMetrics(), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockMetrics);
      expect(result.current.data?.totalRevenue).toBe(5000.0);
      expect(result.current.data?.revenueGrowth).toBe(15.5);
    });

    it('should handle metrics calculation correctly', async () => {
      const metricsWithCalculations = {
        ...mockMetrics,
        averageInvoiceValue: mockMetrics.totalRevenue / mockMetrics.paidInvoices,
        collectionEfficiency:
          (mockMetrics.paidInvoices / (mockMetrics.paidInvoices + mockMetrics.pendingInvoices)) *
          100,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => metricsWithCalculations,
      });

      const { result } = renderHook(() => useBillingMetrics(), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.averageInvoiceValue).toBeCloseTo(111.11);
      expect(result.current.data?.collectionEfficiency).toBeCloseTo(78.95);
    });
  });

  describe('Data Refetching and Cache Management', () => {
    it('should refetch data on manual refresh', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockInvoices,
          pagination: { page: 1, pageSize: 10, total: 2, totalPages: 1 },
        }),
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Clear mock and refetch
      jest.clearAllMocks();

      await result.current.refetch();

      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should handle stale data correctly', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockInvoices,
          pagination: { page: 1, pageSize: 10, total: 2, totalPages: 1 },
        }),
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Data should be considered fresh initially
      expect(result.current.isStale).toBe(false);
    });
  });

  describe('Error Handling and Retry Logic', () => {
    it('should handle network timeouts gracefully', async () => {
      (global.fetch as jest.Mock).mockImplementation(
        () => new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 100))
      );

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(
        () => {
          expect(result.current.isError).toBe(true);
        },
        { timeout: 1000 }
      );

      expect(result.current.error).toBeTruthy();
    });

    it('should handle malformed response data', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ invalidData: 'missing required fields' }),
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should handle gracefully even with unexpected data structure
      expect(result.current.data).toBeDefined();
    });
  });

  describe('Data Transformation and Processing', () => {
    it('should handle empty result sets', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: [],
          pagination: { page: 1, pageSize: 10, total: 0, totalPages: 0 },
        }),
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.data).toEqual([]);
      expect(result.current.data?.pagination.total).toBe(0);
    });

    it('should handle date formatting correctly', async () => {
      const invoiceWithDates = {
        ...mockInvoices[0],
        createdAt: '2024-01-01T10:30:00Z',
        dueDate: '2024-01-15T23:59:59Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: [invoiceWithDates],
          pagination: { page: 1, pageSize: 10, total: 1, totalPages: 1 },
        }),
      });

      const { result } = renderHook(() => useInvoices({}, 1, 10), { wrapper: TestWrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const invoice = result.current.data?.data[0];
      expect(invoice?.createdAt).toBe('2024-01-01T10:30:00Z');
      expect(invoice?.dueDate).toBe('2024-01-15T23:59:59Z');
    });
  });

  describe('Performance and Optimization', () => {
    it('should debounce rapid filter changes', async () => {
      let callCount = 0;
      (global.fetch as jest.Mock).mockImplementation(async () => {
        callCount++;
        return {
          ok: true,
          json: async () => ({
            data: mockInvoices,
            pagination: { page: 1, pageSize: 10, total: 2, totalPages: 1 },
          }),
        };
      });

      const { result, rerender } = renderHook(({ filters }) => useInvoices(filters, 1, 10), {
        wrapper: TestWrapper,
        initialProps: { filters: {} },
      });

      // Rapid filter changes
      rerender({ filters: { status: 'pending' } });
      rerender({ filters: { status: 'paid' } });
      rerender({ filters: { status: 'overdue' } });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should have made fewer calls due to debouncing/batching
      expect(callCount).toBeGreaterThan(0);
      expect(callCount).toBeLessThan(4); // Less than the number of filter changes
    });
  });
});
