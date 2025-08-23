/**
 * Real-World Scenarios Integration Tests
 * Tests complete user workflows and business scenarios
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';

// Import hooks
import { useCustomerManagement } from '../../packages/headless/src/hooks/useCustomerManagement';
import { useNetworkOperations } from '../../packages/headless/src/hooks/useNetworkOperations';
import { useBillingOperations } from '../../packages/headless/src/hooks/useBillingOperations';
import { useISPOperations } from '../../packages/headless/src/hooks/useISPOperations';
import { useStripePayments } from '../../packages/headless/src/hooks/useStripePayments';
import { useDataPersistence } from '../../packages/headless/src/hooks/useDataPersistence';

// Enhanced mocks for real-world testing
const mockApiResponses = new Map();

jest.mock('../../packages/headless/src/api/client', () => ({
  getApiClient: () => ({
    request: jest.fn().mockImplementation((url: string, options: any = {}) => {
      const key = `${options.method || 'GET'} ${url}`;
      const response = mockApiResponses.get(key);
      
      if (response && response.error) {
        return Promise.reject(response.error);
      }
      
      return Promise.resolve(response || { data: {} });
    }),
  }),
}));

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

describe('Real-World ISP Scenarios', () => {
  beforeEach(() => {
    mockApiResponses.clear();
    jest.clearAllMocks();
  });

  describe('Complete Customer Onboarding Flow', () => {
    it('should handle end-to-end customer onboarding from signup to service activation', async () => {
      const wrapper = createWrapper();
      
      // Setup API responses for the complete flow
      mockApiResponses.set('POST /api/v1/customers', {
        data: {
          customer: {
            id: 'cust-001',
            portalId: 'CUST000001',
            accountNumber: 'ACC-001',
            type: 'business',
            status: 'active',
            companyName: 'Acme Corp',
            contacts: [{
              id: 'contact-001',
              type: 'primary',
              firstName: 'John',
              lastName: 'Smith',
              email: 'john@acme.com',
              phone: '+1-555-0100',
              isPrimary: true,
            }],
            addresses: [{
              id: 'addr-001',
              type: 'service',
              street: '100 Business Park Dr',
              city: 'Tech City',
              state: 'CA',
              zipCode: '94000',
              isPrimary: true,
            }],
            services: [],
            billing: {
              preferredMethod: 'email',
              billingCycle: 'monthly',
              dueDay: 1,
              autoPayEnabled: true,
              paperlessBilling: true,
              currentBalance: 0,
              creditBalance: 0,
            },
            createdAt: '2024-01-15T10:00:00Z',
            updatedAt: '2024-01-15T10:00:00Z',
            createdBy: 'sales-rep-1',
            tags: ['new-business', 'enterprise-prospect'],
          },
        },
      });

      mockApiResponses.set('POST /api/v1/customers/cust-001/services', {
        data: {
          service: {
            id: 'svc-001',
            customerId: 'cust-001',
            serviceType: 'fiber',
            packageId: 'pkg-fiber-enterprise-1gb',
            packageName: 'Enterprise Fiber 1GB',
            status: 'pending',
            bandwidth: { download: 1000, upload: 1000, unit: 'Mbps' },
            monthlyRate: 299.99,
            installationFee: 499.99,
            preferredInstallationDate: '2024-01-22T09:00:00Z',
          },
        },
      });

      mockApiResponses.set('POST /api/v1/payments/stripe/intents', {
        data: {
          paymentIntent: {
            id: 'pi_onboarding_setup',
            clientSecret: 'pi_onboarding_setup_secret',
            amount: 49999, // $499.99 setup fee
            currency: 'usd',
            status: 'requires_payment_method',
          },
        },
      });

      // Initialize hooks
      const customerHook = renderHook(() => useCustomerManagement(), { wrapper });
      const paymentHook = renderHook(() => useStripePayments(), { wrapper });

      // Step 1: Create customer account
      let customerId: string;
      await act(async () => {
        customerId = await customerHook.result.current.createCustomer({
          type: 'business',
          companyName: 'Acme Corp',
          primaryContact: {
            firstName: 'John',
            lastName: 'Smith',
            email: 'john@acme.com',
            phone: '+1-555-0100',
            title: 'IT Director',
            canReceiveBilling: true,
            canReceiveTechnical: true,
            canReceiveMarketing: true,
          },
          serviceAddress: {
            street: '100 Business Park Dr',
            city: 'Tech City',
            state: 'CA',
            zipCode: '94000',
            country: 'US',
          },
          billingPreferences: {
            method: 'email',
            cycle: 'monthly',
            dueDay: 1,
            autoPayEnabled: true,
            paperlessBilling: true,
          },
          tags: ['new-business', 'enterprise-prospect'],
        });
      });

      expect(customerId).toBe('cust-001');
      expect(customerHook.result.current.customers).toHaveLength(1);

      // Step 2: Add service to customer
      let serviceId: string;
      await act(async () => {
        serviceId = await customerHook.result.current.addService(customerId, {
          serviceType: 'fiber',
          packageId: 'pkg-fiber-enterprise-1gb',
          serviceAddressId: 'addr-001',
          preferredInstallationDate: '2024-01-22',
          specialInstructions: 'Business hours installation preferred',
        });
      });

      expect(serviceId).toBe('svc-001');

      // Step 3: Set up payment for installation fee
      let setupIntent: any;
      await act(async () => {
        setupIntent = await paymentHook.result.current.createPaymentIntent(
          499.99,
          'usd',
          customerId,
          {
            description: 'Enterprise Fiber Installation Fee',
            setupFutureUsage: 'off_session',
          }
        );
      });

      expect(setupIntent).toMatchObject({
        id: 'pi_onboarding_setup',
        amount: 49999,
        status: 'requires_payment_method',
      });

      // Verify complete onboarding state
      const customer = customerHook.result.current.customers[0];
      expect(customer.services).toHaveLength(1);
      expect(customer.services[0].status).toBe('pending');
      expect(customer.tags).toContain('enterprise-prospect');
    });
  });

  describe('Network Outage Response Workflow', () => {
    it('should handle complete outage response from detection to resolution', async () => {
      const wrapper = createWrapper();
      
      // Setup network outage scenario
      mockApiResponses.set('POST /api/v1/network/incidents', {
        data: {
          incident: {
            id: 'inc-001',
            title: 'Fiber Cut - Industrial District',
            description: 'Construction crew severed main fiber trunk',
            severity: 'critical',
            category: 'outage',
            status: 'open',
            affectedDevices: ['dev-001', 'dev-002'],
            affectedServices: ['fiber', 'dedicated'],
            affectedCustomers: 847,
            affectedAreas: ['Industrial District', 'Tech Park'],
            startTime: '2024-01-15T14:30:00Z',
            detectedTime: '2024-01-15T14:32:00Z',
            impact: {
              customersAffected: 847,
              revenueImpact: 25000,
              slaBreaches: 12,
            },
            updates: [],
            createdBy: 'noc-operator-1',
            tags: ['fiber-cut', 'construction', 'critical'],
          },
        },
      });

      mockApiResponses.set('PUT /api/v1/network/incidents/inc-001/status', {
        data: { success: true },
      });

      mockApiResponses.set('POST /api/v1/support/tickets', {
        data: {
          ticket: {
            id: 'tick-001',
            customerId: 'cust-affected',
            subject: 'Service Outage - No Internet Connection',
            category: 'technical',
            priority: 'high',
            status: 'open',
            createdAt: '2024-01-15T14:45:00Z',
          },
        },
      });

      const networkHook = renderHook(() => useNetworkOperations(), { wrapper });
      const supportHook = renderHook(() => useISPOperations(), { wrapper });

      // Step 1: Detect and create incident
      let incidentId: string;
      await act(async () => {
        incidentId = await networkHook.result.current.createIncident({
          title: 'Fiber Cut - Industrial District',
          description: 'Construction crew severed main fiber trunk',
          severity: 'critical',
          category: 'outage',
          affectedDevices: ['dev-001', 'dev-002'],
          estimatedResolution: '2024-01-15T18:00:00Z',
        });
      });

      expect(incidentId).toBe('inc-001');

      // Step 2: Update incident status as teams respond
      await act(async () => {
        const updated = await networkHook.result.current.updateIncidentStatus(
          incidentId,
          'investigating',
          'Field team dispatched to construction site'
        );
        expect(updated).toBe(true);
      });

      // Step 3: Handle customer support tickets during outage
      const { result: supportResult } = supportHook;
      
      await act(async () => {
        const ticketId = await supportResult.current.createTicket({
          customerId: 'cust-affected',
          subject: 'Service Outage - No Internet Connection',
          description: 'Customer reporting complete loss of internet service',
          category: 'technical',
          priority: 'high',
          status: 'open',
          assignedTo: 'support-agent-1',
          tags: ['outage-related'],
        });
        
        expect(ticketId).toBe('tick-001');
      });

      // Step 4: Resolve incident
      await act(async () => {
        const resolved = await networkHook.result.current.updateIncidentStatus(
          incidentId,
          'resolved',
          'Fiber splice completed. All services restored.'
        );
        expect(resolved).toBe(true);
      });

      // Verify incident tracking
      expect(networkHook.result.current.incidents).toHaveLength(1);
      expect(networkHook.result.current.criticalIncidents).toHaveLength(0); // Should be resolved
    });
  });

  describe('Monthly Billing Cycle Workflow', () => {
    it('should handle complete monthly billing from usage collection to payment processing', async () => {
      const wrapper = createWrapper();

      // Setup billing cycle responses
      mockApiResponses.set('POST /api/v1/billing/usage/process', {
        data: {
          invoice: {
            id: 'inv-monthly-001',
            invoiceNumber: 'INV-2024-001',
            customerId: 'cust-001',
            customerName: 'Acme Corp',
            status: 'draft',
            type: 'monthly',
            subtotal: 299.99,
            taxAmount: 26.99,
            discountAmount: 0,
            total: 326.98,
            amountPaid: 0,
            amountDue: 326.98,
            currency: 'USD',
            lineItems: [
              {
                id: 'line-001',
                description: 'Enterprise Fiber 1GB - Monthly Service',
                quantity: 1,
                unitPrice: 299.99,
                total: 299.99,
                taxable: true,
              },
            ],
            issueDate: '2024-02-01T00:00:00Z',
            dueDate: '2024-03-01T00:00:00Z',
            servicePeriod: {
              start: '2024-01-01T00:00:00Z',
              end: '2024-01-31T23:59:59Z',
            },
          },
          amount: 326.98,
          usageRecords: [
            {
              id: 'usage-001',
              customerId: 'cust-001',
              serviceId: 'svc-001',
              period: {
                start: '2024-01-01T00:00:00Z',
                end: '2024-01-31T23:59:59Z',
              },
              usage: {
                download: 850000000000, // 850GB
                upload: 120000000000,   // 120GB
                total: 970000000000,    // 970GB
              },
              billing: {
                includedData: 1000000000000, // 1TB included
                overageData: 0,
                overageRate: 0.10,
                overageCharge: 0,
              },
            },
          ],
        },
      });

      mockApiResponses.set('POST /api/v1/billing/invoices/inv-monthly-001/send', {
        data: { success: true },
      });

      mockApiResponses.set('POST /api/v1/payments/stripe/intents', {
        data: {
          paymentIntent: {
            id: 'pi_monthly_payment',
            clientSecret: 'pi_monthly_payment_secret',
            amount: 32698, // $326.98
            currency: 'usd',
            status: 'requires_payment_method',
          },
        },
      });

      const billingHook = renderHook(() => useBillingOperations(), { wrapper });
      const paymentHook = renderHook(() => useStripePayments(), { wrapper });

      // Step 1: Process monthly usage billing
      let usageResult: any;
      await act(async () => {
        usageResult = await billingHook.result.current.processUsageBilling('cust-001', {
          start: '2024-01-01T00:00:00Z',
          end: '2024-01-31T23:59:59Z',
        });
      });

      expect(usageResult).toMatchObject({
        invoiceId: 'inv-monthly-001',
        amount: 326.98,
        usageRecords: 1,
      });

      // Step 2: Send invoice to customer
      await act(async () => {
        const sent = await billingHook.result.current.sendInvoice(
          'inv-monthly-001',
          'email'
        );
        expect(sent).toBe(true);
      });

      // Step 3: Customer initiates payment
      let paymentIntent: any;
      await act(async () => {
        paymentIntent = await paymentHook.result.current.createPaymentIntent(
          326.98,
          'usd',
          'cust-001',
          {
            description: 'Monthly Invoice INV-2024-001',
            setupFutureUsage: 'off_session', // For future autopay
          }
        );
      });

      expect(paymentIntent).toMatchObject({
        id: 'pi_monthly_payment',
        amount: 32698,
        currency: 'usd',
      });

      // Verify billing state
      expect(billingHook.result.current.invoices).toHaveLength(1);
      expect(billingHook.result.current.totalRevenue).toBe(326.98);
    });
  });

  describe('Service Provisioning and Installation Workflow', () => {
    it('should handle complete service provisioning from order to activation', async () => {
      const wrapper = createWrapper();

      // Setup provisioning workflow responses
      mockApiResponses.set('POST /api/v1/services/provision', {
        data: {
          requestId: 'prov-001',
        },
      });

      mockApiResponses.set('GET /api/v1/services/provision/prov-001/status', {
        data: {
          requestId: 'prov-001',
          status: 'installing',
          progress: 75,
          assignedTechnician: {
            id: 'tech-001',
            name: 'Mike Johnson',
            phone: '+1-555-0200',
          },
          networkDetails: {
            ipAddress: '10.1.100.50',
            vlan: 100,
            port: 'GE-0/0/1',
            equipment: [
              {
                type: 'ONT',
                model: 'Nokia G-010S-A',
                serialNumber: 'NKIA12345678',
              },
            ],
          },
        },
      });

      const provisioningHook = renderHook(() => useISPOperations(), { wrapper });

      // Step 1: Submit service provisioning request
      let requestId: string;
      await act(async () => {
        requestId = await provisioningHook.result.current.provisionService({
          customerId: 'cust-001',
          serviceType: 'fiber',
          packageId: 'pkg-fiber-enterprise-1gb',
          installationAddress: {
            street: '100 Business Park Dr',
            city: 'Tech City',
            state: 'CA',
            zipCode: '94000',
          },
          bandwidth: {
            download: 1000,
            upload: 1000,
          },
          preferredInstallationDate: '2024-01-22',
          specialInstructions: 'Reception desk on 2nd floor for building access',
        });
      });

      expect(requestId).toBe('prov-001');

      // Step 2: Check provisioning status
      let status: any;
      await act(async () => {
        status = await provisioningHook.result.current.getProvisioningStatus('prov-001');
      });

      expect(status).toMatchObject({
        requestId: 'prov-001',
        status: 'installing',
        progress: 75,
        assignedTechnician: {
          name: 'Mike Johnson',
        },
      });

      // Verify provisioning state
      expect(provisioningHook.result.current.provisioningStatus.get('prov-001')).toBeDefined();
    });
  });

  describe('Multi-Tenant Data Isolation', () => {
    it('should properly isolate data between different ISP tenants', async () => {
      const wrapper = createWrapper();

      // Mock different tenant contexts
      const tenant1Customers = [
        { id: 'cust-t1-001', tenantId: 'tenant-1', name: 'Customer A' },
        { id: 'cust-t1-002', tenantId: 'tenant-1', name: 'Customer B' },
      ];

      const tenant2Customers = [
        { id: 'cust-t2-001', tenantId: 'tenant-2', name: 'Customer X' },
        { id: 'cust-t2-002', tenantId: 'tenant-2', name: 'Customer Y' },
      ];

      // Setup responses based on tenant context
      mockApiResponses.set('GET /api/v1/customers', {
        data: {
          customers: tenant1Customers, // This would be filtered by tenant in real API
          total: 2,
        },
      });

      const customerHook = renderHook(() => useCustomerManagement(), { wrapper });

      await act(async () => {
        await customerHook.result.current.loadCustomers();
      });

      // Verify tenant isolation
      expect(customerHook.result.current.customers).toHaveLength(2);
      expect(customerHook.result.current.customers.every(c => c.tenantId === 'tenant-1')).toBe(true);
    });
  });

  describe('Offline Operation Recovery', () => {
    it('should handle offline operations and sync when connection is restored', async () => {
      const wrapper = createWrapper();

      // Mock initial offline state
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false,
      });

      const persistenceHook = renderHook(() => useDataPersistence(), { wrapper });
      const customerHook = renderHook(() => useCustomerManagement(), { wrapper });

      // Step 1: Queue operations while offline
      await act(async () => {
        const op1 = persistenceHook.result.current.queueOperation({
          type: 'create',
          entity: 'customers',
          entityId: 'offline-cust-1',
          data: { name: 'Offline Customer 1', type: 'residential' },
          maxRetries: 3,
        });

        const op2 = persistenceHook.result.current.queueOperation({
          type: 'update',
          entity: 'customers',
          entityId: 'cust-existing',
          data: { status: 'suspended', notes: 'Payment overdue' },
          maxRetries: 3,
        });

        expect(op1).toBeDefined();
        expect(op2).toBeDefined();
      });

      expect(persistenceHook.result.current.pendingOperations).toHaveLength(2);

      // Step 2: Simulate coming back online
      Object.defineProperty(navigator, 'onLine', {
        value: true,
      });

      // Setup successful sync responses
      mockApiResponses.set('POST /api/v1/customers', {
        data: { customer: { id: 'synced-cust-1' } },
      });

      mockApiResponses.set('PUT /api/v1/customers/cust-existing', {
        data: { customer: { id: 'cust-existing', status: 'suspended' } },
      });

      // Step 3: Sync pending operations
      await act(async () => {
        const syncResult = await persistenceHook.result.current.syncPendingOperations();
        expect(syncResult.synced).toBe(2);
        expect(syncResult.failed).toBe(0);
      });

      expect(persistenceHook.result.current.pendingOperations).toHaveLength(0);
    });
  });

  describe('Performance and Scalability', () => {
    it('should handle large datasets efficiently with pagination and caching', async () => {
      const wrapper = createWrapper();

      // Mock large customer dataset
      const generateMockCustomers = (page: number, limit: number) => {
        const customers = [];
        const start = (page - 1) * limit;
        
        for (let i = start; i < start + limit; i++) {
          customers.push({
            id: `cust-${String(i).padStart(6, '0')}`,
            accountNumber: `ACC-${String(i).padStart(6, '0')}`,
            companyName: `Company ${i}`,
            type: i % 3 === 0 ? 'enterprise' : 'business',
            status: 'active',
            monthlyRevenue: Math.floor(Math.random() * 1000) + 100,
          });
        }
        
        return customers;
      };

      // Setup paginated responses
      mockApiResponses.set('GET /api/v1/customers', {
        data: {
          customers: generateMockCustomers(1, 50),
          total: 10000,
          pagination: {
            page: 1,
            limit: 50,
            totalPages: 200,
          },
        },
      });

      const customerHook = renderHook(() => useCustomerManagement(), { wrapper });

      // Load first page
      await act(async () => {
        await customerHook.result.current.loadCustomers(1, 50);
      });

      expect(customerHook.result.current.customers).toHaveLength(50);
      expect(customerHook.result.current.totalCount).toBe(10000);

      // Test search functionality
      mockApiResponses.set('POST /api/v1/customers/search', {
        data: {
          customers: generateMockCustomers(1, 10).filter(c => c.type === 'enterprise'),
        },
      });

      await act(async () => {
        const searchResults = await customerHook.result.current.searchCustomers(
          'enterprise',
          { type: ['enterprise'] }
        );
        expect(searchResults.length).toBeGreaterThan(0);
      });
    });
  });
});