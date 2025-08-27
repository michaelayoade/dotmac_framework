import { rest } from 'msw';
import { setupServer } from 'msw/node';

// Mock data generators
export const mockCustomer = (overrides = {}) => ({
  id: `customer_${Math.random().toString(36).substr(2, 9)}`,
  name: 'John Doe',
  email: 'john.doe@example.com',
  phone: '+1-555-0123',
  address: {
    street: '123 Main St',
    city: 'Anytown',
    state: 'NY',
    zip: '12345',
  },
  status: 'active',
  services: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  ...overrides,
});

export const mockInvoice = (overrides = {}) => ({
  id: `invoice_${Math.random().toString(36).substr(2, 9)}`,
  invoiceNumber: `INV-${Math.floor(Math.random() * 10000)}`,
  customerId: 'customer_123',
  status: 'sent',
  issueDate: new Date().toISOString(),
  dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  totalAmount: 99.99,
  amountDue: 99.99,
  amountPaid: 0,
  lineItems: [
    {
      id: 'line_1',
      description: 'Internet Service - Monthly',
      quantity: 1,
      unitPrice: 99.99,
      amount: 99.99,
    },
  ],
  ...overrides,
});

export const mockPayment = (overrides = {}) => ({
  id: `payment_${Math.random().toString(36).substr(2, 9)}`,
  invoiceId: 'invoice_123',
  customerId: 'customer_123',
  amount: 99.99,
  status: 'completed',
  method: {
    id: 'pm_123',
    type: 'credit_card',
    lastFour: '4242',
    brand: 'visa',
    isDefault: true,
  },
  processedAt: new Date().toISOString(),
  ...overrides,
});

export const mockProvisioningRequest = (overrides = {}) => ({
  id: `req_${Math.random().toString(36).substr(2, 9)}`,
  customerId: 'customer_123',
  serviceTemplateId: 'template_fiber_100',
  status: 'pending',
  priority: 'medium',
  requestedAt: new Date().toISOString(),
  installationAddress: {
    street: '123 Main St',
    city: 'Anytown',
    state: 'NY',
    zip: '12345',
  },
  customerInfo: {
    name: 'John Doe',
    email: 'john.doe@example.com',
    phone: '+1-555-0123',
  },
  tasks: [],
  equipment: [],
  ...overrides,
});

export const mockCommissionData = (overrides = {}) => ({
  id: `comm_${Math.random().toString(36).substr(2, 9)}`,
  resellerId: 'reseller_123',
  customerId: 'customer_123',
  serviceId: 'service_123',
  type: 'recurring',
  amount: 15.00,
  rate: 0.15,
  baseAmount: 100.00,
  status: 'earned',
  period: {
    start: new Date().toISOString(),
    end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  },
  ...overrides,
});

export const mockNotification = (overrides = {}) => ({
  id: `notif_${Math.random().toString(36).substr(2, 9)}`,
  type: 'info',
  priority: 'medium',
  title: 'Test Notification',
  message: 'This is a test notification',
  channel: ['browser'],
  timestamp: new Date(),
  read: false,
  persistent: false,
  ...overrides,
});

// API Mock Handlers
export const handlers = [
  // Analytics API
  rest.get('/api/analytics/metrics', (req, res, ctx) => {
    return res(
      ctx.json({
        metrics: {
          totalCustomers: 1250,
          activeServices: 2100,
          monthlyRevenue: 125000,
          conversionRate: 0.23,
          customerSatisfaction: 4.6,
          churnRate: 0.05,
        },
        trends: {
          customers: [1200, 1220, 1235, 1250],
          revenue: [120000, 122000, 123500, 125000],
        },
      })
    );
  }),

  // Billing API
  rest.get('/api/billing/invoices', (req, res, ctx) => {
    const invoices = Array.from({ length: 10 }, () => mockInvoice());
    return res(ctx.json({ invoices }));
  }),

  rest.post('/api/billing/invoices', (req, res, ctx) => {
    return res(ctx.json({ invoice: mockInvoice() }));
  }),

  rest.get('/api/billing/payments', (req, res, ctx) => {
    const payments = Array.from({ length: 5 }, () => mockPayment());
    return res(ctx.json({ payments }));
  }),

  rest.post('/api/billing/payments', (req, res, ctx) => {
    return res(ctx.json({ payment: mockPayment({ status: 'completed' }) }));
  }),

  // Provisioning API
  rest.get('/api/provisioning/requests', (req, res, ctx) => {
    const requests = Array.from({ length: 8 }, () => mockProvisioningRequest());
    return res(ctx.json({ requests }));
  }),

  rest.post('/api/provisioning/requests', (req, res, ctx) => {
    return res(ctx.json({ request: mockProvisioningRequest() }));
  }),

  // Commission API
  rest.get('/api/commissions', (req, res, ctx) => {
    const commissions = Array.from({ length: 15 }, () => mockCommissionData());
    const stats = {
      totalEarned: 2350.50,
      monthlyEarned: 450.75,
      totalCustomers: 125,
      avgCommissionPerCustomer: 18.80,
      projectedAnnual: 5400.00,
    };
    return res(ctx.json({ commissions, stats }));
  }),

  // Communication API
  rest.get('/api/communication/messages', (req, res, ctx) => {
    const messages = Array.from({ length: 10 }, (_, i) => ({
      id: `msg_${i}`,
      recipient: `customer${i}@example.com`,
      subject: `Message ${i + 1}`,
      status: ['sent', 'delivered', 'failed'][i % 3],
      sentAt: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
    }));
    return res(ctx.json({ messages }));
  }),

  rest.post('/api/communication/messages', (req, res, ctx) => {
    return res(
      ctx.json({
        message: {
          id: 'msg_new',
          status: 'sent',
          sentAt: new Date().toISOString(),
        },
      })
    );
  }),

  // Territory API
  rest.get('/api/territory/data', (req, res, ctx) => {
    return res(
      ctx.json({
        territories: [
          {
            id: 'territory_1',
            name: 'Downtown Area',
            coordinates: [
              [-74.0059, 40.7128],
              [-74.0059, 40.7228],
              [-73.9959, 40.7228],
              [-73.9959, 40.7128],
            ],
            customers: 45,
            prospects: 12,
            coverage: 'fiber',
          },
        ],
        customers: Array.from({ length: 20 }, (_, i) => ({
          id: `customer_${i}`,
          name: `Customer ${i + 1}`,
          location: {
            lat: 40.7128 + (Math.random() - 0.5) * 0.1,
            lng: -74.0059 + (Math.random() - 0.5) * 0.1,
          },
          status: ['active', 'inactive', 'prospect'][i % 3],
        })),
      })
    );
  }),

  // Error simulation handlers
  rest.get('/api/error/500', (req, res, ctx) => {
    return res(ctx.status(500), ctx.json({ message: 'Internal Server Error' }));
  }),

  rest.get('/api/error/404', (req, res, ctx) => {
    return res(ctx.status(404), ctx.json({ message: 'Not Found' }));
  }),

  rest.get('/api/error/timeout', (req, res, ctx) => {
    return res(ctx.delay('infinite'));
  }),
];

// Test server setup
export const server = setupServer(...handlers);

// Helper functions for testing
export const createMockWebSocket = () => {
  const mockWS = {
    send: jest.fn(),
    close: jest.fn(),
    readyState: WebSocket.OPEN,
    onopen: null as ((event: Event) => void) | null,
    onmessage: null as ((event: MessageEvent) => void) | null,
    onclose: null as ((event: CloseEvent) => void) | null,
    onerror: null as ((event: Event) => void) | null,
  };

  // Simulate WebSocket events
  const simulateOpen = () => {
    if (mockWS.onopen) {
      mockWS.onopen(new Event('open'));
    }
  };

  const simulateMessage = (data: any) => {
    if (mockWS.onmessage) {
      mockWS.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  };

  const simulateClose = () => {
    mockWS.readyState = WebSocket.CLOSED;
    if (mockWS.onclose) {
      mockWS.onclose(new CloseEvent('close'));
    }
  };

  const simulateError = () => {
    if (mockWS.onerror) {
      mockWS.onerror(new Event('error'));
    }
  };

  return {
    mockWS,
    simulateOpen,
    simulateMessage,
    simulateClose,
    simulateError,
  };
};

// Performance testing utilities
export const measurePerformance = async (fn: () => Promise<void> | void, label: string) => {
  const start = performance.now();
  await fn();
  const end = performance.now();
  const duration = end - start;
  
  console.log(`${label}: ${duration.toFixed(2)}ms`);
  
  return duration;
};

export const expectPerformance = (duration: number, threshold: number, label: string) => {
  if (duration > threshold) {
    console.warn(`Performance warning: ${label} took ${duration.toFixed(2)}ms (threshold: ${threshold}ms)`);
  }
  expect(duration).toBeLessThan(threshold);
};

// Memory leak detection
export const detectMemoryLeaks = () => {
  const initialMemory = (performance as any).memory?.usedJSHeapSize || 0;
  
  return {
    check: () => {
      const currentMemory = (performance as any).memory?.usedJSHeapSize || 0;
      const diff = currentMemory - initialMemory;
      const threshold = 10 * 1024 * 1024; // 10MB threshold
      
      if (diff > threshold) {
        console.warn(`Potential memory leak detected: ${(diff / 1024 / 1024).toFixed(2)}MB increase`);
      }
      
      return diff;
    },
  };
};