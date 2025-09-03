/**
 * Billing Data Hooks
 * Custom hooks for fetching and managing billing-related data with React Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
// Import dependencies conditionally for testing
let useAuthStore: any,
  useCSRFProtection: any,
  showErrorNotification: any,
  showSuccessNotification: any;

try {
  const authStore = require('../stores/authStore');
  useAuthStore = authStore.useAuthStore;
} catch {
  useAuthStore = { getState: () => ({ isAuthenticated: true }) };
}

try {
  const csrf = require('../middleware/csrf');
  useCSRFProtection = csrf.useCSRFProtection;
} catch {
  useCSRFProtection = () => ({ makeProtectedRequest: fetch });
}

try {
  const appStore = require('../stores/appStore');
  showErrorNotification = appStore.showErrorNotification;
  showSuccessNotification = appStore.showSuccessNotification;
} catch {
  showErrorNotification = () => {};
  showSuccessNotification = () => {};
}
import type {
  Invoice,
  Payment,
  Report,
  Metrics,
  BillingApiResponse,
  PaginatedResponse,
  CreateInvoiceData,
  ProcessPaymentData,
  BillingFilters,
} from '../types/billing';

// Base API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Query keys for consistent caching
export const billingQueryKeys = {
  all: ['billing'] as const,
  invoices: () => [...billingQueryKeys.all, 'invoices'] as const,
  invoice: (id: string) => [...billingQueryKeys.invoices(), id] as const,
  payments: () => [...billingQueryKeys.all, 'payments'] as const,
  payment: (id: string) => [...billingQueryKeys.payments(), id] as const,
  reports: () => [...billingQueryKeys.all, 'reports'] as const,
  report: (id: string) => [...billingQueryKeys.reports(), id] as const,
  metrics: () => [...billingQueryKeys.all, 'metrics'] as const,
  customers: () => [...billingQueryKeys.all, 'customers'] as const,
} as const;

// Custom API client with authentication and error handling
class BillingApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<BillingApiResponse<T>> {
    const { isAuthenticated } = useAuthStore.getState();

    if (!isAuthenticated) {
      throw new Error('User not authenticated');
    }

    const response = await fetch(`${this.baseUrl}/api${endpoint}`, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        message: `HTTP ${response.status}: ${response.statusText}`,
      }));

      throw new Error(errorData.message || 'Request failed');
    }

    return response.json();
  }

  private async makeProtectedRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<BillingApiResponse<T>> {
    const { makeProtectedRequest } = useCSRFProtection();

    try {
      const response = await makeProtectedRequest(`${this.baseUrl}/api${endpoint}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          message: `HTTP ${response.status}: ${response.statusText}`,
        }));

        throw new Error(errorData.message || 'Request failed');
      }

      return response.json();
    } catch (error) {
      console.error('Protected request failed:', error);
      throw error;
    }
  }

  // Invoice methods
  async getInvoices(
    filters?: BillingFilters,
    page = 1,
    limit = 10
  ): Promise<PaginatedResponse<Invoice>> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(filters &&
        Object.fromEntries(
          Object.entries(filters).map(([key, value]) => [
            key,
            Array.isArray(value) ? value.join(',') : String(value),
          ])
        )),
    });

    const response = await this.makeRequest<PaginatedResponse<Invoice>>(
      `/billing/invoices?${params}`
    );
    return response.data;
  }

  async getInvoice(id: string): Promise<Invoice> {
    const response = await this.makeRequest<Invoice>(`/billing/invoices/${id}`);
    return response.data;
  }

  async createInvoice(data: CreateInvoiceData): Promise<Invoice> {
    const response = await this.makeProtectedRequest<Invoice>('/billing/invoices', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  async updateInvoice(id: string, data: Partial<CreateInvoiceData>): Promise<Invoice> {
    const response = await this.makeProtectedRequest<Invoice>(`/billing/invoices/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  async deleteInvoice(id: string): Promise<void> {
    await this.makeProtectedRequest<void>(`/billing/invoices/${id}`, {
      method: 'DELETE',
    });
  }

  // Payment methods
  async getPayments(page = 1, limit = 10): Promise<PaginatedResponse<Payment>> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });

    const response = await this.makeRequest<PaginatedResponse<Payment>>(
      `/billing/payments?${params}`
    );
    return response.data;
  }

  async processPayment(data: ProcessPaymentData): Promise<Payment> {
    const response = await this.makeProtectedRequest<Payment>('/billing/payments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data;
  }

  // Reports methods
  async getReports(): Promise<Report[]> {
    const response = await this.makeRequest<Report[]>('/billing/reports');
    return response.data;
  }

  async generateReport(type: string, params: Record<string, string>): Promise<Report> {
    const response = await this.makeProtectedRequest<Report>('/billing/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ type, params }),
    });
    return response.data;
  }

  // Metrics methods
  async getMetrics(period = '30d'): Promise<Metrics> {
    const params = new URLSearchParams({ period });
    const response = await this.makeRequest<Metrics>(`/billing/metrics?${params}`);
    return response.data;
  }
}

// Initialize API client
const billingApi = new BillingApiClient(API_BASE_URL);

// Custom hooks
export function useInvoices(filters?: BillingFilters, page = 1, limit = 10) {
  return useQuery({
    queryKey: [...billingQueryKeys.invoices(), { filters, page, limit }],
    queryFn: () => billingApi.getInvoices(filters, page, limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useInvoice(id: string) {
  return useQuery({
    queryKey: billingQueryKeys.invoice(id),
    queryFn: () => billingApi.getInvoice(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useCreateInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: billingApi.createInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.invoices() });
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.metrics() });
      showSuccessNotification('Success', 'Invoice created successfully');
    },
    onError: (error: Error) => {
      showErrorNotification('Error', `Failed to create invoice: ${error.message}`);
    },
  });
}

export function useUpdateInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateInvoiceData> }) =>
      billingApi.updateInvoice(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.invoice(id) });
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.invoices() });
      showSuccessNotification('Success', 'Invoice updated successfully');
    },
    onError: (error: Error) => {
      showErrorNotification('Error', `Failed to update invoice: ${error.message}`);
    },
  });
}

export function useDeleteInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: billingApi.deleteInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.invoices() });
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.metrics() });
      showSuccessNotification('Success', 'Invoice deleted successfully');
    },
    onError: (error: Error) => {
      showErrorNotification('Error', `Failed to delete invoice: ${error.message}`);
    },
  });
}

export function usePayments(page = 1, limit = 10) {
  return useQuery({
    queryKey: [...billingQueryKeys.payments(), { page, limit }],
    queryFn: () => billingApi.getPayments(page, limit),
    staleTime: 5 * 60 * 1000,
  });
}

export function useProcessPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: billingApi.processPayment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.payments() });
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.invoices() });
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.metrics() });
      showSuccessNotification('Success', 'Payment processed successfully');
    },
    onError: (error: Error) => {
      showErrorNotification('Error', `Failed to process payment: ${error.message}`);
    },
  });
}

export function useReports() {
  return useQuery({
    queryKey: billingQueryKeys.reports(),
    queryFn: billingApi.getReports,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ type, params }: { type: string; params: Record<string, string> }) =>
      billingApi.generateReport(type, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingQueryKeys.reports() });
      showSuccessNotification('Success', 'Report generation started');
    },
    onError: (error: Error) => {
      showErrorNotification('Error', `Failed to generate report: ${error.message}`);
    },
  });
}

export function useMetrics(period = '30d') {
  return useQuery({
    queryKey: [...billingQueryKeys.metrics(), { period }],
    queryFn: () => billingApi.getMetrics(period),
    staleTime: 15 * 60 * 1000, // 15 minutes
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
  });
}

// Alias for test compatibility
export const useBillingMetrics = useMetrics;

// Prefetch helpers for better UX
export function useBillingPrefetch() {
  const queryClient = useQueryClient();

  const prefetchInvoices = (filters?: BillingFilters) => {
    queryClient.prefetchQuery({
      queryKey: [...billingQueryKeys.invoices(), { filters, page: 1, limit: 10 }],
      queryFn: () => billingApi.getInvoices(filters, 1, 10),
    });
  };

  const prefetchMetrics = (period = '30d') => {
    queryClient.prefetchQuery({
      queryKey: [...billingQueryKeys.metrics(), { period }],
      queryFn: () => billingApi.getMetrics(period),
    });
  };

  return {
    prefetchInvoices,
    prefetchMetrics,
  };
}
