/**
 * Billing Store Tests
 * Comprehensive test suite for the billing state management store
 */

import { renderHook, act } from '@testing-library/react';
import { useBillingStore, billingSelectors } from '../billingStore';
import { mockFetch, mockApiResponses, clearAllMocks } from '../../__tests__/test-utils';

// Mock the API client
jest.mock('../../lib/api-client', () => ({
  billingApi: {
    fetchInvoices: jest.fn(),
    fetchPayments: jest.fn(),
    fetchReports: jest.fn(),
    fetchMetrics: jest.fn(),
    sendInvoiceReminder: jest.fn(),
    sendBulkReminders: jest.fn(),
    downloadInvoice: jest.fn(),
    downloadReport: jest.fn(),
    generateReport: jest.fn(),
  },
}));

describe('useBillingStore', () => {
  beforeEach(() => {
    clearAllMocks();
    // Reset store state before each test
    useBillingStore.getState().invoices = [];
    useBillingStore.getState().payments = [];
    useBillingStore.getState().reports = [];
    useBillingStore.getState().metrics = null;
    useBillingStore.getState().selectedInvoices = new Set();
    useBillingStore.getState().selectedTab = 'invoices';
    useBillingStore.getState().searchQuery = '';
    useBillingStore.getState().showFilters = false;
    Object.keys(useBillingStore.getState().loading).forEach((key) => {
      (useBillingStore.getState().loading as any)[key] = false;
    });
    Object.keys(useBillingStore.getState().errors).forEach((key) => {
      (useBillingStore.getState().errors as any)[key] = null;
    });
  });

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const { result } = renderHook(() => useBillingStore());

      expect(result.current.invoices).toEqual([]);
      expect(result.current.payments).toEqual([]);
      expect(result.current.reports).toEqual([]);
      expect(result.current.metrics).toBe(null);
      expect(result.current.selectedTab).toBe('invoices');
      expect(result.current.selectedInvoices).toEqual(new Set());
      expect(result.current.searchQuery).toBe('');
      expect(result.current.showFilters).toBe(false);

      expect(result.current.loading.invoices).toBe(false);
      expect(result.current.loading.payments).toBe(false);
      expect(result.current.loading.reports).toBe(false);
      expect(result.current.loading.metrics).toBe(false);

      expect(result.current.errors.invoices).toBe(null);
      expect(result.current.errors.payments).toBe(null);
      expect(result.current.errors.reports).toBe(null);
      expect(result.current.errors.metrics).toBe(null);
    });
  });

  describe('UI State Management', () => {
    it('updates selected tab', () => {
      const { result } = renderHook(() => useBillingStore());

      act(() => {
        result.current.setSelectedTab('payments');
      });

      expect(result.current.selectedTab).toBe('payments');
    });

    it('updates search query', () => {
      const { result } = renderHook(() => useBillingStore());

      act(() => {
        result.current.setSearchQuery('test search');
      });

      expect(result.current.searchQuery).toBe('test search');
    });

    it('toggles invoice selection', () => {
      const { result } = renderHook(() => useBillingStore());

      act(() => {
        result.current.toggleInvoiceSelection('inv-001');
      });

      expect(result.current.selectedInvoices.has('inv-001')).toBe(true);

      act(() => {
        result.current.toggleInvoiceSelection('inv-001');
      });

      expect(result.current.selectedInvoices.has('inv-001')).toBe(false);
    });

    it('selects all invoices', () => {
      const { result } = renderHook(() => useBillingStore());

      // Set up some invoices first
      act(() => {
        useBillingStore.setState({
          invoices: [
            {
              id: 'inv-001',
              customerName: 'Test 1',
              customerEmail: 'test1@example.com',
              total: 100,
              status: 'pending',
              dueDate: '2025-01-15',
              lastReminderSent: null,
            },
            {
              id: 'inv-002',
              customerName: 'Test 2',
              customerEmail: 'test2@example.com',
              total: 200,
              status: 'pending',
              dueDate: '2025-01-16',
              lastReminderSent: null,
            },
          ],
        });
      });

      act(() => {
        result.current.selectAllInvoices(true);
      });

      expect(result.current.selectedInvoices.size).toBe(2);
      expect(result.current.selectedInvoices.has('inv-001')).toBe(true);
      expect(result.current.selectedInvoices.has('inv-002')).toBe(true);

      act(() => {
        result.current.selectAllInvoices(false);
      });

      expect(result.current.selectedInvoices.size).toBe(0);
    });

    it('toggles filter visibility', () => {
      const { result } = renderHook(() => useBillingStore());

      act(() => {
        result.current.setShowFilters(true);
      });

      expect(result.current.showFilters).toBe(true);
    });
  });

  describe('Data Fetching', () => {
    it('fetches invoices successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.fetchInvoices.mockResolvedValue(mockApiResponses.invoices);

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.fetchInvoices();
      });

      expect(billingApi.fetchInvoices).toHaveBeenCalled();
      expect(result.current.loading.invoices).toBe(false);
      expect(result.current.invoices).toEqual(mockApiResponses.invoices.data);
      expect(result.current.errors.invoices).toBe(null);
    });

    it('handles invoice fetch errors', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.fetchInvoices.mockResolvedValue({ success: false, error: 'Network error' });

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.fetchInvoices();
      });

      expect(result.current.loading.invoices).toBe(false);
      expect(result.current.errors.invoices).toBe('Network error');
      expect(result.current.invoices).toEqual([]);
    });

    it('fetches payments successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.fetchPayments.mockResolvedValue(mockApiResponses.payments);

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.fetchPayments();
      });

      expect(billingApi.fetchPayments).toHaveBeenCalled();
      expect(result.current.loading.payments).toBe(false);
      expect(result.current.payments).toEqual(mockApiResponses.payments.data);
    });

    it('fetches reports successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.fetchReports.mockResolvedValue({ success: true, data: [] });

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.fetchReports();
      });

      expect(billingApi.fetchReports).toHaveBeenCalled();
      expect(result.current.loading.reports).toBe(false);
      expect(result.current.reports).toEqual([]);
    });

    it('fetches metrics successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.fetchMetrics.mockResolvedValue(mockApiResponses.metrics);

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.fetchMetrics();
      });

      expect(billingApi.fetchMetrics).toHaveBeenCalled();
      expect(result.current.loading.metrics).toBe(false);
      expect(result.current.metrics).toEqual(mockApiResponses.metrics.data);
    });
  });

  describe('Business Actions', () => {
    it('sends invoice reminder successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.sendInvoiceReminder.mockResolvedValue({ success: true });

      // Set up initial state with an invoice
      act(() => {
        useBillingStore.setState({
          invoices: [
            {
              id: 'inv-001',
              customerName: 'Test',
              customerEmail: 'test@example.com',
              total: 100,
              status: 'pending',
              dueDate: '2025-01-15',
              lastReminderSent: null,
            },
          ],
        });
      });

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.sendInvoiceReminder('inv-001');
      });

      expect(billingApi.sendInvoiceReminder).toHaveBeenCalledWith('inv-001');
      // Check that the invoice was updated
      expect(result.current.invoices[0].lastReminderSent).toBeDefined();
    });

    it('sends bulk reminders successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.sendBulkReminders.mockResolvedValue({ success: true });

      // Set up initial state with invoices
      act(() => {
        useBillingStore.setState({
          invoices: [
            {
              id: 'inv-001',
              customerName: 'Test 1',
              customerEmail: 'test1@example.com',
              total: 100,
              status: 'pending',
              dueDate: '2025-01-15',
              lastReminderSent: null,
            },
            {
              id: 'inv-002',
              customerName: 'Test 2',
              customerEmail: 'test2@example.com',
              total: 200,
              status: 'pending',
              dueDate: '2025-01-16',
              lastReminderSent: null,
            },
          ],
        });
      });

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.sendBulkReminders(['inv-001', 'inv-002']);
      });

      expect(billingApi.sendBulkReminders).toHaveBeenCalledWith(['inv-001', 'inv-002']);
      // Check that all invoices were updated
      result.current.invoices.forEach((invoice) => {
        expect(invoice.lastReminderSent).toBeDefined();
      });
    });

    it('downloads invoice successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      const mockResponse = { blob: jest.fn().mockResolvedValue(new Blob(['test'])) };
      billingApi.downloadInvoice.mockResolvedValue({ success: true, data: mockResponse });

      // Mock DOM elements
      const mockAnchor = {
        href: '',
        download: '',
        click: jest.fn(),
      };
      const createElementSpy = jest
        .spyOn(document, 'createElement')
        .mockReturnValue(mockAnchor as any);
      const createObjectURLSpy = jest.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
      const revokeObjectURLSpy = jest.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
      const appendChildSpy = jest
        .spyOn(document.body, 'appendChild')
        .mockImplementation(() => mockAnchor as any);
      const removeChildSpy = jest
        .spyOn(document.body, 'removeChild')
        .mockImplementation(() => mockAnchor as any);

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.downloadInvoice('inv-001');
      });

      expect(billingApi.downloadInvoice).toHaveBeenCalledWith('inv-001');
      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(mockAnchor.click).toHaveBeenCalled();
      expect(mockAnchor.download).toBe('invoice-inv-001.pdf');

      // Clean up mocks
      createElementSpy.mockRestore();
      createObjectURLSpy.mockRestore();
      revokeObjectURLSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
    });

    it('generates report successfully', async () => {
      const { billingApi } = require('../../lib/api-client');
      const mockReport = { id: 'rep-001', name: 'Test Report' };
      billingApi.generateReport.mockResolvedValue({ success: true, data: { report: mockReport } });

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.generateReport('revenue', { period: 'monthly' });
      });

      expect(billingApi.generateReport).toHaveBeenCalledWith('revenue', { period: 'monthly' });
      expect(result.current.reports).toEqual([mockReport]);
    });
  });

  describe('Computed Values', () => {
    beforeEach(() => {
      // Set up test data
      act(() => {
        useBillingStore.setState({
          invoices: [
            {
              id: 'inv-001',
              customerName: 'John Doe',
              customerEmail: 'john@example.com',
              total: 100,
              status: 'paid',
              dueDate: '2025-01-15',
              lastReminderSent: null,
            },
            {
              id: 'inv-002',
              customerName: 'Jane Smith',
              customerEmail: 'jane@example.com',
              total: 200,
              status: 'pending',
              dueDate: '2025-01-16',
              lastReminderSent: null,
            },
            {
              id: 'inv-003',
              customerName: 'Bob Johnson',
              customerEmail: 'bob@example.com',
              total: 150,
              status: 'overdue',
              dueDate: '2024-12-01',
              lastReminderSent: null,
            },
          ],
          searchQuery: '',
        });
      });
    });

    it('filters invoices by search query', () => {
      const { result } = renderHook(() => useBillingStore());

      act(() => {
        result.current.setSearchQuery('john');
      });

      const filtered = result.current.getFilteredInvoices();
      expect(filtered).toHaveLength(2); // John Doe and Bob Johnson
      expect(filtered.map((inv) => inv.id)).toEqual(['inv-001', 'inv-003']);
    });

    it('calculates total revenue correctly', () => {
      const { result } = renderHook(() => useBillingStore());

      const totalRevenue = result.current.getTotalRevenue();
      expect(totalRevenue).toBe(100); // Only paid invoices
    });

    it('identifies overdue invoices', () => {
      const { result } = renderHook(() => useBillingStore());

      const overdueInvoices = result.current.getOverdueInvoices();
      expect(overdueInvoices).toHaveLength(1);
      expect(overdueInvoices[0].id).toBe('inv-003');
    });
  });

  describe('Selectors', () => {
    beforeEach(() => {
      act(() => {
        useBillingStore.setState({
          invoices: [
            {
              id: 'inv-001',
              customerName: 'Test',
              customerEmail: 'test@example.com',
              total: 100,
              status: 'paid',
              dueDate: '2025-01-15',
              lastReminderSent: null,
            },
          ],
          selectedInvoices: new Set(['inv-001']),
          loading: { invoices: true, payments: false, reports: false, metrics: false },
          errors: { invoices: 'Test error', payments: null, reports: null, metrics: null },
        });
      });
    });

    it('selector getSelectedInvoicesCount works correctly', () => {
      const state = useBillingStore.getState();
      const count = billingSelectors.getSelectedInvoicesCount(state);
      expect(count).toBe(1);
    });

    it('selector isLoading works correctly', () => {
      const state = useBillingStore.getState();
      const isLoading = billingSelectors.isLoading(state);
      expect(isLoading).toBe(true); // invoices is loading
    });

    it('selector hasErrors works correctly', () => {
      const state = useBillingStore.getState();
      const hasErrors = billingSelectors.hasErrors(state);
      expect(hasErrors).toBe(true); // invoices has error
    });
  });

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.sendInvoiceReminder.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useBillingStore());

      await expect(
        act(async () => {
          await result.current.sendInvoiceReminder('inv-001');
        })
      ).rejects.toThrow('Network error');
    });

    it('handles API errors gracefully', async () => {
      const { billingApi } = require('../../lib/api-client');
      billingApi.fetchInvoices.mockResolvedValue({
        success: false,
        error: 'API Error',
        code: 'API_ERROR',
      });

      const { result } = renderHook(() => useBillingStore());

      await act(async () => {
        await result.current.fetchInvoices();
      });

      expect(result.current.errors.invoices).toBe('API Error');
      expect(result.current.loading.invoices).toBe(false);
    });
  });
});
