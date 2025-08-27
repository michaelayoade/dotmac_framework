import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BillingManagement } from '../BillingManagement';
import { 
  renderWithProviders, 
  expectLoadingState,
  expectDataToLoad,
  expectModalToBeOpen,
  expectModalToBeClosed,
  expectSuccessNotification,
  expectErrorNotification,
  fillForm,
  submitForm,
  expectTableToHaveRows,
  mockWebSocketMessage,
  simulateAPIError,
} from '@dotmac/testing';
import { server, handlers, mockInvoice, mockPayment } from '@dotmac/testing';

// Mock the billing hook
const mockBillingData = {
  invoices: [
    mockInvoice({ id: 'inv_1', status: 'sent', totalAmount: 99.99 }),
    mockInvoice({ id: 'inv_2', status: 'paid', totalAmount: 149.99 }),
    mockInvoice({ id: 'inv_3', status: 'overdue', totalAmount: 79.99 }),
  ],
  payments: [
    mockPayment({ id: 'pay_1', status: 'completed', amount: 99.99 }),
    mockPayment({ id: 'pay_2', status: 'failed', amount: 149.99 }),
  ],
  accounts: [
    {
      id: 'acc_1',
      accountNumber: 'ACC-001',
      customerId: 'customer_1',
      status: 'active',
      balance: 50.00,
      billingCycle: 'monthly',
      nextBillDate: new Date(),
      billingAddress: {
        street: '123 Main St',
        city: 'Anytown',
        state: 'NY',
        zip: '12345',
        country: 'US',
      },
    },
  ],
  stats: {
    totalRevenue: 5000,
    monthlyRecurringRevenue: 2500,
    overdueInvoices: 1,
    collectionRate: 95.5,
    averageRevenuePerUser: 125,
    churnRate: 2.5,
    totalInvoices: 150,
    paidInvoices: 140,
    totalOutstanding: 500,
    paymentMethodBreakdown: {
      credit_card: 85,
      bank_account: 15,
    },
    revenueByPlan: {
      'Basic': 1000,
      'Premium': 2500,
      'Enterprise': 1500,
    },
    recentPayments: [],
    upcomingRenewals: [],
  },
  overdueInvoices: [mockInvoice({ status: 'overdue' })],
  failedPayments: [mockPayment({ status: 'failed' })],
  recentPayments: [mockPayment({ status: 'completed' })],
  totalOutstanding: 500,
  isLoading: false,
  isConnected: true,
  paymentProcessing: false,
  error: null,
  // Actions
  processPayment: jest.fn(),
  createInvoice: jest.fn(),
  updateInvoiceStatus: jest.fn(),
  sendInvoice: jest.fn(),
  refundPayment: jest.fn(),
  retryPayment: jest.fn(),
  loadInvoices: jest.fn(),
  loadPayments: jest.fn(),
  selectAccount: jest.fn(),
};

jest.mock('@dotmac/headless', () => ({
  ...jest.requireActual('@dotmac/headless'),
  useBilling: jest.fn(() => mockBillingData),
}));

describe('BillingManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  describe('Overview Tab', () => {
    it('renders billing overview with correct stats', async () => {
      renderWithProviders(<BillingManagement />);

      // Check that overview tab is active by default
      expect(screen.getByText('Overview')).toHaveAttribute('aria-selected', 'true');

      // Check revenue stats
      await waitFor(() => {
        expect(screen.getByText('$5,000')).toBeInTheDocument();
        expect(screen.getByText('MRR: $2,500')).toBeInTheDocument();
      });

      // Check outstanding amount
      expect(screen.getByText('$500')).toBeInTheDocument();
      expect(screen.getByText('1 overdue invoices')).toBeInTheDocument();

      // Check collection rate
      expect(screen.getByText('95.5%')).toBeInTheDocument();
      expect(screen.getByText('140/150 paid')).toBeInTheDocument();

      // Check ARPU
      expect(screen.getByText('$125')).toBeInTheDocument();
      expect(screen.getByText('Churn: 2.5%')).toBeInTheDocument();
    });

    it('displays payment method breakdown', async () => {
      renderWithProviders(<BillingManagement />);

      await waitFor(() => {
        expect(screen.getByText('Payment Methods')).toBeInTheDocument();
        expect(screen.getByText('85')).toBeInTheDocument(); // Credit card count
        expect(screen.getByText('15')).toBeInTheDocument(); // Bank account count
      });
    });

    it('shows overdue invoices section', async () => {
      renderWithProviders(<BillingManagement />);

      await waitFor(() => {
        expect(screen.getByText('Overdue Invoices (1)')).toBeInTheDocument();
      });

      const collectButton = screen.getByText('Collect');
      expect(collectButton).toBeInTheDocument();
    });
  });

  describe('Invoices Tab', () => {
    it('displays invoices table with data', async () => {
      const { user } = renderWithProviders(<BillingManagement />);

      // Switch to invoices tab
      await user.click(screen.getByText(/Invoices/));

      await waitFor(() => {
        expectTableToHaveRows(3); // 3 mock invoices
      });

      // Check invoice data
      expect(screen.getByText('$99.99')).toBeInTheDocument();
      expect(screen.getByText('$149.99')).toBeInTheDocument();
      expect(screen.getByText('$79.99')).toBeInTheDocument();
    });

    it('allows filtering invoices by status', async () => {
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText(/Invoices/));

      // Open status filter
      const statusFilter = screen.getByRole('combobox', { name: /status/i });
      await user.selectOptions(statusFilter, 'paid');

      await waitFor(() => {
        expect(mockBillingData.loadInvoices).toHaveBeenCalledWith(
          expect.objectContaining({ status: 'paid' })
        );
      });
    });

    it('handles bulk invoice operations', async () => {
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText(/Invoices/));

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes).toHaveLength(4); // 3 invoices + select all
      });

      // Select first invoice
      const firstCheckbox = screen.getAllByRole('checkbox')[1];
      await user.click(firstCheckbox);

      // Check that bulk send button appears
      await waitFor(() => {
        expect(screen.getByText(/Send 1 Invoices/)).toBeInTheDocument();
      });

      // Click bulk send
      await user.click(screen.getByText(/Send 1 Invoices/));

      expect(mockBillingData.sendInvoice).toHaveBeenCalled();
    });

    it('opens new invoice modal', async () => {
      const { user } = renderWithProviders(<BillingManagement />);

      const createButton = screen.getByText('Create Invoice');
      await user.click(createButton);

      expectModalToBeOpen(/New Invoice/);
    });
  });

  describe('Invoice Creation', () => {
    it('creates new invoice successfully', async () => {
      mockBillingData.createInvoice.mockResolvedValueOnce(mockInvoice());
      const { user } = renderWithProviders(<BillingManagement />);

      // Open modal
      await user.click(screen.getByText('Create Invoice'));
      expectModalToBeOpen(/New Invoice/);

      // Fill form
      await fillForm({
        'Customer ID': 'customer_123',
        'Due Date': '2024-02-01',
        'Description': 'Monthly Service Fee',
        'Qty': '1',
        'Price': '99.99',
      });

      // Submit form
      await submitForm(/Create Invoice/);

      await waitFor(() => {
        expect(mockBillingData.createInvoice).toHaveBeenCalledWith(
          expect.objectContaining({
            customerId: 'customer_123',
            lineItems: expect.arrayContaining([
              expect.objectContaining({
                description: 'Monthly Service Fee',
                quantity: 1,
                unitPrice: 99.99,
              }),
            ]),
          })
        );
      });

      expectModalToBeClosed();
      await expectSuccessNotification(/Invoice.*created/);
    });

    it('handles invoice creation errors', async () => {
      mockBillingData.createInvoice.mockRejectedValueOnce(new Error('Validation failed'));
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText('Create Invoice'));
      await fillForm({
        'Customer ID': 'invalid',
        'Due Date': '2024-02-01',
      });
      await submitForm(/Create Invoice/);

      await expectErrorNotification(/failed to create/i);
    });
  });

  describe('Payment Processing', () => {
    it('processes payment successfully', async () => {
      mockBillingData.processPayment.mockResolvedValueOnce(
        mockPayment({ status: 'completed' })
      );
      const { user } = renderWithProviders(<BillingManagement />);

      // Go to invoices tab and click collect on an invoice
      await user.click(screen.getByText(/Invoices/));
      
      await waitFor(() => {
        const collectButton = screen.getByText('Collect');
        expect(collectButton).toBeInTheDocument();
      });

      await user.click(screen.getByText('Collect'));

      // Payment modal should open
      expectModalToBeOpen(/Process Payment/);

      // Submit payment
      await submitForm(/Process Payment/);

      await waitFor(() => {
        expect(mockBillingData.processPayment).toHaveBeenCalled();
      });

      await expectSuccessNotification(/Payment.*processed/);
    });

    it('handles payment failures', async () => {
      mockBillingData.processPayment.mockRejectedValueOnce(
        new Error('Payment declined')
      );
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText(/Invoices/));
      
      await waitFor(() => {
        const collectButton = screen.getByText('Collect');
        expect(collectButton).toBeInTheDocument();
      });

      await user.click(screen.getByText('Collect'));
      await submitForm(/Process Payment/);

      await expectErrorNotification(/Payment declined/);
    });
  });

  describe('Payments Tab', () => {
    it('displays payments with correct status indicators', async () => {
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText(/Payments/));

      await waitFor(() => {
        expect(screen.getByText(/completed/)).toBeInTheDocument();
        expect(screen.getByText(/failed/)).toBeInTheDocument();
      });
    });

    it('handles payment retries', async () => {
      mockBillingData.retryPayment.mockResolvedValueOnce(
        mockPayment({ status: 'pending' })
      );
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText(/Payments/));

      await waitFor(() => {
        const retryButton = screen.getByText('Retry');
        expect(retryButton).toBeInTheDocument();
      });

      await user.click(screen.getByText('Retry'));

      expect(mockBillingData.retryPayment).toHaveBeenCalled();
    });

    it('handles payment refunds', async () => {
      mockBillingData.refundPayment.mockResolvedValueOnce(
        mockPayment({ status: 'refunded' })
      );
      
      // Mock window.prompt
      const mockPrompt = jest.spyOn(window, 'prompt').mockReturnValue('Customer request');
      
      const { user } = renderWithProviders(<BillingManagement />);

      await user.click(screen.getByText(/Payments/));

      // Wait for refund button (only appears for completed payments)
      await waitFor(() => {
        const refundButton = screen.getByText('Refund');
        expect(refundButton).toBeInTheDocument();
      });

      await user.click(screen.getByText('Refund'));

      expect(mockPrompt).toHaveBeenCalledWith('Refund reason:');
      expect(mockBillingData.refundPayment).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Number),
        'Customer request'
      );

      mockPrompt.mockRestore();
    });
  });

  describe('Real-time Updates', () => {
    it('handles WebSocket payment completion updates', async () => {
      const mockWebSocket = {
        onmessage: null as any,
        send: jest.fn(),
        close: jest.fn(),
        readyState: WebSocket.OPEN,
      };

      renderWithProviders(<BillingManagement />, {
        websocketUrl: 'ws://localhost:8080',
      });

      // Simulate payment completion message
      const paymentMessage = {
        type: 'payment_completed',
        payment: mockPayment({ amount: 199.99, status: 'completed' }),
      };

      mockWebSocketMessage(mockWebSocket, paymentMessage);

      await expectSuccessNotification(/Payment.*199.99.*completed/);
    });

    it('handles WebSocket payment failure updates', async () => {
      const mockWebSocket = {
        onmessage: null as any,
        send: jest.fn(),
        close: jest.fn(),
        readyState: WebSocket.OPEN,
      };

      renderWithProviders(<BillingManagement />);

      const failureMessage = {
        type: 'payment_failed',
        paymentId: 'pay_123',
        reason: 'Insufficient funds',
      };

      mockWebSocketMessage(mockWebSocket, failureMessage);

      await expectErrorNotification(/Payment failed.*Insufficient funds/);
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', async () => {
      renderWithProviders(<BillingManagement />);

      // Check main navigation
      const tabList = screen.getByRole('tablist');
      expect(tabList).toBeInTheDocument();

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(4); // Overview, Invoices, Payments, Accounts

      tabs.forEach(tab => {
        expect(tab).toHaveAttribute('aria-selected');
      });
    });

    it('supports keyboard navigation', async () => {
      const { user } = renderWithProviders(<BillingManagement />);

      const tabs = screen.getAllByRole('tab');
      
      // Tab through navigation
      await user.tab();
      expect(tabs[0]).toHaveFocus();

      await user.tab();
      expect(tabs[1]).toHaveFocus();
    });
  });

  describe('Error Handling', () => {
    it('displays error state when API fails', async () => {
      mockBillingData.error = 'Failed to load billing data';
      mockBillingData.isLoading = false;

      renderWithProviders(<BillingManagement />);

      await expectErrorNotification(/Failed to load/);
    });

    it('shows loading state while fetching data', () => {
      mockBillingData.isLoading = true;
      mockBillingData.invoices = [];

      renderWithProviders(<BillingManagement />);

      expectLoadingState();
    });
  });

  describe('Performance', () => {
    it('renders quickly with large datasets', async () => {
      const manyInvoices = Array.from({ length: 1000 }, (_, i) => 
        mockInvoice({ id: `inv_${i}` })
      );

      mockBillingData.invoices = manyInvoices;

      const renderTime = performance.now();
      renderWithProviders(<BillingManagement />);
      const endTime = performance.now();

      // Should render within reasonable time even with large dataset
      expect(endTime - renderTime).toBeLessThan(200);
    });

    it('handles rapid WebSocket updates efficiently', async () => {
      const mockWebSocket = {
        onmessage: null as any,
        send: jest.fn(),
        close: jest.fn(),
        readyState: WebSocket.OPEN,
      };

      renderWithProviders(<BillingManagement />);

      // Send many rapid updates
      const startTime = performance.now();
      for (let i = 0; i < 100; i++) {
        mockWebSocketMessage(mockWebSocket, {
          type: 'stats_update',
          stats: { ...mockBillingData.stats, totalRevenue: 5000 + i },
        });
      }
      const endTime = performance.now();

      // Should handle rapid updates efficiently
      expect(endTime - startTime).toBeLessThan(100);
    });
  });
});