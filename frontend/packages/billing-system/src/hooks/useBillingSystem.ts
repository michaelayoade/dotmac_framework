import { useState, useEffect, useCallback, useMemo } from 'react';
import type {
  Invoice,
  Payment,
  PaymentMethod,
  BillingMetrics,
  BillingAccount,
  PaymentRequest,
  PaymentResponse,
  RefundRequest,
  BillingFilters,
  UniversalBillingProps
} from '../types';

interface UseBillingSystemOptions extends UniversalBillingProps {
  apiEndpoint?: string;
  websocketUrl?: string;
  pollInterval?: number;
  enableRealtime?: boolean;
  enableAutoRetry?: boolean;
  maxRetryAttempts?: number;
}

interface BillingSystemState {
  invoices: Invoice[];
  payments: Payment[];
  paymentMethods: PaymentMethod[];
  accounts: BillingAccount[];
  metrics: BillingMetrics | null;
  failedPayments: Payment[];
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
}

interface BillingSystemActions {
  // Invoice actions
  generateInvoice: (data: Partial<Invoice>) => Promise<Invoice>;
  sendInvoice: (invoiceId: string, email?: string) => Promise<void>;
  updateInvoiceStatus: (invoiceId: string, status: string) => Promise<Invoice>;

  // Payment actions
  processPayment: (paymentData: PaymentRequest) => Promise<PaymentResponse>;
  retryPayment: (paymentId: string, paymentMethodId?: string) => Promise<PaymentResponse>;
  refundPayment: (refundData: RefundRequest) => Promise<void>;

  // Payment method actions
  addPaymentMethod: (methodData: Partial<PaymentMethod>) => Promise<PaymentMethod>;
  updatePaymentMethod: (methodId: string, updates: Partial<PaymentMethod>) => Promise<PaymentMethod>;
  removePaymentMethod: (methodId: string) => Promise<void>;
  setDefaultPaymentMethod: (methodId: string) => Promise<void>;

  // Account actions
  selectAccount: (accountId: string) => void;

  // Utility actions
  refreshData: () => Promise<void>;
  applyFilters: (filters: BillingFilters) => void;
}

export function useBillingSystem(options: UseBillingSystemOptions = {}): BillingSystemState & BillingSystemActions {
  const {
    portalType = 'customer',
    customerId,
    accountId,
    apiEndpoint = '/api/billing',
    websocketUrl,
    pollInterval = 30000,
    enableRealtime = false,
    enableAutoRetry = false,
    maxRetryAttempts = 3,
    currency = 'USD'
  } = options;

  const [state, setState] = useState<BillingSystemState>({
    invoices: [],
    payments: [],
    paymentMethods: [],
    accounts: [],
    metrics: null,
    failedPayments: [],
    isLoading: true,
    error: null,
    isConnected: false
  });

  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(accountId || null);
  const [filters, setFilters] = useState<BillingFilters>({});
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  // API helper function
  const apiCall = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const response = await fetch(`${apiEndpoint}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }, [apiEndpoint]);

  // WebSocket connection
  useEffect(() => {
    if (!enableRealtime || !websocketUrl) return;

    const ws = new WebSocket(websocketUrl);

    ws.onopen = () => {
      setState(prev => ({ ...prev, isConnected: true }));

      // Subscribe to billing updates
      ws.send(JSON.stringify({
        type: 'subscribe',
        channel: 'billing',
        customerId,
        accountId: selectedAccountId
      }));
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case 'invoice_updated':
            setState(prev => ({
              ...prev,
              invoices: prev.invoices.map(inv =>
                inv.id === message.data.id ? message.data : inv
              )
            }));
            break;

          case 'payment_processed':
            setState(prev => ({
              ...prev,
              payments: [message.data, ...prev.payments],
              failedPayments: prev.failedPayments.filter(p => p.id !== message.data.id)
            }));
            break;

          case 'payment_failed':
            setState(prev => ({
              ...prev,
              failedPayments: [message.data, ...prev.failedPayments]
            }));
            break;

          case 'metrics_updated':
            setState(prev => ({
              ...prev,
              metrics: message.data
            }));
            break;
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    };

    ws.onclose = () => {
      setState(prev => ({ ...prev, isConnected: false }));
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setState(prev => ({ ...prev, error: 'Real-time connection failed' }));
    };

    setWsConnection(ws);

    return () => {
      ws.close();
      setWsConnection(null);
    };
  }, [enableRealtime, websocketUrl, customerId, selectedAccountId]);

  // Data fetching
  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const params = new URLSearchParams();
      if (customerId) params.set('customerId', customerId);
      if (selectedAccountId) params.set('accountId', selectedAccountId);

      const [invoicesRes, paymentsRes, methodsRes, accountsRes, metricsRes] = await Promise.all([
        apiCall(`/invoices?${params}`),
        apiCall(`/payments?${params}`),
        apiCall(`/payment-methods?${params}`),
        portalType === 'admin' ? apiCall(`/accounts?${params}`) : Promise.resolve([]),
        portalType !== 'customer' ? apiCall(`/metrics?${params}`) : Promise.resolve(null)
      ]);

      setState(prev => ({
        ...prev,
        invoices: invoicesRes.data || [],
        payments: paymentsRes.data || [],
        paymentMethods: methodsRes.data || [],
        accounts: accountsRes.data || [],
        metrics: metricsRes,
        failedPayments: (paymentsRes.data || []).filter((p: Payment) => p.status === 'failed'),
        isLoading: false
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to fetch data',
        isLoading: false
      }));
    }
  }, [apiCall, customerId, selectedAccountId, portalType]);

  // Initial data load
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Polling for non-realtime updates
  useEffect(() => {
    if (enableRealtime || !pollInterval) return;

    const interval = setInterval(fetchData, pollInterval);
    return () => clearInterval(interval);
  }, [enableRealtime, pollInterval, fetchData]);

  // Invoice actions
  const generateInvoice = useCallback(async (data: Partial<Invoice>): Promise<Invoice> => {
    const response = await apiCall('/invoices', {
      method: 'POST',
      body: JSON.stringify({ ...data, customerId, accountId: selectedAccountId })
    });

    const newInvoice = response.data;
    setState(prev => ({
      ...prev,
      invoices: [newInvoice, ...prev.invoices]
    }));

    return newInvoice;
  }, [apiCall, customerId, selectedAccountId]);

  const sendInvoice = useCallback(async (invoiceId: string, email?: string): Promise<void> => {
    await apiCall(`/invoices/${invoiceId}/send`, {
      method: 'POST',
      body: JSON.stringify({ email })
    });

    setState(prev => ({
      ...prev,
      invoices: prev.invoices.map(inv =>
        inv.id === invoiceId ? { ...inv, status: 'sent' as const } : inv
      )
    }));
  }, [apiCall]);

  const updateInvoiceStatus = useCallback(async (invoiceId: string, status: string): Promise<Invoice> => {
    const response = await apiCall(`/invoices/${invoiceId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });

    const updatedInvoice = response.data;
    setState(prev => ({
      ...prev,
      invoices: prev.invoices.map(inv =>
        inv.id === invoiceId ? updatedInvoice : inv
      )
    }));

    return updatedInvoice;
  }, [apiCall]);

  // Payment actions
  const processPayment = useCallback(async (paymentData: PaymentRequest): Promise<PaymentResponse> => {
    const response = await apiCall('/payments', {
      method: 'POST',
      body: JSON.stringify({ ...paymentData, customerId })
    });

    if (response.payment) {
      setState(prev => ({
        ...prev,
        payments: [response.payment, ...prev.payments],
        failedPayments: prev.failedPayments.filter(p => p.invoiceId !== response.payment.invoiceId)
      }));
    }

    return response;
  }, [apiCall, customerId]);

  const retryPayment = useCallback(async (paymentId: string, paymentMethodId?: string): Promise<PaymentResponse> => {
    const response = await apiCall(`/payments/${paymentId}/retry`, {
      method: 'POST',
      body: JSON.stringify({ paymentMethodId })
    });

    if (response.payment) {
      setState(prev => ({
        ...prev,
        payments: prev.payments.map(p => p.id === paymentId ? response.payment : p),
        failedPayments: prev.failedPayments.filter(p => p.id !== paymentId)
      }));
    }

    return response;
  }, [apiCall]);

  const refundPayment = useCallback(async (refundData: RefundRequest): Promise<void> => {
    await apiCall(`/payments/${refundData.paymentId}/refund`, {
      method: 'POST',
      body: JSON.stringify(refundData)
    });

    setState(prev => ({
      ...prev,
      payments: prev.payments.map(p =>
        p.id === refundData.paymentId
          ? { ...p, status: 'refunded' as const, refundedAmount: refundData.amount }
          : p
      )
    }));
  }, [apiCall]);

  // Payment method actions
  const addPaymentMethod = useCallback(async (methodData: Partial<PaymentMethod>): Promise<PaymentMethod> => {
    const response = await apiCall('/payment-methods', {
      method: 'POST',
      body: JSON.stringify({ ...methodData, customerId })
    });

    const newMethod = response.data;
    setState(prev => ({
      ...prev,
      paymentMethods: [...prev.paymentMethods, newMethod]
    }));

    return newMethod;
  }, [apiCall, customerId]);

  const updatePaymentMethod = useCallback(async (methodId: string, updates: Partial<PaymentMethod>): Promise<PaymentMethod> => {
    const response = await apiCall(`/payment-methods/${methodId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates)
    });

    const updatedMethod = response.data;
    setState(prev => ({
      ...prev,
      paymentMethods: prev.paymentMethods.map(m =>
        m.id === methodId ? updatedMethod : m
      )
    }));

    return updatedMethod;
  }, [apiCall]);

  const removePaymentMethod = useCallback(async (methodId: string): Promise<void> => {
    await apiCall(`/payment-methods/${methodId}`, {
      method: 'DELETE'
    });

    setState(prev => ({
      ...prev,
      paymentMethods: prev.paymentMethods.filter(m => m.id !== methodId)
    }));
  }, [apiCall]);

  const setDefaultPaymentMethod = useCallback(async (methodId: string): Promise<void> => {
    await apiCall(`/payment-methods/${methodId}/default`, {
      method: 'POST'
    });

    setState(prev => ({
      ...prev,
      paymentMethods: prev.paymentMethods.map(m => ({
        ...m,
        isDefault: m.id === methodId
      }))
    }));
  }, [apiCall]);

  // Account actions
  const selectAccount = useCallback((accountId: string) => {
    setSelectedAccountId(accountId);
  }, []);

  // Utility actions
  const refreshData = useCallback(async () => {
    await fetchData();
  }, [fetchData]);

  const applyFilters = useCallback((newFilters: BillingFilters) => {
    setFilters(newFilters);
  }, []);

  // Filtered data
  const filteredInvoices = useMemo(() => {
    let filtered = state.invoices;

    if (filters.status) {
      filtered = filtered.filter(inv => inv.status === filters.status);
    }

    if (filters.dateFrom) {
      filtered = filtered.filter(inv => new Date(inv.issueDate) >= new Date(filters.dateFrom!));
    }

    if (filters.dateTo) {
      filtered = filtered.filter(inv => new Date(inv.issueDate) <= new Date(filters.dateTo!));
    }

    if (filters.customerId) {
      filtered = filtered.filter(inv => inv.customerId.includes(filters.customerId!));
    }

    return filtered;
  }, [state.invoices, filters]);

  const filteredPayments = useMemo(() => {
    let filtered = state.payments;

    if (filters.status) {
      filtered = filtered.filter(pay => pay.status === filters.status);
    }

    if (filters.paymentMethod) {
      filtered = filtered.filter(pay => pay.method.type === filters.paymentMethod);
    }

    if (filters.gateway) {
      filtered = filtered.filter(pay => pay.gateway === filters.gateway);
    }

    return filtered;
  }, [state.payments, filters]);

  return {
    // State
    invoices: filteredInvoices,
    payments: filteredPayments,
    paymentMethods: state.paymentMethods,
    accounts: state.accounts,
    metrics: state.metrics,
    failedPayments: state.failedPayments,
    isLoading: state.isLoading,
    error: state.error,
    isConnected: state.isConnected,

    // Actions
    generateInvoice,
    sendInvoice,
    updateInvoiceStatus,
    processPayment,
    retryPayment,
    refundPayment,
    addPaymentMethod,
    updatePaymentMethod,
    removePaymentMethod,
    setDefaultPaymentMethod,
    selectAccount,
    refreshData,
    applyFilters
  };
}
