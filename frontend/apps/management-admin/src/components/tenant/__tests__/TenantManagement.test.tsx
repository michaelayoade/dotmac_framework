import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TenantManagement } from '../TenantManagement';
import { TenantStatus } from '@/types/tenant';

// Mock the API modules
jest.mock('@/lib/api', () => ({
  tenantApi: {
    list: jest.fn(),
    delete: jest.fn(),
    updateStatus: jest.fn(),
  },
  billingApi: {
    getUsage: jest.fn(),
  },
  monitoringApi: {
    health: jest.fn(),
  },
}));

jest.mock('@/lib/navigation', () => ({
  useAppNavigation: () => ({
    push: jest.fn(),
  }),
  routes: {
    tenants: {
      list: '/tenants',
      new: '/tenants/new',
      view: (id: string) => `/tenants/${id}`,
      edit: (id: string) => `/tenants/${id}/edit`,
    },
    monitoring: '/monitoring',
  },
}));

jest.mock('@/components/ui/Toast', () => ({
  useToast: () => ({
    success: jest.fn(),
    error: jest.fn(),
  }),
}));

// Mock @tanstack/react-query
jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(),
  useMutation: jest.fn(),
  useQueryClient: () => ({
    invalidateQueries: jest.fn(),
  }),
}));

const mockTenants = [
  {
    id: '1',
    name: 'Test Tenant 1',
    slug: 'test-tenant-1',
    status: TenantStatus.ACTIVE,
    plan: 'Basic',
    contactEmail: 'test1@example.com',
    contactPhone: '+1234567890',
    createdAt: '2023-01-01T00:00:00Z',
  },
  {
    id: '2',
    name: 'Test Tenant 2',
    slug: 'test-tenant-2',
    status: TenantStatus.PENDING,
    plan: 'Premium',
    contactEmail: 'test2@example.com',
    contactPhone: null,
    createdAt: '2023-01-02T00:00:00Z',
  },
];

const mockHealthData = {
  overall_status: 'healthy',
  services: {},
};

describe('TenantManagement', () => {
  const { useQuery, useMutation } = require('@tanstack/react-query');

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Setup default useQuery mock
    useQuery.mockImplementation(({ queryKey }) => {
      if (queryKey[0] === 'tenants') {
        return {
          data: {
            tenants: mockTenants,
            total: mockTenants.length,
            pages: 1,
          },
          isLoading: false,
          error: null,
        };
      }
      if (queryKey[0] === 'system-health') {
        return {
          data: mockHealthData,
          isLoading: false,
          error: null,
        };
      }
      return {
        data: null,
        isLoading: false,
        error: null,
      };
    });

    // Setup default useMutation mock
    useMutation.mockReturnValue({
      mutate: jest.fn(),
      mutateAsync: jest.fn(),
      isPending: false,
      error: null,
    });
  });

  it('renders tenant management component', () => {
    render(<TenantManagement />);

    expect(screen.getByText('Tenant Management')).toBeInTheDocument();
    expect(screen.getByText('Manage all tenant accounts and their configurations')).toBeInTheDocument();
  });

  it('displays stats cards when showStats is true', () => {
    render(<TenantManagement showStats={true} />);

    expect(screen.getByText('Total Tenants')).toBeInTheDocument();
    expect(screen.getByText('Active Tenants')).toBeInTheDocument();
    expect(screen.getByText('System Health')).toBeInTheDocument();
    expect(screen.getByText('Pending Setup')).toBeInTheDocument();
  });

  it('hides stats cards when showStats is false', () => {
    render(<TenantManagement showStats={false} />);

    expect(screen.queryByText('Total Tenants')).not.toBeInTheDocument();
    expect(screen.queryByText('Active Tenants')).not.toBeInTheDocument();
  });

  it('displays tenant list with proper data', () => {
    render(<TenantManagement />);

    expect(screen.getByText('Test Tenant 1')).toBeInTheDocument();
    expect(screen.getByText('test-tenant-1')).toBeInTheDocument();
    expect(screen.getByText('Test Tenant 2')).toBeInTheDocument();
    expect(screen.getByText('test-tenant-2')).toBeInTheDocument();
  });

  it('shows create button when showCreateButton is true', () => {
    render(<TenantManagement showCreateButton={true} />);

    expect(screen.getByText('Create Tenant')).toBeInTheDocument();
  });

  it('hides create button when showCreateButton is false', () => {
    render(<TenantManagement showCreateButton={false} />);

    expect(screen.queryByText('Create Tenant')).not.toBeInTheDocument();
  });

  it('handles search input changes', async () => {
    const user = userEvent.setup();
    render(<TenantManagement />);

    const searchInput = screen.getByPlaceholderText('Search tenants...');
    await user.type(searchInput, 'test search');

    expect(searchInput).toHaveValue('test search');
  });

  it('handles status filter changes', async () => {
    const user = userEvent.setup();
    render(<TenantManagement />);

    const statusFilter = screen.getByDisplayValue('All Statuses');
    await user.selectOptions(statusFilter, 'active');

    expect(statusFilter).toHaveValue('active');
  });

  it('displays loading spinner when data is loading', () => {
    useQuery.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });

    render(<TenantManagement />);

    expect(screen.getByTestId('loading-spinner') || screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays error message when fetch fails', () => {
    useQuery.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to fetch'),
    });

    render(<TenantManagement />);

    expect(screen.getByText('Failed to load tenants')).toBeInTheDocument();
  });

  it('displays no tenants message when list is empty', () => {
    useQuery.mockReturnValue({
      data: {
        tenants: [],
        total: 0,
        pages: 0,
      },
      isLoading: false,
      error: null,
    });

    render(<TenantManagement />);

    expect(screen.getByText('No tenants found')).toBeInTheDocument();
  });

  it('handles tenant deletion with confirmation', async () => {
    const mockDelete = jest.fn();
    useMutation.mockReturnValue({
      mutate: mockDelete,
      mutateAsync: jest.fn(),
      isPending: false,
      error: null,
    });

    // Mock window.confirm
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);

    render(<TenantManagement />);

    const deleteButtons = screen.getAllByTitle('Delete');
    fireEvent.click(deleteButtons[0]);

    expect(confirmSpy).toHaveBeenCalledWith(
      'Are you sure you want to delete tenant "Test Tenant 1"? This action cannot be undone.'
    );
    expect(mockDelete).toHaveBeenCalledWith('1');

    confirmSpy.mockRestore();
  });

  it('handles tenant status updates', async () => {
    const user = userEvent.setup();
    const mockUpdateStatus = jest.fn();

    useMutation.mockReturnValue({
      mutate: mockUpdateStatus,
      mutateAsync: jest.fn(),
      isPending: false,
      error: null,
    });

    render(<TenantManagement />);

    const statusSelects = screen.getAllByDisplayValue('Active');
    await user.selectOptions(statusSelects[0], TenantStatus.SUSPENDED);

    expect(mockUpdateStatus).toHaveBeenCalledWith({
      id: '1',
      status: TenantStatus.SUSPENDED,
    });
  });

  it('handles compact mode correctly', () => {
    render(<TenantManagement compact={true} />);

    expect(screen.getByText('Recent Tenants')).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Search tenants...')).not.toBeInTheDocument();
  });

  it('shows pagination when there are multiple pages', () => {
    useQuery.mockReturnValue({
      data: {
        tenants: mockTenants,
        total: 20,
        pages: 2,
      },
      isLoading: false,
      error: null,
    });

    render(<TenantManagement />);

    expect(screen.getByText('Previous')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
  });

  it('calculates stats correctly', () => {
    render(<TenantManagement showStats={true} />);

    // Total tenants
    expect(screen.getByText('2')).toBeInTheDocument();

    // Active tenants (1 active tenant)
    const activeCount = mockTenants.filter(t => t.status === TenantStatus.ACTIVE).length;
    expect(screen.getByText(activeCount.toString())).toBeInTheDocument();

    // Pending tenants (1 pending tenant)
    const pendingCount = mockTenants.filter(t => t.status === TenantStatus.PENDING).length;
    expect(screen.getByText(pendingCount.toString())).toBeInTheDocument();
  });

  it('handles view and edit actions', async () => {
    const mockPush = jest.fn();
    const { useAppNavigation } = require('@/lib/navigation');
    useAppNavigation.mockReturnValue({ push: mockPush });

    render(<TenantManagement />);

    const viewButtons = screen.getAllByTitle('View Details');
    const editButtons = screen.getAllByTitle('Edit');

    fireEvent.click(viewButtons[0]);
    expect(mockPush).toHaveBeenCalledWith('/tenants/1');

    fireEvent.click(editButtons[0]);
    expect(mockPush).toHaveBeenCalledWith('/tenants/1/edit');
  });
});
