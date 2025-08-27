/**
 * Unit tests for DataTable component
 */
import { render, screen, waitFor } from '../../../utils/test-utils';
import { DataTable, Column } from '../DataTable';

interface TestData {
  id: number;
  name: string;
  status: string;
  date: string;
}

const mockData: TestData[] = [
  { id: 1, name: 'John Doe', status: 'active', date: '2024-01-01' },
  { id: 2, name: 'Jane Smith', status: 'inactive', date: '2024-01-02' },
  { id: 3, name: 'Bob Johnson', status: 'active', date: '2024-01-03' },
];

const defaultColumns: Column<TestData>[] = [
  { key: 'id', title: 'ID' },
  { key: 'name', title: 'Name', sortable: true },
  { key: 'status', title: 'Status' },
  { key: 'date', title: 'Date', sortable: true },
];

describe('DataTable', () => {
  describe('Rendering', () => {
    it('renders table with data', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Johnson')).toBeInTheDocument();
    });

    it('renders column headers', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      expect(screen.getByText('ID')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Date')).toBeInTheDocument();
    });

    it('renders empty state when no data', () => {
      render(
        <DataTable 
          data={[]} 
          columns={defaultColumns}
          emptyMessage="No records found"
        />
      );
      
      expect(screen.getByText('No records found')).toBeInTheDocument();
    });

    it('renders loading state', () => {
      render(
        <DataTable 
          data={[]} 
          columns={defaultColumns}
          loading={true}
        />
      );
      
      expect(screen.getByText('Loading data...')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
    });
  });

  describe('Search Functionality', () => {
    it('shows search input when searchable=true', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
          searchable={true}
        />
      );
      
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
    });

    it('hides search input when searchable=false', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
          searchable={false}
        />
      );
      
      expect(screen.queryByPlaceholderText('Search...')).not.toBeInTheDocument();
    });

    it('filters data based on search term', async () => {
      const { user } = render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
          searchable={true}
        />
      );
      
      const searchInput = screen.getByPlaceholderText('Search...');
      await user.type(searchInput, 'John');
      
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
        expect(screen.queryByText('Bob Johnson')).not.toBeInTheDocument();
      });
    });

    it('shows filtered result count', async () => {
      const { user } = render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
          searchable={true}
        />
      );
      
      const searchInput = screen.getByPlaceholderText('Search...');
      await user.type(searchInput, 'active');
      
      await waitFor(() => {
        expect(screen.getByText(/Showing 2 of 3 results for "active"/)).toBeInTheDocument();
      });
    });
  });

  describe('Sorting', () => {
    it('shows sort indicators for sortable columns', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      const nameHeader = screen.getByText('Name').closest('th');
      expect(nameHeader).toHaveClass('cursor-pointer');
    });

    it('sorts data when clicking sortable column header', async () => {
      const { user } = render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      const nameHeader = screen.getByText('Name').closest('th');
      await user.click(nameHeader!);
      
      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        // First row is header, so data starts from index 1
        expect(rows[1]).toHaveTextContent('Bob Johnson'); // Alphabetically first
      });
    });

    it('toggles sort direction on repeated clicks', async () => {
      const { user } = render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      const nameHeader = screen.getByText('Name').closest('th');
      
      // Click once for ascending
      await user.click(nameHeader!);
      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        expect(rows[1]).toHaveTextContent('Bob Johnson');
      });
      
      // Click again for descending
      await user.click(nameHeader!);
      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        expect(rows[1]).toHaveTextContent('John Doe'); // Alphabetically last
      });
    });
  });

  describe('Custom Rendering', () => {
    it('uses custom render function when provided', () => {
      const customColumns: Column<TestData>[] = [
        { 
          key: 'name', 
          title: 'Name',
          render: (value) => <strong data-testid="custom-name">{value}</strong>
        },
        {
          key: 'status',
          title: 'Status',
          render: (value) => (
            <span className={`status-${value}`} data-testid="custom-status">
              {value.toUpperCase()}
            </span>
          )
        }
      ];

      render(
        <DataTable 
          data={mockData} 
          columns={customColumns}
        />
      );
      
      expect(screen.getByTestId('custom-name')).toHaveTextContent('John Doe');
      expect(screen.getByTestId('custom-status')).toHaveTextContent('ACTIVE');
      expect(screen.getByTestId('custom-status')).toHaveClass('status-active');
    });
  });

  describe('Accessibility', () => {
    it('has proper table structure', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('columnheader')).toHaveLength(4);
      expect(screen.getAllByRole('row')).toHaveLength(4); // 1 header + 3 data rows
    });

    it('marks sortable columns as clickable', () => {
      render(
        <DataTable 
          data={mockData} 
          columns={defaultColumns}
        />
      );
      
      const nameHeader = screen.getByText('Name').closest('th');
      expect(nameHeader).toHaveClass('cursor-pointer');
      
      const idHeader = screen.getByText('ID').closest('th');
      expect(idHeader).not.toHaveClass('cursor-pointer');
    });
  });

  describe('Performance', () => {
    it('handles large datasets efficiently', () => {
      // Create a large dataset
      const largeData = Array.from({ length: 1000 }, (_, i) => ({
        id: i + 1,
        name: `User ${i + 1}`,
        status: i % 2 === 0 ? 'active' : 'inactive',
        date: `2024-01-${String((i % 30) + 1).padStart(2, '0')}`,
      }));

      const startTime = performance.now();
      
      render(
        <DataTable 
          data={largeData} 
          columns={defaultColumns}
        />
      );
      
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      // Should render within reasonable time (less than 100ms)
      expect(renderTime).toBeLessThan(100);
    });
  });

  describe('Error Handling', () => {
    it('handles malformed data gracefully', () => {
      const malformedData = [
        { id: 1, name: 'John', status: null, date: undefined },
        { id: 2, name: null, status: 'active' },
        { id: 3 }, // Missing fields
      ] as TestData[];

      render(
        <DataTable 
          data={malformedData} 
          columns={defaultColumns}
        />
      );
      
      // Should not crash and render what it can
      expect(screen.getByText('John')).toBeInTheDocument();
    });
  });
});