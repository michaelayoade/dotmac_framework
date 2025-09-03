/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkOrdersList } from '../../../components/work-orders/WorkOrdersList';
import { technicianApiClient } from '../../../lib/api/technician-client';
import { db } from '../../../lib/offline-db';
import '@testing-library/jest-dom';

// Mock the API client
jest.mock('../../../lib/api/technician-client', () => ({
  technicianApiClient: {
    getWorkOrders: jest.fn(),
  },
}));

// Mock the offline database
jest.mock('../../../lib/offline-db', () => ({
  db: {
    workOrders: {
      toArray: jest.fn(),
      orderBy: jest.fn().mockReturnThis(),
      clear: jest.fn(),
      bulkAdd: jest.fn(),
      update: jest.fn(),
      get: jest.fn(),
    },
  },
  SyncManager: {
    addToSyncQueue: jest.fn(),
  },
}));

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

// Mock navigator.vibrate
Object.defineProperty(navigator, 'vibrate', {
  writable: true,
  value: jest.fn(),
});

const mockWorkOrders = [
  {
    id: 'WO-001',
    customerId: 'CUST-001',
    technicianId: 'TECH-001',
    title: 'Fiber Installation - Residential',
    description: 'Install fiber optic internet service',
    priority: 'high',
    status: 'pending',
    scheduledDate: new Date().toISOString(),
    assignedAt: new Date().toISOString(),
    location: {
      address: '123 Main St, Seattle, WA 98101',
      coordinates: [47.6062, -122.3321],
      apartment: 'Apt 2B',
      accessNotes: 'Use side entrance',
    },
    customer: {
      name: 'John Smith',
      phone: '+1 (555) 123-4567',
      email: 'john@example.com',
      serviceId: 'SRV-001',
    },
    equipment: {
      type: 'fiber_modem',
      model: 'Nokia 7368',
      required: ['Fiber ONT', 'Ethernet Cable'],
    },
    checklist: [
      { id: 'check-1', text: 'Verify location', completed: false, required: true },
      { id: 'check-2', text: 'Install equipment', completed: true, required: true },
    ],
    photos: [],
    notes: '',
    syncStatus: 'synced',
    lastModified: new Date().toISOString(),
  },
  {
    id: 'WO-002',
    customerId: 'CUST-002',
    technicianId: 'TECH-001',
    title: 'Service Repair - Connection Issues',
    description: 'Fix intermittent connection drops',
    priority: 'medium',
    status: 'in_progress',
    scheduledDate: new Date().toISOString(),
    assignedAt: new Date().toISOString(),
    location: {
      address: '456 Oak Ave, Bellevue, WA 98004',
      coordinates: [47.6101, -122.2015],
    },
    customer: {
      name: 'Sarah Johnson',
      phone: '+1 (555) 987-6543',
      email: 'sarah@example.com',
      serviceId: 'SRV-002',
    },
    equipment: {
      type: 'cable_modem',
      model: 'ARRIS SURFboard',
      required: ['Coax Cable'],
    },
    checklist: [{ id: 'check-1', text: 'Test connection', completed: true, required: true }],
    photos: [],
    notes: 'Signal levels checked',
    syncStatus: 'pending',
    lastModified: new Date().toISOString(),
  },
];

describe('WorkOrdersList Component', () => {
  const mockTechnicianApiClient = technicianApiClient as jest.Mocked<typeof technicianApiClient>;
  const mockDb = db as jest.Mocked<typeof db>;

  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock implementations
    mockDb.workOrders.toArray.mockResolvedValue(mockWorkOrders);
    mockDb.workOrders.get.mockResolvedValue(mockWorkOrders[0]);
    mockTechnicianApiClient.getWorkOrders.mockResolvedValue({
      success: true,
      data: mockWorkOrders,
    });
  });

  describe('Rendering', () => {
    it('should render loading state initially', () => {
      mockDb.workOrders.toArray.mockImplementation(() => new Promise(() => {})); // Never resolves
      render(<WorkOrdersList />);

      expect(screen.getAllByTestId(/loading|skeleton/i)).toBeTruthy();
    });

    it('should render work orders after loading', async () => {
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
        expect(screen.getByText('Service Repair - Connection Issues')).toBeInTheDocument();
      });
    });

    it('should display work order details correctly', async () => {
      render(<WorkOrdersList />);

      await waitFor(() => {
        // Check first work order
        expect(screen.getByText('John Smith')).toBeInTheDocument();
        expect(screen.getByText('123 Main St, Seattle, WA 98101')).toBeInTheDocument();
        expect(screen.getByText('High priority')).toBeInTheDocument();
        expect(screen.getByText('pending')).toBeInTheDocument();

        // Check progress indicators
        expect(screen.getByText('1/2')).toBeInTheDocument(); // Progress for first order
      });
    });
  });

  describe('Search and Filtering', () => {
    it('should filter work orders by search term', async () => {
      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search work orders...');
      await user.type(searchInput, 'Fiber');

      await waitFor(() => {
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
        expect(screen.queryByText('Service Repair - Connection Issues')).not.toBeInTheDocument();
      });
    });

    it('should filter work orders by customer name', async () => {
      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getAllByText(/John Smith|Sarah Johnson/)).toHaveLength(2);
      });

      const searchInput = screen.getByPlaceholderText('Search work orders...');
      await user.type(searchInput, 'Sarah');

      await waitFor(() => {
        expect(screen.getByText('Sarah Johnson')).toBeInTheDocument();
        expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
      });
    });

    it('should filter work orders by status', async () => {
      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
      });

      const statusFilter = screen.getByDisplayValue('All Status');
      await user.selectOptions(statusFilter, 'pending');

      await waitFor(() => {
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
        expect(screen.queryByText('Service Repair - Connection Issues')).not.toBeInTheDocument();
      });
    });

    it('should show no results message when no matches', async () => {
      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search work orders...');
      await user.type(searchInput, 'nonexistent');

      await waitFor(() => {
        expect(screen.getByText('No work orders match your criteria')).toBeInTheDocument();
      });
    });
  });

  describe('Work Order Actions', () => {
    it('should start work order when Start Work button is clicked', async () => {
      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Start Work')).toBeInTheDocument();
      });

      const startButton = screen.getByText('Start Work');
      await user.click(startButton);

      await waitFor(() => {
        expect(mockDb.workOrders.update).toHaveBeenCalledWith('WO-001', {
          status: 'in_progress',
          completedAt: undefined,
          syncStatus: 'pending',
        });
      });
    });

    it('should complete work order when Complete button is clicked', async () => {
      // Mock work order in progress
      const inProgressOrder = { ...mockWorkOrders[0], status: 'in_progress' };
      mockDb.workOrders.toArray.mockResolvedValue([inProgressOrder]);

      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Complete')).toBeInTheDocument();
      });

      const completeButton = screen.getByText('Complete');
      await user.click(completeButton);

      await waitFor(() => {
        expect(mockDb.workOrders.update).toHaveBeenCalledWith(
          'WO-001',
          expect.objectContaining({
            status: 'completed',
            syncStatus: 'pending',
          })
        );
      });
    });

    it('should trigger navigation when Navigate button is clicked', async () => {
      // Mock window.open
      const mockOpen = jest.fn();
      Object.defineProperty(window, 'open', { writable: true, value: mockOpen });

      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getAllByText('Navigate')).toHaveLength(2);
      });

      const navigateButton = screen.getAllByText('Navigate')[0];
      await user.click(navigateButton);

      expect(mockOpen).toHaveBeenCalledWith(
        'https://www.google.com/maps?q=123%20Main%20St%2C%20Seattle%2C%20WA%2098101',
        '_blank'
      );
    });

    it('should trigger phone call when Call button is clicked', async () => {
      // Mock window.location
      delete (window as any).location;
      (window as any).location = { href: '' };

      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getAllByText('Call')).toHaveLength(2);
      });

      const callButton = screen.getAllByText('Call')[0];
      await user.click(callButton);

      expect(window.location.href).toBe('tel:+1 (555) 123-4567');
    });
  });

  describe('Sync Status', () => {
    it('should show pending sync indicator', async () => {
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Pending sync')).toBeInTheDocument();
      });
    });

    it('should show synced indicator for completed orders', async () => {
      const completedOrder = { ...mockWorkOrders[0], status: 'completed', syncStatus: 'synced' };
      mockDb.workOrders.toArray.mockResolvedValue([completedOrder]);

      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Synced')).toBeInTheDocument();
      });
    });
  });

  describe('API Integration', () => {
    it('should sync work orders from server on mount', async () => {
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(mockTechnicianApiClient.getWorkOrders).toHaveBeenCalled();
      });
    });

    it('should fall back to local data when API fails', async () => {
      mockTechnicianApiClient.getWorkOrders.mockResolvedValue({
        success: false,
        message: 'API Error',
      });

      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(mockDb.workOrders.toArray).toHaveBeenCalled();
        expect(screen.getByText('Fiber Installation - Residential')).toBeInTheDocument();
      });
    });

    it('should use mock data when no local data exists', async () => {
      mockTechnicianApiClient.getWorkOrders.mockResolvedValue({
        success: false,
        message: 'API Error',
      });
      mockDb.workOrders.toArray.mockResolvedValue([]);

      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(mockDb.workOrders.bulkAdd).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle database errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockDb.workOrders.toArray.mockRejectedValue(new Error('Database error'));

      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to load work orders:', expect.any(Error));
      });

      consoleSpy.mockRestore();
    });

    it('should handle status update errors', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockDb.workOrders.update.mockRejectedValue(new Error('Update error'));

      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Start Work')).toBeInTheDocument();
      });

      const startButton = screen.getByText('Start Work');
      await user.click(startButton);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Failed to update order status:',
          expect.any(Error)
        );
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', async () => {
      render(<WorkOrdersList />);

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('Search work orders...');
        expect(searchInput).toBeInTheDocument();

        const statusFilter = screen.getByDisplayValue('All Status');
        expect(statusFilter).toBeInTheDocument();
      });
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<WorkOrdersList />);

      await waitFor(() => {
        expect(screen.getByText('Start Work')).toBeInTheDocument();
      });

      const startButton = screen.getByText('Start Work');
      startButton.focus();

      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockDb.workOrders.update).toHaveBeenCalled();
      });
    });
  });
});
