/**
 * Cross-Service Communication Integration Tests
 * Tests real integration between frontend hooks and backend services
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';

// Import the real hooks we've implemented
import { useCustomerManagement } from '../../packages/headless/src/hooks/useCustomerManagement';
import { useNetworkOperations } from '../../packages/headless/src/hooks/useNetworkOperations';
import { useBillingOperations } from '../../packages/headless/src/hooks/useBillingOperations';
import { useISPOperations } from '../../packages/headless/src/hooks/useISPOperations';
import { useDataPersistence } from '../../packages/headless/src/hooks/useDataPersistence';
import { useStripePayments } from '../../packages/headless/src/hooks/useStripePayments';
import { useRealTimeSync } from '../../packages/headless/src/hooks/useRealTimeSync';

// Mock API client with realistic responses
jest.mock('../../packages/headless/src/api/client', () => ({
  getApiClient: () => ({
    request: jest.fn(),
    getCurrentUser: jest.fn(),
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn(),
  }),
}));

// Mock stores
jest.mock('../../packages/headless/src/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'test-user-1', email: 'test@example.com', name: 'Test User' },
    getValidToken: jest.fn().mockResolvedValue('valid-token'),
  }),
}));

jest.mock('../../packages/headless/src/stores/tenantStore', () => ({
  useTenantStore: () => ({
    currentTenant: { 
      tenant: { 
        id: 'test-tenant-1', 
        name: 'Test ISP',
        defaultCurrency: 'USD'
      } 
    },
  }),
}));

// Mock real-time sync
jest.mock('../../packages/headless/src/hooks/useRealTimeSync', () => ({
  useRealTimeSync: () => ({
    emit: jest.fn(),
    subscribe: jest.fn().mockReturnValue(() => {}),
    isConnected: true,
  }),
}));

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('Cross-Service Communication Integration Tests', () => {
  let mockApiClient: any;

  beforeEach(() => {
    const { getApiClient } = require('../../packages/headless/src/api/client');
    mockApiClient = getApiClient();
    
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default API responses
    mockApiClient.request.mockImplementation((url: string, options: any = {}) => {
      // Simulate network delay
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(getMockResponse(url, options));
        }, 100);
      });
    });
  });

  describe('Customer Management Integration', () => {
    it('should create customer and trigger real-time updates', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCustomerManagement(), { wrapper });

      // Setup mock response for customer creation
      mockApiClient.request.mockResolvedValueOnce({
        data: {
          customer: {
            id: 'cust-123',
            portalId: 'CUST000123',
            accountNumber: 'ACC-123',
            type: 'residential',
            status: 'active',
            contacts: [],
            addresses: [],
            services: [],
            billing: {
              preferredMethod: 'email',
              billingCycle: 'monthly',
              dueDay: 15,
              autoPayEnabled: false,
              paperlessBilling: true,
              currentBalance: 0,
              creditBalance: 0,
            },
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            createdBy: 'test-user-1',
            tags: [],
          },
        },
      });

      await act(async () => {
        const customerId = await result.current.createCustomer({
          type: 'residential',
          primaryContact: {
            firstName: 'John',
            lastName: 'Doe',
            email: 'john.doe@example.com',
            phone: '+1-555-123-4567',
            title: 'Mr.',
            canReceiveBilling: true,
            canReceiveTechnical: true,
            canReceiveMarketing: false,
          },
          serviceAddress: {
            street: '123 Main St',
            city: 'Anytown',
            state: 'NY',
            zipCode: '12345',
            country: 'US',
          },
          billingPreferences: {
            method: 'email',
            cycle: 'monthly',
            dueDay: 15,
            autoPayEnabled: false,
            paperlessBilling: true,
          },
          tags: ['new-customer', 'residential'],
        });

        expect(customerId).toBe('cust-123');
      });

      // Verify API call was made with correct data
      expect(mockApiClient.request).toHaveBeenCalledWith('/api/v1/customers', {
        method: 'POST',
        body: expect.objectContaining({
          type: 'residential',
          tenantId: 'test-tenant-1',
          createdBy: 'test-user-1',
        }),
      });
    });

    it('should handle customer service provisioning workflow', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCustomerManagement(), { wrapper });

      // Mock service addition response
      mockApiClient.request.mockResolvedValueOnce({
        data: {
          service: {
            id: 'svc-456',
            customerId: 'cust-123',
            serviceType: 'fiber',
            packageId: 'pkg-fiber-100',
            packageName: 'Fiber 100 Mbps',
            status: 'pending',
            bandwidth: { download: 100, upload: 100, unit: 'Mbps' },
            monthlyRate: 79.99,
            installationFee: 99.99,
          },
        },
      });

      await act(async () => {
        const serviceId = await result.current.addService('cust-123', {
          serviceType: 'fiber',
          packageId: 'pkg-fiber-100',
          serviceAddressId: 'addr-123',
          preferredInstallationDate: '2024-01-15',
          specialInstructions: 'Call before arrival',
        });

        expect(serviceId).toBe('svc-456');
      });
    });
  });

  describe('Network Operations Integration', () => {
    it('should discover network devices and update topology', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useNetworkOperations(), { wrapper });

      // Mock device discovery response
      mockApiClient.request.mockResolvedValueOnce({
        data: {
          discovered: 5,
          failed: 2,
          devices: [
            {
              id: 'dev-001',
              name: 'Core-Router-01',
              type: 'router',
              vendor: 'Cisco',
              model: 'ISR4331',
              ipAddress: '192.168.1.1',
              status: 'online',
              location: { site: 'Main Office' },
            },
          ],
        },
      });

      let discoveryResult;
      await act(async () => {
        discoveryResult = await result.current.discoverDevices('192.168.1.0/24', {
          snmpCommunity: 'public',
          snmpVersion: '2c',
        });
      });

      expect(discoveryResult).toEqual({
        discovered: 5,
        failed: 2,
      });

      // Verify devices were added to state
      expect(result.current.devices).toHaveLength(1);
      expect(result.current.devices[0].name).toBe('Core-Router-01');
    });

    it('should create and manage network incidents', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useNetworkOperations(), { wrapper });

      // Mock incident creation
      mockApiClient.request.mockResolvedValueOnce({
        data: {
          incident: {
            id: 'inc-001',
            title: 'Fiber Cut on Main Route',
            description: 'Construction activity caused fiber damage',
            severity: 'critical',
            status: 'open',
            affectedCustomers: 250,
            startTime: new Date().toISOString(),
          },
        },
      });

      let incidentId;
      await act(async () => {
        incidentId = await result.current.createIncident({
          title: 'Fiber Cut on Main Route',
          description: 'Construction activity caused fiber damage',
          severity: 'critical',
          category: 'outage',
          affectedDevices: ['dev-001'],
          estimatedResolution: '2024-01-15T18:00:00Z',
        });
      });

      expect(incidentId).toBe('inc-001');
    });
  });

  describe('Billing Operations Integration', () => {
    it('should generate usage-based invoice and process payment', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useBillingOperations(), { wrapper });

      // Mock usage billing process
      mockApiClient.request.mockResolvedValueOnce({
        data: {
          invoice: {
            id: 'inv-001',
            invoiceNumber: 'INV-2024-0001',
            customerId: 'cust-123',
            total: 125.47,
            amountDue: 125.47,
            status: 'sent',
          },
          amount: 125.47,
          usageRecords: [
            {
              id: 'usage-001',
              customerId: 'cust-123',
              usage: { download: 1024000000, upload: 512000000 },
              billing: { overageCharge: 15.47 },
            },
          ],
        },
      });

      let usageResult;
      await act(async () => {
        usageResult = await result.current.processUsageBilling('cust-123', {
          start: '2024-01-01T00:00:00Z',
          end: '2024-01-31T23:59:59Z',
        });
      });

      expect(usageResult).toEqual({
        invoiceId: 'inv-001',
        amount: 125.47,
        usageRecords: 1,
      });
    });

    it('should record payment and update invoice status', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useBillingOperations(), { wrapper });

      // Mock payment recording
      mockApiClient.request.mockResolvedValueOnce({
        data: {
          payment: {
            id: 'pay-001',
            amount: 125.47,
            method: 'credit_card',
            status: 'completed',
          },
          invoice: {
            id: 'inv-001',
            status: 'paid',
            amountPaid: 125.47,
            amountDue: 0,
          },
        },
      });

      let paymentResult;
      await act(async () => {
        paymentResult = await result.current.recordPayment('inv-001', {
          amount: 125.47,
          method: 'credit_card',
          transactionId: 'txn_abc123',
        });
      });

      expect(paymentResult).toBe(true);
    });
  });

  describe('Payment Processing Integration', () => {
    it('should integrate Stripe payment flow with billing', async () => {
      const wrapper = createWrapper();
      const stripeHook = renderHook(() => useStripePayments(), { wrapper });
      const billingHook = renderHook(() => useBillingOperations(), { wrapper });

      // Mock Stripe payment intent creation
      mockApiClient.request.mockImplementation((url: string) => {
        if (url.includes('/stripe/intents')) {
          return Promise.resolve({
            data: {
              paymentIntent: {
                id: 'pi_test123',
                clientSecret: 'pi_test123_secret_test',
                status: 'requires_payment_method',
                amount: 12547, // $125.47 in cents
                currency: 'usd',
              },
            },
          });
        }
        return Promise.resolve({ data: {} });
      });

      let paymentIntent;
      await act(async () => {
        paymentIntent = await stripeHook.result.current.createPaymentIntent(
          125.47,
          'usd',
          'cust-123',
          {
            description: 'Monthly Service Invoice #INV-2024-0001',
            setupFutureUsage: 'off_session',
          }
        );
      });

      expect(paymentIntent).toEqual({
        id: 'pi_test123',
        clientSecret: 'pi_test123_secret_test',
        status: 'requires_payment_method',
        amount: 12547,
        currency: 'usd',
      });
    });
  });

  describe('Data Persistence Integration', () => {
    it('should handle offline operations and sync when online', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useDataPersistence(), { wrapper });

      // Queue offline operation
      let operationId;
      await act(async () => {
        operationId = result.current.queueOperation({
          type: 'create',
          entity: 'customers',
          entityId: 'temp-customer-1',
          data: { name: 'Offline Customer', type: 'residential' },
          maxRetries: 3,
        });
      });

      expect(operationId).toBeDefined();
      expect(result.current.pendingOperations).toHaveLength(1);

      // Mock successful sync
      mockApiClient.request.mockResolvedValueOnce({
        data: { customer: { id: 'cust-synced-1' } },
      });

      // Simulate coming back online and syncing
      await act(async () => {
        const syncResult = await result.current.syncPendingOperations();
        expect(syncResult.synced).toBe(1);
      });

      expect(result.current.pendingOperations).toHaveLength(0);
    });

    it('should handle data conflicts and provide resolution options', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useDataPersistence(), { wrapper });

      // Queue operation that will conflict
      const operationId = result.current.queueOperation({
        type: 'update',
        entity: 'customers',
        entityId: 'cust-123',
        data: { name: 'Updated Name', status: 'active' },
        maxRetries: 3,
      });

      // Mock conflict response
      mockApiClient.request.mockRejectedValueOnce({
        status: 409,
        data: {
          conflictType: 'concurrent_edit',
          serverData: { name: 'Different Name', status: 'suspended' },
        },
      });

      // Trigger sync that will create conflict
      await act(async () => {
        await result.current.syncPendingOperations();
      });

      expect(result.current.conflicts).toHaveLength(1);
      expect(result.current.conflicts[0].conflictType).toBe('concurrent_edit');

      // Resolve conflict with server data
      mockApiClient.request.mockResolvedValueOnce({
        data: { customer: { id: 'cust-123', name: 'Different Name' } },
      });

      await act(async () => {
        const resolved = await result.current.resolveConflict(operationId, 'server');
        expect(resolved).toBe(true);
      });

      expect(result.current.conflicts).toHaveLength(0);
    });
  });

  describe('Real-Time Communication Integration', () => {
    it('should handle cross-service real-time events', async () => {
      const wrapper = createWrapper();
      
      const customerHook = renderHook(() => useCustomerManagement(), { wrapper });
      const networkHook = renderHook(() => useNetworkOperations(), { wrapper });
      const realtimeHook = renderHook(() => useRealTimeSync(), { wrapper });

      // Mock real-time event subscription
      const mockSubscribe = realtimeHook.result.current.subscribe;
      const mockEmit = realtimeHook.result.current.emit;

      // Simulate service outage affecting customers
      await act(async () => {
        // Network hook emits outage event
        mockEmit('network:outage', {
          deviceId: 'dev-001',
          affectedCustomers: ['cust-123', 'cust-456'],
          severity: 'critical',
        });

        // Simulate real-time handler in customer management
        const eventHandler = mockSubscribe.mock.calls.find(
          (call) => call[0] === 'network:*'
        )?.[1];

        if (eventHandler) {
          eventHandler({
            type: 'network:outage',
            data: {
              deviceId: 'dev-001',
              affectedCustomers: ['cust-123', 'cust-456'],
              severity: 'critical',
            },
            timestamp: Date.now(),
          });
        }
      });

      // Verify cross-service communication worked
      expect(mockEmit).toHaveBeenCalledWith('network:outage', expect.any(Object));
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle API failures gracefully with retry logic', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCustomerManagement(), { wrapper });

      // Mock API failure followed by success
      mockApiClient.request
        .mockRejectedValueOnce(new Error('Network timeout'))
        .mockRejectedValueOnce(new Error('Server error'))
        .mockResolvedValueOnce({
          data: { customers: [], total: 0 },
        });

      await act(async () => {
        await result.current.loadCustomers();
      });

      // Should eventually succeed after retries
      await waitFor(() => {
        expect(result.current.customers).toEqual([]);
      });

      // Verify retry attempts were made
      expect(mockApiClient.request).toHaveBeenCalledTimes(3);
    });
  });
});

// Helper function to generate mock API responses
function getMockResponse(url: string, options: any = {}) {
  const method = options.method || 'GET';
  
  if (url.includes('/customers') && method === 'GET') {
    return { data: { customers: [], total: 0 } };
  }
  
  if (url.includes('/customers') && method === 'POST') {
    return {
      data: {
        customer: {
          id: 'mock-customer-id',
          ...options.body,
        },
      },
    };
  }
  
  if (url.includes('/network/devices')) {
    return { data: { devices: [] } };
  }
  
  if (url.includes('/billing/invoices')) {
    return { data: { invoices: [] } };
  }
  
  return { data: {} };
}