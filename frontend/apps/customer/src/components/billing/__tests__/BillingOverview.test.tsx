/**
 * Critical Path Test: Billing Overview Component
 * Tests billing display and payment functionality
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { BillingOverview } from '../BillingOverview';

// Mock customer API
const mockProcessPayment = jest.fn();
jest.mock('../../lib/api/customerApi', () => ({
  CustomerAPI: jest.fn().mockImplementation(() => ({
    processPayment: mockProcessPayment,
  })),
}));

// Mock error tracking
jest.mock('../../lib/monitoring/errorTracking', () => ({
  useErrorHandler: () => ({
    handleBillingError: jest.fn(),
    addBreadcrumb: jest.fn(),
  }),
}));

describe('BillingOverview - Critical Path', () => {
  const user = userEvent.setup();

  const mockInvoices = [
    {
      id: '1',
      number: 'INV-001',
      amount: 59.99,
      dueDate: '2024-02-01',
      status: 'outstanding' as const,
      paidDate: null,
      description: 'Monthly Internet Service',
      items: [
        {
          description: 'Fiber Internet 100/100',
          amount: 59.99,
          quantity: 1,
        },
      ],
    },
    {
      id: '2',
      number: 'INV-002',
      amount: 59.99,
      dueDate: '2024-01-01',
      status: 'paid' as const,
      paidDate: '2023-12-28',
      description: 'Monthly Internet Service',
      items: [],
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    mockProcessPayment.mockReset();
  });

  describe('Invoice Display', () => {
    it('renders billing overview with invoice data', () => {
      render(<BillingOverview invoices={mockInvoices} />);

      expect(screen.getByText('Billing Overview')).toBeInTheDocument();
      expect(screen.getByText('INV-001')).toBeInTheDocument();
      expect(screen.getByText('$59.99')).toBeInTheDocument();
      expect(screen.getByText('Outstanding')).toBeInTheDocument();
    });

    it('shows account balance and next due date', () => {
      render(<BillingOverview invoices={mockInvoices} />);

      // Should calculate outstanding balance
      expect(screen.getByText('$59.99')).toBeInTheDocument();

      // Should show next due date
      expect(screen.getByText('Feb 1, 2024')).toBeInTheDocument();
    });

    it('handles empty invoice list', () => {
      render(<BillingOverview invoices={[]} />);

      expect(screen.getByText('No invoices found')).toBeInTheDocument();
      expect(screen.getByText('$0.00')).toBeInTheDocument(); // Zero balance
    });

    it('displays different invoice statuses correctly', () => {
      render(<BillingOverview invoices={mockInvoices} />);

      expect(screen.getByText('Outstanding')).toBeInTheDocument();
      expect(screen.getByText('Paid')).toBeInTheDocument();
    });
  });

  describe('Payment Processing', () => {
    it('enables quick pay for outstanding invoices', () => {
      render(<BillingOverview invoices={mockInvoices} />);

      const quickPayButton = screen.getByRole('button', { name: /pay now/i });
      expect(quickPayButton).toBeInTheDocument();
      expect(quickPayButton).not.toBeDisabled();
    });

    it('processes payment successfully', async () => {
      mockProcessPayment.mockResolvedValue({
        success: true,
        transactionId: 'txn_123',
        status: 'completed',
      });

      render(<BillingOverview invoices={mockInvoices} />);

      const quickPayButton = screen.getByRole('button', { name: /pay now/i });
      await user.click(quickPayButton);

      // Should show payment modal/form
      expect(screen.getByText('Quick Payment')).toBeInTheDocument();

      // Fill payment form
      const amountInput = screen.getByLabelText(/amount/i);
      await user.clear(amountInput);
      await user.type(amountInput, '59.99');

      const confirmButton = screen.getByRole('button', { name: /confirm payment/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockProcessPayment).toHaveBeenCalledWith({
          amount: 59.99,
          invoiceId: '1',
        });
      });

      expect(screen.getByText('Payment successful!')).toBeInTheDocument();
    });

    it('handles payment failures gracefully', async () => {
      mockProcessPayment.mockRejectedValue(new Error('Payment declined'));

      render(<BillingOverview invoices={mockInvoices} />);

      const quickPayButton = screen.getByRole('button', { name: /pay now/i });
      await user.click(quickPayButton);

      const amountInput = screen.getByLabelText(/amount/i);
      await user.type(amountInput, '59.99');

      const confirmButton = screen.getByRole('button', { name: /confirm payment/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(screen.getByText('Payment failed. Please try again.')).toBeInTheDocument();
      });
    });

    it('validates payment amounts', async () => {
      render(<BillingOverview invoices={mockInvoices} />);

      const quickPayButton = screen.getByRole('button', { name: /pay now/i });
      await user.click(quickPayButton);

      const amountInput = screen.getByLabelText(/amount/i);
      await user.clear(amountInput);
      await user.type(amountInput, '0');

      const confirmButton = screen.getByRole('button', { name: /confirm payment/i });
      await user.click(confirmButton);

      expect(screen.getByText('Amount must be greater than $0')).toBeInTheDocument();
      expect(mockProcessPayment).not.toHaveBeenCalled();
    });
  });

  describe('Invoice Details', () => {
    it('expands invoice details on click', async () => {
      render(<BillingOverview invoices={mockInvoices} />);

      const invoiceRow = screen.getByText('INV-001');
      await user.click(invoiceRow);

      expect(screen.getByText('Fiber Internet 100/100')).toBeInTheDocument();
      expect(screen.getByText('Monthly Internet Service')).toBeInTheDocument();
    });

    it('shows invoice line items correctly', async () => {
      render(<BillingOverview invoices={mockInvoices} />);

      const invoiceRow = screen.getByText('INV-001');
      await user.click(invoiceRow);

      expect(screen.getByText('Fiber Internet 100/100')).toBeInTheDocument();
      expect(screen.getByText('Qty: 1')).toBeInTheDocument();
      expect(screen.getByText('$59.99')).toBeInTheDocument();
    });

    it('allows invoice download', async () => {
      // Mock window.open for PDF download
      const mockOpen = jest.fn();
      Object.defineProperty(window, 'open', { value: mockOpen });

      render(<BillingOverview invoices={mockInvoices} />);

      const downloadButton = screen.getByRole('button', { name: /download/i });
      await user.click(downloadButton);

      expect(mockOpen).toHaveBeenCalledWith('/api/invoices/1/download', '_blank');
    });
  });

  describe('Auto-pay and Payment Methods', () => {
    it('shows auto-pay status when enabled', () => {
      render(
        <BillingOverview
          invoices={mockInvoices}
          autoPayEnabled={true}
          nextAutoPayDate="2024-02-01"
        />
      );

      expect(screen.getByText('Auto-pay enabled')).toBeInTheDocument();
      expect(screen.getByText('Next payment: Feb 1, 2024')).toBeInTheDocument();
    });

    it('allows auto-pay configuration', async () => {
      render(<BillingOverview invoices={mockInvoices} autoPayEnabled={false} />);

      const setupAutoPayButton = screen.getByRole('button', { name: /set up auto.pay/i });
      await user.click(setupAutoPayButton);

      expect(screen.getByText('Set Up Auto-Pay')).toBeInTheDocument();
    });

    it('shows payment method selection for auto-pay', async () => {
      render(<BillingOverview invoices={mockInvoices} autoPayEnabled={false} />);

      const setupAutoPayButton = screen.getByRole('button', { name: /set up auto.pay/i });
      await user.click(setupAutoPayButton);

      expect(screen.getByText('Select Payment Method')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /add new payment method/i })).toBeInTheDocument();
    });
  });

  describe('Accessibility and UX', () => {
    it('has proper ARIA labels and roles', () => {
      render(<BillingOverview invoices={mockInvoices} />);

      const table = screen.getByRole('table');
      expect(table).toHaveAttribute('aria-label', 'Billing invoices');

      const payButton = screen.getByRole('button', { name: /pay now/i });
      expect(payButton).toHaveAttribute('aria-describedby');
    });

    it('supports keyboard navigation', async () => {
      render(<BillingOverview invoices={mockInvoices} />);

      // Tab through interactive elements
      await user.tab();
      expect(screen.getByRole('button', { name: /pay now/i })).toHaveFocus();

      await user.tab();
      expect(screen.getByRole('button', { name: /download/i })).toHaveFocus();
    });

    it('provides screen reader friendly content', () => {
      render(<BillingOverview invoices={mockInvoices} />);

      expect(screen.getByText('Outstanding invoice INV-001')).toBeInTheDocument();
      expect(screen.getByText('Due date February 1, 2024')).toBeInTheDocument();
    });
  });

  describe('Error States and Loading', () => {
    it('shows loading state while processing payment', async () => {
      mockProcessPayment.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

      render(<BillingOverview invoices={mockInvoices} />);

      const quickPayButton = screen.getByRole('button', { name: /pay now/i });
      await user.click(quickPayButton);

      const amountInput = screen.getByLabelText(/amount/i);
      await user.type(amountInput, '59.99');

      const confirmButton = screen.getByRole('button', { name: /confirm payment/i });
      await user.click(confirmButton);

      expect(screen.getByText('Processing payment...')).toBeInTheDocument();
      expect(confirmButton).toBeDisabled();
    });

    it('handles network errors during payment', async () => {
      mockProcessPayment.mockRejectedValue(new Error('Network error'));

      render(<BillingOverview invoices={mockInvoices} />);

      const quickPayButton = screen.getByRole('button', { name: /pay now/i });
      await user.click(quickPayButton);

      const amountInput = screen.getByLabelText(/amount/i);
      await user.type(amountInput, '59.99');

      const confirmButton = screen.getByRole('button', { name: /confirm payment/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(screen.getByText(/network error.*try again/i)).toBeInTheDocument();
      });
    });

    it('shows proper error state for invalid invoice data', () => {
      const invalidInvoices = [
        {
          id: '1',
          number: '', // Invalid invoice number
          amount: -10, // Invalid amount
          dueDate: 'invalid-date',
          status: 'unknown' as any,
        },
      ];

      render(<BillingOverview invoices={invalidInvoices} />);

      expect(screen.getByText('Error loading invoice data')).toBeInTheDocument();
    });
  });
});
