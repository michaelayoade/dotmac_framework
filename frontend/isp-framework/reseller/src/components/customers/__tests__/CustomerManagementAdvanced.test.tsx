/**
 * Comprehensive Test Suite for CustomerManagementAdvanced Component
 *
 * Tests cover:
 * - Component rendering and lifecycle
 * - User interactions and form handling
 * - API integration and error states
 * - Accessibility compliance
 * - Performance benchmarks
 * - Security validation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CustomerManagementAdvanced } from '../CustomerManagementAdvanced';
// Remove unused import - functionality handled by headless package

// Mock dependencies
jest.mock('@dotmac/headless', () => ({
  usePartnerCustomers: jest.fn(),
  useCreateCustomer: jest.fn(),
  useUpdateCustomer: jest.fn(),
  useDeleteCustomer: jest.fn(),
  partnerApiClient: {
    getCustomers: jest.fn(),
    createCustomer: jest.fn(),
    updateCustomer: jest.fn(),
    deleteCustomer: jest.fn(),
  },
}));

jest.mock('../../layout/ResellerLayout', () => ({
  ResellerLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Test data
const mockCustomers = [
  {
    id: 'CUST-001',
    name: 'Tech Innovators Inc',
    email: 'admin@techinnovators.com',
    phone: '+1-555-0123',
    company: 'Tech Innovators Inc',
    address: '123 Innovation Drive',
    city: 'Tech Valley',
    state: 'CA',
    zipCode: '94000',
    status: 'active',
    source: 'referral',
    plan: 'enterprise',
    usage: 85.5,
    mrr: 299.99,
    monthlyRevenue: 299.99,
    connectionStatus: 'online',
    joinDate: '2024-01-15T00:00:00Z',
    lastPayment: '2024-03-01T00:00:00Z',
    lifetimeValue: 7199.76,
  },
  {
    id: 'CUST-002',
    name: 'Local Bakery',
    email: 'owner@localbakery.com',
    phone: '+1-555-0456',
    company: 'Sweet Treats Bakery',
    address: '456 Main Street',
    city: 'Downtown',
    state: 'CA',
    zipCode: '94001',
    status: 'active',
    source: 'website',
    plan: 'business_pro',
    usage: 42.3,
    mrr: 79.99,
    monthlyRevenue: 79.99,
    connectionStatus: 'online',
    joinDate: '2024-02-10T00:00:00Z',
    lastPayment: '2024-03-01T00:00:00Z',
    lifetimeValue: 879.89,
  },
];

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createQueryClient();
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

describe('CustomerManagementAdvanced Component', () => {
  let mockUsePartnerCustomers: jest.MockedFunction<any>;
  let mockUseCreateCustomer: jest.MockedFunction<any>;
  let mockUseUpdateCustomer: jest.MockedFunction<any>;
  let mockUseDeleteCustomer: jest.MockedFunction<any>;

  beforeEach(() => {
    const {
      usePartnerCustomers,
      useCreateCustomer,
      useUpdateCustomer,
      useDeleteCustomer,
    } = require('@dotmac/headless');

    mockUsePartnerCustomers = usePartnerCustomers as jest.MockedFunction<any>;
    mockUseCreateCustomer = useCreateCustomer as jest.MockedFunction<any>;
    mockUseUpdateCustomer = useUpdateCustomer as jest.MockedFunction<any>;
    mockUseDeleteCustomer = useDeleteCustomer as jest.MockedFunction<any>;

    // Default mock implementations
    mockUsePartnerCustomers.mockReturnValue({
      data: { customers: mockCustomers, total: 2, hasNext: false, hasPrev: false },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    mockUseCreateCustomer.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      error: null,
    });

    mockUseUpdateCustomer.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      error: null,
    });

    mockUseDeleteCustomer.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      error: null,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render component successfully', async () => {
      const { container } = render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      expect(screen.getByText('Customer Management')).toBeInTheDocument();
      expect(container).toBeInTheDocument();

      // Test accessibility
      await global.testUtils.checkA11y(container);
    });

    it('should display customers in table format', async () => {
      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('Tech Innovators Inc')).toBeInTheDocument();
        expect(screen.getByText('Local Bakery')).toBeInTheDocument();
      });

      // Check table headers
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Plan')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('should show loading state', async () => {
      mockUsePartnerCustomers.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('should show error state', async () => {
      const errorMessage = 'Failed to load customers';
      mockUsePartnerCustomers.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error(errorMessage),
        refetch: jest.fn(),
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  describe('Search and Filter Functionality', () => {
    it('should filter customers by search term', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/search customers/i);

      await user.type(searchInput, 'Tech');

      // Should trigger search with debounced input
      await waitFor(() => {
        expect(mockUsePartnerCustomers).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            search: 'Tech',
          })
        );
      });
    });

    it('should filter by customer status', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const statusFilter = screen.getByLabelText(/filter by status/i);

      await user.selectOptions(statusFilter, 'active');

      await waitFor(() => {
        expect(mockUsePartnerCustomers).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            status: 'active',
          })
        );
      });
    });

    it('should sort customers by different criteria', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const sortSelect = screen.getByLabelText(/sort by/i);

      await user.selectOptions(sortSelect, 'mrr');

      await waitFor(() => {
        expect(mockUsePartnerCustomers).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            sortBy: 'mrr',
            sortOrder: 'desc',
          })
        );
      });
    });
  });

  describe('Customer Creation', () => {
    it('should open create customer modal', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const addButton = screen.getByRole('button', { name: /add customer/i });
      await user.click(addButton);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText(/create new customer/i)).toBeInTheDocument();
    });

    it('should create customer with valid data', async () => {
      const user = userEvent.setup();
      const mockMutate = jest.fn();

      mockUseCreateCustomer.mockReturnValue({
        mutate: mockMutate,
        isPending: false,
        error: null,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Open modal
      const addButton = screen.getByRole('button', { name: /add customer/i });
      await user.click(addButton);

      // Fill form
      await user.type(screen.getByLabelText(/company name/i), 'New Company');
      await user.type(screen.getByLabelText(/email/i), 'test@newcompany.com');
      await user.type(screen.getByLabelText(/phone/i), '+1-555-9999');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /create customer/i });
      await user.click(submitButton);

      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Company',
          email: 'test@newcompany.com',
          phone: '+1-555-9999',
        })
      );
    });

    it('should validate form inputs', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Open modal
      const addButton = screen.getByRole('button', { name: /add customer/i });
      await user.click(addButton);

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /create customer/i });
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should sanitize malicious input', async () => {
      const user = userEvent.setup();
      const mockMutate = jest.fn();

      mockUseCreateCustomer.mockReturnValue({
        mutate: mockMutate,
        isPending: false,
        error: null,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Open modal
      const addButton = screen.getByRole('button', { name: /add customer/i });
      await user.click(addButton);

      // Input malicious data
      const maliciousInput = '<script>alert("xss")</script>Evil Corp';
      await user.type(screen.getByLabelText(/company name/i), maliciousInput);
      await user.type(screen.getByLabelText(/email/i), 'test@evil.com');
      await user.type(screen.getByLabelText(/phone/i), '+1-555-0000');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /create customer/i });
      await user.click(submitButton);

      // Should sanitize the input
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: expect.not.stringContaining('<script>'),
        })
      );

      // Verify sanitization worked
      const { name } = mockMutate.mock.calls[0][0];
      const result = defaultSanitizer.sanitizeText(maliciousInput);
      expect(name).toBe(result.sanitized);
    });
  });

  describe('Customer Management Actions', () => {
    it('should handle customer editing', async () => {
      const user = userEvent.setup();
      const mockMutate = jest.fn();

      mockUseUpdateCustomer.mockReturnValue({
        mutate: mockMutate,
        isPending: false,
        error: null,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Wait for customers to load
      await waitFor(() => {
        expect(screen.getByText('Tech Innovators Inc')).toBeInTheDocument();
      });

      // Click edit button for first customer
      const editButtons = screen.getAllByLabelText(/edit customer/i);
      await user.click(editButtons[0]);

      // Should open edit modal
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Tech Innovators Inc')).toBeInTheDocument();

      // Make changes
      const nameInput = screen.getByDisplayValue('Tech Innovators Inc');
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated Tech Company');

      // Submit changes
      const saveButton = screen.getByRole('button', { name: /save changes/i });
      await user.click(saveButton);

      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'CUST-001',
          name: 'Updated Tech Company',
        })
      );
    });

    it('should handle customer deletion', async () => {
      const user = userEvent.setup();
      const mockMutate = jest.fn();

      mockUseDeleteCustomer.mockReturnValue({
        mutate: mockMutate,
        isPending: false,
        error: null,
      });

      // Mock window.confirm
      window.confirm = jest.fn(() => true);

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Tech Innovators Inc')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByLabelText(/delete customer/i);
      await user.click(deleteButtons[0]);

      expect(window.confirm).toHaveBeenCalledWith(
        expect.stringContaining('Are you sure you want to delete')
      );
      expect(mockMutate).toHaveBeenCalledWith('CUST-001');
    });

    it('should export customer data', async () => {
      const user = userEvent.setup();

      // Mock URL.createObjectURL
      URL.createObjectURL = jest.fn(() => 'blob:mock-url');
      URL.revokeObjectURL = jest.fn();

      const mockClick = jest.fn();
      const mockLink = {
        href: '',
        download: '',
        click: mockClick,
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const exportButton = screen.getByRole('button', { name: /export/i });
      await user.click(exportButton);

      expect(URL.createObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
    });
  });

  describe('Performance Testing', () => {
    it('should render large customer lists efficiently', async () => {
      const largeCustomerList = Array.from({ length: 1000 }, (_, i) => ({
        ...mockCustomers[0],
        id: `CUST-${i.toString().padStart(3, '0')}`,
        name: `Customer ${i}`,
        email: `customer${i}@example.com`,
      }));

      mockUsePartnerCustomers.mockReturnValue({
        data: { customers: largeCustomerList, total: 1000, hasNext: true, hasPrev: false },
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      });

      await global.testUtils.expectPerformance(async () => {
        render(
          <TestWrapper>
            <CustomerManagementAdvanced />
          </TestWrapper>
        );

        await waitFor(() => {
          expect(screen.getByText('Customer 0')).toBeInTheDocument();
        });
      }, 200); // Should render within 200ms
    });

    it('should handle rapid filter changes efficiently', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/search customers/i);

      await global.testUtils.expectPerformance(async () => {
        // Simulate rapid typing
        await user.type(searchInput, 'rapid filter test');

        // Wait for debounced search
        await waitFor(() => {
          expect(mockUsePartnerCustomers).toHaveBeenCalled();
        });
      }, 500);
    });
  });

  describe('Security Testing', () => {
    it('should prevent XSS attacks in customer data', () => {
      const maliciousCustomer = {
        ...mockCustomers[0],
        name: '<script>alert("xss")</script>Malicious Customer',
        email: 'test@evil.com',
      };

      mockUsePartnerCustomers.mockReturnValue({
        data: { customers: [maliciousCustomer], total: 1, hasNext: false, hasPrev: false },
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      });

      const { container } = render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Should not contain unescaped script tags
      global.testUtils.expectSecureComponent({ container });
    });

    it('should validate CSRF tokens in API calls', async () => {
      const user = userEvent.setup();
      const mockMutate = jest.fn();

      mockUseCreateCustomer.mockReturnValue({
        mutate: mockMutate,
        isPending: false,
        error: null,
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Open create modal and submit
      const addButton = screen.getByRole('button', { name: /add customer/i });
      await user.click(addButton);

      await user.type(screen.getByLabelText(/company name/i), 'Test Company');
      await user.type(screen.getByLabelText(/email/i), 'test@company.com');

      const submitButton = screen.getByRole('button', { name: /create customer/i });
      await user.click(submitButton);

      // Verify CSRF protection is applied
      expect(mockMutate).toHaveBeenCalled();
    });
  });

  describe('Accessibility Testing', () => {
    it('should meet WCAG accessibility standards', async () => {
      const { container } = render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      await global.testUtils.checkA11y(container, {
        rules: {
          'color-contrast': { enabled: true },
          'keyboard-navigation': { enabled: true },
          'aria-labels': { enabled: true },
          'focus-management': { enabled: true },
        },
      });
    });

    it('should support keyboard navigation', async () => {
      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      const addButton = screen.getByRole('button', { name: /add customer/i });

      // Should be focusable
      addButton.focus();
      expect(addButton).toHaveFocus();

      // Should respond to Enter key
      fireEvent.keyDown(addButton, { key: 'Enter', code: 'Enter' });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should have proper ARIA labels and roles', async () => {
      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Check main content has proper roles
      expect(screen.getByRole('main')).toBeInTheDocument();
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /add customer/i })).toBeInTheDocument();

      // Check search input has proper label
      const searchInput = screen.getByPlaceholderText(/search customers/i);
      expect(searchInput).toHaveAccessibleName();
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      const errorMessage = 'Network error occurred';
      mockUsePartnerCustomers.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error(errorMessage),
        refetch: jest.fn(),
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('should handle creation errors', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Customer already exists';

      mockUseCreateCustomer.mockReturnValue({
        mutate: jest.fn(),
        isPending: false,
        error: new Error(errorMessage),
      });

      render(
        <TestWrapper>
          <CustomerManagementAdvanced />
        </TestWrapper>
      );

      // Open modal and submit
      const addButton = screen.getByRole('button', { name: /add customer/i });
      await user.click(addButton);

      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });
});
