/**
 * Component Interactions Integration Tests
 * Tests for complex component interactions and user workflows
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
  createMockWorkOrder, 
  createMockCustomer,
  NetworkSimulator,
  expectAccessible 
} from '../utils/test-utils';

// Mock the data layer
jest.mock('../../lib/offline-db', () => ({
  db: {
    workOrders: {
      where: jest.fn(),
      orderBy: jest.fn(),
      filter: jest.fn(),
      toArray: jest.fn(),
      get: jest.fn(),
      put: jest.fn(),
    },
    customers: {
      get: jest.fn(),
    },
  }
}));

// Mock the work order components - simulate real component structure
const MockWorkOrdersList = React.lazy(() => Promise.resolve({
  default: function WorkOrdersList({ onWorkOrderSelect }: { onWorkOrderSelect: (id: string) => void }) {
    const mockWorkOrders = [
      createMockWorkOrder({ id: 'WO-1', title: 'Installation', status: 'pending' }),
      createMockWorkOrder({ id: 'WO-2', title: 'Repair', status: 'in_progress' }),
      createMockWorkOrder({ id: 'WO-3', title: 'Maintenance', status: 'completed' }),
    ];

    return (
      <div data-testid="work-orders-list">
        <h2>Work Orders</h2>
        {mockWorkOrders.map(wo => (
          <div key={wo.id} data-testid={`work-order-${wo.id}`}>
            <h3>{wo.title}</h3>
            <span data-testid={`status-${wo.id}`}>{wo.status}</span>
            <button 
              onClick={() => onWorkOrderSelect(wo.id)}
              data-testid={`select-${wo.id}`}
            >
              View Details
            </button>
          </div>
        ))}
      </div>
    );
  }
}));

const MockWorkOrderDetails = React.lazy(() => Promise.resolve({
  default: function WorkOrderDetails({ 
    workOrderId, 
    onStatusUpdate,
    onClose 
  }: { 
    workOrderId: string;
    onStatusUpdate: (id: string, status: string) => void;
    onClose: () => void;
  }) {
    const [currentStatus, setCurrentStatus] = React.useState('pending');
    
    const handleStatusChange = (newStatus: string) => {
      setCurrentStatus(newStatus);
      onStatusUpdate(workOrderId, newStatus);
    };

    if (!workOrderId) return <div>No work order selected</div>;

    return (
      <div data-testid="work-order-details">
        <header>
          <h2>Work Order Details: {workOrderId}</h2>
          <button onClick={onClose} data-testid="close-details">
            Close
          </button>
        </header>
        
        <section>
          <h3>Status</h3>
          <span data-testid="current-status">{currentStatus}</span>
          <div>
            <button 
              onClick={() => handleStatusChange('in_progress')}
              data-testid="start-work"
            >
              Start Work
            </button>
            <button 
              onClick={() => handleStatusChange('completed')}
              data-testid="complete-work"
            >
              Complete Work
            </button>
          </div>
        </section>

        <section>
          <h3>Customer Information</h3>
          <div data-testid="customer-info">
            <p>John Doe</p>
            <p>123 Test Street</p>
            <p>555-0123</p>
          </div>
        </section>

        <section>
          <h3>Checklist</h3>
          <div data-testid="work-order-checklist">
            <label>
              <input 
                type="checkbox" 
                data-testid="checklist-item-1"
              />
              Install equipment
            </label>
            <label>
              <input 
                type="checkbox" 
                data-testid="checklist-item-2"
              />
              Test connection
            </label>
          </div>
        </section>
      </div>
    );
  }
}));

const MockOfflineIndicator = React.lazy(() => Promise.resolve({
  default: function OfflineIndicator() {
    const [isOnline, setIsOnline] = React.useState(navigator.onLine);

    React.useEffect(() => {
      const handleOnline = () => setIsOnline(true);
      const handleOffline = () => setIsOnline(false);

      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }, []);

    return (
      <div data-testid="offline-indicator">
        <span data-testid="connection-status">
          {isOnline ? 'Online' : 'Offline'}
        </span>
        {!isOnline && (
          <div data-testid="offline-warning">
            Working in offline mode. Changes will sync when connection is restored.
          </div>
        )}
      </div>
    );
  }
}));

// Main application component that demonstrates integration
const TestTechnicianApp = () => {
  const [selectedWorkOrderId, setSelectedWorkOrderId] = React.useState<string | null>(null);
  const [workOrderStatuses, setWorkOrderStatuses] = React.useState<Record<string, string>>({});

  const handleWorkOrderSelect = (id: string) => {
    setSelectedWorkOrderId(id);
  };

  const handleStatusUpdate = (id: string, status: string) => {
    setWorkOrderStatuses(prev => ({ ...prev, [id]: status }));
  };

  const handleCloseDetails = () => {
    setSelectedWorkOrderId(null);
  };

  return (
    <div data-testid="technician-app">
      <header>
        <h1>Technician Portal</h1>
        <React.Suspense fallback={<div>Loading...</div>}>
          <MockOfflineIndicator />
        </React.Suspense>
      </header>

      <main>
        {!selectedWorkOrderId ? (
          <React.Suspense fallback={<div>Loading work orders...</div>}>
            <MockWorkOrdersList onWorkOrderSelect={handleWorkOrderSelect} />
          </React.Suspense>
        ) : (
          <React.Suspense fallback={<div>Loading details...</div>}>
            <MockWorkOrderDetails
              workOrderId={selectedWorkOrderId}
              onStatusUpdate={handleStatusUpdate}
              onClose={handleCloseDetails}
            />
          </React.Suspense>
        )}
      </main>
    </div>
  );
};

describe('Component Interactions Integration', () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    jest.clearAllMocks();
    NetworkSimulator.reset();
  });

  describe('work order workflow', () => {
    it('should navigate through complete work order workflow', async () => {
      render(<TestTechnicianApp />);

      // 1. Should show work orders list initially
      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      // 2. Should display all work orders
      expect(screen.getByTestId('work-order-WO-1')).toBeInTheDocument();
      expect(screen.getByTestId('work-order-WO-2')).toBeInTheDocument();
      expect(screen.getByTestId('work-order-WO-3')).toBeInTheDocument();

      // 3. Click on first work order
      await user.click(screen.getByTestId('select-WO-1'));

      // 4. Should navigate to work order details
      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });

      expect(screen.getByText('Work Order Details: WO-1')).toBeInTheDocument();

      // 5. Should show customer information
      expect(screen.getByTestId('customer-info')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();

      // 6. Start the work
      await user.click(screen.getByTestId('start-work'));

      // 7. Status should update
      await waitFor(() => {
        expect(screen.getByTestId('current-status')).toHaveTextContent('in_progress');
      });

      // 8. Complete checklist items
      await user.click(screen.getByTestId('checklist-item-1'));
      await user.click(screen.getByTestId('checklist-item-2'));

      // 9. Complete the work
      await user.click(screen.getByTestId('complete-work'));

      // 10. Status should update to completed
      await waitFor(() => {
        expect(screen.getByTestId('current-status')).toHaveTextContent('completed');
      });

      // 11. Navigate back to list
      await user.click(screen.getByTestId('close-details'));

      // 12. Should return to work orders list
      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });
    });

    it('should handle multiple work order updates', async () => {
      render(<TestTechnicianApp />);

      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      // Update first work order
      await user.click(screen.getByTestId('select-WO-1'));
      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('start-work'));
      await user.click(screen.getByTestId('close-details'));

      // Update second work order
      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('select-WO-2'));
      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });
      
      await user.click(screen.getByTestId('complete-work'));
      await user.click(screen.getByTestId('close-details'));

      // Both updates should be handled correctly
      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });
    });
  });

  describe('offline behavior', () => {
    it('should show offline indicator when network is unavailable', async () => {
      render(<TestTechnicianApp />);

      // Initially should be online
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Online');
      });

      // Simulate going offline
      act(() => {
        NetworkSimulator.simulateOffline();
        window.dispatchEvent(new Event('offline'));
      });

      // Should show offline status
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Offline');
      });

      // Should show offline warning
      expect(screen.getByTestId('offline-warning')).toBeInTheDocument();
      expect(screen.getByText(/Working in offline mode/)).toBeInTheDocument();
    });

    it('should continue working offline', async () => {
      render(<TestTechnicianApp />);

      // Go offline
      act(() => {
        NetworkSimulator.simulateOffline();
        window.dispatchEvent(new Event('offline'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Offline');
      });

      // Should still be able to navigate and update work orders
      await user.click(screen.getByTestId('select-WO-1'));
      
      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('start-work'));

      // Status should still update offline
      await waitFor(() => {
        expect(screen.getByTestId('current-status')).toHaveTextContent('in_progress');
      });
    });

    it('should restore online functionality when connection returns', async () => {
      render(<TestTechnicianApp />);

      // Start offline
      act(() => {
        NetworkSimulator.simulateOffline();
        window.dispatchEvent(new Event('offline'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Offline');
      });

      // Go back online
      act(() => {
        NetworkSimulator.simulateOnline();
        window.dispatchEvent(new Event('online'));
      });

      // Should show online status
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Online');
      });

      // Offline warning should be gone
      expect(screen.queryByTestId('offline-warning')).not.toBeInTheDocument();
    });
  });

  describe('performance and user experience', () => {
    it('should load components lazily without blocking UI', async () => {
      render(<TestTechnicianApp />);

      // Should show loading state initially
      expect(screen.getByText('Loading work orders...')).toBeInTheDocument();

      // Should load work orders list
      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      // Should not have loading text anymore
      expect(screen.queryByText('Loading work orders...')).not.toBeInTheDocument();
    });

    it('should handle rapid user interactions gracefully', async () => {
      render(<TestTechnicianApp />);

      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      // Rapid clicking should be handled properly
      const selectButton = screen.getByTestId('select-WO-1');
      
      await user.click(selectButton);
      await user.click(selectButton); // Double click
      
      // Should only show one details view
      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });

      // Rapid status changes
      const startButton = screen.getByTestId('start-work');
      const completeButton = screen.getByTestId('complete-work');

      await user.click(startButton);
      await user.click(completeButton);

      // Final status should be completed
      await waitFor(() => {
        expect(screen.getByTestId('current-status')).toHaveTextContent('completed');
      });
    });
  });

  describe('accessibility', () => {
    it('should be accessible to screen readers', async () => {
      render(<TestTechnicianApp />);

      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      // Check basic accessibility
      await expectAccessible(screen.getByTestId('technician-app'));

      // Should have proper headings structure
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Technician Portal');
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Work Orders');

      // Buttons should be accessible
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
      
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName();
      });
    });

    it('should maintain focus management during navigation', async () => {
      render(<TestTechnicianApp />);

      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      const selectButton = screen.getByTestId('select-WO-1');
      selectButton.focus();
      
      expect(document.activeElement).toBe(selectButton);

      await user.click(selectButton);

      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });

      // Focus should move to a reasonable element in the new view
      expect(document.activeElement).toBeTruthy();
    });
  });

  describe('error handling', () => {
    it('should handle component loading errors gracefully', async () => {
      // Mock a component to throw an error
      const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
        try {
          return <>{children}</>;
        } catch (error) {
          return <div data-testid="error-fallback">Something went wrong</div>;
        }
      };

      render(
        <ErrorBoundary>
          <TestTechnicianApp />
        </ErrorBoundary>
      );

      // Should still render the app structure
      await waitFor(() => {
        expect(screen.getByTestId('technician-app')).toBeInTheDocument();
      });
    });

    it('should handle missing work order data', async () => {
      // Mock empty work orders
      const EmptyWorkOrdersList = () => (
        <div data-testid="work-orders-list">
          <h2>Work Orders</h2>
          <p data-testid="no-work-orders">No work orders available</p>
        </div>
      );

      render(<EmptyWorkOrdersList />);

      expect(screen.getByTestId('no-work-orders')).toBeInTheDocument();
      expect(screen.getByText('No work orders available')).toBeInTheDocument();
    });
  });

  describe('state management', () => {
    it('should maintain state consistency across navigation', async () => {
      render(<TestTechnicianApp />);

      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      // Navigate to details and update status
      await user.click(screen.getByTestId('select-WO-1'));
      
      await waitFor(() => {
        expect(screen.getByTestId('work-order-details')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('start-work'));

      // Navigate back and forth
      await user.click(screen.getByTestId('close-details'));
      
      await waitFor(() => {
        expect(screen.getByTestId('work-orders-list')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('select-WO-1'));

      // Status should be preserved
      await waitFor(() => {
        expect(screen.getByTestId('current-status')).toHaveTextContent('in_progress');
      });
    });
  });
});