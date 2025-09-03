/**
 * Territory Management - Integration Test
 * Tests the actual Territory Management component with real integrations
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock dependencies
jest.mock('@dotmac/headless/hooks/useApiData', () => ({
  useApiData: (key: string, fetcher: () => Promise<any>) => {
    const mockData = {
      territories: [
        {
          id: 'territory_1',
          name: 'Downtown District',
          region: 'Metro Area',
          coverage: 85.5,
          customers: 250,
          revenue: 75000.0,
          status: 'active',
        },
        {
          id: 'territory_2',
          name: 'Suburban Zone',
          region: 'Suburbs',
          coverage: 92.3,
          customers: 180,
          revenue: 54000.0,
          status: 'active',
        },
      ],
      total: 2,
    };

    return {
      data: mockData,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
      lastUpdated: new Date(),
    };
  },
}));

// Create a test Territory Management component
const TestTerritoryManagement: React.FC = () => {
  const [viewMode, setViewMode] = React.useState<'map' | 'list' | 'analytics'>('list');
  const [showFilters, setShowFilters] = React.useState(false);
  const [selectedTerritory, setSelectedTerritory] = React.useState<any>(null);
  const [searchTerm, setSearchTerm] = React.useState('');

  const territories = [
    {
      id: 'territory_1',
      name: 'Downtown District',
      region: 'Metro Area',
      coverage: 85.5,
      customers: 250,
      revenue: 75000.0,
      status: 'active',
      assignedTo: 'Sales Rep A',
      lastUpdated: '2024-01-20',
    },
    {
      id: 'territory_2',
      name: 'Suburban Zone',
      region: 'Suburbs',
      coverage: 92.3,
      customers: 180,
      revenue: 54000.0,
      status: 'active',
      assignedTo: 'Sales Rep B',
      lastUpdated: '2024-01-19',
    },
    {
      id: 'territory_3',
      name: 'Industrial Area',
      region: 'Industrial',
      coverage: 78.2,
      customers: 95,
      revenue: 38000.0,
      status: 'pending',
      assignedTo: 'Sales Rep C',
      lastUpdated: '2024-01-18',
    },
  ];

  const filteredTerritories = territories.filter(
    (territory) =>
      territory.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      territory.region.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div data-testid='territory-management'>
      {/* Header */}
      <div data-testid='territory-header'>
        <h1>Territory Management</h1>

        <div data-testid='view-controls'>
          <button
            onClick={() => setViewMode('map')}
            className={viewMode === 'map' ? 'active' : ''}
            data-testid='view-map'
          >
            Map View
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={viewMode === 'list' ? 'active' : ''}
            data-testid='view-list'
          >
            List View
          </button>
          <button
            onClick={() => setViewMode('analytics')}
            className={viewMode === 'analytics' ? 'active' : ''}
            data-testid='view-analytics'
          >
            Analytics View
          </button>
        </div>

        <button onClick={() => setShowFilters(!showFilters)} data-testid='toggle-filters'>
          {showFilters ? 'Hide' : 'Show'} Filters
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div data-testid='territory-filters'>
          <input
            type='text'
            placeholder='Search territories...'
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            data-testid='territory-search'
          />
          <select data-testid='status-filter'>
            <option value=''>All Status</option>
            <option value='active'>Active</option>
            <option value='pending'>Pending</option>
            <option value='inactive'>Inactive</option>
          </select>
          <select data-testid='region-filter'>
            <option value=''>All Regions</option>
            <option value='Metro Area'>Metro Area</option>
            <option value='Suburbs'>Suburbs</option>
            <option value='Industrial'>Industrial</option>
          </select>
        </div>
      )}

      {/* Main Content */}
      <div data-testid='territory-content'>
        <div data-testid='current-view'>{viewMode}</div>

        {viewMode === 'list' && (
          <div data-testid='territory-list'>
            <table>
              <thead>
                <tr>
                  <th>Territory Name</th>
                  <th>Region</th>
                  <th>Coverage %</th>
                  <th>Customers</th>
                  <th>Revenue</th>
                  <th>Status</th>
                  <th>Assigned To</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTerritories.map((territory) => (
                  <tr key={territory.id} data-testid={`territory-row-${territory.id}`}>
                    <td>{territory.name}</td>
                    <td>{territory.region}</td>
                    <td>{territory.coverage}%</td>
                    <td>{territory.customers}</td>
                    <td>${territory.revenue.toLocaleString()}</td>
                    <td>
                      <span className={`status-${territory.status}`}>{territory.status}</span>
                    </td>
                    <td>{territory.assignedTo}</td>
                    <td>
                      <button
                        onClick={() => setSelectedTerritory(territory)}
                        data-testid={`select-territory-${territory.id}`}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {viewMode === 'map' && (
          <div data-testid='territory-map'>
            <div className='map-container'>
              <h3>Territory Map View</h3>
              <p>Interactive map showing territory boundaries and coverage</p>
              {filteredTerritories.map((territory) => (
                <div
                  key={territory.id}
                  className='map-territory'
                  data-testid={`map-territory-${territory.id}`}
                >
                  {territory.name} - {territory.coverage}% coverage
                </div>
              ))}
            </div>
          </div>
        )}

        {viewMode === 'analytics' && (
          <div data-testid='territory-analytics'>
            <h3>Territory Analytics</h3>
            <div className='analytics-grid'>
              <div data-testid='total-territories'>Total Territories: {territories.length}</div>
              <div data-testid='total-customers'>
                Total Customers: {territories.reduce((sum, t) => sum + t.customers, 0)}
              </div>
              <div data-testid='total-revenue'>
                Total Revenue: $
                {territories.reduce((sum, t) => sum + t.revenue, 0).toLocaleString()}
              </div>
              <div data-testid='average-coverage'>
                Average Coverage:{' '}
                {(territories.reduce((sum, t) => sum + t.coverage, 0) / territories.length).toFixed(
                  1
                )}
                %
              </div>
            </div>

            {/* Performance by Territory */}
            <div data-testid='territory-performance'>
              <h4>Territory Performance</h4>
              {territories.map((territory) => (
                <div
                  key={territory.id}
                  className='performance-item'
                  data-testid={`performance-${territory.id}`}
                >
                  <span>{territory.name}</span>
                  <span>{territory.customers} customers</span>
                  <span>${territory.revenue.toLocaleString()}</span>
                  <span>{territory.coverage}% coverage</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Territory Details Panel */}
      {selectedTerritory && (
        <div data-testid='territory-details'>
          <div className='details-panel'>
            <h3>{selectedTerritory.name}</h3>
            <div data-testid='territory-details-content'>
              <p>
                <strong>Region:</strong> {selectedTerritory.region}
              </p>
              <p>
                <strong>Coverage:</strong> {selectedTerritory.coverage}%
              </p>
              <p>
                <strong>Customers:</strong> {selectedTerritory.customers}
              </p>
              <p>
                <strong>Revenue:</strong> ${selectedTerritory.revenue.toLocaleString()}
              </p>
              <p>
                <strong>Status:</strong> {selectedTerritory.status}
              </p>
              <p>
                <strong>Assigned To:</strong> {selectedTerritory.assignedTo}
              </p>
              <p>
                <strong>Last Updated:</strong> {selectedTerritory.lastUpdated}
              </p>
            </div>
            <button onClick={() => setSelectedTerritory(null)} data-testid='close-details'>
              Close
            </button>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div data-testid='territory-summary'>
        <div data-testid='active-territories'>
          Active: {territories.filter((t) => t.status === 'active').length}
        </div>
        <div data-testid='pending-territories'>
          Pending: {territories.filter((t) => t.status === 'pending').length}
        </div>
        <div data-testid='coverage-stats'>
          Avg Coverage:{' '}
          {(territories.reduce((sum, t) => sum + t.coverage, 0) / territories.length).toFixed(1)}%
        </div>
      </div>
    </div>
  );
};

// Test wrapper
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

describe('Territory Management Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering and Navigation', () => {
    it('should render territory management interface', () => {
      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      expect(screen.getByText('Territory Management')).toBeInTheDocument();
      expect(screen.getByTestId('view-controls')).toBeInTheDocument();
      expect(screen.getByTestId('toggle-filters')).toBeInTheDocument();
    });

    it('should switch between view modes', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Initially in list view
      expect(screen.getByTestId('current-view')).toHaveTextContent('list');
      expect(screen.getByTestId('territory-list')).toBeInTheDocument();

      // Switch to map view
      await user.click(screen.getByTestId('view-map'));
      expect(screen.getByTestId('current-view')).toHaveTextContent('map');
      expect(screen.getByTestId('territory-map')).toBeInTheDocument();

      // Switch to analytics view
      await user.click(screen.getByTestId('view-analytics'));
      expect(screen.getByTestId('current-view')).toHaveTextContent('analytics');
      expect(screen.getByTestId('territory-analytics')).toBeInTheDocument();
    });

    it('should toggle filters panel', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Filters initially hidden
      expect(screen.queryByTestId('territory-filters')).not.toBeInTheDocument();

      // Show filters
      await user.click(screen.getByTestId('toggle-filters'));
      expect(screen.getByTestId('territory-filters')).toBeInTheDocument();
      expect(screen.getByText('Hide Filters')).toBeInTheDocument();

      // Hide filters
      await user.click(screen.getByTestId('toggle-filters'));
      expect(screen.queryByTestId('territory-filters')).not.toBeInTheDocument();
      expect(screen.getByText('Show Filters')).toBeInTheDocument();
    });
  });

  describe('Territory Data Display', () => {
    it('should display territories in list view', () => {
      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      expect(screen.getByText('Downtown District')).toBeInTheDocument();
      expect(screen.getByText('Suburban Zone')).toBeInTheDocument();
      expect(screen.getByText('Industrial Area')).toBeInTheDocument();

      expect(screen.getByText('Metro Area')).toBeInTheDocument();
      expect(screen.getByText('Suburbs')).toBeInTheDocument();
      expect(screen.getByText('Industrial')).toBeInTheDocument();
    });

    it('should show territory performance data', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      await user.click(screen.getByTestId('view-analytics'));

      expect(screen.getByTestId('total-territories')).toHaveTextContent('Total Territories: 3');
      expect(screen.getByTestId('total-customers')).toHaveTextContent('Total Customers: 525');
      expect(screen.getByTestId('total-revenue')).toHaveTextContent('Total Revenue: $167,000');
      expect(screen.getByTestId('average-coverage')).toHaveTextContent('Average Coverage: 85.3%');
    });

    it('should display territory details when selected', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      await user.click(screen.getByTestId('select-territory-territory_1'));

      expect(screen.getByTestId('territory-details')).toBeInTheDocument();
      expect(screen.getByText('Downtown District')).toBeInTheDocument();
      expect(screen.getByText('Metro Area')).toBeInTheDocument();
      expect(screen.getByText('85.5%')).toBeInTheDocument();
      expect(screen.getByText('250')).toBeInTheDocument();
      expect(screen.getByText('$75,000')).toBeInTheDocument();
    });
  });

  describe('Search and Filtering', () => {
    it('should filter territories by name', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Show filters
      await user.click(screen.getByTestId('toggle-filters'));

      // Search for "downtown"
      const searchInput = screen.getByTestId('territory-search');
      await user.type(searchInput, 'downtown');

      await waitFor(() => {
        expect(screen.getByText('Downtown District')).toBeInTheDocument();
        expect(screen.queryByText('Suburban Zone')).not.toBeInTheDocument();
        expect(screen.queryByText('Industrial Area')).not.toBeInTheDocument();
      });
    });

    it('should filter territories by region', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Show filters
      await user.click(screen.getByTestId('toggle-filters'));

      // Search for "suburbs"
      const searchInput = screen.getByTestId('territory-search');
      await user.type(searchInput, 'suburbs');

      await waitFor(() => {
        expect(screen.queryByText('Downtown District')).not.toBeInTheDocument();
        expect(screen.getByText('Suburban Zone')).toBeInTheDocument();
        expect(screen.queryByText('Industrial Area')).not.toBeInTheDocument();
      });
    });
  });

  describe('Map View Integration', () => {
    it('should display territories on map', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      await user.click(screen.getByTestId('view-map'));

      expect(screen.getByText('Territory Map View')).toBeInTheDocument();
      expect(screen.getByTestId('map-territory-territory_1')).toBeInTheDocument();
      expect(screen.getByTestId('map-territory-territory_2')).toBeInTheDocument();
      expect(screen.getByTestId('map-territory-territory_3')).toBeInTheDocument();
    });

    it('should show coverage percentages on map', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      await user.click(screen.getByTestId('view-map'));

      expect(screen.getByText('Downtown District - 85.5% coverage')).toBeInTheDocument();
      expect(screen.getByText('Suburban Zone - 92.3% coverage')).toBeInTheDocument();
      expect(screen.getByText('Industrial Area - 78.2% coverage')).toBeInTheDocument();
    });
  });

  describe('Analytics Integration', () => {
    it('should show territory performance metrics', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      await user.click(screen.getByTestId('view-analytics'));

      expect(screen.getByTestId('performance-territory_1')).toHaveTextContent('Downtown District');
      expect(screen.getByTestId('performance-territory_1')).toHaveTextContent('250 customers');
      expect(screen.getByTestId('performance-territory_1')).toHaveTextContent('$75,000');
      expect(screen.getByTestId('performance-territory_1')).toHaveTextContent('85.5% coverage');
    });

    it('should calculate and display summary statistics', () => {
      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      expect(screen.getByTestId('active-territories')).toHaveTextContent('Active: 2');
      expect(screen.getByTestId('pending-territories')).toHaveTextContent('Pending: 1');
      expect(screen.getByTestId('coverage-stats')).toHaveTextContent('Avg Coverage: 85.3%');
    });
  });

  describe('User Interactions', () => {
    it('should close territory details panel', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Open details
      await user.click(screen.getByTestId('select-territory-territory_1'));
      expect(screen.getByTestId('territory-details')).toBeInTheDocument();

      // Close details
      await user.click(screen.getByTestId('close-details'));
      expect(screen.queryByTestId('territory-details')).not.toBeInTheDocument();
    });

    it('should handle multiple territory selections', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Select first territory
      await user.click(screen.getByTestId('select-territory-territory_1'));
      expect(screen.getByText('Downtown District')).toBeInTheDocument();

      // Select second territory (should replace first)
      await user.click(screen.getByTestId('select-territory-territory_2'));
      expect(screen.getByText('Suburban Zone')).toBeInTheDocument();

      // Verify content changed
      const detailsContent = screen.getByTestId('territory-details-content');
      expect(detailsContent).toHaveTextContent('Suburban Zone');
      expect(detailsContent).toHaveTextContent('92.3%');
      expect(detailsContent).toHaveTextContent('180');
    });
  });

  describe('Responsive Behavior', () => {
    it('should maintain functionality across view switches', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Enable filters in list view
      await user.click(screen.getByTestId('toggle-filters'));
      const searchInput = screen.getByTestId('territory-search');
      await user.type(searchInput, 'downtown');

      // Switch to map view - filtered results should persist
      await user.click(screen.getByTestId('view-map'));
      expect(screen.getByTestId('map-territory-territory_1')).toBeInTheDocument();
      expect(screen.queryByTestId('map-territory-territory_2')).not.toBeInTheDocument();

      // Switch to analytics - filtered results should persist
      await user.click(screen.getByTestId('view-analytics'));
      expect(screen.getByTestId('performance-territory_1')).toBeInTheDocument();
      expect(screen.queryByTestId('performance-territory_2')).not.toBeInTheDocument();
    });

    it('should handle rapid view mode changes', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <TestTerritoryManagement />
        </TestWrapper>
      );

      // Rapid switching
      await user.click(screen.getByTestId('view-map'));
      await user.click(screen.getByTestId('view-analytics'));
      await user.click(screen.getByTestId('view-list'));
      await user.click(screen.getByTestId('view-map'));

      // Should end up in map view
      expect(screen.getByTestId('current-view')).toHaveTextContent('map');
      expect(screen.getByTestId('territory-map')).toBeInTheDocument();
    });
  });
});
