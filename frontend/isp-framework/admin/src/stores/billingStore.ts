/**
 * Billing Store - Unified Management Operations Integration
 * Leverages existing systems through hooks-based architecture
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Invoice, Payment, Report, DashboardStats } from '@dotmac/headless/management/types';

interface BillingState {
  // Data state managed by unified operations
  invoices: Invoice[];
  payments: Payment[];
  reports: Report[];
  dashboardStats: DashboardStats | null;

  // UI state
  selectedTab: 'invoices' | 'payments' | 'reports' | 'analytics';
  selectedInvoices: Set<string>;
  searchQuery: string;
  showFilters: boolean;

  // Loading states
  loading: {
    invoices: boolean;
    payments: boolean;
    reports: boolean;
    metrics: boolean;
  };

  // Error states
  errors: {
    invoices: string | null;
    payments: string | null;
    reports: string | null;
    metrics: string | null;
  };

  // Actions
  setSelectedTab: (tab: 'invoices' | 'payments' | 'reports' | 'analytics') => void;
  setSearchQuery: (query: string) => void;
  toggleInvoiceSelection: (invoiceId: string) => void;
  selectAllInvoices: (select: boolean) => void;
  setShowFilters: (show: boolean) => void;

  // Data actions
  fetchInvoices: () => Promise<void>;
  fetchPayments: () => Promise<void>;
  fetchReports: () => Promise<void>;
  fetchMetrics: () => Promise<void>;

  // Business actions
  sendInvoiceReminder: (invoiceId: string) => Promise<void>;
  sendBulkReminders: (invoiceIds: string[]) => Promise<void>;
  downloadInvoice: (invoiceId: string) => Promise<void>;
  downloadReport: (reportId: string) => Promise<void>;
  generateReport: (type: string, config: any) => Promise<void>;

  // Computed values
  getFilteredInvoices: () => Invoice[];
  getTotalRevenue: () => number;
  getOverdueInvoices: () => Invoice[];
}

export const useBillingStore = create<BillingState>()(
  immer((set, get) => ({
    // Initial state
    invoices: [],
    payments: [],
    reports: [],
    metrics: null,

    selectedTab: 'invoices',
    selectedInvoices: new Set(),
    searchQuery: '',
    showFilters: false,

    loading: {
      invoices: false,
      payments: false,
      reports: false,
      metrics: false,
    },

    errors: {
      invoices: null,
      payments: null,
      reports: null,
      metrics: null,
    },

    // UI Actions
    setSelectedTab: (tab) => {
      set((state) => {
        state.selectedTab = tab;
      });
    },

    setSearchQuery: (query) => {
      set((state) => {
        state.searchQuery = query;
      });
    },

    toggleInvoiceSelection: (invoiceId) => {
      set((state) => {
        if (state.selectedInvoices.has(invoiceId)) {
          state.selectedInvoices.delete(invoiceId);
        } else {
          state.selectedInvoices.add(invoiceId);
        }
      });
    },

    selectAllInvoices: (select) => {
      set((state) => {
        if (select) {
          state.selectedInvoices = new Set(state.invoices.map((i) => i.id));
        } else {
          state.selectedInvoices.clear();
        }
      });
    },

    setShowFilters: (show) => {
      set((state) => {
        state.showFilters = show;
      });
    },

    // Data Actions - Leverage unified management operations through hooks
    fetchInvoices: async () => {
      // Data management handled by useBillingOperations hook
      // Store only manages UI state, data comes from unified operations
    },

    fetchPayments: async () => {
      // Data management handled by useBillingOperations hook
    },

    fetchReports: async () => {
      // Data management handled by useBillingOperations hook
    },

    fetchMetrics: async () => {
      // Data management handled by useBillingOperations hook
    },

    // Business Actions - Leverage unified management operations
    sendInvoiceReminder: async (invoiceId) => {
      // Business logic handled by useBillingOperations hook
    },

    sendBulkReminders: async (invoiceIds) => {
      // Business logic handled by useBillingOperations hook
    },

    downloadInvoice: async (invoiceId) => {
      // File operations handled by useBillingOperations hook
    },

    downloadReport: async (reportId) => {
      // File operations handled by useBillingOperations hook
    },

    generateReport: async (type, config) => {
      // Report generation handled by useBillingOperations hook
    },

    // Computed Values
    getFilteredInvoices: () => {
      const { invoices, searchQuery } = get();

      if (!searchQuery) return invoices;

      const query = searchQuery.toLowerCase();
      return invoices.filter(
        (invoice) =>
          invoice.id.toLowerCase().includes(query) ||
          invoice.customerName.toLowerCase().includes(query) ||
          invoice.customerEmail.toLowerCase().includes(query)
      );
    },

    getTotalRevenue: () => {
      const { invoices } = get();
      return invoices
        .filter((invoice) => invoice.status === 'paid')
        .reduce((total, invoice) => total + invoice.total, 0);
    },

    getOverdueInvoices: () => {
      const { invoices } = get();
      const now = new Date();
      return invoices.filter(
        (invoice) =>
          invoice.status === 'overdue' ||
          (invoice.status === 'pending' && new Date(invoice.dueDate) < now)
      );
    },
  }))
);

// Selectors for better performance
export const billingSelectors = {
  getFilteredInvoices: (state: BillingState) => state.getFilteredInvoices(),
  getTotalRevenue: (state: BillingState) => state.getTotalRevenue(),
  getOverdueInvoices: (state: BillingState) => state.getOverdueInvoices(),
  getSelectedInvoicesCount: (state: BillingState) => state.selectedInvoices.size,
  isLoading: (state: BillingState) => Object.values(state.loading).some(Boolean),
  hasErrors: (state: BillingState) => Object.values(state.errors).some(Boolean),
};
