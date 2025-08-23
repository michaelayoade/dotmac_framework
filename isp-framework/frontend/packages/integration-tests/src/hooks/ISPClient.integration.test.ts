/**
 * ISP Client and Hooks - Integration Tests
 * Tests the integration between useISPTenant, API clients, and data flow coordination
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createISPClient } from '../../headless/src/api/isp-client';
import { useISPTenant } from '../../headless/src/hooks/useISPTenant';
import { usePaymentProcessor } from '../../headless/src/hooks/usePaymentProcessor';
import type { ISPClient } from '../../headless/src/api/isp-client';
import type { Tenant, TenantSettings } from '../../headless/src/types/tenant';

// Mock API clients
jest.mock('../../headless/src/api/clients/IdentityApiClient');
jest.mock('../../headless/src/api/clients/BillingApiClient');
jest.mock('../../headless/src/api/clients/NetworkingApiClient');
jest.mock('../../headless/src/api/clients/AnalyticsApiClient');
jest.mock('../../headless/src/api/clients/ServicesApiClient');

// Mock data
const mockTenant: Tenant = {
  id: 'tenant_integration_test',
  name: 'Integration Test ISP',
  domain: 'test-isp.example.com',
  settings: {
    timezone: 'America/New_York',
    currency: 'USD',
    language: 'en',
    features: {
      billing: true,
      networking: true,
      analytics: true,
      support: true,
      fieldOps: true
    },
    integrations: {
      paymentGateways: ['stripe', 'paypal'],
      smsProviders: ['twilio'],
      emailProviders: ['sendgrid']
    },
    branding: {
      logo: 'https://cdn.test-isp.com/logo.png',
      primaryColor: '#1a365d',
      secondaryColor: '#2d3748'
    },
    billing: {
      taxEnabled: true,
      autoPayEnabled: true,
      reminderDays: [7, 3, 1],
      lateFeeEnabled: true,
      lateFeeAmount: 25.00
    },
    network: {
      monitoringEnabled: true,
      alertThresholds: {
        cpu: 80,
        memory: 85,
        bandwidth: 90
      },
      maintenanceWindows: [
        { day: 'sunday', start: '02:00', end: '04:00' }
      ]
    }
  },
  status: 'active',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-20T12:00:00Z'
};

const mockCustomers = [
  {
    id: 'cust_001',
    tenantId: 'tenant_integration_test',
    email: 'customer1@example.com',
    firstName: 'John',
    lastName: 'Doe',
    status: 'active',
    profile: {
      company: 'Acme Corp',
      phone: '+1-555-0123'
    },
    createdAt: '2024-01-01T00:00:00Z'
  },
  {
    id: 'cust_002',
    tenantId: 'tenant_integration_test',
    email: 'customer2@example.com',
    firstName: 'Jane',
    lastName: 'Smith',
    status: 'active',
    profile: {
      company: 'Tech Inc',
      phone: '+1-555-0456'
    },
    createdAt: '2024-01-05T00:00:00Z'
  }
];

// Test wrapper with providers
const createWrapper = (initialTenant?: Tenant) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  return { Wrapper, queryClient };
};

describe('ISP Client and Hooks Integration', () => {
  let ispClient: ISPClient;
  let mockFetch: jest.Mock;

  beforeEach(() => {
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Create ISP client
    ispClient = createISPClient({
      baseUrl: 'http://localhost:3001',
      apiKey: 'test-api-key',
      tenantId: 'tenant_integration_test'
    });

    // Setup default fetch responses
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/tenants/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTenant)
        });
      }
      if (url.includes('/customers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            customers: mockCustomers,
            total: mockCustomers.length
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('ISP Client Integration', () => {
    it('should initialize all API clients with tenant context', async () => {
      expect(ispClient).toBeDefined();
      expect(ispClient.identity).toBeDefined();
      expect(ispClient.billing).toBeDefined();
      expect(ispClient.networking).toBeDefined();
      expect(ispClient.analytics).toBeDefined();
      expect(ispClient.services).toBeDefined();
      expect(ispClient.support).toBeDefined();

      // Test API client coordination
      const customers = await ispClient.identity.getCustomers({
        page: 1,
        pageSize: 10
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tenants/tenant_integration_test/customers'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-api-key',
            'X-Tenant-ID': 'tenant_integration_test'
          })
        })
      );

      expect(customers).toEqual({
        customers: mockCustomers,
        total: mockCustomers.length
      });
    });

    it('should handle cross-service operations with shared context', async () => {
      // Setup billing response
      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/customers')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              customers: mockCustomers,
              total: mockCustomers.length
            })
          });
        }
        if (url.includes('/billing/customers/cust_001')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              customerId: 'cust_001',
              totalRevenue: 2400.00,
              monthlyRevenue: 200.00,
              status: 'current'
            })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      // Get customer and billing data
      const customers = await ispClient.identity.getCustomers({ page: 1, pageSize: 10 });
      const customerBilling = await ispClient.billing.getCustomerBilling('cust_001');

      // Verify both calls include tenant context
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tenants/tenant_integration_test/customers'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Tenant-ID': 'tenant_integration_test'
          })
        })
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tenants/tenant_integration_test/billing/customers/cust_001'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Tenant-ID': 'tenant_integration_test'
          })
        })
      );

      expect(customers.customers).toHaveLength(2);
      expect(customerBilling.customerId).toBe('cust_001');
    });

    it('should handle API errors gracefully across services', async () => {
      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/customers')) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () => Promise.resolve({ error: 'Internal server error' })
          });
        }
        if (url.includes('/billing')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      // Customer service should fail
      await expect(ispClient.identity.getCustomers({ page: 1, pageSize: 10 }))
        .rejects.toThrow('Internal server error');

      // Billing service should work
      const billingHealth = await ispClient.billing.getBillingAnalytics();
      expect(billingHealth).toEqual({ status: 'healthy' });
    });
  });

  describe('useISPTenant Hook Integration', () => {
    it('should provide tenant context to all components', async () => {
      const { Wrapper } = createWrapper();

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockTenant)
      });

      const { result } = renderHook(() => useISPTenant(), { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.currentTenant).toEqual(mockTenant);
      expect(result.current.error).toBeNull();

      // Verify tenant data structure
      expect(result.current.currentTenant?.settings.features.billing).toBe(true);
      expect(result.current.currentTenant?.settings.integrations.paymentGateways).toContain('stripe');
      expect(result.current.currentTenant?.settings.network.monitoringEnabled).toBe(true);
    });

    it('should handle tenant switching with context preservation', async () => {
      const { Wrapper } = createWrapper();

      const newTenant: Tenant = {
        ...mockTenant,
        id: 'tenant_switch_test',
        name: 'Switched ISP',
        domain: 'switched-isp.example.com'
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockTenant)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(newTenant)
        });

      const { result } = renderHook(() => useISPTenant(), { wrapper: Wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.currentTenant?.id).toBe('tenant_integration_test');
      });

      // Switch tenant
      act(() => {
        result.current.switchTenant('tenant_switch_test');
      });

      await waitFor(() => {
        expect(result.current.currentTenant?.id).toBe('tenant_switch_test');
        expect(result.current.currentTenant?.name).toBe('Switched ISP');
      });

      // Verify API calls made with correct tenant context
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tenants/tenant_integration_test'),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/tenants/tenant_switch_test'),
        expect.any(Object)
      );
    });

    it('should cache tenant settings and invalidate appropriately', async () => {
      const { Wrapper, queryClient } = createWrapper();

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockTenant)
      });

      const { result } = renderHook(() => useISPTenant(), { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.currentTenant).toBeDefined();
      });

      // Second hook instance should use cache
      const { result: result2 } = renderHook(() => useISPTenant(), { wrapper: Wrapper });

      expect(result2.current.currentTenant).toEqual(result.current.currentTenant);
      expect(mockFetch).toHaveBeenCalledTimes(1); // Only one API call due to caching

      // Force refresh should invalidate cache
      act(() => {
        result.current.refreshTenant();
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2); // Second API call after refresh
      });
    });
  });

  describe('Payment Processor Integration', () => {
    it('should integrate with tenant-specific payment configurations', async () => {
      const { Wrapper } = createWrapper();

      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/tenants/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenant)
          });
        }
        if (url.includes('/billing/payment-methods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              supportedMethods: ['credit_card', 'bank_account'],
              processors: {
                stripe: { enabled: true, publishableKey: 'pk_test_123' },
                paypal: { enabled: true, clientId: 'paypal_123' }
              }
            })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      const { result } = renderHook(() => {
        const tenant = useISPTenant();
        const paymentProcessor = usePaymentProcessor({
          tenantId: tenant.currentTenant?.id
        });
        return { tenant, paymentProcessor };
      }, { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.tenant.currentTenant).toBeDefined();
        expect(result.current.paymentProcessor.isLoading).toBe(false);
      });

      // Verify payment processor uses tenant configuration
      expect(result.current.paymentProcessor.supportedMethods).toContain('credit_card');
      expect(result.current.paymentProcessor.supportedMethods).toContain('bank_account');

      // Test payment processing
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          transactionId: 'txn_123',
          amount: 299.99
        })
      });

      let paymentResult;
      await act(async () => {
        paymentResult = await result.current.paymentProcessor.processPayment({
          amount: 299.99,
          currency: 'USD',
          paymentMethodId: 'pm_123',
          customerId: 'cust_001'
        });
      });

      expect(paymentResult).toEqual({
        success: true,
        transactionId: 'txn_123',
        amount: 299.99
      });
    });

    it('should handle payment processor failover', async () => {
      const { Wrapper } = createWrapper();

      // Setup tenant with multiple payment processors
      const tenantWithFailover = {
        ...mockTenant,
        settings: {
          ...mockTenant.settings,
          integrations: {
            ...mockTenant.settings.integrations,
            paymentGateways: ['stripe', 'paypal', 'square']
          }
        }
      };

      mockFetch.mockImplementation((url: string, options: any) => {
        if (url.includes('/tenants/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(tenantWithFailover)
          });
        }
        if (url.includes('/billing/process-payment')) {
          const body = JSON.parse(options.body);
          if (body.processor === 'stripe') {
            // Simulate Stripe failure
            return Promise.resolve({
              ok: false,
              status: 500,
              json: () => Promise.resolve({ error: 'Stripe service unavailable' })
            });
          }
          if (body.processor === 'paypal') {
            // PayPal succeeds
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve({
                success: true,
                transactionId: 'paypal_txn_123',
                amount: 299.99,
                processor: 'paypal'
              })
            });
          }
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      const { result } = renderHook(() => {
        const tenant = useISPTenant();
        const paymentProcessor = usePaymentProcessor({
          tenantId: tenant.currentTenant?.id,
          enableFailover: true
        });
        return { tenant, paymentProcessor };
      }, { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.tenant.currentTenant).toBeDefined();
      });

      // Process payment with failover
      let paymentResult;
      await act(async () => {
        paymentResult = await result.current.paymentProcessor.processPayment({
          amount: 299.99,
          currency: 'USD',
          paymentMethodId: 'pm_123',
          customerId: 'cust_001'
        });
      });

      expect(paymentResult).toEqual({
        success: true,
        transactionId: 'paypal_txn_123',
        amount: 299.99,
        processor: 'paypal'
      });
    });
  });

  describe('Real-world Integration Scenarios', () => {
    it('should coordinate customer onboarding across multiple services', async () => {
      const { Wrapper } = createWrapper();

      // Setup responses for complete customer onboarding flow
      mockFetch.mockImplementation((url: string, options: any) => {
        const method = options?.method || 'GET';
        
        if (url.includes('/tenants/') && method === 'GET') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenant)
          });
        }
        
        if (url.includes('/customers') && method === 'POST') {
          const body = JSON.parse(options.body);
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              id: 'cust_new_001',
              ...body,
              status: 'active',
              createdAt: new Date().toISOString()
            })
          });
        }
        
        if (url.includes('/billing/setup-autopay') && method === 'POST') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              autoPayId: 'autopay_123',
              enabled: true
            })
          });
        }
        
        if (url.includes('/services/provision') && method === 'POST') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              serviceId: 'service_fiber_001',
              status: 'provisioning',
              estimatedCompletion: '2024-01-25T12:00:00Z'
            })
          });
        }
        
        if (url.includes('/notifications/welcome') && method === 'POST') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              messageId: 'msg_welcome_001',
              sent: true
            })
          });
        }
        
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      const { result } = renderHook(() => {
        const tenant = useISPTenant();
        const paymentProcessor = usePaymentProcessor({
          tenantId: tenant.currentTenant?.id
        });
        return { tenant, paymentProcessor, ispClient };
      }, { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.tenant.currentTenant).toBeDefined();
      });

      // Simulate complete customer onboarding
      const newCustomerData = {
        email: 'newcustomer@example.com',
        firstName: 'New',
        lastName: 'Customer',
        profile: {
          company: 'New Company',
          phone: '+1-555-9999'
        }
      };

      // Step 1: Create customer
      const customer = await ispClient.identity.createCustomer(newCustomerData);
      expect(customer.id).toBe('cust_new_001');

      // Step 2: Setup payment method and autopay
      const paymentSetup = await result.current.paymentProcessor.setupPaymentMethod({
        customerId: customer.id,
        type: 'credit_card',
        details: { token: 'card_token_123' }
      });

      const autopaySetup = await ispClient.billing.setupAutoPay({
        customerId: customer.id,
        paymentMethodId: 'pm_new_001',
        enabled: true
      });

      expect(autopaySetup.autoPayId).toBe('autopay_123');

      // Step 3: Provision service
      const serviceProvisioning = await ispClient.services.provisionService({
        customerId: customer.id,
        serviceType: 'fiber',
        plan: 'residential_1gb'
      });

      expect(serviceProvisioning.serviceId).toBe('service_fiber_001');

      // Step 4: Send welcome notification
      const welcomeMessage = await ispClient.notifications.sendWelcomeEmail({
        customerId: customer.id,
        templateId: 'welcome_new_customer'
      });

      expect(welcomeMessage.messageId).toBe('msg_welcome_001');

      // Verify all services called with tenant context
      const fetchCalls = (global.fetch as jest.Mock).mock.calls;
      fetchCalls.forEach(([url, options]) => {
        if (options?.headers) {
          expect(options.headers['X-Tenant-ID']).toBe('tenant_integration_test');
        }
      });
    });

    it('should handle complex multi-service error recovery', async () => {
      const { Wrapper } = createWrapper();

      let callCount = 0;
      mockFetch.mockImplementation((url: string, options: any) => {
        callCount++;
        
        if (url.includes('/tenants/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenant)
          });
        }
        
        // Simulate intermittent failures
        if (url.includes('/billing/') && callCount < 3) {
          return Promise.resolve({
            ok: false,
            status: 503,
            json: () => Promise.resolve({ error: 'Service temporarily unavailable' })
          });
        }
        
        if (url.includes('/billing/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'success' })
          });
        }
        
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      const { result } = renderHook(() => {
        const tenant = useISPTenant();
        return { tenant, ispClient };
      }, { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.tenant.currentTenant).toBeDefined();
      });

      // First two billing calls should fail
      await expect(ispClient.billing.getBillingAnalytics())
        .rejects.toThrow('Service temporarily unavailable');

      await expect(ispClient.billing.getBillingAnalytics())
        .rejects.toThrow('Service temporarily unavailable');

      // Third call should succeed
      const billingResult = await ispClient.billing.getBillingAnalytics();
      expect(billingResult.status).toBe('success');
    });

    it('should maintain data consistency across concurrent operations', async () => {
      const { Wrapper } = createWrapper();

      mockFetch.mockImplementation((url: string, options: any) => {
        if (url.includes('/tenants/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockTenant)
          });
        }
        
        // Simulate different response times for concurrent operations
        const delay = url.includes('/customers') ? 100 : 
                     url.includes('/billing') ? 200 : 50;
        
        return new Promise(resolve => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: () => Promise.resolve({
                service: url.includes('/customers') ? 'identity' :
                        url.includes('/billing') ? 'billing' : 'other',
                timestamp: Date.now()
              })
            });
          }, delay);
        });
      });

      const { result } = renderHook(() => {
        const tenant = useISPTenant();
        return { tenant, ispClient };
      }, { wrapper: Wrapper });

      await waitFor(() => {
        expect(result.current.tenant.currentTenant).toBeDefined();
      });

      // Execute concurrent operations
      const promises = [
        ispClient.identity.getCustomers({ page: 1, pageSize: 10 }),
        ispClient.billing.getBillingAnalytics(),
        ispClient.services.getServices({ page: 1, pageSize: 10 }),
        ispClient.support.getTickets({ page: 1, pageSize: 10 }),
        ispClient.networking.getNetworkStatus('tenant_integration_test')
      ];

      const results = await Promise.all(promises);

      // Verify all operations completed successfully
      expect(results).toHaveLength(5);
      results.forEach(result => {
        expect(result.service).toBeDefined();
        expect(result.timestamp).toBeDefined();
      });

      // Verify tenant context maintained across all operations
      const fetchCalls = (global.fetch as jest.Mock).mock.calls;
      expect(fetchCalls).toHaveLength(6); // 1 tenant + 5 service calls
      
      fetchCalls.slice(1).forEach(([url, options]) => {
        expect(options.headers['X-Tenant-ID']).toBe('tenant_integration_test');
      });
    });
  });
});