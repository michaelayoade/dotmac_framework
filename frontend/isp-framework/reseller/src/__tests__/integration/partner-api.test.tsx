/**
 * Frontend-Backend Integration Tests for Partner Portal
 */

import {
  commissionEngine,
  partnerApiClient,
  usePartnerCustomers,
  usePartnerDashboard,
} from '@dotmac/headless';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';

// Mock server setup
const mockServer = {
  baseURL: 'http://localhost:8000',
  handlers: new Map(),

  get(path: string, handler: Function) {
    this.handlers.set(`GET:${path}`, handler);
  },

  post(path: string, handler: Function) {
    this.handlers.set(`POST:${path}`, handler);
  },

  handle(method: string, path: string, data?: any) {
    const key = `${method}:${path}`;
    const handler = this.handlers.get(key);
    if (handler) {
      return handler(data);
    }
    throw new Error(`No handler for ${key}`);
  },
};

// Test data
const mockPartnerData = {
  partner: {
    id: 'test-partner-123',
    name: 'Test Partner Inc',
    partner_code: 'TEST001',
    territory: 'Test Territory',
    join_date: '2023-06-15T00:00:00Z',
    status: 'active',
    tier: 'Gold',
    contact: {
      name: 'John Doe',
      email: 'john@testpartner.com',
      phone: '+1-555-0123',
    },
  },
  performance: {
    customers_total: 247,
    customers_active: 234,
    customers_this_month: 23,
    revenue: {
      total: 487650,
      this_month: 45780,
      last_month: 42150,
      growth: 8.6,
    },
    commissions: {
      earned: 24382.5,
      pending: 2289.0,
      this_month: 2289.0,
      last_payout: 22093.5,
      next_payout_date: '2024-02-15T00:00:00Z',
    },
    targets: {
      monthly_customers: { current: 23, target: 25, unit: 'customers' },
      monthly_revenue: { current: 45780, target: 50000, unit: 'revenue' },
      quarterly_growth: { current: 8.6, target: 10, unit: 'percentage' },
    },
  },
  recent_customers: [
    {
      id: 'CUST-247',
      name: 'Acme Corp',
      service: 'Fiber 500/500',
      signup_date: '2024-01-28T00:00:00Z',
      status: 'active',
      revenue: 199.99,
      commission: 20.0,
    },
  ],
  sales_goals: [
    {
      id: 'goal-1',
      title: 'Q1 New Customers',
      target: 75,
      current: 23,
      progress: 30.7,
      deadline: '2024-03-31T23:59:59Z',
      status: 'active',
    },
  ],
};

const mockCustomersData = {
  customers: [
    {
      id: 'CUST-101',
      name: 'Acme Corporation',
      email: 'admin@acme.com',
      phone: '+1-555-123-4567',
      address: '123 Business Ave, Tech City, TC 12345',
      plan: 'enterprise',
      mrr: 299.99,
      status: 'active',
      join_date: '2024-01-15T00:00:00Z',
      last_payment: '2024-03-01T00:00:00Z',
      connection_status: 'online',
      usage: 78.5,
    },
    {
      id: 'CUST-102',
      name: 'Local Coffee Shop',
      email: 'owner@localcafe.com',
      phone: '+1-555-987-6543',
      address: '456 Main St, Downtown, DT 54321',
      plan: 'business_pro',
      mrr: 79.99,
      status: 'active',
      join_date: '2024-02-10T00:00:00Z',
      last_payment: '2024-03-01T00:00:00Z',
      connection_status: 'online',
      usage: 42.3,
    },
  ],
  total: 2,
  page: 1,
  limit: 10,
  total_pages: 1,
  has_next: false,
  has_prev: false,
};

// Test wrapper component
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const TestWrapper = ({ children }: { children: ReactNode }) => {
  const queryClient = createTestQueryClient();
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

describe('Partner API Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();

    // Mock fetch globally
    global.fetch = jest.fn();

    // Setup mock API responses
    mockServer.get('/api/v1/partners/test-partner-123/dashboard', () => ({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: mockPartnerData }),
    }));

    mockServer.get('/api/v1/partners/test-partner-123/customers', () => ({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: mockCustomersData }),
    }));
  });

  afterEach(() => {
    queryClient.clear();
    jest.clearAllMocks();
  });

  describe('Dashboard API Integration', () => {
    it('should fetch dashboard data successfully', async () => {
      // Mock successful API response
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: mockPartnerData }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeNull();
      expect(result.current.data).toBeDefined();
      expect(result.current.data?.partner.id).toBe('test-partner-123');
      expect(result.current.data?.partner.name).toBe('Test Partner Inc');
    });

    it('should handle dashboard API errors gracefully', async () => {
      // Mock API error response
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () => Promise.resolve({ detail: 'Access denied to partner data' }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('should validate dashboard data structure', async () => {
      // Mock successful response
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: mockPartnerData }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });

      const data = result.current.data!;

      // Validate required fields
      expect(data.partner).toBeDefined();
      expect(data.partner.id).toBeDefined();
      expect(data.partner.name).toBeDefined();
      expect(data.partner.partner_code).toBeDefined();
      expect(data.partner.tier).toBeDefined();

      expect(data.performance).toBeDefined();
      expect(data.performance.customers_total).toBeGreaterThanOrEqual(0);
      expect(data.performance.revenue.total).toBeGreaterThanOrEqual(0);
      expect(data.performance.commissions.earned).toBeGreaterThanOrEqual(0);

      expect(Array.isArray(data.recent_customers)).toBe(true);
      expect(Array.isArray(data.sales_goals)).toBe(true);
    });
  });

  describe('Customer API Integration', () => {
    it('should fetch customers with pagination', async () => {
      // Mock successful API response
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: mockCustomersData }),
      });

      const { result } = renderHook(
        () => usePartnerCustomers('test-partner-123', { page: 1, limit: 10 }),
        { wrapper: TestWrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeNull();
      expect(result.current.data).toBeDefined();
      expect(result.current.data?.customers).toHaveLength(2);
      expect(result.current.data?.total).toBe(2);
      expect(result.current.data?.page).toBe(1);
    });

    it('should handle customer search and filtering', async () => {
      const searchParams = {
        page: 1,
        limit: 10,
        search: 'acme',
        status: 'active',
      };

      // Mock filtered API response
      const filteredResponse = {
        ...mockCustomersData,
        customers: mockCustomersData.customers.filter(
          (c) => c.name.toLowerCase().includes('acme') && c.status === 'active'
        ),
        total: 1,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: filteredResponse }),
      });

      const { result } = renderHook(() => usePartnerCustomers('test-partner-123', searchParams), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data?.customers).toHaveLength(1);
      expect(result.current.data?.customers[0].name).toContain('Acme');

      // Verify API was called with correct parameters
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('search=acme'),
        expect.any(Object)
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('status=active'),
        expect.any(Object)
      );
    });

    it('should validate customer data structure', async () => {
      // Mock successful response
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: mockCustomersData }),
      });

      const { result } = renderHook(() => usePartnerCustomers('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });

      const customers = result.current.data!.customers;

      customers.forEach((customer) => {
        expect(customer.id).toBeDefined();
        expect(customer.name).toBeDefined();
        expect(customer.email).toMatch(/^[^\s@]+@[^\s@]+\.[^\s@]+$/);
        expect(customer.phone).toBeDefined();
        expect(customer.address).toBeDefined();
        expect(customer.plan).toBeDefined();
        expect(customer.mrr).toBeGreaterThan(0);
        expect(['active', 'pending', 'suspended', 'cancelled']).toContain(customer.status);
      });
    });
  });

  describe('Commission Calculation Integration', () => {
    it('should calculate commission correctly', () => {
      const commissionInput = {
        customerId: 'CUST-101',
        partnerId: 'test-partner-123',
        partnerTier: 'gold' as const,
        productType: 'enterprise' as const,
        monthlyRevenue: 299.99,
        partnerLifetimeRevenue: 200000,
        isNewCustomer: true,
        contractLength: 24,
      };

      const result = commissionEngine.calculateCommission(commissionInput);

      expect(result.customerId).toBe('CUST-101');
      expect(result.partnerId).toBe('test-partner-123');
      expect(result.totalCommission).toBeGreaterThan(0);
      expect(result.effectiveRate).toBeGreaterThan(0);
      expect(result.effectiveRate).toBeLessThan(0.5); // Should be under 50%

      // Should have audit trail
      expect(result.auditTrail).toBeDefined();
      expect(result.auditTrail.length).toBeGreaterThan(0);

      // Should have breakdown
      expect(result.breakdown.baseAmount).toBe(299.99);
      expect(result.breakdown.newCustomerBonus).toBeGreaterThan(0);
      expect(result.breakdown.contractLengthBonus).toBeGreaterThan(0);
    });

    it('should validate commission security limits', () => {
      const invalidInput = {
        customerId: 'CUST-101',
        partnerId: 'test-partner-123',
        partnerTier: 'gold' as const,
        productType: 'enterprise' as const,
        monthlyRevenue: 100, // Low revenue
        partnerLifetimeRevenue: 1000000, // High lifetime revenue
        isNewCustomer: true,
        contractLength: 36,
        promotionalRate: 5.0, // Very high promotional rate to trigger security check
      };

      expect(() => {
        commissionEngine.calculateCommission(invalidInput);
      }).toThrow(/exceeds maximum allowed/);
    });

    it('should handle tier eligibility validation', () => {
      const invalidTierInput = {
        customerId: 'CUST-101',
        partnerId: 'test-partner-123',
        partnerTier: 'platinum' as const, // High tier
        productType: 'enterprise' as const,
        monthlyRevenue: 299.99,
        partnerLifetimeRevenue: 100000, // Too low for platinum
        isNewCustomer: false,
        contractLength: 12,
      };

      expect(() => {
        commissionEngine.calculateCommission(invalidTierInput);
      }).toThrow(/not eligible/);
    });
  });

  describe('API Client Validation', () => {
    it('should validate API responses using Zod schemas', async () => {
      // Mock invalid response structure
      const invalidResponse = {
        partner: {
          id: 'test-partner-123',
          // Missing required fields
        },
        performance: {
          // Invalid structure
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: invalidResponse }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should have error due to validation failure
      expect(result.current.error).toBeTruthy();
    });

    it('should sanitize input data', async () => {
      const maliciousInput = {
        name: '<script>alert("xss")</script>',
        email: 'test@example.com',
        phone: '+1-555-0123',
        address: '123 Test St',
        plan: 'business_pro',
        mrr: 99.99,
      };

      // Mock successful creation
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () =>
          Promise.resolve({
            data: {
              ...maliciousInput,
              id: 'new-customer',
              status: 'pending',
            },
          }),
      });

      try {
        await partnerApiClient.createCustomer('test-partner-123', maliciousInput);
      } catch (error) {
        // Should throw validation error for malicious input
        expect(error).toBeDefined();
      }
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle network errors', async () => {
      // Mock network error
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('should handle authentication errors', async () => {
      // Mock 401 response
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Authentication required' }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
      // Should potentially trigger logout/redirect in real app
    });

    it('should handle authorization errors', async () => {
      // Mock 403 response
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () => Promise.resolve({ detail: 'Access denied to partner data' }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
    });

    it('should handle server errors gracefully', async () => {
      // Mock 500 response
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Internal server error' }),
      });

      const { result } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });
  });

  describe('Performance Integration', () => {
    it('should cache API responses appropriately', async () => {
      // Mock successful response
      (global.fetch as any).mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: mockPartnerData }),
      });

      // First call
      const { result: result1 } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
      });

      // Second call (should use cache)
      const { result: result2 } = renderHook(() => usePartnerDashboard('test-partner-123'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result2.current.isLoading).toBe(false);
      });

      // Should only have made one API call due to caching
      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(result1.current.data).toEqual(result2.current.data);
    });

    it('should handle concurrent requests efficiently', async () => {
      // Mock delayed response
      (global.fetch as any).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  status: 200,
                  json: () => Promise.resolve({ data: mockPartnerData }),
                }),
              100
            )
          )
      );

      // Make multiple concurrent requests
      const hooks = Array.from({ length: 5 }, () =>
        renderHook(() => usePartnerDashboard('test-partner-123'), {
          wrapper: TestWrapper,
        })
      );

      await Promise.all(
        hooks.map(({ result }) => waitFor(() => expect(result.current.isLoading).toBe(false)))
      );

      // Should have deduped requests (only 1 actual API call)
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // All hooks should have the same data
      const firstData = hooks[0].result.current.data;
      hooks.forEach(({ result }) => {
        expect(result.current.data).toEqual(firstData);
      });
    });
  });
});
