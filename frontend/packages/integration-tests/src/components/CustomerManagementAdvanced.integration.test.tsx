/**
 * Customer Management Advanced - Component Integration Tests
 * Tests the integration between customer management, API clients, and data flow
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CustomerManagementAdvanced } from '../../../apps/reseller/src/components/customers/CustomerManagementAdvanced';
import { IdentityApiClient } from '../../headless/src/api/clients/IdentityApiClient';
import { BillingApiClient } from '../../headless/src/api/clients/BillingApiClient';
import { NotificationsApiClient } from '../../headless/src/api/clients/NotificationsApiClient';
import type { Customer } from '../../headless/src/types/identity';

// Mock API clients
jest.mock('../../headless/src/api/clients/IdentityApiClient');
jest.mock('../../headless/src/api/clients/BillingApiClient');
jest.mock('../../headless/src/api/clients/NotificationsApiClient');

const MockedIdentityApiClient = IdentityApiClient as jest.MockedClass<typeof IdentityApiClient>;
const MockedBillingApiClient = BillingApiClient as jest.MockedClass<typeof BillingApiClient>;
const MockedNotificationsApiClient = NotificationsApiClient as jest.MockedClass<
  typeof NotificationsApiClient
>;

// Mock data
const mockCustomers: Customer[] = [
  {
    id: 'cust_001',
    tenantId: 'tenant_test',
    email: 'john.doe@example.com',
    firstName: 'John',
    lastName: 'Doe',
    phone: '+1-555-0123',
    status: 'active',
    profile: {
      company: 'Acme Corp',
      address: '123 Main St',
      city: 'Seattle',
      state: 'WA',
      zipCode: '98101',
    },
    metadata: {
      monthlyRevenue: 299.99,
      lifetimeValue: 7200.0,
      tags: ['VIP', 'Enterprise'],
    },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T12:00:00Z',
  },
  {
    id: 'cust_002',
    tenantId: 'tenant_test',
    email: 'jane.smith@techstart.io',
    firstName: 'Jane',
    lastName: 'Smith',
    phone: '+1-555-0456',
    status: 'prospect',
    profile: {
      company: 'TechStart',
      address: '456 Innovation Blvd',
      city: 'Portland',
      state: 'OR',
      zipCode: '97201',
    },
    metadata: {
      monthlyRevenue: 0,
      lifetimeValue: 0,
      probability: 75,
      dealSize: 499.99,
      tags: ['Startup', 'High-Potential'],
    },
    createdAt: '2024-01-10T00:00:00Z',
    updatedAt: '2024-01-20T15:30:00Z',
  },
];

const mockBillingData = [
  {
    customerId: 'cust_001',
    totalRevenue: 7200.0,
    monthlyRevenue: 299.99,
    unpaidInvoices: 0,
    lastPaymentDate: '2024-01-15',
  },
];

const mockAnalytics = {
  totalCustomers: 250,
  activeCustomers: 180,
  prospects: 70,
  totalRevenue: 75000.0,
  averageDealSize: 350.0,
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

describe('CustomerManagementAdvanced Integration Tests', () => {
  let identityClient: jest.Mocked<IdentityApiClient>;
  let billingClient: jest.Mocked<BillingApiClient>;
  let notificationsClient: jest.Mocked<NotificationsApiClient>;

  beforeEach(() => {
    // Setup API client mocks
    identityClient = {
      getCustomers: jest.fn(),
      getCustomerById: jest.fn(),
      createCustomer: jest.fn(),
      updateCustomer: jest.fn(),
      deleteCustomer: jest.fn(),
      searchCustomers: jest.fn(),
      bulkImportCustomers: jest.fn(),
      exportCustomers: jest.fn(),
    } as any;

    billingClient = {
      getCustomerBilling: jest.fn(),
      getCustomerInvoices: jest.fn(),
      createInvoice: jest.fn(),
      updateInvoice: jest.fn(),
      processPayment: jest.fn(),
      getPaymentMethods: jest.fn(),
      getBillingAnalytics: jest.fn(),
    } as any;

    notificationsClient = {
      sendNotification: jest.fn(),
      createTemplate: jest.fn(),
      getTemplates: jest.fn(),
      scheduleNotification: jest.fn(),
      getNotificationHistory: jest.fn(),
    } as any;

    MockedIdentityApiClient.mockImplementation(() => identityClient);
    MockedBillingApiClient.mockImplementation(() => billingClient);
    MockedNotificationsApiClient.mockImplementation(() => notificationsClient);

    // Setup default mock responses
    identityClient.getCustomers.mockResolvedValue({
      customers: mockCustomers,
      total: mockCustomers.length,
      page: 1,
      pageSize: 20,
    });

    billingClient.getBillingAnalytics.mockResolvedValue(mockAnalytics);
    billingClient.getCustomerBilling.mockResolvedValue(mockBillingData[0]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Integration', () => {
    it('should render customer management with data integration', async () => {
      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Wait for initial data load
      await waitFor(() => {
        expect(screen.getByText('Customer Management')).toBeInTheDocument();
      });

      // Verify API client integration
      expect(identityClient.getCustomers).toHaveBeenCalledWith({
        page: 1,
        pageSize: 20,
        search: '',
        filters: {},
      });

      expect(billingClient.getBillingAnalytics).toHaveBeenCalled();

      // Check customer data rendering
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      });
    });

    it('should handle customer search with API integration', async () => {
      const user = userEvent.setup();
      identityClient.searchCustomers.mockResolvedValue({
        customers: [mockCustomers[0]],
        total: 1,
        page: 1,
        pageSize: 20,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Wait for initial render
      await waitFor(() => {
        expect(screen.getByText('Customer Management')).toBeInTheDocument();
      });

      // Perform search
      const searchInput = screen.getByPlaceholderText(/search customers/i);
      await user.type(searchInput, 'John');

      await waitFor(() => {
        expect(identityClient.searchCustomers).toHaveBeenCalledWith({
          query: 'John',
          page: 1,
          pageSize: 20,
          filters: {},
        });
      });
    });

    it('should integrate customer status updates with notifications', async () => {
      const user = userEvent.setup();
      identityClient.updateCustomer.mockResolvedValue(mockCustomers[0]);
      notificationsClient.sendNotification.mockResolvedValue({ success: true });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });

      // Find and click status update button
      const statusButton = screen.getByText('Active');
      await user.click(statusButton);

      // Select different status
      const inactiveOption = screen.getByText('Inactive');
      await user.click(inactiveOption);

      await waitFor(() => {
        expect(identityClient.updateCustomer).toHaveBeenCalledWith('cust_001', {
          status: 'inactive',
        });
      });

      // Verify notification sent
      await waitFor(() => {
        expect(notificationsClient.sendNotification).toHaveBeenCalledWith({
          customerId: 'cust_001',
          type: 'status_change',
          message: 'Customer status updated to inactive',
          channels: ['email'],
        });
      });
    });

    it('should handle billing integration for customer financial data', async () => {
      const user = userEvent.setup();
      billingClient.getCustomerBilling.mockResolvedValue({
        customerId: 'cust_001',
        totalRevenue: 7200.0,
        monthlyRevenue: 299.99,
        unpaidInvoices: 2,
        lastPaymentDate: '2024-01-15',
        paymentMethod: 'ACH',
        creditScore: 750,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });

      // Click on customer to view details
      const customerRow = screen.getByText('John Doe');
      await user.click(customerRow);

      await waitFor(() => {
        expect(billingClient.getCustomerBilling).toHaveBeenCalledWith('cust_001');
      });

      // Verify billing data displayed
      await waitFor(() => {
        expect(screen.getByText('$7,200.00')).toBeInTheDocument(); // Lifetime value
        expect(screen.getByText('$299.99')).toBeInTheDocument(); // Monthly revenue
      });
    });
  });

  describe('Data Flow Integration', () => {
    it('should coordinate data updates across multiple API clients', async () => {
      const user = userEvent.setup();
      const updatedCustomer = { ...mockCustomers[0], status: 'inactive' as const };
      identityClient.updateCustomer.mockResolvedValue(updatedCustomer);
      billingClient.getCustomerBilling.mockResolvedValue({
        ...mockBillingData[0],
        status: 'suspended',
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });

      // Update customer status
      const moreActionsButton = screen.getByTestId('customer-actions-cust_001');
      await user.click(moreActionsButton);

      const suspendOption = screen.getByText('Suspend Customer');
      await user.click(suspendOption);

      // Confirm suspension
      const confirmButton = screen.getByText('Confirm Suspension');
      await user.click(confirmButton);

      await waitFor(() => {
        // Verify identity update
        expect(identityClient.updateCustomer).toHaveBeenCalledWith('cust_001', {
          status: 'inactive',
          metadata: expect.objectContaining({
            suspensionReason: 'manual',
            suspensionDate: expect.any(String),
          }),
        });

        // Verify billing status update
        expect(billingClient.getCustomerBilling).toHaveBeenCalledWith('cust_001');

        // Verify notification sent
        expect(notificationsClient.sendNotification).toHaveBeenCalledWith({
          customerId: 'cust_001',
          type: 'account_suspension',
          message: 'Your account has been temporarily suspended',
          channels: ['email', 'sms'],
        });
      });
    });

    it('should handle bulk operations with progress tracking', async () => {
      const user = userEvent.setup();
      const bulkCustomers = Array(50)
        .fill(null)
        .map((_, index) => ({
          email: `customer${index}@example.com`,
          firstName: `Customer`,
          lastName: `${index}`,
          phone: `+1-555-${String(index).padStart(4, '0')}`,
        }));

      identityClient.bulkImportCustomers.mockImplementation(async (customers) => {
        // Simulate progress updates
        return {
          success: true,
          imported: customers.length,
          failed: 0,
          errors: [],
        };
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Customer Management')).toBeInTheDocument();
      });

      // Click bulk import
      const importButton = screen.getByText('Import Customers');
      await user.click(importButton);

      // Upload file (mock file input)
      const fileInput = screen.getByTestId('customer-file-upload');
      const mockFile = new File([JSON.stringify(bulkCustomers)], 'customers.json', {
        type: 'application/json',
      });

      await user.upload(fileInput, mockFile);

      // Start import
      const startImportButton = screen.getByText('Start Import');
      await user.click(startImportButton);

      await waitFor(() => {
        expect(identityClient.bulkImportCustomers).toHaveBeenCalledWith(bulkCustomers);
      });

      // Verify success message
      await waitFor(() => {
        expect(screen.getByText('Successfully imported 50 customers')).toBeInTheDocument();
      });
    });

    it('should handle error scenarios with proper fallbacks', async () => {
      // Simulate API failure
      identityClient.getCustomers.mockRejectedValue(new Error('API Error'));
      billingClient.getBillingAnalytics.mockRejectedValue(new Error('Billing Service Unavailable'));

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Wait for error states
      await waitFor(() => {
        expect(screen.getByText(/error loading customers/i)).toBeInTheDocument();
        expect(screen.getByText(/billing data unavailable/i)).toBeInTheDocument();
      });

      // Verify retry functionality
      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(identityClient.getCustomers).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Performance Integration', () => {
    it('should handle large datasets with pagination', async () => {
      const largeDataset = Array(1000)
        .fill(null)
        .map((_, index) => ({
          ...mockCustomers[0],
          id: `cust_${String(index).padStart(4, '0')}`,
          email: `customer${index}@example.com`,
        }));

      identityClient.getCustomers.mockResolvedValue({
        customers: largeDataset.slice(0, 20),
        total: largeDataset.length,
        page: 1,
        pageSize: 20,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('1,000 total customers')).toBeInTheDocument();
      });

      // Test pagination
      const nextPageButton = screen.getByText('Next Page');
      fireEvent.click(nextPageButton);

      await waitFor(() => {
        expect(identityClient.getCustomers).toHaveBeenCalledWith({
          page: 2,
          pageSize: 20,
          search: '',
          filters: {},
        });
      });
    });

    it('should implement proper caching for frequently accessed data', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });

      // Click customer details multiple times
      const customerRow = screen.getByText('John Doe');
      await user.click(customerRow);

      // Wait for details to load
      await waitFor(() => {
        expect(billingClient.getCustomerBilling).toHaveBeenCalledWith('cust_001');
      });

      // Close and reopen details
      const closeButton = screen.getByText('Close');
      await user.click(closeButton);

      await user.click(customerRow);

      // Billing data should not be fetched again due to caching
      expect(billingClient.getCustomerBilling).toHaveBeenCalledTimes(1);
    });
  });

  describe('Security Integration', () => {
    it('should handle authentication failures gracefully', async () => {
      identityClient.getCustomers.mockRejectedValue({
        status: 401,
        message: 'Unauthorized',
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
      });
    });

    it('should respect role-based access controls', async () => {
      const user = userEvent.setup();
      identityClient.deleteCustomer.mockRejectedValue({
        status: 403,
        message: 'Insufficient permissions',
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });

      // Try to delete customer (should be restricted)
      const deleteButton = screen.getByTestId('delete-customer-cust_001');
      await user.click(deleteButton);

      const confirmDelete = screen.getByText('Confirm Delete');
      await user.click(confirmDelete);

      await waitFor(() => {
        expect(screen.getByText(/insufficient permissions/i)).toBeInTheDocument();
      });
    });
  });
});
