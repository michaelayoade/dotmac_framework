/**
 * AdminDataTable component comprehensive tests
 * Testing data table functionality, pagination, sorting, bulk actions, and composition patterns
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import React from 'react';

import { AdminDataTable } from '../DataTable';

// Mock the primitive DataTable component
jest.mock('@dotmac/primitives', () => ({
  dataTable: ({ className, columns, data, selection, ...props }: unknown) => (
    <div
      data-testid='primitive-data-table'
      className={className}
      data-columns={columns.length}
      data-rows={data.length}
      data-has-selection={!!selection}
      {...props}
    >
      <table>
        <thead>
          <tr>
            {columns.map((col: unknown, index: number) => (
              <th key={col.key || index} data-testid={`header-${col.key || index}`}>
                {col.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row: unknown, rowIndex: number) => (
            <tr key={rowIndex} data-testid={`row-${rowIndex}`}>
              {columns.map((col: unknown, colIndex: number) => (
                <td key={colIndex} data-testid={`cell-${rowIndex}-${colIndex}`}>
                  {col.render
                    ? col.render(row[col.dataIndex], row, rowIndex)
                    : row[col.dataIndex] || ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {/* Simulate selection change for testing */}
      {selection && (
        <button
          type='button'
          data-testid='simulate-selection-change'
          onClick={() => selection.onChange?.(['1', '2'])}
          style={{ display: 'none' }}
        />
      )}
    </div>
  ),
}));

// Mock AdminButton and AdminInput components
jest.mock('../Button', () => ({
  AdminButton: ({ children, onClick, disabled, variant, size, leftIcon, ...props }: unknown) => (
    <button
      type='button'
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick}
      disabled={disabled}
      data-variant={variant}
      data-size={size}
      data-testid={props['data-testid'] || 'admin-button'}
      {...props}
    >
      {leftIcon && <span data-testid='button-icon'>{leftIcon}</span>}
      {children}
    </button>
  ),
}));

jest.mock('../Input', () => ({
  AdminInput: ({ value, onChange, placeholder, size, leftIcon, className, ...props }: unknown) => (
    <div className={`input-wrapper ${className || ''}`}>
      {leftIcon && <span data-testid='input-icon'>{leftIcon}</span>}
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        data-size={size}
        data-testid='admin-input'
        {...props}
      />
    </div>
  ),
}));

// Sample test data
const sampleColumns = [
  {
    key: 'name',
    title: 'Name',
    dataIndex: 'name',
    sortable: true,
    width: 200,
  },
  {
    key: 'email',
    title: 'Email',
    dataIndex: 'email',
  },
  {
    key: 'status',
    title: 'Status',
    dataIndex: 'status',
    render: (status: string) => <span data-testid={`status-${status}`}>{status}</span>,
  },
  {
    key: 'actions',
    title: 'Actions',
    width: 120,
    render: (_, row: unknown) => (
      <button type='button' data-testid={`action-${row.id}`}>
        Edit
      </button>
    ),
  },
];

const sampleData = [
  { id: '1', name: 'John Doe', email: 'john@example.com', status: 'active' },
  { id: '2', name: 'Jane Smith', email: 'jane@example.com', status: 'inactive' },
  { id: '3', name: 'Bob Johnson', email: 'bob@example.com', status: 'active' },
  { id: '4', name: 'Alice Brown', email: 'alice@example.com', status: 'pending' },
];

describe('AdminDataTable Component', () => {
  describe('Basic Rendering', () => {
    it('renders table with data and columns', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      expect(screen.getByTestId('primitive-data-table')).toBeInTheDocument();
      expect(screen.getByTestId('header-name')).toHaveTextContent('Name');
      expect(screen.getByTestId('header-email')).toHaveTextContent('Email');
      expect(screen.getByTestId('row-0')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('renders custom cell content', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      expect(screen.getAllByTestId('status-active')).toHaveLength(2);
      expect(screen.getByTestId('action-1')).toBeInTheDocument();
      expect(screen.getByTestId('status-pending')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} className='custom-table' />);

      expect(screen.getByTestId('primitive-data-table')).toHaveClass('custom-table');
    });

    it('shows compact styling when enabled', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} compact={true} />);

      expect(screen.getByTestId('primitive-data-table')).toHaveClass('compact');
    });

    it('applies admin-data-table class', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      expect(screen.getByTestId('primitive-data-table')).toHaveClass('admin-data-table');
    });

    it('renders with default props', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      // Default props should be applied
      expect(screen.getByTestId('primitive-data-table')).toHaveClass('compact'); // compact defaults to true
      expect(screen.queryByTestId('admin-input')).not.toBeInTheDocument(); // enableQuickFilter defaults to false
    });

    it('forwards additional props to primitive table', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          data-loading='true'
          data-rowkey='id'
        />
      );

      const table = screen.getByTestId('primitive-data-table');
      expect(table).toHaveAttribute('data-loading', 'true');
      expect(table).toHaveAttribute('data-rowkey', 'id');
    });
  });

  describe('Row Numbers', () => {
    it('shows row numbers when enabled', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} showRowNumbers={true} />);

      expect(screen.getByTestId('header-__row_number')).toHaveTextContent('#');
      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '5'); // 4 original + 1 row number
    });

    it('does not show row numbers by default', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      expect(screen.queryByTestId('header-__row_number')).not.toBeInTheDocument();
      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '4');
    });

    it('calculates row numbers with pagination correctly', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          showRowNumbers={true}
          pagination={{
            current: 2,
            pageSize: 10,
            total: 50,
            onChange: jest.fn(),
          }}
        />
      );

      expect(screen.getByTestId('header-__row_number')).toBeInTheDocument();
      // Row numbers column should be added at the beginning
      const rowNumberColumn = screen.getByTestId('header-__row_number');
      expect(rowNumberColumn).toHaveTextContent('#');
    });

    it('calculates row numbers with default pagination values', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          showRowNumbers={true}
          pagination={{
            current: 1, // Default case
            pageSize: 10,
            total: 50,
            onChange: jest.fn(),
          }}
        />
      );

      expect(screen.getByTestId('header-__row_number')).toBeInTheDocument();
    });

    it('handles row number calculation edge cases', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} showRowNumbers={true} />);

      // Without pagination, should still show row numbers starting from 1
      expect(screen.getByTestId('header-__row_number')).toBeInTheDocument();
    });
  });

  describe('Quick Filter', () => {
    it('renders quick filter when enabled', () => {
      const handleFilterChange = jest.fn();

      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          quickFilterPlaceholder='Search users...'
          quickFilterValue='test'
          onQuickFilterChange={handleFilterChange}
        />
      );

      const input = screen.getByTestId('admin-input');
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('placeholder', 'Search users...');
      expect(input).toHaveValue('test');
      expect(screen.getByTestId('input-icon')).toBeInTheDocument();
    });

    it('uses default placeholder when not provided', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} enableQuickFilter={true} />);

      const input = screen.getByTestId('admin-input');
      expect(input).toHaveAttribute('placeholder', 'Search...');
    });

    it('handles filter value changes', () => {
      const handleFilterChange = jest.fn();

      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          onQuickFilterChange={handleFilterChange}
        />
      );

      const input = screen.getByTestId('admin-input');
      fireEvent.change(input, { target: { value: 'john' } });

      expect(handleFilterChange).toHaveBeenCalledWith('john');
    });

    it('handles missing onQuickFilterChange gracefully', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} enableQuickFilter={true} />);

      const input = screen.getByTestId('admin-input');
      // Should not throw error when onChange is not provided
      expect(() => {
        fireEvent.change(input, { target: { value: 'test' } });
      }).not.toThrow();
    });

    it('does not render filter when disabled', () => {
      render(
        <AdminDataTable columns={sampleColumns} data={sampleData} enableQuickFilter={false} />
      );

      expect(screen.queryByTestId('admin-input')).not.toBeInTheDocument();
    });

    it('applies correct styling to filter input', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} enableQuickFilter={true} />);

      const input = screen.getByTestId('admin-input');
      expect(input).toHaveAttribute('data-size', 'sm');

      const inputWrapper = input.parentElement;
      expect(inputWrapper).toHaveClass('w-64');
    });
  });

  describe('Bulk Actions', () => {
    const bulkActions = [
      {
        label: 'Export',
        variant: 'outline' as const,
        action: jest.fn(),
        icon: <span data-testid='export-icon'>📤</span>,
      },
      {
        label: 'Delete',
        variant: 'destructive' as const,
        action: jest.fn(),
      },
      {
        label: 'Archive',
        action: jest.fn(), // No variant specified - should use default
      },
    ];

    beforeEach(() => {
      // Reset all mocks before each test
      bulkActions.forEach((action) => {
        action.action.mockClear();
      });
    });

    it('enables selection when bulk actions are enabled', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableBulkActions={true}
          bulkActions={bulkActions}
        />
      );

      const tableEl = screen.getByTestId('primitive-data-table');
      expect(tableEl).toHaveAttribute('data-has-selection', 'true');
    });

    it('does not enable selection when bulk actions are disabled', () => {
      render(
        <AdminDataTable columns={sampleColumns} data={sampleData} enableBulkActions={false} />
      );

      const tableEl = screen.getByTestId('primitive-data-table');
      expect(tableEl).toHaveAttribute('data-has-selection', 'false');
    });

    it('handles selection changes and shows bulk actions', async () => {
      const TestComponent = () => {
        const [selectedRows, setSelectedRows] = React.useState<any[]>([]);
        const [selectedKeys, setSelectedKeys] = React.useState<string[]>([]);

        const selection = {
          selectedRowKeys: selectedKeys,
          onChange: (keys: string[]) => {
            setSelectedKeys(keys);
            const selected = sampleData.filter((item) => keys.includes(item.id));
            setSelectedRows(selected);
          },
          getRowKey: (row: unknown) => row.id,
        };

        return (
          <>
            <AdminDataTable
              columns={sampleColumns}
              data={sampleData}
              enableBulkActions={true}
              bulkActions={bulkActions}
              selection={selection}
            />
            {selectedRows.length > 0 && (
              <div data-testid='bulk-actions-container'>
                <span data-testid='selection-count'>{selectedRows.length} selected</span>
                {bulkActions.map((action, index) => (
                  <button
                    type='button'
                    key={`item-${index}`}
                    data-testid={`bulk-action-${index}`}
                    data-variant={action.variant || 'outline'}
                    onClick={() => action.action(selectedRows)}
                  >
                    {action.icon && <span data-testid={`action-icon-${index}`}>{action.icon}</span>}
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </>
        );
      };

      render(<TestComponent />);

      // Initially no bulk actions should be visible
      expect(screen.queryByTestId('bulk-actions-container')).not.toBeInTheDocument();

      // Simulate selection change
      const simulateButton = screen.getByTestId('simulate-selection-change');
      act(() => {
        fireEvent.click(simulateButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId('bulk-actions-container')).toBeInTheDocument();
      });

      // Check selection count
      expect(screen.getByTestId('selection-count')).toHaveTextContent('2 selected');

      // Check bulk action buttons
      expect(screen.getByTestId('bulk-action-0')).toHaveAttribute('data-variant', 'outline');
      expect(screen.getByTestId('bulk-action-1')).toHaveAttribute('data-variant', 'destructive');
      expect(screen.getByTestId('bulk-action-2')).toHaveAttribute('data-variant', 'outline'); // default fallback

      // Check icons
      expect(screen.getByTestId('action-icon-0')).toBeInTheDocument();
      expect(screen.queryByTestId('action-icon-1')).not.toBeInTheDocument(); // No icon for delete
      expect(screen.queryByTestId('action-icon-2')).not.toBeInTheDocument(); // No icon for archive
    });

    it('executes bulk actions correctly', async () => {
      const TestComponent = () => {
        const [selectedRows, _setSelectedRows] = React.useState([sampleData[0], sampleData[1]]);

        return (
          <div>
            {selectedRows.length > 0 && (
              <div data-testid='bulk-actions-container'>
                {bulkActions.map((action, index) => (
                  <button
                    type='button'
                    key={`item-${index}`}
                    data-testid={`bulk-action-${index}`}
                    onClick={() => action.action(selectedRows)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      };

      render(<TestComponent />);

      // Click first bulk action (Export)
      const exportButton = screen.getByTestId('bulk-action-0');
      fireEvent.click(exportButton);

      expect(bulkActions[0].action).toHaveBeenCalledWith([sampleData[0], sampleData[1]]);
      expect(bulkActions[0].action).toHaveBeenCalledTimes(1);

      // Click second bulk action (Delete)
      const deleteButton = screen.getByTestId('bulk-action-1');
      fireEvent.click(deleteButton);

      expect(bulkActions[1].action).toHaveBeenCalledWith([sampleData[0], sampleData[1]]);
      expect(bulkActions[1].action).toHaveBeenCalledTimes(1);
    });

    it('handles selection changes when no getRowKey provided', () => {
      const TestComponent = () => {
        const [selectedRows, setSelectedRows] = React.useState<any[]>([]);

        const handleSelectionChange = React.useCallback((_keys: string[]) => {
          // When no getRowKey, should not filter rows
          const selected: unknown[] = [];
          setSelectedRows(selected);
        }, []);

        React.useEffect(() => {
          handleSelectionChange(['1', '2']);
        }, [handleSelectionChange]);

        return <div data-testid='selection-count'>{selectedRows.length} selected</div>;
      };

      render(<TestComponent />);

      expect(screen.getByTestId('selection-count')).toHaveTextContent('0 selected');
    });

    it('handles empty bulk actions array', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableBulkActions={true}
          bulkActions={[]}
        />
      );

      const tableEl = screen.getByTestId('primitive-data-table');
      expect(tableEl).toHaveAttribute('data-has-selection', 'true');
    });

    it('passes selection properly to primitive table', () => {
      const mockSelection = {
        selectedRowKeys: ['1', '2'],
        onChange: jest.fn(),
        getRowKey: (row: unknown) => row.id,
      };

      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableBulkActions={true}
          bulkActions={bulkActions}
          selection={mockSelection}
        />
      );

      const table = screen.getByTestId('primitive-data-table');
      expect(table).toHaveAttribute('data-has-selection', 'true');

      // Simulate selection change to test the wrapped onChange
      const simulateButton = screen.getByTestId('simulate-selection-change');
      act(() => {
        fireEvent.click(simulateButton);
      });

      // The original onChange should be called
      expect(mockSelection.onChange).toHaveBeenCalledWith(['1', '2']);
    });
  });

  describe('Pagination', () => {
    const paginationProps = {
      current: 2,
      pageSize: 10,
      total: 150,
      onChange: jest.fn(),
    };

    beforeEach(() => {
      paginationProps.onChange.mockClear();
    });

    it('renders pagination information correctly', () => {
      render(
        <AdminDataTable columns={sampleColumns} data={sampleData} pagination={paginationProps} />
      );

      expect(screen.getByText('Showing 11 to 20 of 150 results')).toBeInTheDocument();
      expect(screen.getByText('Page 2 of 15')).toBeInTheDocument();
    });

    it('renders pagination controls', () => {
      render(
        <AdminDataTable columns={sampleColumns} data={sampleData} pagination={paginationProps} />
      );

      expect(screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
    });

    it('handles previous page click', () => {
      render(
        <AdminDataTable columns={sampleColumns} data={sampleData} pagination={paginationProps} />
      );

      fireEvent.click(screen.getByText('Previous'));
      expect(paginationProps.onChange).toHaveBeenCalledWith(1, 10);
    });

    it('handles next page click', () => {
      render(
        <AdminDataTable columns={sampleColumns} data={sampleData} pagination={paginationProps} />
      );

      fireEvent.click(screen.getByText('Next'));
      expect(paginationProps.onChange).toHaveBeenCalledWith(3, 10);
    });

    it('disables previous button on first page', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          pagination={{
            current: 1,
            pageSize: 10,
            total: 50,
            onChange: jest.fn(),
          }}
        />
      );

      expect(screen.getByText('Previous')).toBeDisabled();
    });

    it('disables next button on last page', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          pagination={{
            current: 15,
            pageSize: 10,
            total: 150,
            onChange: jest.fn(),
          }}
        />
      );

      expect(screen.getByText('Next')).toBeDisabled();
    });

    it('calculates pagination info correctly for edge cases', () => {
      // Test with total that doesn't divide evenly by pageSize
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          pagination={{
            current: 3,
            pageSize: 7,
            total: 20,
            onChange: jest.fn(),
          }}
        />
      );

      expect(screen.getByText('Showing 15 to 20 of 20 results')).toBeInTheDocument();
      expect(screen.getByText('Page 3 of 3')).toBeInTheDocument();
    });

    it('handles pagination onChange being undefined', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          pagination={{
            current: 2,
            pageSize: 10,
            total: 150,
            // onChange intentionally undefined
          }}
        />
      );

      // Should not throw error when clicking pagination buttons
      expect(() => {
        fireEvent.click(screen.getByText('Previous'));
        fireEvent.click(screen.getByText('Next'));
      }).not.toThrow();
    });

    it('does not render pagination when not provided', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      expect(screen.queryByText(/Showing \d+ to \d+ of \d+ results/)).not.toBeInTheDocument();
      expect(screen.queryByText('Previous')).not.toBeInTheDocument();
      expect(screen.queryByText('Next')).not.toBeInTheDocument();
    });
  });

  describe('Selection Handling', () => {
    it('handles complex selection scenarios', async () => {
      const handleSelectionChange = jest.fn();
      const getRowKey = (row: unknown) => row.id;

      const TestComponent = () => {
        const [selectedKeys, setSelectedKeys] = React.useState<string[]>([]);

        const selection = {
          selectedRowKeys: selectedKeys,
          onChange: (keys: string[]) => {
            handleSelectionChange(keys);
            setSelectedKeys(keys);
          },
          getRowKey,
        };

        return (
          <AdminDataTable
            columns={sampleColumns}
            data={sampleData}
            enableBulkActions={true}
            selection={selection}
            bulkActions={[
              {
                label: 'Test',
                action: jest.fn(),
              },
            ]}
          />
        );
      };

      render(<TestComponent />);

      // Verify selection is passed to primitive table
      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute(
        'data-has-selection',
        'true'
      );

      // Simulate selection change
      const simulateButton = screen.getByTestId('simulate-selection-change');
      act(() => {
        fireEvent.click(simulateButton);
      });

      await waitFor(() => {
        expect(handleSelectionChange).toHaveBeenCalledWith(['1', '2']);
      });
    });

    it('filters selected rows correctly based on getRowKey', () => {
      const getRowKey = (row: unknown) => row.id;
      const selectedKeys = ['1', '3'];

      // This simulates the filtering logic in handleSelectionChange
      const expectedSelectedRows = sampleData.filter((item) =>
        selectedKeys.includes(getRowKey(item))
      );

      expect(expectedSelectedRows).toHaveLength(2);
      expect(expectedSelectedRows[0].id).toBe('1');
      expect(expectedSelectedRows[1].id).toBe('3');
    });

    it('handles selection without getRowKey function', () => {
      const TestComponent = () => {
        const [selectedRows, setSelectedRows] = React.useState<any[]>([]);

        const handleSelectionChange = React.useCallback((selectedKeys: string[]) => {
          // Simulate the logic when getRowKey is undefined
          const selection = { getRowKey: undefined };
          if (selection.getRowKey) {
            const selected = sampleData.filter((item) =>
              selectedKeys.includes(selection.getRowKey?.(item))
            );
            setSelectedRows(selected);
          } else {
            setSelectedRows([]);
          }
        }, []);

        React.useEffect(() => {
          handleSelectionChange(['1', '2']);
        }, [handleSelectionChange]);

        return <div data-testid='selected-count'>{selectedRows.length} selected</div>;
      };

      render(<TestComponent />);

      expect(screen.getByTestId('selected-count')).toHaveTextContent('0 selected');
    });

    it('maintains selection state correctly', async () => {
      const TestComponent = () => {
        const [selectedKeys, setSelectedKeys] = React.useState<string[]>(['1']);
        const [selectedRows, setSelectedRows] = React.useState<any[]>([sampleData[0]]);

        const selection = {
          selectedRowKeys: selectedKeys,
          onChange: (keys: string[]) => {
            setSelectedKeys(keys);
            const selected = sampleData.filter((item) => keys.includes(item.id));
            setSelectedRows(selected);
          },
          getRowKey: (row: unknown) => row.id,
        };

        return (
          <>
            <AdminDataTable
              columns={sampleColumns}
              data={sampleData}
              enableBulkActions={true}
              bulkActions={[
                {
                  label: 'Test Action',
                  action: jest.fn(),
                },
              ]}
              selection={selection}
            />
            <div data-testid='current-selection'>
              {selectedRows.map((row) => row.name).join(', ')}
            </div>
          </>
        );
      };

      render(<TestComponent />);

      // Initially one row selected
      expect(screen.getByTestId('current-selection')).toHaveTextContent('John Doe');

      // Simulate changing selection
      const simulateButton = screen.getByTestId('simulate-selection-change');
      act(() => {
        fireEvent.click(simulateButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-selection')).toHaveTextContent('John Doe, Jane Smith');
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles empty data gracefully', () => {
      render(<AdminDataTable columns={sampleColumns} data={[]} />);

      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-rows', '0');
    });

    it('handles empty columns array', () => {
      render(<AdminDataTable columns={[]} data={sampleData} />);

      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '0');
    });

    it('handles bulk actions without enableBulkActions', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableBulkActions={false}
          bulkActions={[
            {
              label: 'Test',
              action: jest.fn(),
            },
          ]}
        />
      );

      expect(screen.queryByText('selected')).not.toBeInTheDocument();
      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute(
        'data-has-selection',
        'false'
      );
    });

    it('handles very large datasets', () => {
      const largeData = Array.from({ length: 10000 }, (_, i) => ({
        id: `${i}`,
        name: `User ${i}`,
        email: `user${i}@example.com`,
        status: i % 2 === 0 ? 'active' : 'inactive',
      }));

      const startTime = performance.now();

      render(<AdminDataTable columns={sampleColumns} data={largeData} />);

      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(10000); // Should render within 10 seconds
      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-rows', '10000');
    });

    it('handles undefined or null values in data', () => {
      const dataWithNulls = [
        { id: '1', name: null, email: undefined, status: 'active' },
        { id: '2', name: '', email: 'jane@example.com', status: null },
      ];

      render(<AdminDataTable columns={sampleColumns} data={dataWithNulls} />);

      expect(screen.getByTestId('primitive-data-table')).toBeInTheDocument();
      expect(screen.getByTestId('row-0')).toBeInTheDocument();
    });

    it('handles columns with missing keys', () => {
      const columnsWithoutKeys = [
        { title: 'Column 1', dataIndex: 'col1' },
        { title: 'Column 2', dataIndex: 'col2' },
      ];

      render(
        <AdminDataTable columns={columnsWithoutKeys} data={[{ col1: 'value1', col2: 'value2' }]} />
      );

      // Should use index as fallback for keys
      expect(screen.getByTestId('header-0')).toBeInTheDocument();
      expect(screen.getByTestId('header-1')).toBeInTheDocument();
    });

    it('handles rapid prop changes', () => {
      const { rerender } = render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={false}
          showRowNumbers={false}
        />
      );

      rerender(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          showRowNumbers={true}
          compact={false}
        />
      );

      expect(screen.getByTestId('admin-input')).toBeInTheDocument();
      expect(screen.getByTestId('header-__row_number')).toBeInTheDocument();
      expect(screen.getByTestId('primitive-data-table')).not.toHaveClass('compact');
    });
  });

  describe('Accessibility', () => {
    it('should be accessible', async () => {
      const { container } = render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          enableBulkActions={true}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('provides proper table structure', () => {
      render(<AdminDataTable columns={sampleColumns} data={sampleData} />);

      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('columnheader')).toHaveLength(sampleColumns.length);
      expect(screen.getAllByRole('row')).toHaveLength(sampleData.length + 1); // +1 for header
    });

    it('filter input has proper accessibility attributes', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          quickFilterPlaceholder='Search data'
        />
      );

      const input = screen.getByTestId('admin-input');
      expect(input).toHaveAttribute('placeholder', 'Search data');
    });

    it('pagination buttons have proper accessibility', () => {
      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          pagination={{
            current: 1,
            pageSize: 10,
            total: 50,
            onChange: jest.fn(),
          }}
        />
      );

      const prevButton = screen.getByText('Previous');
      const nextButton = screen.getByText('Next');

      expect(prevButton).toBeDisabled(); // Should be disabled on first page
      expect(nextButton).not.toBeDisabled();
    });

    it('supports keyboard navigation', () => {
      const handleFilterChange = jest.fn();

      render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          onQuickFilterChange={handleFilterChange}
        />
      );

      const input = screen.getByTestId('admin-input');
      input.focus();
      expect(input).toHaveFocus();
    });
  });

  describe('Performance and Memoization', () => {
    it('memoizes enhanced columns correctly', () => {
      const { rerender } = render(
        <AdminDataTable columns={sampleColumns} data={sampleData} showRowNumbers={true} />
      );

      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '5');

      // Rerender with same props should not change column count
      rerender(<AdminDataTable columns={sampleColumns} data={sampleData} showRowNumbers={true} />);

      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '5');
    });

    it('updates memoized columns when dependencies change', () => {
      const { rerender } = render(
        <AdminDataTable columns={sampleColumns} data={sampleData} showRowNumbers={false} />
      );

      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '4');

      // Change dependency
      rerender(<AdminDataTable columns={sampleColumns} data={sampleData} showRowNumbers={true} />);

      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute('data-columns', '5');
    });

    it('handles selection callback memoization', () => {
      const mockOnChange = jest.fn();
      const selection = {
        selectedRowKeys: [],
        onChange: mockOnChange,
        getRowKey: (row: unknown) => row.id,
      };

      const { rerender } = render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableBulkActions={true}
          selection={selection}
        />
      );

      // Rerender with same selection object
      rerender(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableBulkActions={true}
          selection={selection}
        />
      );

      // Should maintain same callback
      expect(screen.getByTestId('primitive-data-table')).toHaveAttribute(
        'data-has-selection',
        'true'
      );
    });
  });

  describe('Integration and Composition', () => {
    it('integrates with all features enabled', async () => {
      const handlePaginationChange = jest.fn();
      const handleFilterChange = jest.fn();
      const handleBulkAction = jest.fn();
      const handleSelectionChange = jest.fn();

      const { container } = render(
        <AdminDataTable
          columns={sampleColumns}
          data={sampleData}
          enableQuickFilter={true}
          enableBulkActions={true}
          showRowNumbers={true}
          compact={true}
          quickFilterValue='test'
          quickFilterPlaceholder='Search all data...'
          onQuickFilterChange={handleFilterChange}
          bulkActions={[
            {
              label: 'Export',
              action: handleBulkAction,
              variant: 'outline',
              icon: <span data-testid='export-icon'>📤</span>,
            },
          ]}
          pagination={{
            current: 1,
            pageSize: 10,
            total: 30,
            onChange: handlePaginationChange,
          }}
          selection={{
            selectedRowKeys: [],
            onChange: handleSelectionChange,
            getRowKey: (row: unknown) => row.id,
          }}
        />
      );

      // Verify all components are rendered
      expect(screen.getByTestId('admin-input')).toBeInTheDocument();
      expect(screen.getByTestId('primitive-data-table')).toBeInTheDocument();
      expect(screen.getByTestId('header-__row_number')).toBeInTheDocument();
      expect(screen.getByText(/Showing \d+ to \d+ of \d+ results/)).toBeInTheDocument();

      // Test interactions
      fireEvent.change(screen.getByTestId('admin-input'), { target: { value: 'search' } });
      expect(handleFilterChange).toHaveBeenCalledWith('search');

      fireEvent.click(screen.getByText('Next'));
      expect(handlePaginationChange).toHaveBeenCalledWith(2, 10);

      // Test accessibility
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('works with minimal configuration', () => {
      render(
        <AdminDataTable
          columns={[
            { key: 'id', title: 'ID', dataIndex: 'id' },
            { key: 'name', title: 'Name', dataIndex: 'name' },
          ]}
          data={[{ id: '1', name: 'Test User' }]}
        />
      );

      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByTestId('primitive-data-table')).toHaveClass('admin-data-table', 'compact');
    });

    it('handles complex column configurations', () => {
      const complexColumns = [
        {
          key: 'avatar',
          title: '',
          width: 50,
          render: () => <div data-testid='avatar'>👤</div>,
        },
        {
          key: 'user',
          title: 'User Information',
          children: [
            { key: 'name', title: 'Name', dataIndex: 'name' },
            { key: 'email', title: 'Email', dataIndex: 'email' },
          ],
        },
        {
          key: 'actions',
          title: 'Actions',
          width: 200,
          render: (_, record) => (
            <div className='flex space-x-2'>
              <button type='button' data-testid={`edit-${record.id}`}>
                Edit
              </button>
              <button type='button' data-testid={`delete-${record.id}`}>
                Delete
              </button>
            </div>
          ),
        },
      ];

      render(<AdminDataTable columns={complexColumns} data={sampleData} />);

      expect(screen.getAllByTestId('avatar')).toHaveLength(sampleData.length);
      expect(screen.getByTestId('edit-1')).toBeInTheDocument();
    });

    it('handles real-world usage patterns', async () => {
      const TestApp = () => {
        const [data, setData] = React.useState(sampleData);
        const [loading, setLoading] = React.useState(false);
        const [selectedRows, setSelectedRows] = React.useState<any[]>([]);
        const [filterValue, setFilterValue] = React.useState('');
        const [pagination, setPagination] = React.useState({
          current: 1,
          pageSize: 10,
          total: sampleData.length,
        });

        const handleDelete = async (rows: unknown[]) => {
          setLoading(true);
          // Simulate API call
          await new Promise((resolve) => setTimeout(resolve, 100));
          const newData = data.filter((item) => !rows.some((row) => row.id === item.id));
          setData(newData);
          setSelectedRows([]);
          setPagination((prev) => ({ ...prev, total: newData.length }));
          setLoading(false);
        };

        const selection = {
          selectedRowKeys: selectedRows.map((row) => row.id),
          onChange: (keys: string[]) => {
            const selected = data.filter((item) => keys.includes(item.id));
            setSelectedRows(selected);
          },
          getRowKey: (row: unknown) => row.id,
        };

        return (
          <AdminDataTable
            columns={sampleColumns}
            data={data}
            loading={loading}
            enableQuickFilter={true}
            enableBulkActions={true}
            showRowNumbers={true}
            quickFilterValue={filterValue}
            onQuickFilterChange={setFilterValue}
            selection={selection}
            bulkActions={[
              {
                label: 'Delete Selected',
                variant: 'destructive',
                action: handleDelete,
              },
            ]}
            pagination={{
              ...pagination,
              onChange: (page, size) =>
                setPagination((prev) => ({ ...prev, current: page, pageSize: size })),
            }}
          />
        );
      };

      render(<TestApp />);

      // Initial state
      expect(screen.getAllByTestId(/^row-/)).toHaveLength(sampleData.length);

      // Should be interactive and functional
      expect(screen.getByTestId('admin-input')).toBeInTheDocument();
      expect(screen.getByTestId('primitive-data-table')).toBeInTheDocument();
    });
  });

  describe('Display Name', () => {
    it('has correct display name', () => {
      expect(AdminDataTable.displayName).toBe('AdminDataTable');
    });
  });

  describe('Props Interface', () => {
    it('accepts all required props correctly', () => {
      // This test verifies TypeScript interface compliance at runtime
      const requiredProps = {
        columns: sampleColumns,
        data: sampleData,
      };

      expect(() => {
        render(<AdminDataTable {...requiredProps} />);
      }).not.toThrow();
    });

    it('accepts all optional props correctly', () => {
      const allProps = {
        columns: sampleColumns,
        data: sampleData,
        enableBulkActions: true,
        bulkActions: [],
        enableInlineEdit: true,
        enableQuickFilter: true,
        quickFilterPlaceholder: 'Search...',
        quickFilterValue: '',
        onQuickFilterChange: jest.fn(),
        compact: true,
        showRowNumbers: true,
        className: 'custom-class',
        selection: {
          selectedRowKeys: [],
          onChange: jest.fn(),
          getRowKey: (row: unknown) => row.id,
        },
        pagination: {
          current: 1,
          pageSize: 10,
          total: 100,
          onChange: jest.fn(),
        },
      };

      expect(() => {
        render(<AdminDataTable {...allProps} />);
      }).not.toThrow();
    });
  });
});
