/**
 * Billing Store - Centralized billing state management
 * Separates business logic from UI components
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Invoice, Payment, Report, Metrics } from '../types/billing';

interface BillingState {
  // Data state
  invoices: Invoice[];
  payments: Payment[];
  reports: Report[];
  metrics: Metrics | null;
  
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
          state.selectedInvoices = new Set(state.invoices.map(i => i.id));
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
    
    // Data Actions
    fetchInvoices: async () => {
      set((state) => {
        state.loading.invoices = true;
        state.errors.invoices = null;
      });
      
      try {
        // Try ISP Framework integration first, fallback to legacy API
        const { ispBillingIntegration, ISPDataTransformer } = await import('../lib/isp-integration');
        
        try {
          const response = await ispBillingIntegration.getInvoices({
            limit: 100, // Get more for better UX
          });
          
          if (response.success && response.data) {
            const transformedInvoices = response.data.invoices.map(
              ISPDataTransformer.transformInvoiceToAdminFormat
            );
            
            set((state) => {
              state.invoices = transformedInvoices;
              state.loading.invoices = false;
            });
            return;
          }
        } catch (ispError) {
          console.warn('ISP Framework unavailable, falling back to legacy API:', ispError);
        }
        
        // Fallback to legacy API
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.fetchInvoices();
        
        if (response.success) {
          set((state) => {
            state.invoices = response.data || [];
            state.loading.invoices = false;
          });
        } else {
          throw new Error(response.error || 'Failed to fetch invoices');
        }
        
      } catch (error) {
        set((state) => {
          state.errors.invoices = error instanceof Error ? error.message : 'Failed to fetch invoices';
          state.loading.invoices = false;
        });
      }
    },
    
    fetchPayments: async () => {
      set((state) => {
        state.loading.payments = true;
        state.errors.payments = null;
      });
      
      try {
        // Try ISP Framework integration first, fallback to legacy API
        const { ispBillingIntegration, ISPDataTransformer } = await import('../lib/isp-integration');
        
        try {
          const response = await ispBillingIntegration.getPayments({
            limit: 100,
          });
          
          if (response.success && response.data) {
            const transformedPayments = response.data.payments.map(
              ISPDataTransformer.transformPaymentToAdminFormat
            );
            
            set((state) => {
              state.payments = transformedPayments;
              state.loading.payments = false;
            });
            return;
          }
        } catch (ispError) {
          console.warn('ISP Framework unavailable for payments, falling back to legacy API:', ispError);
        }
        
        // Fallback to legacy API
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.fetchPayments();
        
        if (response.success) {
          set((state) => {
            state.payments = response.data || [];
            state.loading.payments = false;
          });
        } else {
          throw new Error(response.error || 'Failed to fetch payments');
        }
        
      } catch (error) {
        set((state) => {
          state.errors.payments = error instanceof Error ? error.message : 'Failed to fetch payments';
          state.loading.payments = false;
        });
      }
    },
    
    fetchReports: async () => {
      set((state) => {
        state.loading.reports = true;
        state.errors.reports = null;
      });
      
      try {
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.fetchReports();
        
        if (response.success) {
          set((state) => {
            state.reports = response.data || [];
            state.loading.reports = false;
          });
        } else {
          throw new Error(response.error || 'Failed to fetch reports');
        }
        
      } catch (error) {
        set((state) => {
          state.errors.reports = error instanceof Error ? error.message : 'Failed to fetch reports';
          state.loading.reports = false;
        });
      }
    },
    
    fetchMetrics: async () => {
      set((state) => {
        state.loading.metrics = true;
        state.errors.metrics = null;
      });
      
      try {
        // Try ISP Framework integration first, fallback to legacy API
        const { ispBillingIntegration, ISPDataTransformer } = await import('../lib/isp-integration');
        
        try {
          const response = await ispBillingIntegration.getBillingMetrics({
            date_from: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Last 90 days
            granularity: 'monthly',
          });
          
          if (response.success && response.data) {
            const transformedMetrics = ISPDataTransformer.transformMetricsToAdminFormat(response.data);
            
            set((state) => {
              state.metrics = transformedMetrics;
              state.loading.metrics = false;
            });
            return;
          }
        } catch (ispError) {
          console.warn('ISP Framework unavailable for metrics, falling back to legacy API:', ispError);
        }
        
        // Fallback to legacy API
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.fetchMetrics();
        
        if (response.success) {
          set((state) => {
            state.metrics = response.data;
            state.loading.metrics = false;
          });
        } else {
          throw new Error(response.error || 'Failed to fetch metrics');
        }
        
      } catch (error) {
        set((state) => {
          state.errors.metrics = error instanceof Error ? error.message : 'Failed to fetch metrics';
          state.loading.metrics = false;
        });
      }
    },
    
    // Business Actions
    sendInvoiceReminder: async (invoiceId) => {
      try {
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.sendInvoiceReminder(invoiceId);
        
        if (!response.success) {
          throw new Error(response.error || 'Failed to send reminder');
        }
        
        // Update invoice status if needed
        set((state) => {
          const invoice = state.invoices.find(i => i.id === invoiceId);
          if (invoice) {
            invoice.lastReminderSent = new Date().toISOString();
          }
        });
        
        console.info(`Reminder sent for invoice ${invoiceId}`);
      } catch (error) {
        console.error('Error sending reminder:', error);
        throw error;
      }
    },
    
    sendBulkReminders: async (invoiceIds) => {
      try {
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.sendBulkReminders(invoiceIds);
        
        if (!response.success) {
          throw new Error(response.error || 'Failed to send bulk reminders');
        }
        
        // Update invoice statuses
        set((state) => {
          const now = new Date().toISOString();
          state.invoices.forEach(invoice => {
            if (invoiceIds.includes(invoice.id)) {
              invoice.lastReminderSent = now;
            }
          });
        });
        
        console.info(`Bulk reminders sent for ${invoiceIds.length} invoices`);
      } catch (error) {
        console.error('Error sending bulk reminders:', error);
        throw error;
      }
    },
    
    downloadInvoice: async (invoiceId) => {
      try {
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.downloadInvoice(invoiceId);
        
        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to download invoice');
        }
        
        const fetchResponse = response.data as Response;
        const blob = await fetchResponse.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `invoice-${invoiceId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.info(`Invoice ${invoiceId} downloaded`);
      } catch (error) {
        console.error('Error downloading invoice:', error);
        throw error;
      }
    },
    
    downloadReport: async (reportId) => {
      try {
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.downloadReport(reportId);
        
        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to download report');
        }
        
        const fetchResponse = response.data as Response;
        const blob = await fetchResponse.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report-${reportId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.info(`Report ${reportId} downloaded`);
      } catch (error) {
        console.error('Error downloading report:', error);
        throw error;
      }
    },
    
    generateReport: async (type, config) => {
      try {
        const { billingApi } = await import('../lib/api-client');
        const response = await billingApi.generateReport(type, config);
        
        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to generate report');
        }
        
        // Add new report to state
        set((state) => {
          state.reports.unshift(response.data.report);
        });
        
        console.info(`Report generation started: ${response.data.report.id}`);
      } catch (error) {
        console.error('Error generating report:', error);
        throw error;
      }
    },
    
    // Computed Values
    getFilteredInvoices: () => {
      const { invoices, searchQuery } = get();
      
      if (!searchQuery) return invoices;
      
      const query = searchQuery.toLowerCase();
      return invoices.filter(invoice => 
        invoice.id.toLowerCase().includes(query) ||
        invoice.customerName.toLowerCase().includes(query) ||
        invoice.customerEmail.toLowerCase().includes(query)
      );
    },
    
    getTotalRevenue: () => {
      const { invoices } = get();
      return invoices
        .filter(invoice => invoice.status === 'paid')
        .reduce((total, invoice) => total + invoice.total, 0);
    },
    
    getOverdueInvoices: () => {
      const { invoices } = get();
      const now = new Date();
      return invoices.filter(invoice => 
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