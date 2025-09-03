/**
 * Dispatch Dashboard Component Tests
 *
 * Comprehensive testing of the dispatch dashboard interface including
 * technician management, work order assignment, and intelligent dispatch.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

import DispatchDashboard from '../../src/components/field-operations/DispatchDashboard';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(() => 'mock-token'),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Sample data
const mockSummary = {
  date: '2024-01-15',
  work_orders: {
    total: 12,
    by_status: {
      scheduled: 3,
      in_progress: 4,
      completed: 5,
    },
    completed_today: 5,
    in_progress: 4,
    overdue: 1,
  },
  technicians: {
    total: 8,
    available: 5,
    on_job: 3,
    off_duty: 0,
  },
};

const mockTechnicians = [
  {
    id: 'tech1',
    full_name: 'John Smith',
    email: 'john@company.com',
    phone: '555-0123',
    skill_level: 'senior',
    current_status: 'available',
    is_available: true,
    current_workload: 25,
    jobs_completed_today: 2,
    average_job_rating: 4.8,
    current_location: {
      latitude: 40.7128,
      longitude: -74.006,
    },
    last_active: '2024-01-15T10:30:00Z',
  },
  {
    id: 'tech2',
    full_name: 'Alice Johnson',
    email: 'alice@company.com',
    phone: '555-0456',
    skill_level: 'expert',
    current_status: 'on_job',
    is_available: false,
    current_workload: 75,
    jobs_completed_today: 1,
    average_job_rating: 4.9,
    last_active: '2024-01-15T09:15:00Z',
  },
];

const mockWorkOrders = [
  {
    id: 'wo1',
    work_order_number: '20240115-0001',
    title: 'Fiber Installation',
    work_order_type: 'installation',
    status: 'scheduled',
    priority: 'high',
    customer_name: 'Jane Doe',
    customer_phone: '555-7890',
    service_address: '123 Main St, Anytown, ST 12345',
    scheduled_date: '2024-01-15',
    technician: null,
    progress_percentage: 0,
    is_overdue: false,
    estimated_duration: 120,
    created_at: '2024-01-15T08:00:00Z',
  },
  {
    id: 'wo2',
    work_order_number: '20240115-0002',
    title: 'Service Repair',
    work_order_type: 'repair',
    status: 'in_progress',
    priority: 'urgent',
    customer_name: 'Bob Wilson',
    service_address: '456 Oak Ave, Anytown, ST 12345',
    technician: mockTechnicians[0],
    progress_percentage: 60,
    is_overdue: false,
    estimated_duration: 90,
    created_at: '2024-01-15T07:30:00Z',
  },
];

describe('DispatchDashboard', () => {
  beforeEach(() => {
    mockFetch.mockClear();

    // Default mock responses
    mockFetch.mockImplementation((url) => {
      if (url.includes('dashboard/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes('technicians')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTechnicians),
        });
      }
      if (url.includes('work-orders')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockWorkOrders),
        });
      }
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail: 'Not found' }),
      });
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders dashboard header and summary cards', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Field Operations Dispatch')).toBeInTheDocument();
    });

    // Check summary cards
    expect(screen.getByText("Today's Work Orders")).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument(); // Total work orders
    expect(screen.getByText('5 completed')).toBeInTheDocument();

    expect(screen.getByText('Available Technicians')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // Available count
    expect(screen.getByText('of 8 total')).toBeInTheDocument();

    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument(); // In progress count

    expect(screen.getByText('Overdue Jobs')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // Overdue count
  });

  test('displays technician list with status and details', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Field Technicians')).toBeInTheDocument();
    });

    // Check technician details
    expect(screen.getByText('John Smith')).toBeInTheDocument();
    expect(screen.getByText('senior')).toBeInTheDocument();
    expect(screen.getByText('available')).toBeInTheDocument();
    expect(screen.getByText('75% capacity')).toBeInTheDocument(); // 100 - 25 workload
    expect(screen.getByText('2 jobs today')).toBeInTheDocument();
    expect(screen.getByText('★ 4.8')).toBeInTheDocument();

    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    expect(screen.getByText('expert')).toBeInTheDocument();
    expect(screen.getByText('on job')).toBeInTheDocument();
    expect(screen.getByText('1 jobs today')).toBeInTheDocument();
  });

  test('displays unassigned work orders with assignment options', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Unassigned Work Orders')).toBeInTheDocument();
    });

    // Check work order details (only unassigned should show)
    expect(screen.getByText('20240115-0001')).toBeInTheDocument();
    expect(screen.getByText('Fiber Installation')).toBeInTheDocument();
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('123 Main St, Anytown, ST 12345')).toBeInTheDocument();

    // Check assignment buttons
    expect(screen.getByText('Auto Assign')).toBeInTheDocument();
    expect(screen.getByText('Manual')).toBeInTheDocument();

    // Work order with technician assigned should not appear in unassigned list
    expect(screen.queryByText('20240115-0002')).not.toBeInTheDocument();
  });

  test('handles intelligent dispatch successfully', async () => {
    const user = userEvent.setup();

    mockFetch.mockImplementationOnce((url) => {
      if (url.includes('dispatch/intelligent')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'tech1',
              full_name: 'John Smith',
            }),
        });
      }
      return mockFetch(url);
    });

    // Mock alert
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Auto Assign')).toBeInTheDocument();
    });

    // Click auto assign button
    await user.click(screen.getByText('Auto Assign'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/field-operations/work-orders/wo1/dispatch/intelligent',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-token',
          }),
        })
      );
    });

    expect(alertSpy).toHaveBeenCalledWith('Work order successfully assigned to John Smith');

    alertSpy.mockRestore();
  });

  test('handles emergency dispatch with confirmation', async () => {
    const user = userEvent.setup();

    // Update mock data to include emergency work order
    const emergencyWorkOrder = {
      ...mockWorkOrders[0],
      priority: 'emergency',
    };

    mockFetch.mockImplementation((url) => {
      if (url.includes('work-orders')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([emergencyWorkOrder, mockWorkOrders[1]]),
        });
      }
      if (url.includes('dispatch/emergency')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'tech1',
              full_name: 'John Smith',
            }),
        });
      }
      return mockFetch(url);
    });

    // Mock confirm and alert
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Emergency')).toBeInTheDocument();
    });

    // Click emergency dispatch button
    await user.click(screen.getByText('Emergency'));

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith(
        'This will immediately dispatch the nearest available technician. Continue?'
      );
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/field-operations/work-orders/wo1/dispatch/emergency',
      expect.objectContaining({
        method: 'POST',
      })
    );

    expect(alertSpy).toHaveBeenCalledWith('Emergency dispatch successful! Assigned to John Smith');

    confirmSpy.mockRestore();
    alertSpy.mockRestore();
  });

  test('handles dispatch errors gracefully', async () => {
    const user = userEvent.setup();

    mockFetch.mockImplementationOnce((url) => {
      if (url.includes('dispatch/intelligent')) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ detail: 'No available technicians' }),
        });
      }
      return mockFetch(url);
    });

    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Auto Assign')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Auto Assign'));

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('Dispatch failed: No available technicians');
    });

    alertSpy.mockRestore();
  });

  test('refreshes data when refresh button is clicked', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    // Clear previous calls
    mockFetch.mockClear();

    // Click refresh
    await user.click(screen.getByText('Refresh'));

    await waitFor(() => {
      // Should make all data loading calls again
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/field-operations/dashboard/summary',
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/field-operations/technicians',
        expect.any(Object)
      );
    });
  });

  test('handles technician selection', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('John Smith')).toBeInTheDocument();
    });

    // Click on technician
    await user.click(screen.getByText('John Smith'));

    // Should highlight selected technician (check for blue background class)
    const technicianRow = screen.getByText('John Smith').closest('div[role="button"], div');
    expect(technicianRow).toHaveClass('bg-blue-50');
  });

  test('displays loading state initially', () => {
    render(<DispatchDashboard />);

    expect(screen.getByText('Loading dispatch dashboard...')).toBeInTheDocument();
    expect(screen.getByRole('generic', { hidden: true })).toHaveClass('animate-spin');
  });

  test('displays error state when data loading fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Error: Network error')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  test('route optimization section is present', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Route Optimization')).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        'Optimize technician routes to minimize travel time and maximize efficiency.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText('Optimize All Routes')).toBeInTheDocument();
    expect(screen.getByText('View Route Analytics')).toBeInTheDocument();
  });

  test('displays work order priority indicators correctly', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      // Should show priority indicators (colored dots or icons)
      expect(screen.getByText('20240115-0001')).toBeInTheDocument();
    });

    // Check that high priority work order has appropriate styling
    const workOrderElement = screen.getByText('20240115-0001').closest('div');
    expect(workOrderElement).toBeInTheDocument();
  });

  test('handles auto-refresh every 30 seconds', async () => {
    jest.useFakeTimers();

    await act(async () => {
      render(<DispatchDashboard />);
    });

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Field Operations Dispatch')).toBeInTheDocument();
    });

    // Clear initial calls
    mockFetch.mockClear();

    // Fast-forward 30 seconds
    act(() => {
      jest.advanceTimersByTime(30000);
    });

    await waitFor(() => {
      // Should have made refresh calls
      expect(mockFetch).toHaveBeenCalled();
    });

    jest.useRealTimers();
  });
});

// Performance tests
describe('DispatchDashboard Performance', () => {
  test('renders within acceptable time', async () => {
    const startTime = performance.now();

    await act(async () => {
      render(<DispatchDashboard />);
    });

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should render within 100ms
    expect(renderTime).toBeLessThan(100);
  });

  test('handles large datasets efficiently', async () => {
    // Mock large dataset
    const largeTechnicianList = Array.from({ length: 50 }, (_, i) => ({
      id: `tech${i}`,
      full_name: `Technician ${i}`,
      email: `tech${i}@company.com`,
      phone: `555-${i.toString().padStart(4, '0')}`,
      skill_level: 'intermediate',
      current_status: i % 2 === 0 ? 'available' : 'on_job',
      is_available: i % 2 === 0,
      current_workload: Math.floor(Math.random() * 100),
      jobs_completed_today: Math.floor(Math.random() * 5),
      average_job_rating: 3 + Math.random() * 2,
    }));

    const largeWorkOrderList = Array.from({ length: 30 }, (_, i) => ({
      id: `wo${i}`,
      work_order_number: `20240115-${i.toString().padStart(4, '0')}`,
      title: `Work Order ${i}`,
      work_order_type: 'installation',
      status: 'scheduled',
      priority: 'normal',
      customer_name: `Customer ${i}`,
      service_address: `${i} Test Street`,
      technician: null,
      progress_percentage: 0,
      is_overdue: false,
    }));

    mockFetch.mockImplementation((url) => {
      if (url.includes('technicians')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(largeTechnicianList),
        });
      }
      if (url.includes('work-orders')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(largeWorkOrderList),
        });
      }
      return mockFetch(url);
    });

    const startTime = performance.now();

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Field Technicians')).toBeInTheDocument();
    });

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should still render efficiently with large datasets
    expect(renderTime).toBeLessThan(200);
  });
});

// Accessibility tests
describe('DispatchDashboard Accessibility', () => {
  test('has proper heading hierarchy', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Field Operations Dispatch'
      );
      expect(screen.getAllByRole('heading', { level: 3 }).length).toBeGreaterThan(0);
    });
  });

  test('has proper button labels and accessibility', async () => {
    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      const refreshButton = screen.getByText('Refresh');
      expect(refreshButton).toBeInTheDocument();
      expect(refreshButton.closest('button')).toHaveAttribute('type', 'button');
    });
  });

  test('supports keyboard navigation', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<DispatchDashboard />);
    });

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    const refreshButton = screen.getByText('Refresh');

    // Focus the button
    await user.tab();

    // Should be focusable
    expect(document.activeElement).toBe(refreshButton.closest('button'));
  });
});
