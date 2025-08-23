/**
 * Billing Management - Component Integration Tests
 * Tests the integration between billing components, payment processing, and data synchronization
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BillingManagement } from '../../../apps/admin/src/components/billing/BillingManagement';
import { BillingApiClient } from '../../headless/src/api/clients/BillingApiClient';
import { IdentityApiClient } from '../../headless/src/api/clients/IdentityApiClient';
import { NotificationsApiClient } from '../../headless/src/api/clients/NotificationsApiClient';
import { AnalyticsApiClient } from '../../headless/src/api/clients/AnalyticsApiClient';
import { usePaymentProcessor } from '../../headless/src/hooks/usePaymentProcessor';
import type { Invoice, PaymentMethod, BillingAnalytics } from '../../headless/src/types/billing';

// Mock API clients and hooks
jest.mock('../../headless/src/api/clients/BillingApiClient');
jest.mock('../../headless/src/api/clients/IdentityApiClient');
jest.mock('../../headless/src/api/clients/NotificationsApiClient');
jest.mock('../../headless/src/api/clients/AnalyticsApiClient');
jest.mock('../../headless/src/hooks/usePaymentProcessor');

const MockedBillingApiClient = BillingApiClient as jest.MockedClass<typeof BillingApiClient>;
const MockedIdentityApiClient = IdentityApiClient as jest.MockedClass<typeof IdentityApiClient>;
const MockedNotificationsApiClient = NotificationsApiClient as jest.MockedClass<
  typeof NotificationsApiClient
>;
const MockedAnalyticsApiClient = AnalyticsApiClient as jest.MockedClass<typeof AnalyticsApiClient>;
const mockUsePaymentProcessor = usePaymentProcessor as jest.MockedFunction<
  typeof usePaymentProcessor
>;

// Mock data
const mockInvoices: Invoice[] = [
  {
    id: 'inv_001',
    customerId: 'cust_001',
    customerName: 'Acme Corp',
    customerEmail: 'billing@acme.com',
    amount: 299.99,
    tax: 24.0,
    total: 323.99,
    currency: 'USD',
    status: 'pending',
    dueDate: '2024-02-15T00:00:00Z',
    paidDate: null,
    paymentMethod: 'ACH',
    services: [{ name: 'Fiber Internet 1GB', amount: 299.99 }],
    billingPeriod: {
      start: '2024-01-01T00:00:00Z',
      end: '2024-01-31T23:59:59Z',
    },
    createdAt: '2024-01-25T00:00:00Z',
    updatedAt: '2024-01-25T00:00:00Z',
  },
  {
    id: 'inv_002',
    customerId: 'cust_002',
    customerName: 'TechStart Inc',
    customerEmail: 'finance@techstart.io',
    amount: 499.99,
    tax: 40.0,
    total: 539.99,
    currency: 'USD',
    status: 'overdue',
    dueDate: '2024-01-15T00:00:00Z',
    paidDate: null,
    paymentMethod: 'Credit Card',
    services: [
      { name: 'Fiber Internet 2GB', amount: 399.99 },
      { name: 'Static IP Address', amount: 100.0 },
    ],
    billingPeriod: {
      start: '2023-12-01T00:00:00Z',
      end: '2023-12-31T23:59:59Z',
    },
    createdAt: '2023-12-25T00:00:00Z',
    updatedAt: '2024-01-20T12:00:00Z',
  },
];

const mockPaymentMethods: PaymentMethod[] = [
  {
    id: 'pm_001',
    customerId: 'cust_001',
    type: 'bank_account',
    isDefault: true,
    details: {
      bankName: 'Chase Bank',
      accountType: 'checking',
      lastFour: '1234',
    },
    status: 'active',
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'pm_002',
    customerId: 'cust_002',
    type: 'credit_card',
    isDefault: true,
    details: {
      brand: 'visa',
      lastFour: '5678',
      expiryMonth: 12,
      expiryYear: 2025,
    },
    status: 'active',
    createdAt: '2024-01-01T00:00:00Z',
  },
];

const mockBillingAnalytics: BillingAnalytics = {
  totalRevenue: 125000.0,
  monthlyRevenue: 12500.0,
  unpaidAmount: 15000.0,
  overdueAmount: 5000.0,
  totalInvoices: 450,
  paidInvoices: 380,
  pendingInvoices: 45,
  overdueInvoices: 25,
  averagePaymentTime: 12.5,
  collectionRate: 94.5,
  revenueGrowth: 8.3,
  topCustomersByRevenue: [
    { customerId: 'cust_enterprise_1', customerName: 'Enterprise Corp', revenue: 5000.0 },
    { customerId: 'cust_enterprise_2', customerName: 'Global Tech', revenue: 4500.0 },
  ],
  paymentMethodDistribution: {
    ACH: 65,
    'Credit Card': 25,
    'Wire Transfer': 10,
  },
};

// Test wrapper with providers
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

describe('BillingManagement Integration Tests', () => {
  let billingClient: jest.Mocked<BillingApiClient>;
  let identityClient: jest.Mocked<IdentityApiClient>;
  let notificationsClient: jest.Mocked<NotificationsApiClient>;
  let analyticsClient: jest.Mocked<AnalyticsApiClient>;
  let mockPaymentProcessor: jest.Mocked<ReturnType<typeof usePaymentProcessor>>;

  beforeEach(() => {
    // Setup API client mocks
    billingClient = {
      getInvoices: jest.fn(),
      getInvoiceById: jest.fn(),
      createInvoice: jest.fn(),
      updateInvoice: jest.fn(),
      deleteInvoice: jest.fn(),
      processPayment: jest.fn(),
      getPaymentMethods: jest.fn(),
      createPaymentMethod: jest.fn(),
      deletePaymentMethod: jest.fn(),
      getBillingAnalytics: jest.fn(),
      generateReport: jest.fn(),
      exportInvoices: jest.fn(),
      sendInvoiceReminder: jest.fn(),
      processRefund: jest.fn(),
      applyCredit: jest.fn(),
      setupAutoPay: jest.fn(),
      calculateTax: jest.fn(),
    } as any;

    identityClient = {
      getCustomers: jest.fn(),
      getCustomerById: jest.fn(),
      searchCustomers: jest.fn(),
    } as any;

    notificationsClient = {
      sendNotification: jest.fn(),
      scheduleNotification: jest.fn(),
      getTemplates: jest.fn(),
      createTemplate: jest.fn(),
    } as any;

    analyticsClient = {
      trackEvent: jest.fn(),
      createReport: jest.fn(),
      getCustomReport: jest.fn(),
      scheduleReport: jest.fn(),
    } as any;

    mockPaymentProcessor = {
      processPayment: jest.fn(),
      processRefund: jest.fn(),
      setupPaymentMethod: jest.fn(),
      verifyPaymentMethod: jest.fn(),
      getPaymentStatus: jest.fn(),
      calculateFees: jest.fn(),
      supportedMethods: ['credit_card', 'bank_account', 'wire_transfer'],
      isLoading: false,
      error: null,
    };

    MockedBillingApiClient.mockImplementation(() => billingClient);
    MockedIdentityApiClient.mockImplementation(() => identityClient);
    MockedNotificationsApiClient.mockImplementation(() => notificationsClient);
    MockedAnalyticsApiClient.mockImplementation(() => analyticsClient);
    mockUsePaymentProcessor.mockReturnValue(mockPaymentProcessor);

    // Setup default mock responses
    billingClient.getInvoices.mockResolvedValue({
      invoices: mockInvoices,
      total: mockInvoices.length,
      page: 1,
      pageSize: 20,
    });

    billingClient.getBillingAnalytics.mockResolvedValue(mockBillingAnalytics);
    billingClient.getPaymentMethods.mockResolvedValue(mockPaymentMethods);

    identityClient.getCustomers.mockResolvedValue({
      customers: [],
      total: 0,
      page: 1,
      pageSize: 20,
    });

    notificationsClient.getTemplates.mockResolvedValue([
      {
        id: 'template_payment_reminder',
        name: 'Payment Reminder',
        type: 'invoice_reminder',
        subject: 'Payment Due: Invoice #{invoiceNumber}',
        body: 'Your payment of {amount} is due on {dueDate}.',
      },
    ]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Integration', () => {
    it('should render billing dashboard with integrated data from multiple APIs', async () => {
      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      // Wait for initial data load
      await waitFor(() => {
        expect(screen.getByText('Billing Management')).toBeInTheDocument();
      });

      // Verify multiple API clients called
      expect(billingClient.getInvoices).toHaveBeenCalled();
      expect(billingClient.getBillingAnalytics).toHaveBeenCalled();
      expect(billingClient.getPaymentMethods).toHaveBeenCalled();

      // Check analytics data rendering
      await waitFor(() => {
        expect(screen.getByText('$125,000.00')).toBeInTheDocument(); // Total revenue
        expect(screen.getByText('$12,500.00')).toBeInTheDocument(); // Monthly revenue
        expect(screen.getByText('$15,000.00')).toBeInTheDocument(); // Unpaid amount
      });

      // Check invoice data rendering
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
    });

    it('should handle payment processing with multiple service integration', async () => {
      const user = userEvent.setup();
      mockPaymentProcessor.processPayment.mockResolvedValue({
        success: true,
        transactionId: 'txn_12345',
        amount: 323.99,
        fee: 9.72,
      });

      billingClient.updateInvoice.mockResolvedValue({
        ...mockInvoices[0],
        status: 'paid',
        paidDate: new Date().toISOString(),
      });

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });

      // Process payment for pending invoice
      const processPaymentButton = screen.getByTestId('process-payment-inv_001');
      await user.click(processPaymentButton);

      // Confirm payment
      const confirmButton = screen.getByText('Process Payment');
      await user.click(confirmButton);

      await waitFor(() => {
        // Verify payment processor integration
        expect(mockPaymentProcessor.processPayment).toHaveBeenCalledWith({
          invoiceId: 'inv_001',
          amount: 323.99,
          paymentMethod: 'pm_001',
          customerId: 'cust_001',
        });

        // Verify invoice status update
        expect(billingClient.updateInvoice).toHaveBeenCalledWith('inv_001', {
          status: 'paid',
          paidDate: expect.any(String),
          paymentTransactionId: 'txn_12345',
        });

        // Verify notification sent
        expect(notificationsClient.sendNotification).toHaveBeenCalledWith({
          customerId: 'cust_001',
          type: 'payment_confirmation',
          message: expect.stringContaining('Payment processed successfully'),
          channels: ['email'],
        });

        // Verify analytics tracking
        expect(analyticsClient.trackEvent).toHaveBeenCalledWith({
          event: 'payment_processed',
          properties: {
            invoiceId: 'inv_001',
            amount: 323.99,
            paymentMethod: 'ACH',
            processingFee: 9.72,
          },
        });
      });
    });

    it('should coordinate invoice creation with customer data and tax calculation', async () => {
      const user = userEvent.setup();
      const mockCustomer = {
        id: 'cust_003',
        name: 'New Customer Corp',
        email: 'billing@newcustomer.com',
        profile: {
          address: '789 Corporate Blvd',
          city: 'San Francisco',
          state: 'CA',
          zipCode: '94105',
        },
      };

      identityClient.getCustomerById.mockResolvedValue(mockCustomer);
      billingClient.calculateTax.mockResolvedValue({
        taxAmount: 35.0,
        taxRate: 8.75,
        taxJurisdiction: 'CA',
      });

      billingClient.createInvoice.mockResolvedValue({
        id: 'inv_003',
        customerId: 'cust_003',
        customerName: 'New Customer Corp',
        amount: 399.99,
        tax: 35.0,
        total: 434.99,
        status: 'pending',
      });

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Billing Management')).toBeInTheDocument();
      });

      // Create new invoice
      const createInvoiceButton = screen.getByText('Create Invoice');
      await user.click(createInvoiceButton);

      // Fill in customer
      const customerSelect = screen.getByTestId('customer-select');
      await user.selectOptions(customerSelect, 'cust_003');

      // Add service line items
      const addServiceButton = screen.getByText('Add Service');
      await user.click(addServiceButton);

      const serviceSelect = screen.getByTestId('service-select');
      await user.selectOptions(serviceSelect, 'fiber_2gb');

      const amountInput = screen.getByTestId('service-amount');
      await user.clear(amountInput);
      await user.type(amountInput, '399.99');

      // Submit invoice creation
      const createButton = screen.getByText('Create Invoice');
      await user.click(createButton);

      await waitFor(() => {
        // Verify customer lookup
        expect(identityClient.getCustomerById).toHaveBeenCalledWith('cust_003');

        // Verify tax calculation
        expect(billingClient.calculateTax).toHaveBeenCalledWith({
          amount: 399.99,
          customerId: 'cust_003',
          address: {
            city: 'San Francisco',
            state: 'CA',
            zipCode: '94105',
          },
        });

        // Verify invoice creation
        expect(billingClient.createInvoice).toHaveBeenCalledWith({
          customerId: 'cust_003',
          amount: 399.99,
          tax: 35.0,
          total: 434.99,
          services: [{ name: 'Fiber Internet 2GB', amount: 399.99 }],
          billingPeriod: expect.any(Object),
        });
      });
    });
  });

  describe('Payment Flow Integration', () => {
    it('should handle failed payments with retry logic and notifications', async () => {
      const user = userEvent.setup();
      mockPaymentProcessor.processPayment
        .mockRejectedValueOnce(new Error('Payment declined'))
        .mockResolvedValueOnce({
          success: true,
          transactionId: 'txn_retry_123',
          amount: 323.99,
        });

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });

      // Attempt payment
      const processPaymentButton = screen.getByTestId('process-payment-inv_001');
      await user.click(processPaymentButton);

      const confirmButton = screen.getByText('Process Payment');
      await user.click(confirmButton);

      // Wait for failure
      await waitFor(() => {
        expect(screen.getByText(/payment declined/i)).toBeInTheDocument();
      });

      // Verify failure notification
      expect(notificationsClient.sendNotification).toHaveBeenCalledWith({
        customerId: 'cust_001',
        type: 'payment_failed',
        message: 'Payment processing failed: Payment declined',
        channels: ['email', 'internal'],
      });

      // Retry payment
      const retryButton = screen.getByText('Retry Payment');
      await user.click(retryButton);

      await waitFor(() => {
        expect(mockPaymentProcessor.processPayment).toHaveBeenCalledTimes(2);
        expect(screen.getByText(/payment processed successfully/i)).toBeInTheDocument();
      });
    });

    it('should handle autopay setup with payment method verification', async () => {
      const user = userEvent.setup();
      mockPaymentProcessor.verifyPaymentMethod.mockResolvedValue({
        verified: true,
        verificationId: 'verify_123',
      });

      billingClient.setupAutoPay.mockResolvedValue({
        success: true,
        autoPayId: 'autopay_123',
      });

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });

      // Setup autopay for customer
      const customerRow = screen.getByTestId('customer-row-cust_001');
      await user.click(customerRow);

      const setupAutoPayButton = screen.getByText('Setup AutoPay');
      await user.click(setupAutoPayButton);

      // Select payment method
      const paymentMethodSelect = screen.getByTestId('autopay-payment-method');
      await user.selectOptions(paymentMethodSelect, 'pm_001');

      // Set billing cycle
      const billingCycleSelect = screen.getByTestId('autopay-billing-cycle');
      await user.selectOptions(billingCycleSelect, 'monthly');

      // Enable autopay
      const enableButton = screen.getByText('Enable AutoPay');
      await user.click(enableButton);

      await waitFor(() => {
        // Verify payment method verification
        expect(mockPaymentProcessor.verifyPaymentMethod).toHaveBeenCalledWith('pm_001');

        // Verify autopay setup
        expect(billingClient.setupAutoPay).toHaveBeenCalledWith({
          customerId: 'cust_001',
          paymentMethodId: 'pm_001',
          billingCycle: 'monthly',
          enabled: true,
        });

        // Verify confirmation notification
        expect(notificationsClient.sendNotification).toHaveBeenCalledWith({
          customerId: 'cust_001',
          type: 'autopay_enabled',
          message: 'AutoPay has been successfully enabled for your account',
          channels: ['email'],
        });
      });
    });
  });

  describe('Analytics and Reporting Integration', () => {
    it('should generate comprehensive billing reports with analytics integration', async () => {
      const user = userEvent.setup();
      const mockReport = {
        id: 'report_billing_monthly',
        type: 'billing_summary',
        period: { start: '2024-01-01', end: '2024-01-31' },
        data: {
          totalRevenue: 12500.0,
          totalInvoices: 45,
          collectionRate: 94.5,
          averagePaymentTime: 12.5,
        },
        generatedAt: '2024-02-01T00:00:00Z',
      };

      billingClient.generateReport.mockResolvedValue(mockReport);
      analyticsClient.createReport.mockResolvedValue({
        reportId: 'analytics_billing_001',
        status: 'completed',
      });

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Billing Management')).toBeInTheDocument();
      });

      // Generate monthly report
      const reportsTab = screen.getByText('Reports');
      await user.click(reportsTab);

      const generateReportButton = screen.getByText('Generate Report');
      await user.click(generateReportButton);

      // Configure report
      const reportTypeSelect = screen.getByTestId('report-type-select');
      await user.selectOptions(reportTypeSelect, 'billing_summary');

      const startDateInput = screen.getByTestId('report-start-date');
      await user.type(startDateInput, '2024-01-01');

      const endDateInput = screen.getByTestId('report-end-date');
      await user.type(endDateInput, '2024-01-31');

      const generateButton = screen.getByText('Generate');
      await user.click(generateButton);

      await waitFor(() => {
        // Verify billing report generation
        expect(billingClient.generateReport).toHaveBeenCalledWith({
          type: 'billing_summary',
          period: { start: '2024-01-01', end: '2024-01-31' },
          includeAnalytics: true,
        });

        // Verify analytics integration
        expect(analyticsClient.createReport).toHaveBeenCalledWith({
          type: 'billing_analytics',
          period: { start: '2024-01-01', end: '2024-01-31' },
          metrics: ['revenue_growth', 'collection_rate', 'payment_trends'],
        });

        // Verify report data displayed
        expect(screen.getByText('$12,500.00')).toBeInTheDocument();
        expect(screen.getByText('94.5%')).toBeInTheDocument();
      });
    });

    it('should handle real-time analytics updates during payment processing', async () => {
      const user = userEvent.setup();

      // Setup real-time analytics mock
      const mockAnalyticsUpdate = {
        totalRevenue: 125323.99, // Updated after payment
        monthlyRevenue: 12823.99,
        unpaidAmount: 14676.01,
        collectionRate: 94.7,
      };

      mockPaymentProcessor.processPayment.mockResolvedValue({
        success: true,
        transactionId: 'txn_realtime',
        amount: 323.99,
      });

      billingClient.getBillingAnalytics
        .mockResolvedValueOnce(mockBillingAnalytics)
        .mockResolvedValueOnce(mockAnalyticsUpdate);

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      // Initial analytics load
      await waitFor(() => {
        expect(screen.getByText('$125,000.00')).toBeInTheDocument();
      });

      // Process payment
      const processPaymentButton = screen.getByTestId('process-payment-inv_001');
      await user.click(processPaymentButton);

      const confirmButton = screen.getByText('Process Payment');
      await user.click(confirmButton);

      // Verify analytics refresh after payment
      await waitFor(() => {
        expect(billingClient.getBillingAnalytics).toHaveBeenCalledTimes(2);
        expect(screen.getByText('$125,323.99')).toBeInTheDocument(); // Updated revenue
        expect(screen.getByText('94.7%')).toBeInTheDocument(); // Updated collection rate
      });
    });
  });

  describe('Error Handling and Resilience', () => {
    it('should handle partial service failures gracefully', async () => {
      // Simulate partial service failures
      billingClient.getInvoices.mockResolvedValue({
        invoices: mockInvoices,
        total: mockInvoices.length,
        page: 1,
        pageSize: 20,
      });

      billingClient.getBillingAnalytics.mockRejectedValue(
        new Error('Analytics service unavailable')
      );
      notificationsClient.sendNotification.mockRejectedValue(
        new Error('Notification service down')
      );

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      // Core billing functionality should work
      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
        expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
      });

      // Analytics section should show error state
      expect(screen.getByText(/analytics temporarily unavailable/i)).toBeInTheDocument();

      // Notifications should fail silently with fallback
      const user = userEvent.setup();
      const processPaymentButton = screen.getByTestId('process-payment-inv_001');
      await user.click(processPaymentButton);

      await waitFor(() => {
        // Payment processing should continue despite notification failure
        expect(screen.getByText(/payment initiated/i)).toBeInTheDocument();
      });
    });

    it('should implement circuit breaker pattern for external services', async () => {
      const user = userEvent.setup();

      // Simulate repeated payment processor failures
      mockPaymentProcessor.processPayment.mockRejectedValue(new Error('Service unavailable'));

      render(
        <TestWrapper>
          <BillingManagement />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });

      // Attempt multiple payments to trigger circuit breaker
      for (let i = 0; i < 3; i++) {
        const processPaymentButton = screen.getByTestId('process-payment-inv_001');
        await user.click(processPaymentButton);

        const confirmButton = screen.getByText('Process Payment');
        await user.click(confirmButton);

        await waitFor(() => {
          expect(screen.getByText(/payment processing failed/i)).toBeInTheDocument();
        });
      }

      // Circuit breaker should activate
      await waitFor(() => {
        expect(screen.getByText(/payment service temporarily unavailable/i)).toBeInTheDocument();
      });
    });
  });
});
