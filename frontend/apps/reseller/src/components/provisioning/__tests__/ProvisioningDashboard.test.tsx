import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProvisioningDashboard } from '../ProvisioningDashboard';
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
  generateTestData,
} from '@dotmac/testing';
import { server, mockProvisioningRequest } from '@dotmac/testing';

const mockProvisioningData = {
  requests: [
    mockProvisioningRequest({ 
      id: 'req_1', 
      status: 'pending', 
      priority: 'high',
      customerInfo: { name: 'John Doe', email: 'john@example.com', phone: '+1-555-0123' },
    }),
    mockProvisioningRequest({ 
      id: 'req_2', 
      status: 'approved', 
      priority: 'medium',
      customerInfo: { name: 'Jane Smith', email: 'jane@example.com', phone: '+1-555-0124' },
    }),
    mockProvisioningRequest({ 
      id: 'req_3', 
      status: 'installing', 
      priority: 'urgent',
      customerInfo: { name: 'Bob Wilson', email: 'bob@example.com', phone: '+1-555-0125' },
      assignedTechnician: 'tech_001',
    }),
  ],
  templates: [
    {
      id: 'template_1',
      name: 'Fiber 100 Mbps',
      category: 'internet',
      speed: '100 Mbps',
      pricing: { setup: 99, monthly: 79.99 },
      features: ['High Speed', 'Unlimited Data', '24/7 Support'],
      sla: { provisioningTime: 24, installationWindow: '9AM-5PM', supportLevel: 'Premium' },
    },
    {
      id: 'template_2',
      name: 'Cable TV Package',
      category: 'tv',
      pricing: { setup: 49, monthly: 59.99 },
      features: ['200+ Channels', 'HD Quality', 'DVR Included'],
      sla: { provisioningTime: 48, installationWindow: '8AM-6PM', supportLevel: 'Standard' },
    },
  ],
  stats: {
    totalRequests: 150,
    pendingRequests: 25,
    activeInstallations: 15,
    completedToday: 8,
    averageProvisioningTime: 18.5,
    successRate: 96.5,
    slaCompliance: 94.2,
    statusBreakdown: {
      pending: 25,
      approved: 30,
      provisioning: 20,
      installing: 15,
      active: 50,
      failed: 5,
      cancelled: 5,
    },
    technicianWorkload: {
      'Tech A': 5,
      'Tech B': 8,
      'Tech C': 3,
      'Tech D': 7,
    },
    upcomingInstallations: [],
  },
  pendingRequests: [mockProvisioningRequest({ status: 'pending' })],
  activeRequests: [mockProvisioningRequest({ status: 'installing' })],
  urgentRequests: [mockProvisioningRequest({ priority: 'urgent' })],
  todayInstallations: [mockProvisioningRequest({ 
    scheduledAt: new Date(),
    assignedTechnician: 'tech_001',
  })],
  isLoading: false,
  isConnected: true,
  error: null,
  // Actions
  createServiceRequest: jest.fn(),
  updateRequestStatus: jest.fn(),
  scheduleInstallation: jest.fn(),
  cancelRequest: jest.fn(),
  bulkUpdateStatus: jest.fn(),
  executeTask: jest.fn(),
  updateEquipmentStatus: jest.fn(),
  loadRequests: jest.fn(),
  loadTemplates: jest.fn(),
  loadStats: jest.fn(),
  selectRequest: jest.fn(),
};

jest.mock('@dotmac/headless', () => ({
  ...jest.requireActual('@dotmac/headless'),
  useProvisioning: jest.fn(() => mockProvisioningData),
}));

describe('ProvisioningDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  describe('Overview Tab', () => {
    it('renders provisioning overview with correct stats', async () => {
      renderWithProviders(<ProvisioningDashboard />);

      // Check stats cards
      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument(); // Pending requests
        expect(screen.getByText('15')).toBeInTheDocument(); // Active installations
        expect(screen.getByText('8')).toBeInTheDocument(); // Completed today
        expect(screen.getByText('94.2%')).toBeInTheDocument(); // SLA Compliance
        expect(screen.getByText('Avg: 18.5h')).toBeInTheDocument();
      });
    });

    it('displays status breakdown chart', async () => {
      renderWithProviders(<ProvisioningDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Status Breakdown')).toBeInTheDocument();
        // Check various status counts
        expect(screen.getByText('25')).toBeInTheDocument(); // pending
        expect(screen.getByText('30')).toBeInTheDocument(); // approved
        expect(screen.getByText('50')).toBeInTheDocument(); // active
      });
    });

    it('shows technician workload distribution', async () => {
      renderWithProviders(<ProvisioningDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Technician Workload')).toBeInTheDocument();
        expect(screen.getByText('Tech A')).toBeInTheDocument();
        expect(screen.getByText('Tech B')).toBeInTheDocument();
        expect(screen.getByText('5')).toBeInTheDocument(); // Tech A workload
        expect(screen.getByText('8')).toBeInTheDocument(); // Tech B workload
      });
    });

    it('displays urgent requests section', async () => {
      renderWithProviders(<ProvisioningDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Urgent Requests (1)')).toBeInTheDocument();
      });

      // Should be able to click on urgent request
      const urgentRequest = screen.getByText('pending');
      expect(urgentRequest).toBeInTheDocument();
    });

    it('shows today\'s installations', async () => {
      renderWithProviders(<ProvisioningDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Today's Installations (1)")).toBeInTheDocument();
        expect(screen.getByText('tech_001')).toBeInTheDocument();
      });
    });
  });

  describe('Service Requests Tab', () => {
    it('displays requests table with data', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Requests/));

      await waitFor(() => {
        expectTableToHaveRows(3); // 3 mock requests
      });

      // Check request data
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('jane@example.com')).toBeInTheDocument();
      expect(screen.getByText('Bob Wilson')).toBeInTheDocument();
    });

    it('allows filtering requests by status', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Requests/));

      // Use status filter
      const statusFilter = screen.getByRole('combobox', { name: /status/i });
      await user.selectOptions(statusFilter, 'pending');

      await waitFor(() => {
        expect(mockProvisioningData.loadRequests).toHaveBeenCalledWith(
          expect.objectContaining({ status: 'pending' })
        );
      });
    });

    it('handles bulk approval operations', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Requests/));

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes).toHaveLength(4); // 3 requests + select all
      });

      // Select first request
      const firstCheckbox = screen.getAllByRole('checkbox')[1];
      await user.click(firstCheckbox);

      // Check that bulk approve button appears
      await waitFor(() => {
        expect(screen.getByText(/Approve 1 Requests/)).toBeInTheDocument();
      });

      // Click bulk approve
      await user.click(screen.getByText(/Approve 1 Requests/));

      expect(mockProvisioningData.bulkUpdateStatus).toHaveBeenCalledWith(
        expect.any(Array),
        'approved',
        'Bulk approved'
      );
    });

    it('handles individual request actions', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Requests/));

      await waitFor(() => {
        // Should have approve button for pending requests
        const approveButton = screen.getByText('Approve');
        expect(approveButton).toBeInTheDocument();
      });

      await user.click(screen.getByText('Approve'));

      expect(mockProvisioningData.updateRequestStatus).toHaveBeenCalledWith(
        'req_1',
        'approved'
      );
    });

    it('handles quick scheduling', async () => {
      mockProvisioningData.scheduleInstallation.mockResolvedValueOnce(
        mockProvisioningRequest({ scheduledAt: new Date() })
      );

      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Requests/));

      await waitFor(() => {
        const scheduleButton = screen.getByText('Schedule');
        expect(scheduleButton).toBeInTheDocument();
      });

      await user.click(screen.getByText('Schedule'));

      expect(mockProvisioningData.scheduleInstallation).toHaveBeenCalled();
    });
  });

  describe('Service Request Creation', () => {
    it('opens new request modal', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      const createButton = screen.getByText('New Service Request');
      await user.click(createButton);

      expectModalToBeOpen(/New Service Request/);
    });

    it('creates new service request successfully', async () => {
      mockProvisioningData.createServiceRequest.mockResolvedValueOnce(
        mockProvisioningRequest()
      );

      const { user } = renderWithProviders(<ProvisioningDashboard />);

      // Open modal
      await user.click(screen.getByText('New Service Request'));
      expectModalToBeOpen(/New Service Request/);

      // Fill form
      await fillForm({
        'Service Template': 'template_1',
        'Customer Name': 'John Doe',
        'Customer Email': 'john@example.com',
        'Customer Phone': '+1-555-0123',
        'Street Address': '123 Main St',
        'City': 'Anytown',
        'State': 'NY',
        'ZIP Code': '12345',
      });

      // Submit form
      await submitForm(/Create Request/);

      await waitFor(() => {
        expect(mockProvisioningData.createServiceRequest).toHaveBeenCalledWith(
          expect.objectContaining({
            serviceTemplateId: 'template_1',
            customerInfo: expect.objectContaining({
              name: 'John Doe',
              email: 'john@example.com',
              phone: '+1-555-0123',
            }),
            installationAddress: expect.objectContaining({
              street: '123 Main St',
              city: 'Anytown',
              state: 'NY',
              zip: '12345',
            }),
          })
        );
      });

      expectModalToBeClosed();
      await expectSuccessNotification(/Service request.*submitted/);
    });

    it('handles request creation errors', async () => {
      mockProvisioningData.createServiceRequest.mockRejectedValueOnce(
        new Error('Validation failed')
      );

      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText('New Service Request'));
      await fillForm({
        'Customer Name': 'John Doe',
        'Customer Email': 'invalid-email',
      });
      await submitForm(/Create Request/);

      await expectErrorNotification(/Validation failed/);
    });
  });

  describe('Service Templates Tab', () => {
    it('displays available service templates', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Templates/));

      await waitFor(() => {
        expect(screen.getByText('Fiber 100 Mbps')).toBeInTheDocument();
        expect(screen.getByText('Cable TV Package')).toBeInTheDocument();
        expect(screen.getByText('$79.99/mo')).toBeInTheDocument();
        expect(screen.getByText('$59.99/mo')).toBeInTheDocument();
      });
    });

    it('shows template features and SLA information', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Templates/));

      await waitFor(() => {
        expect(screen.getByText('High Speed')).toBeInTheDocument();
        expect(screen.getByText('24/7 Support')).toBeInTheDocument();
        expect(screen.getByText('24h')).toBeInTheDocument(); // SLA provisioning time
      });
    });

    it('allows creating requests from templates', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Service Templates/));

      await waitFor(() => {
        const createRequestButtons = screen.getAllByText('Create Request');
        expect(createRequestButtons).toHaveLength(2); // One per template
      });

      await user.click(screen.getAllByText('Create Request')[0]);

      // Should call onCreateRequest with template ID
      expect(console.log).toHaveBeenCalledWith(
        'Create request for template:',
        'template_1',
        {}
      );
    });
  });

  describe('Installation Calendar Tab', () => {
    it('displays installation calendar', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Installation Calendar/));

      await waitFor(() => {
        expect(screen.getByText('Installation Calendar')).toBeInTheDocument();
        expect(screen.getByText("Today's Schedule")).toBeInTheDocument();
      });
    });

    it('shows scheduled installations by date', async () => {
      // Add a scheduled installation for today
      const todayInstallation = mockProvisioningRequest({
        scheduledAt: new Date(),
        customerInfo: { name: 'Test Customer', email: 'test@example.com', phone: '+1-555-0100' },
        assignedTechnician: 'tech_002',
      });

      mockProvisioningData.stats.upcomingInstallations = [todayInstallation];

      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText(/Installation Calendar/));

      await waitFor(() => {
        expect(screen.getByText('Test Customer')).toBeInTheDocument();
        expect(screen.getByText('tech_002')).toBeInTheDocument();
      });
    });
  });

  describe('Real-time Updates', () => {
    it('handles WebSocket request status updates', async () => {
      const mockWebSocket = {
        onmessage: null as any,
        send: jest.fn(),
        close: jest.fn(),
        readyState: WebSocket.OPEN,
      };

      renderWithProviders(<ProvisioningDashboard />);

      // Simulate request status update
      const statusMessage = {
        type: 'request_status_update',
        requestId: 'req_1',
        updates: { status: 'approved' },
      };

      mockWebSocketMessage(mockWebSocket, statusMessage);

      await expectSuccessNotification(/Request.*approved/);
    });

    it('handles technician assignment notifications', async () => {
      const mockWebSocket = {
        onmessage: null as any,
        send: jest.fn(),
        close: jest.fn(),
        readyState: WebSocket.OPEN,
      };

      renderWithProviders(<ProvisioningDashboard />);

      const assignmentMessage = {
        type: 'technician_assigned',
        requestId: 'req_1',
        technicianId: 'tech_003',
      };

      mockWebSocketMessage(mockWebSocket, assignmentMessage);

      await expectSuccessNotification(/Technician assigned/);
    });

    it('handles new service requests', async () => {
      const mockWebSocket = {
        onmessage: null as any,
        send: jest.fn(),
        close: jest.fn(),
        readyState: WebSocket.OPEN,
      };

      renderWithProviders(<ProvisioningDashboard />);

      const newRequestMessage = {
        type: 'new_request',
        request: mockProvisioningRequest({ serviceTemplateId: 'template_fiber_200' }),
      };

      mockWebSocketMessage(mockWebSocket, newRequestMessage);

      await expectSuccessNotification(/New.*template_fiber_200.*request/);
    });
  });

  describe('Error Handling', () => {
    it('displays error state when API fails', async () => {
      mockProvisioningData.error = 'Failed to load provisioning data';
      mockProvisioningData.isLoading = false;

      renderWithProviders(<ProvisioningDashboard />);

      await expectErrorNotification(/Failed to load/);
    });

    it('shows loading state while fetching data', () => {
      mockProvisioningData.isLoading = true;
      mockProvisioningData.requests = [];

      renderWithProviders(<ProvisioningDashboard />);

      expectLoadingState();
    });

    it('handles network connectivity issues', async () => {
      mockProvisioningData.isConnected = false;

      renderWithProviders(<ProvisioningDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Offline')).toBeInTheDocument();
      });
    });
  });

  describe('Performance', () => {
    it('renders efficiently with large datasets', async () => {
      const manyRequests = generateTestData(() => mockProvisioningRequest(), 1000);
      mockProvisioningData.requests = manyRequests;

      const startTime = performance.now();
      renderWithProviders(<ProvisioningDashboard />);
      const endTime = performance.now();

      // Should render within reasonable time
      expect(endTime - startTime).toBeLessThan(300);
    });

    it('handles virtualized table performance', async () => {
      const manyRequests = generateTestData(() => mockProvisioningRequest(), 10000);
      mockProvisioningData.requests = manyRequests;

      const { user } = renderWithProviders(<ProvisioningDashboard />);

      // Switch to requests tab
      const startTime = performance.now();
      await user.click(screen.getByText(/Service Requests/));
      const endTime = performance.now();

      // Virtualized table should handle large datasets efficiently
      expect(endTime - startTime).toBeLessThan(500);

      await waitFor(() => {
        // Only visible rows should be rendered
        const rows = screen.getAllByRole('row');
        expect(rows.length).toBeLessThan(50); // Much less than 10000
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and keyboard navigation', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      // Check tab navigation
      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(4);

      // Test keyboard navigation
      await user.tab();
      expect(tabs[0]).toHaveFocus();

      await user.keyboard('{ArrowRight}');
      expect(tabs[1]).toHaveFocus();
    });

    it('provides screen reader friendly content', async () => {
      renderWithProviders(<ProvisioningDashboard />);

      // Check for proper headings
      expect(screen.getByRole('heading', { name: /Service Provisioning/ })).toBeInTheDocument();
      
      // Check for proper labels on interactive elements
      const createButton = screen.getByRole('button', { name: /New Service Request/ });
      expect(createButton).toHaveAccessibleName();
    });
  });

  describe('Data Validation', () => {
    it('validates form inputs correctly', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText('New Service Request'));

      // Try to submit without required fields
      await submitForm(/Create Request/);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/required/i)).toBeInTheDocument();
      });
    });

    it('validates email format', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText('New Service Request'));

      await fillForm({
        'Customer Email': 'invalid-email-format',
      });

      await submitForm(/Create Request/);

      await waitFor(() => {
        expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
      });
    });

    it('validates phone number format', async () => {
      const { user } = renderWithProviders(<ProvisioningDashboard />);

      await user.click(screen.getByText('New Service Request'));

      await fillForm({
        'Customer Phone': '123', // Invalid format
      });

      await submitForm(/Create Request/);

      await waitFor(() => {
        expect(screen.getByText(/invalid phone/i)).toBeInTheDocument();
      });
    });
  });
});